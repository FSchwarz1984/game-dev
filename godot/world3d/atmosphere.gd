class_name W3Atmosphere
extends Node3D
## Life in the air of the art sample: motes drifting in the light by day, fireflies over the grass
## and the water at night, will-o'-wisps (鬼火) by the nameless graves at night, light shafts under
## the great camphor and old leaves coming down from its crown, rain. Driven by the time of day
## (W3Env) and her position (spawn near view).

var env: W3Env
var terrain: Terrain3D
var particles := W3Particles.new()
var shafts := MultiMeshInstance3D.new()
var wisps: Array = []           # [{pos, home, phase, light}]
var focus := Vector3.ZERO
var rng := RandomNumberGenerator.new()
var _mote_acc := 0.0
var _fly_acc := 0.0
var _rain_acc := 0.0
var glints: Array = []          # [position, phase] from the dressing: small things that catch the light
var lamps: W3Lamps              # the renderer's lamps (the wisps light the graves a cold blue)
var camphor := Vector3.INF      # the great camphor's foot: old leaves come down under its crown
const CAMPHOR_REACH := 15.5     # m from the trunk where its leaves fall
var _leaf_acc := 0.0
var _leaf_light := 1.0          # daylight on the leaves (they are unlit pixels)
# the camphor's old leaves (it sheds them through the year): red, rust, ochre, a few still green
# (sRGB as painted; turned linear for the unlit particle pixels)
const LEAF_COLS := [Color("#c4643a"), Color("#d08a3c"), Color("#d6b04e"), Color("#a84a32"), Color("#8a9a4a")]


func setup(e: W3Env, t: Terrain3D) -> void:
	env = e
	terrain = t
	rng.seed = 99
	add_child(particles)
	_build_shafts()
	_build_wisps()


func _build_shafts() -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	q.center_offset = Vector3(0.5, 0.5, 0)
	mm.mesh = q
	# Shafts fall where the light gets through a crown's rim: around the great camphor, and under the
	# broadleaf trees, maples and pines of the woods and the spur (a crown, a little off its trunk).
	# Each is a ground point; the shader raises the ribbon toward the sun whatever the hour.
	var pts := []
	var cus := []
	for i in 9:
		var a := TAU * (float(i) + rng.randf_range(0.15, 0.85)) / 9.0
		var r := rng.randf_range(9.0, 15.0)
		pts.append(Vector2(cos(a) * r, sin(a) * r * 0.9))
		cus.append(Color(rng.randf_range(9.0, 14.0), [8.0, 11.0, 15.0, 20.0][i % 4], rng.randf_range(0.6, 1.0), rng.randf() * TAU))
	var taken: Array[Vector2] = []
	for p in terrain.info.get("placements", []):
		var kind := String(p["kind"])
		if not kind in ["broadleaf", "beech", "maple", "pine", "persimmon"]:
			continue
		var at := Vector2(float(p["x"]), float(p["z"]))
		var near := false
		for seen in taken:
			if seen.distance_to(at) < 7.5:
				near = true
				break
		if near or taken.size() >= 22:
			continue
		taken.append(at)
		var a2 := rng.randf_range(0.0, TAU)
		var off := Vector2(cos(a2), sin(a2)) * rng.randf_range(1.6, 3.2) * float(p.get("scale", 1.0))
		pts.append(at + off)
		cus.append(Color(rng.randf_range(5.0, 9.0), [6.0, 9.0, 12.0][taken.size() % 3], rng.randf_range(0.45, 0.85), rng.randf() * TAU))
	mm.instance_count = pts.size()
	for i in pts.size():
		var p: Vector2 = pts[i]
		var y := terrain.height_at(p.x, p.y)
		mm.set_instance_transform(i, Transform3D(Basis(), Vector3(p.x, y, p.y)))
		mm.set_instance_custom_data(i, cus[i])
	shafts.multimesh = mm
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/light_shaft.gdshader")
	m.render_priority = 5
	shafts.material_override = m
	shafts.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	shafts.extra_cull_margin = 64.0
	add_child(shafts)


func _build_wisps() -> void:
	var g := terrain.marker("graves")
	for i in 3:
		var home := g + Vector3(-4.0 + i * 3.6, 1.2 + i * 0.2, 0.6 + (i % 2) * 0.7)
		var li := -1
		if lamps:
			li = lamps.add(home, 1.9, Color(0.55, 0.85, 1.0), 0.55, 0.0, true)
		wisps.append({"pos": home, "home": home, "phase": rng.randf() * TAU, "lamp": li})


