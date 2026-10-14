// The ground of the treetop vista (src/vista/ground.js, painted by the bake) with the wave of distance
// (src/vista/wave.js): every pixel knows when the ring reaches it (B channel, bucket of w * 250); behind
// the front the land is its pale "far" self, on the front (two buckets) a brighter pale.
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;     // R, G id; B arrival (255 never); A mask
uniform sampler2D lut : filter_nearest, repeat_disable;     // per time of day
uniform sampler2D lut_far : filter_nearest, repeat_disable; // row 0 far, row 1 the front
uniform float tod_row;
uniform float wave = -1.0;

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	vec4 t = texelFetch(ids, p, 0);
	if (t.a < 0.5) discard;
	int id = int(t.r * 255.0 + 0.5) + int(t.g * 255.0 + 0.5) * 256;
	vec3 c = lut_rgb(lut, id, tod_row);
	if (wave >= 0.0) {
		float b = clamp(floor(wave * 250.0), -1.0, 254.0);
		float arr = floor(t.b * 255.0 + 0.5);
		if (arr <= b - 2.0) c = texelFetch(lut_far, ivec2(id, 0), 0).rgb * 255.0;
		else if (arr <= b) c = texelFetch(lut_far, ivec2(id, 1), 0).rgb * 255.0;
	}
	COLOR = vec4(lin255(c), 1.0);
}
