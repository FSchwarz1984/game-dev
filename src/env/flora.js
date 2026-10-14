/* =====================================================================
   env/flora — trees and plants of a late-summer cedar pass. Every
   painter returns an SB (env/paint.js) whose anchor is the bottom centre
   (where it meets the ground) unless meta says otherwise. All shading
   assumes the light from the top-left. Several variants per species
   (seeded), so a clump never repeats one silhouette.

   Sizes (1 m = 20 px): cedar 7–10 m, pine 5–7 m, maple 4–6 m, the great
   camphor is 26 m (env/camphor.js) — other trees stay well below a
   third of it so it reads as enormous.
   Ported in spirit from legacy/v0.1/src/art_flora.js (tiered cedar,
   layered maple plates, ferns, sasa, susuki, lilies, hydrangea); the
   canopies now use sphere-lit sub-clumps with leaf cells (paint.js
   foliage) instead of flat noise, and a black pine was added.
   ===================================================================== */
import { SB, PX, POST, MAT, foliage, mass, domeBlobs, cylN, LIGHT } from './paint.js';
import { PAL } from './palette.js';
import { RNG, clamp, lerp, hash2, hyp, ramp } from './core.js';

/* ---------------- bark & trunks ---------------- */
/** a tapering trunk along a curve; fissured bark columns, cylinder-shaded */
export function trunk(s, pts, w0, w1, rr, o = {}) {
  const seed = o.seed || 1; let total = 0; for (let i = 0; i < pts.length - 1; i++) total += hyp(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
  let acc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1], L = hyp(bx - ax, by - ay);
    PX.stroke(ax, ay, bx, by, lerp(w0, w1, acc / total) / 2, lerp(w0, w1, (acc + L) / total) / 2, (x, y, t, sx) => {
      const n = cylN(sx);
      const col = Math.floor((sx + 1) * (o.cols ?? 3)), seg = Math.floor(y / (o.seg ?? 6));
      const fis = hash2(col, seg, seed) < (o.fis ?? 0.18);
      let tt = 0.52 - sx * 0.26 + (hash2(col, Math.floor(y / 3), seed + 3) - 0.5) * 0.16 - (fis ? 0.2 : 0);
      if (o.moss && hash2(x >> 1, y >> 1, seed + 9) < o.moss * (1 - (y - Math.min(ay, by)) / 400) && sx < 0.4) {
        s.pz(x, y, PX.rc(PAL.moss, clamp(0.45 - sx * 0.2, 0, 1), x, y, 0.4), (o.z ?? 2) + n[2] * (w0 / 2), { m: MAT.MOSS, b: (o.b ?? 0) + n[2] * w0 / 2 });
        return;
      }
      s.pz(x, y, PX.rc(rr, clamp(tt, 0, 1), x, y, 0.45), (o.z ?? 2) + n[2] * (w0 / 2), { m: MAT.BARK, b: (o.b ?? 0) + n[2] * w0 / 2, n });
    });
    acc += L;
  }
}
/** a branch: thin tapered stroke, top-lit */
function branch(s, x0, y0, x1, y1, w0, w1, rr, z, b) {
  PX.stroke(x0, y0, x1, y1, w0, w1, (x, y, t, sx) => s.pz(x, y, rr[clamp(Math.round((0.48 - sx * 0.22) * (rr.length - 1)), 0, rr.length - 1)], z, { m: MAT.BARK, b, n: cylN(sx * 0.8, 0.3) }));
}

