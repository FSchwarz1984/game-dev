class_name W3Vista
extends Node
## The view from the lookout (眺望岩 of the sample): her eye's perspective out over the land around the
## pass, in the pixel-art language of the top-down world (native resolution, nearest upscale at the
## stage's integer scale, toon bands and the painted shade, palette, dithered aerial perspective,
## bloom only on lights). It has its own World3D:
##   * the land: the region's real heights and ground materials near, and around it the land of the
##     approved map (tools/world3d/w3terrain/vista.py): the summit with the 「隔」 tower to the north,
##     the kiln on the east shoulder, the 裏見之瀑 in the west ravine, the lookout's ravine running
##     down into the canyon, the lower layer to the south (溜池, the terraces and the water-wheel
##     farm, the hot-spring valley) and the old road going down into the 遠化 mist that rings the
##     region; the plain lies beyond it, faint, mountains on the horizon;
##   * trees as impostors drawn for this camera (the region's placements and the woods around);
##   * the great camphor as a mass, the lookout's rocks, the kiln, the farm, the tower's red light;
##   * smoke from the kiln, steam from the hot spring, the waterfall and its mist;
##   * sky, sun, moon, stars and clouds (vista_sky.gdshader).
## She looks out when she stands still on the lookout; A/D (or the arrows) turn her head, any other
## movement key brings the top-down view back. The view dissolves in and out in native pixels.

const DATA := "res://world3d/terrain/saddle/vista.json"
const EYE_H := 1.45
const FOV := 40.0                     # vertical, degrees: a fairly long lens, the land in layers

# hour, zenith, horizon, mist, cloud lit, cloud shade (sRGB)
const SKY_KEYS := [
	[0.0, Color(0.03, 0.04, 0.09), Color(0.09, 0.11, 0.19), Color(0.15, 0.17, 0.25), Color(0.22, 0.24, 0.33), Color(0.06, 0.07, 0.12)],
	[4.6, Color(0.03, 0.04, 0.09), Color(0.09, 0.11, 0.19), Color(0.15, 0.17, 0.25), Color(0.22, 0.24, 0.33), Color(0.06, 0.07, 0.12)],
	[5.6, Color(0.2, 0.22, 0.4), Color(0.86, 0.58, 0.5), Color(0.78, 0.64, 0.66), Color(1.0, 0.76, 0.64), Color(0.42, 0.38, 0.5)],
	[7.0, Color(0.36, 0.52, 0.76), Color(0.88, 0.84, 0.76), Color(0.9, 0.88, 0.85), Color(1.0, 0.96, 0.88), Color(0.6, 0.64, 0.74)],
	[12.0, Color(0.32, 0.5, 0.78), Color(0.73, 0.8, 0.86), Color(0.86, 0.88, 0.9), Color(1.0, 1.0, 0.97), Color(0.64, 0.7, 0.8)],
	[16.0, Color(0.33, 0.48, 0.74), Color(0.8, 0.8, 0.79), Color(0.88, 0.86, 0.84), Color(1.0, 0.96, 0.88), Color(0.62, 0.64, 0.74)],
	[17.6, Color(0.28, 0.34, 0.58), Color(0.98, 0.7, 0.46), Color(0.95, 0.79, 0.66), Color(1.0, 0.8, 0.6), Color(0.54, 0.44, 0.54)],
	[18.6, Color(0.14, 0.15, 0.33), Color(0.74, 0.42, 0.4), Color(0.58, 0.45, 0.51), Color(0.88, 0.54, 0.5), Color(0.28, 0.23, 0.36)],
	[19.6, Color(0.03, 0.04, 0.09), Color(0.09, 0.11, 0.19), Color(0.15, 0.17, 0.25), Color(0.22, 0.24, 0.33), Color(0.06, 0.07, 0.12)],
	[24.0, Color(0.03, 0.04, 0.09), Color(0.09, 0.11, 0.19), Color(0.15, 0.17, 0.25), Color(0.22, 0.24, 0.33), Color(0.06, 0.07, 0.12)],
]

var pv: PixelView3D
var env: W3Env
var terrain: Terrain3D
var data := {}
var vp: SubViewport
var cam: Camera3D
var sun: DirectionalLight3D
var world_env: WorldEnvironment
var environment: Environment
var sky_mat := ShaderMaterial.new()
var view: TextureRect
var display := ShaderMaterial.new()
var root: Node3D
var built := false
var eye := Vector3.ZERO
var yaw := 165.0                      # bearing, degrees clockwise from north
var yaw_target := 165.0
var amount := 0.0                     # 0 hidden .. 1 shown
var active := false                   # wants to be shown
var mats: Array[ShaderMaterial] = []  # materials that need the eye and the air colours
var puffs: Array = []                 # [pos, vel, life, age, size, kind, seed, colour, glow]
var puff_mm := MultiMesh.new()
var puff_src: Array = []              # [pos, rate, kind, acc]
var red_light: MeshInstance3D
var red_mat: ShaderMaterial
var kiln_glow: ShaderMaterial
var rng := RandomNumberGenerator.new()
var _t := 0.0


