extends Node
## Vegetation bench (tools/flora/bench). Builds a pixel stage like the game's (native 480x270
## SubViewport, 2D HDR, pixel snapping, shown x3), instances plant scenes from a layout JSON into a
## y-sorted node, applies a lighting preset and captures screenshots.
## User args after "--":
##   --layout=row|glade        --preset=morning|noon|dusk|night
##   --cam=x,y                 camera centre, world px
##   --player=x,y              placeholder character's feet, world px (also the x-ray hole)
##   --shot=path.png           window capture (x3) at frame --frame (default 40)
##   --full=path.png           whole-layout capture at native resolution
##   --seq=dir --seq-n=24 --seq-every=4   a sequence of window captures (sway, occlusion)
##   --wind=1.0                --walk=x0,y0,x1,y1  (player walks during a sequence)

const BASE := Vector2i(480, 270)
const SCALE := 3

var world_vp: SubViewport
var world: Node2D
var things: Node2D
var view: TextureRect
var shade: CanvasModulate
var sun: DirectionalLight2D
var player: Sprite2D
var args := {}
var frame := 0
var layout := {}
var lanterns: Array = []
var seq_taken := 0
var walk := []


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	get_window().size = BASE * SCALE
	_build_stage()
	_load_layout(String(args.get("layout", "row")))
	_preset(String(args.get("preset", "morning")))
	FloraField.set_wind(float(args.get("wind", "1.0")))
	if args.has("walk"):
		var w := String(args["walk"]).split(",")
		walk = [Vector2(float(w[0]), float(w[1])), Vector2(float(w[2]), float(w[3]))]
	print("BENCH_READY layout=%s preset=%s" % [args.get("layout", "row"), args.get("preset", "morning")])


func _vec(key: String, def: Vector2) -> Vector2:
	if not args.has(key):
		return def
	var p := String(args[key]).split(",")
	return Vector2(float(p[0]), float(p[1]))


func _build_stage() -> void:
	world_vp = SubViewport.new()
	world_vp.size = BASE
	world_vp.use_hdr_2d = true
	world_vp.snap_2d_transforms_to_pixel = true
	world_vp.snap_2d_vertices_to_pixel = true
	world_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	world_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	world_vp.own_world_3d = true
	add_child(world_vp)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CANVAS
	e.glow_enabled = true
	e.glow_intensity = 0.8
	e.glow_strength = 1.0
	e.glow_bloom = 0.0
	e.glow_hdr_threshold = 1.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.environment = e
	world_vp.add_child(env)
	world = Node2D.new()
	world.name = "World"
	world_vp.add_child(world)
	things = Node2D.new()
	things.name = "Things"
	things.y_sort_enabled = true
	world.add_child(things)
	shade = CanvasModulate.new()
	world.add_child(shade)
	sun = DirectionalLight2D.new()
	world.add_child(sun)
	view = TextureRect.new()
	view.texture = world_vp.get_texture()
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view.stretch_mode = TextureRect.STRETCH_SCALE
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	view.size = Vector2(BASE * SCALE)
	var m := ShaderMaterial.new()
	m.shader = load("res://bench/linear_to_srgb.gdshader")
	view.material = m
	add_child(view)


func _load_layout(name: String) -> void:
	var f := FileAccess.open("res://bench/layouts/%s.json" % name, FileAccess.READ)
	layout = JSON.parse_string(f.get_as_text())
	var g := Sprite2D.new()
	g.texture = load(layout["ground"])
	g.centered = false
	g.z_index = -10
	world.add_child(g)
	for it in layout["plants"]:
		var sc: PackedScene = load(it["scene"])
		var n := sc.instantiate() as Node2D
		n.position = Vector2(it["x"], it["y"])
		things.add_child(n)
	for it in layout.get("props", []):
		var s := Sprite2D.new()
		s.texture = load(it["texture"])
		s.centered = false
		s.offset = Vector2(it.get("ox", 0), it.get("oy", 0))
		s.position = Vector2(it["x"], it["y"])
		things.add_child(s)
	for it in layout.get("lanterns", []):
		lanterns.append(Vector2(it[0], it[1]))
	# placeholder character (her sprite at scale): feet on the ground point
	player = Sprite2D.new()
	var ct := CanvasTexture.new()
	ct.diffuse_texture = load("res://bench/char/tsuzumi.png")
	ct.normal_texture = load("res://bench/char/tsuzumi_n.png")
	player.texture = ct
	player.centered = false
	player.offset = Vector2(-28, -61)
	player.position = _vec("player", Vector2(layout.get("player", [240, 200])[0], layout.get("player", [240, 200])[1]))
	things.add_child(player)
	var foot := Sprite2D.new()
	foot.texture = load("res://bench/char/foot_shadow.png")
	foot.centered = true
	foot.position = Vector2(0, -1)
	foot.z_index = -1
	foot.modulate = Color(1, 1, 1, 0.55)
	player.add_child(foot)


