// Composite of the low-res 3D image onto the window (canvas_item, drawn at an integer scale with
// nearest sampling; the sub-pixel camera remainder is the TextureRect's offset). The 3D viewport is
// HDR (float, linear): converted to display values here, then graded per time of day.
// The look (round 4, decision-log G5R2-1): verdant and soft, not withered yellow and hard. A soft
// S-curve on luma, lift/gain/saturation, split toning (shadows a little blue-green, highlights a
// little warm), and a hue-aware turn in Oklab: the dry olive and straw-green hues turn toward a
// fresh green and gain a little chroma, the greens gain a little, the yellows lose a little (so
// sunlit straw reads gold, not "withered"). A light vignette. Last, the 8-bit output is dithered by
// half a code value with a blue-noise tile fixed to the world's pixel lattice (it moves with the
// world as the camera moves by whole pixels, so it never crawls): dark slow gradients do not band.
// Values over white (lights) roll off by their brightest channel, so they keep their hue.
// No film grain (per-frame noise would read as shimmer).
shader_type canvas_item;
render_mode unshaded;

uniform vec3 lift = vec3(0.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform vec3 shadow_tone = vec3(0.0);     // added to dark tones
uniform vec3 high_tone = vec3(0.0);       // added to light tones
uniform float contrast = 0.0;             // S-curve amount 0..1 (pivot low)
uniform float vignette = 0.22;
uniform vec4 fade = vec4(0.0);            // rgb, amount
uniform vec2 view_size = vec2(640.0, 360.0);   // logical (visible) size in native px
uniform vec2 margin_px = vec2(1.0, 1.0);       // the low-res image's hidden border
uniform bool hdr_input = true;            // the viewport holds linear HDR values
uniform float exposure = 1.0;             // linear multiplier before the grade
// (round 4's hue-aware freshening of the greens; off since round 5, G5R3-1: the round-3 colours)
uniform float green_turn = 0.0;           // radians the olive hues turn toward green
uniform float green_gain = 1.0;           // chroma of the greens
uniform float yellow_gain = 1.0;          // chroma of the yellows (straw, dry grass)
uniform sampler2D blue_noise : filter_nearest, repeat_enable;
uniform vec2 cam_cell = vec2(0.0);        // the world lattice cell at the image's centre (y up)
uniform float dither_amp = 1.0;           // in 8-bit code values (peak to peak)
uniform float soft_ends = 0.0;            // ease both ends of the tone curve (the barrier): black stays black

vec3 lin_to_srgb(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}
vec3 srgb_to_lin(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
vec3 to_oklab(vec3 c) {
	vec3 lms = vec3(
		0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b,
		0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b,
		0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b);
	lms = pow(max(lms, vec3(0.0)), vec3(1.0 / 3.0));
	return vec3(
		0.2104542553 * lms.x + 0.7936177850 * lms.y - 0.0040720468 * lms.z,
		1.9779984951 * lms.x - 2.4285922050 * lms.y + 0.4505937099 * lms.z,
		0.0259040371 * lms.x + 0.7827717662 * lms.y - 0.8086757660 * lms.z);
}
vec3 from_oklab(vec3 L) {
	vec3 lms = vec3(
		L.x + 0.3963377774 * L.y + 0.2158037573 * L.z,
		L.x - 0.1055613458 * L.y - 0.0638541728 * L.z,
		L.x - 0.0894841775 * L.y - 1.2914855480 * L.z);
	lms = lms * lms * lms;
	return vec3(
		 4.0767416621 * lms.x - 3.3077115913 * lms.y + 0.2309699292 * lms.z,
		-1.2684380046 * lms.x + 2.6097574011 * lms.y - 0.3413193965 * lms.z,
		-0.0041960863 * lms.x - 0.7034186147 * lms.y + 1.7076147010 * lms.z);
}

void fragment() {
	vec3 c = texture(TEXTURE, UV).rgb;
	vec3 lin = (hdr_input ? c : srgb_to_lin(c)) * exposure;
	// hue-aware turn (Oklab hue: yellow about 1.9 rad, olive 2.0-2.2, green about 2.5)
	vec3 lab = to_oklab(lin);
	float C = length(lab.yz);
	if (C > 0.004) {
		float h = atan(lab.z, lab.y);
		float olive = exp(-pow((h - 2.08) / 0.22, 2.0));
		float green = exp(-pow((h - 2.55) / 0.35, 2.0));
		float yellow = exp(-pow((h - 1.80) / 0.18, 2.0));
		h += green_turn * olive;
		float k = 1.0 + (green_gain - 1.0) * max(green, olive * 0.8) + (yellow_gain - 1.0) * yellow;
		lab.yz = vec2(cos(h), sin(h)) * C * k;
		lin = max(from_oklab(lab), vec3(0.0));
	}
	// lights brighter than white keep their hue (a lantern's core stays warm, a firefly yellow-green):
	// the brightest channel rolls off softly above 0.8 and the others follow it
	float mx = max(lin.r, max(lin.g, lin.b));
	if (mx > 0.8) {
		lin *= (0.8 + 0.2 * (1.0 - exp(-(mx - 0.8) / 0.2))) / mx;
	}
	c = lin_to_srgb(lin);
	// S-curve on luma (the hue and the chroma ratio stay put), pivoting low: the darks keep their
	// place, the mids and lights open up, the top rolls off
	float l0 = dot(c, vec3(0.299, 0.587, 0.114));
	float ls = l0 + contrast * max(l0 - 0.26, 0.0) * (1.0 - l0) * 1.6;
	// soft ends: the darks open a little (zero stays zero: no lift, no veil), the top rolls off a little
	float t0 = clamp(1.0 - l0 / 0.3, 0.0, 1.0);
	ls += soft_ends * 0.35 * l0 * t0 * t0;
	ls -= soft_ends * 0.5 * max(l0 - 0.75, 0.0) * max(l0 - 0.75, 0.0);
	c *= ls / max(l0, 1e-4);
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	c = lift + c * (gain - lift);
	float l2 = dot(c, vec3(0.299, 0.587, 0.114));
	c += shadow_tone * (1.0 - smoothstep(0.0, 0.55, l2)) + high_tone * smoothstep(0.45, 1.0, l2);
	// vignette in the visible frame
	vec2 tex_size = vec2(textureSize(TEXTURE, 0));
	vec2 tp = UV * tex_size;
	vec2 p = (tp - margin_px) / view_size - 0.5;
	c *= 1.0 - dot(p * vec2(1.0, 0.8), p * vec2(1.0, 0.8)) * vignette;
	c = mix(c, fade.rgb, fade.a);
	// blue-noise dither of the 8-bit output, fixed to the world's pixel lattice
	vec2 cell = floor(vec2(tp.x - tex_size.x * 0.5, tex_size.y * 0.5 - tp.y)) + cam_cell;
	float bn = texelFetch(blue_noise, ivec2(mod(cell, 64.0)), 0).r;
	c += (bn - 0.5) * dither_amp / 255.0;
	COLOR = vec4(c, 1.0);
}
