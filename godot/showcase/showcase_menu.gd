class_name ShowcaseMenu
extends Control
## The art sample's menu over the title backdrop (vista "title": night under the great camphor, the
## plain's lamps below). Title and entries in the pixel font on whole native pixels.
## Keys: up/down (W/S, arrows, d-pad, left stick) choose, Enter/Space/gamepad A confirm; the mouse
## points and clicks.

signal chosen(id: String, index: int)

const TEXT := Color8(243, 236, 220)
const DIM := Color8(243, 236, 220, 150)
const HINT := Color8(214, 200, 170, 120)
const MARK := Color8(196, 70, 46)
const SHADOW := Color8(8, 7, 12, 200)
const LINE := 18

var index := 0
var vista: Vista
var title_label: Label
var sub_label: Label
var hint_label: Label
var items: Array[Label] = []
var mark: PixelMark
var _stick_t := 0.0
var _ids: Array[String] = []


func _init() -> void:
	name = "Menu"
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS


func _ready() -> void:
	vista = Vista.new()
	vista.name = "TitleVista"
	add_child(vista)
	vista.show_shot("title")
	title_label = _label("天岸", UiTheme.size("pixel", "title"), TEXT)
	sub_label = _label("美术样章", 12, DIM)
	hint_label = _label("↑↓ 选择　Enter 确定　F11 全屏", 12, HINT)
	for e in _entries():
		_ids.append(String(e[0]))
		var l := _label(String(e[1]), 12, DIM)
		l.mouse_filter = Control.MOUSE_FILTER_STOP
		var i := items.size()
		l.mouse_entered.connect(func() -> void: _select(i))
		l.gui_input.connect(func(ev: InputEvent) -> void:
			if ev is InputEventMouseButton and ev.pressed and (ev as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
				_select(i)
				_confirm())
		items.append(l)
	mark = PixelMark.new()
	mark.colour = MARK
	add_child(mark)
	index = clampi(index, 0, items.size() - 1)
	resized.connect(_layout)
	_layout()
	_select(index)
	Audio.ambience(["night"])


func _entries() -> Array:
	var fs := DisplayServer.window_get_mode() in [DisplayServer.WINDOW_MODE_FULLSCREEN, DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN]
	var calm := GameState.reduce_motion()
	return [["home", "家一带"], ["lookout", "眺望岩"], ["vista", "序章·树顶远景"], ["gallery", "立绘"],
		["motion", "减少晃动：开" if calm else "减少晃动：关"], ["fullscreen", "窗口" if fs else "全屏"], ["quit", "退出"]]


## After the window mode or a setting changed: those entries say their state.
func refresh() -> void:
	var es := _entries()
	for i in items.size():
		items[i].text = String(es[i][1])
	_layout()


func _label(t: String, px: int, c: Color) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_font_override("font", UiTheme.font("pixel"))
	l.add_theme_font_size_override("font_size", px)
	l.add_theme_color_override("font_color", c)
	l.add_theme_color_override("font_shadow_color", SHADOW)
	l.add_theme_constant_override("shadow_offset_x", 1)
	l.add_theme_constant_override("shadow_offset_y", 1)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l


## A column on the left, over the night sky and the dark hill (the plain's lamps are kept clear of the
## words). Everything on whole pixels.
func _layout() -> void:
	if title_label == null:
		return
	var p := Vector2(roundf(size.x * 0.07), roundf(size.y * 0.30))
	title_label.position = p
	sub_label.position = (p + Vector2(2, 30)).round()
	var y := p.y + 58.0
	for i in items.size():
		items[i].position = Vector2(p.x + 12.0, y + i * LINE).round()
	mark.position = Vector2(p.x + 2.0, y + index * LINE + 4.0).round()
	hint_label.position = Vector2(size.x - 8.0 - hint_label.get_minimum_size().x, size.y - 20.0).round()


func _process(dt: float) -> void:
	var ay := Input.get_joy_axis(0, JOY_AXIS_LEFT_Y)
	if absf(ay) > 0.5:
		_stick_t -= dt
		if _stick_t <= 0.0:
			_select(index + (1 if ay > 0.0 else -1))
			_stick_t = 0.22
	else:
		_stick_t = 0.0


func _select(i: int) -> void:
	index = wrapi(i, 0, items.size())
	for k in items.size():
		items[k].add_theme_color_override("font_color", TEXT if k == index else DIM)
	_layout()


func _confirm() -> void:
	chosen.emit(_ids[index], index)


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed:
		match (e as InputEventKey).keycode:
			KEY_UP, KEY_W:
				_select(index - 1)
			KEY_DOWN, KEY_S:
				_select(index + 1)
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				if not (e as InputEventKey).echo:
					_confirm()
			_:
				return
		get_viewport().set_input_as_handled()
	elif e is InputEventJoypadButton and e.pressed:
		match (e as InputEventJoypadButton).button_index:
			JOY_BUTTON_DPAD_UP:
				_select(index - 1)
			JOY_BUTTON_DPAD_DOWN:
				_select(index + 1)
			JOY_BUTTON_A:
				_confirm()
			_:
				return
		get_viewport().set_input_as_handled()


## A 5 x 5 pixel diamond (the dialogue box's mark), drawn on whole pixels.
class PixelMark:
	extends Control
	var colour := Color.WHITE

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		size = Vector2(5, 5)

	func _draw() -> void:
		for r in 5:
			var w := 5 - 2 * absi(r - 2)
			draw_rect(Rect2((5 - w) / 2, r, w, 1), colour)
