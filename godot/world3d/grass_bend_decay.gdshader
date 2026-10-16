// The grass bend map's recovery pass (world3d/grass.gd): drawn first each frame over the whole map,
// it reads what the map held last frame and moves every texel back toward "upright" (rg 0.5, b 0) by
// the fraction k, and by at least one 8-bit step so nothing stays bent for ever.
shader_type canvas_item;
render_mode blend_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform float k = 0.02;
uniform bool init = false;

void fragment() {
	vec4 o = texture(screen_tex, SCREEN_UV);
	if (init || o.a < 0.5) {
		COLOR = vec4(0.5, 0.5, 0.0, 1.0);
	} else {
		vec3 d = o.rgb - vec3(0.5, 0.5, 0.0);
		vec3 s = sign(d) * max(abs(d) * k, vec3(1.0 / 255.0));
		s = mix(s, d, step(abs(d), vec3(1.0 / 255.0)));
		COLOR = vec4(o.rgb - s, 1.0);
	}
}
