// The sky shore's lights (src/vista/south.js shoreGen + drawShoreLights), all faint pale jade:
//   0 its town lamps and lit windows (still)        1 glints running up its rivers (away from us)
//   2 the dance ring, dancers passing the lanterns   3 the yagura at its centre   4 lantern strings
//   5 the gate's mouth: brighter with what goes in (inflow), and here also a flash for every light
//     that arrives (one at a time, then more and more), pushed into HDR so it blooms
// Output: sRGB units into the sky shore's light buffer (composite.gdshader); shown with the reveal.
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform float t;
uniform float reveal;
uniform float inflow;
uniform float flash;            // sum of the recent arrivals' flashes (0..)
uniform float haze_edge;
uniform float bloom_gate = 0.6;

varying flat vec4 v_d;          // type, a, b, c
varying flat vec2 v_pos;
varying vec2 v_px;

const vec3 C_JADE = vec3(196.0, 246.0, 226.0);
const vec3 C_CORE = vec3(236.0, 255.0, 248.0);
const vec3 C_WARM = vec3(222.0, 240.0, 178.0);

void vertex() {
	vec2 pos = MODEL_MATRIX[0].xy;
	float type = MODEL_MATRIX[1].x, pa = MODEL_MATRIX[1].y, pb = MODEL_MATRIX[2].x, pc = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float r = type < 0.5 ? 2.0 : type < 1.5 ? 0.0 : type < 2.5 ? 2.0 : type < 3.5 ? 4.0 : type < 4.5 ? 0.0 : 10.0;
	float a = 0.0;
	if (type < 0.5) {
		// still lamps: pa = brightness b, pb = Z, pc = window (1)
		a = pa * smoothj(haze_edge + 2.0, haze_edge - 10.0, pos.y) * (1.0 - smoothj(30.0, 75.0, pb) * 0.5);
		if (a < 0.03) a = 0.0;
	} else if (type < 1.5) {
		// river glints: pa = u, pb = river index, pc = Z
		float k = sin(pa * 0.9 - t * 1.6 + pb * 2.1);
		a = k < 0.82 ? 0.0 : (k - 0.82) / 0.18 * (1.0 - smoothj(30.0, 70.0, pc) * 0.6);
	} else if (type < 2.5) {
		a = 0.6 + 0.4 * sin(pa * 2.0 - t * 1.3);
	} else if (type < 4.5) {
		a = 1.0;
	} else {
		a = 1.0;
	}
	a *= reveal;
	v_d = vec4(type, a, pa, pc);
	v_pos = floor(pos);
	if (a <= 0.004) {
		VERTEX = vec2(-100000.0);
	} else {
		v_px = v_pos - vec2(r) + VERTEX * (2.0 * r + 1.0);
		VERTEX = world + v_px;
	}
}

void fragment() {
	vec2 d = floor(v_px) - v_pos;
	float type = v_d.x, a = v_d.y;
	bool at0 = d.x == 0.0 && d.y == 0.0;
	vec3 c = vec3(0.0);
	vec3 hdr = vec3(0.0);
	if (type < 0.5) {
		bool win = v_d.w > 0.5;
		if (win) {
			if (at0) c += C_WARM * a;
			c += C_WARM * 0.3 * a * glow_w(d, 2.0);
		} else {
			if (at0) c += C_CORE * a;
			// (big, near lamps carry a small glow: b > 0.8 and Z < 50, flagged by the bake as pc = 2)
			if (v_d.w > 1.5) c += C_JADE * 0.35 * a * glow_w(d, 2.0);
		}
	} else if (type < 1.5) {
		if (at0) c += C_CORE * a;
	} else if (type < 2.5) {
		if (at0) c += C_CORE * a;
		c += C_JADE * 0.45 * a * glow_w(d, 2.0);
	} else if (type < 3.5) {
		if (at0) c += C_CORE * a;
		c += C_JADE * 0.5 * a * glow_w(d, 4.0);
	} else if (type < 4.5) {
		if (at0) c += C_JADE * a * 0.55;
	} else {
		float pulse = 0.85 + 0.15 * sin(t * 2.2);
		c += C_JADE * 0.5 * a * (0.35 + 0.65 * inflow) * pulse * glow_w(d, 9.0);
		c += C_CORE * 0.8 * a * (0.5 + 0.5 * inflow) * glow_w(d, 3.0);
		if (at0) {
			c += C_CORE * a;
			hdr = C_CORE / 255.0 * a * bloom_gate * (0.4 + 0.6 * inflow + flash);
		}
		c += C_CORE * 0.35 * a * min(flash, 2.0) * glow_w(d, 5.0);
	}
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + hdr, 1.0);
}
