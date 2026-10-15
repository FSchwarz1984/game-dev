class_name W3Grass
extends Node3D
## Ground cover (round 4, scene agent): grasses, sedges, ferns, clover, moss cushions, horsetail,
## plantain, dwarf bamboo, pampas grass and the late-summer flowers, as pixel-art cards baked by the
## terrain generator (tools/world3d/w3terrain/cover.py: plant communities, species clumped by noise
## and mixing along their edges, every clump its own tile, size, mirror, tint and wind phase).
## Loaded here from terrain/<name>/cover.bin, one mesh per 16 m chunk and layer, drawn with the
## renderer's outline-less foliage material in card mode (lean 0: the cards stand on the ground at
## their root). The 'low' layer casts no shadow; the 'tall' layer (pampas grass, ferns, dwarf
## bamboo, tall grass and flowers) does.

var terrain: Terrain3D
var mat := ShaderMaterial.new()
var count := 0
var tris := 0


func build(t: Terrain3D) -> void:
	terrain = t
	var info: Dictionary = t.info.get("cover", {})
	if info.is_empty():
		push_warning("W3Grass: the terrain has no ground cover (rebuild it with tools/world3d/build_terrain.py)")
		return
	var atlas: Image = load(String(info.get("atlas", "res://world3d/terrain/common/cover.png")))
	mat.shader = load("res://render3d/shaders/toon_foliage_noline.gdshader")
	mat.set_shader_parameter("foliage_mode", 1)
	mat.set_shader_parameter("leaf_tex", ImageTexture.create_from_image(atlas))
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("cutaway", false)
	mat.set_shader_parameter("wind_px", 1.0)
	mat.set_shader_parameter("porosity", 0.6)
	# the sprites carry their own natural greens: little of the material's extra freshness, a little
	# light through the blades against the sun
	mat.set_shader_parameter("lush", 0.15)
	mat.set_shader_parameter("transmit", 0.35)
	var dir := "res://world3d/terrain/" + String(t.info.get("name", "saddle"))
	var f := FileAccess.open(dir.path_join(String(info.get("file", "cover.bin"))), FileAccess.READ)
	if f == null:
		push_warning("W3Grass: no cover.bin")
		return
	var fmt := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
	for c in info.get("chunks", []):
		var n := int(c["vertices"])
		var nt := int(c["triangles"])
		f.seek(int(c["offset"]))
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = f.get_buffer(n * 12).to_vector3_array()
		arr[Mesh.ARRAY_NORMAL] = f.get_buffer(n * 12).to_vector3_array()
		arr[Mesh.ARRAY_TEX_UV] = f.get_buffer(n * 8).to_vector2_array()
		arr[Mesh.ARRAY_TEX_UV2] = f.get_buffer(n * 8).to_vector2_array()
		arr[Mesh.ARRAY_COLOR] = f.get_buffer(n * 16).to_color_array()
		arr[Mesh.ARRAY_CUSTOM0] = f.get_buffer(n * 16).to_float32_array()
		arr[Mesh.ARRAY_INDEX] = f.get_buffer(nt * 12).to_int32_array()
		var m := ArrayMesh.new()
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr, [], {}, fmt)
		var a: Array = c["aabb"]
		# the cards are rebuilt on the camera plane in the shader: pad the bounds by their size
		m.custom_aabb = AABB(Vector3(a[0][0], a[0][1], a[0][2]) - Vector3(1.0, 1.0, 1.5), Vector3(a[1][0], a[1][1], a[1][2]) + Vector3(2.0, 2.5, 3.0))
		var mi := MeshInstance3D.new()
		mi.name = "Cover_%d_%d_%s" % [int(c["chunk"][0]), int(c["chunk"][1]), String(c["layer"])]
		mi.mesh = m
		mi.material_override = mat
		var tall := String(c["layer"]) == "tall"
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if tall else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		count += n / 4
		tris += nt
	print("COVER cards=%d tris=%d species=%s" % [count, tris, str(info.get("species", {}))])
