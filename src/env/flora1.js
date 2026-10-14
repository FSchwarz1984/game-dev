/* =====================================================================
   env/flora1 — v0.1's flora generators, ported into the 2D atlas (albedo
   + height → normals + bulge + material) and extended. The owner liked
   their stylised shapes: cedars as dense spires of leaf clusters, the
   layered-disk trees (green ones read as pines, the red one is the red
   maple), bamboo, hydrangea, ferns, sasa, susuki, and above all the
   leaf-cluster painter: a hashed grid of small domes, each cell one of
   a few discrete tones, so silhouettes come out scalloped like
   hand-drawn clusters and the dynamic sun gives every cluster its own
   lit and shaded side (the normals come from the cell domes).
   Source: legacy/v0.1/src/art_flora.js (FLORA.clump, trunk, cedar,
   camphor crown, maple, bamboo, fern, sasa, kudzu, susuki, lily,
   hydrangea, dayflower, mushroom). New here: size and species
   parameters, the layered pine, the camphor crown lobe in the same
   language, 彼岸花 (higanbana), clover.
   Light from the top-left (baked tones) — the renderer adds the sun.
   ===================================================================== */
import { SB, PX, POST, MAT } from './paint.js';
import { RNG, clamp, lerp, hash2, hyp, ramp, TAU, drain } from './core.js';

/* v0.1's palette (legacy/v0.1/src/pixel.js), the colours the owner saw */
export const V1 = {
  cedar: ramp('#2d4a3c', 7, { lo: 0.55, hi: 0.55, hueShift: 0.07 }),
  cedarDeep: ramp('#223a33', 5, { lo: 0.5, hi: 0.45 }),
  camphor: ramp('#557f37', 7, { lo: 0.55, hi: 0.5, hueShift: 0.08 }),
  camphorNew: ramp('#8fb04a', 5, { lo: 0.45, hi: 0.4 }),
  maple: ramp('#5f8f3c', 7, { lo: 0.55, hi: 0.5, hueShift: 0.07 }),
  mapleRed: ramp('#a32f2a', 7, { lo: 0.55, hi: 0.45, hueShift: 0.04 }),
  pine: ramp('#3f6a3a', 7, { lo: 0.55, hi: 0.5, hueShift: 0.07 }),
  bamboo: ramp('#6f9a45', 6, { lo: 0.5, hi: 0.45 }),
  bambooOld: ramp('#a39a55', 5, { lo: 0.45, hi: 0.4 }),
  barkCedar: ramp('#6b4330', 6, { lo: 0.55, hi: 0.45 }),
  barkGrey: ramp('#6c6359', 6, { lo: 0.55, hi: 0.45 }),
  barkPine: ramp('#5e4a3e', 6, { lo: 0.55, hi: 0.45, hueShift: 0.04 }),
  moss: ramp('#566f30', 6, { lo: 0.5, hi: 0.45 }),
  fern: ramp('#4f7c39', 6, { lo: 0.5, hi: 0.5 }),
  sasa: ramp('#4c7a34', 6, { lo: 0.5, hi: 0.45 }),
  kudzu: ramp('#4a7034', 6, { lo: 0.5, hi: 0.42, satShift: -0.05 }),
  kudzuFlower: ramp('#9b4f9a', 4, { lo: 0.45, hi: 0.4 }),
  susuki: ramp('#8f9a5a', 5, { lo: 0.45, hi: 0.4 }),
  lily: ramp('#efe9dc', 4, { lo: 0.3, hi: 0.2 }),
  paper: ramp('#ece4d2', 4, { lo: 0.3, hi: 0.2 }),
  higan: ramp('#c8322a', 5, { lo: 0.5, hi: 0.35, hueShift: 0.02 }),
  clover: ramp('#4f7a3a', 5, { lo: 0.5, hi: 0.45 }),
};

/* ---------------- the leaf-cluster painter (v0.1 FLORA.clump) ----------------
   An ellipse of leaf cells on a jittered, staggered grid; each pixel belongs to its nearest cell;
   the cell picks one of a few tones (a few dark, a few light, most mid), the lower half of the clump
   is darker, the cracks between dark cells darker still; z = clump dome + cell dome, so the normals
   (POST.normals) light every cluster on its own upper-left. o: {seed, base (ramp index), mat, cell,
   droop, zk, bulge, bk, tint} */
