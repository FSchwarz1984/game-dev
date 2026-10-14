class_name Actor
extends Node2D
## A character on stage: an AnimatedSprite2D driven by an explicit animation state machine.
##
## States (each decides the animation):
##   LOCOMOTION  the default: walk while moving, else heavyIdle while heavy, else idle. Evaluated
##               every frame, so it always matches what she is doing now.
##   SCRIPTED    a scene walks her (Director.move): the walk loop until idle().
##   ONE_SHOT    a scripted animation (take, give, bow...): plays once, holds its last frame a beat,
##               then returns to LOCOMOTION by itself.
##   HOLD        a looping animation held for a while (Director.play with loop and hold), then
##               LOCOMOTION by itself.
##   POSE        a held pose (asleep, sit...) until release(), or until the scene ends.
## Every scripted state has an exit (time, idle()/release(), and end_scene() which the director
## calls when its last scene ends), so nothing a scene leaves behind outlives the scene. This is
## the fix for R-4: sprites that did not switch back after scripted actions.
##
## Positions: x, z metres (node position = ground point, which y-sorts); the sprite is lifted by
## 20 * (h + lift + hover) px. For her, x/z read and write the field's PlayerBody.

signal step(foot: int)

enum State { LOCOMOTION, SCRIPTED, ONE_SHOT, HOLD, POSE }

const STATE_NAMES := ["locomotion", "scripted", "one_shot", "hold", "pose"]
const ALIAS := {
	"tsuzumi": {"heavy": "heavyIdle", "sleep": "asleep", "unshoulder": "shoulder", "sit": "sitBranch", "stand": "idle"},
	"saji": {"bell": "bellStand", "talk": "sitTalk", "point": "pointStand"},
}
const PLAIN_ONLY := ["strain", "asleep", "sitUp", "sit"]
const VIEW := {"front": "front", "back": "back", "left": "side", "right": "side"}
const HOLD_LAST := 0.25   # seconds a one-shot holds its last frame

var id := ""
var state: State = State.LOCOMOTION
var face := "front"
var variant := ""
var moving := false
var heavy := false
var h := 0.0
var lift := 0.0
var body = null                 # Field.PlayerBody when this actor is her
var anim_name := ""             # the SpriteFrames animation playing now
var look: Dictionary = {}

var _x := 0.0
var _z := 0.0
var _one := ""                  # the scripted animation (ONE_SHOT, HOLD, POSE)
var _t := 0.0
var _dur := 0.0
var _last := Vector2.INF
var _last_frame := -1
var _ring_t := 0.0
var _sound_rings: Array = []    # [{"t": age, "r": max radius m}]
var _sprite_holder: Node2D
var sprite: AnimatedSprite2D
var light: PointLight2D
var _mat: ShaderMaterial

var x: float:
	get:
		return body.x if body != null else _x
	set(v):
		if body != null:
			body.x = v
		else:
			_x = v
var z: float:
	get:
		return body.z if body != null else _z
	set(v):
		if body != null:
			body.z = v
		else:
			_z = v


func _init(p_id: String = "", p_body = null) -> void:
	id = p_id
	name = p_id.capitalize()
	body = p_body
	var sheets := CharacterLibrary.sheets(id)
	variant = "load" if sheets.has("load") else (sheets[0] if not sheets.is_empty() else "")
	_sprite_holder = Node2D.new()
	add_child(_sprite_holder)
	sprite = AnimatedSprite2D.new()
	sprite.centered = true
	var fs := CharacterLibrary.frame_size(id)
	var pv := CharacterLibrary.pivot(id)
	sprite.offset = Vector2(fs.x * 0.5 - pv.x, fs.y * 0.5 - pv.y)
	_mat = ShaderMaterial.new()
	_mat.shader = load("res://actors/actor_sprite.gdshader")
	sprite.material = _mat
	_sprite_holder.add_child(sprite)
	light = PointLight2D.new()
	light.enabled = false
	light.texture = _light_texture()
	light.position = Vector2(0, -18)
	_sprite_holder.add_child(light)
	set_body_look({})


static func _light_texture() -> Texture2D:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.35), Color(1, 1, 1, 0)])
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = 128
	t.height = 128
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t


