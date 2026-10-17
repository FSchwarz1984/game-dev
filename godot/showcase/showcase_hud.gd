class_name ShowcaseHud
extends Control
## The art sample's overlay over the 3D sample (world3d/sample.tscn): the hour and the weather in a
## corner, the keys along the bottom (they fade after a while; H brings them back), and the controls
## for the light: hold Q / E (gamepad LB / RB) to move the hour back / on, 1-4 jump to morning, noon,
## dusk, night, T lets the hour run on its own, R (gamepad Y) brings the rain or takes it away.
## V and B (the sample's own keys) change the camera (G5R3-27) and the depth of field (G5R3-28);
## both show under the hour.
## Walking is the sample's own (WASD / arrows; the gamepad's left stick where the sample reads it).
## The sound (the air of the hour and the weather, the creatures, her steps, the music) is ShowcaseSound's,
## synthesized (G5R3-53: no recordings).

const TEXT := Color8(243, 236, 220)
const DIM := Color8(243, 236, 220, 170)
const SHADOW := Color8(8, 7, 12, 220)
const SCRUB := 1.5            # hours per second while Q / E is held
const FLOW := 1.0 / 30.0      # hours per second when the hour runs on its own (an hour in 30 s)
const PRESETS := [6.6, 12.5, 17.6, 21.5]
const RAIN := 0.85

var sample: Node = null
var lookout := false
var clock: Label
var cam_name: Label
var keys: Label
var tip: Label
var _hint_t := 14.0
var _flow := false
var _rain_target := 0.0
var _rain := 0.0
var _push := 0.0              # pending hour change from the keys this frame
var _up := false              # the lines sit at the top while she looks out (the far view puts her at the bottom)


func _init() -> void:
	name = "ShowcaseHud"
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	clock = _label(12, TEXT)
	cam_name = _label(12, DIM)
	keys = _label(12, DIM)
	keys.text = "WASD 走　Q/E 时刻　1–4 晨午昏夜　T 时间流动　R 雨　V 镜头　B 景深　H 隐藏　Esc 菜单"
	tip = _label(12, DIM)
	tip.text = "走上岩石，站定一会儿就会远眺；A/D 转头，W/S 回来" if lookout else ""
	resized.connect(_layout)
	_layout()


func _label(px: int, c: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", UiTheme.font("pixel"))
	l.add_theme_font_size_override("font_size", px)
	l.add_theme_color_override("font_color", c)
	l.add_theme_color_override("font_shadow_color", SHADOW)
	l.add_theme_constant_override("shadow_offset_x", 1)
	l.add_theme_constant_override("shadow_offset_y", 1)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l


func _layout() -> void:
	clock.position = Vector2(8, 6)
	# the camera preset under the hour (G5R3-27); not while she looks out: the far view has its own
	# projection, and the lines take that place then
	cam_name.position = Vector2(8, 22)
	cam_name.visible = not _up
	if _up:
		# looking out: she and さぢ stand at the bottom of the picture, so the lines go under the clock
		tip.position = Vector2(8, 22)
		keys.position = Vector2(8, 38)
	else:
		keys.position = Vector2(8, size.y - 20.0).round()
		tip.position = Vector2(8, size.y - 36.0).round()


func _env() -> W3Env:
	if sample == null or not is_instance_valid(sample):
		return null
	return sample.get("env") as W3Env


func _process(dt: float) -> void:
	var env := _env()
	if env == null:
		return
	if _rain == 0.0 and _rain_target == 0.0 and env.rain > 0.0:
		_rain = env.rain               # started with --rain
		_rain_target = env.rain
	var h := env.hours
	var dh := 0.0
	if Input.is_physical_key_pressed(KEY_Q) or Input.is_joy_button_pressed(0, JOY_BUTTON_LEFT_SHOULDER):
		dh -= SCRUB * dt
	if Input.is_physical_key_pressed(KEY_E) or Input.is_joy_button_pressed(0, JOY_BUTTON_RIGHT_SHOULDER):
		dh += SCRUB * dt
	if _flow:
		dh += FLOW * dt
	dh += _push
	_push = 0.0
	var rain_moves := not is_equal_approx(_rain, _rain_target)
	if rain_moves:
		_rain = move_toward(_rain, _rain_target, dt / 2.5)
		env.rain = _rain
	if dh != 0.0 or rain_moves:
		sample.call("_set_hours", fposmod(h + dh, 24.0), absf(dh) > 1.0)
	clock.text = _clock_text(env.hours) + ("　雨" if _rain_target > 0.0 else "")
	if lookout:
		var v: Variant = sample.get("vista")
		var up: bool = v is Object and is_instance_valid(v) and (v as Object).get("active") == true
		if up != _up:
			_up = up
			_layout()
	if sample.has_method("camera_name"):
		cam_name.text = "镜头　" + String(sample.call("camera_name"))
		if sample.has_method("dof_name"):
			cam_name.text += "　景深　" + String(sample.call("dof_name"))
	if _hint_t > 0.0:
		_hint_t -= dt
		keys.modulate.a = clampf(_hint_t / 1.5, 0.0, 1.0)
		tip.modulate.a = keys.modulate.a




static func _clock_text(h: float) -> String:
	var m := int(roundf(fposmod(h, 24.0) * 60.0)) % 1440
	var part := "夜"
	var hh := m / 60.0
	if hh >= 4.5 and hh < 7.0:
		part = "清晨"
	elif hh >= 7.0 and hh < 11.0:
		part = "上午"
	elif hh >= 11.0 and hh < 13.0:
		part = "正午"
	elif hh >= 13.0 and hh < 16.5:
		part = "午后"
	elif hh >= 16.5 and hh < 19.0:
		part = "黄昏"
	return "%02d:%02d　%s" % [m / 60, m % 60, part]


func _show_keys() -> void:
	_hint_t = 14.0
	keys.modulate.a = 1.0
	tip.modulate.a = 1.0


func _unhandled_input(e: InputEvent) -> void:
	var env := _env()
	if env == null:
		return
	if e is InputEventKey and e.pressed and not e.echo:
		var k := (e as InputEventKey).physical_keycode
		match k:
			KEY_1, KEY_2, KEY_3, KEY_4:
				_push = fposmod(float(PRESETS[k - KEY_1]) - env.hours, 24.0)
				_flow = false
			KEY_T:
				_flow = not _flow
			KEY_R:
				_rain_target = 0.0 if _rain_target > 0.0 else RAIN
			KEY_H:
				if keys.modulate.a > 0.0:
					_hint_t = 0.0
					keys.modulate.a = 0.0
					tip.modulate.a = 0.0
				else:
					_show_keys()
			_:
				return
		get_viewport().set_input_as_handled()
	elif e is InputEventJoypadButton and e.pressed:
		if (e as InputEventJoypadButton).button_index == JOY_BUTTON_Y:
			_rain_target = 0.0 if _rain_target > 0.0 else RAIN
			get_viewport().set_input_as_handled()
		elif (e as InputEventJoypadButton).button_index == JOY_BUTTON_BACK:
			_show_keys()
			get_viewport().set_input_as_handled()
