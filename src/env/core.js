/* =====================================================================
   env/core — math, deterministic randomness, fast noise and colour for
   the pixel-art painters. Pure functions on numbers and typed arrays:
   everything here runs the same in the browser, a Web Worker and Node
   (tools/env/*.mjs render previews of the art without a browser).
   Ported from legacy/v0.1/src/core.js; the noise is precomputed into
   tileable tables because the home map paints ~7 M pixels at load.
   ===================================================================== */

export const TAU = Math.PI * 2;
export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const sstep = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const fract = v => v - Math.floor(v);
export const hyp = Math.hypot;
export const angDiff = (a, b) => { let d = (b - a) % TAU; if (d > Math.PI) d -= TAU; if (d < -Math.PI) d += TAU; return d; };

/* ---------- hashing / RNG ---------- */
export function hashi(x, y, s = 0) {
  let h = Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(s | 0, 982451653);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return (h ^ (h >>> 16)) >>> 0;
}
/** Integer lattice hash in [0, 1). */
export function hash2(x, y, s = 0) { return hashi(x, y, s) / 4294967296; }
export function hash1(n, s = 0) { return hashi(n, 0x5bd1e995, s) / 4294967296; }

/** mulberry32 with helpers: deterministic placement on every load. */
export function RNG(seed) {
  let a = seed >>> 0;
  const f = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  f.range = (lo, hi) => lo + (hi - lo) * f();
  f.int = (lo, hi) => Math.floor(lo + (hi - lo + 1) * f());
  f.pick = arr => arr[Math.floor(f() * arr.length)];
  f.chance = p => f() < p;
  f.sign = () => (f() < 0.5 ? -1 : 1);
  f.gauss = () => (f() + f() + f() - 1.5) / 1.5;
  return f;
}

/* ---------- value noise (exact, slow path for small sprites) ---------- */
export function vnoise(x, y, s = 0) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
export function fbm(x, y, o = 4, s = 0) {
  let t = 0, a = 0.5, f = 1, n = 0;
  for (let i = 0; i < o; i++) { t += a * vnoise(x * f, y * f, s + i * 17); n += a; a *= 0.5; f *= 2.03; }
  return t / n;
}
export function ridge(x, y, o = 4, s = 0) {
  let t = 0, a = 0.5, f = 1, n = 0;
  for (let i = 0; i < o; i++) { t += a * (1 - Math.abs(vnoise(x * f, y * f, s + i * 31) * 2 - 1)); n += a; a *= 0.5; f *= 2.1; }
  return t / n;
}

/* ---------- tileable noise tables (fast path for big bakes) ----------
   A NoiseTile holds periodic fBm on an N×N lattice; sample(x, y) reads it
   with bilinear interpolation at one lattice unit per input unit, so the
   caller picks the feature size by scaling the coordinates. ~10 ns/sample. */
export class NoiseTile {
  constructor(n = 256, octaves = 4, seed = 1, base = 8, gain = 0.5) {
    this.n = n; this.mask = n - 1; const d = this.d = new Float32Array(n * n);
    let amp = 1, norm = 0;
    for (let o = 0; o < octaves; o++) {
      const cells = base << o; const step = n / cells; // lattice cells across the tile at this octave
      const lat = new Float32Array(cells * cells);
      for (let i = 0; i < lat.length; i++) lat[i] = hash2(i % cells, (i / cells) | 0, seed * 131 + o * 7);
      for (let y = 0; y < n; y++) {
        const fy = y / step, yi = Math.floor(fy), ty = fy - yi, vy = ty * ty * (3 - 2 * ty);
        const y0 = (yi % cells) * cells, y1 = ((yi + 1) % cells) * cells;
        for (let x = 0; x < n; x++) {
          const fx = x / step, xi = Math.floor(fx), tx = fx - xi, ux = tx * tx * (3 - 2 * tx);
          const x0 = xi % cells, x1 = (xi + 1) % cells;
          const a = lat[y0 + x0], b = lat[y0 + x1], c = lat[y1 + x0], e = lat[y1 + x1];
          d[y * n + x] += amp * (a + (b - a) * ux + (c - a) * vy + (a - b - c + e) * ux * vy);
        }
      }
      norm += amp; amp *= gain;
    }
    for (let i = 0; i < d.length; i++) d[i] /= norm;
    // stretch to roughly 0..1 (fBm piles up around 0.5)
    let lo = 1, hi = 0; for (let i = 0; i < d.length; i++) { if (d[i] < lo) lo = d[i]; if (d[i] > hi) hi = d[i]; }
    const k = 1 / Math.max(1e-6, hi - lo); for (let i = 0; i < d.length; i++) d[i] = (d[i] - lo) * k;
  }
  sample(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y), tx = x - xi, ty = y - yi, m = this.mask, n = this.n, d = this.d;
    const x0 = xi & m, x1 = (xi + 1) & m, y0 = (yi & m) * n, y1 = ((yi + 1) & m) * n;
    const a = d[y0 + x0], b = d[y0 + x1], c = d[y1 + x0], e = d[y1 + x1];
    return a + (b - a) * tx + (c - a) * ty + (a - b - c + e) * tx * ty;
  }
  /** nearest lookup: cheaper, blocky on purpose (pixel clusters) */
  at(x, y) { return this.d[((y | 0) & this.mask) * this.n + ((x | 0) & this.mask)]; }
}