func _step(p: Array, dt: float) -> void:
	var kind: int = p[7]
	var t: float = p[3]
	var life: float = p[2]
	var c: Color = p[4]
	if kind == 1:        # mote: slow wander, twinkle
		p[1] = Vector3(sin(t * 0.9 + p[8]) * 0.08 + env.wind * 0.05, sin(t * 0.6 + p[8] * 2.0) * 0.05 + 0.02, cos(t * 0.7 + p[8]) * 0.05)
		c.a = clampf(minf(t / 1.2, (life - t) / 1.2), 0.0, 1.0) * (0.55 + 0.45 * sin(t * 2.3 + p[8])) * p[9]
	elif kind == 2:      # firefly: lazy loops, slow blink
		p[1] = Vector3(sin(t * 0.8 + p[8]) * 0.35, sin(t * 1.3 + p[8] * 1.7) * 0.18, cos(t * 0.6 + p[8] * 0.5) * 0.3)
		var blink := sin(t * 1.6 + p[8] * 3.0)
		c.a = clampf(minf(t / 0.8, (life - t) / 0.8), 0.0, 1.0) * (1.0 if blink > 0.1 else 0.0)
	elif kind == 3:      # wisp tail: rises and fades
		c.a = clampf(1.0 - t / life, 0.0, 1.0) * 0.8
	elif kind == 6:      # glint: a short sparkle, up and down once
		c.a = sin(clampf(t / life, 0.0, 1.0) * PI)
	elif kind == 7:      # a falling leaf: it sways down, turning (edge-on it is one pixel, flat two)
		var gy := terrain.height_at(p[0].x, p[0].z)
		var ph: float = p[8]
		if p[0].y > gy + 0.02:
			p[1] = Vector3(sin(t * 2.1 + ph) * 0.6 + env.wind * 0.12, -0.8 - 0.25 * sin(t * 4.2 + ph), cos(t * 1.7 + ph) * 0.15)
			var turn := sin(t * 4.4 + ph * 3.0)
			p[5] = Vector2(3, 2) if turn > 0.35 else (Vector2(2, 1) if turn > -0.55 else Vector2(1, 1))
			# the lit face now and then (the shade of the crown otherwise)
			var lit := 1.0 if turn > 0.75 else 0.0
			var base: Color = (LEAF_COLS[int(float(p[9]) * LEAF_COLS.size()) % LEAF_COLS.size()] as Color).srgb_to_linear()
			var k := (0.62 + 0.38 * lit) * _leaf_light
			c = Color(base.r * k, base.g * k, base.b * k, c.a)
		else:
			# on the ground: it lies a while, then the litter takes it
			p[1] = Vector3.ZERO
			p[0].y = gy + 0.02
			p[5] = Vector2(2, 1)
			if float(p[2]) - t > 3.0:
				p[2] = t + 3.0
		c.a = clampf((float(p[2]) - t) / 1.0, 0.0, 1.0) * clampf(t / 0.4, 0.0, 1.0)
	elif kind == 4:      # rain: falls; dies on the ground
		var gy := terrain.height_at(p[0].x, p[0].z)
		if p[0].y <= gy:
			p[3] = life
			if rng.randf() < 0.35:
				particles.spawn(Vector3(p[0].x, gy + 0.02, p[0].z), Vector3.ZERO, 0.12, Color(0.75, 0.8, 0.85, 0.7), Vector2(2, 1), 0.0, 5)
	p[4] = c


