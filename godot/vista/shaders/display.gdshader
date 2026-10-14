// Shows the vista's HDR viewport on the window: linear -> sRGB, then the screen-space finishing of
// the JS vista done in sRGB as the canvas did it: the pale front rising over the crown at the end of
// the wave, the vignette (a radial gradient of near-black) and the white the end washes all into. One native pixel = one value (no smoothing
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
uniform float end_k = 0.0;         // the end of the wave: the pale front rises over the crown
uniform vec2 view = vec2(480.0, 270.0);

vec3 to_srgb(vec3 c) {
	c = clamp(c, vec3(0.0), vec3(1.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

void fragment() {
	vec3 c = to_srgb(texture(TEXTURE, UV).rgb);
	vec2 p = floor(UV * tex_size) - border + 0.5;
	if (end_k > 0.0) {
		// south.js endG: a gradient over [0.35 H, H] (stops 0, 0.45 at 0.6, 0.85 at 1), drawn
		// (1 - k) 0.55 H lower than its place, with alpha k 0.85
		float y = p.y - floor((1.0 - end_k) * view.y * 0.55 + 0.5);
		float g = clamp((y - view.y * 0.35) / (view.y * 0.65), 0.0, 1.0);
		float a = y < view.y * 0.35 ? 0.0 : g < 0.6 ? g / 0.6 * 0.45 : mix(0.45, 0.85, (g - 0.6) / 0.4);
		vec3 gc = g < 0.6 ? vec3(214.0, 224.0, 246.0) : mix(vec3(214.0, 224.0, 246.0), vec3(226.0, 232.0, 250.0), (g - 0.6) / 0.4);
		c = mix(c, gc / 255.0, a * end_k * 0.85);
	}
	float k = clamp((length(p - vign_c) - vign_r.x) / (vign_r.y - vign_r.x), 0.0, 1.0) * vign_a;
	c = mix(c, vign_col / 255.0, k);
	c = mix(c, wash_col / 255.0, wash_a);
	COLOR = vec4(c, 1.0);
}
