// The view from the lookout on the window: the same grading as the world's composite
// (composite.gdshader, copied each frame by W3Vista), and the way in and out of it: the picture
// fades into the white of the mist and back out (no halftone): over the top-down world while
// the view is not yet shown, then over the view itself. The view's viewport is HDR (linear float,
// round 4): converted here, and the 8-bit output dithered by half a code value with blue noise fixed
// to the view's lattice of directions (it turns with the land by whole pixels: no crawl, no bands).
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
uniform bool hdr_input = true;
uniform sampler2D blue_noise : filter_nearest, repeat_enable;
uniform vec2 cam_cell = vec2(0.0);          // the view's lattice offset (px of yaw, pitch)
uniform float dither_amp = 1.0;

vec3 lin_to_srgb(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

void fragment() {
	if (!shown) {
		// before the view comes in (or after it has left): only the white, over the world
		COLOR = vec4(veil_col, veil);
	} else {
		vec3 c = texture(TEXTURE, UV).rgb;
		if (hdr_input) {
			// lights over white keep their hue (the brightest channel rolls off, the others follow)
			float mx = max(c.r, max(c.g, c.b));
			if (mx > 0.8) {
				c *= (0.8 + 0.2 * (1.0 - exp(-(mx - 0.8) / 0.2))) / mx;
			}
			c = lin_to_srgb(c);
		}
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
		c = mix(c, veil_col, veil);
		vec2 ts = vec2(textureSize(TEXTURE, 0));
		vec2 tp = UV * ts;
		vec2 cell = floor(vec2(tp.x - ts.x * 0.5, ts.y * 0.5 - tp.y)) + cam_cell;
		c += (texelFetch(blue_noise, ivec2(mod(cell, 64.0)), 0).r - 0.5) * dither_amp / 255.0;
		COLOR = vec4(c, 1.0);
	}
}
