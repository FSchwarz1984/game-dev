/* =====================================================================
   env/groundmat — per-pixel ground materials for the terrain painter.
   Each function writes colour, a normal tilt and a G-buffer material id
   into the shared scratch array OUT = [r, g, b, nx, ny, mat, flags].
   Coordinates: X, Y are world pixels (1 m = 20 px); x, y are screen
   pixels (ordered dither is screen-locked so clusters stay clean).

   Rules that keep it hand-pixelled rather than noisy:
   - colours come from short discrete ramps, never per-pixel lerps;
   - shapes first (clumps, stones, rock blocks with lit top-left edges),
     then sparse glyphs (grass tufts, pebbles, flowers);
   - detail density follows masks, so busy texture never sits next to
     busy texture (Slynyrd, knowledge/02 §8).
   The meadow keeps v0.1's terrainFS structure (big patches → clumps →
   blade marks, dry patches, flowers), which is where its mood lived.
   ===================================================================== */
import { clamp, hashi, hash2, NoiseTile, bayer, ramp, hexRGB } from './core.js';
import { PAL } from './palette.js';
import { MAT } from './paint.js';

export const TM = { // top materials (terrain raster ids)
  NONE: 0, GRASS: 1, CLEAR: 2, MOSS: 3, FLOOR: 4, PATH: 5, PAVE: 6, STEP: 7, ROOT: 8, GRAVEL: 9, BED: 10,
  ROCKTOP: 11, MUD: 12, MEADOW: 13, NEEDLE: 14, SCREE: 15,
};
export const WM = { ROCK: 1, STONEWALL: 2, EARTH: 3, BARK: 4, RISER: 5, MOSSROCK: 6, DROP: 7 };
export const FLAG = { WALL: 1, BLADE: 2, LIP: 4, WET: 8, STEP: 16, EDGE: 32 };

export const OUT = new Float32Array(8);

let NZ = null;
export function noise() {
  if (NZ) return NZ;
  NZ = {
    big: new NoiseTile(256, 4, 11, 4),   // ~64-texel features at octave 0
    mid: new NoiseTile(256, 3, 23, 8),
    cl: new NoiseTile(256, 1, 37, 64),   // 4-texel value noise
    cl2: new NoiseTile(256, 1, 41, 64),
    warp: new NoiseTile(256, 3, 53, 4),
    fine: new NoiseTile(256, 2, 61, 32),
  };
  return NZ;
}

/* ---------------- grass ramps (dark → light), built from v0.1's terrain colours ---------------- */
const G = {
  cool: [[34, 58, 44], [42, 70, 50], [60, 98, 52], [78, 120, 54], [104, 142, 62], [138, 164, 80]],
  warm: [[44, 64, 40], [56, 84, 44], [78, 112, 50], [100, 132, 56], [128, 154, 66], [160, 178, 90]],
  dry: [[64, 66, 42], [84, 88, 52], [106, 112, 64], [128, 128, 74], [150, 146, 86], [176, 168, 108]],
};
const set = (c, k = 1) => { OUT[0] = c[0] * k; OUT[1] = c[1] * k; OUT[2] = c[2] * k; };

// tuft glyphs, 4×3: 1 = blade (one tone lighter), -1 = shade under the tuft (one tone darker)
const TUFT = [
  [0, 1, 0, 1, 1, 0, 1, 0, 0, -1, 0, 0],
  [0, 0, 1, 0, 0, 1, 0, 1, 1, 0, -1, 0],
  [1, 0, 0, 0, 0, 1, 0, 0, 0, -1, 1, 0],
  [0, 1, 0, 0, 1, 1, 0, 1, -1, 0, -1, 0],
  [0, 0, 0, 0, 1, 0, 1, 0, 0, -1, 0, 0],
];

/* ---------------- grass clumps ----------------
   The carpet is a jittered grid of small mounds (11×7 px cells); each
   pixel takes the front-most mound covering it (the one anchored lowest
   on screen), so clumps overlap like real tufts. A mound: a half-ellipse
   with a ragged top of blade tips, the tips and the upper-left lit, a
   dark line under its foot; uncovered pixels are the shaded gaps.
   This is the hand-pixelled grass carpet (clean clusters, no
   checkerboards), and every mound tilts the normal so the dynamic light
   rolls over the carpet. Fills CL; returns false for a gap. */
