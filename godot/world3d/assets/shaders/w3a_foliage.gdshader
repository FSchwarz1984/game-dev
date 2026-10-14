// Foliage cards: camera-facing quads, each a leaf cluster from an atlas (R shade offset, G glint,
// B per-leaf variation, A coverage). Light comes from two normals: the leaf MASS normal (CUSTOM1)
// carries the big light and shadow; the CLUMP normal (NORMAL) adds relief only where the mass is
// lit, so the shade side stays one calm dark shape. Bands index a hue-shifted palette row.
// Card corners snap to whole native pixels and wind moves whole cards by whole pixels.
// Vertex data: VERTEX = card centre; CUSTOM0 = (corner x 0|1, corner y 0|1 (0 = top), width px,
// height px); CUSTOM1 = (mass normal xyz, clump hash); UV = atlas UV of that corner;
// COLOR = (ao, card variation, palette row / 8, wind weight).
shader_type spatial;
render_mode skip_vertex_transform, cull_disabled, depth_draw_opaque, ambient_light_disabled;

#include "w3a_common.gdshaderinc"

uniform sampler2D leaf_tex : filter_nearest, repeat_disable;
uniform sampler2D palette : source_color, filter_nearest, repeat_disable;   // 8 columns: 7 bands + glint
uniform float leaf_contrast = 0.16;
uniform float clump_k = 0.50;        // how much clump relief shows on the lit side
uniform float ao_strength = 0.62;
uniform float shadow_dim = 0.40;
uniform float var_k = 0.06;
// band thresholds on the light value (-1 .. 1): deep | shadow 2 | shadow | mid | light | light 2 | high
uniform vec3 band_lo = vec3(-0.66, -0.34, -0.10);
uniform vec3 band_hi = vec3(0.08, 0.40, 0.72);
uniform float wind_strength = 1.0;
uniform float see_scale = 1.0;
uniform vec3 w3a_cam_fwd = vec3(0.0, -0.819, -0.574);   // the main camera's forward (world)
uniform vec4 w3a_canopy = vec4(0.0, 0.0, -1000.0, 0.0);  // her x, z; cut height (world y); radius (m)
uniform vec3 lantern_tint : source_color = vec3(1.0, 0.62, 0.30);

varying vec4 v_data;
varying vec3 v_nm;
varying vec3 v_centre;
varying float v_off;
varying float v_gloss;
varying float v_leafvar;

void vertex() {
	vec3 wc = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_centre = wc;
	vec4 cv = MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	vec2 size = CUSTOM0.zw;
	vec2 corner = CUSTOM0.xy;
	float ph = wc.x * 0.37 + wc.z * 0.23 + wc.y * 0.11;
	float s = sin(TIME * 1.1 + ph) * 0.65 + sin(TIME * 1.9 + ph * 1.7) * 0.35;
	float sway = floor(s * COLOR.a * wind_strength * 1.25 + 0.5);
	vec2 tl = floor(cv.xy * w3a_px_per_m + vec2(-size.x * 0.5, size.y * 0.5) + 0.5);
	vec2 p = tl + vec2(corner.x * size.x + sway, -corner.y * size.y);
	cv.xy = p / w3a_px_per_m;
	VERTEX = cv.xyz;
	NORMAL = normalize((MODELVIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_nm = normalize((MODELVIEW_MATRIX * vec4(CUSTOM1.xyz, 0.0)).xyz);
	v_data = COLOR;
}

void fragment() {
	vec4 t = texture(leaf_tex, UV);
	if (t.a < 0.5) {
		discard;
	}
	vec3 fwd = -INV_VIEW_MATRIX[2].xyz;
	if (dot(fwd, w3a_cam_fwd) > 0.999) {   // the main camera, not a shadow pass
		w3a_see_through(VERTEX, VIEW_MATRIX, FRAGCOORD.xy, see_scale);
		// canopy lift: under a crown, the leaves below the cut height thin out around her
		if (w3a_canopy.w > 0.0) {
			vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
			float dh = length(wp.xz - w3a_canopy.xy);
			float kr = 1.0 - smoothstep(w3a_canopy.w * 0.72, w3a_canopy.w, dh);
			float ky = 1.0 - smoothstep(w3a_canopy.z - 1.6, w3a_canopy.z + 1.6, wp.y);
			if (kr * ky > 0.0 && kr * ky >= w3a_bayer4(FRAGCOORD.xy)) {
				discard;
			}
		}
	}
	v_off = (t.r * 255.0 - 128.0) / 110.0;
	v_gloss = t.g;
	v_leafvar = t.b;
	ALBEDO = vec3(1.0);
}

void light() {
	int row = int(v_data.b * 8.0);
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 key = normalize((VIEW_MATRIX * vec4(w3a_key_dir, 0.0)).xyz);
		float lm = dot(v_nm, key);
		float lc = dot(NORMAL, key);
		float sun = ATTENUATION;
		float lit = smoothstep(-0.15, 0.45, lm) * sun;
		float l = mix(lm, lc, clump_k * (0.2 + 0.8 * lit));
		l -= (1.0 - sun) * shadow_dim * 2.0;
		l += v_off * leaf_contrast * 2.0 * (0.4 + 0.6 * lit);
		l -= v_data.r * ao_strength * 2.0;
		l += (v_data.g - 0.5) * var_k * 2.0 + (v_leafvar - 0.5) * 0.04;
		l += (w3a_bayer4(FRAGCOORD.xy) - 0.5) * 0.07;
		int band = int(l > band_lo.x) + int(l > band_lo.y) + int(l > band_lo.z) + int(l > band_hi.x) + int(l > band_hi.y) + int(l > band_hi.z);
		vec3 col = texelFetch(palette, ivec2(band, row), 0).rgb;
		if (v_gloss > 0.5 && band >= 4 && sun > 0.5) {
			col = texelFetch(palette, ivec2(7, row), 0).rgb;
		}
		DIFFUSE_LIGHT += w3a_far(col) * LIGHT_COLOR / PI;
	} else {
		float a = clamp(ATTENUATION, 0.0, 1.0) * clamp(dot(NORMAL, LIGHT) * 0.5 + 0.6, 0.0, 1.0);
		float q = floor(a * 4.0 + w3a_bayer4(FRAGCOORD.xy) * 0.6) / 4.0;
		vec3 base = texelFetch(palette, ivec2(4, row), 0).rgb;
		DIFFUSE_LIGHT += base * q * LIGHT_COLOR / PI * lantern_tint;
	}
}
