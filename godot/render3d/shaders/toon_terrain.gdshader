// The ground of the 3D world as pixel art (docs/knowledge/21-3d-pixel-render.md §5, terrain).
// Outline class 1. Every screen texel decides its material from the splat maps through a jittered
// lookup (so grass, worn path, gravel, rock, moss, litter, bank earth and paddy mud meet along
// ragged, pixel-scale borders), takes a clustered tone from its material's palette ramp, and may be
// covered by a hand-drawn glyph (tuft, pebble, leaf, crack, flower) anchored on the screen-texel
// lattice and chosen by its anchor's material, so tufts overhang a path's edge like painted sprites.
// The light model has four sun bands (relief reads through slope shading) with world-anchored
// dithered seams, crisp cast shadows, quantised lanterns and a hemisphere ambient with AO.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_back;
stencil_mode write, compare_always, 1;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D m0 : filter_nearest, repeat_disable;     // grass, dirt, gravel, rock
uniform sampler2D m1 : filter_nearest, repeat_disable;     // moss, litter, bank, paddy
uniform sampler2D m2 : filter_linear, repeat_disable;      // ao, puddle, wear, flowers
uniform sampler2D m3 : filter_linear, repeat_disable;      // litter kind, dryness, tufts, slope/90
uniform sampler2D palette : filter_nearest;                 // 8 tones x 16 rows, sRGB
uniform sampler2D glyphs : filter_nearest;                  // 16 x 16 glyphs of 8 x 8
uniform vec2 splat_origin = vec2(-80.0, -96.0);
uniform float splat_cell = 0.25;
uniform vec2 splat_size = vec2(641.0, 833.0);
// glyph sets: (start, count) in atlas slots
uniform vec2 g_grass = vec2(0.0, 20.0);
uniform vec2 g_flowers = vec2(20.0, 8.0);
uniform vec2 g_dirt = vec2(28.0, 10.0);
uniform vec2 g_gravel = vec2(38.0, 8.0);
uniform vec2 g_rock = vec2(46.0, 10.0);
uniform vec2 g_moss = vec2(56.0, 9.0);
uniform vec2 g_litter = vec2(65.0, 11.0);
uniform vec2 g_needles = vec2(76.0, 7.0);
uniform vec2 g_bamboo = vec2(83.0, 5.0);
uniform vec2 g_bank = vec2(88.0, 8.0);

varying vec3 v_wp;
varying vec3 v_wn;
varying vec3 v_alb;
varying vec2 v_cell;
varying float v_fleck;

const float GC = 7.0;      // glyph cell, native px

void vertex() {
	v_wp = VERTEX;
	v_wn = NORMAL;
}

ivec2 splat_texel(vec2 xz) {
	return ivec2(floor((xz - splat_origin) / splat_cell));
}

// the dominant material at a world point seen through texel cell c (jitter keyed on c)
int material_at(vec2 xz, vec2 c) {
	vec2 jit = (vec2(w3_vnoise(c * 0.23), w3_vnoise(c * 0.23 + 19.7)) - 0.5) * 0.75;
	ivec2 st = splat_texel(xz + jit);
	vec4 a = texelFetch(m0, st, 0);
	vec4 b = texelFetch(m1, st, 0);
	float w[8] = float[8](a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a);
	int best = 0;
	float bw = -1.0;
	for (int k = 0; k < 8; k++) {
		float wk = w[k];
		if (wk > 0.02) {
			// clumps: mixed ground breaks into patches, not salt and pepper
			wk += (w3_vnoise(c / 9.0 + float(k) * 13.1) - 0.5) * 0.34;
		}
		if (wk > bw) {
			bw = wk;
			best = k;
		}
	}
	return best;
}

vec3 pal(float row, float tone) {
	vec3 c = texelFetch(palette, ivec2(int(clamp(floor(tone + 0.5), 0.0, 7.0)), int(row)), 0).rgb;
	return w3_srgb_to_linear(c);
}

vec3 accent(int i) {
	vec3 c = texelFetch(palette, ivec2(i % 8, 11 + i / 8), 0).rgb;
	return w3_srgb_to_linear(c);
}

