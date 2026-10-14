extends Node
## Asset bench for tools/world3d_assets: renders shots of the 3D assets through the renderer's own
## PixelView3D + W3Env (docs/knowledge/21), in a scratch copy of the project made by make_bench.py.
## Driven by a JSON job:  godot --path <bench> res://w3a/w3a_bench.tscn -- --job=/abs/job.json
## job = {"pitch": 55, "shots": [{"out": "/abs/a.png", "hour": 12.5, "focus": [x, y, z],
##   "items": [{"scene": "res://...tscn", "pos": [x, y, z], "yaw": deg, "far": bool}],
##   "fig": [x, y, z] | null, "cut_px": 0, "ground": true, "ground_tint": [r, g, b], "wind": 1.0,
##   "rain": 0.0, "frames": 6}]}
## Saves <out> (native, graded like the game) and <out>_raw.png (the 3D viewport before grading).

var pv: PixelView3D
var env: W3Env
var job: Dictionary
var shots: Array = []
var i := -1
var wait := 0
var shot: Dictionary
var placed: Array[Node] = []
var fig: CharSprite3D
var ground: MeshInstance3D
var ground_mat: ShaderMaterial


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--job="):
			job = JSON.parse_string(FileAccess.get_file_as_string(a.substr(6)))
	if job.is_empty():
		push_error("no --job")
		get_tree().quit(1)
		return
	shots = job.shots
	pv = PixelView3D.new()
	pv.pitch_deg = float(job.get("pitch", 55.0))
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	var plane := PlaneMesh.new()
	plane.size = Vector2(160, 160)
	ground = MeshInstance3D.new()
	ground.mesh = plane
	ground_mat = ShaderMaterial.new()
	ground_mat.shader = load("res://render3d/shaders/toon_solid.gdshader")
	ground_mat.set_shader_parameter("lean", 0.0)
	ground_mat.set_shader_parameter("vertex_ao", 0.0)
	ground.material_override = ground_mat
	pv.world_root.add_child(ground)
	fig = CharSprite3D.new()
	pv.world_root.add_child(fig)
	fig.setup(CharSprite3D.pixel_texture("res://art/sprites/tsuzumi_plain.png"),
		CharSprite3D.pixel_texture("res://art/sprites/tsuzumi_plain_n.png"), Vector2i(64, 64), Vector2i(32, 58))
	fig.show_frame(0, 0)
	_next()


func _process(dt: float) -> void:
	if i < 0 or i >= shots.size():
		return
	env.clock = float(shot.get("clock", 3.0))
	env.tick(0.0)
	pv.update_camera(dt)
	wait -= 1
	if wait > 0:
		return
	_capture()
	_next()


func _next() -> void:
	i += 1
	if i >= shots.size():
		get_tree().quit(0)
		return
	shot = shots[i]
	for n in placed:
		n.queue_free()
	placed.clear()
	for it in shot.get("items", []):
		var ps: PackedScene = load(String(it.scene))
		if ps == null:
			push_error("cannot load " + String(it.scene))
			continue
		var n: Node3D = ps.instantiate()
		var p: Array = it.get("pos", [0, 0, 0])
		n.position = Vector3(p[0], p[1], p[2])
		n.rotation_degrees = Vector3(0, float(it.get("yaw", 0.0)), 0)
		pv.world_root.add_child(n)
		if it.has("state") and n.has_method("set_state"):
			n.call("set_state", it.state)
		placed.append(n)
	ground.visible = bool(shot.get("ground", true))
	var gt: Array = shot.get("ground_tint", [0.42, 0.47, 0.30])
	ground_mat.set_shader_parameter("tint", Color(gt[0], gt[1], gt[2]))
	var f = shot.get("fig")
	fig.visible = f != null
	var k := tan(deg_to_rad(pv.pitch_deg) * 0.5)
	if f != null:
		fig.position = Vector3(f[0], f[1], f[2])
		var chest := fig.position + Vector3(0, 0.95, -k * 0.95)
		RenderingServer.global_shader_parameter_set("w3_player", Vector4(chest.x, chest.y, chest.z, float(shot.get("cut_px", 0.0))))
	else:
		RenderingServer.global_shader_parameter_set("w3_player", Vector4(0, -1000, 0, 0))
	env.rain = float(shot.get("rain", 0.0))
	env.wind = float(shot.get("wind", 1.0))
	env.set_time(float(shot.get("hour", 12.5)))
	RenderingServer.global_shader_parameter_set("w3_wind", Vector4(1.0, 0.2, env.wind, 0.3))
	var fc: Array = shot.get("focus", [0, 1, 0])
	var focus := Vector3(fc[0], fc[1], fc[2])
	# put the focus on a whole screen pixel so the window image maps texel for pixel
	var s := pv.screen_of(focus)
	focus += pv.px_to_world(s.round() - s)
	pv.point_at(focus, {"cut": true})
	wait = int(shot.get("frames", 6))


func _capture() -> void:
	var out := String(shot.out)
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var raw := pv.vp.get_texture().get_image()
	raw = raw.get_region(Rect2i(1, 1, raw.get_width() - 2, raw.get_height() - 2))
	raw.save_png(out.get_basename() + "_raw.png")
	# the graded image the player sees: the window, one sample per native pixel
	var win := get_viewport().get_texture().get_image()
	var s := pv.scale_factor
	var w := int(pv.logical.x)
	var h := int(pv.logical.y)
	var img := Image.create(w, h, false, Image.FORMAT_RGB8)
	var m := pv.margin
	for y in h:
		for x in w:
			img.set_pixel(x, y, win.get_pixel(int(m.x) + x * s + s / 2, int(m.y) + y * s + s / 2))
	img.save_png(out)
	print("shot ", i, " -> ", out)
