// Ground cover: grass tufts, clover, little flowers, ferns standing on the terrain as leaned cards,
// texel for pixel (MultiMesh instances). Outline class 5 (none): plants stay calmer than the
// characters and the things she can use. Colours come from the ground's own palette row at the
// anchor (the atlas stores tone offsets), so a tuft is the same grass as the ground it grows from.
// Each tuft sways as a whole by whole pixels (top rows lean, the root stays put) and bends away
// from her feet when she walks through.
// Instance: transform origin = anchor on the ground, basis Y = ground normal (scaled 1);
// INSTANCE_CUSTOM = (atlas cell, palette row, tone bias, flex).
// Mesh: one quad, UV 0..1 (v up), UV2 = corner offset in px from the anchor.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled, shadows_disabled;
stencil_mode write, compare_always, 5;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D tufts : filter_nearest;
uniform sampler2D palette : filter_nearest;

varying vec3 v_wp;
varying vec3 v_n;
varying flat vec4 v_inst;
varying vec3 v_alb;
varying vec2 v_cell;

void vertex() {
	vec3 anchor = MODEL_MATRIX[3].xyz;
	v_n = normalize(MODEL_MATRIX[1].xyz);
	v_inst = INSTANCE_CUSTOM;
	vec3 a = anchor + w3_snap(anchor);
	float top = UV.y;                                  // 0 root .. 1 tips
	vec2 sway = w3_wind_px(anchor, INSTANCE_CUSTOM.w, 1.0);
	// bend away from her feet
	vec3 d = anchor - (w3_player.xyz - vec3(0.0, 1.0, -0.52));
	float dist = length(d.xz);
	if (dist < 0.7 && w3_player.w > 0.0) {
		sway.x += round(sign(d.x + 0.001) * 2.0 * (1.0 - dist / 0.7));
		sway.y -= round(1.5 * (1.0 - dist / 0.7));
	}
	vec2 off = UV2 + floor(sway * top + 0.5);
	vec3 wp = a + vec3(off.x / w3_view.x, off.y / w3_view.x, -w3_view.w * off.y / w3_view.x);
	VERTEX = wp;
	v_wp = wp;
	NORMAL = v_n;
}

void fragment() {
	vec2 cellv = floor(v_inst.x + 0.5) * vec2(1.0, 0.0);
	int ci = int(v_inst.x + 0.5);
	ivec2 base = ivec2((ci % 4) * 16, (ci / 4) * 16);
	ivec2 tp = base + ivec2(int(clamp(floor(UV.x * 16.0), 0.0, 15.0)), int(clamp(15.0 - floor(UV.y * 16.0), 0.0, 15.0)));
	vec4 t = texelFetch(tufts, tp, 0);
	if (t.a < 0.5) {
		discard;
	}
	// cards are double-sided and may face either way: keep the ground normal they were given
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	vec2 cell = w3_ptex(v_wp);
	int acc = int(t.g * 255.0 + 0.5) - 1;
	vec3 alb;
	if (acc >= 0) {
		alb = w3_srgb_to_linear(texelFetch(palette, ivec2(acc % 8, 11 + acc / 8), 0).rgb);
	} else {
		float tone = clamp(floor(3.6 + v_inst.z + t.r * 255.0 - 4.0 + 0.5), 0.0, 7.0);
		alb = w3_srgb_to_linear(texelFetch(palette, ivec2(int(tone), int(v_inst.y + 0.5)), 0).rgb);
	}
	alb = w3_wetten(alb, 0.6);
	v_alb = alb;
	v_cell = cell;
	ALBEDO = vec3(1.0);
	EMISSION = w3_ambient(alb, v_n, 1.0) + w3_lamp_light(alb, v_wp, v_n, cell, 1.0);
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		float ndl = dot(NORMAL, LIGHT);
		float lvl = ndl > 0.80 ? 1.0 : (ndl > 0.58 ? 0.86 : (ndl > 0.30 ? 0.68 : (ndl > 0.04 ? 0.5 : 0.0)));
		DIFFUSE_LIGHT += v_alb * w3_lit_tint * LIGHT_COLOR / W3_PI * lvl * step(0.5, ATTENUATION);
	} else {
		DIFFUSE_LIGHT += w3_point_light(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, v_cell, 1.0);
	}
}
