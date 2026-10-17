class_name W3Lamps
extends Node
## Lanterns and fires of the 3D pixel renderer (docs/knowledge/21-3d-pixel-render.md §5, lamps).
## Round 4 (Forward+, decision-log G5R2-1): every lamp is a real OmniLight3D in the world (`world`),
## so its light falls off smoothly (no rings), reaches the volumetric fog (a soft halo in the air)
## and the VoxelGI bounce. The lamps are also kept in a small data texture (the global `w3_lamps`,
## 2 rows: position and reach; colour times energy and the lit amount) for the view from the lookout,
## which is a world of its own and lights its home lanterns in its shaders (w3_lamp_light).
## Lamps light up one after another when the evening comes (or go out at dawn), each over ~1.2 s.

const MAX := 64

var enabled := true            # false: no lamp light at all (debugging, --nolamps)
var world: Node3D              # where the OmniLight3D lamps live (the sample's world root)
var lamps: Array = []          # {pos, reach, col (Color, linear, times energy), on, want, delay, flicker, light}
## the engine lights: energy and range for a lamp of (reach, energy) as dressing gives them
var light_gain := 1.6
var light_range := 1.35
const FOG_ENERGY := 1.4         # each lamp's glow in the air (its share of the volumetric fog)
## (G5R3-27) with a perspective camera a lamp the camera cannot see (a lantern under an eave, behind a
## crown) loses its glow in the air with it: W3LampOcclusion, set up when `view` is given
var view: PixelView3D
var ground: Callable            # ground height at (x, z): where hung lamps lean from
var occlusion: W3LampOcclusion
var _img := Image.create(MAX, 2, false, Image.FORMAT_RGBAF)
var _tex: ImageTexture
var _t := 0.0


func _ready() -> void:
	_tex = ImageTexture.create_from_image(_img)
	RenderingServer.global_shader_parameter_set("w3_lamps", _tex)
	RenderingServer.global_shader_parameter_set("w3_lamp_n", 0.0)


## A lamp at a world point. reach: metres to the end of its light; col: its colour (linear);
## energy: the core's strength (1 lights a mid-grey ground to about L* 60). flicker: 0 still .. 1 a
## live flame.
func add(pos: Vector3, reach: float, col: Color, energy: float, flicker := 0.15, manual := false) -> int:
	lamps.append({"pos": pos, "reach": reach, "col": Color(col.r * energy, col.g * energy, col.b * energy),
		"on": 0.0, "want": 0.0, "delay": 0.0, "flicker": flicker, "phase": float(lamps.size()) * 1.618,
		"manual": manual})
	return lamps.size() - 1


## A lamp that something else drives (a wandering will-o'-wisp): its place and how lit it is.
func set_lamp(i: int, pos: Vector3, on: float) -> void:
	var l: Dictionary = lamps[i]
	l["pos"] = pos
	l["on"] = on
	l["want"] = on


## Turn the lamps on (or off). stagger > 0: one after another, that many seconds apart, each fading
## in over `fade` seconds; instant = true sets them at once (a still, a jump in time).
func set_on(on: bool, instant := false, stagger := 0.18, fade := 1.2) -> void:
	var order := range(lamps.size())
	for i in order:
		var l: Dictionary = lamps[i]
		if l["manual"]:
			continue
		var w := 1.0 if on else 0.0
		if instant:
			l["on"] = w
			l["want"] = w
			l["delay"] = 0.0
		elif absf(float(l["want"]) - w) > 0.01:
			l["want"] = w
			l["delay"] = float(i) * stagger
		l["fade"] = fade


func _make_light(l: Dictionary) -> OmniLight3D:
	var o := OmniLight3D.new()
	o.name = "Lamp%d" % lamps.find(l)
	var c: Color = l["col"]
	var e := maxf(maxf(c.r, c.g), c.b)
	o.light_color = Color(c.r / e, c.g / e, c.b / e) if e > 0.0 else Color(1, 0.7, 0.4)
	o.set_meta("energy", e)
	o.omni_range = float(l["reach"]) * light_range
	# a soft, long falloff: a warm pool that fades into the dark with no edge
	o.omni_attenuation = 1.6
	o.light_specular = 0.0
	o.light_volumetric_fog_energy = FOG_ENERGY
	o.shadow_enabled = false
	o.position = l["pos"]
	o.visible = false
	world.add_child(o)
	return o


