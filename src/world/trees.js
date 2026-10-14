// Trees: six species plus bushes and the giant landmark tree. Trunks are shared per variant and
// instanced (rotated and scaled per tree); every tree grows its own foliage around its branch tips,
// so no two read as copies. All clumps of the scene go into two instanced billboard meshes
// (camera-facing balls and upright conifer tiers) with per-instance tint, atlas cell, mirroring
// and sway. Each tree also registers shade/view proxies and a collision circle.

import * as THREE from 'three';
import { makeRng } from '../core/math.js';
import { createEnvMaterial, createBillboardMaterial, createBillboardDepthMaterial, CENTERED_QUAD, UPRIGHT_QUAD } from '../render/materials.js';
import { L, CLUMP } from './art.js';
import { env, limb, merge } from './geom.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const trunkAO = y => 0.62 + 0.38 * Math.min(1, Math.max(0, y / 2.5));

function trunkGeometry(parts, layer, height, sway = 0.6) {
  return env(merge(parts), { layer, ao: trunkAO, wind: (x, y) => sway * Math.max(0, (y - 1.2) / height) ** 2 });
}

// Branch tips around a fork, spread evenly with jitter.
function tipsAround(rng, n, fork, radius, y0, y1) {
  const tips = [], a0 = rng() * Math.PI * 2;
  for (let k = 0; k < n; k++) {
    const a = a0 + (k / n) * Math.PI * 2 + rng.range(-0.3, 0.3), r = radius * rng.range(0.75, 1.1);
    tips.push(V(fork.x + Math.cos(a) * r, rng.range(y0, y1), fork.z + Math.sin(a) * r));
  }
  return tips;
}