const CLW = 11, CLH = 7;
export const CL = { off: 0, nx: 0, ny: 0, tip: false, id: 0 };
export function clump(X, Y, dens, flat = 0, round = false, tall = 0) {
  const cx0 = Math.floor(X / CLW), cy0 = Math.floor(Y / CLH), d255 = dens * 255;
  let bestAy = -1e9, bh = 0, bdx = 0, brx = 1, btop = 0, bbl = 0;
  for (let j = 0; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    const qx = cx0 + i, qy = cy0 + j, h = hashi(qx, qy, 101);
    if ((h & 255) >= d255) continue;
    const ay = qy * CLH + ((h >>> 12) % CLH);
    if (ay < Y || ay <= bestAy) continue;
    const ax = qx * CLW + ((h >>> 8) % CLW) + ((qy & 1) ? 3 : 0);
    const rx = 2 + ((h >>> 16) & 7) % 4, dx = X - ax;
    if (dx < -rx || dx > rx) continue;
    const hg = Math.max(1, 2 + ((h >>> 19) & 3) % 3 - flat);
    const u = dx / (rx + 0.5);
    let blade = 0;
    if (!round && dx > -rx && dx < rx) { const bt = hashi(X, ay, 103) & 15; blade = bt < 2 ? 3 : bt < 5 ? 2 : bt < 8 ? 1 : 0; if (flat) blade = blade > 1 ? 1 : 0; else if (blade && tall) blade += tall; }
    const top = ay - Math.round(hg * Math.sqrt(Math.max(0, 1 - u * u))) - blade;
    if (Y < top) continue;
    bestAy = ay; bh = h; bdx = dx; brx = rx; btop = top; bbl = blade;
  }
  if (bestAy < -1e8) { CL.off = -1; CL.nx = 0; CL.ny = -0.05; CL.tip = false; CL.id = 0; return false; }
  const rel = Y - btop, u = bdx / brx;
  let off = 0;
  if (rel < bbl) off = (rel === 0 && u < 0.2 && ((bh >>> 20) & 1) === 0) ? 2 : 1;   // a blade standing up
  else if (Y === bestAy && rel > 1 && ((bh >>> 22) & 1)) off = -1;
  else if (rel === bbl && u < 0 && ((bh >>> 23) & 1)) off = 1;
  CL.off = off; CL.nx = u * 0.42; CL.ny = rel <= 1 ? 0.32 : Y === bestAy ? -0.32 : 0.04; CL.tip = rel < bbl; CL.id = bh;
  return true;
}

/* ---------------- meadow grass: v0.1's terrainFS painting, baked ----------------
   (legacy/v0.1/src/shaders.js grassCol) Painted, not noisy: big meadow patches (two greens mixed
   by a very slow field) → clumps of a few pixels in three tones → sparse 1×2 blade highlights on
   the lit tops of clumps, crevices only in the hollows → dry and olive patches → wildflowers and
   clover by mask. calm 0..1 pulls the tones together and thins the blades (clearings, verges),
   moist 0..1, flowers 0..1 (patch coverage), dry 0..1 (sun-bleached). The colours are v0.1's. */
