class_name Hud
extends Control
## The play HUD, ported from src/ui (hud.js, prompt.js, actions.js, body.js) and drawn in native
## pixels on its own canvas layer above the world and the fade, below the story text.
##   - The target prompt hangs on the target in the world: its name (遠 tag when far), the qualities
##     it holds as pips, the context key's action, and a refusal line when a verb fails.
##   - The quality keys say what a press will do now (verb, or why it would fail), per the control
##     scheme; on touch they are round keys on an arc around the context key, bottom right, and
##     they preview the gesture being made (swipe up = give, long press = reverse).
##   - Her body is shown on her (Actor.set_body_look); the small gauge top left is only the
##     second reading, with her natural level marked and her returning share filling up.
##   - Tips are anchored on a thing and appear only once she is near it. There is no centre-screen
##     direction or objective marker, ever (F-1): tip() refuses one without a thing.
##   - Touch keys register hit rectangles with the InputRouter, which routes every touch.

const REFUSAL_TEXT := {
	"sacred": "注连绳：动不了",
	"empty": "没有%s了",
	"full": "装不下了",
	"overload": "装不下了，先把多带的放出去",
	"far": "够不着",
	"none": "附近没有可以对它用的东西",
}
const REFUSAL_SHORT := {"sacred": "×", "empty": "无", "full": "满", "overload": "满", "far": "远", "none": "—", "locked": ""}
const VERB := {"take": "取", "give": "予", "release": "放"}
const TIP_NEAR := 7.0
const KEY_DP := 48.0       # touch keys are at least 48 dp across (knowledge/02); the context key 64 dp
const CTX_DP := 64.0
const EDGE := 6.0          # native px kept free at the screen's edge

var field: Field
var stage: PixelStage
var her: Actor
var minimap := Minimap.new()
var shown := true
var kind := "pixel"
var tips: Dictionary = {}
var key_rects: Dictionary = {}     # id -> Rect2, what the input router hits
var plans: Dictionary = {}         # k -> {"verb", "reason", "gesture"} shown on the keys
var prompt_rect := Rect2()
var key_r := 14.0          # native px, from the screen's dpi and the stage scale (touch_sizes())
var ctx_r := 20.0
var _name: Label
var _pips: RichTextLabel
var _ctx: Label
var _say: Label
var _say_t := 0.0
var _say_on_her := false
var _tip: RichTextLabel
var _tip_key := ""
var _key_text: Dictionary = {}     # id -> Label
var _gauge_text: Dictionary = {}   # k -> Label
var _flash: Dictionary = {}        # k -> seconds of highlight after a change
var _last_q: Dictionary = {}


func _init() -> void:
	name = "Hud"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_name = _label("PromptName")
	_ctx = _label("PromptContext")
	_say = _label("PromptSay")
	_say.add_theme_color_override("font_color", Color8(255, 217, 168))
	_pips = RichTextLabel.new()
	_pips.name = "PromptPips"
	_pips.bbcode_enabled = true
	_pips.fit_content = true
	_pips.autowrap_mode = TextServer.AUTOWRAP_OFF
	_pips.scroll_active = false
	_pips.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_pips)
	_tip = RichTextLabel.new()
	_tip.name = "Tip"
	_tip.bbcode_enabled = true
	_tip.fit_content = true
	_tip.autowrap_mode = TextServer.AUTOWRAP_OFF
	_tip.scroll_active = false
	_tip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_tip)
	for k in Qualities.ALL:
		_key_text["q_" + k] = _label("Key_" + k)
		_gauge_text[k] = _label("Gauge_" + k)
		_flash[k] = 0.0
	_key_text["ctx"] = _label("Key_ctx")


func _label(n: String) -> Label:
	var l := Label.new()
	l.name = n
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.autowrap_mode = TextServer.AUTOWRAP_OFF
	l.add_theme_color_override("font_color", Color8(244, 241, 234))
	l.add_theme_color_override("font_outline_color", Color8(10, 9, 13))
	l.add_theme_constant_override("outline_size", 2)
	add_child(l)
	return l


