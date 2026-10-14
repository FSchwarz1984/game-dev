extends TestCase
## Saji's follow: beside and a little behind, never between the camera and her; on terraces she
## follows the lead's path up the stairs.

const DT := 1.0 / 30.0


static func open_blocker() -> Callable:
	return func(_x: float, _z: float, _fx: float, _fz: float) -> Dictionary: return {}


func test_she_keeps_beside_and_north_of_the_lead() -> void:
	var c := Companion.new(1.0, 0.0)
	var lead := Vector2(0, 0)
	var covering := 0
	for i in 150:  # the lead walks north (up the screen) for 5 s
		lead.y -= 3.4 * DT
		c.lead(lead.x, lead.y)
		c.update(DT, lead.x, lead.y, "back", open_blocker())
		# south of the lead (in front of her on screen) she must be off to the side or far enough
		# south that her 27 px sprite ends below the lead's feet
		if c.z > lead.y + 0.05 and absf(c.x - lead.x) < 0.6 and c.z - lead.y < 1.35:
			covering += 1
	eq(covering, 0, "never between the camera and the lead")
	var d := Vector2(c.x - lead.x, c.z - lead.y).length()
	check(d > 0.5 and d < 2.5, "close beside her (%.2f m)" % d)


func test_she_follows_up_the_stairs_on_the_test_region() -> void:
	var r := RegionData.load_dir("res://world/regions/test")
	var f := Field.new({"ground": r.ground_kind, "height": r.height_at, "profile": TestCase.profile("draft")})
	f.player.x = 10.25
	f.player.z = 17.0
	var c := Companion.new(11.5, 17.5)
	var blk := func(x: float, z: float, fx: float, fz: float) -> Dictionary:
		var g := r.ground_kind(x, z, fx, fz)
		return {"wall": true} if g != Field.Ground.GROUND else {}
	var t := 0.0
	while t < 5.0:
		f.update(DT, {"mx": 0, "mz": -1})
		c.lead(f.player.x, f.player.z)
		c.update(DT, f.player.x, f.player.z, "back", blk)
		t += DT
	near(f.player.h, 1.5, 1e-6, "she reached the plateau")
	for i in 90:  # she stands; Saji catches up
		f.update(DT)
		c.lead(f.player.x, f.player.z)
		c.update(DT, f.player.x, f.player.z, "back", blk)
	near(r.height_at(c.x, c.z), 1.5, 1e-6, "Saji is up there too (at %.2f, %.2f)" % [c.x, c.z])
	check(Vector2(c.x - f.player.x, c.z - f.player.z).length() < 2.5, "and close")