func setup(p: PixelView3D, e: W3Env, t: Terrain3D) -> void:
	pv = p
	env = e
	terrain = t
	rng.seed = 77
	var f := FileAccess.open(DATA, FileAccess.READ)
	if f:
		data = JSON.parse_string(f.get_as_text())
	vp = SubViewport.new()
	vp.name = "VistaViewport"
	vp.own_world_3d = true
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.use_taa = false
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.gui_disable_input = true
	vp.positional_shadow_atlas_size = 0
	add_child(vp)
	root = Node3D.new()
	root.name = "Land"
	vp.add_child(root)
	cam = Camera3D.new()
	cam.fov = FOV
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.near = 0.25
	cam.far = 30000.0
	cam.current = true
	vp.add_child(cam)
	# outlines: one full-screen quad drawn first in the transparent pass
	var q := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(2, 2)
	q.mesh = qm
	q.extra_cull_margin = 16384.0
	q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pm := ShaderMaterial.new()
	pm.shader = load("res://render3d/shaders/vista_post.gdshader")
	pm.render_priority = -100
	q.material_override = pm
	q.position = Vector3(0, 0, -1)
	cam.add_child(q)
	sun = DirectionalLight3D.new()
	sun.shadow_enabled = false
	sun.light_specular = 0.0
	vp.add_child(sun)
	environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat.shader = load("res://render3d/shaders/vista_sky.gdshader")
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	sky.process_mode = Sky.PROCESS_MODE_AUTOMATIC
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment.glow_enabled = true
	environment.glow_normalized = false
	environment.glow_intensity = 0.9
	environment.glow_strength = 1.0
	environment.glow_bloom = 0.0
	environment.glow_hdr_threshold = 1.0
	environment.glow_hdr_scale = 2.0
	environment.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	environment.set_glow_level(0, 0.0)
	environment.set_glow_level(1, 1.0)
	environment.set_glow_level(2, 0.6)
	environment.set_glow_level(3, 0.3)
	world_env = WorldEnvironment.new()
	world_env.environment = environment
	vp.add_child(world_env)
	view = TextureRect.new()
	view.name = "VistaView"
	view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view.stretch_mode = TextureRect.STRETCH_SCALE
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	display.shader = load("res://render3d/shaders/vista_display.gdshader")
	view.material = display
	view.visible = false
	pv.add_child(view)
	view.texture = vp.get_texture()
	pv.logical_resized.connect(_fit)
	_fit(pv.logical)
	var lk: Vector3 = terrain.marker("lookout")
	feet = Vector3(lk.x, terrain.height_at(lk.x, lk.z), lk.z)
	eye = cam_pos()


func _fit(size: Vector2) -> void:
	vp.size = Vector2i(size)
	view.position = Vector2.ZERO
	view.size = size


## Build the land (once; about a second). Done on the first look, or up front for recordings.
func build() -> void:
	if built:
		return
	built = true
	var t0 := Time.get_ticks_msec()
	_build_land()
	_build_mist()
	_build_trees()
	_build_camphor()
	_build_rocks()
	_build_landmarks()
	_build_figures()
	_build_puffs()
	print("VISTA built ms=", Time.get_ticks_msec() - t0)


func _common(m: ShaderMaterial) -> void:
	var dir := "res://world3d/terrain/saddle/"
	var md: Dictionary = data["mid"]
	var fd: Dictionary = data["far"]
	m.set_shader_parameter("mid_tex", _tex(dir + String(md["file"])))
	m.set_shader_parameter("mat_tex", _tex(dir + String(md["mat"])))
	m.set_shader_parameter("far_tex", _tex(dir + String(fd["file"])))
	m.set_shader_parameter("mid_frame", Vector4(md["x0"], md["z0"], md["cell"], md["nx"]))
	m.set_shader_parameter("mid_h", Vector2(md["hmin"], md["hrange"]))
	m.set_shader_parameter("far_frame", Vector4(fd["x0"], fd["z0"], fd["cell"], fd["nx"]))
	m.set_shader_parameter("far_h", Vector2(fd["hmin"], fd["hrange"]))
	var me: Dictionary = data["mist"]
	m.set_shader_parameter("mist_ellipse", Vector4(me["cx"], me["cz"], me["rx"], me["rz"]))
	m.set_shader_parameter("eye", eye)
	mats.append(m)


var _tex_cache := {}


func _tex(path: String) -> ImageTexture:
	if not _tex_cache.has(path):
		var im: Image = load(path)
		_tex_cache[path] = ImageTexture.create_from_image(im)
	return _tex_cache[path]


