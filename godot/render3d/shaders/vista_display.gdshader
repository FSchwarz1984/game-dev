// The view from the lookout on the window: the same grading as the world's composite
// (composite.gdshader, copied each frame by W3Vista) and a dissolve in native pixels (an ordered
// 8x8 dither: the view comes in pixel by pixel over the top-down world, and leaves the same way).
shader_type canvas_item;
render_mode unshaded;

uniform vec3 lift = vec3(0.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform vec3 shadow_tone = vec3(0.0);
uniform vec3 high_tone = vec3(0.0);
uniform float vignette = 0.25;
uniform vec4 fade = vec4(0.0);
uniform float amount = 1.0;                 // 0 hidden .. 1 shown

float bayer8(vec2 p) {
	ivec2 q = ivec2(mod(p, 8.0));
	int M[64] = int[64](0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38,
		60, 28, 52, 20, 62, 30, 54, 22, 3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47, 7, 39, 13, 45, 5, 37,
		63, 31, 55, 23, 61, 29, 53, 21);
	return (float(M[q.y * 8 + q.x]) + 0.5) / 64.0;
}

void fragment() {
	vec2 tex_size = vec2(textureSize(TEXTURE, 0));
	vec2 px = floor(UV * tex_size);
	if (bayer8(px) >= amount) discard;
	vec3 c = texture(TEXTURE, UV).rgb;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	c = lift + c * (gain - lift);
	float l2 = dot(c, vec3(0.299, 0.587, 0.114));
	c += shadow_tone * (1.0 - smoothstep(0.0, 0.5, l2)) + high_tone * smoothstep(0.45, 1.0, l2);
	vec2 p = UV - 0.5;
	c *= 1.0 - dot(p * vec2(1.0, 0.8), p * vec2(1.0, 0.8)) * vignette;
	c = mix(c, fade.rgb, fade.a);
	COLOR = vec4(c, 1.0);
}
