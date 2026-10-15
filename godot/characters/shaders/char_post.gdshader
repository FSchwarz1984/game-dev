// Screen post, outline class 3, for the 3D characters (replaces render3d/shaders/post_char.gdshader,
// which only fogged the old sprites that carried their own outline). One full-screen quad in the
// transparent pass, drawn only where the stencil holds 3 (her pixels), reading the opaque image and
// depth (docs/knowledge/24-3d-characters.md):
//   * silhouette: a pixel of hers whose neighbour lies well behind her (the ground, the world) gets
//     the outline: a darker, cooler shade of her own colour, one native pixel, never black; the
//     same rule as the world's outline (post_body.gdshaderinc), drawn on her edge pixels;
//   * inner lines: where one part of her stands in front of another (a sleeve over the coat, the
//     hair over the shoulders), a lighter line, so the parts read as drawn shapes;
//   * fog: a third of it (character protection: she reads first, in the morning mist too).
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
stencil_mode read, compare_equal, 3;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"
#include "res://render3d/shaders/fog.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform float sil_gap = 0.22;        // m: a neighbour this far behind is "not her"
uniform float inner_gap = 0.07;      // m: a part of her this far behind another part
uniform float sil_amount = 1.0;
uniform float inner_amount = 0.55;
uniform float fog_share = 0.33;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float view_depth(vec2 uv, mat4 ip) {
	float d = texture(depth_tex, uv).r;
	vec4 v = ip * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

vec3 line_of(vec3 c) {
	// a darker, cooler shade of the colour itself (outline colours of the portraits: hair -> deep
	// violet, skin -> warm brown, cream -> grey-brown, navy -> near-black indigo)
	// dark enough to part her from the packed earth and the grass (half as dark left the cream
	// sleeves' edge the colour of the ground)
	float l = w3_luma(c);
	vec3 d = c * vec3(0.34, 0.30, 0.40);
	return mix(d, d * vec3(1.08, 0.92, 0.95), smoothstep(0.25, 0.6, l));
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	vec2 uv = SCREEN_UV;
	mat4 ip = INV_PROJECTION_MATRIX;
	float c = view_depth(uv, ip);
	// her outline, drawn on her own edge pixels: where a neighbour lies far behind (the ground) and
	// the shape is at least three pixels thick across that edge (the next two pixels inward are hers),
	// so a sleeve or a sash tail two pixels wide keeps its own colour instead of turning into a line
	vec3 col = texture(screen_tex, uv).rgb;
	float sil = 0.0;
	float inner = 0.0;
	vec2 dirs[4] = vec2[](vec2(-1.0, 0.0), vec2(1.0, 0.0), vec2(0.0, -1.0), vec2(0.0, 1.0));
	for (int i = 0; i < 4; i++) {
		vec2 o = dirs[i] * px;
		float out_d = view_depth(uv + o, ip) - c;
		float in1 = view_depth(uv - o, ip) - c;
		float in2 = view_depth(uv - 2.0 * o, ip) - c;
		bool thick = in1 < sil_gap && in2 < sil_gap;
		if (out_d > sil_gap && thick) {
			sil = 1.0;
		} else if (out_d > inner_gap && out_d <= sil_gap && in1 < inner_gap && in2 < inner_gap) {
			inner = 1.0;
		}
	}
	if (sil > 0.5) {
		col = mix(col, line_of(col), sil_amount);
	} else if (inner > 0.5) {
		col = mix(col, line_of(col), inner_amount);
	}
	float raw = texture(depth_tex, uv).r;
	vec4 vp = ip * vec4(uv * 2.0 - 1.0, raw, 1.0);
	vp.xyz /= vp.w;
	vec3 wp = (INV_VIEW_MATRIX * vec4(vp.xyz, 1.0)).xyz;
	col = mix(col, w3_apply_fog(col, wp, w3_ptex(wp)), fog_share);
	ALBEDO = col;
	ALPHA = 1.0;
}