func _mat(shader: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/%s.gdshader" % shader)
	_common(m)
	return m


# ------------------------------------------------------------------------------------------------
# the land: a radial grid around the eye, lifted in the vertex shader

func _build_land() -> void:
	var mat := _mat("vista_ground")
	var tm: ShaderMaterial = terrain.terrain_mat
	for k in ["m0", "m1", "palette"]:
		mat.set_shader_parameter(k, tm.get_shader_parameter(k))
	var sp: Dictionary = terrain.info["splat"]
	mat.set_shader_parameter("splat_frame", Vector4(terrain.origin.x, terrain.origin.y, float(sp["cell"]), 0.0))
	mat.set_shader_parameter("splat_size", Vector2(sp["size"][0], sp["size"][1]))
	var o := terrain.origin
	mat.set_shader_parameter("local_bounds", Vector4(o.x, o.y, o.x + (terrain.nx - 1) * terrain.cell, o.y + (terrain.nz - 1) * terrain.cell))
	var rings := PackedFloat32Array()
	var r := 0.6
	while r < 15000.0:
		rings.append(r)
		r += maxf(0.45, r * 0.034)
	var segs := 512
	var sectors := 16
	var per := segs / sectors
	for s in sectors:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var cols := per + 1
		for ri in rings.size():
			for c in cols:
				var a := TAU * float(s * per + c) / float(segs)
				st.add_vertex(Vector3(eye.x + sin(a) * rings[ri], 0.0, eye.z - cos(a) * rings[ri]))
		for ri in rings.size() - 1:
			for c in per:
				var i0 := ri * cols + c
				var i1 := i0 + 1
				var j0 := i0 + cols
				var j1 := j0 + 1
				# clockwise seen from above (Godot's front faces)
				st.add_index(i0); st.add_index(j0); st.add_index(i1)
				st.add_index(i1); st.add_index(j0); st.add_index(j1)
		var mesh := st.commit()
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
		root.add_child(mi)
	# a centre cap under her feet
	var cap := SurfaceTool.new()
	cap.begin(Mesh.PRIMITIVE_TRIANGLES)
	for c in segs:
		var a0 := TAU * float(c) / float(segs)
		var a1 := TAU * float(c + 1) / float(segs)
		cap.add_vertex(Vector3(eye.x, 0, eye.z))
		cap.add_vertex(Vector3(eye.x + sin(a0) * rings[0], 0, eye.z - cos(a0) * rings[0]))
		cap.add_vertex(Vector3(eye.x + sin(a1) * rings[0], 0, eye.z - cos(a1) * rings[0]))
	var cmi := MeshInstance3D.new()
	cmi.mesh = cap.commit()
	cmi.material_override = mat
	cmi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(cmi)


# ------------------------------------------------------------------------------------------------
# heights on the CPU (the same maps the shaders read)

var _mid_img: Image
var _far_img: Image


func land_h(x: float, z: float) -> float:
	if _mid_img == null:
		_mid_img = load("res://world3d/terrain/saddle/" + String(data["mid"]["file"]))
		_far_img = load("res://world3d/terrain/saddle/" + String(data["far"]["file"]))
	var md: Dictionary = data["mid"]
	var i := roundi((x - float(md["x0"])) / float(md["cell"]))
	var j := roundi((z - float(md["z0"])) / float(md["cell"]))
	var n := int(md["nx"])
	if i >= 0 and j >= 0 and i < n and j < n:
		var c := _mid_img.get_pixel(i, j)
		return float(md["hmin"]) + (roundf(c.r * 255.0) * 256.0 + roundf(c.g * 255.0)) / 65535.0 * float(md["hrange"])
	var fd: Dictionary = data["far"]
	var fi := clampi(roundi((x - float(fd["x0"])) / float(fd["cell"])), 0, int(fd["nx"]) - 1)
	var fj := clampi(roundi((z - float(fd["z0"])) / float(fd["cell"])), 0, int(fd["nx"]) - 1)
	var cf := _far_img.get_pixel(fi, fj)
	return float(fd["hmin"]) + (roundf(cf.r * 255.0) * 256.0 + roundf(cf.g * 255.0)) / 65535.0 * float(fd["hrange"])


# ------------------------------------------------------------------------------------------------
# the 遠化 mist: a curtain on the ellipse that rings the region

var mist_mat: ShaderMaterial
var sea_mat: ShaderMaterial
const SEA_Y := -150.0


func _build_mist() -> void:
	var me: Dictionary = data["mist"]
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 384
	var e := 1.12
	var pts: Array = []
	for i in n + 1:
		var a := TAU * float(i) / float(n)
		var x := float(me["cx"]) + sin(a) * float(me["rx"]) * e
		var z := float(me["cz"]) - cos(a) * float(me["rz"]) * e
		var g := land_h(x, z)
		pts.append([Vector3(x, g - 30.0, z), g + 34.0])
	for i in n:
		var p0: Vector3 = pts[i][0]
		var p1: Vector3 = pts[i + 1][0]
		var t0: float = pts[i][1]
		var t1: float = pts[i + 1][1]
		var u0 := float(i) / float(n)
		var u1 := float(i + 1) / float(n)
		var a0 := Vector3(p0.x, t0, p0.z)
		var a1 := Vector3(p1.x, t1, p1.z)
		for v in [[a0, Vector2(u0, 0)], [a1, Vector2(u1, 0)], [p1, Vector2(u1, 1)], [a0, Vector2(u0, 0)], [p1, Vector2(u1, 1)], [p0, Vector2(u0, 1)]]:
			st.set_uv(v[1])
			st.add_vertex(v[0])
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mist_mat = _mat("vista_mist")
	mist_mat.render_priority = 1
	mi.material_override = mist_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)
	# the sea of mist over the lowland beyond the ellipse
	var sea := SurfaceTool.new()
	sea.begin(Mesh.PRIMITIVE_TRIANGLES)
	var segs := 256
	var scales := PackedFloat32Array()
	var sc := 0.98
	while sc * minf(float(me["rx"]), float(me["rz"])) < 16000.0:
		scales.append(sc)
		sc *= 1.06
	for ri in scales.size() - 1:
		for c in segs:
			var a0 := TAU * float(c) / float(segs)
			var a1 := TAU * float(c + 1) / float(segs)
			var q := []
			for v in [[a0, scales[ri]], [a1, scales[ri]], [a1, scales[ri + 1]], [a0, scales[ri + 1]]]:
				q.append(Vector3(float(me["cx"]) + sin(v[0]) * float(me["rx"]) * v[1], SEA_Y, float(me["cz"]) - cos(v[0]) * float(me["rz"]) * v[1]))
			for idx in [0, 2, 1, 0, 3, 2]:
				sea.add_vertex(q[idx])
	var smi := MeshInstance3D.new()
	smi.mesh = sea.commit()
	sea_mat = _mat("vista_sea")
	smi.material_override = sea_mat
	smi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	smi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(smi)


