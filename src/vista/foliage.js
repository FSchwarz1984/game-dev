// The great camphor, close up. Leaf clumps are shaded as soft volumes in four clean bands; the
// band boundaries and the outline follow a cellular "leaf" pattern (cells of 3-4 px), so every
// boundary is made of whole leaves, never single-pixel speckle. Overlapping clumps cast a contact
// shadow on the ones behind; edges facing the light get a rim. Limbs are bark cylinders with
// fissures and moss. Painted once into an IndexLayer; palettes give the time of day.

import { clamp, lerp, smooth, rng, hash2, vnoise, IndexLayer, I, iMat } from './util.js';

export const F = { deep: 1, leaf: 2, young: 3, rim: 4, glint: 5, bark: 6, moss: 7, twig: 8, dark: 9 };
export const FOLIAGE_MATS = [];
FOLIAGE_MATS[F.deep] = { albedo: [0.12, 0.17, 0.1], ambK: 0.75, sunK: 0.5 };
FOLIAGE_MATS[F.leaf] = { albedo: [0.25, 0.33, 0.15], ambK: 1, sunK: 1 };
FOLIAGE_MATS[F.young] = { albedo: [0.34, 0.39, 0.17], ambK: 1, sunK: 1 };
FOLIAGE_MATS[F.rim] = { albedo: [0.3, 0.38, 0.2], rim: true, rimK: 0.5, warmRim: 0.7 };
FOLIAGE_MATS[F.glint] = { albedo: [0.33, 0.41, 0.21], ambK: 1.0, sunK: 1.3, gloss: 0.25 };
FOLIAGE_MATS[F.bark] = { albedo: [0.23, 0.22, 0.21], ambK: 1, sunK: 0.95 };
FOLIAGE_MATS[F.moss] = { albedo: [0.3, 0.35, 0.17], ambK: 1, sunK: 0.95 };
FOLIAGE_MATS[F.twig] = { albedo: [0.28, 0.25, 0.21], ambK: 1, sunK: 0.8 };
FOLIAGE_MATS[F.dark] = { albedo: [0.06, 0.08, 0.06], ambK: 0.5, sunK: 0.2 };

// sun bits for the four bands (deep shadow, shadow, mid, light) and a highlight
const BAND_SUN = [0, 2, 4, 6], HI_SUN = 7;

// cellular leaf pattern: id and value of the nearest jittered point, cells ~cs px (cached by size)
const CELL_CACHE = new Map();
function leafCells(w, h, cs, seed) {
  const key = w + 'x' + h + ':' + cs + ':' + seed;
  let c = CELL_CACHE.get(key);
  if (!c) { c = leafCellsRaw(w, h, cs, seed); CELL_CACHE.set(key, c); if (CELL_CACHE.size > 4) CELL_CACHE.delete(CELL_CACHE.keys().next().value); }
  return c;
}
function leafCellsRaw(w, h, cs, seed) {
  const val = new Float32Array(w * h), edge = new Uint8Array(w * h);
  const cy = cs * 0.8;                                   // leaves lie wider than tall
  const gw = Math.ceil(w / cs) + 3, gh = Math.ceil(h / cy) + 3;
  const PX = new Float64Array(gw * gh), PY = new Float64Array(gw * gh), PV = new Float64Array(gw * gh);
  for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
    const k = j * gw + i;
    PX[k] = (i - 1 + 0.1 + hash2(i, j, seed) * 0.8) * cs;
    PY[k] = (j - 1 + 0.1 + hash2(i, j, seed + 1) * 0.8) * cy;
    PV[k] = hash2(i, j, seed + 2);
  }
  const id = new Int32Array(w * h);
  for (let y = 0; y < h; y++) {
    const cj = Math.floor(y / cy) + 1, yy = y + 0.5;
    for (let x = 0; x < w; x++) {
      const ci = Math.floor(x / cs) + 1, xx = x + 0.5;
      let best = 1e18, bk = 0;
      for (let j = cj - 1; j <= cj + 1; j++) {
        const row = j * gw;
        for (let i = ci - 1; i <= ci + 1; i++) {
          const k = row + i, dx = xx - PX[k], dy = (yy - PY[k]) * 1.25, d = dx * dx + dy * dy;
          if (d < best) { best = d; bk = k; }
        }
      }
      const o = y * w + x;
      val[o] = PV[bk]; id[o] = bk;
    }
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    edge[i] = (x + 1 < w && id[i + 1] !== id[i]) || (y + 1 < h && id[i + w] !== id[i]) ? 1 : 0;
  }
  return { val, edge, id };
}

