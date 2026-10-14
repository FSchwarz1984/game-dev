// The painted sky (sky.gdshaderinc) over the far group's whole canvas; the layers above cover what
// is not sky.
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"
#include "res://vista/shaders/sky.gdshaderinc"

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	COLOR = vec4(lin255(sky_px(floor(px))), 1.0);
}
