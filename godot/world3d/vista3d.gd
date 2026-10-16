class_name W3Vista
extends Node
## The view from the lookout (眺望岩 of the sample): her view out over the land around the pass, in
## the pixel-art language of the top-down world (native resolution, nearest upscale at the stage's
## integer scale, toon bands and the painted shade, the palette and glyphs of the top-down ground,
## aerial perspective in whole steps, bloom only on lights). docs/knowledge/21 §10. Its own World3D:
##   * the land: the region's real heights, ground materials and painted marks near (vista_ground,
##     vista_post), and around it the land of the map (tools/world3d/w3terrain/vista.py): the summit
##     with the 「隔」 tower and the ruined temple on its shoulder to the north, the kiln on the east
##     shoulder, the 裏見之瀑 falling into the canyon to the west (its mist rises out of it), the lower
##     layer to the south (溜池, the terraces and the farm), the old road going down to the plain;
##   * the plain far below: fields, the river, villages and a town (vista_house), the railway on its
##     viaduct and iron bridge (vista_line); banks of cumulus over the lowland with a lane open down
##     the middle toward the town (vista_cloud); past a front a few kilometres out the 遠化 has drained
##     the land flat and white (vista_common v_air); mountains on the horizon;
##   * trees, the great camphor, the hut, the shrine and the graves as impostors baked from the real
##     assets (vista_impostor), the lookout's granite rocks, the kiln, the temple, the bridges, the
##     tower and its red light, the home's lanterns at night;
##   * smoke from the kiln, steam from the hot spring, the waterfall's mist (vista_puff);
##   * her (the 3D model, drawn through a camera of its own: _build_fig3d) and さぢ (a sprite);
##   * sky, sun, moon, stars and painted clouds (vista_sky).
## The projection is equirectangular, not perspective (vista_common.gdshaderinc v_project): a screen
## pixel is a fixed step of azimuth and elevation, so turning her head by whole pixels moves the whole
## picture by whole pixels (a perspective camera's sides re-sample as it turns: every grain crawls).
## She looks out when she stands still on the lookout; A/D (or the arrows) turn her head (held at the
## end of the range she turns round, out over the land / back home); W/S bring the top-down view
## back. The view comes in and goes out through the white of the mist (a fade, no halftone).

const DATA := "res://world3d/terrain/saddle/vista.json"
const EYE_H := 1.45
# vertical, degrees (px per radian = half the height / tan(FOV/2)). Round 3's frame (the user,
# G5R3-16: "v3版的畫面裁剪比例最好保留，有電影的感覺"): 40 degrees, the camera where round 3 stood
# (CAM_DIST), so the horizon, the rocks, the pine and the maples sit in the frame as they did; at
# 640x360 that is 494.5 px per radian (round 3: 480x270, 371), everything a third finer, and she and
# さぢ drawn at the land's scale at her distance (fig_ppm, about 26.7 px per metre). (Round 5's first
# try kept 371 px per radian at 51.8 degrees: round 3's picture with a margin round it, more sky and
# more foreground, which the user saw; round 4 kept 40 degrees but pushed the camera back to 24.7 m.)
const FOV := 40.0
const CAM_DIST := 18.55             # round 3's: its 371 px per radian / 20 px per metre

