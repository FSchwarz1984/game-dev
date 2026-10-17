class_name ShowcaseSound
extends Node
## The sound of the 3D sample in the showcase (home area, lookout), on Audio: where she hears from, what her
## feet and さぢ's meet, the air of the hour and the weather, the creatures from where they are, the crows on
## the camphor when they caw or fly, the radio on the engawa post at night, and the music by v0.1's rules
## (the field's phrases now and then, the home piece in the yard, the wonder piece when she looks out).
## Reads the sample (world3d/sample.gd) and its terrain; changes nothing in them.

const HOME_R := 13.0              # the home piece within this of the hut (the yard)
const TREES := ["cedar", "broadleaf", "maple", "beech", "pine", "camphor", "persimmon", "konara", "maple_c",
	"maple_a", "sakaki_a", "sarusuberi_a", "furusugi", "shrub", "azalea", "hydrangea"]
const WONDER_COOLDOWN := 240.0    # the wonder piece at most once in four minutes; between, nothing new

var sample: Node = null
var lookout := false
var ground := AudioGround.new()
var ear: AudioListener3D         # where she hears from
var trees: Array = []             # [Vector3 base, height]
var bamboo_pts: Array = []        # Vector3
var stream_line: PackedVector3Array
var hut := Vector3.INF
var shrine := Vector3.INF
var radio_pos := Vector3.INF
var steps_log: Array = []         # [msec, material, gait] (checks)
var rng := RandomNumberGenerator.new()
var _her_phase := -1.0
var _saji_phase := -1.0
var _saji_steps := 0
var _crow_state := {}             # critter -> [pose, state]
var _radio: AudioStreamPlayer3D
var _music := ""
var _wonder_t := -1e9
var _clock := 0.0
var _looking := false


func _ready() -> void:
	rng.seed = Time.get_ticks_usec() ^ 0x1b873593


## Called by the showcase once the sample is in the tree (its _ready has built the world).
func attach(s: Node, is_lookout: bool) -> void:
	sample = s
	lookout = is_lookout
	var t: Terrain3D = s.get("terrain")
	ground.build(t)
	_read_places(t)
	var pv: PixelView3D = s.get("pv")
	ear = AudioListener3D.new()
	ear.name = "Ear"
	pv.world_root.add_child(ear)
	ear.make_current()
	Audio.attach_world(pv.world_root)
	Audio.amb.places = self
	Audio.amb.preset([])
	_music = ""


func _exit_tree() -> void:
	ground.wait()                 # the road raster's worker must not outlive us (quitting from the sample)
	if sample != null and is_instance_valid(sample):
		var pv: PixelView3D = sample.get("pv")
		if pv:
			Audio.detach_world(pv.world_root)
	Audio.attach_world(null)
	Audio.amb.places = null
	Audio.amb.on = false
	Audio.music("none", {"fade": 1.0})


func _read_places(t: Terrain3D) -> void:
	trees.clear()
	bamboo_pts.clear()
	for p in t.info.get("placements", []):
		var kind := String(p.get("kind", ""))
		var pos := Vector3(float(p["x"]), t.height_at(float(p["x"]), float(p["z"])), float(p["z"]))
		if kind == "bamboo":
			bamboo_pts.append(pos)
		elif kind in TREES:
			trees.append([pos, float(p.get("scale", 1.0))])
	var pts: Array = t.info.get("stream", {}).get("points", [])
	stream_line = PackedVector3Array()
	for q in pts:
		stream_line.append(Vector3(float(q[0]), t.height_at(float(q[0]), float(q[1])), float(q[1])))
	var mk: Dictionary = t.info.get("markers", {})
	if mk.has("hut"):
		hut = t.marker("hut")
	if mk.has("shrine"):
		shrine = t.marker("shrine")
	for pr in t.info.get("props", []):
		if String(pr.get("name", "")) == "radio":
			var x := float(pr["x"])
			var z := float(pr["z"])
			radio_pos = Vector3(x, t.height_at(x, z) + float(pr.get("hang", 1.5)) - 0.18, z + 0.15)


# ------------------------------------------------------------------ places (AudioAmbience asks for these)

