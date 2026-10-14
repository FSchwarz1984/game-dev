extends Node
## InputRouter (autoload): keyboard, gamepad and touch -> movement and semantic actions.
## Every touch is routed here, in _input, before any Control could see it: the visual layers are
## all mouse_filter = IGNORE and register hit rectangles instead, so no overlay can swallow a touch
## (the bug that hit the JS version twice: knowledge/09 §1, decision P-2). The routing order for a
## new touch: capture (dialogue open: any tap advances) > registered keys (quality keys, context
## key) > the floating stick (left half, touch UI only) > a tap on the world (target pick).
## Mouse clicks become touches (input_devices/pointing/emulate_touch_from_mouse); the mouse events
## themselves are ignored here, so nothing is handled twice.
##
## Signal `action(a)`, a.type:
##   "quality"  {k, gesture: "press" | "alt" | "release", source: "key" | "pad" | "touch"}
##              keyboard: 1-5 press, Shift+1-5 alt, L then 1-5 release; pad: X Y B RB LB press,
##              with LT held alt, with RT held release; touch (scheme "explicit"): tap press,
##              swipe up alt, swipe down release; touch (scheme "obvious"): tap press, long press alt.
##              What a gesture does is the game's business (Field.check / Field.plan per scheme).
##   "context"  E / Enter / pad A / the context key      "advance"  any tap while a dialogue captures
##   "dodge"    Space      "cycle"  Tab / pad R3       "pause"  Esc / pad Start / Android back
##   "dispatch" F   "recall" R   (stubs)               "pick"  {pos: logical screen px}
##   "dev"      {what: "scheme" | "font" | "body" | "touch" | "cinema"} F6-F10, debug builds only

signal action(a: Dictionary)

const KEY_QUALITY := {KEY_1: "w", KEY_2: "h", KEY_3: "l", KEY_4: "s", KEY_5: "v"}
const PAD_QUALITY := {
	JOY_BUTTON_X: "w", JOY_BUTTON_Y: "h", JOY_BUTTON_B: "l",
	JOY_BUTTON_RIGHT_SHOULDER: "s", JOY_BUTTON_LEFT_SHOULDER: "v",
}
const TAP_MAX_S := 0.3
const TAP_MAX_PX := 8.0
const KEY_MARGIN := 6.0

var enabled := true
var capture_all := false        # a dialogue is open: every tap advances it
var release_armed := false      # L pressed: the next quality key releases
var logical_size := Vector2(480, 270)

