// Bake of the treetop vista south over the plain ("south" shot) for Godot (godot/vista).
//
// Scene: the sky, the cloud deck, the crown and the sky shore are HEAD's (src/vista/south.js and the
// modules it uses). Since round 5 (G5R3-10) the plain is the 3D lookout's: plain.js reads the 3D
// region's vista data (godot/world3d/terrain/saddle/vista.json and its far / mid / plain maps, which
// bake.mjs hands the page) and draws its river, red viaduct, town, villages, roads, lamps and ring of
// mountains at the same bearings, in the same order of depth (only the depression angles are scaled
// back into the prologue's band, and the mountains lowered just clear of the sky shore: plain.js).
// Re-bake when that data changes. The near branches are near.js's (round 5). Rising lights = the
// early v0.2 plan of commit 8196ebf (src/vista/south.js@8196ebf L106-154), ported verbatim: every lamp
// on the plain leaves on its own cubic Bezier toward the gate, the lamps of a place in a random
// order, two lone lights first (R-8, docs/knowledge/14 §4).
//
// Layout. The composition is the 480x270 frame of the JS vista (the reference frame). Godot shows any
// logical size from ~480x270 up to 1024 wide / 560 tall (integer scale, expand), so the bake paints a
// wider and taller canvas around the reference frame with the same camera: more plain and range at
// the sides, more sky (cloud deck and sky shore overhead) above, more slope below. Every position
// that the JS code derived from the frame size (towns on the sky shore, the gate, the limb, the
// canopy clumps) is derived from the reference frame instead and offset into the canvas.
//   ref = { W: 480, H: 270 }    canvas: Wc wide, the reference frame's left edge at ox
//   far group: horizon at row YL (rowsAbove), GH rows        canopy group: reference row 0 at oyC
// variant "canon" (Wc 480, the JS rows exactly) reproduced the JS frame pixel for pixel, to verify the
// Godot renderer against the JS one; since round 5 that holds for its sky, deck, crown and shore only.
// The crown's clumps stay the JS frame's: the canopy's draws start after HEAD_DRAWS, frozen.

import { clamp, lerp, smooth, rng, hash2, mix3, TAU, run } from '../../../src/vista/util.js';
import { todEnv, palette, skyAt } from '../../../src/vista/tod.js';
import { makeStars, CloudDeck, cloudPalette, CLOUD_MATS } from '../../../src/vista/sky.js';
import * as PL from './plain.js';
import { GROUND_MATS, G, buildPlainGen, paintHouses, plainLanterns, paintViaduct } from './plain.js';
import { paintCanopy, paintCanopyGen, FOLIAGE_MATS } from '../../../src/vista/foliage.js';
import { Wave } from '../../../src/vista/wave.js';
import { nearCrown } from './near.js';
import { buildSkyShoreGen, skyShorePalette } from './skyshore.js';
import { IdSpace, lutRows, idImage, fixed16, fixedS16, rows, todOfRow, TOD_ROWS, TOD0, TOD_STEP, r2, r3 } from './common.js';

const REF_W = 480, REF_H = 270;
const P = { far: 0.1, canopy: 1, front: 2.4 };
const CT = 66;
const KINDS = ['window', 'lantern', 'star', 'fire', 'bonfire'];
// HEAD's draws from its sequence before the canopy (river lanterns and its procession plan, on HEAD's
// map): frozen, so the crown's clumps stay the ones the user approved whatever the plain becomes
export const HEAD_DRAWS = 1768;
// the hour the far comes (the prologue's state from the lights' leaving on)
const WAVE_TOD = 20.3;

// counting RNG: the shipped variant replays the canon variant's draw count before the canopy
function crng(seed) {
  const base = rng(seed);
  let n = 0;
  const f = () => { n++; return base(); };
  f.count = () => n;
  f.skip = k => { for (let i = 0; i < k; i++) f(); return f; };
  return f;
}