# hour, zenith, horizon, mist, cloud lit, cloud shade (sRGB)
const SKY_KEYS := [
	[0.0, Color(0.03, 0.04, 0.09), Color(0.12, 0.11, 0.21), Color(0.15, 0.16, 0.25), Color(0.24, 0.25, 0.36), Color(0.07, 0.07, 0.13)],
	[4.6, Color(0.03, 0.04, 0.09), Color(0.12, 0.11, 0.21), Color(0.15, 0.16, 0.25), Color(0.24, 0.25, 0.36), Color(0.07, 0.07, 0.13)],
	[5.6, Color(0.2, 0.22, 0.4), Color(0.86, 0.58, 0.5), Color(0.78, 0.64, 0.66), Color(1.0, 0.76, 0.64), Color(0.42, 0.38, 0.5)],
	[7.0, Color(0.36, 0.52, 0.76), Color(0.88, 0.84, 0.76), Color(0.9, 0.88, 0.85), Color(1.0, 0.96, 0.88), Color(0.6, 0.64, 0.74)],
	[12.0, Color(0.32, 0.5, 0.78), Color(0.73, 0.8, 0.86), Color(0.86, 0.88, 0.9), Color(1.0, 1.0, 0.97), Color(0.64, 0.7, 0.8)],
	[16.0, Color(0.33, 0.48, 0.74), Color(0.8, 0.8, 0.79), Color(0.88, 0.86, 0.84), Color(1.0, 0.96, 0.88), Color(0.62, 0.64, 0.74)],
	[17.6, Color(0.28, 0.34, 0.58), Color(0.98, 0.7, 0.46), Color(0.95, 0.79, 0.66), Color(1.0, 0.8, 0.6), Color(0.54, 0.44, 0.54)],
	[18.6, Color(0.14, 0.15, 0.33), Color(0.74, 0.42, 0.4), Color(0.58, 0.45, 0.51), Color(0.88, 0.54, 0.5), Color(0.28, 0.23, 0.36)],
	[19.6, Color(0.03, 0.04, 0.09), Color(0.12, 0.11, 0.21), Color(0.15, 0.16, 0.25), Color(0.24, 0.25, 0.36), Color(0.07, 0.07, 0.13)],
	[24.0, Color(0.03, 0.04, 0.09), Color(0.12, 0.11, 0.21), Color(0.15, 0.16, 0.25), Color(0.24, 0.25, 0.36), Color(0.07, 0.07, 0.13)],
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
var puff_mat: ShaderMaterial
var red_light: MeshInstance3D
var red_mat: ShaderMaterial
var kiln_glow: ShaderMaterial
var rng := RandomNumberGenerator.new()
var _t := 0.0
var _vdebug: PackedStringArray = []   # --vdebug=nodrain,nohaze,nocloud (looking into the layers)


func setup(p: PixelView3D, e: W3Env, t: Terrain3D) -> void:
	pv = p
	env = e
	terrain = t
	rng.seed = 77
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--vdebug="):
			_vdebug = a.substr(9).split(",")
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
	# float, linear: the display converts and dithers (round 4: continuous light, no banding)
	vp.use_hdr_2d = true
	add_child(vp)
	root = Node3D.new()
	root.name = "Land"
	vp.add_child(root)
	cam = Camera3D.new()
	# (wider than the picture: the vista draws its own projection, the camera's frustum only culls)
	cam.fov = FOV + 20.0
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
	_common(pm)
	_marks_setup(pm)
	post_mat = pm
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
	display.set_shader_parameter("blue_noise", load("res://render3d/textures/blue_noise64.png"))
	view.material = display
	view.visible = false
	pv.add_child(view)
	view.texture = vp.get_texture()
	pv.logical_resized.connect(_fit)
	_fit(pv.logical)
	var lk: Vector3 = terrain.marker("lookout")
	feet = Vector3(lk.x, terrain.height_at(lk.x, lk.z), lk.z)
	eye = cam_pos()


## The ground's painted marks (vista_post): the top-down ground's glyphs and tufts, its palette and
## the region's splat maps, so a mark is chosen as it would be on the walkable ground.
func _marks_setup(pm: ShaderMaterial) -> void:
	var tm: ShaderMaterial = terrain.terrain_mat
	for k in ["m0", "m1", "m2", "palette", "glyphs"]:
		pm.set_shader_parameter(k, tm.get_shader_parameter(k))
	for k in ["g_grass", "g_flowers", "g_dirt", "g_gravel", "g_rock", "g_moss", "g_litter", "g_bank"]:
		pm.set_shader_parameter(k, tm.get_shader_parameter(k))
	pm.set_shader_parameter("tufts", _tex("res://world3d/terrain/common/tufts.png"))
	var sp: Dictionary = terrain.info["splat"]
	pm.set_shader_parameter("splat_frame", Vector4(terrain.origin.x, terrain.origin.y, float(sp["cell"]), 0.0))
	pm.set_shader_parameter("splat_size", Vector2(sp["size"][0], sp["size"][1]))
	var o := terrain.origin
	pm.set_shader_parameter("local_bounds", Vector4(o.x, o.y, o.x + (terrain.nx - 1) * terrain.cell, o.y + (terrain.nz - 1) * terrain.cell))
	if _vdebug.has("nomarks"):
		pm.set_shader_parameter("marks", false)
	if _vdebug.has("nooutline"):
		pm.set_shader_parameter("strength", 0.0)
	# the 遠化's band without round 3's bright edge (lead 2026-10-16, of three variants: beside the new
	# clouds the edge read as cut paper, the hardness the user disliked in round 3's clouds)
	pm.set_shader_parameter("band_edge", 0.0)


var post_mat: ShaderMaterial


func _fit(size: Vector2) -> void:
	vp.size = Vector2i(size)
	for m in mats:
		m.set_shader_parameter("v_ppr", px_per_rad())
	sky_mat.set_shader_parameter("px_per_rad", px_per_rad())
	_imp_cam = Vector3.INF
	view.position = Vector2.ZERO
	view.size = size


## Build the land (once; about a second). Done on the first look, or up front for recordings.
func build() -> void:
	if built:
		return
	built = true
	var t0 := Time.get_ticks_msec()
	_cloud_layout()
	_build_land()
	_build_mist()
	_build_impostors()
	_build_shapes()
	_build_rocks()
	_build_landmarks()
	_build_plain()
	_build_lines()
	_build_temple()
	_build_figures()
	_build_puffs()
	_place_impostors(eye)
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
	if data.has("plain"):
		var pd: Dictionary = data["plain"]
		m.set_shader_parameter("plain_tex", _tex_lin(dir + String(pd["file"])))
		m.set_shader_parameter("plain_frame", Vector4(pd["x0"], pd["z0"], pd["cell"], pd["nx"]))
	m.set_shader_parameter("sea_base", SEA_Y)
	if vp:
		m.set_shader_parameter("v_ppr", px_per_rad())
	m.set_shader_parameter("front_c", FRONT)
	# the 遠化's print (vista_common v_print): the blocks' flat colours and the key block's ink, from the
	# terrain's palette and the view's own forest (no new colours)
	for kv in _print_colours():
		m.set_shader_parameter(kv[0], kv[1])
	m.set_shader_parameter("eye", eye)
	if cloud_tex:
		m.set_shader_parameter("cloud_tex", cloud_tex)
		m.set_shader_parameter("cloud_box", cloud_box)
		m.set_shader_parameter("cloud_wind", CLOUD_WIND)
	mats.append(m)


var _tex_cache := {}


func _tex(path: String) -> ImageTexture:
	if not _tex_cache.has(path):
		var im: Image = load(path)
		_tex_cache[path] = ImageTexture.create_from_image(im)
	return _tex_cache[path]


## The same, for maps the shaders read with bilinear filtering (distance fields).
func _tex_lin(path: String) -> ImageTexture:
	return _tex(path)


var _print_cols: Array = []

## The 遠化's print colours (vista_common): the key block's ink (the palette's K, sRGB) and two tones
## for the green and the earth blocks (linear): the terrain palette's grass and fallow and bank earth,
## the view's own forest.
func _print_colours() -> Array:
	if _print_cols.is_empty():
		var pal: Image = load("res://world3d/terrain/common/palette.png")
		var lin := func(c: Color) -> Vector3:
			var l := c.srgb_to_linear()
			return Vector3(l.r, l.g, l.b)
		var k := pal.get_pixel(0, 12) if pal else Color8(58, 46, 38)
		_print_cols = [["ink_k", Vector3(k.r, k.g, k.b)],
			["print_green_lt", lin.call(pal.get_pixel(5, 0) if pal else Color8(85, 96, 75))],
			["print_green_dk", lin.call(Color(0.2, 0.29, 0.16))],
			["print_earth_lt", lin.call(pal.get_pixel(5, 8) if pal else Color8(129, 119, 103))],
			["print_earth_dk", lin.call(pal.get_pixel(3, 9) if pal else Color8(88, 75, 61))]]
	return _print_cols


## The 遠化 on the CPU, as vista_common draws it (v_front_r, v_past_m): metres past the front at a
## point (negative before it). The puffs and the sound ask it.
func past_m(x: float, z: float) -> float:
	var dx := x - FRONT.x
	var dz := z - FRONT.y
	var a := atan2(dx, -dz)
	var w := _vnoise(a * 2.2 + 11.0, 3.0) * 0.65 + _vnoise(a * 6.1 + 2.0, 7.0) * 0.35
	return sqrt(dx * dx + dz * dz) - FRONT.z * (0.62 + 0.8 * w)


static func _hash2(x: float, y: float) -> float:
	# (pixel_toon's w3_hash)
	var p3 := Vector3(fposmod(x * 0.1031, 1.0), fposmod(y * 0.1031, 1.0), fposmod(x * 0.1031, 1.0))
	var d := p3.dot(Vector3(p3.y + 33.33, p3.z + 33.33, p3.x + 33.33))
	p3 += Vector3(d, d, d)
	return fposmod((p3.x + p3.y) * p3.z, 1.0)


static func _vnoise(x: float, y: float) -> float:
	var ix := floorf(x)
	var iy := floorf(y)
	var fx := x - ix
	var fy := y - iy
	var ux := fx * fx * (3.0 - 2.0 * fx)
	var uy := fy * fy * (3.0 - 2.0 * fy)
	return lerpf(lerpf(_hash2(ix, iy), _hash2(ix + 1.0, iy), ux), lerpf(_hash2(ix, iy + 1.0), _hash2(ix + 1.0, iy + 1.0), ux), uy)


## How much of the view the 遠化 fills toward a bearing (0..1): rays across the frame at the horizon's
## height and a little under it, each marched over the land to where it meets the ground (or runs
## out to the far ranges); the share of them that end past the front. Cached per degree.
var _far_cache := {}
var _far_sent := 0.0
func far_share(bearing: float, pitch: float) -> float:
	var key := Vector2i(roundi(bearing * 0.5), roundi(pitch))
	if _far_cache.has(key):
		return float(_far_cache[key])
	var hits := 0
	var total := 0
	var half := rad_to_deg(atan(float(vp.size.x) * 0.5 / px_per_rad()))
	for i in 7:
		var b := deg_to_rad(bearing + lerpf(-half, half, float(i) / 6.0))
		for el in [pitch - 1.0, pitch - 5.0]:
			var e := deg_to_rad(el)
			var dir := Vector3(sin(b) * cos(e), sin(e), -cos(b) * cos(e))
			var t := 40.0
			var end := Vector3.INF
			while t < 16000.0:
				var p := eye + dir * t
				if p.y <= ground_h(p.x, p.z):
					end = p
					break
				t *= 1.08
			total += 1
			# (a ray that never meets the land looks at the sky over the far ranges: those lie in the
			# 遠化 when it is that way)
			if end == Vector3.INF:
				end = eye + dir * 16000.0
				if el > pitch - 2.0:
					total -= 1
					continue
			if past_m(end.x, end.z) > 0.0:
				hits += 1
	var k := float(hits) / maxf(float(total), 1.0)
	_far_cache[key] = k
	return k


func _mat(shader: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/%s.gdshader" % shader)
	_common(m)
	return m


# ------------------------------------------------------------------------------------------------
# the land: a radial grid around the eye, lifted in the vertex shader

func _build_land() -> void:
	var mat := _mat("vista_ground")
	if _vdebug.has("slope"):
		mat.set_shader_parameter("dbg_mode", 1)
	if _vdebug.has("plainmap"):
		mat.set_shader_parameter("dbg_mode", 2)
	if _vdebug.has("albedo"):
		mat.set_shader_parameter("dbg_mode", 3)
	if _vdebug.has("ambient"):
		mat.set_shader_parameter("dbg_mode", 4)
	var tm: ShaderMaterial = terrain.terrain_mat
	for k in ["m0", "m1", "m2", "m3", "palette"]:
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


## The vista ground's own height (exactly what vista_common.gdshaderinc v_height draws: bilinear on
## the mid and far maps, the mid map faded out over its outer 60 m). Every impostor stands on this,
## not on the height its generator or the region's terrain gave it (round 4: trees floated over the
## paddies of the lower layer where the terraces had been cut after the woods were spread).
func ground_h(x: float, z: float) -> float:
	land_h(x, z)    # loads the maps
	var md: Dictionary = data["mid"]
	var fd: Dictionary = data["far"]
	var hf := _map_h(_far_img, fd, x, z)
	var lo := Vector2(float(md["x0"]), float(md["z0"]))
	var hi := lo + Vector2.ONE * (float(md["nx"]) - 1.0) * float(md["cell"])
	var e := minf(minf(x - lo.x, hi.x - x), minf(z - lo.y, hi.y - z))
	var w := smoothstep(0.0, 60.0, e)
	if w <= 0.0:
		return hf
	return lerpf(hf, _map_h(_mid_img, md, x, z), w)


func _map_h(img: Image, d: Dictionary, x: float, z: float) -> float:
	var n := int(d["nx"])
	var g := Vector2((x - float(d["x0"])) / float(d["cell"]), (z - float(d["z0"])) / float(d["cell"]))
	g = g.clamp(Vector2.ZERO, Vector2.ONE * (float(n) - 1.001))
	var i := int(floor(g.x))
	var j := int(floor(g.y))
	var f := g - Vector2(i, j)
	var a := _u16(img.get_pixel(i, j), d)
	var b := _u16(img.get_pixel(i + 1, j), d)
	var c := _u16(img.get_pixel(i, j + 1), d)
	var dd := _u16(img.get_pixel(i + 1, j + 1), d)
	return lerpf(lerpf(a, b, f.x), lerpf(c, dd, f.x), f.y)


func _u16(c: Color, d: Dictionary) -> float:
	return float(d["hmin"]) + (roundf(c.r * 255.0) * 256.0 + roundf(c.g * 255.0)) / 65535.0 * float(d["hrange"])


## What the mid map says lies at a point: water (pond, paddy), cultivated land, road (no tree there).
func _open_ground(x: float, z: float) -> bool:
	var md: Dictionary = data["mid"]
	var n := int(md["nx"])
	var i := roundi((x - float(md["x0"])) / float(md["cell"]))
	var j := roundi((z - float(md["z0"])) / float(md["cell"]))
	if i < 0 or j < 0 or i >= n or j >= n:
		return false
	if _mat_img == null:
		_mat_img = load("res://world3d/terrain/saddle/" + String(md["mat"]))
	var c := _mid_img.get_pixel(i, j)
	var m := _mat_img.get_pixel(i, j)
	return c.a > 0.5 or m.r > 0.5 or m.g > 0.5


var _mat_img: Image


# ------------------------------------------------------------------------------------------------
# the sea of clouds over the lowland beyond the region's ring (round 4, second pass: banks of
# billows, vista_cloud.gdshader; the lead found the lifted height field of round 4 read as rocks)

var sea_mat: ShaderMaterial
const SEA_Y := -255.0                 # the banks' soft base (the plain lies at about -340)
const FRONT := Vector3(-50.0, 0.0, 5000.0)   # the 遠化 front: centre x, z, mean radius (m)
const CLOUD_CELL := 340.0             # at most one big bank to a cell of this size
const CLOUD_SMALL := 200.0            # and one small cumulus
const CLOUD_TEX_CELL := 70.0          # m per texel of the room and shade map
const CLOUD_WIND := Vector2(0.45, 0.0)  # m/s: the banks creep east (round their domain)
var cloud_box := Vector4.ZERO         # x0, z0, width, depth of the banks' domain (m)
var cloud_tex: ImageTexture
var cloud_banks: Array = []           # [centre at the start, its billows' instance rows (PackedFloat32Array)]
var cloud_mm := MultiMesh.new()
var cloud_inst: MultiMeshInstance3D
var _cloud_sorted_t := -1e9
var _cloud_sorted_eye := Vector3.INF


## Where the banks lie and the room they have (before the land is built: the ground's material
## reads the shade of the banks).
func _cloud_layout() -> void:
	var half := FRONT.z * 0.98
	cloud_box = Vector4(FRONT.x - half, FRONT.y - half, half * 2.0, half * 2.0)
	var crng := RandomNumberGenerator.new()
	crng.seed = 4711
	var fn := FastNoiseLite.new()
	fn.seed = 23
	fn.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	fn.frequency = 1.0 / 1700.0
	fn.fractal_octaves = 2
	# big banks where the cover is thick, small cumulus round their edges, the land open between
	var n := int(ceil(cloud_box.z / CLOUD_CELL))
	for j in n:
		for i in n:
			var c := Vector2(cloud_box.x + (i + crng.randf_range(0.2, 0.8)) * CLOUD_CELL, cloud_box.y + (j + crng.randf_range(0.2, 0.8)) * CLOUD_CELL)
			var cov := fn.get_noise_2d(c.x, c.y) * 0.5 + 0.5
			var k := crng.randf()
			var sz := crng.randf_range(0.36, 0.52)
			if cov > 0.42 and k > 0.06 and _cloud_room_at(c) > 0.1 + 0.3 * crng.randf():
				_cloud_bank(c, CLOUD_CELL * sz * lerpf(0.9, 1.45, smoothstep(0.42, 0.75, cov)), crng, 1.0)
	var ns := int(ceil(cloud_box.z / CLOUD_SMALL))
	for j in ns:
		for i in ns:
			var c := Vector2(cloud_box.x + (i + crng.randf_range(0.15, 0.85)) * CLOUD_SMALL, cloud_box.y + (j + crng.randf_range(0.15, 0.85)) * CLOUD_SMALL)
			var cov := fn.get_noise_2d(c.x, c.y) * 0.5 + 0.5
			var k := crng.randf()
			var sz := crng.randf_range(0.2, 0.36)
			if cov > 0.3 and cov < 0.5 and k < 0.3 and _cloud_room_at(c) > 0.1:
				_cloud_bank(c, CLOUD_SMALL * sz, crng, 1.0)
	# the map: G the room (fixed to the land), R the banks' shade as they lie at the start
	var tw := int(ceil(cloud_box.z / CLOUD_TEX_CELL))
	var th := int(ceil(cloud_box.w / CLOUD_TEX_CELL))
	var shade := PackedFloat32Array()
	shade.resize(tw * th)
	for b in cloud_banks:
		var bc: Vector3 = b[0]
		var rr: float = float(b[1]) * 0.85
		var k: float = b[5]
		var i0 := maxi(0, int((bc.x - rr - cloud_box.x) / CLOUD_TEX_CELL))
		var i1 := mini(tw - 1, int((bc.x + rr - cloud_box.x) / CLOUD_TEX_CELL))
		var j0 := maxi(0, int((bc.z - rr - cloud_box.y) / CLOUD_TEX_CELL))
		var j1 := mini(th - 1, int((bc.z + rr - cloud_box.y) / CLOUD_TEX_CELL))
		for j in range(j0, j1 + 1):
			for i in range(i0, i1 + 1):
				var p := Vector2(cloud_box.x + (i + 0.5) * CLOUD_TEX_CELL, cloud_box.y + (j + 0.5) * CLOUD_TEX_CELL)
				var v := (1.0 - smoothstep(0.55, 1.0, p.distance_to(Vector2(bc.x, bc.z)) / rr)) * k
				shade[j * tw + i] = maxf(shade[j * tw + i], v)
	var img := Image.create(tw, th, false, Image.FORMAT_RG8)
	for j in th:
		for i in tw:
			var p := Vector2(cloud_box.x + (i + 0.5) * CLOUD_TEX_CELL, cloud_box.y + (j + 0.5) * CLOUD_TEX_CELL)
			img.set_pixel(i, j, Color(shade[j * tw + i], _cloud_room_at(p), 0.0))
	cloud_tex = ImageTexture.create_from_image(img)
	if _vdebug.has("cloudmap"):
		var dbg := img.duplicate() as Image
		dbg.convert(Image.FORMAT_RGB8)
		for b in cloud_banks:
			var bc: Vector3 = b[0]
			var i := int((bc.x - cloud_box.x) / CLOUD_TEX_CELL)
			var j := int((bc.z - cloud_box.y) / CLOUD_TEX_CELL)
			if i >= 0 and j >= 0 and i < tw and j < th:
				dbg.set_pixel(i, j, Color(1, 1, 1))
		var li := int((feet.x - cloud_box.x) / CLOUD_TEX_CELL)
		var lj := int((feet.z - cloud_box.y) / CLOUD_TEX_CELL)
		dbg.set_pixel(li, lj, Color(0, 0, 1))
		dbg.save_png("user://cloudmap.png")
		print("VISTA cloudmap ", OS.get_user_data_dir())


## The room a bank has at a place: none near the region's ring, over the lane open toward the town
## (the lookout's view down the middle to the river and the town), over ground higher than the
## banks' middle (a bank lies against a slope, never over a hill), and less and less toward the
## 遠化 front.
func _cloud_room_at(p: Vector2) -> float:
	var me: Dictionary = data["mist"]
	var e := ((p - Vector2(float(me["cx"]), float(me["cz"]))) / Vector2(float(me["rx"]), float(me["rz"]))).length()
	var rf := p.distance_to(Vector2(FRONT.x, FRONT.y))
	var d := p - Vector2(feet.x, feet.z)
	var rl := d.length()
	var a := rad_to_deg(atan2(d.x, -d.y))
	# (the lane: open full down the middle over the town, its sides closing over a few degrees)
	var la := (absf(a) - 176.0) / 21.0
	var lane := exp(-la * la * la * la) * smoothstep(450.0, 900.0, rl) * (1.0 - smoothstep(3900.0, 4600.0, rl))
	var room := smoothstep(1.04, 1.4, e) * (1.0 - smoothstep(FRONT.z * 0.62, FRONT.z * 0.95, rf)) * (1.0 - lane)
	if room <= 0.0:
		return 0.0
	# (a bank may lie against a slope, its billows fading out before it: vista_cloud)
	return room * smoothstep(-40.0, 10.0, SEA_Y + 20.0 - ground_h(p.x, p.y))


## One bank: a body of big billows along its base over its footprint (longer across the wind), a
## crown heaped toward its middle up to its top, a few heads breaking the top, and thin low fringes
## round its edge. Its billows' instance rows, nearest the eye last.
func _cloud_bank(c: Vector2, big_r: float, crng: RandomNumberGenerator, cover: float) -> void:
	var h := big_r * crng.randf_range(0.34, 0.58)
	var base := SEA_Y + crng.randf_range(-10.0, 12.0)
	var bc := Vector3(c.x, base + h * 0.35, c.y)
	var rows: Array = []   # [centre, radius, cover]
	for k in 4 + int(big_r / 22.0):
		var a := crng.randf() * TAU
		var d := sqrt(crng.randf()) * big_r * 0.66
		var rb := big_r * crng.randf_range(0.24, 0.36)
		rows.append([Vector3(c.x + cos(a) * d * 1.2, base + rb * 0.5, c.y + sin(a) * d * 0.85), rb, cover])
	for k in 2 + int(big_r / 45.0):
		var a := crng.randf() * TAU
		var d := sqrt(crng.randf()) * big_r * 0.4
		var ru := big_r * crng.randf_range(0.22, 0.32)
		var top := base + h * sqrt(maxf(0.0, 1.0 - (d / big_r) * (d / big_r)))
		rows.append([Vector3(c.x + cos(a) * d, top - ru * 0.85, c.y + sin(a) * d), ru, cover])
	for k in crng.randi_range(1, 2) + int(big_r / 90.0):
		var a := crng.randf() * TAU
		var d := crng.randf() * big_r * 0.32
		var rh := big_r * crng.randf_range(0.12, 0.19)
		var top := base + h * sqrt(maxf(0.0, 1.0 - (d / big_r) * (d / big_r)))
		rows.append([Vector3(c.x + cos(a) * d, top + rh * 0.1, c.y + sin(a) * d), rh, cover])
	for k in crng.randi_range(2, 3) + int(big_r / 100.0):
		var a := crng.randf() * TAU
		var d := big_r * crng.randf_range(0.78, 1.0)
		var rf := big_r * crng.randf_range(0.17, 0.25)
		rows.append([Vector3(c.x + cos(a) * d * 1.1, base + rf * 0.3, c.y + sin(a) * d * 0.9), rf, cover * 0.85])
	cloud_banks.append([bc, big_r, h, base, rows, cover * 0.75 + 0.25 * float(cover >= 1.0)])


## The rows of a bank's billows for the MultiMesh buffer (3x4 rows: basis x = bank radius, height,
## base; basis y = the bank's centre; basis z = billow radius, seed, cover; origin = its centre),
## the farthest from the eye first.
func _cloud_rows(b: Array) -> PackedFloat32Array:
	var rows: Array = (b[4] as Array).duplicate()
	rows.sort_custom(func(p, q): return (p[0] as Vector3).distance_squared_to(eye) > (q[0] as Vector3).distance_squared_to(eye))
	var bc: Vector3 = b[0]
	var out := PackedFloat32Array()
	for r in rows:
		var o: Vector3 = r[0]
		var seed := fposmod(o.x * 0.0137 + o.z * 0.0071, 1.0)
		out.append_array([float(b[1]), bc.x, float(r[1]), o.x,
			float(b[2]), bc.y, seed, o.y,
			float(b[3]), bc.z, float(r[2]), o.z])
	return out


func _build_mist() -> void:
	sea_mat = _mat("vista_cloud")
	var total := 0
	for b in cloud_banks:
		total += (b[4] as Array).size()
	cloud_mm.transform_format = MultiMesh.TRANSFORM_3D
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	cloud_mm.mesh = q
	cloud_mm.instance_count = total
	cloud_inst = MultiMeshInstance3D.new()
	cloud_inst.multimesh = cloud_mm
	cloud_inst.material_override = sea_mat
	cloud_inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	cloud_inst.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(cloud_inst)
	_sort_clouds()
	print("VISTA clouds banks=%d billows=%d" % [cloud_banks.size(), total])


## Back to front from the eye: the banks by where they have crept to, each bank's billows as laid
## out (now and then: they creep slowly; and whenever the eye moves to the other place).
func _sort_clouds() -> void:
	_cloud_sorted_t = _t
	var moved := _cloud_sorted_eye.distance_to(eye) > 1.0
	_cloud_sorted_eye = eye
	var order: Array = []
	for i in cloud_banks.size():
		var b: Array = cloud_banks[i]
		if moved or b.size() < 7:
			if b.size() < 7:
				b.append(PackedFloat32Array())
			b[6] = _cloud_rows(b)
		var bc: Vector3 = b[0]
		var x := cloud_box.x + fposmod(bc.x + CLOUD_WIND.x * _t - cloud_box.x, cloud_box.z)
		var cur := Vector3(x, bc.y, bc.z + CLOUD_WIND.y * _t)
		order.append([cur.distance_squared_to(eye), i])
	order.sort_custom(func(p, q): return p[0] > q[0])
	var buf := PackedFloat32Array()
	for o in order:
		buf.append_array(cloud_banks[o[1]][6])
	cloud_mm.buffer = buf


# ------------------------------------------------------------------------------------------------
# impostors

var _tree_rows: Array = []


func _tree(x: float, y: float, z: float, kind: int, h: float, w: float, seed: float) -> void:
	_tree_rows.append([x, y, z, kind, h, w, seed])


## Trees and the great camphor, the hut, the shrine and the graves as impostors baked from the real
## assets (render3d/dev/impostor_bake.gd -> tools/world3d/vista_impostors.py): the region's own props
## (W3Vista.props, handed over by the sample), the woods of the land around (vista.json) and the two
## red maples by the path.
# round 5 (G5R3-1: "遠眺場景那些樹木植被什麼的數量和形狀狀態都需要和上一個版本保持一致"): the trees as round 3
# drew them: their stand-ins (round 3's atlas, merged over the current heroes' by
# tools/world3d/vista_merge_r3.py: impostors_r5) and their number and places (the region's props as
# round 3's sample placed them, and its rocks: round3_props.json), frozen for the view; the heroes
# (the great camphor, the hut, the shrine, the graves) as they stand now
const IMPOSTORS := "res://world3d/vista/impostors_r5.json"
const ATLAS_A := "res://world3d/vista/impostors_r5_a.png"
const ATLAS_N := "res://world3d/vista/impostors_r5_n.png"
const PROPS_R3 := "res://world3d/vista/round3_props.json"
# the baked stand-in of each catalog species, with its height (m)
const IMP_KIND := {"sugi": [["sugi_a", 22.0], ["sugi_d", 26.0]], "pine": [["pine_a", 13.0], ["pine_c", 15.0]],
	"konara": [["konara_a", 12.0], ["konara_c", 14.0]], "buna": [["buna_a", 15.0]], "maple_red": [["maple_red_a", 6.5]],
	"maple": [["maple_a", 7.0]], "take": [["take_c", 13.5]], "kaki": [["kaki_a", 7.5]]}
const BAKED_H := {"sugi_a": 22.0, "sugi_d": 26.0, "pine_a": 13.0, "pine_c": 15.0, "konara_a": 12.0, "konara_c": 14.0, "buna_a": 15.0,
	"take_c": 13.5, "maple_red_a": 6.5, "maple_a": 7.0, "kaki_a": 7.5}
# the baked heroes (one or a few views each), drawn at their own height
const IMP_HERO := ["camphor_great", "hut", "shrine", "graves"]

var props: Array = []                 # [catalog name, position, yaw, scale, height m] from the sample
var imp_frames := {}                  # asset -> {angle index (-1: single views) -> [frames, by ppm desc]}
var imp_rows: Array = []              # [foot, asset, yaw, scale]
var imp_mm := MultiMesh.new()
var imp_mat := ShaderMaterial.new()
var _imp_cam := Vector3.INF
var _float_max := 0.0
var _float_dropped := 0


func _load_impostors() -> void:
	var f := FileAccess.open(IMPOSTORS, FileAccess.READ)
	if f == null:
		push_warning("no impostors: " + IMPOSTORS)
		return
	var m: Dictionary = JSON.parse_string(f.get_as_text())
	for fr in m["frames"]:
		var a := String(fr["asset"])
		var k := int(fr["index"])
		if not imp_frames.has(a):
			imp_frames[a] = {}
		if not imp_frames[a].has(k):
			imp_frames[a][k] = []
		imp_frames[a][k].append(fr)
	for a in imp_frames:
		for k in imp_frames[a]:
			(imp_frames[a][k] as Array).sort_custom(func(x, y): return float(x["ppm"]) > float(y["ppm"]))
	imp_mat.shader = load("res://render3d/shaders/vista_impostor.gdshader")
	imp_mat.set_shader_parameter("r3_page_h", int(m.get("r3_rows", 0)))
	imp_mat.set_shader_parameter("atlas_a", ImageTexture.create_from_image(load(ATLAS_A)))
	imp_mat.set_shader_parameter("atlas_n", ImageTexture.create_from_image(load(ATLAS_N)))
	_common(imp_mat)
	if OS.get_cmdline_user_args().has("--debug_quads"):
		imp_mat.set_shader_parameter("debug_quads", true)


## Round 3's region props and rocks (PROPS_R3), or an empty dictionary.
var _r3_props := {}
func _round3_props() -> Dictionary:
	if _r3_props.is_empty() and FileAccess.file_exists(PROPS_R3):
		var f := FileAccess.open(PROPS_R3, FileAccess.READ)
		_r3_props = JSON.parse_string(f.get_as_text())
	return _r3_props


## The baked stand-in for a catalog prop name, and the scale that gives the prop's height.
func _imp_for(name: String, height: float, seed: float) -> Array:
	for hero in IMP_HERO:
		if name == hero:
			return [hero, 1.0]
	for key in ["maple_red", "sugi", "pine", "konara", "buna", "maple", "take", "kaki"]:
		if name.begins_with(key):
			var opts: Array = IMP_KIND[key]
			var best: Array = opts[0]
			for o in opts:
				if absf(float(o[1]) - height) < absf(float(best[1]) - height):
					best = o
			if opts.size() > 1 and absf(float(opts[0][1]) - float(opts[1][1])) < 5.0 and seed > 0.5:
				best = opts[1]
			return [best[0], height / float(best[1])]
	return []


func _build_impostors() -> void:
	_load_impostors()
	if imp_frames.is_empty():
		return
	# the region's props as the sample placed them (round 5: its trees as round 3 placed them, its
	# heroes as they stand now)
	var region: Array = props
	var r3 := _round3_props()
	if r3.has("trees"):
		region = []
		for pr in props:
			if String(pr[0]) in IMP_HERO:
				region.append(pr)
		for t in r3["trees"]:
			if String(t[0]) in IMP_HERO:
				continue
			region.append([String(t[0]), Vector3(float(t[1]), ground_h(float(t[1]), float(t[2])), float(t[2])), float(t[3]), float(t[4]), float(t[5])])
	for pr in region:
		var name: String = pr[0]
		var pos: Vector3 = pr[1]
		var seed := fposmod(pos.x * 0.137 + pos.z * 0.071, 1.0)
		var m := _imp_for(name, float(pr[4]), seed)
		if m.is_empty() or not imp_frames.has(m[0]):
			continue
		# on the vista's own ground (the region's terrain and the mid map can differ by a little)
		var gp := Vector3(pos.x, ground_h(pos.x, pos.z), pos.z)
		if absf(gp.y - pos.y) > _float_max:
			_float_max = absf(gp.y - pos.y)
		imp_rows.append([gp, m[0], float(pr[2]), float(m[1]) * (1.0 if m[0] in IMP_HERO else 1.0)])
	# the woods around the region (inside the mist), as the land's generator spread them
	for t in data.get("trees", []):
		var kind := int(t[3])
		var h := float(t[4])
		var seed := float(t[5]) / 1000.0
		var nm := ""
		match kind:
			0:
				nm = "sugi_a" if seed < 0.5 else "sugi_d"
			1:
				nm = "pine_a" if seed < 0.5 else "pine_c"
			2:
				nm = "konara_a" if seed < 0.35 else ("konara_c" if seed < 0.65 else "buna_a")
			3:
				nm = "take_c"
			4:
				nm = "maple_red_a" if seed < 0.4 else "maple_a"
		var hh: float = BAKED_H[nm]
		# stood on the ground the vista draws, and never in a paddy, a pond, a field or on a road
		# (the woods were spread before the lower layer's terraces were cut: some stood in the air)
		var tx := float(t[0])
		var tz := float(t[2])
		if _open_ground(tx, tz):
			_float_dropped += 1
			continue
		var gy := ground_h(tx, tz)
		if absf(gy - float(t[1])) > _float_max:
			_float_max = absf(gy - float(t[1]))
		imp_rows.append([Vector3(tx, gy, tz), nm, seed * TAU, h / hh])
	imp_mm.transform_format = MultiMesh.TRANSFORM_3D
	imp_mm.use_custom_data = true
	imp_mm.mesh = _uv_quad()
	imp_mm.instance_count = imp_rows.size()
	for i in imp_rows.size():
		imp_mm.set_instance_transform(i, Transform3D(Basis(), imp_rows[i][0]))
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = imp_mm
	mi.material_override = imp_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)
	print("VISTA impostors=", imp_rows.size(), " regrounded max_dy=%.2f dropped_on_open_ground=%d" % [_float_max, _float_dropped])


## A quad whose UV (0, 0) is its top-left corner (the vertex shaders build it on screen).
func _uv_quad() -> ArrayMesh:
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(1, 1, 0), Vector3(0, 1, 0)])
	arr[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arr[Mesh.ARRAY_NORMAL] = PackedVector3Array([Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK])
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 2, 1, 0, 3, 2])
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	m.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	return m


