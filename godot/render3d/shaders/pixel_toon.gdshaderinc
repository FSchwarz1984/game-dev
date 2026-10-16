// pixel_toon.gdshaderinc — the shared contract of the 3D pixel renderer (docs/knowledge/21-3d-pixel-render.md).
// Every 3D material of the world includes this file. It holds:
//   * the view numbers (pixels per metre, camera pitch, lean) as shader globals,
//   * the screen-texel lattice ("ptex"): the native pixel a world point lands on, independent of the
//     camera (the camera only ever moves by whole texels), so procedural detail and dithering stay
//     glued to the world and never crawl,
//   * lean-back for upright objects (verticals read at w3_view.x px per metre, A Link Between Worlds style),
//   * whole-pixel wind sway, the canopy cut-away around her,
//   * the light model (continuous: wrapped diffuse, transmission through leaves; the engine's ambient).
// Axes (Godot): X east, Y up, Z south (toward the camera). Units: metres. The camera looks north (-Z)
// and down at the pitch held in w3_view. Colours are linear unless a name says srgb.
//
// Declared in godot/project.godot [shader_globals]; the time-of-day controller
// (render3d/world_env.gd) writes them every frame.

global uniform vec4 w3_view;        // x: native px per metre (30), y: sin(pitch), z: cos(pitch), w: lean k = tan(pitch/2)
global uniform float w3_time;       // world clock, seconds (animation; deterministic in captures)
global uniform vec3 w3_sun_dir;     // unit vector toward the sun (or moon at night), world space
global uniform vec3 w3_sun;         // sun colour * intensity (linear), for effects outside light()
global uniform vec3 w3_sky;         // ambient from the sky (cool), linear
global uniform vec3 w3_ground;      // ambient bounced from the ground (warm, dark), linear
global uniform vec3 w3_shade_tint;  // hue shift of surfaces in shadow (cool), multiplier
global uniform vec3 w3_lit_tint;    // hue shift of surfaces in sunlight (warm), multiplier
global uniform vec4 w3_wind;        // xy: wind direction (x east, y south), z: strength 0..2, w: gust 0..1
global uniform float w3_wet;        // rain wetness 0..1
global uniform vec4 w3_player;      // xyz: her chest (world), w: cut-away radius in native px (0 = off; negative: the
                                    // cut-away only, nothing gives way or clears round her: --nochar, an unseen walker)
global uniform float w3_night;      // 0 day .. 1 night
global uniform vec3 w3_fill;        // the sky's light let back into the sun's shadow (round 5; world_env.gd: by the hour)
global uniform sampler2D w3_lamps;  // lamps (render3d/lamps.gd): row 0 xyz + reach, row 1 rgb * energy + on
global uniform float w3_lamp_n;     // how many lamps are lit (texels in use)
global uniform float w3_bake;       // 0 the game; impostor bake (render3d/dev/impostor_bake.gd):
                                    // 1 albedo, 2 normal, 3 AO + class; no wind, no lean

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
// metre reads as many px tall as a horizontal one (k = tan(pitch / 2)). The terrain, water, paths,
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
	if (flex <= 0.0 || w3_bake > 0.5) return vec2(0.0);
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
// keep_px > 0: whatever lies more than keep_px above her on screen stays (a great crown overhead
// frames the top of the view with its lowest boughs instead of vanishing whole)
bool w3_cutaway_k(vec3 wp, vec2 cell, float scale, float keep_px) {
	if (w3_player.w == 0.0) return false;
	vec3 d = wp - w3_player.xyz;
	float toward = dot(d, w3_cam_back());           // > 0: this surface is between her and the camera
	if (toward < 0.3) return false;
	vec2 ds = w3_screen(wp) - w3_screen(w3_player.xyz);
	float r = length(ds * vec2(1.0, 0.8));
	float R = abs(w3_player.w) * scale;
	float ring = min(12.0, R * 0.35);                 // a stippled edge, clear inside
	float k = clamp((R - r) / ring, 0.0, 1.0) * smoothstep(0.3, 1.2, toward);
	if (keep_px > 0.0) {
		k *= 1.0 - clamp((ds.y - keep_px) / 14.0, 0.0, 1.0);
	}
	// scattered, not ordered (an ordered dither reads as a printed screen)
	return w3_hash(cell * 1.11 + 2.9) * 0.75 + w3_vnoise(cell / 1.7) * 0.25 < k;
}
// a scattered (not ordered) threshold per screen texel, fixed to the world's pixel lattice
float w3_stipple(vec2 cell) {
	return w3_hash(cell * 1.11 + 2.9) * 0.75 + w3_vnoise(cell / 1.7) * 0.25;
}
bool w3_cutaway_r(vec3 wp, vec2 cell, float scale) {
	return w3_cutaway_k(wp, cell, scale, 0.0);
}
bool w3_cutaway(vec3 wp, vec2 cell) {
	return w3_cutaway_r(wp, cell, 1.0);
}