func apply_theme(k: String) -> void:
	kind = k
	var f := UiTheme.font(k)
	for c in get_children():
		if c is Label:
			c.add_theme_font_override("font", f)
			c.add_theme_font_size_override("font_size", UiTheme.size(k, "small"))
		elif c is RichTextLabel:
			c.add_theme_font_override("normal_font", f)
			c.add_theme_font_size_override("normal_font_size", UiTheme.size(k, "small"))


func show_hud(on: bool) -> void:
	shown = on


func learned() -> Array:
	return field.learned() if field != null else []


## A first-time tip anchored on a thing; shown only when she is near it. Never without a thing (F-1).
func tip(key: String, text: String, entity: FieldEntity) -> void:
	if entity == null:
		push_warning("Hud.tip('%s'): a tip must hang on a thing (F-1: no centre-screen directions)" % key)
		return
	tips[key] = {"text": text, "entity": entity}


func untip(key: String) -> void:
	tips.erase(key)


## A refusal or a short line under the prompt (on the target, or on her when there is none).
func say(reason: String, k: String = "") -> void:
	var t: String = REFUSAL_TEXT.get(reason, reason)
	if t.contains("%s"):
		t = t % Qualities.kanji(k)
	_say.text = t
	_say_t = 1.6
	_say_on_her = field.target == null


# ------------------------------------------------------------------ per frame

func update_hud(dt: float) -> void:
	var view := get_viewport_rect().size
	var touch := GameState.touch_ui_on()
	var on := shown and field != null and field.control
	_update_plans()
	_layout_keys(view, touch, on)
	_update_prompt(dt, on)
	_update_tip(on)
	_update_gauge(dt, on)
	queue_redraw()


func _update_plans() -> void:
	var scheme := String(GameState.setting("control_scheme"))
	var shift := Input.is_physical_key_pressed(KEY_SHIFT)
	for k in learned():
		var g := InputRouter.held_gesture("q_" + k)
		if g == "":
			g = "release" if InputRouter.release_armed else ("alt" if shift else "press")
		var p: Dictionary
		if scheme == "obvious" and g != "release":
			p = field.plan(k, g == "alt")
		else:
			p = field.check({"press": "take", "alt": "give", "release": "release"}[g], k)
		p["gesture"] = g
		plans[k] = p


func _key_caption(k: String) -> String:
	var p: Dictionary = plans.get(k, {})
	if p.is_empty():
		return ""
	if String(p["reason"]) != "":
		return String(REFUSAL_SHORT.get(p["reason"], "×"))
	return String(VERB[p["verb"]])


func _layout_keys(view: Vector2, touch: bool, on: bool) -> void:
	key_rects.clear()
	var ks := learned()
	for id in _key_text:
		(_key_text[id] as Label).visible = false
	if not on:
		_register_keys(touch, false)
		return
	if touch:
		touch_sizes()
		# the context key in the corner; the quality keys on an arc around it, from the left (180 deg)
		# to above it, spaced so they never overlap; then the whole cluster is pushed inside the screen
		# five keys within about 110 degrees, 4 px apart at least: the arc's radius follows the key size
		var arc := maxf(ctx_r + key_r + 8.0, (key_r + 2.0) / sin(deg_to_rad(13.75)))
		var step := rad_to_deg(2.0 * asin(minf(1.0, (key_r + 2.0) / arc)))
		var c := Vector2.ZERO
		var centers: Dictionary = {"ctx": c}
		for i in ks.size():
			var a := deg_to_rad(180.0 - i * step)
			centers["q_" + String(ks[i])] = Vector2(cos(a), -sin(a)) * arc
		var lo := Vector2.INF
		var hi := -Vector2.INF
		for id in centers:
			var r := ctx_r if id == "ctx" else key_r
			lo = lo.min(centers[id] - Vector2(r, r))
			hi = hi.max(centers[id] + Vector2(r, r))
		var shift := (view - Vector2(EDGE, EDGE) - hi).round()
		for id in centers:
			var r := ctx_r if id == "ctx" else key_r
			var p: Vector2 = centers[id] + shift
			key_rects[id] = Rect2(p - Vector2(r, r), Vector2(r, r) * 2)
		var ctx_label := field.context_label()
		var lc: Label = _key_text["ctx"]
		lc.text = ctx_label
		lc.visible = ctx_label != ""
		_center_label(lc, key_rects["ctx"].get_center())
		for i in ks.size():
			var id := "q_" + String(ks[i])
			var l: Label = _key_text[id]
			l.text = "%s\n%s" % [Qualities.kanji(ks[i]), _key_caption(ks[i])]
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.add_theme_constant_override("line_spacing", -2)
			l.visible = true
			_center_label(l, key_rects[id].get_center())
	else:
		# keyboard / pad: a row of caps, bottom right: "1重" over the verb a press makes now
		var w := 26.0
		var x0 := view.x - 8 - ks.size() * (w + 2)
		for i in ks.size():
			var id := "q_" + String(ks[i])
			var r := Rect2(x0 + i * (w + 2), view.y - 8 - 30, w, 30)
			key_rects[id] = r
			var l: Label = _key_text[id]
			l.text = "%d%s\n%s" % [Qualities.ALL.find(ks[i]) + 1, Qualities.kanji(ks[i]), _key_caption(ks[i])]
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.add_theme_constant_override("line_spacing", -2)
			l.visible = true
			_center_label(l, r.get_center())
	_register_keys(touch, true)


