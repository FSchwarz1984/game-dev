class_name Qualities
## 「移」: the one verb (take, give, release) over five qualities that are moved, never created.
## Ported from src/game/qualities.js. A transfer moves one unit; anything that seems to appear comes
## from an explicit source (sun, fire, waterfall...) and anything that vanishes goes to the air.
## Pure logic: no nodes, no rendering. The presentation reads events and derived state.

const ALL: Array[String] = ["w", "h", "l", "s", "v"]

const INFO := {
	"w": {"kanji": "重", "key": "weight", "color": "#d9c7a6"},
	"h": {"kanji": "熱", "key": "heat", "color": "#ff8a4a"},
	"l": {"kanji": "光", "key": "light", "color": "#ffe08a"},
	"s": {"kanji": "音", "key": "sound", "color": "#9fd0ff"},
	"v": {"kanji": "生", "key": "life", "color": "#8fdc7a"},
}

## Why a transfer was refused; the UI turns each into a line of feedback (never fail silently).
const SACRED := "sacred"       # bound by a shimenawa
const EMPTY := "empty"         # nothing left to take or give
const FULL := "full"           # the receiver cannot hold more
const OVERLOAD := "overload"   # her body would drift beyond what she can carry
const NONE := "none"           # no target
const FAR := "far"             # the target is deep-far: her hand passes through it


static func kanji(k: String) -> String:
	return INFO[k]["kanji"]


static func color(k: String) -> Color:
	return Color.html(INFO[k]["color"])


## Every quality key -> src[k] or the fallback.
static func per(src: Dictionary, fallback: int = 0) -> Dictionary:
	var out := {}
	for k in ALL:
		out[k] = int(src.get(k, fallback))
	return out


static func can_take(actor: QualityHolder, target: QualityHolder, k: String, cap: int) -> String:
	if target.sacred:
		return SACRED
	if target.q[k] <= target.min_q[k]:
		return EMPTY
	if actor.q[k] + 1 > actor.max_q[k]:
		return FULL
	if actor.deviation_after(k, 1) > cap:
		return OVERLOAD
	return ""


static func can_give(actor: QualityHolder, target: QualityHolder, k: String, cap: int) -> String:
	if target.sacred:
		return SACRED
	if actor.q[k] <= actor.min_q[k]:
		return EMPTY
	if target.q[k] + 1 > target.max_q[k]:
		return FULL
	if actor.deviation_after(k, -1) > cap:
		return OVERLOAD
	return ""


static func can_release(actor: QualityHolder, k: String, cap: int) -> String:
	if actor.q[k] <= actor.min_q[k]:
		return EMPTY
	if actor.deviation_after(k, -1) > cap:
		return OVERLOAD
	return ""


## The chemistry table: derived state per material class. Things never change each other directly;
## only their qualities change, and the state follows. First-pass thresholds (from the JS gray box).
static func state_of(h: QualityHolder) -> Dictionary:
	var q := h.q
	match h.material:
		"stone":
			return {"floats": q["w"] <= 0, "anchored": q["w"] >= 3}
		"wood":
			return {"floats": q["w"] <= 1, "burning": q["h"] >= 3, "sprouting": q["v"] >= 2}
		"water":
			return {"frozen": q["h"] <= 0, "steaming": q["h"] >= 3, "silent": q["s"] <= 0}
		"plant":
			return {"stage": clampi(q["v"], 0, 4), "withered": q["v"] <= 0, "burning": q["h"] >= 3}
		"bell":
			return {"ringing": q["s"] >= 1}
		"lantern":
			return {"lit": q["l"] >= 1, "glow": q["l"]}
		"yokai":
			# A hungry yokai is spawned off its natural state; it calms once every quality except life
			# is back at base. Taking all of its life kills it: the same verb, the player's choice.
			var calm: bool = q["v"] > 0
			for k in ALL:
				if k != "v" and q[k] != h.base[k]:
					calm = false
			return {"dead": q["v"] <= 0, "calm": calm}
		"body":
			return BodyState.flags_of(h)
	return {}
