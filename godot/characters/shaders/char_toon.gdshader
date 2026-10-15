// The 3D characters' material (outline class 3), docs/knowledge/24-3d-characters.md.
// Anime cel shading in two or three hard tones per material (no gradient, no dither), lit by the world's sun /
// moon, sky and lamps (pixel_toon.gdshaderinc globals), with the charter's character protection:
//   * the key light keeps the sun's side and height but is brought round to the front, so she is
//     never back-lit; the real sun behind her only catches her edges (a warm back rim, shadowed);
//   * a brightness floor (higher on the face), a little front fill, a cool sky rim on the side away
//     from the key; cast shadows (tree dapple, eaves) dim her only to `shadow_dim`;
//   * the face's features are pixel-art stamps on the screen lattice (char_common.gdshaderinc).
// Mesh data (tools/characters3d): COLOR.rgb sRGB albedo, COLOR.a AO; UV2.x material id, UV2.y
// extra (cloth: 1 navy lining / 2 deep cream lining on the back faces; hair: 0.5 inner layer);
// UV per part (hat: radius fraction, angle fraction).
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled;
stencil_mode write, compare_always, 3;
#include "res://characters/shaders/char_common.gdshaderinc"

uniform float floor_light = 0.40;      // brightness floor, fraction of the albedo (day)
uniform float face_floor = 0.80;       // the face's floor (she reads first, under the hat's brim too)
uniform float night_floor = 0.45;      // the floors scale by this at night
uniform float shadow_dim = 0.62;       // how dark a cast shadow makes her (1 = not at all)
uniform float fill = 0.16;             // front fill (share of the sky's light, from the camera side)
uniform float rim_sky = 0.55;          // cool rim on the side away from the key
uniform float rim_back = 0.9;          // warm rim where the real sun behind her catches an edge
uniform float key_gain = 1.0;
uniform float term = 0.02;             // terminator position (n.l) and half width: soft, not banded
uniform float term_soft = 0.24;
uniform vec3 lining_navy : source_color = vec3(0.21, 0.22, 0.35);
uniform vec4 flash = vec4(1.0, 1.0, 1.0, 0.0);   // rgb, amount (hit / pick-up flashes)
uniform float highlight_comp = 0.36;   // albedo *= 1 - k * albedo (linear)
uniform float white_point = 0.62;      // the most light (linear) her brightest channel may reach: the
                                       // composite's S-curve and gain lift the lights ~20 % after this
uniform float ink_day = 1.25;          // the face's light in full day: the stamps show their own colour there
uniform float hair_sheen = 1.0;        // the highlight band on the hair
uniform float self_shadow_dim = 0.9;   // a cast shadow on a surface turned from the real sun (her own)
uniform int c3_debug = 0;              // 1: the cel tone in grey; 2: the shadow map (lab checks)

// the face (character3d.gd): stamps from an 8x8-cell atlas, placed on the screen lattice
uniform sampler2D c3_face_atlas : source_color, filter_nearest, hint_default_transparent;
uniform int c3_atlas_cols = 16;
uniform int c3_feat_count = 0;
uniform ivec4 c3_feat[12];   // xy: screen px of the stamp's lower-left texel; z: atlas cell; w: flags
                             // (1 mirror, 2 shown, 4 also over the hair: brows over the bangs)
uniform vec4 c3_feat_n[12];  // xyz: world normal of the feature's patch of face; w: least n.n to draw
uniform vec3 c3_head_fwd = vec3(0.0, 0.0, 1.0);  // the head's forward (world), for the face's floor

varying vec3 v_wp;      // rendered (leaned, snapped) world position: the screen lattice
varying vec3 v_wu;      // upright world position (lamps light the real place)
varying vec3 v_wn;      // upright world normal
varying vec3 v_alb;
varying float v_face;
varying vec3 v_key;     // the key light (view space)

const int CELL = 8;