## Choose every impostor's frame for a camera position: the direction nearest the camera's and the
## level of detail nearest its size on screen (texel for pixel). Trees too near the camera for the
## finest level are left out (the camera stands among them).
func _place_impostors(cam_at: Vector3) -> void:
	if imp_rows.is_empty() or cam_at.distance_to(_imp_cam) < 0.01:
		return
	_imp_cam = cam_at
	var ppr := px_per_rad()
	for i in imp_rows.size():
		var r: Array = imp_rows[i]
		var pos: Vector3 = r[0]
		var asset: String = r[1]
		var yaw: float = r[2]
		var scale: float = r[3]
		var d := cam_at - pos
		var want := ppr / maxf(d.length(), 0.1) * scale
		var phi := atan2(d.x, d.z)
		var sets: Dictionary = imp_frames[asset]
		var list: Array
		if sets.has(-1):
			# single views: the one nearest the direction
			var best_a := INF
			for fr in sets[-1]:
				var da := absf(wrapf(phi - yaw - deg_to_rad(float(fr["angle"])), -PI, PI))
				if da < best_a - 1e-4:
					best_a = da
			list = []
			for fr in sets[-1]:
				if absf(absf(wrapf(phi - yaw - deg_to_rad(float(fr["angle"])), -PI, PI)) - best_a) < 1e-3:
					list.append(fr)
		else:
			var nang := sets.size()
			var k := posmod(roundi((phi - yaw) / (TAU / nang)), nang)
			list = sets[k]
		var pick: Dictionary = {}
		var best := INF
		for fr in list:
			var e := absf(log(float(fr["ppm"]) / want))
			if e < best:
				best = e
				pick = fr
		# (the trees round 3 drew, no more: round 3 left out those too near for its finest level, 14.1
		# px per metre at its 371 px per radian; the finer levels since are for drawing the ones it
		# kept at round 3's frame at 640x360, G5R3-16)
		var top3 := 0.0
		for fr in list:
			if float(fr["ppm"]) < 14.2:
				top3 = maxf(top3, float(fr["ppm"]))
		var want3 := want * 371.0 / ppr
		var bas := Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO)
		var fyaw := 0.0
		if not pick.is_empty() and want3 < top3 * 1.3 and want > float(list[-1]["ppm"]) * 0.5:
			var rc: Array = pick["rect"]
			var pv: Array = pick["pivot"]
			bas = Basis(Vector3(rc[0], rc[1], 0.0), Vector3(rc[2], rc[3], 0.0), Vector3(pv[0], pv[1], 0.0))
			fyaw = yaw + deg_to_rad(float(pick["angle"]))
		imp_mm.set_instance_transform(i, Transform3D(bas, pos))
		imp_mm.set_instance_custom_data(i, Color(0.0, 0.0, 0.0, fyaw))


