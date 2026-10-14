class_name BodyState
extends RefCounted
## Her body as data-driven states per quality (docs/design/body-effects-draft.md, PENDING; R-6).
## Each quality is at a level relative to her natural amount: 0 given away, 1 natural, 2 extra,
## 3 extra twice. Every level carries effects (BodyRules) that change, at the same moment, how she
## moves, how the environment acts on her, what she does to it, her risks, her look and her sound.
## The world reads `fx` (merged effects); the actor reads `look()`; the HUD reads `levels` and
## `progress` (how far her given-away share has come back).
##
## Her own share returns by itself: while q[k] < natural, after regen_delay seconds one unit flows
## back from the ledger's air (signed balance, totals conserved), then one every regen_interval.
## Extra she carries never leaves by itself: she must give it or release it.

var prof: Dictionary = {}
var levels: Dictionary = {}       # k -> 0..3
var fx: Dictionary = {}           # merged effects of every quality's current level
var per_q: Dictionary = {}        # k -> effects of that quality's level
var away_t: Dictionary = {}       # k -> seconds her share has been away (toward the next return)
var returned: Dictionary = {}     # k -> units already returned in this absence
var progress: Dictionary = {}     # k -> 0..1 toward the next return (0 when nothing is away)
var hot_t := 0.0                  # seconds spent carrying extra heat
var burning := false
var burn_t := 0.0
var wet := 0.0                    # 0 dry .. 1 soaked
var integrity := 5
var integrity_max := 5
var heal_acc := 0.0


func _init(profile: Dictionary = {}) -> void:
	set_profile(profile)


func set_profile(profile: Dictionary) -> void:
	prof = profile
	integrity_max = int(prof.get("integrity_max", 5))
	integrity = integrity_max
	for k in Qualities.ALL:
		levels[k] = 1
		away_t[k] = 0.0
		returned[k] = 0
		progress[k] = 0.0
	fx = {}
	per_q = {}


func capacity() -> int:
	return int(prof.get("capacity", 1))


func base_speed() -> float:
	return float(prof.get("base_speed", 3.4))


func natural() -> Dictionary:
	return Qualities.per(prof.get("natural", {}), 1)


static func level_of(holder: QualityHolder, k: String) -> int:
	return clampi(holder.q[k] - holder.base[k] + 1, 0, 3)


## Plain flags (heavy/light, hot/cold...) from the drift sign, as bodyState in the JS.
static func flags_of(h: QualityHolder) -> Dictionary:
	var d := func(k: String) -> int: return h.q[k] - h.base[k]
	return {
		"heavy": d.call("w") > 0, "light": d.call("w") < 0,
		"hot": d.call("h") > 0, "cold": d.call("h") < 0,
		"glowing": d.call("l") > 0, "shadowed": d.call("l") < 0,
		"loud": d.call("s") > 0, "silent": d.call("s") < 0,
		"lively": d.call("v") > 0, "faint": d.call("v") < 0,
	}


## Recomputes levels and effects from the holder; returns true when any level changed.
func refresh(holder: QualityHolder) -> bool:
	var changed := false
	var parts: Array = []
	for k in Qualities.ALL:
		var lv := level_of(holder, k)
		if lv != levels[k]:
			changed = true
		levels[k] = lv
		var e := BodyRules.effects_at(prof, k, lv)
		per_q[k] = e
		parts.append(e)
	if changed or fx.is_empty():
		fx = BodyRules.merge_effects(parts)
	return changed


func effect(name: String, default = null):
	return fx.get(name, default)


func flag(name: String) -> bool:
	return bool(fx.get(name, false))


func mul(name: String) -> float:
	return float(fx.get(name, 1.0))


func speed() -> float:
	var s := base_speed() * mul("speed_mul")
	if wet > 0.0:
		s *= 1.0 - 0.245 * wet
	return s