func state_name() -> String:
	return STATE_NAMES[state]


func _resolve(anim: String) -> String:
	return ALIAS.get(id, {}).get(anim, anim)


func _sheet_for(anim: String) -> String:
	if id != "tsuzumi":
		return variant
	if PLAIN_ONLY.has(anim):
		return "plain"
	var s := "plain" if variant == "none" else variant
	if not CharacterLibrary.has_anim(id, s, anim):
		for alt in ["plain", "load", "frame"]:
			if CharacterLibrary.has_anim(id, alt, anim):
				return alt
	return s


# ------------------------------------------------------------------ scripted control

## Start a scripted animation; returns its length in seconds (0 for loops and unknown names).
## opts: {"loop": bool, "hold": seconds}. A looping "walk" is a scripted walk (until idle()); another
## loop is HOLD for `hold` seconds, or POSE without a hold.
func play(anim: String, opts: Dictionary = {}) -> float:
	var a := _resolve(anim)
	var loop := bool(opts.get("loop", false))
	var hold := float(opts.get("hold", 0.0))
	if a == "walk" and loop:
		state = State.SCRIPTED
		_one = ""
		return 0.0
	if not CharacterLibrary.has_anim(id, _sheet_for(a), a):
		push_warning("Actor %s: no animation '%s'" % [id, a])
		return 0.0
	_one = a
	_t = 0.0
	if loop:
		state = State.HOLD if hold > 0.0 else State.POSE
		_dur = hold
		return 0.0
	state = State.ONE_SHOT
	_dur = CharacterLibrary.duration(id, _sheet_for(a), a, VIEW[face])
	_apply(true)
	return _dur


## A held pose (asleep, pinned...) until release().
func pose(anim: String) -> void:
	play(anim, {"loop": true})


## Back to LOCOMOTION from a scripted walk (the director calls it on arrival).
func idle() -> void:
	if state == State.SCRIPTED:
		state = State.LOCOMOTION


func release() -> void:
	state = State.LOCOMOTION
	_one = ""


## The director's safety net when its last scene ends: whatever a scene left, back to locomotion.
func end_scene() -> void:
	state = State.LOCOMOTION
	_one = ""
	lift = 0.0


func set_face(f: String) -> void:
	face = f


# ------------------------------------------------------------------ per frame

func tick(dt: float) -> void:
	var p := Vector2(x, z)
	var delta := p - _last if _last != Vector2.INF else Vector2.ZERO
	_last = p
	var self_moved := delta.length() > 1e-4
	if body != null:
		moving = body.moving and self_moved or state == State.SCRIPTED and self_moved
		if body.moving and state == State.LOCOMOTION:
			face = Proj.face_of(body.fx, body.fz, face)
	else:
		moving = self_moved
	if self_moved and (state == State.SCRIPTED or (state == State.LOCOMOTION and body == null)):
		face = Proj.face_of(delta.x, delta.y, face)
	match state:
		State.ONE_SHOT:
			_t += dt
			# her verb gestures yield to walking at once; a scene's one-shots run while she stands
			if _t >= _dur + HOLD_LAST or (body != null and body.moving and self_moved):
				release()
		State.HOLD:
			_t += dt
			if _t >= _dur:
				release()
	_apply(false)
	position = Proj.sort_px(x, z)
	var hover := float(look.get("hover_m", 0.0))
	var bobbing := float(look.get("hover_bob", 0.0)) * sin(Time.get_ticks_msec() / 1000.0 * 3.1)
	_sprite_holder.position = Vector2(0, -Proj.PPM * (h + lift + hover + bobbing))
	_tick_rings(dt)
	queue_redraw()


