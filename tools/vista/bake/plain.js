// The plain south of the pass for the treetop vista, as the 3D lookout has it (G5R3-10): one land for
// both views. The 3D lookout's land is the source (tools/world3d/w3terrain/vista.py, written to
// godot/world3d/terrain/saddle/: vista.json and the maps vista_far.png (32 m), vista_mid.png (1 m),
// vista_plain.png (8 m: distance to the river, the roads and the railway, the villages' density)):
// the river out of the western canyon, the railway on its long red viaduct, the town where the two
// meet, the villages and their roads, the old road down the pass, the ring of mountains. The bake
// (tools/vista/bake.mjs) decodes those files and hands them to setW3() before the south bake.
//
// The prologue looks due south from the camphor's crown (30 m over the saddle, 380 m over the plain);
// the 3D lookout (vista_s) due south from the rock 50 m away. Mapping into the prologue's units
// (camera height over the plain = 1), x east / z south / y up in metres, the camphor at x = z = 0:
//   X = -x / U, Z = z / U, with U = 182 m: every place keeps its bearing and its order in depth, but
//   the plain lies flatter than the 3D view shows it (the tangent of every depression is k = U / 380 =
//   0.48 times the true one), so it keeps the band of the frame the prologue's plain had (approved,
//   G5R2-4) and its "sea of lights";
//   height above the plain r = y + 350 m: h = r / 380 below the eye; above the eye the true elevation
//   times a factor, h = 1 + (r - 380) / U * k: the mountains keep the 3D view's outline and bearings,
//   lowered only as far as it takes to stay clear of the sky shore when it opens (k = 0.52 over every
//   usual view, less only on the sides an ultra-wide view adds; mountainFit).
// The town is the 3D town; the lamps of the Obon night are where the 3D view has its villages, its
// houses and its street lamps by day. Below the pass the lower layer (the 溜池, the terraces, the
// water-wheel farm, the switchbacks) is the 3D mid grid's (midUse). A shot may draw the depression its
// own way (depG; the title, G5R3-23). The far (遠化) leaves the land its own silver-white ghost, the
// more the nearer the town (G5R3-22): ghostPalette / ghostMaps at the end of this file.

import { clamp, lerp, smooth, rng, hash2, vnoise, fbm, bayer, IndexLayer, I } from '../../../src/vista/util.js';
import { marchGen, sunShadows } from '../../../src/vista/terrain.js';
import { waterBand } from '../../../src/vista/tod.js';
import { G as G0, GROUND_MATS as GM0 } from '../../../src/vista/ground.js';

export const U = 182, EYE_REL = 380, Y_PLAIN = -350;
const FLAT = 8;                       // m of the plain's own roll that still counts as level ground

// materials: the JS vista's, and the viaduct's red iron
export const G = { ...G0, iron: 28 };
export const GROUND_MATS = GM0.slice();
GROUND_MATS[G.iron] = { albedo: [0.4, 0.15, 0.11] };

let W3 = null;
/** The 3D lookout's land: { far, mid, plain: { w, h, x0, z0, cell, data (RGBA) }, json }. */
export function setW3(d) { W3 = d; prepare(); }
export function haveW3() { return W3 != null; }

// ---------------------------------------------------------------- the land in metres

let FARH, MIDH, PL;
function u16(map, hmin, hrange) {
  const n = map.w * map.h, out = new Float32Array(n), D = map.data;
  for (let i = 0; i < n; i++) out[i] = hmin + (D[i * 4] * 256 + D[i * 4 + 1]) / 65535 * hrange;
  return out;
}
function bil(A, map, x, z) {
  const fx = (x - map.x0) / map.cell, fz = (z - map.z0) / map.cell;
  if (fx < 0 || fz < 0 || fx >= map.w - 1 || fz >= map.h - 1) return null;
  const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j, o = j * map.w + i;
  return A[o] * (1 - u) * (1 - v) + A[o + 1] * u * (1 - v) + A[o + map.w] * (1 - u) * v + A[o + map.w + 1] * u * v;
}
/** Height of the land (m, the saddle at ~0) at x, z: the 1 m grid near the region, else the 32 m one. */
export function landY(x, z) {
  const m = bil(MIDH, W3.mid, x, z);
  if (m != null) {
    // blend into the far grid over the mid grid's last 64 m (no seam)
    const e = Math.min(x - W3.mid.x0, W3.mid.x0 + (W3.mid.w - 1) * W3.mid.cell - x, z - W3.mid.z0, W3.mid.z0 + (W3.mid.h - 1) * W3.mid.cell - z);
    if (e >= 64) return m;
    const f = bil(FARH, W3.far, x, z);
    return f == null ? m : lerp(f, m, clamp(e / 64, 0, 1));
  }
  const f = bil(FARH, W3.far, x, z);
  // (beyond the 3D far grid, 16 km out, there is no land in the 3D view either: the ring of mountains
  // at its edge closes the horizon; the plain level here never shows over it)
  return f == null ? Y_PLAIN : f;
}
// the plain map's channels at x, z (bilinear): river m, road m, village 0..1, railway m
const PLN = [0, 0, 0, 0];
function plainAt(x, z) {
  const map = W3.plain, fx = (x - map.x0) / map.cell, fz = (z - map.z0) / map.cell;
  if (fx < 0 || fz < 0 || fx >= map.w - 1 || fz >= map.h - 1) { PLN[0] = PLN[1] = PLN[3] = 255; PLN[2] = 0; return PLN; }
  const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j, D = map.data, o = (j * map.w + i) * 4, ow = map.w * 4;
  for (let c = 0; c < 4; c++) PLN[c] = D[o + c] * (1 - u) * (1 - v) + D[o + 4 + c] * u * (1 - v) + D[o + ow + c] * (1 - u) * v + D[o + ow + 4 + c] * u * v;
  PLN[1] *= 0.5; PLN[2] /= 255; PLN[3] *= 0.5;
  return PLN;
}

