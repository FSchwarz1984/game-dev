# Packs the generator's intermediates (tools/world3d_assets/out/manifest.json) into Godot resources
# next to the PNG textures the generators already wrote (and Godot already imported):
# meshes (.res ArrayMesh), materials (.tres ShaderMaterial using res://render3d/shaders) and scenes
# (.tscn). Run headless in the pack project (tools/world3d_assets/out/pack):
#   godot --headless --path <pack> --script <this file> -- <manifest.json>
extends SceneTree

var manifest: Dictionary
var mat_cache := {}
var mesh_cache := {}


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		push_error("usage: -- <manifest.json>")
		quit(1)
		return
	manifest = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	for path in manifest.materials:
		_material(path)
	for path in manifest.meshes:
		_mesh(path)
	for sc in manifest.scenes:
		_scene(sc)
	print("packed: %d materials, %d meshes, %d scenes" % [manifest.materials.size(), manifest.meshes.size(), manifest.scenes.size()])
	quit(0)


func _material(path: String) -> Material:
	if mat_cache.has(path):
		return mat_cache[path]
	var m: Dictionary = manifest.materials[path]
	var mat := ShaderMaterial.new()
	mat.shader = load(m.shader)
	var types := {}
	for u in mat.shader.get_shader_uniform_list():
		types[u.name] = int(u.type)
	for k in m.params:
		var v = m.params[k]
		if not types.has(k):
			push_error("%s: the shader has no uniform '%s'" % [path, k])
		elif types[k] == TYPE_INT:
			v = int(v)
		elif types[k] == TYPE_BOOL:
			v = bool(v)
		if v is Array:
			match v.size():
				2: v = Vector2(v[0], v[1])
				3: v = Color(v[0], v[1], v[2])
				4: v = Color(v[0], v[1], v[2], v[3])
		mat.set_shader_parameter(k, v)
	for k in m.textures:
		var t: Texture2D = load(m.textures[k])
		if t == null:
			push_error("texture not imported: " + String(m.textures[k]))
		mat.set_shader_parameter(k, t)
	mat.render_priority = int(m.get("render_priority", 0))
	_check(ResourceSaver.save(mat, path), path)
	mat = load(path)
	mat_cache[path] = mat
	return mat


func _mesh(path: String) -> ArrayMesh:
	if mesh_cache.has(path):
		return mesh_cache[path]
	var e: Dictionary = manifest.meshes[path]
	var f := FileAccess.open(e.bin, FileAccess.READ)
	var am := ArrayMesh.new()
	for s in e.surfaces:
		var n: int = int(s.vertices)
		var t: int = int(s.triangles)
		f.seek(int(s.offset))
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = _v3(f.get_buffer(n * 12).to_float32_array())
		arr[Mesh.ARRAY_NORMAL] = _v3(f.get_buffer(n * 12).to_float32_array())
		arr[Mesh.ARRAY_TEX_UV] = _v2(f.get_buffer(n * 8).to_float32_array())
		var fmt := 0
		if s.uv2:
			arr[Mesh.ARRAY_TEX_UV2] = _v2(f.get_buffer(n * 8).to_float32_array())
		if s.color:
			arr[Mesh.ARRAY_COLOR] = _col(f.get_buffer(n * 16).to_float32_array())
		if s.custom0:
			arr[Mesh.ARRAY_CUSTOM0] = f.get_buffer(n * 16).to_float32_array()
			fmt |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
		if s.get("custom1", false):
			arr[Mesh.ARRAY_CUSTOM1] = f.get_buffer(n * 16).to_float32_array()
			fmt |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT
		arr[Mesh.ARRAY_INDEX] = f.get_buffer(t * 12).to_int32_array()
		am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr, [], {}, fmt)
		var si := am.get_surface_count() - 1
		am.surface_set_name(si, String(s.material).get_file().get_basename())
		if manifest.materials.has(s.material):
			am.surface_set_material(si, _material(s.material))
	if e.has("custom_aabb"):
		var a: Array = e.custom_aabb
		am.custom_aabb = AABB(Vector3(a[0][0], a[0][1], a[0][2]), Vector3(a[1][0], a[1][1], a[1][2]))
	_check(ResourceSaver.save(am, path, ResourceSaver.FLAG_COMPRESS), path)
	am = load(path)
	mesh_cache[path] = am
	return am


func _scene(sc: Dictionary) -> void:
	var root := Node3D.new()
	root.name = String(sc.path).get_file().get_basename().to_pascal_case()
	if sc.get("script") != null:
		root.set_script(load(String(sc.script)))
	for k in sc.meta:
		root.set_meta(k, sc.meta[k])
	var by_name := {"": root}
	for nd in sc.nodes:
		var node: Node3D
		match String(nd.get("type", "mesh")):
			"mesh":
				var mi := MeshInstance3D.new()
				mi.mesh = _mesh(nd.mesh)
				if nd.has("material_override"):
					mi.material_override = _material(nd.material_override)
				var cs := String(nd.get("cast_shadow", "on"))
				mi.cast_shadow = {"on": GeometryInstance3D.SHADOW_CASTING_SETTING_ON, "off": GeometryInstance3D.SHADOW_CASTING_SETTING_OFF,
					"double": GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED, "only": GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY}[cs]
				if nd.has("extra_cull_margin"):
					mi.extra_cull_margin = float(nd.extra_cull_margin)
				node = mi
			"marker":
				node = Marker3D.new()
			_:
				node = Node3D.new()
		node.name = nd.name
		if nd.has("pos"):
			node.position = Vector3(nd.pos[0], nd.pos[1], nd.pos[2])
		if nd.has("rot"):
			node.rotation_degrees = Vector3(nd.rot[0], nd.rot[1], nd.rot[2])
		if nd.has("scale"):
			node.scale = Vector3(nd.scale[0], nd.scale[1], nd.scale[2])
		if nd.has("visible"):
			node.visible = bool(nd.visible)
		if nd.has("meta"):
			for k in nd.meta:
				node.set_meta(k, nd.meta[k])
		var parent: Node = by_name.get(String(nd.get("parent", "")), root)
		parent.add_child(node)
		by_name[String(nd.name)] = node
	_own(root, root)
	var ps := PackedScene.new()
	_check(ps.pack(root), sc.path)
	_check(ResourceSaver.save(ps, sc.path), sc.path)
	root.free()


func _own(n: Node, owner: Node) -> void:
	for c in n.get_children():
		c.owner = owner
		_own(c, owner)


func _v3(a: PackedFloat32Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	out.resize(a.size() / 3)
	for i in out.size():
		out[i] = Vector3(a[i * 3], a[i * 3 + 1], a[i * 3 + 2])
	return out


func _v2(a: PackedFloat32Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	out.resize(a.size() / 2)
	for i in out.size():
		out[i] = Vector2(a[i * 2], a[i * 2 + 1])
	return out


func _col(a: PackedFloat32Array) -> PackedColorArray:
	var out := PackedColorArray()
	out.resize(a.size() / 4)
	for i in out.size():
		out[i] = Color(a[i * 4], a[i * 4 + 1], a[i * 4 + 2], a[i * 4 + 3])
	return out


func _check(err: int, what: String) -> void:
	if err != OK:
		push_error("failed (%d): %s" % [err, what])
