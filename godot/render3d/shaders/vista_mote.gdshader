// Small silver lights rising from the 遠化 round the town (G5R3-22) in the view from the lookout
// (W3Vista, vista3d.gd _motes): a point of one pixel (a few of two), set on the lattice of pixel
// corners like the impostors, so a light climbs by whole pixels and never smears; added to what lies
// behind it, a little over white by day so the view's glow takes it (the only things of the 遠化 that
// glow). Hidden behind nearer land by the depth.
// Instance: origin = the light; INSTANCE_CUSTOM = (size px, brightness, seed, 0).
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled, skip_vertex_transform;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform vec3 mote_col = vec3(0.84, 0.9, 1.0);   // linear: a cool silver

varying flat vec4 v_cus;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	// a square of c.x pixels from a corner of the lattice (its pixels' centres inside it)
	vec2 pxo = v_px_of(o, eye);
	vec2 corner = v_snap(pxo);
	vec2 off = vec2(UV.x, -UV.y) * c.x;
	// (far round to the side or behind: not drawn, as v_project)
	POSITION = abs(pxo.x) > 1.75 * v_ppr ? vec4(0.0, 0.0, 0.0, -1.0) : v_clip(corner + off, length(o - eye), PROJECTION_MATRIX);
	v_cus = c;
}

void fragment() {
	ALBEDO = mote_col * v_cus.y;
	ALPHA = 1.0;
}
