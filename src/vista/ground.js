// The ground seen south from the great camphor on 九十九折峠: our own slope with the old road's
// switchbacks, the folds of the range stepping down to the plain on both sides, the plain
// (paddies, a river, roads, hamlets in their groves, the headman's compound, a market town), low
// hills at its far side and two ranges beyond. Units: camera height above the plain = 1 (~500 m);
// the camera sits in the crown of the tree on the pass, the pass itself at 0.94.

import { clamp, smooth, rng, hash2, vnoise, fbm, ridged, bayer, IndexLayer, I, run } from './util.js';
import { marchGen, sunShadows } from './terrain.js';
import { waterBand } from './tod.js';

export const G = {
  riceA: 1, riceB: 2, riceC: 3, crop: 4, fallow: 5, levee: 6, road: 7, paddy: 8, river: 9, bank: 10,
  forest: 11, cedar: 12, rock: 13, grove: 14, townGround: 15, roof: 16, thatch: 17, wall: 18, wood: 19,
  farForest: 20, path: 21, meadow: 22, pond: 23, roofLit: 24, kura: 25, farRock: 26, hillForest: 27,
};
export const GROUND_MATS = [];
GROUND_MATS[G.riceA] = { albedo: [0.34, 0.44, 0.19] };
GROUND_MATS[G.riceB] = { albedo: [0.4, 0.47, 0.2] };
GROUND_MATS[G.riceC] = { albedo: [0.3, 0.39, 0.18] };
GROUND_MATS[G.crop] = { albedo: [0.43, 0.42, 0.22] };
GROUND_MATS[G.fallow] = { albedo: [0.47, 0.4, 0.27] };
GROUND_MATS[G.levee] = { albedo: [0.45, 0.45, 0.26] };
GROUND_MATS[G.road] = { albedo: [0.58, 0.51, 0.39] };
GROUND_MATS[G.paddy] = { albedo: [0.2, 0.26, 0.2], water: true, refl: 0.6 };
GROUND_MATS[G.river] = { albedo: [0.22, 0.28, 0.3], water: true, refl: 0.82 };
GROUND_MATS[G.pond] = { albedo: [0.18, 0.24, 0.22], water: true, refl: 0.72 };
GROUND_MATS[G.bank] = { albedo: [0.46, 0.46, 0.3] };
GROUND_MATS[G.forest] = { albedo: [0.25, 0.33, 0.15] };
GROUND_MATS[G.cedar] = { albedo: [0.16, 0.23, 0.13] };
GROUND_MATS[G.rock] = { albedo: [0.36, 0.35, 0.32] };
GROUND_MATS[G.grove] = { albedo: [0.18, 0.25, 0.12] };
GROUND_MATS[G.townGround] = { albedo: [0.42, 0.38, 0.32] };
GROUND_MATS[G.roof] = { albedo: [0.27, 0.28, 0.32] };
GROUND_MATS[G.roofLit] = { albedo: [0.46, 0.46, 0.48], gloss: 0.3 };
GROUND_MATS[G.thatch] = { albedo: [0.48, 0.4, 0.27] };
GROUND_MATS[G.wall] = { albedo: [0.76, 0.72, 0.64] };
GROUND_MATS[G.kura] = { albedo: [0.9, 0.87, 0.8] };
GROUND_MATS[G.wood] = { albedo: [0.3, 0.24, 0.18] };
GROUND_MATS[G.farForest] = { albedo: [0.24, 0.3, 0.19] };
GROUND_MATS[G.hillForest] = { albedo: [0.22, 0.3, 0.16] };
GROUND_MATS[G.farRock] = { albedo: [0.42, 0.4, 0.38] };
GROUND_MATS[G.path] = { albedo: [0.6, 0.52, 0.4] };
GROUND_MATS[G.meadow] = { albedo: [0.5, 0.48, 0.27] };

// ---------------------------------------------------------------- the map of the plain (X, Z)

