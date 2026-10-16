class_name ShowcaseVista
extends Control
## The prologue's treetop vista on its own (the beats of the prologue without its lines): the camera
## rises out of the camphor's crown over the plain at dusk, the lamps leave the ground and gather
## into the gate, the sky shore opens, the tower goes dark, the far comes up the mountain and washes
## the frame white. Then the white thins back to the sky shore over the dark plain and it holds there;
## Enter / gamepad A plays it again. Vista.play_standalone() runs it (its own director, her figure on
## the limb), so nothing here depends on the story's Director.

const TEXT := Color8(243, 236, 220, 150)
const SHADOW := Color8(8, 7, 12, 220)

var vista: Vista
var hint: Label
var _playing := false


func _init() -> void:
	name = "ShowcaseVista"
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	vista = Vista.new()
	vista.name = "PrologueVista"
	add_child(vista)
	hint = Label.new()
	hint.add_theme_font_override("font", UiTheme.font("pixel"))
	hint.add_theme_font_size_override("font_size", 12)
	hint.add_theme_color_override("font_color", TEXT)
	hint.add_theme_color_override("font_shadow_color", SHADOW)
	hint.add_theme_constant_override("shadow_offset_x", 1)
	hint.add_theme_constant_override("shadow_offset_y", 1)
	hint.text = "Enter 重放　Esc 菜单"
	hint.visible = false
	add_child(hint)
	Audio.ambience(["night", "wind"])
	_play()


func _play() -> void:
	if _playing:
		return
	_playing = true
	hint.visible = false
	await vista.play_standalone()
	_playing = false
	hint.visible = true


func _process(_dt: float) -> void:
	hint.position = Vector2(size.x - 8.0 - hint.get_minimum_size().x, size.y - 20.0).round()


func _unhandled_input(e: InputEvent) -> void:
	var go := false
	if e is InputEventKey and e.pressed and not e.echo:
		go = (e as InputEventKey).keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]
	elif e is InputEventJoypadButton and e.pressed:
		go = (e as InputEventJoypadButton).button_index == JOY_BUTTON_A
	if go and not _playing:
		get_viewport().set_input_as_handled()
		_play()
