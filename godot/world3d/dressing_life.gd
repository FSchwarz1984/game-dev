class_name W3Life
extends Node3D
## Small life that moves (round 5, scene agent; G5R3-5 and the review's "还不够"): the hens walk about
## the yard, peck, scratch and look round, and hurry off when she comes close; the cat asleep on the
## engawa breathes, flicks the tip of its tail and now and then lifts its head (sooner when she comes
## near); two crows of the great camphor: one keeps to its stops on the limbs (perches.crow), turns,
## caws, and flies from stop to stop; the other hops and pecks on the ground by the yard and flies up
## to the tree when she comes near, and back down a while later.
##
## Each creature is one catalog asset whose poses are whole-body meshes on hidden child nodes (the
## catalog's "poses": pose name -> node name; tools/world3d_assets/w3a/props/yard.py), all with
## their origin at the creature's feet, so the renderer's lean-back keeps every pose standing where
## the creature stands; one pose is shown at a time. Something standing above the ground (a crow on
## a limb, the cat on the engawa) leans with what it stands on: its place is moved north by
## lean_k * (height above the ground of what carries it), as the assembly does for hung things.
## Everything runs on the frame's delta (the recordings run at a fixed 30 fps) from a fixed seed.

var terrain: Terrain3D
var lean_k := 0.5206
var catalog := {}
var rng := RandomNumberGenerator.new()
var critters: Array = []          # Critter
var _her: Object
var _looked := false
var _blockers: Array = []         # [Vector3 centre, radius] (the assembly's, when it has them)
var _perches: Array = []          # crow stops on the camphor: Vector3 (world, on the limb)
var _tree_y := 0.0                # the great camphor's base height (what its limbs lean from)
var _ground_spots: Array = []     # open ground by the yard for the crows: Vector3


class Critter:
	var kind := ""                # "hen", "cat", "crow"
	var node: Node3D
	var poses := {}               # pose -> Node3D
	var pose := ""
	var pos := Vector3.ZERO       # the true (upright, un-leaned) place of its feet
	var ref_y := 0.0              # the ground height of what carries it (lean reference)
	var yaw := 0.0
	var home := Vector3.ZERO
	var state := ""
	var t := 0.0                  # time left in the state (s)
	var k := 0                    # a counter for the state (pecks, caws, hops)
	var phase := 0.0
	var target := Vector3.ZERO
	var speed := 0.0
	# flight
	var f_from := Vector3.ZERO
	var f_to := Vector3.ZERO
	var f_ref0 := 0.0
	var f_ref1 := 0.0
	var f_T := 1.0
	var f_s := 0.0
	var perch := -1               # the crow's stop (-1 on the ground)
	var shy_r := 1.2


func build(t: Terrain3D, cat: Dictionary, lk: float, spots: Array) -> void:
	terrain = t
	catalog = cat
	lean_k = lk
	rng.seed = 51207
	for sp in spots:
		var nm: String = sp[0]
		var c := _make(nm)
		if c == null:
			continue
		c.pos = sp[1]
		c.home = sp[1]
		c.yaw = float(sp[2])
		c.ref_y = float(sp[3])
		if nm.begins_with("niwatori"):
			c.kind = "hen"
			c.state = "idle"
			c.t = rng.randf_range(0.2, 1.5)
			c.shy_r = 1.15
		elif nm == "neko":
			c.kind = "cat"
			c.state = "sleep"
			c.t = rng.randf_range(4.0, 12.0)
			c.shy_r = 1.6
		_show(c, "up" if c.kind == "hen" else "sleep")
		critters.append(c)
	_setup_crows()
	for c in critters:
		_place(c)
	print("LIFE hens=%d cats=%d crows=%d" % [_count("hen"), _count("cat"), _count("crow")])


func _count(kind: String) -> int:
	var n := 0
	for c in critters:
		if c.kind == kind:
			n += 1
	return n