// ---------------------------------------------------------------- into the prologue's units

// above the eye: the true elevation times a factor. The mountains keep the 3D view's outline (bearings,
// shape); their height is lowered only as far as it takes for the skyline to stay clear of the sky
// shore when it opens (its lowest row is 22 px over the horizon at the 270-row class, which every
// usual window gets: the peaks stay at or under SKY_SHORE_CLEAR px at f = 360). One factor, k0, over
// all the bearings a view up to 533 px wide shows (16:9 and 16:10 windows; |column - 512| <= 267);
// only the sides a wider view adds ramp smoothly to lower factors where their nearer, taller flanks
// need it. Computed in prepare() (mountainFit); 1 where nothing needs lowering.
export const SKY_SHORE_CLEAR = 20;
const MTN_F = 360, MTN_KEEP = 267, MTN_FREE = 315, MTN_R = 24;
let MTN_COL = null, MTN_INFO = { k0: 1 };
function mtnK(t) {
  if (!MTN_COL) return 1;
  const c = Math.min(1023, Math.max(0, 512 + MTN_F * t - 0.5)), i = Math.min(1022, Math.floor(c)), u = c - i;
  return MTN_COL[i] * (1 - u) + MTN_COL[i + 1] * u;
}
const toH = (r, t = 0) => (r <= EYE_REL ? r / EYE_REL : 1 + (r - EYE_REL) / U * mtnK(t));
export const P = (x, z) => [-x / U, z / U];

// Below the eye, the picture's depression: the screen depression is G(t) of the true one (t = tan,
// from the eye), piecewise linear through DEP. The prologue keeps option C's (every depression at 0.48
// of the 3D's: U / EYE_REL); a shot may set its own (the title, G5R3-23: the lower layer below the
// pass drawn taller, above the grass). Only the projection (the march, houses, lamps, the viaduct)
// uses it; the land's relief (land use, light) does not.
const DEP0 = [[0, 0], [10, 10 * U / EYE_REL]];
let DEP = DEP0;
export function depKnots() { return DEP.map(k => k.slice()); }
/** For tools: another mapping (knots after [0, 0]); the railway's projection is redone. */
export function setDepression(knots) { DEP = knots ? [[0, 0], ...knots] : DEP0; if (W3) prepare(); }
export function depG(t) {
  for (let i = 0; i < DEP.length - 1; i++) {
    const [t0, g0] = DEP[i], [t1, g1] = DEP[i + 1];
    if (t <= t1 || i === DEP.length - 2) return g0 + (t - t0) * (g1 - g0) / (t1 - t0);
  }
  return 0;
}
/** relief height h (prologue units: r / EYE_REL below the eye) -> the height that projects to the
 *  picture's depression at Z */
export function warpH(h, Z) {
  if (h >= 1) return h;
  return 1 - Z * depG((1 - h) * EYE_REL / Math.max(1e-6, Z * U));
}
/** prologue height at X, Z (the plain at 0) */
function heightBase(X, Z) {
  const y = landY(-X * U, Z * U);
  return toH(Math.max(0, y - Y_PLAIN - FLAT), Z > 1e-6 ? X / Z : 0);
}

// the places, mapped (filled by prepare())
export let RIVER = [], RAILWAY = [], ROAD = [], VILLAGES = [], HOUSES = [], LAMPS = [], TOWN = null, HEAD = null;

function catmull(pts, n) {
  const out = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    for (let s = 0; s < n; s++) {
      const t = s / n, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map(k => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
    }
  }
  out.push(pts[pts.length - 1].slice());
  return out;
}
// the 3D river's control points (vista.py RIVER): from the canyon's mouth to the far south-east
const RIVER3 = [[-1100, 420], [-1250, 800], [-1150, 1250], [-700, 1650], [-150, 1900], [350, 2350], [520, 3000], [250, 3700],
  [700, 4500], [1500, 5200], [1900, 6400], [1600, 7800], [2400, 9500], [3200, 12500]];

// the old road from the foot of the pass to the town (vista.py old_road: the same control points,
// Catmull-Rom with 12 steps a span), in prologue units
const OLD_ROAD3 = [[24, 600], [60, 900], [-40, 1300], [-150, 1700], [-260, 2160]];
export function oldRoad() { return catmull(OLD_ROAD3, 12).map(([x, z]) => P(x, z)); }

