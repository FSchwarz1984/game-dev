// Sky: a banded gradient with dithered seams (painted per time of day), a star field, and cloud
// puffs (each its own small indexed sprite, so the deck can drift and part).

import { clamp, lerp, smooth, rng, hash2, bayer, mix3, pack, makeCanvas, ctx2d, IndexLayer, I, TAU, fbm } from './util.js';
import { skyAt, palette } from './tod.js';

// Paint the sky gradient for one time of day. Rows: elevation e = (yh - y) / S; bands every ~5 px
// with a 2-px ordered-dither seam between them.
export function paintSky(w, h, yh, S, env, extra) {
  // a clean gradient: per-row colour quantised to fine steps (no dither speckle), the warm west
  // side blended in per column band
  const c = makeCanvas(w, h), g = ctx2d(c), id = g.createImageData(w, h), U = new Uint32Array(id.data.buffer);
  const NU = 24, q = v => Math.round(v / 2) * 2;
  for (let y = 0; y < h; y++) {
    const e = (yh - y) / S;
    const row = [];
    for (let k = 0; k <= NU; k++) {
      let col = skyAt(env, e, k / NU);
      if (extra) col = extra(col, e, k / NU);
      row.push(pack([q(col[0]), q(col[1]), q(col[2])]));
    }
    for (let x = 0; x < w; x++) U[y * w + x] = row[Math.round((x / (w - 1)) * NU)];
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

// cloud materials: lit by the low sun from the west and from below (sun bits), by the sky (sky bits)
export const CLOUD_MATS = [];
CLOUD_MATS[1] = { albedo: [0.82, 0.8, 0.84], ambK: 1.2, sunK: 0.9 };          // body
CLOUD_MATS[2] = { albedo: [0.95, 0.88, 0.84], ambK: 1.3, sunK: 1.25 };        // lit rim
CLOUD_MATS[3] = { albedo: [0.62, 0.64, 0.74], ambK: 1.0, sunK: 0.55 };        // thick, shaded core

export function cloudPalette(env, opts) {
  return palette(CLOUD_MATS, env, opts || {});
}

/**
 * A deck of clouds on a ceiling at height Hc above the camera, seen in perspective: banks of
 * stratocumulus, big overhead, small and flat toward the horizon. The density is computed once;
 * the deck is re-rendered (indices -> palette) only when the hole or the time of day changes.
 */
export class CloudDeck {
  constructor({ w, h, cx, yh, f, Hc, seed, cover = 0.5, bottom }) {
    this.o = { w, h, cx, yh, f, Hc, seed };
    const yb = bottom ?? yh - 10;
    const D = new Float32Array(w * h), PX = new Float32Array(w * h), PZ = new Float32Array(w * h);
    for (let y = 0; y < Math.min(h, yb); y++) {
      const Z = f * Hc / Math.max(1, yh - y);
      const fade = smooth(yb, yb - 26, y);         // thin out toward the horizon
      for (let x = 0; x < w; x++) {
        const X = (x + 0.5 - cx) * Z / f;
        // banks elongated across the view; detail octaves dropped with distance (no speckle)
        const oct = Z < 14 ? 4 : Z < 30 ? 3 : 2;
        let n = fbm(X * 0.16 + 11, Z * 0.34, oct, seed);
        n += 0.22 * (vnoiseLite(X * 0.05, Z * 0.09, seed + 7) - 0.5);
        const i = y * w + x;
        D[i] = (n - (1 - cover) * 0.72 - 0.22) * 4 * fade;
        PX[i] = X; PZ[i] = Z;
      }
    }
    this.D = D; this.PX = PX; this.PZ = PZ; this.yb = yb;
    this.layer = new IndexLayer(w, h);
    this.key = null;
    this.canvas = makeCanvas(w, h);
    this.g = ctx2d(this.canvas);
  }
  // hole: {X, Z, r} in the deck plane (r = 0: closed). light: [lx, ly] screen direction toward the light
  render(hole, key, pal, light = [0.8, 0.6]) {
    const k = key + '|' + (hole ? hole.r.toFixed(2) : '0');
    if (k === this.key) return this.canvas;
    this.key = k;
    const { w, h } = this.o, D = this.D, idx = this.layer.idx;
    idx.fill(0);
    const val = new Float32Array(w * this.yb);
    for (let i = 0; i < val.length; i++) {
      let d = D[i];
      if (hole && hole.r > 0) {
        const dx = this.PX[i] - hole.X, dz = (this.PZ[i] - hole.Z) * 0.8, q = Math.hypot(dx, dz) / hole.r;
        d -= smooth(1.25, 0.55, q) * 1.6;
        d += smooth(0.9, 1.35, q) * smooth(1.9, 1.35, q) * 0.25 * Math.min(1, hole.r / 3); // clouds bunch up at the hole's rim
      }
      val[i] = d;
    }
    const [lx, ly] = light;
    for (let y = 1; y < this.yb - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x, d = val[i];
      if (d <= 0) continue;
      const gx = val[i + 1] - val[i - 1], gy = val[i + w] - val[i - w], gl = Math.hypot(gx, gy) || 1;
      const nx = -gx / gl, ny = -gy / gl;                       // outward
      const lam = nx * lx + ny * ly;                            // facing the light
      const edge = d < 0.18;
      const thick = clamp(d / 1.6, 0, 1);
      let mat = 1, sun = clamp(Math.round((lam * 0.5 + 0.5) * 6 * (1 - thick * 0.35)), 0, 7);
      if (edge && lam > 0.15) { mat = 2; sun = 7; }
      else if (thick > 0.62 && lam < 0.2) mat = 3;
      const sky = clamp(Math.round((1 - thick) * 2 + (ny < 0 ? 1 : 0)), 0, 3);
      idx[i] = I(mat, sun, sky, 0);
    }
    this.layer.used = null;
    this.layer.despeckle(() => true);
    const U = this.layer.pixels(pal);
    if (!this.img) this.img = this.g.createImageData(w, h);
    new Uint32Array(this.img.data.buffer).set(U);
    this.g.putImageData(this.img, 0, 0);
    return this.canvas;
  }
}

function vnoiseLite(x, y, s) { return fbm(x, y, 2, s); }
