// The land in the view from the lookout (W3Vista): a flat radial mesh around the eye, lifted by the
// height maps in the vertex shader. Near the eye the region's own ground materials (the splat maps
// of the walkable world, its palette); further out forest, rock, fields, terraces, the road, water,
// the plain's field mosaic; toon sun in three bands, the painted shade, aerial perspective and the
// 遠化 mist (vista_common.gdshaderinc). Texture detail is anchored to the world in cells that grow
// with distance, so it stays about one to three pixels wide and never turns to noise.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_back;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform sampler2D m0 : filter_linear, repeat_disable;      // the region's splats (Terrain3D)
uniform sampler2D m1 : filter_linear, repeat_disable;
uniform sampler2D palette : filter_nearest;
uniform vec4 splat_frame = vec4(-80.0, -96.0, 0.25, 0.0);    // origin x, z, cell
uniform vec2 splat_size = vec2(641.0, 833.0);
uniform vec4 local_bounds = vec4(-80.0, -96.0, 80.0, 112.0);
uniform vec3 eye = vec3(0.0);

varying vec3 v_wp;
varying vec3 v_n;
varying vec3 v_alb;

void vertex() {
	vec2 xz = VERTEX.xz;
	float h = v_height(xz);
	float d = length(xz - eye.xz);
	float e = max(0.6, d * 0.006);
	float hx = v_height(xz + vec2(e, 0.0)) - v_height(xz - vec2(e, 0.0));
	float hz = v_height(xz + vec2(0.0, e)) - v_height(xz - vec2(0.0, e));
	v_n = normalize(vec3(-hx, 2.0 * e, -hz));
	VERTEX = vec3(xz.x, h, xz.y);
	v_wp = VERTEX;
	NORMAL = v_n;
}

vec3 pal(float row, float tone) {
	vec3 c = texelFetch(palette, ivec2(int(clamp(floor(tone + 0.5), 0.0, 7.0)), int(row)), 0).rgb;
	return w3_srgb_to_linear(c);
}

vec3 srgb(vec3 c) { return w3_srgb_to_linear(c); }

