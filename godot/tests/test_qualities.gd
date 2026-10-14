extends TestCase
## Port of tests/qualities.test.js.


static func her() -> QualityHolder:
	return QualityHolder.new({"material": "body", "amounts": {"w": 2, "h": 1, "l": 0, "s": 1, "v": 2}})


func totals(L: Ledger) -> Array:
	return Qualities.ALL.map(func(k): return L.total(k))


func test_a_transfer_moves_one_unit_and_the_books_stay_balanced() -> void:
	var L := Ledger.new()
	var me := L.add(her())
	var rock := L.add(QualityHolder.new({"material": "stone", "amounts": {"w": 3}}))
	var before := totals(L)
	var e := L.take(me, rock, "w", 3)
	eq(e["type"], "transfer")
	eq(rock.q["w"], 2)
	eq(me.q["w"], 3)
	L.give(me, rock, "w", 3)
	L.release(me, "h", 3)
	eq(totals(L), before, "totals")


func test_refusals_name_their_reason_so_the_ui_never_fails_silently() -> void:
	var L := Ledger.new()
	var me := L.add(her())
	var camphor := L.add(QualityHolder.new({"material": "plant", "amounts": {"v": 9}, "sacred": true}))
	var empty := L.add(QualityHolder.new({"material": "stone", "amounts": {"w": 0}}))
	eq(L.take(me, camphor, "v", 3)["reason"], Qualities.SACRED)
	eq(L.give(me, camphor, "v", 3)["reason"], Qualities.SACRED)
	eq(L.take(me, empty, "w", 3)["reason"], Qualities.EMPTY)
	eq(L.release(me, "l", 3)["reason"], Qualities.EMPTY)


func test_her_capacity_is_how_far_she_may_drift_from_her_own_natural_state() -> void:
	var L := Ledger.new()
	var me := L.add(her())
	var rock := L.add(QualityHolder.new({"material": "stone", "amounts": {"w": 9}}))
	var pond := L.add(QualityHolder.new({"material": "water", "amounts": {"h": 1}}))
	eq(L.take(me, rock, "w", 2)["type"], "transfer")
	eq(L.take(me, rock, "w", 2)["type"], "transfer")
	eq(L.take(me, rock, "w", 2)["reason"], Qualities.OVERLOAD)
	# giving away her own heat also counts as drifting
	eq(L.give(me, pond, "h", 2)["reason"], Qualities.OVERLOAD)
	L.give(me, rock, "w", 2)
	eq(L.give(me, pond, "h", 2)["type"], "transfer")
	var f := BodyState.flags_of(me)
	check(f["heavy"] and f["cold"], "heavy and cold")


func test_state_follows_qualities_water_freezes_and_boils_stone_floats() -> void:
	var L := Ledger.new()
	var me := L.add(her())
	var pond := L.add(QualityHolder.new({"material": "water", "amounts": {"h": 1}}))
	var rock := L.add(QualityHolder.new({"material": "stone", "amounts": {"w": 1}}))
	eq(Qualities.state_of(pond)["frozen"], false)
	L.take(me, pond, "h", 4)
	eq(Qualities.state_of(pond)["frozen"], true)
	L.take(me, rock, "w", 4)
	eq(Qualities.state_of(rock)["floats"], true)


func test_a_yokai_calms_when_rebalanced_and_dies_when_its_life_is_taken() -> void:
	var L := Ledger.new()
	var me := L.add(QualityHolder.new({"material": "body", "amounts": {"v": 2}, "max": {"v": 9}}))
	var onibi := L.add(QualityHolder.new({"material": "yokai", "amounts": {"h": 4, "v": 2}, "base": {"h": 1}}))
	eq(Qualities.state_of(onibi)["calm"], false)
	for i in 3:
		L.take(me, onibi, "h", 9)
	eq(Qualities.state_of(onibi)["calm"], true)
	var kappa := L.add(QualityHolder.new({"material": "yokai", "amounts": {"w": 3, "v": 2}, "base": {"w": 1}}))
	L.take(me, kappa, "v", 9)
	L.take(me, kappa, "v", 9)
	eq(Qualities.state_of(kappa)["dead"], true)


func test_sources_refill_only_while_active_and_the_ledger_records_it() -> void:
	var L := Ledger.new()
	var day := {"on": true}
	var sun := L.add(QualityHolder.new({"amounts": {"l": 0}, "source": {"k": "l", "rate": 2, "cap": 3, "active": func() -> bool: return day["on"]}}))
	var before := L.total("l")
	L.tick(1.0)
	eq(sun.q["l"], 2)
	day["on"] = false
	L.tick(5.0)
	eq(sun.q["l"], 2)
	eq(L.total("l"), before)
