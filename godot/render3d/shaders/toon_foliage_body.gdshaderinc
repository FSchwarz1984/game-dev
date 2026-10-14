// Body of the foliage toon material (tree crowns, bushes, bamboo leaves, hanging fruit).
// Included by toon_foliage*.gdshader (outline class 2 = silhouette only, softer; 4 = target).
//
// Two ways to build foliage (foliage_mode):
//   0 mesh  — real geometry (leaf blobs, needle tiers). Each vertex leans like any upright object;
//             CUSTOM0.xyz = its sway-group anchor (object space), CUSTOM0.w = flex 0..1, so a group
//             moves rigidly by whole pixels. COLOR.rgb = albedo (sRGB), COLOR.a = AO.
//   1 cards — camera-facing leaf cards, texel for pixel. Per vertex: CUSTOM0.xyz = card anchor
//             (object space), CUSTOM0.w = flex; UV = atlas uv of the corner; UV2 = corner offset
//             from the anchor in native pixels (x right, y up; whole numbers); NORMAL = the light
//             normal you want for the whole card (spherised from the crown centre); COLOR.rgb tints
//             the texture (sRGB), COLOR.a = AO. VERTEX is only used for culling bounds (anchor +
//             rough corner); the shader rebuilds the card. In the shadow pass the card turns to
//             face the sun, so the crown casts a dappled shadow with its leaf silhouettes.
// leaf_tex: RGB = albedo (sRGB, flat pixel-art tones, no baked light direction), A = coverage
// (< 0.5 is cut). Cards are cut away (stippled) where they hide her.
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform int foliage_mode : hint_range(0, 1) = 1;
uniform sampler2D leaf_tex : source_color, filter_nearest, hint_default_white;
uniform vec4 tint : source_color = vec4(1.0);
uniform float lean : hint_range(0.0, 1.0) = 1.0;
uniform float wind_px = 1.0;                     // sway at flex 1, native px (keep 1-2)
uniform float porosity : hint_range(0.0, 1.0) = 0.5;
uniform float hi_band : hint_range(0.0, 1.0) = 1.0;  // sunlit rim band (lighter, warmer)
uniform bool cutaway = true;
uniform float cutaway_scale = 1.0;                // big canopies: the renderer raises it
uniform float shadow_shrink = 1.08;               // cards cast slightly smaller shadows (sun flecks)
uniform float shadow_sieve = 0.03;                // and let this share of their texels through
uniform float vertex_ao : hint_range(0.0, 1.0) = 1.0;
uniform float far : hint_range(0.0, 1.0) = 0.0;   // 遠化: 0 near .. 1 lost its qualities (pale, flat)
// big crowns: light that reaches the shaded side anyway (sky through the gaps, bounce from the ground),
// as a share of the sun, so a crown seen from its shaded side keeps its masses instead of turning into
// a black lid
uniform float shade_fill : hint_range(0.0, 1.0) = 0.0;

varying vec3 v_wp;
varying vec3 v_wu;      // where the leaf really is (before lean and card layout): lamps light that
varying vec3 v_wn;
varying vec3 v_alb;
varying vec2 v_cell;
varying float v_fill;

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 anchor = (MODEL_MATRIX * vec4(CUSTOM0.xyz, 1.0)).xyz;
	float flex = CUSTOM0.w;
	vec3 wp;
	if (foliage_mode == 1) {
		vec3 a = anchor;
		if (IN_SHADOW_PASS) {
			// face the light: the shadow camera's axes
			vec3 r = normalize(INV_VIEW_MATRIX[0].xyz);
			vec3 u = normalize(INV_VIEW_MATRIX[1].xyz);
			// a little smaller in the shadow pass: light leaks between the leaf clusters
			wp = a + (r * UV2.x + u * UV2.y) * shadow_shrink / w3_view.x;
		} else {
			a = w3_lean(a, origin.y, lean);
			a += w3_snap(a);
			vec2 sway = w3_wind_px(anchor, flex, wind_px);
			wp = a + w3_px_to_world(UV2 + sway);
		}
	} else {
		wp = VERTEX;
		if (!IN_SHADOW_PASS) {
			wp = w3_lean(wp, origin.y, lean);
			wp += w3_px_to_world(w3_wind_px(anchor, flex, wind_px));
		}
	}
	VERTEX = wp;
	v_wp = wp;
	v_wu = foliage_mode == 1 ? anchor : VERTEX;
	v_wn = NORMAL;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	vec4 tx = foliage_mode == 1 ? texture(leaf_tex, UV) : vec4(1.0);
	if (tx.a < 0.5) {
		discard;
	}
	if (IN_SHADOW_PASS && foliage_mode == 1) {
		vec2 tc = floor(UV * vec2(textureSize(leaf_tex, 0)) / 2.0);
		if (w3_hash(tc + 17.0) < shadow_sieve) {
			discard;
		}
	}
	// (never in the shadow pass: the cut-away is for the eye, the shadow stays whole)
	if (cutaway && !IN_SHADOW_PASS && w3_cutaway_r(v_wp, cell, cutaway_scale)) {
		discard;
	}
	// cards are rebuilt facing the camera whatever their winding: undo the engine's back-face flip
	if (foliage_mode == 1 && !FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	vec3 wn = normalize(v_wn);
	vec3 alb = w3_srgb_to_linear(COLOR.rgb * tx.rgb) * tint.rgb;
	alb *= (w3_hash(cell) < 0.08 ? 0.94 : 1.0);
	alb = w3_wetten(alb, porosity);
	alb = w3_far(alb, far);
	float ao = mix(1.0, COLOR.a, vertex_ao);
	v_alb = alb * w3_far_light(far);
	v_cell = cell;
	ALBEDO = vec3(1.0);
	EMISSION = w3_ambient(alb, wn, ao) * w3_far_fill(far) + w3_lamp_light(alb, v_wu, wn, cell, 1.0) * (1.0 - far * 0.6);
	// for the fill in light(): how much the card faces the sky, in three steps, times its AO
	v_fill = floor((wn.y * 0.5 + 0.5) * 3.0 + 0.5) / 3.0 * 0.55 + 0.45;
	v_fill *= ao;
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 c = w3_sun_light(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_cell, 1.0);
		float ndl = dot(NORMAL, LIGHT);
		if (hi_band > 0.0 && ndl > 0.8 && ATTENUATION > 0.5) {
			c *= mix(vec3(1.0), vec3(1.22, 1.18, 1.02), hi_band);
		}
		// the fill where the sun does not reach (its own shade or the crown's shadow): the masses keep
		// a hierarchy (tops lighter, undersides darker) instead of one dark lid
		if (shade_fill > 0.0 && (ndl < 0.06 || ATTENUATION < 0.5)) {
			c += v_alb * LIGHT_COLOR / W3_PI * shade_fill * v_fill;
		}
		DIFFUSE_LIGHT += c;
	} else {
		DIFFUSE_LIGHT += w3_point_light(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_cell, 1.0);
	}
}
