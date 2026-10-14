// Puffs in the view from the lookout (W3Vista): the kiln's smoke, the hot spring's steam, the mist
// of the 裏見之瀑, the waterfall itself (kind 3: a falling sheet). Camera-facing quads; a round,
// noise-edged body lit from the sun's side, its cover thinned with an ordered dither (no smooth
// alpha), then the same air as the land. Values stay under 1 (no bloom), except the kiln's glow.
// Instance: origin = centre; COLOR = colour (sRGB) and cover 0..1; INSTANCE_CUSTOM = (size m,
// kind, seed, glow). kind: 0 smoke, 1 steam, 2 mist, 3 waterfall sheet (size = width, seed = height).
shader_type spatial;
render_mode world_vertex_coords, unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);

varying vec3 v_wp;
varying flat vec4 v_cus;
varying flat vec4 v_col;
varying vec2 v_uv;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	vec3 to_cam = normalize(eye - o);
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to_cam));
	vec3 up = normalize(cross(to_cam, right));
	vec2 q = UV - 0.5;
	vec3 wp;
	if (int(c.y + 0.5) == 3) {
		// the waterfall: an upright sheet from its top (origin) down by its height
		wp = o + right * q.x * c.x + vec3(0.0, -(q.y + 0.5) * c.z, 0.0);
	} else {
		wp = o + (right * q.x + up * -q.y) * c.x;
	}
	VERTEX = wp;
	v_wp = wp;
	v_cus = c;
	v_col = COLOR;
	v_uv = UV;
}

void fragment() {
	int kind = int(v_cus.y + 0.5);
	vec2 q = v_uv - 0.5;
	float cover = v_col.a;
	vec3 col = w3_srgb_to_linear(v_col.rgb);
	float n = w3_vnoise(q * 6.0 + v_cus.z * 31.0 + vec2(0.0, TIME * 0.3));
	if (kind == 3) {
		// falling water: streaks running down, ragged edges, white foam at the foot
		float x = q.x;
		float streak = w3_vnoise(vec2(x * 18.0, v_uv.y * 3.0 - TIME * 1.6) + v_cus.z);
		float edge = abs(x) * 2.0 + (w3_vnoise(vec2(v_uv.y * 9.0 - TIME * 2.0, 3.0)) - 0.5) * 0.35;
		if (edge > 0.92) discard;
		col = mix(col * 0.78, col * 1.08, step(0.45, streak));
		if (v_uv.y > 0.9) col = col * 1.1;
	} else {
		// a puff is a cluster of three round lumps, not a disc
		float r = min(length(q - vec2(-0.1, 0.06)) * 2.4, min(length(q - vec2(0.13, 0.02)) * 2.6, length(q - vec2(0.0, -0.12)) * 2.5));
		r += (n - 0.5) * 0.35;
		if (r > 1.0) discard;
		// lit from the sun's side
		vec3 sd = normalize(w3_sun_dir);
		vec3 to_cam = normalize(eye - v_wp);
		vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to_cam));
		float lit = dot(vec2(q.x, -q.y), normalize(vec2(dot(right, sd), sd.y) + 1e-4)) * 2.0 + (n - 0.5) * 0.4;
		col *= lit > 0.1 ? 1.06 : (lit < -0.3 ? 0.72 : 0.88);
	}
	float cq = floor(cover * 4.0 + v_bayer8(FRAGCOORD.xy) * 0.999) / 4.0;
	if (cq <= 0.0) discard;
	vec3 c = v_air(col, v_wp, eye, FRAGCOORD.xy);
	c += col * v_cus.w;
	ALBEDO = c;
	ALPHA = min(cq, 1.0);
}