## Key radii in native px: 48 dp (64 dp for the context key) at this screen's density and the
## stage's integer scale, never smaller than the drawn minimum.
func touch_sizes() -> void:
	var dpi := float(DisplayServer.screen_get_dpi())
	if dpi <= 0.0:
		dpi = 160.0
	var px_per_dp := dpi / 160.0 / float(stage.scale_factor)
	key_r = maxf(14.0, ceilf(KEY_DP * px_per_dp * 0.5))
	ctx_r = maxf(20.0, ceilf(CTX_DP * px_per_dp * 0.5))


func _register_keys(touch: bool, on: bool) -> void:
	for k in Qualities.ALL:
		var id := "q_" + k
		InputRouter.register_key(id, {"rect": key_rects.get(id, Rect2()), "kind": "quality", "k": k,
			"visible": on and touch and key_rects.has(id)})
	InputRouter.register_key("ctx", {"rect": key_rects.get("ctx", Rect2()), "kind": "button", "name": "context",
		"visible": on and touch and key_rects.has("ctx")})


func _center_label(l: Label, c: Vector2) -> void:
	var s := l.get_minimum_size()
	l.size = s
	l.position = (c - s * 0.5).round()


func _anchor_on(e: FieldEntity, extra_m: float) -> Vector2:
	var hgt := float(e.data.get("promptH", 1.6))
	return stage.world_to_screen(Proj.to_px(e.x, e.z, e.h + hgt + extra_m)).round()


## Her sprite's rectangle on screen (logical px), from the frame size around her foot point.
func _her_rect() -> Rect2:
	var p := field.player
	var foot := stage.world_to_screen(Proj.to_px(p.x, p.z, p.h + float(her.look.get("hover_m", 0.0)) if her != null else p.h))
	return Rect2(foot.x - 14.0, foot.y - 42.0, 28.0, 44.0)


func _anchor_on_her(extra_m: float) -> Vector2:
	var p := field.player
	return stage.world_to_screen(Proj.to_px(p.x, p.z, p.h + 2.1 + extra_m)).round()