/* ---------------- cedar 杉: a slim spire of drooping tiers ---------------- */
export function cedar(seed, H = 170, W = 44) {
  const R = RNG(seed * 13 + 1), w = W + 18, h = H + 6, s = new SB(w, h), cx = Math.round(w / 2 + R.range(-1, 1)), baseY = h - 3;
  const crownBot = Math.round(H * R.range(0.6, 0.68)), top = 5;
  trunk(s, [[cx, baseY], [cx + R.range(-1, 1), top + 24]], R.range(5.5, 7.5), 2, PAL.barkCedar, { seed, cols: 2, seg: 7, moss: 0.25, b: 2 });
  for (let k = 0; k < 2; k++) { const d = k ? 1 : -1; PX.stroke(cx + d * 2, baseY - 3, cx + d * R.range(5, 7), baseY + 1, 2.2, 1, (x, y) => s.pz(x, y, PAL.barkCedar[1 + (k ? 0 : 1)], 1.5, { m: MAT.BARK, b: 1 })); }
  const hwAt = y => { const t = clamp((y - top) / (crownBot - top), 0, 1); return (W / 2) * (Math.pow(t, 0.85) * (t > 0.9 ? 1 - (t - 0.9) * 1.6 : 1)) + 2.5; };
  // a dark heart, so the gaps between tiers read as depth
  for (let yy = top + 8; yy < crownBot - 3; yy++) { const hw = hwAt(yy) * 0.55; for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw); x++) s.pz(x, yy, PAL.cedarDeep[hash2(x, yy, seed) < 0.2 ? 1 : 0], 1, { m: MAT.LEAF, b: 1, n: [0, 0, 1] }); }
  const tiers = []; let y = crownBot - 5;
  while (y > top + 7) { tiers.push(y); y -= R.range(7.5, 10) * (y < top + 40 ? 0.72 : 1); }
  for (let i = tiers.length - 1; i >= 0; i--) {
    const ty = tiers[i], up = 1 - i / tiers.length, hw0 = hwAt(ty);
    const tone = -0.06 + up * 0.1 + (i % 2 ? 0.02 : -0.02);
    const zc = 6 + hw0 * 0.35;
    // irregular sprays: each side its own reach and droop, now and then one side missing
    const wl = hw0 * R.range(0.7, 1.15), wr = hw0 * R.range(0.7, 1.15), off = R.range(-2.5, 2.5);
    for (const [sd, hw] of [[-1, wl], [1, wr]]) { if (hw0 > 7 && R() > 0.12) mass(s, { x: cx + off + sd * hw * 0.55, y: ty + R.range(1.5, 3.5), rx: hw * 0.55, ry: 3.2 + hw * 0.06, z: zc - 2, droop: R.range(0.8, 1.4), tilt: sd * R.range(0.05, 0.2), seed: i * 2 + (sd > 0 ? 1 : 0) }, { ramp: PAL.cedar, cell: 2.5, seed, tone: tone - 0.04, under: 1.25, rim: 0.08 }); }
    mass(s, { x: cx + off * 0.6, y: ty, rx: (wl + wr) * 0.33 + 2, ry: 3.8 + hw0 * 0.07, z: zc, droop: R.range(0.5, 0.9), seed: i * 3 + 7 }, { ramp: PAL.cedar, cell: 2.5, seed, tone, under: 1.15, rim: 0.1 });
  }
  // the leader
  for (let yy = 1; yy < top + 10; yy++) s.pz(cx, yy, PAL.cedar[yy < 5 ? 5 : 3], 24, { m: MAT.LEAF, b: 9 });
  for (const [dx, dy] of [[-1, 6], [1, 8], [-1, 10], [1, 11]]) s.pz(cx + dx, top + dy, PAL.cedar[dx < 0 ? 4 : 2], 23, { m: MAT.LEAF, b: 9 });
  POST.ao(s, 2, 0.18); POST.outline(s, { k: 0.62 }); POST.normals(s, 0.8);
  return { s, meta: { ax: cx, ay: baseY + 1, sway: 0.5, foliage: true, occluder: true, kind: 'tree' } };
}

