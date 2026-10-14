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
   Foliage — sphere-lit sub-clumps with leaf cells.
   blobs: [{x, y, r, z}] in sprite px; z = how far the blob's centre
   stands toward the viewer (bigger = in front). Each pixel takes the
   blob whose sphere surface is nearest the viewer, lit from LIGHT, then
   broken into leaf cells (a hashed jittered grid of tiny domes) whose
   borders read as the gaps between leaves.
   o: {ramp, cell (px), mat, seed, lightK, ao (darkening where a blob
   is overlapped), rim (bright top-left rim), bulgeK, tone (offset),
   holes (0..1 chance of sky gaps near the edge), under (dark underside
   amount), only (fn(x,y) => bool)}
   --------------------------------------------------------------------- */
export function foliage(s, blobs, o = {}) {
  const rr = o.ramp, n = rr.length, cell = o.cell || 3.2, seed = o.seed || 1, mat = o.mat ?? MAT.LEAF;
  const L = o.light || LIGHT, bulgeK = o.bulgeK ?? 1, tone = o.tone || 0, under = o.under ?? 0.18;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const b of blobs) { x0 = Math.min(x0, b.x - b.r - 2); x1 = Math.max(x1, b.x + b.r + 2); y0 = Math.min(y0, b.y - b.r - 2); y1 = Math.max(y1, b.y + b.r + 2); }
  x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0)); x1 = Math.min(s.w - 1, Math.ceil(x1)); y1 = Math.min(s.h - 1, Math.ceil(y1));
  // bucket blobs on a coarse grid so each pixel only tests nearby blobs
  const G = 16, gw = Math.ceil((x1 - x0 + 1) / G) + 1, gh = Math.ceil((y1 - y0 + 1) / G) + 1, grid = Array.from({ length: gw * gh }, () => []);
  blobs.forEach((b, bi) => {
    const gx0 = Math.max(0, Math.floor((b.x - b.r - x0) / G)), gx1 = Math.min(gw - 1, Math.floor((b.x + b.r - x0) / G));
    const gy0 = Math.max(0, Math.floor((b.y - b.r - y0) / G)), gy1 = Math.min(gh - 1, Math.floor((b.y + b.r - y0) / G));
    for (let gy = gy0; gy <= gy1; gy++) for (let gx = gx0; gx <= gx1; gx++) grid[gy * gw + gx].push(bi);
  });
  if (!s.N) s.N = new Float32Array(s.w * s.h * 3);
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    if (o.only && !o.only(x, y)) continue;
    const list = grid[Math.floor((y - y0) / G) * gw + Math.floor((x - x0) / G)];
    let best = -1, bz = -1e9, second = -1e9, bdx = 0, bdy = 0, bh = 0;
    for (const bi of list) {
      const b = blobs[bi]; const dx = (x + 0.5 - b.x) / b.r, dy = (y + 0.5 - b.y) / b.r; const d2 = dx * dx + dy * dy;
      // ragged rim: leaf-sized bites out of the silhouette
      const edge = 1 - (hash2(Math.floor((x + 0.5) / cell * 1.3), Math.floor((y + 0.5) / cell * 1.3), seed + bi) < 0.45 ? 0.11 : 0);
      if (d2 > edge * edge) continue;
      const hgt = Math.sqrt(Math.max(0, 1 - d2)); const zz = b.z + hgt * b.r;
      if (zz > bz) { second = bz; bz = zz; best = bi; bdx = dx; bdy = dy; bh = hgt; } else if (zz > second) second = zz;
    }
    if (best < 0) continue;
    const b = blobs[best];
    // leaf cell: jittered grid cell nearest to the pixel
    const gx = (x + 0.5) / cell, gy = (y + 0.5) / (cell * 0.85); const cx = Math.floor(gx), cy = Math.floor(gy);
    let c1 = 1e9, c2 = 1e9, cid = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
      const qx = cx + i, qy = cy + j; const jx = qx + 0.15 + hash2(qx, qy, seed * 7) * 0.7, jy = qy + 0.15 + hash2(qx, qy, seed * 7 + 1) * 0.7;
      const d = (gx - jx) * (gx - jx) + (gy - jy) * (gy - jy);
      if (d < c1) { c2 = c1; c1 = d; cid = hashi32(qx, qy, seed); } else if (d < c2) c2 = d;
    }
    const cellH = Math.sqrt(Math.max(0, 1 - c1 * 1.4));
    const crack = Math.sqrt(c2) - Math.sqrt(c1) < 0.16;
    // normal: blob sphere tilted by the leaf cell dome
    let nx = bdx + (gx - (cx + 0.5)) * 0.25, ny = -bdy + 0.1 - (gy - (cy + 0.5)) * 0.25, nz = bh + 0.35 + cellH * 0.3;
    const nl = Math.hypot(nx, ny, nz); nx /= nl; ny /= nl; nz /= nl;
    let lit = nx * L[0] + ny * L[1] + nz * L[2];
    let t = 0.5 + lit * 0.62 + tone + ((cid & 255) / 255 - 0.5) * 0.16;
    t -= Math.max(0, bdy) * under;                  // undersides of blobs fall into shade
    if (second > -1e8 && bz - second < b.r * 0.35) t -= 0.12; // where blobs overlap: occluded crease
    if (crack) t -= 0.17;
    if (o.ao && bh < 0.35) t -= (0.35 - bh) * o.ao;
    const k = PX.ri(clamp(t, 0, 1), n, x, y, 0.55);
    s.px(x, y, rr[k], { z: bz, b: (b.z + bh * b.r) * bulgeK, m: mat, n: [nx, ny, nz] });
  }
}
function hashi32(x, y, s) { return Math.floor(hash2(x, y, s) * 4294967295) >>> 0; }

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
