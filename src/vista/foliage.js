// The great camphor, close up: leaf clumps built from individual leaf stamps (each leaf shaded by
// the clump's volume and its own tilt, glossy ones catching a glint), and limbs shaded as bark
// cylinders with fissures and moss. Painted once into an IndexLayer; colour comes from palettes.

import { clamp, lerp, smooth, rng, hash2, fbm, vnoise, IndexLayer, I, iMat } from './util.js';

export const F = { deep: 1, leaf: 2, young: 3, rim: 4, glint: 5, bark: 6, moss: 7, twig: 8, dark: 9 };
export const FOLIAGE_MATS = [];
FOLIAGE_MATS[F.deep] = { albedo: [0.13, 0.19, 0.1], ambK: 0.8, sunK: 0.6 };
FOLIAGE_MATS[F.leaf] = { albedo: [0.25, 0.34, 0.15], ambK: 1, sunK: 1, gloss: 0.35 };
FOLIAGE_MATS[F.young] = { albedo: [0.38, 0.42, 0.18], ambK: 1, sunK: 1, gloss: 0.3 };
FOLIAGE_MATS[F.rim] = { albedo: [0.3, 0.38, 0.2], rim: true, rimK: 0.62 };
FOLIAGE_MATS[F.glint] = { albedo: [0.42, 0.5, 0.3], ambK: 1.5, sunK: 1.4, gloss: 0.9 };
FOLIAGE_MATS[F.bark] = { albedo: [0.36, 0.31, 0.26], ambK: 1, sunK: 0.95 };
FOLIAGE_MATS[F.moss] = { albedo: [0.3, 0.36, 0.17], ambK: 1, sunK: 0.95 };
FOLIAGE_MATS[F.twig] = { albedo: [0.3, 0.26, 0.22], ambK: 1, sunK: 0.8 };
FOLIAGE_MATS[F.dark] = { albedo: [0.06, 0.08, 0.06], ambK: 0.5, sunK: 0.2 };

// leaf stamps: small ellipses at 8 angles, 2 sizes; each pixel tagged 0 = body, 1 = upper (lit) half
const STAMPS = (() => {
  const out = [];
  for (const [len, wid] of [[4.2, 2.1], [5.6, 2.6], [3.2, 1.7]]) {
    const row = [];
    for (let a = 0; a < 8; a++) {
      const ang = (a / 8) * Math.PI, ca = Math.cos(ang), sa = Math.sin(ang), px = [];
      const R = Math.ceil(len / 2) + 1;
      for (let y = -R; y <= R; y++) for (let x = -R; x <= R; x++) {
        const u = (x * ca + y * sa) / (len / 2), v = (-x * sa + y * ca) / (wid / 2);
        if (u * u + v * v <= 1.0) px.push([x, y, v < 0 ? 1 : 0, Math.abs(u) > 0.7 ? 1 : 0]);
      }
      row.push(px);
    }
    out.push(row);
  }
  return out;
})();

/**
 * Paint a canopy into an IndexLayer.
 * @param {number} w,h layer size
 * @param {object} spec { clumps: [{x,y,rx,ry,z,young?,dens?}], limbs: [{pts:[[x,y,r],...], z}], light:[lx,ly,lz] }
 */
export function paintCanopy(w, h, spec, seed) {
  const L = new IndexLayer(w, h), R = rng(seed);
  const Z = new Float32Array(w * h).fill(-1e9);
  const [lx, ly, lz] = norm3(spec.light || [0.7, -0.5, 0.5]);
  const items = [...(spec.limbs || []).map(l => ({ k: 'limb', ...l })), ...(spec.clumps || []).map(c => ({ k: 'clump', ...c }))];
  items.sort((a, b) => a.z - b.z);
  for (const it of items) {
    if (it.k === 'limb') limb(L, Z, it, lx, ly, lz, R);
    else clump(L, Z, it, lx, ly, lz, R);
  }
  rimPass(L, spec.rimDir || [lx, ly]);
  L.despeckle(v => { const m = iMat(v); return m === F.leaf || m === F.deep || m === F.young; });
  return L;
}