/* ---------------- black pine 黒松: a crooked trunk carrying flat plates of needles ---------------- */
export function pine(seed, H = 120, lean = 0) {
  const R = RNG(seed * 17 + 5), W = 120, h = H + 8, s = new SB(W, h), cx = W / 2 + R.range(-4, 4) - lean * 14, baseY = h - 3;
  const pts = [[cx, baseY]]; let x = cx, y = baseY; const segs = 5;
  for (let i = 1; i <= segs; i++) { x += R.range(-6, 6) + lean * 7; y -= (baseY - 20) / segs; pts.push([x, y]); }
  trunk(s, pts, R.range(7, 9), 3.2, PAL.barkPine, { seed, cols: 3, seg: 4, fis: 0.34, b: 3 });
  const plates = []; const np = R.int(5, 7);
  for (let i = 0; i < np; i++) {
    const t = i / (np - 1); const p = pts[Math.min(segs, 1 + Math.floor(t * (segs - 0.01)))];
    const side = i === np - 1 ? 0 : (i % 2 ? 1 : -1) * R.range(0.6, 1);
    const px = p[0] + side * R.range(12, 22) * (1 - t * 0.4) + lean * 6, py = p[1] - R.range(3, 8);
    branch(s, p[0], p[1], px, py + 3, 2.4, 1.2, PAL.barkPine, 6, 4);
    plates.push({ x: px, y: py, w: R.range(16, 25) * (1 - t * 0.3), h: R.range(5, 7), i });
  }
  plates.sort((a, b) => a.y - b.y);
  plates.forEach((pl, i) => {
    const zz = 10 + (np - i) * 2;
    mass(s, { x: pl.x - pl.w * 0.35, y: pl.y + 1, rx: pl.w * 0.55, ry: pl.h * 0.9, z: zz - 1, droop: 0.25, seed: i * 5 }, { ramp: PAL.pine, cell: 2.2, seed, tone: -0.02, under: 1.3, rim: 0.12 });
    mass(s, { x: pl.x + pl.w * 0.3, y: pl.y + 0.5, rx: pl.w * 0.6, ry: pl.h, z: zz, droop: 0.2, seed: i * 5 + 1 }, { ramp: PAL.pine, cell: 2.2, seed, tone: 0.02, under: 1.3, rim: 0.12 });
    // needle tufts: a spiky top edge and hanging needles underneath
    for (let k = 0; k < pl.w * 1.6; k++) {
      const xx = Math.round(pl.x + R.range(-pl.w, pl.w) * 0.85);
      for (let yy = Math.round(pl.y - pl.h * 1.2); yy < pl.y + pl.h * 1.3; yy++) {
        if (!s.a(xx, yy)) continue;
        if (R() < 0.6 && !s.a(xx, yy - 1)) { s.px(xx, yy - 1, PAL.pine[4], { m: MAT.LEAF, z: zz + 3, b: zz }); if (R() < 0.35) s.px(xx, yy - 2, PAL.pine[5], { m: MAT.LEAF, z: zz + 3, b: zz }); }
        break;
      }
    }
  });
  POST.ao(s, 2, 0.2); POST.outline(s, { k: 0.62 }); POST.normals(s, 0.8);
  return { s, meta: { ax: Math.round(pts[0][0]), ay: baseY + 1, sway: 0.35, foliage: true, occluder: true, kind: 'tree' } };
}

