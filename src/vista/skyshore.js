// 天岸, the sky shore: a whole land hanging upside down far above the cloud sea, rendered with the
// same column march as the ground, mirrored: the underside of a ceiling at height Hs.
//
// It has to read as land at a glance, small on a phone too, so it carries the signs of land,
// upside down: woods whose conifers hang tips down along every lit edge, a patchwork of fields
// with lit levees, terraces as thin lit lines on the slopes, silver rivers catching the light,
// villages of hanging houses with lit windows, a pagoda hanging spire down. Right above the pass
// the gate: an inverted valley drawn down into a funnel whose mouth points at us. Haze in a few
// flat steps, lit from below by the plain's glow, blue.

import { clamp, smooth, rng, hash2, vnoise, fbm, ridged, IndexLayer, I, pack, mix3, run } from './util.js';
import { marchGen } from './terrain.js';

export const S = {
  land: 1, forest: 2, rock: 3, river: 4, rim: 5, funnel: 6, mouth: 7, funnelRim: 8,
  field: 9, paddy: 10, levee: 11, tree: 12, town: 13, wall: 14, roof: 15, bank: 16,
};
const HAZE_Z = [42, 52, 60, 68];

/**
 * @param o { w, h, cx, yh, f, Hs, funnel: {X, Z, D, R}, towns: [{X, Z, r}], hazeEdgeY, pagoda: {X, Z}, seed }
 */
export function buildSkyShore(o) { return run(buildSkyShoreGen(o)); }

