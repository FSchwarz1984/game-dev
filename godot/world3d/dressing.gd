class_name W3Dressing
extends Node3D
## The renderer's own small dressing for the art sample, in the asset contract's style
## (toon_solid, vertex colours, procedural surface patterns, upright objects lean): stone lanterns
## at the shrine steps, a paper lantern on a post at the yard, bon lanterns by the nameless graves.
## Used where the asset catalog has no such asset yet. Every lantern carries a quantised point light
## that is lit at night (and dim at dusk).

var terrain: Terrain3D
var lamps: W3Lamps                # the renderer's lamps (set by the assembly before build())
var _lit := -1                     # lamps on (1), off (0), not yet set (-1)
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


var glints: Array = []    # [position, phase] places that catch the light (the offering box's coins)
var asset_slots: Array = []   # [catalog name, position, yaw]: lights whose bodies the catalog provides
var has_asset := {}       # names of things the asset catalog already provides
var lean_k := 0.5206      # the camera's lean-back for upright things (tan(pitch / 2)), set by the sample


func build(t: Terrain3D, catalog := {}) -> void:
	terrain = t
	for k in catalog:
		has_asset[k] = true
	stone = _mat({"porosity": 0.5})
	wood = _mat({"porosity": 0.9})
	if not _catalog_has(catalog, ["woodpile", "maki"]):
		woodpile(t.marker("woodpile"))
	if not _catalog_has(catalog, ["fallen_branch", "branch"]):
		fallen_branch(t.marker("fallen_branch"))
	if not _catalog_has(catalog, ["offering_box", "saisen"]):
		offering_box(t.marker("offering_box"))
	if not _catalog_has(catalog, ["stump", "kirikabu"]):
		stump(t.marker("choppable_tree") + Vector3(1.3, 0, 0.7))
	if not _catalog_has(catalog, ["haka", "grave", "muenbo"]):
		graves(t)
	var st: Array = t.info.get("steps", [])
	if not st.is_empty():
		var s: Dictionary = st[0]
		var a := Vector2(s["from"][0], s["from"][1])
		var w := float(s["width"])
		for side in [-1.0, 1.0]:
			var lp := Vector3(a.x + side * (w * 0.5 + 0.9), 0, a.y - 0.3)
			if catalog.has("stone_lantern"):
				var gp := Vector3(lp.x, t.height_at(lp.x, lp.z), lp.z)
				asset_slots.append(["stone_lantern", gp, 0.0])
				_light(gp + Vector3(0, 1.0, 0.25), Color(1.0, 0.66, 0.34), 1.7, 5.5)
			else:
				stone_lantern(lp)
	var door := t.marker("hut_door")
	paper_lantern_post(door + Vector3(2.6, 0, 1.6), catalog.has("lantern_paper"))
	if not _catalog_has(catalog, ["graves", "grave", "haka"]):
		var g := t.marker("graves")
		for i in 3:
			bon_lantern(g + Vector3(-4.6 + i * 4.6, 0, 1.4))


func _catalog_has(catalog: Dictionary, keys: Array) -> bool:
	for name in catalog:
		for k in keys:
			if String(name).begins_with(k) or String(catalog[name].get("species", "")) == k:
				return true
	return false


func set_time(hours: float, instant := true) -> void:
	var dusk := clampf((hours - 17.6) / 1.4, 0.0, 1.0) if hours > 12.0 else 0.0
	var dawn := clampf((5.8 - hours) / 1.0, 0.0, 1.0) if hours < 12.0 else 0.0
	var on := maxf(dusk, dawn)
	if hours >= 19.0 or hours <= 4.8:
		on = 1.0
	# the lamps are lit at 18.4 h (and put out at dawn): one after another, each fading in
	var want := 1 if (hours >= 18.4 or hours <= 5.4) else 0
	if lamps and want != _lit:
		lamps.set_on(want == 1, instant or _lit < 0)
		_lit = want
	for f in flames:
		(f[0] as ShaderMaterial).set_shader_parameter("emission_energy", float(f[1]) * (0.15 + 0.85 * on))