/* ---------------- broadleaf (maple): stacked plates of leaf clusters ---------------- */
export function maple(seed, red = false, H = 100) {
  const R = RNG(seed * 7 + 3), W = 112, h = H + 4, s = new SB(W, h), cx = W / 2 + R.range(-3, 3), baseY = h - 2;
  const lean = R.range(-8, 8);
  trunk(s, [[cx, baseY], [cx + lean * 0.4, baseY - 30], [cx + lean, 46]], 5, 2.6, PAL.barkGrey, { seed, cols: 2, seg: 8, fis: 0.1, b: 2 });
  for (let k = 0; k < 6; k++) { const a = R.range(-1.3, 1.3); branch(s, cx + lean * 0.7, 58 + k * 3, cx + lean + Math.sin(a) * 34, 32 + R.range(-12, 8), 1.8, 0.8, PAL.barkGrey, 5, 3); }
  const rr = red ? PAL.mapleRed : PAL.maple;
  for (let Lr = 0; Lr < 5; Lr++) {
    const y = 14 + Lr * 9 + R.range(-2, 2), wv = 40 - Math.abs(Lr - 2) * 7;
    const n = 3;
    for (let k = 0; k < n; k++) { const f = k / (n - 1) * 2 - 1; const x = cx + lean * (1 - Lr / 6) + f * wv * 0.55 + R.range(-4, 4);
      mass(s, { x, y: y + Math.abs(f) * 2, rx: R.range(11, 15), ry: R.range(5.5, 7), z: 6 + Lr * 4 + (1 - Math.abs(f)) * 3, droop: 0.35, seed: Lr * 7 + k }, { ramp: rr, cell: 2.5, seed, tone: 0.02 + (Lr < 2 ? 0.04 : 0), under: 0.9, rim: 0.1 }); }
  }
  POST.ao(s, 2, 0.18); POST.outline(s, { k: 0.66 }); POST.normals(s, 0.8);
  return { s, meta: { ax: cx, ay: baseY + 1, sway: 0.8, foliage: true, occluder: true, kind: 'tree' } };
}

/* ---------------- shrubs: camellia / azalea ---------------- */
export function bush(seed, kind = 'camellia', w = 34, hgt = 24) {
  const R = RNG(seed * 23 + 7), W = w + 10, H = hgt + 6, s = new SB(W, H), cx = W / 2, by = H - 2;
  const rr = PAL.broad, cell = kind === 'azalea' ? 2.1 : 2.7;
  const n = Math.max(3, Math.round(w / 9));
  const ms = [];
  for (let k = 0; k < n; k++) { const f = n === 1 ? 0 : k / (n - 1) * 2 - 1; ms.push({ x: cx + f * w * 0.32 + R.range(-2, 2), y: by - hgt * 0.42 + Math.abs(f) * hgt * 0.12, rx: w * 0.3 + R.range(-1, 2), ry: hgt * 0.36, z: 4 + (1 - Math.abs(f)) * 5, droop: 0.1, seed: k }); }
  ms.push({ x: cx + R.range(-3, 3), y: by - hgt * 0.62, rx: w * 0.3, ry: hgt * 0.32, z: 12, seed: 9 });
  ms.sort((a, b) => a.z - b.z).forEach(m => mass(s, m, { ramp: rr, cell, seed, tone: 0.02, under: 0.8, rim: 0.08 }));
  if (kind === 'azalea') for (let k = 0; k < 9; k++) { const x = Math.round(R.range(cx - w * 0.38, cx + w * 0.38)), y = Math.round(R.range(by - hgt * 0.9, by - hgt * 0.3)); if (s.a(x, y)) { s.px(x, y, [214, 110, 140], { m: MAT.PETAL, z: 40, b: 10 }); if (s.a(x + 1, y)) s.px(x + 1, y, [182, 80, 112], { m: MAT.PETAL, z: 40, b: 10 }); } }
  if (kind === 'camellia') for (let k = 0; k < 12; k++) { const x = Math.round(R.range(cx - w * 0.4, cx + w * 0.25)), y = Math.round(R.range(by - hgt * 0.95, by - hgt * 0.45)); if (s.a(x, y) && s.a(x - 1, y - 1)) s.px(x - 1, y - 1, PAL.broad[6], { m: MAT.LEAF, z: 40, b: 10 }); }
  POST.ao(s, 2, 0.15); POST.outline(s, { k: 0.64 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, sway: 0.25, foliage: true, kind: 'bush' } };
}

