// Patched Lambert materials shared by the whole scene:
//  - createEnvMaterial: the environment "master material" (terrain, buildings, trunks, rocks)
//  - createBillboardMaterial / createBillboardDepthMaterial: lit, shadow-casting billboards
// Both read the per-frame uniforms in `shared`.

import * as THREE from 'three';
import { PIXEL_SAMPLING, PIXEL_SAMPLING_ARRAY, NOISE, WIND, CUTOUT } from './glsl.js';

/** Uniform objects shared by every patched material; updated once per frame. */
export const shared = {
  uTime: { value: 0 },
  uWind: { value: 0.07 },                         // sway amplitude, metres
  uStretch: { value: 1 },                         // upright billboards: keeps pixels square at the camera pitch
  uSunDir: { value: new THREE.Vector3(0, 1, 0) }, // towards the sun, world space
  uCutCenter: { value: new THREE.Vector2() },     // occlusion cutout, drawing-buffer pixels
  uCutRadius: { value: 0 },
  uCutDepth: { value: 0 },
  uCutFloor: { value: 0 },
  uCutBottom: { value: 0 },
};

const LAYER_PX = 64;      // texels per side of each environment layer
const TEXELS_PER_M = 16;  // texture density: one layer spans 4 m

const cutoutUniforms = () => ({
  uCutCenter: shared.uCutCenter, uCutRadius: shared.uCutRadius, uCutDepth: shared.uCutDepth,
  uCutFloor: shared.uCutFloor, uCutBottom: shared.uCutBottom,
});

const ENV_VERTEX_PARS = /* glsl */ `
attribute vec2 aLayer;
varying vec3 vRest;
varying vec3 vWN;
flat varying vec2 vLayer;
#ifdef ENV_LIP
attribute float aTop;
varying float vTop;
#endif
#ifdef ENV_WIND
attribute float aWind;
${WIND}
#endif
`;

const ENV_VERTEX = /* glsl */ `
#ifdef USE_INSTANCING
  mat4 envModel = modelMatrix * instanceMatrix;
#else
  mat4 envModel = modelMatrix;
#endif
vRest = (envModel * vec4(transformed, 1.0)).xyz;
vWN = normalize(mat3(envModel) * objectNormal);
vLayer = aLayer;
#ifdef ENV_LIP
  vTop = aTop;
#endif
#ifdef ENV_WIND
  transformed += windOffset(vRest) * aWind;
#endif
`;

const ENV_FRAGMENT_PARS = /* glsl */ `
uniform sampler2DArray uLayers;
varying vec3 vRest;
varying vec3 vWN;
flat varying vec2 vLayer;
#ifdef ENV_LIP
varying float vTop;
#endif
${NOISE}
${PIXEL_SAMPLING}
${PIXEL_SAMPLING_ARRAY}
#ifdef OCCLUDER
${CUTOUT}
#endif
`;

// World-space UVs from the dominant axis of the normal; walls read with +V up.
const ENV_MAP = /* glsl */ `
vec3 envN = normalize(vWN);
vec3 envA = abs(envN);
vec2 envUv = envA.y >= max(envA.x, envA.z) ? vRest.xz
  : envA.x >= envA.z ? vec2(-vRest.z * sign(envN.x), -vRest.y)
  : vec2(vRest.x * sign(envN.z), -vRest.y);
envUv *= ${(TEXELS_PER_M / LAYER_PX).toFixed(4)};
float envLayer = vLayer.x;
float envShade = 1.0;
#ifdef ENV_LIP
  // Grass hangs over cliff tops by 1-4 texels with a dark line beneath (HD-2D overhang).
  if (vLayer.y >= 0.0 && envA.y < 0.5) {
    float envBelow = vTop - vRest.y;
    float envCol = floor((envA.x >= envA.z ? vRest.z : vRest.x) * 16.0);
    float envLip = (1.5 + floor(hash11(envCol + vTop * 7.0) * 3.5)) / 16.0;
    if (envBelow < envLip) envLayer = vLayer.y;
    else if (envBelow < envLip + 0.07) envShade = 0.68;
  }
#endif
vec4 envTex = samplePixelArray(uLayers, envUv, envLayer, vec2(${LAYER_PX}.0));
diffuseColor.rgb *= envTex.rgb * envShade;
#ifdef ENV_VARIATION
  // Low-frequency tint drift across the world hides the 4 m texture repeat.
  float envVar = vnoise(vRest.xz * 0.09) * 0.65 + vnoise(vRest.xz * 0.31 + 11.0) * 0.35;
  diffuseColor.rgb *= mix(vec3(0.9, 0.95, 1.03), vec3(1.07, 1.04, 0.9), envVar);
#endif
`;

/**
 * Environment master material. Geometry needs aLayer (vec2: surface layer, lip layer or -1) and
 * vertex colours (tint x AO); aTop with `lip`, aWind with `wind`.
 */
