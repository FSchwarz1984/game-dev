class_name CharLabView
extends PixelView3D
## The character lab's pixel view: the renderer's PixelView3D at the round-4 numbers (640 x 360
## native, 30 px per metre; decision-log G5R2 lead decisions), so the characters can be judged at
## the size they will have before the renderer's own view moves to them. Only the numbers differ;
## the camera, the post quads and the composite are the renderer's. Character class 3 uses the 3D
## characters' post (characters/shaders/char_post.gdshader) instead of the sprites' one.

const LAB_BASE := Vector2(640, 360)
const LAB_PPM := 30.0


func _init() -> void:
	super()
	for q in _post_quads:
		if String(q.name) == "Post_post_char":
			(q.material_override as ShaderMaterial).shader = load("res://characters/shaders/char_post.gdshader")


func apply_view_globals() -> void:
	var p := deg_to_rad(pitch_deg)
	RenderingServer.global_shader_parameter_set("w3_view", Vector4(LAB_PPM, sin(p), cos(p), tan(p * 0.5)))
	Character3D.set_view(LAB_PPM, pitch_deg)
	cam.rotation = Vector3(-p, 0.0, 0.0)


## 1920 x 1080 -> 640 x 360 x3, 1280 x 720 -> x2, 2560 x 1440 -> x4, 3840 x 2160 -> x6.
func fit() -> void:
	var win := get_window()
	var size := Vector2(win.size)
	if size.x < 1 or size.y < 1:
		return
	var s := maxi(1, roundi(size.y / LAB_BASE.y))
	if force_scale > 0:
		s = force_scale
	var cs := Vector2i(floori(size.x / s), floori(size.y / s))
	scale_factor = s
	if win.content_scale_size != cs:
		win.content_scale_size = cs
	logical = Vector2(cs)
	margin = ((size - logical * s) * 0.5).round()
	vp.size = cs + Vector2i(2, 2)
	view.size = Vector2(vp.size)
	cam.size = float(vp.size.y) / LAB_PPM
	composite.set_shader_parameter("view_size", logical)
	logical_resized.emit(logical)


func screen_of(wp: Vector3) -> Vector2:
	return Vector2(wp.x, wp.y * cos_p() - wp.z * sin_p()) * LAB_PPM


func px_to_world(d: Vector2) -> Vector3:
	return Vector3(d.x / LAB_PPM, 0, 0) + cam_up() * (d.y / LAB_PPM)
