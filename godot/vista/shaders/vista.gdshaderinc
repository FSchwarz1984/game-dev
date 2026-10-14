// Shared helpers of the vista shaders, exact ports of src/vista/util.js where they matter:
//   smoothj       JS smooth(a, b, x): smoothstep that also accepts a > b (GLSL's is undefined there)
//   roundj        JS Math.round (halves up)
//   hash2, vnoise the integer hash and value noise of util.js (uint arithmetic wraps like Math.imul)
//   glow_w        the stepped glow of util.js glowSprite / lights.js AddBuffer: (1 - d)^1.7 in sixths
//   lut_rgb       a palette row interpolated between two times of day (sRGB 0..255)
// Colours are worked out in sRGB like the JS canvas did, then converted for the HDR (linear) viewport.
// Locals carry a prefix: Godot rejects a local that shares a uniform's name (e.g. `t`), and the
// helpers are included next to such uniforms.

float smoothj(float sj_a, float sj_b, float sj_x) {
	float sj_t = clamp((sj_x - sj_a) / (sj_b - sj_a), 0.0, 1.0);
	return sj_t * sj_t * (3.0 - 2.0 * sj_t);
}

float roundj(float rj_x) {
	return floor(rj_x + 0.5);
}

vec3 srgb_to_linear(vec3 sl_c) {
	sl_c = max(sl_c, vec3(0.0));
	return mix(pow((sl_c + vec3(0.055)) * (1.0 / 1.055), vec3(2.4)), sl_c * (1.0 / 12.92), lessThan(sl_c, vec3(0.04045)));
}

// a 0..255 sRGB colour as linear light
vec3 lin255(vec3 l2_c) {
	return srgb_to_linear(l2_c / 255.0);
}

float hash2(int h2_x, int h2_y, int h2_s) {
	uint h2_h = uint(h2_x) * 374761393u + uint(h2_y) * 668265263u + uint(h2_s) * 1442695041u;
	h2_h = (h2_h ^ (h2_h >> 13u)) * 1274126177u;
	h2_h ^= h2_h >> 16u;
	return float(h2_h >> 8u) / 16777216.0;
}

float vnoise(float vn_x, float vn_y, int vn_s) {
	float vn_xi = floor(vn_x), vn_yi = floor(vn_y);
	float vn_xf = vn_x - vn_xi, vn_yf = vn_y - vn_yi;
	float vn_u = vn_xf * vn_xf * (3.0 - 2.0 * vn_xf), vn_v = vn_yf * vn_yf * (3.0 - 2.0 * vn_yf);
	int vn_ix = int(vn_xi), vn_iy = int(vn_yi);
	float vn_a = hash2(vn_ix, vn_iy, vn_s), vn_b = hash2(vn_ix + 1, vn_iy, vn_s);
	float vn_c = hash2(vn_ix, vn_iy + 1, vn_s), vn_d = hash2(vn_ix + 1, vn_iy + 1, vn_s);
	return vn_a + (vn_b - vn_a) * vn_u + (vn_c - vn_a) * vn_v + (vn_a - vn_b - vn_c + vn_d) * vn_u * vn_v;
}

float glow_w(vec2 gw_d, float gw_r) {
	float gw_q = length(gw_d) / (gw_r + 0.5);
	return floor(pow(clamp(1.0 - gw_q, 0.0, 1.0), 1.7) * 6.0 + 0.5) / 6.0;
}

// the same for a glow centred between four pixels (a 2x2 core): d from the core's top-left pixel
float glow_w2(vec2 g2_d, float g2_r) {
	float g2_q = length(g2_d - vec2(0.5)) / (g2_r + 1.0);
	return floor(pow(clamp(1.0 - g2_q, 0.0, 1.0), 1.7) * 6.0 + 0.5) / 6.0;
}

int id_at(sampler2D ia_ids, ivec2 ia_p) {
	vec4 ia_v = texelFetch(ia_ids, ia_p, 0);
	return int(ia_v.r * 255.0 + 0.5) + int(ia_v.g * 255.0 + 0.5) * 256;
}

vec3 lut_rgb(sampler2D lr_lut, int lr_id, float lr_row) {
	int lr_rows = textureSize(lr_lut, 0).y;
	float lr_rr = clamp(lr_row, 0.0, float(lr_rows - 1));
	int lr_r0 = int(floor(lr_rr));
	int lr_r1 = min(lr_r0 + 1, lr_rows - 1);
	vec3 lr_a = texelFetch(lr_lut, ivec2(lr_id, lr_r0), 0).rgb;
	vec3 lr_b = texelFetch(lr_lut, ivec2(lr_id, lr_r1), 0).rgb;
	return mix(lr_a, lr_b, lr_rr - float(lr_r0)) * 255.0;
}
