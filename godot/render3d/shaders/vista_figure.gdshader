// Her (and さぢ) in the view from the lookout (W3Vista), seen from behind as she looks out: the
// sprite's own back-view frame on an upright card turned to the camera, texel for pixel (the camera
// stands where one sprite pixel is one screen pixel), lit flat by the hour with the character
// protection (a floor of brightness: she reads first in every light), then the same air (very little
// at this distance).
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
	vec3 to_cam = eye - o;
	vec3 right = normalize(vec3(to_cam.z, 0.0, -to_cam.x));
	vec3 up = normalize(cross(normalize(to_cam), right));
	// corners in sprite px relative to the pivot (y up)
	vec2 c = vec2(mix(-pivot_px.x, frame_rect.z - pivot_px.x, UV.x), mix(pivot_px.y, pivot_px.y - frame_rect.w, UV.y));
	vec3 wp = o + (right * c.x + up * c.y) / 20.0;
	VERTEX = wp;
	v_wp = wp;
	v_px = vec2(UV.x * frame_rect.z, UV.y * frame_rect.w);
}

void fragment() {
	ivec2 tp = ivec2(frame_rect.xy + floor(v_px));
	vec4 t = texelFetch(sheet, tp, 0);
	if (t.a < 0.5) discard;
	vec3 col = t.rgb * light_col;
	// the protection: never darker than a floor of her own colour
	col = max(col, t.rgb * 0.42);
	ALBEDO = v_air(col, v_wp, eye, FRAGCOORD.xy);
}