// The key light (world): the sun's (moon's) east-west side and its height, mirrored onto the camera's
// side of her. The camera looks north and the sun stands in the north through most of the day; the
// first key kept the sun's height on the screen, which left every surface facing the camera in the
// half tone and her whites the colour of the packed earth (her back read as one dark column).
// Mirrored, she is lit like a sprite: what faces the camera and the sky is lit, the side away from
// the sun's east or west a half tone, the undersides (the hat's brim, the chin) shade.
vec3 c3_key_world() {
	vec3 s = w3_sun_dir;
	return normalize(vec3(s.x, max(s.y, 0.2), abs(s.z) + 0.35));
}

// Cel tones (the lead, 2026-10-15: two or three tones per material, like a sprite; the "no stepped
// light" rule is the scene's light fall-off, not her shading): the face two (nearly all lit), the
// rest three (lit, a half tone, shade). Hard steps, no dither, no gradient.
float cel(float ndl, float face) {
	if (face > 0.5) {
		return 1.0;
	}
	// the lit tone covers everything turned toward the key (her big shapes, the white sleeves, must
	// read light), the half tone the turning edges, the shade what faces away
	return 0.55 * step(term - 0.42, ndl) + 0.45 * step(term - 0.08, ndl);
}

void vertex() {
	v_wu = VERTEX;
	v_wn = NORMAL;
	if (!IN_SHADOW_PASS) {
		VERTEX = c3_lean_snap(VERTEX);
	}
	v_wp = VERTEX;
}

vec3 hat_top(vec3 alb, vec2 uv) {
	float s = uv.x;
	float a = uv.y * 2.0 * W3_PI;
	vec2 p = vec2(cos(a), sin(a)) * s;
	// the red band laid across the crown from rim to rim, from her front right to her back left (p.x
	// her left, p.y her back): the half of the top that shows while the hat leans back and to her left
	vec2 bd = normalize(vec2(0.62, 0.78));
	float across = abs(p.x * bd.y - p.y * bd.x);
	if (across < 0.10) {
		return w3_srgb_to_linear(vec3(0.651, 0.220, 0.322));
	}
	// sedge weave: concentric stitched rings, radial ribs of the sedge
	float ring = fract(s * 6.0 + 0.35);
	if (ring < 0.16 && s > 0.08) {
		alb *= 0.80;
	}
	float rib = fract(uv.y * 28.0);
	alb *= rib < 0.5 ? 0.94 : 1.0;
	// the rim's edge a step darker
	alb *= s > 0.985 ? 0.82 : 1.0;
	return alb;
}

