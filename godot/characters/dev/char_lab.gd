extends Node
## The character lab (docs/knowledge/24-3d-characters.md §verify): the saddle's terrain and grass,
## the renderer's time of day, one 3D character, at the round-4 numbers (640 x 360, 30 px per m).
## Everything she does here goes through Character3D's game interface (drive, face_angle, emotes,
## jump, sit, climb, pack), on a fixed 30 fps clock. Run with tools/characters3d/lab.sh. Options:
##   --char=kasasagi      --at=x,z (her spot)      --hours=h      --rain=0..1
##   --yaw=deg            her facing (0 toward the camera, 90 east)
##   --expr=name          her expression          --anim=name[@t]  a clip to hold / play
##   --pack               the carrying frame on   --heavy          the heavy gait
##   --shots=DIR:spec;spec;...   stills; spec = yaw,hours[,expr[,anim[,t]]]; native + window images
##   --turn=DIR[:hours]   turntable: every 15 degrees a still (native), then a continuous turn (frames)
##   --exprs=DIR[:yaw]    the expression sheet (one still per expression)
##   --frames=DIR --route=loop --secs=s   walk / run on a loop (native frames)
##   --show=DIR:name      a scripted showcase (names in SHOWS) recorded as native frames
##   --talk               she talks (mouth)
##   --nosprings          secondary motion off (checks)
##   --hat=t[,away[,roll]]  the hat's tilt facing the camera / facing away, and its roll (degrees)
##   --nograss

const SADDLE := "res://world3d/terrain/saddle"

## Showcases: [seconds, action, args...]. Actions: face yaw | walk dx dz speed | emote name |
## expr name | hold_expr name secs | variant name | jump h | sit | stand | pack on | heavy on |
## climb secs | talk on | stop
const SHOWS := {
	"emotes": [
		[0.0, "expr", "neutral"], [2.5, "variant", "idle_look"], [5.6, "variant", "idle"],
		[6.4, "emote", "tilt"], [8.4, "emote", "pout"], [10.8, "emote", "cheer"], [12.8, "emote", "sigh"],
		[15.4, "talk", true], [17.4, "talk", false], [17.6, "variant", "idle_hat"], [20.4, "variant", "idle_sway"],
		[24.0, "end"]],
	"moves": [
		[0.0, "face", 0.0], [1.0, "face", 90.0], [2.0, "walk", 3.2, 0.0, 1.5], [4.6, "face", 0.0],
		[5.6, "walk", -2.4, 1.0, 3.6], [7.0, "face", 180.0], [8.0, "face", 0.0], [8.8, "jump", 0.45],
		[10.6, "sit"], [14.0, "stand"], [15.6, "pack", true], [15.8, "heavy", true],
		[16.0, "walk", 2.0, -0.8, 0.9], [19.0, "heavy", false], [19.2, "walk", -1.0, 0.6, 1.5],
		[21.0, "face", 0.0], [22.0, "end"]],
	"climb": [
		[0.0, "face", 180.0], [0.6, "climb", 3.2], [4.4, "end"]],
	"wave": [
		[0.0, "face", 45.0], [0.4, "emote", "wave"], [2.4, "emote", "tilt"], [4.2, "end"]],
	# all the acts in one short take (15 s)
	"emotes3": [
		[0.0, "expr", "neutral"], [1.6, "variant", "idle_look"], [4.6, "variant", "idle"], [4.8, "emote", "tilt"],
		[6.4, "emote", "pout"], [8.4, "emote", "cheer"], [10.2, "emote", "wave"], [11.8, "variant", "idle_hat"],
		[14.6, "variant", "idle"], [15.0, "end"]],
	# the tails of "emotes" and "moves" as their own short takes
	"emotes2": [
		[0.0, "expr", "neutral"], [0.2, "talk", true], [2.2, "talk", false], [2.4, "variant", "idle_hat"],
		[5.2, "variant", "idle_sway"], [8.8, "end"]],
	"moves2": [
		[0.0, "face", 0.0], [0.4, "sit"], [3.8, "stand"], [5.2, "pack", true], [5.4, "heavy", true],
		[5.6, "walk", 2.0, -0.8, 0.9], [8.6, "heavy", false], [8.8, "walk", -1.0, 0.6, 1.5], [10.6, "face", 0.0],
		[11.4, "end"]],
	"turns": [
		[0.0, "face", 0.0], [0.5, "face", 120.0], [1.6, "face", 240.0], [2.7, "face", 0.0],
		[3.6, "walk", 1.8, 0.0, 1.5], [4.9, "walk", 0.0, -1.8, 1.5], [6.2, "walk", -1.8, 0.0, 1.5],
		[7.5, "walk", 0.0, 1.8, 1.5], [8.8, "face", 0.0], [10.0, "end"]],
}