function prepare() {
  const J = W3.json;
  FARH = u16(W3.far, J.far.hmin, J.far.hrange);
  MIDH = u16(W3.mid, J.mid.hmin, J.mid.hrange);
  // the river in prologue units, about every 1.5 units, from the canyon (near) to the far south-east
  const dense = catmull(RIVER3, 24), riv = [];
  let acc = 1e9;
  for (let i = 0; i < dense.length; i++) {
    const [X, Z] = P(dense[i][0], dense[i][1]);
    if (riv.length) acc += Math.hypot(X - riv[riv.length - 1][0], Z - riv[riv.length - 1][1]);
    if (acc >= 1.5 || i === dense.length - 1) { riv.push([+X.toFixed(3), +Z.toFixed(3)]); acc = 0; }
  }
  RIVER = riv;
  RAILWAY = J.railway.map(([x, dk, z, gy]) => { const [X, Z] = P(x, z); return [X, Z, warpH(toH(Math.max(0, dk - Y_PLAIN)), Z), warpH(toH(Math.max(0, gy - Y_PLAIN - FLAT)), Z)]; });
  ROAD = J.road.map(([x, z]) => P(x, z));
  VILLAGES = J.villages.map(([x, z, r, n], i) => { const [X, Z] = P(x, z); return { i, X, Z, r: r / U, n, x, z }; });
  HOUSES = J.plain_houses.map(([x, y, z, rot, w, d, hgt, roof, seed, vi]) => { const [X, Z] = P(x, z); return { X, Z, w, roof, seed, vi }; });
  // the water-wheel farm in the lower layer below the pass (the 3D landmarks' houses): thatched
  for (const [x, , z] of (J.landmarks && J.landmarks.houses) || []) { const [X, Z] = P(x, z); HOUSES.push({ X, Z, w: 10, roof: 0, seed: 0, vi: -1, farm: true }); }
  LAMPS = J.plain_lamps.map(([x, y, z]) => P(x, z));
  TOWN = VILLAGES[0];
  // the headman's compound: the biggest house of the nearest village in front of the pass, right of
  // the view's axis (where the first lamp of the old plan rose, R-8): the 3D village at (-300, 1227)
  const near = VILLAGES.filter(v => v.i !== 0 && v.Z > 4 && v.X > 0.2 && v.X / v.Z < 0.4).sort((a, b) => a.Z - b.Z)[0];
  const hs = HOUSES.filter(h => h.vi === near.i).sort((a, b) => b.w - a.w);
  HEAD = { X: hs[0].X, Z: hs[0].Z, vi: near.i };
  MTN_COL = null;
  mountainFit(SKY_SHORE_CLEAR);
}

/** The skyline at factor 1: per far-canvas column (1024, centre 512, f = 360), the highest point over
 *  the horizon in px. */
export function skyline1(f = MTN_F) {
  const keep = MTN_COL;
  MTN_COL = null;
  const top = new Float64Array(1024);
  for (let c = 0; c < 1024; c++) {
    const t = (c + 0.5 - 512) / f;
    let m = 0;
    for (let Z = 4; Z < 900; Z *= 1.004) {
      const h = heightBase(Z * t, Z);
      if (h > 1) m = Math.max(m, f * (h - 1) / Z);
    }
    top[c] = m;
  }
  MTN_COL = keep;
  return top;
}

/** The factor per column. k0 brings the highest point within MTN_KEEP of the centre to `limit` px.
 *  Outward of MTN_FREE (where the sides still need no more than k0) each side takes the running
 *  minimum of what its columns need, eroded and then averaged over MTN_R columns (so it is smooth and
 *  never above what any column needs); the result never reaches inside MTN_KEEP. */
export function mountainFit(limit, f = MTN_F) {
  const top = skyline1(f);
  let c0 = 0;
  for (let c = 0; c < 1024; c++) if (Math.abs(c + 0.5 - 512) <= MTN_KEEP) c0 = Math.max(c0, top[c]);
  const k0 = c0 > limit ? limit / c0 : 1;
  const need = Array.from(top, v => (v > limit ? Math.min(k0, limit / v) : k0));
  const m = new Float64Array(1024).fill(k0);
  for (let c = 512 + MTN_FREE, run = k0; c < 1024; c++) { run = Math.min(run, need[c]); m[c] = run; }
  for (let c = 511 - MTN_FREE, run = k0; c >= 0; c--) { run = Math.min(run, need[c]); m[c] = run; }
  const at = (A, c) => A[Math.min(1023, Math.max(0, c))];
  const ero = Float64Array.from(m, (_, c) => { let v = Infinity; for (let d = -MTN_R; d <= MTN_R; d++) v = Math.min(v, at(m, c + d)); return v; });
  const col = Float64Array.from(ero, (_, c) => { let v = 0; for (let d = -MTN_R; d <= MTN_R; d++) v += at(ero, c + d); return v / (2 * MTN_R + 1); });
  for (let c = 0; c < 1024; c++) if (Math.abs(c + 0.5 - 512) <= MTN_KEEP) col[c] = k0;
  MTN_COL = col;
  let after = 0;
  for (let c = 0; c < 1024; c++) after = Math.max(after, top[c] * col[c]);
  MTN_INFO = { k0, kMin: Math.min(...col), limit, top0: c0, topAll: Math.max(...top), after, kLeft: col[0], kRight: col[1023] };
  return MTN_INFO;
}
export const mountainInfo = () => ({ ...MTN_INFO });
export const mountainColumns = () => MTN_COL && Array.from(MTN_COL, v => +v.toFixed(4));

// ---------------------------------------------------------------- height with the villages' groves

/** villages' house layout and the clumps of trees round them (屋敷林), as height bumps */
export function makeHeight() {
  const R = rng(5150);
  const bumps = [];
  for (const v of VILLAGES) {
    const nc = 2 + Math.round(Math.sqrt(v.n) * 1.1);
    for (let k = 0; k < nc; k++) {
      const a = R() * Math.PI * 2, d = v.r * (0.5 + R() * 0.7);
      bumps.push([v.X + Math.cos(a) * d, v.Z + Math.sin(a) * d * 0.7, (25 + R() * 30) / U, (14 + R() * 10) / EYE_REL]);
    }
  }
  const bz = new Map();
  for (const b of bumps) { const k = Math.floor(b[1]); for (const kk of [k - 1, k, k + 1]) { if (!bz.has(kk)) bz.set(kk, []); bz.get(kk).push(b); } }
  const base = heightBase;
  const height = (X, Z) => {
    let t = base(X, Z);
    if (t < 0.03 && Z > 4) {
      const list = bz.get(Math.floor(Z));
      if (list) for (let k = 0; k < list.length; k++) {
        const b = list[k], dx = X - b[0], dz = Z - b[1], d2 = (dx * dx + dz * dz) / (b[2] * b[2]);
        if (d2 < 1) { const v = b[3] * Math.sqrt(1 - d2); if (v > t) t = v; }
      }
    }
    return t;
  };
  height.base = base;
  // (the projection's height: the relief drawn at the picture's depression)
  height.warp = (X, Z) => warpH(height(X, Z), Z);
  return height;
}

