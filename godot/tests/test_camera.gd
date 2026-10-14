extends TestCase
## The pixel camera: locked to whole pixels while following her as she moves (no shimmer of her
## sprite against the screen), sub-pixel smooth when she stands or for cinematic moves.

const DT := 1.0 / 60.0


func test_following_a_walking_target_stays_on_whole_pixels() -> void:
	var c := PixelCamera.new()
	var p := {"v": Vector2(100, 100)}
	c.follow(func() -> Vector2: return p["v"], {"cut": true})
	var fractional := 0
	for i in 120:
		p["v"] += Vector2(1.13, 0.0)   # 68 px/s, her walking speed at 1 m = 20 px
		c.update(DT)
		if c.pos != c.pos.round():
			fractional += 1
	eq(fractional, 0, "no sub-pixel camera while she walks")
	check(c.pos.x < p["v"].x and c.pos.x > p["v"].x - 20.0, "the camera lags a little (%.1f behind)" % (p["v"].x - c.pos.x))


func test_standing_still_the_camera_settles_smoothly() -> void:
	var c := PixelCamera.new()
	var p := {"v": Vector2(100, 100)}
	c.follow(func() -> Vector2: return p["v"], {"cut": true})
	for i in 30:
		p["v"] += Vector2(1.13, 0.0)
		c.update(DT)
	var seen_fraction := false
	for i in 120:
		c.update(DT)
		if c.pos != c.pos.round():
			seen_fraction = true
	check(seen_fraction, "the settle uses sub-pixel steps")
	check(c.pos.distance_to(p["v"].round()) < 0.6, "and arrives on her")


func test_a_cinematic_move_is_subpixel_and_respects_its_speed() -> void:
	var slow := PixelCamera.new()
	var fast := PixelCamera.new()
	slow.point(Vector2.ZERO, {"cut": true})
	fast.point(Vector2.ZERO, {"cut": true})
	slow.point(Vector2(100, 0), {"speed": 1.0})
	fast.point(Vector2(100, 0), {"speed": 6.0})
	for i in 30:
		slow.update(DT)
		fast.update(DT)
	check(slow.pos.x != roundf(slow.pos.x), "sub-pixel positions")
	check(fast.pos.x > slow.pos.x * 2.0, "a lower speed is a slower crane (%.1f vs %.1f)" % [slow.pos.x, fast.pos.x])


func test_the_view_stays_inside_the_bounds() -> void:
	var c := PixelCamera.new()
	c.view = Vector2(480, 270)
	c.bounds = Rect2(0, 0, 640, 480)
	c.point(Vector2(10, 10), {"cut": true})
	eq(c.pos, Vector2(240, 135), "clamped to the top-left corner")
	c.point(Vector2(1000, 1000), {"cut": true})
	eq(c.pos, Vector2(400, 345), "clamped to the bottom-right corner")
