// Composite of the low-res 3D image onto the window (canvas_item, drawn at an integer scale with
// nearest sampling; the sub-pixel camera remainder is the TextureRect's offset). Grading per time
// of day: a gentle S-curve (contrast without crushing), lift/gain/saturation, split toning (shadows
// cool and a little lifted, highlights warm) and a light vignette. Values are display (sRGB) values.
// No film grain: per-frame noise would read as shimmer.
shader_type canvas_item;
render_mode unshaded;

uniform vec3 lift = vec3(0.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform vec3 shadow_tone = vec3(0.0);     // added to dark tones
uniform vec3 high_tone = vec3(0.0);       // added to light tones
uniform float contrast = 0.0;             // S-curve amount 0..1 (pivot at mid grey)
uniform float vignette = 0.25;
uniform vec4 fade = vec4(0.0);            // rgb, amount
uniform vec2 view_size = vec2(480.0, 270.0);   // logical (visible) size in native px
uniform vec2 margin_px = vec2(1.0, 1.0);       // the low-res image's hidden border

void fragment() {
	vec3 c = texture(TEXTURE, UV).rgb;
	// S-curve on luma (the hue and the chroma ratio stay put), pivoting low: the darks keep their
	// place (the lift raises them a touch), the mids and lights open up, the top rolls off
	float l0 = dot(c, vec3(0.299, 0.587, 0.114));
	float ls = l0 + contrast * max(l0 - 0.26, 0.0) * (1.0 - l0) * 1.6;
	c *= ls / max(l0, 1e-4);
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	c = lift + c * (gain - lift);
	float l2 = dot(c, vec3(0.299, 0.587, 0.114));
	c += shadow_tone * (1.0 - smoothstep(0.0, 0.5, l2)) + high_tone * smoothstep(0.45, 1.0, l2);
	// vignette in the visible frame
	vec2 tex_size = vec2(textureSize(TEXTURE, 0));
	vec2 p = (UV * tex_size - margin_px) / view_size - 0.5;
	c *= 1.0 - dot(p * vec2(1.0, 0.8), p * vec2(1.0, 0.8)) * vignette;
	c = mix(c, fade.rgb, fade.a);
	COLOR = vec4(c, 1.0);
}