export function clump(s, cx, cy, rx, ry, z0, rr, o = {}) {
  const R = RNG((o.seed || 1) * 7 + 3), n = rr.length, base = o.base ?? 3, mat = o.mat ?? MAT.LEAF;
  const cell = o.cell ?? 3.4, droop = o.droop || 0, zk = o.zk ?? 0.85;
  const pts = [];
  for (let gy = -ry - cell; gy <= ry + cell; gy += cell * 0.82) for (let gx = -rx - cell; gx <= rx + cell; gx += cell) {
    const x = gx + (R() - 0.5) * cell * 0.7 + ((Math.round(gy / cell) & 1) ? cell * 0.5 : 0), y = gy + (R() - 0.5) * cell * 0.6;
    const u = x / rx, v = y / ry, d = Math.sqrt(u * u + v * v); if (d > 1.02 - (R() * 0.18)) continue;
    pts.push({ x: cx + x, y: cy + y + droop * u * u * ry * 0.35, r: cell * R.range(0.62, 0.86), t: R(), d });
  }
  if (!pts.length) pts.push({ x: cx, y: cy, r: Math.max(rx, ry), t: 0.5, d: 0 });
  // bucket the cells on a coarse grid so each pixel only tests its neighbours (v0.1 tested them all)
  const G = Math.max(2, cell * 1.2), grid = new Map(), key = (i, j) => i * 73856 + j;
  for (const p of pts) { const k = key(Math.floor(p.x / G), Math.floor(p.y / G)); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(p); }
  const x0 = Math.floor(cx - rx - cell * 2), x1 = Math.ceil(cx + rx + cell * 2), y0 = Math.floor(cy - ry - cell * 2), y1 = Math.ceil(cy + ry + cell * 2 + droop * ry * 0.4);
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    let b1 = null, d1 = 1e9, d2 = 1e9;
    const gi = Math.floor((x + 0.5) / G), gj = Math.floor((y + 0.5) / G);
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) { const L = grid.get(key(gi + i, gj + j)); if (!L) continue;
      for (const p of L) { const d = hyp(x + 0.5 - p.x, (y + 0.5 - p.y) * 1.15) / p.r; if (d < d1) { d2 = d1; d1 = d; b1 = p; } else if (d < d2) d2 = d; } }
    if (!b1 || d1 > 1) continue;
    const u = (x + 0.5 - cx) / rx, v = (y + 0.5 - cy) / ry, D = Math.min(1, Math.sqrt(u * u + v * v));
    const dome = Math.sqrt(Math.max(0, 1 - D * D));
    const z = z0 + dome * Math.min(rx, ry) * zk + Math.sqrt(Math.max(0, 1 - d1 * d1)) * b1.r * 0.9;
    let t = base / (n - 1) + (b1.t < 0.22 ? -0.17 : b1.t > 0.8 ? 0.14 : 0) - Math.max(0, v) * 0.16 - b1.d * 0.06 + (o.tint || 0);
    if (o.rim && v < -0.35 && u < 0.4 && b1.t > 0.35) t += o.rim;          // sun along the upper rim
    if (d2 - d1 < 0.12 && b1.t > 0.5) t -= 0.12;
    const idx = clamp(Math.round(t * (n - 1)), 0, n - 1);
    s.pz(x, y, rr[idx], z, { m: mat, b: (o.bulge ?? 0) + dome * (o.bk ?? 2) });
  }
}

/* ---------------- a trunk (v0.1 FLORA.trunk): fibres, fissures, moss at the foot ---------------- */
export function trunk(s, cx, yTop, yBot, wTop, wBot, rr, o = {}) {
  const seed = o.seed || 1;
  for (let y = Math.floor(yTop); y <= yBot; y++) {
    const t = (y - yTop) / Math.max(1, yBot - yTop); let hw = lerp(wTop, wBot, t) / 2;
    if (o.flare && y > yBot - o.flare) hw += Math.pow((y - (yBot - o.flare)) / o.flare, 2) * (o.flareW || 3);
    const lean = (o.lean || 0) * (1 - t) + Math.sin(t * 3 + seed) * (o.wobble ?? 0.5);
    for (let x = Math.floor(cx + lean - hw - 1); x <= Math.ceil(cx + lean + hw + 1); x++) {
      const sx = (x + 0.5 - cx - lean) / hw; if (Math.abs(sx) > 1) continue;
      const col = Math.floor((x - cx - lean + 40) * (o.fib ?? 0.7));
      const f = hash2(col, Math.floor(y / (o.seg ?? 9)), seed), fis = hash2(col, Math.floor(y / 4), seed + 9) < 0.1;
      let tt = 0.55 + (f - 0.5) * 0.3 - (fis ? 0.3 : 0) - (y > yBot - 3 ? 0.12 : 0) - sx * 0.12;
      if (o.moss && y > yBot - o.moss && hash2(x >> 1, y >> 1, seed + 4) < 0.5 - (yBot - y) / o.moss * 0.4) { s.pz(x, y, V1.moss[clamp(Math.round((0.45 + (hash2(x, y, 2) - 0.5) * 0.3) * 5), 0, 5)], Math.sqrt(1 - sx * sx) * hw + 0.6, { m: MAT.MOSS, b: o.b ?? 1 }); continue; }
      s.pz(x, y, rr[clamp(Math.round(tt * (rr.length - 1)), 0, rr.length - 1)], Math.sqrt(1 - sx * sx) * hw + (fis ? -0.6 : 0), { m: MAT.BARK, b: (o.b ?? 1) + Math.sqrt(1 - sx * sx) });
    }
  }
}
const finish = (s, ao = 2, aoK = 0.25, out = 0.66, nk = 0.8) => { if (ao) POST.ao(s, ao, aoK); POST.outline(s, { k: out }); POST.normals(s, nk); return s; };

/* ---------------- cedar 杉: a dense spire of drooping tiers of leaf clusters (v0.1) ----------------
   H, W in px; o.lean (px at the top), o.thin (0..1: a slimmer, ragged crown — a suppressed tree) */
