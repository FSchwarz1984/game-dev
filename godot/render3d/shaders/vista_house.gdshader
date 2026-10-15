// The houses of the plain's villages and the town in the view from the lookout (W3Vista): at one to
// five kilometres a house is a few pixels, so each is drawn as a tiny sprite built in place in screen
// pixels around its foot on the pixel lattice (geometry this small would flicker as the view turns):
// the roof's rows on top (a lighter ridge row when there is room), the wall's row under it, and at
// night its windows lit (most houses, a few dark); the street lamps are single warm pixels. Then the
// same air as the land.
// Instance: origin = the foot; INSTANCE_CUSTOM = (width m, depth m, height m, seed 0..1);
// COLOR = the roof's colour (sRGB).
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform vec3 light_col = vec3(1.0);
uniform vec3 ambient_col = vec3(0.4);
uniform float night = 0.0;
uniform vec3 window_col : source_color = vec3(1.0, 0.72, 0.38);

varying vec3 v_wp;
varying flat vec4 v_cus;
varying flat vec4 v_col;
varying flat vec2 v_size;     // sprite width, height in px
varying flat float v_roof;    // roof rows
varying vec2 v_px;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	float depth = length(o - eye);
	float ppm = v_ppr / max(length(o - eye), 1.0);      // pixels per metre there
	float wpx = clamp(floor(max(c.x, c.y) * ppm * 0.9 + 0.5), 1.0, 9.0);
	float rpx = clamp(floor(c.z * 0.55 * ppm + 0.5), 1.0, 4.0);
	float hpx = clamp(floor(c.z * 0.45 * ppm + 0.35), 0.0, 3.0);
	if (c.x < 0.0) {
		wpx = 1.0;
		rpx = 1.0;
		hpx = 0.0;
	}
	// the quad: centred on the foot horizontally, from the foot up, on the lattice of pixel corners
	vec2 foot = v_snap(v_px_of(o, eye));
	vec2 off = vec2(UV.x * wpx - floor(wpx * 0.5), (1.0 - UV.y) * (rpx + hpx));
	POSITION = v_clip(foot + off, depth, PROJECTION_MATRIX);
	v_wp = o;
	v_cus = c;
	v_col = COLOR;
	v_size = vec2(wpx, rpx + hpx);
	v_roof = rpx;
	v_px = vec2(UV.x * wpx, (1.0 - UV.y) * (rpx + hpx));
}

void fragment() {
	if (v_cus.x < 0.0) {
		// a street lamp: only its light, at night (a single warm pixel)
		if (night < 0.3 || v_drain(v_wp.xz, v_wp.y) > 0.9) discard;
		ALBEDO = w3_srgb_to_linear(window_col) * 3.4;
	} else {
	vec2 q = floor(v_px);
	float row = v_size.y - 1.0 - q.y;      // 0 at the top
	vec3 sd = normalize(w3_sun_dir);
	float day = clamp(sd.y * 3.0, 0.0, 1.0);
	vec3 col;
	if (row < v_roof) {
		vec3 roof = w3_srgb_to_linear(v_col.rgb);
		// the ridge row catches the light when the roof has room for it
		float k = (row < 0.5 && v_roof > 1.5) ? 1.25 : 1.0;
		// (the end that faces the sun a little lighter)
		if (q.x < 0.5 && v_size.x > 2.5 && sd.x < 0.0) k *= 1.1;
		if (q.x > v_size.x - 1.5 && v_size.x > 2.5 && sd.x > 0.0) k *= 1.1;
		col = roof * k * (ambient_col + light_col * 0.7 * day);
	} else {
		vec3 wall = w3_srgb_to_linear(vec3(0.78, 0.75, 0.68));
		col = wall * (ambient_col + light_col * 0.45 * day);
	}
	// windows at night: most houses lit (a pane or two; a far house that is a single pixel shows
	// only its light)
	// (past the 遠化 front a house has lost its light with everything else)
	bool lit_house = night > 0.3 && fract(v_cus.w * 7.31) > 0.12 && v_drain(v_wp.xz, v_wp.y) < 0.9;
	float h = w3_hash(vec2(v_cus.w * 913.0, q.x));
	bool win = lit_house && ((row >= v_roof && (h > 0.45 || v_size.x < 2.5)) || (v_size.y < 1.5 && h > 0.3));
	vec3 c = v_air(col, v_wp, eye, FRAGCOORD.xy);
	// (in the 遠化's white a house is only its drawing: the roof a faint mark, the wall the paper)
	if (v_past(v_wp, eye, FRAGCOORD.xy)) c = v_paper(row < v_roof ? 0.8 : 0.0);
	// (a lit window shines through the air)
	ALBEDO = win ? mix(c, w3_srgb_to_linear(window_col) * 3.2, 0.88) : c;
	}
}
