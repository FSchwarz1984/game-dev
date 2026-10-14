// Foliage layers (tree crowns, shrub and herb bodies) and big trunks. Own work, CC0.
//
// Wind, pixel-stable: every sway group (one foliage mass, a grass tuft, a bamboo spray; baked in
// sway_data.r, ranked by depth) moves rigidly by whole texels: 0, +-1 (+-2 when max_offset = 2).
// Nothing is resampled between texels, so nothing shimmers. A texel finds what lands on it by
// testing the few source texels that could have moved there (inverse mapping); the nearest group
// wins; if nothing lands, the crown's dark inside shows (sway_data.b bit 7), as when leaves part.
// Flexibility per group is sway_data.g (0 = still: wood, the crown's inside).
//
// X-ray: when the player stands behind this layer (her feet north of the layer's sort point, the
// node origin) and the layer really covers her (sway_data.b bit 6, sampled at her chest, waist and
// head), a hole opens around her chest in stepped alpha. Works per texel, so the edge is pixel art.
//
// Globals (project settings > shader globals): player_pos (vec2, world px of her feet),
// wind_strength (float, 0 calm, 1 normal, 2 gale).
shader_type canvas_item;

uniform sampler2D sway_data : filter_nearest, repeat_disable;
uniform vec3 core_color : source_color = vec3(0.09, 0.17, 0.12);
uniform float sway_amp = 1.0;
uniform int max_offset : hint_range(0, 2) = 1;
uniform float sway_speed = 1.0;
uniform bool occluder = true;
uniform vec2 hole_half = vec2(13.0, 19.0);
uniform float hole_alpha : hint_range(0.0, 1.0) = 0.25;
uniform float hole_lift = 17.0;

global uniform vec2 player_pos;
global uniform float wind_strength;

varying vec4 v_mod;
varying flat vec2 v_origin;
varying flat vec2 v_player_uv;

void vertex() {
	v_mod = COLOR;
	v_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xy;
	vec2 local_player = (inverse(MODEL_MATRIX) * vec4(player_pos, 0.0, 1.0)).xy;
	vec2 rect_origin = VERTEX - UV / TEXTURE_PIXEL_SIZE;
	v_player_uv = (local_player - rect_origin) * TEXTURE_PIXEL_SIZE;
}

float hash1(float n) {
	return fract(sin(n * 12.9898 + 4.1414) * 43758.5453);
}

// whole-texel offset of one sway group at time t
int group_offset(float gid, float flex, float t, float tree_ph) {
	if (gid < 0.5 || flex <= 0.0) {
		return 0;
	}
	float ph = hash1(gid * 1.618 + tree_ph) * 6.2831853;
	float slow = sin(t * 0.93 + ph) * 0.6 + sin(t * 0.37 + ph * 2.3) * 0.4;
	float gust = smoothstep(0.62, 1.0, sin(t * 0.19 + tree_ph * 6.2831853) * 0.5 + 0.5);
	float o = flex * sway_amp * wind_strength * (slow * 0.75 + gust * 0.85);
	float m = float(max_offset);
	return int(clamp(round(o), -m, m));
}

bool bit_set(float channel, float bit_value) {
	float v = floor(channel * 255.0 + 0.5);
	return mod(floor(v / bit_value), 2.0) > 0.5;
}

void fragment() {
	vec2 tps = TEXTURE_PIXEL_SIZE;
	float t = TIME * sway_speed;
	float tree_ph = hash1(v_origin.x * 0.0131 + v_origin.y * 0.0079);
	vec4 col = vec4(0.0);
	vec3 nrm = vec3(0.5, 0.5, 1.0);
	float best = -1.0;
	for (int o = -2; o <= 2; o++) {
		if (abs(o) > max_offset) {
			continue;
		}
		vec2 suv = UV - vec2(float(o), 0.0) * tps;
		if (suv.x < 0.0 || suv.x > 1.0) {
			continue;
		}
		vec4 c = texture(TEXTURE, suv);
		if (c.a < 0.5) {
			continue;
		}
		vec4 d = texture(sway_data, suv);
		float gid = floor(d.r * 255.0 + 0.5);
		if (group_offset(gid, d.g, t, tree_ph) != o) {
			continue;
		}
		if (gid > best) {
			best = gid;
			col = c;
			nrm = texture(NORMAL_TEXTURE, suv).rgb;
		}
	}
	if (best < 0.0) {
		vec4 d0 = texture(sway_data, UV);
		if (d0.a > 0.5 && bit_set(d0.b, 128.0)) {
			col = vec4(core_color, 1.0);
			nrm = vec3(0.5, 0.33, 0.94);
		} else {
			discard;
		}
	}
	COLOR = col * v_mod;
	NORMAL_MAP = nrm;
	if (occluder && player_pos.y < v_origin.y) {
		float cover = 0.0;
		for (int i = 0; i < 3; i++) {
			vec2 q = v_player_uv + vec2(0.0, -6.0 - float(i) * 10.0) * tps;
			if (q.x > 0.0 && q.y > 0.0 && q.x < 1.0 && q.y < 1.0) {
				vec4 dq = texture(sway_data, q);
				if (dq.a > 0.5 && bit_set(dq.b, 64.0)) {
					cover = 1.0;
				}
			}
		}
		if (cover > 0.5) {
			vec2 texel = floor(UV / tps) + 0.5;
			vec2 centre = v_player_uv / tps + vec2(0.0, -hole_lift);
			float r = length((texel - centre) / hole_half);
			float a = clamp((r - 0.72) / 0.28, 0.0, 1.0);
			a = floor(a * 3.0 + 0.5) / 3.0;
			COLOR.a *= mix(hole_alpha, 1.0, a);
		}
	}
}
