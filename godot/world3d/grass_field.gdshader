// The grass field (round 5, scene agent; decision-log G5R3-2: "自然柔顺，和地面的颜色同一个系、协调一致又明显
// 分得开；有物理效果"). Small blade tufts standing on the terrain as pixel-art cards, texel for pixel.
//
// Placement here, not on disk: world3d/grass.gd draws one MultiMesh per 16 m chunk (the node sits on
// the chunk's corner; `lattice` x `lattice` instances, identity transforms); INSTANCE_ID picks a
// lattice cell, hashes jitter it, the terrain's height texture puts the root on the ground and gives
// its normal, and the sward map m4 (tools/world3d/w3terrain/grassfield.py: density, height, flower
// patches, thin) decides whether a tuft grows there, how tall and which cell of the atlas it shows.
// * Colour is the ground's: the tuft takes the terrain's palette row (grass / dry grass, by the same
//   dryness rule) and the terrain's macro tone at its root, computed exactly as toon_terrain does
//   (render3d/shaders/toon_terrain.gdshader, mat 0), so the root pixels ARE the ground's colour; the
//   blades go `tip_lift` tones lighter toward their tips (the ramp's lights lean warm). No tints.
// * Light is the ground's: the ground normal, the terrain's wrap, its AO, its painted shade
//   (w3_paint_shade, shade_flatten) and its sun flecks in the canopy's shade.
// * Motion in whole pixels: the renderer's sway (w3_wind_px), gust fronts that run across the field
//   with the wind (the blades bend and show their lighter backs: a pale band travelling over the
//   sward), and the bend map (world3d/grass.gd): pushed aside and pressed down where she, Saji and the
//   small creatures walk, standing up again over a few seconds.
// Mesh: one quad, UV 0..1 (v up), UV2 = corner offset in native px from the root.
// Outline class 5 (none). Casts no shadow (the instances turn it off); receives them.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_disabled;
stencil_mode write, compare_always, 5;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D blades : filter_nearest;                  // cells of 16 x 16: R tone offset + 4, G accent + 1, A coverage
uniform sampler2D palette : filter_nearest;                 // the terrain's palette (8 tones x 16 rows, sRGB)
uniform sampler2D heights : filter_linear, repeat_disable;  // the terrain's heights (RF, one texel per cell)
uniform sampler2D m2 : filter_linear, repeat_disable;       // the terrain's splat: ao, puddle, wear, flowers
uniform sampler2D m3 : filter_linear, repeat_disable;       // the terrain's splat: litter kind, dryness, tufts, canopy
uniform sampler2D m4 : filter_linear, repeat_disable;       // the sward: density, height, flower patches, thin
uniform sampler2D bend : filter_linear, repeat_disable;     // rg: push direction x/z (0.5 = none), b: pressed
uniform vec2 h_origin = vec2(-80.0, -96.0);
uniform float h_cell = 0.5;
uniform vec2 h_size = vec2(321.0, 417.0);
uniform vec2 splat_origin = vec2(-80.0, -96.0);
uniform float splat_cell = 0.25;
uniform vec2 splat_size = vec2(641.0, 833.0);
uniform vec2 bend_origin = vec2(-80.0, -96.0);
uniform vec2 bend_extent = vec2(160.0, 208.0);
uniform int lattice = 50;
uniform float chunk = 16.0;
uniform int cols = 8;
uniform float dry_bias = 0.12;                              // as the terrain's
uniform float shade_flatten : hint_range(0.0, 1.0) = 0.6;   // as the terrain's
uniform float tip_lift = 1.0;                               // palette tones from root to tip
uniform float flower_k = 0.03;                              // flowers per tuft in a full flower patch
uniform float gust_px = 2.0;                                // how far a gust front bends the tips
uniform float gust_len = 11.0;                              // metres between gust fronts
uniform float gust_speed = 3.4;                             // m/s
uniform float push_px = 3.0;                                // how far her feet push the tips aside

varying vec3 v_wp;
varying flat float v_cellk;
varying flat vec3 v_col;      // palette row, the root's tone, gust 0..1
varying flat float v_ao;
varying float v_fleck;
varying vec3 v_detail;        // albedo / the shade's flattened albedo (light() restores the detail)

