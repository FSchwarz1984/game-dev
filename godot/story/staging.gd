class_name Staging
extends RefCounted
## The dialogue's staging for static portraits (docs/design/dialogue-staging.md; G5R3-13, approved for now with both
## options in G5R3-19). A portrait never moves inside its card and is never redrawn: the acting is short beats of
## whole native pixels: the card hops, shakes or sinks, the box jolts, the view behind shakes or flashes white, manga
## marks (漫符) pop up on the card, a run of words shakes, waves, is big or faint, and the typing slows, hurries or
## stops. StoryUI owns one; DialogueBox asks it to draw the marks.
##
## Script tags, written in a line's text (parsed before anything is escaped; an unknown [tag] shows as it is):
##   span   [抖]..[/抖] shaky   [波]..[/波] wavy   [大]..[/大] 24 px (twice the pixel font)   [轻]..[/轻] faint (55%)
##          [慢]..[/慢] half speed   [快]..[/快] double speed
##   point  [停0.5] stop typing for 0.5 s here
##   beat   fires when the typing reaches the character it stands before:
##          card  [入场] [弹] [笑] [横抖] [跳] [沉] [颤]     box [框抖]     view [震屏] [闪白]
##          marks [漫符:怒] (怒 汗 惊 问 红晕 阴影 闪光 叹气 音符 点点), another anchor: [漫符:汗@cheek]
##          optional (G5R3-19) [集中线] focus lines on the card, [网点] a dot screen behind the portrait
##   [静]   no default beat for this line
## Default beats (D3): a speaker's first line in a conversation slides the card in ([入场]); a later change of
## speaker plays the new face's default beat (FACE_BEAT), else a hop; a new face of the same speaker plays its
## default beat; tired and mischievous faces bring their mark. A line's own tags come after the defaults, so a card
## beat in the line overrides the default one.
## 减少晃动 (reduce_motion, D6): no offset and no flash at all, the words do not move, marks show their last frame.
## Flash safety (WCAG 2.3.1): at most one flash a line and three in any second.

const PAUSE_SHORT := "，、,"
const PAUSE_LONG := "。！？…—!?"
const CPS := 30.0
const SLOW_CPS := 14.0
const FRAME := 1.0 / 30.0
## the words stop moving this long after the line has typed out
const TEXT_SETTLE := 0.6

## card tracks: [seconds per step, [offsets...], "hold"?]; a held track keeps its last offset until the line ends
const CARD_TRACKS := {
	"入场": [FRAME, [Vector2(-16, 0), Vector2(-9, 0), Vector2(-5, 0), Vector2(-2, 0), Vector2(-1, 0), Vector2.ZERO]],
	"弹": [FRAME, [Vector2(0, -1), Vector2(0, -2), Vector2(0, -2), Vector2(0, -1), Vector2.ZERO]],
	"笑": [FRAME, [Vector2(0, -2), Vector2(0, -2), Vector2(0, -1), Vector2.ZERO, Vector2.ZERO, Vector2(0, -1),
		Vector2(0, -1), Vector2.ZERO, Vector2.ZERO, Vector2(0, -1), Vector2.ZERO]],
	"横抖": [FRAME, [Vector2(2, 0), Vector2(-2, 0), Vector2(2, 0), Vector2(-2, 0), Vector2(1, 0), Vector2(-1, 0), Vector2.ZERO]],
	"跳": [FRAME, [Vector2(0, -1), Vector2(0, -3), Vector2(0, -3), Vector2(0, -2)], "hold"],
	"沉": [0.25, [Vector2.ZERO, Vector2(0, 1), Vector2(0, 2)], "hold"],
}
const BOX_TRACK := [FRAME, [Vector2(3, 0), Vector2(-3, 0), Vector2(2, 0), Vector2(-2, 0), Vector2(1, 0), Vector2(-1, 0), Vector2.ZERO]]
const VIEW_TRACK := [FRAME, [Vector2(4, 2), Vector2(-4, -2), Vector2(3, -1), Vector2(-3, 1), Vector2(2, 1), Vector2(-1, 0), Vector2.ZERO]]
const FLASH_TRACK := [FRAME, [0.85, 0.6, 0.35, 0.15, 0.0]]
## the default beat when a face comes on (the marks drawn into v4 itself stay as they are)
const FACE_BEAT := {
	"neutral": "弹", "smile": "弹", "grin": "弹", "laugh": "笑", "surprise": "跳", "shout": "框抖", "sad": "沉",
	"cry": "沉", "cry_loud": "颤", "pout": "弹", "angry": "横抖", "doubt": "弹", "think": "弹", "embarrassed": "沉",
	"serious": "弹", "determined": "弹", "tired": "沉", "calm": "", "blank": "", "afraid": "颤", "mischievous": "弹",
}
const FACE_MARK := {"mischievous": "闪光", "tired": "叹气"}
const MARKS := {"怒": "anger", "汗": "sweat", "惊": "surprise", "问": "question", "红晕": "blush", "阴影": "gloom",
	"闪光": "sparkle", "叹气": "sigh", "音符": "note", "点点": "dots"}