func update(dt: float) -> void:
	_t += dt
	var n := 0
	_update_occlusion(dt)
	if not enabled:
		RenderingServer.global_shader_parameter_set("w3_lamp_n", 0.0)
		for l in lamps:
			if l.get("light"):
				(l["light"] as OmniLight3D).visible = false
		return
	for l in lamps:
		if l["manual"]:
			pass
		elif float(l["delay"]) > 0.0:
			l["delay"] = float(l["delay"]) - dt
		else:
			var f := float(l.get("fade", 1.2))
			l["on"] = move_toward(float(l["on"]), float(l["want"]), dt / maxf(f, 0.01))
		var on := float(l["on"])
		# a live flame breathes a little
		var fl := 1.0 + float(l["flicker"]) * (0.06 * sin(_t * 7.3 + float(l["phase"])) + 0.04 * sin(_t * 13.1 + float(l["phase"]) * 2.0))
		if world != null:
			if l.get("light") == null:
				l["light"] = _make_light(l)
			var o: OmniLight3D = l["light"]
			o.visible = on > 0.001
			o.position = l["pos"]
			o.light_energy = float(o.get_meta("energy")) * light_gain * on * fl
			o.light_volumetric_fog_energy = FOG_ENERGY * float(l.get("vis", 1.0))
		if on <= 0.001 or n >= MAX:
			continue
		var p: Vector3 = l["pos"]
		var c: Color = l["col"]
		var k := on * fl
		_img.set_pixel(n, 0, Color(p.x, p.y, p.z, float(l["reach"])))
		_img.set_pixel(n, 1, Color(c.r * k, c.g * k, c.b * k, on))
		n += 1
	_tex.update(_img)
	RenderingServer.global_shader_parameter_set("w3_lamp_n", float(n))


## How much of each lamp the camera sees, eased (W3LampOcclusion reads it from the depth buffer a
## frame or two late; a glow fades out over a quarter of a second when its lamp goes behind something).
## The orthographic camera keeps every glow as it always was.
func _update_occlusion(dt: float) -> void:
	if view == null or not view.is_perspective() or lamps.is_empty():
		for l in lamps:
			l["vis"] = 1.0
		if occlusion:
			occlusion.set_lamps(PackedFloat32Array(), 0, Vector2.ONE, false, 1.0, 2.0)
		return
	if occlusion == null:
		occlusion = W3LampOcclusion.new()
		var comp := Compositor.new()
		comp.compositor_effects = [occlusion]
		view.cam.compositor = comp
	var cam := view.cam
	var size := Vector2(view.vp.size)
	var back := view.cam_back()
	var k := view.lean_k()
	var data := PackedFloat32Array()
	data.resize(mini(lamps.size(), W3LampOcclusion.MAX) * 4)
	for i in mini(lamps.size(), W3LampOcclusion.MAX):
		var l: Dictionary = lamps[i]
		if float(l["on"]) <= 0.001:
			continue
		# (the lamp where the lantern is drawn: hung things lean back with what they hang from)
		var p: Vector3 = l["pos"]
		if ground.is_valid():
			p.z -= k * maxf(p.y - float(ground.call(p.x, p.z)), 0.0)
		if cam.is_position_behind(p):
			continue
		var s := cam.unproject_position(p)
		if s.x < 0.0 or s.y < 0.0 or s.x >= size.x or s.y >= size.y:
			continue
		data[i * 4] = s.x
		data[i * 4 + 1] = s.y
		data[i * 4 + 2] = (cam.position - p).dot(back)
		data[i * 4 + 3] = 1.0
	occlusion.set_lamps(data, mini(lamps.size(), W3LampOcclusion.MAX), size, false, cam.near, cam.far)
	var vis := occlusion.visibility()
	for i in lamps.size():
		var want := vis[i] if i < vis.size() and i < W3LampOcclusion.MAX else 1.0
		lamps[i]["vis"] = move_toward(float(lamps[i].get("vis", 1.0)), want, dt * 4.0)
