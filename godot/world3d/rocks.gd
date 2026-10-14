class_name W3Rocks
extends Node3D
## Rock that the ground is made of where it is too steep to hold soil: outcrops on the spur and the
## ravine head, the face behind the spring, boulders on rough slopes, the lookout's own slab, and
## stepping stones. Each rock is a faceted, stratified blob (flat shading reads as pixel-art rock
## through the toon bands and the facet outlines), sunk into the slope and tilted with it.
## Sixteen shape variants are instanced with MultiMesh (one draw call per variant).

const VARIANTS := 16

var terrain: Terrain3D
var mat := ShaderMaterial.new()
var shapes: Array[ArrayMesh] = []
var blockers: Array = []


func _ico() -> Array:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var v := [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0),
		Vector3(0, -1, t), Vector3(0, 1, t), Vector3(0, -1, -t), Vector3(0, 1, -t),
		Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	for i in v.size():
		v[i] = (v[i] as Vector3).normalized()
	var f := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
		[10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11],
		[6, 2, 10], [8, 6, 7], [9, 8, 1]]
	for _s in 2:
		var cache := {}
		var nf := []
		for tri in f:
			var m := []
			for e in 3:
				var a: int = tri[e]
				var b: int = tri[(e + 1) % 3]
				var key := Vector2i(mini(a, b), maxi(a, b))
				if not cache.has(key):
					v.append(((v[a] as Vector3) + (v[b] as Vector3)).normalized())
					cache[key] = v.size() - 1
				m.append(cache[key])
			nf.append([tri[0], m[0], m[2]])
			nf.append([tri[1], m[1], m[0]])
			nf.append([tri[2], m[2], m[1]])
			nf.append([m[0], m[1], m[2]])
		f = nf
	return [v, f]


## One rock shape: noisy, flattened, stratified ledges, flat-shaded, vertex-coloured.
func make_shape(seed: int, flat := 0.65, strata := 0.22, sharp := 0.35) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var ico := _ico()
	var verts: Array = ico[0]
	var faces: Array = ico[1]
	var harmonics := []
	for k in 7:
		harmonics.append([Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized(), rng.randf_range(1.5, 4.5), rng.randf_range(0.05, 0.16), rng.randf() * TAU])
	var P := []
	for v in verts:
		var p: Vector3 = v
		var r := 1.0
		for h in harmonics:
			r += float(h[2]) * sin(p.dot(h[0]) * float(h[1]) + float(h[3]))
		p *= r
		p.y *= flat
		# ledges: heights pulled toward strata planes (layered rock, light tops)
		if strata > 0.0:
			var q := p.y / strata
			var fl := floorf(q)
			var fr := q - fl
			p.y = (fl + smoothstep(0.5 - sharp * 0.5, 0.5 + sharp * 0.5, fr)) * strata
		P.append(p)
	var vs := PackedVector3Array()
	var ns := PackedVector3Array()
	var cs := PackedColorArray()
	var u2 := PackedVector2Array()
	var base := Color(0.47, 0.48, 0.47)
	for tri in faces:
		var a: Vector3 = P[tri[0]]
		var b: Vector3 = P[tri[1]]
		var c: Vector3 = P[tri[2]]
		var n := (b - a).cross(c - a)
		if n.length() < 1e-8:
			continue
		n = n.normalized()
		if n.dot(a + b + c) < 0.0:
			n = -n
			var tmp := b
			b = c
			c = tmp
		var ctr := (a + b + c) / 3.0
		var tone := 0.92 + rng.randf() * 0.14
		var col := base * tone
		col = col.lerp(Color(0.40, 0.45, 0.47), clampf(-n.y, 0.0, 1.0) * 0.4)   # undersides bluer
		var ao := clampf(0.55 + (ctr.y + 0.4) * 0.6, 0.5, 1.0)
		col.a = ao
		var moss := clampf((n.y - 0.7) * 2.0, 0.0, 1.0) * (0.35 + 0.35 * sin(ctr.x * 5.0 + ctr.z * 3.0 + float(seed)))
		for p in [a, c, b]:
			vs.append(p)
			ns.append(n)
			cs.append(col)
			u2.append(Vector2(4.0, moss))
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = vs
	arr[Mesh.ARRAY_NORMAL] = ns
	arr[Mesh.ARRAY_COLOR] = cs
	arr[Mesh.ARRAY_TEX_UV2] = u2
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


func build(t: Terrain3D, placements: Array) -> void:
	terrain = t
	mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("porosity", 0.45)
	for i in VARIANTS:
		shapes.append(make_shape(1000 + i * 37, 0.55 + 0.25 * fposmod(i * 0.37, 1.0), 0.18 + 0.12 * fposmod(i * 0.61, 1.0)))
	var per := []
	for i in VARIANTS:
		per.append([])
	for p in placements:
		var kind: String = p["kind"]
		if kind != "boulder" and kind != "outcrop" and kind != "rock_slab":
			continue
		var v := int(p.get("variant", 0)) % VARIANTS
		if kind == "outcrop":
			v = (int(p.get("variant", 0)) * 3 + 5) % VARIANTS
		per[v].append(p)
	for i in VARIANTS:
		var list: Array = per[i]
		if list.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = shapes[i]
		mm.instance_count = list.size()
		for k in list.size():
			mm.set_instance_transform(k, _rock_xform(list[k]))
		var mi := MultiMeshInstance3D.new()
		mi.name = "Rocks_%d" % i
		mi.multimesh = mm
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		add_child(mi)


func _rock_xform(p: Dictionary) -> Transform3D:
	var x: float = p["x"]
	var z: float = p["z"]
	var s := float(p.get("scale", 1.0))
	var kind: String = p["kind"]
	var size := Vector3(0.9, 0.7, 0.8) * s
	if kind == "outcrop":
		size = Vector3(float(p.get("sx", 2.0)), float(p.get("sy", 1.2)), float(p.get("sz", 1.4)))
	elif kind == "rock_slab":
		size = Vector3(float(p.get("sx", 1.6)), float(p.get("sy", 1.2)), float(p.get("sz", 0.9)))
	var n := terrain.normal_at(x, z)
	var up := Vector3.UP.lerp(n, 0.6 if kind != "rock_slab" else 0.2).normalized()
	var yaw := float(p.get("rot", 0.0))
	var fwd := Vector3(sin(yaw), 0, cos(yaw))
	var right := up.cross(fwd).normalized()
	fwd = right.cross(up).normalized()
	var b := Basis(right * size.x, up * size.y, fwd * size.z)
	var sink := float(p.get("sink", 0.35))
	var y := terrain.height_at(x, z) - size.y * sink
	blockers.append([Vector3(x, 0, z), maxf(size.x, size.z) * 0.75])
	return Transform3D(b, Vector3(x, y, z))
