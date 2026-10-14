class_name W3Particles
extends Node3D
## A small CPU particle system for the 3D pixel world (shaders/pixel_particles.gdshader): every
## particle is a camera-facing block of whole native pixels on the texel lattice. Emitters add
## particles with spawn(); update(dt) moves them and uploads one MultiMesh buffer per frame.
## Kinds are plain dictionaries so the scene can add its own (motes, fireflies, smoke, rain...).

const MAX := 2400
const STRIDE := 20      # 12 transform + 4 colour + 4 custom

var mm := MultiMesh.new()
var mi := MultiMeshInstance3D.new()
var parts: Array = []   # each: [pos, vel, life, age, colour, size(w,h), halo, kind, phase, extra]
var buffer := PackedFloat32Array()


func _ready() -> void:
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(0.05, 0.05)
	mm.mesh = q
	mm.instance_count = MAX
	mm.visible_instance_count = 0
	mi.multimesh = mm
	var m := ShaderMaterial.new()
	m.shader = load("res://render3d/shaders/pixel_particles.gdshader")
	m.render_priority = 10
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.extra_cull_margin = 16384.0
	add_child(mi)
	buffer.resize(MAX * STRIDE)


func spawn(pos: Vector3, vel: Vector3, life: float, col: Color, size := Vector2(1, 1), halo := 0.0, kind := 0, extra := 0.0) -> void:
	if parts.size() >= MAX:
		return
	parts.append([pos, vel, life, 0.0, col, size, halo, kind, randf() * TAU, extra])


## step: callable(p: Array, dt) -> void that may change velocity/colour per kind; called per particle
func update(dt: float, step: Callable) -> void:
	var i := 0
	while i < parts.size():
		var p: Array = parts[i]
		p[3] += dt
		if p[3] >= p[2]:
			parts[i] = parts[parts.size() - 1]
			parts.pop_back()
			continue
		if step.is_valid():
			step.call(p, dt)
		p[0] += p[1] * dt
		i += 1
	var n := parts.size()
	for k in n:
		var p: Array = parts[k]
		var o := k * STRIDE
		var pos: Vector3 = p[0]
		buffer[o] = 1.0; buffer[o + 1] = 0.0; buffer[o + 2] = 0.0; buffer[o + 3] = pos.x
		buffer[o + 4] = 0.0; buffer[o + 5] = 1.0; buffer[o + 6] = 0.0; buffer[o + 7] = pos.y
		buffer[o + 8] = 0.0; buffer[o + 9] = 0.0; buffer[o + 10] = 1.0; buffer[o + 11] = pos.z
		var c: Color = p[4]
		buffer[o + 12] = c.r; buffer[o + 13] = c.g; buffer[o + 14] = c.b; buffer[o + 15] = c.a
		var s: Vector2 = p[5]
		buffer[o + 16] = s.x; buffer[o + 17] = s.y; buffer[o + 18] = float(p[7]); buffer[o + 19] = p[6]
	mm.buffer = buffer
	mm.visible_instance_count = n
