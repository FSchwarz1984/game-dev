class_name Character3D
extends Node3D
## A 3D character drawn in the pixel world (docs/knowledge/24-3d-characters.md): the skinned model
## from tools/characters3d (glTF + rig.json + face atlas), the character material
## (shaders/char_toon.gdshader: soft cel light, lean, pixel snap, face stamps; x-ray next pass),
## continuous facing, an AnimationTree (gait locked to the ground speed, idle variants, actions,
## one-shot emotes), spring bones for hair / sleeves / haori / sash, the hat convention
## (hat_tilt_modifier.gd) and the face (pixel stamps placed on the screen lattice every frame).
##
## The node's position is her feet (the logical ground point); the caller moves it. Interface:
##   setup(id)                       load a character (res://characters/<id>/)
##   drive(velocity, dt)             she moves at this ground velocity (world m/s): gait, facing, lean
##   face_angle(yaw, instant)        turn to a yaw (radians; 0 toward the camera / south, +pi/2 east)
##   set_expression(name, hold)      the face (face.json "expressions"); hold > 0: seconds, then back
##   set_talking(on)                 the mouth moves as she talks
##   play_emote(name)                one-shot acts: tilt, pout, cheer, sigh, wave, stop (its face too)
##   stop_emote()                    end a one-shot at once (a cut)
##   jump(), land()                  the jump's start and landing (the caller moves her through the air,
##                                   lifting `position` above `ground_y`)
##   set_climbing(on)                the climbing loop (she faces the trunk; the caller lifts her)
##   sit(), stand()                  seiza and back up
##   set_pack(on)                    the carrying frame (背負子) on her back
##   set_heavy(on)                   the heavy gait (she took 「重」)
##   ground_y                        ground height under her (the lean's base, for jumps)
##   wind                            the world's wind (m/s, world); her own motion is added inside
##   chest() -> Vector3              for the camera and the canopy cut-away
##   Character3D.set_view(ppm, pitch_deg)   whoever sets the w3_view globals calls this too (static)
## Expressions: neutral smile happy grin mischief cat curious surprised angry sad teary cry smug sleepy
## pout embarrassed (face.json); idle variants play by themselves after a while standing still.
## Signals: emote_finished(name)

signal emote_finished(name: String)

const FACE_FRONT := 0.80
const FACE_THREE := 0.42
const FACE_SIDE := 0.10
const TURN_RATE := 640.0           # deg/s, the fastest she turns
const IDLE_VARIANTS := ["idle_look", "idle_sway", "idle_hat"]
const EMOTE_FACE := {"tilt": "curious", "pout": "pout", "cheer": "happy", "sigh": "sleepy", "idle_hat": "mischief",
	"idle_look": "neutral", "idle_sway": "smile", "wave": "grin", "stop": ""}
const EMOTES := ["tilt", "pout", "cheer", "sigh", "wave", "stop"]

var char_id := "kasasagi"
var model: Node3D
var skel: Skeleton3D
var anim_player: AnimationPlayer
var tree: AnimationTree
var springs: SpringBoneSimulator3D
var hat_mod: HatTiltModifier
var head_snap: HeadSnapModifier
var head_turn: HeadTurnModifier
var meshes: Array[MeshInstance3D] = []
var mat: ShaderMaterial
var xray_mat: ShaderMaterial
var face_meta := {}
var rig_meta := {}
var landmarks := {}            # name -> [Vector3 local to the head bone, Vector3 normal (local)]
var head_bone := -1
var ground_y := 0.0

# motion state
var facing := 0.0
var target_facing := 0.0
var ground_speed := 0.0
var _vel := Vector3.ZERO
var _prev_vel := Vector3.ZERO
var _yaw_rate := 0.0
var _lean := Vector2.ZERO          # forward, side (radians)
var _phase := 0.0
var _move := 0.0
var _run := 0.0
var _heavy_k := 0.0
var _turn_k := 0.0
var _act := ""                     # current action clip ("" none)
var _act_k := 0.0
var _act_t := 0.0
var heavy := false
var held_anim := ""
var held_t := 0.0
var idle_variants_enabled := true
var _idle_t := 0.0
var _idle_next := 6.0
var _idle_variant := ""
var _variant_left := 0.0
var _emote := ""
var _was_moving := false
var _clip_len := {}

