// vista_common.gdshaderinc — shared by the shaders of the view from the lookout (W3Vista,
// godot/world3d/vista3d.gd): a perspective camera in its own world, drawn at native resolution in
// the same pixel-art language as the top-down world. Height maps, aerial perspective (haze toward
// the horizon colour, continuous), the sea of clouds over the lowland (where its banks may lie, how
// they creep, the shade they cast on the plain), and the 遠化 beyond the region's ring: the land
// there sinks into the air with distance, faster than the haze alone would take it, and past a front
// that wanders round the region a few kilometres out it is far land in the air's blue-grey, low in
// contrast, layer behind layer (round 4: no longer a flat white with a bright edge, which read as a
// beach).
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D mid_tex : filter_nearest, repeat_disable;   // RG u16 height, B forest, A water
uniform sampler2D mat_tex : filter_nearest, repeat_disable;   // R cultivated, G road, B rock, A stone wall
uniform sampler2D far_tex : filter_nearest, repeat_disable;   // RG u16 height, B forest, A water
uniform vec4 mid_frame = vec4(-640.0, -560.0, 1.0, 1281.0);   // x0, z0, cell, n
uniform vec2 mid_h = vec2(-480.0, 960.0);                     // min, range
uniform vec4 far_frame = vec4(-16000.0, -16000.0, 32.0, 1001.0);
uniform vec2 far_h = vec2(-480.0, 2400.0);
uniform vec4 mist_ellipse = vec4(-50.0, 100.0, 430.0, 370.0);  // centre x, z, radii x, z
uniform vec3 haze_col : source_color = vec3(0.7, 0.75, 0.8);   // linear; the horizon of the sky
uniform vec3 mist_col : source_color = vec3(0.8, 0.8, 0.84);   // linear; the 遠化's pale land
uniform vec3 far_white = vec3(0.66, 0.635, 0.59);              // linear; past the front (its edge glows brighter)
uniform float haze_dist = 2200.0;                              // metres for 63 % haze
uniform float mist_max = 1.0;               // the 遠化's strength (1: as drawn)
uniform sampler2D plain_tex : filter_linear, repeat_disable;   // R river m, G road m*2, B village, A rail m*2
uniform vec4 plain_frame = vec4(-6000.0, 400.0, 8.0, 1501.0);  // x0, z0, cell, n
uniform float cloud_time = 0.0;             // seconds (the clouds drift)
uniform float city_lights = 0.0;            // the plain's lamplight: 0 by day .. 1 at night (on with the dusk)
uniform float sea_base = -255.0;            // the sea of clouds' flat underside (m)
uniform vec3 front_c = vec3(-50.0, 0.0, 4300.0);  // the 遠化 front: centre x, z, mean radius (m)
uniform float v_ppr = 371.0;                // native pixels per radian
uniform vec4 v_cam = vec4(3.1416, -0.2, 240.0, 135.0);   // the view: yaw (rad, as atan(x, -z)), pitch (rad, up +), half size (px)
uniform vec2 v_lat = vec2(0.0);             // yaw and pitch in whole pixels (the lattice's offset)

// ------------------------------------------------------------------------------------------------
// The vista's projection: equirectangular about the world's vertical axis. A screen pixel is a fixed
// step of azimuth across and of elevation up, so when she turns her head (yaw and pitch in whole
// pixels) the whole picture moves by whole pixels, the same pixels, everywhere on the screen: no
// crawl. (A perspective camera keeps only its centre still when it turns; the sides slide by
// fractions of a pixel and every grain re-samples.) World verticals stay vertical and the horizon
// flat; at this field of view (74 x 42 degrees) the rest bends very little. The depth (the depth
// buffer, the outlines, the interpolation) is the distance from the eye. Vertices behind her are
// clipped away (a triangle across the seam behind her would span the whole picture).

