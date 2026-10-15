// The view from the lookout on the window: the same grading as the world's composite
// (composite.gdshader, copied each frame by W3Vista), and the way in and out of it: the picture
// fades into the white of the mist and back out (no halftone): over the top-down world while
// the view is not yet shown, then over the view itself.
shader_type canvas_item;
render_mode unshaded;

uniform vec3 lift = vec3(0.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform vec3 shadow_tone = vec3(0.0);
uniform vec3 high_tone = vec3(0.0);
uniform float contrast = 0.0;
uniform float vignette = 0.25;
uniform vec4 fade = vec4(0.0);
uniform bool shown = true;                  // the view is on screen (under the veil)
uniform float veil = 0.0;                   // 0 .. 1 the mist's white over everything
uniform vec3 veil_col : source_color = vec3(0.92, 0.93, 0.94);

void fragment() {
	if (!shown) {
		// before the view comes in (or after it has left): only the white, over the world
		COLOR = vec4(veil_col, veil);
	} else {
		vec3 c = texture(TEXTURE, UV).rgb;
		float l0 = dot(c, vec3(0.299, 0.587, 0.114));
		float ls = l0 + contrast * max(l0 - 0.26, 0.0) * (1.0 - l0) * 1.6;
		c *= ls / max(l0, 1e-4);
		float l = dot(c, vec3(0.299, 0.587, 0.114));
		c = mix(vec3(l), c, saturation);
		c = lift + c * (gain - lift);
		float l2 = dot(c, vec3(0.299, 0.587, 0.114));
		c += shadow_tone * (1.0 - smoothstep(0.0, 0.55, l2)) + high_tone * smoothstep(0.45, 1.0, l2);
		vec2 p = UV - 0.5;
		c *= 1.0 - dot(p * vec2(1.0, 0.8), p * vec2(1.0, 0.8)) * vignette;
		c = mix(c, fade.rgb, fade.a);
		COLOR = vec4(mix(c, veil_col, veil), 1.0);
	}
}