# face state
var expression := "neutral"
var talking := false
var blink_enabled := true
var _base_expression := "neutral"
var _expr_hold := -1.0
var _blink_t := 2.0
var _blink_on := 0.0
var _talk_t := 0.0
var _talk_i := 0
var _anim_frame_t := 0.0
var _face_dt := 0.0

var pack: Node3D


func setup(id: String) -> void:
	char_id = id
	var dir := "res://characters/%s" % id
	var scene: PackedScene = load("%s/%s.glb" % [dir, id])
	model = scene.instantiate()
	model.name = "Model"
	add_child(model)
	face_meta = _load_json("%s/face.json" % dir)
	rig_meta = _load_json("%s/rig.json" % dir)
	mat = ShaderMaterial.new()
	mat.shader = load("res://characters/shaders/char_toon.gdshader")
	xray_mat = ShaderMaterial.new()
	xray_mat.shader = load("res://characters/shaders/char_xray.gdshader")
	xray_mat.render_priority = 120
	mat.next_pass = xray_mat
	# copied into an ImageTexture: a texture used by a 3D material gets its import switched to VRAM
	# compression by the editor (detect_3d), which would blur the pixel stamps
	var atlas: Texture2D = load("%s/face_atlas.png" % dir)
	mat.set_shader_parameter("c3_face_atlas", ImageTexture.create_from_image(atlas.get_image()))
	mat.set_shader_parameter("c3_atlas_cols", int(face_meta.get("cols", 16)))
	_collect(model)
	for m in meshes:
		m.material_override = mat
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		m.extra_cull_margin = 1.5
	if skel != null:
		head_bone = skel.find_bone("head")
		if anim_player != null:
			_setup_animation()
		_setup_springs()
		_setup_hat()
		_setup_head_snap()
		_setup_head_turn()
		skel.skeleton_updated.connect(_on_skeleton_updated)
	_read_landmarks()


func _load_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	return JSON.parse_string(f.get_as_text())


func _collect(n: Node) -> void:
	if n is MeshInstance3D:
		meshes.append(n)
	if n is Skeleton3D and skel == null:
		skel = n
	if n is AnimationPlayer and anim_player == null:
		anim_player = n
	for c in n.get_children():
		_collect(c)


func _read_landmarks() -> void:
	var lm: Dictionary = rig_meta.get("landmarks", {})
	var head_rest := Transform3D.IDENTITY
	if skel != null and head_bone >= 0:
		head_rest = skel.get_bone_global_rest(head_bone)
	var inv := head_rest.affine_inverse()
	for k in lm:
		var p: Array = lm[k]["p"]
		var n: Array = lm[k]["n"]
		landmarks[k] = [inv * Vector3(p[0], p[1], p[2]), (inv.basis * Vector3(n[0], n[1], n[2])).normalized()]


# ------------------------------------------------------------------------------------------------
# animation tree

func _anim(name: String) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = name
	return a


