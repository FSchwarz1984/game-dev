// Body of the solid toon material (props, buildings, rocks, wood, stone). Included by the class
// files toon_solid*.gdshader, which only differ in their outline class (stencil reference).
// Vertex data: COLOR.rgb = albedo (sRGB), COLOR.a = baked ambient occlusion (1 open .. 0 enclosed);
// UV = texture uv (albedo_mode 1); UV2.x = surface pattern id, UV2.y = pattern amount
// (pixel_toon.gdshaderinc, w3_pattern). Normals are the true (upright) normals.
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

uniform vec4 tint : source_color = vec4(1.0);
// 0: vertex colour only; 1: uv texture x vertex colour; 2: screen-painted texture, texel for pixel,
// placed so that texture pixel screen_origin_px sits on the object's origin (snap the origin)
uniform int albedo_mode : hint_range(0, 2) = 0;
uniform sampler2D albedo_tex : source_color, filter_nearest, hint_default_white;
uniform vec2 screen_origin_px = vec2(0.0);
uniform float lean : hint_range(0.0, 1.0) = 1.0;       // 1 upright object (leans back), 0 ground-hugging
uniform float porosity : hint_range(0.0, 1.0) = 0.7;   // how much rain darkens it
uniform float dither : hint_range(0.0, 1.0) = 1.0;     // (unused since round 4: the light is continuous)
uniform float vertex_ao : hint_range(0.0, 1.0) = 1.0;  // use COLOR.a as ambient occlusion
uniform vec3 emission_color : source_color = vec3(0.0);
uniform float emission_energy = 0.0;                    // > 1 blooms (only light sources)
uniform float emission_at_night : hint_range(0.0, 1.0) = 0.0;  // 1: emission follows w3_night
uniform float far : hint_range(0.0, 1.0) = 0.0;         // 遠化: 0 near .. 1 lost its qualities (pale, flat)
uniform float shade_fill : hint_range(0.0, 1.0) = 0.0;  // share of the sun that still reaches its shade (big trunks under a crown)
uniform bool cutaway = false;                           // stipple out where it hides her (roofs)
uniform float cutaway_scale = 1.0;

varying vec3 v_wp;
varying vec3 v_wu;      // upright (un-leaned) world position: lamps light the real place
varying vec3 v_wn;
varying flat vec2 v_origin_px;
varying vec2 v_cell;

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 wp = VERTEX;
	v_wu = wp;
	if (!IN_SHADOW_PASS) {
		wp = w3_lean(wp, origin.y, lean);
	}
	VERTEX = wp;
	v_wp = wp;
	v_wn = NORMAL;
	v_origin_px = w3_screen(origin);
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	// (never in the shadow pass: the cut-away is for the eye, the shadow stays whole)
	if (cutaway && !IN_SHADOW_PASS && w3_cutaway_r(v_wp, cell, cutaway_scale)) {
		discard;
	}
	vec3 wn = normalize(v_wn);
	vec3 alb = w3_srgb_to_linear(COLOR.rgb) * tint.rgb;
	if (albedo_mode == 1) {
		alb *= texture(albedo_tex, UV).rgb;
	} else if (albedo_mode == 2) {
		vec2 d = cell + 0.5 - round(v_origin_px);
		ivec2 tp = ivec2(floor(screen_origin_px + vec2(d.x, -d.y)));
		alb *= texelFetch(albedo_tex, tp, 0).rgb;
	}
	alb = w3_pattern(alb, UV2.x, UV2.y, v_wp, wn, cell);
	alb = w3_wetten(alb, porosity);
	alb = w3_far(alb, far);
	float ao = mix(1.0, COLOR.a, vertex_ao);
	v_cell = cell;
	// the engine adds the ambient (sky colour, VoxelGI bounce, SSAO) times this albedo and AO
	ALBEDO = alb;
	AO = ao;
	AO_LIGHT_AFFECT = 0.0;
	vec3 em = emission_color * emission_energy * mix(1.0, w3_night, emission_at_night) * (1.0 - far);
	// a faded thing's light flattens: its shade is lifted toward the haze
	EMISSION = em + alb * w3_sky * 0.35 * far;
	if (w3_bake > 0.5) {
		ALBEDO = vec3(0.0);
		EMISSION = w3_bake_out(alb, wn, ao, 0.0);
	}
}

void light() {
	float k = w3_far_light(far);
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 c = w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.3);
		// big trunks under a crown: a share of the light reaches their shade anyway (continuous)
		if (shade_fill > 0.0) {
			float lit = w3_wrap(dot(NORMAL, LIGHT), 0.3) * ATTENUATION;
			c += LIGHT_COLOR / W3_PI * shade_fill * (1.0 - lit);
		}
		DIFFUSE_LIGHT += c * k;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.4) * k;
	}
}
