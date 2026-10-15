// Light shafts through the canopy: additive ribbons from a crown's rim down to the ground along the
// sun's direction (they follow the time of day through w3_sun_dir, so they come from the upper left
// like the rest of the light), soft across, faded at both ends, breathing and drifting slowly.
// Strongest with a low sun (morning, late afternoon), weaker at noon, gone at night and in rain.
// Continuous brightness (round 4: no steps anywhere). Under a high sun a ribbon stands almost
// straight up and reads from above as a pale smudge on the grass, so near noon they all but go (the
// volumetric fog draws the real shafts of the low sun). They thin out over her, so they never lie
// hard on her face.
// Instance: origin = ground point; INSTANCE_CUSTOM = (length m, width px, strength, phase).
shader_type spatial;
render_mode world_vertex_coords, unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

varying vec3 v_wp;
varying vec2 v_uv;
varying flat vec4 v_cus;

void vertex() {
	vec3 g = MODEL_MATRIX[3].xyz;
	// a slow sideways drift (the leaves above move): about 30 cm over half a minute
	g.x += sin(w3_time * 0.11 + INSTANCE_CUSTOM.w) * 0.3;
	vec3 sd = normalize(w3_sun_dir);
	vec3 t = g + sd * min(INSTANCE_CUSTOM.x / max(sd.y, 0.5), 14.0);
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
	float along = smoothstep(0.0, 0.3, v_uv.y) * (1.0 - smoothstep(0.5, 1.0, v_uv.y));
	float breath = 0.7 + 0.3 * sin(w3_time * 0.5 + v_cus.w);
	float sy = w3_sun_dir.y;
	float day = smoothstep(0.1, 0.25, sy) * (1.0 - w3_night) * (1.0 - w3_wet);
	float low = 1.0 - smoothstep(0.45, 0.72, sy);
	// over her: thinned out within a few pixels of her body
	vec2 me = w3_screen(w3_player.xyz);
	float dme = length((w3_screen(v_wp) - me) * vec2(1.0, 0.6));
	float clear = w3_player.w > 0.0 ? smoothstep(12.0, 30.0, dme) : 1.0;
	float a = across * across * along * breath * v_cus.z * day * low * clear;
	if (a <= 0.004) discard;
	ALBEDO = w3_sun * vec3(1.0, 0.93, 0.74) * a * 0.06;
}
