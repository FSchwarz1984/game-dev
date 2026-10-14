/* =====================================================================
   env/paint — the procedural pixel-art kit. A sprite is painted into an
   SB ("sprite buffer") that carries, per pixel: colour, height (z, used
   for normals), bulge (how far the pixel stands toward the camera, used
   for per-pixel depth), material id and emission. Normals are camera
   space: x right, y screen-up, z toward the viewer. Light convention for
   all baked shading: from the top-left (and a little from the front).
   Ported from legacy/v0.1/src/pixel.js; the foliage painter is new
   (sphere-lit sub-clumps + leaf cells on a hashed grid, O(pixels)).
   Pure JS: runs in the browser, in a Worker and in Node.
   ===================================================================== */
import { clamp, lerp, hyp, hash2, vnoise, bayer, rgbToHsl, hslToRgb, RNG } from './core.js';

export const MAT = {
  NONE: 0, GRASS: 1, SOIL: 2, ROCK: 3, PATH: 4, BED: 5, LEAF: 6, BARK: 7, STONE: 8, MOSS: 9,
  SKIN: 10, HAIR: 11, CLOTH: 12, PAPER: 13, METAL: 14, BLADE: 15, PETAL: 16, LAMP: 17, STRAW: 18,
  BAMBOO: 19, FAR: 20, LACQUER: 21, GLASS: 22, WOOD: 23, PLASTER: 24, ROPE: 25, FOOD: 26, WATER: 27,
  SNOW: 28, ROOT: 29, CHAR: 30,
};

/** light used for all baked shading (camera space, normalised): top-left, a little toward the viewer */
export const LIGHT = (() => { const v = [-0.55, 0.62, 0.56]; const l = Math.hypot(...v); return v.map(x => x / l); })();

export class SB {
  constructor(w, h) {
    this.w = w; this.h = h; const n = w * h;
    this.c = new Uint8ClampedArray(n * 4); this.z = new Float32Array(n); this.b = new Float32Array(n);
    this.m = new Uint8Array(n); this.e = new Uint8Array(n); this.N = null; // explicit normals Float32 n*3 (optional)
  }
  in(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h; }
  a(x, y) { x |= 0; y |= 0; return this.in(x, y) ? this.c[(y * this.w + x) * 4 + 3] : 0; }
  col(x, y) { const k = ((y | 0) * this.w + (x | 0)) * 4; return [this.c[k], this.c[k + 1], this.c[k + 2]]; }
  /** put a pixel. o: {z height, b bulge, m material, e emission 0..7, n [nx,ny,nz]} */
  px(x, y, rgb, o) {
    x |= 0; y |= 0; if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const i = y * this.w + x, k = i * 4;
    this.c[k] = rgb[0]; this.c[k + 1] = rgb[1]; this.c[k + 2] = rgb[2]; this.c[k + 3] = 255;
    if (o) {
      if (o.z != null) this.z[i] = o.z; if (o.b != null) this.b[i] = o.b; if (o.m != null) this.m[i] = o.m; if (o.e != null) this.e[i] = o.e;
      if (o.n) { if (!this.N) this.N = new Float32Array(this.w * this.h * 3); this.N[i * 3] = o.n[0]; this.N[i * 3 + 1] = o.n[1]; this.N[i * 3 + 2] = o.n[2]; }
      else if (this.N) { this.N[i * 3] = 0; this.N[i * 3 + 1] = 0; this.N[i * 3 + 2] = 0; }
    }
  }
  /** paint only where nearer (higher z) — overlapping clumps merge like real volume */
  pz(x, y, rgb, z, o = {}) {
    x |= 0; y |= 0; if (x < 0 || y < 0 || x >= this.w || y >= this.h) return false;
    const i = y * this.w + x; if (this.c[i * 4 + 3] && this.z[i] > z) return false;
    o.z = z; this.px(x, y, rgb, o); return true;
  }
  clear(x, y) { x |= 0; y |= 0; if (!this.in(x, y)) return; const i = y * this.w + x; this.c[i * 4 + 3] = 0; this.z[i] = 0; this.m[i] = 0; this.e[i] = 0; this.b[i] = 0; }
  mul(x, y, k) {
    x |= 0; y |= 0; if (!this.in(x, y)) return; const q = (y * this.w + x) * 4; if (!this.c[q + 3]) return;
    if (typeof k === 'number') { this.c[q] *= k; this.c[q + 1] *= k; this.c[q + 2] *= k; }
    else { this.c[q] *= k[0]; this.c[q + 1] *= k[1]; this.c[q + 2] *= k[2]; }
  }
  /** copy another buffer in at (ox, oy); z += dz, b += db; o.depth = z-test; o.flip = mirror */
  blit(s, ox, oy, o = {}) {
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) {
      const si = y * s.w + x; if (!s.c[si * 4 + 3]) continue;
      const tx = (o.flip ? s.w - 1 - x : x) + ox, ty = y + oy; if (!this.in(tx, ty)) continue;
      const ti = ty * this.w + tx, z = s.z[si] + (o.dz || 0);
      if (o.depth && this.c[ti * 4 + 3] && this.z[ti] > z) continue;
      this.c[ti * 4] = s.c[si * 4]; this.c[ti * 4 + 1] = s.c[si * 4 + 1]; this.c[ti * 4 + 2] = s.c[si * 4 + 2]; this.c[ti * 4 + 3] = 255;
      this.z[ti] = z; this.m[ti] = s.m[si]; this.e[ti] = s.e[si]; this.b[ti] = s.b[si] + (o.db || 0);
      if (s.N) {
        if (!this.N) this.N = new Float32Array(this.w * this.h * 3);
        this.N[ti * 3] = s.N[si * 3] * (o.flip ? -1 : 1); this.N[ti * 3 + 1] = s.N[si * 3 + 1]; this.N[ti * 3 + 2] = s.N[si * 3 + 2];
      } else if (this.N) { this.N[ti * 3] = this.N[ti * 3 + 1] = this.N[ti * 3 + 2] = 0; }
    }
  }
  /** bounding box of opaque pixels */
  bbox() {
    let x0 = this.w, y0 = this.h, x1 = -1, y1 = -1;
    for (let y = 0; y < this.h; y++) for (let x = 0; x < this.w; x++) if (this.c[(y * this.w + x) * 4 + 3]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    return x1 < 0 ? null : { x0, y0, x1, y1 };
  }
}

