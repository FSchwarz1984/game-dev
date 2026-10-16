// Characters (and anything drawn as a 2D sprite that must stand in the 3D world): outline class 3.
// The sprite is a leaned card (verticals w3_view.x px per metre like every upright object), texel for
// pixel, anchored at the feet on the pixel lattice. Lit with its normal map through the toon model,
// but with the character protection of the charter: the key light follows the 2D convention (upper
// left, a little in front) instead of the real sun, so she is never back-lit; a brightness floor;
// a cool 1-px rim on the side away from the light; cast shadows (tree dapple, eaves) only dim her
// to 60%, so the canopy reads strong on the ground and weak on her; no dithering anywhere.
// In the shadow pass the card stands upright and turns to face the sun: her shadow is her
// silhouette, true length.
// Mesh: 4 vertices, UV = (0..1) corner, UV2 = corner offset in native px from the pivot (set by
// CharSprite3D from the frame size and pivot).
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled;
stencil_mode write, compare_always, 3;
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform sampler2D sheet : filter_nearest, hint_default_white;    // sRGB values (converted once below)
uniform float ukiyo : hint_range(0.0, 1.0) = 1.0;                 // the round-3 palette (w3_ukiyo_tex, round 5)
uniform sampler2D sheet_n : filter_nearest, hint_normal;
uniform vec4 frame_rect = vec4(0.0, 0.0, 64.0, 64.0);   // px in the sheet: x, y, w, h
uniform bool flip_h = false;
uniform float floor_light = 0.34;      // brightness floor (fraction of the unlit albedo)
uniform float rim = 1.0;
uniform float shadow_dim = 0.6;        // how dark a cast shadow makes her (1 = not at all)
uniform vec4 flash = vec4(1.0, 1.0, 1.0, 0.0);   // rgb, amount (hit / pick-up flashes)
uniform vec3 key_dir_view = vec3(-0.55, 0.60, 0.58);   // the 2D convention key light, view space
uniform float sprite_pitch_deg = 39.33;                 // the pitch the sheets were rendered at
uniform vec2 head_px = vec2(0.5, -35.0);                // this frame's head anchor (px from the pivot, y down)
uniform vec2 pivot_px = vec2(32.0, 65.0);
uniform float face_floor = 0.66;                        // brightness floor on her face under the brim

varying vec3 v_wp;
varying vec3 v_wu;      // the card's upright place (lamps light her where she stands)
varying vec3 v_alb;
varying vec2 v_tex;

void vertex() {
	vec3 anchor = MODEL_MATRIX[3].xyz;
	vec2 off = UV2;
	vec3 wp;
	if (IN_SHADOW_PASS) {
		vec3 r = INV_VIEW_MATRIX[0].xyz;
		r.y = 0.0;
		r = length(r) > 0.001 ? normalize(r) : vec3(1.0, 0.0, 0.0);
		wp = anchor + r * (off.x / w3_view.x) + vec3(0.0, off.y / w3_view.x, 0.0);
	} else {
		vec3 a = anchor + w3_snap(anchor);
		// leaned card: x right, y up 20 px per metre on screen
		wp = a + vec3(off.x / w3_view.x, off.y / w3_view.x, -w3_view.w * off.y / w3_view.x);
	}
	VERTEX = wp;
	v_wp = wp;
	v_wu = anchor + vec3(off.x / w3_view.x, off.y / w3_view.x, 0.0);
}

void fragment() {
	vec2 sheet_size = vec2(textureSize(sheet, 0));
	vec2 uv = UV;
	if (flip_h) uv.x = 1.0 - uv.x;
	vec2 tp = frame_rect.xy + vec2(uv.x, 1.0 - uv.y) * frame_rect.zw;
	ivec2 ti = ivec2(clamp(floor(tp), frame_rect.xy, frame_rect.xy + frame_rect.zw - 1.0));
	vec4 c = texelFetch(sheet, ti, 0);
	if (c.a < 0.5) {
		discard;
	}
	vec3 nm = texelFetch(sheet_n, ti, 0).rgb * 2.0 - 1.0;
	if (flip_h) nm.x = -nm.x;
	// the sheet's normals live in the sprite camera's frame (x right, y up, z to the viewer at the
	// sprite pitch): to world, then to this camera's view space
	float sp = radians(sprite_pitch_deg);
	vec3 nw = vec3(nm.x, nm.y * cos(sp) + nm.z * sin(sp), -nm.y * sin(sp) + nm.z * cos(sp));
	NORMAL = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);
	// the face: a floor of light under the hat's brim (she must read first in any light)
	vec2 rel = vec2(tp.x - frame_rect.x, tp.y - frame_rect.y) - pivot_px;
	if (flip_h) rel.x = -rel.x;
	float face = 1.0 - smoothstep(4.0, 7.0, length((rel - head_px) * vec2(1.0, 1.15)));
	vec3 alb = w3_srgb_to_linear(w3_ukiyo_tex(c.rgb, ukiyo));
	alb = mix(alb, w3_srgb_to_linear(flash.rgb), flash.a);
	// rim: an opaque texel whose neighbour away from the light is empty
	float edge_r = texelFetch(sheet, ti + ivec2(flip_h ? -1 : 1, 0), 0).a;
	float edge_u = texelFetch(sheet, ti + ivec2(0, -1), 0).a;
	float rimk = rim * (edge_r < 0.5 ? 1.0 : 0.0);
	vec3 amb = mix(w3_ground, w3_sky, 0.62) * w3_shade_tint;
	float fl = mix(floor_light, face_floor, face);
	vec3 lum = max(amb, vec3(fl) * (0.62 + 0.38 * (1.0 - w3_night)));
	vec3 em = alb * lum;
	em += rimk * alb * (w3_sky * 1.6 + vec3(0.04)) ;
	em += (edge_u < 0.5 ? 1.0 : 0.0) * alb * w3_sky * 0.35 * rim;
	v_alb = alb;
	ALBEDO = vec3(1.0);
	EMISSION = em;
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 key = normalize(key_dir_view);
		// continuous (round 4): the key wraps round her, never darker than 0.42 of it
		float k = mix(0.42, 1.0, smoothstep(-0.25, 0.65, dot(NORMAL, key)));
		float sh = mix(shadow_dim, 1.0, ATTENUATION);
		DIFFUSE_LIGHT += v_alb * w3_lit_tint * LIGHT_COLOR / W3_PI * k * sh;
	} else {
		// lanterns: engine lights, continuous falloff
		float a = ATTENUATION * (max(dot(NORMAL, LIGHT), 0.0) * 0.5 + 0.5);
		DIFFUSE_LIGHT += v_alb * LIGHT_COLOR / W3_PI * a;
	}
}
