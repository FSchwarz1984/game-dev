class_name PixelView3D
extends Control
## The 3D world rendered as pixel art (docs/knowledge/21-3d-pixel-render.md).
##
## The world renders into a low-res SubViewport at the native size (640x360: 720p x2, 1080p x3, 1440p
## x4, 4K x6; the canvas follows the window like the 2D core's PixelStage, see fit()) plus a 1-pixel
## border. 1 m = 30 native px (PPM) on the camera's picture plane.
## An orthographic camera with fixed yaw (north up) and a fixed pitch looks at it; the camera is
## snapped to whole native texels in view space and the sub-pixel remainder shifts the upscaled
## image (in whole window pixels), so following is smooth while every texel stays on the world's
## pixel lattice (no shimmer). Outlines and fog are a screen post per
## outline class (stencil-gated quads, see shaders/post_*.gdshader); grading is the composite.
##
## Camera space here is "screen px": native pixels, x east, y up the screen (w3_screen() in the
## shaders), independent of where the camera is.

signal logical_resized(size: Vector2)

const BASE := Vector2(640, 360)
const PPM := 30.0

@export var pitch_deg := 55.0
## Dev previews only (asset checks of tall trees): a fixed integer scale instead of the rule.
var force_scale := 0

var vp: SubViewport
var cam: Camera3D
var env_node: WorldEnvironment
var view: TextureRect
var composite: ShaderMaterial
var scale_factor := 1
var logical := BASE
var margin := Vector2.ZERO          # window px of the logical canvas's top-left corner
var world_root: Node3D

# camera state, in screen px
var cam_px := Vector2.ZERO          # exact camera centre (screen px), what is rendered
var render_px := Vector2.ZERO       # snapped centre actually used this frame
var follow_speed := 6.0
var _getter: Callable
var _smooth := Vector2.ZERO
var _last_target := Vector2.INF
var _moving_t := 0.0
var _point := Vector2.ZERO
var _mode := "point"
var _focus := Vector3.ZERO          # world point the camera looks at (sets the depth range)
var _post_quads: Array[MeshInstance3D] = []
## How far the camera stands back from the focus. The depth range is near..far around it; a nearer
## camera gives the volumetric fog (froxels measured from the camera) its resolution where the
## world is. set_camera_distance() keeps near/far around the same slab of world.
var cam_distance := 120.0


func set_camera_distance(d: float) -> void:
	cam_distance = d
	cam.near = maxf(d - 60.0, 0.5)
	cam.far = d + 70.0


func _init() -> void:
	name = "PixelView3D"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)

	vp = SubViewport.new()
	vp.name = "World3DViewport"
	vp.own_world_3d = true
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.use_taa = false
	vp.scaling_3d_scale = 1.0
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.gui_disable_input = true
	vp.handle_input_locally = false
	# float, linear: the grade and the final dither work on the full precision (no banding in slow
	# dark gradients); composite.gdshader converts to display values
	vp.use_hdr_2d = true
	# the lanterns are engine lights since round 4 (no shadows of their own for now)
	vp.positional_shadow_atlas_size = 0
	add_child(vp)

	world_root = Node3D.new()
	world_root.name = "World"
	vp.add_child(world_root)

	cam = Camera3D.new()
	cam.name = "Camera"
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	# The camera stands 120 m back from the focus. Keep the depth range tight: for an orthogonal
	# camera Godot ignores the sun's shadow max distance and fits the shadow map around the bounding
	# sphere of the whole near..far box, so 1..300 m spread the 4096 map over ~300 m (7.3 cm a
	# texel, more than a pixel). Everything she can see lies 100..157 m deep (every walkable focus,
	# checked on the height map), trees reach ~15 m nearer. (docs/knowledge/21 §6.2)
	cam.near = 60.0
	cam.far = 190.0
	cam.current = true
	vp.add_child(cam)

	# one full-screen quad per outline class, drawn first in the transparent pass
	var classes := ["post_solid", "post_foliage", "post_char", "post_target", "post_noline"]
	for c in classes:
		var q := MeshInstance3D.new()
		q.name = "Post_" + c
		var m := QuadMesh.new()
		m.size = Vector2(2, 2)
		q.mesh = m
		q.extra_cull_margin = 16384.0
		q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var sm := ShaderMaterial.new()
		var path := "res://render3d/shaders/%s.gdshader" % c
		# the 3D characters draw their own outline pass for class 3 (round 4, item 7: depth outline,
		# inner lines between parts; docs/knowledge/24) once they are in the tree
		if c == "post_char" and ResourceLoader.exists(CHAR_POST):
			path = CHAR_POST
		sm.shader = load(path)
		sm.render_priority = -100
		q.material_override = sm
		q.position = Vector3(0, 0, -2)
		cam.add_child(q)
		_post_quads.append(q)

	view = TextureRect.new()
	view.name = "WorldView"
	view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view.stretch_mode = TextureRect.STRETCH_SCALE
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	composite = ShaderMaterial.new()
	composite.shader = load("res://render3d/shaders/composite.gdshader")
	composite.set_shader_parameter("blue_noise", load("res://render3d/textures/blue_noise64.png"))
	view.material = composite
	add_child(view)


func _ready() -> void:
	view.texture = vp.get_texture()
	get_window().size_changed.connect(fit)
	apply_view_globals()
	fit()


func set_environment(e: Environment) -> void:
	if env_node == null:
		env_node = WorldEnvironment.new()
		env_node.name = "Env"
		vp.add_child(env_node)
	env_node.environment = e


