// The houses of the plain's villages and the town in the view from the lookout (W3Vista): at one to
// five kilometres a house is a few pixels, so each is drawn as a tiny sprite built in place in screen
// pixels around its foot on the pixel lattice (geometry this small would flicker as the view turns):
// the roof's rows on top (a lighter ridge row when there is room), the wall's row under it, and at
// night its windows lit (most houses, a few dark); the street lamps are single warm pixels. Then the
// same air as the land.
// Round 4 (G5R2-1 ⑩: a more prosperous, modern city): the same sprites draw the city's buildings
// (kind by COLOR.a): concrete blocks of several storeys (a flat roof, the facade's window grid,
// the side away from the sun in shade; at night most windows lit, warm or fluorescent), factory
// chimneys (red and white bands at the top, a blinking red light at night), and long halls (the
// station, the factories' saw-tooth sheds).
// Round 4, second pass (lead: "the city too small and faint: it must read at once as prosperous and
// modern"): high-rises round the station (kind 4: a glass curtain wall that holds the sky by day,
// lighter toward the top, mullions, its crown; at night its floors lit and a red light on top),
// blocks up to 48 px tall, panes that throw the sun back here and there by day (glints that move on
// as the sun moves), and the lights coming on with the dusk, window by window (city_lights: 0 day ..
// 1 night; vista3d.gd), so the dusk already has the first windows lit and the night a carpet.
// Instance: origin = the foot; INSTANCE_CUSTOM = (width m, depth m, height m, seed 0..1);
// COLOR = the roof's colour (sRGB); COLOR.a = kind: 1 house, 0.9 high-rise, 0.75 block, 0.5 chimney,
// 0.25 hall.
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform vec3 light_col = vec3(1.0);
uniform vec3 ambient_col = vec3(0.4);
uniform float night = 0.0;
uniform vec3 window_col : source_color = vec3(1.0, 0.72, 0.38);

varying vec3 v_wp;
varying flat vec4 v_cus;
varying flat vec4 v_col;
varying flat vec2 v_size;     // sprite width, height in px
varying flat float v_roof;    // roof rows
varying flat int v_kind;      // 0 house, 1 block, 2 chimney, 3 hall
varying vec2 v_px;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	float depth = length(o - eye);
	float ppm = v_ppr / max(length(o - eye), 1.0);      // pixels per metre there
	float wpx = clamp(floor(max(c.x, c.y) * ppm * 0.9 + 0.5), 1.0, 9.0);
	float rpx = clamp(floor(c.z * 0.55 * ppm + 0.5), 1.0, 4.0);
	float hpx = clamp(floor(c.z * 0.45 * ppm + 0.35), 0.0, 3.0);
	int kind = COLOR.a > 0.95 ? 0 : (COLOR.a > 0.85 ? 4 : (COLOR.a > 0.6 ? 1 : (COLOR.a > 0.35 ? 2 : 3)));
	if (kind == 1) {
		// a block: a flat roof row over storeys of facade
		wpx = clamp(floor(max(c.x, c.y) * ppm * 0.85 + 0.5), 1.0, 16.0);
		rpx = 1.0;
		hpx = clamp(floor(c.z * ppm + 0.5), 1.0, 48.0);
	} else if (kind == 4) {
		// a high-rise: never under two pixels wide (it must read as a tower, not a post)
		wpx = clamp(floor(max(c.x, c.y) * ppm * 0.85 + 0.5), 2.0, 16.0);
		rpx = 1.0;
		hpx = clamp(floor(c.z * ppm + 0.5), 3.0, 72.0);
	} else if (kind == 2) {
		// a chimney: one or two pixels wide, tall
		wpx = c.x * ppm > 1.4 ? 2.0 : 1.0;
		rpx = 0.0;
		hpx = clamp(floor(c.z * ppm + 0.5), 3.0, 40.0);
	} else if (kind == 3) {
		// a long hall: a wide roof (saw-toothed on a factory) over a low wall
		wpx = clamp(floor(max(c.x, c.y) * ppm * 0.9 + 0.5), 2.0, 24.0);
		rpx = clamp(floor(c.z * 0.5 * ppm + 0.5), 1.0, 3.0);
		hpx = clamp(floor(c.z * 0.5 * ppm + 0.5), 1.0, 3.0);
	}
	if (c.x < 0.0) {
		wpx = 1.0;
		rpx = 1.0;
		hpx = 0.0;
	}
	v_kind = kind;
	// the quad: centred on the foot horizontally, from the foot up, on the lattice of pixel corners
	vec2 foot = v_snap(v_px_of(o, eye));
	vec2 off = vec2(UV.x * wpx - floor(wpx * 0.5), (1.0 - UV.y) * (rpx + hpx));
	POSITION = v_clip(foot + off, depth, PROJECTION_MATRIX);
	v_wp = o;
	v_cus = c;
	v_col = COLOR;
	v_size = vec2(wpx, rpx + hpx);
	v_roof = rpx;
	v_px = vec2(UV.x * wpx, (1.0 - UV.y) * (rpx + hpx));
}