## drawn for each face (they have to fit its eyes); the rest are generic sprites hung on an anchor
const FACE_PIECES := ["gloom", "blush", "focus"]
const MARK_ANCHOR := {"anger": "side", "sweat": "temple", "surprise": "top", "question": "side", "sparkle": "wink",
	"sigh": "mouth", "note": "side", "dots": "side"}
const ANCHOR_ALIAS := {"头旁": "side", "头顶": "top", "太阳穴": "temple", "嘴边": "mouth", "脸颊": "cheek", "眉": "brow",
	"眼旁": "wink"}
## anchors in the portrait's own pixels (a mark's top-left); v4 keeps the eyes and the head's size fixed across a
## character's expressions, so one set serves all her faces
const ANCHORS := {
	"tsuzumi": {"side": Vector2(100, 40), "top": Vector2(100, 46), "temple": Vector2(33, 45), "mouth": Vector2(66, 72),
		"cheek": Vector2(34, 61), "brow": Vector2(44, 30), "wink": Vector2(98, 40)},
	"saji": {"side": Vector2(108, 16), "top": Vector2(100, 8), "temple": Vector2(38, 44), "mouth": Vector2(70, 74),
		"cheek": Vector2(40, 64), "brow": Vector2(46, 34), "wink": Vector2(30, 40)},
	"shione": {"side": Vector2(112, 8), "top": Vector2(104, 2), "temple": Vector2(50, 49), "mouth": Vector2(83, 71),
		"cheek": Vector2(54, 65), "brow": Vector2(60, 36), "wink": Vector2(46, 44)},
}
const BEATS := ["入场", "弹", "笑", "横抖", "跳", "沉", "颤", "框抖", "震屏", "闪白", "集中线", "网点"]
## marks that are a single moment: a skipped line does not show them
const MOMENTARY := ["surprise", "sigh", "focus"]
const ART := "res://art/portraits/staging"

static var _art := {}

var reduce_motion := false
var who := ""
var face := ""
var has_card := false
var seen := {}              # speakers already on in this conversation (their first line slides in)
var faces := {}             # who -> the face they last showed
var time := 0.0             # seconds since the line began
var clock := 0.0            # seconds since the conversation began (the flash limit counts on it)
var shown := 0
var total := 0
var plain := ""
var beats_log: Array = []   # the beats fired in this line: [seconds, tag, arg] (checks, the debug bridge)
var _acc := 0.0
var _cps := CPS
var _done_at := -1.0
var _speed := PackedFloat32Array()
var _pause := {}
var _events: Array = []     # [[character index, tag, arg]]
var _fired := 0
var _card := {}
var _hold := Vector2.ZERO
var _tremble := false
var _box := {}
var _view := {}
var _flash := {}
var _flashes: Array[float] = []
var _flashed_this_line := false
var _marks: Array = []      # [{name, at, t0, frames?: per-face rects}]
var _tone := {}


# ------------------------------------------------------------------ parsing

