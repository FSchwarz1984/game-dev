class_name Terrain3D
extends Node3D
## A natural terrain region built from tools/world3d (godot/world3d/terrain/<name>/): smooth
## heightfield chunks drawn with shaders/toon_terrain.gdshader, the water surfaces, and the queries
## the game needs (height, normal, walkable, water). See docs/knowledge/21-3d-pixel-render.md.

const CHUNK_CELLS := 64

var info := {}
var origin := Vector2.ZERO
var cell := 0.5
var nx := 0
var nz := 0
var heights := PackedFloat32Array()
var walk := PackedByteArray()
var water_h := PackedFloat32Array()
var water_k := PackedByteArray()
var water_flow := PackedFloat32Array()      # flow angle (radians), stream only
var terrain_mat := ShaderMaterial.new()
var water_mat: ShaderMaterial
var chunks: Array[MeshInstance3D] = []
var water_meshes: Array[MeshInstance3D] = []


func load_region(dir: String) -> bool:
	var f := FileAccess.open(dir.path_join("terrain.json"), FileAccess.READ)
	if f == null:
		push_error("Terrain3D: no terrain.json in " + dir)
		return false
	info = JSON.parse_string(f.get_as_text())
	origin = Vector2(info["origin"][0], info["origin"][1])
	cell = float(info["cell"])
	nx = int(info["size"][0])
	nz = int(info["size"][1])
	var hmin: float = info["height"]["min"]
	var hrange: float = info["height"]["range"]
	var him: Image = load(dir.path_join("height.png"))
	var hd := him.get_data()
	var bpp := hd.size() / (nx * nz)
	heights.resize(nx * nz)
	for i in nx * nz:
		var q := hd[i * bpp] * 256 + hd[i * bpp + 1]
		heights[i] = hmin + float(q) / 65535.0 * hrange
	var wim: Image = load(dir.path_join("walk.png"))
	wim.convert(Image.FORMAT_L8)
	walk = wim.get_data()
	var wat: Image = load(dir.path_join("water.png"))
	wat.convert(Image.FORMAT_RGBA8)
	var wd := wat.get_data()
	water_h.resize(nx * nz)
	water_k.resize(nx * nz)
	water_flow.resize(nx * nz)
	for i in nx * nz:
		var q := wd[i * 4] * 256 + wd[i * 4 + 1]
		water_k[i] = wd[i * 4 + 2] / 64
		water_h[i] = hmin + float(q) / 65535.0 * hrange if q > 0 else -1000.0
		water_flow[i] = float(wd[i * 4 + 3]) / 255.0 * TAU
	_setup_material(dir)
	_build_chunks()
	return true


func _image_texture(path: String) -> ImageTexture:
	var im: Image = load(path)
	return ImageTexture.create_from_image(im)


func _setup_material(dir: String) -> void:
	terrain_mat.shader = load("res://render3d/shaders/toon_terrain.gdshader")
	var common := dir.get_base_dir().path_join("common")
	for k in ["m0", "m1", "m2", "m3"]:
		terrain_mat.set_shader_parameter(k, _image_texture(dir.path_join(k + ".png")))
	terrain_mat.set_shader_parameter("palette", _image_texture(common.path_join("palette.png")))
	terrain_mat.set_shader_parameter("glyphs", _image_texture(common.path_join("glyphs.png")))
	var sp: Dictionary = info["splat"]
	terrain_mat.set_shader_parameter("splat_origin", origin)
	terrain_mat.set_shader_parameter("splat_cell", float(sp["cell"]))
	terrain_mat.set_shader_parameter("splat_size", Vector2(sp["size"][0], sp["size"][1]))
	var gf := FileAccess.open(common.path_join("glyphs.json"), FileAccess.READ)
	if gf:
		var table: Dictionary = JSON.parse_string(gf.get_as_text())
		var names := {"grass": "g_grass", "flowers": "g_flowers", "dirt": "g_dirt", "gravel": "g_gravel", "rock": "g_rock",
			"moss": "g_moss", "litter": "g_litter", "needles": "g_needles", "bamboo_litter": "g_bamboo", "bank": "g_bank"}
		for k in names:
			if table.has(k):
				terrain_mat.set_shader_parameter(names[k], Vector2(table[k][0], table[k][1]))


func h_at_index(i: int, j: int) -> float:
	i = clampi(i, 0, nx - 1)
	j = clampi(j, 0, nz - 1)
	return heights[j * nx + i]


func _build_chunks() -> void:
	for c in chunks:
		c.queue_free()
	chunks.clear()
	var cx_n := ceili(float(nx - 1) / CHUNK_CELLS)
	var cz_n := ceili(float(nz - 1) / CHUNK_CELLS)
	for cz in cz_n:
		for cx in cx_n:
			var mi := MeshInstance3D.new()
			mi.name = "Chunk_%d_%d" % [cx, cz]
			mi.mesh = _chunk_mesh(cx * CHUNK_CELLS, cz * CHUNK_CELLS)
			mi.material_override = terrain_mat
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			add_child(mi)
			chunks.append(mi)
			var wm := _water_mesh(cx * CHUNK_CELLS, cz * CHUNK_CELLS)
			if wm != null:
				var w := MeshInstance3D.new()
				w.name = "Water_%d_%d" % [cx, cz]
				w.mesh = wm
				w.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				if water_mat:
					w.material_override = water_mat
				add_child(w)
				water_meshes.append(w)


