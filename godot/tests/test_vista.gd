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


## The art sample's entry (ShowcaseVista): the beats on the vista's own director, her sprite on the
## limb following the poses, and after the white of the far a hold on what the far has left (the
## land its own silver-white ghost, G5R3-22), the sky shore over it, she standing.
func test_the_standalone_play_ends_held_on_the_far_plain() -> void:
	var v := _vista()
	var beats := []
	var at := {}
	var clock := [0.0]
	v.beat.connect(func(n: String) -> void:
		beats.append(n)
		at[n] = clock[0])
	v.play_standalone()   # not awaited: it runs on its own director, ticked by _process as below
	var poses := {}
	var white := 0.0
	var mat := v.view_rect.material as ShaderMaterial
	for i in 4000:
		if beats.has("hold"):
			break
		v._process(DT)    # autoplay is off here: this ticks its director and her pose only
		v.advance(DT)
		clock[0] += DT
		if v._figure != null:
			poses[v._figure.pose] = true
		if beats.has("end"):
			white = maxf(white, float(mat.get_shader_parameter("wash_a")))
	check(beats.has("hold"), "it reaches the hold (%s)" % [beats.slice(-3)])
	eq(beats.slice(0, 2), ["begin", "crane_up"], "it plays the prologue from the start")
	check(beats.find("end") < beats.find("hold"), "the hold comes after the end")
	near(float(at.get("hold", 0.0)) - float(at.get("end", 0.0)), 3.2, 0.2, "a second of white, then 2.2 s back")
	check(white > 0.9, "the far washed the frame white (%.2f)" % white)
	eq(poses.keys().size(), 3, "her sprite sat, stood and shouted (%s)" % [poses.keys()])
	var south: VistaSouth = v.shots["south"]
	check(v._figure != null and v._figure.get_parent() == south.figure, "her sprite is in the figure slot")
	eq(v.shot, "south")
	eq([v.state["sky"], v.state["rise"], v.state["wave"], v.state["settled"], v.state["pose"]], [1.0, 1.0, -1.0, 1.0, "stand"],
		"held on the far plain under the sky shore, the lamps gone, she standing")
	v._process(DT)
	v.advance(DT)
	eq(float(mat.get_shader_parameter("wash_a")), 0.0, "no white left")
	eq(v._figure.pose, "stand")
	eq(float((south.ground.material as ShaderMaterial).get_shader_parameter("settled")), 1.0, "the ground left a ghost (as much as each place is)")
	check(not south.wave_fx.curtain.visible and not south.wave_fx.motes.visible, "no front, no curtain")
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


## The stage's canvas is 640x360-based since 2026-10-15; the vista keeps the canvas of the rule it was
## drawn for (round(h / 270)) and its integer scale in window pixels, centred, covering the window.
func test_the_vista_keeps_its_own_canvas_on_the_640x360_stage() -> void:
	var expect := {Vector2i(1280, 720): [Vector2i(426, 240), 3], Vector2i(1920, 1080): [Vector2i(480, 270), 4],
		Vector2i(2560, 1440): [Vector2i(512, 288), 5], Vector2i(3840, 2160): [Vector2i(480, 270), 8],
		Vector2i(1366, 768): [Vector2i(455, 256), 3], Vector2i(2560, 1080): [Vector2i(640, 270), 4]}
	for win in expect:
		var ss := PixelStage.scale_for(Vector2(win))
		var logical := Vector2i(floori(win.x / float(ss)), floori(win.y / float(ss)))
		var f := Vista.legacy_fit(Vector2(win), logical)
		eq(f["view"], expect[win][0], "the vista's canvas at %s" % win)
		var px := float(f["scale"]) * ss                       # window pixels per vista pixel
		near(px, float(expect[win][1]), 1e-6, "a vista pixel is a whole number of window pixels at %s" % win)
		var o: Vector2 = f["origin"] * ss + ((Vector2(win) - Vector2(logical) * ss) * 0.5).round()
		check(is_equal_approx(o.x, roundf(o.x)) and is_equal_approx(o.y, roundf(o.y)), "it sits on whole window pixels at %s (%s)" % [win, o])
		# with its 1-pixel border it covers the whole window
		var lo := o - Vector2(px, px)
		var hi := o + (Vector2(f["view"]) + Vector2.ONE) * px
		check(lo.x <= 0.0 and lo.y <= 0.0 and hi.x >= win.x and hi.y >= win.y, "it covers the window at %s (%s .. %s)" % [win, lo, hi])