void fragment() {
	if (v_cus.x < 0.0) {
		// a street lamp: only its light, at night (a single warm pixel), lit with the dusk; one in two
		// (round 5: a scattering of warm lights, no city)
		if (city_lights < 0.15 + 0.5 * v_cus.w || fract(v_cus.w * 5.17) > 0.5 || v_drain(v_wp.xz, v_wp.y) > 0.9) discard;
		ALBEDO = w3_srgb_to_linear(window_col) * 3.4;
	} else {
	vec2 q = floor(v_px);
	float row = v_size.y - 1.0 - q.y;      // 0 at the top
	vec3 sd = normalize(w3_sun_dir);
	float day = clamp(sd.y * 3.0, 0.0, 1.0);
	vec3 col;
	if (v_kind > 0) {
		// the city: blocks, chimneys, halls
		bool dark_drain = v_drain(v_wp.xz, v_wp.y) > 0.9;
		vec3 base = w3_srgb_to_linear(v_col.rgb);
		// the face toward the sun lighter, the other in shade (a sprite's two halves)
		bool sunny = (sd.x > 0.0) == (q.x >= floor(v_size.x * 0.5));
		float side = v_size.x > 2.5 ? (sunny ? 1.0 : 0.72) : 0.88;
		vec3 lit = ambient_col + light_col * 0.55 * day * side;
		bool lamp = false;
		vec3 lamp_c = w3_srgb_to_linear(window_col);
		// a pane that throws the sun back (by day, on the sunny half, now and then; the set moves on
		// as the sun moves)
		float sun_step = floor(atan(sd.x, sd.z) * 18.0);
		float gl = w3_hash(vec2(v_cus.w * 733.0 + q.x * 1.7, row * 2.3 + sun_step));
		// (the sun's own colour, a little over 1: a glint is the sun itself, it may bloom)
		vec3 glint = w3_sun / max(max(w3_sun.r, w3_sun.g), 0.01) * 1.3;
		if (v_kind == 1) {
			if (row < v_roof) {
				// flat roofs: pale concrete on some, dark tar on others
				float rk = fract(v_cus.w * 13.7) > 0.45 ? 1.12 : 0.72;
				col = base * rk * (ambient_col + light_col * 0.7 * day);
			} else {
				// storeys: a row of windows on every other pixel row, a pane on every other column
				bool pane = mod(row - v_roof, 2.0) < 1.0 && (v_size.x < 2.5 || mod(q.x, 2.0) < 1.0);
				col = base * lit;
				// (the glass holds the sky)
				if (pane) col = mix(col, mix(w3_srgb_to_linear(vec3(0.34, 0.42, 0.52)) * lit, haze_col * 0.9, 0.3), 0.55);
				if (pane && sunny && day > 0.2 && gl > 0.95) col = glint;
				// at night most panes lit: homes warm, offices a cooler white; they come on with the dusk
				float h = w3_hash(vec2(v_cus.w * 911.0 + q.x * 3.1, row * 1.7));
				lamp = pane && h > 1.0 - 0.62 * city_lights && !dark_drain;
				if (fract(v_cus.w * 5.3) > 0.55) lamp_c = w3_srgb_to_linear(vec3(0.86, 0.92, 1.0));
			}
		} else if (v_kind == 4) {
			// a high-rise: its crown (a band of concrete, a red light on top at night), then the
			// curtain wall: glass holding the sky, lighter toward the top, the sunny half lighter,
			// mullions on every other column, a floor line every third row
			if (row < v_roof) {
				col = base * 1.08 * (ambient_col + light_col * 0.7 * day);
				lamp = city_lights > 0.4 && q.x == floor(v_size.x * 0.5) && fract(w3_time * 0.5 + v_cus.w * 3.0) < 0.5 && !dark_drain;
				lamp_c = w3_srgb_to_linear(vec3(1.0, 0.25, 0.18));
			} else {
				float up = 1.0 - (row - v_roof) / max(v_size.y - v_roof, 1.0);
				vec3 glass = mix(w3_srgb_to_linear(vec3(0.30, 0.38, 0.48)), haze_col, 0.25 + 0.4 * up);
				col = mix(base * lit, glass * mix(0.85, 1.0, sunny ? 1.0 : 0.0) * (0.75 + 0.45 * day), 0.7);
				bool mullion = v_size.x > 2.5 && mod(q.x, 2.0) > 0.5;
				bool floor_line = mod(row - v_roof, 3.0) > 1.5;
				if (mullion || floor_line) col *= 0.82;
				if (!mullion && sunny && day > 0.2 && gl > 0.88) col = glint;
				// (lit by floors and by offices along them, not one pane in two: runs of three columns)
				float h = w3_hash(vec2(v_cus.w * 577.0 + floor(q.x / 3.0) * 2.3, row * 1.3));
				lamp = !floor_line && h > 1.0 - 0.72 * city_lights && !dark_drain;
				lamp_c = w3_srgb_to_linear(h > 0.8 ? vec3(1.0, 0.86, 0.6) : vec3(0.84, 0.92, 1.0));
			}
		} else if (v_kind == 2) {
			// bands of red and white at the top, the stack below
			bool band = row < 4.0 && mod(row, 2.0) < 1.0;
			col = (band ? w3_srgb_to_linear(vec3(0.72, 0.28, 0.22)) : base) * lit;
			// the aviation light at the top, blinking
			lamp = city_lights > 0.4 && row < 0.5 && fract(w3_time * 0.6 + v_cus.w * 3.0) < 0.5 && !dark_drain;
			lamp_c = w3_srgb_to_linear(vec3(1.0, 0.25, 0.18));
		} else {
			if (row < v_roof) {
				// the station's long roof, or a factory's saw-tooth (light and dark by turns)
				float k = fract(v_cus.w * 3.7) > 0.5 && mod(q.x, 3.0) < 1.0 ? 0.7 : 1.05;
				col = base * k * (ambient_col + light_col * 0.7 * day);
			} else {
				col = w3_srgb_to_linear(vec3(0.74, 0.72, 0.68)) * lit;
				float h = w3_hash(vec2(v_cus.w * 617.0, q.x));
				lamp = h > 1.0 - 0.65 * city_lights && !dark_drain;
				lamp_c = w3_srgb_to_linear(vec3(0.92, 0.95, 1.0));
			}
		}
		vec3 cc = v_air(col, v_wp, eye, FRAGCOORD.xy);
		if (v_past(v_wp, eye, FRAGCOORD.xy)) cc = row < v_roof ? v_ink() : v_emboss(vec3(0.0, 1.0, 0.0), v_wp, eye);
		ALBEDO = lamp ? mix(cc, lamp_c * 3.0, 0.85) : cc;
	} else {
	vec3 h_alb = w3_srgb_to_linear(v_col.rgb);   // the block's colour in the 遠化
	int h_plate = V_EARTH;
	if (row < v_roof) {
		vec3 roof = w3_srgb_to_linear(v_col.rgb);
		// the ridge row catches the light when the roof has room for it
		float k = (row < 0.5 && v_roof > 1.5) ? 1.25 : 1.0;
		// (the end that faces the sun a little lighter)
		if (q.x < 0.5 && v_size.x > 2.5 && sd.x < 0.0) k *= 1.1;
		if (q.x > v_size.x - 1.5 && v_size.x > 2.5 && sd.x > 0.0) k *= 1.1;
		col = roof * k * (ambient_col + light_col * 0.7 * day);
	} else {
		// (round 5: dark wooden walls on most, white plaster on some: the storehouses, the town's
		// fronts; a white wall under a dark roof is what reads as a house from afar)
		bool plaster = fract(v_cus.w * 3.73) < 0.55;
		vec3 wall = plaster ? w3_srgb_to_linear(vec3(0.88, 0.86, 0.80)) : w3_srgb_to_linear(vec3(0.52, 0.42, 0.31));
		col = wall * (ambient_col + light_col * 0.45 * day);
		h_alb = wall;
		h_plate = plaster ? V_PAPER : V_EARTH;
	}
	// windows at night: a scattering of houses lit (round 5, the lead: "夜里村子只有零星的暖灯"; a
	// pane or two; a far house that is a single pixel shows only its light)
	// (past the 遠化 front a house has lost its light with everything else)
	bool lit_house = fract(v_cus.w * 7.31) > 1.0 - 0.45 * city_lights && v_drain(v_wp.xz, v_wp.y) < 0.9;
	float h = w3_hash(vec2(v_cus.w * 913.0, q.x));
	bool win = lit_house && ((row >= v_roof && (h > 0.45 || v_size.x < 2.5)) || (v_size.y < 1.5 && h > 0.3));
	vec3 c = v_air(col, v_wp, eye, FRAGCOORD.xy);
	// (in the 遠化 a house prints flat: its roof and a wooden wall from the earths, a plaster wall is
	// the paper; when the earths are gone its roof is the key block's line)
	c = v_print(c, v_flat(h_plate, h_alb), h_plate, vec3(0.0, 1.0, 0.0), v_wp, eye, FRAGCOORD.xy);
	if (row < v_roof && v_past(v_wp, eye, FRAGCOORD.xy) && v_plate_on(V_EARTH, v_wp.xz, length(v_wp - eye), FRAGCOORD.xy) < 0.5) c = v_ink();
	// (a lit window shines through the air)
	ALBEDO = win ? mix(c, w3_srgb_to_linear(window_col) * 3.2, 0.88) : c;
	}
	}
}
