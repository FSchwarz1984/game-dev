// Contact shadow under a character's feet: a pixel ellipse that darkens the ground (multiply),
// drawn on a small quad laid on the terrain. Keeps her grounded in shade and in sun alike. Round 4:
// continuous (darkest under her, fading to nothing at the rim: no ring), and lighter, since the 3D
// model casts its own shadow in the sun; in the shade this is what grounds her.
shader_type spatial;
render_mode unshaded, blend_mul, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled, world_vertex_coords;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform vec2 radius_px = vec2(9.0, 3.5);
uniform float darkness = 0.7;
varying vec3 v_wp;
varying flat vec3 v_origin;

void vertex() {
	v_wp = VERTEX;
	v_origin = MODEL_MATRIX[3].xyz;
}

void fragment() {
	vec2 c = w3_ptex(v_wp) + 0.5 - round(w3_screen_o(v_origin));
	vec2 e = c / radius_px;
	float r = dot(e, e);
	if (r > 1.0) {
		discard;
	}
	float k = mix(darkness, 1.0, smoothstep(0.1, 1.0, r));
	ALBEDO = vec3(k);
}
