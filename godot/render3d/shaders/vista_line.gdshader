// Thin built things in the view from the lookout (W3Vista): the railway's viaduct and its iron bridge,
// the suspension bridge's cables and deck, the 「隔」 tower's legs and braces. Each instance is a
// straight member from one point to another, drawn in screen pixels as a band between its ends and
// never thinner than its minimum in native pixels (so a far pier or a cable stays one whole pixel
// wide instead of breaking into dots), lit in two tones by the sun across it, then the same air.
// The lanterns of the home are members too: a short upright mark, never under two pixels, glowing.
// Instance: basis column 0 = from (world), column 1 = to, column 2 = (half width m, minimum px,
// side shade 0..1 (2: a lamp)); INSTANCE_CUSTOM.x = emission; COLOR = albedo (sRGB).
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform vec3 light_col = vec3(1.0);       // the hour's light (linear), like the figures'
uniform vec3 ambient_col = vec3(0.4);
uniform float lamp_on = 0.0;              // the lamps' glow (members flagged with side shade 2)

varying vec3 v_wp;
varying flat vec4 v_col;
varying flat vec4 v_par;
varying float v_side;

void vertex() {
	vec3 a = MODEL_MATRIX[0].xyz;
	vec3 b = MODEL_MATRIX[1].xyz;
	vec4 par = vec4(MODEL_MATRIX[2].xyz, INSTANCE_CUSTOM.x);
	vec3 p = mix(a, b, UV.x);
	// in screen pixels: the member between its two ends' pixels, its width across that line in
	// pixels (its own width there, never under the minimum)
	vec2 pa = v_px_of(a, eye);
	vec2 pb = v_px_of(b, eye);
	vec2 dir = pb - pa;
	dir = length(dir) > 1e-4 ? normalize(dir) : vec2(0.0, 1.0);
	vec2 side = vec2(-dir.y, dir.x);
	float dist = max(length(p - eye), 0.5);
	float hw = max(par.x * v_ppr / dist, par.y * 0.5);
	v_side = UV.y * 2.0 - 1.0;
	vec2 px = mix(pa, pb, UV.x) + side * v_side * hw;
	POSITION = v_clip(px, dist, PROJECTION_MATRIX);
	v_wp = p;
	v_col = COLOR;
	v_par = par;
}

void fragment() {
	vec3 alb = w3_srgb_to_linear(v_col.rgb);
	// two tones: the half that faces the sun's side lighter
	vec3 sd = normalize(w3_sun_dir);
	float lit = step(0.0, v_side * (sd.x + sd.z) + 0.2) * (1.0 - v_par.z) + v_par.z * 0.5;
	if (v_par.z > 1.5) {
		// a lamp: its flame alone, over 1 so it blooms (it shines through the air)
		if (lamp_on * v_par.w < 0.02) discard;
		ALBEDO = alb * v_par.w * lamp_on;
	} else {
		vec3 c = alb * (ambient_col + light_col * (0.35 + 0.65 * lit) * clamp(sd.y * 3.0, 0.0, 1.0));
		ALBEDO = v_air(c, v_wp, eye, FRAGCOORD.xy) + alb * v_par.w;
		// (in the 遠化's white a viaduct or a bridge is only its drawing)
		if (v_past(v_wp, eye, FRAGCOORD.xy)) ALBEDO = v_paper(0.85);
	}
}
