// Trees, bamboo, houses and the 「隔」 tower in the view from the lookout (W3Vista), as impostors:
// upright quads turned to the camera about their vertical axis, the silhouette drawn by a signed
// distance in the quad (so its edge is crisp at any size and has a one-pixel darker rim), lit on the
// sun's side in two tones with a darker core, then the same air as the land.
// Instance: transform origin = the foot; INSTANCE_CUSTOM = (kind, height m, width m, seed 0..1).
// kind: 0 cedar, 1 red pine, 2 broadleaf, 3 bamboo, 4 maple (red), 5 farmhouse, 6 the tower,
//       7 broadleaf (persimmon, the camphor's neighbours), 8 water-wheel
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled, depth_prepass_alpha;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);

varying vec3 v_wp;
varying flat vec4 v_cus;
varying vec2 v_q;              // x: -0.5..0.5 of the width, y: 0..1 of the height
varying flat vec3 v_right;
varying flat float v_pxh;      // the impostor's height on screen, px

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	vec4 c = INSTANCE_CUSTOM;
	float h = c.y;
	float w = c.z;
	vec3 to_cam = eye - o;
	vec3 right = normalize(vec3(to_cam.z, 0.0, -to_cam.x) + vec3(1e-4, 0.0, 0.0));
	v_q = vec2(UV.x - 0.5, 1.0 - UV.y);
	vec3 wp = o + right * v_q.x * w + vec3(0.0, v_q.y * h - 0.15, 0.0);
	VERTEX = wp;
	v_wp = wp;
	v_cus = c;
	v_right = right;
	NORMAL = normalize(vec3(to_cam.x, 0.0, to_cam.z));
	v_pxh = abs(v_px_of(o + vec3(0.0, h, 0.0), eye).y - v_px_of(o, eye).y);
	POSITION = v_project(wp, eye, PROJECTION_MATRIX);
}

float sd_circle(vec2 p, vec2 c, float r) { return length(p - c) - r; }
float sd_ellipse(vec2 p, vec2 c, vec2 r) { return (length((p - c) / r) - 1.0) * min(r.x, r.y); }
float sd_box(vec2 p, vec2 c, vec2 b) { vec2 d = abs(p - c) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
float sd_seg(vec2 p, vec2 a, vec2 b, float r) {
	vec2 pa = p - a, ba = b - a;
	float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * h) - r;
}

