extends TestCase
## Her body as data-driven states (draft profile, PENDING approval): capacity 1, the given-away
## share returns from the air after 9 s with the books balanced, effects per level, plan() for the
## one-key scheme.

const DT := 1.0 / 30.0


static func draft_field() -> Field:
	var f := Field.new({"profile": TestCase.profile("draft")})
	for k in Qualities.ALL:
		f.allow(k, ["take", "give", "release"])
	return f


static func face_east(f: Field) -> void:
	f.player.fx = 1
	f.player.fz = 0
	for i in 5:
		f.update(DT)


func totals(f: Field) -> Array:
	return Qualities.ALL.map(func(k): return f.L.total(k))


func test_draft_body_is_natural_one_of_each_with_capacity_one() -> void:
	var f := draft_field()
	eq(f.player.holder.q, {"w": 1, "h": 1, "l": 1, "s": 1, "v": 1})
	eq(f.player.cap, 1)
	near(f.player.body.speed(), 3.4)


func test_one_body_form_at_a_time() -> void:
	var f := draft_field()
	f.add({"id": "rock", "x": 1, "z": 0, "q": {"w": 3, "h": 2}})
	face_east(f)
	eq(f.transfer("take", "w")["type"], "transfer")
	eq(f.player.body.levels["w"], 2, "extra weight")
	near(f.player.body.speed(), 3.4 * 0.7, 1e-6, "heavy walks at 0.7")
	eq(f.player.body.fx.get("wind_mul"), 0.0, "the wind cannot move her")
	eq(f.transfer("take", "h")["reason"], Qualities.OVERLOAD, "capacity 1: no second form")
	eq(f.transfer("take", "w")["reason"], Qualities.OVERLOAD, "nor a second unit")


func test_her_given_share_returns_from_the_air_and_the_books_stay_balanced() -> void:
	var f := draft_field()
	var frame := f.add({"id": "frame", "x": 1, "z": 0, "q": {"w": 0}, "base": {"w": 2}})
	face_east(f)
	var before := totals(f)
	eq(f.transfer("give", "w")["type"], "transfer", "gives her own weight")
	eq(f.player.holder.q["w"], 0)
	check(f.player.body.flag("floats"), "light: she floats")
	near(f.player.body.fx.get("hover_m", 0.0), 0.3, 1e-6, "hovers 0.3 m")
	var t := 0.0
	var returned_at := -1.0
	var half := 0.0
	while t < 12.0:
		f.update(DT)
		t += DT
		if absf(t - 4.5) < DT * 0.5:
			half = f.player.body.progress["w"]
		if returned_at < 0.0 and f.player.holder.q["w"] == 1:
			returned_at = t
	check(returned_at > 8.9 and returned_at < 9.2, "returned after 9 s (at %.2f)" % returned_at)
	near(half, 0.5, 0.05, "progress shows the return half way")
	eq(frame.holder.q["w"], 1, "the frame keeps what she gave")
	eq(totals(f), before, "totals conserved (the air lent her the unit)")
	eq(f.L.air["w"], -1, "the air's balance records the loan")


func test_extra_never_leaves_by_itself() -> void:
	var f := draft_field()
	f.add({"id": "rock", "x": 1, "z": 0, "q": {"w": 3}})
	face_east(f)
	f.transfer("take", "w")
	for i in 30 * 20:
		f.update(DT)
	eq(f.player.holder.q["w"], 2, "still carrying the extra after 20 s")


func test_extra_heat_sets_the_hat_alight_and_water_puts_it_out() -> void:
	var f := draft_field()
	f.add({"id": "fire", "x": 1, "z": 0, "q": {"h": 3}})
	face_east(f)
	f.transfer("take", "h")
	var lit_at := -1.0
	var t := 0.0
	while t < 5.0 and lit_at < 0.0:
		f.update(DT)
		t += DT
		for e in f.drain():
			if e["type"] == "ignite":
				lit_at = t
	check(lit_at > 3.4 and lit_at < 3.7, "ignites after 3.5 s (at %.2f)" % lit_at)
	check(f.player.body.burning, "burning")
	var n0 := f.player.body.integrity
	for i in 40:
		f.update(DT)
	check(f.player.body.integrity < n0, "the hat loses notches while burning")
	f.player.on = Field.Ground.WATER
	f.player.body.tick(DT, f.player.holder, f.L, {"in_water": true})
	check(not f.player.body.burning, "water puts it out")


