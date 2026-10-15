// The hemisphere the world's ambient light comes from (render3d/world_env.gd; never drawn: the
// top-down view does not see the sky). The sky's colour above, the ground's bounce below, blended
// across the horizon, so faces turned up take the cool sky and faces turned down the warm bounce.
shader_type sky;

uniform vec3 top = vec3(0.70, 0.80, 1.0);      // linear
uniform vec3 bottom = vec3(0.20, 0.18, 0.15);

void sky() {
	float y = EYEDIR.y;
	COLOR = mix(bottom, top, smoothstep(-0.35, 0.45, y));
}