// silhouette of each kind (p in metres: x across, y up from the foot) as (distance, part, light):
// part 0 foliage, 1 trunk / wood, 2 roof, 3 wall; light -1..1, the clump's own sun side (clusters
// lit top and sunward, dark beneath: the way trees are painted in pixel art); sun2 = the sun's
// direction in the quad's plane
vec3 shape(int kind, vec2 p, float h, float w, float seed, vec2 sun2, float far_k) {
	float n = w3_vnoise(p * 1.7 + seed * 40.0);
	if (kind == 0) {
		// cedar: a tall cone in jagged tiers on a short trunk; each tier lit along its top
		float y = p.y / h;
		float tier = fract(y * 8.0 + seed);
		float half_w = w * 0.5 * pow(clamp(1.0 - y, 0.0, 1.0), 0.85) * (0.8 + 0.24 * tier) * (y > 0.1 ? 1.0 : 0.0);
		float df = abs(p.x) - half_w + (n - 0.5) * 0.25;
		float dt = sd_box(p, vec2(0.0, h * 0.06), vec2(w * 0.05, h * 0.07));
		float l = (tier - 0.5) * 1.2 + p.x / max(w * 0.5, 0.01) * sun2.x * 0.8;
		return df < dt ? vec3(df, 0.0, l) : vec3(dt, 1.0, 0.0);
	} else if (kind == 1) {
		// red pine: a leaning trunk and flat plates of needles, lit on top, dark underneath
		float lean = (seed - 0.5) * 0.35;
		float dt = sd_seg(p, vec2(0.0, 0.0), vec2(lean * h, h * 0.86), w * 0.035);
		float df = 1e3;
		float l = 0.0;
		for (int i = 0; i < 4; i++) {
			float fi = float(i);
			float yy = h * (0.52 + fi * 0.13);
			float xx = lean * yy + (w3_hash(vec2(seed * 10.0, fi)) - 0.5) * w * 0.4;
			vec2 r = vec2(w * (0.36 - fi * 0.06), h * 0.055);
			float e = sd_ellipse(p, vec2(xx, yy), r);
			e = max(e, -(p.y - (yy - r.y * 0.45)));       // flat underside
			e += (n - 0.5) * 0.35;
			if (e < df) {
				df = e;
				l = (p.y - yy) / r.y * 0.9 + (p.x - xx) / r.x * sun2.x * 0.5;
			}
		}
		return df < dt ? vec3(df, 0.0, l) : vec3(dt, 1.0, 0.0);
	} else if (kind == 2 || kind == 4 || kind == 7) {
		// broadleaf: an irregular crown of clumps, broader than tall with an uneven top; each clump
		// lit on its own sun side; the trunk shows only below the crown and only near
		float df = 1e3;
		float l = 0.0;
		for (int i = 0; i < 8; i++) {
			float fi = float(i);
			float hx = w3_hash(vec2(fi, seed * 7.0));
			float hy = w3_hash(vec2(fi + 9.0, seed * 3.0));
			vec2 c = vec2((hx - 0.5) * w * 0.62, h * (0.5 + hy * 0.32));
			float r = w * (0.17 + 0.1 * w3_hash(vec2(fi * 3.0, seed)));
			float d = length(p - c) - r;
			if (d < df) {
				df = d;
				vec2 nn = (p - c) / r;
				l = dot(nn, sun2) * 0.9 + nn.y * 0.35;
			}
		}
		df += (n - 0.5) * 0.45 * (1.0 - far_k * 0.6);
		float dt = sd_box(p, vec2(0.0, h * 0.2), vec2(w * 0.04, h * 0.22));
		if (far_k > 0.6) dt = 1e3;
		return df < dt ? vec3(df, 0.0, l) : vec3(dt, 1.0, 0.0);
	} else if (kind == 3) {
		// bamboo: slim culms bending over into feathery tufts
		float df = 1e3;
		for (int i = 0; i < 5; i++) {
			float fi = float(i);
			float x0 = (fi - 2.0) * w * 0.12;
			float bend = (w3_hash(vec2(fi, seed * 3.0)) - 0.3) * w * 0.4;
			df = min(df, sd_seg(p, vec2(x0, 0.0), vec2(x0 + bend, h * (0.85 + 0.15 * w3_hash(vec2(seed, fi)))), w * 0.018));
		}
		float top = 1e3;
		float l = 0.0;
		for (int i = 0; i < 5; i++) {
			float fi = float(i);
			vec2 c = vec2((w3_hash(vec2(fi, seed)) - 0.5) * w * 0.7, h * (0.6 + 0.3 * w3_hash(vec2(seed, fi + 4.0))));
			float r = w * 0.22;
			float d = length((p - c) / vec2(1.0, 0.7)) - r + (w3_vnoise(p * 3.1 + seed * 9.0) - 0.5) * 0.5;
			if (d < top) { top = d; l = dot((p - c) / r, sun2) * 0.8; }
		}
		return top < df ? vec3(top, 0.0, l) : vec3(df, 1.0, 0.0);
	} else if (kind == 5) {
		// a farmhouse: thatched hipped roof over pale walls
		float roof = max(sd_box(p, vec2(0.0, h * 0.62), vec2(w * 0.5, h * 0.38)), (abs(p.x) - w * 0.5) + (p.y - h * 0.3) * 0.6);
		float wall = sd_box(p, vec2(0.0, h * 0.18), vec2(w * 0.4, h * 0.18));
		float l = p.x / w * sun2.x * 2.0 + 0.2;
		return roof < wall ? vec3(roof, 2.0, l) : vec3(wall, 3.0, l);
	} else if (kind == 6) {
		// the 「隔」 tower: four legs drawn in, braced in X, a platform near the top, a mast
		float y = p.y / h;
		float half_w = w * 0.5 * mix(1.0, 0.18, pow(y, 0.8));
		float legs = min(abs(p.x - half_w), abs(p.x + half_w)) - 0.22;
		float fy = fract(y * 7.0);
		float braces = 1e3;
		if (y < 0.86) {
			float xx = (fy * 2.0 - 1.0) * half_w;
			braces = min(abs(p.x - xx), abs(p.x + xx)) - 0.16;
			braces = min(braces, fy * h / 7.0 - 0.12);
			braces = max(braces, abs(p.x) - half_w);
		}
		float plat = sd_box(p, vec2(0.0, h * 0.86), vec2(half_w + 0.8, 0.35));
		float mast = sd_box(p, vec2(0.0, h * 0.93), vec2(0.18, h * 0.07));
		float d = min(min(legs, braces), min(plat, mast));
		d = max(d, p.y - h);
		d = max(d, abs(p.x) - (half_w + 0.9));
		return vec3(d, 1.0, 0.0);
	} else {
		// the water-wheel: a ring with spokes
		vec2 c = vec2(0.0, h * 0.5);
		float r = h * 0.48;
		float ring = abs(length(p - c) - r) - 0.15;
		float a = atan(p.y - c.y, p.x - c.x);
		float sp = abs(fract(a / 6.2831853 * 8.0 + TIME * 0.05) - 0.5) * r * 0.8 - 0.1;
		float d = min(ring, max(sp, length(p - c) - r));
		return vec3(d, 1.0, 0.0);
	}
}

