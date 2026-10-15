// A 3D character seen through what stands in front of her (charter: "遮挡时挖透视孔"; the art
// sample's x-ray, knowledge/21 §6.15), for the skinned mesh: wherever a trunk, a limb, an eave or a
// post covers her, her silhouette is drawn over it: her edges (where her surface turns away) in her
// x-ray colour, a sparse stipple of her own colour inside. Drawn late in the transparent pass as the
// main material's next pass, without the depth test, only where the stencil does NOT hold 3: where
// she is visible her own pixels wrote 3 and nothing happens. Around her feet whatever covers her
// must stand clearly in front (grass at her feet is not "something in the way").
shader_type spatial;
render_mode world_vertex_coords, unshaded, depth_test_disabled, depth_draw_never, cull_back, shadows_disabled, fog_disabled, blend_mix;
stencil_mode read, compare_not_equal, 3;
#include "res://characters/shaders/char_common.gdshaderinc"

uniform vec3 line_col : source_color = vec3(1.0, 0.84, 0.52);   // her colour (sRGB)
uniform float fill = 0.3;
uniform float min_gap = 0.6;            // m along the view
uniform float gap_below_px = 9.0;       // native px above her feet
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

varying vec3 v_wp;
varying vec3 v_wn;

void vertex() {
	v_wn = NORMAL;
	VERTEX = c3_lean_snap(VERTEX);
	v_wp = VERTEX;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	vec2 feet = floor(w3_screen(c3_leaned_anchor() + w3_snap(c3_leaned_anchor())));
	float up = cell.y - feet.y;
	vec4 sv = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, texture(depth_tex, SCREEN_UV).r, 1.0);
	if (up < gap_below_px && -sv.z / sv.w > -VERTEX.z - min_gap) {
		discard;
	}
	vec3 nv = normalize((VIEW_MATRIX * vec4(normalize(v_wn), 0.0)).xyz);
	vec3 col;
	if (nv.z < 0.38) {
		col = w3_srgb_to_linear(line_col);
	} else {
		// the stipple is keyed to her own lattice (relative to her feet), so it moves with her
		vec2 k = cell - feet;
		if (w3_hash(k * 1.37 + 11.0) > fill) {
			discard;
		}
		col = mix(w3_srgb_to_linear(COLOR.rgb), w3_srgb_to_linear(line_col), 0.35) * 0.9;
	}
	ALBEDO = col;
	ALPHA = 1.0;
}