## G5R2-4 (1): the close leaves the camera rises past are twigs of branches that come up from below the
## frame. Every leaf and twig of the near layer hangs together with its bottom row (no piece floats
## free), and on every size that bottom row stays below the view for the whole crane, so no end of a
## branch is ever in view.
func test_the_near_leaves_hang_from_branches_below_the_frame() -> void:
	var v := _vista()
	v.show_shot("south")
	var south: VistaSouth = v.shots["south"]
	var img: Image = south.data.images["near"]
	var w := img.get_width()
	var h := img.get_height()
	var px := img.get_data()                      # RGBA8
	var seen := PackedByteArray()
	seen.resize(w * h)
	var opaque := 0
	for i in w * h:
		if px[i * 4 + 3] > 127:
			opaque += 1
	# flood from every opaque pixel of the bottom row (8-connected), a span at a time
	var stack := PackedInt32Array()
	for x in w:
		var i := (h - 1) * w + x
		if px[i * 4 + 3] > 127:
			stack.append(i)
	var reached := 0
	while not stack.is_empty():
		var i := stack[stack.size() - 1]
		stack.resize(stack.size() - 1)
		if seen[i] != 0:
			continue
		var y := i / w
		var x0 := i % w
		var x1 := x0
		while x0 > 0 and seen[y * w + x0 - 1] == 0 and px[(y * w + x0 - 1) * 4 + 3] > 127:
			x0 -= 1
		while x1 < w - 1 and seen[y * w + x1 + 1] == 0 and px[(y * w + x1 + 1) * 4 + 3] > 127:
			x1 += 1
		for x in range(x0, x1 + 1):
			seen[y * w + x] = 1
			reached += 1
		for yy in [y - 1, y + 1]:
			if yy < 0 or yy >= h:
				continue
			for x in range(maxi(0, x0 - 1), mini(w - 1, x1 + 1) + 1):
				var j: int = yy * w + x
				if seen[j] == 0 and px[j * 4 + 3] > 127:
					stack.append(j)
	check(opaque > 20000, "the near layer has its sprays (%d px)" % opaque)
	eq(reached, opaque, "every near-leaf pixel hangs from a branch that runs out of the layer's bottom")
	for size in [Vector2i(426, 240), Vector2i(480, 270), Vector2i(455, 256), Vector2i(512, 288), Vector2i(480, 300), Vector2i(426, 341), Vector2i(640, 270), Vector2i(1024, 560)]:
		south.layout(size)
		for pan in [0.0, 0.25, 0.5, 0.75]:
			v.state = {"tod": 19.6, "pan": pan, "rise": 0.0, "sky": 0.0, "wave": -1.0, "pose": "sit"}
			south.update(v.state, 1.0)
			check(not south.near.visible or south.near.position.y + float(h) >= float(size.y),
				"the near layer's bottom is below the view at %s, pan %s (%s + %d)" % [size, pan, south.near.position.y, h])
			check(south.near.position.y >= 0.0, "nothing of the near layer reaches above the view at %s" % size)
	v.queue_free()