/* ---------------- hydrangea 紫陽花, past its best in August ---------------- */
export function hydrangea(seed) {
  const R = RNG(seed * 31 + 2), W = 40, H = 30, s = new SB(W, H), cx = W / 2, by = H - 2;
  foliage(s, domeBlobs(cx, by - 9, 15, 9, 9, 4.5, 6.5, seed, { zk: 0.6 }), { ramp: PAL.sasa, cell: 3, seed, under: 0.5 });
  const heads = [];
  for (let k = 0; k < 6; k++) heads.push({ x: R.range(cx - 13, cx + 13), y: R.range(by - 20, by - 8), r: R.range(3.4, 4.6), z: 16 + R() * 4 });
  heads.forEach((hd, i) => foliage(s, [hd], { ramp: PAL.hydr[i % 3], cell: 1.8, seed: seed * 5 + i, mat: MAT.PETAL, under: 0.3, tone: -0.04 + (i % 2) * 0.06 }));
  POST.outline(s, { k: 0.7 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, sway: 0.3, foliage: true, kind: 'bush' } };
}

/* ---------------- fern: a fountain of arching fronds ---------------- */
export function fern(seed, size = 1) {
  const R = RNG(seed * 3 + 9), W = Math.round(46 * size), H = Math.round(32 * size), s = new SB(W, H), cx = W / 2, by = H - 2;
  const nf = R.int(7, 9);
  const order = [...Array(nf).keys()].sort((p, q) => Math.abs(q - (nf - 1) / 2) - Math.abs(p - (nf - 1) / 2));
  for (const f of order) {
    const u = f / (nf - 1) * 2 - 1, L = R.range(15, 21) * size * (1 - Math.abs(u) * 0.15);
    let x = cx + u * 2, y = by, a = -Math.PI / 2 + u * 1.25 + R.range(-0.1, 0.1); const pts = [[x, y]]; const curl = u * 0.11 + R.range(-0.02, 0.02);
    for (let i = 0; i < 16; i++) { a += curl + 0.02 * Math.sign(u || 1); x += Math.cos(a) * L / 16; y += Math.sin(a) * L / 16 + i * 0.05 * Math.abs(u); pts.push([x, y]); }
    const zf = 3 + (1 - Math.abs(u)) * 3;
    for (let i = 1; i < pts.length; i++) {
      const t = i / pts.length, [px1, py1] = pts[i], [px0, py0] = pts[i - 1]; const dx = px1 - px0, dy = py1 - py0, dl = hyp(dx, dy) || 1;
      const nx = -dy / dl, ny = dx / dl, ll = ((1 - t) * 3.4 + 0.8) * size;
      for (const sd of [-1, 1]) for (let q = 0.5; q <= ll; q += 0.5) {
        const xx = px1 + nx * q * sd + dx / dl * q * 0.6, yy = py1 + ny * q * sd + dy / dl * q * 0.6 + q * 0.2;
        const tone = 0.5 + (sd * nx > 0 ? 0.12 : -0.08) + ((i >> 1) % 2 ? 0.06 : -0.04) - q / ll * 0.14 + (1 - Math.abs(u)) * 0.06 + (u < 0 ? 0.05 : -0.03);
        s.pz(xx, yy, PX.rc(PAL.fern, clamp(tone, 0, 1), xx, yy, 0.3), zf + (1 - t) * 2 - q * 0.3, { m: MAT.LEAF, b: 2 + zf * 0.3 });
      }
      s.pz(px1, py1, PAL.fern[1], zf + (1 - t) * 2 + 0.3, { m: MAT.LEAF, b: 2 + zf * 0.3 });
    }
  }
  POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, sway: 0.9, shadow: 0, foliage: true, kind: 'under' } };
}

