class_name CharSprite3D
extends MeshInstance3D
## A character drawn as a 2D sprite standing in the 3D world (shaders/sprite_char.gdshader): a
## leaned card at the feet, texel for pixel, lit through its normal map with the charter's
## character protection, casting its silhouette as a shadow. Place it with `position` = the feet.
##   setup(sheet, sheet_n, frame_size, pivot); show_frame(col, row, flip)

var mat := ShaderMaterial.new()
var frame_size := Vector2i(64, 64)
var pivot := Vector2i(32, 58)
## her silhouette through whatever covers her (shaders/sprite_xray.gdshader)
var xray := MeshInstance3D.new()
var xray_mat := ShaderMaterial.new()


func _init() -> void:
	mat.shader = load("res://render3d/shaders/sprite_char.gdshader")
	material_override = mat
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	extra_cull_margin = 2.0
	xray_mat.shader = load("res://render3d/shaders/sprite_xray.gdshader")
	xray_mat.render_priority = 120
	xray.material_override = xray_mat
	xray.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	xray.extra_cull_margin = 2.0
	xray.name = "XRay"
	add_child(xray)


## The colour of her outline when something covers her (sRGB).
func set_xray_colour(c: Color) -> void:
	xray_mat.set_shader_parameter("line_col", c)


## Textures are copied into ImageTextures: a CompressedTexture2D used by a 3D material gets its
## import switched to VRAM compression by the editor (detect_3d), which would blur pixel art and
## rewrite another agent's import files.
static func pixel_texture(path: String) -> Texture2D:
	var t: Texture2D = load(path)
	if t == null:
		return null
	return ImageTexture.create_from_image(t.get_image())


func setup(sheet: Texture2D, sheet_n: Texture2D, fsize: Vector2i, piv: Vector2i, sprite_pitch := 39.33) -> void:
	frame_size = fsize
	pivot = piv
	mat.set_shader_parameter("pivot_px", Vector2(piv))
	mat.set_shader_parameter("sprite_pitch_deg", sprite_pitch)
	mat.set_shader_parameter("sheet", sheet)
	mat.set_shader_parameter("sheet_n", sheet_n)
	xray_mat.set_shader_parameter("sheet", sheet)
	var l := -float(piv.x)
	var r := float(fsize.x - piv.x)
	var t := float(piv.y)
	var b := -float(fsize.y - piv.y)
	var corners := [Vector2(l, b), Vector2(r, b), Vector2(r, t), Vector2(l, t)]
	var uvs := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
	var verts := PackedVector3Array()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var nrm := PackedVector3Array()
	for i in 4:
		var c: Vector2 = corners[i]
		verts.append(Vector3(c.x, c.y, 0.0) / 20.0)
		uv.append(uvs[i])
		uv2.append(c)
		nrm.append(Vector3(0, 0, 1))
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = nrm
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_TEX_UV2] = uv2
	# clockwise on screen: Godot's front face
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 2, 1, 0, 3, 2])
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	mesh = m
	xray.mesh = m


func show_frame(col: int, row: int, flip := false, head := Vector2(0.5, -35.0)) -> void:
	mat.set_shader_parameter("frame_rect", Vector4(col * frame_size.x, row * frame_size.y, frame_size.x, frame_size.y))
	mat.set_shader_parameter("flip_h", flip)
	xray_mat.set_shader_parameter("frame_rect", Vector4(col * frame_size.x, row * frame_size.y, frame_size.x, frame_size.y))
	xray_mat.set_shader_parameter("flip_h", flip)
	mat.set_shader_parameter("head_px", head)