## G5R2-4 (3): she stands up where she sat. HEAD put her standing 33 px further along the limb with
## nothing to carry her there, so when the far came she jumped right in one frame. Through the whole
## prologue her place on screen changes only as the camera moves (vertically, in the crane), never
## sideways, and not at all when she stands or shouts.
func test_she_stands_up_where_she_sat() -> void:
	var v := _vista()
	v.show_shot("south")
	var south: VistaSouth = v.shots["south"]
	eq(south.m["anchors"]["stand"], south.m["anchors"]["branch"], "the stand anchor is her seat")
	var d := Director.new()
	d.scene(func(dd: Director) -> void: await v.play_prologue(dd))
	var last := Vector2(-1.0e9, -1.0e9)
	var poses := {}
	var max_dx := 0.0
	var jump_at_pose := 0.0
	var last_pose := ""
	for i in 3000:
		if not d.busy:
			break
		d.tick(DT)
		v.advance(DT)
		if v.shot != "south":
			last = Vector2(-1.0e9, -1.0e9)
			continue
		var at := south.figure.position + south.canopy.position
		var pose := String(v.state.get("pose", "sit"))
		poses[pose] = true
		if last.x > -1.0e8:
			max_dx = maxf(max_dx, absf(at.x - last.x))
			if pose != last_pose:
				jump_at_pose = maxf(jump_at_pose, (at - last).length())
		last = at
		last_pose = pose
	eq(poses.keys().size(), 3, "she sat, stood and shouted (%s)" % [poses.keys()])
	eq(max_dx, 0.0, "she never moves sideways on screen")
	eq(jump_at_pose, 0.0, "standing up and shouting leave her where she was")
	v.queue_free()


## G5R2-4 (2): the sky shore's rivers in the bake run from the gate's foot (u = 0, at the top of the
## frame) out to its far ranges (lower on screen, toward the haze). Its gravity pulls away from us, so
## its water runs back toward u = 0, up the screen; shorelights.gdshader moves the glints that way.
func test_the_sky_shore_rivers_run_from_the_gate_out_to_its_far_ranges() -> void:
	var v := _vista()
	v.show_shot("south")
	var south: VistaSouth = v.shots["south"]
	for ci in south.data.lists["shoreSets"].size():
		var by_river := {}
		for p in south.data.lists["shoreSets"][ci]["flow"]:
			var ri := int(p[3])
			if not by_river.has(ri):
				by_river[ri] = []
			by_river[ri].append(p)
		check(by_river.size() >= 3, "class %d draws its three rivers" % ci)
		for ri in by_river:
			var pts: Array = by_river[ri]
			# least squares slope of the screen row against u: positive = the gate end is up
			var n := float(pts.size())
			var su := 0.0
			var sy := 0.0
			var suu := 0.0
			var suy := 0.0
			for p in pts:
				su += float(p[2])
				sy += float(p[1])
				suu += float(p[2]) * float(p[2])
				suy += float(p[2]) * float(p[1])
			var slope := (n * suy - su * sy) / maxf(1e-6, n * suu - su * su)
			check(slope > 0.5, "class %d river %d: its gate end is the top of the frame (%.2f rows per unit)" % [ci, ri, slope])
	var src := FileAccess.get_file_as_string("res://vista/shaders/shorelights.gdshader")
	check(src.contains("sin(pa * 0.9 + t * 1.6 + pb * 2.1)"), "the glints' crests move toward u = 0 (down that land's rivers)")
	v.queue_free()


# ------------------------------------------------------------------ the bridge (G5R3-61, a proposal)

const BEATS_TO_TOWER := ["begin", "crane_up", "pause_plain", "first_light", "pause_first_light", "lights_leave", "sky_opens",
	"pause_sky_shore", "tower", "tower_dark", "back_to_plain"]
const BEATS_FROM_FAR := ["far_spreads", "pose_stand", "pose_shout", "pause_far", "far_arrives", "end"]


## Runs the prologue with a bridge; per frame on the plain after the tower: the gate's breath and
## flash, the drained ground, whether the bridge's layer is drawn, and the beats' times.
func _run_bridge(v: Vista) -> Dictionary:
	var d := Director.new()
	var out := {"beats": [], "at": {}, "frames": [], "keys": false, "end": 0.0}
	v.beat.connect(func(n: String) -> void:
		out["beats"].append(n)
		out["at"][n] = d.t)
	d.scene(func(dd: Director) -> void: await v.play_prologue(dd))
	for i in 3000:
		if not d.busy:
			break
		d.tick(DT)
		v.advance(DT)
		if v.state.has("drain") or v.state.has("flare"):
			out["keys"] = true
		if v.shots.has("south"):
			var south: VistaSouth = v.shots["south"]
			var shore := south.lights.shore.material as ShaderMaterial
			var ground := south.ground.material as ShaderMaterial
			out["frames"].append({"t": d.t, "shot": v.shot, "drawn": south.drain.points.visible,
				"inhale": float(shore.get_shader_parameter("inhale")), "flash": float(shore.get_shader_parameter("flash")),
				"drain_b": float(ground.get_shader_parameter("drain_b")), "el": float(v.state.get("drain", -1.0)),
				"fl": float(v.state.get("flare", -1.0))})
	out["end"] = d.t
	return out