/* ---------------------------------------------------------------------
   Shapes and strokes
   --------------------------------------------------------------------- */
export const PX = {
  /** noisy ellipse; fn(x, y, u, v, d) with u,v in -1..1 and d the normalised radius */
  ell(cx, cy, rx, ry, fn, o = {}) {
    const amp = o.amp || 0, seed = o.seed || 0, fr = o.freq || 2.2;
    for (let y = Math.floor(cy - ry - 2); y <= Math.ceil(cy + ry + 2); y++) for (let x = Math.floor(cx - rx - 2); x <= Math.ceil(cx + rx + 2); x++) {
      const u = (x + 0.5 - cx) / rx, v = (y + 0.5 - cy) / ry; let d = Math.sqrt(u * u + v * v);
      if (amp) { const a = Math.atan2(v, u); d -= (vnoise(Math.cos(a) * fr + 7, Math.sin(a) * fr + 3, seed) - 0.5) * amp + (hash2(x, y, seed) - 0.5) * amp * 0.35; }
      if (d <= 1) fn(x, y, u, v, d);
    }
  },
  /** tapered stroke: fn(x, y, t along 0..1, s across -1..1) */
  stroke(x0, y0, x1, y1, w0, w1, fn) {
    const L = Math.max(1e-3, hyp(x1 - x0, y1 - y0)), dx = (x1 - x0) / L, dy = (y1 - y0) / L, W = Math.max(w0, w1);
    const minx = Math.floor(Math.min(x0, x1) - W - 1), maxx = Math.ceil(Math.max(x0, x1) + W + 1);
    const miny = Math.floor(Math.min(y0, y1) - W - 1), maxy = Math.ceil(Math.max(y0, y1) + W + 1);
    for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
      const px = x + 0.5 - x0, py = y + 0.5 - y0; const t = clamp((px * dx + py * dy) / L, 0, 1);
      const qx = x0 + dx * t * L, qy = y0 + dy * t * L; const d = hyp(x + 0.5 - qx, y + 0.5 - qy); const w = lerp(w0, w1, t);
      if (d <= w) fn(x, y, t, ((x + 0.5 - qx) * -dy + (y + 0.5 - qy) * dx) / Math.max(w, 0.01));
    }
  },
  /** stroke along a polyline with widths per point; fn(x, y, t, s, segIndex) */
  path(pts, widths, fn) {
    let total = 0; const segs = [];
    for (let i = 0; i < pts.length - 1; i++) { const L = hyp(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]); segs.push(L); total += L; }
    let acc = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const t0 = acc / total, t1 = (acc + segs[i]) / total; acc += segs[i];
      PX.stroke(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], widths[i], widths[i + 1], (x, y, t, s) => fn(x, y, lerp(t0, t1, t), s, i));
    }
  },
  /** polygon fill (even-odd) */
  poly(pts, fn) {
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const p of pts) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
    for (let y = Math.floor(y0); y <= Math.ceil(y1); y++) {
      const py = y + 0.5; const xs = [];
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const a = pts[i], b = pts[j];
        if ((a[1] > py) !== (b[1] > py)) xs.push((b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]);
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2) for (let x = Math.ceil(xs[k] - 0.5); x <= Math.floor(xs[k + 1] - 0.5); x++) fn(x, y);
    }
  },
  rect(x0, y0, x1, y1, fn) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) fn(x, y); },
  /** ramp index from a continuous value, ordered-dithered at band edges (keeps clusters clean) */
  ri(t, n, x, y, spread = 0.5) { const v = clamp(t, 0, 0.9999) * n + (bayer(x, y) - 0.5) * spread; return clamp(Math.floor(v), 0, n - 1); },
  /** pick a colour from a ramp with dithered band edges */
  rc(ramp, t, x, y, spread = 0.5) { return ramp[PX.ri(t, ramp.length, x, y, spread)]; },
};