// ---------------------------------------------------------------- land use

/** what the plain is at X, Z (t: height there) */
export function landuse(X, Z, t) {
  const x = -X * U, z = Z * U;
  const [riv, road, vil] = plainAt(x, z);
  const rw = 26 + 6 * Math.sin(z * 0.002);
  if (riv < rw) return G.river;
  if (riv < rw + 10) return G.bank;
  if (road < 4.5) return G.road;
  if (vil > 0.55 && TOWN && Math.hypot(X - TOWN.X, Z - TOWN.Z) < TOWN.r * 1.25) return G.townGround;
  if (t > 0.012) return G.grove;
  if (vil > 0.35) return vnoise(X * 3, Z * 3, 73) > 0.5 ? G.grove : G.meadow;
  if (Z > 7 && vnoise(X * 0.55 + 9, Z * 0.55, 71) > 0.86) return G.pond;
  // parcels in zones of their own orientation (no single grid across the plain); sizes in metres
  const th = (vnoise(x / 1300 + 5, z / 1300, 61) - 0.5) * 0.9;
  const c = Math.cos(th), s = Math.sin(th);
  const u = x * c - z * s * 0.6, v = x * s + z * c;
  const su = 66 + 18 * vnoise(x / 900, z / 900, 62), sv = 40;
  const iu = Math.floor(u / su), iv = Math.floor(v / sv), fu = u / su - iu, fv = v / sv - iv;
  const edge = Math.min(Math.min(fu, 1 - fu) * su, Math.min(fv, 1 - fv) * sv);
  if (edge < 2.4 + z * 0.0004) return G.levee;
  const h = hash2(iu, iv, 63);
  if (h < 0.24) return G.paddy;
  if (h < 0.5) return G.riceA;
  if (h < 0.68) return G.riceB;
  if (h < 0.82) return G.riceC;
  if (h < 0.94) return G.crop;
  return G.fallow;
}

// forest density of the 3D land (its maps' blue channel) at x, z
function forestAt(x, z) {
  const mid = W3.mid, fx = (x - mid.x0) / mid.cell, fz = (z - mid.z0) / mid.cell;
  if (fx >= 0 && fz >= 0 && fx < mid.w - 1 && fz < mid.h - 1) return mid.data[(Math.floor(fz) * mid.w + Math.floor(fx)) * 4 + 2] / 255;
  const far = W3.far, gx = (x - far.x0) / far.cell, gz = (z - far.z0) / far.cell;
  if (gx >= 0 && gz >= 0 && gx < far.w - 1 && gz < far.h - 1) return far.data[(Math.floor(gz) * far.w + Math.floor(gx)) * 4 + 2] / 255;
  return 0.5;
}

// The lower layer below the pass (G5R3-23: the mid-ground the lookout sees, from the 3D mid grid:
// vista_mat.png R cultivated, G road, B rock, A dry-stone wall; vista_mid.png B forest, A water): the
// 溜池, the terraces flooded for rice (the water holds the sky; bunds along the contours), the old
// road's switchbacks, walls, rock, woods, grass. 0 outside the grid's sample area.
function midUse(x, z) {
  const mid = W3.mid, M = W3.mat;
  if (!M) return 0;
  const fx = (x - mid.x0) / mid.cell, fz = (z - mid.z0) / mid.cell;
  if (fx < 2 || fz < 2 || fx >= mid.w - 3 || fz >= mid.h - 3) return 0;
  const o = (Math.round(fz) * mid.w + Math.round(fx)) * 4;
  const water = mid.data[o + 3] > 127, forest = mid.data[o + 2] / 255;
  const cult = M.data[o] / 255, road = M.data[o + 1] / 255, rock = M.data[o + 2] / 255, wall = M.data[o + 3] / 255;
  if (water) return G.pond;
  if (road > 0.5) return G.path;
  if (wall > 0.5) return G.rock;
  if (cult > 0.5) {
    const y = landY(x, z);
    return ((y / 1.6) % 1 + 1) % 1 < 0.3 ? G.levee : G.paddy;
  }
  if (rock > 0.5) return G.rock;
  if (forest > 0.35) return vnoise(x / 40, z / 40, 51) > 0.56 ? G.cedar : G.forest;
  return G.meadow;
}

// ---------------------------------------------------------------- render the ground