void fragment() {
	int kind = int(v_cus.x + 0.5);
	float h = v_cus.y;
	float w = v_cus.z;
	float seed = v_cus.w;
	vec2 p = vec2(v_q.x * w, v_q.y * h);
	vec3 sd = normalize(w3_sun_dir);
	vec2 sun2 = normalize(vec2(dot(v_right, sd), max(sd.y, 0.2)));
	float far_k = 1.0 - smoothstep(14.0, 40.0, v_pxh);
	vec3 sp = shape(kind, p, h, w, seed, sun2, far_k);
	// one native pixel in these units
	float px = h / max(v_pxh, 1.0);
	if (sp.x > 0.0) discard;
	int part = int(sp.y + 0.5);
	vec3 alb;
	if (kind == 0) alb = part == 0 ? vec3(0.18, 0.27, 0.2) : vec3(0.3, 0.2, 0.14);
	else if (kind == 1) alb = part == 0 ? vec3(0.28, 0.36, 0.2) : vec3(0.5, 0.26, 0.17);
	else if (kind == 2) alb = part == 0 ? mix(vec3(0.29, 0.38, 0.19), vec3(0.33, 0.4, 0.18), seed) : vec3(0.3, 0.24, 0.18);
	else if (kind == 3) alb = part == 0 ? vec3(0.42, 0.5, 0.25) : vec3(0.48, 0.55, 0.3);
	else if (kind == 4) alb = part == 0 ? vec3(0.6, 0.22, 0.16) : vec3(0.3, 0.22, 0.17);
	else if (kind == 5) alb = part == 2 ? vec3(0.48, 0.4, 0.28) : vec3(0.75, 0.72, 0.62);
	else if (kind == 6) alb = vec3(0.32, 0.27, 0.25);
	else if (kind == 7) alb = part == 0 ? vec3(0.3, 0.38, 0.19) : vec3(0.3, 0.24, 0.18);
	else alb = vec3(0.38, 0.3, 0.22);
	alb = w3_srgb_to_linear(alb);
	// the clump's sun side lighter, its underside darker (three tones), a dark rim near
	float nz = w3_vnoise(p * 2.3 + seed * 13.0);
	float tone = sp.z + (nz - 0.5) * 0.45;
	float k = tone > 0.32 ? 1.16 : (tone < -0.3 ? 0.66 : 0.9);
	if (part == 0 && w3_hash(floor(p / max(px, 0.05))) < 0.05) k *= 0.85;
	if (sp.x > -px * 1.05 && v_pxh > 10.0) k = min(k, 0.6);
	// light: the painted shade everywhere, the sun on the lit tones (impostors are lit here, not in
	// light(): their quads face the camera, a normal would tell nothing)
	vec3 col = w3_ambient(alb * k, vec3(0.0, 1.0, 0.0), 1.0);
	float sun_k = k > 1.0 ? 1.0 : (k > 0.8 ? 0.5 : 0.1);
	col += alb * k * w3_lit_tint * w3_sun / W3_PI * sun_k * clamp(sd.y * 2.0 + 0.4, 0.0, 1.0);
	ALBEDO = vec3(0.0);
	// (in the 遠化: the crowns from the green block, red leaves, trunks and the wheel from the earths)
	int plate = (part == 0 && kind != 4 && kind != 5 && kind != 6 && kind < 8) ? V_GREEN : V_EARTH;
	EMISSION = v_print(v_air(col, v_wp, eye, FRAGCOORD.xy), v_flat(plate, alb), plate, vec3(0.0, 1.0, 0.0), v_wp, eye, FRAGCOORD.xy);
}