const GV = { d0: [42, 70, 50], d1: [52, 90, 47], m0: [74, 114, 50], m1: [91, 132, 54], l0: [122, 154, 66], l1: [147, 171, 82], dry: [129, 129, 73], olive: [106, 119, 67], blade: [168, 188, 106] };
const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const sst = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const FLW = [[236, 235, 220], [230, 210, 90], [138, 146, 220], [216, 154, 166], [240, 240, 236]];
export function grass(X, Y, x, y, calm = 0, moist = 0.6, flowers = 0.4, dry = 0) {
  const N = NZ;
  const big = N.big.sample(X * 0.3, Y * 0.3), mid = N.mid.sample(X * 0.7 + 30, Y * 0.7);
  const cl = N.cl.sample(x * 0.8, y * 0.8) * 0.6 + N.cl2.sample(x * 1.9 + 5, y * 1.9) * 0.4, r = hash2(x, y, 3);
  const hue = sst(0.35, 0.75, big);
  let t = mid * 0.45 + cl * 0.55; t = 0.5 + (t - 0.5) * (1 - calm * 0.45);
  const dark = mix3(GV.d0, GV.d1, hue), lite = mix3(GV.l0, GV.l1, hue);
  let c = t < 0.4 ? dark : t < 0.62 ? mix3(GV.m0, GV.m1, hue) : lite, flags = 0;
  // blade highlights only on the lit tops of clumps, crevices only in the hollows
  const blade = hash2(x, y >> 1, 7) > 0.84 + calm * 0.1;
  if (t > 0.5 && blade) { c = mix3(lite, GV.blade, 0.5); flags |= FLAG.BLADE; }
  if (t < 0.45 && r < 0.07 * (1 - calm * 0.6)) c = [dark[0] * 0.82, dark[1] * 0.82, dark[2] * 0.82];
  // dry and olive patches where the slow field is high (the sun-bleached saddle)
  const dk = sst(0.6, 0.82, big + (1 - moist) * 0.28 + dry * 0.22) * 0.6;
  if (dk > 0) c = mix3(c, mix3(GV.dry, GV.olive, mid), dk);
  // clover: trefoils in patches, a few white heads
  const cv = N.warp.sample(X * 0.3 + 170, Y * 0.3 + 40);
  if (cv > 0.66 - flowers * 0.04 && calm < 0.7) {
    const cx = Math.floor(X / 4), cy = Math.floor(Y / 3), ch = hashi(cx, cy, 91);
    if ((ch & 255) < (cv - 0.6) * 1100) {
      const ox = X - cx * 4 - 1 - ((ch >> 8) & 1), oy = Y - cy * 3 - 1;
      if ((ox === 0 && oy === -1) || (Math.abs(ox) === 1 && oy === 0)) c = mix3(GV.m1, GV.l1, 0.55 + ((ch >> 10) & 1) * 0.2);
      else if (ox === 0 && oy === 0) c = ((ch >> 12) & 7) === 0 ? [232, 226, 214] : GV.m0;
    }
  }
  // wildflowers: clustered in patches, 2 px with a darker pixel under
  if (flowers > 0) {
    const patch = N.warp.sample(X * 0.45 + 99, Y * 0.45), th = 1 - flowers * 0.4;
    if (patch > th) {
      const fx = Math.floor(X / 5), fy = Math.floor(Y / 4), fh = hashi(fx, fy, 71);
      if ((fh & 255) < (patch - th) * 700) {
        const ox = X - fx * 5 - ((fh >> 8) & 3), oy = Y - fy * 4 - ((fh >> 10) & 1), q = (fh >> 12) & 15;
        const fc = FLW[q < 6 ? 0 : q < 10 ? 1 : q < 13 ? 2 : q < 15 ? 3 : 4];
        if (oy === 0 && (ox === 0 || ox === 1)) { c = ox === 0 ? fc : [fc[0] * 0.82, fc[1] * 0.8, fc[2] * 0.86]; flags |= FLAG.BLADE; }
        else if (oy === 1 && ox === 0) c = dark;
      }
    }
  }
  OUT[0] = c[0]; OUT[1] = c[1]; OUT[2] = c[2];
  OUT[3] = (cl - 0.5) * 0.5; OUT[4] = (t - 0.5) * 0.7 + (blade ? 0.15 : 0); OUT[5] = MAT.GRASS; OUT[6] = flags;
}

/* ---------------- yard / worn earth (v0.1 pathCol): trodden earth in three tones, pebbles, a few fallen leaves ---------------- */
const YARD = [[119, 108, 75], [139, 129, 96], [158, 147, 122], [139, 139, 139]];
export function yard(X, Y, x, y, leaves = 0.3) {
  const N = NZ, r = hash2(x, y, 85), big = N.mid.sample(X * 1.2, Y * 1.2);
  const v = r * 0.5 + big * 0.5;
  let c = v < 0.3 ? YARD[0] : v < 0.75 ? YARD[1] : YARD[2];
  if (hash2(x >> 1, y >> 1, 86) > 0.975) c = YARD[3];
  const drift = N.warp.sample(X * 0.5 + 31, Y * 0.5);
  if (drift > 1 - leaves * 0.6) { const lh = hashi(X >> 1, Y, 89); if ((lh & 255) < 34) c = PAL.litter[(lh >> 8) & 3]; }
  set(c);
  OUT[3] = (r - 0.5) * 0.3; OUT[4] = 0; OUT[5] = MAT.PATH; OUT[6] = 0;
}

