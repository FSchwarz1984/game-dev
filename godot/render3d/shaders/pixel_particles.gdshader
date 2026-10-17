// Pixel particles (motes, fireflies, smoke, rain, sparks): camera-facing squares and streaks of
// whole native pixels, positioned on the screen-texel lattice so they step pixel by pixel. Drawn
// after the screen post with the shared fog; out of the depth of field's sharp band each one opens
// into a soft disc of its blur radius (G5R3-28), in the band it stays sharp. Emissive values above 1 bloom (fireflies,
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
varying flat float v_coc;   // the depth of field's blur radius here (native px; 0 sharp)

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec3 a = o + w3_snap(o);
	vec2 size = INSTANCE_CUSTOM.xy + vec2(INSTANCE_CUSTOM.w * 2.0);
	// (G5R3-28: out of focus a particle opens into a soft disc of the depth of field's radius at its
	// own depth, as the lamps' flames do in the post; in the sharp band it stays one or two pixels)
	float coc = w3_dof.x > 0.0 ? w3_coc(w3_depth(o)) : 0.0;
	v_coc = coc;
	if (coc > 0.5) {
		// (grown by whole pixels on both sides, so the pixels stay where the sharp particle's are)
		vec2 want = vec2(ceil(2.0 * (max(coc, max(INSTANCE_CUSTOM.x, INSTANCE_CUSTOM.y) * 0.5) + 1.5)));
		size += 2.0 * ceil(max(want - size, vec2(0.0)) * 0.5);
	}
	vec2 off = (UV - 0.5) * size;
	off = floor(off + 0.5);
	// (a mote is so many screen pixels at any depth: G5R3-27)
	vec3 wp = a + w3_px_to_world(off * w3_px_scale(a));
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
	// sharp: the core, and the halo: a one-pixel cross around it at a third of the strength
	float a_sharp = 0.0;
	if (abs(q.x) <= core.x && abs(q.y) <= core.y) {
		a_sharp = v_col.a;
	} else if (v_cus.w > 0.0) {
		vec2 dq = max(abs(q) - core, vec2(0.0));
		if (!(dq.x > 0.0 && dq.y > 0.0) && max(dq.x, dq.y) <= v_cus.w) {
			a_sharp = v_col.a * 0.35;
		}
	}
	// out of focus: a soft disc (an ellipse for a streak) as wide as the blur, its light spread over
	// it (the peak falls with the area, so it never comes out brighter than the sharp particle)
	float k = smoothstep(0.5, 1.5, v_coc);
	float a_disc = 0.0;
	if (k > 0.0) {
		vec2 r = max(vec2(v_coc), core);
		float d = length(q / r);
		float edge = 0.5 / min(r.x, r.y);
		float area0 = max(4.0 * core.x * core.y, 1.0) + (v_cus.w > 0.0 ? 1.4 : 0.0);
		float area1 = 3.14159 * (r.x + 0.25) * (r.y + 0.25);
		a_disc = v_col.a * min(area0 / area1, 1.0) * (1.0 - smoothstep(1.0 - edge, 1.0 + edge, d));
	}
	// (continuous transparency since round 4: no ordered dither)
	float aq = mix(a_sharp, a_disc, k);
	if (aq <= (k > 0.0 ? 0.004 : 0.01)) discard;
	vec3 col = v_col.rgb;
	col = w3_apply_fog(col, v_wp, cell);
	ALBEDO = col;
	ALPHA = min(aq, 1.0);
}
