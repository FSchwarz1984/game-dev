extends TestCase
## The actor's animation state machine: every scripted state ends by itself or by its exit, and
## locomotion always shows what she does now (R-4: sprites that did not switch back). Also the
## sprite directions (eight for locomotion, left and right drawn separately, never mirrored), the
## walk/run choice and playback at her real speed (docs/knowledge/20-sprites.md).

const DT := 1.0 / 30.0


func run(a: Actor, seconds: float) -> void:
	var t := 0.0
	while t < seconds:
		a.tick(DT)
		t += DT


func test_a_one_shot_returns_to_locomotion_by_itself() -> void:
	var a := Actor.new("tsuzumi")
	a.face = "front"
	a.tick(DT)
	eq(a.anim_name, "idle_front")
	var dur := a.play("bow")
	check(dur > 0.5, "bow lasts %.2f s" % dur)
	eq(a.state_name(), "one_shot")
	a.tick(DT)
	eq(a.anim_name, "bow_front", "plays the bow")
	run(a, dur + Actor.HOLD_LAST + 0.1)
	eq(a.state_name(), "locomotion", "back by itself")
	eq(a.anim_name, "idle_front")
	a.free()


func test_a_scripted_walk_ends_with_idle_and_faces_its_way() -> void:
	var a := Actor.new("saji")
	a.play("walk", {"loop": true})
	eq(a.state_name(), "scripted")
	for i in 10:
		a.x += 0.05          # 1.5 m/s: a walk
		a.tick(DT)
	eq(a.anim_name, "walk_right")
	eq(a.face, "right")
	check(not a.sprite.flip_h, "right is drawn facing right")
	for i in 10:
		a.x -= 0.05
		a.tick(DT)
	eq(a.face, "left")
	eq(a.anim_name, "walk_left", "left has its own frames")
	check(not a.sprite.flip_h, "left is drawn, not mirrored (asymmetric design)")
	a.idle()
	a.tick(DT)
	eq(a.state_name(), "locomotion")
	eq(a.anim_name, "idle_left")
	a.free()


func test_left_and_right_are_separate_frames_for_everyone() -> void:
	for id in ["tsuzumi", "saji", "shione"]:
		var a := Actor.new(id)
		var sheet := a._sheet_for("walk")
		var sf := CharacterLibrary.frames(id, sheet)
		for v in Proj.DIR8:
			check(sf.has_animation("walk_" + v), "%s walks %s" % [id, v])
			check(sf.has_animation("idle_" + v), "%s stands %s" % [id, v])
			check(sf.has_animation("run_" + v), "%s runs %s" % [id, v])
		var l := (sf.get_frame_texture("walk_left", 0) as AtlasTexture).region
		var r := (sf.get_frame_texture("walk_right", 0) as AtlasTexture).region
		ne(l, r, "%s: left and right come from different cells" % id)
		check(not bool(CharacterLibrary.anim_meta(id, "walk").get("mirrorLeft", true)), "%s: never mirrored" % id)
		a.free()


func test_every_strip_lies_on_its_sheet_and_no_two_share_a_cell() -> void:
	# the build packs short strips into free row space (knowledge/20 §7): a wrong 'col' would show
	# another animation's frames. Locomotion starts at column 0 (the 3D sample's walker reads only
	# 'row'), and every sheet fits a 4096 texture (phones).
	for id in ["tsuzumi", "saji", "shione"]:
		var fs := CharacterLibrary.frame_size(id)
		for sheet in CharacterLibrary.sheets(id):
			var sd: Dictionary = CharacterLibrary.character(id)["sheets"][sheet]
			var tex := load("res://art/sprites/%s.png" % sd["file"]) as Texture2D
			eq(Vector2i(tex.get_size()), Vector2i(int(sd["width"]), int(sd["height"])), "%s/%s size" % [id, sheet])
			check(int(sd["width"]) <= 4096 and int(sd["height"]) <= 4096, "%s/%s fits 4096" % [id, sheet])
			var seen := {}
			var bad := []
			for anim in sd["anims"]:
				for view in sd["anims"][anim]:
					var e: Dictionary = sd["anims"][anim][view]
					var col := int(e.get("col", 0))
					var row := int(e["row"])
					var n := int(e["frames"])
					if anim in ["idle", "walk", "run"] and col != 0:
						bad.append("%s_%s starts at column %d" % [anim, view, col])
					if (col + n) * fs.x > int(sd["width"]) or (row + 1) * fs.y > int(sd["height"]):
						bad.append("%s_%s runs off the sheet" % [anim, view])
					for i in n:
						var k := "%d,%d" % [col + i, row]
						if seen.has(k):
							bad.append("%s_%s and %s share cell %s" % [anim, view, seen[k], k])
						seen[k] = "%s_%s" % [anim, view]
			check(bad.is_empty(), "%s/%s: %s" % [id, sheet, ", ".join(bad)])