/** Species: trunk(rng) -> { geo, tips } once per variant; foliage(rng, tips) -> clumps per tree. */
const SPECIES = {
  broadleaf: {
    variants: 2, radius: 0.35, trunkH: 3,
    trunk(rng) {
      const fork = V(rng.range(-0.2, 0.2), 2.7, rng.range(-0.2, 0.2));
      const tips = tipsAround(rng, rng.int(3, 4), fork, 2.0, 5.2, 6.4);
      const parts = [limb(V(0, -0.3, 0), V(0, 0.6, 0), 0.5, 0.33), limb(V(0, 0.5, 0), fork, 0.33, 0.25)];
      for (const t of tips) parts.push(limb(fork, t, 0.2, 0.07, 6));
      tips.push(V(fork.x, 7.0, fork.z));
      return { geo: trunkGeometry(parts, L.BARK, 7), tips };
    },
    foliage(rng, tips, out) {
      const tints = ['#6aa044', '#76a94a', '#5f963f', '#82b04f'];
      for (const t of tips) {
        for (let k = rng.int(2, 3); k > 0; k--) {
          out.push({ p: V(t.x + rng.range(-0.9, 0.9), t.y + rng.range(-0.5, 0.7), t.z + rng.range(-0.9, 0.9)), w: rng.range(2.4, 3.4), tile: rng.pick([CLUMP.ROUND_A, CLUMP.ROUND_B, CLUMP.ROUND_C]), tint: rng.pick(tints) });
        }
      }
    },
    canopy: tips => tips.map(t => ({ c: t, r: 2.2 })),
  },
  cedar: {
    variants: 2, radius: 0.4, trunkH: 10,
    trunk(rng) {
      const h = rng.range(11, 13);
      const parts = [limb(V(0, -0.3, 0), V(0, 1, 0), 0.55, 0.4), limb(V(0, 1, 0), V(rng.range(-0.2, 0.2), h, rng.range(-0.2, 0.2)), 0.4, 0.06)];
      return { geo: trunkGeometry(parts, L.BARK, h, 0.4), tips: [V(0, h, 0)] };
    },
    foliage(rng, tips, out) {
      const top = tips[0].y, tints = ['#3f6f56', '#456f50', '#3a6650'];
      const tint = rng.pick(tints);
      for (let y = 2.8; y < top - 0.8; y += rng.range(1.15, 1.45)) {
        const t = (y - 2.8) / (top - 2.8);
        out.push({ p: V(rng.range(-0.15, 0.15), y, rng.range(-0.15, 0.15)), w: 4.6 - t * 3.3, h: 2.5 - t * 0.6, tile: CLUMP.TIER, tint, upright: true, sway: 0.4 });
      }
    },
    canopy: tips => [{ c: V(0, tips[0].y * 0.55, 0), r: 2.6 }],
  },
  pine: {
    variants: 2, radius: 0.32, trunkH: 4,
    trunk(rng) {
      const lean = rng.range(0.8, 1.6), dir = rng() * Math.PI * 2;
      const pts = [V(0, -0.3, 0), V(0, 1.8, 0), V(lean * 0.6, 3.6, 0), V(lean, 5.3, 0.3)].map(p => p.applyAxisAngle(V(0, 1, 0), dir));
      const parts = [];
      for (let k = 0; k < 3; k++) parts.push(limb(pts[k], pts[k + 1], 0.34 - k * 0.08, 0.26 - k * 0.07, 6));
      const tips = [pts[3].clone().add(V(0, 0.5, 0))];
      for (const [k, y] of [[1, 2.6], [2, 4.0], [1, 3.2]]) {
        const a = rng() * Math.PI * 2, base = pts[k].clone().lerp(pts[k + 1], 0.5), tip = V(base.x + Math.cos(a) * 2.6, y + rng.range(0, 0.6), base.z + Math.sin(a) * 2.6);
        parts.push(limb(base, tip, 0.12, 0.05, 5));
        tips.push(tip);
      }
      return { geo: trunkGeometry(parts, L.BARK, 6, 0.4), tips };
    },
    foliage(rng, tips, out) {
      const tints = ['#4a7c48', '#3f6e42', '#557f4a'];
      for (const t of tips) out.push({ p: V(t.x, t.y + 0.25, t.z), w: rng.range(3.0, 3.8), h: rng.range(1.5, 1.9), tile: CLUMP.PAD, tint: rng.pick(tints), sway: 0.6 });
    },
    canopy: tips => tips.map(t => ({ c: t, r: 1.8 })),
  },
  maple: {
    variants: 1, radius: 0.22, trunkH: 2.5,
    trunk(rng) {
      const fork = V(0.1, 2.0, 0);
      const tips = tipsAround(rng, 4, fork, 1.5, 3.8, 4.8);
      const parts = [limb(V(0, -0.3, 0), fork, 0.24, 0.16)];
      for (const t of tips) parts.push(limb(fork, t, 0.12, 0.05, 5));
      tips.push(V(0, 5.4, 0));
      return { geo: trunkGeometry(parts, L.DARKWOOD, 5.5), tips };
    },
    foliage(rng, tips, out) {
      const tints = ['#e0552a', '#e8782c', '#d4402a', '#efa23e'];
      for (const t of tips) for (let k = 0; k < 2; k++) {
        out.push({ p: V(t.x + rng.range(-0.7, 0.7), t.y + rng.range(-0.4, 0.5), t.z + rng.range(-0.7, 0.7)), w: rng.range(1.8, 2.5), tile: CLUMP.MAPLE, tint: rng.pick(tints) });
      }
    },
    canopy: tips => tips.map(t => ({ c: t, r: 1.6 })),
  },
  bamboo: {
    variants: 1, radius: 1.1, trunkH: 7,
    trunk(rng) {
      const parts = [], tips = [];
      for (let k = 0; k < 10; k++) {
        const a = rng() * Math.PI * 2, r = rng.range(0, 1.0), h = rng.range(6.5, 9);
        const base = V(Math.cos(a) * r, -0.2, Math.sin(a) * r), tip = V(base.x + rng.range(-0.6, 0.6), h, base.z + rng.range(-0.6, 0.6));
        parts.push(limb(base, tip, 0.08, 0.05, 5));
        tips.push(tip);
      }
      return { geo: trunkGeometry(parts, L.BAMBOO, 8, 0.9), tips };
    },
    foliage(rng, tips, out) {
      const tints = ['#9cc35c', '#a9c865', '#8db853'];
      for (const t of tips) for (let k = 0; k < 2; k++) {
        out.push({ p: V(t.x + rng.range(-0.5, 0.5), t.y - k * 1.6 - rng.range(0, 0.6), t.z + rng.range(-0.5, 0.5)), w: rng.range(1.5, 2.1), tile: CLUMP.BAMBOO, tint: rng.pick(tints), sway: 1.4 });
      }
    },
    canopy: () => [{ c: V(0, 6.5, 0), r: 2.6 }],
  },
  sapling: {
    variants: 1, radius: 0.15, trunkH: 2,
    trunk(rng) {
      const tips = [V(0.5, 3.4, 0.2), V(-0.5, 3.1, -0.2), V(0, 4.3, 0)];
      const parts = [limb(V(0, -0.3, 0), V(0, 4.0, 0), 0.13, 0.05, 6)];
      for (const t of tips.slice(0, 2)) parts.push(limb(V(0, 2.2, 0), t, 0.06, 0.03, 5));
      return { geo: trunkGeometry(parts, L.GRANITE, 4.3), tips };
    },
    foliage(rng, tips, out) {
      const tints = ['#8fc35c', '#a0cb67', '#86ba55'];
      for (const t of tips) out.push({ p: V(t.x, t.y, t.z), w: rng.range(1.4, 1.9), tile: CLUMP.ROUND_C, tint: rng.pick(tints), sway: 1.2 });
    },
    canopy: () => [{ c: V(0, 3.6, 0), r: 1.4 }],
  },
  bush: {
    variants: 0, radius: 0.7, trunkH: 0,
    foliage(rng, tips, out, variant) {
      const tints = variant === 'azalea' ? ['#ee93b4', '#f5a9c4', '#e486aa'] : ['#5a9443', '#4f873f', '#64a04a'];
      const n = rng.int(1, 3);
      for (let k = 0; k < n; k++) {
        const w = rng.range(1.5, 2.4);
        out.push({ p: V(rng.range(-0.7, 0.7) * (n > 1), w * 0.32, rng.range(-0.7, 0.7) * (n > 1)), w, h: w * 0.8, tile: CLUMP.BUSH, tint: rng.pick(tints), sway: 0.5 });
      }
    },
    canopy: () => [],
  },
};

