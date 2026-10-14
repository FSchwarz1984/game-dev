// Light shafts through the canopy: additive ribbons from the canopy down to the ground along the
// sun's direction (follows the time of day through w3_sun_dir), soft across, faded at both ends,
// breathing slowly, quantised and dithered on the texel lattice. Only while the sun is up.
// Instance: origin = ground point; INSTANCE_CUSTOM = (length m, width px, strength, phase).
shader_type spatial;
render_mode world_vertex_coords, unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

varying vec3 v_wp;
varying vec2 v_uv;
varying flat vec4 v_cus;

void vertex() {
	vec3 g = MODEL_MATRIX[3].xyz;
	vec3 sd = normalize(w3_sun_dir);
	vec3 t = g + sd * min(INSTANCE_CUSTOM.x / max(sd.y, 0.5), 11.0);
	vec2 d = w3_screen(t) - w3_screen(g);
	vec2 pn = normalize(vec2(-d.y, d.x) + vec2(1e-4));
	vec3 wp = mix(g, t, UV.y) + w3_px_to_world(pn * (UV.x - 0.5) * INSTANCE_CUSTOM.y);
	VERTEX = wp;
	v_wp = wp;
	v_uv = UV;
	v_cus = INSTANCE_CUSTOM;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	float across = 1.0 - abs(v_uv.x - 0.5) * 2.0;
	float along = smoothstep(0.0, 0.25, v_uv.y) * (1.0 - smoothstep(0.55, 1.0, v_uv.y));
	float breath = 0.75 + 0.25 * sin(w3_time * 0.6 + v_cus.w);
	// strongest when the sun is low (dawn, late afternoon), gone at noon and at night
	float low = smoothstep(0.16, 0.32, w3_sun_dir.y) * (1.0 - smoothstep(0.5, 0.72, w3_sun_dir.y));
	float sun_up = low * (1.0 - w3_night) * (1.0 - w3_wet);
	float a = across * across * along * breath * v_cus.z * sun_up;
	float aq = floor(a * 4.0 + w3_bayer4(cell) * 0.999) / 4.0;
	if (aq <= 0.0) discard;
	ALBEDO = w3_sun * vec3(1.0, 0.94, 0.78) * aq * 0.11;
}
