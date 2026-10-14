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
import { SB, PX, POST, MAT, mass, crown, cylN } from './paint.js';
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
        if (hash2(x >> 1, y >> 1, seed + 7) < 0.22 && sx < -0.1) { s.pz(x, y, PAL.moss[clamp(Math.round(2.6 - sx), 1, 5)], zf + n[2] * w0 * 0.3, { m: MAT.MOSS, b: lerp(b0, b1, u) + n[2] * 6 - 50, n }); return; }
        s.pz(x, y, BARK[clamp(Math.round(tt + (bayer2(x, y) - 0.5) * 0.6), 0, BARK.length - 1)], zf + n[2] * w0 * 0.3, { m: MAT.BARK, b: lerp(b0, b1, u) + n[2] * 6 - 50, n });
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
      const footRise = (1 - Math.sqrt(Math.max(0, 1 - sx * sx))) * 12; // the base outline curves up toward the sides (they stand further back)
      if (h < footRise - 2) continue;
      // arc-length coordinate around the cylinder: furrows crowd toward the edges
      const U = Math.asin(sx) * 52;
      // buttress ridges: raised bands that run down into the roots
      let ridge = 0; for (const b of butt) { const d = (sx - b.a) / 0.13; ridge += Math.exp(-d * d) * Math.exp(-h / (b.lift * 1.6)); }
      // furrows: wandering vertical lines ~9 px apart in U
      const fu = U + Math.sin(h * 0.045 + Math.floor(U / 8)) * 2.2 + vnoise(U * 0.08, h * 0.02, seed) * 5;
      const fi = Math.floor(fu / 8), ff = fu / 8 - fi;
      // furrows merge and split: their width breathes along the height
      const fw = 0.16 + vnoise(fi * 3.1, h * 0.05, seed + 2) * 0.14;
      const furrow = ff < fw || (ff > 0.55 && ff < 0.55 + fw * 0.5 && vnoise(fi * 2.3, h * 0.03, seed + 6) > 0.62);
      const n = cylN(sx * 0.94, 0.05);
      const plate = vnoise(fi * 5.7, h * 0.07, seed) - 0.5; // slow tone drift along each ridge of bark, no blocks
      let t = 4.0 - sx * 2.4 + ridge * 1.1 + plate * 1.1 + (ff > fw && ff < fw + 0.14 ? 1.0 : 0) + (ff > 0.8 ? -0.4 : 0);
      if (furrow) t -= 2.6;
      if (h < 14) t -= (14 - h) * 0.12;
      let col = BARK[clamp(Math.round(t + (bayer2(x, y) - 0.5) * 0.7), 0, BARK.length - 1)], mat = MAT.BARK;
      // moss: on the lit, upward-facing side and down at the foot, in clumps
      const mz = vnoise(x * 0.06, y * 0.045, seed + 11) * 0.75 + vnoise(x * 0.22, y * 0.22, seed + 12) * 0.25;
      const mossK = (sx < 0.0 ? 0.6 : 0.72) - (h < 70 ? (70 - h) / 70 * 0.16 : 0) - (h > 150 ? 0.06 : 0);
      if (mz > mossK && !furrow) { col = PAL.moss[clamp(Math.round(2.4 - sx * 1.2 + (mz - mossK) * 6 + (bayer2(x, y) - 0.5)), 0, 5)]; mat = MAT.MOSS; }
      else if (hash2(x >> 1, y >> 1, seed + 13) < 0.025 && !furrow) col = PAL.lichen[1 + (hash2(x, y, 3) < 0.5 ? 1 : 0)];
      if (h < footRise + 6) { const k = (footRise + 6 - h) / 8; col = [col[0] * (1 - k * 0.45), col[1] * (1 - k * 0.42), col[2] * (1 - k * 0.38)]; } // soil and shade at the foot
      const z = Math.sqrt(1 - sx * sx) * hw * 0.6 + 10;
      s.pz(x, y, col, z, { m: mat, b: (Math.sqrt(1 - sx * sx) - 1) * 50 + ridge * 6, n });
    }
  }
  // burls: round knots with ring shading
  for (const [bx, bh, br] of [[-28, 120, 8], [24, 150, 6], [36, 72, 7]]) {
    const xc = cx + bx + lean(bh), yc = base - bh;
    PX.ell(xc, yc, br, br * 0.9, (x, y, u, v, d) => { const ring = Math.floor(d * 3.5) % 2; const t = 4.2 - u * 1.6 - v * 1.4 - (ring ? 0.8 : 0) - (d > 0.85 ? 1.2 : 0); s.pz(x, y, BARK[clamp(Math.round(t), 0, BARK.length - 1)], 80, { m: MAT.BARK, b: 6 + (1 - d) * 4, n: [u * 0.7, -v * 0.7, Math.sqrt(Math.max(0.1, 1 - d * d))] }); });
  }
  // the hollow (洞) at the foot, between two buttresses
  { const xc = cx - 30, yc = base - 26;
    PX.ell(xc, yc, 13, 17, (x, y, u, v, d) => { const deep = d < 0.75; const t = deep ? 0.3 + v * 0.3 : 1.4 - u * 0.6; const c = deep ? [34 + v * 10, 28 + v * 8, 26 + v * 6] : BARK[clamp(Math.round(t), 0, 7)]; s.pz(x, y, c, 82, { m: MAT.BARK, b: deep ? -30 : 4, n: deep ? [0, 0, 1] : [-u * 0.6, v * 0.5, 0.6] }); }, { amp: 0.12, seed: 5 });
    for (let x = xc - 9; x <= xc + 9; x++) { const y = Math.round(yc + 16 + Math.abs(x - xc) * 0.15); if (s.a(x, y)) s.px(x, y, PAL.moss[3], { m: MAT.MOSS, z: 83, b: 5 }); } }
  // low limbs reaching west over the hut and east over the shrine (in front of the trunk)
  limb([[cx - 26, base - 112], [cx - 66, base - 132], [cx - 118, base - 136], [cx - 176, base - 128], [cx - 196, base - 122]], 40, 9, 54, 80, 90);
  limb([[cx - 120, base - 136], [cx - 146, base - 160], [cx - 160, base - 176]], 9, 4, 72, 76, 91);
  limb([[cx + 26, base - 122], [cx + 70, base - 142], [cx + 124, base - 146], [cx + 178, base - 140], [cx + 198, base - 134]], 38, 9, 54, 76, 90);
  limb([[cx + 128, base - 146], [cx + 150, base - 168], [cx + 158, base - 184]], 9, 4, 70, 74, 91);
  // (low limbs reach toward the viewer: their bulge grows past the trunk's front plane)
  // ferns in the crotches and on the buttresses
  for (const [fx, fy, sz] of [[cx - 52, base - 118, 0.7], [cx + 44, base - 126, 0.6], [cx - 62, base - 6, 0.8], [cx + 58, base - 10, 0.7], [cx - 6, base - 186, 0.6]]) {
    const f = fern(Math.round(fx * 7 + fy), sz).s; s.blit(f, Math.round(fx - f.w / 2), Math.round(fy - f.h + 3), { dz: 95, db: -2 });
  }
  // the shimenawa: a fat twisted straw rope across the front at ~3 m, shide hanging from it, a tassel at the front
  const ry = base - 62, rw = 9;
  const ropeY = x => { const sx = (x - cx - lean(62)) / (hwAt(62) + 2); return ry + (1 - sx * sx) * 7; };
  for (let x = Math.floor(cx - hwAt(62) - 3 + lean(62)); x <= cx + hwAt(62) + 3 + lean(62); x++) {
    const yc = ropeY(x); const sx = (x - cx - lean(62)) / (hwAt(62) + 2);
    for (let k = -rw / 2; k <= rw / 2; k++) {
      const v = k / (rw / 2), twist = ((x * 0.8 - k * 1.6 + 100) % 6) < 3;
      const t = 2.6 - v * 1.4 + (twist ? 0.7 : -0.5) - Math.abs(sx) * 0.8 - (Math.abs(v) > 0.8 ? 0.9 : 0);
      s.pz(x, Math.round(yc + k), PAL.rope[clamp(Math.round(t), 0, 4)], 120, { m: MAT.ROPE, b: (Math.sqrt(Math.max(0, 1 - sx * sx)) - 1) * 50 + 6 + (1 - Math.abs(v)) * 2, n: [sx * 0.5, -v * 0.8, 0.5] });
    }
    const sy = Math.round(yc + rw / 2 + 1); if (s.a(x, sy)) s.mul(x, sy, [0.55, 0.55, 0.62]); // the rope's shadow on the bark
  }
  for (const fx of [-34, -12, 12, 34]) shide(s, Math.round(cx + lean(62) + fx), Math.round(ropeY(cx + lean(62) + fx) + rw / 2), 125);
  // tassel bundle (房) at the front centre
  { const tx = Math.round(cx + lean(62)), ty = Math.round(ropeY(cx + lean(62)) + rw / 2);
    for (let k = 0; k < 7; k++) for (let y = ty; y < ty + 10 + (k % 3); y++) s.pz(tx - 3 + k, y, PAL.straw[clamp(3 - (k === 0 ? 1 : 0) + (y > ty + 6 ? -1 : 0), 0, 5)], 126, { m: MAT.STRAW, b: 10 }); }
  POST.ao(s, 3, 0.2); POST.outline(s, { k: 0.6, hue: 0.02 }); POST.normals(s, 0.9);
  return { s, meta: { ax: cx, ay: base + 1, sway: 0, foliage: false, occluder: true, kind: 'camphorTrunk' } };
}

