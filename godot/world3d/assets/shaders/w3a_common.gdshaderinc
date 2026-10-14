// Shared by the 3D asset shaders (godot/world3d/assets/shaders). Toon light with hue-shifted ramps,
// the see-through hole around her, and the 遠化 (far) look.
// STAND-IN: until the renderer's contract (docs/knowledge/21-3d-pixel-render.md) exists these
// uniforms are set per material by whoever renders (the asset bench sets them every frame).

uniform float w3a_px_per_m = 20.0;                 // native px per metre (orthographic camera)
uniform vec3 w3a_key_dir = vec3(-0.55, 0.70, 0.45); // world space, toward the light that shades surfaces
uniform vec3 w3a_see_pos = vec3(0.0, -1000.0, 0.0); // world position of her chest
uniform float w3a_see_r_px = 20.0;                  // hole radius in native px
uniform float w3a_see_soft_px = 10.0;               // dithered rim width
uniform vec3 w3a_far_tint : source_color = vec3(0.663, 0.722, 0.824);   // PAL.far #a9b8d2
instance uniform float far_k : hint_range(0.0, 1.0) = 0.0;           // 遠化: 0 near, 1 fully far

float w3a_bayer4(vec2 fc) {
	ivec2 i = ivec2(mod(floor(fc), 4.0));
	int k = i.x + i.y * 4;
	const float m[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
	return (m[k] + 0.5) / 16.0;
}

// Discard what stands between the camera and her, inside a dithered disc around her on screen.
// view_pos: fragment position in view space; view_m: VIEW_MATRIX.
void w3a_see_through(vec3 view_pos, mat4 view_m, vec2 frag_coord, float radius_scale) {
	vec3 sv = (view_m * vec4(w3a_see_pos, 1.0)).xyz;
	if (view_pos.z > sv.z + 0.35) {
		float d = length((view_pos.xy - sv.xy) * w3a_px_per_m);
		float r = w3a_see_r_px * radius_scale;
		float k = 1.0 - smoothstep(r - w3a_see_soft_px, r, d);
		if (k > 0.0 && k >= w3a_bayer4(frag_coord)) {
			discard;
		}
	}
}

// The far look: colours lose their chroma and contrast and drift to a pale blue-grey.
vec3 w3a_far(vec3 col) {
	if (far_k <= 0.0) {
		return col;
	}
	float l = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 pale = mix(vec3(l), w3a_far_tint, 0.55) * 0.45 + w3a_far_tint * 0.55;
	pale = mix(pale, vec3(0.9, 0.92, 0.96), 0.15);
	return mix(col, pale, far_k * 0.88);
}

// Toon bands on a value 0..1 with a light ordered dither only right at the band edges.
float w3a_band(float v, float n, vec2 frag_coord) {
	float d = (w3a_bayer4(frag_coord) - 0.5) * 0.06;
	return clamp(floor((v + d) * n), 0.0, n - 1.0);
}
