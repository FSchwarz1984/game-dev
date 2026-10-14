// The live lights of the title backdrop and the tower insert (src/vista/title.js, tower.js), summed in
// sRGB units into a light buffer (composite.gdshader):
//   0 a star on the water (three groups twinkling out of step)   1 the moon's glitter on the water
//   2 a jade reflection of the ring that is not in the sky       3 a firefly drifting over the slope
//   4 the red aviation lamp of the 「隔」 tower: blinking, a last blink, then dark
// instance: x y | type p1 | p2 p3
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform float t;
uniform vec3 water_groups = vec3(1.0);
uniform float lamp_k = 0.0;      // the lamp's brightness this frame (0..1)
uniform float lamp_state = 2.0;  // 2 alive, 1 alive but between blinks, 0 dead
uniform float bloom = 0.6;

varying flat vec4 v_d;           // type, a, p1, p2
varying flat vec2 v_pos;
varying vec2 v_px;

const vec3 C_STAR = vec3(206.0, 216.0, 255.0);
const vec3 C_JADE = vec3(196.0, 246.0, 226.0);
const vec3 C_FLY = vec3(214.0, 255.0, 150.0);

void vertex() {
	vec2 pos = MODEL_MATRIX[0].xy;
	float type = MODEL_MATRIX[1].x, p1 = MODEL_MATRIX[1].y, p2 = MODEL_MATRIX[2].x, p3 = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float a = 0.0, r = 0.0;
	if (type < 0.5) {
		// p1 = brightness b, p2 = group
		a = p1 * (p2 < 0.5 ? water_groups.x : p2 < 1.5 ? water_groups.y : water_groups.z);
	} else if (type < 1.5) {
		// p1 = phase, p2 = b
		float tw = sin(t * 2.1 + p1) * sin(t * 0.9 + p1 * 3.0);
		a = tw > 0.2 ? (tw - 0.2) * 1.1 * p2 : 0.0;
	} else if (type < 2.5) {
		a = 0.4 * (0.7 + 0.3 * sin(t * 0.8 + p1));
	} else if (type < 3.5) {
		// p1 = phase: a firefly's lazy loop, blinking
		float u = t * 0.18 + p1;
		pos = pos + vec2(sin(u * 1.3) * 14.0 + sin(u * 3.1) * 3.0, sin(u * 0.9) * 6.0);
		float on = max(0.0, sin(t * 1.4 + p1 * 3.0));
		a = on * on * on;
		a = a > 0.05 ? a : 0.0;
		r = 3.0;
	} else {
		a = lamp_state > 0.5 || lamp_k > 0.0 ? 1.0 : 1.0;
		r = 10.0;
	}
	v_d = vec4(type, a, p1, p2);
	v_pos = vec2(roundj(pos.x), roundj(pos.y));
	if (a <= 0.004) {
		VERTEX = vec2(-100000.0);
	} else {
		vec2 lo = v_pos - vec2(r, r);
		vec2 hi = v_pos + vec2(r + 1.0, (type > 3.5 ? 20.0 : r + 1.0));
		v_px = lo + VERTEX * (hi - lo);
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
		if (at0) c = C_STAR * a;
	} else if (type < 1.5) {
		if (at0) c = vec3(214.0, 220.0, 240.0) * a;
	} else if (type < 2.5) {
		if (at0) c = C_JADE * a;
	} else if (type < 3.5) {
		if (at0) { c += C_FLY * a; hdr = C_FLY / 255.0 * a * bloom * 0.5; }
		c += C_FLY * 0.6 * a * 0.7 * glow_w(d, 3.0);
	} else {
		float k = lamp_k;
		if (k > 0.01) {
			c += vec3(255.0, 70.0, 50.0) * 0.5 * k * glow_w(d, 10.0);
			c += vec3(255.0, 120.0, 90.0) * 0.8 * k * glow_w(d, 4.0);
			if (at0) { c += vec3(255.0, 200.0, 180.0) * k; hdr = vec3(1.0, 0.3, 0.2) * k * bloom; }
			// the red catches the top of the lattice
			if (d.x == 1.0 && d.y >= 2.0 && d.y < 19.0) c += vec3(184.0, 52.0, 42.0) * 0.5 * k;
		} else if (at0) {
			c += lamp_state > 0.5 ? vec3(90.0, 30.0, 30.0) * 0.9 : vec3(40.0, 26.0, 30.0) * 0.9;
		}
	}
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + hdr, 1.0);
}