/** The landmark: a ~38 m camphor whose crown leans south over the clearing and the shrine. */
function giantTree(rng) {
  const parts = [limb(V(0, -0.5, 0), V(0, 6, 0), 3.1, 2.6, 12), limb(V(0, 6, 0), V(0.4, 13, 0.8), 2.6, 2.1, 12)];
  for (let k = 0; k < 9; k++) { // buttress roots spreading over the clearing
    const a = (k / 9) * Math.PI * 2 + rng.range(-0.2, 0.2), len = rng.range(5.5, 9.5);
    const mid = V(Math.cos(a) * len * 0.5, 0.15, Math.sin(a) * len * 0.5);
    parts.push(limb(V(Math.cos(a) * 1.6, 1.4, Math.sin(a) * 1.6), mid, 1.0, 0.55, 7));
    parts.push(limb(mid, V(Math.cos(a) * len, -0.45, Math.sin(a) * len), 0.55, 0.18, 6));
  }
  const crown = V(0, 24, 3.5); // crown centre, shifted south over the clearing
  const tips = [];
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * Math.PI * 2 + rng.range(-0.25, 0.25);
    const r = rng.range(9, 13) * (Math.sin(a) > 0 ? 1.2 : 0.9); // longer limbs toward the south (+z)
    const tip = V(crown.x + Math.cos(a) * r, rng.range(18, 24), crown.z + Math.sin(a) * r);
    parts.push(limb(V(0.3, 12.5, 0.6), tip, 1.25, 0.45, 8));
    const sub = tip.clone().add(V(Math.cos(a + 0.8) * 4, rng.range(-3, 2), Math.sin(a + 0.8) * 4));
    parts.push(limb(tip, sub, 0.45, 0.18, 6));
    tips.push(tip, sub);
  }
  const geo = env(merge(parts), { layer: L.BIGBARK, ao: y => 0.55 + 0.45 * Math.min(1, Math.max(0, (y + 0.4) / 4)) });

  const clumps = [], tints = ['#4c8739', '#56913f', '#447c37', '#5f9a45'];
  const add = (p, w) => clumps.push({ p, w, tile: rng.pick([CLUMP.ROUND_A, CLUMP.ROUND_B, CLUMP.ROUND_C]), tint: rng.pick(tints), sway: 0.45 });
  for (const t of tips) for (let k = 0; k < 5; k++) add(V(t.x + rng.range(-2.5, 2.5), t.y + rng.range(-1.2, 2.5), t.z + rng.range(-2.5, 2.5)), rng.range(4, 5.5));
  for (let k = 0; k < 44; k++) { // dome
    const a = rng() * Math.PI * 2, e = rng.range(0.15, 1.2), r = 14;
    add(V(crown.x + Math.cos(a) * Math.cos(e) * r, crown.y + Math.sin(e) * 9, crown.z + Math.sin(a) * Math.cos(e) * r), rng.range(4.2, 6));
  }
  for (let k = 0; k < 18; k++) { // fringe on the south side: a band of leaves framing the clearing
    const a = rng.range(-0.2, Math.PI + 0.2), r = rng.range(13, 17);
    add(V(crown.x + Math.cos(a) * r, rng.range(10.5, 14), crown.z + Math.sin(a) * r * 0.9), rng.range(3.4, 4.4));
  }
  const canopy = [{ c: crown, r: 15 }, ...tips.map(t => ({ c: t, r: 5 }))];
  return { geo, clumps, canopy };
}

const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
const UP = V(0, 1, 0);

/**
 * placements: [{ species, x, y, z, variant? }] (y = ground height). Returns the meshes plus
 * colliders [{ x, z, r }]; proxies are added to the given ProxySet.
 */
