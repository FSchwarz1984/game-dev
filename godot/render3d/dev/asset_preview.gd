extends Node
## Renders one world3d asset with the 3D pixel renderer for checking (internal tool, never shipped):
## a flat patch of ground, a 42-px figure for scale, morning / noon / dusk / night.
##   godot --path godot res://render3d/dev/asset_preview.tscn -- --asset=res://... --out=<dir>
##     [--times=7.5,12.5,17.6,22] [--focus_h=<m>] [--pitch=55]
## Writes <out>/<name>_<hour>.png (native) and <name>_<hour>_x3.png.

var pv: PixelView3D
var env: W3Env
var args := {}
var times: Array[float] = [7.5, 12.5, 17.6, 22.0]
var step := 0
var wait := 0
var name_ := "asset"


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	if args.has("times"):
		times.clear()
		for t in String(args["times"]).split(","):
			times.append(float(t))
	pv = PixelView3D.new()
	if args.has("pitch"):
		pv.pitch_deg = float(args["pitch"])
	if args.has("scale"):
		pv.force_scale = int(args["scale"])
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	# ground patch
	var plane := PlaneMesh.new()
	plane.size = Vector2(60, 60)
	plane.subdivide_width = 1
	plane.subdivide_depth = 1
	var g := MeshInstance3D.new()
	g.mesh = plane
	var gm := ShaderMaterial.new()
	gm.shader = load("res://render3d/shaders/toon_solid.gdshader")
	gm.set_shader_parameter("lean", 0.0)
	gm.set_shader_parameter("tint", Color(0.42, 0.47, 0.30))
	gm.set_shader_parameter("vertex_ao", 0.0)
	g.material_override = gm
	pv.world_root.add_child(g)
	var focus_h := float(args.get("focus_h", "1.0"))
	var path: String = args.get("asset", "")
	if path != "":
		name_ = path.get_file().get_basename()
		var ps: PackedScene = load(path)
		if ps:
			var inst := ps.instantiate()
			pv.world_root.add_child(inst)
		else:
			push_error("cannot load " + path)
	# scale figure: her idle front frame, 2.5 m to the right
	var fig := CharSprite3D.new()
	pv.world_root.add_child(fig)
	fig.setup(CharSprite3D.pixel_texture("res://art/sprites/tsuzumi_plain.png"),
		CharSprite3D.pixel_texture("res://art/sprites/tsuzumi_plain_n.png"), Vector2i(64, 64), Vector2i(32, 58))
	fig.show_frame(0, 0)
	fig.position = Vector3(float(args.get("fig_x", "2.5")), 0, float(args.get("fig_z", "1.0")))
	var k := tan(deg_to_rad(pv.pitch_deg) * 0.5)
	pv.point_at(Vector3(0, focus_h, -k * focus_h), {"cut": true})
	env.set_time(times[0])


func _process(dt: float) -> void:
	env.tick(dt)
	pv.update_camera(dt)
	wait += 1
	if wait < 4:
		return
	wait = 0
	var out: String = args.get("out", "/tmp")
	var h := times[step]
	var img := pv.vp.get_texture().get_image()
	var base := "%s/%s_%s" % [out, name_, String.num(h, 1).replace(".", "h")]
	img.save_png(base + ".png")
	var big := img.duplicate()
	big.resize(img.get_width() * 3, img.get_height() * 3, Image.INTERPOLATE_NEAREST)
	big.save_png(base + "_x3.png")
	print("PREVIEW ", base)
	step += 1
	if step >= times.size():
		get_tree().quit()
		return
	env.set_time(times[step])
