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
uniform float hi_band : hint_range(0.0, 1.0) = 1.0;  // (unused since round 4: the light is continuous)
uniform float transmit : hint_range(0.0, 2.0) = 0.6; // light through the leaves when they are seen against it
uniform float lush : hint_range(0.0, 1.0) = 0.65;    // fresh greens (round 4)
uniform bool cutaway = true;
uniform float cutaway_scale = 1.0;                // big canopies: the renderer raises it
uniform float cutaway_keep_px = 0.0;              // > 0: what lies this far above her stays (the top of the view)
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
	if (cutaway && !IN_SHADOW_PASS && w3_cutaway_k(v_wp, cell, cutaway_scale, cutaway_keep_px)) {
		discard;
	}
	// cards are rebuilt facing the camera whatever their winding: undo the engine's back-face flip
	if (foliage_mode == 1 && !FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	vec3 wn = normalize(v_wn);
	vec3 alb = w3_srgb_to_linear(COLOR.rgb * tx.rgb) * tint.rgb;
	// round 4 (G5R2-1): rich natural greens, not olive. Only the most vivid yellow-greens (bamboo,
	// young leaves) are held under a knee, so a whole grove in sun never turns lime (the G3 lesson:
	// fluorescent green); reds and golds (the maples, the persimmons) keep theirs
	vec3 lab0 = w3_lin_to_oklab(alb);
	if (lab0.y < 0.0) {
		float c0 = length(lab0.yz);
		float c1 = c0 > 0.11 ? 0.11 + (c0 - 0.11) * 0.4 : c0;
		float h0 = atan(lab0.z, lab0.y);
		// the olive leaves turn a little toward a clear green
		float h1 = h0 + (2.48 - h0) * 0.2 * lush;
		c1 *= 1.0 + 0.25 * lush;
		alb = max(w3_oklab_to_lin(vec3(lab0.x, vec2(cos(h1), sin(h1)) * c1)), vec3(0.0));
	}
	alb *= (w3_hash(cell) < 0.08 ? 0.94 : 1.0);
	alb = w3_wetten(alb, porosity);
	alb = w3_far(alb, far);
	float ao = mix(1.0, COLOR.a, vertex_ao);
	v_cell = cell;
	// the engine adds the ambient (sky colour, VoxelGI bounce, SSAO) times this albedo and AO
	ALBEDO = alb;
	AO = ao;
	AO_LIGHT_AFFECT = 0.0;
	EMISSION = alb * w3_sky * 0.35 * far;
	if (w3_bake > 0.5) {
		ALBEDO = vec3(0.0);
		EMISSION = w3_bake_out(alb, wn, ao, 1.0);
	}
	// for the fill in light(): how much the leaf faces the sky, times its AO (continuous)
	v_fill = ((wn.y * 0.5 + 0.5) * 0.55 + 0.45) * ao;
}

void light() {
	float k = w3_far_light(far);
	if (LIGHT_IS_DIRECTIONAL) {
		// light scatters through a crown: a wide wrap, and the leaves seen against the light glow
		// yellow-green (it passes through them: the engine multiplies by the albedo again)
		vec3 c = w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.5);
		c += w3_transmit(NORMAL, LIGHT, VIEW, LIGHT_COLOR, ATTENUATION, vec3(0.9, 1.0, 0.6) * transmit);
		// big crowns: what reaches the shaded side anyway (sky through the gaps, bounce), so a crown
		// seen from its shaded side keeps its masses instead of turning into a dark lid
		if (shade_fill > 0.0) {
			float lit = w3_wrap(dot(NORMAL, LIGHT), 0.5) * ATTENUATION;
			c += LIGHT_COLOR / W3_PI * shade_fill * v_fill * (1.0 - lit);
		}
		DIFFUSE_LIGHT += c * k;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.5) * k;
	}
}
