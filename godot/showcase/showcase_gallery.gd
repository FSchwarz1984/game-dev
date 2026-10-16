class_name ShowcaseGallery
extends Control
## The portraits (v4, 128 x 128, art/portraits): each character's expressions, the portrait shown at
## twice its size in the dialogue box's card colours.
## Up / down: expression; left / right: character; the mouse picks either.
## Space (Enter, E, pad A): a short dialogue that shows the staging (docs/design/dialogue-staging.md, G5R3-19) in the
## game's own dialogue box (StoryUI), over a still of the home area; Space moves it on as in the game, Esc leaves it.
## Its lines are only lines of the fourth script (docs/design/script-04-draft.md); between the two dialogues every
## beat of the vocabulary and both options appear. しをね has no lines yet, so she has no dialogue (the lead's
## decision, 2026-10-16: her voice is written later, for the user to approve).

const DATA := "res://art/portraits/portraits.json"
const ORDER := ["tsuzumi", "saji", "shione"]
const KANA := {"tsuzumi": "もも かささぎ", "saji": "やもり さぢ", "shione": "かいと しをね"}
const GIVEN := {"tsuzumi": "かさゝぎ", "saji": "さぢ", "shione": "しをね"}
const LABELS := {
	"neutral": "平常", "smile": "微笑", "grin": "开怀", "laugh": "大笑", "surprise": "吃惊", "shout": "喊",
	"sad": "难过", "cry": "哭", "pout": "鼓腮", "angry": "生气", "doubt": "怀疑", "think": "思考",
	"embarrassed": "害羞", "serious": "认真", "determined": "坚定", "tired": "困", "calm": "平静",
	"blank": "茫然", "mischievous": "坏笑", "afraid": "害怕", "cry_loud": "大哭",
}
## Kasasagi's and Saji's dialogues: the words are the fourth script's; the faces and the tags are the staging.
const DEMOS := {
	"tsuzumi": [
		{"who": "tsuzumi", "face": "neutral", "text": "我送完灯，看看天色。"},
		{"who": "tsuzumi", "face": "doubt", "text": "[漫符:惊]那是什么啊……"},
		{"who": "tsuzumi", "face": "surprise", "text": "[闪白]诶？送火怎么飘起来了？"},
		{"who": "tsuzumi", "face": "shout", "text": "[集中线][大]婆婆[/大]——！"},
		{"who": "tsuzumi", "face": "serious", "text": "[静][漫符:阴影]坏了。"},
		{"who": "tsuzumi", "face": "tired", "text": "[慢]……[/慢][停0.6]顺路。"},
		{"who": "tsuzumi", "face": "neutral", "text": "[漫符:怒]没您的份。"},
		{"who": "tsuzumi", "face": "serious", "text": "[静][漫符:汗][轻]您小点声。[/轻]"},
	],
	"saji": [
		{"who": "saji", "face": "surprise", "text": "梁、梁飘起来了……你把它吃了？！"},
		{"who": "tsuzumi", "face": "neutral", "text": "没吃。"},
		{"who": "saji", "face": "laugh", "text": "好，从今天起这儿就是我家了！"},
		{"who": "saji", "face": "angry", "text": "[抖]不下！[/抖]这是我家！"},
		{"who": "saji", "face": "cry_loud", "text": "[震屏]哇啊！"},
		{"who": "saji", "face": "afraid", "text": "[网点]家、家里的事……不好往外说……"},
		{"who": "saji", "face": "smile", "text": "[静][漫符:红晕][波]团子大人……[/波]"},
		{"who": "saji", "face": "mischievous", "text": "鼓槌在你那儿吧？我看见她塞的。"},
		{"who": "saji", "face": "neutral", "text": "[漫符:问]钟？"},
		{"who": "saji", "face": "grin", "text": "[静][漫符:音符][快]最后是从窗户翻出来的。[/快]"},
		{"who": "saji", "face": "neutral", "text": "[漫符:点点][慢]……[/慢][停0.4]第三个坛子里的梅干。"},
	],
}
## A still of the home area (the 3D art sample at 9:30, nobody in it), 6 px larger than the page on every side so
## the view can shake (tools/godot/capture_backdrop.sh makes it).
const BACKDROP := "res://art/showcase/dialogue_backdrop.png"
const BACKDROP_PAD := 6
const BG := Color8(18, 15, 22)
const PANEL := Color8(14, 12, 18, 238)
const BORDER := Color8(214, 182, 120, 150)
const BORDER_IN := Color8(10, 9, 13)
const CARD_BG := Color8(78, 70, 86)
const TEXT := Color8(243, 236, 220)
const DIM := Color8(243, 236, 220, 130)
const MARK := Color8(196, 70, 46)
const LINE := 16

