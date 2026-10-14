// Lights: one or two crisp pixels for the source plus a pre-blurred, stepped additive glow, so the
// frame looks finished without any external bloom. Colours are kept warm for this shore and
// pale jade for the sky shore.

import { clamp, mix3, glowSprite, css, makeCanvas, ctx2d } from './util.js';

export const COL = {
  window: [255, 196, 122],
  windowDim: [226, 150, 92],
  lantern: [255, 152, 88],
  fire: [255, 206, 136],
  fireHot: [255, 238, 196],
  ember: [196, 72, 40],
  star: [206, 216, 255],
  jade: [196, 246, 226],
  jadeCore: [236, 255, 248],
  jadeDeep: [120, 210, 190],
  red: [255, 66, 48],
  firefly: [214, 255, 150],
};

const coreCache = new Map();
export const cssOf = (c, a = 1) => {
  const k = c.join(',') + '|' + a.toFixed(2);
  let s = coreCache.get(k);
  if (!s) { s = css(c, a); coreCache.set(k, s); }
  return s;
};

// draw one glow centred on (x, y) (integer pixel centre), additive
export function glow(g, x, y, r, rgb, a) {
  if (a <= 0.01) return;
  const spr = glowSprite(r, rgb.map(v => Math.round(v)), 6, 1.7);
  const prev = g.globalAlpha, op = g.globalCompositeOperation;
  g.globalAlpha = clamp(a, 0, 1);
  if (op !== 'source-atop') g.globalCompositeOperation = 'lighter';
  g.drawImage(spr, Math.round(x) - r, Math.round(y) - r);
  g.globalAlpha = prev; g.globalCompositeOperation = op;
}

export function px(g, x, y, rgb, a = 1, w = 1, h = 1) {
  if (a <= 0.01) return;
  g.fillStyle = cssOf(rgb, Math.round(clamp(a, 0, 1) * 20) / 20);
  g.fillRect(Math.round(x), Math.round(y), w, h);
}

// colour along a rising light's path: our amber turning to their pale jade as it arrives
export function riseColor(base, s) {
  const k = clamp((s - 0.55) / 0.4, 0, 1);
  return mix3(base, COL.jade, k * k * (3 - 2 * k));
}

// Static lights cached in tiles. Each frame the caller gives every light a quantised level (0 =
// off); only tiles whose lights changed are re-rendered, and the tiles are composited with
// 'lighter'. Cuts ~2 draw calls per light per frame to ~1 per tile.
export class LightTiles {
  constructor(lights, drawFn, { tw = 64, th = 40, margin = 7 } = {}) {
    this.tw = tw; this.th = th; this.m = margin; this.draw1 = drawFn;
    this.tiles = new Map();
    for (const L of lights) {
      const k = Math.floor(L.x / tw) + ',' + Math.floor(L.y / th);
      let T = this.tiles.get(k);
      if (!T) { T = { x0: Math.floor(L.x / tw) * tw - margin, y0: Math.floor(L.y / th) * th - margin, lights: [], c: null, dirty: true, any: false }; this.tiles.set(k, T); }
      T.lights.push(L); L._q = -1;
    }
  }
  // levelOf(L) -> integer level (0 off .. n)
  update(levelOf) {
    for (const T of this.tiles.values()) for (const L of T.lights) {
      const q = levelOf(L);
      if (q !== L._q) { L._q = q; T.dirty = true; }
    }
  }
  draw(g, ox, oy) {
    const { tw, th, m } = this;
    const op = g.globalCompositeOperation;
    for (const T of this.tiles.values()) {
      if (T.dirty) {
        T.dirty = false;
        T.any = T.lights.some(L => L._q > 0);
        if (T.any) {
          if (!T.c) { T.c = makeCanvas(tw + 2 * m, th + 2 * m); T.g = ctx2d(T.c); }
          T.g.clearRect(0, 0, T.c.width, T.c.height);
          T.g.globalCompositeOperation = 'lighter';
          for (const L of T.lights) if (L._q > 0) this.draw1(T.g, L, L._q, L.x - T.x0, L.y - T.y0);
          T.g.globalCompositeOperation = 'source-over';
        }
      }
      if (T.any) { g.globalCompositeOperation = 'lighter'; g.drawImage(T.c, T.x0 + ox, T.y0 + oy); }
    }
    g.globalCompositeOperation = op;
  }
}