## The lower layer's water-wheel: a signed-distance silhouette (vista_tree)
func _build_shapes() -> void:
	var lm: Dictionary = data["landmarks"]
	var hs0: Array = lm["houses"][0]
	_tree(hs0[0] + 5.0, hs0[1], hs0[2] + 2.0, 8, 3.4, 3.4, 0.5)
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


# ------------------------------------------------------------------------------------------------
# the rocks of the lookout (the region's own rock shapes, now seen from her eye)

func _build_rocks() -> void:
	var rocks := W3Rocks.new()
	rocks.terrain = terrain
	var shapes := {}
	var m := _mat("vista_solid")
	# (round 5: round 3's rocks, as its sample placed them: the lookout's foreground as it was)
	var r3 := _round3_props()
	var plist: Array = r3["rocks"] if r3.has("rocks") else terrain.info["placements"]
	for p in plist:
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
	puff_src.append([Vector3(kl.x + 1.4, ky + 4.0, kl.z - 0.8), 2.4, 0, 0.0])
	# the tower's red light
	var tw: Array = lm["tower"]
	var lst := SurfaceTool.new()
	lst.begin(Mesh.PRIMITIVE_TRIANGLES)
	# (a beacon seen from half a kilometre: two or three pixels, so its blink reads)
	_box(lst, Vector3(tw[0], float(tw[1]) + TOWER_H + 3.4, tw[2]), Vector3(2.6, 2.6, 2.6), Color(1, 0.2, 0.15))
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
	puff_src.append([Vector3(foot[0], float(foot[1]) + 2.0, foot[2]), 1.6, 2, 0.0])
	# the hot spring's steam
	var hsp: Array = lm["hot_spring"]
	puff_src.append([Vector3(hsp[0], float(hsp[1]) + 1.0, hsp[2]), 1.4, 1, 0.0])


