class_name Targeting
extends RefCounted
## Interaction targeting, ported from src/game/targeting.js: one target at a time, chosen by score,
## shown before any button is pressed, and stable: a challenger must win clearly and for a moment
## before the target switches. Never require pixel-perfect positioning (knowledge/05).
## Candidates are plain dictionaries {"x", "z", "priority"?, "reach"?, "ref"}; the actor is any
## dictionary or object with x, z, fx, fz (unit facing; the stick direction while it is held).

const DEFAULTS := {
	"reach": 2.6,          # metres; candidates may override with their own reach
	"cone_deg": 75.0,      # half-angle of the facing cone; things very close are allowed anyway
	"close_enough": 0.9,   # inside this distance the facing cone is ignored
	"switch_margin": 0.6,  # a challenger must beat the current score by this much...
	"dwell": 0.12,         # ...for this many seconds before the target switches
	"pick_hold": 2.0,      # a touch-picked target stays chosen this long unless it leaves reach
}

var opt: Dictionary = DEFAULTS.duplicate()
var current = null          # the chosen candidate dictionary, or null
var challenger = null
var challenge_t := 0.0
var picked = null
var pick_t := 0.0
var ranked: Array = []


func _init(options: Dictionary = {}) -> void:
	opt.merge(options, true)


## Score one candidate for an actor at (x, z) facing (fx, fz). -INF when not eligible.
## Higher is better: type priority dominates, then facing, then distance.
static func score(actor, c: Dictionary, o: Dictionary = DEFAULTS) -> float:
	var dx: float = c["x"] - actor.x
	var dz: float = c["z"] - actor.z
	var d := sqrt(dx * dx + dz * dz)
	var reach: float = c.get("reach", o["reach"])
	if d > reach:
		return -INF
	var facing := 1.0
	if d > 1e-4:
		facing = (dx * actor.fx + dz * actor.fz) / d
	if d > float(o["close_enough"]) and facing < cos(deg_to_rad(float(o["cone_deg"]))):
		return -INF
	return float(c.get("priority", 0)) * 4.0 + facing * 1.5 - (d / reach) * 2.0


static func _find(list: Array, ref) -> int:
	for i in list.size():
		if list[i]["c"]["ref"] == ref:
			return i
	return -1


## candidates: [{x, z, priority?, reach?, ref}]. Returns the chosen candidate or null.
func update(dt: float, actor, candidates: Array):
	var scored: Array = []
	for c in candidates:
		var s := score(actor, c, opt)
		if s > -INF:
			scored.append({"c": c, "s": s})
	scored.sort_custom(func(a, b): return a["s"] > b["s"])
	ranked = scored.map(func(e): return e["c"])

	# An explicit pick (touch tap or cycling) holds while it stays within reach.
	if picked != null:
		var i := _find(scored, picked["ref"])
		pick_t -= dt
		if i >= 0 and pick_t > 0.0:
			current = scored[i]["c"]
			return current
		picked = null

	if scored.is_empty():
		current = null
		challenger = null
		return null
	var best: Dictionary = scored[0]
	var ci := -1
	if current != null:
		ci = _find(scored, current["ref"])
	if ci < 0:
		challenger = null
		current = best["c"]
		return current
	var cur: Dictionary = scored[ci]
	if best["c"]["ref"] == cur["c"]["ref"] or best["s"] < cur["s"] + float(opt["switch_margin"]):
		challenger = null
		challenge_t = 0.0
		current = cur["c"]
		return current
	if challenger == null or challenger["ref"] != best["c"]["ref"]:
		challenger = best["c"]
		challenge_t = 0.0
	challenge_t += dt
	if challenge_t >= float(opt["dwell"]):
		challenger = null
		current = best["c"]
		return current
	current = cur["c"]
	return current


## Cycle to the next eligible candidate (Tab / shoulder button).
func cycle():
	if ranked.size() < 2:
		return current
	var i := 0
	for j in ranked.size():
		if current != null and ranked[j]["ref"] == current["ref"]:
			i = j
	return pick(ranked[(i + 1) % ranked.size()])


## Choose a candidate explicitly (touch tap on the object, or cycling).
func pick(c: Dictionary):
	picked = c
	pick_t = float(opt["pick_hold"])
	current = c
	return c
