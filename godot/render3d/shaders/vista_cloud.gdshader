// The sea of clouds below the lookout (W3Vista): weather lying over the lowland beyond the region's
// ring, a separate thing from the 遠化 (which drains the land itself: vista_common v_air).
// Round 4, second pass (lead: "the clouds still read as rocks: opaque white lumps, a hard lower
// silhouette, flat white inside"): no longer a lifted height field but banks of billows, each billow
// a round puff facing the eye (vista3d.gd _build_mist lays them out: a body of big billows along the
// bank's base, a crown heaped toward its middle, a few heads breaking the top, thin fringes round its
// edge). A cloud is light and air:
//   * the light comes in big masses: a billow is lit by a normal half its own (a sphere's) and half
//     the whole bank's (an ellipsoid round the bank), so each bank has one sunlit side and one
//     shaded side, with the billows' roundness riding on them; the top of the bank is in the light,
//     the low parts sink into a blue-grey shade, deepest at the base;
//   * no hard outline anywhere: the last part of every billow's radius thins out, the base of the
//     bank dissolves into the air (no flat cut), the fringes are more air than cloud, and the
//     thinning is stippled on the pixel lattice of directions (fixed to the world as she turns her
//     head), a pixel-art soft edge rather than an airbrush;
//   * light shines through the thin edges: a silver lining round the billows toward the sun, bright
//     when the light comes from behind them;
//   * where a billow meets a hillside it fades out over the last metres before the slope (the
//     depth of the land behind it), so a bank lies against the escarpment instead of cutting it.
// The banks creep east with a light wind (wrapping round their domain far beyond the front) and form
// and dissolve with the room they have (vista3d.gd writes it into cloud_tex G: none over the lane
// open toward the town, near the ring, over high ground or toward the 遠化 front). Instance
// transform: origin = the billow's centre; basis x = (bank radius, bank height, bank base y), y = the
// bank's centre, z = (billow radius, seed, cover). Drawn back to front (vista3d.gd sorts the banks).
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
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

varying vec3 v_c;              // the billow's centre (drifted)
varying vec3 v_bc;             // the bank's centre (drifted)
varying vec3 v_bank;           // bank radius, height, base y
varying vec3 v_b;              // billow radius (as it stands now), seed, cover (with the room)
varying vec3 v_right;
varying vec3 v_up;
varying vec3 v_to;
varying vec2 v_q;
varying vec3 v_wp;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec3 bk = MODEL_MATRIX[0].xyz;
	vec3 bc = MODEL_MATRIX[1].xyz;
	vec3 b = MODEL_MATRIX[2].xyz;
	vec3 shift = v_cloud_shift(bc.xz);
	o += shift;
	bc += shift;
	// the room the bank has where it is now: without it the bank dissolves, shrinking toward the
	// middle of its base (never a ghost of the whole bank: a thin veil over a wide area read as a
	// halftone screen)
	float room = v_cloud_room(bc.xz);
	float k = mix(0.25, 1.0, smoothstep(0.0, 0.3, room));
	vec3 foot = vec3(bc.x, bk.z, bc.z);
	o = foot + (o - foot) * k;
	bc = foot + (bc - foot) * k;
	bk.xy *= k;
	// (and each billow swells and settles a little, slowly)
	float r = b.x * k * (1.0 + 0.06 * sin(cloud_time * 0.05 + b.y * 40.0));
	vec3 to = normalize(eye - o);
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to));
	vec3 up = cross(to, right);
	// (the quad a little larger than the billow, for the bumps of its edge; it stands at the
	// billow's front, so the land behind the billow never cuts it)
	vec2 q = (UV - 0.5) * vec2(2.0, -2.0) * 1.15;
	vec3 wp = o + to * r * 0.9 + (right * q.x + up * q.y) * r;
	v_c = o;
	v_bc = bc;
	v_bank = bk;
	v_b = vec3(r, b.y, b.z * smoothstep(0.0, 0.12, room));
	v_right = right;
	v_up = up;
	v_to = to;
	v_q = q;
	v_wp = wp;
	POSITION = room < 0.01 ? vec4(0.0, 0.0, 0.0, -1.0) : v_project(wp, eye, PROJECTION_MATRIX);
}