/**
 * Paint a canopy into an IndexLayer.
 * spec: { clumps: [{x,y,rx,ry,z,young?,lobes?}], limbs: [{pts:[[x,y,r],...], z}], light:[lx,ly,lz], cell? }
 */
export function paintCanopy(w, h, spec, seed) {
  const L = new IndexLayer(w, h), R = rng(seed);
  const Zb = new Float32Array(w * h).fill(-1e9);
  const own = new Int32Array(w * h).fill(-1);   // which clump/limb wrote the pixel
  const cells = leafCells(w, h, spec.cell || 3.6, spec.cellSeed ?? 7);
  const Lt = norm3(spec.light || [0.7, -0.45, 0.5]);
  const items = [...(spec.limbs || []).map(l => ({ k: 'limb', ...l })), ...(spec.clumps || []).map(c => ({ k: 'clump', ...c }))];
  items.sort((a, b) => a.z - b.z);
  items.forEach((it, n) => {
    if (it.k === 'limb') limb(L, Zb, own, n, it, Lt, R);
    else clump(L, Zb, own, n, it, Lt, R, cells);
  });
  // contact shadow: a pixel whose neighbour toward the light belongs to a nearer item sits in its shade
  const src = L.idx.slice(), sx = Math.round(Lt[0] * 2.2), sy = Math.round(Lt[1] * 2.2);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x, v = src[i];
    if (!v) continue;
    const X = x + sx, Y = y + sy;
    if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
    const j = Y * w + X;
    if (own[j] >= 0 && own[j] !== own[i] && Zb[j] > Zb[i] + 0.5) {
      const m = iMat(v);
      if (m === F.leaf || m === F.young || m === F.glint || m === F.rim) L.idx[i] = I(F.deep, 1, (v >> 3) & 3, 0);
      else if (m === F.bark || m === F.moss) L.idx[i] = I(m, Math.max(0, ((v >> 5) & 7) - 3), (v >> 3) & 3, 0);
    }
  }
  if (spec.rimBelow) rimBelow(L, spec.rimBelow); else rimPass(L, own, Lt);
  L.despeckle(v => { const m = iMat(v); return m === F.leaf || m === F.deep || m === F.young; });
  L.own = own; L.depth = Zb;
  return L;
}

function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }

function clump(L, Zb, own, n, c, Lt, R, cells) {
  const { w, h } = L;
  // lobes: the clump is a few overlapping balls of leaves
  const lobes = c.lobes || (() => {
    const out = [[c.x, c.y, Math.min(c.rx, c.ry) * 0.95]];
    const k = 3 + Math.floor(R() * 3);
    for (let i = 0; i < k; i++) {
      const a = (i / k) * Math.PI * 2 + R() * 0.8, d = 0.45 + R() * 0.3;
      out.push([c.x + Math.cos(a) * c.rx * d, c.y + Math.sin(a) * c.ry * d * 0.85 - c.ry * 0.12, Math.min(c.rx, c.ry) * (0.5 + R() * 0.3)]);
    }
    return out;
  })();
  const nl = lobes.length, LX = new Float64Array(nl), LY = new Float64Array(nl), LI = new Float64Array(nl);
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (let k = 0; k < nl; k++) {
    const [lx, ly, lr] = lobes[k];
    LX[k] = lx; LY[k] = ly; LI[k] = 1 / lr;
    x0 = Math.min(x0, lx - lr - 3); x1 = Math.max(x1, lx + lr + 3); y0 = Math.min(y0, ly - lr - 3); y1 = Math.max(y1, ly + lr + 3);
  }
  x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0)); x1 = Math.min(w - 1, Math.ceil(x1)); y1 = Math.min(h - 1, Math.ceil(y1));
  const young = c.young ?? 0.05, zc = c.z * 4, ao = c.ao || 0, glintOk = c.glint !== false;
  const yng = R() < young * 3; // a clump of new summer leaves, a lighter green
  const leafMat = yng ? F.young : F.leaf, lx = Lt[0], ly = Lt[1], lz = Lt[2];
  const cval = cells.val, idx = L.idx;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    let best = -1, nx = 0, ny = 0;
    const px = x + 0.5, py = y + 0.5;
    for (let k = 0; k < nl; k++) {
      const dx = (px - LX[k]) * LI[k], dy = (py - LY[k]) * LI[k], q = 1 - Math.sqrt(dx * dx + dy * dy);
      if (q > best) { best = q; nx = dx; ny = dy; }
    }
    const i = y * w + x, cv = cval[i];
    // scalloped outline: whole leaf cells in or out near the edge
    if (best < (cv - 0.35) * 0.22) continue;
    const nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
    const z = zc + nz;
    if (z <= Zb[i]) continue;
    let v = (nx * lx + ny * ly + nz * lz) * 0.5 + 0.5;
    v += (cv - 0.5) * 0.3;                         // leaf by leaf
    v -= smooth(0.2, 0.9, ny) * 0.12;              // the underside of the clump
    let band = v < 0.34 ? 0 : v < 0.52 ? 1 : v < 0.7 ? 2 : 3;
    band = band - ao < 0 ? 0 : band - ao;
    if (c.dark && band > 1) band = 1;
    if (band > 0 && band < 3 && cv < 0.16) band--;                 // a few leaves turned away: irregular dark notches
    else if (band === 2 && !ao && cv > 0.95 && nz > 0.5) band = 3; // and a few catching the light
    let mat = band === 0 ? F.deep : leafMat, sun = BAND_SUN[band];
    if (glintOk && band === 3 && cv > 0.95 && nz > 0.6) { mat = F.glint; sun = HI_SUN; }
    let sky = Math.round((0.5 - ny * 0.5) * 3 + 0.3); sky = sky < 0 ? 0 : sky > 3 ? 3 : sky;
    Zb[i] = z; own[i] = n;
    idx[i] = (mat << 8) | (sun << 5) | (sky << 3);
  }
}