## A lamp's light (the renderer lights it, render3d/lamps.gd). energy and reach are the old
## OmniLight numbers of this file; the renderer's lamps reach a little less and step their light.
func _light(pos: Vector3, col: Color, energy: float, rng: float) -> void:
	if lamps:
		lamps.add(pos, rng * 0.85, col, energy * 0.75)


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
	var c := Color(0.4, 0.39, 0.36, 1.0)
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


func paper_lantern_post(at: Vector3, asset_lantern := false) -> void:
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
	var lp := Vector3(0.52, arm_y - 0.62, 0)
	if asset_lantern:
		# the catalog's chochin hangs from the arm by its loop (origin at its bottom rim)
		asset_slots.append(["lantern_paper", pos + Vector3(0.52, arm_y - 0.58, 0), 0.0])
		_light(pos + lp + Vector3(0, 0.2, 0.2), Color(1.0, 0.72, 0.42), 1.9, 6.5)
		return
	var lst := SurfaceTool.new()
	lst.begin(Mesh.PRIMITIVE_TRIANGLES)
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


# ------------------------------------------------------------------------------------------------
# curiosity dressing: things near the path that ask to be looked at, picked up, used

func _box(st: SurfaceTool, c: Vector3, size: Vector3, col: Color, pat: float, basis := Basis()) -> void:
	var h := size * 0.5
	var faces := [[Vector3(0, 0, 1), Vector3(1, 0, 0), Vector3(0, 1, 0)], [Vector3(0, 0, -1), Vector3(-1, 0, 0), Vector3(0, 1, 0)],
		[Vector3(1, 0, 0), Vector3(0, 0, -1), Vector3(0, 1, 0)], [Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 0)],
		[Vector3(0, 1, 0), Vector3(1, 0, 0), Vector3(0, 0, -1)], [Vector3(0, -1, 0), Vector3(1, 0, 0), Vector3(0, 0, 1)]]
	for f in faces:
		var n: Vector3 = f[0]
		var u: Vector3 = f[1]
		var v: Vector3 = f[2]
		var o := n * h
		var uu := u * h
		var vv := v * h
		var a := basis * (o - uu - vv) + c
		var b := basis * (o + uu - vv) + c
		var cc := basis * (o + uu + vv) + c
		var d := basis * (o - uu + vv) + c
		var shade := col if n.y >= 0.0 else col.darkened(0.2)
		_tri(st, a, b, cc, basis * n, shade, pat)
		_tri(st, a, cc, d, basis * n, shade, pat)


func _log(st: SurfaceTool, c: Vector3, r: float, length: float, axis: Vector3, bark: Color, end: Color) -> void:
	# an eight-sided log; its ends show light end grain
	var ax := axis.normalized()
	var u := ax.cross(Vector3.UP)
	if u.length() < 0.1:
		u = ax.cross(Vector3.RIGHT)
	u = u.normalized()
	var v := ax.cross(u).normalized()
	var n := 8
	var a0 := c - ax * length * 0.5
	var a1 := c + ax * length * 0.5
	for i in n:
		var t0 := TAU * i / n + 0.2
		var t1 := TAU * (i + 1) / n + 0.2
		var d0 := u * cos(t0) * r + v * sin(t0) * r
		var d1 := u * cos(t1) * r + v * sin(t1) * r
		var nn := (d0 + d1).normalized()
		_tri(st, a0 + d0, a1 + d0, a1 + d1, nn, bark, 2.0)
		_tri(st, a0 + d0, a1 + d1, a0 + d1, nn, bark, 2.0)
		_tri(st, a1, a1 + d1, a1 + d0, ax, end, 0.0)
		_tri(st, a0, a0 + d0, a0 + d1, -ax, end, 0.0)


