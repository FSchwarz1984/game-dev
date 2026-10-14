// The 遠化 mist seen from the lookout (W3Vista): a curtain standing on the ellipse that rings the
// region (map v2: "四周是远化之雾"), dense at its foot, thinning upward to a billowing top edge
// that drifts slowly. The land beyond shows through it faintly ("看得见却不再近"). Pale and
// luminous (a touch lighter than the haze), in whole steps of cover with a narrow dithered seam.
// UV.x = around the ring (0..1), UV.y = 0 at the top edge's base height .. 1 at the foot.
shader_type spatial;
render_mode world_vertex_coords, unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform float time = 0.0;

varying vec3 v_wp;
varying vec2 v_uv;

void vertex() {
	v_wp = VERTEX;
	v_uv = UV;
}

void fragment() {
	float a = v_uv.x * 6.2831853;
	// the top edge: billows along the ring, drifting
	// (broad billows only: a fine term drew thin vertical streaks against the night sky)
	float b = w3_vnoise(vec2(v_uv.x * 70.0 + time * 0.25, 1.0)) * 0.75 + w3_vnoise(vec2(v_uv.x * 140.0 - time * 0.4, 5.0)) * 0.25;
	float top = 0.12 + b * 0.22;
	float cover = smoothstep(top, top + 0.3, v_uv.y);
	cover = max(cover * 0.86, 0.0);
	float dz = v_bayer8(FRAGCOORD.xy) - 0.5;
	float cq = floor(cover * 5.0 + 0.5 + dz * 0.5) / 5.0;
	if (cq <= 0.0) discard;
	// lit along the billows' tops, a little darker in the body
	vec3 col = mist_col * (v_uv.y < top + 0.08 ? 1.06 : 0.97);
	ALBEDO = col;
	ALPHA = min(cq, 0.92);
}