## Registered touch keys: id -> {"rect": Rect2 (logical px), "kind": "quality" | "button",
## "k": quality, "name": action name, "visible": bool}. The HUD updates these every frame.
var keys: Dictionary = {}
## Live touches: index -> {"owner": "capture" | "key" | "stick" | "world", ...}
var touches: Dictionary = {}
## The floating stick: {} when idle, else {"index", "origin", "pos", "r"} (logical px).
var stick: Dictionary = {}
var _lt := false
var _rt := false
var _fast_touch := false
var log_events := false         # debug bridge: print every routed action


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_bind("move_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT], [[JOY_AXIS_LEFT_X, -1.0]])
	_bind("move_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT], [[JOY_AXIS_LEFT_X, 1.0]])
	_bind("move_up", [KEY_W, KEY_UP], [JOY_BUTTON_DPAD_UP], [[JOY_AXIS_LEFT_Y, -1.0]])
	_bind("move_down", [KEY_S, KEY_DOWN], [JOY_BUTTON_DPAD_DOWN], [[JOY_AXIS_LEFT_Y, 1.0]])
	get_tree().root.size_changed.connect(_on_resize)
	_on_resize()


func _bind(name: String, keycodes: Array, buttons: Array, axes: Array) -> void:
	if InputMap.has_action(name):
		return
	InputMap.add_action(name, 0.2)
	for k in keycodes:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(name, e)
	for b in buttons:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(name, e)
	for a in axes:
		var e := InputEventJoypadMotion.new()
		e.axis = a[0]
		e.axis_value = a[1]
		InputMap.action_add_event(name, e)


func _on_resize() -> void:
	logical_size = get_tree().root.get_visible_rect().size


## Movement in world axes: x east, y south (= +z), length <= 1. The stick overrides keys and pad.
func move_vector() -> Vector2:
	if not enabled:
		return Vector2.ZERO
	if not stick.is_empty():
		var d: Vector2 = stick["pos"] - stick["origin"]
		var m := minf(1.0, d.length() / float(stick["r"]))
		if m >= 0.12:
			return d.normalized() * m
		return Vector2.ZERO
	return Input.get_vector("move_left", "move_right", "move_up", "move_down")


## Hold to fast-forward text: any advance key, pad A, or a touch held while a dialogue captures.
func fast_held() -> bool:
	return _fast_touch or Input.is_physical_key_pressed(KEY_E) or Input.is_physical_key_pressed(KEY_SPACE) \
		or Input.is_physical_key_pressed(KEY_ENTER) or Input.is_joy_button_pressed(0, JOY_BUTTON_A)


func _emit(a: Dictionary) -> void:
	if log_events:
		print("ACTION %s" % JSON.stringify(_printable(a)))
	action.emit(a)


static func _printable(a: Dictionary) -> Dictionary:
	var out := {}
	for k in a:
		out[k] = a[k] if not (a[k] is Vector2) else [a[k].x, a[k].y]
	return out


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_emit({"type": "pause"})
	elif what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		touches.clear()
		stick = {}
		_fast_touch = false


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch or event is InputEventScreenDrag:
		if event.device != InputEvent.DEVICE_ID_EMULATION and not GameState.touch_seen:
			GameState.touch_seen = true
		_touch(event)
		get_viewport().set_input_as_handled()
		return
	if not enabled:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		_key(event as InputEventKey)
	elif event is InputEventJoypadMotion:
		if event.axis == JOY_AXIS_TRIGGER_LEFT:
			_lt = event.axis_value > 0.5
		elif event.axis == JOY_AXIS_TRIGGER_RIGHT:
			_rt = event.axis_value > 0.5
	elif event is InputEventJoypadButton and event.pressed:
		_pad(event as InputEventJoypadButton)


func _key(e: InputEventKey) -> void:
	var code := e.physical_keycode
	if KEY_QUALITY.has(code):
		var gesture := "release" if release_armed else ("alt" if e.shift_pressed else "press")
		release_armed = false
		_emit({"type": "quality", "k": KEY_QUALITY[code], "gesture": gesture, "source": "key"})
		return
	match code:
		KEY_L:
			release_armed = true
			_emit({"type": "release_armed"})
		KEY_E, KEY_ENTER, KEY_KP_ENTER:
			_emit({"type": "context", "source": "key"})
		KEY_SPACE:
			_emit({"type": "dodge", "source": "key"})
		KEY_TAB:
			_emit({"type": "cycle"})
		KEY_F:
			_emit({"type": "dispatch"})
		KEY_R:
			_emit({"type": "recall"})
		KEY_ESCAPE:
			_emit({"type": "pause"})
		KEY_F6, KEY_F7, KEY_F8, KEY_F9, KEY_F10:
			if OS.is_debug_build():
				var what: String = {KEY_F6: "scheme", KEY_F7: "font", KEY_F8: "body", KEY_F9: "touch", KEY_F10: "cinema"}[code]
				_emit({"type": "dev", "what": what})


func _pad(e: InputEventJoypadButton) -> void:
	if PAD_QUALITY.has(e.button_index):
		var gesture := "release" if _rt else ("alt" if _lt else "press")
		_emit({"type": "quality", "k": PAD_QUALITY[e.button_index], "gesture": gesture, "source": "pad"})
		return
	match e.button_index:
		JOY_BUTTON_A:
			_emit({"type": "context", "source": "pad"})
		JOY_BUTTON_RIGHT_STICK:
			_emit({"type": "cycle"})
		JOY_BUTTON_START:
			_emit({"type": "pause"})


# ------------------------------------------------------------------ touch

func register_key(id: String, def: Dictionary) -> void:
	keys[id] = def


func unregister_key(id: String) -> void:
	keys.erase(id)


func key_at(pos: Vector2) -> String:
	var best := ""
	var best_d := INF
	for id in keys:
		var k: Dictionary = keys[id]
		if not k.get("visible", true):
			continue
		var r: Rect2 = k["rect"]
		if r.grow(KEY_MARGIN).has_point(pos):
			var d := r.get_center().distance_to(pos)
			if d < best_d:
				best_d = d
				best = id
	return best


## The gesture a held quality key would make if released now (for the key's live preview).
func held_gesture(id: String) -> String:
	for i in touches:
		var t: Dictionary = touches[i]
		if t["owner"] == "key" and t["id"] == id:
			return _gesture_of(t, Time.get_ticks_msec() / 1000.0)
	return ""


func _gesture_of(t: Dictionary, now: float) -> String:
	if String(GameState.setting("control_scheme")) == "obvious":
		return "alt" if now - float(t["t0"]) >= float(GameState.setting("long_press_s")) else "press"
	var dy: float = t["pos"].y - t["start"].y
	var swipe := float(GameState.setting("swipe_px"))
	if dy < -swipe:
		return "alt"
	if dy > swipe:
		return "release"
	return "press"


func _touch(e: InputEvent) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	var idx: int = e.index
	if e is InputEventScreenTouch and e.pressed:
		var pos: Vector2 = e.position
		var t := {"start": pos, "pos": pos, "t0": now, "owner": "world", "id": ""}
		if not enabled:
			t["owner"] = "none"
		elif capture_all:
			t["owner"] = "capture"
			_fast_touch = true
			_emit({"type": "advance", "source": "touch"})
		else:
			var id := key_at(pos)
			if id != "":
				t["owner"] = "key"
				t["id"] = id
				if keys[id].get("kind", "") == "button":
					_emit({"type": String(keys[id]["name"]), "source": "touch"})
			elif GameState.touch_ui_on() and pos.x < logical_size.x * 0.5:
				t["owner"] = "stick"
				var r := clampf(minf(logical_size.x, logical_size.y) * 0.12, 22.0, 36.0)
				stick = {"index": idx, "origin": pos, "pos": pos, "r": r}
		touches[idx] = t
	elif e is InputEventScreenDrag:
		if not touches.has(idx):
			return
		var t: Dictionary = touches[idx]
		t["pos"] = e.position
		if t["owner"] == "stick" and not stick.is_empty() and stick["index"] == idx:
			var d: Vector2 = e.position - stick["origin"]
			var max_d := float(stick["r"]) * 1.3
			if d.length() > max_d:  # the base follows the thumb
				stick["origin"] = e.position - d.normalized() * max_d
			stick["pos"] = e.position
	elif e is InputEventScreenTouch and not e.pressed:
		if not touches.has(idx):
			return
		var t: Dictionary = touches[idx]
		touches.erase(idx)
		t["pos"] = e.position
		var short: bool = now - float(t["t0"]) <= TAP_MAX_S and (e.position - t["start"]).length() <= TAP_MAX_PX
		match t["owner"]:
			"capture":
				_fast_touch = false
			"key":
				var k: Dictionary = keys.get(t["id"], {})
				if k.get("kind", "") == "quality" and not e.canceled:
					_emit({"type": "quality", "k": k["k"], "gesture": _gesture_of(t, now), "source": "touch"})
			"stick":
				if not stick.is_empty() and stick["index"] == idx:
					stick = {}
				if short:
					_emit({"type": "pick", "pos": t["start"]})
			"world":
				if short:
					_emit({"type": "pick", "pos": t["start"]})