/* ---------------- clearing under the great tree: worn earth, moss, short grass ----------------
   the borders are ragged at the pixel scale (a fine noise added to the mask), never clean lines */
export function clearing(X, Y, x, y, wear = 0.3) {
  const N = NZ;
  const w = N.warp.sample(X * 0.5, Y * 0.5) * 0.6 + N.mid.sample(X * 1.1, Y * 1.1) * 0.4 + wear * 0.3 - 0.18 + (N.cl.sample(x * 1.3, y * 1.3) - 0.5) * 0.12;
  if (w > 0.6) { yard(X, Y, x, y, 0.5); return; }
  if (w < 0.43) { moss(X, Y, x, y, 0.25); return; }
  grass(X, Y, x, y, 0.75, 0.8, 0.12);
}

/* ---------------- moss carpet (v0.1): three greens by a slow field and the pixel hash, bright fruiting specks ---------------- */
const MOSS = PAL.moss;
const MV = [[60, 92, 42], [72, 108, 48], [88, 127, 58], [154, 168, 96]];
export function moss(X, Y, x, y, dark = 0) {
  const N = NZ, r = hash2(x, y, 15), big = N.mid.sample(X * 0.9, Y * 0.9) - dark * 0.12;
  const v = r * 0.4 + big * 0.6;
  let c = v < 0.35 ? MV[0] : v < 0.8 ? MV[1] : MV[2];
  if (hash2(x + 2, y, 16) > 0.985) c = MV[3];
  else if (r < 0.03) c = [MV[0][0] * 0.8, MV[0][1] * 0.8, MV[0][2] * 0.8];
  set(c);
  OUT[3] = (r - 0.5) * 0.5; OUT[4] = (big - 0.5) * 0.5; OUT[5] = MAT.MOSS; OUT[6] = 0;
}

/* ---------------- forest floor: dark soil, leaf litter, needles, twigs ---------------- */
const FLOOR = [[44, 36, 32], [59, 46, 40], [74, 60, 46], [92, 76, 52]];
export function floor(X, Y, x, y, leafy = 0.5) {
  const N = NZ;
  const big = N.mid.sample(X * 0.9, Y * 0.9), r = hashi(X, Y, 5);
  const v = big * 0.7 + (r & 255) / 255 * 0.3 + (bayer(x, y) - 0.5) * 0.15;
  let c = FLOOR[v < 0.33 ? 0 : v < 0.6 ? 1 : v < 0.82 ? 2 : 3];
  // needles: short diagonal strokes
  if (hash2(Math.floor((X + Math.floor(Y / 3) * 2) / 3), Y, 11) > 0.9) c = PAL.needle;
  // leaf litter: little 2×2 leaves, clustered
  const lit = N.warp.sample(X * 0.7 + 7, Y * 0.7);
  if (lit > 1 - leafy * 0.75) {
    const lx = X >> 1, ly = Y >> 1, lh = hashi(lx, ly, 19);
    if ((lh & 255) < 70) { c = PAL.litter[(lh >> 8) & 3]; if ((X & 1) && (Y & 1)) c = [c[0] * 0.8, c[1] * 0.78, c[2] * 0.8]; }
  }
  if ((r >> 12 & 1023) < 6) c = PAL.stone[4];
  set(c);
  OUT[3] = ((r & 255) / 255 - 0.5) * 0.4; OUT[4] = (big - 0.5) * 0.4; OUT[5] = MAT.SOIL; OUT[6] = 0;
}

/* ---------------- dirt path (old road, trodden earth) ----------------
   edge 0 inside → 1 at the grass, d distance from the centreline, hw half width, rut 0..1 */
