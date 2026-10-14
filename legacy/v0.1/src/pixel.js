/* =====================================================================
   PIXEL — the procedural pixel-art kit. A sprite is painted into a
   buffer that carries, per pixel: colour, height (for normals), a
   material id, emission and "bulge" (how far the pixel stands toward
   the camera, used for per-pixel depth). Everything is then packed
   into two atlases: ALB (rgba) and NRM (normal.xy, bulge, material).
   Normals are camera-space: x right, y screen-up, z toward the viewer.
   ===================================================================== */
"use strict";
const MAT = {
  NONE: 0, GRASS: 1, SOIL: 2, ROCK: 3, PATH: 4, WATER: 5, LEAF: 6, BARK: 7, STONE: 8, MOSS: 9,
  SKIN: 10, FUR: 11, CLOTH: 12, PAPER: 13, METAL: 14, BLADE: 15, PETAL: 16, LAMP: 17, STRAW: 18,
  BAMBOO: 19, GHOST: 20, LACQUER: 21, GLASS: 22, WOOD: 23,
};
const BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const bayer = (x, y) => (BAYER4[(x & 3) + (y & 3) * 4] + .5) / 16;

class SB {
  constructor(w, h) {
    this.w = w; this.h = h; const n = w * h;
    this.c = new Uint8ClampedArray(n * 4); this.z = new Float32Array(n); this.m = new Uint8Array(n); this.e = new Uint8Array(n);
    this.b = new Float32Array(n); this.nx = null; // explicit normals (optional): Float32Array n*3
  }
  in(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h; }
  i(x, y) { return y * this.w + x; }
  a(x, y) { x |= 0; y |= 0; return this.in(x, y) ? this.c[(y * this.w + x) * 4 + 3] : 0; }
  col(x, y) { const k = (y * this.w + x) * 4; return [this.c[k], this.c[k + 1], this.c[k + 2]]; }
  // put a pixel. o: {z (height), m (material), e (emission 0..7), b (bulge px), keepZ}
  px(x, y, rgb, o = {}) {
    x |= 0; y |= 0; if (!this.in(x, y)) return; const i = y * this.w + x, k = i * 4;
    this.c[k] = rgb[0]; this.c[k + 1] = rgb[1]; this.c[k + 2] = rgb[2]; this.c[k + 3] = 255;
    if (o.z != null) this.z[i] = o.z; if (o.m != null) this.m[i] = o.m; if (o.e != null) this.e[i] = o.e; if (o.b != null) this.b[i] = o.b;
  }
  // only paint where the pixel is nearer (higher z) — lets overlapping clumps merge like real volume
  pz(x, y, rgb, z, o = {}) { x |= 0; y |= 0; if (!this.in(x, y)) return false; const i = y * this.w + x; if (this.c[i * 4 + 3] && this.z[i] > z) return false; o.z = z; this.px(x, y, rgb, o); return true; }
  clear(x, y) { x |= 0; y |= 0; if (!this.in(x, y)) return; const i = y * this.w + x; this.c[i * 4 + 3] = 0; this.z[i] = 0; this.m[i] = 0; }
  mul(x, y, k) { x |= 0; y |= 0; if (!this.in(x, y)) return; const q = (y * this.w + x) * 4; if (!this.c[q + 3]) return; this.c[q] *= k[0] ?? k; this.c[q + 1] *= k[1] ?? k; this.c[q + 2] *= k[2] ?? k; }
  // copy another buffer in at (ox,oy); z is offset by dz
  blit(s, ox, oy, o = {}) {
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) {
      const si = y * s.w + x; if (!s.c[si * 4 + 3]) continue; const tx = (o.flip ? s.w - 1 - x : x) + ox, ty = y + oy; if (!this.in(tx, ty)) continue;
      const ti = ty * this.w + tx; const z = s.z[si] + (o.dz || 0);
      if (o.depth && this.c[ti * 4 + 3] && this.z[ti] > z) continue;
      this.c[ti * 4] = s.c[si * 4]; this.c[ti * 4 + 1] = s.c[si * 4 + 1]; this.c[ti * 4 + 2] = s.c[si * 4 + 2]; this.c[ti * 4 + 3] = 255;
      this.z[ti] = z; this.m[ti] = s.m[si]; this.e[ti] = s.e[si]; this.b[ti] = s.b[si] + (o.db || 0);
      if (s.nx) { if (!this.nx) this.nx = new Float32Array(this.w * this.h * 3); this.nx[ti * 3] = s.nx[si * 3] * (o.flip ? -1 : 1); this.nx[ti * 3 + 1] = s.nx[si * 3 + 1]; this.nx[ti * 3 + 2] = s.nx[si * 3 + 2]; }
    }
  }
}