function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }

function clump(L, Z, c, lx, ly, lz, R) {
  const { w, h } = L;
  const area = Math.PI * c.rx * c.ry;
  const n = Math.round(area * (c.dens ?? 0.42));
  const leaves = [];
  for (let i = 0; i < n; i++) {
    // points on (and a little inside) the clump's front surface, a squashed sphere
    let u, v;
    do { u = R() * 2 - 1; v = R() * 2 - 1; } while (u * u + v * v > 1);
    // a lumpy outline: lobes of the clump
    const ang = Math.atan2(v, u), lobe = 0.82 + 0.18 * Math.sin(ang * 3 + c.x * 0.1) + 0.12 * (vnoise(Math.cos(ang) * 2 + c.x, Math.sin(ang) * 2 + c.y, 3) - 0.5);
    if (u * u + v * v > lobe * lobe) continue;
    const zz = Math.sqrt(Math.max(0, 1 - u * u - v * v)) * (0.6 + 0.4 * R());
    leaves.push([u, v, zz]);
  }
  leaves.sort((a, b) => a[2] - b[2]);
  const young = c.young ?? 0;
  for (const [u, v, zz] of leaves) {
    const x0 = c.x + u * c.rx, y0 = c.y + v * c.ry;
    // leaf normal: the sphere's, tilted at random (leaves face every way, but on average outward)
    let nx = u + (R() - 0.5) * 0.9, ny = v + (R() - 0.5) * 0.9, nz = zz + 0.35;
    const nl = Math.hypot(nx, ny, nz); nx /= nl; ny /= nl; nz /= nl;
    const lam = nx * lx + ny * ly + nz * lz;
    const depth = zz; // 0 back .. 1 front
    let sun = Math.round(clamp(lam * 0.62 + 0.38, 0, 1) * 7 * (0.45 + 0.55 * depth));
    const sky = clamp(Math.round((0.5 - v * 0.5) * 3 * (0.5 + 0.5 * depth) + 0.4), 0, 3);
    const mat = depth < 0.18 ? F.deep : (R() < young ? F.young : F.leaf);
    const size = depth > 0.7 && R() < 0.35 ? 1 : (R() < 0.25 ? 2 : 0);
    const ai = (Math.round(((Math.atan2(ny, nx) + Math.PI * 0.5 + (R() - 0.5) * 1.2) / Math.PI) * 8) % 8 + 8) % 8;
    const stamp = STAMPS[size][ai];
    const glint = mat !== F.deep && lam > 0.55 && depth > 0.55 && R() < 0.22;
    const zv = (c.z || 0) * 4 + depth;
    const xi = Math.round(x0), yi = Math.round(y0);
    for (const [dx, dy, up, tip] of stamp) {
      const X = xi + dx, Y = yi + dy;
      if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
      const k = Y * w + X;
      if (Z[k] > zv) continue;
      Z[k] = zv;
      let s = sun + (up ? 1 : -1) * (depth > 0.3 ? 1 : 0);
      if (tip && !up) s -= 1;
      let m = mat;
      if (glint && up && !tip && dx * dx + dy * dy <= 1) m = F.glint;
      L.idx[k] = I(m, clamp(s, 0, 7), sky, 0);
    }
  }
}