# ------------------------------------------------------------------------------------------------
# the plain's villages and town (tiny sprites built in place: vista_house), the railway's viaduct
# and iron bridge, the suspension bridge and the 「隔」 tower (members never thinner than a pixel:
# vista_line), the ruined temple's hall (vista_solid)

# roofs: silver-grey tiles (light in the sun), thatch, rust-red tin, blue tin
# roofs (round 5, G5R3-1: the user took round 3's villages for ponds, "我上一個版本把這些聚落的點誤認成了水泊":
# their silver-grey and blue tin roofs were the colour of the flooded paddies and the river under the
# haze). Now the warm greys and browns of old tiles and thatch, a few red-brown tin roofs: a village
# reads as a cluster of warm dark specks on the green, never pale and blue like water.
# (light ones mostly: a village from afar is a speckle of light, warm pixels on the green, as in
# round 3, which the user liked; only no longer the pale blue-grey of water)
# weathered tile (light warm grey), old dark tile, thatch in the sun (straw), old thatch, red-brown tin
const ROOFS := [Color(0.64, 0.59, 0.53), Color(0.42, 0.38, 0.35), Color(0.74, 0.63, 0.45), Color(0.60, 0.51, 0.38), Color(0.56, 0.34, 0.26)]
const TOWER_H := 34.0
var house_mat: ShaderMaterial
var line_mat: ShaderMaterial
var lamp_src: W3Lamps                 # the top-down world's lamps (handed over by the sample)
var line_rows: Array = []            # [from, to, half width m, min px, side shade, emission, colour]


func _build_plain() -> void:
	var hs: Array = data.get("plain_houses", [])
	if hs.is_empty():
		return
	var lp: Array = data.get("plain_lamps", [])
	# the lower layer's farmhouses (thatch) join the plain's houses
	hs = hs.duplicate()
	for k in (data["landmarks"].get("houses", []) as Array).size():
		var f: Array = data["landmarks"]["houses"][k]
		hs.append([f[0], f[1], f[2], f[3], 11.0, 7.5, 6.0, 1, 400 + k * 212, -1])
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = _uv_quad()
	mm.instance_count = hs.size() + lp.size()
	# street lamps: a light only, at night (custom width < 0)
	for j in lp.size():
		var l: Array = lp[j]
		mm.set_instance_transform(hs.size() + j, Transform3D(Basis(), Vector3(l[0], float(l[1]) + 4.0, l[2])))
		mm.set_instance_color(hs.size() + j, Color(1.0, 0.8, 0.5))
		mm.set_instance_custom_data(hs.size() + j, Color(-1.0, 1.0, 1.0, fposmod(float(j) * 0.618, 1.0)))
	for i in hs.size():
		var h: Array = hs[i]
		mm.set_instance_transform(i, Transform3D(Basis(), Vector3(h[0], h[1], h[2])))
		var k := int(h[7])
		# (the town's roofs are mostly tiles, light and dark; the villages mostly thatch, a tin roof here
		# and there)
		var rs := fposmod(float(h[8]) * 0.37, 1.0)
		var roof: Color
		if int(h[9]) == 0:
			roof = ROOFS[0] if rs < 0.5 else (ROOFS[1] if rs < 0.85 else ROOFS[4])
		else:
			roof = ROOFS[2] if rs < 0.45 else (ROOFS[3] if rs < 0.8 else (ROOFS[1] if rs < 0.93 else ROOFS[4]))
		mm.set_instance_color(i, roof)
		mm.set_instance_custom_data(i, Color(h[4], h[5], h[6], float(h[8]) / 1000.0))
	house_mat = _mat("vista_house")
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = mm
	mi.material_override = house_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)


func _plain_at(x: float, z: float) -> Color:
	var pd: Dictionary = data["plain"]
	if _plain_img == null:
		_plain_img = load("res://world3d/terrain/saddle/" + String(pd["file"]))
	var i := clampi(roundi((x - float(pd["x0"])) / float(pd["cell"])), 0, int(pd["nx"]) - 1)
	var j := clampi(roundi((z - float(pd["z0"])) / float(pd["cell"])), 0, int(pd["nz"]) - 1)
	return _plain_img.get_pixel(i, j)


var _plain_img: Image


func _line(a: Vector3, b: Vector3, hw: float, min_px: float, col: Color, side := 0.0, em := 0.0) -> void:
	line_rows.append([a, b, hw, min_px, side, em, col])


## The plain's lamplight: on with the dusk (the first windows before sunset), all on at night, off
## again at dawn (round 5: the villages' scattered windows and the old road's lamps; the city is gone).
static func city_lights_at(h: float) -> float:
	h = fposmod(h, 24.0)
	return maxf(smoothstep(16.9, 18.4, h), 1.0 - smoothstep(5.2, 6.4, h))


func _build_lines() -> void:
	var lm: Dictionary = data["landmarks"]
	# the railway: a red-brick viaduct across the plain where the deck stands high over the ground,
	# an embankment's edge where it runs low
	var rail: Array = data.get("railway", [])
	var brick := Color(0.52, 0.31, 0.24)
	for i in rail.size() - 1:
		var a: Array = rail[i]
		var b: Array = rail[i + 1]
		var pa := Vector3(a[0], a[1], a[2])
		var pb := Vector3(b[0], b[1], b[2])
		_line(pa, pb, 2.6, 1.6, brick)
		var clear := float(a[1]) - float(a[3])
		if clear > 5.0:
			_line(Vector3(a[0], a[3], a[2]), pa, 1.8, 1.0, brick, 0.4)
	# the iron bridge over the canyon: a through truss, dark iron
	var ib: Array = lm["iron_bridge"]
	var i0 := Vector3(ib[0][0], ib[0][1], ib[0][2])
	var i1 := Vector3(ib[1][0], ib[1][1], ib[1][2])
	var deck_y := minf(i0.y, i1.y)
	i0.y = deck_y
	i1.y = deck_y
	var iron := Color(0.24, 0.26, 0.3)
	var up := Vector3(0, 6.0, 0)
	_line(i0, i1, 0.5, 1.0, iron)
	_line(i0 + up, i1 + up, 0.35, 1.0, iron)
	var n := 6
	for k in n:
		var t0 := float(k) / n
		var t1 := float(k + 1) / n
		var q0 := i0.lerp(i1, t0)
		var q1 := i0.lerp(i1, t1)
		_line(q0, q0 + up, 0.25, 0.0, iron)
		_line(q0 + (up if k % 2 == 0 else Vector3.ZERO), q1 + (Vector3.ZERO if k % 2 == 0 else up), 0.22, 0.0, iron)
	# the suspension bridge: posts at both rims, the deck and two hand ropes sagging between them
	var sb: Array = lm["suspension_bridge"]
	var s0 := Vector3(sb[0][0], sb[0][1], sb[0][2])
	var s1 := Vector3(sb[1][0], sb[1][1], sb[1][2])
	var wood := Color(0.4, 0.33, 0.26)
	var rope := Color(0.58, 0.53, 0.44)
	var across := (s1 - s0).cross(Vector3.UP).normalized() * 0.8
	for e in [s0, s1]:
		for sd in [-1.0, 1.0]:
			_line(e + across * sd, e + across * sd + Vector3(0, 2.6, 0), 0.15, 1.0, wood)
	var segs := 10
	for k in segs:
		var t0 := float(k) / segs
		var t1 := float(k + 1) / segs
		var sag0 := 4.0 * t0 * (1.0 - t0)
		var sag1 := 4.0 * t1 * (1.0 - t1)
		var d0 := s0.lerp(s1, t0) - Vector3(0, 2.2 * sag0, 0)
		var d1 := s0.lerp(s1, t1) - Vector3(0, 2.2 * sag1, 0)
		_line(d0, d1, 0.6, 1.0, wood)
		for sd in [-1.0, 1.0]:
			_line(d0 + across * sd + Vector3(0, 1.1 + 1.2 * sag0, 0), d1 + across * sd + Vector3(0, 1.1 + 1.2 * sag1, 0), 0.05, 0.0, rope)
	# the 「隔」 tower: four legs from a wide foot to a narrow platform, rings and crossed braces, a
	# mast with the red light (vista3d red_light) on top. Old steel, the colour of rust.
	var tw: Array = lm["tower"]
	var base := Vector3(tw[0], float(tw[1]) - 0.5, tw[2])
	var steel := Color(0.42, 0.29, 0.24)
	var corners := [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]
	var levels := [0.0, 7.0, 14.0, 20.0, 25.5, 30.0, TOWER_H]
	var half := func(y: float) -> float: return lerpf(3.4, 0.9, y / TOWER_H)
	for c in 4:
		var ca: Vector2 = corners[c]
		var cb: Vector2 = corners[(c + 1) % 4]
		for li in levels.size() - 1:
			var y0: float = levels[li]
			var y1: float = levels[li + 1]
			var h0: float = half.call(y0)
			var h1: float = half.call(y1)
			var a0 := base + Vector3(ca.x * h0, y0, ca.y * h0)
			var a1 := base + Vector3(ca.x * h1, y1, ca.y * h1)
			var b0 := base + Vector3(cb.x * h0, y0, cb.y * h0)
			var b1 := base + Vector3(cb.x * h1, y1, cb.y * h1)
			_line(a0, a1, 0.3, 1.0, steel)
			_line(a1, b1, 0.18, 0.0, steel)
			_line(a0, b1, 0.12, 0.0, steel)
			_line(b0, a1, 0.12, 0.0, steel)
	var top := base + Vector3(0, TOWER_H, 0)
	_line(top + Vector3(-1.6, 0, 0), top + Vector3(1.6, 0, 0), 0.4, 1.0, steel)
	_line(top, top + Vector3(0, 3.0, 0), 0.15, 1.0, steel)
	# the home's lanterns (the top-down world's lamps): a glowing mark each, lit with them
	if lamp_src:
		for l in lamp_src.lamps:
			if l["manual"]:
				continue
			var lp: Vector3 = l["pos"]
			var lc: Color = l["col"]
			var e := maxf(lc.r, maxf(lc.g, lc.b))
			var tint := Color(lc.r / e, lc.g / e, lc.b / e) if e > 0.0 else Color(1, 0.7, 0.4)
			_line(lp - Vector3(0, 0.25, 0), lp + Vector3(0, 0.25, 0), 0.18, 2.0, tint.lerp(Color(1.0, 0.86, 0.6), 0.4), 2.0, 2.4)
	if line_rows.is_empty():
		return
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = _uv_quad()
	mm.instance_count = line_rows.size()
	for i in line_rows.size():
		var r: Array = line_rows[i]
		var a: Vector3 = r[0]
		var b: Vector3 = r[1]
		mm.set_instance_transform(i, Transform3D(Basis(a, b, Vector3(r[2], r[3], r[4])), (a + b) * 0.5))
		mm.set_instance_color(i, r[6])
		mm.set_instance_custom_data(i, Color(r[5], 0.0, 0.0, 0.0))
	line_mat = _mat("vista_line")
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = mm
	mi.material_override = line_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)


