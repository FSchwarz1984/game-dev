// Cast shadow of a plant on the ground. Own work, CC0.
// The texture holds the shade cast by the reference sun (meta.json sun_ref): R = crown, G = trunk,
// B = contact shade where the plant meets the ground (sun-independent, kept at night too).
// One node draws the crown part, another the trunk part (channel). As the sun's elevation changes
// (global sun_elevation, degrees) the trunk shadow stretches from the foot along the shadow
// direction and the crown shadow slides along it, continuously (no jumps, R-7).
// Globals: sun_elevation (float, degrees), shadow_strength (float, 0..1: 0 at night or overcast).
shader_type canvas_item;
render_mode unshaded, blend_mul;

uniform int channel = 0;                 // 0 crown, 1 trunk, 2 contact (does not move)
uniform vec4 shade_color : source_color = vec4(0.44, 0.48, 0.62, 1.0);
uniform float strength = 0.85;
uniform float ref_elevation = 47.8;
uniform vec2 shadow_dir = vec2(0.809, 0.588);
uniform float crown_height_px = 200.0;   // mean height of the crown above the ground (px)
uniform float min_elevation = 22.0;      // stylised floor: shadows never run off the screen

global uniform float sun_elevation;
global uniform float shadow_strength;

void vertex() {
	float e = radians(clamp(sun_elevation, min_elevation, 89.0));
	float k = (1.0 / tan(e)) / (1.0 / tan(radians(ref_elevation)));
	vec2 d = normalize(shadow_dir);
	if (channel == 1) {
		VERTEX = VERTEX + d * dot(VERTEX, d) * (k - 1.0);
	} else if (channel == 0) {
		VERTEX = VERTEX + d * crown_height_px * (k - 1.0) * (1.0 / tan(radians(ref_elevation)));
	}
}

void fragment() {
	vec4 s = texture(TEXTURE, UV);
	float v = channel == 1 ? s.g : (channel == 2 ? s.b * 0.6 : s.r);
	float a = v * strength * (channel == 2 ? max(0.5, shadow_strength) : shadow_strength);
	COLOR = vec4(mix(vec3(1.0), shade_color.rgb, a), 1.0);
}
