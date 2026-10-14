// Shared helpers for the vista painters: seeded randomness, noise, colour, canvases and the
// indexed-colour layer that every static vista layer is painted into.
//
// Static layers are painted ONCE as material/shade indices (Uint16 per pixel). A palette turns the
// indices into colours for one time of day; changing the time only re-maps the indices (about a
// millisecond per layer), the geometry is never repainted. The same trick gives the "far" version
// of a layer for the wave of distance: one more palette.

export const TAU = Math.PI * 2;
export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const fract = v => v - Math.floor(v);

// ---------------------------------------------------------------- randomness and noise

export function rng(seed) {
  let a = seed >>> 0;
  const f = () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  f.range = (lo, hi) => lo + (hi - lo) * f();
  f.int = (lo, hi) => Math.floor(lo + (hi - lo + 1) * f());
  f.pick = arr => arr[Math.floor(f() * arr.length)];
  f.chance = p => f() < p;
  f.gauss = () => (f() + f() + f() + f() - 2) / 1.15;
  return f;
}

export function hash2(x, y, s = 0) {
  let h = Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(s | 0, 1442695041);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

export function vnoise(x, y, s = 0) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

export function fbm(x, y, oct = 4, s = 0) {
  let amp = 0.5, fr = 1, sum = 0, norm = 0;
  for (let i = 0; i < oct; i++) { sum += amp * vnoise(x * fr, y * fr, s + i * 31); norm += amp; amp *= 0.5; fr *= 2.03; }
  return sum / norm;
}

// ridged noise: sharp crests, soft valleys (mountain ranges)
export function ridged(x, y, oct = 4, s = 0) {
  let amp = 0.5, fr = 1, sum = 0, norm = 0;
  for (let i = 0; i < oct; i++) { const n = 1 - Math.abs(vnoise(x * fr, y * fr, s + i * 31) * 2 - 1); sum += amp * n * n; norm += amp; amp *= 0.5; fr *= 2.1; }
  return sum / norm;
}

// 4x4 ordered dither threshold in [0,1)
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
export const bayer = (x, y) => (BAYER[(y & 3) * 4 + (x & 3)] + 0.5) / 16;

// ---------------------------------------------------------------- colour

export const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
export const mul3 = (a, b) => [a[0] * b[0], a[1] * b[1], a[2] * b[2]];
export const scale3 = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
export const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const lum = c => c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114;
export const hex = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
export const css = (c, a = 1) => a >= 1
  ? `rgb(${Math.round(clamp(c[0], 0, 255))},${Math.round(clamp(c[1], 0, 255))},${Math.round(clamp(c[2], 0, 255))})`
  : `rgba(${Math.round(clamp(c[0], 0, 255))},${Math.round(clamp(c[1], 0, 255))},${Math.round(clamp(c[2], 0, 255))},${a.toFixed(3)})`;
// little-endian RGBA packed for a Uint32 view over ImageData
export const pack = (c, a = 255) => ((a & 255) << 24 | (clamp(Math.round(c[2]), 0, 255) << 16) | (clamp(Math.round(c[1]), 0, 255) << 8) | clamp(Math.round(c[0]), 0, 255)) >>> 0;

// interpolate a list of [key, value...] keyframes (value arrays or numbers), smoothstepped
export function keyed(keys, k, i) {
  if (k <= keys[0][0]) return keys[0][i];
  for (let j = 0; j < keys.length - 1; j++) {
    const a = keys[j], b = keys[j + 1];
    if (k <= b[0]) {
      const t = smooth(0, 1, (k - a[0]) / (b[0] - a[0]));
      return Array.isArray(a[i]) ? mix3(a[i], b[i], t) : lerp(a[i], b[i], t);
    }
  }
  return keys[keys.length - 1][i];
}

// ---------------------------------------------------------------- canvases

export function makeCanvas(w, h) {
  const c = typeof document !== 'undefined' ? document.createElement('canvas') : new OffscreenCanvas(w, h);
  c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0);
  return c;
}
export const ctx2d = c => c.getContext('2d', { willReadFrequently: false });