## The prologue as it was ("none", the default) stays the user's: it never starts the bridge (no drain
## or burst clock in its state, the bridge's layer never drawn, the gate never drawing its breath, no
## ground drained ahead of the far) and keeps its beats and length (65.6 s).
func test_the_bridge_none_is_the_prologue_as_it_was() -> void:
	var v := _vista()
	eq(v.bridge, "none", "the default is the prologue as it was")
	var r := _run_bridge(v)
	eq(r["beats"], BEATS_TO_TOWER + BEATS_FROM_FAR, "the beats as before")
	near(float(r["end"]), 65.6, 0.5, "the length as before")
	near(float(r["at"]["far_spreads"]) - float(r["at"]["back_to_plain"]), 0.0, 1e-6, "the far bursts as the plain comes back")
	check(not r["keys"], "no drain or burst clock in the state")
	var drawn := false
	var inhale := 0.0
	var drain_b := -10.0
	for f in r["frames"]:
		drawn = drawn or bool(f["drawn"])
		inhale = maxf(inhale, float(f["inhale"]))
		drain_b = maxf(drain_b, float(f["drain_b"]))
	check(not drawn, "the bridge's layer is never drawn")
	eq(inhale, 0.0, "the gate never draws its breath")
	eq(drain_b, -10.0, "no ground drained ahead of the far")
	v.queue_free()


