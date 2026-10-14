// vista_common.gdshaderinc — shared by the shaders of the view from the lookout (W3Vista,
// godot/world3d/vista3d.gd): a perspective camera in its own world, drawn at native resolution in
// the same pixel-art language as the top-down world. Height maps, aerial perspective (haze toward
// the horizon colour, in whole steps with an ordered dither on the screen pixels; the camera only
// rotates in place, so the dither does not crawl over the land), and the 遠化 mist that rings the
// region (luminous, pale: the land beyond it is seen, but faint and flat).
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D mid_tex : filter_nearest, repeat_disable;   // RG u16 height, B forest, A water
uniform sampler2D mat_tex : filter_nearest, repeat_disable;   // R cultivated, G road, B rock, A mist
uniform sampler2D far_tex : filter_nearest, repeat_disable;   // RG u16 height, B forest, A water
uniform vec4 mid_frame = vec4(-640.0, -560.0, 1.0, 1281.0);   // x0, z0, cell, n
uniform vec2 mid_h = vec2(-480.0, 960.0);                     // min, range
uniform vec4 far_frame = vec4(-16000.0, -16000.0, 32.0, 1001.0);
uniform vec2 far_h = vec2(-480.0, 2400.0);
uniform vec4 mist_ellipse = vec4(-50.0, 100.0, 430.0, 370.0);  // centre x, z, radii x, z
uniform vec3 haze_col : source_color = vec3(0.7, 0.75, 0.8);   // linear; the horizon of the sky
uniform vec3 mist_col : source_color = vec3(0.8, 0.8, 0.84);   // linear; the 遠化 mist (lighter)
uniform float haze_dist = 2200.0;                              // metres for 63 % haze
uniform float mist_max = 0.62;              // the curtain (vista_mist) carries the rest
const float V_SEA_Y = -150.0;               // the sea of mist (vista3d.gd SEA_Y)

float v_bayer8(vec2 p) {
	ivec2 q = ivec2(mod(p, 8.0));
	const int M[64] = int[64](0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38,
		60, 28, 52, 20, 62, 30, 54, 22, 3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47, 7, 39, 13, 45, 5, 37,
		63, 31, 55, 23, 61, 29, 53, 21);
	return (float(M[q.y * 8 + q.x]) + 0.5) / 64.0;
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
vec4 v_far_data(vec2 xz) {
	vec2 g = (xz - far_frame.xy) / far_frame.z;
	return texelFetch(far_tex, ivec2(clamp(floor(g + 0.5), vec2(0.0), vec2(far_frame.w - 1.0))), 0);
}

// elliptic distance from the region's middle: 1 on the mist's inner edge
float v_mist_e(vec2 xz) {
	return length((xz - mist_ellipse.xy) / mist_ellipse.zw);
}

// haze and mist amounts at a point, quantised to whole steps with an ordered dither on screen pixels
vec2 v_air_k(vec3 wp, vec3 cam, vec2 frag) {
	float d = length(wp - cam);
	// the air thins with height: far peaks stay legible above the lowland's haze and its mist
	float thin = mix(1.0, 0.35, smoothstep(-100.0, 700.0, wp.y));
	float h = 1.0 - exp(-d / haze_dist * thin);
	float m = smoothstep(0.96, 1.32, v_mist_e(wp.xz)) * mist_max * (1.0 - smoothstep(-60.0, 260.0, wp.y));
	// the plain under the sea of mist is seen through its holes: the sea is the mist there, so the
	// veil over the land below it is thin (the fields and the river read, faint and far)
	float under = 1.0 - smoothstep(V_SEA_Y - 40.0, V_SEA_Y - 5.0, wp.y);
	m *= 1.0 - 0.75 * under;
	h *= 1.0 - 0.3 * under;
	float dz = v_bayer8(frag) - 0.5;
	return vec2(clamp(floor(h * 10.0 + 0.5 + dz * 0.9) / 10.0, 0.0, 1.0),
		clamp(floor(m * 8.0 + 0.5 + dz * 0.9) / 8.0, 0.0, 1.0));
}
// haze and mist over a colour
vec3 v_air(vec3 col, vec3 wp, vec3 cam, vec2 frag) {
	vec2 k = v_air_k(wp, cam, frag);
	return mix(mix(col, haze_col, k.x), mist_col, k.y);
}
// what is left of a light added later (in light()) after the same air
float v_air_keep(vec3 wp, vec3 cam, vec2 frag) {
	vec2 k = v_air_k(wp, cam, frag);
	return (1.0 - k.x) * (1.0 - k.y);
}

// the toon sun of the vista: three bands, the painted shade of pixel_toon (w3_ambient)
vec3 v_sun_bands(vec3 alb, vec3 n, vec3 l, vec3 light_col, float att, vec2 frag) {
	float ndl = dot(n, l);
	float th = (v_bayer8(frag) - 0.5) * 0.05;
	float lvl = ndl > 0.62 + th ? 1.0 : (ndl > 0.3 + th ? 0.78 : (ndl > 0.04 + th ? 0.52 : 0.0));
	return alb * w3_lit_tint * light_col / W3_PI * lvl * step(0.5, att);
}