func _make(nm: String) -> Critter:
	if not catalog.has(nm):
		return null
	var a: Dictionary = catalog[nm]
	var ps: PackedScene = load(String(a.get("scene", "")))
	if ps == null:
		return null
	var c := Critter.new()
	c.node = ps.instantiate() as Node3D
	add_child(c.node)
	var poses: Dictionary = a.get("poses", {"stand": "Mesh"})
	for pz in poses:
		var n := c.node.get_node_or_null(NodePath(String(poses[pz])))
		if n:
			c.poses[pz] = n
			(n as Node3D).visible = false
	return c


func _show(c: Critter, pz: String) -> void:
	if pz == c.pose or not c.poses.has(pz):
		return
	if c.poses.has(c.pose):
		(c.poses[c.pose] as Node3D).visible = false
	(c.poses[pz] as Node3D).visible = true
	c.pose = pz


func _place(c: Critter) -> void:
	var p := c.pos
	var ry := c.ref_y
	if c.kind == "hen" or (c.kind == "crow" and c.state == "ground"):
		ry = terrain.height_at(p.x, p.z)                  # on the ground (a hop leans like a post)
	p.z -= lean_k * maxf(p.y - ry, 0.0)
	c.node.position = p
	c.node.rotation.y = c.yaw


## The yaw that turns the creature's +x (its front) toward d (x, z).
static func _yaw_to(d: Vector3) -> float:
	return atan2(-d.z, d.x)


# ------------------------------------------------------------------------------------------------
func _setup_crows() -> void:
	if not catalog.has("karasu"):
		return
	var per: Dictionary = terrain.info.get("perches", {})
	for q in per.get("crow", []):
		_perches.append(Vector3(q[0], q[1], q[2]))
	var cm := terrain.marker("camphor")
	_tree_y = terrain.height_at(cm.x, cm.z)
	var lure: Array = per.get("crow_lure", [])
	var centre := Vector3(-23.0, 0.0, 13.25)
	if not lure.is_empty():
		centre = Vector3(lure[0][0], 0.0, lure[0][2])
	for i in 24:
		var a := rng.randf() * TAU
		var r := rng.randf_range(0.3, 3.2)
		var q := centre + Vector3(cos(a) * r, 0.0, sin(a) * r)
		if terrain.walkable(q.x, q.z):
			q.y = terrain.height_at(q.x, q.z)
			_ground_spots.append(q)
	if _perches.is_empty():
		return
	# one on a stop the yard and the graves look up to, one on the ground
	var c1 := _make("karasu")
	if c1:
		c1.kind = "crow"
		c1.perch = mini(2, _perches.size() - 1)
		c1.pos = _perches[c1.perch]
		c1.ref_y = _tree_y
		c1.yaw = PI
		c1.state = "perch"
		c1.t = rng.randf_range(2.0, 5.0)
		c1.shy_r = 0.0
		_show(c1, "stand")
		critters.append(c1)
	if not _ground_spots.is_empty():
		var c2 := _make("karasu")
		if c2:
			c2.kind = "crow"
			c2.pos = _ground_spots[0]
			c2.home = c2.pos
			c2.ref_y = c2.pos.y
			c2.yaw = 0.4
			c2.state = "ground"
			c2.t = rng.randf_range(0.5, 2.0)
			c2.shy_r = 2.4
			_show(c2, "stand")
			critters.append(c2)


# ------------------------------------------------------------------------------------------------
func _process(delta: float) -> void:
	if not _looked:
		_looked = true
		var sc := get_tree().current_scene
		if sc:
			var h: Variant = sc.get("her")
			if h is Object and is_instance_valid(h) and (h as Object).get("pos") != null:
				_her = h
			var b: Variant = sc.get("blockers")
			if b is Array:
				_blockers = b
	var her_p := Vector3(1e6, 0.0, 1e6)
	if _her and is_instance_valid(_her):
		her_p = _her.get("pos")
	delta = minf(delta, 0.1)
	for c in critters:
		match c.kind:
			"hen":
				_hen(c, delta, her_p)
			"cat":
				_cat(c, delta, her_p)
			"crow":
				_crow(c, delta, her_p)
		_place(c)