## Advances the timers: the return of her own share, heat building toward ignition, burning,
## getting wet and drying. env: {"in_water": bool, "deep": bool, "sunny": bool}.
## Returns events for the field's queue.
func tick(dt: float, holder: QualityHolder, ledger: Ledger, env: Dictionary = {}) -> Array:
	var events: Array = []
	var delay := float(prof.get("regen_delay", 0.0))
	var interval := float(prof.get("regen_interval", 0.0))
	for k in Qualities.ALL:
		if delay > 0.0 and holder.q[k] < holder.base[k]:
			var need := delay if int(returned[k]) == 0 else maxf(0.1, interval)
			away_t[k] += dt
			progress[k] = clampf(away_t[k] / need, 0.0, 1.0)
			if away_t[k] >= need:
				away_t[k] = 0.0
				returned[k] += 1
				events.append(ledger.regain(holder, k, String(prof.get("regen_from", "air")) != "source"))
				progress[k] = 0.0
		else:
			away_t[k] = 0.0
			returned[k] = 0
			progress[k] = 0.0
	refresh(holder)

	# water and drying
	var rates: Dictionary = prof.get("wet_rates", {})
	if env.get("in_water", false):
		wet = minf(1.0, wet + float(rates.get("deep" if env.get("deep", false) else "shallow", 0.5)) * dt)
	else:
		var dry := float(rates.get("dry_sun" if env.get("sunny", false) else "dry", 0.05)) + float(fx.get("dry_rate_add", 0.0))
		wet = maxf(0.0, wet - dry * dt)

	# heat: carried extra heat builds up and sets the hat alight
	var ignite_after := float(fx.get("ignite_after", 0.0))
	if ignite_after > 0.0:
		hot_t += dt
		if not burning and hot_t >= ignite_after and wet < 0.5:
			burning = true
			burn_t = 0.0
			events.append({"type": "ignite"})
	else:
		hot_t = 0.0
	if burning:
		if env.get("in_water", false) or env.get("rolled", false):
			burning = false
			hot_t = 0.0
			events.append({"type": "extinguished"})
		else:
			burn_t += dt
			var every := float(prof.get("burn_interval", 1.1))
			while burn_t >= every:
				burn_t -= every
				integrity = maxi(0, integrity - 1)
				events.append({"type": "scorched", "integrity": integrity})
				if integrity == 0:
					burning = false
					events.append({"type": "torn"})
					break
	# extra life slowly mends the hat, one notch at a time
	var heal := float(fx.get("heal_rate", 0.0))
	if heal > 0.0 and integrity < integrity_max and not burning:
		heal_acc += heal * dt
		if heal_acc >= 1.0:
			heal_acc -= 1.0
			integrity += 1
			events.append({"type": "mended", "integrity": integrity})
	else:
		heal_acc = 0.0
	return events


## The interface for the sprite: everything her body state shows on her (actor.set_body_look).
func look() -> Dictionary:
	var rings: Array = []
	for k in Qualities.ALL:
		if int(levels[k]) >= 2:
			rings.append(Qualities.INFO[k]["color"])
	return {
		"outline": fx.get("outline", ""),
		"glow_color": fx.get("glow_color", ""),
		"glow_radius": float(fx.get("glow_radius", 0.0)),
		"tint": fx.get("tint", ""),
		"darken": float(fx.get("darken", 0.0)),
		"frost": float(fx.get("frost", 0.0)),
		"ember": float(fx.get("ember", 0.0)),
		"squash": float(fx.get("squash", 0.0)),
		"hover_m": float(fx.get("hover_m", 0.0)),
		"hover_bob": float(fx.get("hover_bob", 0.0)),
		"motes": fx.get("motes", ""),
		"rings": rings,
		"burning": burning,
		"wet": wet,
		"sound_ring": float(fx.get("sound_ring", 0.0)),
	}


## Footstep sound parameters (Audio.footstep).
func step_sound() -> Dictionary:
	return {
		"volume": float(fx.get("step_volume", 1.0)),
		"pitch": float(fx.get("step_pitch", 1.0)),
		"extra": fx.get("step_extra", ""),
	}
