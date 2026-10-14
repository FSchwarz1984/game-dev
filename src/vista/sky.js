// Sky: a banded gradient with dithered seams (painted per time of day), a star field, and cloud
// puffs (each its own small indexed sprite, so the deck can drift and part).

import { clamp, lerp, smooth, rng, hash2, bayer, mix3, pack, makeCanvas, ctx2d, IndexLayer, I, TAU } from './util.js';
import { skyAt, palette } from './tod.js';

// Paint the sky gradient for one time of day. Rows: elevation e = (yh - y) / S; bands every ~5 px
// with a 2-px ordered-dither seam between them.
export function paintSky(w, h, yh, S, env, extra) {
  const c = makeCanvas(w, h), g = ctx2d(c), id = g.createImageData(w, h), U = new Uint32Array(id.data.buffer);
  const NB = Math.max(12, Math.round(S / 5)), NU = 10;
  const cache = new Map();
  for (let y = 0; y < h; y++) {
    const e = (yh - y) / S;
    for (let x = 0; x < w; x++) {
      const d = bayer(x, y) - 0.5;
      const eb = Math.floor(clamp(e, -0.2, 1.2) * NB + 0.5 + d * 0.42);
      const ub = Math.floor((x / w) * NU + 0.5 + d * 0.8);
      const key = eb * 64 + ub;
      let v = cache.get(key);
      if (v === undefined) {
        let col = skyAt(env, eb / NB, ub / NU);
        if (extra) col = extra(col, eb / NB, ub / NU);
        v = pack(col);
        cache.set(key, v);
      }
      U[y * w + x] = v;
    }
  }
  g.putImageData(id, 0, 0);
  return c;
}

// Stars: positions in screen space (sky region above yh). Static ones go in a canvas, twinklers are
// drawn per frame.
export function makeStars(w, yh, seed, opts = {}) {
  const R = rng(seed), stars = [];
  const n = Math.round((opts.density ?? 1) * w * yh / 260);
  for (let i = 0; i < n; i++) {
    const x = Math.floor(R() * w), e = Math.pow(R(), 0.75), y = Math.floor(yh - 2 - e * (yh - 2));
    const r = R();
    const mag = r < 0.03 ? 3 : r < 0.16 ? 2 : r < 0.5 ? 1 : 0; // 0 faint .. 3 bright
    const hue = R();
    const col = hue < 0.2 ? [255, 226, 196] : hue < 0.55 ? [214, 226, 255] : [236, 240, 255];
    stars.push({ x, y, mag, col, ph: R() * TAU, sp: 0.6 + R() * 1.8, tw: mag >= 2 || R() < 0.12 });
  }
  return stars;
}