func _flat_dist(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


func _free(q: Vector3, r: float) -> bool:
	if not terrain.walkable(q.x, q.z):
		return false
	for bl in _blockers:
		var bc: Vector3 = bl[0]
		if Vector2(q.x - bc.x, q.z - bc.z).length() < float(bl[1]) + r:
			return false
	return true


# ---- hens --------------------------------------------------------------------------------------
func _hen(c: Critter, dt: float, her_p: Vector3) -> void:
	c.t -= dt
	var near := _flat_dist(c.pos, her_p) < c.shy_r and absf(her_p.y - c.pos.y) < 1.0
	if near and c.state != "flee":
		# away from her, a little to one side, quickly
		var away := Vector3(c.pos.x - her_p.x, 0.0, c.pos.z - her_p.z).normalized()
		away = away.rotated(Vector3.UP, rng.randf_range(-0.6, 0.6))
		for i in 6:
			var q := c.pos + away * rng.randf_range(1.2, 1.9)
			if _free(q, 0.12):
				c.target = q
				c.state = "flee"
				c.speed = 1.15
				c.phase = 0.0
				break
			away = away.rotated(Vector3.UP, 0.7)
	match c.state:
		"idle":
			if c.t <= 0.0:
				var r := rng.randf()
				if r < 0.45:
					_hen_walk(c)
				elif r < 0.8:
					c.state = "peck"
					c.k = rng.randi_range(2, 4)
					c.t = 0.0
				elif r < 0.9:
					c.state = "scratch"
					c.k = 2
					c.t = 0.0
				else:
					_show(c, "look")
					c.t = rng.randf_range(0.6, 1.6)
			elif c.pose == "up" and rng.randf() < dt * 0.4:
				c.yaw += rng.randf_range(-0.8, 0.8)          # a glance about
		"walk", "flee":
			var d := Vector3(c.target.x - c.pos.x, 0.0, c.target.z - c.pos.z)
			var L := d.length()
			if L < 0.04:
				c.state = "idle" if c.state == "flee" else ("peck" if rng.randf() < 0.7 else "idle")
				c.k = rng.randi_range(1, 3)
				c.t = rng.randf_range(0.3, 1.2)
				_show(c, "up")
				return
			var step := minf(c.speed * dt, L)
			var nq := c.pos + d / L * step
			if not _free(nq, 0.1):
				c.state = "idle"
				c.t = rng.randf_range(0.3, 0.8)
				_show(c, "up")
				return
			c.yaw = lerp_angle(c.yaw, _yaw_to(d), minf(1.0, dt * 10.0))
			c.pos = Vector3(nq.x, terrain.height_at(nq.x, nq.z), nq.z)
			# the stride: up / step, a quick head-bob (a hen's walk)
			c.phase += dt * (6.0 if c.state == "walk" else 10.0)
			_show(c, "step" if fmod(c.phase, 2.0) < 1.0 else "up")
			W3Grass.push_at(c.pos, 0.16)
		"peck":
			if c.t <= 0.0:
				if c.pose == "peck":
					_show(c, "up")
					c.t = rng.randf_range(0.18, 0.4)
					c.k -= 1
					if c.k <= 0:
						c.state = "idle"
						c.t = rng.randf_range(0.4, 1.8)
				else:
					_show(c, "peck")
					c.t = rng.randf_range(0.12, 0.2)
		"scratch":
			# two scrapes backward with a foot, then a look at what turned up
			if c.t <= 0.0:
				if c.k <= 0:
					c.state = "peck"
					c.k = rng.randi_range(1, 3)
					c.t = 0.1
					_show(c, "up")
					return
				var back := Vector3(-cos(c.yaw), 0.0, sin(c.yaw)) * 0.05
				var nq2 := c.pos + back
				if _free(nq2, 0.1):
					c.pos = Vector3(nq2.x, terrain.height_at(nq2.x, nq2.z), nq2.z)
				_show(c, "step" if c.pose != "step" else "up")
				c.t = 0.16
				if c.pose == "up":
					c.k -= 1


func _hen_walk(c: Critter) -> void:
	for i in 8:
		var a := rng.randf() * TAU
		var r := rng.randf_range(0.3, 1.0)
		var q := c.pos + Vector3(cos(a) * r, 0.0, sin(a) * r)
		if _flat_dist(q, c.home) > 1.7:
			q = c.home + (q - c.home).normalized() * 1.2
		if _free(q, 0.12):
			c.target = q
			c.state = "walk"
			c.speed = rng.randf_range(0.32, 0.45)
			c.phase = 0.0
			return
	c.t = 0.5


# ---- the cat -----------------------------------------------------------------------------------
func _cat(c: Critter, dt: float, her_p: Vector3) -> void:
	c.t -= dt
	c.phase += dt
	var near := _flat_dist(c.pos, her_p) < c.shy_r
	match c.state:
		"sleep":
			# breathing: up a pixel and down, slow
			_show(c, "breath" if fmod(c.phase, 3.4) < 1.5 else "sleep")
			if near:
				c.state = "awake"
				c.t = rng.randf_range(2.5, 5.0)
				_show(c, "awake")
			elif c.t <= 0.0:
				if rng.randf() < 0.75:
					c.state = "flick"
					c.t = 0.32
					_show(c, "tail")
				else:
					c.state = "awake"
					c.t = rng.randf_range(2.0, 4.0)
					_show(c, "awake")
		"flick":
			if c.t <= 0.0:
				c.state = "sleep"
				c.t = rng.randf_range(6.0, 16.0)
				_show(c, "sleep")
		"awake":
			if c.t <= 0.0 and not near:
				c.state = "sleep"
				c.t = rng.randf_range(8.0, 20.0)
				_show(c, "sleep")
			elif c.t <= 0.0:
				c.t = 1.0


# ---- crows -------------------------------------------------------------------------------------
func _crow(c: Critter, dt: float, her_p: Vector3) -> void:
	c.t -= dt
	match c.state:
		"perch":
			_crow_idle(c, dt)
			if c.t <= 0.0:
				c.k += 1
				if c.k > rng.randi_range(5, 9):
					c.k = 0
					_crow_leave_perch(c)
				else:
					c.t = rng.randf_range(1.5, 4.0)
		"ground":
			if _flat_dist(c.pos, her_p) < c.shy_r and absf(her_p.y - c.pos.y) < 2.0:
				# up to the tree: the nearest stop she is not under
				var best := -1
				var bd := 1e9
				for i in _perches.size():
					var q: Vector3 = _perches[i]
					var d := _flat_dist(q, c.pos)
					if _flat_dist(q, her_p) > 2.5 and d < bd:
						bd = d
						best = i
				if best >= 0:
					_crow_fly(c, _perches[best], _tree_y, best)
					return
			_crow_ground(c, dt)
		"fly":
			c.f_s = minf(c.f_s + dt / c.f_T, 1.0)
			var s := c.f_s
			var e := s * s * (3.0 - 2.0 * s)
			var p := c.f_from.lerp(c.f_to, e)
			var arc := 0.6 + 0.1 * c.f_from.distance_to(c.f_to)
			p.y += arc * 4.0 * e * (1.0 - e)
			c.pos = p
			c.ref_y = lerpf(c.f_ref0, c.f_ref1, e)
			c.phase += dt
			if s < 0.7:
				_show(c, "fly_a" if fmod(c.phase, 0.22) < 0.11 else "fly_b")
			else:
				_show(c, "fly_a")                           # wings up, braking to land
			if s >= 1.0:
				c.pos = c.f_to
				c.ref_y = c.f_ref1
				_show(c, "stand")
				c.k = 0
				if c.perch >= 0:
					c.state = "perch"
					c.t = rng.randf_range(2.0, 4.0)
				else:
					c.state = "ground"
					c.t = rng.randf_range(0.6, 1.5)


func _crow_idle(c: Critter, dt: float) -> void:
	# on a limb: turn about, caw a few times now and then
	if c.state == "perch" and c.t <= 0.0:
		var r := rng.randf()
		if r < 0.35:
			# side on mostly (the silhouette reads), now and then toward us
			c.yaw = [0.0, PI, -PI * 0.5][rng.randi() % 3] + rng.randf_range(-0.6, 0.6)
		elif r < 0.6:
			c.phase = 0.0
			c.speed = float(rng.randi_range(2, 3))         # caws
	if c.speed > 0.0:
		c.phase += dt
		var n := int(c.phase / 0.5)
		if n >= int(c.speed):
			c.speed = 0.0
			_show(c, "stand")
		else:
			_show(c, "caw" if fmod(c.phase, 0.5) < 0.24 else "stand")


func _crow_leave_perch(c: Critter) -> void:
	# to another stop, or down to the ground by the yard
	if not _ground_spots.is_empty() and rng.randf() < 0.35:
		var q: Vector3 = _ground_spots[rng.randi() % _ground_spots.size()]
		_crow_fly(c, q, q.y, -1)
		return
	var i := rng.randi() % _perches.size()
	if i == c.perch:
		i = (i + 1) % _perches.size()
	_crow_fly(c, _perches[i], _tree_y, i)


func _crow_fly(c: Critter, to: Vector3, ref1: float, perch: int) -> void:
	c.f_from = c.pos
	c.f_to = to
	c.f_ref0 = c.ref_y
	c.f_ref1 = ref1
	c.f_T = clampf(c.pos.distance_to(to) / 4.2, 0.9, 4.0)
	c.f_s = 0.0
	c.perch = perch
	c.state = "fly"
	c.phase = 0.0
	c.speed = 0.0
	c.yaw = _yaw_to(to - c.pos)


func _crow_ground(c: Critter, dt: float) -> void:
	# hops (both feet), pecks, looks about; after a while back up to the tree
	if c.state != "ground":
		return
	if c.speed > 0.0:
		# in a hop: crouch, up, land
		c.phase += dt
		var hop_T := 0.3
		var s := clampf(c.phase / hop_T, 0.0, 1.0)
		var dir := Vector3(cos(c.yaw), 0.0, -sin(c.yaw))
		var q := c.target + dir * 0.17 * s
		q.y = terrain.height_at(q.x, q.z) + 0.07 * sin(PI * s)
		c.pos = q
		_show(c, "hop" if s > 0.12 and s < 0.88 else "stand")
		if s >= 1.0:
			c.speed = 0.0
			c.pos.y = terrain.height_at(c.pos.x, c.pos.z)
			_show(c, "stand")
			W3Grass.push_at(c.pos, 0.12)
		return
	if c.t > 0.0:
		return
	var r := rng.randf()
	if r < 0.4:
		# a hop or two forward (turning first if the way is not free)
		var dir2 := Vector3(cos(c.yaw), 0.0, -sin(c.yaw))
		if not _free(c.pos + dir2 * 0.3, 0.1) or _flat_dist(c.pos, c.home) > 3.0 and rng.randf() < 0.5:
			c.yaw = _yaw_to(c.home - c.pos) + rng.randf_range(-0.8, 0.8)
			c.t = 0.25
			return
		c.target = c.pos
		c.phase = 0.0
		c.speed = 1.0
		c.t = rng.randf_range(0.05, 0.5)
	elif r < 0.7:
		_show(c, "peck" if c.pose != "peck" else "stand")
		c.t = 0.16 if c.pose == "peck" else 0.3
	elif r < 0.82:
		c.yaw += rng.randf_range(-1.6, 1.6)
		_show(c, "stand")
		c.t = rng.randf_range(0.4, 1.2)
	elif r < 0.9:
		c.speed = 0.0
		_show(c, "caw")
		c.t = 0.25
	else:
		c.k += 1
		if c.k > 14 and not _perches.is_empty():
			c.k = 0
			var i := rng.randi() % _perches.size()
			_crow_fly(c, _perches[i], _tree_y, i)
			return
		_show(c, "stand")
		c.t = rng.randf_range(0.6, 2.0)
