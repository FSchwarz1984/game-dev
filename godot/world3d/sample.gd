extends Node
## The art sample (美术样章): the summit saddle of the pass in the 3D pixel renderer.
## Assembly of the terrain, water, ground cover, trees and props, the characters and the time of
## day. Run: godot --path godot res://world3d/sample.tscn [-- options]
##   --hours=h          time of day (default 9.5)        --rain=0..1
##   --at=x,z           start / camera focus (default: her spawn by the hut door)
##   --shot=path.png    save the low-res frame and the window after --frames frames, then quit
##   --shots=dir:x,z,h;x,z,h;...   several views
##   --route=walk       she walks the sample route (hut -> shrine -> camphor -> lookout) by pressing
##                      the same movement keys a player would (Input events), for recordings
##   --pitch=deg        camera pitch (evidence renders)
## Keys: WASD / arrows walk, Shift runs. F2 toggles the time of day (debug).

const CHARS_JSON := "res://actors/characters.json"
const CATALOG := "res://world3d/assets/catalog.json"

var pv: PixelView3D
var env: W3Env
var terrain: Terrain3D
var args := {}
var frame := 0
var focus := Vector3.ZERO
var her: W3Walker
var saji: W3Walker
var her_shadow: MeshInstance3D
var saji_shadow: MeshInstance3D
var trail: Array[Vector3] = []
var catalog := {}
var props_root: Node3D
var blockers: Array = []
var route: Array[Vector2] = []
var route_i := 0
var keys_down := {}


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
	props_root = Node3D.new()
	props_root.name = "Props"
	pv.world_root.add_child(props_root)
	_load_catalog()
	_place_props()
	_spawn_characters()
	focus = her.pos
	if args.has("at"):
		var p := String(args["at"]).split(",")
		her.place(Vector3(float(p[0]), 0.0, float(p[1])))
		saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	pv.follow(_cam_target, {"cut": true})
	if args.get("route", "") == "walk":
		_make_route()


func _cam_target() -> Vector3:
	if her == null:
		return focus
	return her.pos + Vector3(0.0, 0.9, -0.9 * pv_lean())


func pv_lean() -> float:
	return tan(deg_to_rad(pv.pitch_deg) * 0.5)


# ------------------------------------------------------------------------------------------------
# props

func _load_catalog() -> void:
	var f := FileAccess.open(CATALOG, FileAccess.READ)
	if f:
		catalog = JSON.parse_string(f.get_as_text()).get("assets", {})
	print("CATALOG assets=", catalog.size())


## The asset that stands for a placement kind, if the catalog has one.
func _asset_for(kind: String, variant: int) -> String:
	var names := []
	for name in catalog:
		var a: Dictionary = catalog[name]
		var kinds: Array = a.get("kinds", [])
		if name == kind or name.begins_with(kind + "_") or kinds.has(kind):
			names.append(name)
	if names.is_empty():
		return ""
	names.sort()
	return names[variant % names.size()]


func _place_props() -> void:
	var n := 0
	for p in terrain.info["placements"]:
		var kind: String = p["kind"]
		var name := "camphor_great" if kind == "camphor" else _asset_for(kind, int(p.get("variant", 0)))
		if name == "" or not catalog.has(name):
			continue
		var a: Dictionary = catalog[name]
		var ps: PackedScene = load(a["scene"])
		if ps == null:
			continue
		var inst: Node3D = ps.instantiate()
		var pos := Vector3(p["x"], terrain.height_at(p["x"], p["z"]), p["z"])
		inst.position = pos
		if a.get("category", "") != "building":
			inst.rotation.y = float(p.get("rot", 0.0)) if kind != "camphor" else 0.0
		var sc := float(p.get("scale", 1.0))
		if kind != "camphor":
			inst.scale = Vector3.ONE * sc
		props_root.add_child(inst)
		for fp in a.get("footprint", []):
			var off := Vector3(fp[0], 0, fp[1]).rotated(Vector3.UP, inst.rotation.y) * sc
			blockers.append([pos + off, float(fp[2]) * sc])
		n += 1
	print("PROPS placed=", n)


# ------------------------------------------------------------------------------------------------
# characters

func _spawn_characters() -> void:
	var f := FileAccess.open(CHARS_JSON, FileAccess.READ)
	var chars: Dictionary = JSON.parse_string(f.get_as_text())
	her = W3Walker.new()
	her.name = "Tsuzumi"
	pv.world_root.add_child(her)
	her.setup(terrain, "tsuzumi", "load", chars)
	her.blockers = blockers
	her.place(terrain.marker("spawn"))
	saji = W3Walker.new()
	saji.name = "Saji"
	pv.world_root.add_child(saji)
	saji.setup(terrain, "saji", "main", chars)
	saji.blockers = blockers
	saji.radius = 0.25
	saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	her_shadow = _contact_shadow(Vector2(9.0, 3.5))
	saji_shadow = _contact_shadow(Vector2(7.0, 3.0))


func _contact_shadow(r: Vector2) -> MeshInstance3D:
	var q := MeshInstance3D.new()
	var m := PlaneMesh.new()
	m.size = Vector2(1.4, 1.0)
	q.mesh = m
	var sm := ShaderMaterial.new()
	sm.shader = load("res://render3d/shaders/contact_shadow.gdshader")
	sm.set_shader_parameter("radius_px", r)
	sm.render_priority = 1
	q.material_override = sm
	q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pv.world_root.add_child(q)
	return q


