// Painted surfaces (bark, wood, stone, thatch, plaster, paper): a pixel-art albedo atlas sampled
// nearest at one texel per native pixel, lit in a few hard bands whose tints shift cool in shadow
// and warm in light. Alpha < 1 in the atlas marks emissive texels (lantern paper, fire boxes):
// alpha 0.5 = glows when `lit` is on.
shader_type spatial;
render_mode ambient_light_disabled, cull_back;

#include "w3a_common.gdshaderinc"

uniform sampler2D albedo_tex : source_color, filter_nearest, repeat_disable;
uniform vec3 tint_deep : source_color = vec3(0.40, 0.45, 0.60);
uniform vec3 tint_shadow : source_color = vec3(0.56, 0.61, 0.74);
uniform vec3 tint_mid : source_color = vec3(0.84, 0.84, 0.86);
uniform vec3 tint_lit : source_color = vec3(1.0, 0.98, 0.93);
uniform vec3 tint_high : source_color = vec3(1.10, 1.06, 0.94);
uniform float see_through = 0.0;     // 1: discard in front of her (tree trunks, the camphor)
uniform float see_scale = 1.0;
uniform float lit = 0.0;             // lanterns: emissive texels glow
uniform vec3 glow_color : source_color = vec3(1.0, 0.72, 0.40);
uniform float glow_energy = 1.6;
uniform vec3 w3a_cam_fwd = vec3(0.0, -0.819, -0.574);
uniform vec3 lantern_tint : source_color = vec3(1.0, 0.62, 0.30);

varying vec3 v_alb;

void fragment() {
	vec4 t = texture(albedo_tex, UV);
	if (see_through > 0.5) {
		vec3 fwd = -INV_VIEW_MATRIX[2].xyz;
		if (dot(fwd, w3a_cam_fwd) > 0.999) {
			w3a_see_through(VERTEX, VIEW_MATRIX, FRAGCOORD.xy, see_scale);
		}
	}
	v_alb = t.rgb;
	ALBEDO = vec3(1.0);
	if (t.a < 0.75 && lit > 0.5) {
		EMISSION = t.rgb * glow_color * glow_energy;
	}
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 key = normalize((VIEW_MATRIX * vec4(w3a_key_dir, 0.0)).xyz);
		float ndl = dot(NORMAL, key);
		float sh = ATTENUATION;
		vec3 m;
		if (sh < 0.5) {
			m = ndl < -0.15 ? tint_deep : tint_shadow;
		} else if (ndl > 0.78) {
			m = tint_high;
		} else if (ndl > 0.30) {
			m = tint_lit;
		} else if (ndl > -0.15) {
			m = tint_mid;
		} else {
			m = tint_shadow;
		}
		DIFFUSE_LIGHT += w3a_far(v_alb * m) * LIGHT_COLOR / PI;
	} else {
		float a = clamp(ATTENUATION, 0.0, 1.0) * clamp(dot(NORMAL, LIGHT) * 0.6 + 0.5, 0.0, 1.0);
		float q = floor(a * 4.0 + w3a_bayer4(FRAGCOORD.xy) * 0.6) / 4.0;
		DIFFUSE_LIGHT += v_alb * q * LIGHT_COLOR / PI * lantern_tint;
	}
}
