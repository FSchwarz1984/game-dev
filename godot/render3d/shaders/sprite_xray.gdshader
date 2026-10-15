// A character seen through what stands in front of her (charter: "遮挡时挖透视孔"; the art sample
// round 2): wherever a trunk, a limb, an eave or a post covers her sprite, her silhouette is drawn
// over it: a 1-px outline in her colour and a sparse stipple of her own pixels inside, so she (and
// さぢ) always read. Drawn late in the transparent pass, without the depth test, only where the
// stencil does NOT hold the character class (3): where she is visible, her own sprite wrote 3 there
// and nothing happens; where something covered her, its class is there instead.
// Same card as sprite_char.gdshader (CharSprite3D keeps both in step); never in the shadow pass.
shader_type spatial;
render_mode world_vertex_coords, unshaded, depth_test_disabled, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled, blend_mix;
stencil_mode read, compare_not_equal, 3;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D sheet : source_color, filter_nearest, hint_default_white;
uniform vec4 frame_rect = vec4(0.0, 0.0, 64.0, 64.0);   // px in the sheet: x, y, w, h
uniform bool flip_h = false;
uniform vec3 line_col : source_color = vec3(1.0, 0.86, 0.56);   // her colour (sRGB)
uniform float fill = 0.3;                                      // share of her pixels shown inside
// around her feet what covers her must stand clearly in front of her: the grass at her feet and the
// ground her card dips into are not "something in the way" (they would ring her feet whenever she
// walks in grass); above her knees anything counts (a wall she stands right behind)
uniform float min_gap = 0.6;                                   // m along the view
uniform float gap_below_px = 9.0;                              // native px above her feet
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

varying vec3 v_wp;
varying float v_up;

void vertex() {
	vec3 anchor = MODEL_MATRIX[3].xyz;
	vec3 a = anchor + w3_snap(anchor);
	vec2 off = UV2;
	vec3 wp = a + vec3(off.x / w3_view.x, off.y / w3_view.x, -w3_view.w * off.y / w3_view.x);
	VERTEX = wp;
	v_wp = wp;
	v_up = off.y;
}

float alpha_at(ivec2 t) {
	vec2 lo = frame_rect.xy;
	vec2 hi = frame_rect.xy + frame_rect.zw - 1.0;
	if (float(t.x) < lo.x || float(t.y) < lo.y || float(t.x) > hi.x || float(t.y) > hi.y) return 0.0;
	return texelFetch(sheet, t, 0).a;
}

void fragment() {
	vec2 uv = UV;
	if (flip_h) uv.x = 1.0 - uv.x;
	vec2 tp = frame_rect.xy + vec2(uv.x, 1.0 - uv.y) * frame_rect.zw;
	ivec2 ti = ivec2(clamp(floor(tp), frame_rect.xy, frame_rect.xy + frame_rect.zw - 1.0));
	vec4 c = texelFetch(sheet, ti, 0);
	if (c.a < 0.5) {
		discard;
	}
	vec4 sv = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, texture(depth_tex, SCREEN_UV).r, 1.0);
	if (v_up < gap_below_px && -sv.z / sv.w > -VERTEX.z - min_gap) {
		discard;
	}
	bool edge = alpha_at(ti + ivec2(1, 0)) < 0.5 || alpha_at(ti - ivec2(1, 0)) < 0.5
		|| alpha_at(ti + ivec2(0, 1)) < 0.5 || alpha_at(ti - ivec2(0, 1)) < 0.5;
	vec3 col;
	if (edge) {
		col = w3_srgb_to_linear(line_col);
	} else {
		// the stipple is keyed to her own texels, so it moves with her and never crawls
		vec2 k = vec2(ti - ivec2(frame_rect.xy));
		if (w3_hash(k * 1.37 + 11.0) > fill) {
			discard;
		}
		col = mix(w3_srgb_to_linear(c.rgb), w3_srgb_to_linear(line_col), 0.35) * 0.9;
	}
	ALBEDO = col;
	ALPHA = 1.0;
}