func _lay(shadow: MeshInstance3D, p: Vector3) -> void:
	var n := terrain.normal_at(p.x, p.z)
	var b := Basis.looking_at(n.cross(Vector3.RIGHT).normalized() if absf(n.x) < 0.9 else Vector3.FORWARD, n)
	shadow.global_transform = Transform3D(Basis(b.x, n, b.z).orthonormalized(), p + n * 0.04)


func _input_dir() -> Vector2:
	var d := Vector2.ZERO
	if _key(KEY_A) or _key(KEY_LEFT):
		d.x -= 1.0
	if _key(KEY_D) or _key(KEY_RIGHT):
		d.x += 1.0
	if _key(KEY_W) or _key(KEY_UP):
		d.y -= 1.0
	if _key(KEY_S) or _key(KEY_DOWN):
		d.y += 1.0
	return d.normalized() if d.length() > 0.0 else d


func _key(k: Key) -> bool:
	return Input.is_physical_key_pressed(k) or keys_down.get(k, false)


func _follow_saji(dt: float) -> void:
	# breadcrumbs of her path; she leads, さぢ keeps a step behind and to the north side of her
	if trail.is_empty() or trail[-1].distance_to(her.pos) > 0.25:
		trail.append(her.pos)
		if trail.size() > 64:
			trail.remove_at(0)
	var behind := her.pos
	var acc := 0.0
	for i in range(trail.size() - 1, 0, -1):
		acc += trail[i].distance_to(trail[i - 1])
		behind = trail[i - 1]
		if acc >= 1.5:
			break
	var side := Vector3(-0.55, 0, -0.35) if her.facing in [0, 1, 2, 3] else Vector3(0.55, 0, -0.35)
	var want := behind + side
	if her.speed < 0.3:
		want = her.pos + side * 1.6 + Vector3(0, 0, -0.2)
	var d := Vector2(want.x - saji.pos.x, want.z - saji.pos.z)
	var dist := d.length()
	var dir := Vector2.ZERO
	if dist > 0.3:
		dir = d / dist * clampf(dist * 0.9, 0.0, 1.15)
	saji.step(dt, dir)


# ------------------------------------------------------------------------------------------------
# route driver for recordings: presses the movement keys toward the next waypoint

func _make_route() -> void:
	for m in ["hut_door", "offering_box", "camphor_south", "lookout"]:
		pass
	var pts := [Vector2(-15.0, 9.6), Vector2(-12.6, 3.0), Vector2(-11.0, -2.5), Vector2(-10.0, -5.4),
		Vector2(-6.0, -6.2), Vector2(-1.0, -7.0), Vector2(4.0, -8.5), Vector2(7.8, -5.0), Vector2(8.6, 2.0),
		Vector2(5.0, 9.8), Vector2(-3.0, 9.8), Vector2(-9.5, 8.6), Vector2(-16.0, 12.0), Vector2(-17.2, 17.0),
		Vector2(-18.8, 23.0), Vector2(-20.8, 30.0), Vector2(-22.4, 36.0), Vector2(-23.4, 40.6)]
	for p in pts:
		route.append(p)
	her.place(Vector3(pts[0].x, 0, pts[0].y))
	saji.place(her.pos + Vector3(-0.9, 0, -0.6))
	route_i = 1


func _drive_route() -> void:
	for k in [KEY_W, KEY_A, KEY_S, KEY_D]:
		keys_down[k] = false
	if route_i >= route.size():
		return
	var t := route[route_i]
	var d := t - Vector2(her.pos.x, her.pos.z)
	if d.length() < 0.6:
		route_i += 1
		return
	d = d.normalized()
	# the keys a player would hold (8 directions)
	if d.x < -0.38:
		keys_down[KEY_A] = true
	if d.x > 0.38:
		keys_down[KEY_D] = true
	if d.y < -0.38:
		keys_down[KEY_W] = true
	if d.y > 0.38:
		keys_down[KEY_S] = true


# ------------------------------------------------------------------------------------------------

var _shot_list: Array = []
var _shot_i := 0


func _set_view(i: int) -> void:
	var v: Array = _shot_list[i]
	her.place(Vector3(v[0], 0.0, v[1]))
	saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	env.set_time(v[2])
	pv.follow(_cam_target, {"cut": true})


func _process(dt: float) -> void:
	frame += 1
	env.tick(dt)
	if not route.is_empty():
		_drive_route()
	var dir := _input_dir()
	her.step(dt, dir)
	_follow_saji(dt)
	_lay(her_shadow, her.pos)
	_lay(saji_shadow, saji.pos)
	var chest := her.chest()
	RenderingServer.global_shader_parameter_set("w3_player", Vector4(chest.x, chest.y, chest.z, 26.0))
	pv.update_camera(dt)
	if args.has("shots"):
		if _shot_list.is_empty():
			var spec := String(args["shots"]).split(":", true, 1)
			for v in spec[1].split(";"):
				var p := v.split(",")
				_shot_list.append([float(p[0]), float(p[1]), float(p[2]) if p.size() > 2 else 10.0])
			_set_view(0)
		if frame % 12 == 0:
			var outdir := String(args["shots"]).split(":", true, 1)[0]
			var v: Array = _shot_list[_shot_i]
			var base := "%s/v%02d_%d_%d_%sh" % [outdir, _shot_i, int(v[0]), int(v[1]), String.num(v[2], 1)]
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
	if args.has("quit_after") and frame >= int(args["quit_after"]):
		get_tree().quit()
