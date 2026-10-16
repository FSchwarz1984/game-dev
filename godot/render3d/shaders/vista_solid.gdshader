// Solid things in the view from the lookout (W3Vista): the great camphor's crown and trunk, the
// rocks of the lookout, the kiln. Vertex colour as albedo; toon sun in three bands with the painted
// shade; leaves: a world-anchored clump pattern (lit crowns, dark gaps) and a silhouette broken into
// leaf clusters where the surface turns away from the camera; then the same air as the land.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_back;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform float leafy = 0.0;          // 1: foliage (clumps, broken silhouette)
uniform float clump_m = 1.4;        // clump size, metres
uniform vec3 emission_col : source_color = vec3(0.0);
uniform float emission_energy = 0.0;

varying vec3 v_wp;
varying vec3 v_n;
varying vec3 v_alb;
varying vec2 v_pat;

void vertex() {
	v_wp = VERTEX;
	v_n = NORMAL;
	v_pat = UV2;
	POSITION = v_project(VERTEX, eye, PROJECTION_MATRIX);
}

void fragment() {
	vec3 n = normalize(v_n);
	vec3 alb = w3_srgb_to_linear(COLOR.rgb);
	if (leafy > 0.5) {
		vec3 q = v_wp / clump_m;
		float c = w3_vnoise(q.xz + q.y * 0.7) * 0.6 + w3_vnoise(q.xy * 1.7 + 3.0) * 0.4;
		vec3 vdir = normalize(eye - v_wp);
		float rim = 1.0 - abs(dot(n, vdir));
		// leaf clusters break the silhouette
		if (rim > 0.72 && c < 0.5) discard;
		alb *= c > 0.66 ? 1.14 : (c < 0.34 ? 0.66 : 0.92);
		if (w3_hash(floor(v_wp.xz * 3.0 + v_wp.y * 2.0)) < 0.05) alb *= 0.8;
	}
	if (v_pat.x > 0.5) {
		// the surface patterns of the top-down world (w3_pattern: the rocks' granite, grain, lichen and
		// moss), on cells fixed to the surface about a pixel wide (texel for pixel near the eye)
		vec3 an = abs(n);
		vec2 pl = an.y > 0.6 ? v_wp.xz : (an.x > an.z ? v_wp.zy : v_wp.xy);
		vec2 cell = floor(pl / max(0.04, length(v_wp - eye) * 0.0027));
		// (the lookout's rocks are trodden: less moss on their tops than the woods' boulders)
		alb = w3_pattern(alb, v_pat.x, v_pat.y * 0.3 - 0.15, v_wp, n, cell);
	}
	v_alb = alb;
	ALBEDO = vec3(1.0);
	vec3 em = emission_col * emission_energy;
	// (in the 遠化: leafy things from the green block, the rest from the earths)
	int plate = leafy > 0.5 ? V_GREEN : V_EARTH;
	EMISSION = v_print(v_air(w3_ambient(alb, n, COLOR.a), v_wp, eye, FRAGCOORD.xy), v_flat(plate, alb), plate, vec3(0.0, 1.0, 0.0), v_wp, eye, FRAGCOORD.xy) + em * v_print_sun(v_wp, eye, FRAGCOORD.xy);
	EMISSION += w3_lamp_light(alb, v_wp, n, floor(v_wp.xz * 8.0), 1.0) * v_air_keep(v_wp, eye, FRAGCOORD.xy) * (1.0 - v_drain(v_wp.xz, v_wp.y));
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		DIFFUSE_LIGHT += v_sun_bands(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_wp, eye) * v_air_keep(v_wp, eye, FRAGCOORD.xy);
	}
}