func listener_pos() -> Vector3:
	var her: W3Walker = sample.get("her") if sample else null
	return her.pos if her else Vector3.ZERO


func listener() -> Vector3:
	return listener_pos()


## A tree between rmin and rmax of her (its crown, the caller lifts it), or INF.
func tree(r: RandomNumberGenerator, rmin: float, rmax: float) -> Vector3:
	var c := listener_pos()
	var cand: Array = []
	for t in trees:
		var d := Vector2((t[0] as Vector3).x - c.x, (t[0] as Vector3).z - c.z).length()
		if d >= rmin and d <= rmax:
			cand.append(t[0])
	if cand.is_empty():
		return Vector3.INF
	return cand[r.randi() % cand.size()]


## A place in the grass between rmin and rmax of her (not on a path, not in water), or INF.
func grass(r: RandomNumberGenerator, rmin: float, rmax: float) -> Vector3:
	var c := listener_pos()
	var t: Terrain3D = sample.get("terrain")
	for i in 12:
		var a := r.randf() * TAU
		var d := r.randf_range(rmin, rmax)
		var x := c.x + cos(a) * d
		var z := c.z + sin(a) * d
		var m := ground.material_at(x, z)
		if m in ["grass", "moss", "leaves"] and t.walkable(x, z):
			return Vector3(x, t.height_at(x, z), z)
	return Vector3.INF


## A place on the brook between rmin and rmax of her, or INF.
func water(r: RandomNumberGenerator, rmin: float, rmax: float) -> Vector3:
	var c := listener_pos()
	var cand: Array = []
	for q in stream_line:
		var d := Vector2(q.x - c.x, q.z - c.z).length()
		if d >= rmin and d <= rmax:
			cand.append(q)
	if cand.is_empty():
		return Vector3.INF
	return cand[r.randi() % cand.size()]


func bamboo(r: RandomNumberGenerator, rmin: float, rmax: float) -> Vector3:
	var c := listener_pos()
	var cand: Array = []
	for q in bamboo_pts:
		var d := Vector2((q as Vector3).x - c.x, (q as Vector3).z - c.z).length()
		if d >= rmin and d <= rmax:
			cand.append(q)
	if cand.is_empty():
		return Vector3.INF
	return (cand[r.randi() % cand.size()] as Vector3) + Vector3(0, 3.0, 0)


## The brook as emitters every `step` metres.
func stream_points(step: float) -> PackedVector3Array:
	var out := PackedVector3Array()
	if stream_line.size() < 2:
		return out
	var acc := 0.0
	out.append(stream_line[0])
	for i in range(1, stream_line.size()):
		acc += stream_line[i].distance_to(stream_line[i - 1])
		if acc >= step:
			out.append(stream_line[i])
			acc = 0.0
	return out


# ------------------------------------------------------------------ every frame

func _process(dt: float) -> void:
	if sample == null or not is_instance_valid(sample):
		return
	_clock += dt
	var her: W3Walker = sample.get("her")
	var env: W3Env = sample.get("env")
	var pv: PixelView3D = sample.get("pv")
	if her == null or env == null or pv == null:
		return
	# where she hears from: at her head, turned like the camera (what is on the left of the picture is on the left)
	ear.global_transform = Transform3D(pv.cam.global_transform.basis, her.pos + Vector3(0, 1.1, 0))
	Audio.amb.set_state(_air(her, env))
	Audio.amb.gust_front = _gust_front(her.pos, env)
	_steps(her, false)
	var saji: W3Walker = sample.get("saji")
	if saji != null:
		_steps(saji, true)
	_crows(her)
	_radio_update(env.hours)
	_music_update(her)