vec3 pal(float row, float tone) {
	vec3 c = texelFetch(palette, ivec2(int(clamp(floor(tone + 0.5), 0.0, 7.0)), int(row)), 0).rgb;
	return w3_srgb_to_linear(c);
}

float ground_h(vec2 xz) {
	return textureLod(heights, ((xz - h_origin) / h_cell + 0.5) / h_size, 0.0).r;
}

void vertex() {
	vec3 corner = MODEL_MATRIX[3].xyz;
	int i = INSTANCE_ID % lattice;
	int j = INSTANCE_ID / lattice;
	vec2 lc = vec2(float(i), float(j));
	vec2 seed = lc * 1.37 + corner.xz * 0.731;
	float r1 = w3_hash(seed + 0.17);
	float r2 = w3_hash(seed + 5.31);
	float r3 = w3_hash(seed + 11.9);
	float r4 = w3_hash(seed + 23.1);
	float r5 = w3_hash(seed + 37.7);
	float sp = chunk / float(lattice);
	vec2 xz = corner.xz + (lc + 0.5 + (vec2(r1, r2) - 0.5) * 0.9) * sp;
	vec2 suv = (xz - splat_origin) / splat_cell / splat_size;
	vec4 sw = textureLod(m4, suv, 0.0);
	float y = ground_h(xz);
	vec3 anchor = vec3(xz.x, y, xz.y);
	v_wp = anchor;
	v_cellk = 0.0;
	v_col = vec3(0.0);
	v_ao = 1.0;
	if (r3 >= sw.r) {
		// no tuft here: a quad of no size (the rasteriser drops it)
		VERTEX = anchor;
		NORMAL = vec3(0.0, 1.0, 0.0);
	} else {
		float e = h_cell;
		vec3 n = normalize(vec3(ground_h(xz - vec2(e, 0.0)) - ground_h(xz + vec2(e, 0.0)), 2.0 * e,
				ground_h(xz - vec2(0.0, e)) - ground_h(xz + vec2(0.0, e))));
		// which tuft: by the sward's height (a little jitter), a thin one on moss, now and then a flower
		float H = clamp(sw.g + (r4 - 0.5) * 0.16, 0.0, 1.0);
		float cls = H < 0.3 ? 0.0 : (H < 0.55 ? 1.0 : (H < 0.8 ? 2.0 : 3.0));
		float ck = cls * 4.0 + floor(r5 * 3.999);
		if (sw.a > 0.5) {
			ck = 24.0 + floor(r5 * 3.999);
		}
		if (w3_hash(seed + 51.3) < flower_k * sw.b) {
			float kind = floor(mod(w3_fbm(xz / 9.0) * 8.0, 4.0));
			ck = 16.0 + kind + (r4 < 0.5 ? 4.0 : 0.0);
		}
		v_cellk = ck;
		float flex = clamp(0.35 + 0.65 * H, 0.25, 1.0);
		vec3 a = anchor + w3_snap(anchor);
		float top = UV.y;                                  // 0 root .. 1 tips
		vec2 sway = w3_wind_px(anchor, flex, 1.0);
		// gust fronts: narrow bands across the wind that run downwind, broken along their length
		vec2 wd = w3_wind.xy;
		float wl = length(wd);
		wd = wl > 1e-3 ? wd / wl : vec2(1.0, 0.0);
		float along = dot(xz, wd);
		float across = dot(xz, vec2(-wd.y, wd.x));
		float ph = (along - w3_time * gust_speed) / gust_len + w3_vnoise(vec2(across / 9.0, along / 23.0)) * 0.9;
		float front = pow(0.5 + 0.5 * sin(ph * 6.2831853), 5.0);
		float g = front * smoothstep(0.3, 0.62, w3_vnoise(vec2(across / 13.0 + w3_time * 0.03, along / 19.0 + 3.1)));
		g *= clamp(w3_wind.z * 0.55 + w3_wind.w * 0.6, 0.0, 1.0);
		if (w3_bake > 0.5) {
			g = 0.0;
		}
		sway.x += wd.x * g * gust_px * flex;
		sway.y -= g * flex;
		// the bend map: pushed aside and pressed down where something walked, recovering slowly
		vec4 b = textureLod(bend, (xz - bend_origin) / bend_extent, 0.0);
		vec2 push = (b.rg - 0.5) * 2.0;
		float pressed = clamp(b.b, 0.0, 1.0);
		sway.x += push.x * push_px;
		float squash = 1.0 - 0.55 * pressed;
		vec2 off = vec2(UV2.x + floor(sway.x * top + 0.5), floor(UV2.y * squash + sway.y * top + 0.5));
		vec3 wp = a + vec3(off.x / w3_view.x, off.y / w3_view.x, -w3_view.w * off.y / w3_view.x);
		VERTEX = wp;
		v_wp = wp;
		NORMAL = n;
		// the ground's colour at the root: its row (grass or dry grass) and its macro tone, as the terrain
		vec4 e2 = textureLod(m2, suv, 0.0);
		vec4 e3 = textureLod(m3, suv, 0.0);
		float dry = e3.g + (w3_fbm(xz / 3.0 + 7.0) - 0.5) * 0.25;
		float row = dry > 0.5 + dry_bias ? 1.0 : 0.0;
		float macro = w3_fbm(xz / 7.5) * 2.6 - 1.3;
		v_col = vec3(row, 3.6 + floor(macro + 0.5), g);
		v_ao = mix(0.55, 1.0, smoothstep(0.45, 1.0, e2.r));
	}
}