export function cedar(seed, H = 150, W = 46, o = {}) {
  const R = RNG(seed * 13 + 1), w = W + 18, h = H + 4, s = new SB(w, h), cx = Math.round(w / 2 + R.range(-1, 1)), baseY = h - 2;
  const crownBot = Math.round(H * R.range(0.52, 0.66)), top = 3, lean = o.lean ?? R.range(-2.5, 2.5);
  trunk(s, cx, top + 10, baseY, 2, R.range(5.5, 7) * (W / 46), V1.barkCedar, { seed, flare: 7, flareW: 3.5, moss: 8, wobble: 0.3, lean, b: 1 });
  const hwAt = y => { const t = clamp((y - top) / (crownBot - top), 0, 1); return (W / 2) * (Math.pow(t, 0.82) * (t > 0.86 ? 1 - (t - 0.86) * 1.2 : 1)) * (1 - (o.thin || 0) * 0.3) + 1.5; };
  const lx = y => lean * (1 - (y - top) / (baseY - top));
  const tiers = []; let y = crownBot - 3, k = 0;
  while (y > top + 6) { tiers.push({ y, k }); y -= R.range(7.5, 10) * (y < top + 40 ? 0.78 : 1); k++; }
  // a dark heart, so the gaps between tiers read as depth
  for (let yy = top + 4; yy < crownBot - 2; yy++) { const hw = hwAt(yy) * 0.55; for (let x = Math.floor(cx + lx(yy) - hw); x <= Math.ceil(cx + lx(yy) + hw); x++) s.pz(x, yy, V1.cedarDeep[1 + ((x + yy) & 1 && hash2(x, yy, seed) < 0.3 ? 1 : 0)], 2, { m: MAT.LEAF, b: 2 }); }
  for (let i = tiers.length - 1; i >= 0; i--) {
    const T = tiers[i], hw = hwAt(T.y), n = hw > 14 ? 4 : hw > 8 ? 3 : 2;
    if (o.thin && R() < o.thin * 0.35 && i > 1) continue;                     // a missing tier: a gap in a suppressed crown
    for (let j = 0; j < n; j++) {
      const f = n === 1 ? 0 : j / (n - 1) * 2 - 1, x = cx + lx(T.y) + f * hw * 0.72 + R.range(-1.5, 1.5);
      const rx = hw / n * 1.5 + 2.5, ry = R.range(3.6, 5) + hw * 0.06;
      const zf = 6 + (1 - Math.abs(f)) * 7 + (tiers.length - i) * 0.15;
      clump(s, x, T.y + Math.abs(f) * 2.6, rx, ry, zf, V1.cedar, { seed: seed * 31 + i * 7 + j, base: 3.2 + (i / tiers.length) * 0.5, cell: 2.8, droop: 1.3, bulge: 4 + (1 - Math.abs(f)) * 5, zk: 0.75 });
      for (let xx = Math.floor(x - rx * 0.8); xx <= x + rx * 0.8; xx++) { const yy = Math.round(T.y + ry * 0.9 + Math.abs(f) * 2.6 + Math.pow((xx - x) / rx, 2) * 2); if (s.a(xx, yy) && hash2(xx, yy, seed) < 0.7) s.mul(xx, yy, [0.72, 0.76, 0.82]); }
    }
  }
  for (let yy = 1; yy < top + 8; yy++) s.pz(cx + Math.round(lean), yy, V1.cedar[yy < 3 ? 4 : 3], 14, { m: MAT.LEAF, b: 7 });
  for (const [dx, dy] of [[-1, 5], [1, 6], [-1, 8], [1, 9], [-2, 9], [2, 10]]) s.pz(cx + Math.round(lean) + dx, top + dy, V1.cedar[dx < 0 ? 2 : 4], 13, { m: MAT.LEAF, b: 7 });
  finish(s, 2, 0.25, 0.66, 0.8);
  return { s, meta: { ax: cx, ay: baseY + 1, sway: 0.55, foliage: true, occluder: true, kind: 'tree' } };
}

/* ---------------- layered-disk tree (v0.1 maple): horizontal plates of leaf clusters on a leaning trunk ----------------
   o: {ramp, W, H, layers, lean, red, plates (per layer), flat (plate flattening), trunkW, barkRamp}.
   Green with dark needles = the pine the owner liked; red = the red maple; light green = a maple. */
export function layered(seed, o = {}) {
  const R = RNG(seed * 7 + 3), W = Math.round(o.W ?? 92), H = Math.round(o.H ?? 98), s = new SB(W + 40, H + 8), cx = (W + 40) / 2 + R.range(-3, 3), baseY = H + 6;
  const lean = o.lean ?? R.range(-8, 8), L = o.layers ?? 5, crownTop = baseY - H + 16, crownBot = crownTop + (L - 1) * (o.gap ?? 9);
  const bark = o.barkRamp ?? V1.barkGrey, tw = o.trunkW ?? 3.2;
  PX.stroke(cx, baseY, cx + lean, crownBot - 2, tw, tw * 0.53, (x, y, t, sx) => s.pz(x, y, bark[clamp(Math.round((0.52 - sx * 0.18 + (hash2(x >> 1, y >> 2, seed) - 0.5) * 0.15) * 5), 0, 5)], 2 + (1 - Math.abs(sx)) * 2, { m: MAT.BARK, b: 1 }));
  for (let k = 0; k < (o.branches ?? 5); k++) { const a = R.range(-1.3, 1.3); PX.stroke(cx + lean * 0.6, crownBot + 6 + k * 2, cx + lean + Math.sin(a) * W * 0.33, crownTop + 14 + R.range(-10, 6), 1.6, 0.8, (x, y) => s.pz(x, y, bark[2], 4, { m: MAT.BARK, b: 2 })); }
  const rr = o.ramp ?? (o.red ? V1.mapleRed : V1.maple), np = o.plates ?? 4, flat = o.flat ?? 0.58;
  for (let l = 0; l < L; l++) {
    const y = crownTop + l * (o.gap ?? 9) + R.range(-2, 2), wv = (W * 0.39) - Math.abs(l - (L - 1) / 2) * (W * 0.054);
    for (let k = 0; k < np; k++) { const x = cx + lean * (1 - l / (L + 1)) + R.range(-wv * 0.7, wv * 0.7), r = R.range(7, 11) * (W / 92);
      clump(s, x, y + R.range(-2, 2), r * 1.55, r * flat, 6 + l * 2 + R() * 4, rr, { seed: seed * 17 + l * 9 + k, base: o.base ?? 3.3, cell: o.cell ?? 2.6, zk: 0.5, bulge: 5, droop: 0.4, rim: o.rim ?? 0 }); }
  }
  finish(s, 2, 0.22, 0.7, 0.8);
  return { s, meta: { ax: Math.round(cx), ay: baseY + 1, sway: o.sway ?? 0.8, foliage: true, occluder: true, kind: 'tree' } };
}
/** the layered pine: dark needle disks, fewer and broader plates, a crooked dark trunk */
export function pine(seed, H = 110, lean = 0) {
  const R = RNG(seed * 5 + 11);
  return layered(seed + 40, { ramp: V1.pine, W: 104 + R.range(-6, 10), H, layers: R.int(4, 5), gap: 10, plates: 3, flat: 0.5, lean: lean ? lean * 26 : R.range(-10, 10), trunkW: 4.4, barkRamp: V1.barkPine, base: 3.0, cell: 2.4, rim: 0.12, branches: 4, sway: 0.4 });
}