## "drain": back on the plain the gate draws in its breath and the town's colours go up into it as
## grains of light, then the far bursts from the town. Every grain leaves a pixel of the town (ground
## the far reaches within the drained radius) and its way ends in the gate's mouth; the first come in
## before the burst, the last after it, the gate's breath held in between and its flashes as they come;
## the drained ground grows from the town out to its radius by the burst; it adds DRAIN_PRE seconds.
func test_the_drain_rises_from_the_town_into_the_gate() -> void:
	var v := _vista()
	v.bridge = "drain"
	var r := _run_bridge(v)
	var south: VistaSouth = v.shots["south"]
	var dr := south.drain
	eq(r["beats"], BEATS_TO_TOWER + ["drain", "burst"] + BEATS_FROM_FAR, "the drain and the burst between the plain's return and the far")
	near(float(r["at"]["burst"]) - float(r["at"]["back_to_plain"]), VistaSouthDrain.DRAIN_PRE, 0.05, "the burst after the drain")
	near(float(r["at"]["far_spreads"]), float(r["at"]["burst"]), 1e-6, "the far starts with the burst")
	near(float(r["end"]), 65.6 + VistaSouthDrain.DRAIN_PRE, 0.5, "it adds the drain's length, nothing else")
	check(dr.n_grains >= 120, "a swarm of grains (%d)" % dr.n_grains)
	var gate := south.gate()
	var gimg: Image = south.data.images["ground"]
	var from_town := 0
	var into_gate := 0
	for g in dr.grains:
		var p0: Vector2 = g[0]
		var px := gimg.get_pixelv(Vector2i(p0))
		if px.a > 0.5 and roundi(px.b * 255.0) <= VistaSouthDrain.B_MAX and p0.distance_to(dr.town) < 80.0:
			from_town += 1
		if dr.pos_at(g, 0.0, gate).distance_to(p0) < 0.01 and dr.pos_at(g, 1.0, gate).distance_to(gate + Vector2(0, 1)) < 2.0:
			into_gate += 1
	eq(from_town, dr.grains.size(), "every grain leaves a pixel of the town")
	eq(into_gate, dr.grains.size(), "every grain's way starts on its pixel and ends in the gate's mouth")
	# a loose swarm, not a beam: each rises straight off the ground first; across the way the grains
	# are spread wide in its middle and gather only near the gate's mouth
	var way := (dr.town - gate).normalized()
	var across := Vector2(-way.y, way.x)
	var straight := 0
	var mid := PackedFloat32Array()
	var end := PackedFloat32Array()
	for g in dr.grains:
		var p0: Vector2 = g[0]
		var q := dr.pos_at(g, 0.06, gate)
		if q.y < p0.y - 1.0 and absf(q.x - p0.x) < 0.5 * (p0.y - q.y):
			straight += 1
		mid.append((dr.pos_at(g, 0.5, gate) - gate).dot(across))
		end.append((dr.pos_at(g, 0.97, gate) - gate).dot(across))
	mid.sort()
	end.sort()
	var spread_mid := mid[int(mid.size() * 0.9)] - mid[int(mid.size() * 0.1)]
	var spread_end := end[int(end.size() * 0.9)] - end[int(end.size() * 0.1)]
	eq(straight, dr.grains.size(), "every grain floats straight up off the town first")
	check(spread_mid > 30.0, "the swarm is wide in the middle of the way (%.1f px across, 10-90%%)" % spread_mid)
	check(spread_end < 6.0, "and gathers at the gate's mouth (%.1f px)" % spread_end)
	# ground zero: the far's first pixels are where the town is
	var b0 := Vector2.ZERO
	var nb := 0
	for y in range(int(dr.town.y) - 20, int(dr.town.y) + 20):
		for x in range(int(dr.town.x) - 80, int(dr.town.x) + 80):
			var px := gimg.get_pixel(x, y)
			if px.a > 0.5 and roundi(px.b * 255.0) <= 3:
				b0 += Vector2(x, y)
				nb += 1
	check(nb > 0 and (b0 / nb).distance_to(dr.town) < 6.0, "the stream starts where the far bursts (%s vs %s)" % [b0 / maxf(1, nb), dr.town])
	check(dr.arrivals[0] < VistaSouthDrain.DRAIN_PRE - 0.3, "the first grains reach the gate before the burst (%.2f s)" % dr.arrivals[0])
	check(dr.t_last > VistaSouthDrain.DRAIN_PRE + 0.8, "the last go up after it (%.2f s)" % dr.t_last)
	var held := 1.0
	var flash_in := 0.0
	var drain_b := -10.0
	var drawn_before := false
	var drawn_after := false
	for f in r["frames"]:
		var el := float(f["el"])
		if f["shot"] != "south" or el < 0.0:
			continue
		if el > VistaSouthDrain.INHALE.y + 0.05 and el < dr.t_last:
			held = minf(held, float(f["inhale"]))
		if el > dr.arrivals[0] and el < VistaSouthDrain.DRAIN_PRE:
			flash_in = maxf(flash_in, float(f["flash"]))
		if el <= VistaSouthDrain.DRAIN_PRE:
			drain_b = maxf(drain_b, float(f["drain_b"]))
		if el < VistaSouthDrain.INHALE.x - 0.05 and bool(f["drawn"]):
			drawn_before = true
		if el > dr.t_last + 0.2 and float(f["fl"]) > 3.0 and bool(f["drawn"]):
			drawn_after = true
	check(held > 0.95, "the gate holds its breath while the grains come (%.2f)" % held)
	check(flash_in > 0.3, "the gate flashes as they come in (%.2f)" % flash_in)
	near(drain_b, float(VistaSouthDrain.B_MAX), 0.5, "the drained ground reaches its radius by the burst")
	check(not drawn_before and not drawn_after, "the stream is drawn only while it runs")
	eq(float((south.lights.shore.material as ShaderMaterial).get_shader_parameter("inhale")), 0.0, "and the gate breathes out")
	v.queue_free()


