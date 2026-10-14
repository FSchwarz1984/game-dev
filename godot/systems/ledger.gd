class_name Ledger
extends RefCounted
## Keeps the books: every unit is in a holder, in the air, or came from a source.
## total(k) = sum over holders + air - sourced stays constant; the tests rely on it.
## The air is the ambient world's reservoir. Its balance is signed: when her own share comes back to
## her body (BodyState), it is drawn from the air even if nothing was released into it before, so the
## air can owe units. Totals stay exactly conserved either way.

signal event(e: Dictionary)

var holders: Array[QualityHolder] = []
var air: Dictionary = Qualities.per({}, 0)
var sourced: Dictionary = Qualities.per({}, 0)


func add(h: QualityHolder) -> QualityHolder:
	if not holders.has(h):
		holders.append(h)
	return h


## The holder leaves the world; what it held goes to the air (books stay balanced).
func remove(h: QualityHolder) -> void:
	holders.erase(h)
	for k in Qualities.ALL:
		air[k] += h.q[k]


## A story prop leaves the books together with what it holds (the JS field.remove behaviour).
func forget(h: QualityHolder) -> void:
	holders.erase(h)


func total(k: String) -> int:
	var t: int = air[k] - sourced[k]
	for h in holders:
		t += h.q[k]
	return t


func totals() -> Dictionary:
	var out := {}
	for k in Qualities.ALL:
		out[k] = total(k)
	return out


func _emit(e: Dictionary) -> Dictionary:
	event.emit(e)
	return e


func take(actor: QualityHolder, target: QualityHolder, k: String, cap: int) -> Dictionary:
	var reason := Qualities.can_take(actor, target, k, cap)
	if reason != "":
		return _emit({"type": "refused", "verb": "take", "k": k, "actor": actor, "target": target, "reason": reason})
	target.q[k] -= 1
	actor.q[k] += 1
	return _emit({"type": "transfer", "verb": "take", "k": k, "from": target, "to": actor})


func give(actor: QualityHolder, target: QualityHolder, k: String, cap: int) -> Dictionary:
	var reason := Qualities.can_give(actor, target, k, cap)
	if reason != "":
		return _emit({"type": "refused", "verb": "give", "k": k, "actor": actor, "target": target, "reason": reason})
	actor.q[k] -= 1
	target.q[k] += 1
	return _emit({"type": "transfer", "verb": "give", "k": k, "from": actor, "to": target})


## 放: one unit leaves her body as a burst; the presentation layer applies the area effect.
func release(actor: QualityHolder, k: String, cap: int) -> Dictionary:
	var reason := Qualities.can_release(actor, k, cap)
	if reason != "":
		return _emit({"type": "refused", "verb": "release", "k": k, "actor": actor, "reason": reason})
	actor.q[k] -= 1
	air[k] += 1
	return _emit({"type": "release", "verb": "release", "k": k, "from": actor})


## Her own share flows back (BodyState decides when): drawn from the air (from_air), or reappearing
## like a source refill (counted in `sourced`). Either way total(k) is unchanged.
func regain(actor: QualityHolder, k: String, from_air: bool = true) -> Dictionary:
	if from_air:
		air[k] -= 1
	else:
		sourced[k] += 1
	actor.q[k] += 1
	return _emit({"type": "regained", "k": k, "to": actor, "from": "air" if from_air else "source"})


## Sources (sun, fire, waterfall...) refill toward their cap while active.
func tick(dt: float) -> void:
	for h in holders:
		var s := h.source
		if s.is_empty():
			h.regen = 0.0
			continue
		var active: bool = true
		if s.has("active") and s["active"] is Callable:
			active = (s["active"] as Callable).call()
		var k: String = s["k"]
		if not active or h.q[k] >= int(s["cap"]):
			h.regen = 0.0
			continue
		h.regen += float(s["rate"]) * dt
		while h.regen >= 1.0 and h.q[k] < int(s["cap"]):
			h.regen -= 1.0
			h.q[k] += 1
			sourced[k] += 1
			_emit({"type": "source", "k": k, "holder": h})
