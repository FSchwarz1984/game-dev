// The ground of the 3D world as pixel art (docs/knowledge/21-3d-pixel-render.md §5, terrain).
// Outline class 1. Every screen texel decides its material from the splat maps through a jittered
// lookup (so grass, worn path, gravel, rock, moss, litter, bank earth and paddy mud meet along
// ragged, pixel-scale borders), takes a clustered tone from its material's palette ramp, and may be
// covered by a hand-drawn glyph (tuft, pebble, leaf, crack, flower) anchored on the screen-texel
// lattice and chosen by its anchor's material, so tufts overhang a path's edge like painted sprites.
// The light is continuous (round 4): a wrapped sun (relief reads through slope shading), crisp cast
// shadows with sun flecks in the canopy's shade, the engine's ambient (sky colour, VoxelGI, SSAO)
// with the splat's AO, the lanterns as engine lights.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_back;
stencil_mode write, compare_always, 1;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D m0 : filter_linear, repeat_disable;      // grass, dirt, gravel, rock
uniform sampler2D m1 : filter_linear, repeat_disable;      // moss, litter, bank, paddy
uniform sampler2D m2 : filter_linear, repeat_disable;      // ao, puddle, wear, flowers
uniform sampler2D m3 : filter_linear, repeat_disable;      // litter kind, dryness, tufts, slope/90
uniform sampler2D palette : filter_nearest;                 // 8 tones x 16 rows, sRGB
uniform sampler2D glyphs : filter_nearest;                  // 16 x 16 glyphs of 8 x 8
uniform sampler2D water : filter_nearest, repeat_disable;   // water surface (RG u16), kind (B)
uniform vec2 water_origin = vec2(-80.0, -96.0);
uniform float water_cell = 0.5;
uniform vec2 water_size = vec2(321.0, 417.0);
uniform vec2 h_encode = vec2(-44.0, 128.0);                // min, range
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
uniform float lush : hint_range(0.0, 1.0) = 0.45;            // fresh greens over the palette (w3_lush; at night only since round 5)
uniform float dry_bias = 0.12;                              // raises the dry-grass threshold (fewer withered patches)
uniform float shade_flatten : hint_range(0.0, 1.0) = 0.6;    // how much of the painted detail the shade drops

varying vec3 v_wp;
varying vec3 v_wn;
varying vec2 v_cell;
varying float v_fleck;
varying vec3 v_detail;      // detailed albedo / the shade's flattened albedo (light() restores the detail)

const float GC = 7.0;      // glyph cell, native px

void vertex() {
	v_wp = VERTEX;
	v_wn = NORMAL;
	// The ground casts its shadow from 30 cm inside itself: a slope can never shadow itself through
	// depth error (self-shadow acne drew a lattice of dots on the gully's banks), while a ridge's or
	// a rock face's shadow over the land moves by less than a pixel.
	if (IN_SHADOW_PASS) {
		VERTEX -= NORMAL * 0.3;
	}
}

ivec2 splat_texel(vec2 xz) {
	return ivec2(floor((xz - splat_origin) / splat_cell));
}

