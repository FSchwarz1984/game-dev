// A walker's mark on the grass bend map (world3d/grass.gd): the blades under the feet are pressed
// down (b), those around them pushed outward (rg = direction x, z; 0.5 = none), soft at the rim.
shader_type canvas_item;

void fragment() {
	vec2 d = UV * 2.0 - 1.0;
	float r = length(d);
	float f = 1.0 - smoothstep(0.4, 1.0, r);
	vec2 dir = r > 1e-3 ? d / r : vec2(0.0);
	float pushk = smoothstep(0.05, 0.55, r);
	COLOR = vec4(0.5 + 0.5 * dir.x * pushk, 0.5 + 0.5 * dir.y * pushk, 1.0 - smoothstep(0.3, 0.9, r) * 0.6, f);
}
