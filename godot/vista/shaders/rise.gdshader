// The lights rising from the plain to the gate: the model of the early v0.2 vista (src/vista/south.js
// at commit 8196ebf, drawRising; docs/knowledge/14 §4). Every lamp leaves on its own cubic Bezier
// (its place on the plain -> above its hamlet -> toward the gate -> the gate's mouth), in 7.2-9.6 s
// (the two lone lights 11 s), easing s = u 0.62 + smoothstep(u) 0.38 (the lone ones u 0.85 + u^2 0.15).
// Our amber turns to the sky shore's pale jade after half the way. A 1 px core (2x2 for fires and
// the lone two) a little whiter than its colour, a stepped halo (r 2 / 4 / 6), a tail of 1-8 pixels
// behind it along its own curve. While the cloud deck is closed the lights near the end of their
// way are swallowed by it.
// One instance = one light's core and halo (segment 0) or one pixel of its tail (segment q).
// Positions are whole native pixels (JS Math.round). Output: sRGB units into the light buffer (see
// composite.gdshader). New here: the core gets `bloom` more, so with what passes 1.0 the viewport's
// glow blooms the light sources and nothing else; companion sparks (desktop) leave a moment after
// their lamp along their own jittered curve.
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D tdep : filter_nearest, repeat_disable;   // departure time of each lamp (-1e9: not yet)
uniform float t;
uniform float closed = 1.0;     // 1 - smooth(0.15, 0.6, sky)
uniform float bloom = 0.5;      // added to a full core (sRGB units: past 1.0 it blooms)
uniform float halo = 1.0;

varying flat vec4 v_core;       // core pixel x, y, size (1|2), alpha
varying flat vec4 v_glow;       // glow centre x, y, radius, alpha
varying flat vec3 v_rc;         // colour (sRGB 0..255)
varying flat float v_seg;
varying vec2 v_px;

const vec3 C_WINDOW = vec3(255.0, 196.0, 122.0);
const vec3 C_LANTERN = vec3(255.0, 152.0, 88.0);
const vec3 C_FIRE = vec3(255.0, 206.0, 136.0);
const vec3 C_STAR = vec3(206.0, 216.0, 255.0);
const vec3 C_JADE = vec3(196.0, 246.0, 226.0);

vec2 bez(vec2 a, vec2 b, vec2 c, vec2 d, float s) {
	float u = 1.0 - s;
	return u * u * u * a + 3.0 * u * u * s * b + 3.0 * u * s * s * c + s * s * s * d;
}

void vertex() {
	vec2 p0 = MODEL_MATRIX[0].xy, p1 = MODEL_MATRIX[1].xy, p2 = MODEL_MATRIX[2].xy;
	vec2 world = MODEL_MATRIX[3].xy;
	vec2 p3 = COLOR.rg;
	float dur = COLOR.b, delay = COLOR.a;
	int li = int(INSTANCE_CUSTOM.r + 0.5);
	float seg = INSTANCE_CUSTOM.g;
	float kind = INSTANCE_CUSTOM.b;        // 0 window, 1 lantern, 2 star, 3 fire, 4 bonfire
	int flags = int(INSTANCE_CUSTOM.a + 0.5);
	bool solo = (flags & 1) != 0, big = (flags & 2) != 0, comp = (flags & 4) != 0;
	float td = texelFetch(tdep, ivec2(li % 4096, li / 4096), 0).r;
	float el = t - td - delay;
	bool live = td > -1.0e8 && el >= 0.0 && el < dur;
	float u = clamp(el / dur, 0.0, 1.0);
	float s = solo ? u * 0.85 + u * u * 0.15 : u * 0.62 + u * u * (3.0 - 2.0 * u) * 0.38;
	vec3 base = kind < 0.5 ? C_WINDOW : kind < 1.5 ? C_LANTERN : kind < 2.5 ? C_STAR : C_FIRE;
	float kk = clamp((s - 0.55) / 0.4, 0.0, 1.0);
	vec3 rc = mix(base, C_JADE, kk * kk * (3.0 - 2.0 * kk));
	float a = smoothj(0.0, 0.06, u) * (kind > 1.5 && kind < 2.5 ? 0.75 : 1.0);
	a *= 1.0 - closed * smoothj(0.8, 0.97, s);
	a *= 1.0 - smoothj(0.96, 1.0, s) * 0.6;
	if (comp) a *= 0.62;
	float nt = solo ? 8.0 : (kind > 1.5 && kind < 2.5) || comp ? 1.0 : 3.0;
	v_seg = seg;
	v_rc = rc;
	vec2 lo, hi;
	if (!live || a <= 0.02 || seg > nt) {
		VERTEX = vec2(-100000.0);
		v_core = vec4(0.0);
		v_glow = vec4(0.0);
	} else if (seg < 0.5) {
		vec2 q = bez(p0, p1, p2, p3, s);
		vec2 c = vec2(roundj(q.x), roundj(q.y));
		float sz = big && !comp ? 2.0 : 1.0;
		float r = comp ? 1.0 : solo ? 6.0 : big ? 4.0 : 2.0;
		vec2 g = vec2(roundj(q.x + (big && !comp ? 0.5 : 0.0)), c.y);
		v_core = vec4(c, sz, a);
		v_glow = vec4(g, r, a * (solo ? 0.7 : big ? 0.55 : 0.75));
		lo = min(c, g - r);
		hi = max(c + sz, g + r + 1.0);
		v_px = lo + VERTEX * (hi - lo);
		VERTEX = world + v_px;
	} else {
		vec2 q = bez(p0, p1, p2, p3, max(0.0, s - seg * (solo ? 0.008 : 0.012)));
		vec2 c = vec2(roundj(q.x), roundj(q.y));
		v_core = vec4(c, 1.0, a * (0.55 - seg * (0.5 / (nt + 1.0))));
		v_glow = vec4(0.0);
		v_px = c + VERTEX;
		VERTEX = world + v_px;
	}
}

void fragment() {
	vec2 p = floor(v_px);
	vec3 c = vec3(0.0);
	float hdr = 0.0;
	if (v_seg < 0.5) {
		vec2 d = p - v_core.xy;
		if (d.x >= 0.0 && d.y >= 0.0 && d.x < v_core.z && d.y < v_core.z) {
			c += mix(v_rc, vec3(255.0), 0.3) * v_core.w;
			hdr = v_core.w;
		}
		c += v_rc * v_glow.w * glow_w(p - v_glow.xy, v_glow.z) * halo;
	} else {
		c = v_rc * max(v_core.w, 0.0);
	}
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + v_rc / 255.0 * hdr * bloom, 1.0);
}
