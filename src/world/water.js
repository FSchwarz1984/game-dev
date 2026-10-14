// Stylised stream: no Reflector (it would re-render the scene). Ripples are a scrolling height
// field evaluated on the 16 px/m world grid, shaded into quantised bands, with shore foam and
// sparse emissive glints that feed the bloom pass.

import * as THREE from 'three';
import { NOISE } from '../render/glsl.js';
import { shared } from '../render/materials.js';
import { characterLight } from '../render/sprites.js';
import { WATER_Y } from './terrain.js';

const VERTEX = /* glsl */ `
#include <common>
#include <fog_pars_vertex>
attribute float aShore;
varying vec3 vWorld;
varying float vShore;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorld = world.xyz;
  vShore = aShore;
  vec4 mvPosition = viewMatrix * world;
  gl_Position = projectionMatrix * mvPosition;
  #include <fog_vertex>
}
`;

const FRAGMENT = /* glsl */ `
#include <common>
#include <fog_pars_fragment>
uniform float uTime;
uniform vec3 uSunDir, uSunColor, uSkyColor;
uniform vec3 uDeep, uShallow, uFoam;
uniform float uGlint;
varying vec3 vWorld;
varying float vShore;
${NOISE}
float ripples(vec2 p) {
  return vnoise(p * vec2(0.9, 1.7) - vec2(uTime * 0.55, 0.0)) * 0.6
       + vnoise(p * vec2(1.9, 2.8) + vec2(-uTime * 0.85, uTime * 0.1) + 7.3) * 0.4;
}
void main() {
  vec2 cell = floor(vWorld.xz * 16.0);
  vec2 p = (cell + 0.5) / 16.0;
  float e = 1.0 / 16.0;
  float h = ripples(p);
  vec3 n = normalize(vec3(ripples(p - vec2(e, 0.0)) - ripples(p + vec2(e, 0.0)), 0.3,
                          ripples(p - vec2(0.0, e)) - ripples(p + vec2(0.0, e))));
  float depth = smoothstep(0.0, 2.2, vShore + (vnoise(p * 1.3) - 0.5) * 0.5);
  vec3 light = uSkyColor * 1.2 + uSunColor * clamp(dot(n, uSunDir), 0.0, 1.0);
  vec3 col = mix(uShallow, uDeep, depth) * light;
  col += (step(0.64, h) + step(0.76, h)) * 0.06 * light;            // pixel highlight bands
  float foam = step(vShore + (vnoise(p * 2.0 + vec2(uTime * 0.6, 0.0)) - 0.5) * 0.5, 0.16);
  col = mix(col, uFoam * light, foam * 0.6);
  float twinkle = step(0.985, hash12(cell + floor(uTime * 3.0) * 17.0));
  col += uSunColor * uGlint * twinkle * step(0.72, h) * (1.0 - foam); // glints feed bloom
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  #include <fog_fragment>
}
`;

export function createWater(terrain) {
  const verts = new Map(), pos = [], shore = [], idx = [];
  const vertex = (x, z) => {
    const key = `${x},${z}`;
    if (!verts.has(key)) {
      verts.set(key, pos.length / 3);
      pos.push(x, WATER_Y, z);
      shore.push(terrain.shoreDistance(x, z));
    }
    return verts.get(key);
  };
  for (const [x, z] of terrain.waterCells()) {
    const a = vertex(x, z), b = vertex(x, z + 1), c = vertex(x + 1, z + 1), d = vertex(x + 1, z);
    idx.push(a, b, c, a, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('aShore', new THREE.Float32BufferAttribute(shore, 1));
  g.setIndex(idx);
  g.computeBoundingSphere();

  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      uTime: shared.uTime,
      uSunDir: shared.uSunDir,
      uSunColor: characterLight.uSunColor,
      uSkyColor: characterLight.uSkyColor,
      uDeep: { value: new THREE.Color(0x23566e) },
      uShallow: { value: new THREE.Color(0x3f8a8f) },
      uFoam: { value: new THREE.Color(0xe6f2ec) },
      uGlint: { value: 3 },
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    fog: true,
  });
  const mesh = new THREE.Mesh(g, material);
  mesh.name = 'stream';
  return mesh;
}