export function* buildSkyShoreGen(o) {
  const { w, h, cx, yh, f, Hs, funnel: Fn } = o;
  const R = rng(o.seed + 501);
  const towns = o.towns;
  const rivers = makeRivers(R, Fn);
  const flatAt = (X, Z) => {
    let fl = 0;
    for (let k = 0; k < towns.length; k++) {
      const t = towns[k], dx = X - t.X, dz = (Z - t.Z) * 0.8, lim = t.r * 1.5;
      if (dx > lim || dx < -lim || dz > lim || dz < -lim) continue;
      const q = Math.sqrt(dx * dx + dz * dz) / t.r;
      if (q < 1.5) fl = Math.max(fl, smooth(1.5, 0.8, q));
    }
    return fl;
  };
  const nearTown = (X, Z) => towns.some(t => Math.hypot(X - t.X, (Z - t.Z) * 0.8) < t.r * 2.6);
  const riverAt = (X, Z) => {
    let best = 1e9;
    for (let k = 0; k < rivers.length; k++) { const d = distRiver(rivers[k], X, Z); if (d < best) best = d; }
    return best;
  };
  // groves: round clumps of trees hanging from the fields, thick around the villages (屋敷林)
  const GC = 1.5;
  const groveAt = (X, Z) => {
    const ci = Math.floor(X / GC), cj = Math.floor(Z / GC);
    let best = 0;
    for (let j = cj - 1; j <= cj + 1; j++) for (let i = ci - 1; i <= ci + 1; i++) {
      const gx = (i + 0.2 + hash2(i, j, 71) * 0.6) * GC, gz = (j + 0.2 + hash2(i, j, 72) * 0.6) * GC;
      let p = 0.16;
      for (const t of towns) { const q = Math.hypot(gx - t.X, (gz - t.Z) * 0.8) / t.r; if (q < 2.6) p = Math.max(p, q > 1.1 ? 0.85 : 0.2); }
      if (hash2(i, j, 73) > p) continue;
      const r = 0.28 + hash2(i, j, 74) * 0.3, d2 = ((X - gx) ** 2 + (Z - gz) ** 2) / (r * r);
      if (d2 < 1) best = Math.max(best, (0.22 + hash2(i, j, 75) * 0.2) * Math.sqrt(1 - d2));
    }
    return best;
  };
  // rounded hanging hills (wooded), mostly beyond the near fields; then the land's own far ranges
  // a band of rounded wooded hills across the land (its "near range"), a few knolls nearer
  const hillAt = (X, Z) => Math.max(
    smooth(0.36, 0.6, fbm(X * 0.06 + 3, Z * 0.05, 3, 83)) * smooth(43, 49, Z) * (1 - smooth(57, 63, Z)),
    smooth(0.62, 0.8, fbm(X * 0.11 + 9, Z * 0.1, 2, 87)) * smooth(32, 38, Z));
  const depth = (X, Z) => {
    const flat = flatAt(X, Z);
    let d = 0.12 + 0.08 * fbm(X * 0.12, Z * 0.12, 2, 81);
    const hl = hillAt(X, Z);
    d += (1 - flat) * hl * hl * (3 - 2 * hl) * (1.5 + 1.1 * smooth(40, 52, Z)) * (0.8 + 0.4 * vnoise(X * 0.3, Z * 0.3, 86));
    const far = smooth(58, 72, Z);
    if (far > 0) d += (1 - flat) * far * (0.6 + Math.pow(ridged(X * 0.045 + 7, Z * 0.035, 3, 84), 1.4) * 4.2);
    const dr = riverAt(X, Z);
    if (dr < 0.9) d -= (0.9 - dr) * (0.1 + 0.6 * hl);   // valleys
    if (Z < 58) d += groveAt(X, Z) * (1 - hl);
    const fx = X - Fn.X, fz = Z - Fn.Z, r = Math.hypot(fx, fz) / Fn.R;
    if (r < 1) d = Math.max(d, Fn.D * Math.pow(1 - r, 1.9));
    return Math.max(0.02, d);
  };
  const height = (X, Z) => Hs - depth(X, Z);
  const m = yield* marchGen({ w, h, cx, yh, f, camY: 0, z0: 4, z1: 140, height, k: 0.013, ceiling: true });
  const L = new IndexLayer(w, h);
  const Lt = norm3([-0.18, -0.85, -0.5]); // light from below (the plain's glow), a little from the left and toward us
  const hazeOf = Z => { let hz = 0; for (const zz of HAZE_Z) if (Z > zz) hz++; return hz; };
  for (let y = 0; y < h; y++) {
   if ((y & 15) === 15) yield;
   for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!m.mask[i]) continue;
    const X = m.X[i], Z = m.Z[i];
    const dd = depth(X, Z);
    const e = Math.max(0.02, Z * 0.005);
    const dx = depth(X + e, Z) - dd, dz = depth(X, Z + e) - dd;
    let nx = -dx, ny = -e, nz = -dz; const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const lam = nx * Lt[0] + ny * Lt[1] + nz * Lt[2];
    const flatness = -ny;                                   // 1: level ground (facing straight down at us)
    const fr = Math.hypot(X - Fn.X, Z - Fn.Z) / Fn.R;
    const px = Z / f;                                       // world size of a pixel across
    let mat, sun = lam > 0.55 ? 6 : lam > 0.25 ? 4 : 2;
    if (fr < 1) {
      // the gate: an inverted valley drawn down to its mouth: wooded flanks, a throat catching the glow
      mat = fr < 0.05 ? S.mouth : fr < 0.11 ? S.funnelRim : S.funnel;
      if (mat === S.funnel && hash2(x >> 1, y, 7) < 0.3 && (y & 1)) sun = Math.min(6, sun + 2);
    } else {
      const dr = riverAt(X, Z), rw = Math.max(0.12 + 0.04 * Math.sin(X * 1.7 + Z * 0.6), px * 0.7);
      const fl = flatAt(X, Z), hl = hillAt(X, Z), gv = Z < 58 ? groveAt(X, Z) : 0;
      if (dr < rw) { mat = S.river; sun = 4 + (hash2(x, y, 3) < 0.3 ? 2 : 0); }
      else if (dr < rw + px * 1.1 && Z < 56) mat = S.bank;
      else if (hl > 0.12 && hl < 0.42 && Z < 58 && nearTown(X, Z) && flatness > 0.5) {
        // terraces on the lower slopes by the villages: the contour lines of the hill, lit
        const c = dd * 10 + vnoise(X * 0.4, Z * 0.4, 66) * 0.3;
        mat = c - Math.floor(c) < 0.24 ? S.levee : S.field;
        if (mat === S.field) sun = 2 + 2 * (Math.floor(c) % 3);
      } else if (hl > 0.25 || gv > 0.04 || Z > 62 || flatness < 0.7) {
        // woods: a carpet of hanging crowns, tips catching the light from below
        mat = S.forest;
        if (hash2(x >> 1, y, 7) < 0.34 && (y & 1) && sun < 6) sun += 2;
      } else if (fl > 0.55) mat = S.town;
      else {
        // fields: a patchwork of parcels in zones of their own direction, each its own tone (crops,
        // stubble, fallow), the flooded ones catching the glow
        const th = (vnoise(X * 0.06 + 5, Z * 0.06, 61) - 0.5) * 1.2, c = Math.cos(th), sn = Math.sin(th);
        const u = X * c - Z * sn * 0.5, v = X * sn * 0.5 + Z * c;
        const su = 0.9 + 0.7 * vnoise(X * 0.1, Z * 0.1, 62), sv = 0.8 + 0.5 * vnoise(X * 0.09 + 4, Z * 0.09, 64);
        const iu = Math.floor(u / su), iv = Math.floor(v / sv);
        const hp = hash2(iu, iv, 63);
        if (hp < 0.22) { mat = S.paddy; sun = hp < 0.08 ? 6 : hp < 0.15 ? 4 : 2; }
        else { mat = S.field; sun = hp < 0.45 ? 2 : hp < 0.75 ? 4 : 6; }
      }
    }
    L.idx[i] = I(mat, sun, 3, hazeOf(Z));
   }
  }
  yield;
  // lower edges of nearer land against farther land catch the light from below
  const src = L.idx.slice();
  const rimAt = new Uint8Array(w * h);
  for (let y = 0; y < h - 2; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!src[i]) continue;
    if (!src[i + w] || m.Z[i + w] > m.Z[i] * 1.15) {
      const mt = src[i] >> 8;
      if (mt === S.funnel || mt === S.mouth) L.idx[i] = I(S.funnelRim, 4, 3, src[i] & 7);
      else { L.idx[i] = I(S.rim, 6, 3, src[i] & 7); rimAt[i] = 1; }
    }
  }
  // conifers hanging tips down along the lit edges: the edge of a wood, upside down
  {
    const SHAPES = [[], [0], [1, 0], [1, 1, 0], [2, 1, 1, 0], [2, 1, 1, 0, 0], [2, 2, 1, 1, 0, 0]];
    const ref = L.idx.slice(), last = new Int32Array(h).fill(-9);
    for (let x = 0; x < w; x++) for (let y = 1; y < h - 2; y++) {
      const i = y * w + x;
      if (!rimAt[i]) continue;
      const Z = m.Z[i];
      if (Z > 72 || x - last[y] < 2 || Math.abs(x - last[y - 1]) < 2 || Math.abs(x - last[y + 1]) < 2) continue;
      if (hash2(x, y, 97) > 0.8) continue;
      const ht = clamp(Math.round((120 / Z) * (0.6 + 0.8 * hash2(x, y, 98))), 2, 6), shape = SHAPES[ht];
      const hz = ref[i] & 7;
      for (let k = 0; k < ht; k++) {
        const yy = y + 1 + k; if (yy >= h) break;
        for (let q = -shape[k]; q <= shape[k]; q++) {
          const xx = x + q; if (xx < 0 || xx >= w) continue;
          const j = yy * w + xx;
          if (ref[j] && m.Z[j] < Z * 1.06) continue;      // only over what lies beyond
          L.idx[j] = k === ht - 1 ? I(S.rim, 5, 3, hz) : I(S.tree, q > 0 ? 4 : 2, 3, hz);
        }
      }
      last[y] = x + (hash2(x, 7, 99) < 0.5 ? 1 : 0);
    }
  }
  yield;
  // its far edge: the land ends in the haze beyond a distance (frayed a little); its ranges nearer
  // than that hang below the edge, dark against the light between the shores
  const hazeEdgeY = o.hazeEdgeY;
  if (hazeEdgeY) {
    const zCut = f * Hs / Math.max(8, yh - hazeEdgeY);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (!L.idx[i]) continue;
      if (m.Z[i] > zCut * (1 + (vnoise(x * 0.06, 3, 95) - 0.5) * 0.12) || y > hazeEdgeY + 20) L.idx[i] = 0;
    }
  }
  const keep = new Set([S.river, S.rim, S.levee, S.tree, S.funnelRim, S.wall, S.roof]);
  L.despeckle(v => !keep.has(v >> 8));
  const proj = (X, Z) => [cx + f * X / Z, yh - f * height(X, Z) / Z];
  const seen = (X, Z) => {
    const [x, y] = proj(X, Z), xi = Math.round(x), yi = Math.round(y);
    if (yi < 0 || yi >= h || xi < 0 || xi >= w) return null;
    const i = yi * w + xi;
    if (!m.mask[i] || !L.idx[i] || Math.abs(m.Z[i] - Z) > Z * 0.08) return null;
    return [xi, yi];
  };
  const lights = [];
  // villages: houses hanging from the town ground, roofs pointing down at us, windows lit
  for (const t of towns) {
    if (t.Z > 50) continue;
    const n = Math.round(t.r * t.r * 5 + 4);
    const sz = clamp(Math.round(f * 0.32 / t.Z), 2, 4);
    for (let k = 0; k < n; k++) {
      const a = R() * Math.PI * 2, d = Math.sqrt(R()) * t.r * 0.9;
      const p = seen(t.X + Math.cos(a) * d, t.Z + Math.sin(a) * d * 0.8);
      if (!p) continue;
      house(L, p[0], p[1] + 1, sz + (R() < 0.3 ? 1 : 0), hazeOf(t.Z), lights, t.Z, R);
    }
  }
  if (o.pagoda) {
    const p = seen(o.pagoda.X, o.pagoda.Z);
    if (p) pagoda(L, p[0], p[1] + 1, hazeOf(o.pagoda.Z), lights, o.pagoda.Z);
  }
  // lamps: a few streets in each town, scattered farms
  const put = (X, Z, b) => { const p = seen(X, Z); if (p) lights.push({ x: p[0], y: p[1], Z, ph: R(), b }); };
  for (const t of towns) {
    for (let s = 0; s < 3; s++) {
      const a = R() * Math.PI, len = t.r * (0.8 + R() * 0.8), ox = (R() - 0.5) * t.r * 0.6, oz = (R() - 0.5) * t.r * 0.6;
      for (let u = -len / 2; u < len / 2; u += 0.24) put(t.X + ox + Math.cos(a) * u, t.Z + oz + Math.sin(a) * u, 0.5 + R() * 0.3);
    }
  }
  for (let k = 0; k < 30; k++) put((R() - 0.5) * 70, 30 + R() * 40, 0.3 + R() * 0.3);
  // points along the rivers where they can be seen (for the glints that run up them)
  const flow = [];
  rivers.forEach((pts, ri) => {
    let u = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1], len = Math.hypot(bx - ax, bz - az);
      for (let d = 0; d < len; d += 0.3) {
        const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
        const [x, y] = proj(X, Z), xi = Math.round(x), yi = Math.round(y);
        if (yi >= 0 && yi < h && xi >= 0 && xi < w && L.idx[yi * w + xi] && (L.idx[yi * w + xi] >> 8) === S.river) flow.push({ x: xi, y: yi, u: u + d, ri, Z });
      }
      u += len;
    }
  });
  return { layer: L, lights, flow, proj, depth, height, rivers, mask: m.mask, Z: m.Z };
}

