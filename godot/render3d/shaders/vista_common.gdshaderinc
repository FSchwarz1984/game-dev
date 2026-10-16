// vista_common.gdshaderinc — shared by the shaders of the view from the lookout (W3Vista,
// godot/world3d/vista3d.gd): a perspective camera in its own world, drawn at native resolution in
// the same pixel-art language as the top-down world. Height maps, aerial perspective (haze toward
// the horizon colour, continuous), the sea of clouds over the lowland (where its banks may lie, how
// they creep, the shade they cast on the plain), and the 遠化 round the town in the middle of the
// plain (round 5, G5R3-22: v_ghost_k, below).
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
uniform float haze_dist = 2200.0;                              // metres for 63 % haze
uniform float mist_max = 1.0;               // the 遠化's strength (1: as drawn)
uniform sampler2D plain_tex : filter_linear, repeat_disable;   // R river m, G road m*2, B village, A rail m*2
uniform vec4 plain_frame = vec4(-6000.0, 400.0, 8.0, 1501.0);  // x0, z0, cell, n
uniform float cloud_time = 0.0;             // seconds (the clouds drift)
uniform float city_lights = 0.0;            // the plain's lamplight: 0 by day .. 1 at night (on with the dusk)
uniform float sea_base = -255.0;            // the sea of clouds' flat underside (m)
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

// (the 遠化's heart and rings: see the 遠化 below)
// The town and the rings (vista3d.gd sets them from vista.json; the prologue's 2D view keeps the same
// numbers: coord/to_vista2d): full within r0, 0.6 at r1, 0.3 at r2, nothing past r3 (metres), each
// ring's radius wandering a tenth either way round the town. (The plain in front of the town lies
// within two kilometres of it: wider rings drew the whole plain one pale silver, with no heart.)
uniform vec2 ghost_c = vec2(-260.0, 2160.0);
uniform vec4 ghost_r = vec4(350.0, 900.0, 2000.0, 4200.0);
const vec3 V_GHOST_TINT = vec3(0.88, 0.93, 1.05);   // display: a cool silver
// the night look's light (linear): 0.89 lands its lightness on the prologue's silver-grey as the
// screen shows it (the town there sRGB about (118, 126, 145), luma 126; through this view's night grade
// the same numbers came out at luma 133, a little bluer: vista_display's gain and lift)
uniform float ghost_night_gain = 0.89;
// the day's 遠化 (see v_ghost): where it is, by k, coming in early and quickly (its edge where the
// night's is); its key, contrast and shoulder in display terms, before the view's grade
uniform float ghost_day_w0 = 0.035;
uniform float ghost_day_w1 = 0.045;
uniform float ghost_day_key = 0.77;
uniform float ghost_day_key_town = 1.14;
uniform float ghost_day_contrast = 2.8;
uniform float ghost_day_mid = 0.5;
// (a soft shoulder from the knee up to the ceiling: through the view's grade the ceiling lands near
// L* 94, so nothing is blown white; the light and shade stay below it, darker strokes on a bright
// ground, as cut)
uniform float ghost_day_knee = 0.72;
uniform float ghost_day_ceiling = 0.815;
uniform float ghost_day_lref = 1.19;          // the white surface's light at noon (the key is set for it)
const vec3 V_GHOST_TINT_DAY = vec3(0.955, 0.975, 1.02);
float v_ghost_day_w(float k) {
	return smoothstep(ghost_day_w0, ghost_day_w1, k);
}

