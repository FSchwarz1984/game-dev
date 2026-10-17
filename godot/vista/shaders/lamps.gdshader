// The lamps on the plain (src/vista/south.js drawGroundLights + drawStatic): windows, Obon lanterns,
// stars reflected in the paddies (three groups twinkling out of step), fires and the big bonfires,
// each coming on at its own hour. A lamp whose light has left: in the JS it went out at once; here
// it flares for a moment as the light lifts off and dims out over half a second (while the spark
// fades in above it), and a fire leaves an ember. Behind the wave of distance every lamp is out.
// Kind 5: a floating lantern on the river (level given by the CPU). Output: sRGB units into the
// light buffer, like the JS AddBuffer (composite.gdshader adds it); fires and lanterns get a little more.
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D tdep : filter_nearest, repeat_disable;
uniform float t;
uniform float tod = 20.0;
uniform float wave = -1.0;
uniform vec3 star_groups = vec3(1.0);
uniform float bloom_fire = 0.35;
uniform float bloom_lamp = 0.08;
uniform float js_off = 0.0;     // 1: go out at once like the JS (checks)
uniform float drain_w = -1.0;   // (Vista.bridge "drain") the drained radius as the far's progress: embers within go out

varying flat vec4 v_a;          // kind, level (0..), flicker, ember level
varying flat vec4 v_b;          // flags, phase, light x, light y
varying vec2 v_px;

const vec3 C_WINDOW = vec3(255.0, 196.0, 122.0);
const vec3 C_WINDOW_DIM = vec3(226.0, 150.0, 92.0);
const vec3 C_LANTERN = vec3(255.0, 152.0, 88.0);
const vec3 C_FIRE = vec3(255.0, 206.0, 136.0);
const vec3 C_FIRE_HOT = vec3(255.0, 238.0, 196.0);
const vec3 C_EMBER = vec3(196.0, 72.0, 40.0);
const vec3 C_STAR = vec3(206.0, 216.0, 255.0);

void vertex() {
	vec2 pos = MODEL_MATRIX[0].xy;
	float on = MODEL_MATRIX[1].x, ph = MODEL_MATRIX[1].y, arr = MODEL_MATRIX[2].x, kind = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float flags = COLOR.r;
	int li = int(COLOR.g + 0.5);
	int grp = int(COLOR.b + 0.5);
	float td = texelFetch(tdep, ivec2(li % 4096, li / 4096), 0).r;
	float el = td > -1.0e8 ? t - td : -1.0;
	float lv = smoothj(on, on + 0.25, tod);
	if (wave >= 0.0) lv *= 1.0 - smoothj(arr - 0.004, arr + 0.012, wave);
	if (kind > 4.5) lv = on;    // a floating river lantern: its level comes from the CPU (in `on`)
	float ember = 0.0;
	if (kind > 2.5) {
		// fires: an ember once the light has gone (8196ebf: 0.5 a until the wave)
		float e = smoothj(0.0, 0.08, el) * (wave >= 0.0 ? 1.0 - smoothj(arr, arr + 0.02, wave) : 1.0);
		ember = el >= 0.0 ? 0.5 * smoothj(on, on + 0.25, tod) * e : 0.0;
		if (drain_w >= 0.0) ember *= 1.0 - smoothj(arr, arr + 0.02, drain_w);
	}
	if (el >= 0.0) {
		float lift = 1.0 + 0.7 * smoothj(0.0, 0.07, el) * (1.0 - smoothj(0.07, 0.3, el));
		lv *= js_off > 0.5 ? 0.0 : lift * (1.0 - smoothj(0.08, 0.55, el));
	}
	float fl;
	if (kind > 3.5) fl = 0.78 + 0.22 * sin(t * 9.0 + ph * 9.0) * sin(t * 5.1 + ph * 3.0);
	else fl = 0.75 + 0.25 * sin(t * 11.0 + ph * 9.0) * sin(t * 7.3 + ph * 3.0);
	if (kind > 1.5 && kind < 2.5) lv *= (grp == 0 ? star_groups.x : grp == 1 ? star_groups.y : star_groups.z);
	v_a = vec4(kind, lv, fl, ember);
	v_b = vec4(flags, ph, floor(pos.x), floor(pos.y));
	float r = kind > 4.5 ? 2.0 : kind > 3.5 ? 7.0 : kind > 2.5 ? 3.0 : kind > 1.5 ? 0.0 : 2.0;
	if (lv <= 0.004 && ember <= 0.004) {
		VERTEX = vec2(-100000.0);
	} else {
		vec2 lo = floor(pos) - vec2(r + 1.0, r + 2.0);
		vec2 hi = floor(pos) + vec2(r + 1.0, r + 1.0);
		v_px = lo + VERTEX * (hi - lo);
		VERTEX = world + v_px;
	}
}

void fragment() {
	vec2 d = floor(v_px) - v_b.zw;
	float kind = v_a.x, a = v_a.y, fl = v_a.z;
	int flags = int(v_b.x + 0.5);
	bool far = (flags & 1) != 0, path = (flags & 2) != 0;
	vec3 c = vec3(0.0);
	float hdr = 0.0;
	vec3 hc = vec3(0.0);
	bool at0 = d.x == 0.0 && d.y == 0.0;
	if (kind < 0.5) {
		vec3 wc = far ? C_WINDOW_DIM : C_WINDOW;
		if (at0) { c += wc * a * (far ? 0.75 : 0.95); hdr = a * bloom_lamp; hc = wc; }
		if (!far) c += C_WINDOW * 0.35 * a * glow_w(d, 2.0);
	} else if (kind < 1.5) {
		if (at0) { c += C_LANTERN * a * (path ? 0.75 : 0.9); hdr = a * bloom_lamp; hc = C_LANTERN; }
		c += C_LANTERN * 0.4 * a * (path ? 0.8 : 1.0) * glow_w(d, 2.0);
	} else if (kind < 2.5) {
		if (at0) c += C_STAR * a * 0.6;
	} else if (kind < 3.5) {
		if (at0) { c += (fl > 0.85 ? C_FIRE_HOT : C_FIRE) * a; hdr = a * bloom_fire; hc = C_FIRE; }
		if (d.x == 0.0 && d.y == -1.0 && fl > 0.7) c += C_LANTERN * a * 0.6;
		c += C_LANTERN * 0.45 * fl * a * glow_w(d, 3.0);
		if (at0) c += C_EMBER * v_a.w;
	} else if (kind > 4.5) {
		// a floating lantern on the river and its reflection just below it
		if (at0) { c += C_LANTERN * a * 0.85; hdr = a * bloom_lamp; hc = C_LANTERN; }
		if (d.x == 0.0 && d.y == 1.0) c += C_LANTERN * a * 0.3;
		c += C_LANTERN * 0.35 * a * glow_w(d, 2.0);
	} else {
		if ((d.x == -1.0 || d.x == 0.0) && d.y == 0.0) c += C_FIRE * a;
		if (d.x == 0.0 && d.y == -1.0) { c += (fl > 0.8 ? C_FIRE_HOT : C_FIRE) * a; hdr = a * bloom_fire * 1.6; hc = C_FIRE; }
		if (fl > 0.86 && d.y == -2.0 && d.x == -1.0 + (sin(t * 13.0 + v_b.y) > 0.0 ? 1.0 : 0.0)) c += C_LANTERN * a * 0.7;
		c += C_LANTERN * 0.5 * fl * a * glow_w(d - vec2(0.0, -1.0), 6.0);
		if (at0) c += C_EMBER * v_a.w;
	}
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + hc / 255.0 * hdr, 1.0);
}
