// The sky of the view from the lookout (W3Vista), painted rather than dithered: a gradient from the
// horizon to the zenith in whole steps (each seam broken by a scatter on cells fixed to the sky, so a
// pan carries it along, never an ordered halftone), the sun with stepped rings of glow (only the disc
// goes above 1, so only it blooms), the moon and the stars at night; and two kinds of cloud in flat
// tones with clean edges: banks of cumulus low over the horizon (flat bases, heaped tops in lobes,
// lit on the sun's side, a darker belly, the seams between the lobes drawn), and long thin streaks
// higher up (lit along their upper edges). By day they are white and blue-grey, at dusk lit from below
// in warm colours, at night dark with pale moonlit rims.
shader_type sky;

uniform vec3 zenith : source_color = vec3(0.3, 0.45, 0.75);   // linear
uniform vec3 horizon : source_color = vec3(0.7, 0.76, 0.82);
uniform vec3 mist_col : source_color = vec3(0.8, 0.8, 0.84);
uniform vec3 sun_dir = vec3(0.0, 0.5, -0.8);
uniform vec3 sun_col : source_color = vec3(1.0, 0.9, 0.7);
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.97, 0.92);
uniform vec3 cloud_shade : source_color = vec3(0.6, 0.65, 0.75);
uniform float night = 0.0;
uniform float dusk = 0.0;               // 0 .. 1 the golden hour (clouds lit from below)
uniform float px_per_rad = 380.0;      // native pixels per radian at the camera's zoom
uniform float time = 0.0;
// the vista's projection (vista_common.gdshaderinc): each screen pixel a fixed step of azimuth and
// elevation from the view's yaw and pitch, so the sky turns with the land by whole pixels
uniform vec4 view_ang = vec4(3.1416, -0.2, 240.0, 135.0);   // yaw, pitch (rad), half size (px)

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
float fbm(vec2 p) {
	return vnoise(p) * 0.55 + vnoise(p * 2.03 + 7.1) * 0.28 + vnoise(p * 4.1 + 3.3) * 0.17;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	if (!AT_CUBEMAP_PASS) {
		vec2 px = vec2(SCREEN_UV.x - 0.5, 0.5 - SCREEN_UV.y) * view_ang.zw * 2.0;
		float a = view_ang.x + px.x / px_per_rad;
		float e = view_ang.y + px.y / px_per_rad;
		d = vec3(sin(a) * cos(e), sin(e), -cos(a) * cos(e));
	}
	float el = asin(clamp(d.y, -1.0, 1.0));
	// azimuth measured so that its one seam (where it wraps) lies to the north-west, behind both of
	// her views (out: bearings 95 to 292; home: -12 to 60)
	float b = atan(d.x, -d.z);
	float az = mod(b - 2.443 + 3.14159265, 6.2831853) - 3.14159265;
	// sky-fixed pixel cells: the seams' scatter turns with the sky
	vec2 cell = floor(vec2(az, el) * px_per_rad);
	float dz = (hash(cell * 1.37 + 0.5) * 0.7 + vnoise(cell / 1.7) * 0.3) - 0.5;
	// gradient in whole steps
	float t = clamp(el / 1.1, 0.0, 1.0);
	t = pow(t, 0.55);
	float tq = floor(t * 9.0 + 0.5 + dz * 0.5) / 9.0;
	vec3 col = mix(horizon, zenith, tq);
	// the sun's glow: rings in steps
	vec3 s = normalize(sun_dir);
	float cs = dot(d, s);
	float glow = smoothstep(0.86, 1.0, cs) * (1.0 - night * 0.7);
	float gq = floor(glow * 5.0 + 0.5 + dz * 0.5) / 5.0;
	col = mix(col, sun_col * 0.95, gq * 0.55);
	// a thin pale band along the horizon
	float mb = 1.0 - smoothstep(0.0, 0.03, abs(el + 0.004));
	col = mix(col, mist_col, floor(mb * 3.0 + 0.5 + dz * 0.5) / 3.0 * 0.3);
	vec2 sh = normalize(vec2(s.x, s.z) + 1e-4);
	float toward_sun = dot(normalize(vec2(d.x, d.z) + 1e-4), sh);      // -1 away .. 1 toward
	vec3 lit_c = cloud_lit;
	vec3 shade_c = cloud_shade;
	vec3 belly_c = mix(cloud_shade * 0.82, sun_col * 0.75, dusk * 0.6);
	// ---- banks of cumulus low over the horizon
	{
		float u = az * 3.2 + time * 0.0015;
		float base = 0.11 + vnoise(vec2(u * 0.35, 3.0)) * 0.05;            // their flat bases rise and fall
		// (above the far ranges, with sky between: white heaps sitting on the peaks read as snow)
		float bank = smoothstep(0.42, 0.62, vnoise(vec2(u * 0.55, 9.0)));  // where a bank stands at all
		float lobes = fbm(vec2(u * 2.4, 1.7));
		float top = base + bank * (0.03 + lobes * 0.075);
		if (bank > 0.05 && el > base && el < top) {
			float h = (el - base) / max(top - base, 1e-3);
			// the lobes: round heads inside the bank, their seams a darker line
			vec2 q = vec2(u * 9.0, el * 120.0);
			float inner = fbm(q * 0.5 + 3.0);
			float seam = abs(fract(inner * 3.0) - 0.5);
			float l = 0.42 + h * 0.45 + toward_sun * 0.22 + (inner - 0.5) * 0.3;
			float lv = floor(l * 3.0 + 0.5 + dz * 0.4) / 3.0;
			vec3 cc = mix(shade_c, lit_c, clamp(lv, 0.0, 1.0));
			if (h < 0.18 + dz * 0.1) cc = belly_c;
			if (seam < 0.05 && h > 0.25) cc = mix(cc, shade_c, 0.6);
			// the rim that faces the sun catches the light
			if (top - el < 1.2 / px_per_rad && toward_sun > -0.2) cc = mix(cc, lit_c * 1.08, 0.7);
			col = cc;
		}
	}
	// ---- long thin streaks higher up
	{
		vec2 q = vec2(az * 1.6 + time * 0.003, el * 14.0);
		float n = fbm(vec2(q.x * 1.2, q.y + fbm(vec2(q.x * 0.6, 4.0)) * 1.4));
		float band = smoothstep(0.07, 0.16, el) * (1.0 - smoothstep(0.6, 0.85, el));
		float th = 0.66 - band * 0.06;
		if (band > 0.0 && n > th) {
			// lit along the upper edge, darker underneath
			float up = fbm(vec2(q.x * 1.2, q.y + 0.08 + fbm(vec2(q.x * 0.6, 4.0)) * 1.4));
			float lv = up > th ? 0.67 : 0.33;
			if (n > th + 0.1) lv += 0.33;
			lv = clamp(lv + toward_sun * 0.2 + dz * 0.1, 0.0, 1.0);
			vec3 cc = mix(shade_c, lit_c, floor(lv * 3.0 + 0.5) / 3.0);
			col = mix(col, cc, 0.85);
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
		} else if (ang < 0.05) {
			col = mix(col, vec3(0.5, 0.55, 0.7), floor((1.0 - ang / 0.05) * 3.0 + 0.5 + dz * 0.4) / 3.0 * 0.35);
		}
	}
	COLOR = col;
}
