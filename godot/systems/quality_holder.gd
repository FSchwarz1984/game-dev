class_name QualityHolder
extends RefCounted
## Quality state for anything that holds qualities: an object, a creature, or her body.
## `base` is the holder's natural state (yokai return to it when pacified; her body measures how far
## she has drifted from it). `sacred` marks things bound with a shimenawa: their qualities cannot be
## moved in either direction. `source` (sun, fire, waterfall...) refills one quality toward a cap:
## {"k": String, "rate": units/s, "cap": int, "active": Callable -> bool (optional)}.

var q: Dictionary = {}
var base: Dictionary = {}
var min_q: Dictionary = {}
var max_q: Dictionary = {}
var sacred := false
var material := "thing"
var source: Dictionary = {}
var regen := 0.0


## def: {"amounts", "base", "min", "max", "sacred", "material", "source"}, as makeHolder in the JS.
func _init(def: Dictionary = {}) -> void:
	q = Qualities.per(def.get("amounts", {}), 0)
	base = q.duplicate()
	var b: Dictionary = def.get("base", {})
	for k in b:
		base[k] = int(b[k])
	min_q = Qualities.per(def.get("min", {}), 0)
	max_q = Qualities.per(def.get("max", {}), 9)
	sacred = bool(def.get("sacred", false))
	material = String(def.get("material", "thing"))
	source = def.get("source", {})


## How far the holder has drifted from its natural state, summed over all qualities.
func deviation() -> int:
	var d := 0
	for k in Qualities.ALL:
		d += absi(q[k] - base[k])
	return d


func deviation_after(k: String, delta: int) -> int:
	return deviation() - absi(q[k] - base[k]) + absi(q[k] + delta - base[k])


func drift(k: String) -> int:
	return q[k] - base[k]


func snapshot() -> Dictionary:
	return q.duplicate()
