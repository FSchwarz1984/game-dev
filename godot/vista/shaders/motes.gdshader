// The motes of the wave's curtain (src/vista/wave.js drawFront, HEAD): born along the front, they rise
// and drift toward the camera, thinning as they go; each lives in the world (X, Z, height) and is
// projected every frame, so near ones are bigger and faster, and nearer ground hides them. Spawned on
// the CPU into a ring of instances; moved here. Summed into the plain's light buffer (sRGB units).
//   instance: X0 Z0 | H0 hg | vX vZ ; colour: vH life t0 -
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D zmap : filter_nearest, repeat_disable;
uniform float t;
uniform float cx;
uniform float yl;
uniform float f = 360.0;
uniform float alpha = 1.0;

varying flat vec4 v_m;          // x, y, size, a
varying vec2 v_px;

const vec3 MOTE = vec3(226.0, 234.0, 255.0);

void vertex() {
	vec2 xz = MODEL_MATRIX[0].xy;
	float h0 = MODEL_MATRIX[1].x, hg = MODEL_MATRIX[1].y;
	float vx = MODEL_MATRIX[2].x, vz = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float vh = COLOR.r, life = COLOR.g, t0 = COLOR.b;
	float age = t - t0;
	float Z = xz.y + vz * age;
	bool live = life > 0.0 && age >= 0.0 && age < life && Z >= 0.25;
	float X = xz.x + vx * age, H = h0 + vh * age;
	vec2 q = vec2(cx + f * X / Z, yl + f * (1.0 - hg - H) / Z);
	vec2 qi = vec2(roundj(q.x), roundj(q.y));
	ivec2 size = textureSize(zmap, 0);
	if (live && qi.x >= 0.0 && qi.y >= 0.0 && qi.x < float(size.x) && qi.y < float(size.y)) {
		vec2 zv = texelFetch(zmap, ivec2(qi), 0).rg;
		float zg = (floor(zv.r * 255.0 + 0.5) + floor(zv.g * 255.0 + 0.5) * 256.0) * 1024.0 / 65535.0;
		if (zg > 0.0 && zg < Z * 0.85) live = false;          // behind nearer ground
	} else live = false;
	float u = age / max(life, 1e-4);
	float a = alpha * smoothj(0.0, 0.1, age) * pow(max(1.0 - u, 0.0), 1.2) * (0.5 + 0.5 * (1.0 - smoothj(0.0, 0.5, u)));
	float sz = f * 0.006 / Z;
	float big = sz > 1.2 ? (sz > 2.4 ? 3.0 : 2.0) : 1.0;
	a *= big > 1.0 ? 0.8 : 1.0;
	if (!live || a <= 0.004) {
		VERTEX = vec2(-100000.0);
		v_m = vec4(0.0);
	} else {
		vec2 lo = vec2(roundj(q.x - floor(big / 2.0)), roundj(q.y - floor(big / 2.0)));
		v_m = vec4(lo, big, a);
		v_px = lo + VERTEX * big;
		VERTEX = world + v_px;
	}
}

void fragment() {
	COLOR = vec4(MOTE / 255.0 * v_m.w, 1.0);
}