// One additive light buffer per frame: every dynamic point of light (rising lights and their
// tails, fires, the dance ring, motes, the curtain of the wave) is summed on the CPU into an RGB
// buffer and composited with a single putImageData + drawImage('lighter'). A few hundred lights
// cost a few hundred tiny array loops instead of a thousand canvas calls.
const GLOW_W = new Map();
function glowWeights(r) {
  let w = GLOW_W.get(r);
  if (w) return w;
  const n = 2 * r + 1; w = new Float32Array(n * n);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const d = Math.hypot(x - r, y - r) / (r + 0.5);
    let a = Math.pow(clamp(1 - d, 0, 1), 1.7);
    w[y * n + x] = Math.round(a * 6) / 6;
  }
  GLOW_W.set(r, w);
  return w;
}
export class AddBuffer {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.R = new Float32Array(w * h); this.G = new Float32Array(w * h); this.B = new Float32Array(w * h);
    this.c = makeCanvas(w, h); this.g = ctx2d(this.c);
    this.img = this.g.createImageData(w, h); this.U = new Uint32Array(this.img.data.buffer);
    this.x0 = w; this.y0 = h; this.x1 = -1; this.y1 = -1;
    this.px0 = 0; this.py0 = 0; this.px1 = -1; this.py1 = -1; // last flushed box
  }
  _box(x0, y0, x1, y1) { if (x0 < this.x0) this.x0 = x0; if (y0 < this.y0) this.y0 = y0; if (x1 > this.x1) this.x1 = x1; if (y1 > this.y1) this.y1 = y1; }
  // add a single pixel (rgb 0..255, a 0..1); w/h for 2x2 cores
  px(x, y, rgb, a, w = 1, h = 1) {
    if (a <= 0.004) return;
    x = Math.round(x); y = Math.round(y);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const X = x + i, Y = y + j;
      if (X < 0 || Y < 0 || X >= this.w || Y >= this.h) continue;
      const k = Y * this.w + X;
      this.R[k] += rgb[0] * a; this.G[k] += rgb[1] * a; this.B[k] += rgb[2] * a;
    }
    this._box(x, y, x + w - 1, y + h - 1);
  }
  glow(x, y, r, rgb, a) {
    if (a <= 0.004) return;
    x = Math.round(x); y = Math.round(y);
    const wts = glowWeights(r), n = 2 * r + 1, W = this.w, H = this.h;
    const r0 = rgb[0] * a, g0 = rgb[1] * a, b0 = rgb[2] * a;
    for (let j = 0; j < n; j++) {
      const Y = y - r + j; if (Y < 0 || Y >= H) continue;
      for (let i = 0; i < n; i++) {
        const X = x - r + i; if (X < 0 || X >= W) continue;
        const wv = wts[j * n + i]; if (!wv) continue;
        const k = Y * W + X;
        this.R[k] += r0 * wv; this.G[k] += g0 * wv; this.B[k] += b0 * wv;
      }
    }
    this._box(x - r, y - r, x + r, y + r);
  }
  // a vertical strip fading upward (the wave's curtain): bottom at y, height h
  strip(x, y, h, rgb, a) {
    if (a <= 0.004 || h < 1) return;
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || x >= this.w) return;
    for (let k = 0; k <= h; k++) {
      const Y = y - k; if (Y < 0 || Y >= this.h) continue;
      const u = 1 - k / (h + 1), s = Math.round(u * u * 6) / 6 * a;
      if (s <= 0) continue;
      const q = Y * this.w + x;
      this.R[q] += rgb[0] * s; this.G[q] += rgb[1] * s; this.B[q] += rgb[2] * s;
    }
    this._box(x, y - h, x, y);
  }
  // composite onto g at (ox, oy) and clear for the next frame
  flush(g, ox = 0, oy = 0) {
    const W = this.w;
    let x0 = Math.max(0, this.x0), y0 = Math.max(0, this.y0), x1 = Math.min(W - 1, this.x1), y1 = Math.min(this.h - 1, this.y1);
    // the canvas must also be cleared where the last frame drew
    const ux0 = Math.min(x0, this.px0), uy0 = Math.min(y0, this.py0), ux1 = Math.max(x1, this.px1), uy1 = Math.max(y1, this.py1);
    const has = x1 >= x0 && y1 >= y0;
    if (ux1 >= ux0 && uy1 >= uy0) {
      const U = this.U, R = this.R, G = this.G, B = this.B;
      for (let y = uy0; y <= uy1; y++) for (let x = ux0; x <= ux1; x++) {
        const k = y * W + x, r = R[k], gg = G[k], b = B[k];
        if (r || gg || b) {
          U[k] = (255 << 24 | (b > 255 ? 255 : b) << 16 | (gg > 255 ? 255 : gg) << 8 | (r > 255 ? 255 : r)) >>> 0;
          R[k] = 0; G[k] = 0; B[k] = 0;
        } else U[k] = 0;
      }
      this.g.putImageData(this.img, 0, 0, ux0, uy0, ux1 - ux0 + 1, uy1 - uy0 + 1);
    }
    if (has) {
      const op = g.globalCompositeOperation;
      g.globalCompositeOperation = 'lighter';
      g.drawImage(this.c, x0, y0, x1 - x0 + 1, y1 - y0 + 1, x0 + ox, y0 + oy, x1 - x0 + 1, y1 - y0 + 1);
      g.globalCompositeOperation = op;
    }
    this.px0 = has ? x0 : W; this.py0 = has ? y0 : this.h; this.px1 = has ? x1 : -1; this.py1 = has ? y1 : -1;
    this.x0 = W; this.y0 = this.h; this.x1 = -1; this.y1 = -1;
  }
}
