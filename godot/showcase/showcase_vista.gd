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
	vista.beat.connect(_on_beat)
	_play()


## The sound on the prologue's beats (v0.1 and the JS segment 1, src/story/seg1.js, on the same beats): the
## prologue's piece at dusk; as the first lamp leaves, the 遠囃子 comes from nearby and the piece goes; it thins
## to wind while the lamps leave, comes back clear when the sky shore opens ("the hayashi was theirs"); the
## tower's last pulse; the far's wave with the tension piece; her shout; the white cuts everything (v0.1's far
## wave), and what the far has left is heard from far away.
func _on_beat(name: String) -> void:
	match name:
		"begin":
			Audio.far(0.0)
			Audio.music("prologue", {"fade": 2.0, "restart": true})
			Audio.festival(0.0, 0.0, 0.5)
		"first_light":
			Audio.music("none", {"fade": 3.0})
			Audio.festival(0.25, 0.6, 1.5)
		"lights_leave":
			Audio.festival(0.1, 0.3, 2.0)
		"sky_opens":
			Audio.festival(0.0, 0.0, 1.2)
		"pause_sky_shore":
			Audio.festival(0.55, 1.0, 1.5)
		"tower_dark":
			Audio.play("far_pulse", {"bus": "Music"})
		"far_spreads":
			Audio.music("tension", {"fade": 1.0})
			Audio.play("far_wave", {"bus": "Music"})
		"pose_shout":
			Audio.blip("tsuzumi", 1)
		"end":
			Audio.music("none", {"fade": 0.1})
			Audio.festival(0.0, 0.0, 0.1)
			Audio.hush(2.4, 1.1)
			Audio.far(0.85)


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
