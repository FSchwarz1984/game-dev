// 天岸, the sky shore: a whole land hanging upside down far above the cloud sea. Rendered with the
// same column march as the ground, mirrored: the underside of a ceiling at height Hs, from which
// ranges hang with their peaks pointing down, thin silver rivers in the high valleys, towns on the
// flats (their lights are drawn separately), and right above the pass the gate: an inverted
// valley drawn down into a funnel whose mouth points at us.
//
// Readability over detail: haze in a few flat steps (so the ranges stand in layers, like painted
// distant mountains), two tones per face, and a rim of light along every lower edge where a nearer
// range hangs in front of a farther one: the plain's glow catching the peak tips.

import { clamp, lerp, smooth, rng, hash2, vnoise, fbm, ridged, IndexLayer, I, pack, mix3 } from './util.js';
import { march } from './terrain.js';

export const S = { land: 1, forest: 2, rock: 3, river: 4, rim: 5, funnel: 6, mouth: 7, funnelRim: 8 };
const HAZE_Z = [30, 40, 52, 66];

/**
 * @param o { w, h, cx, yh, f, Hs, funnel: {X, Z, D, R}, towns: [{X, Z, r}], hazeEdgeY, seed }
 */
export function buildSkyShore(o) {
  const { w, h, cx, yh, f, Hs, funnel: Fn } = o;
  const R = rng(o.seed + 501);
  const towns = o.towns;
  const rivers = makeRivers(R, Fn);
  const flatAt = (X, Z) => { let fl = 0; for (const t of towns) { const q = Math.hypot(X - t.X, (Z - t.Z) * 0.8) / t.r; if (q < 1.6) fl = Math.max(fl, smooth(1.6, 0.8, q)); } return fl; };
  const depth = (X, Z) => {
    let d = 0.15 + 0.2 * fbm(X * 0.12, Z * 0.12, 2, 81);
    const flat = flatAt(X, Z);
    const rg = ridged(X * 0.11 + 3, Z * 0.1, 3, 83);
    const zone = smooth(0.25, 0.6, vnoise(X * 0.04, Z * 0.05, 85));
    d += (1 - flat) * Math.pow(rg, 2.1) * 5.2 * (0.45 + 0.55 * zone);
    d += (1 - flat) * 0.22 * Math.pow(vnoise(X * 2.6, Z * 2.6, 87), 4);   // hanging forest, tips down
    for (const rv of rivers) { const dd = distRiver(rv, X, Z); if (dd < 0.6) d -= (0.6 - dd) * 0.45; }
    const fx = X - Fn.X, fz = Z - Fn.Z, r = Math.hypot(fx, fz) / Fn.R;
    if (r < 1) {
      const ang = Math.atan2(fz, fx);
      const ribs = 0.9 + 0.1 * Math.abs(Math.sin(ang * 4 + r * 3));
      d = Math.max(d, Fn.D * Math.pow(1 - r, 1.9) * ribs);
    }
    return Math.max(0.02, d);
  };
  const height = (X, Z) => Hs - depth(X, Z);
  const m = march({ w, h, cx, yh, f, camY: 0, z0: 4, z1: 140, height, k: 0.013, ceiling: true });
  const L = new IndexLayer(w, h);
  const Lt = norm3([-0.4, -0.7, -0.6]); // light from below, from the left and toward us
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!m.mask[i]) continue;
    const X = m.X[i], Z = m.Z[i];
    const dd = depth(X, Z);
    const e = Math.max(0.02, Z * 0.005);
    const dx = depth(X + e, Z) - dd, dz = depth(X, Z + e) - dd;
    let nx = -dx, ny = -e, nz = -dz; const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const lam = nx * Lt[0] + ny * Lt[1] + nz * Lt[2];
    const fr = Math.hypot(X - Fn.X, Z - Fn.Z) / Fn.R;
    let mat = S.land;
    if (fr < 1) mat = fr < 0.06 ? S.mouth : S.funnel;
    else if (-ny < 0.55) mat = S.rock;
    else if (vnoise(X * 0.7, Z * 0.7, 89) > 0.5) mat = S.forest;
    if (fr >= 1) for (const rv of rivers) if (distRiver(rv, X, Z) < Z / f * 0.7) mat = S.river;
    const sun = lam > 0.55 ? 6 : lam > 0.25 ? 4 : 2;
    const sky = clamp(Math.round(-ny * 3), 0, 3);
    let haze = 0; for (const zz of HAZE_Z) if (Z > zz) haze++;
    L.idx[i] = I(mat, sun, sky, haze);
  }
  // lower edges of nearer ranges against farther ones catch the light from below
  const src = L.idx.slice();
  for (let y = 0; y < h - 2; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!src[i] || !src[i + w]) continue;
    if (m.Z[i + w] > m.Z[i] * 1.18) {
      const fr = Math.hypot(m.X[i] - Fn.X, m.Z[i] - Fn.Z) / Fn.R;
      L.idx[i] = I(fr < 1 ? S.funnelRim : S.rim, 6, 3, src[i] & 7);
    }
  }
  // the hem: cut off where the haze takes it, frayed a little (nothing beyond is seen)
  const hazeEdgeY = o.hazeEdgeY;
  if (hazeEdgeY) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const k = (y - hazeEdgeY) / 6 + (vnoise(x * 0.07, 3, 95) - 0.5) * 1.4;
    if (k > 0.5) L.idx[y * w + x] = 0;
  }
  L.despeckle(v => (v >> 8) !== S.river && (v >> 8) !== S.rim);
  // lights: towns (streets of lamps and clusters), placed only where they are not hidden
  const proj = (X, Z) => [cx + f * X / Z, yh - f * height(X, Z) / Z];
  const lights = [];
  const put = (X, Z, b) => {
    const [x, y] = proj(X, Z);
    const xi = Math.round(x), yi = Math.round(y);
    if (yi < 0 || yi >= h || xi < 0 || xi >= w) return;
    const i = yi * w + xi;
    if (!m.mask[i] || !L.idx[i] || Math.abs(m.Z[i] - Z) > Z * 0.1) return;
    lights.push({ x: xi, y: yi, Z, ph: R(), b });
  };
  for (const t of towns) {
    // a few streets: lamps in lines
    for (let s = 0; s < 4; s++) {
      const a = R() * Math.PI, len = t.r * (0.8 + R() * 0.8), ox = (R() - 0.5) * t.r * 0.6, oz = (R() - 0.5) * t.r * 0.6;
      for (let u = -len / 2; u < len / 2; u += 0.16) put(t.X + ox + Math.cos(a) * u, t.Z + oz + Math.sin(a) * u, 0.55 + R() * 0.3);
    }
    const n = Math.round(t.r * t.r * 5);
    for (let k = 0; k < n; k++) { const a = R() * Math.PI * 2, d = Math.pow(R(), 0.7) * t.r; put(t.X + Math.cos(a) * d, t.Z + Math.sin(a) * d / 0.8, 0.4 + R() * 0.6); }
  }
  // scattered farms
  for (let k = 0; k < 60; k++) put((R() - 0.5) * 70, 26 + R() * 50, 0.3 + R() * 0.35);
  return { layer: L, lights, proj, depth, height, rivers, mask: m.mask, Z: m.Z };
}

