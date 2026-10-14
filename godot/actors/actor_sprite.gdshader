// Her body state on her sprite (BodyState.look() -> Actor.set_body_look): an outline in the
// quality's colour (ember pulses, frost stays), a tint, darkening that keeps a brightness floor,
// a frost rim and an ember glow. Solid colours only: nothing here dithers or flickers on the
// character (CLAUDE.md §3, character light protection).
shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(0.0);
uniform vec4 tint : source_color = vec4(1.0);
uniform float darken = 0.0;       // 0..1: how much darker (BodyRules "darken")
uniform float floor_light = 0.55; // never darker than this share of the original (light protection)
uniform float frost = 0.0;
uniform float ember = 0.0;
uniform float pulse_speed = 0.0; // 0: steady outline; > 0: the outline breathes (ember)

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	vec2 px = TEXTURE_PIXEL_SIZE;
	// (TEXTURE is sampled inline: a built-in sampler cannot be passed to a function)
	float around = texture(TEXTURE, UV + vec2(px.x, 0.0)).a + texture(TEXTURE, UV - vec2(px.x, 0.0)).a
		+ texture(TEXTURE, UV + vec2(0.0, px.y)).a + texture(TEXTURE, UV - vec2(0.0, px.y)).a;
	if (c.a < 0.5) {
		if (outline_color.a > 0.0 && around > 0.5) {
			float p = pulse_speed > 0.0 ? 0.65 + 0.35 * sin(TIME * pulse_speed) : 1.0;
			c = vec4(outline_color.rgb, outline_color.a * p);
		}
	} else {
		c.rgb *= tint.rgb;
		c.rgb *= max(1.0 - darken, floor_light);
		// rim: opaque pixels at the silhouette's edge
		float edge = step(around, 3.5);
		c.rgb = mix(c.rgb, vec3(0.82, 0.92, 1.0), frost * edge * 0.6);
		c.rgb += vec3(1.0, 0.45, 0.15) * ember * edge * (0.28 + 0.07 * sin(TIME * 4.0));
	}
	COLOR = c;
}
