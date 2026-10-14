extends TestCase
## Port of the director test in tests/field-logic.test.js, plus the scene-end hand-back of actors.


class FakeActor:
	var x := 0.0
	var z := 0.0
	var face := "front"
	var idled := false
	var ended := 0
	var played: Array = []

	func play(anim: String, _opts: Dictionary = {}) -> float:
		played.append(anim)
		return 0.5 if anim == "bow" else 0.0

	func idle() -> void:
		idled = true

	func end_scene() -> void:
		ended += 1


class FakeStage:
	var actors := {}

	func actor(id: String) -> Object:
		return actors.get(id)


class FakeUI:
	signal closed
	var lines: Array = []

	func say(l: Array) -> void:
		lines.append_array(l)
		await closed


func test_the_director_waits_on_the_game_clock_and_walks_actors_along_a_path() -> void:
	var stage := FakeStage.new()
	var a := FakeActor.new()
	stage.actors["a"] = a
	var D := Director.new(stage)
	var log: Array = []
	var k := {"v": 0.0}
	D.scene(func(d: Director) -> void:
		await d.wait(0.5)
		log.append("waited")
		await d.move("a", [[2, 0], [2, -2]], {"speed": 2})
		log.append("arrived")
		await d.tween(1.0, func(v: float) -> void: k["v"] = v)
		log.append("tweened"))
	for i in 200:
		if not D.busy:
			break
		D.tick(0.05)
	eq(log, ["waited", "arrived", "tweened"])
	eq(k["v"], 1.0, "tween reached 1")
	eq(a.x, 2.0)
	eq(a.z, -2.0)
	eq(a.face, "back")
	check(a.idled, "idle() after the walk")
	eq(Proj.face_of_move(-1, 0.2), "left")


func test_nothing_runs_before_its_frame() -> void:
	var D := Director.new()
	var log: Array = []
	D.scene(func(d: Director) -> void:
		await d.wait(0.1)
		log.append("a")
		await d.wait(0.1)
		log.append("b"))
	eq(log, [], "nothing yet")
	D.tick(0.05)
	eq(log, [], "still waiting at 0.05 s")
	D.tick(0.06)
	eq(log, ["a"], "first wait done at 0.11 s, the second only starts now")
	D.tick(0.05)
	eq(log, ["a"], "second wait needs its own 0.1 s")
	D.tick(0.06)
	eq(log, ["a", "b"])
	check(not D.busy, "scene ended")


func test_actors_a_scene_used_are_handed_back_when_the_scene_ends() -> void:
	var stage := FakeStage.new()
	var a := FakeActor.new()
	stage.actors["tsuzumi"] = a
	var D := Director.new(stage)
	D.scene(func(d: Director) -> void:
		await d.play("tsuzumi", "bow"))
	eq(a.played, ["bow"])
	eq(a.ended, 0, "not before the scene ends")
	for i in 20:
		D.tick(0.05)
	check(not D.busy, "scene over")
	eq(a.ended, 1, "end_scene called once")


func test_say_waits_for_the_dialogue_to_close() -> void:
	var ui := FakeUI.new()
	var D := Director.new(null, ui)
	var log: Array = []
	D.scene(func(d: Director) -> void:
		await d.say([{"who": "saji", "text": "一"}, {"who": "tsuzumi", "text": "二"}])
		log.append("closed"))
	eq(ui.lines.size(), 2)
	D.tick(1.0)
	eq(log, [], "a line waits for the player")
	ui.closed.emit()
	eq(log, ["closed"])


func test_reset_drops_pending_waits() -> void:
	var D := Director.new()
	var log: Array = []
	D.scene(func(d: Director) -> void:
		await d.wait(1.0)
		log.append("never"))
	D.reset()
	for i in 40:
		D.tick(0.1)
	eq(log, [])
	check(not D.busy, "not busy after reset")
