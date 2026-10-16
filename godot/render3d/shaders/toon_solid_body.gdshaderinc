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
uniform bool cutaway = false;                           // stipple out where it hides her (roofs, trees)
uniform float cutaway_scale = 1.0;
uniform float cutaway_keep_px = 0.0;                    // > 0: what lies this far above her stays
// one object seen through as a whole (the cut-away mode "fade", round 4 item 4: trunk, limbs and
// leaves of one tree go together): the share of its pixels let through, set per instance
instance uniform float obj_fade = 0.0;
// big masses of light and shade (G5R2 review, "大块明暗 + 局部细节"): the shade shows this share less
// of the surface's painted detail (texture grain, the pattern's specks, cracks and boards); the
// sun puts it back where it falls
uniform float shade_flatten : hint_range(0.0, 1.0) = 0.55;

varying vec3 v_wp;
varying vec3 v_wu;      // upright (un-leaned) world position: lamps light the real place
varying vec3 v_wn;
varying flat vec2 v_origin_px;
varying vec2 v_cell;
varying vec3 v_detail;      // detailed albedo / the shade's flattened albedo (light() restores the detail)
varying flat float v_base_y;
varying float v_sun_open;   // under a dense crown, near the ground: 0 (the sun only as flecks), else 1
varying float v_fleck_s;    // the ground's soft sun flecks (pixel_toon w3_fleck) on what stands low under a crown

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
	v_base_y = origin.y;
}

void fragment() {
	vec2 cell = w3_ptex(v_wp);
	// (never in the shadow pass: the cut-away is for the eye, the shadow stays whole)
	if (cutaway && !IN_SHADOW_PASS && w3_cutaway_k(v_wp, cell, cutaway_scale, cutaway_keep_px)) {
		discard;
	}
	if (obj_fade > 0.0 && !IN_SHADOW_PASS && w3_stipple(cell) < obj_fade) {
		discard;
	}
	// (round 5, the lead: on the steps and stones under the great camphor the shadow map's gaps read as
	// hard-edged yellow patches. What stands low under a dense crown (the steps, stones, the feet of
	// things: fading out from 2 to 4 m above its base) takes the ground's light there: the crown's
	// shade, and the ground's soft flecks where the sun gets through; terrain3d.gd w3_canopy)
	float low = 1.0 - smoothstep(2.0, 4.0, v_wu.y - v_base_y);
	v_sun_open = 1.0;
	v_fleck_s = 0.0;
	if (low > 0.0 && w3_canopy_frame.z > 0.0) {
		vec3 sdir = normalize(w3_sun_dir);
		vec2 proj = v_wu.xz + sdir.xz / max(sdir.y, 0.25) * max(11.0 - (v_wu.y - v_base_y), 1.0);
		float can = w3_canopy_at(proj);
		v_sun_open = mix(1.0, w3_canopy_open(can), low);
		v_fleck_s = (can > 0.2 && w3_night < 0.5) ? w3_fleck(proj, can) * low : 0.0;
	}
	vec3 wn = normalize(v_wn);
	vec3 alb = w3_srgb_to_linear(COLOR.rgb) * tint.rgb;
	vec3 flat_alb = alb;
	if (albedo_mode == 1) {
		vec3 tc = texture(albedo_tex, UV).rgb;
		alb *= tc;
		// the texture's local mean (five taps two texels apart): its grain without the specks
		vec2 ts = 2.0 / vec2(textureSize(albedo_tex, 0));
		vec3 tm = tc + texture(albedo_tex, UV + vec2(ts.x, 0.0)).rgb + texture(albedo_tex, UV - vec2(ts.x, 0.0)).rgb
				+ texture(albedo_tex, UV + vec2(0.0, ts.y)).rgb + texture(albedo_tex, UV - vec2(0.0, ts.y)).rgb;
		flat_alb *= tm * 0.2;
	} else if (albedo_mode == 2) {
		vec2 d = cell + 0.5 - round(v_origin_px);
		ivec2 tp = ivec2(floor(screen_origin_px + vec2(d.x, -d.y)));
		alb *= texelFetch(albedo_tex, tp, 0).rgb;
		flat_alb = alb;
	}
	alb = w3_pattern(alb, UV2.x, UV2.y, v_wp, wn, cell);
	alb = w3_wetten(alb, porosity);
	alb = w3_far(alb, far);
	flat_alb = w3_far(w3_wetten(flat_alb, porosity), far);
	float ao = mix(1.0, COLOR.a, vertex_ao);
	v_cell = cell;
	// the engine adds the ambient (sky colour, VoxelGI bounce, SSAO) times ALBEDO and AO: the shade
	// gets the flattened colour; light() puts the detail back into the direct light
	// and the painter's shade colour (w3_shade_tint, blue-green by day): only the ambient sees it,
	// v_detail undoes it in the direct light
	// (round 5: the round-3 painted shade, w3_paint_shade: the hue turned cool, the chroma kept)
	vec3 a_shade = w3_paint_shade(mix(alb, flat_alb, w3_flatten(shade_flatten)));
	v_detail = alb / max(a_shade, vec3(1e-4));
	ALBEDO = a_shade;
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
		// (round 5: round 3's levels, continuous: w3_sun_level)
		// (under a dense crown, near the ground: the crown's shade and the flecks, as the ground)
		float att = ATTENUATION * v_sun_open;
		float sh = max(att, v_fleck_s);
		vec3 c = w3_sun_level(NORMAL, LIGHT, LIGHT_COLOR, sh, false, 0.3);
		// big trunks under a crown: a share of the light reaches their shade anyway (continuous)
		c *= v_detail;
		if (shade_fill > 0.0) {
			float lit = mix(w3_r3_body(dot(NORMAL, LIGHT)), w3_wrap(dot(NORMAL, LIGHT), 0.3), w3_night) * sh;
			c += LIGHT_COLOR / W3_PI * shade_fill * (1.0 - lit);
		}
		DIFFUSE_LIGHT += (c + w3_shadow_fill(att)) * k;
	} else {
		DIFFUSE_LIGHT += w3_direct(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, 0.4) * v_detail * k;
	}
}