// how far gone a point is: 1 at the heart .. 0 (as it is)
float v_ghost_k(vec2 xz) {
	vec2 d = xz - ghost_c;
	float a = atan(d.x, -d.y);
	float w = 0.9 + 0.2 * (w3_vnoise(vec2(a * 2.6 + 4.0, 1.7)) * 0.7 + w3_vnoise(vec2(a * 7.3 + 1.0, 5.1)) * 0.3);
	float r = length(d) / w;
	float k;
	if (r < ghost_r.x) k = 1.0;
	else if (r < ghost_r.y) k = mix(1.0, 0.6, smoothstep(ghost_r.x, ghost_r.y, r));
	else if (r < ghost_r.z) k = mix(0.6, 0.3, smoothstep(ghost_r.y, ghost_r.z, r));
	else k = mix(0.3, 0.0, smoothstep(ghost_r.z, ghost_r.w, r));
	// (the region's ring round home stays as it is)
	return k * smoothstep(1.15, 1.8, v_mist_e(xz));
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
	// where that point of the sky lay at the start (the banks creep with the wind; over the 遠化 the
	// shade keeps its place, as the banks there do)
	vec2 p0 = p - cloud_wind * (v_ghost_k(wp.xz) > 0.5 ? 0.0 : cloud_time);
	p0.x = cloud_box.x + mod(p0.x - cloud_box.x, cloud_box.z);
	vec2 uv = (p0 - cloud_box.xy) / cloud_box.zw;
	if (uv.y < 0.0 || uv.y > 1.0) return 0.0;
	return textureLod(cloud_tex, uv, 0.0).r * v_cloud_room(p);
}

// ------------------------------------------------------------------------------------------------
// The 遠化 (round 5, the user G5R3-22; the 褪版 tried before it, a print losing its colour blocks out
// at the far ranges, was turned down: the place was wrong, and it read "dirty, like a grey model").
// The prologue's tree-top view bursts the 遠化 from the town in the middle of the plain like a ground
// zero, ring after ring out to the foot of the mountains; the view from the lookout shows what it left:
// heaviest round the town, thinner outward, the farther from the town the more colour stays, the
// region's ring round home untouched, the far ranges as they are. Things gone "far" are still there:
// fields, roads and roofs keep their own lightness and their shapes, but the colour is drawn out of
// them, lifted toward a silver white, a little blue, as if lit by a light from nowhere (round 2's look,
// src/vista/tod.js ghost()). The colour is turned in vista_post (v_ghost, on the frame's own colour, so
// every surface goes the same way); water there is the light of a sky that is not there; no lamp
// burns; nothing moves (the smoke stands, a bank of cloud over it and its shade keep their place:
// vista_puff, vista_cloud, v_cloud_shade); the air over it trembles a little (vista_post, by whole
// pixels, slowly) and small silver lights rise from it (vista3d.gd _motes). It is lit by a light of its
// own more than by the hour's (v_ghost_light): at night a bright silver one or two steps above the
// dark land, by day level with the land round it or a touch above.
// the light a level white surface has at this hour (the sky above, the sun at round 3's middle level):
// the 遠化's lightness is taken against it (how light a thing is, whatever the hour)
float v_light_ref() {
	return w3_luma(vec3(w3_luma(w3_sky)) * w3_shade_tint + w3_sun * w3_lit_tint * (0.78 / W3_PI));
}
// a colour as the 遠化 shows it (k: v_ghost_k). WHERE the 遠化 is does not change with the hour: it
// is a fact of the world (the rings); by day, at dusk and at night the same land is seen to be gone
// far, only how the ghost looks changes (G5R3-29: the user saw the day's 遠化 cover the town alone and
// the night's the whole plain). The night's extent is the measure (the prologue's); the day matches
// it. The same numbers as the prologue's 2D view at night (tools/vista/bake/plain.js GHOST_LOOKS).
// - at night the silver-grey (round 2's ghost() lifted a third wider): ld -> 0.2 + 0.74 ld^0.85, the
//   silver (0.86, 0.92, 1.07) mixed a tenth with its own colour; a light of its own, not the hour's
//   (the user, G5R3-26: the silver-white was too bright at night; the silver-grey of the prologue
//   "在夜間的表現還是不錯的"); it takes the land by k, as the prologue's night does.
// - by day (the user: "还要额外考虑对比度、明度和饱和度"; the lead's measures, G5R3-29): the land
//   there has no air (v_haze_k), so its own light and shade are back; on them it is turned high key
//   and kept sharp: its lightness (display, against the hour's light) spread about the middle by
//   ghost_day_contrast and set on a key a step above the land round it (the town a step more, steep,
//   by k^ghost_day_gamma), under a soft shoulder (never blown white); the colour drawn out to a faint
//   cool silver (chroma near none), a little of its own. All of it comes in by v_ghost_day_w(k): early
//   and quickly at low k, so the day's edge is the night's, and a clear step of lightness there.
// - at dusk and dawn the one turns into the other with the night (w3_night).
const vec3 V_GHOST_TINT_NIGHT = vec3(0.86, 0.92, 1.07);
uniform float ghost_day_gamma = 4.0;
vec3 v_ghost_at(vec3 col, float k, float dist) {
	if (k <= 0.0) return col;
	float lref = max(v_light_ref(), 1e-4);
	float l = w3_luma(col) / lref;
	float ld = pow(clamp(l, 0.0, 1.6), 1.0 / 2.2);
	// by day
	float key = mix(ghost_day_key, ghost_day_key_town, pow(k, ghost_day_gamma));
	// (far off, past ~2.5 km, the spread halves by ~5 km and the middle it turns on comes down to the
	// far land's own: once its air is gone the far land is darker than the near, and turned on the
	// near's middle it fell to the lightness of the hazy land round it, so that the 遠化's far edge
	// did not read)
	float far = smoothstep(2500.0, 5000.0, dist);
	// (and with the sun low the shadows of the far slopes are long and deep: spread as at noon they went
	// black and the 遠化 read dirty; the spread eases to 0.55 as the sun goes down to the hills)
	float sun_hi = smoothstep(0.08, 0.35, normalize(w3_sun_dir).y);
	float con = ghost_day_contrast * mix(1.0, 0.5, far) * mix(0.55, 1.0, sun_hi);
	float lo = key + con * (ld - mix(ghost_day_mid, 0.455, far));
	float kn = ghost_day_knee, room = ghost_day_ceiling - ghost_day_knee;
	lo = lo < kn ? max(lo, 0.0) : kn + room * (1.0 - exp(-(lo - kn) / room));
	vec3 gd = w3_srgb_to_linear(clamp(lo * V_GHOST_TINT_DAY, vec3(0.0), vec3(1.0))) * clamp(lref / ghost_day_lref, 0.5, 1.0);
	gd = mix(gd, col * (w3_luma(gd) / max(w3_luma(col), 1e-5)), 0.03);
	vec3 day = mix(col, gd, v_ghost_day_w(k));
	// at night
	float ln = clamp(0.2 + 0.74 * pow(min(ld, 1.0), 0.85), 0.0, 1.0);
	vec3 own = pow(clamp(col / lref, vec3(0.0), vec3(1.0)), vec3(1.0 / 2.2));
	vec3 gn = w3_srgb_to_linear(clamp(0.9 * ln * V_GHOST_TINT_NIGHT + 0.1 * own, vec3(0.0), vec3(1.0))) * ghost_night_gain;
	return mix(day, mix(col, gn, k), w3_night);
}
vec3 v_ghost(vec3 col, float k) {
	return v_ghost_at(col, k, 0.0);
}
// lamps go out in the 遠化 (and smoke and cloud stand still there: vista_puff, vista_cloud)
float v_drain(vec2 xz, float y) {
	return smoothstep(0.2, 0.35, v_ghost_k(xz));
}

