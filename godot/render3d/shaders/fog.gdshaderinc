// Atmosphere shared by the screen post (opaque world) and the transparent materials drawn after it
// (water, particles, glows): valley mist that lies by absolute height and drifts, and a haze over
// whatever lies far below the camera's focus (the long view down from the lookout).
global uniform vec3 w3_fog_col;     // haze colour (linear)
global uniform vec4 w3_mist;        // x: mist top (m), y: mist bottom (m, densest), z: max density 0..1, w: drift speed
global uniform vec4 w3_haze;        // x: focus height (m), y: depth below focus where haze starts, z: depth where it is full, w: max 0..1

float w3_fog_amount(vec3 wp, vec2 cell) {
	float m = smoothstep(w3_mist.x, w3_mist.y, wp.y) * w3_mist.z;
	if (m > 0.0) {
		// banks of mist drifting east, broken up
		vec2 q = wp.xz * 0.045 + vec2(w3_time * w3_mist.w, w3_time * w3_mist.w * 0.3);
		float n = w3_fbm(q) * 0.7 + w3_fbm(q * 2.3 + 4.1) * 0.3;
		m *= smoothstep(0.25, 0.75, n);
	}
	float below = w3_haze.x - wp.y;
	float h = smoothstep(w3_haze.y, w3_haze.z, below) * w3_haze.w;
	// continuous (round 4: no steps; the buffers are float, so a slow gradient does not band)
	return clamp(max(m, h), 0.0, 1.0);
}
vec3 w3_apply_fog(vec3 col, vec3 wp, vec2 cell) {
	return mix(col, w3_fog_col, w3_fog_amount(wp, cell));
}