func _update_prompt(dt: float, on: bool) -> void:
	var view := get_viewport_rect().size
	var t := field.target if on else null
	_say_t = maxf(0.0, _say_t - dt)
	_name.visible = false
	_pips.visible = false
	_ctx.visible = false
	_say.visible = _say_t > 0.0 and on
	prompt_rect = Rect2()
	var anchor := Vector2.ZERO
	if t != null:
		anchor = _anchor_on(t, 0.0)
		_name.text = t.name + ("　远" if t.deep or t.far >= 0.99 else "")
		_name.visible = true
		var show_q: bool = not t.deep and t.data.get("showQualities", true) != false
		var rows: Array = []
		if show_q:
			for k in Qualities.ALL:
				var n: int = t.holder.q[k]
				var b: int = t.holder.base[k]
				if n <= 0 and b <= 0:
					continue
				var cap := maxi(maxi(n, b), 1)
				rows.append("[color=%s]%s[/color]%s%s" % [Qualities.INFO[k]["color"], Qualities.kanji(k), "●".repeat(n), "○".repeat(maxi(0, cap - n))])
			if t.holder.sacred:
				rows.append("[color=#f0b7a8]注连绳[/color]")
		_pips.text = " ".join(rows)
		_pips.visible = not rows.is_empty()
		var cl := field.context_label()
		_ctx.text = ("E " + cl) if cl != "" and not GameState.touch_ui_on() else ""
		_ctx.visible = _ctx.text != ""
		# stack upward from the anchor: [say] above everything, then name, pips, context
		var lines: Array = []
		if _say.visible and not _say_on_her:
			lines.append(_say)
		lines.append(_name)
		if _pips.visible:
			lines.append(_pips)
		if _ctx.visible:
			lines.append(_ctx)
		var y := anchor.y
		for i in range(lines.size() - 1, -1, -1):
			var c: Control = lines[i]
			var s := c.get_minimum_size()
			if c is RichTextLabel:
				s = Vector2((c as RichTextLabel).get_content_width(), (c as RichTextLabel).get_content_height())
			c.size = s
			y -= s.y
			c.position = Vector2(clampf(roundf(anchor.x - s.x * 0.5), 4.0, view.x - s.x - 4.0), clampf(y, 4.0, view.y - s.y - 4.0))
			prompt_rect = c.get_rect() if prompt_rect.size == Vector2.ZERO else prompt_rect.merge(c.get_rect())
		# the prompt never covers her (prototype rule): if it would, it rises above her head
		var me := _her_rect()
		if prompt_rect.grow(1.0).intersects(me):
			var dy := me.position.y - 3.0 - prompt_rect.end.y
			if prompt_rect.position.y + dy < 4.0:
				dy = me.end.y + 3.0 - prompt_rect.position.y  # no room above her head: below her feet
			for c in lines:
				(c as Control).position.y += dy
			prompt_rect.position.y += dy
	if _say.visible and (_say_on_her or t == null):
		var a := _anchor_on_her(0.2)
		var s := _say.get_minimum_size()
		_say.size = s
		_say.position = Vector2(clampf(roundf(a.x - s.x * 0.5), 4.0, view.x - s.x - 4.0), clampf(a.y - s.y, 4.0, view.y - s.y - 4.0))


func _update_tip(on: bool) -> void:
	var view := get_viewport_rect().size
	var show_key := ""
	if on:
		for key in tips:
			var e: FieldEntity = tips[key]["entity"]
			if Vector2(e.x - field.player.x, e.z - field.player.z).length() <= TIP_NEAR:
				show_key = key
	_tip.visible = show_key != ""
	if show_key == "":
		_tip_key = ""
		return
	if show_key != _tip_key:
		_tip_key = show_key
		_tip.text = StoryUI._bbcode(String(tips[show_key]["text"])).replace("[lb]", "[")
	var a := _anchor_on(tips[show_key]["entity"], 0.9)
	var s := Vector2(_tip.get_content_width(), _tip.get_content_height())
	_tip.size = s
	_tip.position = Vector2(clampf(roundf(a.x - s.x * 0.5), 4.0, view.x - s.x - 4.0), clampf(a.y - s.y - 12.0, 4.0, view.y - s.y - 4.0))


func _update_gauge(dt: float, on: bool) -> void:
	var ks := learned()
	var h := field.player.holder
	var row := 0
	for k in Qualities.ALL:
		var l: Label = _gauge_text[k]
		l.visible = on and ks.has(k)
		if _last_q.has(k) and _last_q[k] != h.q[k]:
			_flash[k] = 0.5
		_last_q[k] = h.q[k]
		_flash[k] = maxf(0.0, _flash[k] - dt)
		if l.visible:
			l.text = Qualities.kanji(k)
			l.size = l.get_minimum_size()
			l.position = Vector2(8 + (2 if _flash[k] > 0.0 else 0), 6 + row * 13)
			row += 1


