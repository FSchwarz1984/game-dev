// 天岸, the sky shore (src/vista/skyshore.js, painted by the bake for the frame's height class),
// composed as south.js shoreGen did: its far edge dissolves into the cloud sea, the light between
// the shores lies behind that edge, and the whole is shown with the reveal as its alpha. Above the
// height class's own frame (a taller window) the land fades into the night overhead (8196ebf).
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;
uniform sampler2D lut : filter_nearest, repeat_disable;
uniform float tod_row;
uniform float row0;            // canvas row of the texture's first row
uniform float haze_edge;       // canvas row of the far edge
uniform vec3 band_col;         // the light between the shores (sRGB 0..255)
uniform vec2 fade = vec2(-1000.0, -999.0);
uniform vec3 fade_col;
uniform float reveal = 1.0;

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	float y = float(p.y) + row0;
	vec4 t = texelFetch(ids, p, 0);
	float land = t.a > 0.5 ? 1.0 : 0.0;
	vec3 c = vec3(0.0);
	if (land > 0.0) {
		int id = int(t.r * 255.0 + 0.5) + int(t.g * 255.0 + 0.5) * 256;
		c = lut_rgb(lut, id, tod_row);
		if (y < fade.y) c = mix(c, fade_col, 1.0 - smoothj(fade.x, fade.y, y + 0.5));
	}
	if (y >= haze_edge + 10.0) land *= 1.0 - smoothj(haze_edge + 10.0, haze_edge + 23.0, y);
	float band = 0.0;
	if (y >= haze_edge - 34.0) band = smoothj(haze_edge - 34.0, haze_edge, y) * (1.0 - smoothj(haze_edge + 8.0, haze_edge + 23.0, y)) * 0.7;
	float a = land + band * (1.0 - land);
	if (a <= 0.002) discard;
	vec3 rgb = (c * land + band_col * band * (1.0 - land)) / a;
	COLOR = vec4(lin255(rgb), a * reveal);
}