function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]); return [v[0] / l, v[1] / l, v[2] / l]; }

// rivers: from the gate's flanks up and away into the far land, meandering (they flow "up", away)
function makeRivers(R, Fn) {
  const out = [];
  const starts = [[Fn.X + Fn.R * 0.3, Fn.Z + Fn.R * 0.95, 0.42], [Fn.X - Fn.R * 0.9, Fn.Z + Fn.R * 0.5, 0.7], [Fn.X + Fn.R * 1.0, Fn.Z + Fn.R * 0.4, 0.28]];
  for (const [sx, sz, a0] of starts) {
    let X = sx, Z = sz, a = Math.PI * a0;
    const pts = [[X, Z]];
    for (let i = 0; i < 60; i++) {
      a += (R() - 0.5) * 0.8;
      a = clamp(a, Math.PI * 0.15, Math.PI * 0.85);
      X += Math.cos(a) * 1.3; Z += Math.sin(a) * 1.3;
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
        bins.get(k).push([ax, az, bx - ax, bz - az]);
      }
    }
  }
  const list = bins.get(Math.floor(Z));
  if (!list) return 1e9;
  let best = 1e9;
  for (const [ax, az, dx, dz] of list) {
    if (X < Math.min(ax, ax + dx) - 1 || X > Math.max(ax, ax + dx) + 1) continue;
    const t = clamp(((X - ax) * dx + (Z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    const d = Math.hypot(X - ax - dx * t, Z - az - dz * t);
    if (d < best) best = d;
  }
  return best;
}

// colours (night): pale blue land, a touch of teal, lit faintly from below; low contrast
const BASE = {
  [S.land]: [[36, 46, 76], [46, 58, 88], [58, 72, 100]],
  [S.forest]: [[31, 42, 68], [40, 53, 80], [50, 65, 92]],
  [S.rock]: [[44, 52, 82], [58, 68, 98], [74, 86, 114]],
  [S.river]: [[112, 134, 160], [136, 160, 184], [156, 182, 204]],
  [S.rim]: [[78, 104, 124], [92, 122, 138], [104, 138, 150]],
  [S.funnel]: [[40, 54, 84], [56, 76, 104], [76, 102, 124]],
  [S.funnelRim]: [[96, 136, 146], [110, 156, 160], [128, 176, 176]],
  [S.mouth]: [[120, 170, 172], [150, 200, 196], [180, 226, 214]],
};
const HAZE_K = [0, 0.3, 0.52, 0.7, 0.84];
export function skyShorePalette(hazeCol) {
  return i => {
    const m = i >> 8, s = (i >> 5) & 7, hz = i & 7;
    const b = BASE[m];
    if (!b) return 0;
    let c = s >= 6 ? b[2] : s >= 4 ? b[1] : b[0];
    c = mix3(c, hazeCol, HAZE_K[Math.min(4, hz)]);
    return pack(c);
  };
}