// glyph set and density for a material (and the extras at its anchor)
vec3 glyph_set(int mat, vec4 e2, vec4 e3, float h) {
	// returns (start, count, density)
	if (mat == 0) {
		float fl = e2.a;
		if (fl > 0.05 && h < fl * 0.12) return vec3(g_flowers, 0.7);
		return vec3(g_grass, 0.18 + 0.5 * e3.b);
	}
	if (mat == 1) return vec3(g_dirt, 0.22 + 0.15 * (1.0 - e2.b));
	if (mat == 2) return vec3(g_gravel, 0.85);
	if (mat == 3) return vec3(g_rock, 0.4);
	if (mat == 4) return vec3(g_moss, 0.5);
	if (mat == 5) {
		if (e3.r > 0.75) return vec3(g_bamboo, 0.7);
		if (e3.r > 0.25) return vec3(g_needles, 0.8);
		return vec3(g_litter, 0.85);
	}
	if (mat == 6) return vec3(g_bank, 0.35);
	return vec3(0.0, 0.0, 0.0);
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	vec3 wn = normalize(v_wn);
	int mat = material_at(v_wp.xz, cell);
	vec2 suv = (v_wp.xz - splat_origin) / splat_cell / splat_size;
	vec4 e2 = texture(m2, suv);
	vec4 e3 = texture(m3, suv);

	// ---- base tone: one system of large soft patches, stepped in whole tones with dithered seams
	// (the 2D lesson: several overlapping patch systems read as camouflage)
	float macro = w3_fbm(v_wp.xz / 7.5) * 2.6 - 1.3;
	// whole steps; the dither only lives in a narrow seam at each step (no screen-door fields)
	float mstep = floor(macro + 0.5 + (w3_bayer4(cell) - 0.5) * 0.22);
	float row;
	float tone;
	float porous = 0.8;
	if (mat == 0) {
		float dry = e3.g + (w3_fbm(v_wp.xz / 3.0 + 7.0) - 0.5) * 0.25;
		row = dry > 0.5 + (w3_bayer4(cell + 2.0) - 0.5) * 0.18 ? 1.0 : 0.0;   // dry grass, dithered edge
		tone = 3.6 + mstep;
		porous = 0.6;
	} else if (mat == 1) {
		row = 2.0;
		tone = 3.4 + mstep * 0.7 + floor(e2.b * 1.6 + 0.3 + (w3_bayer4(cell) - 0.5) * 0.2);
		porous = 1.0;
	} else if (mat == 2) {
		row = 3.0;
		tone = 3.5 + mstep * 0.5 + (w3_hash(floor(cell / 2.0)) - 0.5) * 2.2;
		porous = 0.5;
	} else if (mat == 3) {
		row = 4.0;
		// strata: bands that follow the height of the rock, broken by noise
		float band = floor(v_wp.y * 3.2 + w3_vnoise(cell / 11.0) * 1.6);
		tone = 3.4 + mstep * 0.5 + floor((w3_hash(vec2(band, 7.0)) - 0.5) * 2.0 + 0.5) + floor(wn.y * 1.2);
		porous = 0.45;
	} else if (mat == 4) {
		row = 5.0;
		float cush = w3_vnoise(cell / 4.2);
		tone = 3.4 + mstep * 0.5 + (cush > 0.62 ? 1.0 : (cush < 0.3 ? -1.0 : 0.0));
		porous = 0.9;
	} else if (mat == 5) {
		row = e3.r > 0.75 ? 8.0 : (e3.r > 0.25 ? 7.0 : 6.0);
		tone = 3.2 + mstep * 0.8;
		porous = 0.9;
	} else if (mat == 6) {
		row = 9.0;
		float layer = floor(v_wp.y * 4.0 + w3_vnoise(cell / 8.0) * 1.2);
		tone = 3.2 + mstep * 0.5 + floor((w3_hash(vec2(layer, 3.0)) - 0.5) * 1.6 + 0.5);
		porous = 1.0;
	} else {
		row = 10.0;
		tone = 3.0 + mstep * 0.5;
		porous = 1.0;
	}

	// ---- glyphs anchored on the lattice: up to four cells can reach this texel
	vec3 alb = vec3(0.0);
	bool hit = false;
	float best_y = 1e9;
	float g_tone = 0.0;
	int g_acc = -1;
	vec2 base_c = floor((cell - 7.0) / GC);
	for (int j = 0; j < 2; j++) {
		for (int i = 0; i < 2; i++) {
			vec2 gc = base_c + vec2(float(i), float(j));
			float hh = w3_hash(gc * vec2(1.13, 0.71) + 3.7);
			vec2 off = floor(vec2(w3_hash(gc + 11.3), w3_hash(gc + 27.9)) * GC);
			vec2 anchor = gc * GC + off;                   // bottom-left of the glyph, texel units
			vec2 d = cell - anchor;                        // >= 0 inside the glyph box
			if (d.x < 0.0 || d.y < 0.0 || d.x > 7.0 || d.y > 7.0) continue;
			if (anchor.y > best_y) continue;              // a nearer (lower) glyph already covers it
			// the anchor's world point: left by d.x px, down (south on the ground) by d.y px
			vec2 axz = v_wp.xz + vec2(-d.x / w3_view.x, d.y / (w3_view.x * w3_view.y));
			int amat = material_at(axz, anchor);
			vec3 gs = glyph_set(amat, e2, e3, w3_hash(gc + 5.1));
			// glyphs gather in clumps with bare gaps between them
			float clump = smoothstep(0.3, 0.72, w3_vnoise(gc / 2.6 + 4.0));
			if (gs.y < 0.5 || hh > gs.z * (0.25 + 1.3 * clump)) continue;
			float gi = gs.x + floor(w3_hash(gc + 41.7) * gs.y);
			ivec2 slot = ivec2(int(mod(gi, 16.0)) * 8, int(floor(gi / 16.0)) * 8);
			// atlas rows run downward; glyph texel y counts up from the anchor
			ivec2 tp = slot + ivec2(int(d.x), 7 - int(d.y));
			vec4 gt = texelFetch(glyphs, tp, 0);
			if (gt.a < 0.5) continue;
			if (amat != mat && amat != 0) continue;       // only grass tufts overhang a border
			best_y = anchor.y;
			hit = true;
			g_tone = gt.r * 255.0 - 4.0;
			g_acc = int(gt.g * 255.0 + 0.5) - 1;
		}
	}
	if (hit && g_acc >= 0) {
		alb = accent(g_acc);
	} else {
		float t = tone + (hit ? g_tone : 0.0);
		alb = pal(row, t);
	}

	// ---- wetness and puddles
	alb = w3_wetten(alb, porous);
	float ao = mix(0.55, 1.0, smoothstep(0.45, 1.0, e2.r));
	ao = floor(ao * 4.0 + 0.5 + (w3_bayer4(cell) - 0.5) * 0.3) / 4.0;
	if (w3_wet > 0.25 && e2.g > 0.45 && (mat == 1 || mat == 2)) {
		float ring = step(0.82, w3_vnoise(cell / 3.0 + w3_time * 0.4));
		alb = mix(alb * 0.55, w3_sky * 0.8 + vec3(0.02), 0.55 * w3_wet) + ring * 0.04 * w3_wet;
	}
	// sun flecks under canopies: where the canopy shades the ground, a drifting pattern of crisp
	// light spots gets through (strong on the ground; characters only see the soft shade)
	float can = e3.a;
	v_fleck = 0.0;
	if (can > 0.15) {
		vec2 fq = v_wp.xz / 0.9 + vec2(w3_time * 0.05 * w3_wind.x, w3_time * 0.03);
		float sway = sin(w3_time * 0.7 + v_wp.x * 0.13) * 0.18 * w3_wind.z;
		float fn = w3_vnoise(fq + vec2(sway, 0.0)) * 0.62 + w3_vnoise(fq * 2.3 + vec2(-sway, 5.0)) * 0.38;
		v_fleck = step(0.69 - (1.0 - can) * 0.12, fn);
	}
	v_alb = alb;
	v_cell = cell;
	ALBEDO = vec3(1.0);
	EMISSION = w3_ambient(alb, wn, ao);
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		float ndl = dot(NORMAL, LIGHT);
		float th = (w3_bayer4(v_cell) - 0.5) * 0.05;
		float lvl = ndl > 0.80 + th ? 1.0 : (ndl > 0.58 + th ? 0.86 : (ndl > 0.30 + th ? 0.68 : (ndl > 0.04 + th ? 0.5 : 0.0)));
		float sh = step(0.5, ATTENUATION);
		sh = max(sh, v_fleck * 0.85);
		DIFFUSE_LIGHT += v_alb * w3_lit_tint * LIGHT_COLOR / W3_PI * lvl * sh;
	} else {
		DIFFUSE_LIGHT += w3_point_light(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_cell, 1.0);
	}
}
