class_name DialogueBox
extends Control
## The dialogue box at native pixel resolution (640x360 canvas), laid out per
## docs/knowledge/13-pixel-portraits.md §5 and §10: the 128x128 pixel portrait (v4, G5R2-2) stands in its
## own 132x132 card at the left end of the box (rising 72 px above it; its bottom 4 px above the box's
## bottom), and the text column starts 8 px right of the card, so the portrait can never cover a word
## (F-3). The name plate sits on the box's top border above the text column, always one line, as wide as
## the name. Narration (no speaker) has no card and uses the full width.
## The portrait talks while its line types and blinks now and then: overlays of only the changed pixels
## (art/portraits/<who>/<face>.talk1/.talk2/.blink1/.blink2.png, tools/art/portraits4/talkblink.py) drawn
## over it, so at rest it is exactly the approved expression (knowledge/13 §10.9).
## Everything is drawn on whole native pixels; the stage scales it by an integer.

const BOX_W := 624
const BOX_H := 64
const BOTTOM := 8
const PORTRAIT := 128
const CARD := PORTRAIT + 4
const CARD_RISE := CARD - BOX_H + 4
const PANEL := Color8(14, 12, 18, 238)
const BORDER := Color8(214, 182, 120, 150)
const BORDER_IN := Color8(10, 9, 13, 255)
const CARD_BG := Color8(78, 70, 86, 255)
const PLATE_BG := Color8(26, 20, 24, 255)
const DIAMOND := Color8(196, 70, 46, 255)
const TEXT := Color8(243, 236, 220, 255)

var box := Rect2()
var card := Rect2()
var plate := Rect2()
var text: RichTextLabel
var name_label: Label
var portrait_tex: Texture2D = null
## Optional overlays of the current expression (only their changed pixels are opaque): "talk1", "talk2" (mouth a
## little / more open), "blink1", "blink2" (eyes half / fully closed). They never touch the same pixels, so a
## blink can happen while she talks. Missing ones are simply not drawn.
var overlays: Dictionary = {}
## Set by StoryUI while the line types; false at a pause (punctuation) and once the line is done.
var talking := false
var speaker := ""
var done := false
var _blink := 0.0
var _kind := "pixel"
const MOUTH_STEP := 0.09                                 # s per mouth frame while talking
const MOUTH_CYCLE := [1, 2, 1, 0, 2, 1, 2, 0]           # 0 = the expression's own mouth
const BLINK_FRAMES := [[1, 0.05], [2, 0.08], [1, 0.05]] # [overlay, seconds]
var _mouth := 0
var _mouth_t := 0.0
var _mouth_i := 0
var _eye := 0
var _eye_t := 3.0
var _eye_i := -1


func _init() -> void:
	name = "DialogueBox"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	text = RichTextLabel.new()
	text.name = "Text"
	text.bbcode_enabled = true
	text.scroll_active = false
	text.fit_content = false
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text.visible_characters_behavior = TextServer.VC_CHARS_AFTER_SHAPING
	text.add_theme_color_override("default_color", TEXT)
	text.add_theme_constant_override("line_separation", 4)
	add_child(text)
	name_label = Label.new()
	name_label.name = "Name"
	name_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	name_label.clip_text = false
	name_label.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	name_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	name_label.add_theme_color_override("font_color", Color8(246, 238, 219))
	add_child(name_label)
	visible = false


func apply_theme(kind: String) -> void:
	_kind = kind
	var f := UiTheme.font(kind)
	text.add_theme_font_override("normal_font", f)
	text.add_theme_font_size_override("normal_font_size", UiTheme.size(kind, "body"))
	# Line pitch UiTheme.LINE (16 px): the separation is measured from the font's real height (Fusion Pixel at
	# 12 px is 18 px high with its descent), not from the font size, or the pitch grows to 22 px.
	var body := UiTheme.size(kind, "body")
	text.add_theme_constant_override("line_separation", int(UiTheme.LINE[kind]) - int(ceilf(f.get_height(body))))
	name_label.add_theme_font_override("font", f)
	name_label.add_theme_font_size_override("font_size", UiTheme.size(kind, "name"))
	relayout()


