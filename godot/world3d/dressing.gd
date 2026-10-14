class_name W3Dressing
extends Node3D
## The renderer's own small dressing for the art sample, in the asset contract's style
## (toon_solid, vertex colours, procedural surface patterns, upright objects lean): stone lanterns
## at the shrine steps, a paper lantern on a post at the yard, bon lanterns by the nameless graves.
## Used where the asset catalog has no such asset yet. Every lantern carries a quantised point light
## that is lit at night (and dim at dusk).

var terrain: Terrain3D
var lights: Array[OmniLight3D] = []
var flames: Array = []      # [ShaderMaterial, base energy]
var stone := ShaderMaterial.new()
var wood := ShaderMaterial.new()
var paper := ShaderMaterial.new()


func _mat(params: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/toon_solid.gdshader")
	for k in params:
		m.set_shader_parameter(k, params[k])
	return m


func build(t: Terrain3D) -> void:
	terrain = t
	stone = _mat({"porosity": 0.5})
	wood = _mat({"porosity": 0.9})
	var st: Array = t.info.get("steps", [])
	if not st.is_empty():
		var s: Dictionary = st[0]
		var a := Vector2(s["from"][0], s["from"][1])
		var w := float(s["width"])
		stone_lantern(Vector3(a.x - w * 0.5 - 0.9, 0, a.y - 0.3))
		stone_lantern(Vector3(a.x + w * 0.5 + 0.9, 0, a.y - 0.3))
	var door := t.marker("hut_door")
	paper_lantern_post(door + Vector3(2.6, 0, 1.6))
	var g := t.marker("graves")
	for i in 3:
		bon_lantern(g + Vector3(-4.6 + i * 4.6, 0, 1.4))


func set_time(hours: float) -> void:
	var dusk := clampf((hours - 17.6) / 1.4, 0.0, 1.0) if hours > 12.0 else 0.0
	var dawn := clampf((5.8 - hours) / 1.0, 0.0, 1.0) if hours < 12.0 else 0.0
	var on := maxf(dusk, dawn)
	if hours >= 19.0 or hours <= 4.8:
		on = 1.0
	for l in lights:
		l.light_energy = l.get_meta("energy", 1.6) * on
		l.visible = on > 0.01
	for f in flames:
		(f[0] as ShaderMaterial).set_shader_parameter("emission_energy", float(f[1]) * (0.15 + 0.85 * on))


func _light(pos: Vector3, col: Color, energy: float, rng: float) -> void:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = col
	l.set_meta("energy", energy)
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.2
	l.shadow_enabled = false
	l.light_specular = 0.0
	add_child(l)
	lights.append(l)


# ------------------------------------------------------------------------------------------------
# small mesh builders (vertex-coloured, pattern ids in UV2)

func _prism(st: SurfaceTool, base: Vector3, r0: float, r1: float, h: float, sides: int, col: Color, pat: float, rot := 0.0) -> void:
	for i in sides:
		var a0 := rot + TAU * i / sides
		var a1 := rot + TAU * (i + 1) / sides
		var p0 := base + Vector3(cos(a0) * r0, 0, sin(a0) * r0)
		var p1 := base + Vector3(cos(a1) * r0, 0, sin(a1) * r0)
		var q0 := base + Vector3(cos(a0) * r1, h, sin(a0) * r1)
		var q1 := base + Vector3(cos(a1) * r1, h, sin(a1) * r1)
		var n := (p1 - p0).cross(q0 - p0).normalized() * -1.0
		_tri(st, p0, q0, q1, n, col, pat)
		_tri(st, p0, q1, p1, n, col, pat)
		# cap
		var c := base + Vector3(0, h, 0)
		_tri(st, c, q1, q0, Vector3.UP, col.lightened(0.04), pat)


func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, n: Vector3, col: Color, pat: float) -> void:
	var fn := (b - a).cross(c - a)
	if fn.length() < 1e-9:
		return
	fn = fn.normalized()
	if fn.dot(n) < 0.0:
		var t := b
		b = c
		c = t
		fn = -fn
	for p in [a, c, b]:
		st.set_normal(fn)
		st.set_color(col)
		st.set_uv2(Vector2(pat, 0.3))
		st.add_vertex(p)


func _mi(st: SurfaceTool, m: Material, pos: Vector3) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = m
	mi.position = pos
	add_child(mi)
	return mi


