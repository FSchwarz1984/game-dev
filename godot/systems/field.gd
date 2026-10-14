class_name Field
extends RefCounted
## The playable field, ported from src/game/field.js: her body, the things around her, the transfer
## verb, the context action and zones, on ground supplied by the region. Pure logic on (x, z) metres;
## the presentation reads `entities`, `player`, `target` and the event queue (drain()).
##
## Additions over the JS: her body is a data-driven BodyState (BodyRules profile) that sets her
## speed, acceleration, what ground carries her and the timers of her own returning share; the
## ground has heights (terraces, stairs) and kinds (ground, water, deep water, wall); zones may
## blow wind; plan() says what a quality key would do now, for both control schemes.
##
## 遠化 in one rule: a thing is as far as the share of its natural qualities it has lost. Taking a
## quality from something pushes it away; giving it back brings it near again. A thing that lost
## everything (`deep`) cannot be reached at all: her hand passes through it, and it stays a step
## away however close she walks.

enum Ground { GROUND, WATER, DEEP, WALL }

const COS75 := 0.2588190451  # cos(75 deg)


class PlayerBody:
	var x := 0.0
	var z := 0.0
	var h := 0.0               # height of the ground under her (terraces, stairs)
	var fx := 0.0
	var fz := 1.0
	var vx := 0.0
	var vz := 0.0
	var moving := false
	var cap := 1
	var holder: QualityHolder
	var body: BodyState
	var safe := Vector2.ZERO   # the last dry, solid point she stood on
	var on := Ground.GROUND    # what the ground under her is


var L := Ledger.new()
var ground: Callable        # (x, z, from_x, from_z) -> Ground; invalid: open ground
var height: Callable        # (x, z) -> metres; invalid: 0
var entities: Array[FieldEntity] = []
var by_id: Dictionary = {}
var events: Array = []
var zones: Array = []
var targeting := Targeting.new()
var target: FieldEntity = null
var control := true          # false while a scene moves her
var verbs := {"take": [], "give": [], "release": []}  # qualities she may use with each verb
var player := PlayerBody.new()
var profile: Dictionary = {}  # the BodyRules profile in force


## opts: {"ground": Callable, "height": Callable, "profile": Dictionary (a BodyRules profile)}
func _init(opts: Dictionary = {}) -> void:
	ground = opts.get("ground", Callable())
	height = opts.get("height", Callable())
	var prof: Dictionary = opts.get("profile", {})
	profile = prof
	var natural := Qualities.per(prof.get("natural", {}), 1)
	player.holder = L.add(QualityHolder.new({"material": "body", "amounts": natural}))
	player.body = BodyState.new(prof)
	player.cap = int(prof.get("capacity", 1))
	player.body.refresh(player.holder)
	L.event.connect(_on_ledger_event)  # a method callable: no reference cycle with the ledger


func _on_ledger_event(e: Dictionary) -> void:
	events.append(e)


## Switch her body to another rules profile (setting change); her qualities reset to its natural.
func set_profile(prof: Dictionary) -> void:
	profile = prof
	var natural := Qualities.per(prof.get("natural", {}), 1)
	var h := player.holder
	for k in Qualities.ALL:
		L.air[k] += h.q[k] - natural[k]
		h.q[k] = natural[k]
		h.base[k] = natural[k]
	player.body.set_profile(prof)
	player.cap = int(prof.get("capacity", 1))
	player.body.refresh(h)
	push({"type": "profile"})


func add(def: Dictionary) -> FieldEntity:
	var e := FieldEntity.new()
	e.id = String(def.get("id", "e%d" % (entities.size() + 1)))
	e.kind = String(def.get("kind", "thing"))
	e.name = String(def.get("name", ""))
	e.x = float(def.get("x", 0.0))
	e.z = float(def.get("z", 0.0))
	e.r = float(def.get("r", 0.5))
	e.solid = bool(def.get("solid", false))
	e.priority = int(def.get("priority", 0))
	e.deep = bool(def.get("deep", false))
	e.targetable = def.get("targetable", true) != false
	e.reach = float(def.get("reach", -1.0))
	e.ctx = def.get("ctx", {})
	e.data = def.get("data", {})
	e.h = ground_height(e.x, e.z)
	e.holder = L.add(QualityHolder.new({
		"amounts": def.get("q", {}), "base": def.get("base", {}), "max": def.get("max", {}),
		"sacred": def.get("sacred", false), "material": def.get("material", "thing"),
	}))
	_cap(e.holder)
	e.far = e.farness()
	entities.append(e)
	by_id[e.id] = e
	return e