export function createEnvMaterial(layers, { occluder = false, wind = false, lip = false, variation = false } = {}) {
  const m = new THREE.MeshLambertMaterial({ vertexColors: true });
  m.defines = {};
  if (occluder) m.defines.OCCLUDER = '';
  if (wind) m.defines.ENV_WIND = '';
  if (lip) m.defines.ENV_LIP = '';
  if (variation) m.defines.ENV_VARIATION = '';
  m.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, { uLayers: { value: layers }, uTime: shared.uTime, uWind: shared.uWind }, cutoutUniforms());
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${ENV_VERTEX_PARS}`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>\n${ENV_VERTEX}`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\n${ENV_FRAGMENT_PARS}`)
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        #ifdef OCCLUDER
          if (occlusionCut(vViewPosition.z, vRest.y)) discard;
        #endif`)
      .replace('#include <map_fragment>', ENV_MAP);
  };
  m.customProgramCacheKey = () => 'env:' + Object.keys(m.defines).sort().join(',');
  return m;
}

// ---------------------------------------------------------------------------------------------
// Billboards. THREE.Sprite is unlit and never enters the shadow pass, so these are Mesh quads
// oriented in the vertex shader from the view matrix. In the shadow pass the "view" is the sun's
// camera, so the same code turns the quad toward the light and shadows keep their full width.
//   upright: cylindrical (rotates about Y), pivot at the feet, stretched by uStretch
//   sphere:  faces the camera fully; per-pixel sphere normals make each card shade like a ball

const BB_VERTEX_PARS = /* glsl */ `
uniform float uStretch;
uniform vec3 uSunDir;
varying vec2 vBB;
varying float vCutY;
#ifdef BB_ATLAS
attribute float aTile; // atlas cell; +0.5 = mirrored
uniform vec2 uAtlas;
#endif
#ifdef BB_FRAME
uniform vec4 uFrame;   // u0, v0, du, dv (negative du mirrors)
#endif
#ifdef BB_WIND
attribute float aSway;
#endif
${WIND}
`;

const BB_UV = /* glsl */ `
#if defined(USE_MAP) && defined(BB_ATLAS)
{
  float bbTile = floor(aTile);
  vec2 bbCell = vec2(mod(bbTile, uAtlas.x), floor(bbTile / uAtlas.x));
  vec2 bbUv = vec2(fract(aTile) > 0.25 ? 1.0 - uv.x : uv.x, uv.y);
  vMapUv = (vec2(bbCell.x, uAtlas.y - 1.0 - bbCell.y) + bbUv) / uAtlas;
}
#elif defined(USE_MAP) && defined(BB_FRAME)
  vMapUv = uFrame.xy + uv * uFrame.zw;
#endif
`;

const BB_SETUP = /* glsl */ `
#ifdef USE_INSTANCING
  mat4 bbModel = modelMatrix * instanceMatrix;
#else
  mat4 bbModel = modelMatrix;
#endif
vec3 bbCenter = bbModel[3].xyz;
vec2 bbScale = vec2(length(bbModel[0].xyz), length(bbModel[1].xyz));
#ifdef BB_SPHERE
  vec3 bbRight = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
  vec3 bbUp = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
  float bbStretch = 1.0;
#else
  vec3 bbRight = normalize(vec3(viewMatrix[0][0], 0.0, viewMatrix[2][0]));
  vec3 bbUp = vec3(0.0, 1.0, 0.0);
  #ifdef BB_DEPTH
    float bbStretch = 1.0;
  #else
    float bbStretch = uStretch;
  #endif
#endif
vec3 bbWorld = bbCenter + bbRight * (position.x * bbScale.x) + bbUp * (position.y * bbScale.y * bbStretch);
#if defined(BB_WIND) && !defined(BB_DEPTH)
  #ifdef BB_SPHERE
    bbWorld += windOffset(bbCenter) * aSway;
  #else
    bbWorld += windOffset(bbCenter) * aSway * position.y;
  #endif
#endif
`;

const BB_PROJECT = /* glsl */ `
vec4 mvPosition = viewMatrix * vec4(bbWorld, 1.0);
gl_Position = projectionMatrix * mvPosition;
vBB = position.xy * 2.0;
vCutY = bbWorld.y;
`;

const BB_NORMAL = /* glsl */ `
#ifdef BB_SPHERE
  vec3 transformedNormal = vec3(0.0, 0.0, 1.0);
#else
  vec3 bbBack = normalize(vec3(viewMatrix[0][2], 0.0, viewMatrix[2][2]));
  vec3 transformedNormal = normalize(mat3(viewMatrix) * normalize(bbBack * 0.45 + vec3(0.0, 0.9, 0.0)));
#endif
`;

const BB_FRAGMENT_PARS = /* glsl */ `
uniform vec2 uTexSize;
varying vec2 vBB;
varying float vCutY;
${PIXEL_SAMPLING}
#ifdef OCCLUDER
${CUTOUT}
#endif
#ifdef BB_OUTLINE
uniform vec4 uOutline;
bool outlineNear(vec2 uv) {
  ivec2 t = ivec2(floor(uv * uTexSize));
  for (int y = -2; y <= 2; y++) for (int x = -2; x <= 2; x++) {
    if (abs(x) + abs(y) <= 2 && texelFetch(map, t + ivec2(x, y), 0).a > 0.5) return true;
  }
  return false;
}
#endif
`;

