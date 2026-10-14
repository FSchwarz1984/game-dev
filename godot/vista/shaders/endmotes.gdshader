// The end of the wave (src/vista/south.js, HEAD): the curtain reaches us, its motes rush past the
// camera. In view space (logical px), projected from a small 3D cloud in front of the lens; alpha
// blended white. instance: X Y0 | Z0 vY | vZ t0
shader_type canvas_item;
render_mode blend_mix, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform float t;
uniform vec2 view = vec2(480.0, 270.0);

varying flat float v_a;

void vertex() {
	float X = MODEL_MATRIX[0].x, y0 = MODEL_MATRIX[0].y, z0 = MODEL_MATRIX[1].x, vy = MODEL_MATRIX[1].y;
	float vz = MODEL_MATRIX[2].x, t0 = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	float age = t - t0;
	float Z = z0 + vz * age, Y = y0 + vy * age;
	float fp = view.y * 0.9;
	vec2 q = vec2(view.x / 2.0 + fp * X / max(Z, 0.01), view.y * 0.55 - fp * Y / max(Z, 0.01));
	bool live = t0 > -1.0e8 && age >= 0.0 && Z >= 0.35 && q.x >= -4.0 && q.x <= view.x + 4.0 && q.y >= -4.0 && q.y <= view.y + 4.0;
	float sz = clamp(roundj(2.4 / max(Z, 0.01)), 1.0, 4.0);
	v_a = smoothj(0.0, 0.3, age) * (0.55 + 0.4 * smoothj(4.0, 1.0, Z));
	if (!live) {
		VERTEX = vec2(-100000.0);
	} else {
		vec2 lo = vec2(roundj(q.x - sz / 2.0), roundj(q.y - sz / 2.0));
		VERTEX = world + lo + VERTEX * sz;
	}
}

void fragment() {
	COLOR = vec4(srgb_to_linear(vec3(238.0, 242.0, 255.0) / 255.0), v_a);
}
