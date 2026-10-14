class_name Crew
extends RefCounted
## Followers and hauling, ported from src/game/crew.js. Followers walk in a line along the exact
## path she walked (a small night parade, not a blob) and can be dispatched to haul a physical
## item to a stockpile. Hauling is visible by construction: carriers walk to the item, wait until
## enough of them are there, lift together and walk it home. Taking the item's weight (重) lowers
## how many carriers it needs: the crew runs on the same verb.
## Members, items and stockpiles are dictionaries with "x", "z" (metres); items carry "weight" and
## "ref", stockpiles "ref" and "count".

const DEFAULTS := {
	"spacing": 0.9,      # metres between followers in the line
	"crumb": 0.25,       # breadcrumb spacing along her path
	"speed": 3.4,        # follower walking speed (m/s)
	"carry_speed": 1.6,  # speed while carrying
	"strength": 1,       # weight units one carrier can lift
	"arrive": 0.35,      # how close counts as "arrived"
}

var opt: Dictionary = DEFAULTS.duplicate()
var members: Array = []
var trail: Array[Vector2] = []   # her recent path, newest first
var jobs: Array = []
## Optional pathfinder (x0, z0, x1, z1) -> Array[Vector2] or []; straight lines without it.
var route: Callable


func _init(options: Dictionary = {}) -> void:
	opt.merge(options, true)


## Carriers needed for an item of weight w (an item with no weight still needs one pair of hands).
static func carriers_needed(weight: float, strength: float = 1.0) -> int:
	return maxi(1, ceili(weight / strength))


func add(x: float, z: float) -> Dictionary:
	var m := {"x": x, "z": z, "state": "follow", "job": null, "slot": 0, "path": [], "goal": Vector2.INF}
	members.append(m)
	return m


## Record her position; keeps enough path for the whole line.
func lead(x: float, z: float) -> void:
	var p := Vector2(x, z)
	if trail.is_empty() or trail[0].distance_to(p) >= float(opt["crumb"]):
		trail.push_front(p)
	var keep := ceili((members.size() + 2) * float(opt["spacing"]) / float(opt["crumb"])) + 4
	if trail.size() > keep:
		trail.resize(keep)


## The point `along` metres behind her on the recorded path (Vector2.INF without a path).
func point_behind(along: float) -> Vector2:
	return Crew.point_on_trail(trail, along)


static func point_on_trail(t: Array[Vector2], along: float) -> Vector2:
	if t.is_empty():
		return Vector2.INF
	var acc := 0.0
	for i in range(1, t.size()):
		var seg := t[i - 1].distance_to(t[i])
		if acc + seg >= along:
			var f := (along - acc) / seg if seg > 0.0 else 0.0
			return t[i - 1].lerp(t[i], f)
		acc += seg
	return t[t.size() - 1]


## Send followers to haul `item` to `dest`. Takes the closest idle followers; returns the job, or
## an empty dictionary when nobody is free.
func dispatch(item: Dictionary, dest: Dictionary) -> Dictionary:
	var idle := members.filter(func(m): return m["state"] == "follow")
	var ip := Vector2(item["x"], item["z"])
	idle.sort_custom(func(a, b): return Vector2(a["x"], a["z"]).distance_to(ip) < Vector2(b["x"], b["z"]).distance_to(ip))
	for j in jobs:
		if j["item"]["ref"] == item["ref"]:
			# dispatching again at an item that is still short of hands sends more helpers
			if j["state"] != "gather":
				return j
			for m in idle.slice(0, shortfall(j)):
				m["state"] = "to_item"
				m["job"] = j
				j["carriers"].append(m)
			return j
	if idle.is_empty():
		return {}
	var need := carriers_needed(float(item["weight"]), float(opt["strength"]))
	var job := {"item": item, "dest": dest, "carriers": idle.slice(0, need), "state": "gather", "delivered": false}
	var i := 0
	for m in job["carriers"]:
		m["state"] = "to_item"
		m["job"] = job
		m["slot"] = i
		i += 1
	jobs.append(job)
	return job


## How many more hands a job still needs (shown above the item: "还需要 N").
func shortfall(job: Dictionary) -> int:
	return maxi(0, carriers_needed(float(job["item"]["weight"]), float(opt["strength"])) - job["carriers"].size())


## Everyone drops what they are doing and rejoins the line; carried items stay where they are.
func recall() -> void:
	for j in jobs:
		j["state"] = "dropped"
	jobs = []
	for m in members:
		m["state"] = "follow"
		m["job"] = null


static func _step(m: Dictionary, t: Vector2, speed: float, dt: float) -> float:
	var p := Vector2(m["x"], m["z"])
	var d := p.distance_to(t)
	if d < 1e-6:
		return 0.0
	var s := minf(d, speed * dt)
	p += (t - p) / d * s
	m["x"] = p.x
	m["z"] = p.y
	return d - s


## Walk toward t along a route when a pathfinder is set; returns the distance still to go.
func _go(m: Dictionary, t: Vector2, speed: float, dt: float) -> float:
	var p := Vector2(m["x"], m["z"])
	if not route.is_valid() or p.distance_to(t) < 1.2:
		m["path"] = []
		return _step(m, t, speed, dt)
	if (m.get("path", []) as Array).is_empty() or (m.get("goal", Vector2.INF) as Vector2).distance_to(t) > 0.6:
		var r: Array = route.call(p.x, p.y, t.x, t.y)
		m["path"] = r if not r.is_empty() else [t]
		m["goal"] = t
	var path: Array = m["path"]
	while path.size() > 1 and p.distance_to(path[0]) < 0.25:
		path.pop_front()
	_step(m, path[0], speed, dt)
	return Vector2(m["x"], m["z"]).distance_to(t)


func update(dt: float) -> void:
	var speed := float(opt["speed"])
	# followers in line, in the order they joined; one that has fallen far behind finds its way back
	var rank := 0
	for m in members:
		if m["state"] != "follow":
			continue
		rank += 1
		var p := point_behind(rank * float(opt["spacing"]))
		if p != Vector2.INF:
			if Vector2(m["x"], m["z"]).distance_to(p) > 2.5:
				_go(m, p, speed * 1.3, dt)
			else:
				_step(m, p, speed, dt)

	for job in jobs.duplicate():
		var it: Dictionary = job["item"]
		var carriers: Array = job["carriers"]
		var n := carriers.size()
		if job["state"] == "gather":
			var arrived := 0
			for i in n:
				if _go(carriers[i], _ring(it, i, n), speed, dt) <= float(opt["arrive"]):
					arrived += 1
			if arrived == n and shortfall(job) == 0:
				job["state"] = "carry"
				for m in carriers:
					m["state"] = "carry"
					m["path"] = []
		elif job["state"] == "carry":
			var left := _go(it, Vector2(job["dest"]["x"], job["dest"]["z"]), float(opt["carry_speed"]), dt)
			for i in n:
				var rp := _ring(it, i, n)
				carriers[i]["x"] = rp.x
				carriers[i]["z"] = rp.y
			if left <= float(opt["arrive"]):
				job["state"] = "done"
				job["delivered"] = true
				job["dest"]["count"] = int(job["dest"].get("count", 0)) + 1
				for m in carriers:
					m["state"] = "follow"
					m["job"] = null
				jobs.erase(job)


## Ring positions around the item so carriers don't stack on one point.
static func _ring(it: Dictionary, i: int, n: int) -> Vector2:
	var a := float(i) / float(n) * TAU
	return Vector2(it["x"] + cos(a) * 0.45, it["z"] + sin(a) * 0.45)
