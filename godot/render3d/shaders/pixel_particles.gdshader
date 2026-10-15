// Pixel particles (motes, fireflies, smoke, rain, sparks): camera-facing squares and streaks of
// whole native pixels, positioned on the screen-texel lattice so they step pixel by pixel and never
// blur. Drawn after the screen post with the shared fog. Emissive values above 1 bloom (fireflies,
// will-o'-wisps); everything else stays under 1.
// Instance: origin = world position; COLOR = rgba;
// INSTANCE_CUSTOM = (width px, height px, shape, glow halo px).
shader_type spatial;
render_mode world_vertex_coords, unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"
#include "res://render3d/shaders/fog.gdshaderinc"

varying vec3 v_wp;
varying flat vec4 v_col;
varying flat vec4 v_cus;
varying vec2 v_q;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec3 a = o + w3_snap(o);
	vec2 size = INSTANCE_CUSTOM.xy + vec2(INSTANCE_CUSTOM.w * 2.0);
	vec2 off = (UV - 0.5) * size;
	off = floor(off + 0.5);
	vec3 wp = a + w3_px_to_world(off);
	VERTEX = wp;
	v_wp = wp;
	v_col = COLOR;
	v_cus = INSTANCE_CUSTOM;
	v_q = (UV - 0.5) * size;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	vec2 core = v_cus.xy * 0.5;
	vec2 q = v_q;
	float a = v_col.a;
	// the halo: a one-pixel cross around the core at a third of the strength
	bool in_core = abs(q.x) <= core.x && abs(q.y) <= core.y;
	if (!in_core) {
		if (v_cus.w <= 0.0) discard;
		vec2 dq = max(abs(q) - core, vec2(0.0));
		if (dq.x > 0.0 && dq.y > 0.0) discard;
		a *= 0.35;
	}
	// (continuous transparency since round 4: no ordered dither)
	float aq = a;
	if (aq <= 0.01) discard;
	vec3 col = v_col.rgb;
	col = w3_apply_fog(col, v_wp, cell);
	ALBEDO = col;
	ALPHA = min(aq, 1.0);
}