## v0.1's ambience state from the world: the hour, the rain, the wind (v0.1's slow drift around the world's
## strength; rain makes it windier), and the ground's kind round her (forest, bamboo, meadow, shrine, brook).
func _air(her: W3Walker, env: W3Env) -> Dictionary:
	var t := env.clock
	var drift := 0.25 + 0.2 * sin(t * 0.13) + 0.15 * sin(t * 0.41)
	var wind := clampf(drift * env.wind + env.rain * 0.3, 0.0, 1.0)
	var p := her.pos
	var n := 0
	for tr in trees:
		if Vector2((tr[0] as Vector3).x - p.x, (tr[0] as Vector3).z - p.z).length() < 12.0:
			n += 1
	var forest := clampf(0.3 + n / 6.0, 0.3, 1.0)
	var bam := 0
	for q in bamboo_pts:
		if Vector2((q as Vector3).x - p.x, (q as Vector3).z - p.z).length() < 10.0:
			bam += 1
	var wd := 999.0
	for q in stream_line:
		wd = minf(wd, Vector2(q.x - p.x, q.z - p.z).length())
	# v0.1: water = 1 - distance / 130 px (6.5 m at its 20 px a metre)
	var water := clampf(1.0 - wd / 6.5, 0.0, 1.0)
	var shr := 1.0 if shrine != Vector3.INF and Vector2(shrine.x - p.x, shrine.z - p.z).length() < 7.0 else 0.0
	return {"tod": env.hours, "rain": env.rain, "wind": wind, "near": 1.0, "forest": forest,
		"bamboo": clampf(bam / 4.0, 0.0, 1.0), "meadow": clampf(1.0 - n / 3.0, 0.0, 1.0) * 0.6,
		"shrine": shr, "stream": water, "indoor": false, "cinematic": false, "paused": false}


## The grass field's gust front at a place (world3d/grass_field.gdshader, ported): 0 calm .. 1 a front passing.
func _gust_front(p: Vector3, env: W3Env) -> float:
	var wd := Vector2(1.0, 0.25).normalized()
	var xz := Vector2(p.x, p.z)
	var along := xz.dot(wd)
	var across := xz.dot(Vector2(-wd.y, wd.x))
	var ph := (along - env.clock * 3.4) / 11.0 + _vnoise(Vector2(across / 9.0, along / 23.0)) * 0.9
	var front := pow(0.5 + 0.5 * sin(ph * TAU), 5.0)
	var g := front * AudioAmbience.sstep(0.3, 0.62, _vnoise(Vector2(across / 13.0 + env.clock * 0.03, along / 19.0 + 3.1)))
	return g * clampf(env.wind * 0.55 + 0.35 * 0.6, 0.0, 1.0)


static func _hash(p: Vector2) -> float:
	var p3 := Vector3(p.x, p.y, p.x) * 0.1031
	p3 = Vector3(p3.x - floorf(p3.x), p3.y - floorf(p3.y), p3.z - floorf(p3.z))
	var d := p3.dot(Vector3(p3.y, p3.z, p3.x) + Vector3(33.33, 33.33, 33.33))
	p3 += Vector3(d, d, d)
	var v := (p3.x + p3.y) * p3.z
	return v - floorf(v)


static func _vnoise(p: Vector2) -> float:
	var i := Vector2(floorf(p.x), floorf(p.y))
	var f := p - i
	var u := f * f * (Vector2(3, 3) - 2.0 * f)
	return lerpf(lerpf(_hash(i), _hash(i + Vector2(1, 0)), u.x), lerpf(_hash(i + Vector2(0, 1)), _hash(i + Vector2(1, 1)), u.x), u.y)


## A step at each footfall of the walk / run cycle (the sheet's 8 frames: feet down at 1/16 and 9/16 of it).
func _steps(w: W3Walker, is_saji: bool) -> void:
	if w.anim != "walk" and w.anim != "run":
		if is_saji:
			_saji_phase = -1.0
		else:
			_her_phase = -1.0
		return
	var ph := fposmod(w.anim_t, 8.0) / 8.0
	var last := _saji_phase if is_saji else _her_phase
	if is_saji:
		_saji_phase = ph
	else:
		_her_phase = ph
	if last < 0.0:
		return
	for i in footfalls(last, ph):
		_footfall(w, is_saji)


## How many feet came down between two phases of the walk cycle (0..1, forward, wrapping): feet at 1/16, 9/16.
static func footfalls(last: float, ph: float) -> int:
	var n := 0
	for f in [1.0 / 16.0, 9.0 / 16.0]:
		if ph >= last:
			if f > last and f <= ph:
				n += 1
		elif f > last or f <= ph:
			n += 1
	return n


