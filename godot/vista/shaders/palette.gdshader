// A painted layer (canopy, near leaves, stirring sprays): ids -> colour of this time of day, from the
// baked palette rows (tools/vista), interpolated between the two rows around the hour.
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;
uniform sampler2D lut : filter_nearest, repeat_disable;
uniform float tod_row;
uniform vec2 src_ofs;          // where in `ids` this quad starts (sprites cut from a strip)

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	ivec2 p = ivec2(floor(px + src_ofs));
	vec4 t = texelFetch(ids, p, 0);
	if (t.a < 0.5) discard;
	int id = int(t.r * 255.0 + 0.5) + int(t.g * 255.0 + 0.5) * 256;
	COLOR = vec4(lin255(lut_rgb(lut, id, tod_row)), 1.0);
}
