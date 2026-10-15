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

varying vec3 v_wp;
varying vec2 v_px;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	// corners in sprite px relative to the pivot (y up), around the foot moved onto the pixel lattice:
	// one sprite pixel is one screen pixel (the camera stands where 20 px per metre holds)
	vec2 c = vec2(mix(-pivot_px.x, frame_rect.z - pivot_px.x, UV.x), mix(pivot_px.y, pivot_px.y - frame_rect.w, UV.y));
	vec2 foot = v_snap(v_px_of(o, eye));
	POSITION = v_clip(foot + c, length(o - eye), PROJECTION_MATRIX);
	v_wp = o + vec3(0.0, c.y / 20.0, 0.0);
	v_px = vec2(UV.x * frame_rect.z, UV.y * frame_rect.w);
}

uniform float rim_side = 1.0;           // +1: the sun is to the screen's right, -1: to its left
uniform vec3 rim_col = vec3(1.0, 0.92, 0.78);

void fragment() {
	ivec2 tp = ivec2(frame_rect.xy + floor(v_px));
	vec4 t = texelFetch(sheet, tp, 0);
	if (t.a < 0.5) discard;
	vec3 col = t.rgb * light_col;
	// the protection: never darker than a floor of her own colour, a light rim on the sun's side of
	// her outline (the edge pixel whose neighbour toward the light is empty), no dither on her
	col = max(col, t.rgb * 0.42);
	ivec2 side = ivec2(int(rim_side), 0);
	ivec2 q = tp + side;
	bool inside = q.x >= int(frame_rect.x) && q.x < int(frame_rect.x + frame_rect.z);
	if (!inside || texelFetch(sheet, q, 0).a < 0.5) {
		col = mix(col, max(col, t.rgb) * rim_col * 1.25, 0.6);
	}
	ALBEDO = v_air(col, v_wp, eye, FRAGCOORD.xy);
}
