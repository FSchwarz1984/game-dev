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


func _ico(subdiv := 3) -> Array:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var v := [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0),
		Vector3(0, -1, t), Vector3(0, 1, t), Vector3(0, -1, -t), Vector3(0, 1, -t),
		Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	for i in v.size():
		v[i] = (v[i] as Vector3).normalized()
	var f := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
		[10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11],
		[6, 2, 10], [8, 6, 7], [9, 8, 1]]
	for _s in subdiv:
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


## One rock shape: an irregular displaced blob (several scales of noise, a few chipped notches in
## the silhouette, an optional hint of strata), smooth-shaded so the toon bands follow its bumps
## instead of showing polygon planes, vertex-coloured (grey variation, darker crevices, moss on what
## faces up, dark where it meets the ground).
func make_shape(seed: int, flat := 0.65, strata := 0.22, sharp := 0.35, subdiv := 3) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var ico := _ico(subdiv)
	var verts: Array = ico[0]
	var faces: Array = ico[1]
	var noise := FastNoiseLite.new()
	noise.seed = seed
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 1.6
	noise.fractal_type = FastNoiseLite.FRACTAL_FBM
	noise.fractal_octaves = 4
	var harmonics := []
	for k in 6:
		harmonics.append([Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized(), rng.randf_range(1.2, 3.4), rng.randf_range(0.05, 0.14), rng.randf() * TAU])
	var notches := []
	for k in 3:
		notches.append([Vector3(rng.randf_range(-1, 1), rng.randf_range(-0.3, 0.8), rng.randf_range(-1, 1)).normalized(), rng.randf_range(0.82, 0.95)])
	var P := PackedVector3Array()
	var disp := PackedFloat32Array()
	for v in verts:
		var d: Vector3 = v
		var r := 1.0
		for h in harmonics:
			r += float(h[2]) * sin(d.dot(h[0]) * float(h[1]) + float(h[3]))
		r += noise.get_noise_3dv(d * 1.0) * 0.16
		# chipped notches: the silhouette breaks where a plane bites into the blob
		for nt in notches:
			var nd: Vector3 = nt[0]
			var lim: float = nt[1]
			var along := d.dot(nd) * r
			if along > lim:
				r -= (along - lim) * 0.85
		var p := d * r
		p.y *= flat
		if p.y < -0.25:
			p.y = -0.25 + (p.y + 0.25) * 0.35
		if strata > 0.0:
			var q := p.y / strata
			var fl := floorf(q)
			p.y = (fl + smoothstep(0.5 - sharp * 0.5, 0.5 + sharp * 0.5, q - fl)) * strata * 0.5 + p.y * 0.5
		P.append(p)
		disp.append(r)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var mnoise := FastNoiseLite.new()
	mnoise.seed = seed + 5
	mnoise.frequency = 2.2
	for i in P.size():
		var p: Vector3 = P[i]
		var crevice := clampf((1.0 - disp[i]) * 3.0, 0.0, 1.0)
		var tone := 0.9 + 0.12 * noise.get_noise_3dv(p * 0.7 + Vector3(9, 1, 3))
		# granite: a warm grey (feldspar and quartz), the crevices a cooler grey
		var col := Color(0.52, 0.515, 0.495) * tone
		col = col.lerp(Color(0.41, 0.42, 0.42), crevice * 0.6)
		col.a = clampf(0.5 + (p.y + 0.25) * 0.9, 0.45, 1.0)          # AO: dark where it meets the ground
		st.set_color(col)
		var moss_n := mnoise.get_noise_3dv(p) * 0.5 + 0.5
		st.set_uv2(Vector2(4.0, clampf(moss_n * 1.0 - 0.3, 0.0, 1.0)))
		st.add_vertex(p)
	for tri in faces:
		var a: Vector3 = P[tri[0]]
		var b: Vector3 = P[tri[1]]
		var c: Vector3 = P[tri[2]]
		var n := (b - a).cross(c - a)
		if n.dot(a + b + c) < 0.0:
			st.add_index(tri[0]); st.add_index(tri[1]); st.add_index(tri[2])
		else:
			st.add_index(tri[0]); st.add_index(tri[2]); st.add_index(tri[1])
	st.generate_normals()
	return st.commit()


func build(t: Terrain3D, placements: Array) -> void:
	terrain = t
	mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("porosity", 0.45)
	for i in VARIANTS:
		shapes.append(make_shape(1000 + i * 37, 0.55 + 0.25 * fposmod(i * 0.37, 1.0), (0.22 if i % 3 == 0 else 0.0)))
	var groups := {}
	for p in placements:
		var kind: String = p["kind"]
		if kind != "boulder" and kind != "outcrop" and kind != "rock_slab":
			continue
		var v := int(p.get("variant", 0)) % VARIANTS
		if kind == "outcrop":
			v = (int(p.get("variant", 0)) * 3 + 5) % VARIANTS
		var key := Vector3i(v, floori(float(p["x"]) / 32.0), floori(float(p["z"]) / 32.0))
		if not groups.has(key):
			groups[key] = []
		groups[key].append(p)
	for key in groups:
		var list: Array = groups[key]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = shapes[key.x]
		mm.instance_count = list.size()
		for k in list.size():
			mm.set_instance_transform(k, _rock_xform(list[k]))
		var mi := MultiMeshInstance3D.new()
		mi.name = "Rocks_%d_%d_%d" % [key.x, key.y, key.z]
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
	# what blocks her is the rock's girth where it comes out of the ground (deeply sunk rocks, like
	# the lookout's rim, are mostly below her feet)
	blockers.append([Vector3(x, 0, z), maxf(size.x, size.z) * 0.5 * (1.0 - sink * 0.6)])
	return Transform3D(b, Vector3(x, y, z))