func test_effects_of_two_forms_combine_by_their_rules() -> void:
	var prof := TestCase.profile("draft")
	var parts := [BodyRules.effects_at(prof, "w", 2), BodyRules.effects_at(prof, "h", 0)]
	var fx := BodyRules.merge_effects(parts)
	near(float(fx["speed_mul"]), 0.7)
	eq(fx["freezes_water"], true)
	eq(fx["outline"], "#a8d8ff", "the cold one's frost outline")
	var two := BodyRules.effects_at(prof, "w", 3)
	near(float(two["speed_mul"]), 0.55, 1e-6, "extra twice overrides")
	eq(two["sinks"], true, "and inherits the rest of extra")


func test_one_key_scheme_plans_the_obvious_thing() -> void:
	var f := draft_field()
	var rock := f.add({"id": "rock", "x": 1, "z": 0, "q": {"w": 3}})
	face_east(f)
	var p := f.plan("w")
	eq([p["verb"], p["reason"]], ["take", ""], "natural: the key takes")
	f.act("w")
	eq(f.player.holder.q["w"], 2)
	p = f.plan("w")
	eq([p["verb"], p["reason"]], ["give", ""], "carrying extra: the key gives it back")
	p = f.plan("w", true)
	eq([p["verb"], p["reason"]], ["take", Qualities.OVERLOAD], "alt: take one more, refused at capacity 1")
	f.act("w")
	eq(f.player.holder.q["w"], 1)
	p = f.plan("w", true)
	eq(p["verb"], "give", "alt with nothing extra: give her own share")
	f.act("w", true)
	eq(f.player.holder.q["w"], 0)
	eq(rock.holder.q["w"], 4)
	# with no target the obvious action of carried extra is to release it
	f.target = null
	f.player.holder.q["h"] = 2
	eq(f.plan("h")["verb"], "release")


func test_the_legacy_profile_keeps_the_js_body() -> void:
	var f := Field.new({"profile": TestCase.profile("legacy")})
	eq(f.player.holder.q, {"w": 2, "h": 1, "l": 0, "s": 1, "v": 3})
	eq(f.player.cap, 3)
	f.player.holder.q["w"] = 1
	for i in 30 * 12:
		f.update(DT)
	eq(f.player.holder.q["w"], 1, "no return in the legacy profile")
	near(f.player.body.speed(), 3.4 * 1.2, 1e-6, "light walks at 1.2")


func test_the_return_can_reappear_instead_and_the_books_still_balance() -> void:
	var prof := TestCase.profile("draft").duplicate(true)
	prof["regen_from"] = "source"
	var f := Field.new({"profile": prof})
	f.allow("w")
	f.add({"id": "frame", "x": 1, "z": 0, "q": {"w": 0}, "base": {"w": 2}})
	face_east(f)
	var before := totals(f)
	f.transfer("give", "w")
	for i in 30 * 10:
		f.update(DT)
	eq(f.player.holder.q["w"], 1, "back after 9 s")
	eq(f.L.air["w"], 0, "the air lent nothing")
	eq(f.L.sourced["w"], 1, "the return is booked like a source")
	eq(totals(f), before)


func test_nothing_holds_more_than_two_over_its_natural_amount() -> void:
	var f := draft_field()
	var bowl := f.add({"id": "bowl", "x": 1, "z": 0, "q": {"w": 1}})
	face_east(f)
	# give her own weight, wait for it to return, give again...: the bowl stops at natural + 2
	var gave := 0
	for round in 4:
		var e := f.transfer("give", "w")
		if e.get("type", "") == "transfer":
			gave += 1
		else:
			eq(e.get("reason", ""), Qualities.FULL, "refused as full")
		for i in 30 * 10:
			f.update(DT)
	eq(bowl.holder.q["w"], 3, "1 natural + 2")
	eq(gave, 2)