const PX = {
  // iterate a (noisy) ellipse; fn(x, y, u, v, d) with u,v in -1..1 and d = normalised radius
  ell(cx, cy, rx, ry, fn, o = {}) {
    const amp = o.amp || 0, seed = o.seed || 0, fr = o.freq || 2.2;
    for (let y = Math.floor(cy - ry - 2); y <= Math.ceil(cy + ry + 2); y++) for (let x = Math.floor(cx - rx - 2); x <= Math.ceil(cx + rx + 2); x++) {
      const u = (x + .5 - cx) / rx, v = (y + .5 - cy) / ry; let d = Math.sqrt(u * u + v * v);
      if (amp) { const a = Math.atan2(v, u); d -= (vnoise(Math.cos(a) * fr + 7, Math.sin(a) * fr + 3, seed) - .5) * amp + (hash2(x, y, seed) - .5) * amp * .35; }
      if (d <= 1) fn(x, y, u, v, d);
    }
  },
  // thick line / tapered stroke: fn(x, y, t, s) t along 0..1, s across -1..1
  stroke(x0, y0, x1, y1, w0, w1, fn) {
    const L = Math.max(1, hyp(x1 - x0, y1 - y0)), dx = (x1 - x0) / L, dy = (y1 - y0) / L;
    const minx = Math.floor(Math.min(x0, x1) - Math.max(w0, w1) - 1), maxx = Math.ceil(Math.max(x0, x1) + Math.max(w0, w1) + 1);
    const miny = Math.floor(Math.min(y0, y1) - Math.max(w0, w1) - 1), maxy = Math.ceil(Math.max(y0, y1) + Math.max(w0, w1) + 1);
    for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
      const px = x + .5 - x0, py = y + .5 - y0; const t = clamp((px * dx + py * dy) / L, 0, 1);
      const qx = x0 + dx * t * L, qy = y0 + dy * t * L; const d = hyp(x + .5 - qx, y + .5 - qy); const w = lerp(w0, w1, t);
      if (d <= w) fn(x, y, t, ((x + .5 - qx) * -dy + (y + .5 - qy) * dx) / Math.max(w, .01));
    }
  },
  // polygon fill (even-odd)
  poly(pts, fn) {
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const p of pts) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
    for (let y = Math.floor(y0); y <= Math.ceil(y1); y++) for (let x = Math.floor(x0); x <= Math.ceil(x1); x++) {
      const px = x + .5, py = y + .5; let ins = false;
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) { const a = pts[i], b = pts[j]; if ((a[1] > py) !== (b[1] > py) && px < (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]) ins = !ins; }
      if (ins) fn(x, y);
    }
  },
  // choose an index in a ramp from a continuous value, ordered-dithered at the band edges (keeps clusters clean)
  rampIdx(t, n, x, y, spread = .5) { const v = clamp(t, 0, .9999) * n + (bayer(x, y) - .5) * spread; return clamp(Math.floor(v), 0, n - 1); },
  // turn the height channel into camera-space normals (pixels without explicit normals)
  normals(s, k = 1, edge = 0) {
    const w = s.w, h = s.h, N = new Float32Array(w * h * 3);
    const Z = (x, y) => { if (x < 0 || y < 0 || x >= w || y >= h) return edge; const i = y * w + x; return s.c[i * 4 + 3] ? s.z[i] : edge; };
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue;
      if (s.nx && (s.nx[i * 3] || s.nx[i * 3 + 1] || s.nx[i * 3 + 2])) { N[i * 3] = s.nx[i * 3]; N[i * 3 + 1] = s.nx[i * 3 + 1]; N[i * 3 + 2] = s.nx[i * 3 + 2]; continue; }
      const dx = (Z(x + 1, y - 1) + 2 * Z(x + 1, y) + Z(x + 1, y + 1) - Z(x - 1, y - 1) - 2 * Z(x - 1, y) - Z(x - 1, y + 1)) / 8;
      const dy = (Z(x - 1, y + 1) + 2 * Z(x, y + 1) + Z(x + 1, y + 1) - Z(x - 1, y - 1) - 2 * Z(x, y - 1) - Z(x + 1, y - 1)) / 8;
      let nx = -dx * k, ny = dy * k, nz = 1; const l = hyp(nx, ny, nz); N[i * 3] = nx / l; N[i * 3 + 1] = ny / l; N[i * 3 + 2] = nz / l;
    }
    s.N = N; return N;
  },
  // selective outline: pixels on the silhouette darken toward a hue-shifted shadow of themselves
  selout(s, o = {}) {
    const w = s.w, h = s.h, k = o.k ?? .62, inner = o.inner ?? true, mask = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue;
      let edge = false; for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h || !s.c[(yy * w + xx) * 4 + 3]) edge = true; }
      if (edge && (!o.only || o.only(x, y, i))) mask[i] = 1;
    }
    if (inner) for (let i = 0; i < w * h; i++) if (mask[i]) { const q = i * 4; const c = [s.c[q], s.c[q + 1], s.c[q + 2]]; const [hh, ss, ll] = rgbToHsl(c[0], c[1], c[2]); const r = hslToRgb(hh + (o.hue ?? .03), Math.min(1, ss * 1.1), ll * k); s.c[q] = r[0]; s.c[q + 1] = r[1]; s.c[q + 2] = r[2]; }
  },
  // darken pixels that have opaque, nearer (higher z) neighbours above them — cheap baked occlusion inside a sprite
  ao(s, r = 3, k = .25) {
    const w = s.w, h = s.h, out = new Float32Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue; let occ = 0, n = 0;
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) { if (!dx && !dy) continue; const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue; const j = yy * w + xx; n++; if (s.c[j * 4 + 3] && s.z[j] > s.z[i] + 1.2) occ += Math.min(1, (s.z[j] - s.z[i]) / 6); }
      out[i] = n ? occ / n : 0;
    }
    for (let i = 0; i < w * h; i++) if (out[i] > 0) { const q = i * 4, m = 1 - out[i] * k * 2.2; s.c[q] *= m * .96; s.c[q + 1] *= m * .98; s.c[q + 2] *= m; }
  },
  canvasOf(s) { const cv = document.createElement("canvas"); cv.width = s.w; cv.height = s.h; const g = cv.getContext("2d"); const id = g.createImageData(s.w, s.h); id.data.set(s.c); g.putImageData(id, 0, 0); return cv; },
};