## The profile's guard: nothing holds more than natural + over_natural_cap of any quality.
func _cap(h: QualityHolder) -> void:
	var over := int(profile.get("over_natural_cap", -1))
	if over < 0:
		return
	for k in Qualities.ALL:
		h.max_q[k] = mini(h.max_q[k], maxi(h.q[k], h.base[k] + over))


func get_entity(id: String) -> FieldEntity:
	return by_id.get(id)


func remove(e: FieldEntity) -> void:
	entities.erase(e)
	by_id.erase(e.id)
	L.forget(e.holder)  # its qualities leave the books with it (story props only)
	if target == e:
		target = null


## A region the story listens to: {"id", "x0","x1","z0","z1"} or {"id","x","z","r"}.
## "block": a line she says when it turns her back; "wind": Vector2 m/s pushing her (scaled by her
## body's wind_mul).
func zone(def: Dictionary) -> Dictionary:
	var z := {"inside": false, "block": "", "touched": false}
	z.merge(def, true)
	zones.append(z)
	return z


## Let her use quality k with these verbs (the story unlocks them as they are taught).
func allow(k: String, which: Array = ["take", "give"]) -> void:
	for v in which:
		if not verbs[v].has(k):
			verbs[v].append(k)


func learned() -> Array:
	var out: Array = []
	for k in Qualities.ALL:
		if verbs["take"].has(k) or verbs["give"].has(k) or verbs["release"].has(k):
			out.append(k)
	return out


func set_deep(e: FieldEntity, deep: bool) -> void:
	e.deep = deep
	refresh(e)


func ground_height(x: float, z: float) -> float:
	return float(height.call(x, z)) if height.is_valid() else 0.0


func ground_kind(x: float, z: float, fx: float, fz: float) -> int:
	return int(ground.call(x, z, fx, fz)) if ground.is_valid() else Ground.GROUND


# ------------------------------------------------------------------ per frame

## input: {"mx", "mz"} world-axis movement (-1..1).
func update(dt: float, input: Dictionary = {}) -> void:
	var P := player
	L.tick(dt)
	var env := {"in_water": P.on == Ground.WATER or P.on == Ground.DEEP, "deep": P.on == Ground.DEEP}
	for e in P.body.tick(dt, P.holder, L, env):
		events.append(e)
	var was_moving := P.moving
	P.moving = false
	var want := Vector2.ZERO
	if control:
		var m := Vector2(float(input.get("mx", 0.0)), float(input.get("mz", 0.0)))
		var len := m.length()
		if len > 0.05:
			var dir := m / len
			P.fx = dir.x
			P.fz = dir.y
			want = dir * P.body.speed() * minf(1.0, len)
			P.moving = true
			if not was_moving:
				events.append({"type": "moved"})
	var v := Vector2(P.vx, P.vz)
	var accel := float(P.body.effect("accel", 0.0))
	v = v.move_toward(want, accel * dt) if accel > 0.0 else want
	var wind := _wind_at(P.x, P.z) * P.body.mul("wind_mul")
	var step := (v + wind) * dt
	P.vx = v.x
	P.vz = v.y
	if control and step.length() > 1e-7:
		var np := Mover.try_move(Vector2(P.x, P.z), Vector2(P.x, P.z) + step, blocker)
		P.x = np.x
		P.z = np.y
	P.h = ground_height(P.x, P.z)
	var on := ground_kind(P.x, P.z, P.x, P.z)
	if on != P.on and (on == Ground.WATER or on == Ground.DEEP) and P.body.flag("freezes_water") and not P.body.flag("floats"):
		events.append({"type": "froze", "x": P.x, "z": P.z})
	P.on = on
	if on == Ground.GROUND:
		P.safe = Vector2(P.x, P.z)

	_check_zones()
	for e in entities:
		refresh(e)

	var cands: Array = []
	for e in entities:
		if e.hidden or not e.targetable:
			continue
		cands.append({"x": e.x, "z": e.z, "priority": e.priority, "reach": e.reach if e.reach >= 0.0 else 1.6 + e.r, "ref": e})
	# What she faces decides; but standing still with nothing in front of her (a scene just turned
	# her away), the thing beside her is still chosen.
	var in_front := false
	for c in cands:
		var dx: float = c["x"] - P.x
		var dz: float = c["z"] - P.z
		var d := sqrt(dx * dx + dz * dz)
		if d <= c["reach"] and (d <= 0.9 or (dx * P.fx + dz * P.fz) / d >= COS75):
			in_front = true
			break
	var wide := not P.moving and not in_front
	targeting.opt["cone_deg"] = 135.0 if wide else 75.0
	targeting.opt["close_enough"] = 1.6 if wide else 0.9
	var t = targeting.update(dt, P, cands) if control else null
	var was := target
	target = t["ref"] if t != null else null
	if target != null and target != was:
		events.append({"type": "target", "e": target})


