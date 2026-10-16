// Her (and さぢ) in the view from the lookout (W3Vista), seen from behind as she looks out: the
// sprite's own back-view frame on an upright card turned to the camera, texel for pixel (the camera
// stands where one sprite pixel is one screen pixel), lit flat by the hour with the character
// protection (a floor of brightness: she reads first in every light; a light rim on the sun's side of
// her outline; no dither), then the same air (very little at this distance).
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled, depth_prepass_alpha;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform sampler2D sheet : filter_nearest, source_color;
uniform vec4 frame_rect = vec4(0.0, 0.0, 64.0, 78.0);   // px in the sheet
uniform vec2 pivot_px = vec2(32.0, 65.0);
uniform vec3 eye = vec3(0.0);
uniform vec3 light_col = vec3(1.0);                      // the hour's light on her (linear)
uniform float sheet_ppm = 20.0;                          // the sheet's px per metre
uniform float px_scale = 1.0;                            // screen px per sheet px (the land's scale at her)

varying vec3 v_wp;
varying vec2 v_px;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	// corners in sprite px relative to the pivot (y up), around the foot moved onto the pixel lattice;
	// px_scale screen px per sheet px (her 3D picture: 1, drawn at the land's scale; a 20 px/m sprite:
	// the land's scale at her distance over 20, about 1.33)
	vec2 c = vec2(mix(-pivot_px.x, frame_rect.z - pivot_px.x, UV.x), mix(pivot_px.y, pivot_px.y - frame_rect.w, UV.y));
	vec2 foot = v_snap(v_px_of(o, eye));
	POSITION = v_clip(foot + floor(c * px_scale + 0.5), length(o - eye), PROJECTION_MATRIX);
	v_wp = o + vec3(0.0, c.y / sheet_ppm, 0.0);
	v_px = vec2(UV.x * frame_rect.z, UV.y * frame_rect.w);
}

uniform float rim_side = 1.0;           // +1: the sun is to the screen's right, -1: to its left
uniform vec3 rim_col = vec3(1.0, 0.92, 0.78);
// her 3D model's picture (vista3d.gd _build_fig3d): lit already by her own material in her own
// world (the light of the hour, her brightness floor, her rims); here only her outline, a pixel wide,
// a dark tone of the colour beside it (the top-down world draws it in its post pass), and the air
uniform bool baked = false;

void fragment() {
	ivec2 tp = ivec2(frame_rect.xy + floor(v_px));
	vec4 t = texelFetch(sheet, tp, 0);
	vec3 col = t.rgb;
	if (baked) {
		if (t.a < 0.5) {
			vec4 nb = vec4(0.0);
			for (int k = 0; k < 4; k++) {
				ivec2 o = k == 0 ? ivec2(1, 0) : (k == 1 ? ivec2(-1, 0) : (k == 2 ? ivec2(0, 1) : ivec2(0, -1)));
				ivec2 qp = clamp(tp + o, ivec2(frame_rect.xy), ivec2(frame_rect.xy + frame_rect.zw) - 1);
				vec4 tn = texelFetch(sheet, qp, 0);
				if (tn.a >= 0.5 && nb.a < 0.5) nb = tn;
			}
			if (nb.a < 0.5) discard;
			col = nb.rgb * vec3(0.32, 0.28, 0.3);
		}
	} else {
		if (t.a < 0.5) discard;
		col = t.rgb * light_col;
		// the protection: never darker than a floor of her own colour, a light rim on the sun's side of
		// her outline (the edge pixel whose neighbour toward the light is empty), no dither on her
		col = max(col, t.rgb * 0.42);
		ivec2 side = ivec2(int(rim_side), 0);
		ivec2 q = tp + side;
		bool inside = q.x >= int(frame_rect.x) && q.x < int(frame_rect.x + frame_rect.z);
		if (!inside || texelFetch(sheet, q, 0).a < 0.5) {
			col = mix(col, max(col, t.rgb) * rim_col * 1.25, 0.6);
		}
	}
	ALBEDO = v_air(col, v_wp, eye, FRAGCOORD.xy);
}
