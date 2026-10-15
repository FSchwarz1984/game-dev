// The sea of clouds below the lookout (W3Vista): weather lying over the lowland beyond the region's
// ring, a separate thing from the 遠化 (which drains the land itself: vista_common v_air). Billows
// with volume: domes on three scales (big banks, the billows riding on them, small heads breaking
// their tops) on jittered grids, thinned by a slow cover field into banks with gaps where the plain
// shows below (vista_common v_cloud_field). The top surface is a radial grid lifted by the same field
// in the vertex stage; every pixel recomputes the field (crisp gap edges, its own normal). Lit in
// steps from a sun never higher than about 33 degrees (a high sun would leave every top the same
// white): the tops in the sun, the sides in the cool shade, the foot of each billow deepest; the
// rims that face the sun but turn away from her eye catch a brighter line. Near is big and far is
// small by perspective; far away the billows settle into calmer bands. Then the vista's haze.
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
// (the tones are mixed as painted, in sRGB, then turned linear: mixed linear, every middle tone
// came out nearly white)
uniform vec3 lit_col = vec3(0.98, 0.97, 0.94);
uniform vec3 shade_col = vec3(0.70, 0.74, 0.84);
uniform vec3 deep_col = vec3(0.50, 0.55, 0.68);
uniform vec3 rim_col = vec3(1.0, 1.0, 0.98);
uniform float night = 0.0;

varying vec3 v_wp;

float lod_at(float dist) {
	return smoothstep(2400.0, 7000.0, dist);
}

void vertex() {
	float dist = length(VERTEX - eye);
	vec3 f = v_cloud_field(VERTEX.xz, lod_at(dist));
	VERTEX.y = sea_base + (f.x > 0.5 ? f.x : -60.0);
	v_wp = VERTEX;
	POSITION = v_project(VERTEX, eye, PROJECTION_MATRIX);
}

void fragment() {
	vec2 xz = v_wp.xz;
	float dist = length(v_wp - eye);
	float lod = lod_at(dist);
	vec3 f = v_cloud_field(xz, lod);
	// (and where the grid's triangles stretch down into a gap, they are not cloud: only the top
	// surface is drawn, within the grid's chord error of the field)
	if (f.x < 0.6 || v_wp.y < sea_base + f.x - max(1.5, dist * 0.005)) {
		discard;
	}
	vec3 n = normalize(vec3(-f.y, 1.0, -f.z));
	vec3 s0 = normalize(w3_sun_dir);
	vec2 sh = normalize(s0.xz + vec2(1e-4));
	float se = clamp(s0.y, 0.12, 0.55);
	vec3 sd = normalize(vec3(sh.x * sqrt(1.0 - se * se), se, sh.y * sqrt(1.0 - se * se)));
	// band seams scattered on cells fixed to the cloud (about a pixel), so a pan carries them along
	vec2 cell = v_dir_cell(v_wp, eye);
	float dz = (w3_hash(cell * 1.31 + 2.7) * 0.7 + w3_vnoise(cell / 1.9) * 0.3 - 0.5) * 0.06;
	float l = dot(n, sd);
	float lvl = l > 0.72 + dz ? 1.0 : (l > 0.46 + dz ? 0.76 : (l > 0.18 + dz ? 0.44 : 0.14));
	vec3 col = mix(shade_col, lit_col, lvl);
	// the foot of each billow, where it sinks into the bank or the next one: the deepest shade
	float foot = 1.0 - smoothstep(3.0, 20.0, f.x);
	if (foot > 0.5 + dz * 4.0 && n.y < 0.8) {
		col = mix(col, deep_col, 0.8);
	}
	// a bright rim where a billow's edge faces the sun and turns away from her eye
	vec3 v = normalize(eye - v_wp);
	float edge = 1.0 - abs(dot(n, v));
	if (edge > 0.82 && l > 0.25 && foot < 0.3) {
		col = mix(col, rim_col, 0.7);
	}
	// far away the billows settle: their steps flatten toward the lit band
	col = mix(col, mix(shade_col, lit_col, 0.78), lod * 0.55);
	// (the world's grade lifts the light end: the brightest cloud is painted a little under white,
	// so its tones survive the grade instead of clipping together)
	ALBEDO = v_air_only(w3_srgb_to_linear(col * 0.84), v_wp, eye, FRAGCOORD.xy);
}
