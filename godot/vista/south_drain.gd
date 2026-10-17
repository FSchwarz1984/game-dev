class_name VistaSouthDrain
extends RefCounted
## The bridge between the gathered lights and the burst at the town (G5R3-61; a proposal, not yet
## approved: Vista.bridge picks it, "none" is the prologue as it was). The lights of the plain have all
## gone into the gate on the sky shore's point; the far bursts from the town, down on the plain and to
## the right of it. Two ways to join them, both driven from Vista.state:
##   "drain" (state.drain = seconds since the drain began): back on the plain the gate draws in its
##     breath (a faint ring closes in on its mouth, its light tightens and brightens), and the town's
##     own colours are drawn up out of the ground, the last breath of the lights' rising and in their
##     language: grains of light, each the colour of what its pixel of the town is made of (thatch,
##     tile, white wall, grove, paddy: the material's own, unlit), float straight up off the whole town,
##     then each bends toward the gate on its own curve, the swarm loose and wide in the middle of the
##     way and gathering only at the gate's mouth, faster and faster, turning the sky shore's pale jade
##     past half its way; where they leave, the ground goes its silver-grey ghost, from the middle of
##     the town out. Then the town bursts white (the far's front starts there) while the last grains go
##     up; the gate takes them in, flashing, and breathes out.
##   "flash" (no drain): a beat after the cut back to the plain the gate flares and in the same frame
##     the town bursts white.
## state.flare = seconds since the burst (both). Everything is a function of those two numbers (the
## arrivals at the gate are planned, not counted), so a frame can be shown at any moment of it.
## The grains move on the GPU (shaders/drain.gdshader); pos_at() here is the same path, for checks.

const DRAIN_PRE := 3.4        # the cut back to the plain .. the burst (s): what "drain" adds
const FLASH_PRE := 0.8        # "flash": the beat before the gate flares and the town bursts (s)
const INHALE := Vector2(0.3, 0.9)     # the gate draws its breath (s after the cut)
const DEP := Vector2(0.45, 3.55)      # the first and the last grain leave the town (s)
const DUR := Vector2(2.3, 1.75)       # time to the gate of the first and of the last grains (s, +-15%)
const B_MAX := 36                     # the drained radius at the burst, in arrival buckets (~ 230 m)

var s: VistaSouth
var points: VistaPoints
var n_grains := 0
var town := Vector2.ZERO               # canvas px of the far group: the middle of the town
var arrivals := PackedFloat32Array()   # when each grain reaches the gate (s after the drain began), sorted
var t_last := 0.0                      # the last of them
var grains: Array = []                 # [p0, o, dur, f, b, lift, seed, colour] (checks, tests)


func setup(p_s: VistaSouth, quality: String) -> void:
	s = p_s
	var m := s.m
	if s.lights.dep.is_empty():
		# (the plain's depression knots, as update_river loads them on its first frame)
		s.lights.dep = m.get("dep", [])
		s.lights.eye_rel = float(m.get("eyeRel", 380.0))
		s.lights.plain_u = float(m.get("plainU", 182.0))
	var f := float(m["f"])
	var zc := float(m["Zc"])
	town = Vector2(float(m["Cx"]) + f * float(m["Xc"]) / zc, float(m["YL"]) + f * s.lights.floor_dep(zc))
	n_grains = 150 if quality == "high" else 90
	var rng := RandomNumberGenerator.new()
	rng.seed = 6113
	# the town's pixels the grains leave from: the ground the far reaches first, by its arrival
	# bucket (the ground image's B), the middle first, each with its own colour (its material's, unlit:
	# the bake's groundAlbedo; without it, as the evening sun showed it)
	var gi: Image = s.data.images["ground"]
	var lut: Image = s.data.images["lutGround"]
	var albedo: Array = s.data.lists.get("groundAlbedo", [])
	var gd := gi.get_data()
	var gw := gi.get_width()
	var gh := gi.get_height()
	var src: Array = []
	for y in range(maxi(0, int(town.y) - 30), mini(gh, int(town.y) + 30)):
		for x in range(maxi(0, int(town.x) - 140), mini(gw, int(town.x) + 140)):
			var o := (y * gw + x) * 4
			if gd[o + 3] < 128:
				continue
			var b := int(gd[o + 2])
			if b > B_MAX:
				continue
			var id := int(gd[o]) + int(gd[o + 1]) * 256
			var own := lut.get_pixel(id, 0)
			if id < albedo.size():
				own = Color(float(albedo[id][0]) / 255.0, float(albedo[id][1]) / 255.0, float(albedo[id][2]) / 255.0)
			src.append([b + rng.randf() * 10.0, Vector2(x, y), _glow_colour(own)])
	src.sort_custom(func(a: Array, b: Array) -> bool: return float(a[0]) < float(b[0]))
	# departures thicken toward the burst (the drain gathers pace), in a few soft gusts: the k-th
	# leaves at DEP.x + span w(k / n)^(1 / 1.6), w(x) = x + 0.012 sin(10 pi x); the first leave from
	# the middle of the town, the last from its edge. Each its own speed (+-15%), height off the ground
	# before it bends (12-30 px), and bend: its second control point somewhere between a quarter and
	# a half of the way down from the gate, and 30 px to the right .. 66 px to the left of that way (the
	# swarm's belly, mostly away from the sky shore's pagoda, which stands right of the way)
	var inst: Array = []
	arrivals.clear()
	grains.clear()
	for k in n_grains:
		var x := float(k) / float(n_grains - 1)
		var o := DEP.x + (DEP.y - DEP.x) * pow(clampf(x + 0.012 * sin(TAU * 5.0 * x), 0.0, 1.0), 1.0 / 1.6)
		var dur := lerpf(DUR.x, DUR.y, x) * rng.randf_range(0.85, 1.15)
		var pick: Array = src[mini(src.size() - 1, int(round(x * (src.size() - 1) * 0.92 + rng.randf() * src.size() * 0.08)))]
		var p0: Vector2 = pick[1]
		var col: Color = pick[2]
		var fw := rng.randf_range(0.25, 0.5)
		var bw := lerpf(-30.0, 66.0, (rng.randf() + rng.randf()) * 0.5)
		var lift := rng.randf_range(12.0, 30.0)
		var seed := float(k) + (0.25 if k % 3 == 0 else 0.0)   # (+ 0.25: a faint halo, one grain in three)
		for q in 3:
			inst.append([[p0.x, p0.y, o, dur, fw, bw], Color(col.r, col.g, col.b, lift), Color(q, 2, 0, seed)])
		arrivals.append(o + dur)
		grains.append([p0, o, dur, fw, bw, lift, k, col])
	# the burst at the town; the gate's flare in the same frame (variant "flash": gate_k); the gate's
	# breath (a ring closing in on its mouth)
	inst.append([[town.x, town.y, 0, 1, 0, 0], Color(1, 1, 1, 0), Color(0, 0, 2, 0)])
	inst.append([[town.x, town.y, 0, 1, 0, 0], Color(1, 1, 1, 0), Color(0, 0, 3, 0)])
	inst.append([[town.x, town.y, 0, 1, 0, 0], Color(1, 1, 1, 0), Color(0, 0, 4, 0)])
	arrivals.sort()
	t_last = arrivals[arrivals.size() - 1]
	points = VistaPoints.new(inst.size(), preload("res://vista/shaders/drain.gdshader"))
	points.name = "Drain"
	for i in inst.size():
		points.put(i, inst[i][0], inst[i][1], inst[i][2])
	points.commit()
	points.set_param("inhale_t", INHALE)
	points.visible = false


