// Gray-box props: vermilion torii, chibi-scale house, small shrine, stone lantern, bridge, rocks.
// Static parts sharing a material are merged into one draw; highlightable things (a rock, the
// lantern, the shrine) stay separate objects for the highlight API.

import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { makeRng } from '../core/math.js';
import { createEnvMaterial } from '../render/materials.js';
import { L } from './art.js';
import { env, box, post, merge } from './geom.js';
import { SITE } from './terrain.js';

const PAPER = 0xffc879;

// Box rotated about X (roof slabs sloping toward +-z).
function slab(w, h, d, x, y, z, rx = 0, rz = 0) {
  const g = new THREE.BoxGeometry(w, h, d);
  if (rx) g.rotateX(rx);
  if (rz) g.rotateZ(rz);
  return g.translate(x, y, z);
}
const part = (geo, layer, tint) => env(geo, { layer, tint });

function torii() {
  const parts = [];
  for (const x of [-1.35, 1.35]) {
    parts.push(part(post(0.17, 0.15, 3.3, x, 0, 0), L.VERMILION));
    parts.push(part(post(0.23, 0.23, 0.32, x, 0, 0), L.LACQUER));
  }
  parts.push(
    part(box(3.3, 0.22, 0.18, 0, 2.38, 0), L.VERMILION),
    part(box(0.18, 0.5, 0.16, 0, 2.6, 0), L.VERMILION),
    part(box(4.0, 0.26, 0.34, 0, 3.1, 0), L.VERMILION),
    part(box(4.2, 0.16, 0.42, 0, 3.36, 0), L.LACQUER),
    part(slab(0.7, 0.16, 0.42, -2.3, 3.5, 0, 0, -0.28), L.LACQUER),
    part(slab(0.7, 0.16, 0.42, 2.3, 3.5, 0, 0, 0.28), L.LACQUER),
  );
  return merge(parts);
}

function house() {
  const rise = 1.75, run = 2.15, angle = Math.atan2(rise, run), len = Math.hypot(rise, run) + 0.25;
  const parts = [
    part(box(4.4, 0.3, 3.6), L.GRANITE),
    part(box(4.0, 1.6, 3.2, 0, 0.3, 0), L.PLASTER),
    part(box(4.1, 0.18, 3.3, 0, 1.82, 0), L.DARKWOOD),
    part(box(0.95, 1.3, 0.08, 0.7, 0.3, 1.62), L.DARKWOOD),
    part(box(1.0, 0.7, 0.06, -1.1, 0.95, 1.62), L.DARKWOOD),
    part(slab(4.9, 0.24, len, 0, 1.9 + rise / 2, run / 2, angle), L.THATCH),
    part(slab(4.9, 0.24, len, 0, 1.9 + rise / 2, -run / 2, -angle), L.THATCH),
    part(box(5.0, 0.28, 0.45, 0, 1.9 + rise - 0.1, 0), L.THATCH, 0xb89a70),
  ];
  for (const [x, z] of [[-1.95, -1.55], [1.95, -1.55], [-1.95, 1.55], [1.95, 1.55]]) parts.push(part(box(0.22, 1.6, 0.22, x, 0.3, z), L.DARKWOOD));
  for (const sx of [-1, 1]) { // gable ends
    const tri = new THREE.BufferGeometry();
    const y0 = 1.9, x = sx * 2.0;
    tri.setAttribute('position', new THREE.Float32BufferAttribute([x, y0, -1.6, x, y0, 1.6, x, y0 + rise - 0.1, 0], 3));
    tri.setIndex(sx > 0 ? [0, 2, 1] : [0, 1, 2]);
    tri.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2));
    tri.computeVertexNormals();
    parts.push(part(tri, L.PLASTER, 0xe8e0cc));
  }
  return merge(parts);
}

function shrineParts() {
  const rise = 0.42, half = 0.62, angle = Math.atan2(rise, half);
  const body = merge([
    part(box(1.6, 0.35, 1.3), L.GRANITE),
    part(box(1.25, 0.3, 1.0, 0, 0.35, 0), L.GRANITE),
    part(box(0.85, 0.72, 0.7, 0, 0.65, 0), L.DARKWOOD),
    part(box(0.56, 0.5, 0.05, 0, 0.75, 0.36), L.VERMILION),
    part(slab(Math.hypot(rise, half) + 0.12, 0.09, 1.15, -half / 2, 1.37 + rise / 2, 0, 0, angle), L.COPPER),
    part(slab(Math.hypot(rise, half) + 0.12, 0.09, 1.15, half / 2, 1.37 + rise / 2, 0, 0, -angle), L.COPPER),
    part(box(0.14, 0.12, 1.2, 0, 1.37 + rise - 0.04, 0), L.COPPER, 0xa8c8b8),
    part(post(0.05, 0.05, 1.25, -1.05, 0, 0.35), L.DARKWOOD),
    part(post(0.05, 0.05, 1.25, 1.05, 0, 0.35), L.DARKWOOD),
  ]);
  return body;
}

