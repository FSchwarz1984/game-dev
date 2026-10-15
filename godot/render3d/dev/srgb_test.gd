extends Node
## Internal test (never shipped): does a sampler with source_color return linear values here?
## A unshaded quad shows texture value 0.5 (sRGB) with and without the hint; the viewport is not HDR,
## so the engine converts linear to sRGB on output: 128 = the sampler linearised, 188 = raw.

var vp: SubViewport
var frame := 0


func _ready() -> void:
	vp = SubViewport.new()
	vp.size = Vector2i(64, 32)
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.own_world_3d = true
	add_child(vp)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 2.0
	cam.position = Vector3(0, 0, 5)
	vp.add_child(cam)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)
	var img := Image.create(4, 4, false, Image.FORMAT_RGBA8)
	img.fill(Color8(128, 128, 128, 255))
	var tex := ImageTexture.create_from_image(img)
	for i in 2:
		var sh := Shader.new()
		var hint := "source_color, " if i == 0 else ""
		sh.code = "shader_type spatial;\nrender_mode unshaded;\nuniform sampler2D t : %sfilter_nearest;\nvoid fragment() { ALBEDO = texture(t, UV).rgb; }\n" % hint
		var m := ShaderMaterial.new()
		m.shader = sh
		m.set_shader_parameter("t", tex)
		var q := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(1.9, 1.9)
		q.mesh = qm
		q.material_override = m
		q.position = Vector3(-1.0 + 2.0 * i, 0, 0)
		vp.add_child(q)


func _process(_dt: float) -> void:
	frame += 1
	if frame == 10:
		var im := vp.get_texture().get_image()
		print("SRGBTEST with source_color: ", im.get_pixel(16, 16).r8, "  without: ", im.get_pixel(48, 16).r8)
		get_tree().quit()
