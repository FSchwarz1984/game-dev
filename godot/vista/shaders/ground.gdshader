// The ground of the treetop vista (painted by the bake: since round 5 the 3D lookout's plain) with the
// wave of distance (src/vista/wave.js): every pixel knows when the ring reaches it (B channel, bucket of
// w * 250). On the front (two buckets) the land flashes white, the event itself (lut_far row 0). Behind
// it the land has gone far (遠化, G5R3-22): its own silver-white ghost (lut_far row 1: v0.2's ghost,
// everything in its place and shape, its lightness kept, drained of colour, lifted), mixed with the
// night by how much a ghost the place is: the nearer the town (ground zero, where the tide bursts
// from), the more (ghost_map R, in steps); and over it the air shimmers a little, as over heat: the
// land sways up and down by whole pixels, slowly, most near the town (ghost_map G). `settled`: the far
// has been and gone over all the land in sight (the art sample's last frame).
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
uniform float mirage_px = 1.6;         // the shimmer's sway at ground zero (whole pixels after rounding)

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
		// the shimmer: whole-pixel sway, a slow swell along the row with a slower beat over it
		float m = texelFetch(ghost_map, p, 0).g;
		if (m > 0.004) {
			float x = float(p.x);
			float s = sin(x * 0.19 + t * 1.25 + sin(x * 0.043 - t * 0.37) * 2.1) * 0.7 + sin(x * 0.071 - t * 0.83) * 0.3;
			int off = int(floor(mirage_px * m * s + 0.5));
			if (off != 0) {
				ivec2 q = p + ivec2(0, off);
				vec4 tq = texelFetch(ids, q, 0);
				if (tq.a > 0.5 && gone(tq, b)) {
					p = q;
					tex = tq;
				}
			}
		}
	}
	int id = int(tex.r * 255.0 + 0.5) + int(tex.g * 255.0 + 0.5) * 256;
	vec3 c = lut_rgb(lut, id, tod_row);
	if (far_on) {
		if (gone(tex, b)) {
			float g = texelFetch(ghost_map, p, 0).r;
			vec3 gc = texelFetch(lut_far, ivec2(id, 1), 0).rgb * 255.0;
			c = mix(c, gc, g);
		} else if (wave >= 0.0 && floor(tex.b * 255.0 + 0.5) <= b) {
			c = texelFetch(lut_far, ivec2(id, 0), 0).rgb * 255.0;
		}
	}
	COLOR = vec4(lin255(c), 1.0);
}
