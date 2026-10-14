/* =====================================================================
   env/camphor — 大楠, the great camphor at the pass summit (御神木).
   It must read as enormous: the trunk is ~5 m across (100 px) and flares
   to ~10 m at its buttresses, the crown spans ~44 m and rises to ~27 m.
   Built from parts so that depth, shadows and fades work:
     - the trunk sprite: buttress roots, furrowed bark plates, burls, moss,
       lichen, ferns in the crotches, a hollow at the foot, two low limbs
       (west over the hut, east over the shrine), the fork into the crown,
       and the shimenawa with shide at ~3 m (it is protected: the one
       "cannot take" marker is the shimenawa);
     - 14 crown lobes, each a cumulus of leaf masses with a hanging
       fringe, placed in world space around the trunk (front lobes low and
       to the sides so the trunk stays visible, back lobes high);
     - the surface roots are terrain (env/home.js layoutTerrain), so they
       are walls you walk around.
   Light from the top-left; camphor greens from PAL.camphor; new growth on
   the sunlit tops from PAL.camphorNew.
   ===================================================================== */
import { SB, PX, POST, MAT, mass, cylN } from './paint.js';
import { PAL } from './palette.js';
import { RNG, clamp, lerp, hash2, hyp, vnoise } from './core.js';
import { fern } from './flora.js';

const BARK = PAL.barkCamphor;