## A material's colour made a small light: its own hue and saturation (no dyeing), brought up to a
## lamp's level.
static func _glow_colour(c: Color) -> Color:
	var mx := maxf(c.r, maxf(c.g, c.b))
	if mx <= 0.001:
		return Color(0.85, 0.85, 0.85)
	var v := 0.92 / mx
	return Color(c.r * v, c.g * v, c.b * v)


## This frame: el = seconds since the drain began (< 0: none), fl = seconds since the burst (< 0:
## none), gate = the gate's mouth (canvas px); gate_flare: the gate flares with the burst ("flash").
func update(el: float, fl: float, gate: Vector2, gate_flare: bool = false) -> void:
	points.visible = (el >= INHALE.x - 0.02 and el < t_last + 0.1) or (fl >= 0.0 and fl < 3.0)
	if not points.visible:
		return
	points.set_param("el", el)
	points.set_param("fl", fl)
	points.set_param("town", town)
	points.set_param("gate", gate)
	points.set_param("gate_k", 1.0 if gate_flare else 0.0)


## How far the gate has drawn its breath (0..1): in before the grains leave, held while they come,
## out again after the last.
func inhale(el: float) -> float:
	if el < 0.0:
		return 0.0
	return VistaEnv.smoothj(INHALE.x, INHALE.y, el) * (1.0 - VistaEnv.smoothj(t_last + 0.2, t_last + 1.1, el))


## The gate's flashes as the grains come in (added to the rising lights' ones): a small one for each,
## a larger one for the last.
func flash(el: float) -> float:
	if el < 0.0:
		return 0.0
	var f := 0.0
	var i := arrivals.bsearch(el, false) - 1
	while i >= 0 and el - arrivals[i] < 1.5:
		f += exp(-(el - arrivals[i]) / 0.28) * 0.2
		i -= 1
	if el >= t_last:
		f += exp(-(el - t_last) / 0.35) * 1.1
	return f


## How many came in over the last 1.5 s, as the gate's inflow (0..1, added to the rising lights').
func inflow(el: float) -> float:
	if el < 0.0:
		return 0.0
	var hi := arrivals.bsearch(el, false)
	var lo := arrivals.bsearch(el - 1.5, false)
	return clampf(float(hi - lo) / 45.0, 0.0, 1.0)


## The drained radius of the town's ground (arrival buckets; < -5: none): from the middle out, as
## the grains leave.
func ground_b(el: float) -> float:
	if el < 0.0:
		return -10.0
	return -8.0 + float(B_MAX + 8) * VistaEnv.smoothj(DEP.x + 0.15, DRAIN_PRE, el)


## The grain's place (canvas px) at s along its way: the path of shaders/drain.gdshader.
func pos_at(g: Array, s_: float, gate: Vector2) -> Vector2:
	var p0: Vector2 = g[0]
	var fw := float(g[3])
	var bw := float(g[4])
	var lift := float(g[5])
	var k := int(g[6])
	var way := town - gate
	var across := Vector2(-way.y, way.x).normalized()
	var p1 := p0 + Vector2((_hash2(k, 1, 71) - 0.5) * 6.0, -lift)
	var p2 := gate + way * fw + across * bw
	var p3 := gate + Vector2((_hash2(k, 2, 71) - 0.5) * 3.0, 1.0 + (_hash2(k, 3, 71) - 0.5) * 2.0)
	var u := 1.0 - s_
	return u * u * u * p0 + 3.0 * u * u * s_ * p1 + 3.0 * u * s_ * s_ * p2 + s_ * s_ * s_ * p3


## vista.gdshaderinc's hash2 (uint arithmetic), for pos_at.
static func _hash2(x: int, y: int, sd: int) -> float:
	var h := (x * 374761393 + y * 668265263 + sd * 1442695041) & 0xFFFFFFFF
	h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
	h ^= h >> 16
	return float(h >> 8) / 16777216.0
