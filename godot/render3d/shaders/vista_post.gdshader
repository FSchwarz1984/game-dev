// Outlines for the view from the lookout (W3Vista): a full-screen quad drawn first in the
// transparent pass. Where a neighbouring pixel lies clearly farther (relative to the distance, so far
// ridges get their line as well as near rocks), this pixel is on the near edge of something: it takes
// a darker, cooler shade of the darker side. One native pixel wide, never black.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform float strength = 0.75;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float view_depth(vec2 uv, mat4 ip) {
	float d = texture(depth_tex, uv).r;
	vec4 v = ip * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	vec2 uv = SCREEN_UV;
	mat4 ip = INV_PROJECTION_MATRIX;
	float c = view_depth(uv, ip);
	float l = view_depth(uv - vec2(px.x, 0.0), ip);
	float r = view_depth(uv + vec2(px.x, 0.0), ip);
	float u = view_depth(uv - vec2(0.0, px.y), ip);
	float d = view_depth(uv + vec2(0.0, px.y), ip);
	vec3 col = texture(screen_tex, uv).rgb;
	vec2 behind = vec2(-px.x, 0.0);
	float bd = l;
	if (r > bd) { bd = r; behind = vec2(px.x, 0.0); }
	if (u > bd) { bd = u; behind = vec2(0.0, -px.y); }
	if (d > bd) { bd = d; behind = vec2(0.0, px.y); }
	// the sky is very far: an edge against it counts
	float jump = bd - c;
	float th = 0.35 + c * 0.06;
	if (c < 20000.0 && jump > th) {
		vec3 bcol = texture(screen_tex, uv + behind).rgb;
		vec3 base = dot(bcol, vec3(0.3, 0.59, 0.11)) < dot(col, vec3(0.3, 0.59, 0.11)) ? mix(col, bcol, 0.6) : col;
		col = mix(col, base * vec3(0.55, 0.58, 0.68), strength * (1.0 - smoothstep(1500.0, 6000.0, c)));
	}
	ALBEDO = col;
	ALPHA = 1.0;
}
