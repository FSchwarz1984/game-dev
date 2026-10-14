// The painted sky of the vista (src/vista/sky.js paintSky + tod.js skyAt), shared by the sky layer and
// the stars (which are mixed over it in sRGB like the JS canvas). Per row a colour by elevation, the
// warm west in column bands, quantised to steps of 2 like the JS.

uniform vec3 sky_z;
uniform vec3 sky_up;
uniform vec3 sky_lo;
uniform vec3 sky_ho;
uniform vec3 sky_glow;
uniform float glow_amt;
uniform float horizon;        // canvas row of the horizon
uniform float sky_s = 140.8;  // elevation scale (rows from the horizon to the top of the painted sky)
uniform float ref_x0;         // canvas x of the reference frame's left edge
uniform float ref_w = 480.0;
uniform float bands = 24.0;

vec3 sky_at(float sa_e, float sa_u) {
	sa_e = clamp(sa_e, 0.0, 1.0);
	vec3 sa_c;
	if (sa_e < 0.16) sa_c = mix(sky_ho, sky_lo, smoothj(0.0, 0.16, sa_e));
	else if (sa_e < 0.5) sa_c = mix(sky_lo, sky_up, smoothj(0.16, 0.5, sa_e));
	else sa_c = mix(sky_up, sky_z, smoothj(0.5, 1.0, sa_e));
	float sa_g = glow_amt * pow(clamp(sa_u, 0.0, 1.0), 2.2) * pow(1.0 - clamp(sa_e / 0.55, 0.0, 1.0), 1.6);
	if (sa_g > 0.0) sa_c = mix(sa_c, sky_glow, clamp(sa_g, 0.0, 1.0) * 0.85);
	return sa_c;
}

// the sky's colour (sRGB 0..255) at a canvas pixel
vec3 sky_px(vec2 sp_p) {
	float sp_e = (horizon - sp_p.y) / sky_s;
	float sp_k = roundj((sp_p.x - ref_x0) / (ref_w - 1.0) * bands);
	return clamp(floor(sky_at(sp_e, sp_k / bands) * 0.5 + 0.5) * 2.0, 0.0, 255.0);
}