void fragment() {
	int ci = int(v_cellk + 0.5);
	ivec2 base = ivec2((ci % cols) * 16, (ci / cols) * 16);
	ivec2 tp = base + ivec2(int(clamp(floor(UV.x * 16.0), 0.0, 15.0)), int(clamp(15.0 - floor(UV.y * 16.0), 0.0, 15.0)));
	vec4 t = texelFetch(blades, tp, 0);
	if (t.a < 0.5) {
		discard;
	}
	// cards are double-sided and may face either way: keep the ground normal they were given
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	int acc = int(t.g * 255.0 + 0.5) - 1;
	float lift = t.r * 255.0 - 4.0;
	// in a gust the bent tips show their lighter backs
	float tone = v_col.y + lift * tip_lift + ((lift > 0.5 && v_col.z > 0.4) ? 1.0 : 0.0);
	vec3 alb = acc >= 0 ? w3_srgb_to_linear(texelFetch(palette, ivec2(acc % 8, 11 + acc / 8), 0).rgb) : pal(v_col.x, tone);
	vec3 flat_alb = pal(v_col.x, v_col.y);
	alb = w3_wetten(alb, 0.6);
	flat_alb = w3_wetten(flat_alb, 0.6);
	// sun flecks in the canopy's shade, as on the ground under it
	vec3 sdir = normalize(w3_sun_dir);
	vec2 proj = v_wp.xz + sdir.xz / max(sdir.y, 0.25) * 11.0;
	float can = texture(m3, (proj - splat_origin) / splat_cell / splat_size).a;
	v_fleck = 0.0;
	if (can > 0.2 && w3_night < 0.5) {
		float swy = sin(w3_time * 0.8 + w3_hash(floor(v_wp.xz / 1.5)) * 6.28) * 0.35 * w3_wind.z;
		vec2 fq = v_wp.xz / 0.42 + vec2(swy, swy * 0.5);
		float fn = w3_vnoise(fq) * 0.7 + w3_vnoise(fq * 2.1 + 5.0) * 0.3;
		float cluster = w3_vnoise(v_wp.xz / 2.6 + 9.0);
		v_fleck = step(0.69 + can * 0.05, fn) * step(0.34 + can * 0.22, cluster);
	}
	vec3 a_shade = w3_paint_shade(mix(alb, flat_alb, shade_flatten));
	v_detail = alb / max(a_shade, vec3(1e-4));
	ALBEDO = a_shade;
	AO = v_ao;
	AO_LIGHT_AFFECT = 0.0;
}

void light() {
	// lit as the ground it grows from (toon_terrain's light)
	if (LIGHT_IS_DIRECTIONAL) {
		float sh = max(ATTENUATION, v_fleck * 0.85);
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, sh, 0.15) * v_detail;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.4) * v_detail;
	}
}
