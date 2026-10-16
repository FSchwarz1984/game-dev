class_name VistaSouthLights
extends RefCounted
## The lights of the south shot: the lamps on the plain, their rising (8196ebf), the stars, the sky
## shore's lights and the floating lanterns on the river. The GPU moves every light (shaders
## lamps / rise / stars / shorelights); this keeps only what needs a memory:
##  - departures: a lamp leaves when `rise` first passes its turn r (JS: as if rise had run at 1/30
##    per second when it jumps), its departure time goes into a 1-row float texture the shaders read;
##  - arrivals at the gate: how many came in the last 1.5 s (inflow, 8196ebf) and a flash for each one
##    (new: the gate brightens light by light), how many are in the air (the deck's warm glow).
## Quality "high" adds companion sparks: each fire and many lamps leave as a small cluster (a spark
## or a few, a moment after the lamp, each on its own jittered curve), "low" (phones) is the JS set.

const KIND_STAR := 2
const KIND_FIRE := 3
const KIND_BONFIRE := 4
const RIVER_SEGS := 15
const NEVER := -1.0e9         # departure time of a lamp that has not left (times can be negative)

var s: VistaSouth
var L: Array = []             # the baked rows
var n := 0
var order: PackedInt32Array   # lamp indices by departure turn r
var r_of: PackedFloat32Array
var tdep: PackedFloat32Array
var arrived: PackedByteArray
var n_dep := 0
var tdep_img: Image
var tdep_tex: ImageTexture
var dirty := true
var arrivals: Array[float] = []
var inflow := 0.0
var flash := 0.0
var in_flight := 0
var companions := 0
var lamps: VistaPoints
var rise: VistaPoints
var stars: VistaPoints
var shore: VistaPoints
var river: VistaPoints
var river_l: Array = []
var _built_class := -1
var quality := "high"


func setup(p_s: VistaSouth, far: Node2D, quality_: String) -> void:
	s = p_s
	quality = quality_
	L = s.data.lists["lights"]
	n = L.size()
	var idx := range(n)
	idx.sort_custom(func(a: int, b: int) -> bool: return float(L[a][6]) < float(L[b][6]) or (float(L[a][6]) == float(L[b][6]) and a < b))
	order = PackedInt32Array(idx)
	r_of = PackedFloat32Array()
	for i in order:
		r_of.append(float(L[i][6]))
	tdep = PackedFloat32Array()
	tdep.resize(n)
	tdep.fill(NEVER)
	arrived = PackedByteArray()
	arrived.resize(n)
	tdep_img = Image.create(maxi(1, n), 1, false, Image.FORMAT_RF)
	tdep_img.fill(Color(NEVER, 0, 0, 0))
	tdep_tex = ImageTexture.create_from_image(tdep_img)
	river_l = s.m["riverLanterns"]

	stars = VistaPoints.new(0, preload("res://vista/shaders/stars.gdshader"))
	stars.name = "Stars"
	_build_stars()
	shore = VistaPoints.new(0, preload("res://vista/shaders/shorelights.gdshader"))
	shore.name = "ShoreLights"
	lamps = VistaPoints.new(0, preload("res://vista/shaders/lamps.gdshader"))
	lamps.name = "Lamps"
	_build_lamps()
	river = VistaPoints.new(river_l.size(), preload("res://vista/shaders/lamps.gdshader"))
	river.name = "RiverLanterns"
	rise = VistaPoints.new(0, preload("res://vista/shaders/rise.gdshader"))
	rise.name = "Rise"
	for p in [lamps, river, rise]:
		p.set_param("tdep", tdep_tex)
	# river lanterns use the lamp shader as lanterns that never leave (their tdep reads NEVER)
	river.set_param("tdep", _never_tex())


## Attach the layers at their place in the far group (called by VistaSouth in draw order).
func layer(name: String) -> Node2D:
	return {"stars": stars, "shore": shore, "lamps": lamps, "river": river, "rise": rise}[name]


func _never_tex() -> ImageTexture:
	var img := Image.create(1, 1, false, Image.FORMAT_RF)
	img.fill(Color(NEVER, 0, 0, 0))
	return ImageTexture.create_from_image(img)


func _build_stars() -> void:
	var list: Array = s.data.lists["stars"]
	stars.resize(list.size())
	for i in list.size():
		var st: Array = list[i]
		# x y mag r g b ph sp tw
		stars.put(i, [st[0], st[1], st[6], st[7], st[2], st[8]], Color(st[3] / 255.0, st[4] / 255.0, st[5] / 255.0, 1.0))
	stars.commit()


func _build_lamps() -> void:
	lamps.resize(n)
	for i in n:
		var l: Array = L[i]
		var grp := int(floor(float(l[5]) * 7.0)) % 3 if int(l[2]) == KIND_STAR else 0
		# x y | on ph | arr kind ; colour: flags, lamp index, star group
		lamps.put(i, [l[0], l[1], l[4], l[5], l[8], l[2]], Color(float(l[3]), float(i), float(grp), 0.0))
	lamps.commit()


