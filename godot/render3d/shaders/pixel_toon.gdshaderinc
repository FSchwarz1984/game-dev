// pixel_toon.gdshaderinc — the shared contract of the 3D pixel renderer (docs/knowledge/21-3d-pixel-render.md).
// Every 3D material of the world includes this file. It holds:
//   * the view numbers (pixels per metre, camera pitch, lean) as shader globals,
//   * the screen-texel lattice ("ptex"): the native pixel a world point lands on, independent of the
//     camera (the camera only ever moves by whole texels), so procedural detail and dithering stay
//     glued to the world and never crawl,
//   * lean-back for upright objects (verticals read at 20 px per metre, A Link Between Worlds style),
//   * whole-pixel wind sway, the canopy cut-away around her,
//   * the toon light model (banded sun, quantised lanterns, hemisphere ambient with warm/cool shift).
// Axes (Godot): X east, Y up, Z south (toward the camera). Units: metres. The camera looks north (-Z)
// and down at the pitch held in w3_view. Colours are linear unless a name says srgb.
//
// Declared in godot/project.godot [shader_globals]; the time-of-day controller
// (render3d/world_env.gd) writes them every frame.

global uniform vec4 w3_view;        // x: native px per metre (20), y: sin(pitch), z: cos(pitch), w: lean k = tan(pitch/2)
global uniform float w3_time;       // world clock, seconds (animation; deterministic in captures)
global uniform vec3 w3_sun_dir;     // unit vector toward the sun (or moon at night), world space
global uniform vec3 w3_sun;         // sun colour * intensity (linear), for effects outside light()
global uniform vec3 w3_sky;         // ambient from the sky (cool), linear
global uniform vec3 w3_ground;      // ambient bounced from the ground (warm, dark), linear
global uniform vec3 w3_shade_tint;  // hue shift of surfaces in shadow (cool), multiplier
global uniform vec3 w3_lit_tint;    // hue shift of surfaces in sunlight (warm), multiplier
global uniform vec4 w3_wind;        // xy: wind direction (x east, y south), z: strength 0..2, w: gust 0..1
global uniform float w3_wet;        // rain wetness 0..1
global uniform vec4 w3_player;      // xyz: her chest (world), w: cut-away radius in native px (0 = off)
global uniform float w3_night;      // 0 day .. 1 night

const float W3_PI = 3.14159265;