// pixels from the centre of the view (y up) of a world point
vec2 v_px_of(vec3 wp, vec3 cam) {
	vec3 d = wp - cam;
	float az = atan(d.x, -d.z);
	float el = atan(d.y, length(d.xz));
	float da = mod(az - v_cam.x + W3_PI, 2.0 * W3_PI) - W3_PI;
	return vec2(da, el - v_cam.y) * v_ppr;
}
vec3 v_fwd() {
	return vec3(sin(v_cam.x) * cos(v_cam.y), sin(v_cam.y), -cos(v_cam.x) * cos(v_cam.y));
}
// clip position of a point px pixels from the centre at a distance (the camera's own depth row)
vec4 v_clip(vec2 px, float dist, mat4 proj) {
	vec4 c = proj * vec4(0.0, 0.0, -max(dist, 0.3), 1.0);
	vec2 sgn = vec2(sign(proj[0][0]), sign(proj[1][1]));
	return vec4(px / v_cam.zw * sgn * c.w, c.z, c.w);
}
vec4 v_project(vec3 wp, vec3 cam, mat4 proj) {
	vec2 px = v_px_of(wp, cam);
	if (abs(px.x) > 1.75 * v_ppr) {
		return vec4(0.0, 0.0, 0.0, -1.0);
	}
	return v_clip(px, length(wp - cam), proj);
}
// a point moved onto the lattice of pixel corners (sprites drawn texel for pixel from it)
vec2 v_snap(vec2 px) {
	vec2 f = fract(v_cam.zw);
	return floor(px - f + 0.5) + f;
}
// the direction from the view of a pixel (px from the centre, y up)
vec3 v_dir_of(vec2 px) {
	float az = v_cam.x + px.x / v_ppr;
	float el = v_cam.y + px.y / v_ppr;
	return vec3(sin(az) * cos(el), sin(el), -cos(az) * cos(el));
}
// The pixel cell of a world point on the lattice of directions: one cell per screen pixel, fixed to
// the world (the camera only turns, by whole pixels), square on the screen whatever the surface's
// angle (cells fixed to the map stretch into streaks where the land is seen at a grazing angle).
vec2 v_dir_cell(vec3 wp, vec3 cam) {
	return floor(v_px_of(wp, cam) + v_cam.zw + v_lat);
}

// a 4x4 ordered dither threshold (0..1) for a pixel cell
float v_bayer(vec2 cell) {
	ivec2 i = ivec2(mod(cell, 4.0));
	int k = i.x + i.y * 4;
	float m[16] = float[](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[k] + 0.5) / 16.0;
}

float v_u16(vec4 t, vec2 hr) {
	return hr.x + (t.r * 255.0 * 256.0 + t.g * 255.0) / 65535.0 * hr.y;
}

