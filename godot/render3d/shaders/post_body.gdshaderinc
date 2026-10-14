// Screen post for one outline class (a full-screen quad in the transparent pass, gated by the
// stencil reference its class file sets). It reads the opaque image and depth once:
//   * silhouette: a pixel whose neighbour is clearly farther is on the near edge of something ->
//     darker, cooler shade of its own colour (never black; one native pixel wide),
//   * crease: second difference of depth among continuous neighbours (orthographic depth is linear,
//     so flat planes give zero): concave -> darker, convex -> a lighter catch,
//   * fog: valley mist by absolute height, and haze for whatever lies far below her.
// Class parameters come from #defines in the class file:
//   OL_SIL (0..1) silhouette strength, OL_CREASE (0..1), OL_TINT (vec3 dark multiplier),
//   OL_RIM (0/1) warm highlight rim instead of a dark line (the current target).
#include "res://render3d/shaders/pixel_toon.gdshaderinc"
#include "res://render3d/shaders/fog.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float w3_view_depth(vec2 uv, mat4 inv_proj) {
	float d = texture(depth_tex, uv).r;
	vec4 v = inv_proj * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	vec2 uv = SCREEN_UV;
	mat4 ip = INV_PROJECTION_MATRIX;
	float c = w3_view_depth(uv, ip);
	float l = w3_view_depth(uv - vec2(px.x, 0.0), ip);
	float r = w3_view_depth(uv + vec2(px.x, 0.0), ip);
	float u = w3_view_depth(uv - vec2(0.0, px.y), ip);
	float d = w3_view_depth(uv + vec2(0.0, px.y), ip);
	vec3 col = texture(screen_tex, uv).rgb;

	// world position of this pixel
	float raw = texture(depth_tex, uv).r;
	vec4 vp = ip * vec4(uv * 2.0 - 1.0, raw, 1.0);
	vp.xyz /= vp.w;
	vec3 wp = (INV_VIEW_MATRIX * vec4(vp.xyz, 1.0)).xyz;
	vec2 cell = w3_ptex(wp);

	float far_n = max(max(l, r), max(u, d)) - c;      // > 0: a neighbour lies behind me
	float sil = step(0.35, far_n);
	// the neighbour behind: the line is a darker shade of whichever side is darker, so a pale object
	// keeps its edge against a mid-tone ground (selective outline, never black)
	vec2 behind = vec2(-px.x, 0.0);
	float bd = l;
	if (r > bd) { bd = r; behind = vec2(px.x, 0.0); }
	if (u > bd) { bd = u; behind = vec2(0.0, -px.y); }
	if (d > bd) { bd = d; behind = vec2(0.0, px.y); }
	vec3 bcol = texture(screen_tex, uv + behind).rgb;
#if OL_RIM
	if (sil > 0.0) {
		col = mix(col, vec3(1.0, 0.86, 0.55) * (0.6 + w3_luma(col) * 0.8), 0.85);
	}
#else
	if (sil > 0.0) {
		vec3 base = w3_luma(bcol) < w3_luma(col) ? mix(col, bcol, 0.6) : col;
		col = mix(col, base * OL_TINT, OL_SIL);
	} else if (OL_CREASE > 0.0) {
		// only among neighbours on the same surface
		float th = 0.25;
		bool cont = abs(l - c) < th && abs(r - c) < th && abs(u - c) < th && abs(d - c) < th;
		if (cont) {
			float lap = max(l + r - 2.0 * c, u + d - 2.0 * c);
			float lap2 = min(l + r - 2.0 * c, u + d - 2.0 * c);
			if (lap > 0.06) {
				col = mix(col, col * mix(OL_TINT, vec3(1.0), 0.45), OL_CREASE);          // concave: a valley line
			} else if (lap2 < -0.06) {
				col = mix(col, col * 1.18 + vec3(0.012), OL_CREASE * 0.8);             // convex: light catches the edge
			}
		}
	}
#endif
	col = w3_apply_fog(col, wp, cell);
	ALBEDO = col;
	ALPHA = 1.0;
}