func stone_lantern(at: Vector3) -> void:
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var c := Color(0.55, 0.55, 0.52, 1.0)
	_prism(st, Vector3(0, 0, 0), 0.34, 0.3, 0.16, 6, c.darkened(0.08), 4.0)
	_prism(st, Vector3(0, 0.16, 0), 0.12, 0.11, 0.62, 8, c, 4.0)
	_prism(st, Vector3(0, 0.78, 0), 0.26, 0.24, 0.1, 6, c, 4.0)
	# fire box: four posts and an emissive window
	for i in 4:
		var a := TAU * i / 4.0 + PI / 4.0
		_prism(st, Vector3(cos(a) * 0.15, 0.88, sin(a) * 0.15), 0.04, 0.04, 0.26, 4, c, 4.0)
	_prism(st, Vector3(0, 1.14, 0), 0.42, 0.06, 0.22, 6, c.lightened(0.05), 4.0, 0.26)
	_prism(st, Vector3(0, 1.36, 0), 0.07, 0.0, 0.14, 6, c, 4.0)
	_mi(st, stone, pos)
	var fst := SurfaceTool.new()
	fst.begin(Mesh.PRIMITIVE_TRIANGLES)
	_prism(fst, Vector3(0, 0.9, 0), 0.12, 0.12, 0.2, 4, Color(1.0, 0.85, 0.6), 6.0, PI / 4.0)
	var fm := _mat({"emission_color": Color(1.0, 0.68, 0.32), "emission_energy": 2.6, "dither": 0.0})
	_mi(fst, fm, pos)
	flames.append([fm, 2.6])
	_light(pos + Vector3(0, 1.0, 0.25), Color(1.0, 0.66, 0.34), 1.7, 5.5)


func paper_lantern_post(at: Vector3) -> void:
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var w := Color(0.42, 0.32, 0.23, 1.0)
	_prism(st, Vector3(0, -0.2, 0), 0.07, 0.06, 2.3, 4, w, 2.0, PI / 4.0)
	# arm
	st.set_color(w)
	var arm_y := 2.0
	for k in 4:
		pass
	_prism(st, Vector3(0.0, arm_y, 0), 0.04, 0.04, 0.05, 4, w, 2.0)
	_mi(st, wood, pos)
	var ast := SurfaceTool.new()
	ast.begin(Mesh.PRIMITIVE_TRIANGLES)
	# the arm as a thin slanted prism toward +x
	var a0 := Vector3(0, arm_y, 0)
	var a1 := Vector3(0.55, arm_y + 0.05, 0)
	var off := [Vector3(0, 0.03, 0.03), Vector3(0, -0.03, 0.03), Vector3(0, -0.03, -0.03), Vector3(0, 0.03, -0.03)]
	for i in 4:
		var o0: Vector3 = off[i]
		var o1: Vector3 = off[(i + 1) % 4]
		var n := (o0 + o1).normalized()
		_tri(ast, a0 + o0, a1 + o0, a1 + o1, n, w, 2.0)
		_tri(ast, a0 + o0, a1 + o1, a0 + o1, n, w, 2.0)
	_mi(ast, wood, pos)
	# the lantern hanging from the arm
	var lst := SurfaceTool.new()
	lst.begin(Mesh.PRIMITIVE_TRIANGLES)
	var lp := Vector3(0.52, arm_y - 0.62, 0)
	_prism(lst, lp + Vector3(0, 0.0, 0), 0.13, 0.17, 0.2, 8, Color(0.95, 0.9, 0.8), 6.0)
	_prism(lst, lp + Vector3(0, 0.2, 0), 0.17, 0.13, 0.2, 8, Color(0.95, 0.9, 0.8), 6.0)
	var fm := _mat({"emission_color": Color(1.0, 0.78, 0.5), "emission_energy": 2.2, "dither": 0.0})
	_mi(lst, fm, pos)
	flames.append([fm, 2.2])
	var rst := SurfaceTool.new()
	rst.begin(Mesh.PRIMITIVE_TRIANGLES)
	_prism(rst, lp + Vector3(0, -0.04, 0), 0.11, 0.11, 0.05, 8, Color(0.12, 0.1, 0.09), 0.0)
	_prism(rst, lp + Vector3(0, 0.39, 0), 0.11, 0.11, 0.05, 8, Color(0.12, 0.1, 0.09), 0.0)
	_mi(rst, wood, pos)
	_light(pos + lp + Vector3(0, 0.2, 0.2), Color(1.0, 0.72, 0.42), 1.9, 6.5)


func bon_lantern(at: Vector3) -> void:
	# a small bon lantern on a bamboo stake before the graves (送り盆)
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_prism(st, Vector3(0, -0.1, 0), 0.025, 0.02, 1.15, 4, Color(0.55, 0.58, 0.32), 0.0)
	_mi(st, wood, pos)
	var lst := SurfaceTool.new()
	lst.begin(Mesh.PRIMITIVE_TRIANGLES)
	_prism(lst, Vector3(0, 0.78, 0), 0.08, 0.1, 0.12, 8, Color(0.96, 0.94, 0.88), 6.0)
	_prism(lst, Vector3(0, 0.9, 0), 0.1, 0.08, 0.12, 8, Color(0.96, 0.94, 0.88), 6.0)
	var fm := _mat({"emission_color": Color(1.0, 0.8, 0.55), "emission_energy": 1.9, "dither": 0.0})
	_mi(lst, fm, pos)
	flames.append([fm, 1.9])
	_light(pos + Vector3(0, 0.9, 0.15), Color(1.0, 0.74, 0.46), 1.1, 3.8)