/* ---------------- the camphor's crown lobe, in v0.1's language: a dark interior, then layered leaf
   masses — the broad ones in front and low, new growth on the top — each mass a cluster of cells
   lit on its own upper-left, separated by the dark of the interior ---------------- */
export function camphorLobe(seed, w = 220, h = 130, o = {}) { return drain(camphorLobeG(seed, w, h, o)); }
/** the lobe painter as a generator (yields between masses, for the async bake) */
export function* camphorLobeG(seed, w = 220, h = 130, o = {}) {
  const R = RNG(seed * 41 + 3), W = Math.ceil(w * 1.3) + 24, Hh = h + 60, s = new SB(W, Hh), cx = Math.round(W / 2), base = h + 34;
  // the interior: deep, cool green; limbs show in it
  PX.ell(cx, base - h * 0.48, w * 0.43, h * 0.4, (x, y) => s.pz(x, y, V1.cedarDeep[1 + ((x ^ y) & 1 && hash2(x, y, seed) < 0.4 ? 1 : 0)], 2, { m: MAT.LEAF, b: 2 }), { amp: 0.22, seed });
  for (let k = 0; k < 3; k++) { const x0 = cx + R.range(-w * 0.2, w * 0.2); PX.stroke(x0, base - h * 0.2, x0 + R.range(-w * 0.32, w * 0.32), base - h * 0.62, 4.5, 2, (x, y, t, sx) => s.pz(x, y, V1.barkGrey[clamp(Math.round((0.36 - sx * 0.12) * 5), 0, 5)], 4, { m: MAT.BARK, b: 4 })); }
  // the masses: a half-dome of clumps, front (low) ones biggest and nearest
  const ms = [];
  const N = Math.round(14 + w / 11);
  for (let i = 0; i < N; i++) {
    const a = R.range(-Math.PI - 0.3, 0.3), rr = Math.sqrt(R());
    const x = cx + Math.cos(a) * rr * w * 0.42, y = base - h * 0.46 + Math.sin(a) * rr * h * (Math.sin(a) > 0 ? 0.3 : 0.5) + R.range(-4, 4);
    ms.push({ x, y, r: R.range(14, 22) * (1 - rr * 0.2) * Math.min(1.15, w / 200), z: 10 + (1 - rr) * 26 + R() * 6 + (y - (base - h)) * 0.12 });
  }
  // the lowest masses hang along the bottom edge, touching the crown (never floating free under it)
  for (let i = 0; i < Math.round(w / 30); i++) ms.push({ x: cx + R.range(-w * 0.34, w * 0.34), y: base - h * R.range(0.2, 0.28), r: R.range(12, 16), z: 30 + R() * 8, low: true });
  ms.sort((a, b) => a.z - b.z);
  for (const [k, m] of ms.entries()) {
    if ((k & 3) === 3) yield;
    const top = m.y < base - h * 0.7;
    clump(s, m.x, m.y, m.r * 1.1, m.r * 0.88, m.z, top && !o.dark && R() < 0.75 ? V1.camphorNew : V1.camphor, { seed: seed * 101 + k, base: top ? 2.6 : m.low ? 2.7 : 3.1, cell: 4.2, zk: 0.65, bulge: 10 + m.z * 0.35, rim: 0.1 });
  }
  // a few leaves hanging under the lowest masses
  for (let k = 0; k < w / 8; k++) { const x = Math.round(cx + R.range(-w * 0.44, w * 0.44)); let y = Hh - 1; while (y > 0 && !s.a(x, y)) y--; if (y <= 0) continue; const Ln = R.int(1, 3); for (let j = 1; j <= Ln; j++) s.pz(x + (j === Ln && R() < 0.5 ? (R() < 0.5 ? -1 : 1) : 0), y + j, V1.camphor[clamp(2 - (j >> 1), 0, 6)], 60, { m: MAT.LEAF, b: 20 }); }
  yield; POST.ao(s, 2, 0.26); yield; POST.outline(s, { k: 0.7 }); POST.normals(s, 0.75);
  return { s, meta: { ax: cx, ay: Hh - 4, sway: 0.18, foliage: true, occluder: true, kind: 'camphorLobe' } };
}

