// Shared helpers of the vista shaders, exact ports of src/vista/util.js where they matter:
//   smoothj       JS smooth(a, b, x): smoothstep that also accepts a > b (GLSL's is undefined there)
//   roundj        JS Math.round (halves up)
//   hash2, vnoise the integer hash and value noise of util.js (uint arithmetic wraps like Math.imul)
//   glow_w        the stepped glow of util.js glowSprite / lights.js AddBuffer: (1 - d)^1.7 in sixths
//   lut_rgb       a palette row interpolated between two times of day (sRGB 0..255)
// Colours are worked out in sRGB like the JS canvas did, then converted for the HDR (linear) viewport.

float smoothj(float a, float b, float x) {
	float t = clamp((x - a) / (b - a), 0.0, 1.0);
	return t * t * (3.0 - 2.0 * t);
}

float roundj(float x) {
	return floor(x + 0.5);
}

vec3 srgb_to_linear(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(pow((c + vec3(0.055)) * (1.0 / 1.055), vec3(2.4)), c * (1.0 / 12.92), lessThan(c, vec3(0.04045)));
}

// a 0..255 sRGB colour as linear light
vec3 lin255(vec3 c) {
	return srgb_to_linear(c / 255.0);
}

float hash2(int x, int y, int s) {
	uint h = uint(x) * 374761393u + uint(y) * 668265263u + uint(s) * 1442695041u;
	h = (h ^ (h >> 13u)) * 1274126177u;
	h ^= h >> 16u;
	return float(h >> 8u) / 16777216.0;
}

float vnoise(float x, float y, int s) {
	float xi = floor(x), yi = floor(y);
	float xf = x - xi, yf = y - yi;
	float u = xf * xf * (3.0 - 2.0 * xf), v = yf * yf * (3.0 - 2.0 * yf);
	int ix = int(xi), iy = int(yi);
	float a = hash2(ix, iy, s), b = hash2(ix + 1, iy, s), c = hash2(ix, iy + 1, s), d = hash2(ix + 1, iy + 1, s);
	return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

float glow_w(vec2 d, float r) {
	float q = length(d) / (r + 0.5);
	float a = pow(clamp(1.0 - q, 0.0, 1.0), 1.7);
	return floor(a * 6.0 + 0.5) / 6.0;
}

// the same for a glow centred between four pixels (a 2x2 core): d from the core's top-left pixel
float glow_w2(vec2 d, float r) {
	float q = length(d - vec2(0.5)) / (r + 1.0);
	return floor(pow(clamp(1.0 - q, 0.0, 1.0), 1.7) * 6.0 + 0.5) / 6.0;
}

int id_at(sampler2D ids, ivec2 p) {
	vec4 v = texelFetch(ids, p, 0);
	return int(v.r * 255.0 + 0.5) + int(v.g * 255.0 + 0.5) * 256;
}

vec3 lut_rgb(sampler2D lut, int id, float row) {
	int rows = textureSize(lut, 0).y;
	float rr = clamp(row, 0.0, float(rows - 1));
	int r0 = int(floor(rr));
	int r1 = min(r0 + 1, rows - 1);
	vec3 a = texelFetch(lut, ivec2(id, r0), 0).rgb;
	vec3 b = texelFetch(lut, ivec2(id, r1), 0).rgb;
	return mix(a, b, rr - float(r0)) * 255.0;
}