/** The ground as an index layer, marched from the crown (fork of src/vista/ground.js buildGroundGen). */
export function* buildPlainGen({ w, h, cx, yh, f, S, sun, seed }) {
  const height = makeHeight();
  const t0 = performance.now();
  const m = yield* marchGen({ w, h, cx, yh, f, camY: 1, z0: 0.22, z1: 900, height: height.warp, k: 0.008, kFar: 0.02, zFar: 70 });
  yield;
  const shadow = sunShadows(height, { xa: -70, xb: 70, za: 0.3, zb: 160, nx: 900, nz: 260, slope: sun.slope, soft: 0.05 });
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
      const xm = -X * U, zm = Z * U, dist = Math.hypot(xm, zm);
      let mat;
      const plain = t < 0.012 || (t < 0.07 && ny > 0.3 && dist > 1500);
      if (plain && dist > 700) {
        if (Z > 6) {
          // a far row covers a deep strip of the plain: look across all of it, so that the thin
          // things (the river, a road) are never missed and the parcels are not aliased
          const dz = Z * Z / f, ms = [];
          for (let q = 0; q < 5; q++) { const zq = Z + dz * (q / 4 - 0.5); ms.push(landuse(X * zq / Z, zq, height(X * zq / Z, zq))); }
          mat = ms.includes(G.river) ? G.river : ms.includes(G.bank) ? G.bank : ms.includes(G.road) ? G.road : ms[1] === ms[3] ? ms[1] : ms[2];
        } else mat = landuse(X, Z, t);
      } else if (dist > 4200 && t > 0.05) {
        // the ring of mountains: forest below, rock on the steep upper slopes
        mat = ny < 0.6 && t > 1.3 ? G.farRock : dist > 9000 ? G.farForest : G.hillForest;
      } else if (dist > 120 && (mat = midUse(xm, zm))) {
        // the lower layer below the pass, as the 3D has it
      } else {
        const fo = forestAt(xm, zm);
        const cedar = vnoise(X * 0.8, Z * 0.6, 51) > 0.56;
        mat = fo > 0.35 || dist < 700 ? (cedar ? G.cedar : G.forest) : (vnoise(X * 2, Z * 2, 53) > 0.5 ? G.meadow : G.forest);
        if (ny < 0.4 && vnoise(X * 3, Z * 3, 52) > 0.35) mat = G.rock;
        if (dist < 700 && roadDist(X, Z) < 2.6 / U && vnoise(X * 40, Z * 40, 77) > 0.3) mat = G.path;
      }
      let sun8, sky4, tex = 0;
      if ((mat === G.forest || mat === G.cedar || mat === G.hillForest) && dist > 600) {
        // tree crowns too small for the geometry: a lit cap and a shaded side per crown (~2-3 px)
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
  // height: the projection's (for anything placed in the picture: houses, lamps); relief: the land's
  return { layer: L, X: m.X, Z: m.Z, mask: m.mask, height: height.warp, relief: height, ms: { total: Math.round(performance.now() - t0) } };
}

// ---------------------------------------------------------------- houses and their lamps

const LIT = 6, SHD = 2;
function hazeOf(Z) { return clamp(Math.floor((1 - Math.exp(-Z / 62)) * 8), 0, 7); }
function houseSprite(w, kind) {
  const px = [], half = w / 2;
  if (kind === 'kura') {
    const hW = Math.max(2, Math.round(w * 0.9)), rH = Math.max(1, Math.round(w * 0.35));
    for (let y = 0; y < hW; y++) for (let x = 0; x < w; x++) px.push([x - Math.floor(half), -y, G.kura, x >= half ? SHD + 1 : LIT]);
    for (let y = 0; y < rH; y++) for (let x = -1; x <= w; x++) if (x >= y - 1 && x <= w - y) px.push([x - Math.floor(half), -hW - y, G.roof, x >= half ? LIT : SHD]);
    return px;
  }
  const wallH = Math.max(1, Math.round(w * 0.28));
  const roofH = kind === 'thatch' ? Math.max(2, Math.round(w * 0.55)) : Math.max(1, Math.round(w * 0.36));
  const roofMat = kind === 'thatch' ? G.thatch : G.roof;
  for (let y = 0; y < wallH; y++) for (let x = 0; x < w; x++) {
    const m = (x === 0 || x === w - 1) && w > 4 ? G.wood : G.wall;
    px.push([x - Math.floor(half), -y, y === wallH - 1 && w > 3 ? G.wood : m, x >= half ? LIT - 1 : SHD]);
  }
  for (let y = 0; y < roofH; y++) {
    const inset = kind === 'thatch' ? Math.round((y / roofH) ** 1.6 * (half - 0.5)) : Math.round(y * (half / roofH) * 0.85);
    for (let x = -1 + inset; x <= w - inset; x++) px.push([x - Math.floor(half), -wallH - y, roofMat === G.roof && y === roofH - 1 ? G.roofLit : roofMat, x >= half - 0.5 ? LIT : SHD]);
  }
  return px;
}

/**
 * The 3D view's houses on the plain, drawn small and clear (src/vista/buildings.js paintBuildings,
 * fed with the 3D houses); each reports its window, its gate lantern and the fire at its gate (送り火)
 * for the lights. Only one house in a few gets each: the night keeps the density of lights the
 * prologue had. Returns lights [{x, y, X, Z, kind, vi}].
 */
export function paintHouses(L, Xb, Zb, cam, seed) {
  const R = rng(seed + 101), { cx, yh, f, height } = cam, lights = [];
  const sizeAt = (Z, wm, k = 1) => Math.max(2, Math.round(f * (wm / U) / Z * 1.6 * k));
  const list = [];
  for (const ho of HOUSES) {
    if (ho.farm) {
      // (the farm below the pass, near: drawn at its own size, its windows lit, a lantern at the door)
      list.push({ X: ho.X, Z: ho.Z, w: sizeAt(ho.Z, ho.w, 0.62), kind: 'thatch', vi: -1, farm: true, win: true, lantern: true });
      continue;
    }
    if (ho.Z < 3) continue;
    const town = ho.vi === TOWN.i, head = ho.X === HEAD.X && ho.Z === HEAD.Z;
    const kind = head ? 'thatch' : town ? (R() < 0.82 ? 'tile' : 'thatch') : (ho.roof === 0 ? 'thatch' : R() < 0.5 ? 'thatch' : 'tile');
    list.push({ X: ho.X, Z: ho.Z, w: sizeAt(ho.Z, ho.w, head ? 1.6 : 1), kind, vi: ho.vi, head, town,
      win: head || R() < (town ? 0.42 : 0.2), fire: head || R() < (town ? 0.06 : 0.07), lantern: head || R() < (town ? 0.12 : 0.1) });
  }
  // the headman's white store (kura) beside the main house; the town's temple roof
  list.push({ X: HEAD.X - 0.12, Z: HEAD.Z + 0.06, w: sizeAt(HEAD.Z, 9), kind: 'kura', vi: HEAD.vi });
  const tem = HOUSES.filter(h => h.vi === TOWN.i).sort((a, b) => b.w - a.w)[0];
  list.push({ X: tem.X + 0.3, Z: tem.Z + 0.25, w: sizeAt(tem.Z, 22), kind: 'tile', vi: TOWN.i, temple: true, fire: true, win: true });
  list.sort((a, b) => b.Z - a.Z);
  const { w: W, h: H, idx } = L;
  for (const b of list) {
    const x0 = Math.round(cx + f * b.X / b.Z), y0 = Math.round(yh + f * (1 - height(b.X, b.Z)) / b.Z);
    if (x0 < -20 || x0 > W + 20 || y0 < 0 || y0 >= H) continue;
    const gi = y0 * W + clamp(x0, 0, W - 1);
    if (Zb[gi] < b.Z * 0.92) continue;            // hidden behind a nearer slope
    const hz8 = hazeOf(b.Z);
    for (const [dx, dy, mat, sun] of houseSprite(b.w, b.kind)) {
      const x = x0 + dx, y = y0 + dy;
      if (x < 0 || y < 0 || x >= W || y >= H) continue;
      const i = y * W + x;
      if (Zb[i] < b.Z * 0.9) continue;
      idx[i] = I(mat, sun, 3, hz8);
      Xb[i] = b.X; Zb[i] = b.Z;
    }
    const wallY = y0 - 1;
    if (b.win) {
      const nWin = b.temple ? 3 : b.head ? 4 : b.w >= 5 ? 2 : 1;
      for (let k = 0; k < nWin; k++) {
        const dx = Math.round((k + 0.5) / nWin * b.w - b.w / 2);
        lights.push({ x: x0 + dx, y: wallY, X: b.X, Z: b.Z, kind: 'window', far: b.Z > 30, vi: b.vi, head: b.head });
      }
    }
    if (b.lantern) lights.push({ x: x0 + Math.round(b.w / 2) + 1, y: y0 - 1, X: b.X, Z: b.Z, kind: 'lantern', vi: b.vi });
    if (b.fire) lights.push({ x: x0 - Math.round(b.w / 2) - 1, y: y0, X: b.X, Z: b.Z, kind: b.head || b.temple ? 'bonfire' : 'fire', vi: b.vi });
  }
  L.used = null;
  return lights;
}

/** Obon lanterns where the 3D view has its street lamps (the old road lit all the way to the town,
 *  the roads where they come into the villages), one every ~2 px of the frame at most. */
export function plainLanterns(cam, Zb, W, H) {
  const { cx, yh, f, height } = cam, out = [];
  const taken = new Set();
  for (const [X, Z] of LAMPS) {
    if (Z < 3) continue;
    const x = Math.round(cx + f * X / Z), y = Math.round(yh + f * (1 - height(X, Z)) / Z) - 1;
    if (x < 0 || x >= W || y < 0 || y >= H) continue;
    if (Zb[(y + 1) * W + x] < Z * 0.9) continue;
    const key = (x >> 1) + ':' + y;
    if (taken.has(key)) continue;
    taken.add(key);
    // the old road (to the town) is a line of lanterns; elsewhere one lamp in two
    const toTown = TOWN && Math.hypot(X - TOWN.X, Z - TOWN.Z) < 14 && X > -2.5;
    if (!toTown && hash2(x, y, 717) < 0.72) continue;
    out.push({ x, y, X, Z, kind: 'lantern', road: toTown ? 0 : 1 });
  }
  return out;
}

/** The night's lanterns along the roads that the frame shows, appended to lights (prologue and title
 *  share them): the old road's switchbacks down the pass, an Obon lantern every ~40 m; and the old
 *  road on across the plain to the town, where on the night of the 送魂 paper lanterns hang between
 *  its street lamps, one every ~12 m, so that from the crown it is a thread of light winding into the
 *  town (HEAD's procession road was one). ground: { Z, height }; cam: { cx, yh, f }. */
export function roadLanterns(lights, ground, cam, W, H) {
  const { cx, yh, f } = cam;
  const SW = ROAD;
  for (let i = 0, acc = 0; i < SW.length - 1; i++) {
    const [ax, az] = SW[i], [bx, bz] = SW[i + 1], len = Math.hypot(bx - ax, bz - az), step = 40 / U;
    for (let d = acc; d < len; d += step) {
      const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
      const x = Math.round(cx + f * X / Z), y = Math.round(yh + f * (1 - ground.height(X, Z)) / Z) - 1;
      if (x < 0 || x >= W || y < 0 || y >= H) continue;
      if (ground.Z[(y + 1) * W + x] < Z * 0.85) continue;
      lights.push({ x, y, X, Z, kind: 'lantern', path: true });
    }
    acc = (acc - len) % step; if (acc < 0) acc += step;
  }
  const OR = oldRoad(), taken = new Set(lights.map(L => L.x + ':' + L.y));
  for (let i = 0, acc = 0; i < OR.length - 1; i++) {
    const [ax, az] = OR[i], [bx, bz] = OR[i + 1], len = Math.hypot(bx - ax, bz - az), step = 12 / U;
    for (let d = acc; d < len; d += step) {
      const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
      const x = Math.round(cx + f * X / Z), y = Math.round(yh + f * (1 - ground.height(X, Z)) / Z) - 1;
      if (x < 0 || x >= W || y < 0 || y >= H || taken.has(x + ':' + y)) continue;
      if (ground.Z[(y + 1) * W + x] < Z * 0.85) continue;
      taken.add(x + ':' + y);
      lights.push({ x, y, X, Z, kind: 'lantern', path: true });
    }
    acc = (acc - len) % step; if (acc < 0) acc += step;
  }
  return lights;
}

/** Bonfires on the river bank by the town, where the lanterns are set on the water (three); and the
 *  river's points near the town (indices into RIVER), for the floating lanterns. */
export function riverBonfires(ground, cam, W, H) {
  const { cx, yh, f } = cam, near = [], out = [];
  for (let i = 0; i < RIVER.length; i++) if (Math.hypot(RIVER[i][0] - TOWN.X, RIVER[i][1] - TOWN.Z) < 3.4) near.push(i);
  for (const q of [0.15, 0.5, 0.85]) {
    const i = near[Math.min(near.length - 1, Math.floor(q * near.length))];
    const X = RIVER[i][0] + 0.16, Z = RIVER[i][1];
    const x = Math.round(cx + f * X / Z), y = Math.round(yh + f * (1 - warpH(0, Z)) / Z);
    if (x > 0 && x < W && y > 0 && y < H && ground.Z[y * W + x] > Z * 0.9) out.push({ x, y, X, Z, kind: 'bonfire', river: true });
  }
  return { fires: out, near };
}

function roadDist(X, Z) {
  let best = 1e9;
  for (let i = 0; i < ROAD.length - 1; i++) {
    const [ax, az] = ROAD[i], [bx, bz] = ROAD[i + 1], dx = bx - ax, dz = bz - az;
    const t = clamp(((X - ax) * dx + (Z - az) * dz) / (dx * dx + dz * dz || 1), 0, 1);
    const d = Math.hypot(X - ax - dx * t, Z - az - dz * t);
    if (d < best) best = d;
  }
  return best;
}

/** The old road's switchbacks down the pass (the region's road, vista.json "road"), as a polyline. */
export function switchbacks() { return ROAD; }

/**
 * The railway on its viaduct, in red iron, over the ground (drawn in front of what lies behind it,
 * behind what is nearer): the deck a dark line on its piers, every ~22 m a pair of legs to the
 * ground. At night it is a dark shadow across the plain that the lamps show up.
 */
export function paintViaduct(L, Xb, Zb, cam) {
  const { cx, yh, f } = cam, { w: W, h: H, idx } = L;
  const put = (x, y, X, Z, sun, sky) => {
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    const i = y * W + x;
    if (Zb[i] < Z * 0.995) return;               // something nearer is there
    idx[i] = I(G.iron, sun, sky, hazeOf(Z)); Zb[i] = Z; Xb[i] = X;
  };
  const pts = RAILWAY;
  let acc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [X0, Z0, hd0, hg0] = pts[i], [X1, Z1, hd1, hg1] = pts[i + 1];
    if (Z0 < 3 && Z1 < 3) continue;
    const xa = cx + f * X0 / Z0, ya = yh + f * (1 - hd0) / Z0, xb = cx + f * X1 / Z1, yb = yh + f * (1 - hd1) / Z1;
    const n = Math.max(1, Math.ceil(Math.hypot(xb - xa, yb - ya) * 2));
    for (let s = 0; s <= n; s++) {
      const t = s / n, Z = lerp(Z0, Z1, t), X = lerp(X0, X1, t), x = lerp(xa, xb, t), y = lerp(ya, yb, t);
      const thick = Z < 9 ? 2 : 1;
      for (let k = 0; k < thick; k++) put(x, y + k, X, Z, k === 0 ? 3 : 1, k === 0 ? 3 : 1);
    }
    // legs: the 3D trestle's bents every ~22 m (in prologue units 22 / U)
    const seg = Math.hypot(X1 - X0, Z1 - Z0);
    for (let d = acc; d < seg; d += 22 / U) {
      const t = d / seg, X = lerp(X0, X1, t), Z = lerp(Z0, Z1, t), hd = lerp(hd0, hd1, t), hg = lerp(hg0, hg1, t);
      const x = Math.round(cx + f * X / Z), y0 = yh + f * (1 - hd) / Z, y1 = yh + f * (1 - hg) / Z;
      for (let y = Math.ceil(y0 + 1); y <= Math.round(y1); y++) put(x, y, X, Z, 1, 1);
    }
    acc = (acc - seg) % (22 / U); if (acc < 0) acc += 22 / U;
  }
  L.used = null;
}

