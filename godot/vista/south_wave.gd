class_name VistaSouthWave
extends RefCounted
## The wave of distance's moving parts (src/vista/wave.js drawFront and the end of south.js draw(),
## HEAD): the curtain at the front (a shader over the ground, curtain.gdshader), the motes the front
## sheds (spawned here from the baked pixels of each arrival bucket, moved by motes.gdshader) and, at
## the end, the white rising over the crown (display.gdshader, in sRGB) and the motes rushing past the
## camera (endmotes.gdshader).
## The JS let up to 1600 motes live; "low" quality (phones) keeps 700.
## Over the land gone far (G5R3-22) small silver motes rise slowly from the ground and drift off,
## thickest over the town (ground zero), behind the tide and in the hold after it (ghost_motes, the
## mote shader's ghost mode): the 3D lookout's motes (vista3d.gd _motes), the same numbers.

var s: VistaSouth
var curtain: VistaQuad
var motes: VistaPoints
var end_k := 0.0              # the white rising over the crown (drawn by the display shader)
var end_motes: VistaPoints
var rng := RandomNumberGenerator.new()
var rng_end := RandomNumberGenerator.new()
var start := PackedInt32Array()      # first index of each arrival bucket in xy
var count := PackedInt32Array()
var xy := PackedByteArray()          # u16 pairs (x, y), 1 in 3 ground pixels, sorted by bucket
var next := 0
var next_end := 0
var n_motes := 1600
var n_end := 900
var ghost_motes: VistaPoints
var rng_ghost := RandomNumberGenerator.new()
var n_ghost := 220
var next_ghost := 0
var ghost_acc := 0.0
var ghost_warm := false
var aimg: PackedByteArray           # the ground's ids (B: the bucket the tide reaches each pixel in)
var zimg: PackedByteArray
var zw := 0
var zh := 0
var cx := 0.0
var yl := 0.0
var f := 360.0


func setup(p_s: VistaSouth, quality: String) -> void:
	s = p_s
	rng.seed = 977
	rng_end.seed = 4111
	n_motes = 1600 if quality == "high" else 700
	n_end = 900 if quality == "high" else 400
	var b: Array = s.data.lists.get("moteBuckets", [])
	start.resize(256)
	count.resize(256)
	var acc := 0
	for k in 256:
		start[k] = acc
		count[k] = int(b[k]) if k < b.size() else 0
		acc += count[k]
	xy = s.data.raw("moteXY")
	var zi: Image = s.data.images["groundZ"]
	zimg = zi.get_data()
	zw = zi.get_width()
	zh = zi.get_height()
	cx = float(s.m["Cx"])
	yl = float(s.m["YL"])
	f = float(s.m["f"])

	curtain = VistaQuad.new(Vector2(float(s.m["Wc"]), float(s.m["GH"])), preload("res://vista/shaders/curtain.gdshader"))
	curtain.name = "Curtain"
	curtain.set_param("ids", s.data.tex("ground"))
	curtain.set_param("zmap", s.data.tex("groundZ"))
	curtain.set_param("f", f)
	motes = VistaPoints.new(n_motes, preload("res://vista/shaders/motes.gdshader"))
	motes.name = "Motes"
	motes.set_param("zmap", s.data.tex("groundZ"))
	motes.set_param("cx", cx)
	motes.set_param("yl", yl)
	motes.set_param("f", f)
	end_motes = VistaPoints.new(n_end, preload("res://vista/shaders/endmotes.gdshader"))
	end_motes.name = "EndMotes"
	_clear_end()
	rng_ghost.seed = 6151
	n_ghost = 220 if quality == "high" else 110
	ghost_motes = VistaPoints.new(n_ghost, preload("res://vista/shaders/motes.gdshader"))
	ghost_motes.name = "GhostMotes"
	ghost_motes.set_param("zmap", s.data.tex("groundZ"))
	ghost_motes.set_param("cx", cx)
	ghost_motes.set_param("yl", yl)
	ghost_motes.set_param("f", f)
	ghost_motes.set_param("ghost", true)
	ghost_motes.set_param("u", float(s.m.get("plainU", 182.0)))
	# (at night, as the lookout's: 0.7, each its own 0.8-1.15 of it)
	ghost_motes.set_param("alpha", 0.7)
	for i in n_ghost:
		ghost_motes.put(i, [0, 1, 0, 0, 0, 0], Color(0, 0, -1.0e9, 0))
	ghost_motes.commit()
	aimg = (s.data.images["ground"] as Image).get_data()


func _clear_end() -> void:
	for i in n_end:
		end_motes.put(i, [0, 0, 0, 0, 0, -1.0e9])
	end_motes.commit()
	next_end = 0


