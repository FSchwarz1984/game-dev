// The air near the ground (round 4, Forward+ volumetric fog): one FogVolume over the region whose
// density lies in a layer over the terrain (thick at the ground, thinning upward, nothing far above
// it), drifting in broken banks. The sun's light scatters in it (shafts through the crowns, the
// canopy's shadow cut out of it), the lanterns light it (soft halos at night), the morning mist
// glows. The global fog stays zero: the air between the top-down camera and the ground is a
// convention, not air (a global density draws a veil over everything).
// render3d/world_env.gd sets density, layer, albedo and drift per hour; terrain3d.gd gives the
// height texture.
shader_type fog;

uniform sampler2D ground : filter_linear, repeat_disable;    // terrain heights (R, metres)
uniform vec4 frame = vec4(-80.0, -96.0, 0.5, 0.0);           // origin x, z, cell size
uniform vec2 cells = vec2(321.0, 417.0);
uniform float density = 0.02;          // at the ground
uniform float layer = 3.0;             // metres for the density to fall to 1/e
uniform vec3 albedo : source_color = vec3(0.92, 0.95, 1.0);
uniform vec3 emission : source_color = vec3(0.0);
uniform float drift = 0.0;             // advected offset (m), from the wind and the clock
uniform float banks = 0.55;            // 0 even .. 1 broken into banks
// the barrier (round 4, item 5; render3d/realm_mask.gd): R sanctum, G gate fog band, B band height / 8
uniform sampler2D realm : filter_linear, repeat_disable;
uniform vec4 realm_frame = vec4(-80.0, -96.0, 1.0, 0.0);
uniform vec2 realm_cells = vec2(161.0, 209.0);
uniform float realm_boost = 0.0;       // inside: the air holds this much more light (density x (1 + k))
uniform vec3 realm_albedo : source_color = vec3(1.0, 0.97, 0.9);
uniform float band_density = 0.0;      // a gate's mist, at the band's full value
uniform float band_swell = 0.0;        // 0 .. 1 she is deep in a gate's band: the mist rises and fills it

float hash2(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
float vnoise2(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), u.x), mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), u.x), u.y);
}

void fog() {
	vec3 wp = WORLD_POSITION;
	vec2 uv = ((wp.xz - frame.xy) / frame.z + 0.5) / cells;
	float g = texture(ground, uv).r;
	float above = wp.y - g;
	float d = density * exp(-max(above, 0.0) / max(layer, 0.1));
	vec2 q = (wp.xz + vec2(drift, drift * 0.35)) * 0.045;
	float n = vnoise2(q) * 0.65 + vnoise2(q * 2.3 + 7.1) * 0.35;
	d *= mix(1.0, 0.25 + 1.5 * n, banks);
	vec4 rm = texture(realm, ((wp.xz - realm_frame.xy) / realm_frame.z + 0.5) / realm_cells);
	// inside the barrier the air is fuller of light (thicker, warmer: a soft glow in the shafts)
	d *= 1.0 + realm_boost * rm.r;
	// a gate's mist (lead 16:00: not a lit box over her): low wisps along the ground, densest at the
	// ground and thinning within a metre or so, uneven, drifting between the stones and the cedars,
	// the band's edge broken by noise. When she is deep in the band (band_swell) it rises to the
	// band's height and fills up: the moment the place can change unseen.
	float bh = max(rm.b * 8.0, 0.5);
	vec2 fq = wp.xz * vec2(0.42, 0.9) + vec2(drift * 0.11, drift * 0.02);
	float wisp = vnoise2(fq) * 0.6 + vnoise2(fq * 2.3 + 3.1) * 0.4;
	vec2 eq = wp.xz * 0.55 + vec2(drift * 0.05, 0.0);
	// (the noise only breaks the band's own edge: nothing where the band's feather has not reached)
	float edge = smoothstep(0.22, 0.62, rm.g + (vnoise2(eq + 11.0) - 0.5) * 0.8 + (vnoise2(eq * 2.6 + 4.0) - 0.5) * 0.35)
			* smoothstep(0.0, 0.18, rm.g);
	float low = exp(-max(above, 0.0) / mix(0.8, bh * 0.55, band_swell));
	float streaks = smoothstep(0.42, 0.8, wisp);
	float body = mix(streaks * 2.4, 0.8 + 0.8 * wisp, band_swell);
	float curtain = edge * band_density * low * body * (1.0 + 3.0 * band_swell);
	DENSITY = above < -1.0 ? 0.0 : d + curtain;
	ALBEDO = mix(albedo, realm_albedo, rm.r * 0.6);
	EMISSION = emission;
}