export { heightBase as _heightBase, plainAt as _plainAt, forestAt as _forestAt };

// ---------------------------------------------------------------- 遠化: the silver-white ghost (G5R3-22)
//
// The land the tide has passed is its own ghost, as the first vista had it (src/vista/tod.js ghost(),
// v0.2; the user: "幽灵一样银白色的"): everything still there in its own place and shape, the fields,
// roads and roofs keeping their own lightness and their light and shade, drained of colour, lifted, a
// bluish silver-white lit by nothing in particular; its lamps out, nothing reflected in its water.
// Ground zero is the town (the tide bursts from it): the nearer the town, the more a ghost, thinner
// ring by ring outward, nothing left past the last ring (the land there as it was, its lamps lit);
// the region's ring round home untouched. These are the 3D lookout's own numbers and its own function
// (godot/world3d/vista3d.gd ghost_k, vista_common v_ghost_k), so the prologue and the lookout show the
// same 遠化. Over the land gone far the air shimmers a little, as over heat (a whole-pixel sway up
// and down, the more the more a ghost), and silver motes rise from it (Godot).
// (Tried and rejected: the 褪版, the land as a woodblock print losing its colour blocks down to the
// key block's lines on the paper, G5R3-18; the user, G5R3-22: "太脏、像灰模".)
/** ground zero (m, the 3D frame): the town, vista.json's largest village */
export function ghostZero() { const v = VILLAGES.reduce((a, b) => (b.n > a.n ? b : a)); return [v.x, v.z]; }
/** the rings (m from ground zero): full within r0, 0.75 at r1, 0.4 at r2, nothing past r3 (vista3d.gd GHOST_R) */
export const GHOST_R = [400, 1100, 2600, 5500];
/** the region's ellipse round home (vista.json mist: cx, cz, rx, rz in m) */
export function ghostHome() { const m = W3.json.mist; return { cx: m.cx, cz: m.cz, rx: m.rx, rz: m.rz }; }
// pixel_toon's w3_hash and vista3d.gd _vnoise (fposmod = the GLSL fract)
const fract = x => x - Math.floor(x);
function w3hash(x, y) {
  let p0 = fract(x * 0.1031), p1 = fract(y * 0.1031), p2 = fract(x * 0.1031);
  const d = p0 * (p1 + 33.33) + p1 * (p2 + 33.33) + p2 * (p0 + 33.33);
  p0 += d; p1 += d; p2 += d;
  return fract((p0 + p1) * p2);
}
function w3vnoise(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  return lerp(lerp(w3hash(ix, iy), w3hash(ix + 1, iy), ux), lerp(w3hash(ix, iy + 1), w3hash(ix + 1, iy + 1), ux), uy);
}
/** How much a ghost a point of the land is (x, z in m, the 3D frame): 1 at the town .. 0, each ring's
 *  radius wandering a tenth either way with the bearing; 0 inside the region's ring round home,
 *  coming in from 1.15 to 1.8 times it. Exactly vista3d.gd ghost_k. */
