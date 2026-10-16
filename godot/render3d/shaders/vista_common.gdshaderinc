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
// the 遠化: beyond the region's ring the land pales more and more with distance (it loses its
// nearness, it does not hide in a fog); past the front it lies flat and white. The front wanders
// round the region (its radius per direction). High ground keeps more of itself.

float v_front_r(vec2 xz) {
	vec2 d = xz - front_c.xy;
	float a = atan(d.x, -d.y);
	float w = w3_vnoise(vec2(a * 2.2 + 11.0, 3.0)) * 0.65 + w3_vnoise(vec2(a * 6.1 + 2.0, 7.0)) * 0.35;
	return front_c.z * (0.62 + 0.8 * w);
}

// 0 inside the ring; up to about 0.3 before the front; 1 past it
// (round 5, G5R3-1: round 3's 遠化 again, the lead: "远处那条米色的宽带是第三轮的，按第三轮恢复（它读起来像
// 浮世绘、大和绘里的すやり霞）"; round 4's "far land in the air" was rolled back with the colours)
float v_drain(vec2 xz, float y) {
	float e = v_mist_e(xz);
	if (e < 1.0) return 0.0;
	float r = length(xz - front_c.xy);
	float rf = v_front_r(xz);
	// (the high ground keeps more of itself: far mountains stand out of the white)
	float hk = 1.0 - 0.85 * smoothstep(-300.0, -60.0, y);
	if (r > rf) {
		// past the front the white takes the land up to a height that wanders from place to place:
		// up one slope, short of the next, so its far side is no level line (a white that stopped
		// at one height read as a lake filling the plain)
		float top = -250.0 + 600.0 * w3_vnoise(xz / 2500.0 + 5.0);
		return y < top ? 1.0 : min(hk, 0.55);
	}
	float f = r / rf;
	return (0.03 + 0.3 * f * f) * hk;
}

// haze (air) and drain (遠化) amounts at a point (continuous since round 4: the HDR view and the
// display's blue-noise dither keep a slow gradient from banding)
vec2 v_air_k(vec3 wp, vec3 cam, vec2 frag) {
	float d = length(wp - cam);
	// the air thins with height: far peaks stay legible above the lowland's haze
	float thin = mix(1.0, 0.35, smoothstep(-100.0, 700.0, wp.y));
	float h = 1.0 - exp(-d / haze_dist * thin);
	float m = v_drain(wp.xz, wp.y) * mist_max;
	return vec2(clamp(h, 0.0, 1.0), m > 0.99 ? 1.0 : clamp(m, 0.0, 1.0));
}
// the 遠化's white with the land's drawing in it: ink 0 the paper, 1 the darkest line
vec3 v_paper(float ink) {
	return far_white * (1.0 - 0.17 * ink);
}
// haze and the 遠化 over a colour: paler and greyer toward the front, past it the flat white
vec3 v_air(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	vec2 k = v_air_k(wp, cam, frag);
	float l0 = dot(col, vec3(0.299, 0.587, 0.114));
	if (k.y >= 1.0) {
		// past the front: paper white with the land's drawing left in it, like a print faded in the
		// sun: what was dark (woods, the groves round the villages, roofs, the river's banks, the
		// viaduct) a faint warm grey, everything light the paper itself. Dark marks on white, never
		// light flecks on a darker ground (those read as the glitter of water).
		// (col is the land's ambient light here: the sun is added later, and not past the front; so
		// divided by the ambient it is about the land's own lightness, at every hour)
		float la = max(dot(w3_sky + w3_ground, vec3(0.299, 0.587, 0.114)), 0.01);
		return v_paper(1.0 - smoothstep(0.02, 0.08, l0 / la));
	}
	col = mix(col, haze_col, k.x);
	float l = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 pale = mix(vec3(l), col, 0.45) * 0.55 + mist_col * 0.5;
	return mix(col, pale, clamp(k.y * 1.3, 0.0, 1.0));
}
// the clouds and the sky: haze only (weather is not drained)
vec3 v_air_only(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	return mix(col, haze_col, v_air_k(wp, cam, frag).x);
}
// what is left of a light added later (in light()) after the same air
float v_air_keep(vec3 wp, vec3 cam, vec2 frag) {
	vec2 k = v_air_k(wp, cam, frag);
	return k.y >= 1.0 ? 0.0 : (1.0 - k.x) * (1.0 - clamp(k.y * 1.4, 0.0, 0.85));
}
// past the 遠化 front (the flat white): the things drawn on it give their own ink
bool v_past(vec3 wp, vec3 cam, vec2 frag) {
	return v_air_k(wp, cam, frag).y >= 1.0;
}

// the toon sun of the vista: three bands, the painted shade of pixel_toon (w3_ambient); the band
// seams scattered on cells fixed to the world (about a pixel there)
// (the name is old: since round 4 the sun on the vista's land is continuous, a wrapped Lambert, and
// its shadows soft-edged, like the top-down world's)
vec3 v_sun_bands(vec3 alb, vec3 n, vec3 l, vec3 light_col, float att, vec3 wp, vec3 cam) {
	// (about the old bands' levels on average: 0.6 at a third lit, 0.9 at two thirds, 1 facing it)
	float lvl = smoothstep(-0.25, 0.75, dot(n, l));
	return alb * w3_lit_tint * light_col / W3_PI * lvl * att;
}
