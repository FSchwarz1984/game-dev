class_name Mover
## The kinematic mover, ported from Field.tryMove in src/game/field.js. Positions are (x, z) metres.
## blocker(x, z) -> Dictionary: {} when she may stand there, {"e": thing} for a round thing (anything
## with x, z), {"wall": true} for the ground, a cliff or a zone.
## Against a round thing she slides around it along its tangent; against anything else, along
## whichever axis is free; against a slanted bank she tries nearby directions, closest first.
## Never snags on a curve or a single corner cell.

const SLIDE_ANGLES: Array[float] = [0.5, -0.5, 1.0, -1.0, 1.35, -1.35, PI / 2.0, -PI / 2.0]


static func try_move(p: Vector2, n: Vector2, blocker: Callable) -> Vector2:
	var hit: Dictionary = blocker.call(n.x, n.y)
	if hit.is_empty():
		return n
	if hit.has("e"):
		var e = hit["e"]
		var o := Vector2(p.x - e.x, p.y - e.z)
		var od := o.length()
		if od < 1e-9:
			od = 1.0
		var t := Vector2(-o.y / od, o.x / od)
		var along := (n - p).dot(t)
		var s := p + t * along
		if absf(along) > 1e-5 and (blocker.call(s.x, s.y) as Dictionary).is_empty():
			return s
	if absf(n.x - p.x) > 1e-6 and (blocker.call(n.x, p.y) as Dictionary).is_empty():
		return Vector2(n.x, p.y)
	if absf(n.y - p.y) > 1e-6 and (blocker.call(p.x, n.y) as Dictionary).is_empty():
		return Vector2(p.x, n.y)
	var d := n - p
	var len := d.length()
	if len < 1e-6:
		return p
	# sideways last, at a fair pace: one step off a corner cell is enough to get round it
	for a in SLIDE_ANGLES:
		var c := cos(a)
		var sn := sin(a)
		var k := maxf(0.6, c)
		var tp := p + Vector2(d.x * c - d.y * sn, d.x * sn + d.y * c) * k
		if (blocker.call(tp.x, tp.y) as Dictionary).is_empty():
			return tp
	return p