void fragment() {
	vec2 q = v_q;
	float r = v_b.x;
	float seed = v_b.y;
	float R = v_bank.x;
	float H = v_bank.y;
	float base = v_bank.z;
	// the billow's outline: round, with smaller lumps on it (a cauliflower's), turning slowly
	float l = length(q);
	vec2 dq = q / max(l, 1e-4);
	float lump = w3_vnoise(dq * 2.2 + seed * 37.0 + vec2(cloud_time * 0.004, 0.0)) * 0.6
		+ w3_vnoise(dq * 5.3 + seed * 11.0) * 0.4;
	float rr = l / (1.0 - 0.26 * lump);
	if (rr > 1.0) {
		discard;
	}
	// the point on the billow seen here (a sphere's front) and its normal
	float nz = sqrt(max(1.0 - rr * rr, 0.0));
	vec3 n = normalize(v_right * q.x + v_up * q.y + v_to * nz);
	vec3 sp = v_c + n * r;
	// the light's direction (kept a little above the horizon and below the zenith: the masses read
	// at every hour)
	vec3 s0 = normalize(w3_sun_dir);
	vec2 sh = normalize(s0.xz + vec2(1e-4));
	float se = clamp(s0.y, 0.14, 0.6);
	vec3 sd = normalize(vec3(sh.x * sqrt(1.0 - se * se), se, sh.y * sqrt(1.0 - se * se)));
	// the big masses: half the billow's own normal, half the bank's (an ellipsoid round the bank)
	vec3 rel = (sp - v_bc) / vec3(R, H, R);
	vec3 nb = normalize(rel / vec3(R, H, R) * R);
	vec3 nl = normalize(mix(n, nb, 0.78));
	// (and a little of the billows' own churning inside the light)
	float churn = w3_vnoise(q * 2.6 + seed * 19.0) - 0.5;
	float lit = smoothstep(-0.1, 0.55, dot(nl, sd) + churn * 0.18);
	// height in the bank: its top in the light, its low parts in its own blue-grey shade
	float hb = clamp((sp.y - base) / max(H, 1.0), 0.0, 1.0);
	vec3 col = mix(deep_col, shade_col, smoothstep(0.05, 0.55, hb));
	col = mix(col, lit_col, lit * mix(0.3, 1.0, smoothstep(0.2, 0.7, hb)));
	// light through the thin edge, brightest when it comes from behind the billow (a silver lining)
	vec3 v = normalize(sp - eye);
	float back = pow(clamp(dot(v, sd) * 0.5 + 0.5, 0.0, 1.0), 3.0);
	float rim = smoothstep(0.62, 0.97, rr) * smoothstep(-0.35, 0.35, dot(n, sd));
	col = mix(col, rim_col, rim * (0.2 + 0.7 * back) * (1.0 - night * 0.6));
	// (the world's grade lifts the light end: the brightest cloud is painted a little under white,
	// so its tones survive the grade instead of clipping together)
	vec3 c = w3_srgb_to_linear(col * 0.86);
	// at night the city's lights glow on the undersides of the banks near it
	c += v_city_glow(sp) * 9.0 * (1.0 - smoothstep(0.1, 0.8, hb));
	c = v_air_only(c, sp, eye, FRAGCOORD.xy);
	// the cover. The edge: crisp round the top, where the light draws the billow's round edge (a
	// pixel and a half), melting over much more of the radius below; the base dissolves into the
	// air. Both thinning bands are dithered on the lattice of directions (an ordered pattern fixed to
	// the world as she turns her head): a soft edge in pixels, not an airbrush and not specks.
	float dist = length(v_wp - eye);
	float r_px = max(r / dist * v_ppr, 1.0);
	// (only the billows along the bank's base melt below: one higher up sits over the others, and
	// a dithered lower edge there drew every billow as a bubble)
	float at_base = 1.0 - smoothstep(0.7, 1.3, (v_c.y - base) / r);
	float up_side = smoothstep(0.35, -0.6, dq.y) * at_base;
	float soft = clamp(mix(1.6 / r_px, max(0.4, 3.0 / r_px), up_side), 0.02, 0.6);
	float edge = 1.0 - smoothstep(1.0 - soft, 1.0, rr);
	float b_w = max(r * 0.4, 3.0 * dist / v_ppr);
	float low = smoothstep(base - b_w * 0.6, base + b_w, sp.y);
	float th = v_bayer(v_dir_cell(sp, eye));
	if (edge * low < th) {
		discard;
	}
	float a = v_b.z;
	// fading out before a slope behind it (the land's depth here against the billow's front)
	float d = texture(depth_tex, SCREEN_UV).r;
	vec4 vv = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, d, 1.0);
	float scene = -vv.z / vv.w;
	a *= clamp((scene - dist) / (r * 1.2), 0.0, 1.0);
	if (a <= 0.004) {
		discard;
	}
	ALBEDO = c;
	ALPHA = a;
}
