class_name StoryUI
extends Control
## The story's words on screen, ported from src/story/ui.js: the dialogue box (DialogueBox) with
## typewriter text and voice blips, caption cards (字幕卡), the title drop, cinematic subtitles and
## barks. Lives on the top canvas layer; the fade and letterbox (Cinema) are on a layer below it
## and below the HUD, so no fade ever covers a word.
## Advance: E / Enter / Space / pad A, or a tap anywhere while a line is up (the input router's
## capture); the first press completes the line, the next one moves on. Hold to fast-forward.
##   await ui.say([{"who": "saji", "text": "……", "face": "smile"}, {"who": "narr", "text": "..."}])
## Timed text waits on the game clock: `wait` is the director's wait.

signal dialogue_closed

const CAST := {
	"tsuzumi": {"name": "百々かさゝぎ", "kana": "もも かささぎ", "voice": "tsuzumi"},
	"saji": {"name": "家守さぢ", "kana": "やもり さじ", "voice": "saji"},
	"shione": {"name": "垣外しをね", "kana": "かいと しおね", "voice": "shione"},
	"narr": {"name": "", "kana": "", "voice": ""},
}
const PAUSE_SHORT := "，、,"
const PAUSE_LONG := "。！？…—!?"
const SILENT := "，。、！？…—「」（）『』 ,.!?"

var cinema: Cinema
var dlg: DialogueBox
var wait: Callable
var kind := "pixel"
var _lines: Array = []
var _i := 0
var _shown := 0
var _total := 0
var _t := 0.0
var _open := false
var _holds := 0
var _labels: Dictionary = {}     # "card", "card_sub", "title", "title_sub", "sub", "bark"
var _alpha: Dictionary = {}      # label -> [current, target, speed]
var _bark_t := 0.0


func _init() -> void:
	name = "StoryUI"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	dlg = DialogueBox.new()
	add_child(dlg)
	for key in ["card", "card_sub", "title", "title_sub", "sub", "bark"]:
		var l := Label.new()
		l.name = key
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.autowrap_mode = TextServer.AUTOWRAP_OFF
		l.modulate.a = 0.0
		l.add_theme_color_override("font_color", Color8(243, 236, 220))
		l.add_theme_color_override("font_outline_color", Color8(8, 7, 10))
		l.add_theme_constant_override("outline_size", 2)
		add_child(l)
		_labels[key] = l
		_alpha[key] = [0.0, 0.0, 1.0]
	_labels["title"].add_theme_color_override("font_color", Color8(42, 34, 48))
	_labels["title"].add_theme_color_override("font_outline_color", Color8(255, 255, 255, 150))
	_labels["title_sub"].add_theme_color_override("font_color", Color8(91, 76, 94))
	_labels["title_sub"].add_theme_constant_override("outline_size", 0)


func apply_theme(k: String) -> void:
	kind = k
	dlg.apply_theme(k)
	var f := UiTheme.font(k)
	for key in _labels:
		var l: Label = _labels[key]
		l.add_theme_font_override("font", f)
		var role := "title" if key == "title" else ("card" if key == "card" else "small")
		l.add_theme_font_size_override("font_size", UiTheme.size(k, role))


var blocking: bool:
	get:
		return _open or _holds > 0


var dialogue_open: bool:
	get:
		return _open


# ------------------------------------------------------------------ dialogue

## lines: [{"who", "text", "face"?, "slow"?}]; resolves when the last line is dismissed.
func say(lines: Array) -> void:
	if lines.is_empty():
		return
	_lines = lines
	_i = 0
	_open = true
	InputRouter.capture_all = true
	Audio.duck(0.35, 0.3)
	_show_line()
	await dialogue_closed


func _show_line() -> void:
	var line: Dictionary = _lines[_i]
	var who := String(line.get("who", "narr"))
	var cast: Dictionary = CAST.get(who, CAST["narr"])
	var tex: Texture2D = null
	if cast["name"] != "":
		tex = portrait(who, String(line.get("face", "neutral")))
	dlg.show_line(String(cast["name"]), tex, _bbcode(String(line.get("text", ""))))
	_total = dlg.text.get_total_character_count()
	_shown = 0
	_t = 0.0


## The pixel portrait of a cast member's expression (art/portraits/<who>/<face>.png), or neutral.
static func portrait(who: String, face: String) -> Texture2D:
	for f in [face, "neutral"]:
		var p := "res://art/portraits/%s/%s.png" % [who, f]
		if ResourceLoader.exists(p):
			return load(p) as Texture2D
	return null


## 「重」 and the other quality names take their quality's colour; nothing else is markup.
static func _bbcode(text: String) -> String:
	var out := text.replace("[", "[lb]")
	for k in Qualities.ALL:
		var kj := Qualities.kanji(k)
		out = out.replace("「%s」" % kj, "[color=%s]「%s」[/color]" % [Qualities.INFO[k]["color"], kj])
	return out


## Complete the line, or move to the next one (E / tap / click).
func advance() -> void:
	if not _open:
		return
	if not dlg.done:
		_shown = _total
		dlg.text.visible_characters = -1
		dlg.done = true
		return
	Audio.sfx("ui")
	_i += 1
	if _i >= _lines.size():
		_open = false
		dlg.visible = false
		InputRouter.capture_all = false
		Audio.duck(0.0, 0.5)
		if wait.is_valid():
			await wait.call(0.12)
		dialogue_closed.emit()
	else:
		_show_line()