export function buildTrees({ placements, giant, layers, clumpTexture, proxies, seed = 7 }) {
  const rng = makeRng(seed);
  const trunkMaterial = createEnvMaterial(layers, { wind: true, occluder: true });
  const group = new THREE.Group();
  const colliders = [];
  const clumps = [];

  // Shared trunk shapes per species variant.
  const shapes = {};
  for (const [name, sp] of Object.entries(SPECIES)) {
    shapes[name] = [];
    for (let v = 0; v < sp.variants; v++) shapes[name].push({ ...sp.trunk(rng), matrices: [] });
  }

  const place = (pl, localClumps, canopy, { radius, trunkH }) => {
    const rot = rng() * Math.PI * 2, scale = rng.range(0.85, 1.15);
    _q.setFromAxisAngle(UP, rot);
    _m.compose(_p.set(pl.x, pl.y, pl.z), _q, _s.setScalar(scale));
    for (const c of localClumps) {
      clumps.push({ ...c, p: c.p.clone().applyMatrix4(_m), w: c.w * scale, h: (c.h ?? c.w) * scale });
    }
    for (const { c, r } of canopy) {
      const w = c.clone().applyMatrix4(_m);
      proxies.addSphere(w.x, w.y, w.z, r * scale, { density: 0.75 });
    }
    colliders.push({ x: pl.x, z: pl.z, r: radius * scale });
    if (trunkH) proxies.addCylinder(pl.x, pl.z, radius * scale, pl.y - 0.5, pl.y + trunkH * scale, { density: 1 });
    return _m.clone();
  };

  for (const pl of placements) {
    const sp = SPECIES[pl.species];
    const local = [];
    if (sp.variants) {
      const shape = rng.pick(shapes[pl.species]);
      sp.foliage(rng, shape.tips, local, pl.variant);
      shape.matrices.push(place(pl, local, sp.canopy(shape.tips), sp));
    } else {
      sp.foliage(rng, [], local, pl.variant);
      place(pl, local, local.map(c => ({ c: c.p, r: c.w * 0.5 })), sp);
    }
  }

  for (const list of Object.values(shapes)) for (const shape of list) {
    if (!shape.matrices.length) continue;
    const mesh = new THREE.InstancedMesh(shape.geo, trunkMaterial, shape.matrices.length);
    shape.matrices.forEach((m, k) => mesh.setMatrixAt(k, m));
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.computeBoundingSphere();
    group.add(mesh);
  }

  if (giant) {
    const g = giantTree(rng);
    const mesh = new THREE.Mesh(g.geo, createEnvMaterial(layers, { occluder: true }));
    mesh.position.copy(giant);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.name = 'giant-tree';
    group.add(mesh);
    for (const c of g.clumps) clumps.push({ ...c, p: c.p.add(giant), h: c.w });
    for (const { c, r } of g.canopy) proxies.addSphere(giant.x + c.x, giant.y + c.y, giant.z + c.z, r, { density: 0.8 });
    proxies.addCylinder(giant.x, giant.z, 3.0, giant.y - 1, giant.y + 14, { density: 1 });
    colliders.push({ x: giant.x, z: giant.z, r: 3.2 });
  }

  group.add(clumpMesh(clumps.filter(c => !c.upright), clumpTexture, 'sphere'));
  group.add(clumpMesh(clumps.filter(c => c.upright), clumpTexture, 'upright'));
  return { group, colliders };
}

function clumpMesh(list, texture, mode) {
  const opts = { map: texture, mode, atlas: [4, 2], wind: true, occluder: true };
  const geo = (mode === 'sphere' ? CENTERED_QUAD : UPRIGHT_QUAD).clone();
  const mesh = new THREE.InstancedMesh(geo, createBillboardMaterial(opts), list.length);
  const tiles = new Float32Array(list.length), sways = new Float32Array(list.length);
  const c = new THREE.Color();
  const rng = makeRng(list.length * 31 + 5);
  list.forEach((k, i) => {
    _m.compose(k.p, _q.identity(), _s.set(k.w, k.h ?? k.w, 1));
    mesh.setMatrixAt(i, _m);
    tiles[i] = k.tile + (rng() < 0.5 ? 0.5 : 0); // random mirroring
    sways[i] = (k.sway ?? 1) * rng.range(0.7, 1.3);
    mesh.setColorAt(i, c.set(k.tint).multiplyScalar(rng.range(0.92, 1.06)));
  });
  geo.setAttribute('aTile', new THREE.InstancedBufferAttribute(tiles, 1));
  geo.setAttribute('aSway', new THREE.InstancedBufferAttribute(sways, 1));
  mesh.customDepthMaterial = createBillboardDepthMaterial(opts);
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.computeBoundingSphere();
  mesh.name = `clumps-${mode}`;
  return mesh;
}