var data := {}
var ci := 0
var ei := 0
var big: TextureRect
var kana_label: Label
var tabs: Array[Label] = []
var rows: Array[Label] = []
var hint: Label
var story: StoryUI
var cinema: Cinema
var backdrop: TextureRect
var _demo := false
var _shake := Vector2i.ZERO
var _origin := Vector2.ZERO
var _stick_t := 0.0


func _init() -> void:
	name = "Gallery"
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS


func _ready() -> void:
	var f := FileAccess.open(DATA, FileAccess.READ)
	if f != null:
		data = JSON.parse_string(f.get_as_text())
	backdrop = _tex()
	backdrop.name = "Backdrop"
	backdrop.texture = load(BACKDROP) as Texture2D if ResourceLoader.exists(BACKDROP) else null
	backdrop.visible = false
	big = _tex()
	kana_label = _label(12, DIM)
	hint = _label(12, DIM)
	for i in ORDER.size():
		var l := _label(12, DIM)
		l.text = String(_char(ORDER[i]).get("name", ORDER[i]))
		l.mouse_filter = Control.MOUSE_FILTER_STOP
		l.gui_input.connect(func(ev: InputEvent) -> void:
			if ev is InputEventMouseButton and ev.pressed and (ev as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
				_set_char(i))
		tabs.append(l)
	# the game's own dialogue layer: the flash under the box (Cinema), the box, the portrait card and the words
	cinema = Cinema.new()
	add_child(cinema)
	story = StoryUI.new()
	story.cinema = cinema
	story.view_shake = func(o: Vector2i) -> void:
		_shake = o
		_layout()
	add_child(story)
	story.apply_theme("pixel")
	resized.connect(_layout)
	Audio.ambience(["wind"])
	_set_char(0)


func _char(id: String) -> Dictionary:
	return data.get("characters", {}).get(id, {})


func _tex() -> TextureRect:
	var t := TextureRect.new()
	t.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	t.stretch_mode = TextureRect.STRETCH_SCALE
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(t)
	return t


func _label(px: int, c: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", UiTheme.font("pixel"))
	l.add_theme_font_size_override("font_size", px)
	l.add_theme_color_override("font_color", c)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l


func _set_char(i: int) -> void:
	ci = wrapi(i, 0, ORDER.size())
	for r in rows:
		r.queue_free()
	rows.clear()
	var exprs: Array = _char(ORDER[ci]).get("expressions", [])
	for k in exprs.size():
		var l := _label(12, DIM)
		l.text = String(LABELS.get(String(exprs[k]), String(exprs[k])))
		l.mouse_filter = Control.MOUSE_FILTER_STOP
		l.mouse_entered.connect(func() -> void: _set_expr(k))
		rows.append(l)
	for t in tabs.size():
		tabs[t].add_theme_color_override("font_color", TEXT if t == ci else DIM)
	kana_label.text = String(KANA.get(ORDER[ci], ""))
	_set_hint()
	_set_expr(clampi(ei, 0, maxi(0, exprs.size() - 1)))


func _set_hint() -> void:
	var calm := "　（减少晃动：开）" if GameState.reduce_motion() else ""
	if _demo:
		hint.text = "Space 下一句　Esc 返回" + calm
	elif DEMOS.has(ORDER[ci]):
		hint.text = "Space 演示对话　↑↓ 表情　←→ 人物　Esc 菜单" + calm
	else:
		hint.text = "%s还没有台词　↑↓ 表情　←→ 人物　Esc 菜单" % String(GIVEN.get(ORDER[ci], ""))


func _set_expr(k: int) -> void:
	var exprs: Array = _char(ORDER[ci]).get("expressions", [])
	if exprs.is_empty():
		return
	ei = wrapi(k, 0, exprs.size())
	var path := "res://art/portraits/%s/%s.png" % [ORDER[ci], String(exprs[ei])]
	var tex := load(path) as Texture2D
	big.texture = tex
	for r in rows.size():
		rows[r].add_theme_color_override("font_color", TEXT if r == ei else DIM)
	_layout()


## A 640 x 360 page centred on the canvas: the portrait x2 on the left in a bordered frame; the
## character tabs, the name and the expressions on the right.
func _layout() -> void:
	_origin = ((size - Vector2(640, 360)) * 0.5).floor()
	var o := _origin
	big.position = o + Vector2(48, 52)
	big.size = Vector2(256, 256)
	for t in tabs.size():
		var x := 0.0
		for j in t:
			x += tabs[j].get_minimum_size().x + 16.0
		tabs[t].position = o + Vector2(336.0 + x, 30)
	if ci < tabs.size():
		kana_label.position = tabs[ci].position + Vector2(0, 20)
	var col := 9
	for r in rows.size():
		rows[r].position = o + Vector2(348 + (r / col) * 72, 86 + (r % col) * LINE)
	hint.size = hint.get_minimum_size()
	hint.position = o + Vector2(640 - 8, 6 if _demo else 360 - 20) - Vector2(hint.get_minimum_size().x, 0)
	backdrop.position = o - Vector2(BACKDROP_PAD, BACKDROP_PAD) + Vector2(_shake)
	backdrop.size = Vector2(640 + 2 * BACKDROP_PAD, 360 + 2 * BACKDROP_PAD)
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG)
	if _demo:
		return
	var o := _origin
	# the portrait's frame: dark inner line, gold border, the card colour behind it
	var fr := Rect2(o + Vector2(44, 48), Vector2(264, 264))
	draw_rect(fr, BORDER)
	draw_rect(fr.grow(-1), BORDER_IN)
	draw_rect(fr.grow(-2), CARD_BG)
	# the selected expression's mark
	if ei < rows.size():
		var p := rows[ei].position + Vector2(-9, 5)
		for r in 5:
			var w := 5 - 2 * absi(r - 2)
			draw_rect(Rect2(p + Vector2((5 - w) / 2, r), Vector2(w, 1)), MARK)
	# the selected character's tab underline
	if ci < tabs.size():
		var t := tabs[ci]
		draw_rect(Rect2(t.position + Vector2(0, 15), Vector2(t.get_minimum_size().x, 1)), MARK)


func _process(dt: float) -> void:
	story.update(dt)
	if _demo:
		return
	var ay := Input.get_joy_axis(0, JOY_AXIS_LEFT_Y)
	var ax := Input.get_joy_axis(0, JOY_AXIS_LEFT_X)
	if absf(ay) > 0.5 or absf(ax) > 0.5:
		_stick_t -= dt
		if _stick_t <= 0.0:
			if absf(ay) >= absf(ax):
				_set_expr(ei + (1 if ay > 0.0 else -1))
			else:
				_set_char(ci + (1 if ax > 0.0 else -1))
			_stick_t = 0.22
	else:
		_stick_t = 0.0


## The dialogue: the page gives way to the still and the game's dialogue box; when the last line is dismissed (or
## Esc), the page comes back.
func _start_demo() -> void:
	var lines: Array = DEMOS.get(ORDER[ci], [])
	if lines.is_empty() or _demo:
		return
	_demo = true
	_show_page(false)
	await story.say(lines)
	_demo = false
	_shake = Vector2i.ZERO
	_show_page(true)


func _show_page(on: bool) -> void:
	big.visible = on
	kana_label.visible = on
	for l in tabs:
		l.visible = on
	for l in rows:
		l.visible = on
	backdrop.visible = not on
	_set_hint()
	_layout()


## Esc while the dialogue is up leaves the dialogue, not the page (the showcase takes Esc to the menu otherwise).
func _input(e: InputEvent) -> void:
	if _demo and e is InputEventKey and e.pressed and not e.echo and (e as InputEventKey).keycode == KEY_ESCAPE:
		get_viewport().set_input_as_handled()
		story.close()


func _unhandled_input(e: InputEvent) -> void:
	if _demo:
		var go := false
		if e is InputEventKey and e.pressed and not e.echo:
			go = (e as InputEventKey).keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER, KEY_E]
		elif e is InputEventJoypadButton and e.pressed:
			go = (e as InputEventJoypadButton).button_index == JOY_BUTTON_A
		elif e is InputEventMouseButton and e.pressed:
			go = (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT
		if go:
			story.advance()
		get_viewport().set_input_as_handled()
		return
	if e is InputEventKey and e.pressed:
		match (e as InputEventKey).keycode:
			KEY_SPACE, KEY_ENTER, KEY_KP_ENTER, KEY_E:
				if not (e as InputEventKey).echo:
					_start_demo()
			KEY_UP, KEY_W:
				_set_expr(ei - 1)
			KEY_DOWN, KEY_S:
				_set_expr(ei + 1)
			KEY_LEFT, KEY_A:
				_set_char(ci - 1)
			KEY_RIGHT, KEY_D:
				_set_char(ci + 1)
			_:
				return
		get_viewport().set_input_as_handled()
	elif e is InputEventJoypadButton and e.pressed:
		match (e as InputEventJoypadButton).button_index:
			JOY_BUTTON_A:
				_start_demo()
			JOY_BUTTON_DPAD_UP:
				_set_expr(ei - 1)
			JOY_BUTTON_DPAD_DOWN:
				_set_expr(ei + 1)
			JOY_BUTTON_DPAD_LEFT:
				_set_char(ci - 1)
			JOY_BUTTON_DPAD_RIGHT:
				_set_char(ci + 1)
			_:
				return
		get_viewport().set_input_as_handled()
