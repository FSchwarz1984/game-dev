// Trees, the great camphor, the hut, the shrine and the graves in the view from the lookout
// (W3Vista), as impostors baked from the real assets (render3d/dev/impostor_bake.gd, packed by
// tools/world3d/vista_impostors.py): each instance draws one frame of the atlas, the level of
// detail nearest its size on screen and the direction nearest the camera's (chosen by W3Vista),
// texel for pixel: the quad is built in screen pixels around the foot, which sits on a whole pixel,
// so the frame never resamples and a pan moves it by whole pixels. Lit like the world's own
// foliage and wood (toon sun bands, the painted shade, the leaves' quieter lit side and their
// sunlit rim) from the baked normals; then the vista's air.
// Instance: transform origin = the foot; basis columns 0, 1, 2 = (rect x, y), (rect w, h), (pivot x,
//   y) in atlas texels; INSTANCE_CUSTOM.a = the frame's yaw in world space (radians).
// Mesh: a quad with UV (0, 0) at the top-left corner.
shader_type spatial;
render_mode ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform sampler2D atlas_a : filter_nearest, repeat_disable;   // albedo (sRGB), A: 0 empty, .5 wood, 1 leaves
uniform sampler2D atlas_n : filter_nearest, repeat_disable;   // normal * .5 + .5 (bake frame), A: AO
uniform float hero_leaf_ukiyo = 0.4;   // the heroes' leaves (the great camphor): round 3's palette in part (w3_ukiyo_tex)
uniform int r3_page_h = 0;          // rows of the atlas that are round 3's page (round 5); the heroes' page below
uniform vec3 eye = vec3(0.0);
uniform float emission_night = 0.0;                            // the lit windows of the buildings (later)
uniform bool debug_quads = false;

varying vec3 v_wp;
varying vec2 v_tex;
varying flat float v_yaw;
varying flat float v_seed;

void vertex() {
	// the frame rides in the instance's basis (full floats): column 0 = rect x, y; column 1 = rect
	// w, h; column 2 = pivot x, y (the shader never transforms anything by the basis)
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	vec2 rxy = MODEL_MATRIX[0].xy;
	vec2 rwh = MODEL_MATRIX[1].xy;
	vec2 piv = MODEL_MATRIX[2].xy;
	// built in screen pixels (y up): the foot moved onto the lattice of pixel corners, the corners
	// whole pixels away from it (vista_common: the projection)
	vec2 foot = v_snap(v_px_of(o, eye));
	vec2 off = vec2(UV.x * rwh.x - piv.x, piv.y - UV.y * rwh.y);
	POSITION = v_clip(foot + off, length(o - eye), PROJECTION_MATRIX);
	v_tex = rxy + UV * rwh;
	v_wp = o;
	v_yaw = c.a;
	v_seed = fract(o.x * 0.137 + o.z * 0.071);
}

varying vec3 v_alb;
varying vec3 v_alb_sun;
varying float v_leaf;

void fragment() {
	ivec2 tp = ivec2(floor(v_tex));
	vec4 a = texelFetch(atlas_a, tp, 0);
	if (a.a < 0.25) {
		if (debug_quads) { ALBEDO = vec3(0.0); EMISSION = vec3(fract(v_tex.x / 64.0), fract(v_tex.y / 64.0), 1.0); NORMAL = vec3(0.0, 0.0, 1.0); v_alb = vec3(0.0); v_alb_sun = vec3(0.0); v_leaf = 0.0; } else {
		discard; }
	} else {
	vec4 nt = texelFetch(atlas_n, tp, 0);
	vec3 nb = normalize(nt.rgb * 2.0 - 1.0);
	// from the bake's frame (the asset turned so its frame direction faces +Z) into the world
	float cy = cos(v_yaw);
	float sy = sin(v_yaw);
	vec3 n = vec3(cy * nb.x + sy * nb.z, nb.y, -sy * nb.x + cy * nb.z);
	float leaf = a.a > 0.75 ? 1.0 : 0.0;
	// (round 5: the trees come from round 3's page of the atlas, baked when the leaves were drawn
	// deeper; the heroes' page below it was baked in round 4: the great camphor's leaves, painted since
	// for one conversion, take a part of round 3's palette as they do in the world, sample.gd
	// ONE_CONVERSION_LEAVES)
	if (leaf > 0.5 && r3_page_h > 0 && tp.y >= r3_page_h) {
		a.rgb = w3_ukiyo_tex(a.rgb, hero_leaf_ukiyo);
	}
	vec3 alb = w3_srgb_to_linear(a.rgb);
	// a little variety between trees of one kind
	alb *= 0.94 + 0.12 * v_seed;
	float ao = nt.a;
	v_alb = alb;
	// leaves in the sun: quieter, a little darker than a surface (the world's foliage, v1.4)
	vec3 lab = w3_lin_to_oklab(alb);
	// (round 5: round 3's again: its atlas carries round 3's deeper leaves)
	v_alb_sun = (leaf > 0.5 && lab.y < 0.0) ? max(w3_oklab_to_lin(vec3(lab.x, lab.yz * 0.72)), vec3(0.0)) * 0.88 : alb;
	v_leaf = leaf;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ALBEDO = vec3(1.0);
	EMISSION = v_air(w3_ambient(alb, n, ao), v_wp, eye, FRAGCOORD.xy);
	}
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		// continuous (round 4); round 3's levels by day (round 5, w3_r3_body), the leaves facing the
		// sun a touch brighter
		float ndl = dot(NORMAL, LIGHT);
		float band = mix(w3_r3_body(ndl), w3_wrap(ndl, 0.25), w3_night);
		vec3 c = v_alb_sun * w3_lit_tint * LIGHT_COLOR / W3_PI * band;
		if (v_leaf > 0.5) {
			c *= mix(vec3(1.0), vec3(1.13, 1.12, 1.06), smoothstep(0.65, 0.95, ndl));
		}
		DIFFUSE_LIGHT += c * v_air_keep(v_wp, eye, FRAGCOORD.xy);
	}
}