var pv: CharLabView
var env: W3Env
var terrain: Terrain3D
var ch: Character3D
var args := {}
var frame := 0
var _queue: Array = []        # pending captures: [kind, data]
var _settle := 0
var _route: Array = []
var _route_t := 0.0
var _rec_dir := ""
var _rec_n := 0
var _rec_frames := 0
var _rec_kind := ""
# showcase state
var _show: Array = []
var _show_i := 0
var _vel := Vector3.ZERO
var _goal := Vector2.INF
var _goal_speed := 0.0
var _jump_t := -1.0
var _jump_h := 0.4
var _climb_left := 0.0
var _trunk: MeshInstance3D
var _pending_still := ""


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
		elif a.begins_with("--"):
			args[a.substr(2)] = "1"
	pv = CharLabView.new()
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	env.rain = float(args.get("rain", "0"))
	env.set_time(float(args.get("hours", "10.5")))
	terrain = Terrain3D.new()
	terrain.name = "Terrain"
	pv.world_root.add_child(terrain)
	terrain.load_region(SADDLE)
	if not args.has("nograss"):
		var grass := W3Grass.new()
		grass.name = "Grass"
		pv.world_root.add_child(grass)
		grass.build(terrain)
	ch = Character3D.new()
	ch.name = "Character"
	pv.world_root.add_child(ch)
	ch.setup(String(args.get("char", "kasasagi")))
	if args.has("nosprings") and ch.springs != null:
		ch.springs.active = false
	if args.has("spring_test") and ch.springs != null:
		# --spring_test=gravity|collisions|stiff: switch one ingredient off (checks)
		for k in ch.springs.setting_count:
			match String(args["spring_test"]):
				"gravity":
					ch.springs.set_gravity(k, 0.0)
				"collisions":
					ch.springs.set_collision_count(k, 0)
				"stiff":
					ch.springs.set_stiffness(k, 4.0)
	if args.has("mat"):
		# --mat=name:value,name:value: the character material's uniforms (checks)
		for kv in String(args["mat"]).split(","):
			var nv := kv.split(":")
			var v: Variant = int(nv[1]) if nv[0] == "c3_debug" else float(nv[1])
			ch.mat.set_shader_parameter(nv[0], v)
	if args.has("hat") and ch.hat_mod != null:
		# --hat=tilt[,tilt_away[,roll]] degrees: try the hat convention's numbers
		var hp := String(args["hat"]).split(",")
		ch.hat_mod.tilt = deg_to_rad(float(hp[0]))
		if hp.size() > 1:
			ch.hat_mod.tilt_away = deg_to_rad(float(hp[1]))
		if hp.size() > 2:
			ch.hat_mod.roll = deg_to_rad(float(hp[2]))
	# stills show the expression asked for, not a blink that happened to fall on the frame
	var stills := args.has("shots") or args.has("exprs") or args.has("turn")
	ch.blink_enabled = not stills
	ch.idle_variants_enabled = not stills and not args.has("show")
	var at := Vector2(-17.6, 17.2)
	if args.has("at"):
		var p := String(args["at"]).split(",")
		at = Vector2(float(p[0]), float(p[1]))
	_place(at)
	ch.face_angle(deg_to_rad(float(args.get("yaw", "0"))), true)
	if args.has("expr"):
		ch.set_expression(String(args["expr"]))
	if args.has("anim"):
		var an := String(args["anim"]).split("@")
		ch.hold_anim(an[0], float(an[1]) if an.size() > 1 else 0.0)
	if args.has("pack"):
		ch.set_pack(true)
	if args.has("heavy"):
		ch.set_heavy(true)
	if args.has("talk"):
		ch.set_talking(true)
	pv.follow(_cam_target, {"cut": true})
	_plan()