/* ---------------- sasa 熊笹: broad blades with pale margins ---------------- */
export function sasa(seed, size = 1) {
  const R = RNG(seed * 11 + 5), W = Math.round(38 * size), H = Math.round(30 * size), s = new SB(W, H), cx = W / 2, by = H - 1;
  const n = R.int(9, 13), stems = [];
  for (let k = 0; k < n; k++) stems.push({ u: R.range(-1, 1), k });
  stems.sort((p, q) => Math.abs(q.u) - Math.abs(p.u));
  for (const st of stems) {
    const u = st.u, k = st.k, a = -Math.PI / 2 + u * 1.35 + R.range(-0.15, 0.15), L = R.range(11, 15) * size, bx = cx + u * 5 * size;
    const mx = bx + Math.cos(a) * 4, my = by - 6 * size, x1 = mx + Math.cos(a) * L, y1 = my + Math.sin(a) * L * 0.9 + Math.abs(u) * 4;
    PX.stroke(bx, by, mx, my, 0.5, 0.5, (x, y) => s.pz(x, y, PAL.sasa[1], 1, { m: MAT.LEAF }));
    const z0 = 2 + (1 - Math.abs(u)) * 3;
    PX.stroke(mx, my, x1, y1, 2.6 * size, 0.3, (x, y, t, sx) => {
      const edge = Math.abs(sx) > 0.74 && t > 0.12 && t < 0.9, mid = Math.abs(sx) < 0.18 && t < 0.8;
      s.pz(x, y, edge ? PAL.susuki[3] : PX.rc(PAL.sasa, clamp(0.5 - sx * 0.16 + (mid ? 0.16 : 0) + (k % 2 ? 0.06 : -0.06), 0, 1), x, y, 0.3), z0 + t * 2 + (1 - Math.abs(sx)), { m: MAT.LEAF, b: 2 + z0 * 0.3 });
    });
  }
  POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, sway: 0.9, shadow: 0, foliage: true, kind: 'under' } };
}

/* ---------------- susuki 芒: arching blades and the first silver plumes ---------------- */
export function susuki(seed, plumes = true) {
  const R = RNG(seed * 23 + 8), W = 46, H = 56, s = new SB(W, H), cx = W / 2, by = H - 1;
  const blade = PAL.susuki, plume = ramp('#ddd2c2', 4, { lo: 0.3, hi: 0.2, hueShift: 0.02 });
  for (let k = 0; k < 24; k++) {
    const a = R.range(-2.8, -0.35), Lb = R.range(14, 27), bend = R.range(0.35, 0.95) * (Math.cos(a) > 0 ? 1 : -1);
    let x = cx + R.range(-3, 3), y = by;
    for (let i = 0; i < Lb; i++) { const t = i / Lb, ang = a + bend * t * t; x += Math.cos(ang); y += Math.sin(ang); s.pz(x, y, blade[clamp(Math.round((0.38 + t * 0.32 + (k % 3 - 1) * 0.1) * 4), 0, 4)], 2 + t * 4, { m: MAT.BLADE, b: 2 }); }
  }
  if (plumes) { const np = R.int(2, 4);
    for (let k = 0; k < np; k++) {
      let x = cx + R.range(-4, 4), y = by - 6; const a = R.range(-2.05, -1.1), Lp = R.range(34, 46), lean = R.range(0.5, 0.8) * (Math.cos(a) >= 0 ? 1 : -1);
      for (let i = 0; i < Lp; i++) {
        const t = i / Lp, ang = a + lean * t * t * 1.2; x += Math.cos(ang); y += Math.sin(ang);
        s.pz(x, y, t < 0.55 ? blade[2] : plume[2], 6 + t * 2, { m: MAT.BLADE, b: 3 });
        if (t > 0.55 && i % 2 === 0) { const hl = 2 + Math.round((1 - Math.abs(t - 0.78) * 3.5) * 3); const ha = ang + lean * 1.9;
          for (let q = 1; q <= hl; q++) s.pz(x + Math.cos(ha) * q, y + Math.sin(ha) * q + q * 0.55, plume[clamp(3 - Math.floor(q / hl * 3), 0, 3)], 7 + t * 2 - q * 0.2, { m: MAT.BLADE, b: 3 }); }
      }
    } }
  POST.outline(s, { k: 0.84 }); POST.normals(s, 0.8);
  return { s, meta: { ax: cx, ay: by + 1, sway: 1.7, foliage: true, kind: 'under' } };
}

