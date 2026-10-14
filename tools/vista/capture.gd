extends SceneTree
## Renders the vista (godot/vista) at fixed time steps and saves what the window shows, for checks
## and previews (not part of the game). Run in a real window (Xvfb + Mesa, the Mobile renderer):
##   godot --path godot --rendering-method mobile --resolution 960x540 -s tools/vista/capture.gd -- --plan=plan.json
## plan.json: {"out": dir, "exact": bool, "data_dir": "res://vista/data", "quality": "high",
##   "shots": [{"name": n, "shot": "south", "state": {...}, "frames": 30, "dt": 1/60,
##              "seq": {"n": 12, "every": 3, "ramps": [[key, from, to, u0, u1], ...]},   (optional)
##              "native": true}]}
## Each capture is <out>/<name>.png (the window) and, with "native", <name>.native.png: the window
## sampled back to one value per native pixel (it is drawn at an integer scale). A sequence writes
## <name>-000.png ... with the state ramped like tools/vista/shot.mjs does for the JS vista.

var plan: Dictionary
var out := ""


func _initialize() -> void:
	var path := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--plan="):
			path = a.substr(7)
	var j := JSON.new()
	if path == "" or j.parse(FileAccess.get_file_as_string(path)) != OK:
		push_error("capture: needs --plan=<json>")
		quit(2)
		return
	plan = j.data
	out = String(plan.get("out", "user://vista-capture"))
	DirAccess.make_dir_recursive_absolute(out)
	_run.call_deferred()


func _run() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 1
	root.add_child(layer)
	for _i in 3:
		await process_frame
	for s in plan.get("shots", []):
		var v := Vista.new()
		v.autoplay = false
		v.exact = bool(plan.get("exact", false))
		v.quality = String(plan.get("quality", "high"))
		v.data_dir = String(plan.get("data_dir", VistaData.DEFAULT_DIR))
		for k in s.get("state", {}):
			v.state[k] = s["state"][k]
		layer.add_child(v)
		v.show_shot(String(s.get("shot", "south")))
		var dt := float(s.get("dt", 1.0 / 60.0))
		var frames := int(s.get("frames", 30))
		for _f in frames:
			v.advance(dt)
			await process_frame
		var seq: Dictionary = s.get("seq", {})
		if seq.is_empty():
			await RenderingServer.frame_post_draw
			_save(String(s["name"]), bool(s.get("native", true)))
		else:
			var n := int(seq.get("n", 10))
			var steps := maxi(1, roundi(float(seq.get("every", 0.1)) / dt))
			var total := maxi(1, (n - 1) * steps)
			for i in n:
				if i > 0:
					for j in steps:
						var u := minf(1.0, float((i - 1) * steps + j + 1) / total)
						for r in seq.get("ramps", []):
							var u0 := float(r[3]) if r.size() > 3 else 0.0
							var u1 := float(r[4]) if r.size() > 4 else 1.0
							v.state[r[0]] = lerpf(float(r[1]), float(r[2]), clampf((u - u0) / (u1 - u0), 0.0, 1.0))
						v.advance(dt)
						await process_frame
				await RenderingServer.frame_post_draw
				_save("%s-%03d" % [s["name"], i], bool(s.get("native", true)))
		v.queue_free()
		await process_frame
	quit(0)


func _save(name: String, native: bool) -> void:
	var img := root.get_texture().get_image()
	img.save_png(out.path_join(name + ".png"))
	if native:
		var win := Vector2(img.get_size())
		var s := maxi(1, floori(minf(win.x / 480.0, win.y / 270.0)))
		var w := floori(win.x / s)
		var h := floori(win.y / s)
		var margin := ((win - Vector2(w * s, h * s)) * 0.5).round()
		var n := Image.create(w, h, false, Image.FORMAT_RGB8)
		for y in h:
			for x in w:
				n.set_pixel(x, y, img.get_pixel(int(margin.x) + x * s + s / 2, int(margin.y) + y * s + s / 2))
		n.save_png(out.path_join(name + ".native.png"))
	print("CAPTURE %s" % name)