# ------------------------------------------------------------------------------------------------
# impostors

var _tree_rows: Array = []


func _tree(x: float, y: float, z: float, kind: int, h: float, w: float, seed: float) -> void:
	_tree_rows.append([x, y, z, kind, h, w, seed])


func _build_trees() -> void:
	# the region's own trees (the same placements as the walkable world)
	for p in terrain.info["placements"]:
		var kind: String = p["kind"]
		var x: float = p["x"]
		var z: float = p["z"]
		var d := Vector2(x - eye.x, z - eye.z).length()
		if d < 22.0:
			continue
		var y := terrain.height_at(x, z)
		var sc := float(p.get("scale", 1.0))
		var v := int(p.get("variant", 0))
		var seed := fposmod(v * 0.137 + x * 0.013, 1.0)
		match kind:
			"cedar":
				var cedar_h: Array[float] = [22.0, 17.0, 12.0, 26.0, 9.0]
				var h: float = cedar_h[v % 5] * sc
				_tree(x, y, z, 0, h, h * 0.3, seed)
			"choppable":
				_tree(x, y, z, 0, 5.6, 1.8, seed)
			"pine":
				var pine_h: Array[float] = [13.0, 10.0, 15.0, 8.0]
				var h2: float = pine_h[v % 4] * sc
				_tree(x, y, z, 1, h2, h2 * 0.95, seed)
			"maple":
				_tree(x, y, z, 4 if v % 4 == 3 else 2, 6.5 * sc, 6.0 * sc, seed)
			"beech", "broadleaf":
				_tree(x, y, z, 2, 8.0 * sc, 7.0 * sc, seed)
			"persimmon":
				_tree(x, y, z, 7, 7.5, 7.0, seed)
			"bamboo":
				_tree(x, y, z, 3, 9.0 * sc, 4.0 * sc, seed)
	# the woods around the region
	for t in data.get("trees", []):
		var kind: int = int(t[3])
		var h3: float = t[4]
		var ratio: Array[float] = [0.3, 0.95, 0.85, 0.45, 0.9]
		var w: float = h3 * ratio[kind]
		_tree(t[0], t[1], t[2], kind, h3, w, float(t[5]) / 1000.0)
	var lm: Dictionary = data["landmarks"]
	for hs in lm.get("houses", []):
		_tree(hs[0], hs[1], hs[2], 5, 5.5, 8.5, 0.3)
	var hs0: Array = lm["houses"][0]
	_tree(hs0[0] + 5.0, hs0[1], hs0[2] + 2.0, 8, 3.4, 3.4, 0.5)
	var tw: Array = lm["tower"]
	_tree(tw[0], tw[1], tw[2], 6, 34.0, 8.0, 0.5)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	mm.mesh = q
	mm.instance_count = _tree_rows.size()
	for i in _tree_rows.size():
		var r: Array = _tree_rows[i]
		mm.set_instance_transform(i, Transform3D(Basis(), Vector3(r[0], r[1], r[2])))
		mm.set_instance_custom_data(i, Color(float(r[3]), r[4], r[5], r[6]))
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = mm
	mi.material_override = _mat("vista_tree")
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)
	print("VISTA trees=", _tree_rows.size())


# ------------------------------------------------------------------------------------------------
# the great camphor as a mass (its crown from the asset catalog's numbers)

func _lump(st: SurfaceTool, c: Vector3, r: Vector3, col: Color, seed: int) -> void:
	var sph := SphereMesh.new()
	sph.radial_segments = 14
	sph.rings = 8
	var arr := sph.get_mesh_arrays()
	var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var idx: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
	var noise := FastNoiseLite.new()
	noise.seed = seed
	noise.frequency = 1.3
	var pts := PackedVector3Array()
	pts.resize(v.size())
	for i in v.size():
		var d := (v[i] * 2.0)
		var k := 1.0 + noise.get_noise_3dv(d * 1.5) * 0.22
		pts[i] = c + Vector3(d.x * r.x, d.y * r.y, d.z * r.z) * k
	for t in range(0, idx.size(), 3):
		var a := pts[idx[t]]
		var b := pts[idx[t + 1]]
		var cc := pts[idx[t + 2]]
		var n := (b - a).cross(cc - a)
		if n.length() < 1e-6:
			continue
		n = n.normalized()
		if n.dot((a + b + cc) / 3.0 - c) < 0.0:
			n = -n
			var tmp := b
			b = cc
			cc = tmp
		for p in [a, cc, b]:
			var up := clampf(((p as Vector3).y - c.y) / r.y * 0.5 + 0.5, 0.0, 1.0)
			st.set_color(col.lerp(col.lightened(0.12), up))
			st.set_normal(((p as Vector3) - c).normalized())
			st.add_vertex(p)