func _draw() -> void:
	if field == null:
		return
	var on := shown and field.control
	var touch := GameState.touch_ui_on()
	# target prompt backing
	if prompt_rect.size != Vector2.ZERO:
		draw_rect(prompt_rect.grow(2), Color(0.06, 0.05, 0.08, 0.62))
	if _say.visible:
		draw_rect(_say.get_rect().grow(2), Color(0.06, 0.05, 0.08, 0.62))
	if _tip.visible:
		var r := _tip.get_rect().grow(3)
		draw_rect(r, Color(0.055, 0.047, 0.07, 0.8))
		draw_rect(r, Color8(214, 178, 106, 140), false, 1.0)
	# keys
	if on:
		for id in key_rects:
			var r: Rect2 = key_rects[id]
			if id == "ctx":
				var lit := field.context_label() != ""
				_disc(r.get_center(), ctx_r, Color(0.06, 0.07, 0.11, 0.62 if lit else 0.35), Color(0.96, 0.95, 0.92, 0.35))
				continue
			var k := String(id).substr(2)
			var p: Dictionary = plans.get(k, {})
			var ok := not p.is_empty() and String(p["reason"]) == ""
			var qc := Qualities.color(k)
			if touch:
				var held := InputRouter.held_gesture(id) != ""
				var lift := Vector2(0, -6 if p.get("gesture", "") == "alt" and held else (6 if p.get("gesture", "") == "release" and held else 0))
				_disc(r.get_center() + lift, key_r + (2.0 if held else 0.0), Color(0.06, 0.07, 0.11, 0.62 if ok else 0.4), qc if ok else qc.darkened(0.5))
			else:
				draw_rect(r, Color(0.06, 0.07, 0.11, 0.6 if ok else 0.35))
				draw_rect(r, qc if ok else qc.darkened(0.5), false, 1.0)
	# the floating stick
	if not InputRouter.stick.is_empty():
		var s: Dictionary = InputRouter.stick
		var o: Vector2 = s["origin"]
		var d: Vector2 = s["pos"] - o
		var rr := float(s["r"])
		if d.length() > rr:
			d = d.normalized() * rr
		_ring(o, rr, Color(0.96, 0.95, 0.92, 0.35))
		_disc(o + d, rr * 0.42, Color(0.96, 0.95, 0.92, 0.3), Color(0.96, 0.95, 0.92, 0.6))
	# the body gauge: second reading only, small, top left
	if on:
		var h := field.player.holder
		var row := 0
		var ks := learned()
		for k in Qualities.ALL:
			if not ks.has(k):
				continue
			var y := 6 + row * 13 + 6
			var x := 22.0
			var top := maxi(maxi(h.q[k], h.base[k]), field.player.cap + h.base[k])
			for i in range(1, top + 1):
				var r := Rect2(x + (i - 1) * 7, y - 2, 5, 5)
				var c := Qualities.color(k)
				if i <= h.q[k]:
					draw_rect(r, c)
				elif i <= h.base[k]:
					# her own share, away: fills up as it returns
					var prog: float = field.player.body.progress.get(k, 0.0)
					draw_rect(r, Color(c, 0.35), false, 1.0)
					draw_rect(Rect2(r.position.x, r.end.y - r.size.y * prog, r.size.x, r.size.y * prog), Color(c, 0.6))
				else:
					draw_rect(r, Color(c, 0.25), false, 1.0)
				if i == h.base[k]:
					draw_rect(r.grow(1), Color(1, 1, 1, 0.55), false, 1.0)
			row += 1


func _disc(c: Vector2, r: float, fill: Color, edge: Color) -> void:
	draw_circle(c, r, fill)
	draw_arc(c, r, 0.0, TAU, 32, edge, 2.0)


func _ring(c: Vector2, r: float, col: Color) -> void:
	draw_arc(c, r, 0.0, TAU, 32, col, 1.5)