/* ---------------- bamboo 孟宗竹 (v0.1) ---------------- */
export function bamboo(seed, H = 196) {
  const R = RNG(seed * 5 + 2), W = 54, s = new SB(W, H + 2), baseY = H, cx = W / 2 + R.range(-3, 3), old = R() < 0.3;
  const culm = old ? ramp('#9a9a58', 6, { lo: 0.5, hi: 0.4 }) : ramp('#6d9452', 6, { lo: 0.5, hi: 0.45, hueShift: 0.04 });
  const cw = R.range(2.3, 3), curve = R.range(-7, 7);
  const X = y => cx + curve * Math.pow(1 - y / H, 2);
  const nodeGap = R.int(14, 18), ph = R.int(0, 12);
  for (let y = 10; y <= baseY; y++) {
    const xc = X(y), node = (y + ph) % nodeGap;
    for (let x = Math.floor(xc - cw - 1); x <= Math.ceil(xc + cw + 1); x++) {
      const sx = (x + 0.5 - xc) / cw; if (Math.abs(sx) > 1) continue;
      let t = 0.56 + (node === 0 ? -0.4 : node === 1 ? 0.3 : node < 5 ? 0.1 : 0) + (old && hash2(x, y >> 1, seed + 2) < 0.06 ? -0.35 : 0) - sx * 0.14;
      s.px(x, y, culm[clamp(Math.round(t * 5), 0, 5)], { z: Math.sqrt(1 - sx * sx) * cw + 1, m: MAT.BAMBOO, b: 1 });
    }
  }
  const leaves = ramp('#4d7e3a', 6, { lo: 0.5, hi: 0.5, hueShift: 0.06 });
  const leaf = (x0, y0, a, L, z, k) => PX.stroke(x0, y0, x0 + Math.cos(a) * L, y0 + Math.sin(a) * L * 0.6 + L * 0.32, 1.25, 0.2, (x, y, t, sx) => {
    const mid = Math.abs(sx) < 0.3 && t > 0.1 && t < 0.7; s.pz(x, y, leaves[clamp(Math.round((0.5 + (mid ? 0.16 : 0) + (k % 3 - 1) * 0.12 - t * 0.08) * 5), 0, 5)], z + (1 - t), { m: MAT.LEAF, b: 4 });
  });
  for (let y = 14; y < H * 0.56; y++) {
    if ((y + ph) % nodeGap !== 3) continue;
    for (const dir of [-1, 1]) {
      if (R() < 0.08) continue;
      const bl = R.range(8, 16) * (1 - y / H * 0.3), bx = X(y) + dir * bl, by = y - R.range(3, 7);
      PX.stroke(X(y), y, bx, by, 0.6, 0.5, (x, yy) => s.pz(x, yy, culm[1], 3, { m: MAT.BAMBOO, b: 2 }));
      const nl = R.int(8, 13);
      for (let k = 0; k < nl; k++) leaf(bx + R.range(-3, 3), by + R.range(-2, 2), (dir > 0 ? 0 : Math.PI) + dir * R.range(-0.5, 0.9), R.range(7, 12), 5 + R() * 3, k);
    }
  }
  for (let k = 0; k < 18; k++) leaf(X(12) + R.range(-4, 4), R.range(4, 20), R.range(-3, 0) - 0.3, R.range(7, 12), 7, k);
  POST.outline(s, { k: 0.74 }); POST.normals(s, 0.85);
  return { s, meta: { ax: Math.round(cx), ay: baseY + 1, sway: 1.6, foliage: true, occluder: true, kind: 'tree' } };
}

