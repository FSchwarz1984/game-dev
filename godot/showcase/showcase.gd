class_name Showcase
extends Node
## The art sample build delivered for Windows (G5R3-0): a menu over the title backdrop, and from it
## the home area (the 3D art sample: walk, time of day, rain), the lookout, the prologue's treetop
## vista and the portraits. Not the game's segment: no story, no lines.
##   Esc / gamepad B or Start: back to the menu (from the menu: nothing; 退出 quits)
##   F11 or Alt+Enter: fullscreen <-> window
## Command line (checks): -- --mode=home|lookout|vista|gallery starts there instead of the menu;
## the sample's own options (--hours=, --rain=, --shot=, ...) pass through to it.

const SAMPLE := "res://world3d/sample.tscn"
const MIN_W := 400.0

var mode := ""
var screen: Node = null         # the current screen (menu, sample, vista host, gallery)
var hud: ShowcaseHud = null
var hud_layer: CanvasLayer
var veil_layer: CanvasLayer
var veil: ColorRect
var args := {}
var _menu_index := 0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	hud_layer = CanvasLayer.new()
	hud_layer.name = "HudLayer"
	hud_layer.layer = 10
	add_child(hud_layer)
	veil_layer = CanvasLayer.new()
	veil_layer.name = "VeilLayer"
	veil_layer.layer = 50
	add_child(veil_layer)
	veil = ColorRect.new()
	veil.color = Color(0.039, 0.035, 0.05, 1.0)
	veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	veil.set_anchors_preset(Control.PRESET_FULL_RECT)
	veil.visible = false
	veil_layer.add_child(veil)
	get_window().size_changed.connect(_fit_canvas)
	if not args.has("windowed") and not OS.has_feature("editor") and not args.has("shot"):
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	_fit_canvas()
	open(String(args.get("mode", "menu")))


## The 2D canvas rule outside the 3D sample (which sets it itself, PixelView3D.fit): s = round(h /
## 360), the canvas is the window divided by s, so every native pixel is s x s window pixels.
func _fit_canvas() -> void:
	if mode == "home" or mode == "lookout":
		return
	var win := get_window()
	var size := Vector2(win.size)
	if size.x < 1.0 or size.y < 1.0:
		return
	var s := PixelStage.scale_for(size, PixelView3D.BASE)
	var cs := Vector2i(floori(size.x / s), floori(size.y / s))
	if win.content_scale_size != cs:
		win.content_scale_size = cs


## Go to a screen. The old one is freed first; a heavy one (the sample) is built a frame later
## behind the veil, so the switch never shows a half-built world.
func open(m: String) -> void:
	if not m in ["menu", "home", "lookout", "vista", "gallery"]:
		m = "menu"
	veil.visible = true
	if hud != null:
		hud.queue_free()
		hud = null
	if screen != null:
		screen.queue_free()
		screen = null
	Audio.ambience([])
	mode = m
	await get_tree().process_frame
	await get_tree().process_frame
	match m:
		"menu":
			_fit_canvas()
			var menu := ShowcaseMenu.new()
			menu.index = _menu_index
			menu.chosen.connect(_on_chosen)
			screen = menu
			add_child(menu)
		"home", "lookout":
			_open_sample(m)
		"vista":
			_fit_canvas()
			var host := ShowcaseVista.new()
			screen = host
			add_child(host)
		"gallery":
			_fit_canvas()
			var g := ShowcaseGallery.new()
			screen = g
			add_child(g)
	await get_tree().process_frame
	veil.visible = false


func _open_sample(m: String) -> void:
	var inst := (load(SAMPLE) as PackedScene).instantiate()
	# the sample adds its command-line options to `args` in _ready() and never clears it, so these
	# are its defaults here and the command line still wins
	var a: Dictionary = inst.get("args")
	a["hours"] = "9.5" if m == "home" else "16.5"
	# G5R3-21: this delivery has no character (her model is being redone): an unseen walker carries
	# the camera, nothing stands in for her
	a["nochar"] = "1"
	if m == "lookout":
		var lk := _lookout_start()
		if lk != Vector2.INF:
			a["at"] = "%.2f,%.2f" % [lk.x, lk.y]
	for k in args:
		if k != "mode":
			a[k] = args[k]
	screen = inst
	add_child(inst)
	hud = ShowcaseHud.new()
	hud.sample = inst
	hud.lookout = m == "lookout"
	hud_layer.add_child(hud)


## A point on the path a few steps before the lookout rock: walking onto it and standing still there
## turns the view out over the land (the sample's W3Vista).
func _lookout_start() -> Vector2:
	var f := FileAccess.open("res://world3d/terrain/saddle/terrain.json", FileAccess.READ)
	if f == null:
		return Vector2.INF
	var info: Variant = JSON.parse_string(f.get_as_text())
	if not info is Dictionary:
		return Vector2.INF
	var lk: Dictionary = (info as Dictionary).get("markers", {}).get("lookout", {})
	if lk.is_empty():
		return Vector2.INF
	var p := Vector2(float(lk["x"]), float(lk["z"]))
	var route: Array = (info as Dictionary).get("routes", {}).get("lookout", [])
	# the route's point about 3 m before its end (the rock), else 3 m north of the rock
	var best := p + Vector2(0.0, -3.0)
	for q in route:
		var v := Vector2(float(q[0]), float(q[1]))
		var d := v.distance_to(p)
		if d > 2.2 and d < 4.5:
			best = v
	return best


func _on_chosen(id: String, index: int) -> void:
	_menu_index = index
	match id:
		"quit":
			get_tree().quit()
		"fullscreen":
			_toggle_fullscreen()
			(screen as ShowcaseMenu).refresh()
		"motion":
			# 减少晃动 (docs/design/dialogue-staging.md D6): the dialogue's staging without movement or flashes
			GameState.set_setting("reduce_motion", not GameState.reduce_motion())
			(screen as ShowcaseMenu).refresh()
		_:
			open(id)


func _toggle_fullscreen() -> void:
	var m := DisplayServer.window_get_mode()
	if m == DisplayServer.WINDOW_MODE_FULLSCREEN or m == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
		var scr := DisplayServer.window_get_current_screen()
		var ss := DisplayServer.screen_get_size(scr)
		# the largest 16:9 window of whole 640x360 steps that fits the screen with room for its frame
		var k := maxi(1, mini(int((ss.x - 64) / 640.0), int((ss.y - 96) / 360.0)))
		var ws := Vector2i(640 * k, 360 * k)
		DisplayServer.window_set_size(ws)
		DisplayServer.window_set_position(DisplayServer.screen_get_position(scr) + (ss - ws) / 2)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)


func _input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		var k := e as InputEventKey
		if k.keycode == KEY_F11 or (k.keycode == KEY_ENTER and k.alt_pressed):
			_toggle_fullscreen()
			if screen is ShowcaseMenu:
				(screen as ShowcaseMenu).refresh()
			get_viewport().set_input_as_handled()
			return
		if k.keycode == KEY_ESCAPE and mode != "menu":
			get_viewport().set_input_as_handled()
			open("menu")
			return
	if e is InputEventJoypadButton and e.pressed and mode != "menu":
		var b := (e as InputEventJoypadButton).button_index
		if b == JOY_BUTTON_START or b == JOY_BUTTON_B:
			get_viewport().set_input_as_handled()
			open("menu")
