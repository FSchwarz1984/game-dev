class_name W3Grass
extends Node3D
## Ground cover on the terrain (shaders/toon_grass.gdshader): tufts, clover, small flowers and
## ferns, scattered from the terrain's grass and tuft-density maps on a jittered grid, clumped by
## noise, kept off paths, water, rock and steep banks. One MultiMesh per 16 m chunk for culling.

const CHUNK := 16.0
const STEP := 0.42

var terrain: Terrain3D
var mat := ShaderMaterial.new()
var count := 0


func build(t: Terrain3D) -> void:
	terrain = t
	var dir := "res://world3d/terrain/saddle"
	var common := "res://world3d/terrain/common"
	mat.shader = load("res://render3d/shaders/toon_grass.gdshader")
	mat.set_shader_parameter("tufts", ImageTexture.create_from_image(load(common + "/tufts.png")))
	mat.set_shader_parameter("palette", ImageTexture.create_from_image(load(common + "/palette.png")))
	var m0: Image = load(dir + "/m0.png")
	var m1: Image = load(dir + "/m1.png")
	var m2: Image = load(dir + "/m2.png")
	var m3: Image = load(dir + "/m3.png")
	var sp: Dictionary = terrain.info["splat"]
	var scell := float(sp["cell"])
	var sw := int(sp["size"][0])
	var sh := int(sp["size"][1])
	var x0 := terrain.origin.x
	var z0 := terrain.origin.y
	var x1 := x0 + (terrain.nx - 1) * terrain.cell
	var z1 := z0 + (terrain.nz - 1) * terrain.cell
	var noise := FastNoiseLite.new()
	noise.seed = 77
	noise.frequency = 0.085
	var edge := FastNoiseLite.new()
	edge.seed = 78
	edge.frequency = 0.45
	var rng := RandomNumberGenerator.new()
	rng.seed = 404
	var chunks := {}
	var quad := _quad()
	var z := z0 + STEP * 0.5
	while z < z1:
		var x := x0 + STEP * 0.5
		while x < x1:
			var px := x + rng.randf_range(-0.45, 0.45) * STEP
			var pz := z + rng.randf_range(-0.45, 0.45) * STEP
			var si := clampi(int((px - x0) / scell), 0, sw - 1)
			var sj := clampi(int((pz - z0) / scell), 0, sh - 1)
			var c0 := m0.get_pixel(si, sj)
			var c1 := m1.get_pixel(si, sj)
			var c2 := m2.get_pixel(si, sj)
			var c3 := m3.get_pixel(si, sj)
			var grass := c0.r
			var dens := c3.b
			# massing: big clumps with bare ground between them (negative space), ragged edges
			var clump := noise.get_noise_2d(px, pz) * 0.5 + 0.5 + edge.get_noise_2d(px, pz) * 0.12
			var mass := smoothstep(0.5, 0.64, clump)
			var p := grass * (0.03 + 0.95 * mass * (0.45 + 0.55 * dens)) * (1.0 - c3.a * 0.55)
			var moss := c1.r
			var fern := moss * 0.35 + (c3.a * 0.25 if c1.g > 0.3 else 0.0)
			if rng.randf() < p and grass > 0.55 and terrain.walkable(px, pz):
				var w := terrain.water_at(px, pz)
				if w["kind"] == 0:
					var dry := c3.g > 0.55
					var flowers := c2.a
					var cellv := 0
					var r := rng.randf()
					if flowers > 0.15 and rng.randf() < flowers * 0.4:
						cellv = [7, 8, 9][rng.randi() % 3]
					elif dry:
						cellv = [10, 2, 3, 4][rng.randi() % 4] if r < 0.5 else [0, 1][rng.randi() % 2]
					elif mass > 0.85 and r < 0.55:
						cellv = [2, 3, 4, 5][rng.randi() % 4]          # the heart of a clump grows tall
					elif mass < 0.3:
						cellv = [0, 1, 6][rng.randi() % 3]             # singles in the open stay short
					else:
						cellv = [0, 1, 2, 3, 6][rng.randi() % 5]
					_add(chunks, px, pz, cellv, 1.0 if dry else 0.0, rng.randf_range(-0.6, 0.3) + mass * 0.25, 0.8 if cellv in [4, 5] else 0.5)
			elif rng.randf() < fern * 0.5 and terrain.walkable(px, pz) and terrain.water_at(px, pz)["kind"] == 0:
				_add(chunks, px, pz, 11, 5.0 if moss > 0.4 else 0.0, rng.randf_range(-0.6, 0.3), 0.5)
			x += STEP
		z += STEP
	for key in chunks:
		var list: Array = chunks[key]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = quad
		mm.instance_count = list.size()
		for k in list.size():
			var e: Array = list[k]
			mm.set_instance_transform(k, e[0])
			mm.set_instance_custom_data(k, e[1])
		var mi := MultiMeshInstance3D.new()
		mi.multimesh = mm
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.extra_cull_margin = 1.0
		add_child(mi)
		count += list.size()


func _add(chunks: Dictionary, x: float, z: float, cellv: int, row: float, tone: float, flex: float) -> void:
	var key := Vector2i(floori(x / CHUNK), floori(z / CHUNK))
	if not chunks.has(key):
		chunks[key] = []
	var y := terrain.height_at(x, z)
	var n := terrain.normal_at(x, z)
	var b := Basis(Vector3.RIGHT, n, Vector3.BACK)
	chunks[key].append([Transform3D(b, Vector3(x, y, z)), Color(float(cellv), row, tone, flex)])


func _quad() -> ArrayMesh:
	var corners := [Vector2(-8, -1), Vector2(8, -1), Vector2(8, 15), Vector2(-8, 15)]
	var uvs := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
	var verts := PackedVector3Array()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var nrm := PackedVector3Array()
	for i in 4:
		var c: Vector2 = corners[i]
		verts.append(Vector3(c.x, c.y, 0.0) / 20.0)
		uv.append(uvs[i])
		uv2.append(c)
		nrm.append(Vector3.UP)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = nrm
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_TEX_UV2] = uv2
	# clockwise on screen: Godot's front face (corners: bottom-left, bottom-right, top-right, top-left)
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 2, 1, 0, 3, 2])
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m
