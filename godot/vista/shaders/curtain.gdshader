// The foot of the wave's curtain (src/vista/wave.js drawFront, HEAD): along the front, the top pixel of
// every run of ground the ring is passing (its two newest buckets) sends up a short strip of pale
// light, taller where the ground is near; its height breathes along the front. Summed into the plain's
// light buffer (sRGB units) like the JS AddBuffer.strip.
shader_type canvas_item;
render_mode blend_add;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;     // B = arrival bucket
uniform sampler2D zmap : filter_nearest, repeat_disable;    // ground depth, 16-bit fixed over [0, 1024]
uniform float wave = -1.0;
uniform float t;
uniform float f = 360.0;
uniform float alpha = 1.0;

varying vec2 px;

const vec3 CURTAIN = vec3(168.0, 184.0, 222.0);

void vertex() {
	px = VERTEX;
}

bool in_band(ivec2 q, float b) {
	if (q.y < 0) return false;
	float arr = floor(texelFetch(ids, q, 0).b * 255.0 + 0.5);
	return arr <= b && arr > b - 2.0 && arr < 255.0;
}

void fragment() {
	if (wave < 0.0) discard;
	float b = clamp(floor(wave * 250.0), -1.0, 254.0);
	ivec2 p = ivec2(floor(px));
	ivec2 size = textureSize(ids, 0);
	vec3 c = vec3(0.0);
	bool above = in_band(p + ivec2(0, -1), b);
	for (int k = 0; k <= 16; k++) {
		ivec2 q = p + ivec2(0, k);
		if (q.y >= size.y) break;
		bool here = in_band(q, b);
		if (here && !above) {
			vec2 zv = texelFetch(zmap, q, 0).rg;
			float z = (floor(zv.r * 255.0 + 0.5) + floor(zv.g * 255.0 + 0.5) * 256.0) * 1024.0 / 65535.0;
			float hh = clamp(roundj(f * 0.06 / max(z, 0.01) * (0.7 + 0.6 * vnoise(float(q.x) * 0.13, t * 0.5, 31))), 2.0, 16.0);
			if (float(k) <= hh) {
				float u = 1.0 - float(k) / (hh + 1.0);
				float a = clamp(alpha * (0.16 + 0.24 * smoothj(22.0, 3.0, z)), 0.0, 1.0);
				c += CURTAIN * floor(u * u * 6.0 + 0.5) / 6.0 * a;
			}
		}
		above = here;
	}
	if (c.r <= 0.0) discard;
	COLOR = vec4(c / 255.0, 1.0);
}