function lanternParts() {
  return merge([
    part(post(0.42, 0.42, 0.22, 0, 0, 0, 6), L.GRANITE),
    part(post(0.3, 0.27, 0.12, 0, 0.22, 0, 6), L.GRANITE),
    part(post(0.13, 0.11, 0.62, 0, 0.34, 0, 8), L.GRANITE),
    part(post(0.3, 0.26, 0.14, 0, 0.96, 0, 6), L.GRANITE),
    ...[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([x, z]) => part(box(0.07, 0.34, 0.07, x * 0.17, 1.1, z * 0.17), L.GRANITE)),
    part(post(0.48, 0.1, 0.24, 0, 1.44, 0, 6), L.GRANITE),
    part(new THREE.SphereGeometry(0.09, 6, 4).translate(0, 1.74, 0), L.GRANITE),
  ]);
}

function bridgeGeometry(b) {
  const len = b.z1 - b.z0, cz = (b.z0 + b.z1) / 2, cx = (b.x0 + b.x1) / 2;
  const parts = [part(box(b.x1 - b.x0, 0.15, len, cx, b.y - 0.15, cz), L.PLANK)];
  for (const x of [b.x0 + 0.1, b.x1 - 0.1]) {
    parts.push(part(box(0.12, 0.1, len, x, b.y + 0.62, cz), L.DARKWOOD));
    for (let z = b.z0 + 0.2; z < b.z1; z += 1.5) parts.push(part(box(0.13, 0.7, 0.13, x, b.y, z), L.DARKWOOD));
    for (const z of [cz - 2.5, cz + 2.5]) parts.push(part(post(0.13, 0.13, 1.6, x, -1.5, z, 6), L.DARKWOOD));
  }
  return merge(parts);
}

// A faceted boulder: jittered icosahedron, flat-shaded through non-indexed normals.
function rockGeometry(rng, sx, sy, sz) {
  let g = mergeVertices(new THREE.IcosahedronGeometry(1, 1).deleteAttribute('normal').deleteAttribute('uv'));
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const k = rng.range(0.82, 1.12);
    p.setXYZ(i, p.getX(i) * k * sx, Math.max(-0.25, p.getY(i)) * k * sy, p.getZ(i) * k * sz);
  }
  g = g.toNonIndexed();
  g.computeVertexNormals();
  return env(g, { layer: L.ROCK, ao: y => 0.7 + 0.3 * Math.min(1, Math.max(0, y / sy)) });
}

