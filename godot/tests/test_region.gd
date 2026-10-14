extends TestCase
## The ground model of the test region: terraces at 0.5 m steps, cliffs block, stairs connect,
## stairs have side walls, water stops a natural body. Moves go through Field.update (the mover).

const DT := 1.0 / 30.0


static func region() -> RegionData:
	return RegionData.load_dir("res://world/regions/test")


static func field_on(r: RegionData, prof: String = "draft") -> Field:
	return Field.new({"ground": r.ground_kind, "height": r.height_at, "profile": TestCase.profile(prof)})


static func walk(f: Field, seconds: float, dir: Vector2) -> void:
	var t := 0.0
	while t < seconds:
		f.update(DT, {"mx": dir.x, "mz": dir.y})
		t += DT


func place(f: Field, x: float, z: float) -> void:
	f.player.x = x
	f.player.z = z
	f.player.h = f.ground_height(x, z)
	f.player.vx = 0.0
	f.player.vz = 0.0


func test_the_mask_gives_terrace_heights_in_half_metre_steps() -> void:
	var r := region()
	eq(r.size, Vector2i(128, 96), "mask size")
	near(r.height_at(10.25, 22.0), 0.0)
	near(r.height_at(5.0, 11.0), 0.5)
	near(r.height_at(5.0, 3.0), 1.5)
	near(r.height_at(25.0, 3.0), 1.0)
	eq(r.material_at(10.25, 20.0), "dirt")
	eq(r.material_at(10.25, 13.5), "stairs")
	eq(r.material_at(4.5, 18.5), "deep_water")
	eq(r.material_at(-1.0, 5.0), "void", "outside the region")
	eq(r.ground_kind(-0.1, 5.0, 0.1, 5.0), Field.Ground.WALL, "the region's edge blocks")


func test_a_cliff_blocks_her_both_ways() -> void:
	var r := region()
	var f := field_on(r)
	place(f, 5.0, 14.6)
	walk(f, 2.0, Vector2(0, -1))
	check(f.player.z >= 14.0, "stopped below the 0.5 m cliff (z=%.2f)" % f.player.z)
	near(f.player.h, 0.0)
	place(f, 5.0, 7.6)
	near(f.player.h, 1.5, 1e-6, "on the plateau")
	walk(f, 2.0, Vector2(0, 1))
	check(f.player.z < 8.0, "stopped at the plateau's edge (z=%.2f)" % f.player.z)
	near(f.player.h, 1.5)


func test_stairs_carry_her_up_one_level_and_then_the_next() -> void:
	var r := region()
	var f := field_on(r)
	place(f, 10.25, 16.0)
	walk(f, 1.6, Vector2(0, -1))
	check(f.player.z < 13.0, "climbed the first stairs (z=%.2f)" % f.player.z)
	near(f.player.h, 0.5, 1e-6, "on the middle terrace")
	walk(f, 2.4, Vector2(0, -1))
	check(f.player.z < 6.0, "climbed the second stairs (z=%.2f)" % f.player.z)
	near(f.player.h, 1.5, 1e-6, "on the plateau")
	# and back down
	walk(f, 4.0, Vector2(0, 1))
	check(f.player.z > 14.0, "came back down (z=%.2f)" % f.player.z)
	near(f.player.h, 0.0)


func test_a_staircase_has_side_walls() -> void:
	# Pushing sideways on the stairs, the mover slides her along the side wall (up or down the steps,
	# as along any wall); she may leave the staircase only at its foot or head, never over its side.
	var r := region()
	var f := field_on(r)
	for dir in [Vector2(1, 0), Vector2(-1, 0)]:
		place(f, 10.25, 7.0)
		near(f.player.h, 1.0, 0.13, "half way up")
		var bad := 0
		for i in 45:
			var p0 := Vector2(f.player.x, f.player.z)
			var m0 := r.material_at(p0.x, p0.y)
			var h0 := f.player.h
			f.update(DT, {"mx": dir.x, "mz": dir.y})
			var m1 := r.material_at(f.player.x, f.player.z)
			if (m0 == "stairs") != (m1 == "stairs") and absf(f.player.h - h0) > 0.05:
				var c0 := int(floor(p0.x / r.cell_m))
				var c1 := int(floor(f.player.x / r.cell_m))
				if c0 != c1:
					bad += 1
		eq(bad, 0, "never over the side wall pushing %s" % str(dir))


func test_heights_change_only_on_stairs() -> void:
	# walking anywhere for a while, every change of height between frames is small (stairs), never a
	# cliff's 0.5 m
	var r := region()
	var f := field_on(r)
	place(f, 10.25, 22.0)
	var worst := 0.0
	var dirs := [Vector2(0, -1), Vector2(1, -1).normalized(), Vector2(1, 0), Vector2(-1, -1).normalized(), Vector2(0, 1), Vector2(-1, 0)]
	for d in dirs:
		for i in 90:
			var h0 := f.player.h
			f.update(DT, {"mx": d.x, "mz": d.y})
			worst = maxf(worst, absf(f.player.h - h0))
	check(worst <= 0.3 + 1e-6, "largest height change between frames %.3f m" % worst)


func test_water_stops_a_natural_body_and_carries_a_light_one() -> void:
	var r := region()
	var f := field_on(r)
	place(f, 8.0, 18.5)  # east of the pond, on grass
	var wet_frames := 0
	for i in 60:
		f.update(DT, {"mx": -1, "mz": 0})
		if r.material_at(f.player.x, f.player.z).contains("water"):
			wet_frames += 1
	eq(wet_frames, 0, "a natural body never steps onto the water")
	# give her own weight away: light, she floats over the water (draft: w given -> floats)
	place(f, 8.0, 18.5)
	f.player.holder.q["w"] = 0
	f.player.body.refresh(f.player.holder)
	check(f.player.body.flag("floats"), "floats")
	for i in 45:
		f.update(DT, {"mx": -1, "mz": 0})
	check(r.material_at(f.player.x, f.player.z).contains("water"), "light, she is out on the pond (x=%.2f)" % f.player.x)
