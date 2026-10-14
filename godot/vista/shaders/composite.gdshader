// Adds a buffer of light onto the scene the way the JS vista did ('lighter' on an sRGB canvas: a dim
// halo over a dark sky shows), instead of in linear light (where it would all but vanish). The
// lights were summed in sRGB units (0..1 per channel) into their own float buffer; here
// result = linear(srgb(scene) + lights). What goes past 1.0 (cores, the gate, many sparks on one
// pixel) is kept, scaled by `excess`, as HDR: that, and only that, is what the viewport's glow blooms.
shader_type canvas_item;
render_mode blend_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D add_tex : filter_nearest, repeat_disable;
uniform float excess = 0.35;

vec3 to_srgb(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

vec3 to_lin(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec3 dst = texture(screen_tex, SCREEN_UV).rgb;
	vec3 add = texelFetch(add_tex, ivec2(FRAGCOORD.xy), 0).rgb;
	vec3 s = to_srgb(dst) + add;
	vec3 over = max(s - 1.0, vec3(0.0));
	COLOR = vec4(to_lin(min(s, vec3(1.0))) + to_lin(vec3(1.0) + over * excess) - vec3(1.0), 1.0);
}