// ------------------------------------------------------------------------------------------------
// The sky's light let back into the sun's shadow (round 5, the lead: the mornings, the evenings and
// the shrine under the great camphor were far darker than round 3's). Round 3 lit all its shade with
// the whole sky; since round 4 the VoxelGI sees little sky under a crown or by a hedge, and with the
// sun low most of the frame lies in such shade. Added in light() for the sun, where the sun is
// shadowed (att: its shadow, 0 in shadow .. 1 lit), as more ambient (the engine multiplies it by the
// painted shade's albedo like the sky's own light). world_env.gd sets w3_fill by the hour: none at
// midday, at night or in rain, so those keep their light as it was.
vec3 w3_shadow_fill(float att) {
	return w3_fill * (1.0 - clamp(att, 0.0, 1.0));
}

// ------------------------------------------------------------------------------------------------
// colour helpers
vec3 w3_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
float w3_luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

// ------------------------------------------------------------------------------------------------
// impostor bake output (w3_bake > 0): what the material is, not how it is lit. Written to EMISSION
// with no lights in the bake world, so the viewport holds the value itself (sRGB-encoded on output:
// the albedo comes out as its own sRGB; the data passes are pre-linearised to come out exact).
vec3 w3_bake_out(vec3 albedo, vec3 world_n, float ao, float cls) {
	if (w3_bake < 1.5) return albedo;
	if (w3_bake < 2.5) return w3_srgb_to_linear(clamp(world_n * 0.5 + 0.5, 0.0, 1.0));
	return w3_srgb_to_linear(vec3(clamp(ao, 0.0, 1.0), cls, 0.0));
}

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
	// quiet colours (packed earth, stone, wood) turn only a little: their shade stays their own
	// colour, a touch cooler, instead of going red-violet
	turn *= smoothstep(0.025, 0.075, C);
	// right across from blue-violet (yellows and straw near 85 degrees) the turn has no side to take:
	// two near-identical yellows would shade one rust-red, the other lime. It fades out there.
	turn *= 1.0 - smoothstep(0.82 * W3_PI, 0.97 * W3_PI, abs(d));
	h += clamp(d, -turn, turn);
	vec2 ab = vec2(cos(h), sin(h)) * (C * 1.15 + 0.006) + vec2(cos(TARGET), sin(TARGET)) * 0.005;
	return max(w3_oklab_to_lin(vec3(lab.x, ab)), vec3(0.0));
}