func _build_camphor() -> void:
	var at := terrain.marker("camphor")
	var base := Vector3(at.x, terrain.height_at(at.x, at.z), at.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var r := RandomNumberGenerator.new()
	r.seed = 1717
	var col := Color(0.29, 0.38, 0.2)
	for i in 16:
		var a := r.randf() * TAU
		var rr := sqrt(r.randf()) * 11.5
		var c := base + Vector3(cos(a) * rr, 12.5 + r.randf_range(-1.5, 3.5) + (11.5 - rr) * 0.35, sin(a) * rr + 0.5)
		var s := r.randf_range(4.2, 6.8)
		_lump(st, c, Vector3(s, s * 0.62, s), col.darkened(r.randf_range(0.0, 0.12)), 300 + i)
	var crown := MeshInstance3D.new()
	crown.mesh = st.commit()
	var m := _mat("vista_solid")
	m.set_shader_parameter("leafy", 1.0)
	m.set_shader_parameter("clump_m", 1.3)
	crown.material_override = m
	root.add_child(crown)
	# trunk and the big low limbs
	var tr := SurfaceTool.new()
	tr.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bark := Color(0.3, 0.25, 0.2)
	_tube(tr, base + Vector3(0, -0.5, 0), base + Vector3(0.3, 10.0, 0.2), 3.3, 1.7, bark)
	for i in 5:
		var a := TAU * i / 5.0 + 0.4
		var from := base + Vector3(0, 6.5 + i * 0.6, 0)
		var to := base + Vector3(cos(a) * 10.0, 10.5 + (i % 2) * 2.0, sin(a) * 10.0)
		_tube(tr, from, to, 1.0, 0.45, bark)
	var trunk := MeshInstance3D.new()
	trunk.mesh = tr.commit()
	trunk.material_override = _mat("vista_solid")
	root.add_child(trunk)


func _tube(st: SurfaceTool, a: Vector3, b: Vector3, r0: float, r1: float, col: Color) -> void:
	var ax := (b - a).normalized()
	var u := ax.cross(Vector3.FORWARD if absf(ax.dot(Vector3.FORWARD)) < 0.9 else Vector3.RIGHT).normalized()
	var v := ax.cross(u).normalized()
	var n := 10
	for i in n:
		var t0 := TAU * i / n
		var t1 := TAU * (i + 1) / n
		var d0 := u * cos(t0) + v * sin(t0)
		var d1 := u * cos(t1) + v * sin(t1)
		var p0 := a + d0 * r0
		var p1 := a + d1 * r0
		var q0 := b + d0 * r1
		var q1 := b + d1 * r1
		for tri in [[p0, q0, q1, d0, d0, d1], [p0, q1, p1, d0, d1, d1]]:
			# outward faces, clockwise for Godot
			var x0: Vector3 = tri[0]
			var x1: Vector3 = tri[1]
			var x2: Vector3 = tri[2]
			var fn := (x1 - x0).cross(x2 - x0)
			var nn: Vector3 = tri[3]
			if fn.dot(nn) > 0.0:
				var tmp := x1
				x1 = x2
				x2 = tmp
			for p in [x0, x1, x2]:
				st.set_color(col)
				st.set_normal(((p as Vector3) - a - ax * ax.dot((p as Vector3) - a)).normalized())
				st.add_vertex(p)


# ------------------------------------------------------------------------------------------------
# the rocks of the lookout (the region's own rock shapes, now seen from her eye)

func _build_rocks() -> void:
	var rocks := W3Rocks.new()
	rocks.terrain = terrain
	var shapes := {}
	var m := _mat("vista_solid")
	for p in terrain.info["placements"]:
		var kind: String = p["kind"]
		if kind != "boulder" and kind != "outcrop" and kind != "rock_slab":
			continue
		if Vector2(float(p["x"]) - eye.x, float(p["z"]) - eye.z).length() > 45.0:
			continue
		var v := int(p.get("variant", 0)) % W3Rocks.VARIANTS
		if kind == "outcrop":
			v = (int(p.get("variant", 0)) * 3 + 5) % W3Rocks.VARIANTS
		if not shapes.has(v):
			shapes[v] = rocks.make_shape(1000 + v * 37, 0.55 + 0.25 * fposmod(v * 0.37, 1.0), (0.22 if v % 3 == 0 else 0.0))
		var mi := MeshInstance3D.new()
		mi.mesh = shapes[v]
		mi.material_override = m
		mi.transform = rocks._rock_xform(p)
		root.add_child(mi)
	rocks.free()


# ------------------------------------------------------------------------------------------------
# landmarks: the kiln, the tower's red light, the waterfall

func _build_landmarks() -> void:
	var lm: Dictionary = data["landmarks"]
	# the kiln on the east shoulder: a low hut over the kiln, a chimney
	var kl := terrain.marker("kiln")
	var ky := terrain.height_at(kl.x, kl.z)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_box(st, Vector3(kl.x, ky + 1.0, kl.z), Vector3(4.0, 2.0, 3.2), Color(0.42, 0.36, 0.3))
	_box(st, Vector3(kl.x, ky + 2.3, kl.z), Vector3(4.8, 0.6, 4.0), Color(0.36, 0.3, 0.24))
	_box(st, Vector3(kl.x + 1.4, ky + 2.8, kl.z - 0.8), Vector3(0.5, 2.2, 0.5), Color(0.5, 0.42, 0.36))
	var kmi := MeshInstance3D.new()
	kmi.mesh = st.commit()
	kmi.material_override = _mat("vista_solid")
	root.add_child(kmi)
	# the kiln's mouth glows at night
	var gst := SurfaceTool.new()
	gst.begin(Mesh.PRIMITIVE_TRIANGLES)
	_box(gst, Vector3(kl.x, ky + 0.5, kl.z + 1.62), Vector3(1.0, 0.8, 0.05), Color(0.9, 0.4, 0.15))
	var gmi := MeshInstance3D.new()
	gmi.mesh = gst.commit()
	kiln_glow = _mat("vista_solid")
	kiln_glow.set_shader_parameter("emission_col", Color(1.0, 0.45, 0.15))
	gmi.material_override = kiln_glow
	root.add_child(gmi)
	puff_src.append([Vector3(kl.x + 1.4, ky + 4.0, kl.z - 0.8), 0.9, 0, 0.0])
	# the tower's red light
	var tw: Array = lm["tower"]
	var lst := SurfaceTool.new()
	lst.begin(Mesh.PRIMITIVE_TRIANGLES)
	_box(lst, Vector3(tw[0], float(tw[1]) + 34.4, tw[2]), Vector3(1.4, 1.4, 1.4), Color(1, 0.2, 0.15))
	red_light = MeshInstance3D.new()
	red_light.mesh = lst.commit()
	red_mat = _mat("vista_solid")
	red_mat.set_shader_parameter("emission_col", Color(1.0, 0.18, 0.12))
	red_light.material_override = red_mat
	root.add_child(red_light)
	# the waterfall: a falling sheet from the lip to the foot, mist at its foot
	var lip: Array = lm["waterfall_lip"]
	var foot: Array = lm["waterfall_foot"]
	var drop := maxf(float(lip[1]) - float(foot[1]), 8.0)
	puffs.append([Vector3(lip[0], float(lip[1]) + 1.0, float(lip[2]) + 2.0), Vector3.ZERO, 1e9, 0.0, 6.0, 3, drop + 1.0, Color(0.86, 0.9, 0.92, 1.0), 0.0])
	puff_src.append([Vector3(foot[0], float(foot[1]) + 2.0, foot[2]), 3.0, 2, 0.0])
	# the hot spring's steam
	var hsp: Array = lm["hot_spring"]
	puff_src.append([Vector3(hsp[0], float(hsp[1]) + 1.0, hsp[2]), 1.4, 1, 0.0])


func _box(st: SurfaceTool, c: Vector3, s: Vector3, col: Color) -> void:
	var h := s * 0.5
	var faces := [[Vector3(0, 0, 1), Vector3(1, 0, 0), Vector3(0, 1, 0)], [Vector3(0, 0, -1), Vector3(-1, 0, 0), Vector3(0, 1, 0)],
		[Vector3(1, 0, 0), Vector3(0, 0, -1), Vector3(0, 1, 0)], [Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 0)],
		[Vector3(0, 1, 0), Vector3(1, 0, 0), Vector3(0, 0, -1)], [Vector3(0, -1, 0), Vector3(1, 0, 0), Vector3(0, 0, 1)]]
	for f in faces:
		var n: Vector3 = f[0]
		var u: Vector3 = f[1]
		var v: Vector3 = f[2]
		var o := c + n * h
		var a := o - u * h - v * h
		var b := o + u * h - v * h
		var cc := o + u * h + v * h
		var d := o - u * h + v * h
		for tri in [[a, b, cc], [a, cc, d]]:
			var x0: Vector3 = tri[0]
			var x1: Vector3 = tri[1]
			var x2: Vector3 = tri[2]
			if (x1 - x0).cross(x2 - x0).dot(n) > 0.0:
				var tmp := x1
				x1 = x2
				x2 = tmp
			for p in [x0, x1, x2]:
				st.set_color(col)
				st.set_normal(n)
				st.add_vertex(p)


