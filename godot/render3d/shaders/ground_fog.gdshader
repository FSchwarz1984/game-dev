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
	DENSITY = above < -1.0 ? 0.0 : d;
	ALBEDO = albedo;
	EMISSION = emission;
}
