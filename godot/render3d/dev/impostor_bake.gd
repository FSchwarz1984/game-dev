extends Node
## Impostor bake for the view from the lookout (W3Vista, docs/knowledge/21 §10): each asset of the
## catalog seen from N directions around it (or from given ones), rendered by the world's own
## materials in bake mode (global w3_bake: 1 albedo, 2 normal, 3 AO + class; no wind, no lean, no
## cut-away) with an orthographic camera at 20 px per metre, texel for pixel: the leaf cards and the
## surface patterns come out exactly as the world draws them. tools/world3d/vista_impostors.py packs
## the frames into the vista's LOD atlases.
##   bash tools/world3d/run3d.sh res://render3d/dev/impostor_bake.tscn <out> 1280x720 -- \
##     --out=<dir> --assets=sugi_a,pine_a --angles=8 --elev=8
##     [--views=name:deg:elev,...]  (single views: the direction toward the camera in degrees, the
##                                   vertical angle; for the hut, the shrine and the great camphor)
## Writes <dir>/<asset>_<k>_{a,n,o}.png and <dir>/frames.json (size, pivot px, angle, elevation).

const CATALOG := "res://world3d/assets/catalog.json"
const PPM := 20.0

var args := {}
var vp: SubViewport
var cam: Camera3D
var out_dir := ""
var frames: Array = []


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	out_dir = String(args.get("out", "user://impostors"))
	DirAccess.make_dir_recursive_absolute(out_dir)
	vp = SubViewport.new()
	vp.own_world_3d = true
	vp.transparent_bg = true
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.use_taa = false
	vp.positional_shadow_atlas_size = 0
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(vp)
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.background_color = Color(0, 0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.glow_enabled = false
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.near = 1.0
	cam.far = 600.0
	cam.current = true
	vp.add_child(cam)
	# the world's globals for a bake: no wind, no cut-away, no lamps, dry, day
	RenderingServer.global_shader_parameter_set("w3_player", Vector4(0, -1000, 0, 0))
	RenderingServer.global_shader_parameter_set("w3_wind", Vector4(0, 0, 0, 0))
	RenderingServer.global_shader_parameter_set("w3_time", 0.0)
	RenderingServer.global_shader_parameter_set("w3_night", 0.0)
	RenderingServer.global_shader_parameter_set("w3_lamp_n", 0.0)
	RenderingServer.global_shader_parameter_set("w3_wet", 0.0)
	_run.call_deferred()


func _run() -> void:
	var f := FileAccess.open(CATALOG, FileAccess.READ)
	var catalog: Dictionary = JSON.parse_string(f.get_as_text()).get("assets", {})
	var jobs: Array = []     # [asset, angle deg, elevation deg, index]
	var n := int(args.get("angles", "8"))
	var elev := float(args.get("elev", "8"))
	for nm in String(args.get("assets", "")).split(",", false):
		for k in n:
			jobs.append([nm, 360.0 * k / n, elev, k])
	for v in String(args.get("views", "")).split(",", false):
		var p := v.split(":")
		jobs.append([p[0], float(p[1]), float(p[2]) if p.size() > 2 else elev, -1])
	for j in jobs:
		var nm: String = j[0]
		if not catalog.has(nm):
			push_error("no asset " + nm)
			continue
		var ps: PackedScene = load(String(catalog[nm]["scene"]))
		var inst: Node3D = ps.instantiate()
		vp.add_child(inst)
		await _bake(inst, nm, float(j[1]), float(j[2]), int(j[3]))
		inst.queue_free()
		await get_tree().process_frame
	var fo := FileAccess.open(out_dir.path_join("frames.json"), FileAccess.WRITE)
	fo.store_string(JSON.stringify({"ppm": PPM, "frames": frames}, " "))
	fo.close()
	print("BAKED frames=", frames.size())
	get_tree().quit()


## The bounds of everything the instance draws (mesh AABBs in world space).
func _bounds(n: Node, acc: Array) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mi := n as MeshInstance3D
		var bb := mi.global_transform * mi.mesh.get_aabb()
		acc.append(bb)
	for c in n.get_children():
		_bounds(c, acc)


func _bake(inst: Node3D, nm: String, angle_deg: float, elev_deg: float, k: int) -> void:
	# the camera looks north (-Z), pitched down by the elevation; the asset turns instead, so that the
	# direction toward the camera in the asset's own frame is angle_deg (0 = its +Z, its front)
	inst.rotation = Vector3(0.0, -deg_to_rad(angle_deg), 0.0)
	inst.position = Vector3.ZERO
	var e := deg_to_rad(elev_deg)
	RenderingServer.global_shader_parameter_set("w3_view", Vector4(PPM, sin(e), cos(e), 0.0))
	await get_tree().process_frame
	var boxes: Array = []
	_bounds(inst, boxes)
	var sx0 := INF
	var sx1 := -INF
	var sy0 := INF
	var sy1 := -INF
	for bb in boxes:
		var b := bb as AABB
		for c in 8:
			var p := b.get_endpoint(c)
			var sx := p.x
			var sy := p.y * cos(e) - p.z * sin(e)
			sx0 = minf(sx0, sx)
			sx1 = maxf(sx1, sx)
			sy0 = minf(sy0, sy)
			sy1 = maxf(sy1, sy)
	var pad := 1.5
	sx0 -= pad
	sx1 += pad
	sy0 -= pad
	sy1 += pad
	var w := int(ceil((sx1 - sx0) * PPM / 2.0)) * 2
	var h := int(ceil((sy1 - sy0) * PPM / 2.0)) * 2
	var cx := roundf((sx0 + sx1) * 0.5 * PPM) / PPM
	var cy := roundf((sy0 + sy1) * 0.5 * PPM) / PPM
	vp.size = Vector2i(w, h)
	cam.size = float(h) / PPM
	var right := Vector3(1, 0, 0)
	var up := Vector3(0, cos(e), -sin(e))
	var back := Vector3(0, sin(e), cos(e))
	cam.global_transform = Transform3D(Basis(right, up, back), right * cx + up * cy + back * 300.0)
	var base := "%s_%s" % [nm, (str(k) if k >= 0 else "v%d" % int(round(angle_deg)))]
	for pass_i in [1, 2, 3]:
		RenderingServer.global_shader_parameter_set("w3_bake", float(pass_i))
		vp.render_target_update_mode = SubViewport.UPDATE_ONCE
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var img := vp.get_texture().get_image()
		img.save_png(out_dir.path_join("%s_%s.png" % [base, ["a", "n", "o"][pass_i - 1]]))
	RenderingServer.global_shader_parameter_set("w3_bake", 0.0)
	frames.append({"asset": nm, "file": base, "angle": angle_deg, "elev": elev_deg, "index": k,
		"size": [w, h], "pivot": [w * 0.5 - cx * PPM, h * 0.5 + cy * PPM]})
	print("BAKE ", base, " ", w, "x", h)