// ------------------------------------------------------------------------------------------------
// hashing and noise (all keyed on integer lattices so results are stable)
float w3_hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
float w3_hash3(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}
float w3_vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(w3_hash(i), w3_hash(i + vec2(1.0, 0.0)), u.x),
	           mix(w3_hash(i + vec2(0.0, 1.0)), w3_hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float w3_fbm(vec2 p) {
	return w3_vnoise(p) * 0.55 + w3_vnoise(p * 2.07 + 7.3) * 0.3 + w3_vnoise(p * 4.3 + 1.7) * 0.15;
}
// 4x4 ordered dither threshold in (0,1), keyed on a texel cell (never on FRAGCOORD: that would crawl)
float w3_bayer4(vec2 cell) {
	ivec2 i = ivec2(mod(cell, 4.0));
	int k = i.x + i.y * 4;
	float m[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
	return (m[k] + 0.5) / 16.0;
}

// ------------------------------------------------------------------------------------------------
// the screen-texel lattice
// Native pixel coordinates of a (rendered, i.e. already leaned) world point: x to the east, y up the
// screen. The camera is snapped so that pixel centres sit at k + 0.5, hence floor() is the texel cell.
vec2 w3_screen(vec3 wp) {
	return vec2(wp.x, wp.y * w3_view.z - wp.z * w3_view.y) * w3_view.x;
}
vec2 w3_ptex(vec3 wp) {
	return floor(w3_screen(wp));
}
// camera axes in world space
vec3 w3_cam_right() { return vec3(1.0, 0.0, 0.0); }
vec3 w3_cam_up() { return vec3(0.0, w3_view.z, -w3_view.y); }
vec3 w3_cam_back() { return vec3(0.0, w3_view.y, w3_view.z); }   // from the scene toward the camera
// world displacement that moves a point by (dx, dy) native px on screen (y up), without changing depth
vec3 w3_px_to_world(vec2 d) {
	return w3_cam_right() * (d.x / w3_view.x) + w3_cam_up() * (d.y / w3_view.x);
}
// displacement that moves an anchor onto the texel corner lattice (integer ptex): cards and painted
// details then map texel-for-pixel
vec3 w3_snap(vec3 anchor_wp) {
	vec2 s = w3_screen(anchor_wp);
	return w3_px_to_world(round(s) - s);
}

// ------------------------------------------------------------------------------------------------
// lean-back: upright objects are sheared north by k * height above their base, so that a vertical
// metre reads 20 px tall like a horizontal one (k = tan(pitch / 2)). The terrain, water, paths,
// steps and retaining walls do not lean. Shadows are cast by the upright geometry (the shadow pass
// skips the lean), and lighting uses the upright normals.
vec3 w3_lean(vec3 wp, float base_y, float amount) {
	wp.z -= w3_view.w * (wp.y - base_y) * amount;
	return wp;
}

// ------------------------------------------------------------------------------------------------
// wind: a sway group (all vertices sharing one anchor) moves rigidly by whole native pixels, so
// textures never swim and the image never shimmers. flex 0 = rigid (trunks), 1 = free tips.
vec2 w3_wind_px(vec3 anchor, float flex, float amp_px) {
	if (flex <= 0.0) return vec2(0.0);
	float ph = anchor.x * 0.37 + anchor.z * 0.23 + anchor.y * 0.11;
	float t = w3_time;
	float s = sin(t * 1.7 + ph) * 0.6 + sin(t * 2.9 + ph * 1.7) * 0.4;
	float str = w3_wind.z;
	float gust = w3_wind.w * (0.5 + 0.5 * sin(t * 0.43 + ph * 0.3));
	float dx = (s * (0.35 + 0.45 * str) + w3_wind.x * (str * 0.6 + gust)) * amp_px * flex;
	float dy = -abs(s) * 0.25 * amp_px * flex * str;
	return vec2(round(dx), round(dy));
}

// ------------------------------------------------------------------------------------------------
// the canopy / roof cut-away around her: true when this fragment hides her and should be stippled out
bool w3_cutaway_r(vec3 wp, vec2 cell, float scale) {
	if (w3_player.w <= 0.0) return false;
	vec3 d = wp - w3_player.xyz;
	float toward = dot(d, w3_cam_back());           // > 0: this surface is between her and the camera
	if (toward < 0.3) return false;
	vec2 ds = w3_screen(wp) - w3_screen(w3_player.xyz);
	float r = length(ds * vec2(1.0, 0.8));
	float R = w3_player.w * scale;
	float ring = min(12.0, R * 0.35);                 // a dithered edge, clear inside
	float k = clamp((R - r) / ring, 0.0, 1.0) * smoothstep(0.3, 1.2, toward);
	return w3_bayer4(cell) < k;
}
bool w3_cutaway(vec3 wp, vec2 cell) {
	return w3_cutaway_r(wp, cell, 1.0);
}

// ------------------------------------------------------------------------------------------------
// colour helpers
vec3 w3_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
float w3_luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

// ------------------------------------------------------------------------------------------------
// Oklab (Bjorn Ottosson, 2020), a perceptual colour space: used for the painter's shadow colour.
vec3 w3_lin_to_oklab(vec3 c) {
	vec3 lms = vec3(
		0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b,
		0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b,
		0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b);
	lms = pow(max(lms, vec3(0.0)), vec3(1.0 / 3.0));
	return vec3(
		0.2104542553 * lms.x + 0.7936177850 * lms.y - 0.0040720468 * lms.z,
		1.9779984951 * lms.x - 2.4285922050 * lms.y + 0.4505937099 * lms.z,
		0.0259040371 * lms.x + 0.7827717662 * lms.y - 0.8086757660 * lms.z);
}
vec3 w3_oklab_to_lin(vec3 L) {
	vec3 lms = vec3(
		L.x + 0.3963377774 * L.y + 0.2158037573 * L.z,
		L.x - 0.1055613458 * L.y - 0.0638541728 * L.z,
		L.x - 0.0894841775 * L.y - 1.2914855480 * L.z);
	lms = lms * lms * lms;
	return vec3(
		 4.0767416621 * lms.x - 3.3077115913 * lms.y + 0.2309699292 * lms.z,
		-1.2684380046 * lms.x + 2.6097574011 * lms.y - 0.3413193965 * lms.z,
		-0.0041960863 * lms.x - 0.7034186147 * lms.y + 1.7076147010 * lms.z);
}
// The painter's shadow colour of an albedo: its hue turns toward blue-violet by up to `turn` radians
// (warm browns through red-violet, greens toward blue-green), its chroma is kept (so it reads richer
// as it darkens instead of going grey), and greys pick up a little slate. Lightness is unchanged.
vec3 w3_shadow_hue(vec3 albedo, float turn) {
	vec3 lab = w3_lin_to_oklab(albedo);
	float C = length(lab.yz);
	float h = atan(lab.z, lab.y);
	const float TARGET = -1.66;                    // Oklab hue of blue-violet (about 265 degrees)
	float d = mod(TARGET - h + W3_PI, 2.0 * W3_PI) - W3_PI;
	h += clamp(d, -turn, turn);
	vec2 ab = vec2(cos(h), sin(h)) * (C * 1.15 + 0.006) + vec2(cos(TARGET), sin(TARGET)) * 0.005;
	return max(w3_oklab_to_lin(vec3(lab.x, ab)), vec3(0.0));
}

// ------------------------------------------------------------------------------------------------
// toon light model
// Ambient (goes to EMISSION in fragment): hemisphere sky/ground by the world normal, quantised to
// three steps so rounded forms stay flat-shaded. The shade is painted, not physically filtered: the
// ambient's brightness, only a third of its colour (a blue sky multiplied into a warm albedo would
// grey it), and a hue turn toward the cool side that keeps chroma (w3_shadow_hue), plus the global
// w3_shade_tint.
vec3 w3_ambient(vec3 albedo, vec3 world_n, float ao) {
	float up = world_n.y * 0.5 + 0.5;
	up = floor(up * 3.0 + 0.5) / 3.0;
	vec3 amb = mix(w3_ground, w3_sky, up);
	float lum = max(w3_luma(amb), 1e-4);
	vec3 amb_tint = mix(vec3(1.0), amb / lum, 0.2) * w3_shade_tint;
	return w3_shadow_hue(albedo, 0.38) * lum * amb_tint * ao;
}
// Sun / moon (call in light() for LIGHT_IS_DIRECTIONAL): two lit bands and a crisp shadow edge.
// dither: 0 for characters and painted cards, 1 lets the band edges dither on world-anchored cells.
vec3 w3_sun_light(vec3 albedo, vec3 n, vec3 l, vec3 light_col, float attenuation, vec2 cell, float dither) {
	float ndl = dot(n, l);
	float th = (w3_bayer4(cell) - 0.5) * 0.04 * dither;
	float band = ndl > 0.42 + th ? 1.0 : (ndl > 0.06 + th ? 0.62 : 0.0);
	float sh = step(0.5, attenuation);
	return albedo * w3_lit_tint * light_col / W3_PI * band * sh;
}
// Lanterns and fire (call in light() for the other lights): falloff quantised to four steps with a
// world-anchored dither, so a lantern draws pixel-art rings of light.
vec3 w3_point_light(vec3 albedo, vec3 n, vec3 l, vec3 light_col, float attenuation, vec2 cell, float dither) {
	float ndl = max(dot(n, l), 0.0) * 0.6 + 0.4;
	float a = attenuation * ndl;
	// rings in whole steps; the dither lives only in a narrow seam at each step and is scattered,
	// not ordered (an ordered dither over a slow falloff draws wide checkered bands)
	float sc = w3_hash(cell * 1.31 + 2.7) * 0.7 + w3_vnoise(cell / 1.9) * 0.3;
	float q = floor(a * 4.0 + 0.5 + (sc - 0.5) * 0.32 * dither) / 4.0;
	return albedo * light_col / W3_PI * q;
}
// Wet surfaces darken; porosity 0 (glazed tile, metal) .. 1 (soil, wood, thatch)
vec3 w3_wetten(vec3 albedo, float porosity) {
	return albedo * mix(1.0, 0.62, w3_wet * porosity);
}

// ------------------------------------------------------------------------------------------------
// procedural surface patterns for vertex-coloured meshes (UV2.x = pattern id, UV2.y = amount)
// Keyed on the screen-texel cell so every surface gets texel-for-pixel detail whatever its angle.
//   0 plain   1 wood planks   2 bark   3 thatch   4 stone   5 roof tiles   6 paper   7 moss on top
vec3 w3_pattern(vec3 col, float id, float amount, vec3 wp, vec3 wn, vec2 cell) {
	float r = w3_hash(cell);
	int p = int(id + 0.5);
	if (p == 0) {
		col *= (r < 0.12 ? 0.93 : (r > 0.93 ? 1.05 : 1.0));
	} else if (p == 1) {            // planks: boards along the dominant horizontal axis
		float along = abs(wn.z) > abs(wn.x) ? wp.x : wp.z;
		float across = abs(wn.y) > 0.6 ? (abs(wn.z) > abs(wn.x) ? wp.z : wp.x) : wp.y;
		float board = floor(across * 4.0);
		float seam = step(0.86, fract(across * 4.0));
		col *= 0.9 + w3_hash(vec2(board, 3.0)) * 0.16;
		col *= 0.95 + w3_hash(vec2(floor(along * 12.0), board)) * 0.08;
		col = mix(col, col * 0.62, seam);
	} else if (p == 2) {            // bark: vertical streaks, broken
		float strand = w3_hash(vec2(cell.x, floor(cell.y / 6.0)));
		col *= 0.82 + strand * 0.28;
		if (w3_hash(vec2(cell.x * 0.5, floor(cell.y / 3.0))) > 0.9) col *= 0.75;
	} else if (p == 3) {            // thatch: straw strands, combed rows
		float strand = w3_hash(vec2(cell.x, floor(cell.y / 5.0)));
		col *= 0.8 + strand * 0.32;
		if (mod(cell.y, 6.0) < 1.0) col *= 0.78;
	} else if (p == 4) {            // stone: speckle, organic cracks (noise iso-lines), lit edges, tidy moss on the tops
		float bl = w3_vnoise(cell / 9.0);
		col *= 0.95 + floor(bl * 3.0) * 0.04;
		col *= (r < 0.1 ? 0.88 : (r > 0.94 ? 1.08 : 1.0));
		float cr = abs(w3_vnoise(cell / 7.0 + 13.0) - 0.5);
		if (cr < 0.022) col *= 0.62;
		float cr2 = abs(w3_vnoise(cell / 4.0 + 41.0) - 0.5);
		if (cr2 < 0.015 && wn.y < 0.6) col *= 0.75;
		if (wn.y > 0.86 && w3_vnoise(cell / 4.5 + 9.0) > 0.7 - amount * 0.2) col = mix(col, vec3(0.065, 0.098, 0.023), 0.8);
	} else if (p == 5) {            // roof tiles (kawara): rows across, joints
		if (mod(cell.y, 4.0) < 1.0) col *= 0.7;
		col *= 0.9 + w3_hash(vec2(floor(cell.x / 3.0), floor(cell.y / 4.0))) * 0.16;
	} else if (p == 6) {            // washi paper: faint fibres
		col *= 0.95 + w3_hash(cell * vec2(1.0, 0.3)) * 0.08;
	} else if (p == 7) {            // moss on whatever faces up
		if (wn.y > 0.55 && w3_vnoise(cell / 4.0 + 3.0) > 0.55 - amount * 0.35) col = mix(col, vec3(0.050, 0.080, 0.018), 0.85);
		col *= (r < 0.12 ? 0.92 : 1.0);
	}
	return col;
}