# ------------------------------------------------------------------------------------------------
# her and さぢ on the lookout, seen from behind (the camera stands back on the spur so that one sprite
# pixel is one screen pixel: 20 px per metre at FIG_DIST)

const FIG_DIST := 18.5
var figure_mats: Array[ShaderMaterial] = []
var feet := Vector3.ZERO


func _build_figures() -> void:
	var f := FileAccess.open("res://world3d/sprites/characters.json", FileAccess.READ)
	if f == null:
		return
	var chars: Dictionary = JSON.parse_string(f.get_as_text())
	for spec in [["tsuzumi", "load", Vector3(0, 0, 0)], ["saji", "main", Vector3(0.85, 0, -0.35)]]:
		var c: Dictionary = chars[spec[0]]
		var sh: Dictionary = c["sheets"][spec[1]]
		var a: Dictionary = sh["anims"]["idle"]["back"]
		var fw := int(c["frame"][0])
		var fh := int(c["frame"][1])
		var m := _mat("vista_figure")
		m.set_shader_parameter("sheet", CharSprite3D.pixel_texture("res://world3d/sprites/%s.png" % sh["file"]))
		m.set_shader_parameter("frame_rect", Vector4(int(a["col"]) * fw, int(a["row"]) * fh, fw, fh))
		m.set_shader_parameter("pivot_px", Vector2(c["pivot"][0], c["pivot"][1]))
		var q := QuadMesh.new()
		q.size = Vector2(1, 1)
		var mi := MeshInstance3D.new()
		mi.mesh = q
		mi.material_override = m
		mi.extra_cull_margin = 8.0
		var p: Vector3 = feet + (spec[2] as Vector3)
		p.y = terrain.height_at(p.x, p.z)
		mi.position = p
		root.add_child(mi)
		figure_mats.append(m)