export function ghostK(x, z) {
  const [cx, cz] = ghostZero();
  const dx = x - cx, dz = z - cz;
  const a = Math.atan2(dx, -dz);
  const w = 0.9 + 0.2 * (w3vnoise(a * 2.6 + 4.0, 1.7) * 0.7 + w3vnoise(a * 7.3 + 1.0, 5.1) * 0.3);
  const r = Math.hypot(dx, dz) / w, [r0, r1, r2, r3] = GHOST_R;
  let k;
  if (r < r0) k = 1;
  else if (r < r1) k = lerp(1, 0.75, smooth(r0, r1, r));
  else if (r < r2) k = lerp(0.75, 0.4, smooth(r1, r2, r));
  else k = lerp(0.4, 0, smooth(r2, r3, r));
  const h = ghostHome(), e = Math.hypot((x - h.cx) / h.rx, (z - h.cz) / h.rz);
  return k * smooth(1.15, 1.8, e);
}
/** Whether a lamp at X, Z (prologue units) goes out as the tide passes: as the lookout's lamps do
 *  (vista_common v_drain, smoothstep(0.2, 0.35, k)), one lamp at a time by its own draw. */
export function lampDrained(X, Z, seed) {
  const dr = smooth(0.2, 0.35, ghostK(-X * U, Z * U));
  return dr > 0 && hash2(Math.round(X * 1000), Math.round(Z * 1000), 947 + (seed | 0)) < dr;
}
const GHOST_HAZE = [0.6, 0.66, 0.78];
const SUNLV = [0, 0.1, 0.22, 0.36, 0.5, 0.66, 0.83, 1], SKYLV = [0.42, 0.62, 0.82, 1], HAZELV = [0, 0.12, 0.24, 0.37, 0.5, 0.63, 0.77, 0.9];
const lum3 = c => c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114;
const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** The ghost's colour for a ground id (packed sRGB, alpha 255): v0.2's ghost(), its lightness spread a
 *  third wider and its haze kept to half, so that the land's shapes stay clear. */