// A soft additive glow, pre-blurred and stepped into a few rings so it sits with the pixel art
// instead of smearing over it. Drawn with 'lighter'.
const glowCache = new Map();
export function glowSprite(r, rgb, steps = 6, power = 1.6) {
  const key = r + ':' + rgb.join(',') + ':' + steps + ':' + power;
  let c = glowCache.get(key);
  if (c) return c;
  const n = r * 2 + 1;
  c = makeCanvas(n, n);
  const g = ctx2d(c), id = g.createImageData(n, n), U = new Uint32Array(id.data.buffer);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const d = Math.hypot(x - r, y - r) / (r + 0.5);
    let a = Math.pow(clamp(1 - d, 0, 1), power);
    a = Math.round(a * steps) / steps;
    if (a <= 0) continue;
    U[y * n + x] = pack(scale3(rgb, a), 255);
  }
  g.putImageData(id, 0, 0);
  glowCache.set(key, c);
  return c;
}

// ---------------------------------------------------------------- the indexed layer

// Index layout (Uint16): material (high byte, 0 = empty) | sun 0..7 (bits 5-7) | sky 0..3 (bits 3-4) | haze 0..7 (bits 0-2)
export const I = (mat, sun = 7, sky = 3, haze = 0) => (mat << 8) | (clamp(sun, 0, 7) << 5) | (clamp(sky, 0, 3) << 3) | clamp(haze, 0, 7);
export const iMat = i => i >> 8;
export const iSun = i => (i >> 5) & 7;
export const iSky = i => (i >> 3) & 3;
export const iHaze = i => i & 7;

export class IndexLayer {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.idx = new Uint16Array(w * h);
    this.used = null;
    this.maps = new Map(); // palette key -> canvas
  }
  set(x, y, v) { if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.idx[y * this.w + x] = v; }
  get(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h ? this.idx[y * this.w + x] : 0; }
  // the distinct indices actually painted (palettes are only evaluated for these)
  usedIndices() {
    if (this.used) return this.used;
    const seen = new Uint8Array(65536), out = [];
    for (let i = 0; i < this.idx.length; i++) { const v = this.idx[i]; if (v && !seen[v]) { seen[v] = 1; out.push(v); } }
    return (this.used = out);
  }
  // Remove lone pixels: a pixel that matches none of its 4 neighbours and whose material says it
  // may be cleaned takes the most common neighbour. Keeps clusters clean (no speckle).
  despeckle(mayClean, passes = 1) {
    const { w, h } = this;
    for (let p = 0; p < passes; p++) {
      const src = this.idx.slice();
      for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
        const i = y * w + x, v = src[i];
        if (!v || !mayClean(v)) continue;
        const a = src[i - 1], b = src[i + 1], c = src[i - w], d = src[i + w];
        if (a === v || b === v || c === v || d === v) continue;
        // most common neighbour (ties: left/right first: horizontal runs read cleaner)
        let best = a, bn = 0;
        for (const q of [a, b, c, d]) { const n = (q === a) + (q === b) + (q === c) + (q === d); if (n > bn) { bn = n; best = q; } }
        if (best && iMat(best) === iMat(v)) this.idx[i] = best;
      }
    }
    this.used = null;
  }
  // map through a palette function (index -> packed colour or 0), cached by key
  canvas(key, palFn) {
    let c = this.maps.get(key);
    if (c) return c;
    const lut = new Uint32Array(65536);
    for (const v of this.usedIndices()) lut[v] = palFn(v) >>> 0;
    c = makeCanvas(this.w, this.h);
    const g = ctx2d(c), id = g.createImageData(this.w, this.h), U = new Uint32Array(id.data.buffer), S = this.idx;
    for (let i = 0; i < S.length; i++) { const v = S[i]; if (v) U[i] = lut[v]; }
    g.putImageData(id, 0, 0);
    this.maps.set(key, c);
    if (this.maps.size > 6) this.maps.delete(this.maps.keys().next().value); // keep a few times of day
    return c;
  }
  // raw packed pixels for a palette (for per-pixel compositing such as the wave)
  pixels(palFn) {
    const lut = new Uint32Array(65536);
    for (const v of this.usedIndices()) lut[v] = palFn(v) >>> 0;
    const out = new Uint32Array(this.idx.length), S = this.idx;
    for (let i = 0; i < S.length; i++) { const v = S[i]; if (v) out[i] = lut[v]; }
    return out;
  }
}
