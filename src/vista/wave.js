// The wave of distance (遠化): a ring on the ground plane expanding from the plain under the sky
// shore. Every ground pixel knows its ground position (X, Z), so it knows when the ring reaches
// it; pixels are switched to their "far" colour (pale, flat, blue-grey) incrementally as the
// ring passes, with a bright pale front, and a curtain of motes rises from the front.

import { clamp, lerp, smooth, rng, vnoise, makeCanvas, ctx2d, mix3, pack } from './util.js';

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
   * @param o { w, h, X, Z, mask (Uint8, 1 = ground), Xc, Zc, R, f, cx, yl (camera: view axis, horizon row) }
   */
  constructor(o) {
    this.o = o;
    const { w, h, X, Z, mask } = o;
    const N = w * h, arr = new Uint8Array(N).fill(255), cnt = new Uint32Array(257);
    for (let i = 0; i < N; i++) {
      if (!mask[i]) continue;
      const d = Math.hypot(X[i] - o.Xc, Z[i] - o.Zc) / o.R;
      const jit = (vnoise(X[i] * 1.3, Z[i] * 1.3, 909) - 0.5) * 0.03 * smooth(20, 7, Z[i]);   // a ragged, not a compass-drawn, front (near only: no speckle far away)
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
  }
  arrivalOf(X, Z) { return waveAt(Math.hypot(X - this.o.Xc, Z - this.o.Zc) / this.o.R); }
  // (re)base on the current palettes: normal, far and front colours as packed pixel arrays
  base(key, normal, far) {
    this.key = key; this.normal = normal; this.far = far;
    this.front = new Uint32Array(far.length);
    const nf = this.o.noFront;
    for (let i = 0; i < far.length; i++) {
      const v = far[i];
      if (!v) continue;
      if (nf && nf[i]) { this.front[i] = v; continue; }     // houses do not light up as the front passes
      const r = v & 255, g = (v >> 8) & 255, b = (v >> 16) & 255;
      this.front[i] = pack(mix3([r, g, b], [222, 230, 250], 0.34));
    }
    this.U.set(normal);
    this.B = -1;
    this.dirty = [0, this.o.h - 1];
  }
  // advance to wave progress w (0..1); returns the composite canvas. Only the pixels that change are
  // touched, and only small rectangles around them are uploaded (blocks of 8 rows, their x extent).
  update(w) {
    const B = clamp(Math.floor(w * 250), -1, 254), nb = this.band;
    const { U, normal, far, front, start, cnt, list } = this;
    const W = this.o.w, H = this.o.h, NB = Math.ceil(H / 8);
    const bx0 = this.bx0 || (this.bx0 = new Int32Array(NB)), bx1 = this.bx1 || (this.bx1 = new Int32Array(NB));
    bx0.fill(W); bx1.fill(-1);
    const setRange = (a, b, src) => { // buckets a..b inclusive
      for (let k = Math.max(0, a); k <= Math.min(254, b); k++) {
        for (let j = start[k], e = start[k] + cnt[k]; j < e; j++) {
          const i = list[j]; U[i] = src[i];
          const y = (i / W) | 0, x = i - y * W, q = y >> 3;
          if (x < bx0[q]) bx0[q] = x; if (x > bx1[q]) bx1[q] = x;
        }
      }
    };
    if (B < this.B) { // scrubbed back: restore everything after B
      setRange(B + 1, this.B, normal);
      setRange(B - nb + 1, B, front);
    } else if (B > this.B) {
      setRange(Math.max(0, this.B - nb + 1), B - nb, far);      // left the bright front
      setRange(Math.max(this.B + 1, B - nb + 1), B, front);      // newly reached
    }
    this.B = B;
    if (this.dirty) { this.dirty = null; this.g.putImageData(this.img, 0, 0); return this.canvas; }
    for (let q = 0; q < NB; q++) {
      if (bx1[q] < bx0[q]) continue;
      const y0 = q * 8, hh = Math.min(8, H - y0);
      this.g.putImageData(this.img, 0, 0, bx0[q], y0, bx1[q] - bx0[q] + 1, hh);
    }
    return this.canvas;
  }
  // The front is a curtain of pale motes: born thick along the ground where the ring is passing,
  // they rise and drift toward the camera, thinning as they go. Each lives in the world (X, Z,
  // height) and is projected every frame, so near ones are bigger and faster; nearer ground hides
  // them. A faint glow lies along the foot of the curtain. Summed into an AddBuffer (same
  // coordinates as this layer).
  drawFront(AB, w, t, dt, alpha = 1) {
    const B = this.B, nb = this.band, { arr, start, cnt, list } = this, { w: W, h: H, Z, X, f, cx, yl } = this.o;
    if (B < 0) { this.motes.length = 0; return; }
    const R = this.R;
    let ns = 0;
    if (!this.strips) this.strips = new Uint32Array(4096);
    for (let k = Math.max(0, B - nb + 1); k <= B; k++) {
      for (let j = start[k], e = start[k] + cnt[k]; j < e; j++) {
        const i = list[j];
        const up = i - W;
        if (up >= 0 && arr[up] <= B && arr[up] > B - nb) continue; // not the top of its run
        if (ns === this.strips.length) { const n2 = new Uint32Array(ns * 2); n2.set(this.strips); this.strips = n2; }
        this.strips[ns++] = i;
      }
    }
    const strips = this.strips;
    // the foot of the curtain: a low glow, short
    for (let si = 0; si < ns; si++) {
      const i = strips[si], x = i % W, y = (i / W) | 0, z = Z[i];
      const hh = clamp(Math.round(f * 0.03 / z), 1, 8);
      AB.strip(x, y, hh, CURTAIN, clamp(alpha * (0.06 + 0.22 * smooth(22, 3, z)), 0, 1));
    }
    // new motes, many: the curtain is thick at its foot
    const want = Math.min(48, Math.round(ns * 0.05 * Math.min(2, dt * 60)) + 1);
    for (let n = 0; n < want && ns; n++) {
      const i = strips[Math.floor(R() * ns)], y = (i / W) | 0, z = Z[i];
      const hg = 1 - (y - yl) * z / f;                         // the ground's height there
      const life = 1.2 + R() * 2.6;
      this.motes.push({ X: X[i] + (R() - 0.5) * z * 0.004, Z: z * (1 - R() * 0.01), hg, H: R() * 0.004 * z,
        vH: (0.006 + R() * 0.02) * Math.sqrt(z), vZ: -(0.03 + R() * 0.06) * z, vX: (R() - 0.5) * 0.02 * z, life, age: 0 });
    }
    const keep = [], mc = MOTE;
    for (const m of this.motes) {
      m.age += dt; if (m.age >= m.life) continue;
      m.Z += m.vZ * dt; m.H += m.vH * dt; m.X += m.vX * dt;
      if (m.Z < 0.25) continue;
      keep.push(m);
      const x = cx + f * m.X / m.Z, y = yl + f * (1 - m.hg - m.H) / m.Z;
      const xi = Math.round(x), yi = Math.round(y);
      if (xi < 0 || yi < 0 || xi >= W || yi >= H) continue;
      const zg = Z[yi * W + xi];
      if (zg && zg < m.Z * 0.85) continue;                    // behind nearer ground
      const u = m.age / m.life, sz = f * 0.006 / m.Z;
      const a = alpha * smooth(0, 0.12, m.age) * Math.pow(1 - u, 1.3) * (0.35 + 0.65 * (1 - smooth(0, 0.6, u)));
      const big = sz > 1.2 ? (sz > 2.4 ? 3 : 2) : 1;
      AB.px(x - (big >> 1), y - (big >> 1), mc, a * (big > 1 ? 0.8 : 1), big, big);
    }
    this.motes = keep.length > 1600 ? keep.slice(-1600) : keep;
  }
}

const CURTAIN = [168, 184, 222], MOTE = [226, 234, 255];