export function ghostPalette() {
  const cache = new Map();
  return v => {
    let out = cache.get(v);
    if (out !== undefined) return out;
    const mat = GROUND_MATS[v >> 8];
    if (!mat) { cache.set(v, 0); return 0; }
    const s = (v >> 5) & 7, k = (v >> 3) & 3, h = v & 7;
    let c;
    if (mat.water) c = [0.6, 0.66, 0.76].map(q => q * (0.62 + (mat.refl ?? 0.6) * 0.4));
    else if (mat.rim) c = mat.albedo.map(q => q * 1.2);
    else c = mat.albedo.map(q => q * (0.66 + 0.42 * SUNLV[s] + 0.12 * SKYLV[k]));
    const l = clamp(lum3(c), 0, 1), L2 = clamp(0.2 + 0.74 * Math.pow(l, 0.85), 0, 1);
    let g = mix3([L2 * 0.86, L2 * 0.92, L2 * 1.07], c, 0.1);
    if (h) g = mix3(g, GHOST_HAZE, HAZELV[h] * 0.3);
    const q = g.map(x => Math.round(clamp(x, 0, 1) * 255));
    out = ((255 << 24) | (q[2] << 16) | (q[1] << 8) | q[0]) >>> 0;
    cache.set(v, out);
    return out;
  };
}

/**
 * Per ground pixel (RGBA8): R how much a ghost the place is once the tide has passed (ghostK, 0..255);
 * G how much the air over it shimmers (k^1.5, as the lookout's: most at the town, next to none below
 * 0.5); B, A 0.
 */
export function ghostMaps(L, Xb, Zb, mask, W, H) {
  const N = W * H, out = new Uint8Array(N * 4);
  for (let i = 0; i < N; i++) {
    if (!mask[i]) continue;
    const k = ghostK(-Xb[i] * U, Zb[i] * U);
    out[i * 4] = Math.round(k * 255);
    out[i * 4 + 1] = Math.round(Math.pow(k, 1.5) * 255);
  }
  return out;
}

