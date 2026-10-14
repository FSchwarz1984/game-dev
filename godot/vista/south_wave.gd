class_name VistaSouthWave
extends RefCounted
## The wave of distance's moving parts (src/vista/wave.js drawFront and the end of south.js draw(),
## HEAD): the curtain at the front (a shader over the ground, curtain.gdshader), the motes the front
## sheds (spawned here from the baked pixels of each arrival bucket, moved by motes.gdshader) and, at
## the end, the white rising over the crown (display.gdshader, in sRGB) and the motes rushing past the
## camera (endmotes.gdshader).
## The JS let up to 1600 motes live; "low" quality (phones) keeps 700.

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


func update(wave: float, t: float, dt: float, view: Vector2i) -> void:
	var on := wave >= 0.0
	curtain.visible = on
	motes.visible = on
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
