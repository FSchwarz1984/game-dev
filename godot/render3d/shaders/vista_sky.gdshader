// The sky of the view from the lookout (W3Vista): a gradient from the horizon to the zenith in whole
// steps (dithered on cells fixed to the sky, so a pan carries the pattern with it), the sun with a
// stepped glow (only the disc goes above 1, so only it blooms), the moon and stars at night, a few
// banks of cloud low over the land, lit from the sun's side, and the pale band of the 遠化 mist on
// the horizon all around.
shader_type sky;

uniform vec3 zenith : source_color = vec3(0.3, 0.45, 0.75);   // linear
uniform vec3 horizon : source_color = vec3(0.7, 0.76, 0.82);
uniform vec3 mist_col : source_color = vec3(0.8, 0.8, 0.84);
uniform vec3 sun_dir = vec3(0.0, 0.5, -0.8);
uniform vec3 sun_col : source_color = vec3(1.0, 0.9, 0.7);
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.97, 0.92);
uniform vec3 cloud_shade : source_color = vec3(0.6, 0.65, 0.75);
uniform float night = 0.0;
uniform float px_per_rad = 380.0;      // native pixels per radian at the camera's zoom
uniform float time = 0.0;

float hash(vec2 p) {
	p = fract(p * vec2(0.1031, 0.1030));
	p += dot(p, p.yx + 33.33);
	return fract((p.x + p.y) * p.x);
}
float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float hash3(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}
float vnoise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), u.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), u.x), u.y);
	float b = mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), u.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), u.x), u.y);
	return mix(a, b, u.z);
}
float bayer4(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	int M[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(M[q.y * 4 + q.x]) + 0.5) / 16.0;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float el = asin(clamp(d.y, -1.0, 1.0));
	// azimuth from the north-north-west, so the one seam of the sky-fixed cells lies behind the
	// lookout, where the view rarely turns
	float az = atan(d.x * 0.88 + d.z * 0.47, -d.z * 0.88 + d.x * 0.47);
	// sky-fixed pixel cells: the dither turns with the sky
	vec2 cell = floor(vec2(az, el) * px_per_rad);
	float dz = bayer4(cell) - 0.5;
	// gradient in whole steps
	float t = clamp(el / 1.1, 0.0, 1.0);
	t = pow(t, 0.55);
	float tq = floor(t * 9.0 + 0.5 + dz * 0.9) / 9.0;
	vec3 col = mix(horizon, zenith, tq);
	// the sun's glow: rings in steps
	vec3 s = normalize(sun_dir);
	float cs = dot(d, s);
	float glow = smoothstep(0.86, 1.0, cs) * (1.0 - night * 0.7);
	float gq = floor(glow * 5.0 + 0.5 + dz * 0.9) / 5.0;
	col = mix(col, sun_col * 0.95, gq * 0.55);
	// the band of the 遠化 mist all around the horizon
	float mb = 1.0 - smoothstep(0.0, 0.035, abs(el + 0.005));
	float mq = floor(mb * 4.0 + 0.5 + dz * 0.9) / 4.0;
	col = mix(col, mist_col, mq * 0.55);
	// clouds: cumulus banks low over the land, flat underneath, drifting; 3D noise on the view
	// direction (no seam anywhere)
	if (el > 0.005 && el < 0.34) {
		vec3 q = vec3(d.x * 5.5 + time * 0.002, el * 22.0, d.z * 5.5);
		float c = vnoise3(q) * 0.55 + vnoise3(q * 2.2 + 4.0) * 0.3 + vnoise3(q * 4.7 + 9.0) * 0.15;
		float base = 0.035 + vnoise3(vec3(d.x, 0.0, d.z) * 3.0) * 0.06;    // the flat base rises and falls
		float top = base + 0.06 + c * 0.16;
		float inside = step(base, el) * step(el, top) * step(0.5, c);
		if (inside > 0.5) {
			float lit = dot(normalize(vec3(d.x, 0.0, d.z)), normalize(vec3(s.x, 0.0, s.z) + 1e-4)) * 0.5 + 0.5;
			float up = (el - base) / max(top - base, 1e-3);
			float l = lit * 0.55 + up * 0.6 + (c - 0.5) * 0.4;
			vec3 cc = mix(cloud_shade, cloud_lit, clamp(floor(l * 3.0 + 0.5 + dz * 0.6) / 3.0, 0.0, 1.0));
			col = cc;
		}
	}
	// stars at night
	if (night > 0.3 && el > 0.04) {
		float h = hash(cell + 17.0);
		float tw = 0.6 + 0.4 * sin(time * 2.0 + h * 40.0);
		if (h > 0.9965) col = mix(col, vec3(0.95, 0.95, 1.0) * (0.7 + 0.6 * h) * tw, night);
	}
	// the sun's disc, or the moon at night
	float ang = acos(clamp(cs, -1.0, 1.0));
	if (night < 0.5) {
		if (ang < 0.016) col = sun_col * 2.6;
	} else {
		if (ang < 0.013) {
			// the moon: pale, with two darker seas
			vec2 m = vec2(dot(d, normalize(cross(s, vec3(0.0, 1.0, 0.0)))), d.y - s.y) / 0.013;
			col = vec3(0.92, 0.93, 0.86) * 1.25;
			if (length(m - vec2(0.25, 0.2)) < 0.35 || length(m - vec2(-0.3, -0.25)) < 0.25) col *= 0.82;
		}
	}
	COLOR = col;
}