/* ---------------- undergrowth (v0.1) ---------------- */
export function fern(seed, k = 1) { // a fountain of arching fronds; paired leaflets shrink toward each tip
  const R = RNG(seed * 3 + 9), W = Math.round(44 * k) + 4, H = Math.round(32 * k) + 2, s = new SB(W, H), cx = W / 2, by = H - 2;
  const nf = R.int(7, 9);
  const order = [...Array(nf).keys()].sort((p, q) => Math.abs(q - (nf - 1) / 2) - Math.abs(p - (nf - 1) / 2));
  for (const f of order) {
    const u = f / (nf - 1) * 2 - 1, a0 = -Math.PI / 2 + u * 1.25 + R.range(-0.1, 0.1), L = R.range(15, 21) * (1 - Math.abs(u) * 0.15) * k;
    let x = cx + u * 2, y = by, a = a0; const pts = [[x, y]]; const curl = u * 0.11 + R.range(-0.02, 0.02);
    for (let i = 0; i < 16; i++) { a += curl + 0.02 * Math.sign(u || 1); x += Math.cos(a) * L / 16; y += Math.sin(a) * L / 16 + i * 0.05 * Math.abs(u); pts.push([x, y]); }
    const zf = 3 + (1 - Math.abs(u)) * 3;
    for (let i = 1; i < pts.length; i++) {
      const t = i / pts.length, [px1, py1] = pts[i], [px0, py0] = pts[i - 1]; const dx = px1 - px0, dy = py1 - py0, dl = hyp(dx, dy) || 1;
      const nx = -dy / dl, ny = dx / dl, ll = ((1 - t) * 3.4 + 0.8) * k;
      for (const sd of [-1, 1]) for (let q = 0.5; q <= ll; q += 0.5) {
        const xx = px1 + nx * q * sd + dx / dl * q * 0.6, yy = py1 + ny * q * sd + dy / dl * q * 0.6 + q * 0.2;
        const tone = 0.5 + (sd * nx > 0 ? 0.1 : -0.06) + ((i >> 1) % 2 ? 0.06 : -0.04) - q / ll * 0.12 + (1 - Math.abs(u)) * 0.05;
        s.pz(xx, yy, V1.fern[clamp(Math.round(tone * 5), 0, 5)], zf + (1 - t) * 2 - q * 0.3, { m: MAT.LEAF, b: 2 + zf * 0.3 });
      }
      s.pz(px1, py1, V1.fern[1], zf + (1 - t) * 2 + 0.3, { m: MAT.LEAF, b: 2 + zf * 0.3 });
    }
  }
  POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  return { s, meta: { ax: Math.round(cx), ay: by + 1, sway: 0.9, shadow: 0, foliage: true, kind: 'under' } };
}
export function sasa(seed, k = 1) { // 熊笹 — broad blades with pale margins, held up and out
  const R = RNG(seed * 11 + 5), W = Math.round(36 * k) + 4, H = Math.round(30 * k) + 2, s = new SB(W, H), cx = W / 2, by = H - 1;
  const n = R.int(9, 12), stems = [];
  for (let j = 0; j < n; j++) stems.push({ u: R.range(-1, 1), k: j });
  stems.sort((p, q) => Math.abs(q.u) - Math.abs(p.u));
  for (const st of stems) {
    const u = st.u, a = -Math.PI / 2 + u * 1.35 + R.range(-0.15, 0.15), L = R.range(11, 15) * k, bx = cx + u * 5 * k;
    const mx = bx + Math.cos(a) * 4 * k, my = by - 6 * k, x1 = mx + Math.cos(a) * L, y1 = my + Math.sin(a) * L * 0.9 + Math.abs(u) * 4;
    PX.stroke(bx, by, mx, my, 0.5, 0.5, (x, y) => s.pz(x, y, V1.sasa[1], 1, { m: MAT.LEAF }));
    const z0 = 2 + (1 - Math.abs(u)) * 3;
    PX.stroke(mx, my, x1, y1, 2.6 * Math.max(0.8, k), 0.3, (x, y, t, sx) => {
      const edge = Math.abs(sx) > 0.74 && t > 0.12 && t < 0.9, mid = Math.abs(sx) < 0.18 && t < 0.8;
      s.pz(x, y, edge ? V1.susuki[3] : V1.sasa[clamp(Math.round((0.5 - sx * 0.14 + (mid ? 0.16 : 0) + (st.k % 2 ? 0.06 : -0.06)) * 5), 0, 5)], z0 + t * 2 + (1 - Math.abs(sx)), { m: MAT.LEAF, b: 2 + z0 * 0.3 });
    });
  }
  POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  return { s, meta: { ax: Math.round(cx), ay: by + 1, sway: 0.9, shadow: 0, foliage: true, kind: 'under' } };
}
export function kudzu(seed) { // 葛 — trifoliate leaves smothering a bank; silver undersides; grape-purple spikes
  const R = RNG(seed * 19 + 4), W = 64, H = 38, s = new SB(W, H), rr = V1.kudzu, under = ramp('#a3b18c', 4, { lo: 0.35, hi: 0.3 });
  const leaflet = (x, y, a, L, z, flip) => PX.stroke(x, y, x + Math.cos(a) * L, y + Math.sin(a) * L * 0.78, L * 0.5, 0.5, (xx, yy, t, sx) => {
    const vein = Math.abs(sx) < 0.14 && t < 0.88; const col = flip ? under[clamp(Math.round((0.62 - sx * 0.1 + (vein ? 0.2 : 0)) * 3), 0, 3)] : rr[clamp(Math.round((0.46 + (vein ? 0.2 : 0) - sx * 0.12 - t * 0.05) * 5), 0, 5)];
    s.pz(xx, yy, col, z + (1 - Math.abs(sx)) * 1.4 + t * 0.5, { m: MAT.LEAF, b: 2 });
  });
  const L = [];
  for (let k = 0; k < 30; k++) L.push({ x: R.range(7, W - 7), y: R.range(9, H - 5), sz: R.range(5, 7.5), a: R.range(-0.5, 0.5) - Math.PI / 2, flip: R() < 0.12 });
  L.sort((p, q) => p.y - q.y);
  for (const l of L) { const z = 2 + l.y * 0.25; leaflet(l.x, l.y, l.a, l.sz, z, l.flip); leaflet(l.x, l.y, l.a - 1.3, l.sz * 0.85, z - 0.3, l.flip); leaflet(l.x, l.y, l.a + 1.3, l.sz * 0.85, z - 0.3, l.flip); }
  for (let k = 0; k < 5; k++) { const x = R.range(8, W - 8) | 0, y = R.range(3, H - 14) | 0; for (let j = 0; j < 9; j++) { const c = V1.kudzuFlower[clamp(Math.round((0.4 + (j % 2 ? 0.2 : -0.1) + j / 9 * 0.3) * 3), 0, 3)]; s.pz(x + (j % 2), y + j, c, 18 - j * 0.2, { m: MAT.PETAL, b: 5 }); if (j % 2 === 0 && j < 7) s.pz(x - 1, y + j, V1.kudzuFlower[1], 17, { m: MAT.PETAL, b: 5 }); } }
  POST.outline(s, { k: 0.74 }); POST.normals(s, 0.9);
  return { s, meta: { ax: W / 2, ay: H, sway: 0.5, shadow: 0, foliage: true, kind: 'under' } };
}
export function susuki(seed, plumes = true) { // 芒 — arching blades and silver plumes, combed by the wind
  const R = RNG(seed * 23 + 8), W = 48, H = 58, s = new SB(W, H), cx = W / 2, by = H - 1;
  const blade = ramp('#7f8f4c', 5, { lo: 0.45, hi: 0.4 }), plume = ramp('#ddd2c2', 4, { lo: 0.3, hi: 0.2, hueShift: 0.02 });
  for (let k = 0; k < 22; k++) {
    const a = R.range(-2.8, -0.35), Lb = R.range(14, 27), bend = R.range(0.35, 0.95) * (Math.cos(a) > 0 ? 1 : -1);
    let x = cx + R.range(-3, 3), y = by;
    for (let i = 0; i < Lb; i++) { const t = i / Lb, ang = a + bend * t * t; x += Math.cos(ang); y += Math.sin(ang); s.pz(x, y, blade[clamp(Math.round((0.42 + t * 0.3 + (k % 3 - 1) * 0.1) * 4), 0, 4)], 2 + t * 4, { m: MAT.BLADE, b: 2 }); }
  }
  const np = plumes ? R.int(3, 5) : 0;
  for (let k = 0; k < np; k++) {
    let x = cx + R.range(-4, 4), y = by - 6; const a = R.range(-2.05, -1.1), Lp = R.range(34, 46), lean = R.range(0.5, 0.8) * (Math.cos(a) >= 0 ? 1 : -1);
    for (let i = 0; i < Lp; i++) {
      const t = i / Lp, ang = a + lean * t * t * 1.2; x += Math.cos(ang); y += Math.sin(ang);
      s.pz(x, y, t < 0.55 ? blade[2] : plume[2], 6 + t * 2, { m: MAT.BLADE, b: 3 });
      if (t > 0.55 && i % 2 === 0) { const hl = 2 + Math.round((1 - Math.abs(t - 0.78) * 3.5) * 3); const ha = ang + lean * 1.9;
        for (let q = 1; q <= hl; q++) s.pz(x + Math.cos(ha) * q, y + Math.sin(ha) * q + q * 0.55, plume[clamp(3 - Math.floor(q / hl * 3), 0, 3)], 7 + t * 2 - q * 0.2, { m: MAT.BLADE, b: 3 }); }
    }
  }
  POST.outline(s, { k: 0.84 }); POST.normals(s, 0.8);
  return { s, meta: { ax: Math.round(cx), ay: by + 1, sway: 1.8, shadow: 0, foliage: true, kind: 'under' } };
}
export function lily(seed) { // 山百合 — heavy white trumpets with a golden band, crimson freckles
  const R = RNG(seed * 29 + 1), W = 24, H = 36, s = new SB(W, H), cx = W / 2 + R.range(-1, 1), by = H - 1;
  const top = R.int(10, 13);
  PX.stroke(cx, by, cx + R.range(-2, 2), top, 0.6, 0.6, (x, y) => s.pz(x, y, V1.fern[2], 2, { m: MAT.LEAF }));
  for (let k = 0; k < 7; k++) { const y = by - 3 - k * 3, d = k % 2 ? 1 : -1; PX.stroke(cx, y, cx + d * 6, y - 3, 1.2, 0.2, (x, yy, t, sx) => s.pz(x, yy, V1.fern[clamp(3 - (sx > 0 ? 1 : 0), 0, 5)], 3, { m: MAT.LEAF, b: 1 })); }
  const nf = R.int(1, 3);
  for (let f = 0; f < nf; f++) {
    const fx = cx + (f - (nf - 1) / 2) * 7, fy = top + (f % 2) * 3;
    for (let p = 0; p < 6; p++) { const a = p / 6 * TAU + 0.3; PX.stroke(fx, fy, fx + Math.cos(a) * 5.5, fy + Math.sin(a) * 4.2 + 1, 1.7, 0.5, (x, y, t, sx) => {
      const stripe = Math.abs(sx) < 0.3 && t < 0.75; const dot = !stripe && hash2(x, y, f * 7 + p) < 0.16 && t > 0.25 && t < 0.8;
      s.pz(x, y, stripe ? [234, 192, 80] : dot ? [172, 46, 40] : V1.lily[clamp(Math.round((0.75 - t * 0.3 + (sx > 0 ? 0.1 : -0.05)) * 3), 0, 3)], 8 + (1 - t) * 3, { m: MAT.PETAL, b: 4 }); }); }
    s.pz(fx, fy, [124, 82, 40], 12, { m: MAT.PETAL, b: 4 }); s.pz(fx + 1, fy - 1, [196, 120, 50], 12, { m: MAT.PETAL, b: 4 });
  }
  POST.outline(s, { k: 0.82 }); POST.normals(s, 0.9);
  return { s, meta: { ax: Math.round(cx), ay: by + 1, sway: 1, shadow: 0, foliage: true, kind: 'under' } };
}
export function hydrangea(seed, k = 1) { // 紫陽花, past its best in August — blue going to dusty violet
  const R = RNG(seed * 31 + 2), W = Math.round(36 * k), H = Math.round(30 * k), s = new SB(W, H);
  for (let j = 0; j < 8; j++) clump(s, R.range(7, W - 7), R.range(11, H - 6), R.range(5, 7.5) * k, R.range(4, 5.5) * k, 2 + R() * 3, V1.sasa, { seed: seed + j, base: 2.6, cell: 3.2, zk: 0.6 });
  const fl = [ramp('#6f86c4', 5, { lo: 0.4, hi: 0.35 }), ramp('#9a7fbf', 5, { lo: 0.4, hi: 0.35 }), ramp('#8d9fc9', 5, { lo: 0.4, hi: 0.3 })];
  for (let j = 0; j < Math.round(5 * k); j++) clump(s, R.range(8, W - 8), R.range(8, H - 10), R.range(4, 5.5), R.range(3.6, 4.8), 9 + R() * 2, R.pick(fl), { seed: seed * 5 + j, base: 2.4, cell: 1.9, zk: 0.9, mat: MAT.PETAL, bulge: 3 });
  POST.outline(s, { k: 0.74 }); POST.normals(s, 1);
  return { s, meta: { ax: W / 2, ay: H - 2, sway: 0.4, shadow: 0, foliage: true, kind: 'under' } };
}
export function dayflower(seed) { // 露草 — tiny blue flags in the wet grass
  const R = RNG(seed * 37 + 3), W = 16, H = 12, s = new SB(W, H);
  for (let k = 0; k < 5; k++) { const x = R.range(3, W - 3); PX.stroke(x, H - 1, x + R.range(-3, 3), R.range(3, H - 3), 0.5, 0.5, (xx, yy) => s.pz(xx, yy, V1.fern[2 + (k & 1)], 1, { m: MAT.LEAF })); }
  for (let k = 0; k < 3; k++) { const x = R.range(3, W - 4) | 0, y = R.range(2, H - 6) | 0; s.pz(x, y, [58, 100, 196], 4, { m: MAT.PETAL, b: 2 }); s.pz(x + 1, y, [86, 132, 222], 4, { m: MAT.PETAL, b: 2 }); s.pz(x, y + 1, [242, 212, 90], 4, { m: MAT.PETAL, b: 2 }); }
  POST.normals(s, 1);
  return { s, meta: { ax: W / 2, ay: H, sway: 0.6, shadow: 0, kind: 'under' } };
}
export function mushroom(seed) {
  const R = RNG(seed * 41 + 6), W = 14, H = 11, s = new SB(W, H);
  const cap = R() < 0.5 ? ramp('#b07a4c', 4) : ramp('#d9cfb4', 4);
  for (let k = 0; k < 3; k++) { const x = 3 + k * 3.5 + R.range(-1, 1), h = R.range(3, 6), r = R.range(1.8, 2.8);
    PX.stroke(x, H - 1, x, H - 1 - h, 0.7, 0.6, (xx, yy) => s.pz(xx, yy, V1.paper[2], 2, { m: MAT.PAPER }));
    PX.ell(x, H - 1 - h, r, r * 0.6, (xx, yy, u, v, d) => s.pz(xx, yy, cap[clamp(Math.round((0.55 - v * 0.3) * 3), 0, 3)], 4 + (1 - d) * 2, { m: MAT.CLOTH, b: 2 })); }
  POST.normals(s, 1);
  return { s, meta: { ax: W / 2, ay: H, sway: 0, shadow: 0, kind: 'under' } };
}