export function bakeSouth(o = {}) {
  const seed = o.seed ?? 7;
  const Wc = o.Wc ?? REF_W, ox = Math.round((Wc - REF_W) / 2);
  // the reference frame (JS south.js with W = 480, H = 270)
  const yh0 = Math.round(clamp(REF_H * 0.475, REF_H - 165, REF_H - 118));         // 128
  const D0 = Math.max(40, Math.round(REF_H - CT - REF_H * 0.36));                  // 107
  const padTop0 = Math.ceil(D0 * P.far) + 2;                                         // 13
  const yl0 = yh0 + padTop0;                                                         // 141
  const f = 360, S = Math.max(110, yh0 * 1.1);
  const YL = o.rowsAbove ?? yl0, GH = YL + (o.rowsBelow ?? (REF_H - yh0));
  const dyC = YL - yl0;                       // JS far-layer row r -> canvas row r + dyC
  const Cx = ox + Math.round(REF_W / 2);
  const sun = { dir: norm([0.85, 0.27, -0.45]), slope: 0.3 };
  const RH = crng(seed * 7 + 3);              // the JS sequence: river lanterns, (HEAD plan), canopy
  const R8 = crng(seed * 7 + 3);              // 8196ebf's sequence: river lanterns, rising plan
  const RX = rng(seed * 101 + 17);            // extensions outside the reference frame

  // ---------------- ground, buildings, lights on the ground: the plain of the 3D lookout (G5R3-10;
  // tools/vista/bake/plain.js): the river out of the western canyon, the railway's red viaduct, the
  // town where they meet, the 3D view's villages, roads and street lamps, the ring of mountains
  if (!PL.haveW3()) throw new Error('south: the 3D lookout\'s land is not loaded (plain.js setW3)');
  const ground = run(buildPlainGen({ w: Wc, h: GH, cx: Cx, yh: YL, f, S, sun, seed }));
  const cam = { cx: Cx, yh: YL, f, height: ground.height };
  const lights = paintHouses(ground.layer, ground.X, ground.Z, cam, seed);
  lights.push(...plainLanterns(cam, ground.Z, Wc, GH));
  // the old road's switchbacks down the pass, an Obon lantern every ~40 m
  const SW = PL.switchbacks();
  for (let i = 0, acc = 0; i < SW.length - 1; i++) {
    const [ax, az] = SW[i], [bx, bz] = SW[i + 1], len = Math.hypot(bx - ax, bz - az), step = 40 / PL.U;
    for (let d = acc; d < len; d += step) {
      const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
      const x = Math.round(Cx + f * X / Z), y = Math.round(YL + f * (1 - ground.height(X, Z)) / Z) - 1;
      if (x < 0 || x >= Wc || y < 0 || y >= GH) continue;
      if (ground.Z[(y + 1) * Wc + x] < Z * 0.85) continue;
      lights.push({ x, y, X, Z, kind: 'lantern', path: true });
    }
    acc = (acc - len) % step; if (acc < 0) acc += step;
  }
  // the old road on across the plain to the town: on the night of the 送魂 paper lanterns hang
  // between its street lamps (the 3D's, in plainLanterns), one every ~12 m, so that from the crown it
  // is a thread of light winding into the town (HEAD's procession road was one)
  const OR = PL.oldRoad(), taken = new Set(lights.map(L => L.x + ':' + L.y));
  for (let i = 0, acc = 0; i < OR.length - 1; i++) {
    const [ax, az] = OR[i], [bx, bz] = OR[i + 1], len = Math.hypot(bx - ax, bz - az), step = 12 / PL.U;
    for (let d = acc; d < len; d += step) {
      const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
      const x = Math.round(Cx + f * X / Z), y = Math.round(YL + f * (1 - ground.height(X, Z)) / Z) - 1;
      if (x < 0 || x >= Wc || y < 0 || y >= GH || taken.has(x + ':' + y)) continue;
      if (ground.Z[(y + 1) * Wc + x] < Z * 0.85) continue;
      taken.add(x + ':' + y);
      lights.push({ x, y, X, Z, kind: 'lantern', path: true });
    }
    acc = (acc - len) % step; if (acc < 0) acc += step;
  }
  paintViaduct(ground.layer, ground.X, ground.Z, cam);
  // the far as plates peeled (G5R3-18): the key block's lines and how far each place ends up gone
  const fadeMap = PL.fadeMaps(ground.layer, ground.X, ground.Z, ground.mask, Wc, GH, f, sun.dir);
  // bonfires on the river bank by the town (where the lanterns are set on the water)
  const RIV = PL.RIVER, near = [];
  for (let i = 0; i < RIV.length; i++) if (Math.hypot(RIV[i][0] - PL.TOWN.X, RIV[i][1] - PL.TOWN.Z) < 3.4) near.push(i);
  for (const q of [0.15, 0.5, 0.85]) {
    const i = near[Math.min(near.length - 1, Math.floor(q * near.length))];
    const X = RIV[i][0] + 0.16, Z = RIV[i][1];
    const x = Math.round(Cx + f * X / Z), y = Math.round(YL + f / Z);
    if (x > 0 && x < Wc && y > 0 && y < GH && ground.Z[y * Wc + x] > Z * 0.9) lights.push({ x, y, X, Z, kind: 'bonfire', river: true });
  }
  // the floating lanterns (灯籠流し), set on the water just above the town and carried down the
  // stretch below it, ~18 points (~5 km), thinning out downstream: past the town's front and away
  // along the river toward the far south-east, a trail of lights going off into the distance (the
  // river's course at night; Godot dims them with distance). The
  // river flows away from us (out of the canyon, off to the south-east): Godot moves a lantern toward
  // the start of meta.river, so that list runs from the far end back. HEAD's 26 draws for the first
  // 26 (its count before the crown is frozen), the rest from their own sequence.
  const riverRev = RIV.slice().reverse(), uTown = RIV.length - 1 - near[0];
  const river = [], RL = rng(seed * 13 + 5), SPAN = 18;
  for (let k = 0; k < 64; k++) {
    const R = k < 26 ? RH : RL, a = R(), ph = R(), sd = R();
    river.push({ u0: uTown + 0.5 - a * a * SPAN, ph, side: (sd - 0.5) * 0.06 });   // fewer further down
  }
  R8.skip(78);
  const stars = makeStars(Wc, YL, seed * 3 + 1);
  const paddyStars = [];
  for (let y = YL + 2; y < GH; y++) for (let x = 0; x < Wc; x++) {
    const v = ground.layer.idx[y * Wc + x], m = v >> 8;
    if (m !== G.paddy && m !== G.pond && m !== G.river) continue;
    if (hash2(x, y, 211) < 0.03 * (1 - smooth(60, 110, y - YL))) paddyStars.push({ x, y, X: ground.X[y * Wc + x], Z: ground.Z[y * Wc + x], kind: 'star', ph: hash2(x, y, 212) * TAU });
  }
  lights.push(...paddyStars);

  // ---------------- the gate (funnel) and the sky shore (HEAD L78-96), per height class. The JS
  // scaled the sky shore with the frame's horizon (Hs = 9 yh / 114: a taller frame sees the same
  // stretch of it, the gate always ~30% of the horizon height from the top), so it is baked for a
  // few frame heights; Godot picks the tallest class whose horizon fits and fades the shore into the
  // night sky above that class's frame (8196ebf's way: no ceiling of rock pressing down).
  const towns = [
    { X: (-0.3 * REF_W) * 38 / f, Z: 38, r: 3.2 },
    { X: (0.28 * REF_W) * 44 / f, Z: 44, r: 3.6 },
    { X: (0.02 * REF_W) * 62 / f, Z: 62, r: 4.5 },
  ];
  const ringC = { X: (0.2 * REF_W) * 31 / f, Z: 31, r: 0.95 };
  towns.push({ X: ringC.X, Z: ringC.Z, r: 2.0 });
  const ring = [];
  for (let k = 0; k < 22; k++) ring.push(k / 22 * TAU);
  const Hcl = 2.6;
  const classH = o.classes ?? [REF_H];
  const yhOf = Hk => Math.round(clamp(Hk * 0.475, Hk - 165, Hk - 118));
  const classes = classH.map((Hk, ci) => {
    const yh = yhOf(Hk);
    const D = Math.max(40, Math.round(Hk - CT - Hk * 0.36)), padTop = Math.ceil(D * P.far) + 2;
    const Hs = 9 * yh / 114, Zf = 21;
    const tipX = Cx - Math.round(REF_W * 0.05), tipY = YL - (yh - Math.round(yh * 0.3));
    const Fn = { X: (tipX - Cx) * Zf / f, Z: Zf, D: Hs - (YL - tipY) * Zf / f, R: 6.5 };
    const hazeEdgeY = YL - Math.round(clamp(yh * 0.36, 26, 100));
    const shoreH = hazeEdgeY + 25;
    const shore = run(buildSkyShoreGen({ w: Wc, h: shoreH, cx: Cx, yh: YL, f, Hs, funnel: Fn, towns, hazeEdgeY,
      pagoda: { x: 0.64, px: ox + 0.64 * REF_W, half: 0.12 * REF_W }, seed }));
    const T = shore.proj(Fn.X, Fn.Z); T[1] += 1;
    // rows kept: from a little above the tallest frame this class serves, down to the haze edge
    const top = ci + 1 < classH.length ? yhOf(classH[ci + 1]) + 40 : YL;
    const y0 = Math.max(0, YL - top);
    return { H: Hk, yh, D, padTop, Hs, Fn, T, hazeEdgeY, shoreH, y0, shore, S: Math.max(110, yh * 1.1),
      hole: { X: Fn.X * Hcl / (Hs - Fn.D), Z: Fn.Z * Hcl / (Hs - Fn.D) },
      fade: [YL - yh - padTop - 34, YL - yh - padTop + 6] };
  });
  const C0 = classes[0], shore = C0.shore, T = C0.T;

  // ---------------- cloud deck (HEAD L98-104): one for every class (its height does not scale)
  const deck = new CloudDeck({ w: Wc, h: YL, cx: Cx, yh: YL, f, Hc: Hcl, seed: seed * 5 + 2, cover: 0.5, bottom: YL - 16 });

  // ---------------- HEAD's procession plan, run only to consume the JS random sequence (the canopy
  // clumps after it must match the JS frame); its result is thrown away
  // (the count is frozen: the plain's lights no longer come from HEAD's map, and the crown the user
  // approved must keep every clump)
  const headDraws = o.headDraws ?? HEAD_DRAWS;
  RH.skip(headDraws - RH.count());

  // ---------------- rising: the plan of 8196ebf (south.js@8196ebf L106-154), verbatim but for x - ox
  const TOWN = PL.TOWN, clusters = [{ X: TOWN.X, Z: TOWN.Z }, { X: PL.HEAD.X, Z: PL.HEAD.Z }, ...PL.VILLAGES.filter(v => v !== TOWN).map(v => ({ X: v.X, Z: v.Z }))];
  for (const L of lights) {
    let best = 0, bd = 1e9;
    for (let k = 0; k < clusters.length; k++) { const d = Math.hypot(L.X - clusters[k].X, L.Z - clusters[k].Z); if (d < bd) { bd = d; best = k; } }
    L.cl = L.kind === 'star' ? 100 + Math.floor((L.x - ox) / 40) : best;
    L.on = L.kind === 'star' ? 19.4 + R8() * 0.6 : L.kind === 'window' ? 18.25 + R8() * 1.1 : L.kind === 'lantern' ? 18.6 + R8() * 0.7 : 19.0 + R8() * 0.7;
    L.ph = L.ph ?? R8() * TAU;
  }
  const byCl = new Map();
  for (const L of lights) { if (!byCl.has(L.cl)) byCl.set(L.cl, []); byCl.get(L.cl).push(L); }
  const first = lights.find(L => L.kind === 'window' && L.head);
  const second = lights.find(L => L.kind === 'bonfire' && L !== first) || lights[1];
  for (const [k, arr] of byCl) {
    arr.sort(() => R8() - 0.5);
    const rest = arr.filter(L => L !== first && L !== second), n = rest.length;
    const c = clusters[k], d = c ? Math.hypot(c.X - TOWN.X, c.Z - TOWN.Z) : 12;
    const start = 0.17 + clamp(d / 40, 0, 1) * 0.1 + R8() * 0.03;
    rest.forEach((L, i) => { L.r = start + (0.96 - start) * (i + R8() * 0.5) / Math.max(1, n); });
  }
  if (first) first.r = 0.03;
  if (second) second.r = 0.11;
  const clCentre = new Map();
  for (const k of byCl.keys()) {
    const all = lights.filter(L => L.cl === k);
    const mx = all.reduce((s, L) => s + L.x, 0) / all.length, my = all.reduce((s, L) => s + L.y, 0) / all.length;
    clCentre.set(k, [mx, my]);
  }
  const clJit = new Map();
  for (const k of byCl.keys()) clJit.set(k, [(R8() - 0.5) * 14, (R8() - 0.5) * 10, 16 + R8() * 18]);
  for (const L of lights) {
    const [mx, my] = clCentre.get(L.cl), [jx, jy, cl] = clJit.get(L.cl);
    L.p1 = [mx + jx * 0.3 + (R8() - 0.5) * 2, my - cl - 4 + (R8() - 0.5) * 2];
    const sx = lerp(T[0], mx, 0.62) + jx + (R8() - 0.5) * 3, sy = lerp(T[1], my - 40, 0.45) + jy + (R8() - 0.5) * 3;
    L.p2 = [sx, sy];
    L.p3 = [T[0] + (R8() - 0.5) * 3, T[1] + (R8() - 0.5) * 2];
    L.dur = 7.2 + hash2(L.cl, 7, 41) * 2.4 + R8() * 0.3;
    if (L === first || L === second) {
      L.solo = true;
      L.p1 = [L.x, L.y - (L.y - T[1]) * 0.75];
      L.p2 = [lerp(L.x, T[0], 0.35), T[1] + (L.y - T[1]) * 0.12];
      L.dur = 11;
    }
  }

  // ---------------- the wave (HEAD L214-220)
  // the far spreads from the plain under the gate (HEAD's town lay under it; the 3D town is right of it
  // now): the ground point under the gate's tip ~4.7 km out, so the ring crosses the whole plain
  const Zc = 26, Xc = (T[0] - Cx) / f * Zc;
  const noFront = new Uint8Array(Wc * GH);
  for (let i = 0; i < noFront.length; i++) { const m = ground.layer.idx[i] >> 8; noFront[i] = m === G.roof || m === G.roofLit || m === G.thatch || m === G.wall || m === G.kura || m === G.wood || m === G.iron ? 1 : 0; }
  const wave = new Wave({ w: Wc, h: GH, X: ground.X, Z: ground.Z, mask: ground.mask, Xc, Zc, R: Math.hypot(Xc, Zc) - 0.05, f, cx: Cx, yl: YL, noFront });
  for (const L of lights) L.arr = wave.arrivalOf(L.X, L.Z);

  // ---------------- the canopy (HEAD L233-253), reference clumps exact, extensions with RX
  const Dmax = o.Dmax ?? D0;
  const oyC = o.canopyTop ?? 0;                   // canvas rows above the reference layer's row 0
  const CH = CT + Dmax + 40;
  const CHc = oyC + CH + (o.canopyBottom ?? 0);
  const ext = Wc > REF_W;
  const back = run(canopyBack(Wc, ox, oyC, CHc, CT + D0 + 40, RH, RX, ext));
  const frontC = run(canopyFront(Wc, ox, oyC, CHc, ext, RX));
  // near branches (tools/vista/bake/near.js): the camphor's own boughs in front of the lens, each its own
  // design (G5R3-10). The layer is taller than any view's share of it, so every limb runs out of the
  // view's bottom for the whole crane on every view up to ~600 rows tall (VistaSouth puts its top at
  // H + 4 - dy * near_k: at pan 0 its bottom is 150 + pan_d - 4 rows below the view's top on a tall
  // view, 2.4 pan_d - 4 on one up to 270 rows). It keeps clear of where she sits over the whole crane
  // (her sprite's box swept through every view size and pan: canvas columns 555..587, rows above 108).
  // HEAD's sprays drew from RH and RX; the same number of draws is made here so that everything after
  // (the stirring sprays) keeps its random values.
  for (let i = 0; i < 7 * 22; i++) RH();
  if (ext) for (let i = 0; i < 6 * 22; i++) RX();
  const nearH = REF_H + 190, sitX = Math.round(ox + REF_W * 0.62);
  const nearL = run(nearCrown(Wc, ox, nearH, ext, { x0: sitX - 22, x1: sitX + 24, y1: 114 }));
  const stir = [];
  const stirX = [0.05, 0.17, 0.3, 0.88, 0.97];
  const extStir = ext ? stirExtension(ox, Wc) : [];
  for (const fx of [...stirX, ...extStir]) {
    const isExt = !stirX.includes(fx);
    const Rr = isExt ? RX : RH;
    const x = Math.round(ox + REF_W * fx);
    let top = 0; while (top < CHc - 1 && !back.layer.idx[top * Wc + x]) top++;
    const lay = paintCanopy(26, 20, { clumps: [{ x: 13, y: 11, rx: 9 + Rr() * 2, ry: 6.5, z: 2, glint: false }], limbs: [], light: [0.72, -0.42, 0.45], cell: 3.4, cellSeed: 31 }, 120 + Math.round(fx * 100));
    stir.push({ layer: lay, x: x - 13, y: top - 12, ph: Rr() * TAU });
  }
  // where she sits on the limb, and where she stands: on the same spot (she stands up where she sat).
  // HEAD had her stand 0.07 W further along the limb (x 0.69 W), and nothing carried her there: when
  // the far came she jumped 33 px to the right in one frame (G5R2-4)
  const bx = Math.round(ox + REF_W * 0.62), sx = bx;
  const anchors = { branch: { x: bx, y: back.limbTop(bx) }, stand: { x: sx, y: back.limbTop(sx) } };

  // ---------------- palettes (LUT rows by time of day)
  const envs = [];
  for (let r = 0; r < TOD_ROWS; r++) envs.push(todEnv(todOfRow(r)));
  const envG = e => ({ ...e, sun: e.sun.map(v => v * (1 - 0.8 * e.night)) });
  const gSpace = new IdSpace().add(ground.layer.idx);
  const groundLut = lutRows(gSpace, envs.map(e => palette(GROUND_MATS, envG(e), { haze: e.mist })));
  // the far (遠化, G5R3-18): row 0 the white of the front as it passes (the event itself: HEAD's pale
  // front, houses keep the pale), rows 1..4 the land as a print losing its blocks (plain.js: the 3D
  // view's blocks and colours), in the light of the hour the far comes (20.3 h: it does not change
  // meanwhile); the key block's ink in that light goes to meta.fade
  const farPal = palette(GROUND_MATS, envG(envs[0]), { haze: envs[0].mist, far: true });
  const envW = envG(todEnv(WAVE_TOD));
  const nightPal = palette(GROUND_MATS, envW, { haze: envW.mist });
  const stagePals = [];
  for (let st = 1; st <= PL.FADE_STAGES; st++) stagePals.push(PL.fadePalette(st, nightPal));
  const farLut = lutRows(gSpace, [v => {
    const p = farPal(v), m = v >> 8;
    if (m === G.roof || m === G.roofLit || m === G.thatch || m === G.wall || m === G.kura || m === G.wood || m === G.iron) return p;
    const c = mix3([p & 255, (p >> 8) & 255, (p >> 16) & 255], [222, 230, 250], 0.34);
    return ((255 << 24) | (Math.round(c[2]) << 16) | (Math.round(c[1]) << 8) | Math.round(c[0])) >>> 0;
  }, ...stagePals], true);
  const fSpace = new IdSpace().add(back.layer.idx).add(frontC.layer.idx).add(nearL.idx);
  for (const sp of stir) fSpace.add(sp.layer.idx);
  const foliageLut = lutRows(fSpace, envs.map(e => palette(FOLIAGE_MATS, { ...e, sun: e.sun.map(v => v * (1 - 0.7 * e.night)) })));
  const sSpace = new IdSpace();
  for (const c of classes) sSpace.add(c.shore.layer.idx);
  const shoreLut = lutRows(sSpace, envs.map(e => skyShorePalette(mix3(skyAt(e, 0.3, 0.5), [104, 128, 152], 0.7))));
  // clouds: index = mat (1..3) << 8 | sun << 5 | sky << 3, look-up by (mat-1)*32 + sun*4 + sky
  const cloudLut = { w: 96, h: TOD_ROWS, data: new Uint8Array(96 * TOD_ROWS * 4) };
  envs.forEach((e, r) => {
    const pal = cloudPalette({ ...e, sun: mix3(e.sun.map(v => v * 0.9), [0.42, 0.27, 0.2], e.night) });
    for (let m = 1; m <= 3; m++) for (let s = 0; s < 8; s++) for (let k = 0; k < 4; k++) {
      const p = pal((m << 8) | (s << 5) | (k << 3)) >>> 0, o2 = (r * 96 + (m - 1) * 32 + s * 4 + k) * 4;
      cloudLut.data[o2] = p & 255; cloudLut.data[o2 + 1] = (p >> 8) & 255; cloudLut.data[o2 + 2] = (p >> 16) & 255; cloudLut.data[o2 + 3] = 255;
    }
  });
  // the shore's haze colour behind its far edge (per time of day, HEAD L300) and the sky's colours
  const shoreBand = envs.map(e => mix3(skyAt(e, 0.3, 0.5), [118, 150, 164], 0.6).map(Math.round));

  // ---------------- images
  const groundIds = gSpace.map(ground.layer.idx);
  const arrival = wave.arr;                                  // 0..254 bucket (w * 250), 255 never
  const zmap = fixed16(ground.Z, 0, 1024);                   // ground depth (for mote and lantern occlusion)
  const deckRows = deck.yb;                                  // rows 0 .. yb-1 carry density
  const deckD = fixedS16(rows(deck.D, Wc, 0, deckRows), 8192);   // the density lies in about [-2.4, 1.7]

  // the wave's pixels by arrival bucket (for the motes): 1 of 3 ground pixels, as (x, y) u16 pairs
  const buckets = new Uint32Array(256);
  const pick = [];
  for (let i = 0; i < arrival.length; i++) if (arrival[i] < 255 && hash2(i % Wc, (i / Wc) | 0, 913) < 0.34) pick.push(i);
  pick.sort((a, b) => arrival[a] - arrival[b] || a - b);
  for (const i of pick) buckets[arrival[i]]++;
  const moteXY = new Uint16Array(pick.length * 2);
  pick.forEach((i, k) => { moteXY[k * 2] = i % Wc; moteXY[k * 2 + 1] = (i / Wc) | 0; });

  const out = {
    meta: {
      shot: 'south', seed, refW: REF_W, refH: REF_H, Wc, ox, YL, GH, dyC, Cx, f, S, yh0, D0, padTop0, CT, P,
      Hcl, deckRows, deckYa: deck.ya, Xc, Zc, waveR: Math.hypot(Xc, Zc) - 0.05,
      classes: classes.map(c => ({ H: c.H, yh: c.yh, D: c.D, padTop: c.padTop, S: r3(c.S), Hs: r3(c.Hs), Fn: c.Fn, T: c.T.map(r2), hole: c.hole, hazeEdgeY: c.hazeEdgeY, shoreH: c.shoreH, y0: c.y0, fade: c.fade })),
      oyC, CH, CHc, nearH, headDraws, anchors, tod0: TOD0, todStep: TOD_STEP, todRows: TOD_ROWS,
      deckScale: 8192, zFixed: [0, 1024], counts: { lights: lights.length, stars: stars.length, paddyStars: paddyStars.length },
      river: riverRev, riverLanterns: river.map(v => [r3(v.u0), r3(v.ph), r3(v.side)]), plainU: PL.U,
      // how far the mountains were lowered to stay clear of the sky shore (plain.js mountainFit)
      mountain: (({ k0, kMin, limit, top0, topAll }) => ({ k0: r3(k0), kMin: r3(kMin), limitPx: limit, topPx: r3(top0), topWidePx: r3(topAll) }))(PL.mountainInfo()),
      // the far as a print (plain.js): the key block's ink at the hour, the blocks' fronts past the rim
      fade: { ink: PL.fadeInk(), paperAlpha: PL.PAPER_ALPHA, plateAt: PL.PLATE_AT, plateSpread: PL.PLATE_SPREAD, tod: WAVE_TOD },
      shoreBand, ringC, first: first ? lights.indexOf(first) : -1, second: second ? lights.indexOf(second) : -1,
      kinds: KINDS,
    },
    // per lamp: x y kind flags on ph r dur arr | p1 q2 q3 | X Z cl. The curve's control points are
    // affine in the gate T (8196ebf: p2 = lerp(T, centre, 0.62 / 0.45) + jitter, p3 = T + jitter), so
    // they are stored without T and Godot adds the gate of the height class in use:
    //   p2 = q2 + (0.38 T.x, 0.55 T.y), p3 = q3 + T; the two lone lights (flag 4) instead use
    //   p1 = (x, 0.25 y + 0.75 T.y), p2 = (0.65 x + 0.35 T.x, 0.88 T.y + 0.12 y).
    lights: lights.map(L => [L.x, L.y, KINDS.indexOf(L.kind), (L.far ? 1 : 0) | (L.path ? 2 : 0) | (L.solo ? 4 : 0) | (L.road === 1 ? 8 : 0) | (L.river ? 16 : 0),
      r3(L.on), r3(L.ph), r3(L.r), r3(L.dur), r3(L.arr), r2(L.p1[0]), r2(L.p1[1]),
      r2(L.p2[0] - 0.38 * T[0]), r2(L.p2[1] - 0.55 * T[1]), r2(L.p3[0] - T[0]), r2(L.p3[1] - T[1]), r3(L.X), r3(L.Z), L.cl]),
    stars: stars.map(s => [s.x, s.y, s.mag, s.col[0], s.col[1], s.col[2], r3(s.ph), r3(s.sp), s.tw ? 1 : 0]),
    // the sky shore's lamps, river glints and dance ring, per height class
    shoreSets: classes.map(c => {
      const sh = c.shore;
      return {
        lights: sh.lights.map(L => [L.x, L.y, r2(L.Z), r3(L.ph), r3(L.b), L.win ? 1 : 0]),
        flow: sh.flow.map(p => [p.x, p.y, r3(p.u), p.ri, r2(p.Z)]),
        ring: ring.map(th => sh.proj(ringC.X + Math.cos(th) * ringC.r, ringC.Z + Math.sin(th) * ringC.r).map(Math.round).concat([r3(th)])),
        yagura: sh.proj(ringC.X, ringC.Z).map(Math.round),
        strings: (() => { const q = []; for (let k = 0; k < 8; k++) { const th = k / 8 * TAU + 0.2; for (let j = 1; j <= 3; j++) q.push(sh.proj(ringC.X + Math.cos(th) * ringC.r * j / 4, ringC.Z + Math.sin(th) * ringC.r * j / 4).map(Math.round)); } return q; })(),
      };
    }),
    stir: stir.map(sp => ({ x: sp.x, y: sp.y, ph: r3(sp.ph), w: 26, h: 20 })),
    moteBuckets: Array.from(buckets),
    images: {
      ground: idImage(groundIds, Wc, GH, arrival),
      groundFade: { w: Wc, h: GH, data: fadeMap, fmt: 'rgba8' },
      groundZ: { w: Wc, h: GH, data: zmap, fmt: 'rg8' },
      ...Object.fromEntries(classes.map(c => ['shore' + c.H, idImage(sSpace.map(rows(c.shore.layer.idx, Wc, c.y0, c.shoreH)), Wc, c.shoreH - c.y0)])),
      deck: { w: Wc, h: deckRows, data: deckD, fmt: 'rg8' },
      canopyBack: idImage(fSpace.map(back.layer.idx), Wc, CHc),
      canopyFront: idImage(fSpace.map(frontC.layer.idx), Wc, CHc),
      near: idImage(fSpace.map(nearL.idx), Wc, nearH),
      stir: (() => {                                   // the stirring sprays side by side in one strip
        const w = 26 * stir.length, h = 20, ids = new Uint16Array(w * h);
        stir.forEach((sp, k) => { const m = fSpace.map(sp.layer.idx); for (let y = 0; y < h; y++) for (let x = 0; x < 26; x++) ids[y * w + k * 26 + x] = m[y * 26 + x]; });
        return idImage(ids, w, h);
      })(),
      lutGround: groundLut, lutFar: farLut, lutFoliage: foliageLut, lutShore: shoreLut, lutCloud: cloudLut,
      moteXY: { w: moteXY.length / 2, h: 1, data: new Uint8Array(moteXY.buffer), fmt: 'rg16' },
    },
  };
  // for quick previews in the page (not exported): the layers with their palettes
  out._layers = { ground, shore, deck, back, frontC, nearL, stir, lights, gSpace, fSpace, sSpace };
  return out;
}

