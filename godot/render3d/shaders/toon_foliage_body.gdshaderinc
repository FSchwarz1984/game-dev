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
uniform sampler2D leaf_tex : filter_nearest, hint_default_white;    // sRGB values (converted once below)
uniform vec4 tint : source_color = vec4(1.0);
uniform float lean : hint_range(0.0, 1.0) = 1.0;
uniform float wind_px = 1.0;                     // sway at flex 1, native px (keep 1-2)
uniform float push_px = 0.0;                     // ground cover: how far a card bends away from her feet (px)
uniform float porosity : hint_range(0.0, 1.0) = 0.5;
uniform float hi_band : hint_range(0.0, 1.0) = 1.0;  // the leaves turned full to the sun a touch brighter and warmer (round 3; continuous since round 5)
uniform float transmit : hint_range(0.0, 2.0) = 0.6; // light through the leaves when they are seen against it
uniform float lush : hint_range(0.0, 1.0) = 0.42;    // fresh greens (round 4; at night only since round 5)
uniform float ukiyo : hint_range(0.0, 1.0) = 1.0;    // the round-3 palette for the texture (w3_ukiyo_tex)
uniform bool cutaway = true;
uniform float cutaway_scale = 1.0;                // big canopies: the renderer raises it
uniform float cutaway_keep_px = 0.0;              // > 0: what lies this far above her stays (the top of the view)
instance uniform float obj_fade = 0.0;            // the cut-away mode "fade": this share of the object's pixels let through
// the shadow pass draws each card this much larger, so a crown casts big solid masses of shade (on
// itself and on the ground; G5R2 review: "大块明暗") rather than a sieve of leaf-sized holes. The sun
// flecks on the ground are the terrain's own (small, clustered, crisp).
uniform float shadow_shrink = 1.35;
uniform float shadow_sieve = 0.0;                 // share of the shadow texels let through
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
varying vec3 v_detail;      // albedo / the shade's albedo (the shade's tint; light() undoes it)
varying vec3 v_detail_sun;  // the same for the sunlit side (its green quieter, round 3)

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
			// ground cover bends away from her feet (push_px at her feet, nothing beyond 0.7 m;
			// the root stays, the tip moves: scaled by the corner's height on the card)
			if (push_px > 0.0 && w3_player.w > 0.0) {
				vec3 dp = anchor - (w3_player.xyz - vec3(0.0, 1.0, -0.52));
				float dist = length(dp.xz);
				if (dist < 0.7) {
					float k = (1.0 - dist / 0.7) * flex * clamp(UV2.y / 12.0, 0.0, 1.0);
					sway.x += round(sign(dp.x + 0.001) * push_px * k);
					sway.y -= round(push_px * 0.75 * k);
				}
			}
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
	if (obj_fade > 0.0 && !IN_SHADOW_PASS && w3_stipple(cell) < obj_fade) {
		discard;
	}
	// cards are rebuilt facing the camera whatever their winding: undo the engine's back-face flip
	if (foliage_mode == 1 && !FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	vec3 wn = normalize(v_wn);
	// (round 5, G5R3-1: the round-3 palette, w3_ukiyo_tex; by day)
	vec3 alb = w3_srgb_to_linear(COLOR.rgb * w3_ukiyo_tex(tx.rgb, foliage_mode == 1 ? ukiyo : 0.0)) * tint.rgb;
	// leaves read a touch quieter than they were painted (round 3, knowledge/17 §3: v0.1's olive
	// greens): the greens' chroma x0.8, and the vivid yellow-greens (bamboo, young leaves) compressed
	// above a knee, so a whole grove in sun never turns lime; reds and golds (the maples, the
	// persimmons) keep theirs. (At night round 4's: a higher knee, the olive turned a little green.)
	vec3 lab0 = w3_lin_to_oklab(alb);
	if (lab0.y < 0.0) {
		float c0 = length(lab0.yz);
		float c3 = c0 * 0.8;
		c3 = c3 > 0.06 ? 0.06 + (c3 - 0.06) * 0.35 : c3;
		float c4 = (c0 > 0.11 ? 0.11 + (c0 - 0.11) * 0.4 : c0) * (1.0 + 0.25 * lush);
		float h0 = atan(lab0.z, lab0.y);
		float h1 = mix(h0, h0 + (2.48 - h0) * 0.2 * lush, w3_night);
		float c1 = mix(c3, c4, w3_night);
		alb = max(w3_oklab_to_lin(vec3(lab0.x, vec2(cos(h1), sin(h1)) * c1)), vec3(0.0));
	}
	alb *= (w3_hash(cell) < 0.08 ? 0.94 : 1.0);
	alb = w3_wetten(alb, porosity);
	alb = w3_far(alb, far);
	float ao = mix(1.0, COLOR.a, vertex_ao);
	v_cell = cell;
	// the engine adds the ambient (sky colour, VoxelGI bounce, SSAO) times ALBEDO and AO; the shade
	// takes the painter's shade colour (w3_shade_tint), which light() undoes in the direct light
	// (round 5: the round-3 painted shade, w3_paint_shade)
	vec3 a_shade = w3_paint_shade(alb);
	v_detail = alb / max(a_shade, vec3(1e-4));
	// sun on leaves (round 3): a little of it goes through them and the sheen of the sky washes the
	// lit side, so its green is quieter and it is not as bright as a surface (a sunlit wood would
	// otherwise read lime; knowledge/17 §3)
	vec3 lab_s = w3_lin_to_oklab(alb);
	vec3 alb_sun = lab_s.y < 0.0 ? max(w3_oklab_to_lin(vec3(lab_s.x, lab_s.yz * 0.72)), vec3(0.0)) * 0.88 : alb;
	v_detail_sun = alb_sun / max(a_shade, vec3(1e-4));
	ALBEDO = a_shade;
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
		// (round 5: round 3's levels, continuous: w3_sun_level; round 4's wrap at night)
		vec3 c = w3_sun_level(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, false, 0.5);
		// (the leaves turned full to the sun a touch brighter and warmer: round 3's top band, continuous)
		float ndl = dot(NORMAL, LIGHT);
		c *= mix(vec3(1.0), vec3(1.13, 1.12, 1.06), hi_band * smoothstep(0.7, 0.9, ndl) * ATTENUATION * (1.0 - w3_night));
		// (light through the leaves against the sun: round 4's, a little of it by day)
		c += w3_transmit(NORMAL, LIGHT, VIEW, LIGHT_COLOR, ATTENUATION, vec3(0.9, 1.0, 0.6) * transmit * mix(0.35, 1.0, w3_night));
		c *= mix(v_detail_sun, v_detail, w3_night);
		// big crowns: what reaches the shaded side anyway (sky through the gaps, bounce), so a crown
		// seen from its shaded side keeps its masses instead of turning into a dark lid
		if (shade_fill > 0.0) {
			float lit = mix(w3_r3_body(dot(NORMAL, LIGHT)), w3_wrap(dot(NORMAL, LIGHT), 0.5), w3_night) * ATTENUATION;
			c += LIGHT_COLOR / W3_PI * shade_fill * v_fill * (1.0 - lit);
		}
		DIFFUSE_LIGHT += c * k;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.5) * v_detail * k;
	}
}