/* ---------------- new: 彼岸花 — red spider lilies on bare stems, by the graves at the equinox ---------------- */
export function higanbana(seed, n = 0) {
  const R = RNG(seed * 43 + 7), W = 26, H = 26, s = new SB(W, H), by = H - 1, nf = n || R.int(3, 6), rr = V1.higan;
  const heads = [];
  for (let f = 0; f < nf; f++) heads.push({ x: R.range(5, W - 5), y: R.range(5, 12), z: R.range(4, 8) });
  heads.sort((a, b) => a.z - b.z);
  for (const h of heads) {
    PX.stroke(h.x + R.range(-1.5, 1.5), by, h.x, h.y + 2, 0.55, 0.5, (x, y, t) => s.pz(x, y, V1.fern[t > 0.5 ? 3 : 2], 1 + t, { m: MAT.LEAF, b: 1 }));
    // six curled petals and the long stamens sweeping up and out
    for (let p = 0; p < 6; p++) { const a = p / 6 * TAU + R.range(-0.2, 0.2), L = R.range(2.6, 3.6);
      PX.stroke(h.x, h.y, h.x + Math.cos(a) * L, h.y + Math.sin(a) * L * 0.7, 0.9, 0.4, (x, y, t) => s.pz(x, y, rr[clamp(Math.round(3 - t * 1.5 + (Math.sin(a) > 0 ? -1 : 0)), 0, 4)], h.z + 2 - t, { m: MAT.PETAL, b: 3 })); }
    for (let k = 0; k < 6; k++) { const a = -Math.PI / 2 + (k / 5 - 0.5) * 2.6, L = R.range(4, 6);
      for (let i = 1; i <= L; i++) { const t = i / L, x = h.x + Math.cos(a) * i, y = h.y + Math.sin(a) * i * 0.8 - t * t * 1.5; s.pz(x, y, i === Math.round(L) ? [236, 196, 120] : rr[4], h.z + 3, { m: MAT.PETAL, b: 3 }); } }
    s.pz(h.x, h.y, rr[1], h.z + 3.5, { m: MAT.PETAL, b: 3 });
  }
  POST.outline(s, { k: 0.78 }); POST.normals(s, 1);
  return { s, meta: { ax: W / 2, ay: by + 1, sway: 0.7, shadow: 0, foliage: true, kind: 'under' } };
}

/* preview for tools/env/sheet.mjs */
export function PREVIEW() {
  return [
    ['cedar', () => cedar(1, 150, 46)], ['cedarB', () => cedar(3, 210, 56)], ['cedarThin', () => cedar(5, 170, 40, { thin: 0.7 })],
    ['pine', () => pine(1, 110)], ['pineLean', () => pine(9, 118, 0.9)], ['maple', () => layered(3)], ['mapleR', () => layered(9, { red: true })], ['mapleS', () => layered(5, { W: 70, H: 76, layers: 4 })],
    ['lobe', () => camphorLobe(11, 196, 112)],
    ['bamboo', () => bamboo(1, 180)], ['fern', () => fern(1)], ['sasa', () => sasa(1)], ['kudzu', () => kudzu(1)], ['susuki', () => susuki(1)], ['lily', () => lily(1)],
    ['hydr', () => hydrangea(1)], ['dayfl', () => dayflower(1)], ['mush', () => mushroom(1)], ['higan', () => higanbana(1)],
  ];
}