/* ---------- colour ---------- */
export function hexRGB(h) { if (typeof h !== 'string') return h; const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
export function rgbHex(c) { return '#' + c.map(v => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0')).join(''); }
export function mixRGB(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
export function mulRGB(a, k) { return [a[0] * k, a[1] * k, a[2] * k]; }
export function lum(c) { return (c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114) / 255; }
export function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); let h = 0, s = 0; const l = (mx + mn) / 2;
  if (mx !== mn) {
    const d = mx - mn; s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
    h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6;
  }
  return [h, s, l];
}
export function hslToRgb(h, s, l) {
  h = ((h % 1) + 1) % 1; if (s === 0) return [l * 255, l * 255, l * 255];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = t => { t = ((t % 1) + 1) % 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < 0.5) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p; };
  return [f(h + 1 / 3) * 255, f(h) * 255, f(h - 1 / 3) * 255];
}
/** Hue-shifted ramp: shadows drift toward cool violet-blue, lights toward warm yellow.
    This is what keeps procedural pixel art from looking like "texture times light". */
export function ramp(base, n = 5, o = {}) {
  const c = hexRGB(base); const [h, s, l] = rgbToHsl(c[0], c[1], c[2]);
  const out = []; const lo = o.lo ?? 0.42, hi = o.hi ?? 0.38, hs = o.hueShift ?? 0.055, ss = o.satShift ?? 0.1;
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0.5 : i / (n - 1); const k = t - 0.5;
    const targetH = k < 0 ? 0.68 : 0.13; const dh = angDiff(h * TAU, targetH * TAU) / TAU;
    const hh = h + dh * Math.abs(k) * 2 * hs * 4;
    const ll = clamp(l + (k < 0 ? k * 2 * lo * l : k * 2 * hi * (1 - l)), 0, 1);
    const sat = clamp(s + (k < 0 ? Math.abs(k) * ss : -Math.abs(k) * ss * 0.8), 0, 1);
    out.push(hslToRgb(hh, sat, ll).map(v => Math.round(v)));
  }
  return out;
}
/** pick from a ramp by a continuous 0..1 value */
export const rpick = (r, t) => r[clamp(Math.round(t * (r.length - 1)), 0, r.length - 1)];

/* ---------- ordered dither ---------- */
export const BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
/** Ordered dither, deliberately weak: band edges get a 1–2 px stipple, never a wide checkerboard
    (Eastward-style clean clusters; checkerboard fields read as screen-door noise at 3×). */
export const DITHER_K = 0.4;
export const bayer = (x, y) => 0.5 + ((BAYER4[(x & 3) + (y & 3) * 4] + 0.5) / 16 - 0.5) * DITHER_K;

/* ---------- geometry helpers ---------- */
/** distance from p to a polyline; returns {d, i, t, s} (segment index, param, signed side) */
export function polyDist(px, py, pts) {
  let best = 1e9, bi = 0, bt = 0, side = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const ax = pts[i][0], ay = pts[i][1], bx = pts[i + 1][0], by = pts[i + 1][1];
    const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1;
    let t = ((px - ax) * dx + (py - ay) * dy) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t;
    const ex = px - ax - dx * t, ey = py - ay - dy * t, d = Math.sqrt(ex * ex + ey * ey);
    if (d < best) { best = d; bi = i; bt = t; side = Math.sign(dx * ey - dy * ex); }
  }
  return { d: best, i: bi, t: bt, s: side };
}
/** Catmull-Rom resample of a polyline: smooth, roughly `step` apart */
export function smoothPath(pts, step = 1, closed = false) {
  const P = closed ? [pts[pts.length - 1], ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts[pts.length - 1]];
  const out = [];
  for (let i = 1; i < P.length - 2; i++) {
    const p0 = P[i - 1], p1 = P[i], p2 = P[i + 1], p3 = P[i + 2];
    const L = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]); const n = Math.max(1, Math.ceil(L / step));
    for (let k = 0; k < n; k++) {
      const t = k / n, t2 = t * t, t3 = t2 * t;
      const f = (a, b, c, d) => 0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  if (!closed) out.push(pts[pts.length - 1].slice());
  return out;
}
/** point in polygon (even-odd) */
export function inPoly(x, y, pts) {
  let ins = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const a = pts[i], b = pts[j];
    if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) ins = !ins;
  }
  return ins;
}

/** run a generator to completion (the synchronous path of a stepped job), returning its value */
export function drain(g) { let r; do { r = g.next(); } while (!r.done); return r.value; }