func _footfall(w: W3Walker, is_saji: bool) -> void:
	var m := ground.material_at(w.pos.x, w.pos.z)
	var run := w.anim == "run"
	if is_saji:
		# barefoot, a child: soil, grass, wood or stone, lighter; her bell on every other step (8.1)
		var sm := "wood" if m == "wood" else ("stone" if m == "stone" else ("grass" if m in ["grass", "moss", "leaves"] else "soil"))
		Audio.play_at("saji_step_" + sm, w.pos, {"db": -5.0, "unit": 3.0, "max": 22.0})
		_saji_steps += 1
		if _saji_steps % 2 == 0 and rng.randf() < 0.8:
			Audio.play_at("bell_saji", w.pos + Vector3(0, 0.7, 0), {"unit": 3.0, "max": 18.0})
	else:
		Audio.footstep_at(m, w.pos, run)
	steps_log.append([Time.get_ticks_msec(), m, "run" if run else "walk", is_saji])
	if steps_log.size() > 400:
		steps_log.pop_front()


## The camphor's crows: a caw when one opens its beak (W3Life's "caw" pose), wings when one takes off.
func _crows(her: W3Walker) -> void:
	var d: Variant = sample.get("dressing")
	if d == null:
		return
	var life: Variant = (d as Object).get("life")
	if life == null:
		return
	for c in (life as Object).get("critters"):
		if String(c.kind) != "crow":
			continue
		var prev: Array = _crow_state.get(c, ["", ""])
		var pose := String(c.pose)
		var st := String(c.state)
		if pose == "caw" and prev[0] != "caw":
			Audio.play_at("caw", c.pos + Vector3(0, 0.3, 0), {"unit": 10.0, "max": 70.0, "bus": "Ambience"})
		if st == "fly" and prev[1] != "fly" and prev[1] != "":
			Audio.play_at("wings", c.pos, {"unit": 6.0, "max": 35.0, "bus": "Ambience"})
		_crow_state[c] = [pose, st]


## The radio on the engawa post sounds at night: the 遠囃子 through its little speaker, static, the dial
## (v0.1: it came alive on the night of the prologue; script 05 scene 3).
func _radio_update(h: float) -> void:
	if radio_pos == Vector3.INF or not Audio.has("radio_fest"):
		return
	var night := h >= 19.5 or h < 4.5
	if _radio == null:
		_radio = AudioStreamPlayer3D.new()
		_radio.bus = "Ambience"
		var st := Audio.stream_of(String(Audio.sounds["radio_fest"]["files"][0]))
		if st is AudioStreamOggVorbis:
			(st as AudioStreamOggVorbis).loop = true
		_radio.stream = st
		_radio.unit_size = 2.0
		_radio.max_distance = 16.0
		_radio.max_db = 0.0
		_radio.volume_db = -80.0
		Audio.world.add_child(_radio)
		_radio.global_position = radio_pos
	var target := -6.0 if night else -80.0
	if night and not _radio.playing:
		_radio.play(rng.randf() * 60.0)
	_radio.volume_db = move_toward(_radio.volume_db, target, get_process_delta_time() * 20.0)
	if not night and _radio.playing and _radio.volume_db <= -79.0:
		_radio.stop()


## v0.1's music, placed: the home piece in the yard round the hut; elsewhere the field's phrases with their long
## silences; on the lookout, when she looks out, the wonder piece (once in a while), then the field again.
func _music_update(her: W3Walker) -> void:
	var want := "explore"
	if hut != Vector3.INF and Vector2(hut.x - her.pos.x, hut.z - her.pos.z).length() < HOME_R:
		want = "home"
	var v: Variant = sample.get("vista")
	var looking: bool = v is Object and is_instance_valid(v) and (v as Object).get("active") == true
	if looking and not _looking and _clock - _wonder_t > WONDER_COOLDOWN:
		_wonder_t = _clock
		Audio.music("wonder", {"fade": 2.0})
		_music = "wonder"
	_looking = looking
	if _music == "wonder" and Audio.mus.current == "wonder":
		return
	if want != _music:
		_music = want
		Audio.music(want, {"fade": 4.0 if want == "explore" else 3.0})