## Where the camera stands: on the spur behind her, a little to her right, looking out over her
## shoulder (she stands left of the middle, low in the frame).
func cam_pos() -> Vector3:
	# one sprite pixel = one screen pixel at her: distance = px per radian / 20
	var d := float(vp.size.y) * 0.5 / tan(deg_to_rad(FOV * 0.5)) / 20.0
	var off := Vector3(-4.0, EYE_H + 4.3, -18.0).normalized() * d
	return feet + Vector3(0.0, 1.0, 0.0) + off


# ------------------------------------------------------------------------------------------------
# puffs: smoke, steam, mist, the waterfall sheet

func _build_puffs() -> void:
	puff_mm.transform_format = MultiMesh.TRANSFORM_3D
	puff_mm.use_colors = true
	puff_mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	puff_mm.mesh = q
	puff_mm.instance_count = 400
	puff_mm.visible_instance_count = 0
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = puff_mm
	var m := _mat("vista_puff")
	m.render_priority = 2
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)
	# warm up so the columns stand when the view opens
	for i in 240:
		_step_puffs(0.1)


func _step_puffs(dt: float) -> void:
	var wind := Vector3(0.9, 0.0, 0.35) * (env.wind if env else 1.0)
	for s in puff_src:
		s[3] = float(s[3]) + dt * float(s[1])
		while float(s[3]) > 1.0:
			s[3] = float(s[3]) - 1.0
			var kind: int = s[2]
			var p: Vector3 = s[0]
			var col := Color(0.8, 0.78, 0.76, 1.0) if kind == 0 else (Color(0.93, 0.94, 0.95, 0.9) if kind == 1 else Color(0.9, 0.93, 0.95, 0.75))
			var life := 13.0 if kind == 0 else (8.0 if kind == 1 else 5.0)
			var vel := Vector3(rng.randf_range(-0.15, 0.15), 1.1 if kind == 0 else (0.8 if kind == 1 else 0.5), rng.randf_range(-0.15, 0.15))
			puffs.append([p + Vector3(rng.randf_range(-0.4, 0.4), 0, rng.randf_range(-0.4, 0.4)), vel, life, 0.0, 2.2 if kind != 2 else 3.4, kind, rng.randf(), col, 0.0])
	var i := 0
	while i < puffs.size():
		var pf: Array = puffs[i]
		pf[3] = float(pf[3]) + dt
		if float(pf[3]) > float(pf[2]):
			puffs.remove_at(i)
			continue
		if int(pf[5]) != 3:
			var age := float(pf[3]) / float(pf[2])
			pf[0] = (pf[0] as Vector3) + ((pf[1] as Vector3) + wind * age * (1.2 if int(pf[5]) == 0 else 0.6)) * dt
			pf[4] = float(pf[4]) + dt * (0.55 if int(pf[5]) == 0 else 0.4)
		i += 1


func _write_puffs() -> void:
	var n := mini(puffs.size(), puff_mm.instance_count)
	for i in n:
		var pf: Array = puffs[i]
		var kind := int(pf[5])
		var col: Color = pf[7]
		var size := float(pf[4])
		if kind != 3:
			# puffs thin out by shrinking and breaking up late in life, not by a long fade
			var age := float(pf[3]) / float(pf[2])
			col.a *= clampf((1.0 - age) * 3.0, 0.0, 1.0)
			size *= clampf(minf(age * 8.0, 1.0), 0.3, 1.0)
		puff_mm.set_instance_transform(i, Transform3D(Basis(), pf[0]))
		puff_mm.set_instance_color(i, col)
		puff_mm.set_instance_custom_data(i, Color(size, float(kind), float(pf[6]), float(pf[8])))
	puff_mm.visible_instance_count = n


