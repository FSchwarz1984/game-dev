class_name VistaPoints
extends MultiMeshInstance2D
## Many small lights in one draw call: a MultiMesh of unit quads whose instances carry data instead
## of transforms. The shaders (skip_vertex_transform) read 6 floats from the instance matrix
## (MODEL_MATRIX[0].xy, [1].xy, [2].xy; the origin stays 0 so MODEL_MATRIX[3].xy is the node's
## offset), 4 from the instance colour and 4 from the custom data, and place each quad themselves,
## on whole native pixels.
##   var p := VistaPoints.new(n, shader); p.put(i, [a, b, c, d, e, f], Color(...), Color(...)); p.commit()

const STRIDE := 16

var count := 0
var buf := PackedFloat32Array()


func _init(n: int = 0, shader: Shader = null) -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_2D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = _unit_quad()
	# the quads are placed by the shader: never cull by the (meaningless) instance transforms
	mm.custom_aabb = AABB(Vector3(-8192, -8192, -1), Vector3(16384, 16384, 2))
	multimesh = mm
	if shader != null:
		var m := ShaderMaterial.new()
		m.shader = shader
		material = m
	resize(n)


static func _unit_quad() -> ArrayMesh:
	var a := []
	a.resize(Mesh.ARRAY_MAX)
	a[Mesh.ARRAY_VERTEX] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	a[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	a[Mesh.ARRAY_COLOR] = PackedColorArray([Color.WHITE, Color.WHITE, Color.WHITE, Color.WHITE])
	a[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, a)
	return mesh


func resize(n: int) -> void:
	count = n
	multimesh.instance_count = n
	multimesh.visible_instance_count = n
	buf.resize(n * STRIDE)
	buf.fill(0.0)


## Instance i: m = up to 6 floats (matrix), col and cus 4 floats each.
func put(i: int, m: Array, col: Color = Color(0, 0, 0, 0), cus: Color = Color(0, 0, 0, 0)) -> void:
	var o := i * STRIDE
	# buffer layout per 2D instance: x.x y.x pad origin.x | x.y y.y pad origin.y | colour | custom
	var slots := [0, 4, 1, 5, 2, 6]
	for k in mini(6, m.size()):
		buf[o + slots[k]] = float(m[k])
	buf[o + 3] = 0.0
	buf[o + 7] = 0.0
	buf[o + 8] = col.r
	buf[o + 9] = col.g
	buf[o + 10] = col.b
	buf[o + 11] = col.a
	buf[o + 12] = cus.r
	buf[o + 13] = cus.g
	buf[o + 14] = cus.b
	buf[o + 15] = cus.a


func commit() -> void:
	if count > 0:
		multimesh.buffer = buf


func set_param(name: StringName, value: Variant) -> void:
	(material as ShaderMaterial).set_shader_parameter(name, value)