function limb(L, Z, b, lx, ly, lz, R) {
  const { w, h } = L, pts = b.pts;
  let along = 0;
  const seed = Math.floor(R() * 1000);
  for (let s = 0; s < pts.length - 1; s++) {
    const [ax, ay, ar] = pts[s], [bx, by, br] = pts[s + 1];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1, tx = dx / len, ty = dy / len;
    const nx = -ty, ny = tx; // cross direction (pointing "up-left" for a left-to-right limb)
    const rmax = Math.max(ar, br) + 1;
    const x0 = Math.floor(Math.min(ax, bx) - rmax), x1 = Math.ceil(Math.max(ax, bx) + rmax);
    const y0 = Math.floor(Math.min(ay, by) - rmax), y1 = Math.ceil(Math.max(ay, by) + rmax);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      if (x < 0 || y < 0 || x >= w || y >= h) continue;
      const px = x + 0.5 - ax, py = y + 0.5 - ay;
      const tt = clamp((px * tx + py * ty) / len, 0, 1);
      const r = lerp(ar, br, tt);
      const cx = px - tx * tt * len, cy = py - ty * tt * len;
      const dist = Math.hypot(cx, cy);
      if (dist > r) continue;
      let c = (cx * nx + cy * ny) / r; // -1..1 across the limb
      // which side is "up"? make c > 0 the side facing up
      if (ny > 0) c = -c;
      const k = y * w + x, zv = (b.z || 0) * 4 + 0.5 + Math.sqrt(1 - c * c) * 0.4;
      if (Z[k] > zv) continue;
      Z[k] = zv;
      // cylinder normal in screen space: up-side (c>0) faces -y
      const upx = ny > 0 ? -nx : nx, upy = ny > 0 ? -ny : ny;
      const snx = upx * c, sny = upy * c, snz = Math.sqrt(Math.max(0, 1 - c * c));
      const lam = snx * lx + sny * ly + snz * lz;
      const a = along + tt * len;
      // bark: long fissures running along the limb, broken by plates
      const fis = fbm(a * 0.18, c * 2.6 + seed, 3, seed) + (vnoise(a * 0.6, c * 7, seed + 5) - 0.5) * 0.25;
      let mat = F.bark, sun = Math.round(clamp(lam * 0.6 + 0.4, 0, 1) * 7);
      if (fis < 0.36) sun = Math.max(0, sun - 3);
      else if (fis > 0.66) sun = Math.min(7, sun + 1);
      if (c < -0.72) sun = Math.max(0, sun - 2); // the underside in its own shade
      if (c > 0.35 && vnoise(a * 0.22, c * 2 + seed, seed + 9) > 0.56 && (b.moss ?? 1)) mat = F.moss;
      const sky = clamp(Math.round((c * 0.5 + 0.5) * 3), 0, 3);
      L.idx[k] = I(mat, sun, sky, 0);
    }
    along += len;
  }
}

// edges: a leaf pixel with open sky on the light side becomes rim light (sun bits = strength)
function rimPass(L, [rx, ry]) {
  const { w, h, idx } = L, src = idx.slice();
  const sx = Math.sign(rx), sy = Math.sign(ry);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x, v = src[i];
    if (!v) continue;
    const m = iMat(v);
    if (m !== F.leaf && m !== F.young && m !== F.glint && m !== F.deep) continue;
    const openUp = !src[i - w], openSide = sx ? !src[i + sx] : false, openDiag = !src[i - w + sx];
    const n = (openUp ? 2 : 0) + (openSide ? 1 : 0) + (openDiag ? 1 : 0);
    if (n >= 2) idx[i] = I(F.rim, clamp(2 + n, 0, 7), 3, 0);
  }
  L.used = null;
}

// Scatter clumps along a curve: helper for canopy edges and sprays
export function clumpsAlong(R, pts, { r0 = 8, r1 = 14, step = 0.7, jitter = 4, z = 0, young = 0.08, squash = 0.72 }) {
  const out = [];
  for (let s = 0; s < pts.length - 1; s++) {
    const [ax, ay] = pts[s], [bx, by] = pts[s + 1], len = Math.hypot(bx - ax, by - ay);
    let d = 0;
    while (d < len) {
      const t = d / len, r = lerp(r0, r1, R());
      out.push({ x: lerp(ax, bx, t) + (R() - 0.5) * jitter * 2, y: lerp(ay, by, t) + (R() - 0.5) * jitter * 2, rx: r, ry: r * squash, z: z + R() * 0.5, young: R() < 0.25 ? young * 4 : young });
      d += r * step;
    }
  }
  return out;
}