# ------------------------------------------------------------------------------------------------
# per frame

func px_per_rad() -> float:
	return float(vp.size.y) * 0.5 / tan(deg_to_rad(FOV * 0.5))


## Bearing (deg) and the pitch that suits it: down over the lower layer to the south, a little up
## toward the summit and the tower to the north.
func pitch_for(bearing: float) -> float:
	var south := cos(deg_to_rad(bearing - 180.0))     # 1 facing south, -1 facing north
	return lerpf(8.0, -7.0, south * 0.5 + 0.5)


func update(dt: float) -> void:
	_t += dt
	var want := 1.0 if active else 0.0
	amount = move_toward(amount, want, dt / 0.7)
	var showing := amount > 0.0
	view.visible = showing
	if not showing:
		vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
		pv.vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		return
	if not built:
		build()
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	# the world view underneath stops while it is fully covered
	pv.vp.render_target_update_mode = SubViewport.UPDATE_DISABLED if amount >= 1.0 else SubViewport.UPDATE_ALWAYS
	display.set_shader_parameter("amount", amount)
	for k in ["lift", "gain", "saturation", "shadow_tone", "high_tone", "fade"]:
		display.set_shader_parameter(k, pv.composite.get_shader_parameter(k))
	# the camera: turns toward the wanted bearing, in whole-pixel steps at the centre of the view
	yaw = lerpf(yaw, yaw_target, 1.0 - exp(-dt * 2.2))
	var step := rad_to_deg(1.0 / px_per_rad())
	var yq := roundf(yaw / step) * step
	var pitch := roundf(pitch_for(yq) / step) * step
	var e := cam_pos()
	if e.distance_to(eye) > 0.001:
		eye = e
		for m in mats:
			m.set_shader_parameter("eye", eye)
	cam.position = eye
	cam.rotation = Vector3(deg_to_rad(pitch), -deg_to_rad(yq), 0.0)
	# the time of day: the same sun and globals as the world, the sky's own colours
	sun.light_color = env.sun.light_color
	sun.light_energy = env.sun.light_energy
	sun.global_transform = env.sun.global_transform
	var k := _sky_at(env.hours)
	var night := clampf(float(env.sample(env.hours)[11]), 0.0, 1.0)
	sky_mat.set_shader_parameter("zenith", k[1])
	sky_mat.set_shader_parameter("horizon", (k[2] as Color).lerp(Color(0.62, 0.64, 0.67), env.rain * 0.7))
	sky_mat.set_shader_parameter("mist_col", k[3])
	sky_mat.set_shader_parameter("cloud_lit", k[4])
	sky_mat.set_shader_parameter("cloud_shade", k[5])
	sky_mat.set_shader_parameter("sun_dir", W3Env.sun_direction(env.hours))
	sky_mat.set_shader_parameter("sun_col", Color(1.0, 0.92, 0.75) if night < 0.5 else Color(0.9, 0.92, 1.0))
	sky_mat.set_shader_parameter("night", night)
	sky_mat.set_shader_parameter("px_per_rad", px_per_rad())
	sky_mat.set_shader_parameter("time", _t)
	var haze_dist := lerpf(3600.0, 1100.0, env.rain) * (0.7 if env.hours < 8.0 else 1.0)
	for m in mats:
		m.set_shader_parameter("haze_col", (k[2] as Color).lerp(Color(0.62, 0.64, 0.67), env.rain * 0.7))
		m.set_shader_parameter("mist_col", k[3])
		m.set_shader_parameter("haze_dist", haze_dist)
	# lights: the tower blinks red, the kiln glows at night
	var blink := 1.0 if fmod(_t, 2.0) < 1.0 else 0.25
	red_mat.set_shader_parameter("emission_energy", (1.6 + 2.2 * night) * blink)
	kiln_glow.set_shader_parameter("emission_energy", 0.4 + 2.4 * night)
	var lc := Vector3(env.sun.light_color.r, env.sun.light_color.g, env.sun.light_color.b) * env.sun.light_energy * 0.55
	var sky_v: Vector3 = Vector3(0.5, 0.55, 0.62) * (1.0 - night * 0.65)
	for fm in figure_mats:
		fm.set_shader_parameter("light_col", lc + sky_v)
	if mist_mat:
		mist_mat.set_shader_parameter("time", _t)
	if sea_mat:
		sea_mat.set_shader_parameter("time", _t)
		sea_mat.set_shader_parameter("lit_col", (k[4] as Color).lerp(k[3], 0.35))
		sea_mat.set_shader_parameter("shade_col", (k[5] as Color).lerp(k[3], 0.3))
	_step_puffs(dt)
	_write_puffs()


func _sky_at(h: float) -> Array:
	h = fposmod(h, 24.0)
	for i in SKY_KEYS.size() - 1:
		var a: Array = SKY_KEYS[i]
		var b: Array = SKY_KEYS[i + 1]
		if h >= float(a[0]) and h <= float(b[0]):
			var t := (h - float(a[0])) / maxf(float(b[0]) - float(a[0]), 1e-4)
			var out := [h]
			for j in range(1, a.size()):
				out.append((a[j] as Color).lerp(b[j], t))
			return out
	return SKY_KEYS[0]