/* ---------------------------------------------------------------------
   ATLAS — shelf packer into a pair of RGBA8 pages (albedo + normal).
   rect: {x,y,w,h,u0,v0,u1,v1, ax, ay (anchor: base point in sprite px)}
   --------------------------------------------------------------------- */
const ATLAS = {
  W: 2048, H: 2048, alb: null, nrm: null, rects: {}, shelfs: [], tAlb: null, tNrm: null,
  init(W = 2048, H = 2048) { this.W = W; this.H = H; this.alb = new Uint8ClampedArray(W * H * 4); this.nrm = new Uint8ClampedArray(W * H * 4); this.rects = {}; this.shelfs = []; this.cx = 1; this.cy = 1; this.rowH = 0; },
  place(w, h) {
    // simple shelf packing, tall-first callers get good density
    for (const s of this.shelfs) if (h <= s.h && s.x + w + 1 <= this.W) { const r = { x: s.x, y: s.y }; s.x += w + 1; return r; }
    const y = this.shelfs.length ? this.shelfs[this.shelfs.length - 1].y + this.shelfs[this.shelfs.length - 1].h + 1 : 1;
    if (y + h + 1 > this.H) throw new Error("atlas full");
    const s = { x: 1 + w + 1, y, h }; this.shelfs.push(s); return { x: 1, y };
  },
  // add a finished sprite buffer; meta.ax/ay = anchor (the point that sits on the ground), default bottom-centre
  add(name, s, meta = {}) {
    if (!s.N) PX.normals(s, meta.nk ?? 1);
    const p = this.place(s.w, s.h), W = this.W;
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) {
      const i = y * s.w + x, k = i * 4; if (!s.c[k + 3]) continue; const t = ((p.y + y) * W + p.x + x) * 4;
      this.alb[t] = s.c[k]; this.alb[t + 1] = s.c[k + 1]; this.alb[t + 2] = s.c[k + 2]; this.alb[t + 3] = 255;
      this.nrm[t] = (s.N[i * 3] * .5 + .5) * 255; this.nrm[t + 1] = (s.N[i * 3 + 1] * .5 + .5) * 255;
      this.nrm[t + 2] = clamp(s.b[i] * 4, 0, 255); this.nrm[t + 3] = (s.m[i] & 31) | ((s.e[i] & 7) << 5);
    }
    const r = { x: p.x, y: p.y, w: s.w, h: s.h, u0: p.x / W, v0: p.y / this.H, u1: (p.x + s.w) / W, v1: (p.y + s.h) / this.H,
      ax: meta.ax ?? s.w / 2, ay: meta.ay ?? s.h, sway: meta.sway || 0, shadow: meta.shadow ?? 1, foot: meta.foot || 0, kind: meta.kind || "" };
    this.rects[name] = r; return r;
  },
  upload() {
    this.tAlb = GL.tex(this.W, this.H, new Uint8Array(this.alb.buffer));
    this.tNrm = GL.tex(this.W, this.H, new Uint8Array(this.nrm.buffer));
    // the CPU copies are only needed for collision masks of a few sprites; keep albedo, drop normals
    this.nrm = null;
  },
};