func _place(at: Vector2) -> void:
	var y := terrain.height_at(at.x, at.y)
	ch.position = Vector3(at.x, y, at.y)
	ch.ground_y = y


func _cam_target() -> Vector3:
	var k := tan(deg_to_rad(pv.pitch_deg) * 0.5)
	return Vector3(ch.position.x, ch.ground_y, ch.position.z) + Vector3(0.0, 0.9, -0.9 * k)


# ------------------------------------------------------------------------------------------------
# capture plans

func _plan() -> void:
	if args.has("shots"):
		var parts := String(args["shots"]).split(":", true, 1)
		for spec in parts[1].split(";"):
			_queue.append(["still", parts[0], spec])
	if args.has("turn"):
		var tp := String(args["turn"]).split(":")
		var hours := float(tp[1]) if tp.size() > 1 else env.hours
		for k in 24:
			_queue.append(["still", tp[0], "%d,%s" % [k * 15, String.num(hours, 2)]])
		_queue.append(["spin", tp[0], hours])
	if args.has("exprs"):
		var ep := String(args["exprs"]).split(":")
		var yaw := ep[1] if ep.size() > 1 else "0"
		var names: Dictionary = ch.face_meta.get("expressions", {})
		for n in names:
			_queue.append(["still", ep[0], "%s,%s,%s" % [yaw, String.num(env.hours, 2), n]])
	if args.has("frames"):
		_queue.append(["route", String(args["frames"]), String(args.get("route", "loop"))])
	if args.has("show"):
		var sp := String(args["show"]).split(":")
		_queue.append(["show", sp[0], sp[1] if sp.size() > 1 else "emotes"])
	_settle = int(args.get("settle", "12"))


func _process(dt: float) -> void:
	frame += 1
	env.tick(dt)
	if _rec_dir != "":
		match _rec_kind:
			"route":
				_drive_route(dt)
			"spin":
				ch.face_angle(TAU * float(_rec_n) / float(_rec_frames), true)
				ch.drive(Vector3.ZERO, dt)
			"show":
				_drive_show(dt)
	pv.update_camera(dt)
	if _queue.is_empty() and _rec_dir == "":
		if args.has("quit_after") and frame >= int(args["quit_after"]):
			get_tree().quit()
		if (args.has("shots") or args.has("turn") or args.has("exprs") or args.has("frames") or args.has("show")) and frame > 2:
			get_tree().quit()
		return
	if _rec_dir != "":
		_save_native("%s/f%05d.png" % [_rec_dir, _rec_n])
		_rec_n += 1
		if _rec_n >= _rec_frames:
			_rec_dir = ""
			ch.drive(Vector3.ZERO, dt)
		return
	if _settle > 0:
		_settle -= 1
		return
	var job: Array = _queue.pop_front()
	match String(job[0]):
		"still":
			_do_still(job[1], job[2])
		"spin":
			env.set_time(float(job[2]))
			_start_rec(String(job[1]) + "/spin", int(args.get("spin_frames", "180")), "spin")
		"route":
			_start_route(job[1], job[2])
		"show":
			_start_show(job[1], job[2])