/* ---------------- 山百合: heavy white trumpets, a golden band, crimson freckles ---------------- */
export function lily(seed) {
  const R = RNG(seed * 29 + 1), W = 26, H = 38, s = new SB(W, H), cx = W / 2 + R.range(-1, 1), by = H - 1, top = R.int(10, 13);
  PX.stroke(cx, by, cx + R.range(-2, 2), top, 0.6, 0.6, (x, y) => s.pz(x, y, PAL.fern[2], 2, { m: MAT.LEAF }));
  for (let k = 0; k < 7; k++) { const y = by - 3 - k * 3, d = k % 2 ? 1 : -1; PX.stroke(cx, y, cx + d * 6, y - 3, 1.2, 0.2, (x, yy, t, sx) => s.pz(x, yy, PAL.fern[clamp(3 - (sx > 0 ? 1 : 0), 0, 5)], 3, { m: MAT.LEAF, b: 1 })); }
  const nf = R.int(1, 3);
  for (let f = 0; f < nf; f++) {
    const fx = cx + (f - (nf - 1) / 2) * 7, fy = top + (f % 2) * 3;
    for (let p = 0; p < 6; p++) { const a = p / 6 * Math.PI * 2 + 0.3; PX.stroke(fx, fy, fx + Math.cos(a) * 5.5, fy + Math.sin(a) * 4.2 + 1, 1.7, 0.5, (x, y, t, sx) => {
      const stripe = Math.abs(sx) < 0.3 && t < 0.75; const dot = !stripe && hash2(x, y, f * 7 + p) < 0.16 && t > 0.25 && t < 0.8;
      s.pz(x, y, stripe ? [234, 192, 80] : dot ? [172, 46, 40] : PAL.lily[clamp(Math.round((0.75 - t * 0.3 + (sx > 0 ? 0.1 : -0.05)) * 3), 0, 3)], 8 + (1 - t) * 3, { m: MAT.PETAL, b: 4 }); }); }
    s.pz(fx, fy, [124, 82, 40], 12, { m: MAT.PETAL, b: 4 });
  }
  POST.outline(s, { k: 0.82 }); POST.normals(s, 0.9);
  return { s, meta: { ax: cx, ay: by + 1, sway: 1, foliage: true, kind: 'under' } };
}

/* ---------------- grass tufts (swaying, instanced) ---------------- */
export function tuft(seed, kind = 0) {
  const R = RNG(seed * 97 + 5), W = 13, H = kind === 2 ? 18 : 12, s = new SB(W, H), cx = W / 2, by = H - 1;
  const rr = kind === 1 ? PAL.susuki : [[34, 58, 44], [52, 86, 46], [78, 118, 54], [108, 146, 64], [140, 168, 84]];
  const nb = R.int(5, 9);
  for (let b = 0; b < nb; b++) {
    let x = cx + R.range(-3.5, 3.5), y = by; const a = R.range(-2.2, -0.95), L = R.range(5, H - 2), bend = R.range(-0.5, 0.5);
    for (let i = 0; i < L; i++) { const t = i / L; x += Math.cos(a + bend * t); y += Math.sin(a + bend * t); s.pz(x, y, rr[clamp(Math.floor(1 + t * 3.2), 0, rr.length - 1)], 1 + t, { m: MAT.BLADE, b: 1 }); }
  }
  if (kind === 3) { const fx = Math.round(cx + R.range(-2, 2)), fy = R.int(1, 3); const c = R.pick([PAL.flowerWhite, PAL.flowerYellow, PAL.flowerBlue, PAL.flowerPink]); s.px(fx, fy, c, { m: MAT.PETAL, z: 4, b: 2 }); s.px(fx + 1, fy, c.map(v => v * 0.85), { m: MAT.PETAL, z: 4, b: 2 }); }
  POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, sway: 1.2, shadow: 0, foliage: true, kind: 'tuft' } };
}