function limb(L, Zb, own, n, b, Lt, R) {
  const { w, h } = L, pts = b.pts;
  let along = 0;
  const seed = Math.floor(R() * 1000);
  for (let s = 0; s < pts.length - 1; s++) {
    const [ax, ay, ar] = pts[s], [bx, by, br] = pts[s + 1];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1, tx = dx / len, ty = dy / len;
    // "up" across the limb
    let ux = -ty, uy = tx; if (uy > 0) { ux = -ux; uy = -uy; }
    const rmax = Math.max(ar, br) + 1;
    const x0 = Math.floor(Math.min(ax, bx) - rmax), x1 = Math.ceil(Math.max(ax, bx) + rmax);
    const y0 = Math.floor(Math.min(ay, by) - rmax), y1 = Math.ceil(Math.max(ay, by) + rmax);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      if (x < 0 || y < 0 || x >= w || y >= h) continue;
      const px = x + 0.5 - ax, py = y + 0.5 - ay;
      const tt = clamp((px * tx + py * ty) / len, 0, 1);
      if ((tt === 0 && s > 0) || (tt === 1 && s < pts.length - 2 && (px * tx + py * ty) > len)) {} // joints: allowed
      const aa = along + tt * len;
      const r = lerp(ar, br, tt) * (1 + 0.1 * Math.sin(aa * 0.21 + seed) + 0.07 * Math.sin(aa * 0.53 + seed * 2));
      const cxp = px - tx * tt * len, cyp = py - ty * tt * len;
      const dist = Math.hypot(cxp, cyp);
      if (dist > r) continue;
      const c = (cxp * ux + cyp * uy) / r; // +1 top .. -1 underside
      const i = y * w + x, z = b.z * 4 + 1 + Math.sqrt(Math.max(0, 1 - c * c));
      if (z <= Zb[i]) continue;
      const nxs = ux * c, nys = uy * c, nzs = Math.sqrt(Math.max(0, 1 - c * c));
      const lam = nxs * Lt[0] + nys * Lt[1] + nzs * Lt[2];
      const a = along + tt * len;
      // bark: long fissures along the limb, plates between them
      const wob = (vnoise(a * 0.09, seed, seed + 3) - 0.5) * 2.2;
      const fur = Math.abs(Math.sin((c * 2.1 + wob) * Math.PI));           // ~2 furrows across the visible face
      const brk = vnoise(a * 0.25, c * 2 + seed, seed + 4);                 // furrows break into plates
      let v = lam * 0.5 + 0.5;
      let band = v < 0.36 ? 0 : v < 0.55 ? 1 : v < 0.74 ? 2 : 3;
      if (fur < 0.22 && brk > 0.3) band = Math.max(0, band - 2);
      else if (fur > 0.8 && band < 3 && c > -0.3) band++;
      if (c < -0.6) band = Math.min(band, 1);
      let mat = F.bark;
      if (c > 0.3 && vnoise(a * 0.2, c * 1.6 + seed, seed + 9) > 0.55 && (b.moss ?? 1)) mat = F.moss;
      if (b.dark) { mat = F.dark; band = c < -0.75 ? 2 : 0; }
      const sky = clamp(Math.round((c * 0.5 + 0.5) * 3), 0, 3);
      Zb[i] = z; own[i] = n;
      L.idx[i] = I(mat, [1, 3, 5, 7][band], sky, 0);
    }
    along += len;
  }
}