/* ---------------- the trunk ---------------- */
export function camphorTrunk(seed = 3) {
  const W = 400, H = 300, s = new SB(W, H), cx = 200, base = 284;
  const R = RNG(seed);
  if (!s.N) s.N = new Float32Array(W * H * 3);
  // limbs behind the trunk first (the fork into the crown), then the trunk, then low limbs in front
  const limb = (pts, w0, w1, b0, b1, zf) => {
    let total = 0; for (let i = 0; i < pts.length - 1; i++) total += hyp(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
    let acc = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i], [bx, by] = pts[i + 1], L = hyp(bx - ax, by - ay);
      PX.stroke(ax, ay, bx, by, lerp(w0, w1, acc / total) / 2, lerp(w0, w1, (acc + L) / total) / 2, (x, y, t, sx) => {
        const u = (acc + t * L) / total; const n = cylN(sx * 0.9, 0.25);
        const fur = hash2(Math.floor((sx + 1) * 3), Math.floor((acc + t * L) / 6), seed + 5) < 0.2;
        let tt = 3.4 - sx * 1.6 + (fur ? -1.4 : 0) + (hash2(x >> 1, y >> 1, seed) - 0.5) * 0.6;
        if (hash2(x >> 1, y >> 1, seed + 7) < 0.22 && sx < -0.1) { s.pz(x, y, PAL.moss[clamp(Math.round(2.6 - sx), 1, 5)], zf + n[2] * w0 * 0.3, { m: MAT.MOSS, b: lerp(b0, b1, u) + n[2] * 6, n }); return; }
        s.pz(x, y, BARK[clamp(Math.round(tt + (bayer2(x, y) - 0.5) * 0.6), 0, BARK.length - 1)], zf + n[2] * w0 * 0.3, { m: MAT.BARK, b: lerp(b0, b1, u) + n[2] * 6, n });
      });
      acc += L;
    }
  };
  limb([[cx - 14, base - 160], [cx - 34, base - 206], [cx - 70, base - 248], [cx - 122, base - 290]], 62, 18, 40, 0, 4);
  limb([[cx + 16, base - 164], [cx + 34, base - 212], [cx + 64, base - 254], [cx + 108, base - 296]], 58, 18, 40, 0, 4);
  limb([[cx + 2, base - 176], [cx + 6, base - 232], [cx - 4, base - 300]], 56, 26, 36, 0, 5);
  limb([[cx - 30, base - 214], [cx - 18, base - 262], [cx - 26, base - 300]], 26, 12, 20, 0, 3);
  // the trunk proper: half width over height, buttresses near the foot
  const butt = [-0.98, -0.52, 0.04, 0.5, 0.96].map((a, i) => ({ a, w: [22, 15, 12, 16, 24][i], lift: [26, 18, 12, 18, 28][i] }));
  const hwAt = h => lerp(53, 44, clamp(h / 200, 0, 1)) + 40 * Math.exp(-h / 24) - Math.max(0, h - 168) * 0.9;
  const lean = h => Math.sin(h * 0.012) * 4 + h * 0.03;
  for (let h = -2; h <= 186; h++) {
    const y = base - h, hw = hwAt(h), xc = cx + lean(h);
    // silhouette with buttress bumps at the foot
    let xl = xc - hw, xr = xc + hw;
    for (const b of butt) { const bump = b.w * Math.exp(-h / b.lift); if (b.a < -0.8) xl -= bump; if (b.a > 0.8) xr += bump; }
    for (let x = Math.floor(xl); x <= Math.ceil(xr); x++) {
      const sx = clamp((x + 0.5 - (xl + xr) / 2) / ((xr - xl) / 2), -1, 1);
      // arc-length coordinate around the cylinder: furrows crowd toward the edges
      const U = Math.asin(sx) * 52;
      // buttress ridges: raised bands that run down into the roots
      let ridge = 0; for (const b of butt) { const d = (sx - b.a) / 0.13; ridge += Math.exp(-d * d) * Math.exp(-h / (b.lift * 1.6)); }
      // furrows: wandering vertical lines ~9 px apart in U
      const fu = U + Math.sin(h * 0.045 + Math.floor(U / 8)) * 2.2 + vnoise(U * 0.08, h * 0.02, seed) * 5;
      const fi = Math.floor(fu / 8), ff = fu / 8 - fi;
      const furrow = ff < 0.2 || (ff > 0.52 && ff < 0.62 && hash2(fi, Math.floor(h / 23), seed + 2) < 0.35);
      const crack = !furrow && ((h + Math.floor(hash2(fi, 3, seed) * 15)) % 15) === 0 && hash2(fi, Math.floor(h / 15), seed + 4) < 0.75;
      const n = cylN(sx * 0.94, 0.05);
      let t = 4.0 - sx * 2.4 + ridge * 1.1 + (hash2(fi, Math.floor(h / 7), seed) - 0.5) * 0.8 + (ff > 0.2 && ff < 0.34 ? 1.0 : 0);
      if (furrow) t -= 2.7; if (crack) t -= 1.8;
      if (h < 14) t -= (14 - h) * 0.12;
      let col = BARK[clamp(Math.round(t + (bayer2(x, y) - 0.5) * 0.7), 0, BARK.length - 1)], mat = MAT.BARK;
      // moss: on the lit, upward-facing side and down at the foot, in clumps
      const mz = vnoise(x * 0.06, y * 0.045, seed + 11) * 0.75 + vnoise(x * 0.22, y * 0.22, seed + 12) * 0.25;
      const mossK = (sx < 0.0 ? 0.6 : 0.72) - (h < 70 ? (70 - h) / 70 * 0.16 : 0) - (h > 150 ? 0.06 : 0);
      if (mz > mossK && !furrow) { col = PAL.moss[clamp(Math.round(2.4 - sx * 1.2 + (mz - mossK) * 6 + (bayer2(x, y) - 0.5)), 0, 5)]; mat = MAT.MOSS; }
      else if (hash2(x >> 1, y >> 1, seed + 13) < 0.025 && !furrow) col = PAL.lichen[1 + (hash2(x, y, 3) < 0.5 ? 1 : 0)];
      const z = Math.sqrt(1 - sx * sx) * hw * 0.6 + 10;
      s.pz(x, y, col, z, { m: mat, b: Math.sqrt(1 - sx * sx) * 50 + ridge * 6, n });
    }
  }
  // burls: round knots with ring shading
  for (const [bx, bh, br] of [[-28, 120, 8], [24, 150, 6], [36, 72, 7]]) {
    const xc = cx + bx + lean(bh), yc = base - bh;
    PX.ell(xc, yc, br, br * 0.9, (x, y, u, v, d) => { const ring = Math.floor(d * 3.5) % 2; const t = 4.2 - u * 1.6 - v * 1.4 - (ring ? 0.8 : 0) - (d > 0.85 ? 1.2 : 0); s.pz(x, y, BARK[clamp(Math.round(t), 0, BARK.length - 1)], 80, { m: MAT.BARK, b: 56 + (1 - d) * 4, n: [u * 0.7, -v * 0.7, Math.sqrt(Math.max(0.1, 1 - d * d))] }); });
  }
  // the hollow (洞) at the foot, between two buttresses
  { const xc = cx - 30, yc = base - 26;
    PX.ell(xc, yc, 13, 17, (x, y, u, v, d) => { const deep = d < 0.75; const t = deep ? 0.3 + v * 0.3 : 1.4 - u * 0.6; const c = deep ? [34 + v * 10, 28 + v * 8, 26 + v * 6] : BARK[clamp(Math.round(t), 0, 7)]; s.pz(x, y, c, 82, { m: MAT.BARK, b: deep ? 20 : 54, n: deep ? [0, 0, 1] : [-u * 0.6, v * 0.5, 0.6] }); }, { amp: 0.12, seed: 5 });
    for (let x = xc - 9; x <= xc + 9; x++) { const y = Math.round(yc + 16 + Math.abs(x - xc) * 0.15); if (s.a(x, y)) s.px(x, y, PAL.moss[3], { m: MAT.MOSS, z: 83, b: 55 }); } }
  // low limbs reaching west over the hut and east over the shrine (in front of the trunk)
  limb([[cx - 26, base - 112], [cx - 66, base - 132], [cx - 118, base - 136], [cx - 176, base - 128], [cx - 196, base - 122]], 40, 9, 54, 80, 90);
  limb([[cx - 120, base - 136], [cx - 146, base - 160], [cx - 160, base - 176]], 9, 4, 72, 76, 91);
  limb([[cx + 26, base - 122], [cx + 70, base - 142], [cx + 124, base - 146], [cx + 178, base - 140], [cx + 198, base - 134]], 38, 9, 54, 76, 90);
  limb([[cx + 128, base - 146], [cx + 150, base - 168], [cx + 158, base - 184]], 9, 4, 70, 74, 91);
  // ferns in the crotches and on the buttresses
  for (const [fx, fy, sz] of [[cx - 52, base - 118, 0.7], [cx + 44, base - 126, 0.6], [cx - 62, base - 6, 0.8], [cx + 58, base - 10, 0.7], [cx - 6, base - 186, 0.6]]) {
    const f = fern(Math.round(fx * 7 + fy), sz).s; s.blit(f, Math.round(fx - f.w / 2), Math.round(fy - f.h + 3), { dz: 95 });
  }
  // the shimenawa: a fat twisted straw rope across the front at ~3 m, shide hanging from it, a tassel at the front
  const ry = base - 62, rw = 9;
  const ropeY = x => { const sx = (x - cx - lean(62)) / (hwAt(62) + 2); return ry + (1 - sx * sx) * 7; };
  for (let x = Math.floor(cx - hwAt(62) - 3 + lean(62)); x <= cx + hwAt(62) + 3 + lean(62); x++) {
    const yc = ropeY(x); const sx = (x - cx - lean(62)) / (hwAt(62) + 2);
    for (let k = -rw / 2; k <= rw / 2; k++) {
      const v = k / (rw / 2), twist = ((x * 0.8 - k * 1.6 + 100) % 6) < 3;
      const t = 2.6 - v * 1.4 + (twist ? 0.7 : -0.5) - Math.abs(sx) * 0.8 - (Math.abs(v) > 0.8 ? 0.9 : 0);
      s.pz(x, Math.round(yc + k), PAL.rope[clamp(Math.round(t), 0, 4)], 120, { m: MAT.ROPE, b: 58 + (1 - Math.abs(sx)) * 6 + (1 - Math.abs(v)) * 2, n: [sx * 0.5, -v * 0.8, 0.5] });
    }
    const sy = Math.round(yc + rw / 2 + 1); if (s.a(x, sy)) s.mul(x, sy, [0.55, 0.55, 0.62]); // the rope's shadow on the bark
  }
  for (const fx of [-34, -12, 12, 34]) shide(s, Math.round(cx + lean(62) + fx), Math.round(ropeY(cx + lean(62) + fx) + rw / 2), 125);
  // tassel bundle (房) at the front centre
  { const tx = Math.round(cx + lean(62)), ty = Math.round(ropeY(cx + lean(62)) + rw / 2);
    for (let k = 0; k < 7; k++) for (let y = ty; y < ty + 10 + (k % 3); y++) s.pz(tx - 3 + k, y, PAL.straw[clamp(3 - (k === 0 ? 1 : 0) + (y > ty + 6 ? -1 : 0), 0, 5)], 126, { m: MAT.STRAW, b: 64 }); }
  POST.ao(s, 3, 0.2); POST.outline(s, { k: 0.6, hue: 0.02 }); POST.normals(s, 0.9);
  return { s, meta: { ax: cx, ay: base + 1, sway: 0, foliage: false, occluder: true, kind: 'camphorTrunk' } };
}