## A line's text -> {bb: BBCode for the RichTextLabel (the words escaped), plain: the words, speed: per character,
## pause: {after n characters: seconds}, events: [[n, tag, arg]], quiet: [静] was given}.
static func parse(raw: String) -> Dictionary:
	var acc := {"bb": "", "plain": "", "speed": [], "pause": {}, "events": [], "quiet": false, "rate": 1.0}
	var re := RegEx.create_from_string("\\[(/?)([^\\[\\]]+)\\]")
	var pos := 0
	for m in re.search_all(raw):
		_lit(acc, raw.substr(pos, m.get_start() - pos))
		pos = m.get_end()
		var close := m.get_string(1) == "/"
		var tag := m.get_string(2).strip_edges()
		var n: int = String(acc["plain"]).length()
		match tag:
			"抖":
				acc["bb"] += "[/pshake]" if close else "[pshake]"
			"波":
				acc["bb"] += "[/pwave]" if close else "[pwave]"
			"大":
				acc["bb"] += "[/font_size]" if close else "[font_size=24]"
			"轻":
				acc["bb"] += "[/color]" if close else "[color=#f3ecdc8c]"
			"慢":
				acc["rate"] = 1.0 if close else 0.5
			"快":
				acc["rate"] = 1.0 if close else 2.0
			"静":
				acc["quiet"] = true
			_:
				if close:
					_lit(acc, m.get_string())
				elif tag.begins_with("停") and (tag.length() == 1 or tag.substr(1).is_valid_float()):
					var sec := 0.5 if tag.length() == 1 else tag.substr(1).to_float()
					acc["pause"][n] = float(acc["pause"].get(n, 0.0)) + sec
				elif tag.begins_with("漫符:") or tag.begins_with("漫符："):
					acc["events"].append([n, "漫符", tag.substr(3)])
				elif tag in BEATS:
					acc["events"].append([n, tag, ""])
				else:
					_lit(acc, m.get_string())
	_lit(acc, raw.substr(pos))
	return {"bb": acc["bb"], "plain": acc["plain"], "speed": PackedFloat32Array(acc["speed"]), "pause": acc["pause"],
		"events": acc["events"], "quiet": acc["quiet"]}


static func _lit(acc: Dictionary, s: String) -> void:
	var sp: Array = acc["speed"]
	for i in s.length():
		sp.append(acc["rate"])
	acc["plain"] += s
	acc["bb"] += s.replace("[", "[lb]")


# ------------------------------------------------------------------ a conversation and its lines

## A new conversation: every speaker slides in again on her first line.
func reset() -> void:
	who = ""
	face = ""
	seen = {}
	faces = {}
	clock = 0.0
	_flashes.clear()
	_clear_line()


## The conversation is over: nothing stays up or offset.
func end() -> void:
	_clear_line()
	has_card = false


func _clear_line() -> void:
	time = 0.0
	_acc = 0.0
	shown = 0
	_fired = 0
	_done_at = -1.0
	_card = {}
	_hold = Vector2.ZERO
	_tremble = false
	_box = {}
	_view = {}
	_flash = {}
	_flashed_this_line = false
	_marks = []
	_tone = {}
	beats_log = []


## Start a line. cast_id: who speaks ("narr" for narration: no card); parsed: parse()'s result; card: whether the
## line shows a portrait card; slow: the line's own slow typing (14 characters a second).
func begin(cast_id: String, new_face: String, parsed: Dictionary, card: bool, slow: bool = false) -> void:
	_clear_line()
	var quiet: bool = parsed["quiet"]
	var new_speaker := cast_id != who
	var face_changed := String(faces.get(cast_id, "")) != new_face
	who = cast_id
	face = new_face
	faces[cast_id] = new_face
	has_card = card
	plain = parsed["plain"]
	total = plain.length()
	_speed = parsed["speed"]
	_pause = parsed["pause"]
	_cps = SLOW_CPS if slow else CPS
	var pre: Array = []
	if card:
		if not seen.has(cast_id):
			pre.append([0, "入场", ""])
			seen[cast_id] = true
		elif new_speaker and not quiet:
			var fb := String(FACE_BEAT.get(new_face, ""))
			pre.append([0, fb if fb != "" else "弹", ""])
		elif face_changed and not quiet and String(FACE_BEAT.get(new_face, "")) != "":
			pre.append([0, String(FACE_BEAT[new_face]), ""])
		if face_changed and not quiet and FACE_MARK.has(new_face):
			pre.append([0, "漫符", String(FACE_MARK[new_face])])
	_events = pre + (parsed["events"] as Array)
	_fire_due()