// ------------------------------------------------------------------------------------------------
// The round-3 palette (round 5, decision-log G5R3-1: the user's colours are round 3's, "浮世绘式的
// 色调"; round 4's freshening, lush greens, a saturated grade and blue-green shade, was rolled back
// as "画蛇添足"). Two parts of that look are reproduced here on purpose:
// * w3_ukiyo_tex: leaf, ground-cover and old-sprite textures pass their sRGB values through the sRGB
//   curve once more before the usual conversion: deeper, richer mid-tones. Rounds 1-3 drew them so
//   by a double sRGB conversion (an error found and fixed in round 4: a source_color sampler and a
//   manual conversion); the look it gave is now the palette, kept by this function on purpose, not
//   by a sampler hint. k 0 .. 1 (1: round 3 exactly).
// * w3_paint_shade: what the ambient light (the sky, the VoxelGI bounce) sees of a surface: its
//   colour with the hue turned toward the cool side, the chroma kept (w3_shadow_hue), times the
//   painter's shade tint; the sky's own colour reaches it only in part (world_env.gd gives the
//   engine a sky of low chroma): a blue sky multiplied into warm earth greys it (knowledge/21 §6 #7).
//   Round 3 painted its shade the same way, in EMISSION; now the engine's ambient carries it, so the
//   VoxelGI bounce and SSAO work on it. light() undoes it for the direct light (v_detail).
// * w3_r3_ground / w3_r3_body: the sun's levels of round 3. Round 3 drew the sun in bands (the ground
//   0.5 / 0.68 / 0.86 / 1 above n.l 0.04 / 0.30 / 0.58 / 0.80; everything else 0.62 / 1 above 0.06 /
//   0.42): generous to the faces turned half away, so a low sun still lit the land warmly. The look
//   keeps those levels as a smooth curve through the middle of each band (no steps, G5R2-1: the
//   light stays continuous). At night the moon keeps round 4's wrapped Lambert (the user: "夜里的光非
//   常好"): w3_sun_level blends by w3_night.
vec3 w3_ukiyo_tex(vec3 srgb, float k) {
	// (by day; at night round 4's colours are kept)
	return mix(srgb, w3_srgb_to_linear(srgb), k * (1.0 - w3_night));
}
vec3 w3_paint_shade(vec3 alb) {
	// (round 4's night is kept: no hue turn in the dark)
	return max(mix(w3_shadow_hue(alb, 0.38), alb, w3_night) * w3_shade_tint, alb * 0.05);
}

// How much of a material's painted detail its shade drops (its `shade_flatten`): big masses of light
// and shade with the detail in the sun (G5R2) holds while there is a sun. Under a rain's overcast
// nearly all the light is the sky's, so a flattened shade turned every surface into flat colour (the
// user, G5R3-5: the hut in the rain "全是色塊"); the detail comes back as the rain sets in.
float w3_flatten(float k) {
	return k * (1.0 - 0.85 * w3_wet);
}
float w3_r3_ground(float ndl) {
	return 0.5 * smoothstep(-0.08, 0.16, ndl) + 0.18 * smoothstep(0.18, 0.42, ndl)
		+ 0.18 * smoothstep(0.46, 0.70, ndl) + 0.14 * smoothstep(0.70, 0.90, ndl);
}
float w3_r3_body(float ndl) {
	return 0.62 * smoothstep(-0.10, 0.18, ndl) + 0.38 * smoothstep(0.24, 0.60, ndl);
}
// the sun's (or the moon's) direct light at a level: round 3's by day, round 4's wrap at night
// (ground: true for the terrain's ramp; wrap: round 4's wrap for the night)
vec3 w3_sun_level(vec3 n, vec3 l, vec3 light_col, float atten, bool ground, float wrap) {
	float ndl = dot(n, l);
	float day = ground ? w3_r3_ground(ndl) : w3_r3_body(ndl);
	float d4 = clamp((ndl + wrap) / (1.0 + wrap), 0.0, 1.0);
	// (no local named "tint": materials have a uniform of that name, knowledge/21 §6 #6)
	vec3 w3_lt = mix(w3_lit_tint, mix(vec3(1.0), w3_lit_tint, d4), w3_night);
	return light_col * w3_lt * (mix(day, d4, w3_night) * atten / W3_PI);
}

// Lush: the ground's greens made fresh (round 4, G5R2-1: "饱满自然的绿", not withered olive): chroma
// raised and the hue turned toward a clear green. k 0 .. 1. Round 5 (G5R3-1): by day no more (the
// callers scale it by w3_night: round 4's night, which the user kept, keeps it).
vec3 w3_lush(vec3 c, float k) {
	if (k <= 0.0) return c;
	vec3 lab = w3_lin_to_oklab(c);
	float C = length(lab.yz);
	float h = atan(lab.z, lab.y);
	h += (2.48 - h) * 0.3 * k;
	C = C * (1.0 + 1.4 * k) + 0.01 * k;
	return max(w3_oklab_to_lin(vec3(lab.x * (1.0 + 0.04 * k), cos(h) * C, sin(h) * C)), vec3(0.0));
}