// bilinear height from a u16 RG map (the two bytes must be decoded before they are blended)
float v_height_map(sampler2D tex, vec4 frame, vec2 hr, vec2 xz) {
	vec2 g = (xz - frame.xy) / frame.z;
	g = clamp(g, vec2(0.0), vec2(frame.w - 1.001));
	vec2 i = floor(g);
	vec2 f = g - i;
	ivec2 p = ivec2(i);
	float a = v_u16(texelFetch(tex, p, 0), hr);
	float b = v_u16(texelFetch(tex, p + ivec2(1, 0), 0), hr);
	float c = v_u16(texelFetch(tex, p + ivec2(0, 1), 0), hr);
	float d = v_u16(texelFetch(tex, p + ivec2(1, 1), 0), hr);
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// 1 inside the mid map (1 m), fading to 0 over its outer 60 m
float v_mid_weight(vec2 xz) {
	vec2 lo = mid_frame.xy;
	vec2 hi = mid_frame.xy + vec2(mid_frame.w - 1.0) * mid_frame.z;
	float e = min(min(xz.x - lo.x, hi.x - xz.x), min(xz.y - lo.y, hi.y - xz.y));
	return smoothstep(0.0, 60.0, e);
}

float v_height(vec2 xz) {
	float w = v_mid_weight(xz);
	float hf = v_height_map(far_tex, far_frame, far_h, xz);
	if (w <= 0.0) return hf;
	float hm = v_height_map(mid_tex, mid_frame, mid_h, xz);
	return mix(hf, hm, w);
}

vec4 v_mid_data(vec2 xz) {
	vec2 g = (xz - mid_frame.xy) / mid_frame.z;
	return texelFetch(mid_tex, ivec2(clamp(floor(g + 0.5), vec2(0.0), vec2(mid_frame.w - 1.0))), 0);
}
vec4 v_mat_data(vec2 xz) {
	vec2 g = (xz - mid_frame.xy) / mid_frame.z;
	return texelFetch(mat_tex, ivec2(clamp(floor(g + 0.5), vec2(0.0), vec2(mid_frame.w - 1.0))), 0);
}
// the plain's map, bilinear (distance fields: crisp edges at any distance)
vec4 v_plain_data(vec2 xz) {
	vec2 g = (xz - plain_frame.xy) / plain_frame.z;
	return texture(plain_tex, (g + 0.5) / plain_frame.w);
}
vec4 v_far_data(vec2 xz) {
	vec2 g = (xz - far_frame.xy) / far_frame.z;
	return texelFetch(far_tex, ivec2(clamp(floor(g + 0.5), vec2(0.0), vec2(far_frame.w - 1.0))), 0);
}

// elliptic distance from the region's middle: 1 on the mist's inner edge
float v_mist_e(vec2 xz) {
	return length((xz - mist_ellipse.xy) / mist_ellipse.zw);
}

// ------------------------------------------------------------------------------------------------
// the sea of clouds: banks of billows (vista_cloud.gdshader), laid out by vista3d.gd _build_mist in a
// square domain round the region; they creep east with the wind, wrapping round the domain (far
// beyond the front, where no bank has room). cloud_tex over the domain: R the banks' shade on the
// land below as they lay at the start, G the room a bank has at a place (fixed to the land).

uniform sampler2D cloud_tex : filter_linear, repeat_disable;
uniform vec4 cloud_box = vec4(-4950.0, -4900.0, 9800.0, 9800.0);   // x0, z0, width, depth (m)
uniform vec2 cloud_wind = vec2(0.45, 0.0);                         // m/s

// how far a bank (by its centre at the start) has crept by now: east with the wind, round the domain
vec3 v_cloud_shift(vec2 bc) {
	vec2 d = cloud_wind * cloud_time;
	float x = cloud_box.x + mod(bc.x + d.x - cloud_box.x, cloud_box.z);
	return vec3(x - bc.x, 0.0, d.y);
}
// the room a bank has at a place: 0 none (it dissolves) .. 1
float v_cloud_room(vec2 p) {
	vec2 uv = (p - cloud_box.xy) / cloud_box.zw;
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) return 0.0;
	return textureLod(cloud_tex, uv, 0.0).g;
}
// the shade of the banks on the land below (0 open sky .. 1 under a bank)
float v_cloud_shade(vec3 wp) {
	vec3 sd = normalize(w3_sun_dir);
	if (sd.y < 0.05) return 0.0;
	vec2 p = wp.xz + sd.xz / sd.y * (sea_base + 40.0 - wp.y);
	// where that point of the sky lay at the start (the banks creep with the wind)
	vec2 p0 = p - cloud_wind * cloud_time;
	p0.x = cloud_box.x + mod(p0.x - cloud_box.x, cloud_box.z);
	vec2 uv = (p0 - cloud_box.xy) / cloud_box.zw;
	if (uv.y < 0.0 || uv.y > 1.0) return 0.0;
	return textureLod(cloud_tex, uv, 0.0).r * v_cloud_room(p);
}

// ------------------------------------------------------------------------------------------------
// the 遠化 as a print losing its blocks (褪版; round 5, the user G5R3-15/18: "遠化選a好了"). The 遠化
// is things that are still in their place and in sight but no longer "near" (the rule of the world:
// the more of its nature a thing has lost, the farther it is). So it is drawn as a woodblock print
// whose colour blocks come away, never as air: past the front (where the prologue's white tide
// stopped; it wanders round the region) the land keeps its place and its drawing, and its blocks
// go one after another, each at its own front farther out:
//   0 the gradations and the fine tones (bokashi: the light's modelling, the clouds' shade on the
//     land, the water's sky): the surfaces print flat, two tones to a block;
//   1 the green block (grass, rice, woods, leaves);
//   2 the water's blue;
//   3 the earths and ochres (soil, roads, dry fields, rock, roofs, wood, brick);
// at last only the key block is left: its ink lines (vista_post: the outlines; vista_ground: the
// borders of fields, woods, water, roads and villages) on the paper, and the paper's blind
// embossing (karazuri: the relief pressed into the white, a very light light and shade by the
// surface's normal). A block is printed or not (no fading toward white: a seam dithered on the
// screen pixel), so the blocks read one by one, not as a loss of saturation. Paper and ink are the
// palette's (far_white; the palette's ink K); no haze, no paling in the 遠化; at night no lamps there,
// the paper as dark as the night and the lines just legible. Nothing in it moves (vista_cloud,
// vista_puff, the water here; vista3d.gd). Anything that loses its nature later (「移」) is drawn by
// the same rule: v_print with its block.