## Typing and beats for one frame. rate: 3 while the advance key is held (fast-forward). Returns the characters that
## came out this frame as [[index, character], ...] (for the voice blips).
func step(dt: float, rate: float = 1.0) -> Array:
	time += dt
	clock += dt
	var out: Array = []
	if shown < total:
		_acc += dt * rate
		while shown < total:
			var need := 1.0 / (_cps * (_speed[shown] if shown < _speed.size() else 1.0))
			if _acc < need:
				break
			_acc -= need
			var c := plain[shown]
			shown += 1
			out.append([shown - 1, c])
			if PAUSE_SHORT.contains(c):
				_acc -= 0.09
			elif PAUSE_LONG.contains(c):
				_acc -= 0.22
			if _pause.has(shown):
				_acc -= float(_pause[shown])
			_fire_due()
		if shown >= total:
			_done_at = time
	_fire_due()
	return out


## The line comes out at once (the player pressed advance while it typed): the beats still to come are applied in
## their settled state (a held hop, a mark already up, the dot screen); the ones that are only a moment are dropped.
func complete() -> void:
	if shown < total:
		shown = total
		_done_at = time
	while _fired < _events.size():
		var e: Array = _events[_fired]
		_fired += 1
		_fire(String(e[1]), String(e[2]), true)


var typed_out: bool:
	get:
		return shown >= total


func _due(n: int) -> bool:
	return n == 0 or shown > n or shown >= total


func _fire_due() -> void:
	while _fired < _events.size() and _due(int(_events[_fired][0])):
		var e: Array = _events[_fired]
		_fired += 1
		_fire(String(e[1]), String(e[2]), false)


func _fire(tag: String, arg: String, skipped: bool) -> void:
	beats_log.append([snappedf(time, 0.001), tag, arg])
	match tag:
		"漫符":
			var parts := arg.split("@")
			var n := String(MARKS.get(parts[0], parts[0]))
			_add_mark(n, parts[1] if parts.size() > 1 else "", skipped)
		"集中线":
			_add_mark("focus", "", skipped)
		"网点":
			_tone = {"t0": time - (10.0 if skipped else 0.0)}
		"框抖":
			if not skipped:
				_box = {"track": BOX_TRACK, "t0": time}
		"震屏":
			if not skipped:
				_view = {"track": VIEW_TRACK, "t0": time}
		"闪白":
			if not skipped and not _flashed_this_line:
				var recent := _flashes.filter(func(t: float) -> bool: return clock - t < 1.0)
				if recent.size() < 3:
					_flash = {"t0": time}
					_flashes.append(clock)
					_flashed_this_line = true
		"颤":
			_tremble = true
		_:
			if CARD_TRACKS.has(tag):
				var tr: Array = CARD_TRACKS[tag]
				if not skipped:
					_card = {"track": tr, "t0": time}
					_hold = Vector2.ZERO                     # the last card beat wins
				elif tr.size() > 2:
					_card = {}
					_hold = (tr[1] as Array)[-1]


func _add_mark(n: String, anchor: String, skipped: bool) -> void:
	if not has_card or (skipped and n in MOMENTARY):
		return
	var t0 := time - (10.0 if skipped else 0.0)
	if n in FACE_PIECES:
		var piece := face_piece(who, face, n)
		if not piece.is_empty():
			_marks.append({"name": n, "frames": piece, "t0": t0})
		return
	if not mark_frames(n).is_empty() and ANCHORS.has(who):
		var a := String(ANCHOR_ALIAS.get(anchor, anchor))
		if not (ANCHORS[who] as Dictionary).has(a):
			a = String(MARK_ANCHOR.get(n, "side"))
		_marks.append({"name": n, "at": ANCHORS[who][a], "t0": t0})


# ------------------------------------------------------------------ what it looks like now

func _track_value(tr: Array, age: float) -> Variant:
	var steps: Array = tr[1]
	var i := int(age / float(tr[0]))
	if i < steps.size():
		return steps[i]
	return steps[-1] if tr.size() > 2 else null