/* ---------------------------------------------------------------------
   Foliage masses. A mass is one clump of leaves lit as a single form
   (an ellipsoid, optionally drooping at the ends); leaf cells (a hashed
   jittered grid of small domes) only add texture, cracks between leaves
   and a scalloped, leaf-shaped silhouette. Lighting the mass rather than
   every little blob is what separates painted foliage from a pile of
   lit balls (the "voxel-ball trees" the owner rejected).
   m: {x, y, rx, ry, z, droop (ends hang by droop*ry*u^2), tilt}
   o: {ramp, cell, seed, mat, tone, under (shade the lower part), rim,
       spread (dither), bulgeK, light, cellK (texture strength), only,
       blobK (flat tone offset per leaf cell: band edges become leaf-cluster
       shapes instead of tiles), gapW (dark crack between cells, 0 = none)}
   --------------------------------------------------------------------- */
export function mass(s, m, o = {}) {
  const rr = o.ramp, n = rr.length, cell = o.cell || 3.2, seed = (o.seed || 1) * 7 + (m.seed || 0), mat = o.mat ?? MAT.LEAF;
  const L = o.light || LIGHT, tone = (o.tone || 0) + (m.tone || 0), under = o.under ?? 0.35, cellK = o.cellK ?? 0.38, bulgeK = o.bulgeK ?? 1;
  const droop = m.droop || 0, tilt = m.tilt || 0, ct = Math.cos(tilt), st = Math.sin(tilt);
  const x0 = Math.max(0, Math.floor(m.x - m.rx - cell * 2)), x1 = Math.min(s.w - 1, Math.ceil(m.x + m.rx + cell * 2));
  const y0 = Math.max(0, Math.floor(m.y - m.ry - cell * 2)), y1 = Math.min(s.h - 1, Math.ceil(m.y + m.ry + Math.abs(droop) * m.ry + cell * 2));
  if (!s.N) s.N = new Float32Array(s.w * s.h * 3);
  const local = (px, py) => { const dx = px - m.x, dy = py - m.y; const ux = (dx * ct + dy * st) / m.rx; let vy = (-dx * st + dy * ct); vy = (vy - droop * m.ry * ux * ux) / m.ry; return [ux, vy]; };
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    if (o.only && !o.only(x, y)) continue;
    // nearest leaf cell
    const gx = (x + 0.5) / cell, gy = (y + 0.5) / (cell * 0.82), cx = Math.floor(gx), cy = Math.floor(gy);
    let c1 = 1e9, c2 = 1e9, ccx = 0, ccy = 0, cid = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
      const qx = cx + i, qy = cy + j; const h = hash2(qx, qy, seed);
      const jx = qx + 0.18 + h * 0.64, jy = qy + 0.18 + hash2(qx, qy, seed + 1) * 0.64;
      const d = (gx - jx) * (gx - jx) + (gy - jy) * (gy - jy);
      if (d < c1) { c2 = c1; c1 = d; ccx = jx * cell; ccy = jy * cell * 0.82; cid = h; } else if (d < c2) c2 = d;
    }
    const [u, v] = local(x + 0.5, y + 0.5); const r2 = u * u + v * v;
    const [cu, cv] = local(ccx, ccy); const rc2 = cu * cu + cv * cv;
    // silhouette: interior pixels, plus the leaf-shaped cells whose centre lies inside
    if (r2 > 1) { if (rc2 > 0.98 || c1 > 0.28) continue; }
    else if (r2 > 0.8 && rc2 > 1.06) continue;
    const dome = Math.sqrt(Math.max(0, 1 - Math.min(1, r2)));
    const cellH = Math.sqrt(Math.max(0, 1 - c1 * 2.2));
    // normal: the mass ellipsoid (blended toward a shared group form, so a crown lobe reads as one volume), tilted by the leaf cell
    let nx = u * 0.9, ny = -v * 0.9 + 0.12, nz = dome + 0.25;
    if (o.group) { const G = o.group, gu = (x + 0.5 - G.x) / G.rx, gv = (y + 0.5 - G.y) / G.ry, gd = Math.sqrt(Math.max(0, 1 - Math.min(1, gu * gu + gv * gv))), k = G.k ?? 0.6;
      nx = nx * (1 - k) + gu * 0.9 * k; ny = ny * (1 - k) + (-gv * 0.9 + 0.12) * k; nz = nz * (1 - k) + (gd + 0.25) * k; }
    const lx = (x + 0.5 - ccx) / cell, ly = (y + 0.5 - ccy) / cell; nx += lx * cellK; ny -= ly * cellK; nz += cellH * cellK * 0.6;
    const nl = Math.hypot(nx, ny, nz); nx /= nl; ny /= nl; nz /= nl;
    const lit = nx * L[0] + ny * L[1] + nz * L[2];
    let t = (o.base ?? 0.36) + lit * (o.litK ?? 0.5) + tone + (cid - 0.5) * (o.blobK ?? 0.12);
    if (v > 0.25) t -= (v - 0.25) * under;           // the underside falls into shade
    if (Math.sqrt(c2) - Math.sqrt(c1) < (o.gapW ?? 0.13)) t -= 0.13; // gaps between leaves
    if (o.rim && r2 > 0.55 && v < -0.2 && u < 0.3) t += o.rim; // sun on the upper rim
    const k = PX.ri(clamp(t, 0, 1), n, x, y, o.spread ?? 0.35);
    const z = (m.z || 0) + dome * Math.min(m.rx, m.ry) * (o.zk ?? 0.8) + cellH * 0.8;
    s.pz(x, y, rr[k], z, { m: mat, b: z * bulgeK, n: [nx, ny, nz] });
  }
}
/** A broadleaf crown: one leafy volume — a darker core (what shows in the crevices), then big
    overlapping bulges (young growth on the top row, the broadest in front and below), lit mostly as
    the whole crown and a little as themselves, with flat leaf-cluster tone blobs (band edges break
    into leaf shapes, never tiles or checkerboards), a fringe tucked under the lowest edge and a few
    sky gaps. o: {x, y (crown centre), w, h, ramp, young, seed, tone, z0, fringe, gaps, cell} */
