class_name BodyRules
extends Resource
## Every number of her body in one resource (res://systems/body_rules.tres), as switchable profiles.
## "draft"  = docs/design/body-effects-draft.md (PENDING the user's approval): natural 1 of each
##            quality, capacity 1, her own share returns after 9 s, per-state effects.
## "legacy" = what the JS segment 1 shipped (natural w2 h1 l0 s1 v3, capacity 3, no return;
##            heavy walks at 0.7, light at 1.2 and over water).
## GameState.settings["body_profile"] picks one; nothing in code hard-codes these numbers.
##
## A profile:
##   natural: {k: int}          her natural amount of each quality (her holder's base)
##   capacity, capacity_max     how far she may drift from natural, summed over qualities
##   regen_delay, regen_interval  seconds until her given-away share returns (first unit, then each
##                              further unit); <= 0 disables the return
##   regen_from                 "air": the unit is drawn from the ledger's air (signed balance;
##                              strictly conserved, as the lead specified for P1); "source": it
##                              reappears like a source refill (the draft's latest wording: the one
##                              exception to conservation, still balanced through Ledger.sourced)
##   over_natural_cap           no holder may hold more than natural + this of any quality (the
##                              draft's guard against farming her returning share); < 0: no cap
##   base_speed (m/s), accel (m/s^2, 0 = instant), integrity_max (hat notches)
##   burn_interval (s per lost notch while burning), wet_rates {shallow, deep, dry, dry_sun}
##   states: {k: {"given": {...}, "extra": {...}, "extra2": {...}}}  effects per level; "natural" has
##           none. "extra2" (two units over natural) inherits "extra" and overrides it.
##
## Effect keys and how several states combine (MERGE):
##   movement:     speed_mul, accel, hover_m, hover_bob, fall_mul, can_dodge, push_strength
##   environment:  wind_mul, floats, sinks, freezes_water, melts_ice, presses_plates,
##                 breaks_rotten, flattens_grass, ignites_grass, reveals_hidden, rings_bells,
##                 scares_animals, footprint_flowers, attracts_insects
##   risk:         ignite_after (s), damage_mul, blown_by_gust, heal_rate, dry_rate_add
##   detection:    seen_mul, heard_mul, life_sense_mul
##   look:         outline (colour), glow_color, glow_radius (m), tint, darken, frost, ember,
##                 squash, motes, dark_spot, step_dust, sparks, breath, sound_ring (m)
##   sound:        step_volume, step_pitch, step_extra ("thud", "drum")

const LEVELS: Array[String] = ["given", "natural", "extra", "extra2"]

const MERGE := {
	"speed_mul": "mul", "wind_mul": "mul", "fall_mul": "max", "damage_mul": "mul",
	"seen_mul": "mul", "heard_mul": "mul", "life_sense_mul": "mul",
	"step_volume": "mul", "step_pitch": "mul",
	"accel": "min_pos", "ignite_after": "min_pos",
	"hover_m": "max", "hover_bob": "max", "push_strength": "max", "glow_radius": "max",
	"darken": "max", "frost": "max", "ember": "max", "squash": "max", "sound_ring": "max",
	"heal_rate": "max", "dry_rate_add": "max",
}

@export var active_profile: String = "draft"
@export var profiles: Dictionary = {}


func profile(name: String = "") -> Dictionary:
	var key := name if name != "" else active_profile
	if profiles.has(key):
		return profiles[key]
	push_warning("BodyRules: no profile '%s', using '%s'" % [key, active_profile])
	return profiles.get(active_profile, {})


func profile_names() -> Array:
	return profiles.keys()


## Effects of quality k at level i (0 given, 1 natural, 2 extra, 3 extra2) in a profile.
static func effects_at(prof: Dictionary, k: String, level: int) -> Dictionary:
	var states: Dictionary = prof.get("states", {}).get(k, {})
	match level:
		0:
			return states.get("given", {})
		2:
			return states.get("extra", {})
		3:
			var e: Dictionary = states.get("extra", {}).duplicate()
			e.merge(states.get("extra2", {}), true)
			return e
	return {}


## Combines the effects of several qualities into one dictionary, by MERGE.
static func merge_effects(parts: Array) -> Dictionary:
	var out := {}
	for part in parts:
		for key in part:
			var v = part[key]
			if not out.has(key):
				out[key] = v
				continue
			var rule: String = MERGE.get(key, "")
			if v is bool:
				out[key] = out[key] or v
			elif rule == "mul":
				out[key] = float(out[key]) * float(v)
			elif rule == "max":
				out[key] = maxf(float(out[key]), float(v))
			elif rule == "min_pos":
				var a := float(out[key])
				var b := float(v)
				out[key] = b if a <= 0.0 else (a if b <= 0.0 else minf(a, b))
			# strings and colours: the first quality in Qualities.ALL order wins
	return out