/** 紙垂: paper folded into a four-step zigzag */
export function shide(s, x, y, z) {
  const seq = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [2, 2], [3, 2], [1, 3], [2, 3], [3, 3], [3, 4], [4, 4], [2, 5], [3, 5], [4, 5]];
  for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2, PAL.paper[dy % 2 ? 2 : 4], z, { m: MAT.PAPER, b: 64 });
  for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2 + 1, PAL.paper[1], z - 0.2, { m: MAT.PAPER, b: 64 });
}

/* ---------------- a crown lobe ----------------
   w, h: size in px; a cumulus of leaf masses with a hanging fringe. */
export function camphorLobe(seed, w = 220, h = 130, o = {}) {
  const R = RNG(seed * 41 + 3), W = w + 24, Hh = h + 36, s = new SB(W, Hh), cx = W / 2, base = h + 12;
  const rr = PAL.camphor;
  // limbs glimpsed through the lower gaps
  for (let k = 0; k < 3; k++) { const x0 = cx + R.range(-w * 0.2, w * 0.2); PX.stroke(x0, base + 6, x0 + R.range(-w * 0.3, w * 0.3), base - h * 0.5, 5, 2, (x, y, t, sx) => s.pz(x, y, BARK[clamp(Math.round(1.6 - sx), 0, 7)], 1, { m: MAT.BARK, b: 2 })); }
  const ms = [];
  const nb = Math.max(3, Math.round(w / 58));
  for (let k = 0; k < nb; k++) { const f = nb === 1 ? 0 : k / (nb - 1) * 2 - 1; ms.push({ x: cx + f * w * 0.36 + R.range(-6, 6), y: base - h * 0.22 + Math.abs(f) * h * 0.06 + R.range(-3, 3), rx: w / nb * 0.68 + R.range(-3, 5), ry: h * 0.26 + R.range(-3, 3), z: 40 + (1 - Math.abs(f)) * 6, droop: R.range(0.1, 0.3), seed: k, tone: -0.03 }); }
  const nm = Math.max(2, nb - 1);
  for (let k = 0; k < nm; k++) { const f = nm === 1 ? 0 : k / (nm - 1) * 2 - 1; ms.push({ x: cx + f * w * 0.28 + R.range(-6, 6), y: base - h * 0.5 + R.range(-4, 4), rx: w / nm * 0.6 + R.range(-3, 4), ry: h * 0.27, z: 30 + (1 - Math.abs(f)) * 5, droop: 0.15, seed: 10 + k, tone: 0.03 }); }
  const nt = R() < 0.5 ? 1 : 2;
  for (let k = 0; k < nt; k++) ms.push({ x: cx + (nt === 1 ? 0 : (k ? 1 : -1) * w * 0.16) + R.range(-8, 8), y: base - h * 0.74 + R.range(-3, 3), rx: w * (nt === 1 ? 0.3 : 0.22), ry: h * 0.26, z: 22, droop: 0.1, seed: 20 + k, tone: 0.07, top: true });
  ms.sort((a, b) => a.z - b.z);
  const group = { x: cx - w * 0.05, y: base - h * 0.42, rx: w * 0.56, ry: h * 0.62, k: 0.62 };
  for (const m of ms) mass(s, m, { ramp: m.top && !o.dark ? mixRamp(rr, PAL.camphorNew) : rr, cell: 3.4, seed: seed * 3, tone: (o.tone || 0) - 0.04, under: 0.8, rim: 0.1, cellK: 0.45, group, base: 0.3, litK: 0.52 });
  // the hanging fringe along the bottom edge
  const nf = Math.round(w / 22);
  for (let k = 0; k < nf; k++) { const x = cx + R.range(-w * 0.44, w * 0.44); const y = base + R.range(-2, 6); mass(s, { x, y, rx: R.range(6, 11), ry: R.range(5, 7), z: 46, droop: 0.6, seed: 40 + k, tone: -0.1 }, { ramp: rr, cell: 3, seed: seed * 3 + 1, under: 1.1, rim: 0.0, base: 0.3, litK: 0.4 }); }
  // dangling leaf clusters
  for (let k = 0; k < w / 6; k++) { const x = Math.round(cx + R.range(-w * 0.45, w * 0.45)); let y = base; while (y < Hh - 2 && s.a(x, y)) y++; if (!s.a(x, y - 1)) continue; const L = R.int(1, 4); for (let j = 0; j < L; j++) s.pz(x + (j === L - 1 && R() < 0.5 ? (R() < 0.5 ? -1 : 1) : 0), y + j, rr[clamp(2 - (j >> 1), 0, 7)], 47, { m: MAT.LEAF, b: 46 }); }
  // sky gaps near the rim
  for (let k = 0; k < 7; k++) { const a = R.range(Math.PI * 1.05, Math.PI * 1.95), d = R.range(0.55, 0.85); const gx = cx + Math.cos(a) * w * 0.42 * d, gy = base - h * 0.45 + Math.sin(a) * h * 0.5 * d; const r = R.range(1.5, 3.2);
    for (let y = Math.floor(gy - r); y <= gy + r; y++) for (let x = Math.floor(gx - r); x <= gx + r; x++) if (hyp(x - gx, (y - gy) * 1.3) < r) s.clear(x, y); }
  POST.ao(s, 3, 0.18); POST.outline(s, { k: 0.58, hue: 0.03 }); POST.normals(s, 0.9);
  return { s, meta: { ax: cx, ay: Hh - 4, sway: 0.18, foliage: true, occluder: true, kind: 'camphorLobe' } };
}
function mixRamp(a, b) { return a.map((c, i) => i >= a.length - 3 ? b[Math.min(b.length - 1, i - (a.length - b.length))].map((v, k) => Math.round((v + c[k]) / 2)) : c); }
function bayer2(x, y) { return [[0, 0.5], [0.75, 0.25]][y & 1][x & 1]; }

