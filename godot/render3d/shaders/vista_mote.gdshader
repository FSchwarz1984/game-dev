// Small silver lights rising from the 遠化 round the town (G5R3-22) in the view from the lookout
// (W3Vista, vista3d.gd _motes): a point of one pixel (a few of two), set on the lattice of pixel
// corners like the impostors, so a light climbs by whole pixels and never smears. Hidden behind nearer
// land by the depth.
// At night a cool silver over the dark silver-grey land. By day the land round the town is silver-white
// itself and a white point on it cannot be seen (the lead): there the point is a light cool blue with
// a one-pixel darker, cooler edge round it (its four sides), fading out toward the night.
// Instance: origin = the light; INSTANCE_CUSTOM = (size px, brightness, seed, fade 0..1).
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled, skip_vertex_transform;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform vec3 mote_col = vec3(0.84, 0.9, 1.0);       // linear: a cool silver (the night's)
uniform vec3 mote_day = vec3(0.5, 0.78, 1.25);      // linear: a light cool blue (the day's)
uniform vec3 edge_col = vec3(0.07, 0.1, 0.19);      // linear: the day's edge, a dark cool slate
uniform float edge_alpha = 0.6;

varying flat vec4 v_cus;
varying vec2 v_q;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	// a square of c.x pixels from a corner of the lattice (its pixels' centres inside it), and a pixel
	// round it for the edge
	vec2 pxo = v_px_of(o, eye);
	vec2 corner = v_snap(pxo);
	float n = c.x + 2.0;
	vec2 off = vec2(UV.x, -UV.y) * n + vec2(-1.0, 1.0);
	// (far round to the side or behind: not drawn, as v_project)
	POSITION = abs(pxo.x) > 1.75 * v_ppr ? vec4(0.0, 0.0, 0.0, -1.0) : v_clip(corner + off, length(o - eye), PROJECTION_MATRIX);
	v_cus = c;
	v_q = UV * n;
}

void fragment() {
	float n = v_cus.x + 2.0;
	vec2 q = floor(clamp(v_q, vec2(0.0), vec2(n - 0.001)));
	bool ex = q.x < 0.5 || q.x > n - 1.5;
	bool ey = q.y < 0.5 || q.y > n - 1.5;
	float day = 1.0 - w3_night;
	if (ex && ey) discard;                       // (the edge goes round the four sides, not the corners)
	if (ex || ey) {
		if (day < 0.01) discard;
		ALBEDO = edge_col;
		ALPHA = edge_alpha * day * v_cus.w;
	} else {
		// (at night as bright as it was added over the land; by day the light blue)
		ALBEDO = mix(mote_col * 1.3, mote_day, day) * v_cus.y;
		ALPHA = clamp(v_cus.w, 0.0, 1.0);
	}
}