func refresh(e: FieldEntity) -> void:
	var f := e.farness()
	if f != e.far:
		var was := e.far
		e.far = f
		if f == 0.0 and was > 0.0:
			events.append({"type": "near", "e": e})
		if f > 0.0 and was == 0.0:
			events.append({"type": "far", "e": e})


## Move her toward (nx, nz), sliding along whatever blocks (Mover). Scenes use it too.
func try_move(nx: float, nz: float) -> void:
	var np := Mover.try_move(Vector2(player.x, player.z), Vector2(nx, nz), blocker)
	player.x = np.x
	player.z = np.y
	player.h = ground_height(player.x, player.z)


func can_stand(x: float, z: float) -> bool:
	return blocker(x, z).is_empty()


## What stops her stepping to (x, z): {}, {"e": thing} or {"wall": true}.
func blocker(x: float, z: float) -> Dictionary:
	var P := player
	if ground.is_valid():
		var g := int(ground.call(x, z, P.x, P.z))
		if g == Ground.WALL:
			return {"wall": true}
		if g == Ground.WATER or g == Ground.DEEP:
			if not (P.body.flag("floats") or P.body.flag("freezes_water")):
				return {"wall": true}
	for e in entities:
		if e.hidden:
			continue
		# deep-far things keep a step away; solid things block; neither may trap her inside
		var r := e.r + 0.55 if e.deep else (e.r + 0.3 if e.solid else 0.0)
		if r <= 0.0:
			continue
		var d := Vector2(x - e.x, z - e.z).length()
		if d < r and d < Vector2(P.x - e.x, P.z - e.z).length():
			return {"e": e}
	for zn in zones:
		if String(zn.get("block", "")) != "" and _in_zone(zn, x, z) and not _in_zone(zn, P.x, P.z):
			return {"wall": true}
	return {}


func _wind_at(x: float, z: float) -> Vector2:
	var w := Vector2.ZERO
	for zn in zones:
		if zn.has("wind") and _in_zone(zn, x, z):
			w += zn["wind"]
	return w


func _check_zones() -> void:
	var P := player
	for zn in zones:
		var now := _in_zone(zn, P.x, P.z)
		if now and not zn["inside"]:
			events.append({"type": "enter", "zone": zn["id"]})
		if not now and zn["inside"]:
			events.append({"type": "leave", "zone": zn["id"]})
		zn["inside"] = now
		# a blocking zone she touches from outside: the story says why she turns back
		var block := String(zn.get("block", ""))
		if block != "" and not now and _near_zone(zn, P.x, P.z, 0.25) and P.moving:
			if not zn["touched"]:
				events.append({"type": "blocked", "zone": zn["id"], "say": block})
			zn["touched"] = true
		elif not _near_zone(zn, P.x, P.z, 1.2):
			zn["touched"] = false


static func _in_zone(z: Dictionary, x: float, zz: float) -> bool:
	if z.has("r"):
		return Vector2(x - z["x"], zz - z["z"]).length() < z["r"]
	return x >= z["x0"] and x <= z["x1"] and zz >= z["z0"] and zz <= z["z1"]


static func _near_zone(z: Dictionary, x: float, zz: float, m: float) -> bool:
	if z.has("r"):
		return Vector2(x - z["x"], zz - z["z"]).length() < z["r"] + m
	return x >= z["x0"] - m and x <= z["x1"] + m and zz >= z["z0"] - m and zz <= z["z1"] + m


# ------------------------------------------------------------------ verbs