func woodpile(at: Vector3) -> void:
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 31
	var bark := Color(0.36, 0.28, 0.2, 1.0)
	var end := Color(0.78, 0.66, 0.46, 1.0)
	for row in 4:
		var count := 6 - (1 if row == 3 else 0)
		for k in count:
			var r := rng.randf_range(0.075, 0.1)
			var x := -0.55 + (k + (0.5 if row % 2 == 1 else 0.0)) * 0.2
			var y := 0.09 + row * 0.165
			var len := rng.randf_range(0.42, 0.5)
			_log(st, Vector3(x, y, rng.randf_range(-0.03, 0.03)), r, len, Vector3(rng.randf_range(-0.06, 0.06), 0, 1), bark.lightened(rng.randf_range(-0.05, 0.08)), end.darkened(rng.randf_range(0.0, 0.15)))
	# stakes holding the stack
	_box(st, Vector3(-0.72, 0.38, 0), Vector3(0.06, 0.82, 0.06), Color(0.4, 0.31, 0.22), 2.0)
	_box(st, Vector3(0.62, 0.38, 0), Vector3(0.06, 0.82, 0.06), Color(0.4, 0.31, 0.22), 2.0)
	_mi(st, wood, pos)
	# the chopping block with the hatchet in it, in front of the stack
	var cb := SurfaceTool.new()
	cb.begin(Mesh.PRIMITIVE_TRIANGLES)
	_log(cb, Vector3(0.35, 0.18, 0.85), 0.22, 0.36, Vector3.UP, Color(0.34, 0.27, 0.2), Color(0.66, 0.55, 0.38))
	_box(cb, Vector3(0.38, 0.5, 0.85), Vector3(0.05, 0.4, 0.05), Color(0.55, 0.42, 0.28), 1.0, Basis(Vector3(0, 0, 1), 0.5))
	_box(cb, Vector3(0.28, 0.4, 0.85), Vector3(0.16, 0.07, 0.03), Color(0.3, 0.31, 0.33), 0.0, Basis(Vector3(0, 0, 1), 0.5))
	_mi(cb, wood, pos)
	for k in 5:
		# split pieces and chips scattered on the ground
		var ch := SurfaceTool.new()
		ch.begin(Mesh.PRIMITIVE_TRIANGLES)
		_box(ch, Vector3(rng.randf_range(-0.2, 0.9), 0.02, rng.randf_range(0.6, 1.3)), Vector3(0.12, 0.03, 0.05), end.darkened(0.1), 0.0, Basis(Vector3.UP, rng.randf() * TAU))
		var mi := _mi(ch, _mat({"lean": 0.0}), pos)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func fallen_branch(at: Vector3) -> void:
	# a camphor branch broken off in the wind, lying across the edge of the path
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bark := Color(0.32, 0.26, 0.2, 1.0)
	var pts := [Vector3(-1.1, 0.07, -0.35), Vector3(-0.4, 0.08, -0.1), Vector3(0.3, 0.06, 0.1), Vector3(1.0, 0.05, 0.42)]
	var radii := [0.075, 0.06, 0.045, 0.03]
	for i in pts.size() - 1:
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		_log(st, (a + b) * 0.5, (radii[i] + radii[i + 1]) * 0.5, a.distance_to(b) + 0.04, b - a, bark, Color(0.62, 0.5, 0.34))
	var twigs := [[Vector3(-0.4, 0.08, -0.1), Vector3(-0.2, 0.06, -0.55)], [Vector3(0.3, 0.06, 0.1), Vector3(0.55, 0.05, -0.25)], [Vector3(0.6, 0.05, 0.25), Vector3(0.85, 0.04, 0.7)]]
	for tw in twigs:
		var a: Vector3 = tw[0]
		var b: Vector3 = tw[1]
		_log(st, (a + b) * 0.5, 0.018, a.distance_to(b), b - a, bark, bark)
	var mi := _mi(st, _mat({"lean": 0.0, "porosity": 0.9}), pos)
	# its leaves, still green-brown: a few cards in the foliage style
	var lv := SurfaceTool.new()
	lv.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for k in 9:
		var c: Vector3 = pts[1 + k % 3].lerp(twigs[k % 3][1], rng.randf_range(0.3, 1.0)) + Vector3(rng.randf_range(-0.15, 0.15), 0.06, rng.randf_range(-0.12, 0.12))
		var col := Color(0.36, 0.4, 0.2).lerp(Color(0.5, 0.38, 0.2), rng.randf())
		_box(lv, c, Vector3(0.16, 0.025, 0.1), col, 0.0, Basis(Vector3.UP, rng.randf() * TAU))
	var ml := _mi(lv, _mat({"lean": 0.0, "porosity": 0.6}), pos)
	ml.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func offering_box(at: Vector3) -> void:
	# 賽銭箱 before the shrine: a dark wooden box with a slatted top; coins inside catch the light
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var w := Color(0.32, 0.22, 0.16, 1.0)
	_box(st, Vector3(0, 0.2, 0), Vector3(0.62, 0.36, 0.4), w, 1.0)
	for k in 5:
		_box(st, Vector3(-0.24 + k * 0.12, 0.4, 0), Vector3(0.05, 0.04, 0.42), w.lightened(0.12), 1.0, Basis(Vector3.RIGHT, 0.35))
	_box(st, Vector3(0, 0.03, 0), Vector3(0.7, 0.06, 0.46), w.darkened(0.15), 1.0)
	_mi(st, _mat({"porosity": 0.6}), pos)
	glints.append([pos + Vector3(0.05, 0.42, -0.42 * lean_k), 0.0])