const int V_PAPER = 0;      // white things: printed by no block (plaster, smoke, steam, clouds)
const int V_GREEN = 1;
const int V_BLUE = 2;
const int V_EARTH = 3;
// metres past the front where the gradations, the green, the blue, the earths are gone (each block's
// own front wanders a fifth either way). The front lies 4.4-6.2 km from the lookout, the far ranges
// 10-16 km: the blocks' fronts are about evenly spaced in 1 / distance (so on the screen), the
// flat print from the front, the green gone by about 6.5 km, the blue by 8, the earths by 10; the
// farthest ranges are the key block alone
uniform vec4 plate_at = vec4(300.0, 1500.0, 3000.0, 5000.0);
uniform vec3 ink_k = vec3(0.216, 0.184, 0.157);   // the palette's ink (K, sRGB; vista3d.gd sets it from the palette)
// the blocks' flat colours (linear; vista3d.gd sets them from the terrain's palette and the view's own
// colours): two tones to a block, light and dark
uniform vec3 print_green_lt = vec3(0.10, 0.13, 0.06);
uniform vec3 print_green_dk = vec3(0.033, 0.069, 0.022);
uniform vec3 print_earth_lt = vec3(0.20, 0.17, 0.12);
uniform vec3 print_earth_dk = vec3(0.07, 0.055, 0.04);

float v_front_r(vec2 xz) {
	vec2 d = xz - front_c.xy;
	float a = atan(d.x, -d.y);
	float w = w3_vnoise(vec2(a * 2.2 + 11.0, 3.0)) * 0.65 + w3_vnoise(vec2(a * 6.1 + 2.0, 7.0)) * 0.35;
	return front_c.z * (0.62 + 0.8 * w);
}
// metres past the 遠化's front (negative before it)
float v_past_m(vec2 xz) {
	return length(xz - front_c.xy) - v_front_r(xz);
}
// where block k is gone, metres past the front, wandering with the direction (its own line)
float v_plate_front(int k, vec2 xz) {
	vec2 d = xz - front_c.xy;
	float a = atan(d.x, -d.y);
	float w = w3_vnoise(vec2(a * 3.3 + float(k) * 17.0, float(k) * 5.0 + 1.0)) * 0.7 + w3_vnoise(vec2(a * 9.1 + float(k) * 3.0, 9.0)) * 0.3;
	return plate_at[k] * (0.8 + 0.4 * w);
}
// 1 while block k is still printed at this point, 0 past its front; the seam dithered over about two
// screen pixels (dist: from the eye, to size the seam)
float v_plate_on(int k, vec2 xz, float dist, vec2 frag) {
	float past = v_past_m(xz) - v_plate_front(k, xz);
	float seam = 2.0 * dist / v_ppr;
	return step(past, (w3_hash(floor(frag) + float(k) * 7.31) - 0.5) * seam);
}
// how far into the 遠化: 0 before the front .. 1 past the last block (only the key block)
float v_fade(vec2 xz) {
	float p = v_past_m(xz);
	return p <= 0.0 ? 0.0 : clamp(p / plate_at.w, 0.0, 1.0);
}
// the light a print shows: no modelling, the hour's light on a level surface (the sky above, the sun
// at round 3's middle level), so the faded land keeps the hour (warm at dusk, dark at night)
vec3 v_print_light() {
	return vec3(w3_luma(w3_sky)) * w3_shade_tint + w3_sun * w3_lit_tint * (0.78 / W3_PI);
}
// a block's flat colour for a surface of albedo alb (light or dark tone of the block)
vec3 v_flat(int plate, vec3 alb) {
	float l = w3_luma(alb);
	if (plate == V_GREEN) return l > 0.075 ? print_green_lt : print_green_dk;
	// (the earths: one light ochre for soil, roads, fields, rock; the dark only for wood and dark roofs:
	// dark flecks on the far ranges read as dirt)
	if (plate == V_EARTH) return l > 0.05 ? print_earth_lt : print_earth_dk;
	return alb;
}
// the paper, with its blind embossing: the relief pressed into it, read by the light on the slope
// against the light on level ground (a level paper is the paper; a face to the light a few
// hundredths lighter, one away a few darker)
vec3 v_emboss(vec3 n) {
	vec3 sd = normalize(w3_sun_dir);
	return far_white * (1.0 + 0.25 * clamp(dot(n, sd) - max(sd.y, 0.2), -0.4, 0.3));
}
// the key block's ink: the palette's K, printed (lit like the paper), a little of the paper through it
vec3 v_ink() {
	vec3 k = w3_srgb_to_linear(ink_k);
	float paper_l = max(w3_luma(far_white), 1e-4);
	// (lit as the paper is: the paper's own albedo is about 0.75)
	return mix(far_white, k * paper_l / 0.75, 0.78);
}
// a surface's colour past the front: amb its colour as drawn before the 遠化 (ambient-lit, without
// the sun); flat_c its block's flat colour (the albedo the print uses: two tones to a block, v_flat);
// plate its block; n its normal (world). Before the front it is amb.
vec3 v_print(vec3 amb, vec3 flat_c, int plate, vec3 n, vec3 wp, vec3 cam, vec2 frag) {
	float dist = length(wp - cam);
	if (v_plate_on(0, wp.xz, dist, frag) > 0.5) return amb;
	if (plate == V_PAPER || v_plate_on(plate, wp.xz, dist, frag) < 0.5) return v_emboss(n);
	return flat_c * v_print_light();
}
// the sun's share a surface keeps (the gradations go first: past the front no modelling)
float v_print_sun(vec3 wp, vec3 cam, vec2 frag) {
	return v_plate_on(0, wp.xz, length(wp - cam), frag);
}

