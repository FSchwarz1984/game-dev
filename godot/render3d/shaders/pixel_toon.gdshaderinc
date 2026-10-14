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
	float k = smoothstep(R, R * 0.55, r) * smoothstep(0.3, 1.2, toward);
	return w3_bayer4(cell) < k * 0.82;
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
// toon light model
// Ambient (goes to EMISSION in fragment): hemisphere sky/ground by the world normal, quantised to
// three steps so rounded forms stay flat-shaded; shadowed surfaces shift cool (w3_shade_tint).
vec3 w3_ambient(vec3 albedo, vec3 world_n, float ao) {
	float up = world_n.y * 0.5 + 0.5;
	up = floor(up * 3.0 + 0.5) / 3.0;
	vec3 amb = mix(w3_ground, w3_sky, up);
	return albedo * w3_shade_tint * amb * ao;
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
	float q = floor(a * 4.0 + mix(0.5, w3_bayer4(cell), dither)) / 4.0;
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
	} else if (p == 4) {            // stone: soft blotches, a few cracks, moss where it faces up
		float bl = w3_vnoise(cell / 5.0);
		col *= 0.86 + bl * 0.22 + (r - 0.5) * 0.06;
		if (w3_hash(floor(cell / vec2(3.0, 2.0)) + 5.0) > 0.94) col *= 0.7;
		if (wn.y > 0.7 && w3_vnoise(cell / 3.0 + 9.0) > 0.62 - amount * 0.3) col = mix(col, vec3(0.065, 0.098, 0.023), 0.8);
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