func stump(at: Vector3) -> void:
	# an old stump beside the young tree that could be felled: someone cut here before
	var pos := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_log(st, Vector3(0, 0.15, 0), 0.26, 0.4, Vector3.UP, Color(0.33, 0.26, 0.2), Color(0.6, 0.5, 0.36))
	_mi(st, wood, pos)


func graves(t: Terrain3D) -> void:
	# nine nameless graves (無縁墓): weathered stones of mixed shapes in a row on their bench
	var pads: Array = t.info.get("pads", [])
	var centre := t.marker("graves")
	var ang := 0.0
	for p in pads:
		if p["id"] == "graves_bench":
			ang = deg_to_rad(float(p.get("angle", 0.0)))
	var rng := RandomNumberGenerator.new()
	rng.seed = 909
	for i in 9:
		var off := Vector3(-4.6 + i * 1.15 + rng.randf_range(-0.12, 0.12), 0, rng.randf_range(-0.2, 0.15)).rotated(Vector3.UP, -ang)
		var p := centre + off
		p.y = t.height_at(p.x, p.z)
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var h := rng.randf_range(0.55, 0.9)
		var wdt := rng.randf_range(0.32, 0.44)
		var col := Color(0.6, 0.59, 0.55).darkened(rng.randf_range(0.0, 0.16))
		col.a = 1.0
		var tilt := Basis(Vector3(0, 0, 1), rng.randf_range(-0.12, 0.12)) * Basis(Vector3(1, 0, 0), rng.randf_range(-0.08, 0.05))
		if i % 3 == 1:
			# a natural stone, rounded
			_prism(st, Vector3(0, 0, 0), wdt * 0.9, wdt * 0.55, h * 0.75, 7, col, 4.0, rng.randf())
		else:
			_box(st, Vector3(0, h * 0.5, 0), Vector3(wdt, h, wdt * 0.72), col, 4.0, tilt)
			# a rounded cap (old stones lose their edges)
			_box(st, Vector3(0, h + 0.035, 0), Vector3(wdt * 0.8, 0.07, wdt * 0.58), col.lightened(0.05), 4.0, tilt)
		# a little base stone
		_box(st, Vector3(0, 0.04, 0.02), Vector3(wdt * 1.5, 0.1, wdt * 1.1), col.darkened(0.12), 4.0)
		var mi := _mi(st, _mat({"porosity": 0.5}), p)
		mi.rotation.y = ang
		# a cup of water before every third stone
		if i % 3 == 0:
			var cup := SurfaceTool.new()
			cup.begin(Mesh.PRIMITIVE_TRIANGLES)
			_prism(cup, Vector3(0, 0, 0.32), 0.05, 0.06, 0.07, 6, Color(0.82, 0.8, 0.74), 0.0)
			var mc := _mi(cup, _mat({}), p)
			mc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
