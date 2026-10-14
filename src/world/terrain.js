// Terraced block terrain on a 1 m grid: higher at the back (north) and framed on every side so the
// camera rarely sees sky. Stairs, a ramp, a stream channel, world-UV layers, corner AO in the
// vertex colours and grass lips on cliff tops. Also answers height and walkability queries.

import * as THREE from 'three';
import { fbm, clamp, lerp } from '../core/math.js';
import { L } from './art.js';

export const WATER_Y = -0.55;
const BED_Y = -1.3;
const N = 112;        // cells per side
const ORIGIN = -56;   // world x/z of cell 0's corner
const MAX_RUN = 8;    // longest merged run of flat top faces
const GRASSY = new Set([L.GRASS, L.MOSS]);
const RAMP_X = 1; // ramp[i]: 0 flat, 1..4 rises toward +x, -x, +z, -z

/** Stream centre line and half width. */
const streamZ = x => 12 + 2.2 * Math.sin(x * 0.085 + 0.6) + Math.sin(x * 0.21);
const streamHalf = x => 2.0 + 0.5 * Math.sin(x * 0.13 + 1.3);

/** Landmark positions the scene and the terrain agree on. */
export const SITE = {
  giantTree: new THREE.Vector3(5, 1, -13),
  shrine: new THREE.Vector3(-2.5, 1, -7.2),
  torii: new THREE.Vector3(-2.5, 0, -0.8),
  spawn: new THREE.Vector3(0.5, 0, 5),
  bridge: { x0: 2, x1: 5, z0: 9.6, z1: 18.6, y: 0.22 },
};

function baseHeight(x, z) {
  const n = (fbm(x * 0.06, z * 0.06, 2, 7) - 0.5) * 7; // organic, still blocky, edges
  let h = 0;
  const mx = (x - 2) / 15, mz = (z + 12) / 9.2;
  if (mx * mx + mz * mz < 1 + n * 0.04 || z + n < -16) h = 1; // the clearing under the giant tree
  if (z + n < -23) h = 3;
  if (z + n * 1.1 < -32) h = 6;
  if (z + n < -41) h = 9;
  if (x - n < -22 && z < 6) h = Math.max(h, 2);
  if (x - n < -33) h = Math.max(h, 4.5);
  if (x + n > 21) h = Math.max(h, 1.5);
  if (x + n > 29) h = Math.max(h, 3);
  if (x + n > 38) h = Math.max(h, 5.5);
  const far = streamZ(x) + streamHalf(x);
  if (z - n > far + 9) h = Math.max(h, 1);
  if (z - n > far + 17) h = Math.max(h, 2.5);
  if (z - n > far + 25) h = Math.max(h, 4);
  if (Math.max(Math.abs(x), Math.abs(z)) + n > 47) h = Math.max(h, 9 + Math.round(fbm(x * 0.1, z * 0.1, 2, 3) * 4) * 0.5);
  return h;
}

const PATHS = [
  { w: 1.0, pts: [[3.5, 24], [3.5, 18], [3.5, 10], [2, 7], [0, 3], [-2.5, 0.5], [-2.5, -3], [-2.5, -8]] },
  { w: 0.8, pts: [[0, 3], [9, 2.5], [18, 2.5], [23, 2.5]] },
  { w: 0.8, pts: [[-2.5, 0], [-10, 0.5], [-20, 0.5]] },
  { w: 0.7, pts: [[-1, -5], [3, -6], [9, -8.5], [11.5, -15], [11.5, -21]] },
];