export function crown(s, o) {
  const R = RNG((o.seed || 1) * 41 + 3), rr = o.ramp, young = o.young || rr, w = o.w, h = o.h, cx = o.x, cy = o.y, z0 = o.z0 || 0;
  const cell = o.cell ?? (w > 150 ? 4.4 : w > 80 ? 3.6 : 3);
  const group = { x: cx - w * 0.06, y: cy - h * 0.06, rx: w * 0.56, ry: h * 0.62, k: o.groupK ?? 0.84 };
  mass(s, { x: cx, y: cy + h * 0.06, rx: w * 0.47, ry: h * 0.44, z: z0, droop: 0.12, seed: 99 }, { ramp: rr, cell: cell * 0.95, seed: o.seed * 3 + 7, tone: (o.tone || 0) - 0.12, under: 0.5, cellK: 0.12, blobK: 0.26, gapW: 0.04, group, base: 0.3, litK: 0.5, zk: 0.3 });
  const cl = [];
  for (let r = 0; r < 3; r++) {
    const t = r / 2;                                   // 0 the top (back) → 1 the bottom (front)
    const rad = w * (0.15 + t * 0.05) * R.range(0.95, 1.08);
    const yy = cy + h * (-0.24 + t * 0.44);
    const half = w * (0.3 + t * 0.12);
    const n = r === 0 ? (w > 205 ? 3 : 2) : r === 1 ? 3 + (w > 225 ? 1 : 0) : 3;
    for (let i = 0; i < n; i++) {
      const f = n === 1 ? 0 : i / (n - 1) * 2 - 1;
      const x = cx + f * half + R.range(-rad * 0.18, rad * 0.18), y = yy + f * f * h * 0.07 + R.range(-rad * 0.12, rad * 0.12);
      const rx = rad * R.range(0.9, 1.12), ry = rx * R.range(0.66, 0.78);
      cl.push({ x, y, rx, ry, z: z0 + 10 + t * 30 + (1 - Math.abs(f)) * 6 + R.range(0, 3), droop: R.range(0.08, 0.22), seed: r * 16 + i, tone: (r === 0 ? 0.03 : 0) + R.range(-0.025, 0.025), top: r === 0 });
    }
  }
  cl.sort((a, b) => a.z - b.z);
  for (const m of cl) mass(s, m, { ramp: m.top ? young : rr, cell, seed: o.seed * 3, tone: (o.tone || 0) - 0.02, under: 0.32, rim: 0.03, cellK: 0.16, blobK: 0.36, gapW: 0.06, group, base: o.base ?? 0.37, litK: o.litK ?? 0.62, zk: 0.45 });
  if (o.fringe !== false) { // tucked up under the crown's own lowest edge, so it hangs from it
    const nf = Math.round(w / 20);
    for (let k = 0; k < nf; k++) {
      const x = Math.round(cx + R.range(-w * 0.42, w * 0.42)); let yb = -1; for (let y = Math.min(s.h - 1, Math.ceil(cy + h)); y >= 0; y--) if (s.a(x, y)) { yb = y; break; }
      if (yb < 0) continue;
      mass(s, { x, y: yb - 1, rx: R.range(0.025, 0.045) * w + 2, ry: R.range(3, 5), z: z0 + 46, droop: 0.5, seed: 40 + k, tone: -0.1 }, { ramp: rr, cell: cell * 0.8, seed: o.seed * 3 + 1, under: 1.1, rim: 0.0, base: 0.3, litK: 0.4, blobK: 0.2, gapW: 0.04 });
    }
  }
  const ng = o.gaps ?? Math.round(w / 40);
  for (let k = 0; k < ng; k++) { const a = R.range(Math.PI * 1.05, Math.PI * 1.95), d = R.range(0.6, 0.85); const gx = cx + Math.cos(a) * w * 0.42 * d, gy = cy + Math.sin(a) * h * 0.5 * d; const r = R.range(1.2, 2.6) * Math.min(1, w / 120 + 0.4);
    for (let y = Math.floor(gy - r); y <= gy + r; y++) for (let x = Math.floor(gx - r); x <= gx + r; x++) if (hyp(x - gx, (y - gy) * 1.3) < r) s.clear(x, y); }
}