## who: cast id or "" for narration; portrait: the expression's texture or null; overs: its talk/blink overlays.
func show_line(who_name: String, portrait: Texture2D, bbcode: String, overs: Dictionary = {}) -> void:
	speaker = who_name
	portrait_tex = portrait
	overlays = overs
	_mouth = 0
	_mouth_i = 0
	name_label.text = who_name
	text.text = bbcode
	text.visible_characters = 0
	done = false
	visible = true
	relayout()


func relayout() -> void:
	var view := get_viewport_rect().size
	var bw := minf(BOX_W, view.x - 2.0 * BOTTOM)
	var bx := floorf((view.x - bw) * 0.5)
	var by := view.y - BOTTOM - BOX_H
	box = Rect2(bx, by, bw, BOX_H)
	var has_card := portrait_tex != null
	card = Rect2(bx + 4, by - CARD_RISE, CARD, CARD) if has_card else Rect2()
	var tx := card.end.x + 8 if has_card else bx + 12
	text.position = Vector2(tx, by + 12)
	# two lines at the 16-px pitch need 16 + font height (34 px at 12 px); room for that plus slack, ending
	# above the advance arrow
	text.size = Vector2(bx + bw - 9 - tx, BOX_H - 22)
	var nw := ceilf(name_label.get_minimum_size().x)
	var px := card.end.x + 6 if has_card else bx + 10
	plate = Rect2(px, by - 8, 15 + nw, 15) if speaker != "" else Rect2()
	name_label.visible = speaker != ""
	name_label.position = Vector2(px + 12, by - 9)
	name_label.size = Vector2(nw, 15)
	queue_redraw()


func _process(dt: float) -> void:
	if visible and done:
		_blink += dt
		queue_redraw()
	if not visible or portrait_tex == null:
		return
	var before := Vector2i(_mouth, _eye)
	# mouth: steps through MOUTH_CYCLE while the text types; rests on the expression's own mouth otherwise
	if talking:
		_mouth_t += dt
		if _mouth_t >= MOUTH_STEP:
			_mouth_t -= MOUTH_STEP
			_mouth_i = (_mouth_i + 1) % MOUTH_CYCLE.size()
			_mouth = MOUTH_CYCLE[_mouth_i]
	else:
		_mouth = 0
		_mouth_t = 0.0
	# eyes: a blink every 2.5-6 s (half, closed, half)
	_eye_t -= dt
	if _eye_t <= 0.0:
		_eye_i += 1
		if _eye_i >= BLINK_FRAMES.size():
			_eye_i = -1
			_eye = 0
			_eye_t = randf_range(2.5, 6.0)
		else:
			_eye = BLINK_FRAMES[_eye_i][0]
			_eye_t = BLINK_FRAMES[_eye_i][1]
	if Vector2i(_mouth, _eye) != before:
		queue_redraw()


func _draw() -> void:
	if not visible:
		return
	# the box: dark panel, gold rule, inner dark rule
	draw_rect(box, PANEL)
	draw_rect(box, BORDER, false, 1.0)
	draw_rect(box.grow(-1), BORDER_IN, false, 1.0)
	if portrait_tex != null:
		draw_rect(card, BORDER)
		draw_rect(card.grow(-1), BORDER_IN)
		draw_rect(card.grow(-2), CARD_BG)
		draw_texture(portrait_tex, card.position + Vector2(2, 2))
		if _mouth > 0 and overlays.has("talk%d" % _mouth):
			draw_texture(overlays["talk%d" % _mouth], card.position + Vector2(2, 2))
		if _eye > 0 and overlays.has("blink%d" % _eye):
			draw_texture(overlays["blink%d" % _eye], card.position + Vector2(2, 2))
	if speaker != "":
		draw_rect(plate, PLATE_BG)
		draw_rect(plate, BORDER, false, 1.0)
		var c := plate.position + Vector2(6, 7)
		draw_colored_polygon(PackedVector2Array([c + Vector2(0, -3), c + Vector2(3, 0), c + Vector2(0, 3), c + Vector2(-3, 0)]), DIAMOND)
	if done and fmod(_blink, 1.0) < 0.7:
		var p := box.end - Vector2(11, 9)
		draw_colored_polygon(PackedVector2Array([p, p + Vector2(6, 0), p + Vector2(3, 3)]), BORDER.lightened(0.3))


## The rectangle a tap counts on (for the input router's capture; the whole screen captures anyway).
func hit_rect() -> Rect2:
	return box.merge(card) if portrait_tex != null else box
