// Outlines, the 遠化's edge and the ground's painted marks for the view from the lookout (W3Vista): a
// full-screen quad drawn first in the transparent pass.
// Outlines: where a neighbouring pixel lies clearly farther (relative to the distance, so far ridges
// get their line as well as near rocks), this pixel is on the near edge of something: it takes a
// darker, cooler shade of the darker side. One native pixel wide, never black. Light things (the
// clouds' billows) get a light line; in the 遠化 every edge is the key block's ink line (the 褪版,
// vista_common), at every distance.
// Marks: the same hand-drawn glyphs as the top-down ground (tufts, flowers, pebbles, gravel, rock
// chips, moss, litter; pixelart.py) stand on the land, texel for pixel. Their anchors are fixed to the
// lattice of view directions in cells of 8 pixels (vista_common: the projection moves the picture by
// whole pixels as she turns, so an anchor always lands on the same ground: the marks never crawl),
// the ground under each anchor is read back from the depth, its material from the region's splats (or
// the land's maps beyond), and the mark takes the lit colour of the ground it grows from (darker and
// lighter strokes; flowers their own colours). A mark stands up from its anchor and may overhang what
// lies behind it, never what stands in front.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform float strength = 0.75;
uniform float band_edge = 0.0;          // the 遠化's bright edge (round 3: 1; round 5: 0, the lead's choice)
uniform vec3 eye = vec3(0.0);
uniform sampler2D glyphs : filter_nearest;  // 16 x 16 glyphs of 8 x 8 (R tone + 4, G accent + 1, A)
uniform sampler2D tufts : filter_nearest;   // 4 x 4 tufts of 16 x 16
uniform sampler2D palette : filter_nearest;
uniform sampler2D m0 : filter_linear, repeat_disable;
uniform sampler2D m1 : filter_linear, repeat_disable;
uniform sampler2D m2 : filter_linear, repeat_disable;
uniform vec4 splat_frame = vec4(-80.0, -96.0, 0.25, 0.0);
uniform vec2 splat_size = vec2(641.0, 833.0);
uniform vec4 local_bounds = vec4(-80.0, -96.0, 80.0, 112.0);
uniform vec2 g_grass = vec2(0.0, 20.0);
uniform vec2 g_flowers = vec2(20.0, 8.0);
uniform vec2 g_dirt = vec2(28.0, 10.0);
uniform vec2 g_gravel = vec2(38.0, 8.0);
uniform vec2 g_rock = vec2(46.0, 10.0);
uniform vec2 g_moss = vec2(56.0, 9.0);
uniform vec2 g_litter = vec2(65.0, 11.0);
uniform vec2 g_bank = vec2(88.0, 8.0);
uniform bool marks = true;