export const RIVER = [[-7.4, 6.4], [-5.2, 7.8], [-3.2, 9.4], [-1.7, 11.4], [-0.6, 13.8], [0.5, 16.2], [0.3, 19.0], [-0.9, 21.4], [-1.7, 24.2], [-0.8, 27.6], [1.5, 31.5], [4.4, 37.5], [8.2, 46], [14, 62], [24, 92]];
export const ROADS = [
  { pts: [[0.05, 5.5], [0.3, 7.4], [0.86, 9.1], [0.55, 11.8], [-0.1, 15.2], [-0.55, 18.6], [-0.95, 21.4]], lanterns: 0.15, main: true },
  { pts: [[-10, 13.6], [-6, 12.9], [-3.2, 12.1], [-0.6, 12.3], [0.55, 11.8], [3.4, 12.6], [6.5, 13.6], [11, 15.2]], lanterns: 0.32 },
  { pts: [[-0.95, 21.4], [0.8, 24.6], [2.6, 28.6], [4.2, 33.5], [5.6, 39]], lanterns: 0.5 },
  { pts: [[-0.95, 21.4], [-3.4, 23.2], [-6.5, 25.8], [-10, 28.5]], lanterns: 0 },
];
export const HEADMAN = { X: 1.14, Z: 9.5 };
export const TOWN = { X: -1.3, Z: 22.6, r: 1.7 };
export const HAMLETS = [
  { X: 2.9, Z: 12.4, r: 0.42, n: 6 }, { X: -2.7, Z: 10.6, r: 0.4, n: 5 }, { X: 4.7, Z: 17.4, r: 0.55, n: 7 },
  { X: -4.4, Z: 16.0, r: 0.55, n: 6 }, { X: 2.2, Z: 21.0, r: 0.5, n: 5 }, { X: -5.8, Z: 22.6, r: 0.7, n: 6 },
  { X: 6.8, Z: 26, r: 0.7, n: 6 }, { X: 1.5, Z: 30.5, r: 0.7, n: 7 }, { X: -3.8, Z: 31.5, r: 0.8, n: 6 },
  { X: 5.2, Z: 36, r: 0.9, n: 5 }, { X: -1.6, Z: 39, r: 0.9, n: 5 }, { X: -7.8, Z: 34, r: 1, n: 5 },
  { X: 9.8, Z: 21.5, r: 0.7, n: 5 }, { X: -8.8, Z: 18.6, r: 0.6, n: 5 }, { X: -1.2, Z: 7.6, r: 0.3, n: 3 },
];
export const WOODS = [{ X: -0.3, Z: 17.2, r: 0.42 }, { X: 3.7, Z: 24.4, r: 0.5 }, { X: -3.3, Z: 27.4, r: 0.6 }, { X: 1.9, Z: 14.6, r: 0.3 }];
// the old road's switchbacks down our slope (九十九折)
export const SWITCHBACKS = (() => {
  const pts = [];
  let side = 1;
  for (let Z = 0.5; Z < 5.2; Z += 0.55) { pts.push([side * (0.16 + Z * 0.04), Z]); side = -side; }
  pts.push([0.05, 5.5]);
  return pts;
})();