func _do_still(dir: String, spec: String) -> void:
	# first frame: set up; the image is taken a few frames later
	if _pending_still == "":
		var f := spec.split(",")
		ch.stop_emote()
		ch.hold_anim("idle")
		ch.held_anim = ""
		ch.face_angle(deg_to_rad(float(f[0])), true)
		env.set_time(float(f[1]))
		if f.size() > 2 and f[2] != "":
			ch.set_expression(f[2])
		var wait := 0
		if f.size() > 3 and f[3] != "":
			var t := float(f[4]) if f.size() > 4 else 0.0
			ch.hold_anim(f[3], t)
			# a gait clip is held at time t; any other clip plays, and the still waits t seconds into it
			if not (f[3] in ["walk", "run", "heavy_walk", "turn_step", "idle"]):
				wait = int(t * 30.0)
		_pending_still = "%s/%s" % [dir, spec.replace(",", "_").replace(".", "p")]
		_queue.push_front(["still", dir, spec])
		_settle = int(args.get("still_settle", "4")) + wait
		return
	DirAccess.make_dir_recursive_absolute(dir)
	_save_native(_pending_still + ".png")
	get_viewport().get_texture().get_image().save_png(_pending_still + "_win.png")
	print("STILL ", _pending_still)
	if ch.hat_mod != null:
		print("  hat t=%.1f fwd=%s look_up=%.1f" % [rad_to_deg(ch.hat_mod.last_t), ch.hat_mod.last_fwd, rad_to_deg(ch.hat_mod.last_look_up)])
	_pending_still = ""


func _start_rec(dir: String, frames: int, kind: String) -> void:
	_rec_dir = dir
	DirAccess.make_dir_recursive_absolute(_rec_dir)
	_rec_n = 0
	_rec_frames = frames
	_rec_kind = kind


func _start_route(dir: String, kind: String) -> void:
	_start_rec(dir, int(float(args.get("secs", "12")) * 30.0), "route")
	var c := Vector2(ch.position.x, ch.position.z)
	_route = []
	if kind == "loop":
		# a rounded loop over grass and the yard's packed earth
		for k in 33:
			var a := TAU * k / 32.0
			_route.append(c + Vector2(cos(a) * 2.6, sin(a) * 1.7))
	_route_t = 0.0


## The loop: walk 0-40 %, stand, run 50-85 %, stand.
func _drive_route(dt: float) -> void:
	var secs := float(_rec_frames) / 30.0
	var ph := (float(_rec_n) / 30.0) / secs
	var speed := 0.0
	if ph < 0.4:
		speed = 1.5
	elif ph >= 0.5 and ph < 0.85:
		speed = 3.6
	var cur := Vector2(ch.position.x, ch.position.z)
	var want := Vector3.ZERO
	if speed > 0.0:
		var target: Vector2 = _route[int(_route_t) % _route.size()]
		var to := target - cur
		if to.length() < 0.35:
			_route_t += 1.0
			target = _route[int(_route_t) % _route.size()]
			to = target - cur
		var d := to.normalized() * speed
		want = Vector3(d.x, 0.0, d.y)
	_move(want, dt)


## A body that accelerates and brakes like a person (not instantly), on the terrain.
func _move(want: Vector3, dt: float) -> void:
	var k := 1.0 - exp(-dt * (9.0 if want.length() > _vel.length() else 7.0))
	_vel = _vel.lerp(want, k)
	if want == Vector3.ZERO and _vel.length() < 0.05:
		_vel = Vector3.ZERO
	var np := Vector2(ch.position.x, ch.position.z) + Vector2(_vel.x, _vel.z) * dt
	var y := terrain.height_at(np.x, np.y)
	ch.ground_y = y
	var lift := ch.position.y - ch.ground_y if _jump_t >= 0.0 or _climb_left > 0.0 else 0.0
	ch.position = Vector3(np.x, y + lift, np.y)
	ch.drive(_vel, dt)


# ------------------------------------------------------------------------------------------------
# showcases

func _start_show(dir: String, name: String) -> void:
	_show = SHOWS.get(name, [])
	_show_i = 0
	var end := 10.0
	for e in _show:
		if e[1] == "end":
			end = e[0]
	_start_rec(dir, int(end * 30.0), "show")


