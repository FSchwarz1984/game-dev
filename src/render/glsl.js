// GLSL snippets shared by the custom and patched materials.

/**
 * Anti-aliased nearest sampling: texels stay crisp at any magnification, texel edges blend over
 * one screen pixel (so sprites don't crawl when they move by sub-pixels) and mipmaps still apply
 * when minified. Textures using it must have LinearFilter magnification.
 */
export const PIXEL_SAMPLING = /* glsl */ `
vec2 pixelUv(vec2 uv, vec2 size) {
  vec2 px = uv * size;
  vec2 fw = max(fwidth(px), vec2(1e-4));
  vec2 edge = floor(px + 0.5);
  return (edge + clamp((px - edge) / fw, -0.5, 0.5)) / size;
}
vec4 samplePixel(sampler2D tex, vec2 uv, vec2 size) {
  return textureGrad(tex, pixelUv(uv, size), dFdx(uv), dFdy(uv));
}
`;

export const PIXEL_SAMPLING_ARRAY = /* glsl */ `
vec4 samplePixelArray(sampler2DArray tex, vec2 uv, float layer, vec2 size) {
  return textureGrad(tex, vec3(pixelUv(uv, size), layer), dFdx(uv), dFdy(uv));
}
`;

export const NOISE = /* glsl */ `
float hash11(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}
`;

/** Slow, low-frequency sway; only the main pass uses it, so cast shadows stay still. */
export const WIND = /* glsl */ `
uniform float uTime;
uniform float uWind;
vec3 windOffset(vec3 p) {
  float ph = dot(p.xz, vec2(0.21, 0.17));
  float s = sin(uTime * 1.1 + ph) * 0.55 + sin(uTime * 1.9 + ph * 1.7) * 0.3 + sin(uTime * 0.6 + ph * 0.4) * 0.45;
  return vec3(s, 0.0, s * 0.45) * uWind;
}
`;

/**
 * Screen-space circular cutout around the player for occluders only. A fragment is removed when it
 * is inside the circle, nearer to the camera than the player, above her feet in the world and not
 * below her feet on screen (cutting there hides nothing and would open hollow terrain columns).
 * The rim is dithered (environment only - characters are never dithered).
 */
export const CUTOUT = /* glsl */ `
uniform vec2 uCutCenter;
uniform float uCutRadius;
uniform float uCutDepth;
uniform float uCutFloor;
uniform float uCutBottom;
float bayer4(vec2 p) {
  ivec2 q = ivec2(mod(p, 4.0));
  const float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
  return (m[q.x + q.y * 4] + 0.5) / 16.0;
}
bool occlusionCut(float viewDepth, float worldY) {
  if (uCutRadius < 1.0 || viewDepth > uCutDepth || worldY < uCutFloor) return false;
  float r = length(gl_FragCoord.xy - uCutCenter) / uCutRadius;
  float cut = min(1.0 - smoothstep(0.72, 1.0, r), clamp((gl_FragCoord.y - uCutBottom) / (0.12 * uCutRadius), 0.0, 1.0));
  return r < 1.0 && cut > bayer4(gl_FragCoord.xy);
}
`;