func _setup_animation() -> void:
	var clips: Dictionary = rig_meta.get("clips", {})
	var lib := anim_player.get_animation_library("")
	for n in lib.get_animation_list():
		var a := lib.get_animation(n)
		_clip_len[String(n)] = a.length
		if clips.get(String(n), {}).get("loop", false):
			a.loop_mode = Animation.LOOP_LINEAR
	var bt := AnimationNodeBlendTree.new()
	# idle and its variants
	var idle_x := AnimationNodeTransition.new()
	idle_x.xfade_time = 0.4
	var idles: Array = ["idle"] + IDLE_VARIANTS
	for n in idles:
		idle_x.add_input(n)
	bt.add_node("idle_x", idle_x)
	for i in idles.size():
		bt.add_node("a_" + idles[i], _anim(idles[i]))
		bt.connect_node("idle_x", i, "a_" + idles[i])
	# the gait: walk / run / heavy, each seeked to one shared phase (feet locked to the ground)
	for n in ["walk", "run", "heavy_walk"]:
		bt.add_node("a_" + n, _anim(n))
		bt.add_node("s_" + n, AnimationNodeTimeSeek.new())
		bt.connect_node("s_" + n, 0, "a_" + n)
	bt.add_node("walk_run", AnimationNodeBlend2.new())
	bt.connect_node("walk_run", 0, "s_walk")
	bt.connect_node("walk_run", 1, "s_run")
	bt.add_node("gait", AnimationNodeBlend2.new())
	bt.connect_node("gait", 0, "walk_run")
	bt.connect_node("gait", 1, "s_heavy_walk")
	bt.add_node("a_turn", _anim("turn_step"))
	bt.add_node("stand", AnimationNodeBlend2.new())
	bt.connect_node("stand", 0, "idle_x")
	bt.connect_node("stand", 1, "a_turn")
	bt.add_node("loco", AnimationNodeBlend2.new())
	bt.connect_node("loco", 0, "stand")
	bt.connect_node("loco", 1, "gait")
	# actions that replace the locomotion (jump, climb, sit)
	var acts := ["jump_start", "jump_air", "jump_land", "climb", "sit_down", "sit_idle", "stand_up"]
	var act_x := AnimationNodeTransition.new()
	act_x.xfade_time = 0.12
	for n in acts:
		act_x.add_input(n)
	bt.add_node("act_x", act_x)
	for i in acts.size():
		bt.add_node("a_" + acts[i], _anim(acts[i]))
		bt.connect_node("act_x", i, "a_" + acts[i])
	bt.add_node("act", AnimationNodeBlend2.new())
	bt.connect_node("act", 0, "loco")
	bt.connect_node("act", 1, "act_x")
	# one-shot emotes over everything
	var shot := AnimationNodeOneShot.new()
	shot.fadein_time = 0.18
	shot.fadeout_time = 0.3
	bt.add_node("emote", shot)
	bt.add_node("a_emote", _anim("tilt"))
	bt.connect_node("emote", 0, "act")
	bt.connect_node("emote", 1, "a_emote")
	bt.connect_node("output", 0, "emote")
	tree = AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = bt
	model.add_child(tree)
	tree.anim_player = tree.get_path_to(anim_player)
	tree.active = true
	for b in ["walk_run", "gait", "stand", "loco", "act"]:
		_set_blend(b, 0.0)


func _set_blend(node: String, v: float) -> void:
	tree.set("parameters/%s/blend_amount" % node, v)


# ------------------------------------------------------------------------------------------------
# spring bones (rig.json "springs": chains with stiffness, drag, gravity, radius; "colliders")

func _setup_springs() -> void:
	var chains: Array = rig_meta.get("springs", [])
	if chains.is_empty():
		return
	springs = SpringBoneSimulator3D.new()
	springs.name = "Springs"
	skel.add_child(springs)
	var cols: Array = rig_meta.get("colliders", [])
	var by_name := {}
	for c in cols:
		var cap := SpringBoneCollisionCapsule3D.new()
		cap.name = String(c["name"])
		springs.add_child(cap)
		cap.bone_name = String(c["bone"])
		cap.radius = float(c["radius"])
		cap.height = maxf(float(c["height"]), cap.radius * 2.0 + 0.001)
		var off: Array = c.get("offset", [0, 0, 0])
		cap.position_offset = Vector3(off[0], off[1], off[2])
		var rot: Array = c.get("rot", [0, 0, 0])
		cap.rotation_offset = Quaternion.from_euler(Vector3(deg_to_rad(rot[0]), deg_to_rad(rot[1]), deg_to_rad(rot[2])))
		by_name[cap.name] = cap
	springs.setting_count = chains.size()
	for k in chains.size():
		var c: Dictionary = chains[k]
		springs.set_root_bone_name(k, c["root"])
		springs.set_end_bone_name(k, c["end"])
		springs.set_extend_end_bone(k, true)
		springs.set_end_bone_direction(k, SkeletonModifier3D.BONE_DIRECTION_FROM_PARENT)
		springs.set_end_bone_length(k, float(c.get("tip", 0.1)))
		springs.set_stiffness(k, float(c.get("stiffness", 1.0)))
		springs.set_drag(k, float(c.get("drag", 0.4)))
		springs.set_gravity(k, float(c.get("gravity", 0.0)))
		springs.set_radius(k, float(c.get("radius", 0.02)))
		# inertia is measured against this node (it moves with her but does not turn): walking at a
		# steady pace does not fling the hair, her turns, bobs and stops do; the air of her own speed
		# is the breeze below (_update_wind)
		springs.set_center_from(k, SpringBoneSimulator3D.CENTER_FROM_NODE)
		springs.set_center_node(k, springs.get_path_to(self))
		springs.set_enable_all_child_collisions(k, false)
		var names: Array = c.get("collide", [])
		springs.set_collision_count(k, names.size())
		for j in names.size():
			if by_name.has(names[j]):
				springs.set_collision_path(k, j, springs.get_path_to(by_name[names[j]]))