func test_diagonal_motion_shows_the_diagonal_view_with_hysteresis() -> void:
	var a := Actor.new("shione")
	a.play("walk", {"loop": true})
	for i in 8:
		a.x += 0.04
		a.z += 0.04
		a.tick(DT)
	eq(a.anim_name, "walk_front_right", "south-east")
	eq(a.face, "front", "the four-way face for the game logic keeps the vertical on an exact diagonal")
	# a slight wobble toward south keeps the diagonal (hysteresis), a clear turn changes it
	for i in 4:
		a.x += 0.03
		a.z += 0.05
		a.tick(DT)
	eq(a.anim_name, "walk_front_right", "no flicker on a sector edge")
	for i in 6:
		a.z += 0.06
		a.tick(DT)
	eq(a.anim_name, "walk_front", "straight south")
	a.idle()
	a.free()


func test_run_above_the_run_speed_and_playback_follows_speed() -> void:
	var a := Actor.new("saji")
	var walk_v := float(CharacterLibrary.anim_meta("saji", "walk")["speed"])
	var run_from := float(CharacterLibrary.anim_meta("saji", "run")["from"])
	check(walk_v > 0.5 and run_from > walk_v, "walk %.2f m/s, run from %.2f m/s" % [walk_v, run_from])
	a.play("walk", {"loop": true})
	for i in 12:
		a.x += walk_v * DT
		a.tick(DT)
	eq(a.anim_name, "walk_right")
	near(a.sprite.speed_scale, 1.0, 0.05, "the walk plays 1:1 at its own speed")
	for i in 12:
		a.x += (run_from + 0.4) * DT
		a.tick(DT)
	eq(a.anim_name, "run_right", "fast enough to run")
	for i in 12:
		a.x += run_from * 0.9 * DT
		a.tick(DT)
	eq(a.anim_name, "run_right", "hysteresis: still running just below the run speed")
	for i in 12:
		a.x += walk_v * 1.2 * DT
		a.tick(DT)
	eq(a.anim_name, "walk_right", "slowed down: walking again")
	near(a.sprite.speed_scale, 1.2, 0.08, "the walk plays faster when she walks faster")
	a.idle()
	a.free()


func test_a_held_loop_ends_after_its_hold_and_a_pose_at_the_scenes_end() -> void:
	var a := Actor.new("tsuzumi")
	a.play("lookUp", {"loop": true, "hold": 1.0})
	eq(a.state_name(), "hold")
	run(a, 0.5)
	eq(a.anim_name.get_slice("_", 0), "lookUp")
	run(a, 0.6)
	eq(a.state_name(), "locomotion", "the hold ran out")
	a.pose("sleep")
	run(a, 5.0)
	eq(a.state_name(), "pose", "a pose holds")
	eq(a.anim_name, "asleep_right", "on the plain sheet, lying across the view")
	eq(a.sprite.sprite_frames, CharacterLibrary.frames("tsuzumi", "plain"), "from the plain sheet")
	a.end_scene()
	a.tick(DT)
	eq(a.state_name(), "locomotion", "the director's scene end releases it")
	a.free()


func test_the_vista_limb_poses_have_her_animations_from_behind() -> void:
	# the tree-top vista asks for "sit", "stand" and "shout" (vista.gd set_pose) and shows her from
	# behind; each must be a drawn animation, not a fallback to idle (knowledge/20 §6)
	var a := Actor.new("tsuzumi")
	a.face = "back"
	for p in ["sit", "stand", "shout"]:
		a.play(p, {"loop": true})
		a.tick(DT)
		eq(a.state_name(), "pose", "%s holds" % p)
		check(a.anim_name.ends_with("_back"), "%s: %s is seen from behind" % [p, a.anim_name])
		check(not a.anim_name.begins_with("idle"), "%s is drawn (%s)" % [p, a.anim_name])
	a.free()


func test_locomotion_follows_her_body() -> void:
	var f := Field.new({"profile": TestCase.profile("draft")})
	var a := Actor.new("tsuzumi", f.player)
	a.tick(DT)
	for i in 6:
		f.update(DT, {"mx": 0, "mz": 1})
		a.tick(DT)
	eq(a.anim_name, "walk_front", "walking south")
	f.update(DT)
	a.tick(DT)
	eq(a.anim_name, "idle_front", "standing")
	a.heavy = true
	a.tick(DT)
	# no drawn heavy pose (pending body decision): she stands, her body look carries the weight
	eq(a.anim_name, "idle_front", "heavy standing")
	# her verb gesture yields to walking at once
	a.play("take")
	for i in 3:
		f.update(DT, {"mx": 1, "mz": 0})
		a.tick(DT)
	eq(a.state_name(), "locomotion", "walking cancels the gesture")
	eq(a.anim_name, "walk_right")
	a.free()


func test_an_unknown_animation_is_refused_and_changes_nothing() -> void:
	var a := Actor.new("shione")
	a.tick(DT)
	var before := a.anim_name
	eq(a.play("no_such_anim"), 0.0)
	eq(a.state_name(), "locomotion")
	a.tick(DT)
	eq(a.anim_name, before)
	a.free()