// ------------------------------------------------------------------------------------------------
// light (round 4, decision-log G5R2-1: no bands, no rings). Every light falls off continuously and
// the terminator is a soft gradient: a little wrap, so forms read round and the shade side is never a
// cut-out. The pixel-art clarity comes from the low resolution, the whole-pixel camera, the palette,
// the grade and the outlines, not from cutting the light into steps.
//
// The world's materials take the engine's ambient (the time of day's sky colour, the VoxelGI bounce,
// SSAO; render3d/world_env.gd): their ALBEDO is the real albedo, and light() adds only the direct
// light without it (the engine multiplies the diffuse and the ambient by ALBEDO).

// wrapped Lambert: wrap 0 = Lambert; 0.3 solids; 0.5 leaves (light scatters through a crown)
float w3_wrap(float ndl, float wrap) {
	return clamp((ndl + wrap) / (1.0 + wrap), 0.0, 1.0);
}
// direct light of the sun, the moon or a lamp (call in light()); lit surfaces lean a little warm
vec3 w3_direct(vec3 n, vec3 l, vec3 light_col, float atten, float wrap) {
	float d = w3_wrap(dot(n, l), wrap);
	return light_col * mix(vec3(1.0), w3_lit_tint, d) * (d * atten / W3_PI);
}
// light through thin things (leaves, paper, petals) seen against the light: what reaches the back of
// the surface, tinted by the material (call in light(); color = how much and what colour gets through)
vec3 w3_transmit(vec3 n, vec3 l, vec3 v, vec3 light_col, float atten, vec3 color) {
	float back = clamp(-dot(n, l) * 0.6 + 0.4, 0.0, 1.0);
	// strongest when the light is behind the leaf as seen from the camera (sun low, ahead of us)
	float toward = pow(clamp(dot(-v, l) * 0.5 + 0.5, 0.0, 1.0), 2.0);
	return light_col * color * (back * (0.35 + 0.65 * toward) * atten / W3_PI);
}