func _chunk_mesh(i0: int, j0: int) -> ArrayMesh:
	var w := mini(CHUNK_CELLS, nx - 1 - i0) + 1
	var d := mini(CHUNK_CELLS, nz - 1 - j0) + 1
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	verts.resize(w * d)
	norms.resize(w * d)
	for j in d:
		for i in w:
			var gi := i0 + i
			var gj := j0 + j
			var h := h_at_index(gi, gj)
			verts[j * w + i] = Vector3(origin.x + gi * cell, h, origin.y + gj * cell)
			var dx := (h_at_index(gi + 1, gj) - h_at_index(gi - 1, gj)) / (2.0 * cell)
			var dz := (h_at_index(gi, gj + 1) - h_at_index(gi, gj - 1)) / (2.0 * cell)
			norms[j * w + i] = Vector3(-dx, 1.0, -dz).normalized()
	var idx := PackedInt32Array()
	idx.resize((w - 1) * (d - 1) * 6)
	var k := 0
	for j in d - 1:
		for i in w - 1:
			var a := j * w + i
			# split each quad along the diagonal that follows the surface better
			var h00 := verts[a].y
			var h11 := verts[a + w + 1].y
			var h10 := verts[a + 1].y
			var h01 := verts[a + w].y
			if absf(h00 - h11) < absf(h10 - h01):
				idx[k] = a; idx[k + 1] = a + 1; idx[k + 2] = a + w + 1
				idx[k + 3] = a; idx[k + 4] = a + w + 1; idx[k + 5] = a + w
			else:
				idx[k] = a; idx[k + 1] = a + 1; idx[k + 2] = a + w
				idx[k + 3] = a + 1; idx[k + 4] = a + w + 1; idx[k + 5] = a + w
			k += 6
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


func _water_mesh(i0: int, j0: int) -> ArrayMesh:
	var w := mini(CHUNK_CELLS, nx - 1 - i0)
	var d := mini(CHUNK_CELLS, nz - 1 - j0)
	var verts := PackedVector3Array()
	var uv2 := PackedVector2Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for j in d:
		for i in w:
			var gi := i0 + i
			var gj := j0 + j
			var kk := water_k[gj * nx + gi]
			if kk == 0:
				continue
			var hw := water_h[gj * nx + gi]
			var fl := water_flow[gj * nx + gi]
			var base := verts.size()
			var x := origin.x + gi * cell - cell * 0.5
			var z := origin.y + gj * cell - cell * 0.5
			for c in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
				verts.append(Vector3(x + c.x * cell, hw, z + c.y * cell))
				uv2.append(Vector2(float(kk), fl))
				cols.append(Color(1, 1, 1, 1))
			idx.append_array([base, base + 1, base + 2, base, base + 2, base + 3])
	if verts.is_empty():
		return null
	var norms := PackedVector3Array()
	norms.resize(verts.size())
	norms.fill(Vector3.UP)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_TEX_UV2] = uv2
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


# ------------------------------------------------------------------------------------------------
# queries

func height_at(x: float, z: float) -> float:
	var fx := (x - origin.x) / cell
	var fz := (z - origin.y) / cell
	var i := floori(fx)
	var j := floori(fz)
	var tx := fx - i
	var tz := fz - j
	var a := h_at_index(i, j)
	var b := h_at_index(i + 1, j)
	var c := h_at_index(i, j + 1)
	var d := h_at_index(i + 1, j + 1)
	return lerpf(lerpf(a, b, tx), lerpf(c, d, tx), tz)


func normal_at(x: float, z: float) -> Vector3:
	var e := cell
	var dx := (height_at(x + e, z) - height_at(x - e, z)) / (2.0 * e)
	var dz := (height_at(x, z + e) - height_at(x, z - e)) / (2.0 * e)
	return Vector3(-dx, 1.0, -dz).normalized()


func walkable(x: float, z: float) -> bool:
	var i := roundi((x - origin.x) / cell)
	var j := roundi((z - origin.y) / cell)
	if i < 0 or j < 0 or i >= nx or j >= nz:
		return false
	return walk[j * nx + i] > 127


func water_at(x: float, z: float) -> Dictionary:
	var i := clampi(roundi((x - origin.x) / cell), 0, nx - 1)
	var j := clampi(roundi((z - origin.y) / cell), 0, nz - 1)
	return {"kind": water_k[j * nx + i], "h": water_h[j * nx + i]}


func marker(name: String) -> Vector3:
	var m: Dictionary = info["markers"].get(name, {})
	if m.is_empty():
		return Vector3.ZERO
	return Vector3(m["x"], height_at(m["x"], m["z"]), m["z"])
