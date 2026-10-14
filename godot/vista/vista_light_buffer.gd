class_name VistaLightBuffer
extends RefCounted
## A buffer that lights are summed into in sRGB units (the JS AddBuffer) and its composite pass, which
## adds it onto everything drawn before it in the vista's viewport, as the JS 'lighter' canvas did
## (composite.gdshader); what passes 1.0 becomes HDR in proportion to `excess` and the vista's glow
## blooms it. The buffer is a SubViewport inside the vista's viewport, so it renders first.
##   var b := VistaLightBuffer.new(owner_node, draw_parent, "Lamps", 0.4)
##   b.root.add_child(light_layer)        # layers placed in the same coordinates as draw_parent
##   b.fit(view); b.follow(draw_parent_offset_in_viewport)   every layout / frame

var vp: SubViewport
var root: Node2D
var copy: BackBufferCopy
var quad: VistaQuad


func _init(owner: Node, draw_parent: Node, label: String, excess: float = 0.35) -> void:
	vp = SubViewport.new()
	vp.name = label + "Buffer"
	vp.use_hdr_2d = true
	vp.transparent_bg = true
	vp.snap_2d_transforms_to_pixel = true
	vp.snap_2d_vertices_to_pixel = true
	vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.gui_disable_input = true
	vp.size = Vector2i(482, 272)
	root = Node2D.new()
	root.name = "Root"
	vp.add_child(root)
	owner.add_child(vp)
	copy = BackBufferCopy.new()
	copy.name = label + "Copy"
	copy.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
	draw_parent.add_child(copy)
	quad = VistaQuad.new(Vector2(482, 272), preload("res://vista/shaders/composite.gdshader"))
	quad.name = label + "Light"
	quad.set_param("add_tex", vp.get_texture())
	quad.set_param("excess", excess)
	draw_parent.add_child(quad)


## The vista's viewport size (logical view + a 1 px border on every side).
func fit(view: Vector2i) -> void:
	vp.size = view + Vector2i(2, 2)
	quad.size = Vector2(vp.size)


## `ofs`: where the draw parent's origin is in the vista viewport (its offset + the 1 px border).
func follow(ofs: Vector2) -> void:
	root.position = ofs
	quad.position = -ofs


func set_visible(on: bool) -> void:
	quad.visible = on
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS if on else SubViewport.UPDATE_DISABLED