// (compatibility: 1 in the 遠化 (past the front), else 0; the lamps and the outlines ask this)
float v_drain(vec2 xz, float y) {
	return v_past_m(xz) > 0.0 ? 1.0 : 0.0;
}

// the air before the 遠化: haze with distance, gone across the front's first stretch (nothing in the
// 遠化 hides in air)
float v_haze_k(vec3 wp, vec3 cam) {
	float d = length(wp - cam);
	// the air thins with height: far peaks stay legible above the lowland's haze
	float thin = mix(1.0, 0.35, smoothstep(-100.0, 700.0, wp.y));
	float h = 1.0 - exp(-d / haze_dist * thin);
	return clamp(h, 0.0, 1.0) * (1.0 - smoothstep(-400.0, plate_at.x, v_past_m(wp.xz))) * mist_max;
}
vec3 v_air(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	return mix(col, haze_col, v_haze_k(wp, cam));
}
// the clouds and the sky: the same air
vec3 v_air_only(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	return mix(col, haze_col, v_haze_k(wp, cam));
}
// what is left of the sun's light (added in light()) after the air and the 遠化's gradations
float v_air_keep(vec3 wp, vec3 cam, vec2 frag) {
	return (1.0 - v_haze_k(wp, cam)) * v_print_sun(wp, cam, frag);
}
// past the 遠化's first block (the gradations): the surfaces print flat
bool v_past(vec3 wp, vec3 cam, vec2 frag) {
	return v_print_sun(wp, cam, frag) < 0.5;
}
// (kept for the old callers: the paper with a share of ink)
vec3 v_paper(float ink) {
	return mix(far_white, v_ink(), ink);
}

// the toon sun of the vista: three bands, the painted shade of pixel_toon (w3_ambient); the band
// seams scattered on cells fixed to the world (about a pixel there)
// (the name is old: since round 4 the sun on the vista's land is continuous, a wrapped Lambert, and
// its shadows soft-edged, like the top-down world's)
vec3 v_sun_bands(vec3 alb, vec3 n, vec3 l, vec3 light_col, float att, vec3 wp, vec3 cam) {
	// round 3's levels (0.52 / 0.78 / 1 above n.l 0.04 / 0.30 / 0.62) as a smooth curve through the
	// middle of each (round 5, G5R3-1); round 4's at night
	float ndl = dot(n, l);
	float r3 = 0.52 * smoothstep(-0.08, 0.16, ndl) + 0.26 * smoothstep(0.20, 0.44, ndl) + 0.22 * smoothstep(0.50, 0.74, ndl);
	float lvl = mix(r3, smoothstep(-0.25, 0.75, ndl), w3_night);
	return alb * w3_lit_tint * light_col / W3_PI * lvl * att;
}
