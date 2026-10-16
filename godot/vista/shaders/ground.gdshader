// The ground of the treetop vista (painted by the bake: since round 5 the 3D lookout's plain) with the
// wave of distance (src/vista/wave.js): every pixel knows when the ring reaches it (B channel, bucket of
// w * 250). On the front (two buckets) the land flashes white, the event itself (lut_far row 0). Behind
// it the land has gone far (遠化, G5R3-18), drawn as the 3D lookout draws it (vista_common "褪版"): a
// woodblock print whose colour blocks come away one after another, the gradations first (flat
// prints), then the green, the water's blue, the earths, down to the key block's ink lines on the
// paper; how many are gone at a place is baked (fade_map G: its stage); after the tide they come off
// one by one over a moment (lut_far rows 1..4). `settled`: the far has been and gone, every place at
// its stage. At night the paper is as dark as the night and the lines only just show.
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D ids : filter_nearest, repeat_disable;     // R, G id; B arrival (255 never); A mask
uniform sampler2D lut : filter_nearest, repeat_disable;     // per time of day
uniform sampler2D lut_far : filter_nearest, repeat_disable; // row 0 the front, rows 1..4 the stages
uniform sampler2D fade_map : filter_nearest, repeat_disable; // R ink (0 | 1), G stage x 50, B emboss, A delay
uniform float tod_row;
uniform float wave = -1.0;
uniform float settled = 0.0;
uniform vec3 ink_col = vec3(15.0, 13.0, 13.0);   // the key block's ink (sRGB 0..255)

const float PEEL = 5.0;      // buckets of the wave between one block and the next coming off
const float DELAY = 4.0;     // buckets: the longest a place waits before its first block goes

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
		float fin = clamp(floor(fm.g * 255.0 / 50.0 + 0.001), 0.0, 4.0);
		float st = 0.0;
		if (settled > 0.5) {
			st = fin;
		} else {
			float b = clamp(floor(wave * 250.0), -1.0, 254.0);
			float arr = floor(t.b * 255.0 + 0.5);
			if (arr <= b - 2.0) {
				float since = b - 2.0 - arr - floor(fm.a * DELAY + 0.5);
				st = since < 0.0 ? min(fin, 1.0) : min(fin, 1.0 + floor(since / PEEL));
			} else if (arr <= b) {
				c = texelFetch(lut_far, ivec2(id, 0), 0).rgb * 255.0;
			}
		}
		if (st >= 1.0) {
			vec4 pc = texelFetch(lut_far, ivec2(id, int(st)), 0);
			c = pc.rgb * 255.0;
			// the paper (flagged by its alpha): its blind embossing, the big relief pressed in
			if (pc.a < 0.75) c *= 1.0 + (fm.b * 255.0 - 128.0) / 120.0 * 0.07;
			if (fm.r > 0.5) c = ink_col;
		}
	}
	COLOR = vec4(lin255(c), 1.0);
}