## The card's offset from its place (whole native px).
func card_offset() -> Vector2:
	if reduce_motion:
		return Vector2.ZERO
	var off := _hold
	if not _card.is_empty():
		var v: Variant = _track_value(_card["track"], time - float(_card["t0"]))
		if v == null:
			_card = {}
		else:
			off = v
			if (_card["track"] as Array).size() > 2:
				_hold = v
	if _tremble and (_done_at < 0.0 or time - _done_at < 0.3):
		off.x += float(absi(hash(int(time * 15.0))) % 3 - 1)
	return off


func box_offset() -> Vector2:
	if reduce_motion or _box.is_empty():
		return Vector2.ZERO
	var v: Variant = _track_value(_box["track"], time - float(_box["t0"]))
	if v == null:
		_box = {}
		return Vector2.ZERO
	return v


## How far the view behind (the world) is shaken, whole native px; the box and the words never shake with it (D5).
func view_offset() -> Vector2i:
	if reduce_motion or _view.is_empty():
		return Vector2i.ZERO
	var v: Variant = _track_value(_view["track"], time - float(_view["t0"]))
	if v == null:
		_view = {}
		return Vector2i.ZERO
	return Vector2i(v)


## The white over the view (under the box, the card and the words).
func flash_alpha() -> float:
	if reduce_motion or _flash.is_empty():
		return 0.0
	var v: Variant = _track_value(FLASH_TRACK, time - float(_flash["t0"]))
	if v == null:
		_flash = {}
		return 0.0
	return float(v)


## Whether shaky and wavy words still move (they settle TEXT_SETTLE after the line has typed out).
func text_moving() -> bool:
	return not reduce_motion and (_done_at < 0.0 or time - _done_at <= TEXT_SETTLE)


## The marks up now: [{name, frame, offset}] (for checks).
func marks_now() -> Array:
	var out: Array = []
	for m in _marks:
		var st := _mark_state(String(m["name"]), time - float(m["t0"]))
		if int(st[0]) >= 0:
			out.append({"name": m["name"], "frame": st[0], "offset": st[1]})
	return out


## Frame and offset of a mark at an age; frame -1 when it is not showing.
func _mark_state(n: String, age: float) -> Array:
	if reduce_motion:
		match n:
			"gloom":
				return [3, Vector2.ZERO]
			"blush":
				return [2, Vector2.ZERO]
			"focus":
				return [1 if age < 0.56 else -1, Vector2.ZERO]
			"sparkle":
				return [2, Vector2.ZERO]
			"surprise":
				return [1 if age < 0.44 else -1, Vector2.ZERO]
			"sigh":
				return [3 if age < 0.72 else -1, Vector2.ZERO]
			"sweat":
				return [1, Vector2(0, 3)]
			"anger":
				return [1, Vector2.ZERO]
		return [mark_frames(n).size() - 1, Vector2.ZERO]
	match n:
		"gloom":
			return [mini(3, int(age / 0.1)), Vector2.ZERO]
		"blush":
			return [mini(2, int(age / 0.07)), Vector2.ZERO]
		"focus":
			var acc := 0.0
			for st in [[0, 0.05], [1, 0.15], [2, 0.12], [1, 0.12], [2, 0.12]]:
				acc += float(st[1])
				if age < acc:
					return [int(st[0]), Vector2.ZERO]
			return [-1, Vector2.ZERO]
		"anger":
			if age < 0.06:
				return [0, Vector2(2, 2)]                # the small one, centred on the full mark
			return [2 if fmod(age - 0.06, 0.6) < 0.08 else 1, Vector2.ZERO]
		"sweat":
			if age < 0.06:
				return [0, Vector2(1, 1)]
			return [1, Vector2(0, mini(3, int((age - 0.06) / 0.18)))]
		"surprise":
			return [0 if age < 0.04 else (1 if age < 0.34 else (2 if age < 0.44 else -1)), Vector2.ZERO]
		"question":
			if age < 0.12:
				return [0, Vector2(0, 2 - int(age / 0.04))]
			return [0, Vector2(0, -1 if fmod(age - 0.12, 0.8) < 0.25 else 0)]
		"sparkle":
			var seq := [0, 1, 2, 3, 2, 1, 0]
			var i := int(fmod(age, 1.2) / 0.06)
			return [seq[i] if i < seq.size() else -1, Vector2.ZERO]
		"sigh":
			var j := int(age / 0.12)
			if j > 5:
				return [-1, Vector2.ZERO]
			return [mini(3, j), Vector2(j, -j)]
		"note":
			var k := int(age / 0.25) % 2
			return [k, Vector2(0, -k)]
		"dots":
			return [mini(2, int(age / 0.18)), Vector2.ZERO]
	return [-1, Vector2.ZERO]