const PATH = PAL.path;
export function path(X, Y, x, y, edge = 0, d = 0, hw = 30, rut = 0) {
  // v0.1's trodden earth (three tones by the pixel hash and a slow field), two worn ruts, pebbles;
  // the verge spills over the edge: grass in ragged tongues, a darker band where earth meets grass
  const N = NZ, r = hash2(x, y, 21), big = N.mid.sample(X * 1.2, Y * 1.2), cl = N.cl.sample(X * 0.7, Y * 0.7);
  let v = r * 0.5 + big * 0.5;
  if (rut > 0) { const u = Math.abs(d) / hw; const band = Math.exp(-Math.pow((u - 0.42) / 0.12, 2)); v -= band * 0.25 * rut; }
  let c = v < 0.3 ? YARD[0] : v < 0.75 ? YARD[1] : YARD[2];
  if (hash2(x >> 1, y >> 1, 23) > 0.975) c = YARD[3];
  OUT[0] = c[0]; OUT[1] = c[1]; OUT[2] = c[2];
  if (edge > 0) {
    const g = edge - (hash2(x, y, 24) * 0.35 + cl * 0.5);
    if (g > 0.16) { grass(X, Y, x, y, 0.3, 0.5, 0.1); return; }
    if (g > 0.04) { OUT[0] *= 0.84; OUT[1] *= 0.85; OUT[2] *= 0.8; }
  }
  OUT[3] = (r - 0.5) * 0.3; OUT[4] = 0; OUT[5] = MAT.PATH; OUT[6] = 0;
}

const JOINT = [52, 50, 38];
/* ---------------- 石畳: irregular flat stones of the old highway ----------------
   jittered Voronoi; each stone lit along its top-left bevel, mossy joints */
export function paving(X, Y, x, y, moss_ = 0.5) {
  const S = 13, gx = X / S, gy = Y / (S * 0.8), cx = Math.floor(gx), cy = Math.floor(gy);
  let d1 = 1e9, d2 = 1e9, id = 0, ox = 0, oy = 0;
  for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    const qx = cx + i, qy = cy + j, h = hashi(qx, qy, 31);
    const jx = qx + 0.2 + (h & 255) / 255 * 0.6, jy = qy + 0.2 + ((h >> 8) & 255) / 255 * 0.6;
    const dx = gx - jx, dy = gy - jy, d = dx * dx + dy * dy;
    if (d < d1) { d2 = d1; d1 = d; id = h; ox = dx; oy = dy; } else if (d < d2) d2 = d;
  }
  const gap = Math.sqrt(d2) - Math.sqrt(d1);
  if (gap < 0.11) { // joint
    const mj = hash2(X, Y, 33) < moss_ ? MOSS[1] : JOINT;
    set(mj); OUT[3] = 0; OUT[4] = -0.2; OUT[5] = MAT.SOIL; OUT[6] = 0; return;
  }
  const rr = (id & 3) === 0 ? PAL.stoneWarm : PAL.stone;
  let t = 2 + ((id >> 16) & 255) / 255 * 1.6 + (bayer(x, y) - 0.5) * 0.5;
  if (gap < 0.2) t += (ox < 0 || oy < 0) ? 1.1 : -1.2;   // bevel: top-left edges catch light
  else t += (-ox - oy) * 0.6;
  let c = rr[clamp(Math.round(t), 0, rr.length - 1)];
  if (((id >> 24) & 255) / 255 < moss_ * 0.35 && hash2(X >> 1, Y >> 1, 37) < 0.5) c = MOSS[2 + ((X + Y) & 1)];
  set(c);
  OUT[3] = -ox * 0.3; OUT[4] = -oy * 0.3; OUT[5] = MAT.STONE; OUT[6] = 0;
}

/* ---------------- stone step tread ----------------
   stepIdx, across (px from the flight's left edge), depthIn (px from the nosing) */