const STAR_A = [0.32, 0.55, 0.8, 1];
export function starCanvas(w, h, stars, horizonFade) {
  const c = makeCanvas(w, h), g = ctx2d(c);
  for (const s of stars) {
    if (s.tw) continue;
    const a = STAR_A[s.mag] * (horizonFade ? horizonFade(s.y) : 1);
    if (a <= 0.02) continue;
    g.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${a.toFixed(3)})`;
    g.fillRect(s.x, s.y, 1, 1);
  }
  return c;
}

export function drawTwinklers(g, stars, t, alpha, ox = 0, oy = 0, horizonFade, mask) {
  for (const s of stars) {
    if (!s.tw) continue;
    const x = s.x + ox, y = s.y + oy;
    if (mask && !mask(x, y)) continue;
    const tw = 0.62 + 0.38 * Math.sin(t * s.sp + s.ph) * Math.sin(t * s.sp * 0.37 + s.ph * 2.1);
    const a = alpha * STAR_A[s.mag] * tw * (horizonFade ? horizonFade(s.y) : 1);
    if (a <= 0.03) continue;
    g.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${a.toFixed(3)})`;
    g.fillRect(x, y, 1, 1);
    if (s.mag === 3 && tw > 0.78) { // the brightest flare into a tiny cross at their peak
      g.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${(a * 0.4).toFixed(3)})`;
      g.fillRect(x - 1, y, 1, 1); g.fillRect(x + 1, y, 1, 1); g.fillRect(x, y - 1, 1, 1); g.fillRect(x, y + 1, 1, 1);
    }
  }
}

// ---------------------------------------------------------------- clouds

// cloud materials: lit by the sun (sun bits) from the low west, by the sky from above (sky bits)
export const CLOUD_MATS = [];
CLOUD_MATS[1] = { albedo: [0.86, 0.84, 0.86], ambK: 1.25, sunK: 0.95 };          // body
CLOUD_MATS[2] = { albedo: [0.92, 0.86, 0.84], ambK: 1.35, sunK: 1.15 };          // sunlit / underlit rim
CLOUD_MATS[3] = { albedo: [0.7, 0.72, 0.8], ambK: 1.05, sunK: 0.6 };             // shadowed core

// One puff: overlapping lobes on a flattish base, shaded as a soft volume. Light from lx (+1 =
// from the right) and from below (ly < 0: lit underside, how clouds above a lit plain look).
export function makePuff(R, wPx, hPx, lx = 1, ly = -0.35) {
  const pad = 2, w = Math.ceil(wPx) + pad * 2, h = Math.ceil(hPx) + pad * 2;
  const L = new IndexLayer(w, h);
  const lobes = [], n = 3 + Math.floor(wPx / 7);
  for (let i = 0; i < n; i++) {
    const u = (i + 0.5) / n, r = hPx * (0.35 + 0.4 * Math.sin(u * Math.PI)) * (0.75 + R() * 0.45);
    lobes.push([pad + u * wPx, pad + hPx - r * 0.9 - R() * hPx * 0.1, r]);
  }
  for (let i = 0; i < Math.floor(n / 2); i++) { // a second tier on top
    const u = 0.25 + R() * 0.5, r = hPx * (0.3 + R() * 0.25);
    lobes.push([pad + u * wPx, pad + hPx * 0.45 - R() * hPx * 0.2, r]);
  }
  const base = pad + hPx;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let best = -1, nx = 0, ny = 0;
    for (const [bx, by, br] of lobes) {
      const dx = x + 0.5 - bx, dy = (y + 0.5 - by) * 1.15, d = 1 - Math.hypot(dx, dy) / br;
      if (d > best) { best = d; nx = dx / br; ny = dy / br; }
    }
    if (best < 0 || y + 0.5 > base + 0.6) continue;
    if (best < 0.08 && hash2(x, y, 7) < 0.5) continue; // a frayed edge, not a hard disc
    const nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
    const ld = clamp(nx * lx * 0.8 - ny * ly * 1.2 + nz * 0.25, -1, 1);  // light from side/below
    const up = clamp(-ny * 0.9 + 0.4, 0, 1);                               // sky light on the tops
    const flat = smooth(base - 2.5, base, y + 0.5);                        // the flat base, darker
    let mat = 1, sun = Math.round(clamp(ld * 0.5 + 0.5, 0, 1) * 7), sky = Math.round(up * 3);
    if (best < 0.22 && ld > 0.25) mat = 2;
    if (best > 0.55 && ld < 0.1) mat = 3;
    if (flat > 0.5) { sun = Math.max(0, sun - 2); sky = Math.max(0, sky - 1); }
    L.idx[y * w + x] = I(mat, sun, sky, 0);
  }
  L.despeckle(() => true);
  return L;
}

export function cloudPalette(env, extraHaze) {
  return palette(CLOUD_MATS, env, extraHaze ? { haze: extraHaze } : {});
}

// Build a deck of puffs on a ceiling plane: rows recede toward the horizon (smaller, flatter, closer
// together). Each puff carries its ceiling position (X, Z) so it can part around a point.
export function makeDeck(seed, { w, yh, f, height, zNear, zFar, cover = 0.55, xSpread = 1.4 }) {
  const R = rng(seed), puffs = [];
  let Z = zNear;
  while (Z < zFar) {
    const yRow = yh - f * height / Z;
    const scale = f / Z;                                    // px per unit at this depth
    const half = (w * 0.5 * xSpread) / scale;               // lateral extent visible (units)
    let X = -half + R() * 0.6;
    while (X < half) {
      const wu = 0.55 + R() * 0.9;                          // width in units
      if (R() < cover) {
        const wPx = Math.max(6, wu * scale), hPx = Math.max(3, wPx * (0.22 + R() * 0.14) * (0.55 + 0.45 * smooth(zFar, zNear, Z)));
        if (wPx < 160) puffs.push({ X: X + wu / 2, Z, wPx, hPx, layer: makePuff(R, wPx, hPx), seed: R() });
      }
      X += wu * (0.75 + R() * 0.6);
    }
    Z *= 1.16 + R() * 0.08;
  }
  // far to near so near puffs overlap far ones
  puffs.sort((a, b) => b.Z - a.Z);
  return puffs;
}
