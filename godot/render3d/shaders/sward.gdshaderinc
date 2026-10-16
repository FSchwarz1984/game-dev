// The sward's colour: one field for the grass ground and the grass that stands on it (round 5, renderer).
// Lead 2026-10-16 (decision-log G5R3-1, G5R3-2): round 3's colours of the grass, without round 3's
// blotches ("顏色深一塊淺一塊"). The grass ground (toon_terrain, mat 0) and the grass field's tufts
// (world3d/grass_field) both take their colour from here, so the root of a tuft is the colour of the
// ground it stands on. How dry the sward is (the palette's grass row toward its dry-grass row) and its
// macro tone change only over metres, as soft gradients: no whole-tone steps with stippled seams, no
// patches of a metre or two. The detail (single darker blades, glyphs, the tufts' lighter tips) stays
// in whole palette tones on top of it.
// Needs pixel_toon.gdshaderinc, and in the including shader `uniform sampler2D palette` (the terrain's
// palette: 8 tones x 16 rows, sRGB; row 0 grass, row 1 dry grass).

// How dry: 0 green .. 1 dry grass. dryness: the splat's m3.g (low-frequency already: baked steep south
// faces, thin soil by the rock; tools/world3d/w3terrain/materials.py); bias: the terrain's dry_bias.
// The noise only wanders the edge by a few metres; the ramp is wide, so the change takes metres.
float w3_sward_dry(vec2 xz, float dryness, float bias) {
	float d = dryness - bias + (w3_vnoise(xz / 9.0 + 7.0) - 0.5) * 0.16;
	return smoothstep(0.36, 0.64, d);
}

// The macro tone on the palette ramp (3.6 the middle), continuous: about +-0.6 of a tone, at most
// +-1.2, over 5-10 m (round 3 stepped whole tones over 2-4 m patches).
float w3_sward_tone(vec2 xz) {
	float n = w3_vnoise(xz / 10.0) * 0.7 + w3_vnoise(xz / 4.6 + 3.1) * 0.3;
	return 3.6 + (n - 0.5) * 2.4;
}

// The sward's colour (linear) at a dryness and a tone. A fractional tone is blended between the two
// nearest tones of the ramp (in sRGB, which is close to even steps of lightness).
vec3 w3_sward_col(float dry, float tone) {
	float t = clamp(tone, 0.0, 7.0);
	int t0 = int(floor(t));
	int t1 = min(t0 + 1, 7);
	float f = t - float(t0);
	vec3 g = mix(texelFetch(palette, ivec2(t0, 0), 0).rgb, texelFetch(palette, ivec2(t1, 0), 0).rgb, f);
	vec3 d = mix(texelFetch(palette, ivec2(t0, 1), 0).rgb, texelFetch(palette, ivec2(t1, 1), 0).rgb, f);
	return w3_srgb_to_linear(mix(g, d, dry));
}