## The ruined temple's hall on the summit's shoulder: a stone base, white walls between dark posts,
## and the great hipped-and-gabled roof of grey tiles with its ends lifted (from the look back, a roof
## breaking the skyline between the tower and the great camphor).
func _build_temple() -> void:
	var lm: Dictionary = data["landmarks"]
	if not lm.has("temple"):
		return
	var t: Array = lm["temple"]
	var o := Vector3(t[0], float(t[1]), t[2])
	var yaw := float(t[3])
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bas := Basis(Vector3.UP, yaw)
	var W := 16.0
	var D := 12.0
	_obox(st, o, bas, Vector3(0, 0.6, 0), Vector3(W + 6.0, 1.2, D + 6.0), Color(0.56, 0.54, 0.5))
	_obox(st, o, bas, Vector3(0, 3.6, 0), Vector3(W, 4.8, D), Color(0.8, 0.77, 0.7))
	for i in 6:
		var x := lerpf(-W * 0.5, W * 0.5, float(i) / 5.0)
		_obox(st, o, bas, Vector3(x, 3.6, D * 0.5 + 0.05), Vector3(0.6, 4.8, 0.3), Color(0.3, 0.22, 0.18))
	# the roof: a hip below, a gable above, the eaves deep and their corners lifted
	var ey := 6.2
	var ov := 3.4
	var rw := W * 0.5 + ov
	var rd := D * 0.5 + ov
	var lift := 2.0
	var c0 := [Vector3(-rw, ey + lift, -rd), Vector3(rw, ey + lift, -rd), Vector3(rw, ey + lift, rd), Vector3(-rw, ey + lift, rd)]
	var mid0 := [Vector3(0, ey, -rd), Vector3(rw, ey, 0), Vector3(0, ey, rd), Vector3(-rw, ey, 0)]
	var gy := ey + 5.6
	var g := [Vector3(-W * 0.32, gy, -D * 0.2), Vector3(W * 0.32, gy, -D * 0.2), Vector3(W * 0.32, gy, D * 0.2), Vector3(-W * 0.32, gy, D * 0.2)]
	var ry := gy + 3.4
	var ridge := [Vector3(-W * 0.36, ry, 0), Vector3(W * 0.36, ry, 0)]
	var tile := Color(0.24, 0.25, 0.28)
	var tile_l := Color(0.34, 0.35, 0.38)
	# lower hip: each side from the eave (corner, middle, corner) up to the gable's foot
	for side in 4:
		var a: Vector3 = c0[side]
		var m: Vector3 = mid0[side]
		var b: Vector3 = c0[(side + 1) % 4]
		var ga: Vector3 = g[side]
		var gb: Vector3 = g[(side + 1) % 4]
		var col := tile_l if side == 2 else tile
		_otri(st, o, bas, a, m, ga, col)
		_otri(st, o, bas, m, gb, ga, col)
		_otri(st, o, bas, m, b, gb, col)
	# upper gable roof: two slopes to the ridge, two gable ends (lighter: the gable's board)
	_otri(st, o, bas, g[0], g[1], ridge[1], tile)
	_otri(st, o, bas, g[0], ridge[1], ridge[0], tile)
	_otri(st, o, bas, g[2], g[3], ridge[0], tile_l)
	_otri(st, o, bas, g[2], ridge[0], ridge[1], tile_l)
	_otri(st, o, bas, g[3], g[0], ridge[0], Color(0.62, 0.58, 0.5))
	_otri(st, o, bas, g[1], g[2], ridge[1], Color(0.62, 0.58, 0.5))
	# the ridge and its raised ends
	_obox(st, o, bas, Vector3(0, ry + 0.25, 0), Vector3(W * 0.76, 0.5, 0.7), Color(0.2, 0.21, 0.23))
	for sx in [-1.0, 1.0]:
		_obox(st, o, bas, Vector3(sx * W * 0.38, ry + 0.7, 0), Vector3(0.9, 1.4, 0.8), Color(0.2, 0.21, 0.23))
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = _mat("vista_solid")
	root.add_child(mi)


## A box turned by a basis about an origin (the temple's parts).
func _obox(st: SurfaceTool, o: Vector3, b: Basis, c: Vector3, sz: Vector3, col: Color) -> void:
	var h := sz * 0.5
	var p := []
	for k in 8:
		p.append(o + b * (c + Vector3(h.x * (1 if k & 1 else -1), h.y * (1 if k & 2 else -1), h.z * (1 if k & 4 else -1))))
	for f in [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]:
		_oquad(st, p[f[0]], p[f[1]], p[f[2]], p[f[3]], col, o + b * c)


func _oquad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, col: Color, ctr: Vector3) -> void:
	for tri in [[a, b, c], [a, c, d]]:
		var x0: Vector3 = tri[0]
		var x1: Vector3 = tri[1]
		var x2: Vector3 = tri[2]
		# outward and clockwise seen from outside (Godot's front faces)
		if (x1 - x0).cross(x2 - x0).dot((x0 + x1 + x2) / 3.0 - ctr) > 0.0:
			var tmp := x1
			x1 = x2
			x2 = tmp
		for v in [x0, x1, x2]:
			st.set_color(col)
			st.add_vertex(v)


func _otri(st: SurfaceTool, o: Vector3, b: Basis, a: Vector3, m: Vector3, c: Vector3, col: Color) -> void:
	var pa := o + b * a
	var pm := o + b * m
	var pc := o + b * c
	# facing up and out (a roof seen from above and the side)
	if (pm - pa).cross(pc - pa).y > 0.0:
		var tmp := pm
		pm = pc
		pc = tmp
	for v in [pa, pm, pc]:
		st.set_color(col)
		st.add_vertex(v)


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
# her and さぢ on the lookout, seen from behind (the camera stands back on the spur at round 3's
# distance; they are drawn at the land's scale there, fig_ppm)

var figure_mats: Array[ShaderMaterial] = []
var feet := Vector3.ZERO

# where she can turn her head: out over the land (east by the kiln's smoke round the plain to the
# west and the waterfall's mist), or back home (the saddle under the great camphor); past either
# end the view goes through the mist's white to the other place
const OUT_YAW := Vector2(95.0, 292.0)
const HOME_YAW := Vector2(-12.0, 60.0)
const HOME_BEARING := 22.0          # the look back: between the hut and the great camphor
const HOME_CAM_H := 4.0             # the camera's height over her feet when she looks back
const OUT_CAM_BEARING := -12.5      # where the camera stands from her when she looks out (NNW)
const OUT_CAM_ELEV := 28.0          # and how high: her back from above, the land below past the brow
var sector := 0                     # 0 out, 1 home
var veil := 0.0                     # the mist's white over the picture (the ways in and out)
var shown := false                  # the view is on screen (under the veil)
var _trans := ""                    # "in", "out", "flip" while one runs
var _trans_t := 0.0
var _switched := false
var _flip_sector := 0
var _flip_yaw := 0.0
var _push := 0.0                    # seconds she has turned against the end of the range
const VEIL_IN := 0.3
const VEIL_OUT := 0.35


func _build_figures() -> void:
	var f := FileAccess.open("res://world3d/sprites/characters.json", FileAccess.READ)
	if f == null:
		return
	var chars: Dictionary = JSON.parse_string(f.get_as_text())
	for spec in [["tsuzumi", "load", Vector3(0, 0, 0)], ["saji", "main", Vector3(0.85, 0, -0.35)]]:
		var m := _mat("vista_figure")
		if spec[0] == "tsuzumi" and _build_fig3d():
			# her: the 3D model (round 4: the lead asked whether the view still showed the old sprite),
			# drawn upright through an orthographic camera of its own at the view's scale (20 px per
			# metre), its picture used like a sprite's frame
			m.set_shader_parameter("sheet", fig_vp.get_texture())
			m.set_shader_parameter("frame_rect", Vector4(0, 0, FIG_PX.x, FIG_PX.y))
			m.set_shader_parameter("pivot_px", FIG_FOOT)
			m.set_shader_parameter("baked", true)
			m.set_shader_parameter("sheet_ppm", fig_ppm())
			m.set_shader_parameter("px_scale", 1.0)
			fig_mat = m
		else:
			var c: Dictionary = chars[spec[0]]
			var sh: Dictionary = c["sheets"][spec[1]]
			var a: Dictionary = sh["anims"]["idle"]["back"]
			var fw := int(c["frame"][0])
			var fh := int(c["frame"][1])
			m.set_shader_parameter("sheet", CharSprite3D.pixel_texture("res://world3d/sprites/%s.png" % sh["file"]))
			m.set_shader_parameter("frame_rect", Vector4(int(a["col"]) * fw, int(a["row"]) * fh, fw, fh))
			m.set_shader_parameter("pivot_px", Vector2(c["pivot"][0], c["pivot"][1]))
			# (her sprite sheets are 20 px per metre: さぢ at the land's scale is a third bigger)
			m.set_shader_parameter("sheet_ppm", 20.0)
			m.set_shader_parameter("px_scale", fig_ppm() / 20.0)
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


# her 3D model in the view: a world of its own (her, the sun) seen by an orthographic camera from the
# view's eye, at the land's scale at her distance (fig_ppm); she turns toward where the view looks
const FIG_PX := Vector2i(54, 70)       # the picture's size (native px: 40 x 52 at 20 px/m, at fig_ppm)
const FIG_FOOT := Vector2(27.0, 63.0)  # her feet in it (px from its top left)
var fig_vp: SubViewport
var fig_cam: Camera3D
var fig_sun: DirectionalLight3D
var fig_fill: DirectionalLight3D
var fig_char: Character3D
var fig_mat: ShaderMaterial
var _fig_eye := Vector3.INF
var _fig_started := false


