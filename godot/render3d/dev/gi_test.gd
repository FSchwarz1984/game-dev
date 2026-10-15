extends Node
## Internal test (never shipped): which of Forward+'s lighting features work with the art sample's
## camera (orthogonal, north, 55 degrees down, 120 m back, near 60 / far 190) at 640x360, and what
## they cost on the software rasteriser. Plain StandardMaterial3D, so only the engine is measured.
##   godot --path godot res://render3d/dev/gi_test.tscn -- --gi=sdfgi|voxel|none --vfog=1 --ssao=1
##        --ssil=1 --shot=/tmp/a.png --frames=40

var args := {}
var vp: SubViewport
var cam: Camera3D
var env: Environment
var frame := 0
var t0 := 0
var times: Array[float] = []
var _voxel: VoxelGI


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	vp = SubViewport.new()
	vp.size = Vector2i(640, 360)
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.own_world_3d = true
	add_child(vp)
	var view := TextureRect.new()
	view.texture = vp.get_texture()
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view.size = Vector2(1920, 1080)
	view.stretch_mode = TextureRect.STRETCH_SCALE
	add_child(view)

	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.size = 12.0
	var dist := float(args.get("dist", "120"))
	cam.near = dist - 60.0 if dist > 70.0 else 2.0
	cam.far = dist + 70.0
	var p := deg_to_rad(55.0)
	cam.rotation = Vector3(-p, 0, 0)
	cam.position = Vector3(0, sin(p), cos(p)) * dist
	vp.add_child(cam)

	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(0.35, 0.55, 0.85)
	sm.sky_horizon_color = Color(0.7, 0.8, 0.9)
	sm.ground_bottom_color = Color(0.2, 0.25, 0.2)
	sm.ground_horizon_color = Color(0.6, 0.7, 0.75)
	sky.sky_material = sm
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = float(args.get("amb", "0.35"))
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var gi: String = args.get("gi", "none")
	if gi == "sdfgi":
		env.sdfgi_enabled = true
		env.sdfgi_cascades = int(args.get("cascades", "4"))
		env.sdfgi_min_cell_size = float(args.get("cell", "0.2"))
		env.sdfgi_use_occlusion = true
		env.sdfgi_energy = 1.0
	if args.get("vfog", "0") == "1":
		env.volumetric_fog_enabled = true
		env.volumetric_fog_density = float(args.get("fogd", "0.02"))
		env.volumetric_fog_albedo = Color(0.9, 0.95, 1.0)
		env.volumetric_fog_length = float(args.get("fogl", "200"))
		env.volumetric_fog_detail_spread = 2.0
		env.volumetric_fog_gi_inject = 1.0
	if args.get("ssao", "0") == "1":
		env.ssao_enabled = true
		env.ssao_radius = 1.5
		env.ssao_intensity = 2.0
	if args.get("ssil", "0") == "1":
		env.ssil_enabled = true
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_max_distance = 300.0
	sun.rotation = Vector3(deg_to_rad(-50.0), deg_to_rad(30.0), 0)
	sun.light_energy = 1.4
	sun.light_volumetric_fog_energy = 1.0
	vp.add_child(sun)

	# ground, boxes, a "tree" (trunk + crown spheres), a wall
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(80, 80)
	ground.mesh = pm
	ground.material_override = _mat(Color(0.35, 0.55, 0.25))
	vp.add_child(ground)
	for i in 6:
		var b := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(1.5, 1.0 + i * 0.6, 1.5)
		b.mesh = bm
		b.position = Vector3(-8.0 + i * 3.2, bm.size.y * 0.5, -2.0 + (i % 2) * 3.0)
		b.material_override = _mat(Color(0.8, 0.75, 0.65) if i % 2 == 0 else Color(0.85, 0.3, 0.2))
		vp.add_child(b)
	# a big orange wall beside white blocks: colour bleeding shows the GI
	var wall := MeshInstance3D.new()
	var wm := BoxMesh.new()
	wm.size = Vector3(6.0, 3.0, 0.4)
	wall.mesh = wm
	wall.position = Vector3(-3.0, 1.5, 3.5)
	wall.material_override = _mat(Color(0.95, 0.45, 0.1))
	vp.add_child(wall)
	for i in 3:
		var w2 := MeshInstance3D.new()
		var w2m := BoxMesh.new()
		w2m.size = Vector3(1.0, 1.0, 1.0)
		w2.mesh = w2m
		w2.position = Vector3(-5.0 + i * 2.0, 0.5, 2.6)
		w2.material_override = _mat(Color(0.9, 0.9, 0.9))
		vp.add_child(w2)
	if args.get("gi", "none") == "voxel":
		var vg := VoxelGI.new()
		vg.size = Vector3(40, 16, 40)
		vg.position = Vector3(0, 6, 0)
		vg.subdiv = VoxelGI.SUBDIV_128
		vp.add_child(vg)
		_voxel = vg
	var trunk := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.3
	cm.bottom_radius = 0.4
	cm.height = 5.0
	trunk.mesh = cm
	trunk.position = Vector3(5, 2.5, -4)
	trunk.material_override = _mat(Color(0.35, 0.25, 0.18))
	vp.add_child(trunk)
	for k in 5:
		var s := MeshInstance3D.new()
		var sp := SphereMesh.new()
		sp.radius = 1.6
		sp.height = 3.2
		s.mesh = sp
		s.position = Vector3(5 + sin(k * 1.3) * 1.5, 5.5 + (k % 2) * 0.8, -4 + cos(k * 1.3) * 1.5)
		s.material_override = _mat(Color(0.25, 0.45, 0.2))
		vp.add_child(s)
	if args.has("lamp"):
		var o := OmniLight3D.new()
		o.position = Vector3(0, 1.5, 2)
		o.light_color = Color(1.0, 0.7, 0.4)
		o.light_energy = 3.0
		o.omni_range = 6.0
		o.light_volumetric_fog_energy = 2.0
		vp.add_child(o)
	t0 = Time.get_ticks_msec()


func _mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 1.0
	return m


func _process(_dt: float) -> void:
	frame += 1
	if frame == 3 and _voxel:
		var tb := Time.get_ticks_msec()
		_voxel.bake()
		print("GITEST voxel bake ms=%d" % (Time.get_ticks_msec() - tb))
	var now := Time.get_ticks_msec()
	if frame > 5:
		times.append(float(now - t0))
	t0 = now
	if frame == int(args.get("frames", "40")):
		var img := vp.get_texture().get_image()
		if args.has("shot"):
			img.save_png(String(args["shot"]))
		times.sort()
		print("GITEST gi=%s vfog=%s ssao=%s ssil=%s median_ms=%.0f" % [args.get("gi", "none"), args.get("vfog", "0"), args.get("ssao", "0"), args.get("ssil", "0"), times[times.size() / 2]])
		get_tree().quit()