// fast polyline distance: segments as flat arrays with boxes; result in POLY.d / POLY.u
export const POLY = { d: 0, u: 0 };
export function polyline(pts, pad) {
  const n = pts.length - 1, S = new Float64Array(n * 8);
  for (let i = 0; i < n; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
    S.set([ax, az, bx - ax, bz - az, Math.min(ax, bx) - pad, Math.max(ax, bx) + pad, Math.min(az, bz) - pad, Math.max(az, bz) + pad], i * 8);
  }
  return { S, n, pts };
}
export function distPoly(P, X, Z) {
  const S = P.S;
  let best = 1e9, bu = 0;
  for (let i = 0, o = 0; i < P.n; i++, o += 8) {
    if (X < S[o + 4] || X > S[o + 5] || Z < S[o + 6] || Z > S[o + 7]) continue;
    const ax = S[o], az = S[o + 1], dx = S[o + 2], dz = S[o + 3];
    const t = clamp(((X - ax) * dx + (Z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    const ex = X - ax - dx * t, ez = Z - az - dz * t, d = ex * ex + ez * ez;
    if (d < best) { best = d; bu = i + t; }
  }
  POLY.d = Math.sqrt(best); POLY.u = bu;
  return POLY.d;
}
const RIVER_P = polyline(RIVER, 0.3);
const ROADS_P = ROADS.map(r => polyline(r.pts, 0.06));
const SWITCH_P = polyline(SWITCHBACKS, 0.06);

// hamlets: houses and the clumps of trees around them (屋敷林), placed once
export function hamletLayout(seed) {
  const R = rng(seed), out = [];
  for (const h of HAMLETS) {
    const houses = [], clumps = [];
    for (let i = 0; i < h.n; i++) {
      const a = R() * Math.PI * 2, d = Math.sqrt(R()) * h.r * 0.75;
      houses.push({ X: h.X + Math.cos(a) * d, Z: h.Z + Math.sin(a) * d * 0.8, big: R() < 0.25, thatch: R() < 0.45, ph: R() });
    }
    const nc = 3 + Math.round(h.r * 7);
    for (let i = 0; i < nc; i++) {
      const a = R() * Math.PI * 2, d = h.r * (0.55 + R() * 0.55);
      clumps.push([h.X + Math.cos(a) * d, h.Z + Math.sin(a) * d * 0.7, 0.05 + R() * 0.08, 0.03 + R() * 0.025]);
    }
    out.push({ ...h, houses, clumps });
  }
  return out;
}

// ---------------------------------------------------------------- height

// Folds of the range, designed on screen (x from the view axis, y from the horizon, both in px at
// f = 360) and lifted into the world: each fold is a ridge from A to B, tapering into the plain.
const FOLD_SPECS = [
  // [xA, yA, zA, xB, yB, zB, width0, widthK, seed]
  [-262, 30, 2.6, -136, 56, 4.8, 0.3, 0.1, 1],     // L1 near
  [-262, 2, 4.0, -104, 31, 9.0, 0.36, 0.12, 2],    // L2
  [-262, -24, 7.0, -188, 7, 13.0, 0.5, 0.14, 3],   // L3 outer, standing above L2
  [262, 26, 2.6, 124, 57, 5.0, 0.3, 0.1, 4],       // R1 near
  [262, -8, 4.4, 128, 27, 9.5, 0.36, 0.12, 5],     // R2
  [262, -32, 8.0, 204, 4, 14.0, 0.5, 0.14, 6],     // R3
];
const F360 = 360;
export const FOLDS = FOLD_SPECS.map(([xa, ya, za, xb, yb, zb, w0, wk, s]) => ({
  XA: xa * za / F360, ZA: za, HA: 1 - ya * za / F360,
  XB: xb * zb / F360, ZB: zb, HB: 1 - yb * zb / F360, w0, wk, s, side: Math.sign(xa),
}));

function foldH(F, X, Z) {
  if (Z < F.ZA - 3.5 || Z > F.ZB + 2.6) return 0;
  // position along the ridge (extrapolated toward the camera, tapering past B)
  const u = (Z - F.ZA) / (F.ZB - F.ZA);
  const xr = F.XA + (F.XB - F.XA) * u;
  let H = u <= 1 ? F.HA + (F.HB - F.HA) * u : F.HB * Math.max(0, 1 - (Z - F.ZB) / 2.6);
  if (u < 0) H = F.HA + (F.HA - F.HB) * (-u) * 0.35;
  const w = F.w0 + F.wk * Z;
  const d = Math.abs(X - xr) / w;
  if (d >= 1.6) return 0;
  const n = ridged(Z * 1.1 + F.s * 7, X * 1.1, 2, F.s);
  const prof = d < 1 ? Math.pow(1 - d * d, 0.7) : 0;
  // the outer side keeps some height (the massif behind the fold)
  const outer = (X - xr) * F.side > 0 ? 0.55 * clamp(1 - (d - 1) / 0.6, 0, 1) * (d >= 1 ? 1 : 0) : 0;
  return H * Math.max(prof, outer) * (0.88 + 0.24 * n);
}

function ourSlope(X, Z) {
  const foot = 5.6 + 0.4 * Math.sin(X * 0.8 + 1);
  if (Z >= foot) return 0;
  const p = 1 - Z / foot;
  let t = 0.94 * Math.pow(p, 1.4);
  t *= 0.9 + 0.2 * ridged(X * 1.6 + Z * 0.12, Z * 0.32, 2, 21);   // gullies running down the slope
  return t + 0.05 * X * X * p;
}

// crowns of trees: a jittered grid of domes (cedar zones pointed)
function crowns(X, Z, cell, amp, cedarZone) {
  const ci = Math.floor(X / cell), cj = Math.floor(Z / cell);
  let best = 0;
  for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    const a = ci + i, b = cj + j;
    const px = (a + 0.15 + hash2(a, b, 5) * 0.7) * cell, pz = (b + 0.15 + hash2(a, b, 6) * 0.7) * cell;
    const r = cell * (0.6 + hash2(a, b, 7) * 0.3), dx = X - px, dz = Z - pz;
    const d2 = (dx * dx + dz * dz) / (r * r);
    if (d2 >= 1) continue;
    const v = cedarZone ? (1 - Math.sqrt(d2)) * 1.3 : Math.sqrt(1 - d2);
    if (v > best) best = v;
  }
  return best * amp;
}

export function makeHeight(hamlets) {
  const bumps = [];
  for (const h of hamlets) for (const c of h.clumps) bumps.push(c);
  for (const w of WOODS) for (let i = 0; i < 5; i++) bumps.push([w.X + Math.cos(i * 1.3) * w.r * 0.5, w.Z + Math.sin(i * 1.3) * w.r * 0.4, w.r * 0.5, 0.05]);
  bumps.push([HEADMAN.X - 0.05, HEADMAN.Z + 0.16, 0.14, 0.045], [HEADMAN.X + 0.2, HEADMAN.Z + 0.12, 0.12, 0.04], [HEADMAN.X - 0.22, HEADMAN.Z + 0.05, 0.09, 0.035]);
  // bucket the bumps by Z for speed
  const bz = new Map();
  for (const b of bumps) { const k = Math.floor(b[1]); for (const kk of [k - 1, k, k + 1]) { if (!bz.has(kk)) bz.set(kk, []); bz.get(kk).push(b); } }
  const base = (X, Z) => {
    let t = ourSlope(X, Z);
    for (const F of FOLDS) { const v = foldH(F, X, Z); if (v > t) t = v; }
    if (Z > 24) {
      // low hills along the far side of the plain (in and out of the horizon)
      const m1 = smooth(28, 36, Z) * (1 - smooth(52, 62, Z));
      if (m1 > 0) { const n = fbm(X * 0.09 + 3, Z * 0.05, 3, 31); t = Math.max(t, m1 * smooth(0.42, 0.75, n) * (0.5 + 0.8 * n)); }
      // the near range, then the far range
      const m2 = smooth(64, 76, Z) * (1 - smooth(118, 130, Z));
      if (m2 > 0) t = Math.max(t, m2 * (0.6 + 4.6 * ridged(X * 0.04 + 7, Z * 0.035, 4, 41)));
      const m3 = smooth(150, 170, Z);
      if (m3 > 0) t = Math.max(t, m3 * (2.5 + 9.5 * ridged(X * 0.022 + 2, Z * 0.02, 4, 43)));
    }
    return t;
  };
  const height = (X, Z) => {
    let t = base(X, Z);
    if (t > 0.012 && Z < 6.5) { // forest crowns where they are big enough to see (farther: shading texture)
      const cedar = vnoise(X * 0.8, Z * 0.6, 51) > 0.56;
      t += crowns(X, Z, 0.045, 0.024, cedar) * smooth(6.5, 3.5, Z);
    }
    if (Z > 6 && Z < 45) {
      const list = bz.get(Math.floor(Z));
      if (list) for (let k = 0; k < list.length; k++) {
        const b = list[k], dx = X - b[0], dz = Z - b[1], d2 = (dx * dx + dz * dz) / (b[2] * b[2]);
        if (d2 < 1) { const v = b[3] * Math.sqrt(1 - d2); if (v > t) t = v; }
      }
    }
    return t;
  };
  height.base = base;
  return height;
}

// ---------------------------------------------------------------- land use on the plain

export function landuse(X, Z, t) {
  const dr = distPoly(RIVER_P, X, Z);
  const rw = 0.075 + 0.015 * Math.sin(POLY.u * 2.3);
  if (dr < rw) return G.river;
  if (dr < rw + 0.04) return G.bank;
  for (let k = 0; k < ROADS_P.length; k++) if (distPoly(ROADS_P[k], X, Z) < (k === 0 ? 0.022 : 0.016)) return G.road;
  const tx = X - TOWN.X, tz = (Z - TOWN.Z) * 0.8;
  if (tx * tx + tz * tz < TOWN.r * TOWN.r) return G.townGround;
  if (t > 0.012) return G.grove;
  if (Z > 7 && vnoise(X * 0.55 + 9, Z * 0.55, 71) > 0.85) return G.pond;
  // parcels in zones of their own orientation (no single grid across the plain)
  const th = (vnoise(X * 0.07 + 5, Z * 0.07, 61) - 0.5) * 0.9;
  const c = Math.cos(th), s = Math.sin(th);
  const u = X * c - Z * s * 0.6, v = X * s + Z * c;
  const su = 0.36 + 0.1 * vnoise(X * 0.2, Z * 0.2, 62), sv = 0.22;
  const iu = Math.floor(u / su), iv = Math.floor(v / sv), fu = u / su - iu, fv = v / sv - iv;
  const edge = Math.min(Math.min(fu, 1 - fu) * su, Math.min(fv, 1 - fv) * sv);
  if (edge < 0.013 + Z * 0.0004) return G.levee;
  const h = hash2(iu, iv, 63);
  if (h < 0.24) return G.paddy;
  if (h < 0.5) return G.riceA;
  if (h < 0.68) return G.riceB;
  if (h < 0.82) return G.riceC;
  if (h < 0.94) return G.crop;
  return G.fallow;
}

// ---------------------------------------------------------------- render the ground to an index layer

export function buildGround(o) { return run(buildGroundGen(o)); }

export function* buildGroundGen({ w, h, cx, yh, f, S, sun, seed }) {
  const hamlets = hamletLayout(seed);
  const height = makeHeight(hamlets);
  const t0 = performance.now();
  const gapsFor = dir => (Math.abs(dir) < 0.17 ? [[11.6, 26]] : null);
  const m = yield* marchGen({ w, h, cx, yh, f, camY: 1, z0: 0.22, z1: 280, height, k: 0.013, kFar: 0.03, zFar: 26, gapsFor });
  const tMarch = performance.now() - t0;
  yield;
  const shadow = sunShadows(height, { xa: -16, xb: 16, za: 0.3, zb: 70, nx: 480, nz: 180, slope: sun.slope, soft: 0.05 });
  yield;
  const L = new IndexLayer(w, h);
  const [slx, sly, slz] = sun.dir;
  for (let y = 0; y < h; y++) {
   if ((y & 15) === 15) yield;
   for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!m.mask[i]) continue;
    const X = m.X[i], Z = m.Z[i];
    const t = height(X, Z);
    let nx = 0, ny = 1, nz = 0;
    if (t > 0.002) {
      const e = Math.max(0.006, Z * 0.0045);
      const hx = height(X + e, Z) - t, hz = height(X, Z + e) - t;
      const l = Math.hypot(hx, e, hz); nx = -hx / l; ny = e / l; nz = -hz / l;
    }
    const lam = Math.max(0, nx * slx + ny * sly + nz * slz);
    const sh = shadow(X, Z);
    let mat;
    const plain = Z > 4.5 && Z < 60 && (t < 0.012 || (Z > 6 && t < 0.07 && ny > 0.3));
    if (plain) {
      if (Z > 9) { // supersample in depth: a far row covers many parcels
        const dz = Z * Z / f * 0.5;
        const a = landuse(X, Z - dz * 0.33, height(X, Z - dz * 0.33)), b = landuse(X, Z, t), c = landuse(X, Z + dz * 0.33, height(X, Z + dz * 0.33));
        mat = a === c ? a : b;
      } else mat = landuse(X, Z, t);
    } else if (Z > 24) {
      mat = Z > 60 ? (ny < 0.55 && t > 3 ? G.farRock : G.farForest) : G.hillForest;
    } else {
      const cedar = vnoise(X * 0.8, Z * 0.6, 51) > 0.56;
      mat = cedar ? G.cedar : G.forest;
      if (ny < 0.4 && vnoise(X * 3, Z * 3, 52) > 0.35) mat = G.rock;
      if (Z < 5.6 && Math.abs(X) < 0.8) {
        if (distPoly(SWITCH_P, X, Z) < 0.018 && vnoise(X * 12, Z * 12, 77) > 0.38) mat = G.path;
      }
    }
    let sun8, sky4;
    let tex = 0;
    if ((mat === G.forest || mat === G.cedar || mat === G.hillForest) && Z > 3.5) {
      // tree crowns too small for the geometry: a lit cap and a shaded side per crown, cells ~2-3 px
      const cs = 0.06 * Math.max(1, Z / 6), u = X / cs, v = (Z + t * 4) / (cs * 1.6);
      const cu = Math.floor(u), cv = Math.floor(v), fu = u - cu - 0.5, fv = v - cv - 0.5;
      const hh = hash2(cu, cv, 333);
      tex = (fu + fv * 0.6 > 0.15 ? 1 : fu + fv * 0.6 < -0.32 ? -1 : 0) + (hh < 0.12 ? -1 : 0);
    }
    if (GROUND_MATS[mat].water) {
      sun8 = waterBand(y - yh, S);
      sky4 = sh > 0.5 ? 3 : 2;
    } else {
      const direct = Math.pow(lam, 0.75) * sh;
      sun8 = clamp(Math.round(direct * 7) + tex, 0, 7);
      sky4 = clamp(Math.round((ny - 0.45) / 0.55 * 3), 0, 3);
    }
    const hz = 1 - Math.exp(-Z / 62);
    const haze = clamp(Math.floor(hz * 8 + (plain ? (bayer(x, y) - 0.5) * 0.7 : 0)), 0, 7);
    L.idx[i] = I(mat, sun8, sky4, haze);
   }
  }
  yield;
  L.despeckle(() => true);
  return { layer: L, X: m.X, Z: m.Z, mask: m.mask, height, hamlets, ms: { march: Math.round(tMarch), total: Math.round(performance.now() - t0) } };
}
