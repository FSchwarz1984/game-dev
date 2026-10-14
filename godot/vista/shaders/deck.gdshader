// The cloud deck between the shores (src/vista/sky.js CloudDeck.renderGen): a density field baked per
// pixel; the hole over the gate is carved here every frame (so it opens smoothly), then each pixel is
// shaded by its density gradient into body / lit rim / thick core and looked up in the cloud palette.
// The light of the lanterns below and of the open sky tint the deck where it is (source-atop).
shader_type canvas_item;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D dens : filter_nearest, repeat_disable;   // density, 16-bit fixed: q = d * 8192 + 32768
uniform sampler2D lut : filter_nearest, repeat_disable;    // 96 entries per time of day
uniform float tod_row;
uniform float cx;
uniform float yh;
uniform float f = 360.0;
uniform float hc = 2.6;
uniform float ya;
uniform float yb;
uniform float wc;
uniform vec3 hole;             // X, Z on the deck, radius (0: closed)
uniform vec2 light_dir = vec2(0.82, 0.58);
uniform vec2 gate;             // the gate's mouth (canvas)
uniform float flux;            // warm light from the lanterns rising beneath
uniform float reveal;          // jade light of the sky shore once the deck parts

varying vec2 px;

void vertex() {
	px = VERTEX;
}

float val(ivec2 p) {
	vec2 v = texelFetch(dens, p, 0).rg;
	float d = (floor(v.r * 255.0 + 0.5) + floor(v.g * 255.0 + 0.5) * 256.0 - 32768.0) / 8192.0;
	if (hole.z > 0.0) {
		float Z = f * hc / max(1.0, yh - float(p.y));
		float X = (float(p.x) + 0.5 - cx) * Z / f;
		float q = length(vec2(X - hole.x, (Z - hole.y) * 0.8)) / hole.z;
		d -= smoothj(1.25, 0.55, q) * 1.6;
		d += smoothj(0.9, 1.35, q) * smoothj(1.9, 1.35, q) * 0.25 * min(1.0, hole.z / 3.0) * (1.0 - smoothj(3.5, 7.0, hole.z));
	}
	return d;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	if (float(p.y) < ya || float(p.y) > yb - 2.0 || p.x <= 0 || float(p.x) >= wc - 1.0) discard;
	float d = val(p);
	if (d <= 0.0) discard;
	float gx = val(p + ivec2(1, 0)) - val(p - ivec2(1, 0));
	float gy = val(p + ivec2(0, 1)) - val(p - ivec2(0, 1));
	float gl = length(vec2(gx, gy));
	if (gl == 0.0) gl = 1.0;
	float nx = -gx / gl, ny = -gy / gl;
	float lam = nx * light_dir.x + ny * light_dir.y;
	float thick = clamp(d / 1.6, 0.0, 1.0);
	int mat = 1;
	float sun = clamp(roundj((lam * 0.5 + 0.5) * 6.0 * (1.0 - thick * 0.35)), 0.0, 7.0);
	if (d < 0.18 && lam > 0.15) { mat = 2; sun = 7.0; }
	else if (thick > 0.62 && lam < 0.2) mat = 3;
	float sky = clamp(roundj((1.0 - thick) * 2.0 + (ny < 0.0 ? 1.0 : 0.0)), 0.0, 3.0);
	vec3 c = lut_rgb(lut, (mat - 1) * 32 + int(sun) * 4 + int(sky), tod_row);
	vec2 q = vec2(p);
	if (flux > 0.01) c = mix(c, vec3(255.0, 176.0, 120.0), glow_w(q - vec2(roundj(gate.x), roundj(gate.y + 30.0)), 70.0) * clamp(0.5 * flux, 0.0, 1.0));
	if (reveal > 0.0) c = mix(c, vec3(170.0, 236.0, 216.0), glow_w(q - vec2(roundj(gate.x), roundj(gate.y + 10.0)), 56.0) * clamp(0.45 * reveal, 0.0, 1.0));
	COLOR = vec4(lin255(c), 1.0);
}