func _drive_show(dt: float) -> void:
	var t := float(_rec_n) / 30.0
	while _show_i < _show.size() and float(_show[_show_i][0]) <= t:
		_show_event(_show[_show_i])
		_show_i += 1
	var want := Vector3.ZERO
	if _goal != Vector2.INF:
		var cur := Vector2(ch.position.x, ch.position.z)
		var to := _goal - cur
		var stop_d := _vel.length() * _vel.length() / (2.0 * 4.0)
		if to.length() < maxf(0.05, stop_d * 0.6):
			_goal = Vector2.INF
		else:
			var d := to.normalized() * _goal_speed
			want = Vector3(d.x, 0.0, d.y)
	_move(want, dt)
	# the jump: up after the crouch, a parabola, the landing
	if _jump_t >= 0.0:
		_jump_t += dt
		var t0 := 0.26
		var air := 0.62
		var h := 0.0
		if _jump_t > t0 and _jump_t < t0 + air:
			var x := (_jump_t - t0) / air
			h = 4.0 * _jump_h * x * (1.0 - x)
		ch.position.y = ch.ground_y + h
		if _jump_t >= t0 + air - 0.05 and _jump_t - dt < t0 + air - 0.05:
			ch.land()
		if _jump_t >= t0 + air:
			ch.position.y = ch.ground_y
			_jump_t = -1.0
	if _climb_left > 0.0:
		_climb_left -= dt
		ch.position.y += 0.5 * dt
		if _climb_left <= 0.0:
			ch.set_climbing(false)


func _show_event(e: Array) -> void:
	var cur := Vector2(ch.position.x, ch.position.z)
	match String(e[1]):
		"face":
			ch.face_angle(deg_to_rad(float(e[2])))
		"walk":
			_goal = cur + Vector2(float(e[2]), float(e[3]))
			_goal_speed = float(e[4])
		"emote":
			ch.play_emote(String(e[2]))
		"expr":
			ch.set_expression(String(e[2]))
		"hold_expr":
			ch.set_expression(String(e[2]), float(e[3]))
		"variant":
			ch.hold_anim(String(e[2]))
			ch.held_anim = ""
		"jump":
			_jump_h = float(e[2])
			_jump_t = 0.0
			ch.jump()
		"sit":
			ch.sit()
		"stand":
			ch.stand()
		"pack":
			ch.set_pack(bool(e[2]))
		"heavy":
			ch.set_heavy(bool(e[2]))
		"talk":
			ch.set_talking(bool(e[2]))
		"climb":
			_add_trunk()
			ch.set_climbing(true)
			_climb_left = float(e[2])


## A post to climb (a stand-in for the great camphor's trunk), just north of her.
func _add_trunk() -> void:
	if _trunk != null:
		return
	_trunk = MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.22
	cyl.bottom_radius = 0.26
	cyl.height = 4.0
	cyl.radial_segments = 16
	# the lean's base is the mesh's origin: the post stands on it, so its geometry is lifted
	var arr := cyl.get_mesh_arrays()
	var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	for i in v.size():
		v[i] += Vector3(0.0, 2.0, 0.0)
	arr[Mesh.ARRAY_VERTEX] = v
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	_trunk.mesh = am
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/toon_solid.gdshader")
	m.set_shader_parameter("tint", Color(0.42, 0.33, 0.26))
	_trunk.material_override = m
	pv.world_root.add_child(_trunk)
	_trunk.position = Vector3(ch.position.x, ch.ground_y, ch.position.z - 0.42)


## The native frame as displayed (graded): one pixel per native pixel, taken from the centre of each
## s x s block of the window image (C++ resize, nearest; the block centre survives the camera's
## whole-window-pixel remainder shift).
func _save_native(path: String) -> void:
	var win := get_viewport().get_texture().get_image()
	var s := pv.scale_factor
	var lg := Vector2i(pv.logical)
	var off := Vector2i(pv.margin)
	var reg := win.get_region(Rect2i(off, lg * s))
	reg.resize(lg.x, lg.y, Image.INTERPOLATE_NEAREST)
	reg.convert(Image.FORMAT_RGB8)
	reg.save_png(path)