## "flash": a beat on the plain, then the gate flares in the frame the town bursts; it adds FLASH_PRE.
func test_the_flash_bridge_flares_the_gate_as_the_town_bursts() -> void:
	var v := _vista()
	v.bridge = "flash"
	var r := _run_bridge(v)
	eq(r["beats"], BEATS_TO_TOWER + ["gate_flash", "burst"] + BEATS_FROM_FAR, "a beat, then the burst")
	near(float(r["at"]["burst"]) - float(r["at"]["back_to_plain"]), VistaSouthDrain.FLASH_PRE, 0.05, "the beat's length")
	near(float(r["end"]), 65.6 + VistaSouthDrain.FLASH_PRE, 0.5, "it adds the beat, nothing else")
	var before := 0.0
	var at_burst := 0.0
	var burst_drawn := false
	var back := float(r["at"]["back_to_plain"])
	for f in r["frames"]:
		if f["shot"] != "south" or float(f["t"]) < back:
			continue
		var fl := float(f["fl"])
		if fl < 0.0:
			before = maxf(before, float(f["flash"]))
		elif fl < 0.05:
			at_burst = maxf(at_burst, float(f["flash"]))
			burst_drawn = burst_drawn or bool(f["drawn"])
	check(before < 0.5, "the gate is quiet before (%.2f)" % before)
	check(at_burst > 2.0, "it flares in the burst's frame (%.2f)" % at_burst)
	check(burst_drawn, "the town's burst is drawn in that frame")
	v.queue_free()


## G5R3-50: the leaves framing the 「隔」 tower insert hang from boughs that run out of the frame. In
## every view the canvas serves, every leaf pixel in view joins (8-connected, through pixels in view)
## the frame's edge on its corner's sides: the bottom or left edge for the bottom left, the bottom or
## right for the bottom right, the top or left for the top left (before, two clumps floated over the
## dark ridge at the bottom left on every view, more in every corner on wide ones).
func test_the_tower_leaves_hang_from_boughs_out_of_the_frame() -> void:
	var v := _vista()
	v.show_shot("tower")
	var tower: VistaTower = v.shots["tower"]
	var sides := {"BL": ["left", "bottom"], "BR": ["right", "bottom"], "TL": ["top", "left"]}
	for size in [Vector2i(426, 240), Vector2i(480, 270), Vector2i(455, 256), Vector2i(512, 288), Vector2i(480, 300), Vector2i(533, 300),
			Vector2i(640, 270), Vector2i(688, 288), Vector2i(800, 360), Vector2i(960, 270), Vector2i(1024, 560)]:
		tower.layout(size)
		tower.update({"tower": 1.0}, 1.0)
		for k in ["BL", "BR", "TL"]:
			var spr: Sprite2D = tower.leaves[k]
			var img: Image = spr.texture.get_image()
			var lw := img.get_width()
			var lh := img.get_height()
			var o := Vector2i(spr.position.round())
			var data := img.get_data()
			# the layer's pixels in view, by screen position
			var w: int = size.x
			var h: int = size.y
			var vis := PackedByteArray()
			vis.resize(w * h)
			var n_vis := 0
			for y in range(maxi(0, o.y), mini(h, o.y + lh)):
				for x in range(maxi(0, o.x), mini(w, o.x + lw)):
					if data[((y - o.y) * lw + (x - o.x)) * 4 + 3] > 127:
						vis[y * w + x] = 1
						n_vis += 1
			var stack := PackedInt32Array()
			for i in w * h:
				if vis[i] == 0:
					continue
				var x := i % w
				var y := i / w
				var edge := false
				for sd in sides[k]:
					edge = edge or (sd == "left" and x == 0) or (sd == "right" and x == w - 1) or (sd == "top" and y == 0) or (sd == "bottom" and y == h - 1)
				if edge:
					vis[i] = 2
					stack.append(i)
			var reached := stack.size()
			while not stack.is_empty():
				var i := stack[stack.size() - 1]
				stack.resize(stack.size() - 1)
				var x := i % w
				var y := i / w
				for dy in [-1, 0, 1]:
					for dx in [-1, 0, 1]:
						var xx: int = x + dx
						var yy: int = y + dy
						if xx < 0 or yy < 0 or xx >= w or yy >= h:
							continue
						var j := yy * w + xx
						if vis[j] == 1:
							vis[j] = 2
							reached += 1
							stack.append(j)
			eq(reached, n_vis, "every leaf of the %s corner in view hangs from the frame's edge at %s (%d of %d px)" % [k, size, reached, n_vis])
	v.queue_free()