func _setup_head_snap() -> void:
	if head_bone < 0:
		return
	head_snap = HeadSnapModifier.new()
	head_snap.name = "HeadSnap"
	head_snap.bone = head_bone
	head_snap.character = self
	skel.add_child(head_snap)
	skel.move_child(head_snap, 0)          # first: the hat and the springs hang from the head


func _setup_head_turn() -> void:
	if head_bone < 0:
		return
	head_turn = HeadTurnModifier.new()
	head_turn.name = "HeadTurn"
	head_turn.bone = head_bone
	head_turn.bias = deg_to_rad(float(rig_meta.get("head_turn_bias_deg", 20.0)))
	skel.add_child(head_turn)
	skel.move_child(head_turn, 0)          # before the snap, the hat and the springs


func _setup_hat() -> void:
	var hb := skel.find_bone("hat")
	if hb < 0:
		return
	hat_mod = HatTiltModifier.new()
	hat_mod.name = "HatTilt"
	hat_mod.bone = hb
	hat_mod.head_bone = head_bone
	hat_mod.tilt = deg_to_rad(float(rig_meta.get("hat_tilt_deg", 52.0)))
	hat_mod.tilt_away = deg_to_rad(float(rig_meta.get("hat_tilt_away_deg", 24.0)))
	hat_mod.roll = deg_to_rad(float(rig_meta.get("hat_roll_deg", 12.0)))
	skel.add_child(hat_mod)
	# the hat turns before the springs run
	skel.move_child(hat_mod, 0)


# ------------------------------------------------------------------------------------------------
# the game's interface

## Turn to a yaw (radians; 0 toward the camera / south, +pi/2 east). Not instant: she turns at her
## own pace (a step on the spot when she stands).
func face_angle(yaw: float, instant := false) -> void:
	target_facing = yaw
	if instant:
		facing = yaw
		_yaw_rate = 0.0
		_apply_body()


## She moves at this ground velocity (world, m/s); the caller moves the node.
func drive(vel: Vector3, _dt := 0.0) -> void:
	_vel = Vector3(vel.x, 0.0, vel.z)
	var h := Vector2(_vel.x, _vel.z)
	ground_speed = h.length()
	if ground_speed > 0.08:
		target_facing = atan2(h.x, h.y)


func set_expression(name: String, hold := -1.0) -> void:
	if hold > 0.0:
		_expr_hold = hold
	else:
		_base_expression = name
		_expr_hold = -1.0
	expression = name


func set_talking(on: bool) -> void:
	talking = on


func set_heavy(on: bool) -> void:
	heavy = on