## The rising lights' instances: control points need the gate of the height class in use.
func build_for_class(ci: int) -> void:
	if ci == _built_class:
		return
	_built_class = ci
	var T := s.gate()
	var inst: Array = []
	var rng := RandomNumberGenerator.new()
	companions = 0
	for i in n:
		var l: Array = L[i]
		var kind := int(l[2])
		var flags := int(l[3])
		var solo := (flags & 4) != 0
		var big := solo or kind == KIND_FIRE or kind == KIND_BONFIRE
		var x := float(l[0])
		var y := float(l[1])
		var p1 := Vector2(l[9], l[10])
		var p2 := Vector2(l[11], l[12]) + Vector2(0.38 * T.x, 0.55 * T.y)
		var p3 := Vector2(l[13], l[14]) + T
		if solo:
			p1 = Vector2(x, 0.25 * y + 0.75 * T.y)
			p2 = Vector2(0.65 * x + 0.35 * T.x, 0.88 * T.y + 0.12 * y)
		var dur := float(l[7])
		var fl := (1 if solo else 0) | (2 if big else 0)
		var nt := 8 if solo else (1 if kind == KIND_STAR else 3)
		for q in nt + 1:
			inst.append([[x, y, p1.x, p1.y, p2.x, p2.y], Color(p3.x, p3.y, dur, 0.0), Color(i, q, kind, fl)])
		if quality != "high" or solo or kind == KIND_STAR:
			continue
		# companion sparks: a lamp leaves as a little cluster of sparks (fires as a burst)
		rng.seed = 7919 * (i + 1)
		var nc := 0
		match kind:
			KIND_BONFIRE:
				nc = 4
			KIND_FIRE:
				nc = 2
			0:
				nc = 1 if rng.randf() < 0.55 else 0
			_:
				nc = 1 if rng.randf() < 0.45 else 0
		for c in nc:
			var delay := (0.08 + rng.randf() * 0.7) if kind >= KIND_FIRE else (0.2 + rng.randf() * 1.1)
			var j1 := Vector2(rng.randf_range(-4.0, 4.0), rng.randf_range(-3.0, 3.0))
			var j2 := Vector2(rng.randf_range(-6.0, 6.0), rng.randf_range(-4.0, 4.0))
			var j3 := Vector2(rng.randf_range(-2.0, 2.0), rng.randf_range(-1.5, 1.5))
			var x0 := x + float(rng.randi_range(-1, 1))
			var d2 := dur * rng.randf_range(0.9, 1.12)
			for q in 2:
				inst.append([[x0, y, p1.x + j1.x, p1.y + j1.y, p2.x + j2.x, p2.y + j2.y], Color(p3.x + j3.x, p3.y + j3.y, d2, delay), Color(i, q, kind, 4)])
			companions += 1
	rise.resize(inst.size())
	for k in inst.size():
		rise.put(k, inst[k][0], inst[k][1], inst[k][2])
	rise.commit()
	_build_shore(ci)


func _build_shore(ci: int) -> void:
	var set: Dictionary = s.data.lists["shoreSets"][ci]
	var items: Array = []
	for l in set["lights"]:
		# x y Z ph b win
		var big := float(l[4]) > 0.8 and float(l[2]) < 50.0
		items.append([l[0], l[1], 0, l[4], l[2], 1 if int(l[5]) == 1 else (2 if big else 0)])
	for p in set["flow"]:
		items.append([p[0], p[1], 1, p[2], p[3], p[4]])
	for r in set["ring"]:
		items.append([r[0], r[1], 2, r[2], 0, 0])
	items.append([set["yagura"][0], set["yagura"][1], 3, 0, 0, 0])
	for p in set["strings"]:
		items.append([p[0], p[1], 4, 0, 0, 0])
	var T := s.gate()
	items.append([floor(T.x + 0.5), floor(T.y + 0.5), 5, 0, 0, 0])
	shore.resize(items.size())
	for k in items.size():
		shore.put(k, items[k])
	shore.commit()


## Departures and arrivals for this frame (the JS updateRise, 8196ebf).
func update(rise_k: float, t: float) -> void:
	# departures: rise passing a lamp's turn; scrubbing back takes them home again
	while n_dep < n and r_of[n_dep] <= rise_k:
		var i := order[n_dep]
		tdep[i] = t - (rise_k - r_of[n_dep]) * 30.0
		tdep_img.set_pixel(i, 0, Color(tdep[i], 0, 0, 0))
		n_dep += 1
		dirty = true
	while n_dep > 0 and r_of[n_dep - 1] > rise_k:
		n_dep -= 1
		var i := order[n_dep]
		tdep[i] = NEVER
		arrived[i] = 0
		tdep_img.set_pixel(i, 0, Color(NEVER, 0, 0, 0))
		dirty = true
	if dirty:
		tdep_tex.update(tdep_img)
		dirty = false
	# arrivals at the gate
	in_flight = 0
	for k in n_dep:
		var i := order[k]
		if arrived[i] != 0:
			continue
		var el := t - tdep[i]
		if el >= float(L[i][7]):
			arrived[i] = 1
			arrivals.append(tdep[i] + float(L[i][7]))
		else:
			in_flight += 1
	while not arrivals.is_empty() and arrivals[0] < t - 1.5:
		arrivals.pop_front()
	inflow = clampf(arrivals.size() / 12.0, 0.0, 1.0)
	flash = 0.0
	for a in arrivals:
		flash += exp(-(t - a) / 0.28) * 0.55
	for p in [lamps, river, rise]:
		p.set_param("t", t)


