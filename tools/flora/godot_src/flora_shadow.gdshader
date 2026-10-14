// Cast shadow of a plant on the ground. Own work, CC0. docs/knowledge/18-vegetation.md
// The texture holds the shade cast by the sun at the reference elevation (meta.json sun_ref):
// R = crown, G = trunk, B = contact shade where the plant meets the ground (does not depend on the
// sun; stays at night). Two nodes: channel 0 draws the cast shadow (crown and trunk together, the
// darker of the two, so the trunk's shadow inside the crown's is not darker twice), channel 2 the
// contact shade. As the sun's elevation changes (sun_elev_deg, the same value the terrain uses)
// the trunk shadow stretches from the foot along the shadow direction, and the crown shadow slides
// along it and lengthens: continuously, never a jump (R-7). The quad is enlarged in vertex() to
// hold the moved shadow; fragment() maps each pixel back to the texel it shows (nearest), so the
// shadow stays crisp pixel art at every length.
// Set for every plant at once by FloraField: sun_elev_deg, shade_color (from the sun and sky colours,
// so a tree's shadow on open ground is as dark as a cliff's), shadow_strength.
shader_type canvas_item;
render_mode unshaded, blend_mul;

uniform int channel = 0;                 // 0 cast shadow (crown + trunk), 2 contact (does not move)
uniform vec4 shade_color : source_color = vec4(0.50, 0.53, 0.62, 1.0);
uniform vec4 contact_color : source_color = vec4(0.62, 0.64, 0.70, 1.0);
uniform float shadow_strength = 1.0;     // 0..1 (overcast, deep night)
uniform float sun_elev_deg = 40.0;
uniform float ref_elevation = 40.0;      // the elevation the texture was baked at
uniform vec2 shadow_dir = vec2(0.9243, -0.3818);   // on the ground, screen px (x right, y down)
uniform float crown_height_px = 200.0;   // mean height of the crown above the ground (px)
uniform float min_elevation = 10.0;      // below this the shadows stop growing

varying vec2 v_local;
varying flat vec2 v_rect_origin;
varying flat vec2 v_rect_size;

vec2 dir() {
	return normalize(shadow_dir);
}

float elev() {
	return radians(clamp(sun_elev_deg, min_elevation, 89.0));
}

// where a texel of the baked crown (crown = true) or trunk shadow lands now (local px, foot = 0)
vec2 forward(vec2 p, bool crown) {
	vec2 d = dir();
	float e = elev();
	float e0 = radians(ref_elevation);
	float a = dot(p, d);
	vec2 b = p - d * a;
	if (crown) {
		float c0 = crown_height_px / tan(e0);
		float c = crown_height_px / tan(e);
		return b + d * (c + (a - c0) * sin(e0) / sin(e));
	}
	return b + d * (a > 0.0 ? a * tan(e0) / tan(e) : a);
}

// the inverse: which texel of the baked shadow this pixel shows
vec2 backward(vec2 p, bool crown) {
	vec2 d = dir();
	float e = elev();
	float e0 = radians(ref_elevation);
	float a = dot(p, d);
	vec2 b = p - d * a;
	if (crown) {
		float c0 = crown_height_px / tan(e0);
		float c = crown_height_px / tan(e);
		return b + d * (c0 + (a - c) * sin(e) / sin(e0));
	}
	return b + d * (a > 0.0 ? a * tan(e) / tan(e0) : a);
}

// the UV of the texel under local point p (its centre; nearest), or -1 outside the texture
// (TEXTURE itself cannot be passed to a function: sampled inline, knowledge/16 section 12)
vec2 texel_uv(vec2 p) {
	vec2 uv = (p - v_rect_origin) / v_rect_size;
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x >= 1.0 || uv.y >= 1.0) {
		return vec2(-1.0);
	}
	return (floor(uv * v_rect_size) + 0.5) / v_rect_size;
}

void vertex() {
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 o = VERTEX - UV * size;
	v_rect_origin = o;
	v_rect_size = size;
	if (channel != 2) {
		// the box that holds the baked shadow and where both parts have moved to
		vec2 mn = o;
		vec2 mx = o + size;
		vec2 cs[4] = {o, o + vec2(size.x, 0.0), o + size, o + vec2(0.0, size.y)};
		for (int i = 0; i < 4; i++) {
			vec2 f = forward(cs[i], true);
			vec2 g = forward(cs[i], false);
			mn = min(mn, min(f, g));
			mx = max(mx, max(f, g));
		}
		VERTEX = mix(mn, mx, UV);
	}
	v_local = VERTEX;
}

void fragment() {
	float v;
	vec3 shade;
	if (channel == 2) {
		vec2 uv = texel_uv(v_local);
		v = uv.x < 0.0 ? 0.0 : texture(TEXTURE, uv).b * 0.6;
		shade = contact_color.rgb;
	} else {
		vec2 uc = texel_uv(backward(v_local, true));
		vec2 ut = texel_uv(backward(v_local, false));
		float c = uc.x < 0.0 ? 0.0 : texture(TEXTURE, uc).r;
		float t = ut.x < 0.0 ? 0.0 : texture(TEXTURE, ut).g;
		v = max(c, t) * shadow_strength;
		shade = shade_color.rgb;
	}
	COLOR = vec4(mix(vec3(1.0), shade, v), 1.0);
}
