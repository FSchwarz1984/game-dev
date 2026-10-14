extends TestCase
## The treetop vista (godot/vista): its timeline on the director's clock keeps the JS segment 1's
## beats, order and timing; the lights leave as in 8196ebf (two lone lights first, then every lamp of
## the plain on its own curve into the gate); everything is deterministic; and every logical size the
## stage can make is covered (no empty canvas, the gate and her branch in view).

const DT := 1.0 / 30.0


func _vista() -> Vista:
	var v := Vista.new()
	v.autoplay = false
	v.quality = "high"
	(Engine.get_main_loop() as SceneTree).root.add_child(v)
	return v


## Runs the whole prologue; returns what happened along the way.
func _run_prologue(v: Vista) -> Dictionary:
	var d := Director.new()
	var out := {"beats": [], "at": {}, "shot_at": {}, "max_air": 0, "arrived": 0, "tdep": PackedFloat32Array(), "end": 0.0}
	v.beat.connect(func(n: String) -> void:
		out["beats"].append(n)
		out["at"][n] = d.t
		out["shot_at"][n] = v.shot)
	d.scene(func(dd: Director) -> void: await v.play_prologue(dd))
	var south: VistaSouth = null
	for i in 3000:
		if not d.busy:
			break
		d.tick(DT)
		v.advance(DT)
		if south == null and v.shots.has("south"):
			south = v.shots["south"]
		if south != null:
			out["max_air"] = maxi(out["max_air"], south.lights.in_flight)
	out["end"] = d.t
	if south != null:
		out["tdep"] = south.lights.tdep.duplicate()
		for i in south.lights.n:
			out["arrived"] += south.lights.arrived[i]
	return out


func test_the_prologue_keeps_the_js_beats_order_and_timing() -> void:
	var v := _vista()
	var r := _run_prologue(v)
	var expect := ["begin", "crane_up", "pause_plain", "first_light", "pause_first_light", "lights_leave", "sky_opens",
		"pause_sky_shore", "tower", "tower_dark", "back_to_plain", "far_spreads", "pose_stand", "pose_shout", "pause_far", "far_arrives", "end"]
	eq(r["beats"], expect, "beats in the JS order")
	# JS seg1 rise(): 7 + 5.7 + 6 + 1.5 + 16 + 10 + 4.5 + 2 + 1.8 + 5.5 + 0.4 + 2.6 + 2.6 = 65.6 s;
	# every wait ends on a frame, as in the JS, so up to a frame late per beat (13 beats at 30 fps)
	near(float(r["end"]), 65.6, 0.5, "total length")
	near(float(r["at"]["lights_leave"]), 20.2, 0.2, "the lights leave after the first one")
	near(float(r["at"]["tower"]), 50.7, 0.4, "the tower insert")
	eq(r["shot_at"]["tower"], "tower", "the insert shows the tower")
	eq(r["shot_at"]["far_spreads"], "south", "back on the plain for the far")
	eq(v.state["rise"], 1.0, "every light has left")
	eq(v.state["sky"], 1.0, "the sky is open")
	eq(v.state["wave"], 1.0, "the far has arrived")
	eq(v.state["pose"], "shout")
	v.queue_free()


func test_the_lights_leave_like_8196ebf_two_alone_then_all_into_the_gate() -> void:
	var v := _vista()
	var r := _run_prologue(v)
	var south: VistaSouth = v.shots["south"]
	var lt := south.lights
	eq([int(lt.L[lt.order[0]][3]) & 4, int(lt.L[lt.order[1]][3]) & 4], [4, 4], "the first two to leave are the lone lights")
	check(lt.tdep[lt.order[0]] < lt.tdep[lt.order[1]] and lt.tdep[lt.order[1]] < lt.tdep[lt.order[2]], "they left in that order")
	check(lt.tdep[lt.order[1]] - lt.tdep[lt.order[0]] > 5.0, "the second one well after the first (%.1f s)" % (lt.tdep[lt.order[1]] - lt.tdep[lt.order[0]]))
	var n := south.lights.n
	check(n > 500, "the whole plain's lamps rise (%d)" % n)
	check(int(r["max_air"]) >= 100, "many in the air at once (%d), not a queue of a few" % int(r["max_air"]))
	check(int(r["arrived"]) >= n - 40, "nearly all reached the gate by the end (%d of %d)" % [int(r["arrived"]), n])
	# 8196ebf's departure order: the headman's lamp at rise 0.03, the bonfire light at 0.11, the rest
	# from 0.17 on (places nearer the town sooner)
	var first: Array = south.lights.L[south.lights.order[0]]
	var second: Array = south.lights.L[south.lights.order[1]]
	near(float(first[6]), 0.03, 1e-6, "first lone light's turn")
	near(float(second[6]), 0.11, 1e-6, "second lone light's turn")
	check(float(south.lights.L[south.lights.order[2]][6]) >= 0.17, "the rest start at rise 0.17")
	v.queue_free()


func test_the_vista_is_deterministic() -> void:
	var a := _vista()
	var ra := _run_prologue(a)
	a.queue_free()
	var b := _vista()
	var rb := _run_prologue(b)
	b.queue_free()
	eq(ra["tdep"], rb["tdep"], "the same departure times on a second run")


func test_every_logical_size_is_covered_and_keeps_its_landmarks() -> void:
	var v := _vista()
	v.show_shot("south")
	var south: VistaSouth = v.shots["south"]
	var m := south.m
	for size in [Vector2i(480, 270), Vector2i(600, 270), Vector2i(640, 360), Vector2i(683, 384), Vector2i(512, 288), Vector2i(800, 360), Vector2i(1024, 560)]:
		south.layout(size)
		for pan in [0.0, 1.0]:
			v.state = {"tod": 20.3, "pan": pan, "rise": 0.0, "sky": 1.0, "wave": -1.0, "pose": "sit"}
			south.update(v.state, 1.0)
			# the far group's canvas covers the whole view
			var far := Rect2(south.far.position, Vector2(float(m["Wc"]), float(m["GH"])))
			check(far.encloses(Rect2(Vector2.ZERO, Vector2(size))), "far canvas covers %s at pan %s" % [size, pan])
			# the canopy covers the bottom of the view across its width
			var can := Rect2(south.canopy.position, Vector2(float(m["Wc"]), float(m["CHc"])))
			check(can.position.x <= 0.0 and can.end.x >= size.x and can.end.y >= size.y, "canopy reaches the edges at %s" % size)
		var gate := south.gate() + south.far.position
		check(gate.y > 8.0 and gate.y < size.y * 0.5 and gate.x > 0.0 and gate.x < size.x, "the gate is in view at %s (%s)" % [size, gate])
		var br: Vector2 = south.anchors["branch"]
		check(br.y > size.y * 0.5 and br.y < size.y and br.x > 0.0 and br.x < size.x, "her branch is in view at %s" % size)
		check(int(south.cls["yh"]) <= South_yh(size.y), "the sky shore class fits the horizon at %s" % size)
	v.queue_free()


static func South_yh(h: int) -> int:
	return VistaSouth.yh_of(h)
