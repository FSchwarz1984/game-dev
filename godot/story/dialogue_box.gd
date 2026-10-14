class_name DialogueBox
extends Control
## The dialogue box at native pixel resolution, laid out per docs/knowledge/13-pixel-portraits.md §5:
## the 80x80 pixel portrait stands in its own 84x84 card at the left end of the box (rising 24 px
## above it), and the text column starts 8 px right of the card, so the portrait can never cover a
## word (F-3). The name plate sits on the box's top border above the text column, always one line,
## as wide as the name. Narration (no speaker) has no card and uses the full width.
## Everything is drawn on whole native pixels; the stage scales it by an integer.

const BOX_W := 468
const BOX_H := 64
const BOTTOM := 6
const CARD := 84
const CARD_RISE := 24
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
var speaker := ""
var done := false
var _blink := 0.0
var _kind := "pixel"


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
	text.add_theme_constant_override("line_separation", UiTheme.LINE[kind] - UiTheme.size(kind, "body"))
	name_label.add_theme_font_override("font", f)
	name_label.add_theme_font_size_override("font_size", UiTheme.size(kind, "name"))
	relayout()


## who: cast id or "" for narration; portrait: the expression's texture or null.
func show_line(who_name: String, portrait: Texture2D, bbcode: String) -> void:
	speaker = who_name
	portrait_tex = portrait
	name_label.text = who_name
	text.text = bbcode
	text.visible_characters = 0
	done = false
	visible = true
	relayout()


func relayout() -> void:
	var view := get_viewport_rect().size
	var bw := minf(BOX_W, view.x - 12.0)
	var bx := floorf((view.x - bw) * 0.5)
	var by := view.y - BOTTOM - BOX_H
	box = Rect2(bx, by, bw, BOX_H)
	var has_card := portrait_tex != null
	card = Rect2(bx + 4, by - CARD_RISE, CARD, CARD) if has_card else Rect2()
	var tx := card.end.x + 8 if has_card else bx + 12
	var line := int(UiTheme.LINE[_kind])
	text.position = Vector2(tx, by + 12)
	text.size = Vector2(bx + bw - 9 - tx, line * 2 + 2)
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