func _build_fig3d() -> bool:
	if not FileAccess.file_exists("res://characters/kasasagi/rig.json") or _vdebug.has("sprites"):
		return false
	fig_vp = SubViewport.new()
	fig_vp.name = "VistaFigure"
	fig_vp.size = FIG_PX
	fig_vp.own_world_3d = true
	fig_vp.transparent_bg = true
	fig_vp.msaa_3d = Viewport.MSAA_DISABLED
	fig_vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	fig_vp.use_taa = false
	fig_vp.positional_shadow_atlas_size = 0
	fig_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(fig_vp)
	var w := Node3D.new()
	w.name = "Figure"
	fig_vp.add_child(w)
	fig_char = Character3D.new()
	w.add_child(fig_char)
	fig_char.setup("kasasagi")
	fig_char.ground_y = 0.0
	for mm in fig_char.meshes:
		mm.set_instance_shader_parameter("c3_no_lean", 1.0)
		mm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	fig_cam = Camera3D.new()
	fig_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	fig_cam.keep_aspect = Camera3D.KEEP_HEIGHT
	fig_cam.size = float(FIG_PX.y) / fig_ppm()
	fig_cam.near = 0.05
	fig_cam.far = 40.0
	fig_cam.current = true
	fig_vp.add_child(fig_cam)
	fig_sun = DirectionalLight3D.new()
	fig_sun.light_specular = 0.0
	fig_sun.shadow_enabled = true
	fig_sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	fig_sun.directional_shadow_max_distance = 8.0
	fig_vp.add_child(fig_sun)
	# (the character protection's fill from the camera's side: the view sees her back, which the sun
	# of the view to the south leaves in shade all day)
	fig_fill = DirectionalLight3D.new()
	fig_fill.light_specular = 0.0
	fig_fill.shadow_enabled = false
	fig_vp.add_child(fig_fill)
	return true


## Every frame while the view is shown: her camera from the view's eye (the picture's feet pixel
## fixed), the sun, and where she faces (where the view looks, turned at most 55 degrees from her back
## to the camera: the face itself is the top-down view's, pixel stamps that only that camera draws).
func _update_fig3d(bearing: float) -> void:
	if fig_vp == null:
		return
	fig_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	fig_char.process_mode = Node.PROCESS_MODE_INHERIT
	var look := (feet + Vector3(0.0, 0.9, 0.0) - eye).normalized()
	if _fig_eye.distance_to(eye) > 0.01:
		_fig_eye = eye
		var up := (Vector3.UP - look * look.y).normalized()
		# the orthographic picture is centred on its middle: the feet FIG_FOOT px from its top left
		var below := (FIG_FOOT.y - float(FIG_PX.y) * 0.5) / fig_ppm()
		var right := look.cross(up).normalized()
		var aside := (FIG_FOOT.x - float(FIG_PX.x) * 0.5) / fig_ppm()
		var aim := up * below - right * aside
		fig_cam.look_at_from_position(aim - look * 12.0, aim, Vector3.UP)
	var cam_yaw := atan2(look.x, look.z)
	var b := deg_to_rad(bearing)
	var want := atan2(sin(b), -cos(b))
	var rel := clampf(wrapf(want - cam_yaw, -PI, PI), deg_to_rad(-55.0), deg_to_rad(55.0))
	fig_char.face_angle(cam_yaw + rel, not _fig_started)
	_fig_started = true
	fig_sun.global_transform = env.sun.global_transform
	fig_sun.light_color = env.sun.light_color
	fig_sun.light_energy = env.sun.light_energy
	# the fill: from the camera, a little above it, the sky's colour, about a third of the sun's
	# light by day and a share of the moon's at night
	var night := clampf(float(env.sample(env.hours)[11]), 0.0, 1.0)
	fig_fill.look_at_from_position(Vector3.ZERO, look + Vector3(0.0, -0.35, 0.0), Vector3.UP)
	fig_fill.light_color = Color(0.86, 0.9, 1.0).lerp(Color(0.6, 0.68, 0.95), night)
	fig_fill.light_energy = maxf(env.sun.light_energy, 0.25) * 0.38 * (1.0 - 0.5 * night)


func _pause_fig3d() -> void:
	if fig_vp == null:
		return
	fig_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	fig_char.process_mode = Node.PROCESS_MODE_DISABLED


## Where the camera stands: behind her, round 3's distance (CAM_DIST; round 3 chose it so that one
## 20 px/m sprite pixel was one screen pixel). Two places: looking out (up the spur north-north-west of her, 28 degrees above
## her, high enough to see the lower layer past the rock's brow) and looking back home (south of her,
## out over the drop, low, so the great camphor rises over the saddle). Within one the camera only
## turns in place (the impostors' frames, the marks' anchors and the band seams stay put).
func cam_pos() -> Vector3:
	var d := CAM_DIST
	if sector == 0:
		# up the spur behind her, high enough to see the lower layer past the rock's brow
		var b := deg_to_rad(OUT_CAM_BEARING)
		var el := deg_to_rad(OUT_CAM_ELEV)
		return feet + Vector3(0.0, 1.0, 0.0) + Vector3(sin(b) * cos(el), sin(el), -cos(b) * cos(el)) * d
	var hb := HOME_CAM_H
	var r := sqrt(maxf(d * d - hb * hb, 1.0))
	var b := deg_to_rad(HOME_BEARING + 180.0)
	return feet + Vector3(sin(b) * r, hb, -cos(b) * r)


# ------------------------------------------------------------------------------------------------
# puffs: smoke, steam, mist, the waterfall sheet

func _build_puffs() -> void:
	puff_mm.transform_format = MultiMesh.TRANSFORM_3D
	puff_mm.use_colors = true
	puff_mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	puff_mm.mesh = q
	puff_mm.instance_count = 900
	puff_mm.visible_instance_count = 0
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = puff_mm
	var m := _mat("vista_puff")
	puff_mat = m
	m.render_priority = 2
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-16000, -600, -16000), Vector3(32000, 2600, 32000))
	root.add_child(mi)
	# warm up so the columns stand when the view opens
	for i in 480:
		_step_puffs(0.1)
	# (nothing moves in the 遠化: a source there keeps the column it had, still; vista_puff draws it
	# as the paper)
	var still := 0
	for s in puff_src:
		if past_m((s[0] as Vector3).x, (s[0] as Vector3).z) > 0.0:
			s[1] = 0.0
			still += 1
	for pf in puffs:
		if past_m((pf[0] as Vector3).x, (pf[0] as Vector3).z) > 0.0:
			pf.append(true)
	print("VISTA puffs sources=%d still_in_enka=%d" % [puff_src.size(), still])


func _step_puffs(dt: float) -> void:
	var wind := Vector3(0.9, 0.0, 0.35) * (env.wind if env else 1.0)
	for s in puff_src:
		s[3] = float(s[3]) + dt * float(s[1])
		while float(s[3]) > 1.0:
			s[3] = float(s[3]) - 1.0
			var kind: int = s[2]
			var p: Vector3 = s[0]
			# smoke from the kiln: a narrow column of small puffs widening as it rises; steam from the
			# hot spring; the waterfall's mist: a tall plume that climbs out of the canyon
			# (kind 4: a factory chimney's smoke on the plain, kilometres out: big slow puffs)
			var col := Color(0.74, 0.73, 0.74, 1.0) if kind == 0 else (Color(0.93, 0.94, 0.95, 0.9) if kind == 1 else (Color(0.86, 0.86, 0.85, 0.9) if kind == 4 else Color(0.92, 0.94, 0.96, 0.8)))
			var life := 14.0 if kind == 0 else (8.0 if kind == 1 else (60.0 if kind == 4 else 42.0))
			var up := 1.5 if kind == 0 else (0.8 if kind == 1 else (2.6 if kind == 4 else 5.0))
			var vel := Vector3(rng.randf_range(-0.15, 0.15), up, rng.randf_range(-0.15, 0.15))
			var sz := 0.9 if kind == 0 else (2.2 if kind == 1 else (12.0 if kind == 4 else 7.0))
			var jit := 0.3 if kind == 0 else (0.4 if kind == 1 else (2.0 if kind == 4 else 5.0))
			puffs.append([p + Vector3(rng.randf_range(-jit, jit), 0, rng.randf_range(-jit, jit)), vel, life, 0.0, sz, kind, rng.randf(), col, 0.0])
	var i := 0
	while i < puffs.size():
		var pf: Array = puffs[i]
		if pf.size() > 9:
			i += 1
			continue
		pf[3] = float(pf[3]) + dt
		if float(pf[3]) > float(pf[2]):
			puffs.remove_at(i)
			continue
		if int(pf[5]) != 3:
			var age := float(pf[3]) / float(pf[2])
			var k := int(pf[5])
			# (the plume slows as it climbs and spreads; smoke and steam lean with the wind)
			var v: Vector3 = pf[1]
			if k == 2:
				v.y *= 1.0 - age * 0.7
			pf[0] = (pf[0] as Vector3) + (v + wind * age * (1.2 if k == 0 else (0.6 if k == 1 else (3.0 if k == 4 else 1.4)))) * dt
			pf[4] = float(pf[4]) + dt * (0.32 if k == 0 else (0.4 if k == 2 else (0.9 if k == 4 else 0.4))) * (1.6 if k == 2 else 1.0)
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


## Pixels per metre at her distance from the camera: she and さぢ are drawn at the land's scale there.
func fig_ppm() -> float:
	return px_per_rad() / CAM_DIST


## The pitch that suits a bearing: down over the land to the south (her feet stay in the frame),
## lifted toward the east (the kiln's smoke) and the west (the canyon's mist); looking back home, up
## a little, so the great camphor stands in the frame over her.
func pitch_for(bearing: float) -> float:
	if sector == 1:
		return 4.0
	# (her feet stay in the frame looking south; east and west the camera lifts toward the
	# kiln's smoke and the canyon's mist)
	var keys := [[95.0, -6.0], [130.0, -9.0], [180.0, -13.0], [228.0, -9.0], [248.0, -2.0], [292.0, -2.0]]
	for i in keys.size() - 1:
		var a: Array = keys[i]
		var b: Array = keys[i + 1]
		if bearing <= float(b[0]):
			return lerpf(float(a[1]), float(b[1]), smoothstep(float(a[0]), float(b[0]), bearing))
	return float(keys[-1][1])


## Show the view at once (stills), or hide it at once.
func show_now(sec: int, bearing: float) -> void:
	active = true
	shown = true
	veil = 0.0
	_trans = ""
	sector = sec
	yaw = bearing
	yaw_target = bearing
	amount = 1.0


func hide_now() -> void:
	active = false
	shown = false
	veil = 0.0
	_trans = ""
	amount = 0.0


## Go through the white to the other place (or to a bearing in this one).
func flip_to(sec: int, bearing: float) -> void:
	if _trans != "":
		return
	_trans = "flip"
	_trans_t = 0.0
	_switched = false
	_flip_sector = sec
	_flip_yaw = bearing


## She turns her head (dir -1 left / counter-clockwise, +1 right); held against the end of a range
## for a moment, she turns round to the other place.
func turn(dir: float, dt: float) -> void:
	if _trans != "" or not shown:
		return
	var rng_y := OUT_YAW if sector == 0 else HOME_YAW
	var t := yaw_target + dir * 55.0 * dt
	if t < rng_y.x or t > rng_y.y:
		_push += dt
		t = clampf(t, rng_y.x, rng_y.y)
		if _push > 0.35:
			_push = 0.0
			if sector == 0:
				flip_to(1, HOME_YAW.y if dir < 0.0 else HOME_YAW.x)
			else:
				flip_to(0, OUT_YAW.y if dir < 0.0 else OUT_YAW.x)
	else:
		_push = 0.0
	yaw_target = t


