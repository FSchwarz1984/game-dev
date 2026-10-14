extends TestCase
## Port of tests/crew.test.js.


static func run(crew: Crew, seconds: float, leader = null) -> void:
	var dt := 1.0 / 60.0
	var t := 0.0
	while t < seconds:
		if leader != null:
			leader["x"] += leader["vx"] * dt
			leader["z"] += leader["vz"] * dt
			crew.lead(leader["x"], leader["z"])
		crew.update(dt)
		t += dt


func test_followers_walk_in_a_line_along_her_path_not_in_a_clump() -> void:
	var crew := Crew.new()
	for i in 4:
		crew.add(0, 0)
	var her := {"x": 0.0, "z": 0.0, "vx": 2.0, "vz": 0.0}
	run(crew, 3, her)
	her["vx"] = 0.0
	her["vz"] = 2.0  # she turns a corner
	run(crew, 2, her)
	var m := crew.members
	for i in range(1, m.size()):
		var gap := Vector2(m[i]["x"] - m[i - 1]["x"], m[i]["z"] - m[i - 1]["z"]).length()
		check(gap > 0.6 and gap < 1.3, "gap %.2f between follower %d and %d" % [gap, i - 1, i])
	# the last follower is still on the first leg of the path (x axis): the line traces the corner
	check(absf(m[3]["z"]) < 0.6 or m[3]["x"] > 5, "the line traces the path around the corner")


func test_a_heavy_item_waits_for_enough_hands_and_taking_its_weight_needs_fewer() -> void:
	eq(Crew.carriers_needed(3), 3)
	eq(Crew.carriers_needed(0), 1)
	var crew := Crew.new()
	crew.add(0, 0)
	crew.add(0, 0)
	var log := {"x": 4.0, "z": 0.0, "weight": 3, "ref": "log"}
	var yard := {"x": 0.0, "z": 4.0, "ref": "yard", "count": 0}
	var job := crew.dispatch(log, yard)
	eq(crew.shortfall(job), 1)
	run(crew, 4)
	eq(job["state"], "gather", "two carriers cannot lift a weight-3 log")
	log["weight"] = 2  # she took one unit of its weight
	run(crew, 8)
	eq(job["delivered"], true)
	eq(yard["count"], 1)
	check(Vector2(log["x"] - yard["x"], log["z"] - yard["z"]).length() < 0.5, "delivered to the yard")
	check(crew.members.all(func(mm): return mm["state"] == "follow"), "everyone back in line")


func test_dispatching_again_sends_more_helpers_to_an_item_that_is_short_of_hands() -> void:
	var crew := Crew.new()
	var a := crew.add(0, 0)
	var rock := {"x": 3.0, "z": 0.0, "weight": 2, "ref": "rock"}
	var job := crew.dispatch(rock, {"x": 0.0, "z": 3.0, "ref": "yard"})
	eq(crew.shortfall(job), 1)
	var b := crew.add(0, 0)
	crew.dispatch(rock, job["dest"])
	eq(crew.shortfall(job), 0)
	check(job["carriers"].has(a) and job["carriers"].has(b), "both carry")


func test_recall_drops_the_load_where_it_is_and_everyone_rejoins_the_line() -> void:
	var crew := Crew.new()
	crew.add(0, 0)
	var box := {"x": 3.0, "z": 0.0, "weight": 1, "ref": "box"}
	crew.dispatch(box, {"x": -6.0, "z": 0.0, "ref": "yard"})
	run(crew, 2.5)
	crew.recall()
	var where := Vector2(box["x"], box["z"])
	run(crew, 1)
	eq(Vector2(box["x"], box["z"]), where)
	eq(crew.members[0]["state"], "follow")