## The terrain's time-of-day table (tools/terrain/tengan_terrain/preview.py TOD): sun elevation,
## sun colour * energy (DirectionalLight2D), sky = ambient (CanvasModulate).
func _preset(p: String) -> void:
	var presets := {
		"morning": {"elev": 24.0, "sun": Color(0.76, 0.68, 0.55), "sky": Color(0.56, 0.58, 0.65)},
		"noon": {"elev": 58.0, "sun": Color(0.64, 0.61, 0.53), "sky": Color(0.53, 0.56, 0.60)},
		"dusk": {"elev": 12.0, "sun": Color(1.12, 0.68, 0.40), "sky": Color(0.42, 0.37, 0.49)},
		"night": {"elev": 40.0, "sun": Color(0.20, 0.25, 0.40), "sky": Color(0.19, 0.23, 0.36)},
	}
	var q: Dictionary = presets[p]
	shade.color = q["sky"]
	sun.color = q["sun"]
	sun.energy = 1.0
	FloraField.set_sun(q["elev"], q["sun"], q["sky"])
	# the placeholder character takes Godot's own 2D light: point the light the same way on screen
	var s := FloraField.sun_dir
	var on_screen := Vector2(s.x, -(s.y - s.z) * 0.70710678)     # toward the sun, screen (y down)
	sun.rotation = Vector2(0, 1).angle_to(-on_screen)
	sun.height = clampf((s.y + s.z) * 0.70710678, 0.0, 1.0)
	if p == "night" or p == "dusk":
		var tex := GradientTexture2D.new()
		tex.fill = GradientTexture2D.FILL_RADIAL
		tex.fill_from = Vector2(0.5, 0.5)
		tex.fill_to = Vector2(1.0, 0.5)
		tex.width = 256
		tex.height = 256
		var gr := Gradient.new()
		gr.set_color(0, Color(1, 1, 1, 1))
		gr.set_color(1, Color(1, 1, 1, 0))
		tex.gradient = gr
		for pos in lanterns:
			var l := PointLight2D.new()
			l.texture = tex
			l.texture_scale = 1.4
			l.color = Color(1.0, 0.68, 0.38)
			l.energy = 1.5 if p == "night" else 0.6
			l.height = 28.0
			l.position = pos
			world.add_child(l)


func _cam(c: Vector2) -> void:
	world_vp.canvas_transform = Transform2D(0.0, -c.round() + Vector2(BASE) * 0.5)


func _process(_delta: float) -> void:
	frame += 1
	if walk.size() == 2:
		var n := int(args.get("seq-n", "24")) * int(args.get("seq-every", "4"))
		var t := clampf(float(frame - 10) / float(max(1, n)), 0.0, 1.0)
		player.position = (walk[0].lerp(walk[1], t)).round()
	FloraField.set_player(player.global_position, player.global_position.y)
	_cam(_vec("cam", player.position + Vector2(0, -40)))
	var shot_frame := int(args.get("frame", "40"))
	if args.has("shot") and frame == shot_frame:
		_save_window(String(args["shot"]))
	if args.has("seq") and frame > 10 and seq_taken < int(args.get("seq-n", "24")):
		if (frame - 10) % int(args.get("seq-every", "4")) == 0:
			DirAccess.make_dir_recursive_absolute(String(args["seq"]))
			_save_window("%s/f%03d.png" % [args["seq"], seq_taken])
			seq_taken += 1
	if args.has("full") and frame == shot_frame + 2:
		await _save_full(String(args["full"]))
	var done := frame > shot_frame + 6
	if args.has("seq"):
		done = done and seq_taken >= int(args.get("seq-n", "24"))
	if done:
		print("BENCH_DONE frame=%d" % frame)
		get_tree().quit()


func _save_window(path: String) -> void:
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png(path)
	print("SHOT %s %dx%d err=%d" % [path, img.get_width(), img.get_height(), err])


func _save_full(path: String) -> void:
	var b: Array = layout["bounds"]
	var size := Vector2i(int(b[2]), int(b[3]))
	var big := SubViewport.new()
	big.size = size
	big.use_hdr_2d = true
	big.snap_2d_transforms_to_pixel = true
	big.snap_2d_vertices_to_pixel = true
	big.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	big.world_2d = world_vp.world_2d
	big.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(big)
	big.canvas_transform = Transform2D(0.0, Vector2(-b[0], -b[1]))
	var conv := SubViewport.new()
	conv.size = size
	conv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var tr := TextureRect.new()
	tr.texture = big.get_texture()
	tr.size = Vector2(size)
	var m := ShaderMaterial.new()
	m.shader = load("res://bench/linear_to_srgb.gdshader")
	tr.material = m
	conv.add_child(tr)
	add_child(conv)
	for i in 4:
		await RenderingServer.frame_post_draw
	var img := conv.get_texture().get_image()
	var err := img.save_png(path)
	print("FULL %s %dx%d err=%d" % [path, img.get_width(), img.get_height(), err])