/** Returns { group, colliders, highlightables }; adds proxies, lanterns and glows. */
export function buildProps({ layers, terrain, lighting, proxies }) {
  const rng = makeRng(23);
  const group = new THREE.Group();
  const solid = createEnvMaterial(layers);
  const occluding = createEnvMaterial(layers, { occluder: true });
  const colliders = [];
  const highlightables = [];
  const glowMaterial = () => new THREE.MeshLambertMaterial({ color: 0xf3e3c0 });
  const add = (geo, material, x, y, z, name) => {
    const m = new THREE.Mesh(geo, material);
    m.position.set(x, y, z);
    m.castShadow = m.receiveShadow = true;
    m.name = name;
    group.add(m);
    return m;
  };

  // Torii on the path, in front of the steps up to the clearing.
  const t = SITE.torii;
  add(torii(), occluding, t.x, t.y, t.z, 'torii');
  for (const sx of [-1.35, 1.35]) {
    colliders.push({ x: t.x + sx, z: t.z, r: 0.3 });
    proxies.addCylinder(t.x + sx, t.z, 0.2, t.y, t.y + 3.3);
  }
  proxies.addBox([t.x - 2.2, t.y + 2.3, t.z - 0.25], [t.x + 2.2, t.y + 3.5, t.z + 0.25], { density: 0.9 });

  // Chibi house in the west meadow; its window glows at night.
  const hx = -12, hz = 3.5, hy = terrain.heightAt(hx, hz);
  add(house(), occluding, hx, hy, hz, 'house');
  const win = glowMaterial();
  add(box(0.8, 0.5, 0.04, -1.1, 1.05, 1.66), win, hx, hy, hz, 'house-window');
  lighting.addGlow(win, PAPER, 2.2);
  lighting.addLantern({ position: new THREE.Vector3(hx - 1.1, hy + 1.3, hz + 2.3), intensity: 7, distance: 7, priority: 1 });
  colliders.push({ minX: hx - 2.3, maxX: hx + 2.3, minZ: hz - 1.9, maxZ: hz + 1.9 });
  proxies.addBox([hx - 2.5, hy, hz - 2.4], [hx + 2.5, hy + 3.6, hz + 2.4]);

  // Shrine under the giant tree, with two paper lanterns.
  const s = SITE.shrine;
  const shrine = new THREE.Group();
  shrine.name = 'shrine';
  shrine.position.copy(s);
  const shrineBody = new THREE.Mesh(shrineParts(), solid);
  shrineBody.castShadow = shrineBody.receiveShadow = true;
  shrine.add(shrineBody);
  const paper = glowMaterial();
  for (const x of [-1.05, 1.05]) {
    const lamp = new THREE.Mesh(box(0.24, 0.3, 0.24, x, 1.25, 0.35), paper);
    lamp.castShadow = true;
    shrine.add(lamp);
  }
  lighting.addGlow(paper, PAPER, 3);
  lighting.addLantern({ position: new THREE.Vector3(s.x, s.y + 1.4, s.z + 0.9), intensity: 6, distance: 7, priority: 2 });
  group.add(shrine);
  highlightables.push(shrine);
  colliders.push({ minX: s.x - 0.9, maxX: s.x + 0.9, minZ: s.z - 0.75, maxZ: s.z + 0.75 });
  proxies.addBox([s.x - 0.8, s.y, s.z - 0.65], [s.x + 0.8, s.y + 1.85, s.z + 0.65]);

  // Stone lantern beside the steps; the brightest light at night.
  const lx = 0.9, lz = -2.0, ly = terrain.heightAt(lx, lz);
  const lantern = new THREE.Group();
  lantern.name = 'stone-lantern';
  lantern.position.set(lx, ly, lz);
  const stone = new THREE.Mesh(lanternParts(), solid);
  stone.castShadow = stone.receiveShadow = true;
  const flame = glowMaterial();
  lantern.add(stone, new THREE.Mesh(box(0.26, 0.28, 0.26, 0, 1.13, 0), flame));
  lighting.addGlow(flame, PAPER, 4);
  lighting.addLantern({ position: new THREE.Vector3(lx, ly + 1.27, lz), intensity: 10, distance: 10, priority: 3 });
  group.add(lantern);
  highlightables.push(lantern);
  colliders.push({ x: lx, z: lz, r: 0.45 });
  proxies.addCylinder(lx, lz, 0.3, ly, ly + 1.8, { shade: false });

  // Bridge over the stream.
  add(bridgeGeometry(SITE.bridge), solid, 0, 0, 0, 'bridge');

  // Rocks: one highlightable boulder, the rest merged into a single draw.
  const big = add(rockGeometry(rng, 1.1, 0.95, 0.9), solid, 6.8, terrain.heightAt(6.8, 4.6), 4.6, 'boulder');
  big.rotation.y = 0.6;
  highlightables.push(big);
  colliders.push({ x: 6.8, z: 4.6, r: 1.0 });
  proxies.addSphere(6.8, big.position.y + 0.4, 4.6, 0.9, { shade: false });

  const rockSpots = [
    [9.5, 10.2, 0.6], [11, 10.6, 0.4], [14.5, 9.6, 0.7], [-6, 9.5, 0.5], [-7.2, 10.1, 0.35], [-20, 8.5, 0.8],
    [8.5, -4.5, 0.5], [-8.5, -3.6, 0.6], [16.5, -8.5, 0.7], [-1.5, 16.8, 0.45], [7.5, 17.6, 0.55], [24, -2, 0.9],
    [-15, -14, 0.8], [1.5, -20, 0.6], [-25, 8, 0.7], [18, 18.5, 0.5],
  ];
  const rocks = rockSpots.map(([x, z, s]) => {
    const g = rockGeometry(rng, s * rng.range(1.0, 1.5), s * rng.range(0.7, 1.0), s * rng.range(0.9, 1.3));
    g.rotateY(rng() * Math.PI * 2);
    colliders.push({ x, z, r: s * 1.1 });
    return g.translate(x, terrain.heightAt(x, z), z);
  });
  add(merge(rocks), solid, 0, 0, 0, 'rocks');

  return { group, colliders, highlightables };
}