## What `verb` with quality k would do to the current target now: {"verb", "k", "target", "reason"}.
## reason "" means it would succeed; "locked" means she has not learned it (the key is hidden).
func check(verb: String, k: String) -> Dictionary:
	var P := player
	var t := target
	var out := {"verb": verb, "k": k, "target": t, "reason": ""}
	if not verbs.get(verb, []).has(k):
		out["reason"] = "locked"
	elif verb == "release":
		out["target"] = null
		out["reason"] = Qualities.can_release(P.holder, k, P.cap)
	elif t == null:
		out["reason"] = Qualities.NONE
	elif t.deep:
		out["reason"] = Qualities.FAR
	elif verb == "take":
		out["reason"] = Qualities.can_take(P.holder, t.holder, k, P.cap)
	else:
		out["reason"] = Qualities.can_give(P.holder, t.holder, k, P.cap)
	return out


## Control scheme (b), "one key does the obvious thing" (prototype planFor; knowledge/12 §1.2):
## carrying extra k, the key gives the extra away (to the target, or releases it with none);
## otherwise it takes k from the target. alt (Shift / long press / trigger): not carrying extra,
## give her own share (to the target, or release it); already carrying extra, take one more.
func plan(k: String, alt: bool = false) -> Dictionary:
	var extra: bool = player.holder.q[k] > player.holder.base[k]
	var verb := ""
	if alt == extra:
		verb = "take"
	else:
		verb = "give" if target != null else "release"
	return check(verb, k)


## 取 / 予 / 放 with quality k on the current target. Returns the ledger event (or a refusal), or
## an empty dictionary when she has not learned the verb (the key is not shown).
func transfer(verb: String, k: String) -> Dictionary:
	var P := player
	var t := target
	if not control or not verbs.get(verb, []).has(k):
		return {}
	var e: Dictionary
	if verb == "release":
		e = L.release(P.holder, k, P.cap)
	elif t == null:
		e = push({"type": "refused", "verb": verb, "k": k, "reason": Qualities.NONE})
	elif t.deep:
		e = push({"type": "refused", "verb": verb, "k": k, "reason": Qualities.FAR, "target": t.holder, "e": t})
	elif verb == "take":
		e = L.take(P.holder, t.holder, k, P.cap)
	else:
		e = L.give(P.holder, t.holder, k, P.cap)
	if e.get("type", "") == "transfer":
		push({"type": "fx", "verb": verb, "k": k, "e": t, "color": Qualities.INFO[k]["color"]})
		refresh(t)
	elif e.get("type", "") == "release":
		push({"type": "fx", "verb": verb, "k": k, "e": null, "color": Qualities.INFO[k]["color"]})
	P.body.refresh(P.holder)
	return e


## Execute what plan() says (scheme b).
func act(k: String, alt: bool = false) -> Dictionary:
	var p := plan(k, alt)
	if p["reason"] == "locked":
		return {}
	return transfer(p["verb"], k)


## The context key: the target's action. Returns what happened as a short label, or "".
func context() -> String:
	if not control or target == null or target.ctx.is_empty():
		return ""
	if target.ctx.has("label") and target.context_label() == "":
		return ""
	var r = (target.ctx["run"] as Callable).call()
	return String(r) if r != null else ""


## What the context key would do now, without doing it (shown on the key and the prompt).
func context_label() -> String:
	return target.context_label() if target != null else ""


## A touch tap on a thing: she turns to it and targets it, if it is within reach.
func pick(e: FieldEntity) -> bool:
	if e == null or e.hidden or not e.targetable:
		return false
	var P := player
	var dx := e.x - P.x
	var dz := e.z - P.z
	var d := sqrt(dx * dx + dz * dz)
	var reach := e.reach if e.reach >= 0.0 else 1.6 + e.r
	if d > reach:
		push({"type": "refused", "verb": "pick", "reason": Qualities.FAR, "e": e})
		return false
	if d > 1e-3:
		P.fx = dx / d
		P.fz = dz / d
	targeting.pick({"x": e.x, "z": e.z, "priority": e.priority, "reach": reach, "ref": e})
	if target != e:
		target = e
		events.append({"type": "target", "e": e})
	return true


## Put her body back to its natural state (the shrine's safety net); the units go to the air.
func restore_body() -> void:
	var h := player.holder
	for k in Qualities.ALL:
		var d: int = h.q[k] - h.base[k]
		h.q[k] = h.base[k]
		L.air[k] += d
	player.body.refresh(h)
	push({"type": "returned"})


func push(e: Dictionary) -> Dictionary:
	events.append(e)
	return e


func drain() -> Array:
	var e := events
	events = []
	return e
