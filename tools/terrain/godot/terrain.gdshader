// Terrain chunk shader (preview of the lighting contract in docs/knowledge/17).
// TEXTURE = albedo (CanvasTexture diffuse), NORMAL = the baked normal map (CanvasTexture normal),
// light_tex: R = sun horizon elevation (deg * 255/90), G = sky visibility, B = material code.
// CanvasModulate supplies the ambient (sky) colour; a DirectionalLight2D is the sun and only
// lends its colour/energy: its direction is the world vector sun_dir, and the baked horizon decides
// shadow, so shadows lengthen smoothly with sun_elev_deg and never jump (R-7).
shader_type canvas_item;

uniform sampler2D light_tex : filter_nearest, repeat_disable;
uniform vec3 sun_dir = vec3(-0.70, 0.64, 0.29);   // toward the sun, world (x east, y up, z south)
uniform float sun_elev_deg = 40.0;
uniform float shadow_soft_deg = 2.5;
uniform float bounce_k = 0.45;                     // light thrown back onto walls, x ambient

varying vec3 v_albedo;
varying float v_vis;
varying vec3 v_nw;

vec3 world_normal(vec3 ns) {
	// Godot's canvas NORMAL: x right, y down, z out of the screen.
	// Screen up = (0, 1, -1)/sqrt2 and out = (0, 1, 1)/sqrt2 in world (oblique 3/4 view).
	float up = -ns.y;
	float o = ns.z;
	return normalize(vec3(ns.x, (up + o) * 0.70710678, (o - up) * 0.70710678));
}

void fragment() {
	vec4 a = texture(TEXTURE, UV);
	vec4 l = texture(light_tex, UV);
	vec3 nw = world_normal(NORMAL);
	float horizon = l.r * 90.0;
	float sky = l.g;
	float vis = smoothstep(horizon - shadow_soft_deg, horizon + shadow_soft_deg, sun_elev_deg);
	float ny = clamp(nw.y, -1.0, 1.0);
	float amb = (0.75 + 0.25 * ny) * (0.5 + 0.5 * sky) + bounce_k * (0.5 - 0.5 * ny);
	v_albedo = a.rgb;
	v_vis = vis;
	v_nw = nw;
	COLOR = vec4(a.rgb * amb, a.a);
}

void light() {
	// LIGHT_COLOR.a carries the light texture's falloff (point lights); energy is separate.
	if (LIGHT_IS_DIRECTIONAL) {
		float ndl = max(dot(v_nw, normalize(sun_dir)), 0.0);
		LIGHT = vec4(LIGHT_COLOR.rgb * LIGHT_ENERGY * v_albedo * ndl * v_vis, 1.0);
	} else {
		float ndl = max(dot(NORMAL, LIGHT_DIRECTION), 0.0);
		LIGHT = vec4(LIGHT_COLOR.rgb * LIGHT_ENERGY * v_albedo * ndl, LIGHT_COLOR.a);
	}
}
