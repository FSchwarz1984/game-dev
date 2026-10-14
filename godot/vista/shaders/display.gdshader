// Shows the vista's HDR viewport on the window: linear -> sRGB, then the screen-space finishing of
// the JS vista done in sRGB as the canvas did it: the vignette (a radial gradient of near-black) and
// the white the end of the wave washes everything into. One native pixel = one value (no smoothing
// across the upscale).
shader_type canvas_item;

uniform vec2 tex_size;
uniform vec2 border = vec2(1.0);
uniform vec2 vign_c;
uniform vec2 vign_r;              // inner, outer radius
uniform float vign_a = 0.35;
uniform vec3 vign_col = vec3(4.0, 5.0, 12.0);
uniform float wash_a = 0.0;
uniform vec3 wash_col = vec3(226.0, 232.0, 246.0);

vec3 to_srgb(vec3 c) {
	c = clamp(c, vec3(0.0), vec3(1.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

void fragment() {
	vec3 c = to_srgb(texture(TEXTURE, UV).rgb);
	vec2 p = floor(UV * tex_size) - border + 0.5;
	float k = clamp((length(p - vign_c) - vign_r.x) / (vign_r.y - vign_r.x), 0.0, 1.0) * vign_a;
	c = mix(c, vign_col / 255.0, k);
	c = mix(c, wash_col / 255.0, wash_a);
	COLOR = vec4(c, 1.0);
}