// a house hanging from the ground at (x, y): its walls, then its roof pointing down; a lit window
function house(L, x, y, s, hz, lights, Z, R) {
  const { w, h, idx } = L;
  const set = (xx, yy, v) => { if (xx >= 0 && yy >= 0 && xx < w && yy < h) idx[yy * w + xx] = v; };
  const hw = Math.max(1, Math.round(s * 0.6));
  for (let k = 0; k < hw; k++) for (let q = 0; q < s; q++) set(x - (s >> 1) + q, y + k, I(S.wall, q === s - 1 ? 2 : 4, 3, hz));
  const rh = Math.max(1, Math.ceil(s / 2));
  for (let k = 0; k < rh; k++) {
    const half = (s >> 1) + 1 - k;
    for (let q = -half; q <= half - (s % 2 ? 0 : 1); q++) set(x + q, y + hw + k, I(S.roof, k === rh - 1 ? 4 : 2, 3, hz));
  }
  if (R() < 0.75) lights.push({ x: x - (s >> 1) + Math.floor(R() * s), y: y + Math.min(hw - 1, 1), Z, ph: R(), b: 0.75, win: true });
}

// a five-storey pagoda hanging from the ground at (x, y): tiers shrinking downward, eaves flaring
// with their tips turned "up" toward its own ground, and the spire with its rings pointing at us
function pagoda(L, x, y, hz, lights, Z) {
  const { w, h, idx } = L;
  const set = (xx, yy, v) => { if (xx >= 0 && yy >= 0 && xx < w && yy < h) idx[yy * w + xx] = v; };
  let yy = y;
  for (let q = -3; q <= 3; q++) set(x + q, yy, I(S.wall, 2, 3, hz));      // the base on its platform
  yy++;
  for (let tier = 0; tier < 5; tier++) {
    const body = tier < 2 ? 2 : 1, eave = tier < 2 ? 4 : tier < 4 ? 3 : 2;
    for (let k = 0; k < 2; k++) for (let q = -body; q <= body; q++) set(x + q, yy + k, I(S.wall, q > 0 ? 2 : 4, 3, hz));
    if (tier < 4) lights.push({ x, y: yy, Z, ph: tier * 0.21, b: 0.85, win: true });
    yy += 2;
    for (let q = -eave; q <= eave; q++) set(x + q, yy, I(S.roof, 2, 3, hz));
    set(x - eave, yy - 1, I(S.roof, 4, 3, hz)); set(x + eave, yy - 1, I(S.roof, 4, 3, hz)); // the tips turned toward its ground
    yy += 1;
  }
  // the spire (相輪) with its rings
  for (let k = 0; k < 6; k++) {
    set(x, yy + k, I(S.roof, 4, 3, hz));
    if (k === 1 || k === 3) { set(x - 1, yy + k, I(S.roof, 4, 3, hz)); set(x + 1, yy + k, I(S.roof, 4, 3, hz)); }
  }
  set(x, yy + 6, I(S.rim, 6, 3, hz));
}

