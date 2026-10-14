extends Node
## The art sample (美术样章): the summit saddle of the pass in the 3D pixel renderer.
## Assembly of the terrain, water, ground cover, trees and props, the characters and the time of
## day. Run: godot --path godot res://world3d/sample.tscn [-- options]
##   --at=x,z         camera focus (world metres; default: her spawn)
##   --hours=h        time of day (default 9.5)      --rain=0..1
##   --shot=path.png  save the low-res frame and the window after --frames frames, then quit
##   --pitch=deg      camera pitch (evidence renders)

var pv: PixelView3D
var env: W3Env
var terrain: Terrain3D
var args := {}
var frame := 0
var focus := Vector3.ZERO


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
		elif a.begins_with("--"):
			args[a.substr(2)] = "1"
	pv = PixelView3D.new()
	if args.has("pitch"):
		pv.pitch_deg = float(args["pitch"])
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	env.rain = float(args.get("rain", "0"))
	env.set_time(float(args.get("hours", "9.5")))
	terrain = Terrain3D.new()
	terrain.name = "Terrain"
	pv.world_root.add_child(terrain)
	var t0 := Time.get_ticks_msec()
	terrain.load_region("res://world3d/terrain/saddle")
	print("TERRAIN_LOADED ms=", Time.get_ticks_msec() - t0)
	focus = terrain.marker("spawn")
	if args.has("at"):
		var p := String(args["at"]).split(",")
		focus = Vector3(float(p[0]), 0.0, float(p[1]))
		focus.y = terrain.height_at(focus.x, focus.z)
	pv.follow(func() -> Vector3: return focus, {"cut": true})


var _shot_list: Array = []
var _shot_i := 0


func _set_view(i: int) -> void:
	var v: Array = _shot_list[i]
	focus = Vector3(v[0], 0.0, v[1])
	focus.y = terrain.height_at(focus.x, focus.z)
	env.set_time(v[2])
	pv.follow(func() -> Vector3: return focus, {"cut": true})


func _process(dt: float) -> void:
	frame += 1
	env.tick(dt)
	pv.update_camera(dt)
	# --shots=dir:x,z,h;x,z,h;...  renders each view (low-res + window) in turn
	if args.has("shots"):
		if _shot_list.is_empty():
			var spec := String(args["shots"]).split(":", true, 1)
			for v in spec[1].split(";"):
				var p := v.split(",")
				_shot_list.append([float(p[0]), float(p[1]), float(p[2]) if p.size() > 2 else 10.0])
			_set_view(0)
		if frame % 12 == 0:
			var dir := String(args["shots"]).split(":", true, 1)[0]
			var v: Array = _shot_list[_shot_i]
			var base := "%s/v%02d_%d_%d_%sh" % [dir, _shot_i, int(v[0]), int(v[1]), String.num(v[2], 1)]
			pv.vp.get_texture().get_image().save_png(base + ".png")
			print("SHOT ", base)
			_shot_i += 1
			if _shot_i >= _shot_list.size():
				get_tree().quit()
				return
			_set_view(_shot_i)
		return
	if args.has("shot") and frame == int(args.get("frames", "30")):
		var path: String = args["shot"]
		var img := pv.vp.get_texture().get_image()
		img.save_png(path)
		get_viewport().get_texture().get_image().save_png(path.replace(".png", "_win.png"))
		print("SHOT ", path, " ", img.get_size())
		get_tree().quit()
