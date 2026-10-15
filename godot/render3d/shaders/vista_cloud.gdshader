// The sea of clouds below the lookout (W3Vista): weather lying over the lowland beyond the region's
// ring, a separate thing from the 遠化 (which drains the land itself: vista_common v_air). Billows
// with volume: domes on three scales (big banks, the billows riding on them, small heads breaking
// their tops) on jittered grids, thinned by a slow cover field into banks with gaps where the plain
// shows below (vista_common v_cloud_field). The top surface is a radial grid lifted by the same field
// in the vertex stage; every pixel recomputes the field and its own normal.
// Round 4 (G5R2-1 ⑩: "the cloud looked like a rock"): soft, not carved. The light is continuous
// (a wide wrap from the sun, never brighter than about 33 degrees up, so the tops do not all go the
// same white), the cool shade deepens softly toward the foot of each billow, light shines through
// the thin fringes (brightest toward the sun), and the fringe itself is translucent: where a billow
// thins out at its edge the land shows through it. Drawn back to front (the grid's outer rings
// first). Far away the billows settle into calmer bands. Then the vista's haze.
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled, blend_mix, depth_draw_never;
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
	// (where the grid's triangles stretch down into a gap they are not cloud: only the top surface is
	// drawn, within the grid's chord error of the field)
	if (f.x < 0.3 || v_wp.y < sea_base + f.x - max(1.5, dist * 0.005)) {
		discard;
	}
	vec3 n = normalize(vec3(-f.y, 1.0, -f.z));
	vec3 s0 = normalize(w3_sun_dir);
	vec2 sh = normalize(s0.xz + vec2(1e-4));
	float se = clamp(s0.y, 0.12, 0.55);
	vec3 sd = normalize(vec3(sh.x * sqrt(1.0 - se * se), se, sh.y * sqrt(1.0 - se * se)));
	// soft light: a wide continuous wrap (cloud scatters; there is no terminator line on it)
	float l = dot(n, sd);
	float lit = clamp((l + 0.45) / 1.45, 0.0, 1.0);
	lit = lit * lit * (3.0 - 2.0 * lit);
	vec3 col = mix(shade_col, lit_col, lit);
	// the foot of each billow, where it sinks into the bank or the next one: a softly deeper shade
	float foot = 1.0 - smoothstep(2.0, 26.0, f.x);
	col = mix(col, deep_col, foot * 0.5 * (1.0 - 0.5 * clamp(n.y, 0.0, 1.0)));
	// light through the thin fringes, brightest where she looks toward the sun (a silver lining)
	vec3 v = normalize(v_wp - eye);
	float thin = 1.0 - smoothstep(0.5, 12.0, f.x);
	float toward = pow(clamp(dot(v, sd) * 0.5 + 0.5, 0.0, 1.0), 2.0);
	col = mix(col, rim_col, thin * (0.25 + 0.6 * toward));
	// far away the billows settle toward the lit tone
	col = mix(col, mix(shade_col, lit_col, 0.78), lod * 0.55);
	// (the world's grade lifts the light end: the brightest cloud is painted a little under white,
	// so its tones survive the grade instead of clipping together)
	ALBEDO = v_air_only(w3_srgb_to_linear(col * 0.84), v_wp, eye, FRAGCOORD.xy);
	// the fringe is translucent: the land shows through where a billow thins out
	ALPHA = smoothstep(0.3, 9.0 + dist * 0.0015, f.x);
}