/* ---------------------------------------------------------------------
   PALETTE — the art direction in numbers. Summer cedar mountains under
   a shin-hanga sky: blue-green shadows, honeyed light, indigo dusk.
   --------------------------------------------------------------------- */
const PAL = {
  cedar: ramp("#2d4a3c", 7, { lo: .55, hi: .55, hueShift: .07 }),
  cedarDeep: ramp("#223a33", 5, { lo: .5, hi: .45 }),
  camphor: ramp("#557f37", 7, { lo: .55, hi: .5, hueShift: .08 }),
  camphorNew: ramp("#8fb04a", 5, { lo: .45, hi: .4 }),
  maple: ramp("#5f8f3c", 7, { lo: .55, hi: .5, hueShift: .07 }),
  bamboo: ramp("#6f9a45", 6, { lo: .5, hi: .45 }),
  bambooOld: ramp("#a39a55", 5, { lo: .45, hi: .4 }),
  bambooLeaf: ramp("#4f7f3b", 6, { lo: .5, hi: .5 }),
  barkCedar: ramp("#6b4330", 6, { lo: .55, hi: .45 }),
  barkGrey: ramp("#6c6359", 6, { lo: .55, hi: .45 }),
  wood: ramp("#7a6450", 6, { lo: .5, hi: .45 }),
  woodRed: ramp("#a8452e", 5, { lo: .5, hi: .4 }),
  stone: ramp("#73777a", 7, { lo: .55, hi: .5, hueShift: .04 }),
  stoneWarm: ramp("#7d766b", 6, { lo: .5, hi: .45 }),
  moss: ramp("#566f30", 6, { lo: .5, hi: .45 }),
  fern: ramp("#4f7c39", 6, { lo: .5, hi: .5 }),
  sasa: ramp("#4c7a34", 6, { lo: .5, hi: .45 }),
  kudzu: ramp("#4a7034", 6, { lo: .5, hi: .42, satShift: -.05 }),
  kudzuFlower: ramp("#9b4f9a", 4, { lo: .45, hi: .4 }),
  susuki: ramp("#8f9a5a", 5, { lo: .45, hi: .4 }),
  plume: ramp("#d9cdb0", 4, { lo: .35, hi: .3 }),
  lily: ramp("#efe9dc", 4, { lo: .3, hi: .2 }),
  straw: ramp("#b89a5c", 5, { lo: .5, hi: .4 }),
  paper: ramp("#ece4d2", 4, { lo: .3, hi: .2 }),
  soil: ramp("#6e523b", 6, { lo: .5, hi: .45 }),
  rust: ramp("#7b4a2c", 5, { lo: .5, hi: .4 }),
  metal: ramp("#5d6366", 5, { lo: .5, hi: .5 }),
  brick: ramp("#7d5144", 5, { lo: .5, hi: .4 }),
  water: ramp("#2f6a6e", 5, { lo: .5, hi: .4 }),
  // Tsuzura
  hair: ramp("#e2a743", 6, { lo: .55, hi: .5, hueShift: .06 }),
  hairTip: ramp("#6a3d1e", 4, { lo: .5, hi: .4 }),
  indigo: ramp("#2c3c6b", 6, { lo: .55, hi: .5, hueShift: .04 }),
  red: ramp("#c53a2b", 5, { lo: .5, hi: .4 }),
  skin: ramp("#f1d9bd", 5, { lo: .3, hi: .25, hueShift: .03 }),
  cream: ramp("#f3e7cf", 4, { lo: .3, hi: .2 }),
  legs: ramp("#3a2619", 4, { lo: .45, hi: .4 }),
  far: ramp("#9fb3d4", 5, { lo: .35, hi: .25 }),
};
