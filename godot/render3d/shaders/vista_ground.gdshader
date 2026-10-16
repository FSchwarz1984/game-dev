// The land in the view from the lookout (W3Vista): a flat radial mesh around the eye, lifted by the
// height maps in the vertex shader. Near the eye the region's own ground materials (the splat maps
// of the walkable world, its palette); further out forest, rock, fields, terraces, the road, water,
// the plain's field mosaic; toon sun in three bands, the painted shade, aerial perspective and the
// 遠化 mist (vista_common.gdshaderinc). Texture detail is anchored to the world in cells that grow
// with distance, so it stays about one to three pixels wide and never turns to noise.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_back;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform sampler2D m0 : filter_linear, repeat_disable;      // the region's splats (Terrain3D)
uniform sampler2D m1 : filter_linear, repeat_disable;
uniform sampler2D m2 : filter_linear, repeat_disable;      // ao, puddle, wear, flowers
uniform sampler2D m3 : filter_linear, repeat_disable;      // litter kind, dryness, tufts, canopy
uniform sampler2D palette : filter_nearest;
uniform vec4 splat_frame = vec4(-80.0, -96.0, 0.25, 0.0);    // origin x, z, cell
uniform vec2 splat_size = vec2(641.0, 833.0);
uniform vec4 local_bounds = vec4(-80.0, -96.0, 80.0, 112.0);
uniform vec3 eye = vec3(0.0);
uniform int dbg_mode = 0;
// the region's grass as the top-down world colours it (one soft colour field: round 5)
#include "res://render3d/shaders/sward.gdshaderinc"

varying vec3 v_wp;
varying vec3 v_n;
varying vec3 v_alb;
varying float v_shade;      // under the sea of clouds (no sun)
varying float v_river;
varying float v_town;       // the villages' density on the plain (their lamplit streets at night)

void vertex() {
	vec2 xz = VERTEX.xz;
	float h = v_height(xz);
	float d = length(xz - eye.xz);
	float e = max(0.6, d * 0.006);
	float hx = v_height(xz + vec2(e, 0.0)) - v_height(xz - vec2(e, 0.0));
	float hz = v_height(xz + vec2(0.0, e)) - v_height(xz - vec2(0.0, e));
	v_n = normalize(vec3(-hx, 2.0 * e, -hz));
	VERTEX = vec3(xz.x, h, xz.y);
	v_wp = VERTEX;
	NORMAL = v_n;
	POSITION = v_project(VERTEX, eye, PROJECTION_MATRIX);
}

vec3 pal(float row, float tone) {
	vec3 c = texelFetch(palette, ivec2(int(clamp(floor(tone + 0.5), 0.0, 7.0)), int(row)), 0).rgb;
	return w3_srgb_to_linear(c);
}

vec3 srgb(vec3 c) { return w3_srgb_to_linear(c); }

// value noise in three dimensions (the far land's grain: on a face seen steeply a noise of the map
// alone stretches into streaks down the face; one that also changes with height never does)
float vnoise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	vec3 u = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(w3_hash3(i), w3_hash3(i + vec3(1, 0, 0)), u.x), mix(w3_hash3(i + vec3(0, 1, 0)), w3_hash3(i + vec3(1, 1, 0)), u.x), u.y);
	float b = mix(mix(w3_hash3(i + vec3(0, 0, 1)), w3_hash3(i + vec3(1, 0, 1)), u.x), mix(w3_hash3(i + vec3(0, 1, 1)), w3_hash3(i + vec3(1, 1, 1)), u.x), u.y);
	return mix(a, b, u.z);
}

