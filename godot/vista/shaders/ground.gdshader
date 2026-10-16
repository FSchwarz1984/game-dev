// The ground of the treetop vista (painted by the bake: since round 5 the 3D lookout's plain) with the
// wave of distance (src/vista/wave.js): every pixel knows when the ring reaches it (B channel, bucket of
// w * 250). On the front (two buckets) the land flashes white, the event itself (lut_far row 0). Behind
// it the land has gone far (遠化, G5R3-18): a print losing its colour blocks, one by one, patch by
// patch, down to the stage that place ends at (lut_far rows 1..4: no bokashi, no greens, no water
// blue, no earth colours), with the key block's ink lines over it; at night the paper is dark and the
// lines only just show. `settled`: the far has been and gone, every place at its final stage.
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;     // R, G id; B arrival (255 never); A mask
uniform sampler2D lut : filter_nearest, repeat_disable;     // per time of day
uniform sampler2D lut_far : filter_nearest, repeat_disable; // row 0 the front, rows 1..4 the stages
uniform sampler2D fade_map : filter_nearest, repeat_disable; // R ink, G final stage x 50, B patch delay
uniform float tod_row;
uniform float wave = -1.0;
uniform float settled = 0.0;

const float PEEL = 5.0;      // buckets of the wave between one block and the next coming off
const float DELAY = 8.0;     // buckets: the longest a patch waits before its first block goes
const float INK = 0.7;       // how dark the key block's lines are on the paper

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	vec4 t = texelFetch(ids, p, 0);
	if (t.a < 0.5) discard;
	int id = int(t.r * 255.0 + 0.5) + int(t.g * 255.0 + 0.5) * 256;
	vec3 c = lut_rgb(lut, id, tod_row);
	if (wave >= 0.0 || settled > 0.5) {
		vec4 fm = texelFetch(fade_map, p, 0);
		float fin = clamp(floor(fm.g * 255.0 / 50.0 + 0.001), 1.0, 4.0);
		float st = -1.0;
		if (settled > 0.5) {
			st = fin;
		} else {
			float b = clamp(floor(wave * 250.0), -1.0, 254.0);
			float arr = floor(t.b * 255.0 + 0.5);
			if (arr <= b - 2.0) {
				float since = b - 2.0 - arr - floor(fm.b * DELAY + 0.5);
				st = clamp(1.0 + floor(max(since, 0.0) / PEEL), 1.0, fin);
			} else if (arr <= b) {
				c = texelFetch(lut_far, ivec2(id, 0), 0).rgb * 255.0;
			}
		}
		if (st >= 1.0) {
			c = texelFetch(lut_far, ivec2(id, int(st)), 0).rgb * 255.0;
			float vis = st < 1.5 ? 0.5 : st < 2.5 ? 0.7 : st < 3.5 ? 0.85 : 1.0;
			c *= 1.0 - INK * vis * fm.r;
		}
	}
	COLOR = vec4(lin255(c), 1.0);
}
