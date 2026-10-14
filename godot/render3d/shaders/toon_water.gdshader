// Pixel water (docs/knowledge/21-3d-pixel-render.md): the spring pool, the stream, the paddies.
// Transparent, drawn after the screen post (so it applies the shared fog itself). It refracts what
// lies under it (screen texture, offset in whole texels), tints by depth (depth texture), lays a
// hint of sky on the surface, combs flow lines along the stream, rings foam where it meets stones
// and banks, glints the sun on crests, and rings with rain. Paddies are mid-August rice: rows of
// green standing in water, the water only glinting between them.
// Mesh: UV2.x = kind (1 pool, 2 stream, 3 paddy), UV2.y = flow angle (radians, stream).
shader_type spatial;
render_mode world_vertex_coords, blend_mix, depth_draw_never, ambient_light_disabled, specular_disabled, fog_disabled, cull_back, shadows_disabled;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"
#include "res://render3d/shaders/fog.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform vec3 shallow_col : source_color = vec3(0.30, 0.42, 0.40);
uniform vec3 deep_col : source_color = vec3(0.09, 0.17, 0.20);
uniform vec3 rice_col : source_color = vec3(0.42, 0.60, 0.24);

varying vec3 v_wp;
varying flat vec2 v_kind;
varying vec3 v_alb;
varying vec2 v_cell;

void vertex() {
	v_wp = VERTEX;
	v_kind = UV2;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	float kind = floor(v_kind.x + 0.5);
	float t = w3_time;
	// what lies beneath, and how deep it is
	float raw = texture(depth_tex, SCREEN_UV).r;
	vec4 vp = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, raw, 1.0);
	vp.xyz /= vp.w;
	vec3 bottom = (INV_VIEW_MATRIX * vec4(vp.xyz, 1.0)).xyz;
	float depth = max(v_wp.y - bottom.y, 0.0);
	vec2 flow = vec2(cos(v_kind.y), sin(v_kind.y));
	float moving = kind > 1.5 && kind < 2.5 ? 1.0 : 0.0;
	// ripple field in screen-texel space (stable), combed along the flow in the stream
	vec2 q = cell / vec2(9.0, 5.0);
	vec2 fq = vec2(dot(cell, vec2(flow.y, -flow.x)) / 3.0, dot(cell, flow) / 14.0);
	float rip = mix(w3_vnoise(q + vec2(t * 0.35, t * 0.2)), w3_vnoise(fq - vec2(0.0, t * 1.6)), moving);
	// refraction: whole-texel offsets
	vec2 off = floor((vec2(rip, w3_vnoise(q * 1.3 + 4.0 + t * 0.3)) - 0.5) * 2.4 * clamp(depth * 3.0, 0.0, 1.0) + 0.5);
	vec3 under = texture(screen_tex, SCREEN_UV + off / VIEWPORT_SIZE).rgb;
	float dk = smoothstep(0.0, 0.9, depth);
	vec3 body = mix(shallow_col, deep_col, dk) * (w3_sky * 1.3 + w3_sun * 0.55);
	float a = clamp(0.25 + dk * 0.65, 0.0, 0.92);
	vec3 col = mix(under, body, a);
	// sky in the surface, a little stronger where it is calm
	float sky_k = (0.10 + 0.12 * dk) * (1.0 - moving * 0.4);
	col = mix(col, w3_sky * 1.25 + w3_fog_col * 0.2, sky_k);
	// light bands of the ripples (crisp, never smooth)
	float band = step(0.68, rip) * step(rip, 0.74);
	col += band * (w3_sky * 0.25 + w3_sun * 0.18);
	// flow lines in the stream
	float streak = step(0.8, w3_vnoise(vec2(fq.x * 2.0, fq.y * 0.7 - t * 2.4)));
	col = mix(col, col * 1.25 + vec3(0.03), streak * moving * 0.8);
	// foam where it is shallow (banks, stones), breaking and breathing
	float lap = 0.06 + 0.03 * sin(t * 1.4 + w3_vnoise(cell / 6.0) * 6.0);
	float foam = (1.0 - smoothstep(lap * 0.5, lap, depth)) * step(0.45, w3_vnoise(cell / 2.0 + vec2(t * 0.8 * (moving + 0.2), 0.0)));
	col = mix(col, vec3(0.82, 0.88, 0.88) * (w3_sky * 0.6 + w3_sun * 0.6 + 0.1), foam * 0.75);
	// sun glints on crests (bloom a little)
	float glint = step(0.996, w3_hash(cell + floor(t * 3.0) * 7.31)) * step(0.55, rip) * (1.0 - w3_night * 0.7);
	col += glint * w3_sun * 1.3;
	// rain rings
	if (w3_wet > 0.05) {
		vec2 rc = floor(cell / 11.0);
		float ph = fract(t * 0.8 + w3_hash(rc) * 3.0);
		vec2 ctr = rc * 11.0 + floor(vec2(w3_hash(rc + 1.0), w3_hash(rc + 2.0)) * 9.0) + 1.0;
		float r = length((cell - ctr) * vec2(1.0, 1.25));
		float ring = step(abs(r - ph * 5.0), 0.5) * (1.0 - ph) * step(w3_hash(rc + floor(t * 0.8 + w3_hash(rc) * 3.0)), w3_wet);
		col += ring * (w3_sky * 0.5 + 0.03);
	}
	// paddies: rice standing in water, rows running across the field
	if (kind > 2.5) {
		float row = mod(cell.y + floor(w3_vnoise(vec2(cell.x / 14.0, 1.0)) * 3.0), 4.0);
		float plant = step(0.32, w3_vnoise(cell / vec2(1.6, 2.4) + vec2(0.0, floor(t * 0.5) * 0.0)));
		float stem = row < 2.5 ? plant : 0.0;
		vec3 rice = rice_col * (row < 0.5 ? 1.18 : (row < 1.5 ? 1.0 : 0.8));
		rice *= 0.9 + 0.2 * w3_hash(floor(cell / 2.0));
		col = mix(col, rice * (w3_sky * 1.1 + w3_sun * 0.95), stem);
	}
	col = w3_apply_fog(col, v_wp, cell);
	v_cell = cell;
	ALBEDO = vec3(0.0);
	EMISSION = col;
	ALPHA = 1.0;
}