void fragment() {
	vec3 wp = v_wp;
	vec2 xz = wp.xz;
	float dist = length(wp - eye);
	v_shade = 0.0;
	v_river = 0.0;
	v_town = 0.0;
	vec3 n = normalize(v_n);
	// (round 4: away from the eye the mesh's rings lie tens of metres apart and its radial strips
	// run straight up the screen; a normal interpolated across them shaded every strip of a hill's
	// face its own way, a curtain of vertical streaks. Out there the normal comes from the height
	// maps, per pixel.)
	if (dist > 160.0) {
		// (and the height: inside a long triangle the mesh's height strays tens of metres from the
		// land's; every choice made by height, the plain's edge, the strata, the haze, then changed
		// from one strip to the next)
		wp.y = v_height(xz);
		float e = max(1.0, dist * 0.004);
		float hx = v_height(xz + vec2(e, 0.0)) - v_height(xz - vec2(e, 0.0));
		float hz = v_height(xz + vec2(0.0, e)) - v_height(xz - vec2(0.0, e));
		n = normalize(vec3(-hx, 2.0 * e, -hz));
		NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	}
	// texture cell: about a pixel and a half wide at this distance (fine grain near, never blocks).
	// On steep faces the cells lie in the face (along it and down its fall line), not in the map:
	// map cells seen on a face that turns toward the eye stretch into vertical streaks.
	float tc = max(0.02, dist * 0.0028);
	vec2 pl = xz;
	if (n.y < 0.74 + (w3_hash(floor(xz / tc) * 0.37) - 0.5) * 0.08) {
		vec2 th = normalize(vec2(-n.z, n.x) + vec2(1e-4));
		pl = vec2(dot(xz, th), wp.y / max(0.45, sqrt(1.0 - n.y * n.y)));
	}
	vec2 cell = floor(pl / tc);
	float n1 = w3_hash(cell);
	float clump = w3_vnoise(pl / max(3.0, dist * 0.02));
	// (out on the far land, where the mesh is coarse and faces are seen steeply, the grain in three
	// dimensions: round 4, the hills beside the plain were curtains of vertical streaks)
	vec3 wq = vec3(xz.x, wp.y * 1.6, xz.y);
	if (dist > 160.0) {
		n1 = w3_hash3(floor(wq / tc) + 0.5);
		clump = vnoise3(wq / max(3.0, dist * 0.02));
	}
	float slope = degrees(acos(clamp(n.y, 0.0, 1.0)));
	vec3 alb;
	bool water = false;
	int plate = V_GREEN;        // the block that prints this ground in the 遠化 (vista_common v_print)
	float ink = 0.0;            // 1 on a line of the key block (the borders of fields, woods, water, roads, villages)
	float wood = 0.0;           // 1 in a wood (the key block draws its crowns once the green is gone)
	bool local = xz.x > local_bounds.x && xz.x < local_bounds.z && xz.y > local_bounds.y && xz.y < local_bounds.w;
	if (local) {
		// the walkable region, as the top-down ground paints it (toon_terrain): its dominant ground
		// material through a jittered lookup on the pixel lattice (ragged, pixel-scale borders), one
		// system of large soft patches stepped in whole tones, and each material's own grain: blades
		// in the grass, dry grass where the map says, pebbles along the path's edges, gravel in pairs,
		// strata on the rock, cushions of moss, the bank's earth in layers where it is steep
		vec2 pc = v_dir_cell(wp, eye);
		vec2 uv = (xz - splat_frame.xy) / splat_frame.z / splat_size;
		vec4 a = texture(m0, uv);
		vec4 b = texture(m1, uv);
		vec4 e2 = texture(m2, uv);
		vec4 e3 = texture(m3, uv);
		float w[8] = float[8](a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a);
		int best = 0;
		float bw = -1.0;
		for (int k = 0; k < 8; k++) {
			float wk = w[k];
			if (wk > 0.01) {
				float fine = w3_vnoise(pc / 2.3 + float(k) * 7.7) * 0.65 + w3_hash(pc + float(k) * 3.1) * 0.35;
				wk += (fine - 0.5) * 0.28;
			}
			if (wk > bw) { bw = wk; best = k; }
		}
		float macro = w3_fbm(xz / 7.5) * 2.6 - 1.3;
		float stip = w3_hash(pc * 1.37 + 0.5) * 0.65 + w3_vnoise(pc / 1.8) * 0.35;
		float mstep = floor(macro + 0.5 + (stip - 0.5) * 0.3);
		float row;
		float tone;
		float sw_dry = -1.0;
		if (best == 0) {
			// (round 5: the sward's colour field, as toon_terrain: dryness and tone soft over metres)
			sw_dry = w3_sward_dry(xz, e3.g, 0.0);
			row = 0.0;
			float gr = w3_hash(pc * 0.73 + 17.0);
			tone = w3_sward_tone(xz) + (gr < 0.11 ? -1.0 : (gr > 0.94 ? 1.0 : 0.0));
		} else if (best == 1) {
			row = 2.0;
			tone = 3.4 + mstep * 0.7 + floor(e2.b * 1.6 + 0.3 + (stip - 0.5) * 0.25);
			if (w3_hash(pc * 0.61 + 9.0) < 0.06 * (1.0 - e2.b)) tone -= 1.5;      // a pebble's shade
			else if (w3_hash(pc * 0.43 + 2.0) > 0.93) tone += 1.0;                 // a lit grain
		} else if (best == 2) {
			row = 3.0;
			tone = 3.5 + mstep * 0.5 + (w3_hash(floor(pc / 2.0)) - 0.5) * 2.2;
		} else if (best == 3) {
			row = 4.0;
			float band = floor(wp.y * 1.4 + w3_vnoise(pc / 11.0) * 1.6);
			float bk = smoothstep(0.85, 0.6, n.y);
			tone = 3.4 + mstep * 0.5 + floor((w3_hash(vec2(band, 7.0)) - 0.5) * 2.0 * bk + 0.5) + floor(n.y * 1.2);
		} else if (best == 4) {
			row = 5.0;
			float cush = w3_vnoise(pc / 4.2);
			tone = 3.4 + mstep * 0.5 + (cush > 0.62 ? 1.0 : (cush < 0.3 ? -1.0 : 0.0));
		} else if (best == 5) {
			row = e3.r > 0.75 ? 8.0 : (e3.r > 0.25 ? 7.0 : 6.0);
			tone = 3.2 + mstep * 0.8 + (w3_hash(pc * 0.83) < 0.15 ? -1.0 : 0.0);
		} else if (best == 6) {
			row = 9.0;
			float layer = floor(wp.y * 1.55 + w3_vnoise(pc / 8.0) * 1.2);
			float lk = smoothstep(0.85, 0.6, n.y);
			tone = 3.2 + mstep * 0.5 + floor((w3_hash(vec2(layer, 3.0)) - 0.5) * 1.6 * lk + 0.5);
			// the earth's grain: crumbs and small stones, darker hollows (seen closer than from above)
			float gq = w3_hash(pc * 0.71 + 12.0);
			tone += gq < 0.12 ? -1.0 : (gq > 0.92 ? 1.0 : 0.0);
			// roots and stones in the cut earth, in short runs along the layers
			if (lk > 0.5 && w3_hash(vec2(floor(pc.x / 3.0), pc.y) * 0.57 + 4.0) < 0.06) tone -= 1.5;
		} else {
			row = 10.0;
			tone = 3.0 + mstep * 0.5;
		}
		alb = sw_dry >= 0.0 ? w3_sward_col(sw_dry, tone) : pal(row, tone);
		// the terraces' paddies: water holding the sky, young rice in sparse rows across it
		if (best == 7) {
			water = true;
		}
	} else {
		vec4 md = v_mid_data(xz);
		vec4 mt = v_mat_data(xz);
		float mw = v_mid_weight(xz);
		vec4 fd = v_far_data(xz);
		float forest = mix(fd.b, md.b, mw);
		float wat = mix(fd.a, md.a, mw);
		float cult = mt.r * mw;
		float road = mt.g * mw;
		float rock = max(mt.b * mw, smoothstep(44.0, 56.0, slope));
		bool plain = wp.y < -270.0 && slope < 9.0 && v_mist_e(xz) > 1.08;
		// grass and scrub as the base
		float tone = 3.4 + floor((clump - 0.5) * 2.6 + 0.5) + (n1 < 0.14 ? -1.0 : (n1 > 0.9 ? 1.0 : 0.0));
		alb = pal(n1 > 0.55 && clump > 0.6 ? 1.0 : 0.0, tone);
		if (plain) {
			// the plain in early summer: blocks of paddies in strips (young rice, a few still flooded
			// and holding the sky), dry fields and fallow, groves round the villages, lanes, the river
			vec4 pm = v_plain_data(xz);
			float d_river = pm.r * 255.0;
			float d_road = pm.g * 127.5;
			float dens = pm.b;
			v_town = dens;
			float pxm = dist / v_ppr;                      // metres per pixel here
			// (the paddies follow an old grid that turns slowly across the plain)
			float ang = (w3_vnoise(xz / 2600.0 + 3.0) - 0.5) * 0.9;
			vec2 ax = vec2(cos(ang), sin(ang));
			vec2 uv = vec2(dot(xz, ax), dot(xz, vec2(-ax.y, ax.x)));
			vec2 bc = floor(uv / vec2(240.0, 180.0));
			float bh = w3_hash(bc + 3.3);
			float sw = mix(16.0, 28.0, w3_hash(bc + 9.1));
			float along = uv.y;
			float si = floor(along / sw);
			float sh = w3_hash(vec2(si, floor(uv.x / 110.0) + floor(bh * 97.0)));
			float kind = mix(sh, w3_vnoise(uv / 500.0), 0.45);   // fields of a kind in groups
			if (kind < 0.5) alb = pal(0.0, 4.6 + floor(sh * 4.0) * 0.5);           // young rice
			else if (kind < 0.66) alb = pal(5.0, 5.2);                           // rice further on
			else if (kind < 0.74) { water = true; }                              // still flooded
			else if (kind < 0.87) { alb = pal(6.0, 4.4 + floor(sh * 9.0) * 0.3); plate = V_EARTH; }   // dry fields
			else { alb = pal(8.0, 4.0); plate = V_EARTH; }                       // fallow
			// (the key block: the paddies' blocks, where a block is a few pixels across)
			vec2 bl = abs(fract(uv / vec2(240.0, 180.0)) - 0.5) * vec2(240.0, 180.0);
			if (pxm < 50.0 && max(bl.x - 120.0 + pxm * 0.55, bl.y - 90.0 + pxm * 0.55) > 0.0) ink = 1.0;
			// the levees between the strips, where the pixel can hold them
			if (pxm < sw * 0.4 && fract(along / sw) < max(0.06, pxm * 0.5 / sw)) alb = pal(0.0, 3.0);
			// groves and gardens round the villages, a tree line along the lanes
			if (dens > 0.18 + w3_hash(cell * 0.7) * 0.3) {
				float g = w3_vnoise(xz / max(6.0, pxm * 2.0));
				alb = g > 0.5 ? srgb(vec3(0.21, 0.29, 0.16)) : srgb(vec3(0.16, 0.23, 0.13));
				water = false;
				plate = V_GREEN;
			}
			// (the key block: a village's grove drawn round)
			if (abs(dens - 0.33) < max(fwidth(dens) * 0.6, 1e-4)) ink = 1.0;
			if (d_road < max(2.6, pxm * 0.55)) { alb = pal(8.0, 6.0); water = false; plate = V_EARTH; ink = 1.0; }
			else if (d_road < max(5.0, pxm * 1.1) && w3_hash(floor(xz / 9.0)) > 0.55) { alb = srgb(vec3(0.19, 0.27, 0.15)); water = false; plate = V_GREEN; }
			float r_edge = 34.0 + w3_vnoise(xz / 90.0) * 10.0;
			if (d_river < r_edge) { water = true; v_river = 1.0; }
			else if (d_river < 44.0) { alb = pal(9.0, 3.0); water = false; plate = V_EARTH; }        // its banks
			// (the key block: the river's banks)
			if (abs(d_river - r_edge) < max(pxm * 0.55, fwidth(d_river) * 0.6)) ink = 1.0;
		}
		if (cult > 0.5) {
			// the lower layer's terraces: young rice in muted greens, a few strips still flooded
			float rowf = (wp.y + w3_vnoise(xz / 30.0) * 2.0) / 1.6;
			float rh = w3_hash(vec2(floor(rowf), 3.0));
			alb = pal(rh < 0.3 ? 5.0 : 0.0, rh < 0.3 ? 5.4 : 4.8);
			if (rh > 0.72) { water = true; }
			// the risers: grass banks, darker
			if (fract(rowf) < 0.18) { alb = pal(0.0, 2.5); water = false; }
		}
		// (the key block: the edges of the terraces, the woods, the water)
		if (abs(cult - 0.5) < max(fwidth(cult) * 0.6, 1e-4)) ink = 1.0;
		if (!plain && abs(forest - 0.4) < max(fwidth(forest) * 0.6, 1e-4)) ink = 1.0;
		if (!plain && abs(wat - 0.5) < max(fwidth(wat) * 0.6, 1e-4)) ink = 1.0;
		bool far_hill = !plain && dist > 2600.0;
		wood = (forest > 0.4 && !plain) ? 1.0 : 0.0;
		if (forest > 0.4 && !plain) {
			// canopy seen from above: dark clumps, lit crowns
			float k = dist > 160.0 ? vnoise3(wq / max(4.0, dist * 0.012) + 3.0) : w3_vnoise(pl / max(4.0, dist * 0.012) + 3.0);
			alb = k > 0.62 ? srgb(vec3(0.27, 0.36, 0.19)) : (k > 0.35 ? srgb(vec3(0.2, 0.29, 0.16)) : srgb(vec3(0.13, 0.2, 0.12)));
		}
		if (rock > 0.5 && !far_hill) {
			// rock faces: bands along the height (strata), in clusters, not salt and pepper
			float k = w3_vnoise(vec2((xz.x + xz.y) / max(6.0, dist * 0.03), wp.y / max(1.2, dist * 0.006)));
			alb = pal(4.0, 2.6 + floor((k - 0.5) * 2.2 + 0.5));
			plate = V_EARTH;
		}
		if (far_hill) {
			// far mountains: masses, not texture: woods dark, open slopes and crags lighter, in a few
			// large patches (the light's bands and the haze give them their form)
			float k = w3_vnoise(xz / 520.0 + 7.0);
			alb = forest > 0.4 ? (k > 0.5 ? srgb(vec3(0.22, 0.3, 0.18)) : srgb(vec3(0.18, 0.25, 0.16)))
				: (slope > 38.0 ? pal(4.0, 4.0) : pal(0.0, k > 0.55 ? 5.0 : 4.0));
			plate = (forest <= 0.4 && slope > 38.0) ? V_EARTH : V_GREEN;
		}
		if (road > 0.5) {
			alb = pal(2.0, 4.0 + (n1 < 0.2 ? -1.0 : 0.0));
			plate = V_EARTH;
		}
		if (mt.a * mw > 0.5) {
			// a dry-stone wall (the temple's terrace): courses of grey stones, dark joints
			float course = floor(wp.y / 0.55);
			float blk = floor((pl.x + w3_hash(vec2(course, 1.0)) * 1.3) / 1.1);
			alb = pal(3.0, 4.6 + (w3_hash(vec2(course, blk)) - 0.5) * 2.0);
			if (fract(wp.y / 0.55) < 0.2 && dist < 900.0) alb = pal(3.0, 2.2);
			plate = V_EARTH;
		}
		if (wat > 0.5 && !plain) {
			water = true;
		}
		// the shade of the sea of clouds on the land below it
		v_shade = wp.y < sea_base ? v_cloud_shade(wp) : 0.0;
	}
	if (water) {
		// water: the sky's colour (brighter toward the horizon, where it mirrors the low sky), a
		// lighter line here and there where the wind ruffles it; the river sparkles toward the sun
		vec3 v = normalize(eye - wp);
		// (the region's own paddies are shallow and full of young rice: they hold less of the sky)
		float graze = (1.0 - clamp(v.y * 4.0, 0.0, 1.0)) * (local ? 0.35 : 1.0);
		vec3 sky = mix(mix(haze_col, w3_sky * 1.6, 0.35), haze_col * 1.05, graze);
		alb = mix(sky * mix(0.5, 0.86, graze), pal(0.0, 3.0), 0.3 * (1.0 - graze));
		vec2 rq = vec2(xz.x * 0.4, xz.y * 2.0) / max(1.0, dist * 0.004) + cloud_time * 0.05;
		float ruffle = w3_vnoise(rq);
		// (a ruffled line only where it is a few pixels long: far off it would be streaks)
		if (ruffle > 0.8 && (v_river > 0.5 || dist < 700.0)) alb = sky * mix(0.72, 0.98, graze);
		vec3 sd = normalize(w3_sun_dir);
		vec3 rv = vec3(-v.x, v.y, -v.z);
		float glint = dot(rv, sd);
		if (v_river > 0.5 && sd.y > 0.0 && glint > 0.9 - 0.06 * ruffle && w3_hash(floor(xz / max(2.0, dist * 0.0027))) > 0.55) {
			alb = w3_sun * 0.34 * (1.0 - v_shade);
		}
		alb *= 1.0 - v_shade * 0.35;
		v_alb = alb;
		ALBEDO = vec3(0.0);
		// (in the 遠化 the water is its block, flat and still: no sky's gradation, no ruffle, no glint;
		// then paper with its banks drawn)
		vec3 w_flat = mix(haze_col, w3_sky * 1.6, 0.35) * 0.62 / max(w3_luma(v_print_light()), 1e-3);
		EMISSION = v_print(v_air(alb, wp, eye, FRAGCOORD.xy), w_flat, V_BLUE, n, wp, eye, FRAGCOORD.xy);
		if (ink > 0.5 && v_past(wp, eye, FRAGCOORD.xy)) EMISSION = v_ink();
	} else {
		v_alb = alb;
		ALBEDO = vec3(1.0);
		EMISSION = v_print(v_air(w3_ambient(alb, n, 1.0) * (1.0 - v_shade * 0.25), wp, eye, FRAGCOORD.xy), v_flat(plate, alb), plate, n, wp, eye, FRAGCOORD.xy);
		// the key block's lines where the print has lost its gradations
		if (ink > 0.5 && v_past(wp, eye, FRAGCOORD.xy)) EMISSION = v_ink();
		// and its woods: once the green block is gone a wood is small crowns in ink on the paper, as a
		// print draws a wooded hill (a white field there read as snow)
		if (wood > 0.5 && v_past(wp, eye, FRAGCOORD.xy) && v_plate_on(V_GREEN, xz, dist, FRAGCOORD.xy) < 0.5) {
			vec2 pc = v_dir_cell(wp, eye);
			vec2 cc = floor(pc / vec2(4.0, 3.0));
			vec2 q = pc - cc * vec2(4.0, 3.0) - vec2(floor(w3_hash(cc + 9.1) * 2.0), 0.0);
			bool crown = (q.y == 1.0 && q.x == 1.0) || (q.y == 0.0 && (q.x == 0.0 || q.x == 2.0));
			if (crown && w3_hash(cc * 1.7 + 3.0) < 0.6) EMISSION = v_ink();
		}
		if (dbg_mode == 1) { EMISSION = vec3(clamp(slope / 60.0, 0.0, 1.0), n.y, 0.0); ALBEDO = vec3(0.0); }
		if (dbg_mode == 3) { EMISSION = alb; ALBEDO = vec3(0.0); }
		if (dbg_mode == 4) { EMISSION = w3_ambient(alb, n, 1.0); ALBEDO = vec3(0.0); }
		if (dbg_mode == 2) { EMISSION = (local ? vec3(0,0,1) : (wp.y < -270.0 ? vec3(1,0,0) : vec3(0,1,0))) * 0.5; ALBEDO = vec3(0.0); }
		// the home's lanterns light their pools on the ground at night (the same lamps as the
		// top-down world: render3d/lamps.gd)
		if (local) {
			EMISSION += w3_lamp_light(alb, wp, n, cell, 1.0) * v_air_keep(wp, eye, FRAGCOORD.xy);
		}
	}
	// (round 5, G5R3-1: no glow of streets at night any more, the city is gone and the lead wants
	// only a scattering of warm windows in the villages: vista_house)
	// (the 遠化's edge, a line of light where the white meets the land, is drawn by vista_post)
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 c = v_sun_bands(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_wp, eye);
		// the sun's share fades with the same air as the rest, and under the clouds' shade
		DIFFUSE_LIGHT += c * v_air_keep(v_wp, eye, FRAGCOORD.xy) * (1.0 - v_shade);
	}
}
