extends SceneTree
## Plays the prologue's vista timeline (Vista.play_prologue on a Director) or the title backdrop in a
## real window, one fixed step per frame, for Godot's Movie Maker or for a native-pixel frame grab
## (not part of the game). The figure is her real sprite (VistaFigure); --figure=stand_in uses the old
## preview stand-in instead.
##   godot --path godot --rendering-method forward_plus --resolution 1280x720 --fixed-fps 30 \
##     [--write-movie /tmp/rec/f.png] -s tools/vista/record.gd -- [--shot=prologue|title] \
##     [--seconds=8] [--quality=high|low] [--to=999] [--grab=DIR] [--rise=DIR --from=0 --every=1] \
##     [--stats]
## The prologue runs to its end and one second more (or to --to seconds); the title for --seconds.
## Movie Maker writes the project's window size (1280x720 here: the 640x360 logical canvas at 2x);
## --grab=DIR writes every frame at one pixel per native pixel (DIR/g00000.png ...), at any window.
## --rise=DIR writes the rising lights' own buffer (what they add, in sRGB units, before the
## composite; screen pixel (x, y) is (x + 1, y + 1) there) every --every frames from --from seconds
## on, with the timeline time in DIR/times.txt: the long exposure is the maximum over these.
## --stats prints, once a second of the timeline, the renderer's counters for the frame (draw calls,
## objects, primitives) and the instance counts of the light layers.
## The first two frames are drawn before the vista exists (black).

var v: Vista
var d: Director
var stand: Node2D
var figure_kind := "real"
var shot := "prologue"
var quality := "high"
var seconds := 8.0
var to := 1.0e9
var grab := ""
var rise_dir := ""
var rise_from := 0.0
var rise_every := 1
var rise_n := 0
var rise_times := PackedStringArray()
var going := false
var started := false
var done_at := -1.0
var frame := 0
var grabbed := 0
var stats := false
var _stat_sec := -1


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			shot = a.substr(7)
		elif a.begins_with("--seconds="):
			seconds = float(a.substr(10))
		elif a.begins_with("--quality="):
			quality = a.substr(10)
		elif a.begins_with("--to="):
			to = float(a.substr(5))
		elif a.begins_with("--grab="):
			grab = a.substr(7)
		elif a.begins_with("--rise="):
			rise_dir = a.substr(7)
		elif a.begins_with("--from="):
			rise_from = float(a.substr(7))
		elif a.begins_with("--every="):
			rise_every = maxi(1, int(a.substr(8)))
		elif a.begins_with("--figure="):
			figure_kind = a.substr(9)
		elif a == "--stats":
			stats = true
	if grab != "":
		DirAccess.make_dir_recursive_absolute(grab)
	if rise_dir != "":
		DirAccess.make_dir_recursive_absolute(rise_dir)
	root.size_changed.connect(_fit)
	_fit()
	_start.call_deferred()


func _fit() -> void:
	var win := Vector2(root.size)
	# the stage's rule (godot/core/pixel_stage.gd, knowledge/16 §13): round(h / 270), canvas at least 400 wide
	var sc := maxi(1, roundi(win.y / 270.0))
	while sc > 1 and win.x / sc < 400.0:
		sc -= 1
	root.content_scale_size = Vector2i(floori(win.x / sc), floori(win.y / sc))


func _start() -> void:
	await process_frame
	var layer := CanvasLayer.new()
	layer.layer = 1
	root.add_child(layer)
	v = Vista.new()
	v.autoplay = false
	v.quality = quality
	layer.add_child(v)
	d = Director.new()
	if shot == "title":
		v.show_shot("title")
	else:
		v.begin()
	if v.figure_slot() != null:
		stand = VistaStandIn.new() if figure_kind == "stand_in" else VistaFigure.new()
		v.figure_slot().add_child(stand)
	if grab != "" or rise_dir != "" or stats:
		RenderingServer.frame_post_draw.connect(_grab)
	going = true


func _process(delta: float) -> bool:
	if not going:
		return false
	frame += 1
	if shot == "title":
		v.advance(delta)
		return float(frame) * delta >= seconds
	if not started:
		started = true
		d.scene(func(dd: Director) -> void: await v.play_prologue(dd))
	d.tick(delta)
	v.advance(delta)
	if stand != null:
		stand.call("set_pose", String(v.state.get("pose", "sit")))
	if d.t >= to:
		_finish()
		return true
	if not d.busy:
		if done_at < 0.0:
			done_at = d.t
		if d.t - done_at >= 1.0:
			_finish()
			return true
	return false


func _finish() -> void:
	if rise_dir != "":
		var f := FileAccess.open(rise_dir.path_join("times.txt"), FileAccess.WRITE)
		f.store_string("\n".join(rise_times) + "\n")


## The frame just drawn, one pixel per native pixel (the window is an integer scale of it, centred).
func _grab() -> void:
	if not going:
		return
	if stats and started and int(d.t) != _stat_sec:
		_stat_sec = int(d.t)
		_print_stats()
	if rise_dir != "" and started and d.t >= rise_from and frame % rise_every == 0 and v.shot == "south":
		var south: VistaSouth = v.shots["south"]
		var ri := south.add_rise.get_texture().get_image()
		ri.convert(Image.FORMAT_RGB8)
		ri.save_png(rise_dir.path_join("r%05d.png" % rise_n))
		rise_times.append("%d %.4f %.4f %.4f" % [rise_n, d.t, float(v.state["rise"]), float(v.state["sky"])])
		rise_n += 1
	if grab == "":
		return
	var img := root.get_texture().get_image()
	var win := img.get_size()
	var s := maxi(1, roundi(win.y / 270.0))
	while s > 1 and win.x / s < 400.0:
		s -= 1
	var w := floori(win.x / float(s))
	var h := floori(win.y / float(s))
	if s > 1:
		var mx := int(round((win.x - w * s) * 0.5))
		var my := int(round((win.y - h * s) * 0.5))
		img = img.get_region(Rect2i(mx, my, w * s, h * s))
		img.resize(w, h, Image.INTERPOLATE_NEAREST)
	img.convert(Image.FORMAT_RGB8)
	img.save_png(grab.path_join("g%05d.png" % grabbed))
	grabbed += 1


func _print_stats() -> void:
	var rs := RenderingServer
	var line := "STATS t=%5.1f shot=%s rise=%.2f sky=%.2f wave=%.2f draw_calls=%d objects=%d primitives=%d" % [
		d.t, v.shot, float(v.state["rise"]), float(v.state["sky"]), float(v.state["wave"]),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)]
	if v.shot == "south":
		var south: VistaSouth = v.shots["south"]
		var lt: VistaSouthLights = south.lights
		line += " lights=%d in_flight=%d" % [lt.n, lt.in_flight]
		for k in ["stars", "shore", "lamps", "river", "rise"]:
			var l = lt.layer(k)
			if l is MultiMeshInstance2D and l.multimesh != null:
				line += " %s=%d" % [k, l.multimesh.instance_count]
		line += " motes=%d end_motes=%d" % [south.wave_fx.motes.multimesh.instance_count, south.wave_fx.end_motes.multimesh.instance_count]
	print(line)
