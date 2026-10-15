// The sea of clouds below the lookout (W3Vista): weather lying over the lowland beyond the region's
// ring, a separate thing from the 遠化 (which drains the land itself: vista_common v_air). Billows
// on three scales (big banks, the billows riding on them, small heads breaking their tops) on
// jittered grids, thinned by a slow cover field into banks with gaps where the plain shows below
// (vista_common v_cloud_field). The top surface is a radial grid lifted by the same field in the
// vertex stage; every pixel recomputes the field and its own normal.
// Round 4, second pass (lead: "the clouds still read as rocks"): a cloud is light and air, not a
// solid. (1) The light comes in big masses: the shading normal is mostly the big bank's (the riding
// billows only add a little), the sunward tops bright and warm-white, the sides and the low parts of
// every bank a blue-grey shade, the foot deepest. (2) It has no hard outline: the grid is not pulled
// down into the gaps any more (that drew a crisp cut along the triangles), the cover fades out over
// the last metres of every billow's foot, and the edges seen edge-on (the silhouette against what
// lies behind) turn transparent, so every edge melts into the air with the land showing through.
// (3) Light shines through the thin fringes (a silver lining toward the sun). Drawn back to front.
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
	// (the gaps stay at the base: their pixels are simply transparent)
	VERTEX.y = sea_base + max(f.x, 0.0);
	v_wp = VERTEX;
	POSITION = v_project(VERTEX, eye, PROJECTION_MATRIX);
}

void fragment() {
	vec2 xz = v_wp.xz;
	float dist = length(v_wp - eye);
	float lod = lod_at(dist);
	vec3 f = v_cloud_field(xz, lod);
	// the cover: nothing in the gaps, fading in over the foot of every billow (wider far away, where
	// a metre is a fraction of a pixel)
	float a = smoothstep(0.5, 14.0 + dist * 0.0022, f.x);
	if (a < 0.01) {
		discard;
	}
	// the big masses of light and shade: the bank's own normal, the riding billows only a little
	vec3 big = v_domes(xz, 300.0, 0.38, 0.62, 0.0);
	vec3 nb = normalize(vec3(-big.y, 1.0, -big.z));
	vec3 nd = normalize(vec3(-f.y, 1.0, -f.z));
	vec3 n = normalize(mix(nb, nd, big.x > 0.5 ? 0.35 : 1.0));
	vec3 s0 = normalize(w3_sun_dir);
	vec2 sh = normalize(s0.xz + vec2(1e-4));
	float se = clamp(s0.y, 0.12, 0.55);
	vec3 sd = normalize(vec3(sh.x * sqrt(1.0 - se * se), se, sh.y * sqrt(1.0 - se * se)));
	float l = dot(n, sd);
	float lit = smoothstep(-0.25, 0.75, l);
	// higher in the bank, more light: the tops shine, the lower parts sink into a blue-grey shade
	float top = smoothstep(4.0, 46.0, f.x);
	vec3 under = mix(deep_col, shade_col, 0.35);
	vec3 col = mix(under, shade_col, smoothstep(0.0, 0.5, top));
	col = mix(col, lit_col, lit * mix(0.45, 1.0, top));
	// light through the thin fringes, brightest looking toward the sun (a silver lining)
	vec3 v = normalize(v_wp - eye);
	float thin = 1.0 - smoothstep(0.5, 10.0, f.x);
	float toward = pow(clamp(dot(v, sd) * 0.5 + 0.5, 0.0, 1.0), 2.0);
	col = mix(col, rim_col, thin * (0.2 + 0.55 * toward));
	// far away the billows settle toward an even, lighter tone
	col = mix(col, mix(shade_col, lit_col, 0.72), lod * 0.5);
	// (the world's grade lifts the light end: the brightest cloud is painted a little under white,
	// so its tones survive the grade instead of clipping together)
	ALBEDO = v_air_only(w3_srgb_to_linear(col * 0.84), v_wp, eye, FRAGCOORD.xy);
	// the edges seen edge-on melt into what lies behind (no hard outline against the land)
	float face = abs(dot(nd, -v));
	a *= mix(0.15, 1.0, smoothstep(0.03, 0.32, face));
	ALPHA = a;
}