func update(dt: float) -> void:
	if _open and not dlg.done:
		var line: Dictionary = _lines[_i]
		var plain := dlg.text.get_parsed_text()
		var who := String(line.get("who", "narr"))
		var voice := String(CAST.get(who, CAST["narr"])["voice"])
		_t += dt * (3.0 if InputRouter.fast_held() else 1.0)
		var cps := 14.0 if line.get("slow", false) else 30.0
		while _t > 1.0 / cps and _shown < _total:
			var c := plain[_shown] if _shown < plain.length() else ""
			_t -= 1.0 / cps
			_shown += 1
			if PAUSE_SHORT.contains(c):
				_t -= 0.09
			elif PAUSE_LONG.contains(c):
				_t -= 0.22
			if voice != "" and c != "" and not SILENT.contains(c) and _shown % 2 == 1:
				Audio.blip(voice, _shown)
		dlg.text.visible_characters = _shown
		if _shown >= _total:
			dlg.done = true
	for key in _alpha:
		var a: Array = _alpha[key]
		a[0] = move_toward(a[0], a[1], dt / maxf(0.05, a[2]))
		(_labels[key] as Label).modulate.a = a[0]
	if _bark_t > 0.0:
		_bark_t -= dt
		if _bark_t <= 0.0:
			_alpha["bark"][1] = 0.0
	_layout_labels()


func _layout_labels() -> void:
	var view := get_viewport_rect().size
	var place := func(key: String, y: float) -> void:
		var l: Label = _labels[key]
		var w := ceilf(l.get_minimum_size().x)
		l.size = Vector2(w, l.get_minimum_size().y)
		l.position = Vector2(floorf((view.x - w) * 0.5), floorf(y))
	place.call("card", view.y * 0.70)
	place.call("card_sub", view.y * 0.70 + 18)
	place.call("title", view.y * 0.42)
	place.call("title_sub", view.y * 0.42 + 34)
	place.call("sub", view.y * 0.80)
	place.call("bark", 8)


# ------------------------------------------------------------------ cinematic text

func _hold(keys: Array, texts: Array, visible_s: float, total_s: float, fade_s: float) -> void:
	_holds += 1
	for i in keys.size():
		(_labels[keys[i]] as Label).text = texts[i]
		_alpha[keys[i]] = [_alpha[keys[i]][0], 1.0, fade_s]
	if wait.is_valid():
		await wait.call(visible_s)
	for k in keys:
		_alpha[k][1] = 0.0
	if wait.is_valid():
		await wait.call(maxf(0.0, total_s - visible_s))
	_holds -= 1


## A caption card (字幕卡): a place or a time, centred low.
func card(head: String, sub_text: String = "", dur: float = 3.6) -> void:
	await _hold(["card", "card_sub"], [head, sub_text], dur, dur + 1.4, 1.2)


## The title drop.
func title(head: String, sub_text: String = "", dur: float = 4.5) -> void:
	await _hold(["title", "title_sub"], [head, sub_text], dur, dur + 1.8, 1.6)


## A spoken line without the box (cinematic subtitle).
func sub(text: String, dur: float = -1.0) -> void:
	var d := dur if dur > 0.0 else maxf(2.4, text.length() * 0.16)
	await _hold(["sub"], [text], d, d + 0.8, 0.7)


## A line said in passing (a bark): small, at the top, never stops play or waits for a key.
func bark(line: Dictionary, dur: float = -1.0) -> void:
	var who := String(line.get("who", "narr"))
	var cast: Dictionary = CAST.get(who, CAST["narr"])
	var text := String(line.get("text", ""))
	(_labels["bark"] as Label).text = ("%s　%s" % [cast["name"], text]) if cast["name"] != "" else text
	_alpha["bark"] = [_alpha["bark"][0], 1.0, 0.2]
	_bark_t = dur if dur > 0.0 else maxf(2.2, text.length() * 0.17)
	if String(cast["voice"]) != "":
		for i in range(0, mini(6, text.length()), 2):
			Audio.blip(String(cast["voice"]), i)


func fade(alpha: float, dur: float = 0.6, color: Color = Color.BLACK) -> void:
	if cinema != null:
		cinema.fade_to(alpha, dur, color)
	if wait.is_valid():
		await wait.call(dur)


func letterbox(on: bool) -> void:
	if cinema != null:
		cinema.letterbox(on)


## For the debug bridge.
func snapshot() -> Dictionary:
	var out := {"open": _open, "blocking": blocking, "fade": cinema.fade_alpha if cinema != null else 0.0,
		"labels": {}}
	for key in _labels:
		var l: Label = _labels[key]
		if l.modulate.a > 0.01:
			out["labels"][key] = {"text": l.text, "alpha": snappedf(l.modulate.a, 0.01),
				"rect": [l.position.x, l.position.y, l.size.x, l.size.y]}
	if _open:
		var line: Dictionary = _lines[_i]
		out.merge({"who": line.get("who", "narr"), "index": _i, "count": _lines.size(), "shown": _shown,
			"total": _total, "done": dlg.done, "text": String(line.get("text", "")),
			"box": [dlg.box.position.x, dlg.box.position.y, dlg.box.size.x, dlg.box.size.y],
			"card": [dlg.card.position.x, dlg.card.position.y, dlg.card.size.x, dlg.card.size.y],
			"text_rect": [dlg.text.position.x, dlg.text.position.y, dlg.text.size.x, dlg.text.size.y]})
	return out