/* ---------------- a surface root, lying on the ground ----------------
   path in the ground plane (screen = ground for things that lie flat):
   starts at the trunk, heading `ang` (radians, 0 = east, π/2 = south). */
export function camphorRoot(seed, len = 90, w0 = 22, w1 = 5, ang = Math.PI / 2, curl = 0.6, h0 = 9) {
  // A surface root: thick where it leaves the trunk, it dives into the ground after about half its
  // length and surfaces again in one or two low arches further out — it snakes under the moss rather
  // than ending in a point (pointed, fully exposed roots read as tentacles).
  const R = RNG(seed * 53 + 1), pts = []; let x = 0, y = 0, a = ang;
  const n = Math.ceil(len / 3);
  for (let i = 0; i <= n; i++) { pts.push([x, y]); a += (R() - 0.5) * 0.3 + curl * 0.015 * Math.sin(i * 0.35 + seed); x += Math.cos(a) * 3; y += Math.sin(a) * 3; }
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const p of pts) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
  const pad = w0 + h0 + 4, W = Math.ceil(x1 - x0 + pad * 2), H = Math.ceil(y1 - y0 + pad * 2), ox = pad - x0, oy = pad - y0, s = new SB(W, H);
  if (!s.N) s.N = new Float32Array(W * H * 3);
  const dive = R.range(0.5, 0.6), arches = [[dive + R.range(0.1, 0.14), dive + R.range(0.26, 0.32)]];
  if (len > 60) arches.push([R.range(0.8, 0.84), R.range(0.92, 0.97)]);
  // visible height (0..1 of h0) and width along the root
  const vis = t => {
    if (t <= dive) return Math.pow(1 - t / dive * 0.75, 1.3) * Math.min(1, (dive - t) / 0.08 + 0.15);
    for (const [a0, a1] of arches) if (t > a0 && t < a1) return Math.pow(Math.sin(Math.PI * (t - a0) / (a1 - a0)), 0.7) * 0.32 * (1.15 - t);
    return 0;
  };
  for (let i = 0; i < pts.length - 1; i++) {
    const t0 = i / (pts.length - 1), t1 = (i + 1) / (pts.length - 1);
    const vA = vis(t0), vB = vis(t1); if (vA <= 0.02 && vB <= 0.02) continue;
    const wAt = t => (w1 + (w0 - w1) * Math.pow(Math.max(0, 1 - t / dive), 2.2)) * (0.62 + 0.38 * Math.min(1, vis(t) * 2.5)) * (1 + 0.12 * Math.sin(t * 23 + seed));
    const hA = h0 * vA, hB = h0 * vB, wA = wAt(t0) / 2, wB = wAt(t1) / 2;
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    PX.stroke(ax + ox, ay + oy - hA * 0.8, bx + ox, by + oy - hB * 0.8, wA + hA * 0.3, wB + hB * 0.3, (px, py, t, sx) => {
      const tt = lerp(t0, t1, t), v = vis(tt), hgt = h0 * v;
      if (v <= 0.02) return;
      // the top faces up-left and catches light; the lower edge (its south side) is shade and soil
      const ww = w1 + (w0 - w1) * Math.pow(Math.max(0, 1 - tt / dive), 2.2), lanes = 2 + Math.round(ww / 7), lane = Math.floor((sx + 1) / 2 * lanes), fur = ((sx + 1) / 2 * lanes) % 1 < 0.24;
      let tone = 3.2 - sx * 1.2 + (hash2(lane, Math.floor((i * 3 + t * 3) / 7), seed) - 0.5) * 0.5 - (fur ? 0.9 : 0);
      if (sx > 0.55) tone -= (sx - 0.55) * 3;
      let col = BARK[clamp(Math.round(tone + (bayer2(px, py) - 0.5) * 0.5), 0, 7)], mat = MAT.BARK;
      // moss on the upper side, thicker where the root is low (it grows over from the ground)
      const mz = vnoise(px * 0.08, py * 0.08, seed + 3) + (1 - v) * 0.25;
      if (mz > 0.62 && sx < 0.3 && !fur) { col = PAL.moss[clamp(Math.round(2 + (mz - 0.62) * 7 - sx), 1, 5)]; mat = MAT.MOSS; }
      // where it sinks, soil heaped against its sides
      if (v < 0.22 && Math.abs(sx) > 0.6) { col = PAL.soil[clamp(Math.round(1.5 - sx), 0, 5)]; mat = MAT.SOIL; }
      const lift = hgt * Math.sqrt(Math.max(0, 1 - sx * sx));
      s.pz(px, py, col, 10 + lift, { m: mat, b: 0, n: [0, -sx * 0.7, 0.7] });
      s.b[py * W + px] = lift; // corrected to the ground plane below
    });
  }
  POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  const ax = Math.round(ox), ay = Math.round(oy);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const i = y * W + x; if (s.c[i * 4 + 3]) s.b[i] = -2 * (ay - y) + s.b[i] * 1.2; }
  return { s, meta: { ax, ay, sway: 0, kind: 'root' } };
}