func play_emote(name: String) -> void:
	if tree == null or not _clip_len.has(name):
		return
	(tree.tree_root.get_node("a_emote") as AnimationNodeAnimation).animation = name
	tree.set("parameters/emote/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	_emote = name
	var f: String = EMOTE_FACE.get(name, "")
	if f != "":
		set_expression(f, _clip_len[name] * 0.9)


## Ends a one-shot emote at once (the lab between stills; a cut in a scene).
func stop_emote() -> void:
	if tree != null:
		tree.set("parameters/emote/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)
	_emote = ""


func jump() -> void:
	_start_act("jump_start")


func land() -> void:
	_start_act("jump_land")


func set_climbing(on: bool) -> void:
	if on:
		_start_act("climb")
	elif _act == "climb":
		_act = ""


func sit() -> void:
	_start_act("sit_down")


func stand() -> void:
	if _act in ["sit_down", "sit_idle"]:
		_start_act("stand_up")


func set_pack(on: bool) -> void:
	if on and pack == null and skel != null:
		var path := "res://characters/props/shoiko.glb"
		if not ResourceLoader.exists(path):
			return
		var att := BoneAttachment3D.new()
		att.name = "PackMount"
		skel.add_child(att)
		att.bone_name = "chest"
		pack = (load(path) as PackedScene).instantiate()
		att.add_child(pack)
		# modelled in her model space: the bone's inverse rest puts it back where it was modelled
		pack.transform = skel.get_bone_global_rest(skel.find_bone("chest")).affine_inverse()
		for c in _all_meshes(pack):
			c.material_override = mat
			meshes.append(c)
	if pack != null:
		(pack.get_parent() as Node3D).visible = on


func _all_meshes(n: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	if n is MeshInstance3D:
		out.append(n)
	for c in n.get_children():
		out.append_array(_all_meshes(c))
	return out


## Hold one clip at a time (lab stills): the gait clips at a time in seconds; others play.
func hold_anim(name: String, t := 0.0) -> void:
	held_anim = name
	held_t = t
	if tree == null:
		return
	if name in ["jump_start", "jump_air", "jump_land", "climb", "sit_down", "sit_idle", "stand_up"]:
		_start_act(name)
	elif name in IDLE_VARIANTS or name == "idle":
		tree.set("parameters/idle_x/transition_request", name)
	elif name in EMOTES:
		play_emote(name)


func set_xray_colour(c: Color) -> void:
	xray_mat.set_shader_parameter("line_col", c)


func chest() -> Vector3:
	return global_position + Vector3(0, 0.9, 0)


func _start_act(name: String) -> void:
	_act = name
	_act_t = 0.0
	tree.set("parameters/act_x/transition_request", name)


# ------------------------------------------------------------------------------------------------
# per frame

func _process(dt: float) -> void:
	if tree != null:
		_update_motion(dt)
	else:
		facing = target_facing
	_apply_body()
	_update_instance()
	if skel == null:
		_update_face(dt)
	else:
		_face_dt += dt


func _on_skeleton_updated() -> void:
	_update_face(_face_dt)
	_face_dt = 0.0


func _update_motion(dt: float) -> void:
	# turning: the body eases toward the wanted yaw (quicker when she moves); the yaw rate drives the
	# lean and the stepping on the spot
	var d := wrapf(target_facing - facing, -PI, PI)
	var rate := deg_to_rad(TURN_RATE) * (0.55 + 0.45 * clampf(ground_speed / 1.5, 0.0, 1.0))
	var step := clampf(d * 10.0 * dt, -rate * dt, rate * dt)
	if absf(d) < 0.002:
		step = d
	facing = wrapf(facing + step, -PI, PI)
	_yaw_rate = lerpf(_yaw_rate, step / maxf(dt, 1e-4), clampf(dt * 12.0, 0.0, 1.0))
	var clips: Dictionary = rig_meta.get("clips", {})
	var walk_v := float(clips.get("walk", {}).get("speed", 1.5))
	var run_v := float(clips.get("run", {}).get("speed", 3.6))
	var heavy_v := float(clips.get("heavy_walk", {}).get("speed", 0.95))
	var sp := ground_speed
	_move = move_toward(_move, smoothstep(0.03, 0.45, sp), dt * 6.0)
	_run = move_toward(_run, smoothstep(walk_v * 1.25, run_v * 0.8, sp), dt * 4.0)
	_heavy_k = move_toward(_heavy_k, 1.0 if heavy else 0.0, dt * 3.0)
	var turning := clampf((absf(_yaw_rate) - 1.2) / 2.0, 0.0, 1.0) * (1.0 - _move)
	_turn_k = move_toward(_turn_k, turning, dt * 8.0)
	# the gait phase advances by the distance covered: one loop is the cycle's own stride
	var loop_m := lerpf(walk_v * float(_clip_len.get("walk", 0.6)), run_v * float(_clip_len.get("run", 0.4)), _run)
	loop_m = lerpf(loop_m, heavy_v * float(_clip_len.get("heavy_walk", 0.87)), _heavy_k)
	_phase = fposmod(_phase + sp * dt / maxf(loop_m, 0.1), 1.0)
	if sp < 0.03 and _move < 0.05:
		_phase = 0.0
	var held_gait := held_anim in ["walk", "run", "heavy_walk"]
	for n in ["walk", "run", "heavy_walk"]:
		var t: float = held_t if held_gait else _phase * float(_clip_len.get(n, 1.0))
		tree.set("parameters/s_%s/seek_request" % n, t)
	if held_gait:
		_set_blend("loco", 1.0)
		_set_blend("walk_run", 1.0 if held_anim == "run" else 0.0)
		_set_blend("gait", 1.0 if held_anim == "heavy_walk" else 0.0)
		_set_blend("stand", 0.0)
	else:
		_set_blend("walk_run", _run)
		_set_blend("gait", _heavy_k)
		_set_blend("stand", _turn_k)
		_set_blend("loco", _move)
	# a stop: the body carries on and settles (one shot), when she was moving briskly
	if _was_moving and sp < 0.1 and _act == "" and _emote == "":
		play_emote("stop")
		_was_moving = false
	elif sp > 0.6:
		_was_moving = true
	# idle variants after a while standing still
	if _move < 0.02 and _act == "" and idle_variants_enabled and held_anim == "":
		_idle_t += dt
		if _idle_variant != "":
			_variant_left -= dt
			if _variant_left <= 0.0:
				tree.set("parameters/idle_x/transition_request", "idle")
				_idle_variant = ""
				_idle_next = randf_range(5.0, 9.0)
				_idle_t = 0.0
		elif _idle_t > _idle_next:
			_idle_variant = IDLE_VARIANTS[randi() % IDLE_VARIANTS.size()]
			tree.set("parameters/idle_x/transition_request", _idle_variant)
			_variant_left = float(_clip_len.get(_idle_variant, 3.0)) * (2.0 if _idle_variant == "idle_sway" else 1.0)
			var f: String = EMOTE_FACE.get(_idle_variant, "")
			if f != "":
				set_expression(f, _variant_left)
	elif held_anim == "":
		_idle_t = 0.0
		if _idle_variant != "":
			tree.set("parameters/idle_x/transition_request", "idle")
			_idle_variant = ""
	# actions
	if _act != "":
		_act_t += dt
		var alen: float = _clip_len.get(_act, 1.0)
		if _act == "jump_start" and _act_t >= alen:
			_start_act("jump_air")
		elif _act == "jump_land" and _act_t >= alen:
			_act = ""
		elif _act == "sit_down" and _act_t >= alen:
			_start_act("sit_idle")
		elif _act == "stand_up" and _act_t >= alen:
			_act = ""
	_act_k = move_toward(_act_k, 1.0 if _act != "" else 0.0, dt * 8.0)
	_set_blend("act", _act_k)
	if _emote != "" and not bool(tree.get("parameters/emote/active")):
		var e := _emote
		_emote = ""
		emote_finished.emit(e)
	# lean: into the acceleration (forward / back) and into the turn (side), springy
	var acc := (_vel - _prev_vel) / maxf(dt, 1e-4)
	_prev_vel = _vel
	var fwd := Vector3(sin(facing), 0.0, cos(facing))
	var right := Vector3(-cos(facing), 0.0, sin(facing))
	var want_f := clampf(acc.dot(fwd) * 0.03, -0.10, 0.14) + 0.04 * _run * _move
	var want_s := clampf(-_yaw_rate * sp * 0.045, -0.18, 0.18) + clampf(acc.dot(right) * -0.015, -0.06, 0.06)
	_lean = _lean.lerp(Vector2(want_f, want_s), clampf(dt * 9.0, 0.0, 1.0))


func _apply_body() -> void:
	if model == null:
		return
	model.rotation = Vector3(_lean.x, facing, _lean.y)
	_update_wind()


## The air she moves through pushes her hair, sleeves and sash back (and the world's wind, when the
## caller sets `wind`): one external force, scaled per chain by rig.json "wind".
var wind := Vector3.ZERO


func _update_wind() -> void:
	if springs == null:
		return
	# one force for the simulator (Godot 4.7 has a single external force per simulator)
	springs.external_force = (-_vel + wind) * 0.22


## The anchor and lean base every material reads (instance uniforms).
func _update_instance() -> void:
	var p := global_position
	for m in meshes:
		m.set_instance_shader_parameter("c3_anchor", p)
		m.set_instance_shader_parameter("c3_base_y", ground_y)


# ------------------------------------------------------------------------------------------------
# the face

## The view numbers the shaders read from the global w3_view (px per metre, sin and cos of the pitch,
## lean k). Global shader parameters cannot be read back at run time, so whoever sets w3_view also
## calls Character3D.set_view() (the renderer's PixelView3D.apply_view_globals; the lab's view).
static var view_numbers := Vector4(30.0, sin(deg_to_rad(55.0)), cos(deg_to_rad(55.0)), tan(deg_to_rad(27.5)))


static func set_view(ppm: float, pitch_deg: float) -> void:
	var p := deg_to_rad(pitch_deg)
	view_numbers = Vector4(ppm, sin(p), cos(p), tan(p * 0.5))


func _screen(wp: Vector3, v: Vector4) -> Vector2:
	return Vector2(wp.x, wp.y * v.z - wp.z * v.y) * v.x


## The rendered (leaned, snapped) position of a point of her body, exactly as the shader does it.
func _rendered(wp: Vector3, v: Vector4) -> Vector3:
	wp.z -= v.w * (wp.y - ground_y)
	var a := global_position
	a.z -= v.w * (a.y - ground_y)
	var s := _screen(a, v)
	var d := s.round() - s
	return wp + Vector3(d.x / v.x, 0, 0) + Vector3(0, v.z, -v.y) * (d.y / v.x)


## Screen px (x right, y up) of a point of her body as rendered (leaned and snapped).
func screen_rendered(wp: Vector3) -> Vector2:
	return _screen(_rendered(wp, view_numbers), view_numbers)


func _head_global() -> Transform3D:
	if skel != null and head_bone >= 0:
		return skel.global_transform * skel.get_bone_global_pose(head_bone)
	return model.global_transform


func _stamp(name: String) -> Dictionary:
	var st: Dictionary = face_meta.get("stamps", {})
	return st.get(name, {})


## Facing of a surface normal toward the camera, horizontally: 1 straight at us, 0 side on.
static func _facing_of(n: Vector3) -> float:
	var h := Vector2(n.x, n.z)
	if h.length() < 1e-4:
		return 1.0
	return h.normalized().y


func _view_tag(f: float) -> String:
	if f >= FACE_FRONT:
		return "f"
	if f >= FACE_THREE:
		return "t"
	if f >= FACE_SIDE:
		return "s"
	return ""


func _update_face(dt: float) -> void:
	if landmarks.is_empty() or face_meta.is_empty():
		return
	var v := view_numbers
	var hg := _head_global()
	if _expr_hold > 0.0:
		_expr_hold -= dt
		if _expr_hold <= 0.0:
			expression = _base_expression
	var exprs: Dictionary = face_meta.get("expressions", {})
	var ex: Dictionary = exprs.get(expression, exprs.get("neutral", {}))
	# blink: every 2-5.5 s for 0.12 s (not when the eyes are already shut or squeezed)
	_blink_t -= dt
	if _blink_t <= 0.0 and blink_enabled:
		_blink_on = 0.12
		_blink_t = randf_range(2.0, 5.5)
	_blink_on = maxf(0.0, _blink_on - dt)
	_anim_frame_t += dt
	# talking: the mouth moves at ~8 Hz with a little irregularity
	if talking:
		_talk_t -= dt
		if _talk_t <= 0.0:
			_talk_i = (_talk_i + 1 + randi() % 2) % 4
			_talk_t = randf_range(0.08, 0.16)
	var centre_l: Array = landmarks["face"]
	var centre_w: Vector3 = hg * (centre_l[0] as Vector3)
	var cs := _screen(_rendered(centre_w, v), v)
	var c_px := cs.floor()
	var face_n := (hg.basis * (centre_l[1] as Vector3)).normalized()
	var face_f := _facing_of(face_n)
	var feats: Array = []
	var norms: Array = []
	var eye_name: String
	var e = ex.get("eyes", "open")
	if e is Array:
		eye_name = e[int(_anim_frame_t * 6.0) % e.size()]
	else:
		eye_name = e
	if _blink_on > 0.0 and eye_name in ["open", "grin", "wide", "sad", "angry", "smug", "teary"]:
		eye_name = "blink"
	var mouth_name: String = ex.get("mouth", "neutral")
	if talking:
		var talk: Array = face_meta.get("talk", ["neutral"])
		mouth_name = talk[_talk_i % talk.size()]
	# pairs stay level: where both eyes (brows, cheeks) show, both take the mean of their projected
	# heights (projected as they are, the far eye of a three-quarter face sat 2-3 px higher: the camera
	# looks down); where only one shows (profile) it keeps its own projection
	var eye_y := _pair_y("eye", hg, v)
	var brow_y := _pair_y("brow", hg, v)
	var cheek_y := _pair_y("cheek", hg, v)
	for side in ["R", "L"]:
		_feature(feats, norms, "eye_" + side, "eye_%s_%s" % [side, eye_name], hg, v, cs, c_px, 0.12, false,
				false, false, eye_y)
		# brows: one name for both, or {"R": name, "L": name} (one brow cocked)
		var brows = ex.get("brows", "")
		if brows is Dictionary:
			brows = brows.get(side, "")
		if brows is String and brows != "":
			_feature(feats, norms, "brow_" + side, "brow_%s_%s" % [side, brows], hg, v, cs, c_px, 0.1, true,
					false, false, brow_y)
		if ex.get("blush", false):
			_feature(feats, norms, "cheek_" + side, "cheek_%s_blush" % side, hg, v, cs, c_px, 0.2, false,
					false, false, cheek_y)
	# the mouth: chosen by the face's own facing; the narrowed variants lose columns on the screen's
	# left (the far side when she turns to her left, +x); mirrored when she turns to her right
	if _view_tag(face_f) != "":
		_feature(feats, norms, "mouth", "mouth_%s" % mouth_name, hg, v, cs, c_px, 0.1, false, face_n.x < -0.05)
	var mark: String = ex.get("mark", "")
	if mark != "":
		_feature(feats, norms, mark if mark == "sweat" else "mark", "mark_" + mark, hg, v, cs, c_px, -1.0, true, false, true)
	mat.set_shader_parameter("c3_feat_count", feats.size())
	mat.set_shader_parameter("c3_feat", feats)
	mat.set_shader_parameter("c3_feat_n", norms)


## The mean projected screen height of a left-right pair of landmarks when both face the camera
## enough to be drawn, else NAN (each keeps its own).
func _pair_y(base: String, hg: Transform3D, v: Vector4) -> float:
	var ys: Array[float] = []
	for side in ["R", "L"]:
		var lm := "%s_%s" % [base, side]
		if not landmarks.has(lm):
			return NAN
		var l: Array = landmarks[lm]
		var n := (hg.basis * (l[1] as Vector3)).normalized()
		if _view_tag(_facing_of(n)) == "":
			return NAN
		ys.append(_screen(_rendered(hg * (l[0] as Vector3), v), v).y)
	return (ys[0] + ys[1]) * 0.5


## Adds one stamp: the landmark's screen pixel relative to the face's centre (rounded, so the
## features stay rigid in pixels while the head turns), the view variant from the landmark's own
## facing, and its normal for the shader's side test.
func _feature(feats: Array, norms: Array, lm: String, stamp_base: String, hg: Transform3D, v: Vector4,
		cs: Vector2, c_px: Vector2, min_dot: float, over_hair: bool, mirror := false, no_view := false,
		y_level := NAN) -> void:
	if not landmarks.has(lm):
		return
	var l: Array = landmarks[lm]
	var wp: Vector3 = hg * (l[0] as Vector3)
	var n := (hg.basis * (l[1] as Vector3)).normalized()
	var tag := "f" if no_view else _view_tag(_facing_of(n))
	if tag == "":
		return
	var name := stamp_base if no_view else "%s_%s" % [stamp_base, tag]
	var st := _stamp(name)
	if st.is_empty() and not no_view:
		st = _stamp("%s_f" % stamp_base)
	if st.is_empty():
		return
	var s := _screen(_rendered(wp, v), v)
	if not is_nan(y_level):
		s.y = y_level
	var px := c_px + (s - cs).round()
	var piv: Array = st["pivot"]
	var size: Array = st["size"]
	var cell := 8
	var bl_x := int(px.x) - (int(size[0]) - 1 - int(piv[0]) if mirror else int(piv[0]))
	var bl_y := int(px.y) - (cell - 1 - int(piv[1]))
	var flags := 2 | (1 if mirror else 0) | (4 if over_hair else 0)
	if mirror:
		# the shader mirrors within the 8-wide cell: shift so the stamp's own columns land right
		bl_x -= cell - int(size[0])
	feats.append(Vector4i(bl_x, bl_y, int(st["cell"]), flags))
	norms.append(Vector4(n.x, n.y, n.z, min_dot))