## The floating lanterns drifting down the river (灯籠流し), positioned on the CPU. Since round 5 the
## river is the 3D lookout's: out of the western canyon, past the town's front and away to the south-
## east, so they drift away from us; dimmer as they go (a trail into the distance, not a blob where
## the river turns away and they crowd on screen).
func update_river(t: float, tod: float, rise_k: float, wave: float) -> void:
	if dep.is_empty():
		dep = s.m.get("dep", [])
		eye_rel = float(s.m.get("eyeRel", 380.0))
		plain_u = float(s.m.get("plainU", 182.0))
	var ra := VistaEnv.smoothj(19.1, 19.5, tod) * (1.0 - VistaEnv.smoothj(0.12, 0.6, rise_k))
	river.visible = ra > 0.02
	if not river.visible:
		return
	var rv: Array = s.m["river"]
	var cx := float(s.m["Cx"])
	var yl := float(s.m["YL"])
	var f := float(s.m["f"])
	var zimg: Image = s.data.images["groundZ"]
	var w := zimg.get_width()
	var h := zimg.get_height()
	var zb := zimg.get_data()
	for k in river_l.size():
		var fl: Array = river_l[k]
		var u := float(fl[0]) - fposmod(t * 0.02 + float(fl[1]) * 3.0, 3.0)
		var a := 0.0
		var x := -100.0
		var y := -100.0
		if u >= 0.5:
			var i := int(floor(u))
			var kk := u - i
			var A: Array = rv[i]
			var B: Array = rv[mini(i + 1, rv.size() - 1)]
			var X := lerpf(A[0], B[0], kk) + float(fl[2])
			var Z := lerpf(A[1], B[1], kk)
			x = floor(cx + f * X / Z + 0.5)
			y = floor(yl + f * floor_dep(Z) + 0.5)
			if x >= 0 and x < w and y >= 0 and y < h:
				var o := (int(y) * w + int(x)) * 2
				var zg := (zb[o] + zb[o + 1] * 256) * 1024.0 / 65535.0
				if zg >= Z * 0.9:
					a = ra * clampf(1.0 - (Z - 11.0) / 12.0, 0.4, 1.0)
					if wave >= 0.0:
						var arr := VistaSouthLights.wave_at(Vector2(X, Z).distance_to(Vector2(s.m["Xc"], s.m["Zc"])) / float(s.m["waveR"]))
						a *= 1.0 - VistaEnv.smoothj(arr - 0.004, arr + 0.012, wave)
		# kind 5 of the lamp shader: its level in the `on` slot, never leaving (the tdep texture is NEVER)
		river.put(k, [x, y, a, 0.0, 9.0, 5.0], Color(0, 0, 0, 0))
	river.commit()


## wave.js waveAt: the wave's progress when its ring reaches distance r (fraction of R).
const RK := [[0.0, 0.0], [0.12, 0.07], [0.3, 0.27], [0.5, 0.56], [0.62, 0.74], [0.8, 0.9], [0.95, 0.985], [1.0, 1.04]]


static func wave_at(r: float) -> float:
	if r <= 0.0:
		return 0.0
	for i in RK.size() - 1:
		if r <= RK[i + 1][1]:
			return lerpf(RK[i][0], RK[i + 1][0], (r - RK[i][1]) / (RK[i + 1][1] - RK[i][1]))
	return 1.01


var dep: Array = []          # the picture's depression below the eye (plain.js depG): knots (t, g)
var eye_rel := 380.0
var plain_u := 182.0


## The plain's floor at depth Z (prologue units) as the picture draws it: its depression / f (plain.js
## depG of the true depression; without knots the old proportional one, 1 / Z).
func floor_dep(Z: float) -> float:
	if dep.size() < 2:
		return 1.0 / Z
	var t := eye_rel / maxf(1e-6, Z * plain_u)
	for i in dep.size() - 1:
		var a: Array = dep[i]
		var b: Array = dep[i + 1]
		if t <= float(b[0]) or i == dep.size() - 2:
			return float(a[1]) + (t - float(a[0])) * (float(b[1]) - float(a[1])) / (float(b[0]) - float(a[0]))
	return 0.0