/** 紙垂: paper folded into a four-step zigzag */
export function shide(s, x, y, z) {
  const seq = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [2, 2], [3, 2], [1, 3], [2, 3], [3, 3], [3, 4], [4, 4], [2, 5], [3, 5], [4, 5]];
  for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2, PAL.paper[dy % 2 ? 2 : 4], z, { m: MAT.PAPER, b: 10 });
  for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2 + 1, PAL.paper[1], z - 0.2, { m: MAT.PAPER, b: 10 });
}

/* ---------------- a crown lobe ----------------
   w, h: size in px; a cumulus of leaf masses with a hanging fringe. */
export function camphorLobe(seed, w = 220, h = 130, o = {}) {
  const R = RNG(seed * 41 + 3), W = Math.ceil(w * 1.4) + 24, Hh = h + 60, s = new SB(W, Hh), cx = Math.round(W / 2), base = h + 34; // (the anchor stays 22 px under the lobe's base)
  const rr = PAL.camphor, young = mixRamp(rr, PAL.camphorNew);
  // limbs glimpsed through the lower gaps
  for (let k = 0; k < 2; k++) { const x0 = cx + R.range(-w * 0.2, w * 0.2); PX.stroke(x0, base - 2, x0 + R.range(-w * 0.3, w * 0.3), base - h * 0.5, 4, 2, (x, y, t, sx) => s.pz(x, y, BARK[clamp(Math.round(1.6 - sx), 0, 7)], 1, { m: MAT.BARK, b: 2 })); }
  crown(s, { x: cx, y: base - h * 0.5, w, h, ramp: rr, young: o.dark ? rr : young, seed, tone: o.tone || 0 });
  // dangling leaf clusters
  for (let k = 0; k < w / 7; k++) { const x = Math.round(cx + R.range(-w * 0.45, w * 0.45)); let y = base; while (y < Hh - 2 && s.a(x, y)) y++; if (!s.a(x, y - 1)) continue; const L = R.int(1, 4); for (let j = 0; j < L; j++) s.pz(x + (j === L - 1 && R() < 0.5 ? (R() < 0.5 ? -1 : 1) : 0), y + j, rr[clamp(2 - (j >> 1), 0, 7)], 47, { m: MAT.LEAF, b: 46 }); }
  POST.ao(s, 3, 0.26); POST.outline(s, { k: 0.58, hue: 0.03 }); POST.normals(s, 0.9);
  return { s, meta: { ax: cx, ay: Hh - 4, sway: 0.18, foliage: true, occluder: true, kind: 'camphorLobe' } };
}
function mixRamp(a, b) { return a.map((c, i) => i >= a.length - 3 ? b[Math.min(b.length - 1, i - (a.length - b.length))].map((v, k) => Math.round((v + c[k]) / 2)) : c); }
function bayer2(x, y) { return 0.5 + ([[0, 0.5], [0.75, 0.25]][y & 1][x & 1] - 0.375) * 0.45; }

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
/** surface roots around the trunk: [dx, dz from the trunk centre (m), heading (rad), length px, w0, w1, h0] */
export const ROOTS = [
  [-2.5, 2.1, 2.3, 110, 26, 9, 8], [2.6, 2.2, 0.8, 120, 26, 9, 8],
  [-0.9, 2.5, 1.85, 70, 16, 6, 5], [1.2, 2.5, 1.3, 76, 16, 6, 5], [-3.3, 1.5, 2.65, 64, 15, 6, 5], [3.4, 1.4, 0.45, 70, 15, 6, 5],
];
export function PREVIEW() {
  return [['trunk', () => camphorTrunk(3)], ...ROOTS.slice(0, 3).map((r, i) => ['root' + i, () => camphorRoot(i + 1, r[3], r[4], r[5], r[2], 0.6, r[6])]), ...LOBES.slice(0, 2).map(l => [l[0], () => camphorLobe(l[6], l[4], l[5])])];
}