void fragment() {
	vec3 wp = v_wp;
	vec2 xz = wp.xz;
	float dist = length(wp - eye);
	// texture cell: about a pixel and a half wide at this distance (fine grain near, never blocks)
	float tc = max(0.02, dist * 0.0028);
	vec2 cell = floor(xz / tc);
	float n1 = w3_hash(cell);
	float clump = w3_vnoise(xz / max(3.0, dist * 0.02));
	vec3 n = normalize(v_n);
	float slope = degrees(acos(clamp(n.y, 0.0, 1.0)));
	vec3 alb;
	bool water = false;
	bool local = xz.x > local_bounds.x && xz.x < local_bounds.z && xz.y > local_bounds.y && xz.y < local_bounds.w;
	if (local) {
		// the walkable region: its dominant ground material and palette tone
		vec2 uv = (xz - splat_frame.xy) / splat_frame.z / splat_size;
		vec4 a = texture(m0, uv);
		vec4 b = texture(m1, uv);
		float w[8] = float[8](a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a);
		int best = 0;
		float bw = -1.0;
		for (int k = 0; k < 8; k++) {
			float wk = w[k] + (w3_hash(cell + float(k) * 3.1) - 0.5) * 0.2;
			if (wk > bw) { bw = wk; best = k; }
		}
		float rows[8] = float[8](0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 9.0, 10.0);
		float tone = 3.5 + floor((clump - 0.5) * 2.4 + 0.5) + (n1 < 0.12 ? -1.0 : (n1 > 0.9 ? 1.0 : 0.0));
		alb = pal(rows[best], tone);
		// the terraces' paddies: water holding the sky, young rice in sparse rows across it
		if (best == 7) {
			water = true;
		}
	} else {
		vec4 md = v_mid_data(xz);
		vec4 mt = v_mat_data(xz);
		float mw = v_mid_weight(xz);
		vec4 fd = v_far_data(xz);
		float forest = mix(fd.b, md.b, mw);
		float wat = mix(fd.a, md.a, mw);
		float cult = mt.r * mw;
		float road = mt.g * mw;
		float rock = max(mt.b * mw, smoothstep(44.0, 56.0, slope));
		bool plain = wp.y < -280.0 && slope < 6.0;
		// grass and scrub as the base
		float tone = 3.4 + floor((clump - 0.5) * 2.6 + 0.5) + (n1 < 0.14 ? -1.0 : (n1 > 0.9 ? 1.0 : 0.0));
		alb = pal(n1 > 0.55 && clump > 0.6 ? 1.0 : 0.0, tone);
		if (plain) {
			// the plain: a mosaic of paddies and dry fields, dark lines of hedges and lanes
			vec2 fc = floor(xz / vec2(46.0, 34.0));
			float fh = w3_hash(fc + 7.0);
			vec2 ff = fract(xz / vec2(46.0, 34.0));
			vec3 c0 = fh < 0.45 ? srgb(vec3(0.43, 0.52, 0.27)) : (fh < 0.7 ? srgb(vec3(0.52, 0.55, 0.3)) : (fh < 0.85 ? srgb(vec3(0.56, 0.5, 0.33)) : srgb(vec3(0.36, 0.43, 0.25))));
			alb = c0;
			if (min(min(ff.x, ff.y), min(1.0 - ff.x, 1.0 - ff.y)) < tc / 40.0) alb *= 0.7;
			if (w3_hash(floor(xz / 420.0)) > 0.8 && w3_vnoise(xz / 60.0) > 0.7) alb = srgb(vec3(0.32, 0.3, 0.27));   // a village
		}
		if (cult > 0.5) {
			// terraces and fields: bright young rice, flooded strips catching the sky
			float row = floor((wp.y + w3_vnoise(xz / 30.0) * 2.0) / 1.6);
			float rh = w3_hash(vec2(row, 3.0));
			alb = rh < 0.3 ? srgb(vec3(0.5, 0.6, 0.3)) : srgb(vec3(0.45, 0.56, 0.28));
			if (rh > 0.78) { water = true; }
			// the risers: grass banks, darker
			if (fract((wp.y + w3_vnoise(xz / 30.0) * 2.0) / 1.6) < 0.18) alb = pal(0.0, 2.5);
		}
		if (forest > 0.4 && !plain) {
			// canopy seen from above: dark clumps, lit crowns
			float k = w3_vnoise(xz / max(4.0, dist * 0.012) + 3.0);
			alb = k > 0.62 ? srgb(vec3(0.27, 0.36, 0.19)) : (k > 0.35 ? srgb(vec3(0.2, 0.29, 0.16)) : srgb(vec3(0.13, 0.2, 0.12)));
		}
		if (rock > 0.5) {
			// rock faces: bands along the height (strata), in clusters, not salt and pepper
			float k = w3_vnoise(vec2((xz.x + xz.y) / max(6.0, dist * 0.03), wp.y / max(1.2, dist * 0.006)));
			alb = pal(4.0, 2.6 + floor((k - 0.5) * 2.2 + 0.5));
		}
		if (road > 0.5) {
			alb = pal(2.0, 4.0 + (n1 < 0.2 ? -1.0 : 0.0));
		}
		if (wat > 0.5) {
			water = true;
		}
	}
	if (water) {
		// water: the sky's colour, a lighter line here and there where the wind ruffles it
		// (a calm, dim mirror: young rice and the mud under the shallow water darken it)
		vec3 sky = mix(haze_col, w3_sky * 1.6, 0.35);
		alb = mix(sky * 0.5, pal(0.0, 3.0), 0.3);
		if (w3_vnoise(vec2(xz.x * 0.4, xz.y * 2.0) + TIME * 0.05) > 0.82) alb = sky * 0.72;
		v_alb = alb;
		ALBEDO = vec3(0.0);
		EMISSION = v_air(alb, wp, eye, FRAGCOORD.xy);
	} else {
		v_alb = alb;
		ALBEDO = vec3(1.0);
		EMISSION = v_air(w3_ambient(alb, n, 1.0), wp, eye, FRAGCOORD.xy);
	}
}

void light() {
	if (LIGHT_IS_DIRECTIONAL) {
		vec3 c = v_sun_bands(v_alb, NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, FRAGCOORD.xy);
		// the sun's share fades with the same air as the rest
		DIFFUSE_LIGHT += c * v_air_keep(v_wp, eye, FRAGCOORD.xy);
	}
}