function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]); return [v[0] / l, v[1] / l, v[2] / l]; }

// rivers: from the gate's flanks up and away into the far land, in slow smooth meanders (they flow
// "up", away)
function makeRivers(R, Fn) {
  const out = [];
  const starts = [[Fn.X + Fn.R * 0.3, Fn.Z + Fn.R * 0.95, 0.42], [Fn.X - Fn.R * 0.9, Fn.Z + Fn.R * 0.5, 0.66], [Fn.X + Fn.R * 1.0, Fn.Z + Fn.R * 0.4, 0.3]];
  for (const [sx, sz, a0] of starts) {
    let X = sx, Z = sz;
    const p1 = R() * 6.28, p2 = R() * 6.28, f1 = 0.16 + R() * 0.06, f2 = 0.43 + R() * 0.1;
    const pts = [[X, Z]];
    for (let i = 0; i < 260; i++) {
      const a = Math.PI * (a0 + 0.17 * Math.sin(i * f1 + p1) + 0.07 * Math.sin(i * f2 + p2));
      X += Math.cos(a) * 0.4; Z += Math.sin(a) * 0.4;
      pts.push([X, Z]);
      if (Z > 110) break;
    }
    out.push(pts);
  }
  return out;
}

// distance to a river polyline; segments are binned by Z on first use
function distRiver(pts, X, Z) {
  let bins = pts.bins;
  if (!bins) {
    bins = pts.bins = new Map();
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
      for (let k = Math.floor(Math.min(az, bz) - 1); k <= Math.floor(Math.max(az, bz) + 1); k++) {
        if (!bins.has(k)) bins.set(k, []);
        bins.get(k).push(ax, az, bx - ax, bz - az);
      }
    }
  }
  const list = bins.get(Math.floor(Z));
  if (!list) return 1e9;
  let best = 1e9;
  for (let o = 0; o < list.length; o += 4) {
    const ax = list[o], az = list[o + 1], dx = list[o + 2], dz = list[o + 3];
    if (X < Math.min(ax, ax + dx) - 1 || X > Math.max(ax, ax + dx) + 1) continue;
    const t = clamp(((X - ax) * dx + (Z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    const d = Math.hypot(X - ax - dx * t, Z - az - dz * t);
    if (d < best) best = d;
  }
  return best;
}

// colours (night): a land at night seen from below: the ground dark, its rivers silver, its lit edges
// and terraces catching the glow from below, its lamps (drawn separately) bright; blue, a touch of
// teal. Three tones per material (by the sun bits); haze in flat steps toward its far edge.
const BASE = {
  [S.land]: [[26, 33, 56], [31, 39, 62], [36, 45, 68]],
  [S.forest]: [[15, 21, 39], [20, 28, 48], [27, 37, 58]],
  [S.tree]: [[12, 17, 33], [17, 24, 42], [24, 33, 52]],
  [S.rock]: [[30, 37, 60], [40, 48, 72], [50, 60, 84]],
  [S.field]: [[32, 41, 64], [42, 53, 76], [54, 66, 88]],
  [S.paddy]: [[46, 62, 86], [60, 80, 102], [78, 100, 120]],
  [S.levee]: [[62, 82, 104], [76, 98, 118], [92, 116, 134]],
  [S.town]: [[36, 42, 64], [42, 49, 70], [48, 56, 76]],
  [S.wall]: [[52, 62, 86], [70, 82, 104], [88, 100, 120]],
  [S.roof]: [[14, 19, 35], [22, 29, 48], [34, 44, 64]],
  [S.bank]: [[34, 44, 66], [40, 52, 74], [46, 60, 82]],
  [S.river]: [[128, 152, 176], [152, 178, 200], [180, 206, 224]],
  [S.rim]: [[74, 102, 120], [92, 124, 140], [110, 144, 156]],
  [S.funnel]: [[22, 31, 54], [30, 42, 66], [40, 54, 78]],
  [S.funnelRim]: [[56, 80, 100], [68, 96, 114], [82, 112, 128]],
  [S.mouth]: [[104, 146, 152], [124, 168, 170], [146, 190, 188]],
};
const HAZE_K = [0, 0.18, 0.42, 0.66, 0.84];
export function skyShorePalette(hazeCol) {
  return i => {
    const m = i >> 8, s = (i >> 5) & 7, hz = i & 7;
    const b = BASE[m];
    if (!b) return 0;
    let c = s >= 6 ? b[2] : s >= 4 ? b[1] : b[0];
    c = mix3(c, hazeCol, HAZE_K[Math.min(4, hz)] * (m === S.river || m === S.rim ? 0.6 : 1));
    return pack(c);
  };
}
