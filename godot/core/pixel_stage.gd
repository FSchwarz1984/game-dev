class_name PixelStage
extends Control
## The pixel-perfect stage. The window is filled at an integer scale s = floor(min(w / 480,
## h / 270)) and the logical (native-pixel) canvas grows to fill it: content_scale_size =
## (w / s, h / s), so a bigger window shows more world and there are no black bars (at most one
## stray window pixel at odd sizes). Stretch mode is canvas_items with integer scaling (project
## settings): everything is laid out in native pixels and drawn at s times.
##
## The world renders into its own SubViewport at native resolution plus a 1-pixel border, with
## pixel snapping and nearest filtering, so it is pixel-perfect; it is shown upscaled by s, offset by
## the camera's sub-pixel remainder (in whole screen pixels). This is the SmoothPixelSubViewport-
## Container approach (docs/knowledge/11, MIT, apples/godot-smooth-pixel-subviewport-container),
## rewritten. "viewport" stretch mode cannot do it: it renders the whole window at native size,
## where a sub-pixel offset does not exist.
##
## The world viewport has its own World3D: the WorldEnvironment (2D HDR glow, tonemap) applies to
## the world only, never to text and UI drawn above it.

signal logical_resized(size: Vector2)

const BASE := Vector2(480, 270)

var world_vp: SubViewport
var world_root: Node2D
var view: TextureRect
var env: WorldEnvironment
var cam := PixelCamera.new()
var scale_factor := 1
var logical := BASE
var margin := Vector2.ZERO        # window px of the logical canvas's top-left corner
var render_cam := Vector2.ZERO    # the camera position actually rendered this frame (world px)
var hdr := true


func _init() -> void:
	name = "Stage"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)

	world_vp = SubViewport.new()
	world_vp.name = "WorldViewport"
	world_vp.own_world_3d = true
	world_vp.use_hdr_2d = hdr
	world_vp.snap_2d_transforms_to_pixel = true
	world_vp.snap_2d_vertices_to_pixel = true
	world_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	world_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	world_vp.gui_disable_input = true
	world_vp.handle_input_locally = false
	add_child(world_vp)

	env = WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CANVAS
	e.glow_enabled = true
	e.glow_intensity = 0.8
	e.glow_strength = 1.0
	e.glow_bloom = 0.0
	e.glow_hdr_threshold = 1.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.environment = e
	world_vp.add_child(env)

	world_root = Node2D.new()
	world_root.name = "World"
	world_vp.add_child(world_root)

	view = TextureRect.new()
	view.name = "WorldView"
	view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view.stretch_mode = TextureRect.STRETCH_SCALE
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	add_child(view)


func _ready() -> void:
	view.texture = world_vp.get_texture()
	if hdr:
		# The world viewport holds linear HDR values; the window shows sRGB. Convert when drawing it.
		var m := ShaderMaterial.new()
		m.shader = load("res://core/linear_to_srgb.gdshader")
		view.material = m
	get_window().size_changed.connect(fit)
	fit()


## Recomputes the integer scale and the logical canvas from the window size.
func fit() -> void:
	var win := get_window()
	var size := Vector2(win.size)
	if size.x < 1 or size.y < 1:
		return
	var s := maxi(1, floori(minf(size.x / BASE.x, size.y / BASE.y)))
	var cs := Vector2i(floori(size.x / s), floori(size.y / s))
	scale_factor = s
	if win.content_scale_size != cs:
		win.content_scale_size = cs
	logical = Vector2(cs)
	margin = ((size - logical * s) * 0.5).round()
	world_vp.size = cs + Vector2i(2, 2)
	view.size = Vector2(world_vp.size)
	cam.view = logical
	logical_resized.emit(logical)


## Applies the camera to this frame: the integer part into the world's canvas, the remainder (in
## whole screen pixels) into the view's offset. The game calls it after moving things and before
## the HUD projects anything, so the HUD and the world agree on the same frame.
func apply_camera() -> void:
	var c := cam.pos
	var ci := c.round()
	var frac := ((c - ci) * scale_factor).round() / float(scale_factor)
	render_cam = ci + frac
	world_vp.canvas_transform = Transform2D(0.0, -ci + (logical * 0.5).floor() + Vector2.ONE)
	view.position = -Vector2.ONE - frac


## World pixels -> logical screen pixels (where the HUD draws), for the frame being rendered.
func world_to_screen(p: Vector2) -> Vector2:
	return p - render_cam + (logical * 0.5).floor()


func screen_to_world(s: Vector2) -> Vector2:
	return s + render_cam - (logical * 0.5).floor()


## Logical screen pixels -> window pixels (what a real finger or xdotool clicks).
func to_window(s: Vector2) -> Vector2:
	return margin + s * scale_factor
