// The ground of the treetop vista (painted by the bake: since round 5 the 3D lookout's plain) with the
// wave of distance (src/vista/wave.js): every pixel knows when the ring reaches it (B channel, bucket of
// w * 250). On the front (two buckets) the land flashes white, the event itself (lut_far row 0). Behind
// it the land has gone far (遠化, G5R3-22): its own silver-white ghost (lut_far row 1: v0.2's ghost,
// everything in its place and shape, its lightness kept, drained of colour, lifted), mixed with the
// night in linear light by how much a ghost the place is (ghost_map R: plain.js ghostK, the 3D
// lookout's ghost_k: 1 round the town, ground zero, 0.75 at 1.1 km, 0.4 at 2.6 km, nothing past
// 5.5 km, nothing in the region's ring round home); and over it the air trembles a little, as over
// heat: the picture there is taken from a whole pixel above or below in slow bands that drift upward,
// the more the more a ghost (ghost_map G = k^1.5; the lookout's vista_post, its numbers scaled from
// its 640x360 to our 480x270), only from the 遠化's own land. `settled`: the far has been and gone
// over all the land in sight (the hold).
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;     // R, G id; B arrival (255 never); A mask
uniform sampler2D lut : filter_nearest, repeat_disable;     // per time of day
uniform sampler2D lut_far : filter_nearest, repeat_disable; // row 0 the front, row 1 the ghost
uniform sampler2D ghost_map : filter_nearest, repeat_disable; // R how much a ghost, G the shimmer
uniform float tod_row;
uniform float wave = -1.0;
uniform float settled = 0.0;
uniform float t = 0.0;                 // the vista clock (the shimmer)
uniform float mirage_amp = 1.15;      // the lookout's: a pixel at most, where k^1.5 n > 0.43
// (Vista.bridge "drain", G5R3-61) before the far bursts, the town's colours drawn up into the gate:
// the ground the far reaches first (its arrival bucket within drain_b, a soft edge of 8 buckets)
// already its ghost. < -5: none
uniform float drain_b = -10.0;

varying vec2 px;

void vertex() {
	px = VERTEX;
}

// gone far: the tide has passed (two buckets behind the front), or all of it has
bool gone(vec4 tex, float b) {
	return settled > 0.5 || floor(tex.b * 255.0 + 0.5) <= b - 2.0;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	vec4 tex = texelFetch(ids, p, 0);
	if (tex.a < 0.5) discard;
	float b = wave >= 0.0 ? clamp(floor(wave * 250.0), -1.0, 254.0) : -10.0;
	bool far_on = wave >= 0.0 || settled > 0.5;
	if (far_on && gone(tex, b)) {
		// the trembling air (the lookout's bands, in its pixels: ours are 4/3 of its)
		float m = texelFetch(ghost_map, p, 0).g;
		if (m > 0.004) {
			vec2 q3 = vec2(p) * (4.0 / 3.0);
			float n = sin(q3.x / 11.0 + t * 0.7 + sin(q3.y / 5.0 + t * 0.9) * 1.6) * 0.6 + sin(q3.x / 29.0 - q3.y / 13.0 + t * 0.45) * 0.4;
			int off = int(floor(n * mirage_amp * m + 0.5));
			if (off != 0) {
				ivec2 q = p + ivec2(0, off);
				vec4 tq = texelFetch(ids, q, 0);
				if (tq.a > 0.5 && gone(tq, b) && texelFetch(ghost_map, q, 0).r > 0.05) {
					p = q;
					tex = tq;
				}
			}
		}
	}
	int id = int(tex.r * 255.0 + 0.5) + int(tex.g * 255.0 + 0.5) * 256;
	vec3 c = lin255(lut_rgb(lut, id, tod_row));
	bool far_done = false;
	if (far_on) {
		if (gone(tex, b)) {
			float g = texelFetch(ghost_map, p, 0).r;
			c = mix(c, lin255(texelFetch(lut_far, ivec2(id, 1), 0).rgb * 255.0), g);
			far_done = true;
		} else if (wave >= 0.0 && floor(tex.b * 255.0 + 0.5) <= b) {
			c = lin255(texelFetch(lut_far, ivec2(id, 0), 0).rgb * 255.0);
			far_done = true;
		}
	}
	if (!far_done && drain_b > -5.0) {
		float dm = clamp((drain_b - floor(tex.b * 255.0 + 0.5)) / 8.0, 0.0, 1.0);
		if (dm > 0.0) {
			float g = texelFetch(ghost_map, p, 0).r;
			c = mix(c, lin255(texelFetch(lut_far, ivec2(id, 1), 0).rgb * 255.0), g * dm);
		}
	}
	COLOR = vec4(c, 1.0);
}
