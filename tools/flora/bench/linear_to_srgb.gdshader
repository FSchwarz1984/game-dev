// Shows the world viewport's linear HDR values on the sRGB window (PixelStage). Values above 1 are
// clipped here; the world's glow has already spread them.
shader_type canvas_item;

vec3 to_srgb(vec3 c) {
	c = clamp(c, vec3(0.0), vec3(1.0));
	vec3 lo = c * 12.92;
	vec3 hi = 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055;
	return mix(lo, hi, step(vec3(0.0031308), c));
}

void fragment() {
	vec4 t = texture(TEXTURE, UV);
	COLOR = vec4(to_srgb(t.rgb), t.a);
}