export function tread(X, Y, x, y, stepIdx, across, depthIn, mossy = 0.4) {
  const off = hash2(stepIdx, 0, 41) * 30, seg = Math.floor((across + off) / 23);
  const h = hashi(seg, stepIdx, 43), tone = (h & 255) / 255;
  const fu = (across + off) % 23;
  const rr = (h >> 8) & 1 ? PAL.stoneWarm : PAL.stone;
  let t = 3 + tone * 1.2 + (bayer(x, y) - 0.5) * 0.6;
  if (depthIn < 1.2) t += 1.6;             // the nosing catches the light
  else if (depthIn < 2.2) t += 0.6;
  if (fu < 1) t -= 2.2;                    // joint between slabs
  else if (fu < 2) t += 0.6;
  let c = rr[clamp(Math.round(t), 0, rr.length - 1)];
  const edge = across < 5 || hash2(X >> 1, Y >> 1, 47) < mossy * 0.1;
  if (edge && hash2(X, Y, 49) < 0.55) c = MOSS[2 + (hash2(X, Y, 50) < 0.5 ? 0 : 1)];
  set(c);
  OUT[3] = 0; OUT[4] = depthIn < 1.5 ? 0.2 : 0; OUT[5] = MAT.STONE; OUT[6] = FLAG.STEP;
}

/* ---------------- gravel / stream shingle ---------------- */
const GRAVEL = PAL.gravel;
export function gravel(X, Y, x, y) {
  const r = hashi(X, Y, 51), r2 = hash2(X >> 1, Y >> 1, 52);
  const v = (r & 255) / 255 * 0.4 + r2 * 0.35 + NZ.mid.sample(X, Y) * 0.25;
  let c = GRAVEL[clamp(Math.floor(v * 4.6), 0, 4)];
  if (r2 > 0.92) { const q = (X & 1) + (Y & 1) * 2; c = q === 0 ? PAL.stone[5] : q === 3 ? PAL.stone[1] : PAL.stone[3]; }
  set(c);
  OUT[3] = ((r & 255) / 255 - 0.5) * 0.6; OUT[4] = (r2 - 0.5) * 0.6; OUT[5] = MAT.STONE; OUT[6] = 0;
}

/* ---------------- river bed (seen through water) ---------------- */
export function bed(X, Y, x, y) {
  const r = hashi(X, Y, 55), r2 = hash2(X >> 1, Y >> 1, 56);
  let c = r2 < 0.4 ? PAL.bed[1] : r2 < 0.75 ? PAL.bed[2] : PAL.bed[0];
  if ((r & 255) > 238) c = PAL.bed[4];
  set(c);
  OUT[3] = ((r & 255) / 255 - 0.5) * 0.6; OUT[4] = (r2 - 0.5) * 0.6; OUT[5] = MAT.BED; OUT[6] = FLAG.WET;
}

/* ---------------- root top (the camphor's surface roots) ----------------
   along: px along the root, across: -1..1 */
const BARK = PAL.barkCamphor;
export function rootTop(X, Y, x, y, along, across) {
  const lane = Math.floor((across + 1) * 2.5), f = hash2(Math.floor(along / 9) + lane * 7, lane, 61);
  const furrow = ((across + 1) * 2.5) % 1 < 0.22;
  let t = 3.6 - across * 1.5 + (f - 0.5) * 1.0 + (bayer(x, y) - 0.5) * 0.5 - (Math.abs(across) > 0.75 ? 1.0 : 0) - (furrow ? 1.2 : 0);
  let c = BARK[clamp(Math.round(t), 0, BARK.length - 1)];
  const mz = NZ.warp.sample(X * 0.6, Y * 0.6);
  if (mz > 0.6 && across < 0.4) c = MOSS[clamp(Math.round(1.6 + (mz - 0.6) * 6 - across), 1, 4)];
  set(c);
  OUT[3] = across * 0.6; OUT[4] = 0.2; OUT[5] = MAT.BARK; OUT[6] = 0;
}

/* ---------------- walls (faces between levels) ----------------
   u: horizontal coordinate along the face (px), ha: absolute height of
   the pixel (px, keeps courses continuous between columns), h: height
   above the wall's foot (px), H: total wall height (px), lit: -1..1
   from the face normal against the light. */
