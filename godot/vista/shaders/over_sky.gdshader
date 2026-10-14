// A translucent baked layer (the moon's halo on the title, the faint hanging sky shore of the tower)
// laid over the baked sky behind it in sRGB, as the JS canvas did (in linear light the soft halo
// reads much brighter and its steps show). Opaque output; transparent pixels are skipped.
shader_type canvas_item;
render_mode blend_disabled;
#include "res://vista/shaders/vista.gdshaderinc"

uniform sampler2D img : filter_nearest, repeat_disable;      // straight-alpha RGBA, sRGB
uniform sampler2D sky_tex : filter_nearest, repeat_disable;  // the sky behind it, sRGB
uniform vec2 sky_ofs;          // this quad's (0, 0) in the sky texture's pixels

varying vec2 px;

void vertex() {
	px = VERTEX;
}

void fragment() {
	ivec2 p = ivec2(floor(px));
	vec4 c = texelFetch(img, p, 0);
	if (c.a <= 0.0) discard;
	ivec2 q = ivec2(floor(px + sky_ofs));
	ivec2 sz = textureSize(sky_tex, 0);
	vec3 sky = texelFetch(sky_tex, clamp(q, ivec2(0), sz - 1), 0).rgb;
	COLOR = vec4(srgb_to_linear(mix(sky, c.rgb, c.a)), 1.0);
}