/** crown layout around the trunk (metres): [name, dx, dz, y (lobe bottom height), w px, h px, seed] */
export const LOBES = [
  ['lobeW1', -8.6, 3.6, 5.0, 196, 112, 11], ['lobeE1', 9.6, 3.0, 5.6, 188, 108, 12],
  ['lobeW2', -16.6, 0.6, 7.6, 214, 124, 13], ['lobeE2', 17.6, 0.2, 8.2, 214, 124, 14],
  ['lobeC1', -4.2, 1.2, 10.4, 214, 134, 15], ['lobeC2', 6.4, 0.4, 10.8, 200, 128, 16],
  ['lobeW3', -11.8, -4.8, 13.6, 236, 146, 17], ['lobeE3', 12.4, -5.0, 14.0, 236, 146, 18],
  ['lobeC3', 0.4, -4.2, 15.6, 252, 154, 19], ['lobeW4', -17.6, -8.2, 11.6, 196, 126, 20], ['lobeE4', 20.6, -8.0, 12.2, 198, 128, 21],
  ['lobeW5', -6.2, -10.4, 18.2, 236, 146, 22], ['lobeE5', 8.2, -10.2, 18.6, 236, 146, 23], ['lobeT', 0.6, -12.4, 21.4, 220, 128, 24],
];

/** preview for tools/env/sheet.mjs */
export function PREVIEW() {
  return [['trunk', () => camphorTrunk(3)], ...LOBES.slice(0, 4).map(l => [l[0], () => camphorLobe(l[6], l[4], l[5])])];
}