func update(dt: float, at: Vector3) -> void:
	focus = at
	var night := clampf(1.0 - absf(env.hours - 12.0) / 7.0, 0.0, 1.0)
	var dark := 1.0 - night
	var is_night := env.hours < 5.2 or env.hours > 19.2
	var day := not is_night and env.rain < 0.4
	var lowsun := clampf(1.0 - absf(env.hours - 12.0) / 6.5, 0.0, 1.0)
	# motes in the warm light (by day, under the trees)
	if day:
		_mote_acc += dt * 10.0
		while _mote_acc > 1.0:
			_mote_acc -= 1.0
			var p := at + Vector3(rng.randf_range(-12, 12), 0, rng.randf_range(-9, 7))
			p.y = terrain.height_at(p.x, p.z) + rng.randf_range(0.6, 3.2)
			var warm := Color(1.0, 0.92, 0.7) * (0.9 + 0.3 * (1.0 - lowsun))
			warm.a = 1.0
			particles.spawn(p, Vector3.ZERO, rng.randf_range(4.0, 8.0), warm, Vector2(1, 1), 0.0, 1, rng.randf_range(0.45, 0.85))
	# old leaves coming down under the great camphor (by day). Each starts just above the top of the
	# view, so it drifts in from the crown overhead and never appears out of nothing: a point's height
	# on screen is 0.574 m per metre of height (particles do not lean) less 0.819 m per metre south
	# of the camera's focus (her chest, 0.47 m north of her feet), and the top edge is 6.75 m up
	_leaf_light = clampf(1.0 - maxf(absf(env.hours - 12.0) - 5.0, 0.0) / 2.5, 0.45, 1.0) * (1.0 - 0.3 * env.rain)
	if camphor != Vector3.INF and not is_night:
		var dc := Vector2(at.x - camphor.x, at.z - camphor.z).length()
		if dc < CAMPHOR_REACH + 8.0:
			_leaf_acc += dt * 2.0
			while _leaf_acc > 1.0:
				_leaf_acc -= 1.0
				var lp := at + Vector3(rng.randf_range(-12.0, 12.0), 0, rng.randf_range(-5.0, 4.0))
				if Vector2(lp.x - camphor.x, lp.z - camphor.z).length() > CAMPHOR_REACH:
					continue
				var dz := lp.z - at.z
				lp.y = at.y + 0.9 + (6.9 + 0.819 * (dz + 0.47)) / 0.574 + rng.randf_range(0.0, 1.5)
				if lp.y < terrain.height_at(lp.x, lp.z) + 4.0:
					continue
				particles.spawn(lp, Vector3.ZERO, 45.0, Color(0.6, 0.3, 0.15, 1.0), Vector2(2, 1), 0.0, 7, rng.randf())
	# fireflies at night over grass and water
	if is_night and env.rain < 0.3:
		_fly_acc += dt * 7.0
		while _fly_acc > 1.0:
			_fly_acc -= 1.0
			var p := at + Vector3(rng.randf_range(-12, 12), 0, rng.randf_range(-9, 7))
			var w := terrain.water_at(p.x, p.z)
			if not terrain.walkable(p.x, p.z) and int(w["kind"]) == 0:
				continue
			p.y = terrain.height_at(p.x, p.z) + rng.randf_range(0.3, 1.6)
			particles.spawn(p, Vector3.ZERO, rng.randf_range(5.0, 10.0), Color(0.8, 1.0, 0.45) * 2.4, Vector2(1, 1), 1.0, 2)
	# rain: streaks falling past the camera, splashes where they land
	if env.rain > 0.05:
		_rain_acc += dt * 260.0 * env.rain
		while _rain_acc > 1.0:
			_rain_acc -= 1.0
			var p := at + Vector3(rng.randf_range(-13, 13), 0, rng.randf_range(-9, 9))
			var gy := terrain.height_at(p.x, p.z)
			p.y = gy + rng.randf_range(2.0, 7.0)
			var c := Color(0.72, 0.78, 0.86, 0.55)
			particles.spawn(p, Vector3(env.wind * 0.6, -11.0, 0.8), 1.2, c, Vector2(1, 4), 0.0, 4)
	# glints: coins in the offering box catch the light now and then (fainter by lantern light)
	for gl in glints:
		gl[1] = float(gl[1]) - dt
		if float(gl[1]) <= 0.0:
			gl[1] = rng.randf_range(2.2, 4.0)
			var gp: Vector3 = gl[0]
			var k := 1.7 if not is_night else 1.1
			var gc := Color(1.0, 0.9, 0.62) * k
			gc.a = 1.0
			particles.spawn(gp + Vector3(rng.randf_range(-0.12, 0.12), 0.0, rng.randf_range(-0.05, 0.05)), Vector3.ZERO, 0.45, gc, Vector2(1, 1), 1.0, 6)
	# will-o'-wisps by the graves at night
	for wd in wisps:
		var li: int = wd["lamp"]
		if is_night:
			wd["phase"] = float(wd["phase"]) + dt
			var ph: float = wd["phase"]
			var home: Vector3 = wd["home"]
			var pos := home + Vector3(sin(ph * 0.37) * 0.9, sin(ph * 0.9) * 0.25, cos(ph * 0.29) * 0.6)
			wd["pos"] = pos
			if li >= 0:
				lamps.set_lamp(li, pos, 0.85 + 0.15 * sin(ph * 7.0))
			particles.spawn(pos, Vector3(0, 0.0, 0), 0.06, Color(0.7, 0.95, 1.0) * 2.2, Vector2(2, 3), 1.0, 0)
			if rng.randf() < dt * 14.0:
				particles.spawn(pos + Vector3(rng.randf_range(-0.05, 0.05), 0.1, 0), Vector3(rng.randf_range(-0.1, 0.1), 0.55, 0), rng.randf_range(0.4, 0.8), Color(0.55, 0.85, 1.0) * 1.6, Vector2(1, 1), 0.0, 3)
		elif li >= 0:
			lamps.set_lamp(li, wd["pos"], 0.0)
	particles.update(dt, _step)