func _run_transition(dt: float) -> void:
	if _trans == "" and active and not shown:
		_trans = "in"
		_trans_t = 0.0
		_switched = false
	elif _trans == "" and not active and shown:
		_trans = "out"
		_trans_t = 0.0
		_switched = false
	if _trans == "":
		return
	_trans_t += dt
	if _trans_t < VEIL_IN:
		veil = _trans_t / VEIL_IN
		return
	if not _switched:
		_switched = true
		match _trans:
			"in":
				shown = true
			"out":
				shown = false
			"flip":
				sector = _flip_sector
				yaw = _flip_yaw
				yaw_target = _flip_yaw
	veil = clampf(1.0 - (_trans_t - VEIL_IN) / VEIL_OUT, 0.0, 1.0)
	if _trans_t >= VEIL_IN + VEIL_OUT:
		veil = 0.0
		_trans = ""


func update(dt: float) -> void:
	_t += dt
	if active and not built:
		build()
	_run_transition(dt)
	amount = 1.0 if shown else 0.0
	view.visible = shown or veil > 0.0
	display.set_shader_parameter("shown", shown)
	display.set_shader_parameter("veil", veil)
	var kv := _sky_at(env.hours)
	display.set_shader_parameter("veil_col", (kv[3] as Color).lerp(Color(0.95, 0.95, 0.94), 0.35))
	var audio := get_node_or_null("/root/Audio")
	if not shown:
		vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
		pv.vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		_pause_fig3d()
		if audio and _far_sent != 0.0:
			_far_sent = 0.0
			audio.call("far", 0.0)
		return
	# (the sound of the 遠化: as she turns her head toward it the wind, the birds and the insects
	# recede, hollow and far; turned back they return. Audio.far, no new sound)
	if audio:
		var fk := far_share(yaw, pitch_for(yaw)) if sector == 0 else 0.0
		if absf(fk - _far_sent) > 0.01:
			_far_sent = fk
			audio.call("far", fk)
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	# the world view underneath stops while the view covers it
	pv.vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	for k in ["lift", "gain", "saturation", "shadow_tone", "high_tone", "fade", "contrast"]:
		display.set_shader_parameter(k, pv.composite.get_shader_parameter(k))
	# (the view holds whole sunlit hillsides of leaves: the world's extra saturation would turn them
	# lime; the distance wants quieter colour anyway)
	# (round 5: the world's saturation as it is, as in round 3; round 4 capped it at 1.04)
	if _vdebug.has("nograde"):
		display.set_shader_parameter("lift", Vector3.ZERO)
		display.set_shader_parameter("gain", Vector3.ONE)
		display.set_shader_parameter("saturation", 1.0)
		display.set_shader_parameter("shadow_tone", Vector3.ZERO)
		display.set_shader_parameter("high_tone", Vector3.ZERO)
		display.set_shader_parameter("contrast", 0.0)
		display.set_shader_parameter("vignette", 0.0)
	# the view: turns toward the wanted bearing in whole pixels of its projection (vista_common: a
	# pixel is a fixed step of azimuth and elevation), so the whole picture moves by whole pixels
	yaw = lerpf(yaw, yaw_target, 1.0 - exp(-dt * 2.2))
	var ppr := px_per_rad()
	var step := rad_to_deg(1.0 / ppr)
	var yq := roundf(yaw / step) * step
	var pitch := roundf(pitch_for(yq) / step) * step
	eye = cam_pos()
	_place_impostors(eye)
	_update_fig3d(yq)
	var lat := Vector2(roundf(deg_to_rad(yq) * ppr), roundf(deg_to_rad(pitch) * ppr))
	var vc := Vector4(lat.x / ppr, lat.y / ppr, float(vp.size.x) * 0.5, float(vp.size.y) * 0.5)
	# (every frame, on every material: the eye moves when she turns round to the other place, and the
	# outline pass was made before the eye was known)
	for m in mats:
		m.set_shader_parameter("eye", eye)
		m.set_shader_parameter("v_cam", vc)
		m.set_shader_parameter("v_lat", lat)
	sky_mat.set_shader_parameter("view_ang", vc)
	display.set_shader_parameter("cam_cell", lat)
	# (the camera itself gives the lighting its view space and culls; its own perspective is not drawn)
	cam.position = eye
	cam.rotation = Vector3(deg_to_rad(pitch), -deg_to_rad(yq), 0.0)
	# the time of day: the same sun and globals as the world, the sky's own colours
	sun.light_color = env.sun.light_color
	sun.light_energy = env.sun.light_energy
	sun.global_transform = env.sun.global_transform
	var k := _sky_at(env.hours)
	var night := clampf(float(env.sample(env.hours)[11]), 0.0, 1.0)
	sky_mat.set_shader_parameter("zenith", k[1])
	var hz: Color = (k[2] as Color).lerp(Color(0.62, 0.64, 0.67), env.rain * 0.7)
	sky_mat.set_shader_parameter("horizon", hz)
	# (round 5: one horizon all round, as in round 3)
	sky_mat.set_shader_parameter("horizon_away", hz)
	sky_mat.set_shader_parameter("mist_col", k[3])
	sky_mat.set_shader_parameter("cloud_lit", k[4])
	sky_mat.set_shader_parameter("cloud_shade", k[5])
	sky_mat.set_shader_parameter("sun_dir", W3Env.sun_direction(env.hours))
	sky_mat.set_shader_parameter("sun_col", Color(1.0, 0.92, 0.75) if night < 0.5 else Color(0.9, 0.92, 1.0))
	sky_mat.set_shader_parameter("night", night)
	sky_mat.set_shader_parameter("dusk", clampf(1.0 - absf(env.hours - 17.7) / 1.3, 0.0, 1.0) * (1.0 - night))
	sky_mat.set_shader_parameter("px_per_rad", px_per_rad())
	sky_mat.set_shader_parameter("time", _t)
	# (clear enough that the plain's fields, river and villages read through it; mornings hazier)
	var haze_dist := lerpf(9000.0, 1500.0, env.rain) * lerpf(1.0, 0.82, clampf(1.0 - absf(env.hours - 6.8) / 2.2, 0.0, 1.0))
	# the 遠化's white: the lightest of the land (under white, so the ghost of the land in it and its
	# glowing edge still show after the grade), a dim pale glow in the dark
	# (the world's grade lifts and clips the light end: about 0.85 sRGB is the last value that keeps
	# its difference from its neighbours, so the white sits just under it and only its edge clips)
	# (a warm paper white, like a print faded in the sun: a cool white beside the haze read as water)
	# (round 5, G5R3-1: round 3's band again, "すやり霞")
	# (at night the 遠化's paper is as dark as the night, never a glow: its lines just legible)
	var fw := Color(0.66, 0.635, 0.59).lerp(Color(0.055, 0.06, 0.085), night)
	if env.hours > 16.5 and env.hours < 19.5:
		fw = fw.lerp(Color(0.68, 0.6, 0.52), clampf(1.0 - absf(env.hours - 17.8) / 1.3, 0.0, 1.0) * (1.0 - night))
	for m in mats:
		m.set_shader_parameter("haze_col", hz)
		m.set_shader_parameter("mist_col", k[3])
		m.set_shader_parameter("haze_dist", haze_dist)
		m.set_shader_parameter("far_white", Vector3(fw.r, fw.g, fw.b))
	# lights: the tower blinks red, the kiln glows at night
	# the tower's beacon: a second on, a second off (dark when off, so the blink reads from afar)
	var blink := 1.0 if fmod(_t, 2.0) < 1.0 else 0.04
	red_mat.set_shader_parameter("emission_energy", (1.6 + 3.0 * night) * blink)
	kiln_glow.set_shader_parameter("emission_energy", 0.4 + 2.4 * night)
	var lc := Vector3(env.sun.light_color.r, env.sun.light_color.g, env.sun.light_color.b) * env.sun.light_energy * 0.55
	var sky_v: Vector3 = Vector3(0.5, 0.55, 0.62) * (1.0 - night * 0.65)
	# (the rim on the sun's side of her outline: which side of the screen the sun is on)
	var sd := W3Env.sun_direction(env.hours)
	var right := cam.global_transform.basis.x
	var fig_rim := Color(1.0, 0.9, 0.74).lerp(Color(0.7, 0.78, 1.0), night)
	for fm in figure_mats:
		fm.set_shader_parameter("light_col", lc + sky_v)
		fm.set_shader_parameter("rim_side", 1.0 if sd.dot(right) >= 0.0 else -1.0)
		fm.set_shader_parameter("rim_col", Vector3(fig_rim.r, fig_rim.g, fig_rim.b))
	for m in [house_mat, line_mat]:
		if m:
			m.set_shader_parameter("light_col", lc * 1.6)
			m.set_shader_parameter("ambient_col", sky_v * 0.75)
	if house_mat:
		house_mat.set_shader_parameter("night", night)
	if puff_mat:
		# smoke and mist take the hour's light: warm at dusk, dim and blue at night
		var dusk_k := clampf(1.0 - absf(env.hours - 17.7) / 1.3, 0.0, 1.0) * (1.0 - night)
		var pk := Color(1, 1, 1).lerp(Color(1.0, 0.84, 0.7), dusk_k * 0.8).lerp(Color(0.1, 0.11, 0.16), night)
		puff_mat.set_shader_parameter("light_k", Vector3(pk.r, pk.g, pk.b))
	if line_mat and lamp_src:
		var on := 0.0
		for l in lamp_src.lamps:
			if not l["manual"]:
				on = maxf(on, float(l["on"]))
		line_mat.set_shader_parameter("lamp_on", on)
	var cl := city_lights_at(env.hours)
	for m in mats:
		m.set_shader_parameter("cloud_time", _t)
		m.set_shader_parameter("city_lights", cl)
	if cloud_inst and (_t - _cloud_sorted_t > 8.0 or _cloud_sorted_eye.distance_to(eye) > 1.0):
		_sort_clouds()

	if sea_mat:
		var lit_c: Color = k[4]
		var shade_c: Color = k[5]
		# (sRGB: the shader mixes the tones as painted)
		sea_mat.set_shader_parameter("lit_col", Vector3(lit_c.r, lit_c.g, lit_c.b))
		sea_mat.set_shader_parameter("shade_col", Vector3(shade_c.r, shade_c.g, shade_c.b))
		sea_mat.set_shader_parameter("deep_col", Vector3(shade_c.r * 0.78, shade_c.g * 0.81, shade_c.b * 0.9))
		var rim_c := lit_c.lerp(Color(1, 1, 1), 0.5)
		sea_mat.set_shader_parameter("rim_col", Vector3(rim_c.r, rim_c.g, rim_c.b))
		sea_mat.set_shader_parameter("night", night)
	if not _vdebug.is_empty():
		for m in mats:
			if _vdebug.has("nodrain"):
				m.set_shader_parameter("mist_max", 0.0)
			if _vdebug.has("nohaze"):
				m.set_shader_parameter("haze_dist", 1e9)
		if _vdebug.has("nocloud") and cloud_inst:
			cloud_inst.visible = false
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
