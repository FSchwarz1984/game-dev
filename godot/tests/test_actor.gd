extends TestCase
## The actor's animation state machine: every scripted state ends by itself or by its exit, and
## locomotion always shows what she does now (R-4: sprites that did not switch back).

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
		a.x += 0.1
		a.tick(DT)
	eq(a.anim_name, "walk_side")
	eq(a.face, "right")
	check(not a.sprite.flip_h, "side frames face right")
	for i in 10:
		a.x -= 0.1
		a.tick(DT)
	eq(a.face, "left")
	check(a.sprite.flip_h, "left mirrors the side frames")
	a.idle()
	a.tick(DT)
	eq(a.state_name(), "locomotion")
	eq(a.anim_name, "idle_side")
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
	eq(a.anim_name, "asleep_side", "on the plain sheet, seen from the side")
	a.end_scene()
	a.tick(DT)
	eq(a.state_name(), "locomotion", "the director's scene end releases it")
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
	eq(a.anim_name, "heavyIdle_front", "heavy standing")
	# her verb gesture yields to walking at once
	a.play("take")
	for i in 3:
		f.update(DT, {"mx": 1, "mz": 0})
		a.tick(DT)
	eq(a.state_name(), "locomotion", "walking cancels the gesture")
	eq(a.anim_name, "walk_side")
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
