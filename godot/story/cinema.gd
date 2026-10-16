class_name Cinema
extends Control
## Letterbox bars and the fade, on their own canvas layer BELOW the HUD and every text layer: a
## fade covers the picture and the letterbox, never words (knowledge/09 §1: the JS fade layer once
## hid the title drop and the end card). Animated on the game clock through tick(dt).
## The dialogue's white flash (闪白, docs/design/dialogue-staging.md §2.3) is here too, under the letterbox and the
## fade: it whitens the picture, never the box, the portrait or a word.

var flash_rect: ColorRect
var fade_rect: ColorRect
var bars: Array[ColorRect] = []
var fade_alpha := 0.0
var _fade_from := 0.0
var _fade_to := 0.0
var _fade_t := 0.0
var _fade_dur := 0.0
var _box := 0.0
var _box_to := 0.0


func _init() -> void:
	name = "Cinema"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	flash_rect = ColorRect.new()
	flash_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flash_rect.color = Color(1, 1, 1, 0)
	flash_rect.visible = false
	add_child(flash_rect)
	for i in 2:
		var b := ColorRect.new()
		b.color = Color8(7, 8, 11)
		b.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(b)
		bars.append(b)
	fade_rect = ColorRect.new()
	fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade_rect.color = Color(0, 0, 0, 0)
	add_child(fade_rect)


func fade_to(alpha: float, dur: float, color: Color) -> void:
	_fade_from = fade_alpha
	_fade_to = alpha
	_fade_t = 0.0
	_fade_dur = maxf(0.0001, dur)
	fade_rect.color = Color(color.r, color.g, color.b, fade_alpha)


## The flash's whiteness now (0: none); StoryUI sets it every frame from its staging.
func set_flash(alpha: float) -> void:
	flash_rect.visible = alpha > 0.0
	flash_rect.color.a = alpha
	flash_rect.position = Vector2.ZERO
	flash_rect.size = get_viewport_rect().size


func letterbox(on: bool) -> void:
	_box_to = 1.0 if on else 0.0


func tick(dt: float) -> void:
	var view := get_viewport_rect().size
	_fade_t += dt
	var k := clampf(_fade_t / _fade_dur, 0.0, 1.0) if _fade_dur > 0.0 else 1.0
	fade_alpha = lerpf(_fade_from, _fade_to, k)
	fade_rect.color.a = fade_alpha
	fade_rect.position = Vector2.ZERO
	fade_rect.size = view
	_box = move_toward(_box, _box_to, dt / 0.6)
	var hb := roundf(view.y * 0.11 * (_box * _box * (3.0 - 2.0 * _box)))
	bars[0].position = Vector2.ZERO
	bars[0].size = Vector2(view.x, hb)
	bars[1].position = Vector2(0, view.y - hb)
	bars[1].size = Vector2(view.x, hb)
