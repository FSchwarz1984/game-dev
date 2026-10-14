// The wave of distance (遠化): a ring on the ground plane expanding from the plain under the sky
// shore. Every ground pixel knows its ground position (X, Z), so it knows when the ring reaches
// it; pixels are switched to their "far" colour (pale, flat, blue-grey) incrementally as the
// ring passes, with a bright pale front, and a curtain of motes rises from the front.

import { clamp, lerp, smooth, rng, hash2, vnoise, makeCanvas, ctx2d, mix3, pack } from './util.js';

// radius (fraction of R) for wave progress w: creeping over the far plain, then rushing in
const RK = [[0, 0], [0.12, 0.07], [0.3, 0.27], [0.5, 0.56], [0.62, 0.74], [0.8, 0.9], [0.95, 0.985], [1, 1.04]];
export function radiusAt(w) {
  if (w <= 0) return 0;
  for (let i = 0; i < RK.length - 1; i++) if (w <= RK[i + 1][0]) { const [a, ra] = RK[i], [b, rb] = RK[i + 1]; return lerp(ra, rb, (w - a) / (b - a)); }
  return RK[RK.length - 1][1];
}
function waveAt(r) {
  if (r <= 0) return 0;
  for (let i = 0; i < RK.length - 1; i++) if (r <= RK[i + 1][1]) { const [a, ra] = RK[i], [b, rb] = RK[i + 1]; return lerp(a, b, (r - ra) / (rb - ra)); }
  return 1.01;
}

