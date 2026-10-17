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
// verification (sample.gd --crawl): 1 draws the view depth (R: m / 1000, under 1 even for the
// orthographic camera 120 m back), the class (G: / 10) and a marker (B 0.777) instead of the picture
global uniform float w3_dbg;
#ifndef OL_CLASS
#define OL_CLASS 0
#endif
// depth of field (G5R3-28; PixelView3D.DOF_LEVELS, B in the sample; w3_dof and w3_coc in
// pixel_toon): a tilt-shift blur by depth, gathered here at the native resolution. Only the classes
// that #define OL_DOF blur (the ground, the solid things, the foliage, the ground cover); the
// characters (3) and the target (4) never do, and their colour never spreads onto what lies behind
// them. (The particles blur themselves: pixel_particles.)
const float W3_DOF_GLOW = 1.5;      // how much more an HDR highlight (a flame, a lit window) weighs: small bright discs

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float w3_view_depth(vec2 uv, mat4 inv_proj) {
	float d = texture(depth_tex, uv).r;
	vec4 v = inv_proj * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

// scatter-as-gather over the whole pixels of a disc: a sample counts where its own blur reaches this
// pixel; one nearer than this pixel (a blurred bough in front) spreads over it by its own radius, one
// on the same surface or behind only within both radii (so a sharp thing never smears, and a sharp
// thing behind a blurred one is not pulled forward). Disc edges are soft by a pixel; highlights weigh more.
vec3 w3_dof_gather(vec2 uv, vec2 px, mat4 ip, float dc, float rc, vec3 cc) {
	float rmax = w3_dof.x;
	// a first look round (8 samples at the full radius): nothing blurred near and this one sharp -> as is
	if (rc < 0.25) {
		float reach = 0.0;
		for (int k = 0; k < 8; k++) {
			float a = float(k) * 0.785398;
			vec2 o = round(vec2(cos(a), sin(a)) * rmax);
			float ds = w3_view_depth(uv + o * px, ip);
			if (ds < dc - 0.5) {
				reach = max(reach, w3_coc(ds) - length(o) + 0.5);
			}
		}
		if (reach <= 0.0) {
			return cc;
		}
	}
	vec3 acc = cc;
	float wsum = 1.0;
	int R = int(ceil(rmax));
	for (int y = -R; y <= R; y++) {
		for (int x = -R; x <= R; x++) {
			if (x == 0 && y == 0) {
				continue;
			}
			vec2 o = vec2(float(x), float(y));
			float dist = length(o);
			if (dist > rmax + 0.5) {
				continue;
			}
			vec2 suv = uv + o * px;
			float ds = w3_view_depth(suv, ip);
			float rs = w3_coc(ds);
			float reach = ds < dc - 0.5 ? rs : min(rs, rc);
			float w = clamp(reach - dist + 0.5, 0.0, 1.0);
			if (w <= 0.0) {
				continue;
			}
			vec3 cs = texture(screen_tex, suv).rgb;
			w *= 1.0 + W3_DOF_GLOW * max(w3_luma(cs) - 1.0, 0.0);
			acc += cs * w;
			wsum += w;
		}
	}
	return acc / wsum;
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
	// (the depth of field: where this pixel is blurred its lines fade with it)
	float lines = 1.0;
#ifdef OL_DOF
	if (w3_dof.x > 0.0) {
		float rc = w3_coc(c);
		col = w3_dof_gather(uv, px, ip, c, rc, col);
		lines = 1.0 - smoothstep(0.6, 1.6, rc);
	}
#endif

	// world position of this pixel
	float raw = texture(depth_tex, uv).r;
	vec4 vp = ip * vec4(uv * 2.0 - 1.0, raw, 1.0);
	vp.xyz /= vp.w;
	vec3 wp = (INV_VIEW_MATRIX * vec4(vp.xyz, 1.0)).xyz;
	vec2 cell = w3_ptex(wp);

	float far_n = max(max(l, r), max(u, d)) - c;      // > 0: a neighbour lies behind me
	float sil = step(0.35, far_n) * lines;
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
		if (cont && lines > 0.0) {
			float lap = max(l + r - 2.0 * c, u + d - 2.0 * c);
			float lap2 = min(l + r - 2.0 * c, u + d - 2.0 * c);
			if (lap > 0.06) {
				col = mix(col, col * mix(OL_TINT, vec3(1.0), 0.45), OL_CREASE * lines);  // concave: a valley line
			} else if (lap2 < -0.06) {
				// convex: light catches the edge (the small lift only where there is light to catch: on a
				// near-black surface at night it drew a faint wireframe; the buffer is linear since round 4)
				col = mix(col, col * 1.18 + vec3(0.012) * smoothstep(0.0, 0.06, w3_luma(col)), OL_CREASE * 0.8 * lines);
			}
		}
	}
#endif
#ifdef OL_FOG
	col = mix(col, w3_apply_fog(col, wp, cell), OL_FOG);
#else
	col = w3_apply_fog(col, wp, cell);
#endif
	if (w3_dbg > 0.5) {
		col = vec3(c / 1000.0, float(OL_CLASS) / 10.0, 0.777);
	}
	ALBEDO = col;
	ALPHA = 1.0;
}