// the air: haze with distance (continuous since round 4: the HDR view and the display's blue-noise
// dither keep a slow gradient from banding)
float v_haze_k(vec3 wp, vec3 cam) {
	float d = length(wp - cam);
	// the air thins with height: far peaks stay legible above the lowland's haze
	float thin = mix(1.0, 0.35, smoothstep(-100.0, 700.0, wp.y));
	float h = 1.0 - exp(-d / haze_dist * thin);
	// (the 遠化 is no air. At night over it half the haze, so its fields and roads keep their shapes;
	// by day none: what has gone far is seen clearer than the land round it, not hazier (the lead,
	// G5R3-29), coming in with the day's weight, so its edge is where the 遠化's is)
	float gk = v_ghost_k(wp.xz);
	return clamp(h, 0.0, 1.0) * mist_max * (1.0 - mix(v_ghost_day_w(gk), 0.5 * gk, w3_night));
}
vec3 v_air(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	return mix(col, haze_col, v_haze_k(wp, cam));
}
// the clouds and the sky: the same air
vec3 v_air_only(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	return mix(col, haze_col, v_haze_k(wp, cam));
}
// what is left of a light added later (in light()) after the same air
float v_air_keep(vec3 wp, vec3 cam, vec2 frag) {
	return 1.0 - v_haze_k(wp, cam);
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