const ROCK = PAL.rock, ROCKW = PAL.rockWarm, SOIL = PAL.soil;
export function wall(kind, X, u, ha, h, H, x, y, lit) {
  const N = NZ, dith = (bayer(x, y) - 0.5) * 0.6;
  let c, mat = MAT.ROCK;
  if (kind === WM.STONEWALL) {               // 石垣, 野面積み: irregular field stones, dark chinks, moss on the ledges
    // a stretched Voronoi of stones (wider than tall, bigger toward the foot), each lit along its upper-left bevel
    const big = h < H * 0.4 ? 1.25 : 1, CWs = 15 * big, CHs = 9.5 * big;
    const gx = u / CWs, gy = (ha + 2) / CHs, cx = Math.floor(gx), cy = Math.floor(gy);
    let d1 = 1e9, d2 = 1e9, id = 0, ox = 0, oy = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
      const qx = cx + i, qy = cy + j, hh = hashi(qx, qy, 74);
      const jx = qx + 0.12 + (hh & 255) / 255 * 0.76, jy = qy + 0.2 + ((hh >> 8) & 255) / 255 * 0.6;
      const dx = gx - jx, dy = (gy - jy) * 1.15, dd = dx * dx + dy * dy;
      if (dd < d1) { d2 = d1; d1 = dd; id = hh; ox = dx; oy = dy; } else if (dd < d2) d2 = dd;
    }
    const gap = Math.sqrt(d2) - Math.sqrt(d1);
    const R = ((id >>> 20) & 3) === 0 ? PAL.stoneWarm : ((id >>> 20) & 3) === 1 ? PAL.stoneCool : PAL.stone;
    if (gap < 0.075) {                       // the chink between stones: dark, now and then a moss plug
      if (hash2(X >> 1, ha >> 1, 75) < 0.22) { set(MOSS[1 + (hash2(X, ha, 78) < 0.5 ? 1 : 0)]); OUT[3] = 0; OUT[4] = 0; OUT[5] = MAT.MOSS; OUT[6] = FLAG.WALL; return; }
      c = R[0];
    } else {
      let t = 2.3 + ((id >> 16) & 255) / 255 * 1.3 + dith * 0.6 + lit * 0.6;
      t += -ox * 0.9 + oy * 1.1;                      // ha grows upward: +oy = the stone's upper part
      if (gap < 0.16) t += (oy > 0 || ox < -0.1) ? 0.9 : -1.0;   // bevel: lit along the top-left, shaded under
      if (h < 3) t -= (3 - h) * 0.4;                  // the foot sits in shade and damp
      c = R[clamp(Math.round(t), 1, R.length - 1)];
      if (oy > 0.18 && gap > 0.1 && ((id >>> 12) & 7) < 2 && NZ.warp.sample(X * 0.3, ha * 0.5) > 0.5) c = MOSS[clamp(Math.round(2 + oy * 3 + dith), 2, 4)];
    }
    mat = MAT.STONE;
  } else if (kind === WM.RISER) {
    let t = 1.6 + hash2(Math.floor(u / 23), Math.floor(ha / 5), 77) * 0.8 + dith;
    const fromTop = H - h - 1;
    if (fromTop < 1) t += 2.2; else if (h < 1) t -= 0.8;
    if (((u % 23) + 23) % 23 < 1) t -= 1;
    c = PAL.stone[clamp(Math.round(t), 0, PAL.stone.length - 1)]; mat = MAT.STONE;
  } else if (kind === WM.EARTH) {               // a cut bank: layered soil, embedded stones, roots, a few tufts
    const strata = N.mid.sample(u * 0.08, ha * 0.9) * 0.7 + N.cl.sample(u * 0.25, ha * 0.5) * 0.3;
    let t = 1.5 + strata * 2 + dith * 0.5 + lit * 0.5 + (H - h < 3 ? 0.7 : 0) - (h < 4 ? (4 - h) * 0.3 : 0);
    c = SOIL[clamp(Math.round(t), 0, SOIL.length - 1)]; mat = MAT.SOIL;
    // stones: little rounded lumps lit at the top-left, a dark pixel under them
    const sx = Math.floor(u / 7), sy = Math.floor(ha / 6), sh = hashi(sx, sy, 79);
    if ((sh & 255) < 46) { const cx = sx * 7 + 1 + ((sh >> 8) & 3), cy = sy * 6 + 1 + ((sh >> 10) & 3), r = 1.2 + ((sh >> 12) & 3) * 0.5, dx = u - cx, dy = ha - cy, d = Math.sqrt(dx * dx + dy * dy * 1.4);
      if (d < r) { c = PAL.stoneWarm[clamp(Math.round(3 - dx * 0.6 + dy * 0.7), 1, 6)]; mat = MAT.STONE; } else if (d < r + 1 && dy < 0) c = SOIL[0]; }
    // a root threading the bank
    const rl = Math.abs(Math.sin(u * 0.09 + Math.floor(ha / 11) * 2.1) * 3 + (ha % 11) - 5);
    if (rl < 0.5 && hash2(Math.floor(u / 23), Math.floor(ha / 11), 81) < 0.35) c = BARK[2];
    // tufts growing out of the bank
    const tx = Math.floor(u / 9), ty = Math.floor(ha / 7), th = hashi(tx, ty, 83);
    if ((th & 255) < 26 && h > 3) { const ox = u - tx * 9 - 3, oy = ha - ty * 7 - 2; if (oy >= 0 && oy < 3 && Math.abs(ox) <= 2 - oy * 0.5) { c = G.warm[clamp(3 - oy + (ox < 0 ? 1 : 0), 1, 5)]; mat = MAT.GRASS; } }
  } else if (kind === WM.BARK) {
    let t = 2.2 + hash2(Math.floor(u / 3), Math.floor(ha / 6), 81) * 1.6 + dith - (h < 2 ? 0.8 : 0) + lit * 0.8;
    c = BARK[clamp(Math.round(t), 0, BARK.length - 1)]; mat = MAT.BARK;
  } else { // ROCK, MOSSROCK, DROP: natural cliff — big irregular blocks lit along the top-left, cracks, earth seams
    const big = kind === WM.DROP ? 1.35 : 1;
    const CW = 21 * big, CHh = 14 * big, row = Math.floor(ha / CHh), roff = hash2(row, 7, 89) * CW;
    const gx = (u + roff) / CW, gy = ha / CHh, cx = Math.floor(gx), cy = Math.floor(gy);
    let d1 = 1e9, d2 = 1e9, id = 0, ox = 0, oy = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
      const qx = cx + i, qy = cy + j, hh = hashi(qx, qy, 83);
      const jx = qx + 0.1 + (hh & 255) / 255 * 0.8, jy = qy + 0.1 + ((hh >> 8) & 255) / 255 * 0.8;
      const dx = gx - jx, dy = (gy - jy) * 1.2, dd = dx * dx + dy * dy;
      if (dd < d1) { d2 = d1; d1 = dd; id = hh; ox = dx; oy = dy; } else if (dd < d2) d2 = dd;
    }
    const gap = Math.sqrt(d2) - Math.sqrt(d1);
    const earth = N.warp.sample(u * 0.08 + 20, ha * 0.12) > 0.66;
    const R = earth ? SOIL : (kind === WM.DROP || ((id >>> 24) & 3) === 0) ? ROCKW : ROCK;
    let t = 2.5 + ((id >> 16) & 255) / 255 * 1.3 + dith * 0.8 + lit * 1.0;
    t += -ox * 1.1 + oy * 1.4;                       // ha grows upward: +oy = upper part of the block
    if (gap < 0.07) t = 0.4 + lit * 0.4;             // crack
    else if (gap < 0.15) t += (oy > 0 ? 1.0 : -0.9); // block rim: lit above, shaded below
    const vcrack = hash2(Math.floor(u / 2), Math.floor(ha / 18), 87) > 0.985;
    if (vcrack) t -= 1.6;
    if (h < 6) t -= (6 - h) * 0.3;                   // the foot is occluded and damp
    c = R[clamp(Math.round(t), 0, R.length - 1)];
    if (earth) mat = MAT.SOIL;
    const mossy = kind === WM.MOSSROCK ? 0.45 : 0.62;
    if (oy > 0.12 && gap > 0.1 && N.warp.sample(u * 0.5 + 30, ha * 0.7) > mossy) { c = MOSS[clamp(Math.round(2 + lit + oy * 2.4 + dith), 1, 5)]; mat = MAT.MOSS; }
    else if (oy > 0.32 && gap > 0.1 && ((id >>> 20) & 15) < 2) { c = G.warm[clamp(Math.round(2 + lit + dith * 2), 1, 4)]; mat = MAT.GRASS; } // a tuft on a ledge
  }
  set(c); OUT[3] = 0; OUT[4] = 0; OUT[5] = mat; OUT[6] = FLAG.WALL;
}
