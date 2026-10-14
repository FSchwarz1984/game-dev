// The sea of mist below the region's rim, seen from the lookout (W3Vista): the 遠化 mist lies over
// the lowland like a cloud sea; the road goes down into it (map v2: "山路走下去会溶进雾里"), far
// peaks stand out of it, and through its holes the plain shows, faint ("看得见却不再近").
// A level surface beyond the mist's ellipse; billows from a noise field whose slope lights them in
// three bands from the sun's side; holes where the cover is thin; detail fades with distance so the
// far sea is calm instead of noisy; then the same air as the land.
shader_type spatial;
render_mode world_vertex_coords, unshaded, cull_disabled, fog_disabled, shadows_disabled;
#include "res://render3d/shaders/vista_common.gdshaderinc"

uniform vec3 eye = vec3(0.0);
uniform float time = 0.0;
uniform vec3 lit_col : source_color = vec3(0.95, 0.95, 0.93);
uniform vec3 shade_col : source_color = vec3(0.68, 0.72, 0.82);

varying vec3 v_wp;

void vertex() {
	v_wp = VERTEX;
}

float field(vec2 xz, float lod) {
	vec2 q = xz / 300.0 + vec2(time * 0.0016, time * 0.0007);
	float c = w3_vnoise(q) * 0.55 + w3_vnoise(q * 2.3 + 7.0) * 0.28;
	c += (w3_vnoise(q * 5.3 + 3.0) - 0.5) * 0.34 * (1.0 - lod);
	return c + 0.08;
}

void fragment() {
	vec2 xz = v_wp.xz;
	float dist = length(v_wp - eye);
	float lod = smoothstep(2500.0, 9000.0, dist);
	float e = v_mist_e(xz);
	float c = field(xz, lod);
	// the sea starts at the mist's ellipse, thin there
	c *= smoothstep(0.98, 1.16, e) * 0.35 + 0.65;
	float dz = v_bayer8(FRAGCOORD.xy) - 0.5;
	float th = mix(0.36, 0.3, lod);
	if (c < th + dz * 0.03 || e < 0.98) discard;
	// billows: the noise's slope as a normal, lit from the sun's side in three bands
	float k = 34.0;
	float cx = field(xz + vec2(9.0, 0.0), lod) - c;
	float cz = field(xz + vec2(0.0, 9.0), lod) - c;
	vec3 n = normalize(vec3(-cx * k, 1.0, -cz * k));
	vec3 sd = normalize(w3_sun_dir);
	float l = dot(n, normalize(vec3(sd.x, max(sd.y, 0.15), sd.z)));
	float lvl = l > 0.92 + dz * 0.04 ? 1.0 : (l > 0.75 + dz * 0.04 ? 0.6 : 0.2);
	vec3 col = mix(shade_col, lit_col, lvl);
	// the edges of holes are darker (the mist thins there and the dark plain shows)
	if (c < th + 0.035) col *= 0.86;
	ALBEDO = v_air(col, v_wp, eye, FRAGCOORD.xy);
}
