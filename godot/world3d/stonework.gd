class_name W3Stonework
extends Node3D
## The stonework people built where the land needed holding, and the roads they laid (round 4):
##   * dry-stone retaining walls (野面積み) along the yards cut into or built out from the slope and
##     the shrine terrace's stone face: from the terrain generator's real pad edges (terrain.json
##     "walls"), so they hold exactly the step the terrain has; small faceted stones (W3Rocks
##     shapes, flattened) in irregular courses with a slight batter, MultiMesh per shape;
##   * the roads and paths as real geometry (tools/world3d/w3terrain/roads.py, terrain.json "roads"
##     and roads.bin): stone paving with kerbs, gutters and cross drains, natural-stone, log and
##     cut-stone steps, stepping stones, half-buried stones and roots, per 16 m chunk. The 'flat'
##     layer (paving, stepping stones) casts no shadow; the 'solid' layer (steps, kerbs, logs) does.
## Materials: the renderer's toon_solid, not leaned (ground-hugging, docs/knowledge/21 §2.1).

const SHAPES := 8

var terrain: Terrain3D
var mat := ShaderMaterial.new()
var road_mat := ShaderMaterial.new()
var per_shape := []
var rng := RandomNumberGenerator.new()
var road_tris := 0
var road_meshes := 0


func build(t: Terrain3D, rocks: W3Rocks) -> void:
	terrain = t
	rng.seed = 2207
	mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("porosity", 0.55)
	mat.set_shader_parameter("tint", Color(1.04, 1.0, 0.94))
	road_mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	road_mat.set_shader_parameter("lean", 0.0)
	road_mat.set_shader_parameter("porosity", 0.6)
	var shapes: Array[ArrayMesh] = []
	for i in SHAPES:
		# wall stones are 6-10 px across: 80 triangles each is plenty (1,280 made the walls 1.7 M
		# triangles a frame)
		shapes.append(rocks.make_shape(5000 + i * 53, 0.62, 0.0, 0.0, 1))
		per_shape.append([])
	for w in terrain.info.get("walls", []):
		_wall(w)
	for i in SHAPES:
		var list: Array = per_shape[i]
		if list.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = shapes[i]
		mm.instance_count = list.size()
		for k in list.size():
			mm.set_instance_transform(k, list[k])
		var mi := MultiMeshInstance3D.new()
		mi.name = "Stones_%d" % i
		mi.multimesh = mm
		mi.material_override = mat
		add_child(mi)
	_roads()


## The road and path geometry baked by the terrain generator.
func _roads() -> void:
	var info: Dictionary = terrain.info.get("roads", {})
	if info.is_empty():
		return
	var dir := "res://world3d/terrain/" + String(terrain.info.get("name", "saddle"))
	var f := FileAccess.open(dir.path_join(String(info.get("file", "roads.bin"))), FileAccess.READ)
	if f == null:
		push_warning("W3Stonework: no road geometry (%s)" % info.get("file", ""))
		return
	for c in info.get("chunks", []):
		var n := int(c["vertices"])
		var t := int(c["triangles"])
		f.seek(int(c["offset"]))
		var verts := f.get_buffer(n * 12).to_vector3_array()
		var norms := f.get_buffer(n * 12).to_vector3_array()
		var cols := f.get_buffer(n * 16).to_color_array()
		var uvs := f.get_buffer(n * 8).to_vector2_array()
		var idx := f.get_buffer(t * 12).to_int32_array()
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = verts
		arr[Mesh.ARRAY_NORMAL] = norms
		arr[Mesh.ARRAY_COLOR] = cols
		arr[Mesh.ARRAY_TEX_UV2] = uvs
		arr[Mesh.ARRAY_INDEX] = idx
		var m := ArrayMesh.new()
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		var mi := MeshInstance3D.new()
		mi.name = "Road_%d_%d_%s" % [int(c["chunk"][0]), int(c["chunk"][1]), String(c["layer"])]
		mi.mesh = m
		mi.material_override = road_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if String(c["layer"]) == "solid" else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		road_tris += t
		road_meshes += 1
	print("ROADS meshes=%d tris=%d" % [road_meshes, road_tris])


func _stone(origin: Vector3, face: Vector3, w: float, h: float, d: float, tilt := 0.0) -> void:
	# a stone whose front looks along `face` (horizontal), x along the wall, y up (battered back)
	var fwd := Vector3(face.x, 0, face.z).normalized()
	var right := Vector3.UP.cross(fwd).normalized()
	var up := (Vector3.UP + -fwd * tilt).normalized()
	var b := Basis(right * w * 0.5, up * h * 0.5, fwd * d * 0.5)
	b = b.rotated(fwd, rng.randf_range(-0.12, 0.12))
	per_shape[rng.randi() % SHAPES].append(Transform3D(b, origin))


func _wall(w: Dictionary) -> void:
	var pts: Array = w["points"]
	var nrm: Array = w["normals"]
	var top: Array = w["top"]
	var bot: Array = w["bottom"]
	var cut: Array = w["cut"]
	# walk along the wall in stone-width steps, laying courses from the foot to the top
	var total := 0.0
	for k in pts.size() - 1:
		total += Vector2(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]).length()
	var s := 0.0
	while s < total:
		# position at arc length s
		var a := 0.0
		var k := 0
		while k < pts.size() - 2:
			var seg := Vector2(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]).length()
			if a + seg >= s:
				break
			a += seg
			k += 1
		var seg2 := maxf(0.001, Vector2(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]).length())
		var t := clampf((s - a) / seg2, 0.0, 1.0)
		var p := Vector2(lerpf(pts[k][0], pts[k + 1][0], t), lerpf(pts[k][1], pts[k + 1][1], t))
		var n := Vector2(lerpf(nrm[k][0], nrm[k + 1][0], t), lerpf(nrm[k][1], nrm[k + 1][1], t)).normalized()
		var y0 := lerpf(bot[k], bot[k + 1], t)
		var y1 := lerpf(top[k], top[k + 1], t)
		var is_cut: bool = cut[k]
		var face := Vector3(n.x, 0, n.y) * (-1.0 if is_cut else 1.0)
		var sw := rng.randf_range(0.34, 0.58)
		var y := y0 - 0.12
		var course := 0
		while y < y1 - 0.06:
			var sh := minf(rng.randf_range(0.22, 0.34), y1 - y + 0.04)
			var batter := (y - y0) * 0.16
			var c := Vector3(p.x, y + sh * 0.5, p.y) - face * (batter + 0.1) + Vector3(n.x, 0, n.y) * (0.0 if is_cut else -0.05)
			c += Vector3(face.z, 0, -face.x) * ((0.5 if course % 2 == 1 else 0.0) * sw * 0.4)
			_stone(c, face, sw * rng.randf_range(0.85, 1.1), sh * 1.08, 0.42, 0.18)
			y += sh * 0.92
			course += 1
		s += sw * 0.88