func _z_at(x: int, y: int) -> float:
	if x < 0 or y < 0 or x >= zw or y >= zh:
		return 0.0
	var o := (y * zw + x) * 2
	return (zimg[o] + zimg[o + 1] * 256) * 1024.0 / 65535.0


func update(wave: float, t: float, dt: float, view: Vector2i, settled: bool = false) -> void:
	var on := wave >= 0.0
	curtain.visible = on
	motes.visible = on
	ghost_motes.visible = on or settled
	if on or settled:
		ghost_motes.set_param("t", t)
		_spawn_ghost(wave, t, dt, settled)
	if on:
		curtain.set_param("wave", wave)
		curtain.set_param("t", t)
		motes.set_param("t", t)
		_spawn(wave, t, dt)
	# the end: the pale front comes up the trunk and over the crown, its motes rush past us
	var k := VistaEnv.smoothj(0.82, 1.0, wave) if wave > 0.82 else 0.0
	end_k = k
	end_motes.set_param("t", t)
	end_motes.set_param("view", Vector2(view))
	end_motes.visible = wave >= 0.8
	if k > 0.0:
		var n := roundi((3.0 + 30.0 * k) * minf(2.0, dt * 60.0 + 0.01))
		for q in n:
			end_motes.put(next_end, [(rng_end.randf() - 0.5) * 7.0, -2.2 + rng_end.randf() * 3.4,
				1.6 + rng_end.randf() * 7.0, 0.25 + rng_end.randf() * 0.7, -(1.1 + rng_end.randf() * 2.0), t])
			next_end = (next_end + 1) % n_end
		end_motes.commit()
	elif wave < 0.8 and next_end != 0:
		_clear_end()


## New motes along the front: many, the curtain is thick at its foot (wave.js: about a tenth of the
## front's strips a frame, at most 80).
func _spawn(wave: float, t: float, dt: float) -> void:
	var b := int(clampf(floor(wave * 250.0), -1.0, 254.0))
	if b < 0:
		return
	var lo := maxi(0, b - 1)
	var band := 0
	for k in range(lo, b + 1):
		band += count[k]
	if band == 0:
		return
	var ns := band * 3.0 * 0.5
	var want := mini(80, roundi(ns * 0.1 * minf(2.0, dt * 60.0)) + 1)
	for q in want:
		var j := rng.randi_range(0, band - 1)
		var k := lo
		while j >= count[k]:
			j -= count[k]
			k += 1
		var o := (start[k] + j) * 4
		var x := xy[o] + xy[o + 1] * 256
		var y := xy[o + 2] + xy[o + 3] * 256
		var z := _z_at(x, y)
		if z <= 0.0:
			continue
		var X := (x + 0.5 - cx) * z / f
		var hg := 1.0 - (y - yl) * z / f
		var life := 0.45 + rng.randf() * rng.randf() * 1.6
		motes.put(next, [X + (rng.randf() - 0.5) * z * 0.004, z * (1.0 - rng.randf() * 0.01), rng.randf() * 0.004 * z, hg,
			(rng.randf() - 0.5) * 0.03 * z, -(0.08 + rng.randf() * 0.12) * z],
			Color((5.0 + rng.randf() * 11.0) * z / f, life, t, 0.0))
		next = (next + 1) % n_motes
	motes.commit()


