extends TestCase
## Port of tests/targeting.test.js.


class Who:
	var x := 0.0
	var z := 0.0
	var fx := 0.0
	var fz := 1.0

	func _init(px := 0.0, pz := 0.0, pfx := 0.0, pfz := 1.0) -> void:
		x = px
		z = pz
		fx = pfx
		fz = pfz


static func c(ref: String, x: float, z: float, extra: Dictionary = {}) -> Dictionary:
	var d := {"ref": ref, "x": x, "z": z}
	d.merge(extra, true)
	return d


func test_things_behind_her_are_ignored_unless_they_are_right_at_her_feet() -> void:
	eq(Targeting.score(Who.new(), c("a", 0, -2)), -INF)
	check(Targeting.score(Who.new(), c("b", 0, -0.5)) > -INF, "at her feet")
	check(Targeting.score(Who.new(), c("c", 0, 2)) > -INF, "in front")


func test_type_priority_wins_over_a_slightly_better_position() -> void:
	var t := Targeting.new()
	var got = t.update(0.016, Who.new(), [c("rock", 0.2, 1.0), c("npc", 0.6, 1.6, {"priority": 1})])
	eq(got["ref"], "npc")


func test_the_target_does_not_flicker_when_two_candidates_are_nearly_tied() -> void:
	var t := Targeting.new()
	var cands := [c("a", -0.3, 1.2), c("b", 0.3, 1.2)]
	var first = t.update(0.016, Who.new(), cands)["ref"]
	for i in 60:
		var wobble := 0.05 if i % 2 else -0.05
		eq(t.update(0.016, Who.new(0, 0, wobble, 1), cands)["ref"], first, "frame %d" % i)


func test_a_clearly_better_challenger_takes_over_after_the_dwell_time() -> void:
	var t := Targeting.new()
	t.update(0.016, Who.new(), [c("far", 0, 2.4)])
	var cands := [c("far", 0, 2.4), c("near", 0, 0.6, {"priority": 1})]
	eq(t.update(0.05, Who.new(), cands)["ref"], "far")
	eq(t.update(0.1, Who.new(), cands)["ref"], "near")


func test_cycling_and_touch_picks_hold_until_the_pick_expires_or_leaves_reach() -> void:
	var t := Targeting.new()
	var cands := [c("a", 0, 1), c("b", 0.4, 1.4)]
	t.update(0.016, Who.new(), cands)
	var next = t.cycle()
	ne(next["ref"], "a")
	for i in 30:
		eq(t.update(0.016, Who.new(), cands)["ref"], next["ref"], "held %d" % i)
	eq(t.update(0.016, Who.new(), [c("a", 0, 1)])["ref"], "a")