# ------------------------------------------------------------------ drawing (DialogueBox calls these)

## Behind the portrait, on the card's colour: the dot screen ([网点]). at: the portrait's top-left.
func draw_under(ci: CanvasItem, at: Vector2) -> void:
	if _tone.is_empty():
		return
	var fr: Array = art_meta().get("tone", [])
	if fr.is_empty():
		return
	var k := fr.size() - 1 if reduce_motion else mini(fr.size() - 1, int((time - float(_tone["t0"])) / 0.12))
	_blit(ci, atlas("marks"), fr[k], at)


## Over the portrait: the marks and the focus lines. at: the portrait's top-left.
func draw_over(ci: CanvasItem, at: Vector2) -> void:
	for m in _marks:
		var st := _mark_state(String(m["name"]), time - float(m["t0"]))
		var f := int(st[0])
		if f < 0:
			continue
		if m.has("frames"):                              # a per-face piece: its rects carry their own position
			var fr: Array = m["frames"]
			var r: Array = fr[mini(f, fr.size() - 1)]
			if int(r[2]) > 0:
				_blit(ci, atlas(who), r, at + Vector2(float(r[4]), float(r[5])))
		else:
			var fr: Array = mark_frames(String(m["name"]))
			_blit(ci, atlas("marks"), fr[mini(f, fr.size() - 1)], at + Vector2(m["at"]) + Vector2(st[1]))


static func _blit(ci: CanvasItem, tex: Texture2D, r: Array, pos: Vector2) -> void:
	if tex == null or int(r[2]) <= 0:
		return
	ci.draw_texture_rect_region(tex, Rect2(pos, Vector2(float(r[2]), float(r[3]))),
		Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])))


# ------------------------------------------------------------------ the pictures (tools/art/portraits4/staging_fx.py)

## Drops the loaded pictures (at exit, so no texture outlives the engine).
static func clear() -> void:
	_art.clear()


static func art_meta() -> Dictionary:
	if not _art.has("meta"):
		var f := FileAccess.open(ART.path_join("staging.json"), FileAccess.READ)
		var data: Variant = JSON.parse_string(f.get_as_text()) if f != null else null
		_art["meta"] = data if data is Dictionary else {}
	return _art["meta"]


static func atlas(name: String) -> Texture2D:
	if not _art.has(name):
		var p := ART.path_join(name + ".png")
		_art[name] = load(p) as Texture2D if ResourceLoader.exists(p) else null
	return _art[name]


static func mark_frames(n: String) -> Array:
	return art_meta().get("marks", {}).get(n, [])


## A per-face piece's frames ([x, y, w, h, ox, oy] each), or [] when that face has none.
static func face_piece(cast_id: String, expr: String, kind: String) -> Array:
	return art_meta().get("faces", {}).get(cast_id, {}).get(expr, {}).get(kind, [])


## For the debug bridge and checks.
func snapshot() -> Dictionary:
	var marks: Array = []
	for m in marks_now():
		marks.append(m["name"])
	return {"who": who, "face": face, "shown": shown, "total": total, "card": [card_offset().x, card_offset().y],
		"box": [box_offset().x, box_offset().y], "view": [view_offset().x, view_offset().y],
		"flash": snappedf(flash_alpha(), 0.01), "marks": marks, "tone": not _tone.is_empty(),
		"text_moving": text_moving(), "reduce_motion": reduce_motion, "log": beats_log.duplicate()}
