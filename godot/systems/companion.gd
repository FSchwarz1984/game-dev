class_name Companion
extends RefCounted
## Saji's follow logic, ported from Actor.followStep in src/app/actors.js and made terrain-aware.
## She keeps beside and a little behind the lead, always a step north of the lead's feet, so she
## never stands between the camera and the lead. When the side spot is not reachable (a cliff, the
## lead on stairs, water) or she has fallen behind, she walks the lead's own recent path, which is
## always walkable. Very far behind (a scene teleported the lead), she catches up along the path.
## On the path she keeps her place in order and only skips ahead to crumbs she can reach in a straight
## line: the nearest crumb in plan can be a cliff above her (the lead walked back along the edge), and
## walking straight at it is how she used to get stuck at the foot of the stairs (knowledge/16 §14).

const DEFAULTS := {
	"side": 1.0,          # metres to the side of the lead
	"back": 0.45,         # metres north of the lead's feet
	"near": 0.5,          # close enough: stand still
	"speed": 3.2,
	"run_speed": 4.6,     # when more than run_beyond away
	"run_beyond": 3.0,
	"trail_spacing": 1.5, # how far behind the lead she walks on the path (>= 1.35 m: her sprite
	                      # then ends below the lead's feet even when she is straight south)
	"crumb": 0.25,
	"catch_up": 7.0,      # farther than this: jump onto the path behind the lead
}

var x := 0.0
var z := 0.0
var moving := false
var face := "front"
var opt: Dictionary = DEFAULTS.duplicate()
var trail: Array[Vector2] = []
var mode := "side"          # "side" or "trail"
var _stuck_t := 0.0
var _trail_end := false     # the trail goal is the last crumb before the lead
var _seq := 0               # crumbs recorded so far: the crumb at index i has id _seq - 1 - i
var _cursor := -1           # id of the crumb she is walking to on the trail (-1: pick one)


func _init(px: float = 0.0, pz: float = 0.0, options: Dictionary = {}) -> void:
	x = px
	z = pz
	opt.merge(options, true)


## Record the lead's position (call every frame before update).
func lead(lx: float, lz: float) -> void:
	var p := Vector2(lx, lz)
	if trail.is_empty() or trail[0].distance_to(p) >= float(opt["crumb"]):
		trail.push_front(p)
		_seq += 1
	if trail.size() > 160:
		trail.resize(160)


## lead_x, lead_z, lead_face: the lead now. blocker(x, z, from_x, from_z) -> Dictionary as Mover's
## blocker for her own body ({} = free). Returns true when she moved.
func update(dt: float, lead_x: float, lead_z: float, lead_face: String, blocker: Callable) -> bool:
	var me := Vector2(x, z)
	var lp := Vector2(lead_x, lead_z)
	var dist_lead := me.distance_to(lp)
	if dist_lead > float(opt["catch_up"]) and not trail.is_empty():
		var p := Crew.point_on_trail(trail, float(opt["trail_spacing"]) * 1.5)
		x = p.x
		z = p.y
		mode = "trail"
		_cursor = -1
		moving = false
		return true

	var side := 1.0
	if lead_face == "left":
		side = 1.0
	elif lead_face == "right":
		side = -1.0
	else:
		side = 1.0 if x >= lead_x else -1.0
	var goal := Vector2(lead_x + side * float(opt["side"]), lead_z - float(opt["back"]))
	if mode == "side" and (_stuck_t > 0.6 or not _reachable(me, goal, blocker)):
		mode = "trail"
		_cursor = -1
	if mode == "trail":
		if dist_lead < 1.6 and _stuck_t <= 0.0 and _reachable(me, goal, blocker):
			mode = "side"
		else:
			if _stuck_t > 1.0:  # something stands on the path: start again from the nearest crumb she can reach
				_cursor = -1
				_stuck_t = 0.0
			goal = _next_on_trail(me, blocker)

	var d := me.distance_to(goal)
	# on the trail the next crumb is a short step ahead: only stop at the end of the trail
	var stop := float(opt["near"]) if mode == "side" else (0.3 if _trail_end else 0.05)
	if d < stop:
		moving = false
		_stuck_t = 0.0
		return false
	var sp := minf(d, (float(opt["run_speed"]) if d > float(opt["run_beyond"]) else float(opt["speed"])) * dt)
	var want := me + (goal - me) / d * sp
	var np := Mover.try_move(me, want, func(px: float, pz: float) -> Dictionary: return blocker.call(px, pz, x, z))
	var moved := np.distance_to(me)
	if moved < sp * 0.3:
		_stuck_t += dt
	else:
		_stuck_t = maxf(0.0, _stuck_t - dt)
	if moved > 1e-4:
		face = Proj.face_of(np.x - x, np.y - z, face)
	x = np.x
	z = np.y
	moving = moved > 1e-4
	return moving


## The breadcrumb to walk to next. She keeps her place on the lead's path (the cursor), moves it on
## when she reaches a crumb, and looks up to a metre further along for a crumb she can walk to in a
## straight line; never closer to the lead than trail_spacing.
func _next_on_trail(me: Vector2, blocker: Callable) -> Vector2:
	if trail.is_empty():
		return me
	# index 0 is the newest (the lead); she walks toward lower indices
	var min_index := 0
	var acc := 0.0
	for i in range(1, trail.size()):
		acc += trail[i - 1].distance_to(trail[i])
		if acc >= float(opt["trail_spacing"]):
			min_index = i
			break
	var ci := _seq - 1 - _cursor
	if _cursor < 0 or ci < 0 or ci >= trail.size():
		ci = _nearest_reachable(me, blocker)
	# move on once she is at this crumb, but only to a next one she can walk to from here (within
	# 0.35 m of the top step she can still be on the stairs while the next crumb is on the plateau
	# beside them: then she first steps onto this crumb)
	while ci > min_index and trail[ci].distance_to(me) < 0.35 and _reachable(me, trail[ci - 1], blocker):
		ci -= 1
	var ahead := ci
	for j in range(ci - 1, maxi(min_index, ci - 4) - 1, -1):
		if _reachable(me, trail[j], blocker):
			ahead = j
	ci = maxi(ahead, min_index)
	_cursor = _seq - 1 - ci
	_trail_end = ci == min_index
	return trail[ci]


## The crumb nearest to her that she can reach in a straight line (the nearest one when none is).
func _nearest_reachable(me: Vector2, blocker: Callable) -> int:
	var order: Array[int] = []
	for i in trail.size():
		order.append(i)
	order.sort_custom(func(a: int, b: int) -> bool: return trail[a].distance_squared_to(me) < trail[b].distance_squared_to(me))
	for k in mini(order.size(), 16):
		if _reachable(me, trail[order[k]], blocker):
			return order[k]
	return order[0]


## Whether she can walk from a to b in a straight line (checked every 0.2 m with her own blocker).
func _reachable(a: Vector2, b: Vector2, blocker: Callable) -> bool:
	var n := maxi(1, ceili(a.distance_to(b) / 0.2))
	var prev := a
	for k in range(1, n + 1):
		var p := a.lerp(b, float(k) / n)
		if not (blocker.call(p.x, p.y, prev.x, prev.y) as Dictionary).is_empty():
			return false
		prev = p
	return true