export class Wave {
  /**
   * @param o { w, h, X, Z, mask (Uint8, 1 = ground), Xc, Zc, R, f }
   */
  constructor(o) {
    this.o = o;
    const { w, h, X, Z, mask } = o;
    const N = w * h, arr = new Uint8Array(N).fill(255), cnt = new Uint32Array(257);
    for (let i = 0; i < N; i++) {
      if (!mask[i]) continue;
      const d = Math.hypot(X[i] - o.Xc, Z[i] - o.Zc) / o.R;
      const jit = (vnoise(X[i] * 1.3, Z[i] * 1.3, 909) - 0.5) * 0.03;   // a ragged, not a compass-drawn, front
      const a = clamp(Math.round((waveAt(d) + jit) * 250), 0, 254);
      arr[i] = a; cnt[a]++;
    }
    // bucket the pixel indices by arrival (counting sort)
    const start = new Uint32Array(256);
    for (let a = 1; a < 256; a++) start[a] = start[a - 1] + cnt[a - 1];
    const list = new Uint32Array(N), fill = start.slice();
    for (let i = 0; i < N; i++) if (arr[i] < 255) list[fill[arr[i]]++] = i;
    this.arr = arr; this.start = start; this.cnt = cnt; this.list = list;
    this.canvas = makeCanvas(w, h);
    this.g = ctx2d(this.canvas);
    this.img = this.g.createImageData(w, h);
    this.U = new Uint32Array(this.img.data.buffer);
    this.B = -1; this.key = null;
    this.motes = [];
    this.R = rng(977);
    this.band = 2; // buckets in the bright front
    this.curtain = curtainSprite();
  }
  arrivalOf(X, Z) { return waveAt(Math.hypot(X - this.o.Xc, Z - this.o.Zc) / this.o.R); }
  // (re)base on the current palettes: normal, far and front colours as packed pixel arrays
  base(key, normal, far) {
    this.key = key; this.normal = normal; this.far = far;
    this.front = new Uint32Array(far.length);
    for (let i = 0; i < far.length; i++) {
      const v = far[i];
      if (!v) continue;
      const r = v & 255, g = (v >> 8) & 255, b = (v >> 16) & 255;
      this.front[i] = pack(mix3([r, g, b], [214, 224, 246], 0.42));
    }
    this.U.set(normal);
    this.B = -1;
    this.dirty = [0, this.o.h - 1];
  }
  // advance to wave progress w (0..1); returns the composite canvas
  update(w) {
    const B = clamp(Math.floor(w * 250), -1, 254), nb = this.band;
    const { U, normal, far, front, start, cnt, list } = this;
    let y0 = 1e9, y1 = -1;
    const W = this.o.w;
    const setRange = (a, b, src) => { // buckets a..b inclusive
      for (let k = Math.max(0, a); k <= Math.min(254, b); k++) {
        for (let j = start[k], e = start[k] + cnt[k]; j < e; j++) { const i = list[j]; U[i] = src[i]; const y = (i / W) | 0; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      }
    };
    if (B < this.B) { // scrubbed back: restore everything after B
      setRange(B + 1, this.B, normal);
      setRange(B - nb + 1, B, front);
    } else if (B > this.B) {
      setRange(Math.max(0, this.B - nb + 1), B - nb, far);      // left the bright front
      setRange(Math.max(this.B + 1, B - nb + 1), B, front);      // newly reached
      if (this.B < B - nb) setRange(this.B + 1, B - nb, far);
    }
    this.B = B;
    if (this.dirty) { y0 = Math.min(y0, this.dirty[0]); y1 = Math.max(y1, this.dirty[1]); this.dirty = null; }
    if (y1 >= y0) this.g.putImageData(this.img, 0, 0, 0, y0, W, y1 - y0 + 1);
    return this.canvas;
  }
  // the curtain of pale motes rising from the front; occluded by anything nearer than the front
  drawFront(g, ox, oy, w, t, dt, alpha = 1) {
    const B = this.B, nb = this.band, { arr, start, cnt, list } = this, { w: W, Z, f } = this.o;
    if (B < 0) { this.motes.length = 0; return; }
    const R = this.R;
    // strips from the topmost front pixel of each run in a column
    const strips = [];
    for (let k = Math.max(0, B - nb + 1); k <= B; k++) {
      for (let j = start[k], e = start[k] + cnt[k]; j < e; j++) {
        const i = list[j];
        const up = i - W;
        if (up >= 0 && arr[up] <= B && arr[up] > B - nb) continue; // not the top of its run
        strips.push(i);
      }
    }
    const spr = this.curtain;
    g.globalCompositeOperation = 'lighter';
    for (const i of strips) {
      const x = i % W, y = (i / W) | 0, z = Z[i];
      const hx = vnoise(x * 0.11, t * 0.4, 17);                 // a curtain, not a comb: heights vary smoothly
      let hc = clamp((f * 0.2 / z) * (0.55 + 0.7 * hx), 2, 60);
      // stop at anything nearer than the front
      let top = y, lim = y - hc;
      while (top > lim && top > 0) { const zi = Z[(top - 1) * W + x]; if (zi && zi < z * 0.78) break; top--; }
      const hh = y - top;
      if (hh < 1) continue;
      const shimmer = 0.7 + 0.3 * Math.sin(t * 2.3 + x * 0.17);
      g.globalAlpha = clamp(alpha * shimmer * (0.22 + 0.26 * smooth(20, 2, z)), 0, 1);
      g.drawImage(spr, 0, 0, 1, 64, x + ox, top + oy, 1, hh + 1);
    }
    // motes: spawn on the front, rise, fade
    const want = Math.min(24, Math.round(strips.length * 0.025) + 1);
    for (let n = 0; n < want && strips.length; n++) {
      const i = strips[Math.floor(R() * strips.length)], x = i % W, y = (i / W) | 0, z = Z[i];
      const sc = clamp(f * 0.012 / z, 0.25, 4);
      this.motes.push({ x, y, vy: -(6 + 14 * R()) * sc, vx: (R() - 0.5) * 2 * sc, life: 0.8 + R() * 1.4, age: 0, big: sc > 1.6 && R() < 0.5 });
    }
    const keep = [];
    for (const m of this.motes) {
      m.age += dt; if (m.age >= m.life) continue;
      m.x += m.vx * dt; m.y += m.vy * dt;
      const a = alpha * (1 - m.age / m.life) * smooth(0, 0.15, m.age) * 0.75;
      g.globalAlpha = clamp(a, 0, 1);
      g.fillStyle = '#e6ecff';
      g.fillRect(Math.round(m.x + ox), Math.round(m.y + oy), m.big ? 2 : 1, m.big ? 2 : 1);
      keep.push(m);
    }
    this.motes = keep.length > 700 ? keep.slice(-700) : keep;
    g.globalAlpha = 1;
    g.globalCompositeOperation = 'source-over';
  }
}

function curtainSprite() {
  const c = makeCanvas(1, 64), g = ctx2d(c), id = g.createImageData(1, 64);
  for (let y = 0; y < 64; y++) {
    const u = y / 63; // 0 top .. 1 bottom
    const a = Math.pow(u, 2.2) * 0.9;
    const k = Math.round(a * 6) / 6; // stepped, like the glows
    id.data[y * 4] = Math.round(176 * k); id.data[y * 4 + 1] = Math.round(190 * k); id.data[y * 4 + 2] = Math.round(226 * k); id.data[y * 4 + 3] = 255;
  }
  g.putImageData(id, 0, 0);
  return c;
}