// The dominant material at a world point seen through texel cell c. The weights are sampled
// smoothly; a fine two-scale noise keyed on the texel lattice breaks every border into a band a few
// pixels wide (organic, finely broken edges, never big hard blobs).
int material_at(vec2 xz, vec2 c) {
	vec2 uv = (xz - splat_origin) / splat_cell / splat_size;
	vec4 a = texture(m0, uv);
	vec4 b = texture(m1, uv);
	float w[8] = float[8](a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a);
	int best = 0;
	float bw = -1.0;
	for (int k = 0; k < 8; k++) {
		float wk = w[k];
		if (wk > 0.01) {
			float fine = w3_vnoise(c / 2.3 + float(k) * 7.7) * 0.65 + w3_hash(c + float(k) * 3.1) * 0.35;
			wk += (fine - 0.5) * 0.28;
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

// glyph set and density for a material (and the extras at its anchor); gc = the glyph's cell
vec3 glyph_set(int mat, vec4 e2, vec4 e3, float h, vec2 gc) {
	// returns (start, count, density)
	if (mat == 0) {
		// flowers only in small, sparse clusters
		float cl = w3_vnoise(gc / 3.0 + 31.0);
		if (e2.a > 0.05 && cl > 0.72 && h < e2.a * 0.9) return vec3(g_flowers, 0.85);
		return vec3(g_grass, 0.3 + 0.55 * e3.b);
	}
	if (mat == 1) return vec3(g_dirt, 0.12 + 0.55 * (1.0 - e2.b));       // pebbles gather at the edges
	if (mat == 2) return vec3(g_gravel, 0.85);
	if (mat == 3) return vec3(g_rock, 0.45);
	if (mat == 4) return vec3(g_moss, 0.55);
	if (mat == 5) {
		if (e3.r > 0.75) return vec3(g_bamboo, 0.7);
		if (e3.r > 0.25) return vec3(g_needles, 0.8);
		return vec3(g_litter, 0.9);
	}
	if (mat == 6) return vec3(g_bank, 0.4);
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
	// seams are broken by a scattered stipple (organic), not an ordered dither (which draws
	// checkered bands wherever the field changes slowly)
	float stip = w3_hash(cell * 1.37 + 0.5) * 0.65 + w3_vnoise(cell / 1.8) * 0.35;
	float mstep = floor(macro + 0.5 + (stip - 0.5) * 0.3);
	float row;
	float tone;
	float base_tone = -100.0;     // the tone before the painted grain (grass): the shade keeps only this
	float porous = 0.8;
	if (mat == 0) {
		float dry = e3.g + (w3_fbm(v_wp.xz / 3.0 + 7.0) - 0.5) * 0.25;
		row = dry > 0.5 + dry_bias + (stip - 0.5) * 0.2 ? 1.0 : 0.0;   // dry grass, stippled edge
		tone = 3.6 + mstep;
		base_tone = tone;
		// painted grain: single darker blades and a few lit ones scattered through the sward
		float gr = w3_hash(cell * 0.73 + 17.0);
		tone += gr < 0.11 ? -1.0 : (gr > 0.94 ? 1.0 : 0.0);
		porous = 0.6;
	} else if (mat == 1) {
		row = 2.0;
		tone = 3.4 + mstep * 0.7 + floor(e2.b * 1.6 + 0.3 + (stip - 0.5) * 0.25);
		porous = 1.0;
	} else if (mat == 2) {
		row = 3.0;
		tone = 3.5 + mstep * 0.5 + (w3_hash(floor(cell / 2.0)) - 0.5) * 2.2;
		porous = 0.5;
	} else if (mat == 3) {
		row = 4.0;
		// strata: bands that follow the height of the rock, broken by noise
		// (a band every 0.7 m of height: 8 px on a vertical face; denser bands alias into stripes)
		float band = floor(v_wp.y * 1.4 + w3_vnoise(cell / 11.0) * 1.6);
		float bk = smoothstep(0.85, 0.6, wn.y);
		tone = 3.4 + mstep * 0.5 + floor((w3_hash(vec2(band, 7.0)) - 0.5) * 2.0 * bk + 0.5) + floor(wn.y * 1.2);
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
		// cut earth in layers only where the bank is steep, a layer every 0.65 m of height
		float layer = floor(v_wp.y * 1.55 + w3_vnoise(cell / 8.0) * 1.2);
		float lk = smoothstep(0.85, 0.6, wn.y);
		tone = 3.2 + mstep * 0.5 + floor((w3_hash(vec2(layer, 3.0)) - 0.5) * 1.6 * lk + 0.5);
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
			vec3 gs = glyph_set(amat, e2, e3, w3_hash(gc + 5.1), gc);
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
	// the flat colour of the ground here (its macro tone, without the grain and the glyphs): what
	// the shade shows (big masses of light and shade, detail in the light; G5R2 review)
	vec3 flat_alb = pal(row, base_tone > -50.0 ? base_tone : tone);
	if (hit && g_acc >= 0) {
		alb = accent(g_acc);
	} else {
		float t = tone + (hit ? g_tone : 0.0);
		alb = pal(row, t);
	}
	// grass, dry grass and moss: fresh greens (w3_lush)
	if (row < 1.5 || abs(row - 5.0) < 0.5) {
		float lk = (row > 0.5 && row < 1.5 ? lush * 0.7 : lush) * w3_night;
		if (!(hit && g_acc >= 0)) alb = w3_lush(alb, lk);
		flat_alb = w3_lush(flat_alb, lk);
	}

	// ---- under water: wet, dark, a little green (the stream bed, the pool's floor)
	vec4 wt = texelFetch(water, ivec2(floor((v_wp.xz - water_origin) / water_cell + 0.5)), 0);
	if (wt.b > 0.1) {
		float wh = h_encode.x + (wt.r * 255.0 * 256.0 + wt.g * 255.0) / 65535.0 * h_encode.y;
		if (v_wp.y < wh) {
			alb *= vec3(0.42, 0.5, 0.46);
			flat_alb *= vec3(0.42, 0.5, 0.46);
		}
	}
	// ---- wetness and puddles
	alb = w3_wetten(alb, porous);
	flat_alb = w3_wetten(flat_alb, porous);
	float ao = mix(0.55, 1.0, smoothstep(0.45, 1.0, e2.r));
	// puddles in the ruts and the low spots of paths: a darker mirror of the overcast sky with
	// rings where the drops fall (only the deepest spots, so they stay small)
	if (w3_wet > 0.25 && e2.g > 0.62 && (mat == 1 || mat == 2)) {
		vec2 rc = floor(cell / 5.0);
		float ph = fract(w3_time * 0.9 + w3_hash(rc) * 7.0);
		vec2 c0 = (rc + vec2(w3_hash(rc + 1.3), w3_hash(rc + 2.7))) * 5.0;
		float rr = length((cell - c0) * vec2(1.0, 1.6));
		float ring = step(abs(rr - ph * 3.0), 0.5) * (1.0 - ph);
		alb = mix(alb * 0.5, w3_sky * 0.42, 0.7 * w3_wet) + ring * 0.035 * w3_wet;
		flat_alb = alb;
	}
	// sun flecks in the shade of the canopies. The canopy map is read where the sun's ray through
	// this point meets the crowns (about 11 m up), so the flecks fall inside the cast shade rather
	// than under the trunks. Small crisp spots (pinhole images of the sun) in loose clusters, which
	// wobble in place as the wind moves the leaves (strong on the ground; characters only see the
	// soft shade).
	vec3 sdir = normalize(w3_sun_dir);
	vec2 proj = v_wp.xz + sdir.xz / max(sdir.y, 0.25) * 11.0;
	float can = texture(m3, (proj - splat_origin) / splat_cell / splat_size).a;
	v_fleck = 0.0;
	if (can > 0.2 && w3_night < 0.5) {
		float sway = sin(w3_time * 0.8 + w3_hash(floor(v_wp.xz / 1.5)) * 6.28) * 0.35 * w3_wind.z;
		vec2 fq = v_wp.xz / 0.42 + vec2(sway, sway * 0.5);
		float fn = w3_vnoise(fq) * 0.7 + w3_vnoise(fq * 2.1 + 5.0) * 0.3;
		float cluster = w3_vnoise(v_wp.xz / 2.6 + 9.0);
		// toward the rim of a crown (thinner canopy) the flecks are many and larger; in its heart few
		v_fleck = step(0.69 + can * 0.05, fn) * step(0.34 + can * 0.22, cluster);
	}
	v_cell = cell;
	// the engine adds the ambient (sky colour, VoxelGI bounce, SSAO) times ALBEDO and AO: the shade
	// gets the flattened colour (shade_flatten of the detail removed); light() puts the detail back
	// into the direct light (v_detail = detailed / flattened), so detail shows where the sun falls
	// and the painter's shade colour (w3_shade_tint, blue-green by day): only the ambient sees it,
	// v_detail undoes it in the direct light
	// (round 5: the round-3 painted shade, w3_paint_shade: the hue turned cool, the chroma kept)
	vec3 a_shade = w3_paint_shade(mix(alb, flat_alb, shade_flatten));
	v_detail = alb / max(a_shade, vec3(1e-4));
	ALBEDO = a_shade;
	AO = ao;
	AO_LIGHT_AFFECT = 0.0;
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		float sh = max(ATTENUATION, v_fleck * 0.85);
		// (round 5: round 3's levels, continuous: w3_sun_level)
		DIFFUSE_LIGHT += w3_sun_level(NORMAL, LIGHT, LIGHT_COLOR, sh, true, 0.15) * v_detail;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.4) * v_detail;
	}
}
