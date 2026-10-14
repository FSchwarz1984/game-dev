// The stars over the plain (src/vista/sky.js makeStars, starCanvas, drawTwinklers): faint to bright
// (4 magnitudes), a few twinkling, the brightest flaring into a small cross at their peak; they fade
// toward the horizon and come out with the night. Mixed over the painted sky in sRGB, as the JS
// canvas did (a faint star in linear blending would read brighter than it was drawn).
shader_type canvas_item;
render_mode blend_disabled, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"
#include "res://vista/shaders/sky.gdshaderinc"

uniform float t;
uniform float stars = 1.0;      // env.stars
uniform bool sky_from_tex = false;                                  // tower, title: a baked sky
uniform sampler2D sky_tex : filter_nearest, repeat_disable;
uniform float fade_y0 = 0.0;    // with a baked sky: the fade toward its horizon (smooth(y0, y1, y))
uniform float fade_y1 = -36.0;

varying flat vec4 v_c;          // colour (sRGB 0..1), alpha
varying flat float v_flare;
varying vec2 v_px;
varying flat vec2 v_pos;

void vertex() {
	vec2 pos = MODEL_MATRIX[0].xy;
	float ph = MODEL_MATRIX[1].x, sp = MODEL_MATRIX[1].y, mag = MODEL_MATRIX[2].x, tw = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float sa = mag < 0.5 ? 0.32 : mag < 1.5 ? 0.55 : mag < 2.5 ? 0.8 : 1.0;
	float fade = sky_from_tex ? smoothj(fade_y0, fade_y1, pos.y) : smoothj(horizon, horizon - 36.0, pos.y);
	float a = sa * fade;
	float flare = 0.0;
	bool show = a > 0.02;
	if (tw > 0.5) {
		float k = 0.62 + 0.38 * sin(t * sp + ph) * sin(t * sp * 0.37 + ph * 2.1);
		a *= k;
		show = a * stars > 0.03;
		flare = mag > 2.5 && k > 0.78 ? 1.0 : 0.0;
	}
	a *= stars;
	v_c = vec4(COLOR.rgb, a);
	v_flare = flare;
	v_pos = pos;
	if (!show || stars <= 0.02) {
		VERTEX = vec2(-100000.0);
	} else {
		vec2 lo = pos - vec2(flare);
		v_px = lo + VERTEX * (1.0 + 2.0 * flare);
		VERTEX = world + v_px;
	}
}

void fragment() {
	vec2 p = floor(v_px);
	vec2 d = p - v_pos;
	float a = v_c.a;
	if (d.x != 0.0 || d.y != 0.0) {
		if (abs(d.x) + abs(d.y) != 1.0) discard;
		a *= 0.4;
	}
	vec3 sky = sky_from_tex ? texelFetch(sky_tex, ivec2(p), 0).rgb * 255.0 : sky_px(p);
	COLOR = vec4(lin255(mix(sky, v_c.rgb * 255.0, clamp(a, 0.0, 1.0))), 1.0);
}
