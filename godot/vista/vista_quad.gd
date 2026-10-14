class_name VistaQuad
extends Node2D
## A rectangle drawn with the node's material: the vista's full layers (sky, cloud deck, ground, sky
## shore, canopy) are shaders over one quad, reading their baked data from shader uniforms (never as
## the item's own texture: in an HDR viewport that one is read as sRGB colour, and the data would be
## decoded). The shaders get the local pixel position from VERTEX, so (0, 0) is the layer's top-left.

var size := Vector2.ZERO:
	set(v):
		size = v
		queue_redraw()


func _init(p_size: Vector2 = Vector2.ZERO, p_shader: Shader = null) -> void:
	size = p_size
	if p_shader != null:
		var m := ShaderMaterial.new()
		m.shader = p_shader
		material = m
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST


func _draw() -> void:
	if size.x > 0.0 and size.y > 0.0:
		draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)


func set_param(name: StringName, value: Variant) -> void:
	(material as ShaderMaterial).set_shader_parameter(name, value)
