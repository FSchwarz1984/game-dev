extends TestCase
## Port of tests/field-logic.test.js (the field part), with the JS body: the "legacy" profile.

const DT := 1.0 / 30.0


static func make(opts: Dictionary = {}) -> Field:
	var o := {"profile": TestCase.profile("legacy")}
	o.merge(opts, true)
	return Field.new(o)


static func facing(f: Field, e: FieldEntity) -> void:
	var d := Vector2(e.x - f.player.x, e.z - f.player.z)
	var n := d.normalized()
	f.player.fx = n.x
	f.player.fz = n.y


static func settle(f: Field) -> void:
	for i in 10:
		f.update(DT)


static func has_event(evs: Array, type: String, e = null) -> bool:
	for ev in evs:
		if ev.get("type", "") == type and (e == null or ev.get("e") == e):
			return true
	return false


func test_taking_a_quality_pushes_a_thing_away_giving_it_back_brings_it_near() -> void:
	var f := make()
	f.allow("w")
	var beam := f.add({"id": "beam", "name": "梁", "x": 1, "z": 0, "q": {"w": 3}})
	var frame := f.add({"id": "frame", "name": "旧背負子", "x": -1, "z": 0, "q": {"w": 0}, "base": {"w": 3}})
	eq(beam.farness(), 0.0)
	eq(frame.farness(), 1.0)
	facing(f, beam)
	settle(f)
	check(f.target == beam, "beam targeted")
	for i in 3:
		eq(f.transfer("take", "w")["type"], "transfer")
	eq(beam.holder.q["w"], 0)
	eq(beam.far, 1.0)
	eq(f.player.holder.q["w"], 5)
	check(has_event(f.drain(), "far", beam), "far event")
	facing(f, frame)
	settle(f)
	check(f.target == frame, "frame targeted")
	f.transfer("give", "w")
	near(frame.far, 2.0 / 3.0, 1e-9, "each unit brings back a third")
	f.transfer("give", "w")
	f.transfer("give", "w")
	eq(frame.far, 0.0)
	check(has_event(f.drain(), "near", frame), "near event")
	eq(f.player.holder.q["w"], 2)


func test_a_deep_far_thing_cannot_be_touched_or_reached() -> void:
	var f := make()
	f.allow("w")
	var hut := f.add({"id": "hut", "name": "小屋", "x": 3, "z": 0, "r": 1.5, "deep": true})
	f.player.fx = 1
	f.player.fz = 0
	var closest := 1e9
	for i in 90:
		f.update(DT, {"mx": 1, "mz": 0})
		closest = minf(closest, Vector2(f.player.x - 3, f.player.z).length())
	check(closest >= 1.5 + 0.5, "she stays a step away (closest %.2f m)" % closest)
	f.player.x = 0
	f.player.z = 0
	f.player.fx = 1
	f.player.fz = 0
	for i in 5:
		f.update(DT)
	check(f.target == hut, "hut targeted")
	var e := f.transfer("give", "w")
	eq(e["type"], "refused")
	eq(e["reason"], "far")
	eq(hut.far, 1.0)


func test_verbs_she_has_not_learned_do_nothing_and_nothing_changes_hands() -> void:
	var f := make()
	var rock := f.add({"id": "rock", "x": 1, "z": 0, "q": {"w": 2}})
	f.player.fx = 1
	f.player.fz = 0
	settle(f)
	eq(f.transfer("take", "w"), {})
	eq(rock.holder.q["w"], 2)
	f.allow("w", ["take"])
	eq(f.transfer("give", "w"), {})
	eq(f.transfer("take", "w")["type"], "transfer")


func test_a_blocking_zone_turns_her_back_once_per_approach_and_says_why() -> void:
	var f := make()
	f.zone({"id": "east", "x0": 5, "x1": 20, "z0": -10, "z1": 10, "block": "还没背上背负子。"})
	for i in 120:
		f.update(DT, {"mx": 1, "mz": 0})
	check(f.player.x < 5, "stopped before the zone")
	var ev := f.drain().filter(func(e): return e["type"] == "blocked")
	eq(ev.size(), 1)
	if ev.size() > 0:
		eq(ev[0]["say"], "还没背上背负子。")


func test_the_shrine_puts_her_body_back_and_the_books_stay_balanced() -> void:
	var f := make()
	f.allow("w")
	f.add({"id": "rock", "x": 1, "z": 0, "q": {"w": 3}})
	f.player.fx = 1
	f.player.fz = 0
	settle(f)
	var before := Qualities.ALL.map(func(k): return f.L.total(k))
	f.transfer("take", "w")
	f.transfer("take", "w")
	f.restore_body()
	eq(f.player.holder.q["w"], 2)
	eq(Qualities.ALL.map(func(k): return f.L.total(k)), before)


func test_the_context_key_runs_the_targets_action_only_when_it_offers_one() -> void:
	var f := make()
	var hung := {"n": 0}
	var label := func() -> String: return "" if hung["n"] > 0 else "挂灯笼"
	var run := func() -> String:
		hung["n"] += 1
		return "挂上了"
	f.add({"id": "grave", "x": 1, "z": 0, "ctx": {"label": label, "run": run}})
	f.player.fx = 1
	f.player.fz = 0
	settle(f)
	eq(f.context_label(), "挂灯笼")
	eq(f.context(), "挂上了")
	eq(f.context_label(), "")
	eq(f.context(), "")
	eq(hung["n"], 1)


func test_standing_still_she_still_chooses_the_thing_beside_her_even_if_a_scene_turned_her_away() -> void:
	var f := make()
	var beam := f.add({"id": "beam", "x": 0, "z": -1.6, "r": 0.7, "q": {"w": 3}})
	f.player.fx = 1
	f.player.fz = 0
	for i in 10:
		f.update(DT)
	check(f.target == beam, "beam beside her")
	# walking east, the cone narrows again and the beam behind her shoulder drops out
	for i in 10:
		f.update(DT, {"mx": 1, "mz": 0})
	check(f.target != beam, "beam dropped while walking away")


func test_pushing_into_a_slanted_wall_she_slides_along_it_instead_of_sticking() -> void:
	# ground below the line z = x is walkable; above it is a wall (a diagonal bank)
	var g := func(x: float, z: float, _fx: float, _fz: float) -> int:
		return Field.Ground.GROUND if z > x else Field.Ground.WALL
	var f := make({"ground": g})
	f.player.x = 0
	f.player.z = 1
	for i in 60:
		f.update(DT, {"mx": 1, "mz": 0})
	check(f.player.x > 1, "she moved along the bank (x=%.2f)" % f.player.x)
	check(f.player.z > f.player.x, "and never through it")


func test_a_single_blocked_cell_at_a_corner_does_not_pin_her_she_steps_round_it() -> void:
	var g := func(x: float, z: float, _fx: float, _fz: float) -> int:
		return Field.Ground.WALL if (x >= 0.25 and x < 0.5 and z >= 0.0 and z < 0.25) else Field.Ground.GROUND
	var f := make({"ground": g})
	f.player.x = 0.24
	f.player.z = 0.14
	var d := Vector2(cos(0.4), sin(0.4))
	for i in 30:
		f.update(DT, {"mx": d.x, "mz": d.y})
	check(f.player.x > 0.6, "she got past the corner (x=%.2f)" % f.player.x)