// ---------------------------------------------------------------- canopy (HEAD L697-758)

// The reference clumps are HEAD's, in the same order and with the same draws from R; a wider canvas
// gets more crown at both sides from RX (the crown's top surface keeps rising toward the edges, as
// the bowl of the crown does, but is capped so a wide frame still looks over the plain).
function* canopyBack(Wc, ox, oyC, CHc, CH0, R, RX, ext) {
  const W = REF_W;
  const P = (fx, y, r) => [ox + W * fx, oyC + y, r];
  const limb = [P(1.06, CT - 12, 9), P(0.96, CT - 22, 8), P(0.86, CT - 29, 7), P(0.77, CT - 33, 6.4), P(0.69, CT - 35, 5.9),
    P(0.61, CT - 36, 5.3), P(0.54, CT - 36.5, 4.6), P(0.48, CT - 38, 3.6), P(0.44, CT - 41, 2.6), P(0.41, CT - 45, 1.6), P(0.39, CT - 49, 1)];
  if (ext) limb.unshift(P(1.5, CT + 22, 13), P(1.3, CT + 6, 11.5), P(1.16, CT - 3, 10));
  const clumps = [];
  const rise = u => Math.pow(Math.abs(u - 0.48) * 2, 2.2) * 20 + (u > 0.88 ? (u - 0.88) * 140 : 0);
  const riseX = u => Math.min(rise(clamp(u, -0.45, 1.5)), 70);   // extensions: capped
  const C = (x, y, o) => ({ ...o, x: ox + x, y: oyC + y });
  // ---- HEAD, exactly (rows of the reference layer, CH0 = CT + D + 40 of the 270-high frame)
  for (let x = -30; x < W + 40; x += 36 + R() * 14) {
    const u = x / W;
    clumps.push(C(x, CT - 22 - rise(u) + R() * 6, { rx: 30 + R() * 10, ry: 18 + R() * 5, z: 0.3 + R() * 0.1, ao: 1, glint: false }));
  }
  for (let x = -14; x < W + 40; x += 34 + R() * 14) {
    const u = x / W;
    clumps.push(C(x, CT - 4 - rise(u) * 0.6 + R() * 6, { rx: 30 + R() * 10, ry: 19 + R() * 5, z: 0.7 + R() * 0.1, glint: false }));
  }
  for (let x = -24; x < W + 40; x += 38 + R() * 12) clumps.push(C(x, CT + 14 + R() * 6, { rx: 34 + R() * 8, ry: 22 + R() * 4, z: 1.0 + R() * 0.1, glint: false }));
  let rowN = 0;
  for (let y = CT + 46, row = 0; y < CH0 + 24; y += 26, row++, rowN++) for (let x = -20 + (row % 2) * 20; x < W + 30; x += 40 + R() * 12) {
    clumps.push(C(x, y + R() * 8, { rx: 30 + R() * 10, ry: 20 + R() * 5, z: 1.1 + row * 0.2 + R() * 0.1, ao: row % 3 === 0 ? 1 : 0, glint: false }));
  }
  for (let k = 0; k < 4; k++) clumps.push(C(W * (0.95 + R() * 0.1), CT - 40 + k * 12 + R() * 6, { rx: 16 + R() * 8, ry: 12 + R() * 4, z: 1.7 + R() * 0.2, glint: false }));
  clumps.push(C(W * 0.39, CT - 56, { rx: 11, ry: 8, z: 1.8, glint: false }), C(W * 0.36, CT - 51, { rx: 9, ry: 6, z: 1.75, glint: false }), C(W * 0.415, CT - 62, { rx: 7, ry: 5, z: 1.8, young: 0.5, glint: false }));
  clumps.push(C(W * 0.5, CT - 45, { rx: 6, ry: 4, z: 1.6, glint: false }), C(W * 0.8, CT - 41, { rx: 7, ry: 5, z: 1.6, young: 0.4, glint: false }));
  for (let k = 0; k < 3; k++) clumps.push(C(W * (0.01 + R() * 0.08), CT - 56 + R() * 18, { rx: 14 + R() * 6, ry: 10 + R() * 4, z: 1.2 + R() * 0.3, glint: false }));
  // ---- extensions (a wider or taller canvas): the same rows continued, from RX
  if (ext || CHc - oyC > CH0) {
    const x0 = -ox - 40, x1 = Wc - ox + 40;
    for (let x = x0; x < x1; x += 36 + RX() * 14) {
      if (x >= -30 && x < W + 40) continue;
      clumps.push(C(x, CT - 22 - riseX(x / W) + RX() * 6, { rx: 30 + RX() * 10, ry: 18 + RX() * 5, z: 0.3 + RX() * 0.1, ao: 1, glint: false }));
    }
    for (let x = x0; x < x1; x += 34 + RX() * 14) {
      if (x >= -14 && x < W + 40) continue;
      clumps.push(C(x, CT - 4 - riseX(x / W) * 0.6 + RX() * 6, { rx: 30 + RX() * 10, ry: 19 + RX() * 5, z: 0.7 + RX() * 0.1, glint: false }));
    }
    for (let x = x0; x < x1; x += 38 + RX() * 12) {
      if (x >= -24 && x < W + 40) continue;
      clumps.push(C(x, CT + 14 + RX() * 6, { rx: 34 + RX() * 8, ry: 22 + RX() * 4, z: 1.0 + RX() * 0.1, glint: false }));
    }
    for (let y = CT + 46, row = 0; y < CHc - oyC + 24; y += 26, row++) for (let x = x0 + (row % 2) * 20; x < x1; x += 40 + RX() * 12) {
      if (x >= -20 && x < W + 30 && y < CH0 + 24) continue;
      clumps.push(C(x, y + RX() * 8, { rx: 30 + RX() * 10, ry: 20 + RX() * 5, z: 1.1 + row * 0.2 + RX() * 0.1, ao: row % 3 === 0 ? 1 : 0, glint: false }));
    }
  }
  if (ext) {
    // the crown the limb comes out of, right of the reference frame: it buries the limb's root
    for (let k = 0; k < 9; k++) clumps.push(C(W * (1.08 + RX() * 0.42), CT - 44 + k * 9 + RX() * 8, { rx: 18 + RX() * 10, ry: 13 + RX() * 5, z: 1.7 + RX() * 0.2, glint: false }));
    // sprays rising at the far left of a wide frame, like the ones at the reference frame's left
    for (let k = 0; k < 4; k++) clumps.push(C(W * (-0.12 - RX() * 0.4), CT - 60 + RX() * 22, { rx: 14 + RX() * 7, ry: 10 + RX() * 4, z: 1.2 + RX() * 0.3, glint: false }));
  }
  void rowN;
  const layer = yield* paintCanopyGen(Wc, CHc, { clumps, limbs: [{ pts: limb, z: 1.5 }], light: [0.72, -0.42, 0.45] }, 41);
  const limbTop = x => {
    for (let y = 0; y < CHc; y++) { const v = layer.idx[y * Wc + x]; if (v && ((v >> 8) === 6 || (v >> 8) === 7)) return y; }
    return oyC + CT - 40;
  };
  return { layer, limbTop };
}