const CHAR3D := "res://characters/character3d.gd"
const CHAR_POST := "res://characters/shaders/char_post.gdshader"


func apply_view_globals() -> void:
	var p := deg_to_rad(pitch_deg)
	RenderingServer.global_shader_parameter_set("w3_view", Vector4(PPM, sin(p), cos(p), tan(p * 0.5)))
	cam.rotation = Vector3(-p, 0.0, 0.0)
	# the 3D characters stamp their faces with the same numbers (a global shader parameter cannot be
	# read back at run time)
	if ResourceLoader.exists(CHAR3D):
		(load(CHAR3D) as GDScript).call("set_view", PPM, pitch_deg)


## Integer scale from the window, the same rule as the 2D core (core/pixel_stage.gd scale_for()):
## s = round(h / 360), lowered while the canvas would be narrower than 400; the canvas is the window
## divided by s (1280x720 -> 640x360 x2, 1920x1080 -> 640x360 x3, 2560x1440 -> 640x360 x4, 3840x2160
## -> 640x360 x6, 1366x768 -> 683x384 x2). No black bars, no fractional scale.
func fit() -> void:
	var win := get_window()
	var size := Vector2(win.size)
	if size.x < 1 or size.y < 1:
		return
	var s := PixelStage.scale_for(size, BASE)
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
	cam.size = float(vp.size.y) / PPM
	composite.set_shader_parameter("view_size", logical)
	logical_resized.emit(logical)


# ------------------------------------------------------------------------------------------------
# screen px <-> world

func sin_p() -> float:
	return sin(deg_to_rad(pitch_deg))


func cos_p() -> float:
	return cos(deg_to_rad(pitch_deg))


## Screen px (x east, y up) of a rendered world point (already leaned, if it is an upright object).
func screen_of(wp: Vector3) -> Vector2:
	return Vector2(wp.x, wp.y * cos_p() - wp.z * sin_p()) * PPM


## Screen px of a point on an upright object at height h above its base b (the lean applied).
func screen_of_upright(base: Vector3, h: float) -> Vector2:
	var k := tan(deg_to_rad(pitch_deg) * 0.5)
	return screen_of(base + Vector3(0, h, -k * h))


func cam_up() -> Vector3:
	return Vector3(0, cos_p(), -sin_p())


func cam_back() -> Vector3:
	return Vector3(0, sin_p(), cos_p())


func px_to_world(d: Vector2) -> Vector3:
	return Vector3(d.x / PPM, 0, 0) + cam_up() * (d.y / PPM)


## Logical canvas px (y down, origin top-left: where the HUD draws) of a world point this frame.
func world_to_canvas(wp: Vector3) -> Vector2:
	var s := screen_of(wp) - cam_px
	return Vector2(s.x, -s.y) + (logical * 0.5)


## Window px (what a real finger or xdotool clicks) of a world point this frame.
func world_to_window(wp: Vector3) -> Vector2:
	return margin + world_to_canvas(wp) * scale_factor


# ------------------------------------------------------------------------------------------------
# camera

## Follow a getter returning a world point (her feet, say). While the target moves the camera is
## locked to its whole-pixel position (a sub-pixel camera over a sprite that steps in whole pixels
## makes the sprite shimmer); the lag eases out sub-pixel smooth when she stands still.
func follow(getter: Callable, opts: Dictionary = {}) -> void:
	_getter = getter
	_mode = "follow"
	follow_speed = float(opts.get("speed", 6.0))
	if opts.get("cut", false) and getter.is_valid():
		_focus = getter.call()
		var t: Vector2 = screen_of(_focus)
		_smooth = t
		cam_px = t.round()
	else:
		_smooth = cam_px


func point_at(wp: Vector3, opts: Dictionary = {}) -> void:
	_mode = "point"
	_focus = wp
	_point = screen_of(wp)
	follow_speed = float(opts.get("speed", 3.0))
	if opts.get("cut", false):
		cam_px = _point


func update_camera(dt: float) -> void:
	var k := 1.0 - exp(-follow_speed * dt)
	if _mode == "follow" and _getter.is_valid():
		_focus = _getter.call()
		var raw: Vector2 = screen_of(_focus)
		if _last_target != Vector2.INF and raw.distance_to(_last_target) > 0.001:
			_moving_t = 0.0
		else:
			_moving_t += dt
		_last_target = raw
		var t := raw.round()
		_smooth += (t - _smooth) * k
		var lag := _smooth - t
		cam_px = t + (lag.round() if _moving_t < 0.2 else lag)
	elif _mode == "point":
		cam_px += (_point - cam_px) * k
		if cam_px.distance_to(_point) < 0.01:
			cam_px = _point
	apply_camera()


## Renders this frame from the snapped camera and shifts the image by the remainder.
func apply_camera() -> void:
	var size := Vector2(vp.size)
	# pixel centres must sit at k + 0.5 on the lattice: with an odd viewport size the centre is a
	# pixel centre, so it moves half a pixel
	var half := Vector2(fmod(size.x, 2.0), fmod(size.y, 2.0)) * 0.5
	var si := cam_px.round() + half
	var frac := cam_px - cam_px.round()
	render_px = si
	composite.set_shader_parameter("cam_cell", si.floor())
	# a world point on the view axis whose screen position is si; the camera stands back from it
	var centre := px_to_world(si) + cam_back() * _focus.dot(cam_back())
	cam.position = centre + cam_back() * cam_distance
	# the image content sits frac px away from where it should; move the image back (window px)
	var off := (frac * scale_factor).round() / float(scale_factor)
	view.position = -Vector2.ONE - Vector2(off.x, -off.y)