// seen from below: the lower edges against the sky catch it (brighter near a light behind, e.g. the moon)
function rimBelow(L, o) {
  const { w, h, idx } = L, src = idx.slice();
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x, v = src[i];
    if (!v) continue;
    const below = !src[i + w], side = !src[i - 1] || !src[i + 1];
    if (!below && !(side && !src[i + w - 1] && !src[i + w + 1])) continue;
    const near = o.x != null ? clamp(1 - Math.hypot(x - o.x, y - o.y) / o.r, 0, 1) : 0;
    const m = iMat(v);
    const s = Math.round(2 + near * 5);
    if (m === F.bark || m === F.moss) idx[i] = I(m, clamp(((v >> 5) & 7) + 2, 0, 7), 3, 0);
    else idx[i] = I(F.rim, s, 3, 0);
  }
  L.used = null;
}

// edges: a leaf pixel with open sky above it (and toward the light) catches a rim of light
function rimPass(L, own, Lt) {
  const { w, h, idx } = L, src = idx.slice();
  const sx = Lt[0] > 0.25 ? 1 : Lt[0] < -0.25 ? -1 : 0;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x, v = src[i];
    if (!v) continue;
    const m = iMat(v);
    if (m === F.bark || m === F.moss || m === F.deep) continue;
    const up = src[i - w], side = src[i + sx], diag = src[i - w + sx], lit = ((v >> 5) & 7) >= 4;
    if (!up && (!diag || !side) && lit) idx[i] = I(F.rim, !side ? 6 : 4, 3, 0);
    else if (!up && !lit && ((v >> 5) & 7) >= 2) idx[i] = I(F.rim, 1, 3, 0);
    else if (!side && !diag && lit) idx[i] = I(F.rim, 3, 3, 0);
  }
  L.used = null;
}

// Foreground grass and ferns in silhouette, rimmed on one side by the moon. Blades are drawn as
// curved 1-px strokes thickening to 2 px at the base; a few carry an early susuki plume.
export function paintGrass(w, h, seed, { n = 110, rimSide = 1, plumes = 0.12, hMin = 0.25, hMax = 0.9 } = {}) {
  const L = new IndexLayer(w, h), R = rng(seed);
  const put = (x, y, v) => { x = Math.round(x); y = Math.round(y); if (x >= 0 && y >= 0 && x < w && y < h) L.idx[y * w + x] = v; };
  // a dark ground mass with a ragged top
  for (let x = 0; x < w; x++) {
    const top = Math.round(h - 3 - 3 * vnoise(x * 0.08, 1, seed) - 2 * vnoise(x * 0.3, 2, seed));
    for (let y = top; y < h; y++) put(x, y, I(F.dark, 1, 1, 0));
  }
  // tufts: several blades fanning out of one root, 2 px thick for most of their length
  const tufts = Math.max(4, Math.round(n / 6));
  for (let k = 0; k < tufts; k++) {
    const rx = R() * w, size = hMin + R() * (hMax - hMin), nb = 4 + Math.floor(R() * 6);
    for (let b = 0; b < nb; b++) {
      const bh = h * size * (0.55 + R() * 0.45), lean = (b / (nb - 1 || 1) - 0.5) * 1.3 + (R() - 0.5) * 0.4, curl = lean * (0.3 + R() * 0.5);
      const bx = rx + (R() - 0.5) * 4;
      const steps = Math.ceil(bh * 1.1);
      let x = bx, y = h - 1;
      for (let i = 0; i < steps; i++) {
        const t = i / steps;
        x = bx + lean * bh * 0.45 * t * t + curl * bh * 0.4 * t * t * t;
        y = h - 1 - bh * (t - 0.22 * t * t * Math.abs(lean));
        const lit = (rimSide > 0 ? lean + curl * t > 0.12 : lean + curl * t < -0.12) && t > 0.25;
        const v = lit && R() < 0.75 ? I(F.rim, 3 + Math.round(t * 3), 3, 0) : I(F.dark, 1, 2, 0);
        put(x, y, v);
        if (t < 0.7) put(x - rimSide, y, I(F.dark, 0, 1, 0));   // the blade's body, 2 px
      }
      if (R() < plumes) for (let j = 0; j < 7; j++) put(x + j * 0.7 * Math.sign(lean || 1), y + j * 0.6, I(F.rim, 4 + (j > 4 ? 2 : 0), 3, 0));
    }
  }
  return L;
}