/* ---------------- moss mound / small ground plants ---------------- */
export function mossClump(seed, w = 16) {
  const s = new SB(w + 4, 10), cx = (w + 4) / 2;
  foliage(s, domeBlobs(cx, 6, w / 2, 3, Math.round(w / 3), 2.5, 3.6, seed, { zk: 0.5 }), { ramp: PAL.moss, cell: 1.6, seed, under: 0.4 });
  POST.outline(s, { k: 0.75 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: 9, sway: 0, shadow: 0, kind: 'under' } };
}

export function bamboo(seed, H = 150) {
  const R = RNG(seed * 5 + 2), W = 58, s = new SB(W, H + 2), baseY = H, cx = W / 2 + R.range(-3, 3), old = R() < 0.3;
  const culm = old ? PAL.bambooOld : PAL.bamboo, cw = R.range(2.2, 2.8), curve = R.range(-7, 7);
  const X = y => cx + curve * Math.pow(1 - y / H, 2), nodeGap = R.int(13, 17), ph = R.int(0, 12);
  for (let y = 8; y <= baseY; y++) { const xc = X(y), node = (y + ph) % nodeGap;
    for (let x = Math.floor(xc - cw - 1); x <= Math.ceil(xc + cw + 1); x++) { const sx = (x + 0.5 - xc) / cw; if (Math.abs(sx) > 1) continue;
      const t = 0.56 - sx * 0.25 + (node === 0 ? -0.4 : node === 1 ? 0.3 : 0); s.px(x, y, culm[clamp(Math.round(t * (culm.length - 1)), 0, culm.length - 1)], { z: Math.sqrt(1 - sx * sx) * cw + 1, m: MAT.BAMBOO, b: 1, n: cylN(sx) }); } }
  const leaves = PAL.bambooLeaf;
  const leaf = (x0, y0, a, L, z, k) => PX.stroke(x0, y0, x0 + Math.cos(a) * L, y0 + Math.sin(a) * L * 0.6 + L * 0.32, 1.25, 0.2, (x, y, t, sx) => s.pz(x, y, leaves[clamp(Math.round((0.5 + (Math.abs(sx) < 0.3 && t > 0.1 && t < 0.7 ? 0.16 : 0) + (k % 3 - 1) * 0.12 - t * 0.08) * 5), 0, 5)], z + (1 - t), { m: MAT.LEAF, b: 4 }));
  for (let y = 12; y < H * 0.6; y++) { if ((y + ph) % nodeGap !== 3) continue;
    for (const dir of [-1, 1]) { if (R() < 0.08) continue; const bl = R.range(8, 16) * (1 - y / H * 0.3), bx = X(y) + dir * bl, by = y - R.range(3, 7);
      PX.stroke(X(y), y, bx, by, 0.6, 0.5, (x, yy) => s.pz(x, yy, culm[1], 3, { m: MAT.BAMBOO, b: 2 }));
      const nl = R.int(8, 13); for (let k = 0; k < nl; k++) leaf(bx + R.range(-3, 3), by + R.range(-2, 2), (dir > 0 ? 0 : Math.PI) + dir * R.range(-0.5, 0.9), R.range(7, 12), 5 + R() * 3, k); } }
  for (let k = 0; k < 16; k++) leaf(X(10) + R.range(-4, 4), R.range(3, 18), R.range(-3, 0) - 0.3, R.range(7, 12), 7, k);
  POST.outline(s, { k: 0.74 }); POST.normals(s, 0.85);
  return { s, meta: { ax: Math.round(X(baseY)), ay: baseY + 1, sway: 1.5, foliage: true, occluder: true, kind: 'tree' } };
}