/** compatibility: a list of round blobs becomes masses */
export function foliage(s, blobs, o = {}) { for (const b of blobs) mass(s, { x: b.x, y: b.y, rx: b.r, ry: b.r * 0.92, z: b.z }, o); }

/** cluster of blobs on a dome — convenience for crowns and bushes */
export function domeBlobs(cx, cy, rx, ry, count, rMin, rMax, seed, o = {}) {
  const R = RNG(seed), out = [];
  for (let i = 0; i < count; i++) {
    const a = R() * Math.PI * 2, rr = Math.sqrt(R()) * (o.spread ?? 0.82);
    const x = cx + Math.cos(a) * rr * rx, y = cy + Math.sin(a) * rr * ry * (o.flat ?? 1) - (o.lift || 0) * (1 - rr) * ry;
    const r = lerp(rMin, rMax, R()) * (1 - rr * (o.shrink ?? 0.25));
    out.push({ x, y, r, z: (1 - rr) * (o.zk ?? 0.6) * Math.min(rx, ry) + (o.z0 || 0) + R() * 2 - (y - cy) * (o.tilt ?? 0.15) });
  }
  return out;
}

/* ---------------------------------------------------------------------
   Post-processing of a painted sprite
   --------------------------------------------------------------------- */
export const POST = {
  /** height field → camera-space normals for pixels without explicit ones */
  normals(s, k = 1, edge = 0) {
    const w = s.w, h = s.h, N = s.N || (s.N = new Float32Array(w * h * 3));
    const Z = (x, y) => { if (x < 0 || y < 0 || x >= w || y >= h) return edge; const i = y * w + x; return s.c[i * 4 + 3] ? s.z[i] : edge; };
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue;
      if (N[i * 3] || N[i * 3 + 1] || N[i * 3 + 2]) continue;
      const dx = (Z(x + 1, y - 1) + 2 * Z(x + 1, y) + Z(x + 1, y + 1) - Z(x - 1, y - 1) - 2 * Z(x - 1, y) - Z(x - 1, y + 1)) / 8;
      const dy = (Z(x - 1, y + 1) + 2 * Z(x, y + 1) + Z(x + 1, y + 1) - Z(x - 1, y - 1) - 2 * Z(x, y - 1) - Z(x + 1, y - 1)) / 8;
      const nx = -dx * k, ny = dy * k, nz = 1, l = Math.hypot(nx, ny, nz);
      N[i * 3] = nx / l; N[i * 3 + 1] = ny / l; N[i * 3 + 2] = nz / l;
    }
    return N;
  },
  /** selective outline: silhouette pixels darken toward a hue-shifted shadow of themselves.
      o.k darkness, o.hue shift, o.only(x,y,i) filter, o.bottomK extra on the lower-right edge */
  outline(s, o = {}) {
    const w = s.w, h = s.h, k = o.k ?? 0.62, mask = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue;
      let e = 0;
      if (x + 1 >= w || !s.c[(i + 1) * 4 + 3]) e |= 1; if (x - 1 < 0 || !s.c[(i - 1) * 4 + 3]) e |= 2;
      if (y + 1 >= h || !s.c[(i + w) * 4 + 3]) e |= 4; if (y - 1 < 0 || !s.c[(i - w) * 4 + 3]) e |= 8;
      if (e && (!o.only || o.only(x, y, i))) mask[i] = e;
    }
    for (let i = 0; i < w * h; i++) if (mask[i]) {
      const q = i * 4; const [hh, ss, ll] = rgbToHsl(s.c[q], s.c[q + 1], s.c[q + 2]);
      // lower/right edges (away from the light) darker than upper/left
      const away = (mask[i] & 1) || (mask[i] & 4) ? 1 : 0;
      const kk = away ? k * (o.awayK ?? 0.92) : Math.min(1, k * (o.towardK ?? 1.18));
      const r = hslToRgb(hh + (o.hue ?? 0.03), Math.min(1, ss * 1.12), ll * kk); s.c[q] = r[0]; s.c[q + 1] = r[1]; s.c[q + 2] = r[2];
    }
  },
  /** darken pixels overlapped by nearer (higher z) neighbours — baked occlusion */
  ao(s, r = 3, k = 0.25) {
    const w = s.w, h = s.h, out = new Float32Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x; if (!s.c[i * 4 + 3]) continue; let occ = 0, n = 0;
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        if (!dx && !dy) continue; const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const j = yy * w + xx; n++; if (s.c[j * 4 + 3] && s.z[j] > s.z[i] + 1.2) occ += Math.min(1, (s.z[j] - s.z[i]) / 6);
      }
      out[i] = n ? occ / n : 0;
    }
    for (let i = 0; i < w * h; i++) if (out[i] > 0) { const q = i * 4, m = 1 - out[i] * k * 2.2; s.c[q] *= m * 0.96; s.c[q + 1] *= m * 0.98; s.c[q + 2] *= m; }
  },
  /** run the usual finish: occlusion, outline, normals */
  finish(s, o = {}) {
    if (o.ao !== false) POST.ao(s, o.aoR ?? 2, o.aoK ?? 0.22);
    if (o.outline !== false) POST.outline(s, Object.assign({ k: 0.66 }, o.outlineOpts || {}));
    POST.normals(s, o.nk ?? 1);
    return s;
  },
};

/* ---------------------------------------------------------------------
   Small helpers used by many painters
   --------------------------------------------------------------------- */
/** shade a box face pixel from its face normal (camera space) → ramp t */
export function faceT(n, base = 0.5, k = 0.45) { return base + (n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]) * k; }
/** cylinder normal across a vertical stroke: sx in -1..1 */
export function cylN(sx, tiltY = 0) { const nz = Math.sqrt(Math.max(0, 1 - sx * sx)); const l = Math.hypot(sx, tiltY, nz) || 1; return [sx / l, tiltY / l, nz / l]; }
