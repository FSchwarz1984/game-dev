// Billboard sprites on Mesh quads: lit, shadow-casting, readable.
//
// Characters get "protected" lighting (docs/knowledge/02 section 1.2, v0.1 post-mortem): a
// brightness floor, a camera-front fill, a rim light on silhouette texels, and ONE smoothed sun
// visibility value for the whole sprite computed on the CPU from proxy volumes. They never sample
// the shadow map, so leaf shadows cannot dapple, dither or flicker on them, while the ground keeps
// full-contrast shadows. Props use ordinary Lambert lighting with per-pixel shadows.

import * as THREE from 'three';
import { PIXEL_SAMPLING } from './glsl.js';
import { shared, createBillboardMaterial, createBillboardDepthMaterial, UPRIGHT_QUAD } from './materials.js';

/** Lighting terms shared by every protected sprite (colours already divided by pi); Lighting writes them. */
export const characterLight = {
  uSunDir: shared.uSunDir,
  uSunColor: { value: new THREE.Color() },
  uSkyColor: { value: new THREE.Color() },
  uGroundColor: { value: new THREE.Color() },
  uFillColor: { value: new THREE.Color() },
  uRimColor: { value: new THREE.Color() },
  uRimDir: { value: new THREE.Vector2(0, 1) }, // screen-space direction the rim light comes from
  uRimStrength: { value: 0.5 },
  uFloor: { value: 0.5 },                      // minimum luminance of the light term
  uShadeStrength: { value: 0.45 },             // how far shade may dim a character (env gets 1.0)
};

const CHARACTER_VERTEX = /* glsl */ `
#include <common>
#include <fog_pars_vertex>
uniform vec4 uFrame;
uniform float uStretch;
varying vec2 vUv;
varying float vSide;
void main() {
  vec3 center = modelMatrix[3].xyz;
  vec2 size = vec2(length(modelMatrix[0].xyz), length(modelMatrix[1].xyz));
  vec3 right = normalize(vec3(viewMatrix[0][0], 0.0, viewMatrix[2][0]));
  vec3 world = center + right * (position.x * size.x) + vec3(0.0, position.y * size.y * uStretch, 0.0);
  vUv = uFrame.xy + uv * uFrame.zw;
  vSide = position.x * 2.0;
  vec4 mvPosition = viewMatrix * vec4(world, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  #include <fog_vertex>
}
`;

const CHARACTER_FRAGMENT = /* glsl */ `
#include <common>
#include <fog_pars_fragment>
uniform sampler2D map;
uniform vec2 uTexSize;
uniform vec4 uFrame;
uniform vec3 uSunDir, uSunColor, uSkyColor, uGroundColor, uFillColor, uRimColor, uKeyDir, uKeyColor;
uniform vec2 uRimDir;
uniform float uRimStrength, uFloor, uShade, uShadeStrength;
uniform vec4 uOutline;
varying vec2 vUv;
varying float vSide;
${PIXEL_SAMPLING}
float alphaAt(ivec2 t) { return texelFetch(map, t, 0).a; }
float wrapLight(vec3 n, vec3 l) { return clamp(dot(n, l) * 0.6 + 0.4, 0.0, 1.0); }

void main() {
  vec4 tex = samplePixel(map, vUv, uTexSize);
  ivec2 t = ivec2(floor(vUv * uTexSize));
  vec3 col;
  if (tex.a < 0.5) {
    // Highlight outline: a two-texel ring outside the silhouette (frames keep a transparent margin).
    bool near = false;
    if (uOutline.a > 0.0) {
      for (int y = -2; y <= 2; y++) for (int x = -2; x <= 2; x++) {
        if (abs(x) + abs(y) <= 2 && alphaAt(t + ivec2(x, y)) > 0.5) near = true;
      }
    }
    if (!near) discard;
    col = uOutline.rgb;
  } else {
    // A rounded, slightly upward normal gives the flat card some volume without per-pixel shadow.
    vec3 right = normalize(vec3(viewMatrix[0][0], 0.0, viewMatrix[2][0]));
    vec3 back = normalize(vec3(viewMatrix[0][2], 0.0, viewMatrix[2][2]));
    vec3 n = normalize(back + right * (vSide * 0.55) + vec3(0.0, 0.35, 0.0));
    vec3 light = uSunColor * wrapLight(n, uSunDir) * mix(1.0, uShade, uShadeStrength)
      + mix(uGroundColor, uSkyColor, 0.5 + 0.5 * n.y)
      + uFillColor
      + uKeyColor * wrapLight(n, uKeyDir);
    light *= max(1.0, uFloor / max(dot(light, vec3(0.2126, 0.7152, 0.0722)), 1e-4));
    col = tex.rgb * light;
    // Rim: silhouette texels whose open side faces the rim light; crisp, one texel wide.
    vec2 open = vec2(alphaAt(t - ivec2(1, 0)) - alphaAt(t + ivec2(1, 0)), alphaAt(t - ivec2(0, 1)) - alphaAt(t + ivec2(0, 1)));
    open.x *= sign(uFrame.z);
    if (dot(open, open) > 0.25) {
      col += uRimColor * uRimStrength * (0.35 + 0.65 * max(dot(normalize(open), uRimDir), 0.0));
    }
  }
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  #include <fog_fragment>
}
`;