## Chooses the SpriteFrames animation for the state and facing; restarts it when it changes.
func _apply(restart: bool) -> void:
	var anim := ""
	match state:
		State.LOCOMOTION:
			anim = "walk" if moving else ("heavyIdle" if heavy else "idle")
		State.SCRIPTED:
			anim = "walk"
		_:
			anim = _one
	var sheet := _sheet_for(anim)
	var v := CharacterLibrary.view_for(id, sheet, anim, VIEW[face])
	if v == "":
		anim = "idle"
		sheet = _sheet_for(anim)
		v = CharacterLibrary.view_for(id, sheet, anim, VIEW[face])
	var frames := CharacterLibrary.frames(id, sheet)
	if sprite.sprite_frames != frames:
		sprite.sprite_frames = frames
	var n := "%s_%s" % [anim, v]
	if n != anim_name or restart:
		anim_name = n
		if frames.has_animation(n):
			sprite.play(n)
			_last_frame = -1
	var meta := CharacterLibrary.anim_meta(id, anim)
	sprite.flip_h = face == "left" and v == "side" and bool(meta.get("mirrorLeft", true))
	# footfalls on the walk's contact frames
	if anim == "walk" and moving:
		var f := sprite.frame
		var count := frames.get_frame_count(n) if frames.has_animation(n) else 0
		if f != _last_frame and count > 0 and (f == 0 or f == count / 2):
			step.emit(0 if f == 0 else 1)
			var ring := float(look.get("sound_ring", 0.0))
			if ring > 0.0:
				_sound_rings.append({"t": 0.0, "r": ring})
		_last_frame = f


# ------------------------------------------------------------------ her body, shown on her

## The interface for body-state sprite effects (BodyState.look()).
func set_body_look(l: Dictionary) -> void:
	look = l
	var outline := String(l.get("outline", ""))
	_mat.set_shader_parameter("outline_color", Color.html(outline) if outline != "" else Color(0, 0, 0, 0))
	_mat.set_shader_parameter("pulse_speed", 6.0 if float(l.get("ember", 0.0)) > 0.0 else 0.0)
	var tint := String(l.get("tint", ""))
	_mat.set_shader_parameter("tint", Color.html(tint) if tint != "" else Color.WHITE)
	_mat.set_shader_parameter("darken", float(l.get("darken", 0.0)))
	_mat.set_shader_parameter("frost", float(l.get("frost", 0.0)))
	_mat.set_shader_parameter("ember", float(l.get("ember", 0.0)) + (1.0 if l.get("burning", false) else 0.0))
	var squash := float(l.get("squash", 0.0))
	sprite.scale = Vector2(1.0 + squash * 0.5, 1.0 - squash)
	var radius := float(l.get("glow_radius", 0.0))
	light.enabled = radius > 0.0
	if radius > 0.0:
		var c := String(l.get("glow_color", "#ffe08a"))
		light.color = Color.html(c if c != "" else "#ffe08a")
		light.texture_scale = radius * Proj.PPM * 2.0 / 128.0
		light.energy = 1.1


func _tick_rings(dt: float) -> void:
	_ring_t += dt
	for r in _sound_rings:
		r["t"] += dt
	_sound_rings = _sound_rings.filter(func(r): return r["t"] < 0.6)


func _draw() -> void:
	var ground := Vector2(0, -Proj.PPM * (h + lift))
	# the shadow stays on the ground while she hovers: the gap shows she is light
	var hover := float(look.get("hover_m", 0.0))
	var sw := 7.0 * (1.0 - clampf(hover, 0.0, 0.6))
	_ellipse(ground, Vector2(sw, 2.0), Color(0, 0, 0, 0.32))
	# one ring per quality she carries extra, pulsing every 0.7 s
	var rings: Array = look.get("rings", [])
	for i in rings.size():
		var k := fmod(_ring_t + i * 0.23, 0.7) / 0.7
		var c := Color.html(rings[i])
		c.a = (1.0 - k) * 0.85
		_ellipse_line(ground, Vector2(5.0 + 9.0 * k, 1.8 + 3.0 * k), c)
	for r in _sound_rings:
		var k: float = r["t"] / 0.6
		var rad: float = float(r["r"]) * Proj.PPM * k
		_ellipse_line(ground, Vector2(rad, rad * 0.4), Color(0.62, 0.82, 1.0, 1.0 - k))


func _ellipse(c: Vector2, r: Vector2, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 16:
		var a := TAU * i / 16.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y))
	draw_colored_polygon(pts, col)


func _ellipse_line(c: Vector2, r: Vector2, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 21:
		var a := TAU * i / 20.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y).round())
	draw_polyline(pts, col, 1.0)
