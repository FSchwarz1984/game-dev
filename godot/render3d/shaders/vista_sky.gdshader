// The sky of the view from the lookout (W3Vista). Round 4 (G5R2-1: Shinkai's skies, soft light):
// every tone is continuous (the viewport is HDR and the display dithers the 8-bit output with blue
// noise fixed to the view's lattice, so a slow gradient neither bands nor crawls): a deep clear blue
// at the zenith opening to a pale, humid horizon; the sun with a soft wide glow (only the disc goes
// above 1, so only it blooms); the moon and the stars at night; and two kinds of cloud with soft,
// translucent edges: banks of cumulus low over the horizon (flat bases, heaped tops in lobes, lit on
// the sun's side with a bright rim where the light comes through, a cool blue-grey belly), and long
// thin streaks higher up (lit along their upper edges). By day they are white and blue-grey, at dusk
// lit from below in warm colours, at night dark with pale moonlit rims.
shader_type sky;

uniform vec3 zenith : source_color = vec3(0.3, 0.45, 0.75);   // linear
uniform vec3 horizon : source_color = vec3(0.7, 0.76, 0.82);       // toward the sun
uniform vec3 horizon_away : source_color = vec3(0.7, 0.76, 0.82);  // away from it (round 4: cooler; rose at dusk)
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
	// the gradient, continuous: the pale humid horizon opening into the clear blue overhead
	float t = clamp(el / 1.1, 0.0, 1.0);
	t = pow(t, 0.55);
	vec3 s = normalize(sun_dir);
	// (the horizon warm toward the sun, cooler away from it: the far land's air takes the same,
	// vista_common v_haze)
	float tw = dot(normalize(vec2(d.x, d.z) + 1e-4), normalize(vec2(s.x, s.z) + 1e-4));
	vec3 hz = mix(horizon_away, horizon, smoothstep(-0.6, 0.8, tw));
	vec3 col = mix(hz, zenith, t);
	// the sun's glow: a soft wide halo and a brighter core around the disc
	float cs = dot(d, s);
	float glow = smoothstep(0.86, 1.0, cs) * (1.0 - night * 0.7);
	float halo = pow(clamp(cs * 0.5 + 0.5, 0.0, 1.0), 6.0) * (1.0 - night * 0.8);
	col = mix(col, sun_col * 0.95, glow * glow * 0.55 + halo * 0.22);
	// a pale band of haze along the horizon
	float mb = 1.0 - smoothstep(0.0, 0.035, abs(el + 0.004));
	col = mix(col, mist_col, mb * 0.32);
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
		// a soft fringe: the top thins out over a few pixels, the base over one or two
		float px = 1.0 / px_per_rad;
		float edge = smoothstep(0.0, 3.5 * px, top - el) * smoothstep(-0.5 * px, 1.5 * px, el - base);
		if (bank > 0.05 && edge > 0.0) {
			float h = clamp((el - base) / max(top - base, 1e-3), 0.0, 1.0);
			// the lobes: round heads inside the bank, softly parted
			vec2 q = vec2(u * 9.0, el * 120.0);
			float inner = fbm(q * 0.5 + 3.0);
			float seam = abs(fract(inner * 3.0) - 0.5);
			// lit from above and from the sun's side, the lobes only a gentle swell (no mottling)
			float l = 0.46 + h * 0.5 + toward_sun * 0.2 + (inner - 0.5) * 0.12;
			vec3 cc = mix(shade_c, lit_c, clamp(l, 0.0, 1.0));
			cc = mix(cc, belly_c, 1.0 - smoothstep(0.04, 0.32, h));
			cc = mix(cc, shade_c, (1.0 - smoothstep(0.02, 0.09, seam)) * smoothstep(0.2, 0.4, h) * 0.35);
			// the rim toward the sun: the light comes through the thin top
			float rim = (1.0 - smoothstep(0.0, 2.5 * px, top - el)) * smoothstep(-0.3, 0.4, toward_sun);
			cc = mix(cc, lit_c * 1.08, rim * 0.75);
			// the thin fringe lets the sky through
			col = mix(col, cc, edge * (0.55 + 0.45 * smoothstep(0.0, 0.25, h)));
		}
	}
	// ---- long thin streaks higher up
	{
		vec2 q = vec2(az * 1.6 + time * 0.003, el * 14.0);
		float n = fbm(vec2(q.x * 1.2, q.y + fbm(vec2(q.x * 0.6, 4.0)) * 1.4));
		float band = smoothstep(0.07, 0.16, el) * (1.0 - smoothstep(0.6, 0.85, el));
		float th = 0.66 - band * 0.06;
		float a = band * smoothstep(th, th + 0.09, n);
		if (a > 0.0) {
			// lit along the upper edge, darker underneath, thin and wispy at the ends
			float up = fbm(vec2(q.x * 1.2, q.y + 0.08 + fbm(vec2(q.x * 0.6, 4.0)) * 1.4));
			float lv = 0.33 + 0.34 * smoothstep(th - 0.05, th + 0.05, up) + 0.33 * smoothstep(th + 0.05, th + 0.15, n);
			lv = clamp(lv + toward_sun * 0.2, 0.0, 1.0);
			vec3 cc = mix(shade_c, lit_c, lv);
			col = mix(col, cc, 0.85 * a);
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
		} else if (ang < 0.06) {
			float mg = 1.0 - ang / 0.06;
			col = mix(col, vec3(0.5, 0.55, 0.7), mg * mg * 0.4);
		}
	}
	COLOR = col;
}