function billboardDefines({ mode, atlas, frame, wind, occluder, outline }) {
  const d = {};
  if (mode === 'sphere') d.BB_SPHERE = '';
  if (atlas) d.BB_ATLAS = '';
  if (frame) d.BB_FRAME = '';
  if (wind) d.BB_WIND = '';
  if (occluder) d.OCCLUDER = '';
  if (outline) d.BB_OUTLINE = '';
  return d;
}

function billboardUniforms({ atlas, frame }) {
  const u = { uStretch: shared.uStretch, uSunDir: shared.uSunDir, uTime: shared.uTime, uWind: shared.uWind };
  if (atlas) u.uAtlas = { value: new THREE.Vector2(atlas[0], atlas[1]) };
  if (frame) u.uFrame = frame;
  return u;
}

/**
 * Lit billboard material (MeshLambertMaterial + vertex patch).
 * opts: map, mode ('upright' | 'sphere'), atlas [cols, rows] (instanced, attribute aTile),
 * frame ({ value: Vector4 }, single sprite), wind (instanced, attribute aSway), occluder, outline.
 */
export function createBillboardMaterial(opts) {
  const { map } = opts;
  const m = new THREE.MeshLambertMaterial({ map, alphaTest: 0.5, side: THREE.FrontSide });
  m.shadowSide = THREE.DoubleSide;
  m.defines = billboardDefines(opts);
  const uniforms = billboardUniforms(opts);
  uniforms.uTexSize = { value: new THREE.Vector2(map.image.width, map.image.height) };
  if (opts.outline) uniforms.uOutline = { value: new THREE.Vector4(0, 0, 0, 0) };
  m.userData.uniforms = uniforms;
  m.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms, cutoutUniforms());
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${BB_VERTEX_PARS}`)
      .replace('#include <uv_vertex>', `#include <uv_vertex>\n${BB_UV}`)
      .replace('#include <beginnormal_vertex>', `${BB_SETUP}\n#include <beginnormal_vertex>`)
      .replace('#include <defaultnormal_vertex>', BB_NORMAL)
      .replace('#include <project_vertex>', BB_PROJECT)
      .replace('#include <worldpos_vertex>', 'vec4 worldPosition = vec4(bbWorld, 1.0);')
      // Look the shadow up half a quad toward the sun, past the quad's own light-facing caster.
      .replace('#include <shadowmap_vertex>', `worldPosition.xyz += uSunDir * (bbScale.x * 0.5 + 0.15);\n#include <shadowmap_vertex>`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <map_pars_fragment>', `#include <map_pars_fragment>\n${BB_FRAGMENT_PARS}`)
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        #ifdef OCCLUDER
          if (occlusionCut(vViewPosition.z, vCutY)) discard;
        #endif`)
      .replace('#include <map_fragment>', `#ifdef USE_MAP
          diffuseColor *= samplePixel(map, vMapUv, uTexSize);
        #endif`)
      .replace('#include <alphatest_fragment>', `bool bbOutline = false;
        #ifdef BB_OUTLINE
          if (diffuseColor.a < 0.5 && uOutline.a > 0.0 && outlineNear(vMapUv)) { bbOutline = true; diffuseColor.a = 1.0; }
        #endif
        #include <alphatest_fragment>`)
      .replace('#include <dithering_fragment>', `#include <dithering_fragment>
        #ifdef BB_OUTLINE
          if (bbOutline) gl_FragColor = vec4(uOutline.rgb, 1.0);
        #endif`);
    if (opts.mode === 'sphere') {
      shader.fragmentShader = shader.fragmentShader.replace('#include <normal_fragment_begin>', `
        float faceDirection = 1.0;
        vec3 normal = normalize(vec3(vBB * 0.85, sqrt(max(0.0, 1.0 - dot(vBB, vBB))) + 0.2));
        vec3 nonPerturbedNormal = normal;`);
    }
  };
  m.customProgramCacheKey = () => 'bb:' + Object.keys(m.defines).sort().join(',');
  return m;
}

/** Shadow-pass companion: same quad, turned toward the light (the shadow camera's view matrix). */
export function createBillboardDepthMaterial(opts) {
  const m = new THREE.MeshDepthMaterial();
  m.defines = { ...billboardDefines({ ...opts, occluder: false, outline: false }), BB_DEPTH: '' };
  const uniforms = billboardUniforms(opts);
  m.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${BB_VERTEX_PARS}`)
      .replace('#include <uv_vertex>', `#include <uv_vertex>\n${BB_UV}`)
      .replace('#include <begin_vertex>', `${BB_SETUP}\n#include <begin_vertex>`)
      .replace('#include <project_vertex>', BB_PROJECT);
  };
  m.customProgramCacheKey = () => 'bbdepth:' + Object.keys(m.defines).sort().join(',');
  return m;
}

/** Unit quads: upright sprites pivot at the feet, sphere cards at their centre. */
export const UPRIGHT_QUAD = new THREE.PlaneGeometry(1, 1).translate(0, 0.5, 0);
export const CENTERED_QUAD = new THREE.PlaneGeometry(1, 1);