function distToPolyline(x, z, pts) {
  let best = Infinity;
  for (let k = 0; k < pts.length - 1; k++) {
    const [ax, az] = pts[k], [bx, bz] = pts[k + 1];
    const dx = bx - ax, dz = bz - az;
    const t = clamp(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    best = Math.min(best, Math.hypot(x - ax - dx * t, z - az - dz * t));
  }
  return best;
}

export class Terrain {
  constructor() {
    this.h = new Float32Array(N * N);
    this.top = new Uint8Array(N * N);
    this.water = new Uint8Array(N * N);
    this.ramp = new Uint8Array(N * N);
    this.r0 = new Float32Array(N * N);
    this.r1 = new Float32Array(N * N);
    this.side = new Int8Array(N * N).fill(-1); // forced side layer (stairs)
    this.bridges = [SITE.bridge];
    this.author();
  }

  author() {
    const giant = SITE.giantTree;
    for (let iz = 0; iz < N; iz++) for (let ix = 0; ix < N; ix++) {
      const x = ORIGIN + ix + 0.5, z = ORIGIN + iz + 0.5, i = iz * N + ix;
      this.h[i] = baseHeight(x, z);
      if (Math.abs(z - streamZ(x)) < streamHalf(x) && Math.abs(x) < 47) this.water[i] = 1;
      const underCanopy = Math.hypot(x - giant.x, (z - giant.z) * 1.15) < 13;
      this.top[i] = this.h[i] >= 6 || underCanopy ? L.MOSS : L.GRASS;
    }
    // Sand banks along the stream.
    for (let iz = 1; iz < N - 1; iz++) for (let ix = 1; ix < N - 1; ix++) {
      const i = iz * N + ix;
      if (this.water[i]) continue;
      if (this.water[i - 1] || this.water[i + 1] || this.water[i - N] || this.water[i + N]) this.top[i] = L.SAND;
    }
    for (const p of PATHS) this.paint((x, z) => distToPolyline(x, z, p.pts) < p.w, L.PATH);

    // Steps from the meadow up to the clearing, with a paved forecourt before the shrine.
    this.fill(-4.5, -9.5, -0.5, -3, 1, L.PAVING);
    this.fill(-4.5, -3, -0.5, -2, 0.5, L.PAVING, L.PAVING);
    // Stairs from the clearing to the north terrace, cut into the wall.
    this.fill(9, -20, 14, -16, 1);
    this.fill(9, -27, 14, -23, 3);
    this.fill(9, -23, 10, -20, 3);
    this.fill(13, -23, 14, -20, 3);
    [1.5, 2, 2.5].forEach((h, k) => this.fill(10, -21 - k, 13, -20 - k, h, L.PAVING, L.PAVING));
    // Stairs up to the west terrace.
    this.fill(-27, -2, -23, 3, 2);
    this.fill(-23, -2, -20, -1, 2);
    this.fill(-23, 2, -20, 3, 2);
    [0.5, 1, 1.5].forEach((h, k) => this.fill(-21 - k, -1, -20 - k, 2, h, L.PAVING, L.PAVING));
    // Earth ramp up to the east hill.
    this.fill(22, 0, 26, 5, 1.5);
    for (let k = 0; k < 3; k++) this.setRamp(19 + k, 1, 20 + k, 4, RAMP_X, k * 0.5, k * 0.5 + 0.5, L.PATH);
  }

  idx(x, z) {
    const ix = Math.floor(x - ORIGIN), iz = Math.floor(z - ORIGIN);
    return ix < 0 || iz < 0 || ix >= N || iz >= N ? -1 : iz * N + ix;
  }

  forCells(x0, z0, x1, z1, fn) {
    for (let z = z0 + 0.5; z < z1; z++) for (let x = x0 + 0.5; x < x1; x++) { const i = this.idx(x, z); if (i >= 0) fn(i); }
  }

  fill(x0, z0, x1, z1, h, top = null, side = -1) {
    this.forCells(x0, z0, x1, z1, i => {
      this.h[i] = h; this.ramp[i] = 0; this.water[i] = 0;
      if (top !== null) this.top[i] = top;
      this.side[i] = side;
    });
  }

  setRamp(x0, z0, x1, z1, dir, lo, hi, top) {
    this.forCells(x0, z0, x1, z1, i => {
      this.ramp[i] = dir; this.r0[i] = lo; this.r1[i] = hi; this.h[i] = hi; this.top[i] = top; this.water[i] = 0;
    });
  }

  paint(test, layer) {
    for (let iz = 0; iz < N; iz++) for (let ix = 0; ix < N; ix++) {
      const i = iz * N + ix;
      if (!this.water[i] && test(ORIGIN + ix + 0.5, ORIGIN + iz + 0.5)) this.top[i] = layer;
    }
  }

  heightAt(x, z) {
    for (const b of this.bridges) if (x >= b.x0 && x < b.x1 && z >= b.z0 && z < b.z1) return b.y;
    const i = this.idx(x, z);
    if (i < 0) return 12;
    if (this.water[i]) return BED_Y;
    if (!this.ramp[i]) return this.h[i];
    const fx = x - Math.floor(x), fz = z - Math.floor(z);
    const t = [0, fx, 1 - fx, fz, 1 - fz][this.ramp[i]];
    return lerp(this.r0[i], this.r1[i], t);
  }

  walkable(x, z) {
    for (const b of this.bridges) if (x >= b.x0 && x < b.x1 && z >= b.z0 && z < b.z1) return true;
    const i = this.idx(x, z);
    return i >= 0 && !this.water[i];
  }

  // Corner height of cell i at grid corner (cx, cz) (0/1 within the cell).
  cornerH(i, cx, cz) {
    if (this.water[i]) return BED_Y;
    const r = this.ramp[i];
    if (!r) return this.h[i];
    const t = [0, cx, 1 - cx, cz, 1 - cz][r];
    return lerp(this.r0[i], this.r1[i], t);
  }

  // Ambient occlusion of a top-face corner: darker where higher cells meet it.
  cornerAO(ix, iz, gx, gz, h) {
    let count = 0;
    for (const [cx, cz] of [[gx - 1, gz - 1], [gx, gz - 1], [gx - 1, gz], [gx, gz]]) {
      if (cx === ix && cz === iz) continue;
      if (cx < 0 || cz < 0 || cx >= N || cz >= N) continue;
      const j = cz * N + cx;
      if (!this.water[j] && this.h[j] >= h + 0.45) count++;
    }
    return [1, 0.8, 0.68, 0.6][count];
  }

  /** Builds the terrain geometry (tops, cliff sides with lip data, and an outer skirt). */
  buildGeometry() {
    const pos = [], nor = [], col = [], lay = [], tops = [], idx = [];
    const _n = new THREE.Vector3(), _e1 = new THREE.Vector3(), _e2 = new THREE.Vector3();
    const cool = h => { const c = clamp(h / 10, 0, 1) * 0.08; return [1 - c, 1, 1 + c * 0.6]; };
    // Corners in any order around the quad; flipped if needed so the face points along `normal`.
    const quad = (corners, normal, layer, lip, topY, shades) => {
      _e1.subVectors(corners[1], corners[0]);
      _e2.subVectors(corners[2], corners[0]);
      _n.crossVectors(_e1, _e2);
      const order = _n.dot(normal) >= 0 ? [0, 1, 2, 3] : [0, 3, 2, 1];
      const base = pos.length / 3;
      for (const k of order) {
        const c = corners[k], t = cool(c.y), s = shades[k];
        pos.push(c.x, c.y, c.z);
        nor.push(normal.x, normal.y, normal.z);
        col.push(t[0] * s, t[1] * s, t[2] * s);
        lay.push(layer, lip);
        tops.push(topY);
      }
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    };
    const V = (x, y, z) => new THREE.Vector3(x, y, z);
    const UPN = V(0, 1, 0);

    // Top faces: plain cells merge into runs along x.
    for (let iz = 0; iz < N; iz++) {
      let ix = 0;
      while (ix < N) {
        const i = iz * N + ix;
        if (this.water[i]) { ix++; continue; }
        const h = this.h[i], z0 = ORIGIN + iz, x0 = ORIGIN + ix;
        const ao = [this.cornerAO(ix, iz, ix, iz, h), this.cornerAO(ix, iz, ix + 1, iz, h), this.cornerAO(ix, iz, ix + 1, iz + 1, h), this.cornerAO(ix, iz, ix, iz + 1, h)];
        const plain = !this.ramp[i] && ao.every(a => a === 1);
        let run = 1;
        if (plain) {
          while (ix + run < N && run < MAX_RUN) {
            const j = i + run;
            if (this.water[j] || this.ramp[j] || this.h[j] !== h || this.top[j] !== this.top[i]) break;
            const jx = ix + run;
            if (this.cornerAO(jx, iz, jx + 1, iz, h) !== 1 || this.cornerAO(jx, iz, jx + 1, iz + 1, h) !== 1) break;
            run++;
          }
        }
        const x1 = x0 + run;
        const ys = [this.cornerH(i, 0, 0), this.cornerH(i, 1, 0), this.cornerH(i, 1, 1), this.cornerH(i, 0, 1)];
        const corners = [V(x0, ys[0], z0), V(x1, ys[1], z0), V(x1, ys[2], z0 + 1), V(x0, ys[3], z0 + 1)];
        let normal = UPN;
        if (this.ramp[i]) {
          _e1.subVectors(corners[2], corners[0]);
          _e2.subVectors(corners[1], corners[3]);
          normal = new THREE.Vector3().crossVectors(_e1, _e2).normalize();
          if (normal.y < 0) normal.negate();
        }
        quad(corners, normal, this.top[i], -1, h, ao);
        ix += run;
      }
    }

    // Side faces wherever a neighbour is lower.
    const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    for (let iz = 0; iz < N; iz++) for (let ix = 0; ix < N; ix++) {
      const i = iz * N + ix;
      if (this.water[i]) continue;
      const x0 = ORIGIN + ix, z0 = ORIGIN + iz;
      for (const [dx, dz] of dirs) {
        const jx = ix + dx, jz = iz + dz;
        if (jx < 0 || jz < 0 || jx >= N || jz >= N) continue;
        const j = jz * N + jx;
        // The shared edge's two corners, in this cell's local coordinates.
        const ca = dx ? [dx > 0 ? 1 : 0, 0] : [0, dz > 0 ? 1 : 0];
        const cb = dx ? [dx > 0 ? 1 : 0, 1] : [1, dz > 0 ? 1 : 0];
        const ha = this.cornerH(i, ca[0], ca[1]), hb = this.cornerH(i, cb[0], cb[1]);
        const nA = this.cornerH(j, ca[0] - dx, ca[1] - dz), nB = this.cornerH(j, cb[0] - dx, cb[1] - dz);
        if (ha <= nA + 1e-3 && hb <= nB + 1e-3) continue;
        const drop = Math.max(ha - nA, hb - nB);
        const layer = this.side[i] >= 0 ? this.side[i] : drop >= 1.5 || this.h[i] >= 3 ? L.CLIFF : L.EARTH;
        const lip = !this.ramp[i] && GRASSY.has(this.top[i]) ? this.top[i] : -1;
        const bottomShade = drop >= 1 ? 0.55 : 0.7;
        quad(
          [V(x0 + ca[0], nA, z0 + ca[1]), V(x0 + cb[0], nB, z0 + cb[1]), V(x0 + cb[0], hb, z0 + cb[1]), V(x0 + ca[0], ha, z0 + ca[1])],
          V(dx, 0, dz), layer, lip, Math.max(ha, hb), [bottomShade, bottomShade, 1, 1],
        );
      }
    }

    // Skirt: a plateau ring beyond the grid, level with the frame ridges.
    const S = 320, E = -ORIGIN, sy = 9;
    for (const [ax, az, bx, bz] of [[-S, -S, S, -E], [-S, E, S, S], [-S, -E, -E, E], [E, -E, S, E]]) {
      quad([V(ax, sy, az), V(bx, sy, az), V(bx, sy, bz), V(ax, sy, bz)], UPN, L.MOSS, -1, sy, [1, 1, 1, 1]);
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setAttribute('aLayer', new THREE.Float32BufferAttribute(lay, 2));
    g.setAttribute('aTop', new THREE.Float32BufferAttribute(tops, 1));
    g.setIndex(idx);
    g.computeBoundingSphere();
    return g;
  }

  /** Corner (min x, min z) of every water cell. */
  waterCells() {
    const cells = [];
    for (let iz = 0; iz < N; iz++) for (let ix = 0; ix < N; ix++) if (this.water[iz * N + ix]) cells.push([ORIGIN + ix, ORIGIN + iz]);
    return cells;
  }

  /** Distance in metres (capped at 3) from a grid corner to the nearest dry cell. */
  shoreDistance(x, z) {
    let best = 3;
    for (let dz = -4; dz <= 3; dz++) for (let dx = -4; dx <= 3; dx++) {
      const cx = x + dx + 0.5, cz = z + dz + 0.5, i = this.idx(cx, cz);
      if (i >= 0 && !this.water[i]) best = Math.min(best, Math.max(0, Math.hypot(cx - x, cz - z) - 0.5));
    }
    return best;
  }
}