const float CELL = 8.0;                     // anchor cell, in pixels of the lattice of directions

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float view_depth(vec2 uv, mat4 ip) {
	float d = texture(depth_tex, uv).r;
	vec4 v = ip * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

// the world point seen at a screen uv (top-left origin): the pixel's direction (the vista's
// projection) out to its distance (the depth buffer holds the distance from the eye)
vec3 world_at(vec2 uv, mat4 ip, vec2 vpx) {
	vec2 px = vec2(uv.x - 0.5, 0.5 - uv.y) * vpx;
	return eye + v_dir_of(px) * view_depth(uv, ip);
}

// the region's dominant ground material at a point (toon_terrain's order: 0 grass, 1 dirt, 2 gravel,
// 3 rock, 4 moss, 5 litter, 6 bank, 7 paddy)
int material_at(vec2 xz, vec2 c) {
	vec2 uv = (xz - splat_frame.xy) / splat_frame.z / splat_size;
	vec4 a = texture(m0, uv);
	vec4 b = texture(m1, uv);
	float w[8] = float[8](a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a);
	int best = 0;
	float bw = -1.0;
	for (int k = 0; k < 8; k++) {
		float wk = w[k] + (w3_hash(c + float(k) * 3.1) - 0.5) * 0.25;
		if (wk > bw) { bw = wk; best = k; }
	}
	return best;
}

vec3 accent(int i) {
	return w3_srgb_to_linear(texelFetch(palette, ivec2(i % 8, 11 + i / 8), 0).rgb);
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	vec2 uv = SCREEN_UV;
	mat4 ip = INV_PROJECTION_MATRIX;
	float c = view_depth(uv, ip);
	float l = view_depth(uv - vec2(px.x, 0.0), ip);
	float r = view_depth(uv + vec2(px.x, 0.0), ip);
	float u = view_depth(uv - vec2(0.0, px.y), ip);
	float d = view_depth(uv + vec2(0.0, px.y), ip);
	vec3 col = texture(screen_tex, uv).rgb;
	vec2 behind = vec2(-px.x, 0.0);
	float bd = l;
	if (r > bd) { bd = r; behind = vec2(px.x, 0.0); }
	if (u > bd) { bd = u; behind = vec2(0.0, -px.y); }
	if (d > bd) { bd = d; behind = vec2(0.0, px.y); }
	// the sky is very far: an edge against it counts
	float jump = bd - c;
	vec3 wp = c < 20000.0 ? world_at(uv, ip, VIEWPORT_SIZE) : eye;
	// (in the 遠化 the key block's lines must not be eaten: a nearer ridge before a farther one gets
	// its line at a third of the depth step the rest of the view needs)
	bool enka = c < 20000.0 && v_past(wp, eye, FRAGCOORD.xy);
	float th = 0.35 + c * (enka ? 0.02 : 0.06);
	if (c < 20000.0 && jump > th) {
		if (enka) {
			// in the 遠化 (past its gradations) every edge is the key block's line in ink, at every
			// distance: ridges, the far mountains against the sky, trees, houses (the 褪版: what is left
			// of a print when its colour blocks are gone; vista_common)
			col = v_ink();
		} else {
			float keep = 1.0;
			vec3 bcol = texture(screen_tex, uv + behind).rgb;
			vec3 base = dot(bcol, vec3(0.3, 0.59, 0.11)) < dot(col, vec3(0.3, 0.59, 0.11)) ? mix(col, bcol, 0.6) : col;
			float lb = dot(base, vec3(0.3, 0.59, 0.11));
			vec3 tint = mix(vec3(0.55, 0.58, 0.68), vec3(0.86, 0.88, 0.94), smoothstep(0.5, 0.75, lb));
			col = mix(col, base * tint, strength * keep * (1.0 - smoothstep(1500.0, 6000.0, c)) * mix(1.0, 0.7, smoothstep(0.5, 0.75, lb)));
		}
	}

	// ---- the 遠化's edge (round 3's; back in round 5): where the white meets land that keeps its
	// colour on the same ground (not where something nearer stands in front of it), a line of light
	// one pixel wide on the white's side, wherever it runs: across the plain, up and over the hills
	// (it glows a little). band_edge: 1 as round 3 drew it, 0 none (round 5: none, lead 2026-10-16)
	if (c < 20000.0 && band_edge > 0.0) {
		vec3 wc = world_at(uv, ip, VIEWPORT_SIZE);
		if (v_drain(wc.xz, wc.y) > 0.99) {
			bool edge = false;
			for (int k = 0; k < 4; k++) {
				vec2 o = k == 0 ? vec2(px.x, 0.0) : (k == 1 ? vec2(-px.x, 0.0) : (k == 2 ? vec2(0.0, px.y) : vec2(0.0, -px.y)));
				float dn = view_depth(uv + o, ip);
				if (abs(dn - c) > c * 0.12 + 2.0) continue;
				vec3 wn = world_at(uv + o, ip, VIEWPORT_SIZE);
				if (v_drain(wn.xz, wn.y) < 0.99) edge = true;
			}
			if (edge) col = mix(col, far_white * 1.3, band_edge);
		}
	}

	// ---- the marks
	if (marks) {
		vec2 vpx = VIEWPORT_SIZE;
		// this pixel (y up from the bottom) and its place on the lattice of directions
		vec2 p = floor(vec2(uv.x, 1.0 - uv.y) * vpx);
		vec2 L = p + v_lat;
		vec2 cell0 = floor(L / CELL);
		float best_y = 1e9;
		vec3 mark = vec3(0.0);
		bool hit = false;
		for (int j = -2; j <= 0; j++) {
			for (int i = -1; i <= 1; i++) {
				vec2 cc = cell0 + vec2(float(i), float(j));
				// the anchor's pixel: a whole pixel of the lattice inside its cell, back on the screen
				vec2 apx = cc * CELL + floor(vec2(w3_hash(cc * 1.31 + 0.7), w3_hash(cc * 2.17 + 5.3)) * CELL) - v_lat;
				if (apx.x < 0.0 || apx.y < 0.0 || apx.x >= vpx.x || apx.y >= vpx.y) continue;
				// glyph texel: x across from the anchor, y up from it
				vec2 g = p - apx;
				if (g.y < 0.0 || g.y > 15.0 || abs(g.x) > 8.0) continue;
				if (apx.y > best_y) continue;         // a nearer (lower) mark already covers it
				vec2 auv_c = vec2((apx.x + 0.5) / vpx.x, 1.0 - (apx.y + 0.5) / vpx.y);
				float adepth = view_depth(auv_c, ip);
				if (adepth > 140.0 || adepth < 2.0) continue;
				// the mark stands in front of what lies at this pixel, never behind it
				if (c < adepth - 0.6 - adepth * 0.02) continue;
				vec3 aw = world_at(auv_c, ip, vpx);
				// only on the land (not on trees, rocks, figures, clouds)
				if (abs(aw.y - v_height(aw.xz)) > 0.35 + adepth * 0.01) continue;
				bool local = aw.x > local_bounds.x && aw.x < local_bounds.z && aw.z > local_bounds.y && aw.z < local_bounds.w;
				int mat = 0;
				vec4 e2 = vec4(0.0);
				if (local) {
					mat = material_at(aw.xz, cc);
					e2 = texture(m2, (aw.xz - splat_frame.xy) / splat_frame.z / splat_size);
				} else {
					vec4 md = v_mid_data(aw.xz);
					vec4 mt = v_mat_data(aw.xz);
					if (md.b > 0.4 || md.a > 0.5) continue;     // woods and water: no marks
					mat = mt.b > 0.5 ? 3 : (mt.g > 0.5 ? 1 : 0);
				}
				if (mat == 7) continue;
				float hh = w3_hash(cc * vec2(1.13, 0.71) + 3.7);
				float clump = smoothstep(0.3, 0.72, w3_vnoise(cc / 2.6 + 4.0));
				vec3 gs;                                 // start, count, density
				bool big = false;
				if (mat == 0) {
					float cl = w3_vnoise(cc / 3.0 + 31.0);
					if (e2.a > 0.05 && cl > 0.7 && hh < e2.a * 0.9) gs = vec3(g_flowers, 0.8);
					else if (!local && cl > 0.82 && hh < 0.12) gs = vec3(g_flowers, 0.8);
					else { gs = vec3(g_grass, 0.62); big = adepth < 24.0 && w3_hash(cc + 9.9) < 0.55; }
				} else if (mat == 1) gs = vec3(g_dirt, 0.18 + 0.55 * (1.0 - e2.b));
				else if (mat == 2) gs = vec3(g_gravel, 0.8);
				else if (mat == 3) gs = vec3(g_rock, 0.5);
				else if (mat == 4) gs = vec3(g_moss, 0.55);
				else if (mat == 5) gs = vec3(g_litter, 0.8);
				else gs = vec3(g_bank, 0.4);
				if (hh > gs.z * (0.3 + 1.2 * clump)) continue;
				vec4 gt;
				if (big) {
					// the big tufts near the eye (16 x 16, the anchor at the bottom middle)
					if (g.x < -8.0 || g.x > 7.0) continue;
					float ti = floor(w3_hash(cc + 41.7) * 7.0);
					ivec2 tb = ivec2(int(mod(ti, 4.0)) * 16, int(floor(ti / 4.0)) * 16);
					gt = texelFetch(tufts, tb + ivec2(int(g.x + 8.0), 15 - int(g.y)), 0);
				} else {
					if (g.y > 7.0 || g.x < -4.0 || g.x > 3.0) continue;
					float gi = gs.x + floor(w3_hash(cc + 41.7) * gs.y);
					ivec2 slot = ivec2(int(mod(gi, 16.0)) * 8, int(floor(gi / 16.0)) * 8);
					gt = texelFetch(glyphs, slot + ivec2(int(g.x + 4.0), 7 - int(g.y)), 0);
				}
				if (gt.a < 0.5) continue;
				vec3 ground = texture(screen_tex, auv_c).rgb;
				int acc = int(gt.g * 255.0 + 0.5) - 1;
				vec3 mc;
				if (acc >= 0) {
					// its own colour, in the light the ground there is in
					float lk = clamp(dot(ground, vec3(0.3, 0.59, 0.11)) / 0.22, 0.35, 1.6);
					mc = accent(acc) * lk;
				} else {
					float t = gt.r * 255.0 - 4.0;
					mc = ground * (1.0 + t * 0.16);
				}
				best_y = apx.y;
				mark = mc;
				hit = true;
			}
		}
		if (hit) col = mark;
	}
	ALBEDO = col;
	ALPHA = 1.0;
}