// The painted ambient for materials outside the engine's light (the view from the lookout, its own
// world): a hemisphere sky/ground by the world normal, continuous; the shade's hue turns cool while
// keeping chroma (w3_shadow_hue). Goes to EMISSION.
vec3 w3_ambient(vec3 albedo, vec3 world_n, float ao) {
	float up = world_n.y * 0.5 + 0.5;
	vec3 amb = mix(w3_ground, w3_sky, up);
	float lum = max(w3_luma(amb), 1e-4);
	vec3 amb_tint = mix(vec3(1.0), amb / lum, 0.2) * w3_shade_tint;
	return w3_shadow_hue(albedo, 0.38) * lum * amb_tint * ao;
}
// Sun / moon with the albedo folded in (materials whose ALBEDO is 1: the lookout's), continuous.
// (cell and dither are kept for the callers; nothing is dithered any more)
vec3 w3_sun_light(vec3 albedo, vec3 n, vec3 l, vec3 light_col, float attenuation, vec2 cell, float dither) {
	return albedo * w3_direct(n, l, light_col, attenuation, 0.25);
}
// Point lights with the albedo folded in, continuous.
vec3 w3_point_light(vec3 albedo, vec3 n, vec3 l, vec3 light_col, float attenuation, vec2 cell, float dither) {
	float ndl = max(dot(n, l), 0.0) * 0.6 + 0.4;
	return albedo * light_col / W3_PI * attenuation * ndl;
}
// Lanterns and fires from the renderer's own list (render3d/lamps.gd, the global w3_lamps): used by
// the view from the lookout, which is a world of its own (the main world has real OmniLight3D lamps).
// A smooth pool: a warm core that falls off softly and turns orange toward its edge, which meets the
// dark with no visible line; lamps add up (softly limited). Add the result to EMISSION.
vec3 w3_lamp_light(vec3 albedo, vec3 wp, vec3 n, vec2 cell, float dither) {
	int cnt = int(w3_lamp_n + 0.5);
	if (cnt <= 0) return vec3(0.0);
	vec3 sum = vec3(0.0);
	for (int i = 0; i < cnt; i++) {
		vec4 a = texelFetch(w3_lamps, ivec2(i, 0), 0);
		vec3 d = a.xyz - wp;
		float dist = length(d * vec3(1.0, 0.4, 1.0));
		if (dist >= a.w) continue;
		vec4 c = texelFetch(w3_lamps, ivec2(i, 1), 0);
		float f = 1.0 - dist / a.w;
		float face = clamp(dot(n, normalize(d)) * 0.7 + 0.3, 0.0, 1.0);
		float v = f * f * mix(1.0, face, 0.8);
		vec3 lamp_tint = mix(vec3(1.0, 0.45, 0.16), vec3(1.0, 0.80, 0.56), clamp(f * 1.3, 0.0, 1.0));
		sum += c.rgb * lamp_tint * v;
	}
	// several pools overlapping do not burn white
	sum = sum / (1.0 + max(max(sum.r, sum.g), sum.b) * 0.35);
	return albedo * sum;
}
// 遠化 (far, 0..1): a thing that has lost its qualities looks far: pale, nearly grey, a little cool,
// lifted toward the haze. Materials also flatten their light by the same amount (w3_far_light).
vec3 w3_far(vec3 albedo, float k) {
	if (k <= 0.0) return albedo;
	float l = w3_luma(albedo);
	vec3 pale = mix(vec3(l) * vec3(0.95, 0.98, 1.05), vec3(0.6, 0.62, 0.67), 0.45);
	return mix(albedo, pale, clamp(k, 0.0, 1.0) * 0.85);
}
// the light's share left to a faded thing (its shading flattens: shade lifted, sun weakened)
float w3_far_light(float k) { return mix(1.0, 0.55, clamp(k, 0.0, 1.0)); }
float w3_far_fill(float k) { return mix(1.0, 1.6, clamp(k, 0.0, 1.0)); }
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
	} else if (p == 3) {            // thatch
		if (abs(wn.y) < 0.5) {
			// a cut face (the eave, the steps between the courses): the ends of the straw, a dense
			// speckle of pale stalk ends with dark gaps between, in loose layers
			float lay = w3_vnoise(vec2(cell.x / 9.0, floor(cell.y / 3.0)));
			col *= (r > 0.58 ? 1.16 : (r < 0.1 ? 0.66 : 0.96)) * (0.9 + lay * 0.2);
		} else {
			// the slope: straw strands down the fall line, broken, a few darker combed gaps
			float strand = w3_hash(vec2(cell.x, floor(cell.y / 5.0)));
			col *= 0.82 + strand * 0.3;
			if (w3_hash(vec2(floor(cell.x / 3.0), floor(cell.y / 7.0)) + 5.0) > 0.86) col *= 0.82;
		}
	} else if (p == 4) {            // stone (granite): grain, organic cracks (noise iso-lines), lichen, tidy moss on the tops
		float bl = w3_vnoise(cell / 9.0);
		col *= 0.95 + floor(bl * 3.0) * 0.04;
		// the grain of granite: dark mica specks, pale feldspar
		col *= (r < 0.07 ? 0.74 : (r < 0.14 ? 0.9 : (r > 0.95 ? 1.14 : 1.0)));
		// crustose lichen: pale grey-green rosettes, and now and then a small orange-yellow one, on
		// the faces that see the sky
		if (wn.y > -0.25) {
			float ln = w3_vnoise(cell / 3.3 + 21.0) * 0.75 + w3_hash(cell * 0.7 + 5.0) * 0.25;
			if (ln > 0.72) col = mix(col, vec3(0.40, 0.43, 0.33), 0.55);
			else if (w3_vnoise(cell / 2.1 + 57.0) > 0.9 && r < 0.5) col = mix(col, vec3(0.50, 0.32, 0.08), 0.5);
		}
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
