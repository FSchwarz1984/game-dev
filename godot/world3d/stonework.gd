class_name W3Stonework
extends Node3D
## The stonework people built where the land needed holding: dry-stone retaining walls (野面積み)
## along the yards that were cut into or built out from the slope, the shrine terrace's stone face
## and its steps. Walls come from the terrain generator's real pad edges (terrain.json "walls"),
## so they hold exactly the step the terrain has. Stones are small faceted rocks (W3Rocks shapes,
## flattened), stacked in irregular courses with a slight batter; MultiMesh per shape.

const SHAPES := 8

var terrain: Terrain3D
var mat := ShaderMaterial.new()
var per_shape := []
var rng := RandomNumberGenerator.new()


func build(t: Terrain3D, rocks: W3Rocks) -> void:
	terrain = t
	rng.seed = 2207
	mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("porosity", 0.55)
	mat.set_shader_parameter("tint", Color(1.04, 1.0, 0.94))
	var shapes: Array[ArrayMesh] = []
	for i in SHAPES:
		# wall stones are 6-10 px across: 80 triangles each is plenty (1,280 made the walls 1.7 M
		# triangles a frame)
		shapes.append(rocks.make_shape(5000 + i * 53, 0.62, 0.0, 0.0, 1))
		per_shape.append([])
	for w in terrain.info.get("walls", []):
		_wall(w)
	for st in terrain.info.get("steps", []):
		_steps(st)
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
	var acc := 0.0
	var i := 0
	var along := 0.0
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


func _steps(st: Dictionary) -> void:
	var a := Vector2(st["from"][0], st["from"][1])
	var b := Vector2(st["to"][0], st["to"][1])
	var ha := terrain.height_at(a.x, a.y)
	var hb := terrain.height_at(b.x, b.y)
	var n := int(st.get("count", 4))
	var dir := (b - a).normalized()
	var face := Vector3(-dir.x, 0, -dir.y)       # the risers look back down the steps
	var width := float(st["width"])
	for i in n:
		var t0 := float(i) / n
		var t1 := float(i + 1) / n
		var p := a.lerp(b, (t0 + t1) * 0.5)
		var y_top := lerpf(ha, hb, t1)
		var depth := (b - a).length() / n
		# each tread is two or three stones side by side
		var parts := 2 if i % 2 == 0 else 3
		for j in parts:
			var off := (float(j) + 0.5) / parts - 0.5
			var side := Vector3(face.z, 0, -face.x) * off * width
			var c := Vector3(p.x, y_top - 0.12, p.y) + side
			_stone(c, face, width / parts * 1.05, 0.3, depth * 1.15, 0.0)