function* canopyFront(Wc, ox, oyC, CHc, ext, RX) {
  const W = REF_W;
  const P = (fx, y, rx, ry, z) => ({ x: ox + W * fx, y: oyC + y, rx, ry, z });
  const clumps = [
    P(0.61, CT - 21, 13, 9, 3.2), P(0.71, CT - 17, 17, 11, 3.1), P(0.52, CT - 14, 15, 10, 3.15),
    P(0.84, CT - 12, 22, 14, 3.1), P(0.98, CT - 20, 20, 14, 3), P(0.4, CT - 4, 22, 13, 3),
    P(0.22, CT - 2, 24, 14, 3), P(0.05, CT - 8, 24, 15, 3),
  ];
  if (ext) for (const fx of [-0.12, -0.3, -0.48, 1.14, 1.3, 1.46]) clumps.push(P(fx, CT - 6 - RX() * 10, 22 + RX() * 6, 13 + RX() * 3, 3));
  return { layer: yield* paintCanopyGen(Wc, CHc, { clumps: clumps.map(c => ({ ...c, glint: false })), limbs: [], light: [0.72, -0.42, 0.45] }, 43) };
}

function stirExtension(ox, Wc) {
  const out = [];
  for (const fx of [-0.1, -0.27, -0.44, 1.1, 1.27, 1.44]) { const x = ox + REF_W * fx; if (x > 13 && x < Wc - 13) out.push(fx); }
  return out;
}

function norm(v) { const l = Math.hypot(...v); return v.map(q => q / l); }

// re-exported for previews
export { GROUND_MATS, FOLIAGE_MATS, CLOUD_MATS, palette, todEnv, skyAt };