## Silver motes off the land gone far, as the lookout's (vista3d.gd _spawn_mote, _step_motes): about
## n/9 a second, each from a point within the last ring taken by the cube of how much a ghost it is
## (most of them over the town), where that ground is in sight and the tide has passed it; 1-24 m off
## the ground, rising 4.5-10 m a second (a pixel or two a second there) and slowing, drifting a metre
## a second aside, living 6-12 s, faded in and out (motes.gdshader, ghost mode); one pixel, one in ten
## two. On the first frame of a hold not reached through the tide the lights are already there, at
## all ages (the view opens on lights risen, not on all of them starting together).
func _spawn_ghost(wave: float, t: float, dt: float, settled: bool) -> void:
	if aimg.is_empty():
		return
	var b := 254 if settled else int(clampf(floor(wave * 250.0), -1.0, 254.0)) - 2
	if b < 0:
		return
	var warm := settled and not ghost_warm
	ghost_warm = true
	ghost_acc = minf(ghost_acc + minf(dt, 0.1) * float(n_ghost) / 9.0, 3.0)
	if warm:
		ghost_acc = float(n_ghost)
	var u := float(s.m.get("plainU", 182.0))
	var g: Dictionary = s.m.get("ghost", {})
	var zero: Array = g.get("zero", [-260.0, 2160.0])
	var R: Array = g.get("r", [400.0, 1100.0, 2600.0, 5500.0])
	var put := false
	while ghost_acc >= 1.0:
		ghost_acc -= 1.0
		for _try in 8:
			var r := sqrt(rng_ghost.randf()) * float(R[3])
			var a := rng_ghost.randf() * TAU
			var xm := float(zero[0]) + cos(a) * r
			var zm := float(zero[1]) + sin(a) * r
			var k := ghost_k(xm, zm)
			if rng_ghost.randf() >= k * k * k:
				continue
			var X := -xm / u
			var Z := zm / u
			if Z < 2.0:
				continue
			var x := int(floor(cx + f * X / Z + 0.5))
			var y := int(floor(yl + f * s.lights.floor_dep(Z) + 0.5))
			if x < 0 or y < 0 or x >= zw or y >= zh:
				continue
			var z := _z_at(x, y)
			if z <= 0.0 or absf(z - Z) > Z * 0.12:
				continue                              # that ground is not in sight there
			if aimg[(y * zw + x) * 4 + 2] > b:
				continue                              # the tide has not passed it yet
			var hg := 1.0 - (y - yl) * z / f
			var life := rng_ghost.randf_range(6.0, 12.0)
			var age0 := rng_ghost.randf() * life if warm else 0.0
			var size := 2.0 if rng_ghost.randf() < 0.1 else 1.0
			var br := lerpf(0.8, 1.15, rng_ghost.randf())
			# instance: X0 Z0 | H0 hg | vX seed ; colour: vH life t0 (brightness + 10 per extra pixel)
			ghost_motes.put(next_ghost, [X, z, rng_ghost.randf_range(1.0, 24.0) / u, hg,
				rng_ghost.randf_range(-1.2, 1.2) / u, rng_ghost.randf()],
				Color(rng_ghost.randf_range(4.5, 10.0) / u, life, t - age0, br + (size - 1.0) * 10.0))
			next_ghost = (next_ghost + 1) % n_ghost
			put = true
			break
	if put:
		ghost_motes.commit()


## How much a ghost a point of the land is (x, z in m, the 3D frame): 1 at the town .. 0 past the last
## ring and in the region's ring round home (meta.ghost; plain.js ghostK, vista3d.gd ghost_k).
func ghost_k(x: float, z: float) -> float:
	var g: Dictionary = s.m.get("ghost", {})
	var zero: Array = g.get("zero", [-260.0, 2160.0])
	var R: Array = g.get("r", [400.0, 1100.0, 2600.0, 5500.0])
	var dx := x - float(zero[0])
	var dz := z - float(zero[1])
	var a := atan2(dx, -dz)
	var w := 0.9 + 0.2 * (_vnoise(a * 2.6 + 4.0, 1.7) * 0.7 + _vnoise(a * 7.3 + 1.0, 5.1) * 0.3)
	var r := sqrt(dx * dx + dz * dz) / w
	var k := 0.0
	if r < float(R[0]):
		k = 1.0
	elif r < float(R[1]):
		k = lerpf(1.0, 0.75, smoothstep(float(R[0]), float(R[1]), r))
	elif r < float(R[2]):
		k = lerpf(0.75, 0.4, smoothstep(float(R[1]), float(R[2]), r))
	else:
		k = lerpf(0.4, 0.0, smoothstep(float(R[2]), float(R[3]), r))
	var h: Dictionary = g.get("home", {})
	if not h.is_empty():
		var e := Vector2((x - float(h["cx"])) / float(h["rx"]), (z - float(h["cz"])) / float(h["rz"])).length()
		k *= smoothstep(1.15, 1.8, e)
	return k


# (pixel_toon's w3_hash, vista3d.gd _hash2 / _vnoise)
static func _hash2(x: float, y: float) -> float:
	var p3 := Vector3(fposmod(x * 0.1031, 1.0), fposmod(y * 0.1031, 1.0), fposmod(x * 0.1031, 1.0))
	var d := p3.dot(Vector3(p3.y + 33.33, p3.z + 33.33, p3.x + 33.33))
	p3 += Vector3(d, d, d)
	return fposmod((p3.x + p3.y) * p3.z, 1.0)


static func _vnoise(x: float, y: float) -> float:
	var ix := floorf(x)
	var iy := floorf(y)
	var fx := x - ix
	var fy := y - iy
	var ux := fx * fx * (3.0 - 2.0 * fx)
	var uy := fy * fy * (3.0 - 2.0 * fy)
	return lerpf(lerpf(_hash2(ix, iy), _hash2(ix + 1.0, iy), ux), lerpf(_hash2(ix, iy + 1.0), _hash2(ix + 1.0, iy + 1.0), ux), uy)