function createCharacterMaterial(texture, frame) {
  const uniforms = {
    ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
    ...characterLight,
    map: { value: texture },
    uTexSize: { value: new THREE.Vector2(texture.image.width, texture.image.height) },
    uFrame: frame,
    uStretch: shared.uStretch,
    uShade: { value: 1 },
    uKeyDir: { value: new THREE.Vector3(0, 1, 0) },
    uKeyColor: { value: new THREE.Color(0, 0, 0) },
    uOutline: { value: new THREE.Vector4(0, 0, 0, 0) },
  };
  const m = new THREE.ShaderMaterial({ uniforms, vertexShader: CHARACTER_VERTEX, fragmentShader: CHARACTER_FRAGMENT, fog: true });
  // The shadow pass copies map/alphaTest from the main material into the depth material.
  m.map = texture;
  m.alphaTest = 0.5;
  m.shadowSide = THREE.DoubleSide;
  m.userData.uniforms = uniforms;
  return m;
}

/**
 * sheet: { texture, frameW, frameH } (texels). size: [width, height] in metres.
 * kind: 'character' (protected lighting) or 'prop' (normal lighting).
 */
export function createSprite({ sheet, size, kind = 'prop', castShadow = true }) {
  const frame = { value: new THREE.Vector4() };
  const material = kind === 'character'
    ? createCharacterMaterial(sheet.texture, frame)
    : createBillboardMaterial({ map: sheet.texture, mode: 'upright', frame, outline: true });
  const mesh = new THREE.Mesh(UPRIGHT_QUAD, material);
  mesh.scale.set(size[0], size[1], 1);
  mesh.castShadow = castShadow;
  mesh.receiveShadow = kind === 'prop';
  mesh.customDepthMaterial = createBillboardDepthMaterial({ map: sheet.texture, mode: 'upright', frame });

  const uniforms = material.userData.uniforms;
  const { width, height } = sheet.texture.image;
  mesh.userData.sprite = {
    kind,
    size,
    uniforms,
    /** Select atlas cell (col, row from the top); mirror flips horizontally. */
    setFrame(col, row, mirror = false) {
      const du = sheet.frameW / width, dv = sheet.frameH / height;
      const u0 = col * du, v0 = 1 - (row + 1) * dv;
      frame.value.set(mirror ? u0 + du : u0, v0, mirror ? -du : du, dv);
    },
    /** color: THREE.Color (linear) or null to clear. */
    setOutline(color) {
      if (color) uniforms.uOutline.value.set(color.r, color.g, color.b, 1);
      else uniforms.uOutline.value.w = 0;
    },
  };
  mesh.userData.sprite.setFrame(0, 0);
  return mesh;
}