void fragment() {
	int mat = int(UV2.x + 0.5);
	float extra = UV2.y;
	vec3 alb = w3_srgb_to_linear(COLOR.rgb);
	vec3 n = normalize(v_wn);
	if (!FRONT_FACING) {
		n = -n;
		if (extra > 0.5 && extra < 1.5) {
			alb = w3_srgb_to_linear(lining_navy);
		} else if (extra > 1.5) {
			alb *= 0.80;
		}
	}
	vec2 cell = w3_ptex(v_wp);
	if (mat == CM_HAT_TOP) {
		alb = hat_top(alb, UV);
	} else if (mat == CM_HAIR && extra > 0.35) {
		alb *= 0.55;                      // the inner layer of the long hair: the partings between
		                                  // the bunches, a clear step darker
	}
	// the sheen: the crown's (cap and bangs, extra 0) where the hair turns to the light, and on the
	// long hair (extra 0.2) a band across the bunches just under the hat, which the partings break
	// into two or three pieces (one band across a uniform mass read as a pale hole)
	float hh = v_wu.y - c3_base_y;
	bool long_hair = mat == CM_HAIR && extra > 0.1 && extra < 0.35;
	if (mat == CM_HAIR && (extra < 0.1 || (long_hair && hh > 0.90 && hh < 1.00))) {
		// the anime highlight band (天使の輪): a pale violet sheen across the hair where it turns
		// toward the light and up toward the camera; one or two pixels wide on her head
		vec3 nvh = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
		vec3 kh = normalize((VIEW_MATRIX * vec4(c3_key_world(), 0.0)).xyz);
		float facing_key = dot(nvh, normalize(kh + vec3(0.0, 0.0, 1.0)));
		float band = step(0.82, facing_key) * (1.0 - step(0.95, facing_key));
		alb = mix(alb, alb * vec3(1.9, 1.8, 2.15) + vec3(0.012, 0.010, 0.020), band * hair_sheen * (1.0 - w3_night * 0.6));
	} else if (mat == CM_STRAW) {
		alb *= 0.92 + 0.1 * step(0.5, fract(UV.x * 9.0));
	}
	float glow = 0.0;
	vec3 ink = vec3(0.0);
	float has_ink = 0.0;
	// face stamps (eyes, brows, mouth, blush, tears) on the screen lattice; marks (anger, sweat,
	// zzz) and brows may also lie over the hair and the hat (flag 4)
	if (mat == CM_FACE || mat == CM_HAIR || mat == CM_HAT_TOP || mat == CM_HAT_UNDER) {
		ivec2 c = ivec2(cell);
		vec4 st = vec4(0.0);
		for (int i = 0; i < c3_feat_count; i++) {
			ivec4 f = c3_feat[i];
			if ((f.w & 2) == 0) continue;
			if (mat != CM_FACE && (f.w & 4) == 0) continue;
			ivec2 l = c - f.xy;
			if (l.x < 0 || l.y < 0 || l.x >= CELL || l.y >= CELL) continue;
			if (dot(n, c3_feat_n[i].xyz) < c3_feat_n[i].w) continue;
			int col = f.z % c3_atlas_cols;
			int row = f.z / c3_atlas_cols;
			int ax = (f.w & 1) != 0 ? CELL - 1 - l.x : l.x;
			int ay = CELL - 1 - l.y;
			vec4 t = texelFetch(c3_face_atlas, ivec2(col * CELL + ax, row * CELL + ay), 0);
			if (t.a > 0.1) {
				st = t;
			}
		}
		if (st.a > 0.1) {
			ink = st.rgb;
			has_ink = 1.0;
			glow = st.a < 0.95 ? 1.0 : 0.0;
		}
	}
	alb = mix(alb, w3_srgb_to_linear(flash.rgb), flash.a);
	// her brightest colours (the cream haori, the hat) are compressed so that full sun plus the sky
	// stays under the bloom threshold (1.0) like the world's own materials; the darks are untouched
	alb *= 1.0 - highlight_comp * alb;
	// the face and the other skin: lit flat (a two-tone face with a grey lower half read as a mask)
	float face = (mat == CM_FACE || mat == CM_SKIN) ? 1.0 : 0.0;
	v_face = face;
	v_alb = alb;

	vec3 nv = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	NORMAL = nv;
	// the key light: the sun's (moon's) side and height, on the camera's side of her
	vec3 key = normalize((VIEW_MATRIX * vec4(c3_key_world(), 0.0)).xyz);
	v_key = key;

	// ambient: the sky and the ground bounce, continuous; painted shade (hue turned cool, chroma kept)
	float up = (n.y > 0.15 || face > 0.5) ? 0.8 : 0.4;   // two tones of sky and bounce (the face one)
	vec3 amb = mix(w3_ground, w3_sky, up);
	float lum = max(w3_luma(amb), 1e-4);
	// the key's level where she faces it (as light() gives it, cast shadows aside)
	float lit_est = cel(dot(nv, key), face);
	// (Godot's LIGHT_COLOR is colour * energy * pi, so light()'s LIGHT_COLOR / pi is w3_sun itself)
	float key_full = w3_luma(w3_sun * w3_lit_tint) * key_gain;
	float key_l = key_full * lit_est;
	// her brights must not clip to flat white (a white face loses its features, the cream its folds):
	// the albedo is scaled so its brightest channel in full light (the key plus the sky) stays at
	// white_point. One factor per material, not per pixel, so the cel tones keep their steps (hue
	// kept; the darks never get there and are untouched)
	float lum_top = max(w3_luma(mix(w3_ground, w3_sky, 0.8)), 1e-4);
	float peak = max(max(alb.r, alb.g), alb.b) * (key_full + lum_top * (1.0 + fill));
	alb *= min(1.0, white_point / max(peak, 1e-4));
	v_alb = alb;
	vec3 amb_tint = mix(vec3(1.0), amb / lum, 0.2) * w3_shade_tint;
	vec3 shade = w3_shadow_hue(alb, 0.30) * lum * amb_tint;
	// the floor: never darker than this share of her albedo (the face more), less at night. It fills
	// only what the key leaves (the key's level where she faces it, as light() gives it, cast shadows
	// aside): in full sun the face is its albedo, not albedo plus floor (that blew it out to white)
	float fl = mix(floor_light, face_floor, face) * mix(1.0, night_floor, w3_night);
	float want = w3_luma(alb) * max(fl - key_l, 0.0);
	shade *= max(1.0, want / max(w3_luma(shade), 1e-5));
	vec3 em = shade;
	// front fill
	em += alb * lum * fill * step(0.35, nv.z);
	// cool rim on the side away from the key (silhouette edges)
	float fr = step(0.82, 1.0 - max(nv.z, 0.0));
	float away = smoothstep(0.05, -0.45, dot(normalize(nv.xy + vec2(1e-4)), normalize(key.xy + vec2(1e-4))));
	em += alb * w3_sky * rim_sky * fr * away * (1.0 - face * 0.7);
	// lamps: the same light as the world, no stipple on her
	em += w3_lamp_light(alb, v_wu, n, cell, 0.0);
	// the face's ink (eyes, brows, mouth): drawn colours, not lit surfaces. They take the face's
	// light level (so they dim at night with her face) but none of its shading: an eye never goes
	// pale in the sun nor muddy in the shade. Highlights and tears keep a glow.
	if (has_ink > 0.5) {
		float sun_l = w3_luma(w3_sun) * smoothstep(-0.3, 0.4, dot(nv, key));
		float level = clamp((lum + sun_l) / ink_day, 0.25, 1.0);
		level = max(level, mix(face_floor, 0.55, w3_night) * 0.8);
		em = ink * level + ink * glow * 0.35;
		v_alb = vec3(0.0);
	}
	ALBEDO = vec3(1.0);
	EMISSION = em;
	if (c3_debug == 1) {
		EMISSION = vec3(0.15 + 0.6 * lit_est);
		v_alb = vec3(0.0);
	} else if (c3_debug == 2) {
		EMISSION = vec3(0.0);
		v_alb = vec3(0.0);
	}
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 key = v_key;
		float ndl = dot(NORMAL, key);
		float lit = cel(ndl, v_face);
		// cast shadows: on a surface turned from the real sun the shadow map always reports her own
		// body (the camera mostly sees that side: the sun stands in the north), so there it dims her
		// only a little; surfaces toward the sun (the hat's crown, her shoulders) take the world's
		// shadows in full (the tree's dapple on the hat)
		float dim = mix(self_shadow_dim, shadow_dim, step(0.1, dot(NORMAL, LIGHT)));
		float sh = mix(dim, 1.0, ATTENUATION);
		DIFFUSE_LIGHT += v_alb * w3_lit_tint * LIGHT_COLOR / W3_PI * lit * sh * key_gain;
		if (c3_debug == 2) {
			DIFFUSE_LIGHT = vec3(0.1 + 0.6 * ATTENUATION) * step(0.0, dot(NORMAL, LIGHT) + 2.0);
		}
		// the real sun behind her (it stands in the north most of the day) catches her edges
		float fr = step(0.75, 1.0 - max(dot(NORMAL, VIEW), 0.0));
		float back = step(0.3, dot(NORMAL, LIGHT)) * 0.6 * step(LIGHT.z, -0.1);
		DIFFUSE_LIGHT += v_alb * LIGHT_COLOR / W3_PI * fr * back * rim_back * ATTENUATION;
	} else {
		float a = ATTENUATION * (max(dot(NORMAL, LIGHT), 0.0) * 0.6 + 0.4);
		DIFFUSE_LIGHT += v_alb * LIGHT_COLOR / W3_PI * a;
	}
}
