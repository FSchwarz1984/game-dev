class_name Companion
extends RefCounted
## Saji's follow logic, ported from Actor.followStep in src/app/actors.js and made terrain-aware.
## She keeps beside and a little behind the lead, always a step north of the lead's feet, so she
## never stands between the camera and the lead. When the side spot is not reachable (a cliff, the
## lead on stairs, water) or she has fallen behind, she walks the lead's own recent path, which is
## always walkable. Very far behind (a scene teleported the lead), she catches up along the path.

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


func _init(px: float = 0.0, pz: float = 0.0, options: Dictionary = {}) -> void:
	x = px
	z = pz
	opt.merge(options, true)


## Record the lead's position (call every frame before update).
func lead(lx: float, lz: float) -> void:
	var p := Vector2(lx, lz)
	if trail.is_empty() or trail[0].distance_to(p) >= float(opt["crumb"]):
		trail.push_front(p)
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
	var free := func(px: float, pz: float) -> bool:
		return (blocker.call(px, pz, x, z) as Dictionary).is_empty()
	if mode == "side" and (not free.call(goal.x, goal.y) or _stuck_t > 0.6):
		mode = "trail"
	if mode == "trail":
		if dist_lead < 1.6 and free.call(goal.x, goal.y) and _stuck_t <= 0.0:
			mode = "side"
		else:
			goal = _next_on_trail(me)

	var d := me.distance_to(goal)
	if d < float(opt["near"]):
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


## The breadcrumb to walk to next: the point a little further toward the lead from the crumb
## nearest to her, but never closer to the lead than trail_spacing.
func _next_on_trail(me: Vector2) -> Vector2:
	if trail.is_empty():
		return me
	var best := 0
	var bd := INF
	for i in trail.size():
		var d := trail[i].distance_to(me)
		if d < bd:
			bd = d
			best = i
	# index 0 is the newest (the lead); walk toward lower indices
	var min_index := 0
	var acc := 0.0
	for i in range(1, trail.size()):
		acc += trail[i - 1].distance_to(trail[i])
		if acc >= float(opt["trail_spacing"]):
			min_index = i
			break
	var target_i := maxi(min_index, best - 2)
	return trail[target_i]
