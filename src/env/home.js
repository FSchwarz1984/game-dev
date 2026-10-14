/* =====================================================================
   env/home — 「大楠と道祖神（家）」: the pass summit where she lives.
   The first location of the game (segment 1: prologue dusk → night,
   the first morning after the Far). ~120 × 86 m playable.

   Coordinates: metres, x east, z south, y up (1 m = 20 px).
   Bearings follow the approved map (docs/design/map.md, map-v2.svg, as
   measured by the lead): the old highway leaves EAST-south-east toward
   九十九折宿 and climbs to the saddle in switchbacks with stone steps;
   a path north-east starts the north loop to the abandoned temple; the
   summit and its iron tower are NNE (seen over the north-east ridge);
   the waterfall 裏見之瀑 is just north of home; the kiln smoke rises in
   the east; the plain lies to the south, where the land drops away.

     z  0  ── NW: cliff with the waterfall │ north wood │ NE ridge (tower beyond)
     z 10  ── pool, stream                  │ camphor    │ NE terrace (+3 m), path → temple
     z 27  ── hut (SW of the trunk) · TRUNK (50, 27) · shrine (SE)
     z 40  ── the clearing; the old highway crosses the saddle
     z 58  ── saddle's south edge: lookout (W) │ nine graves, the top of the 九十九折 (E)
     z 58..78 ── the switchbacks: three DIAGONAL legs on benches cut into the hillside,
                 hairpins with short stone flights; the road enters at the east edge (z 72)
     z 78+ ── the drop toward the plain: treetops and haze

   The vegetation is v0.1's (env/flora1.js): cedar spires, layered-disk
   pines and maples, bamboo, ferns, sasa, susuki, hydrangea, lilies, plus
   higanbana by the graves — set in groves of mixed species and sizes
   with open ground between them, never in rows.

   createHomeMap() → the gameplay map (heightAt, waterAt, walkable,
   colliders, objects, spawn, shots, climb points) plus map.render for
   the renderer; createHomeMapAsync() does the same bake in ~20 ms slices
   so a title screen keeps animating. API summary at the end of the file.
   ===================================================================== */
import { MapKit } from './mapkit.js';
import { Terrain, PPM } from './terrain.js';
import { TM, WM } from './groundmat.js';
import { RNG, hash2, fbm, clamp, drain } from './core.js';
import * as F from './flora.js';
import * as V from './flora1.js';
import * as P from './props.js';
import { camphorTrunkG, camphorRoot, LOBES, ROOTS } from './camphor.js';
import { paintBackdropG } from './backdrop.js';

export const HOME = {
  trunk: [50, 27], hut: [40.8, 34.2], shrine: [57.6, 33.2],
  pool: [25.5, 8.0], dosojin: [121.5, 69.95], graves: [70.6, 58.75], lookout: [42.5, 60.2],
};

/** the mountainside below the south rims: rim polyline (m), step heights, step depth (m), the walkable level above */
export const SLOPES = [
  { rim: [[9, 61.8], [16, 61.3], [22, 61.2], [33, 62.3], [41, 63.2], [47, 62.6], [55, 61.2], [62.5, 60.4], [67, 60.8]], steps: [-2.5, -5.5, -8.5, -11.5, -14], dz: 3.1, seed: 0, level: 0 },
  { rim: [[-8, 63.8], [2, 63.2], [8.5, 62.2], [12, 62.4]], steps: [-5.5, -8.5, -11.5, -14], dz: 3.1, seed: 3, level: -3 },
  { rim: [[60, 77.6], [70, 78.4], [80, 78.8], [90, 78.6], [100, 77.8], [110, 76.6], [120, 75.0], [130, 74.6]], steps: [-7.5, -10.5, -14], dz: 2.9, seed: 5, level: -4.5 },
];

/* the 九十九折: three legs, each on its own level, joined by short flights at the hairpins.
   C (−1.5): from the saddle steps (86, 59.9) east-south-east to the east hairpin (115.4, 64)
   B (−3):   from the east hairpin (115.2, 67.8) west-south-west to the west hairpin (95.6, 72.4)
   A (−4.5): from the west hairpin (95.4, 76.4) east-north-east to the east edge (131, 72) */
export const ROAD = {
  C: [[86.2, 59.9], [90, 60.3], [97, 61.0], [104, 62.0], [110, 62.9], [113.6, 63.4], [115.4, 64.2]],
  B: [[115.2, 67.8], [113, 68.3], [108, 69.1], [102, 70.3], [97.8, 71.5], [95.6, 72.4]],
  A: [[95.4, 76.4], [98.4, 76.2], [104, 75.3], [110, 74.1], [115, 73.0], [119.4, 72.4], [125, 72.1], [131, 72.0]],
  saddle: [[86, 56.7], [83.4, 55.4], [80.5, 53.4], [74, 49.6], [65, 45.2], [56, 42.2], [46.5, 40.8], [39, 40.6]],
  // flights: [lower end, upper end, width, lower level, upper level, steps]
  flights: [[[86, 60.2], [86, 56.5], 2.8, -1.5, 0, 6], [[115.3, 67.9], [115.3, 63.6], 2.8, -3, -1.5, 6], [[95.5, 76.6], [95.5, 71.9], 2.8, -4.5, -3, 6]],
};

/** the terrain layout as a generator (yields between primitives); layoutTerrain(T) runs it at once */
export function layoutTerrain(T) { return drain(layoutTerrainG(T)); }
export function* layoutTerrainG(T) {
  const L = (poly, Z, o) => T.level(poly, Z, o);
  // base: the saddle (0 m), sun-bleached meadow
  L([[-8, -8], [130, -8], [130, 108], [-8, 108]], 0, { raw: true, top: TM.MEADOW, wall: WM.ROCK, pa: 60, pb: 110 }); yield 0.02;
  // west: the stream valley in two steps
  L([[-8, 3], [20.5, 5.5], [21.8, 16], [20.2, 25], [19.4, 33], [18.2, 39.6], [-8, 41]], -1.5, { top: TM.GRASS, wall: WM.EARTH, seed: 21, amp: 0.7, pb: 140 }); yield;
  L([[-8, 40.4], [16.4, 39.8], [15.2, 47], [12.5, 55], [8.5, 63], [-8, 66]], -3, { top: TM.GRASS, wall: WM.ROCK, seed: 23, amp: 0.6, pb: 120 }); yield;
  // the drop toward the plain (south): a steep wooded mountainside in 3 m steps below the rims
  for (const sl of SLOPES) for (const [k, h] of sl.steps.entries()) {
    const off = sl.dz * k, rim = sl.rim.map(([x, z]) => [x, z + off + (k ? (hash2(Math.round(x), k, 5) - 0.5) * 0.8 : 0)]);
    L([...rim, [sl.rim[sl.rim.length - 1][0], 108], [sl.rim[0][0], 108]], h, { top: TM.FLOOR, wall: k % 2 ? WM.EARTH : WM.MOSSROCK, seed: 31 + k * 7 + sl.seed, amp: 0.5, scale: 2.6, pb: 150 });
    yield 0.05;
  }
  // north-west: the cliff the waterfall pours over (+8 m), upper wood on top
  L([[-8, -8], [47, -8], [45.5, 1.5], [41, 3.4], [35.5, 3.9], [29.5, 4.3], [21.5, 4.6], [15, 3.5], [8, 4.4], [2, 3.2], [-8, 4]], 8, { top: TM.FLOOR, wall: WM.ROCK, seed: 41, amp: 0.45, scale: 2.5, pb: 160 }); yield;
  // north wood behind the camphor (+1.5 m, an earth bank)
  L([[44, -8], [80, -8], [79, 6], [74, 10.5], [66, 12.5], [58, 13.8], [50, 13.2], [46, 10], [44.5, 4]], 1.5, { top: TM.FLOOR, wall: WM.EARTH, seed: 43, amp: 0.6, pb: 180 }); yield;
  // north-east terrace (+3 m): the path toward the temple; the ridge beyond opens to the summit
  L([[73.5, 8], [80, 6.5], [95, 7.5], [108, 6.2], [130, 7], [130, 26.5], [114, 25.6], [100, 26.8], [90, 25.4], [82.5, 24.3], [77.5, 21.5], [74.5, 15]], 3, { top: TM.GRASS, wall: WM.MOSSROCK, seed: 47, amp: 0.55, scale: 2.5, pa: 30, pb: 90 }); yield;
  // beyond the NE ridge: nothing is painted, the backdrop (summit, tower) shows
  T.level([[74, -8], [130, -8], [130, 7.4], [108, 6.6], [95, 7.9], [80, 6.9], [73.8, 8.4]], 3, { top: TM.NONE, seed: 47, amp: 0.4, scale: 2.2 }); yield 0.1;
  // the switchback hillside: three levels whose edges run diagonally and curve with the legs of the road;
  // the banks between them change width along their length (wide in the west, narrow at the hairpins)
  L([[64.5, 58.6], [70, 57.8], [78, 57.4], [86, 57.6], [94, 58.2], [104, 58.6], [114, 59.6], [122, 60.4], [130, 60.8], [130, 64.6], [124, 65.2], [116, 65.9], [108, 66.2], [100, 66.6], [92, 67.0], [84, 67.4], [74, 66.5], [66, 65.2], [64.6, 62]], -1.5,
    { top: TM.GRASS, wall: WM.EARTH, seed: 51, amp: 0.6, scale: 2.6, pa: 80, pb: 60 }); yield;
  L([[64.6, 64.6], [74, 66.0], [84, 66.9], [92, 66.5], [100, 66.1], [108, 65.7], [116, 65.4], [124, 64.7], [130, 64.2], [130, 69.4], [120, 70.0], [112, 71.2], [104, 72.8], [96, 74.4], [88, 75.0], [76, 75.2], [64.6, 73.8]], -3,
    { top: TM.GRASS, wall: WM.EARTH, seed: 53, amp: 0.6, scale: 2.6, pa: 80, pb: 50 }); yield;
  L([[62.4, 73.2], [76, 74.7], [88, 74.5], [96, 73.9], [104, 72.3], [112, 70.7], [120, 69.5], [130, 69.0], [130, 75.2], [120, 75.4], [110, 76.9], [100, 78.3], [90, 79.2], [76, 79.4], [62.6, 78.4]], -4.5,
    { top: TM.GRASS, wall: WM.MOSSROCK, seed: 55, amp: 0.5, scale: 2.6, pa: 80, pb: 70 }); yield 0.15;
  // dry-stone walls where a leg runs along an edge or a flight lands; the rest are grassy earth banks
  T.zone([[63, 50], [96, 50], [96, 58.9], [63, 58.9]], { wall: WM.STONEWALL, raw: true });        // behind the graves, round the top flight
  T.zone([[106, 64.0], [126, 64.0], [126, 67.4], [106, 67.4]], { wall: WM.STONEWALL, raw: true });   // under the east hairpin
  T.zone([[88, 72.0], [104, 72.0], [104, 76.0], [88, 76.0]], { wall: WM.STONEWALL, raw: true });    // under the west hairpin
  // material zones
  T.zone([[33, 25], [44, 22.5], [58, 23], [68, 27.5], [70, 36], [66, 45], [56, 49.5], [42, 48.5], [33, 42], [31, 33]], { top: TM.CLEAR, pa: 110, only: [TM.MEADOW], seed: 61, amp: 1.2 }); yield;
  T.zone([[40.5, 22.5], [49, 20.5], [58, 22], [61.5, 27.5], [60.8, 33.5], [55, 31], [50, 30.6], [45, 31], [39, 31.5]], { top: TM.MOSS, pa: 60, only: [TM.CLEAR, TM.MEADOW], seed: 63, amp: 0.8 });
  // worn earth before the hut door and along the way to the shrine (she walks here every day)
  T.zone(Terrain.ell(41.6, 36.0, 4.6, 2.0, 20), { top: TM.CLEAR, pa: 250, only: [TM.CLEAR, TM.MEADOW, TM.MOSS], seed: 64, amp: 0.6, scale: 1.4 });
  T.zone([[44, 35.2], [52, 35.4], [57.6, 35.0], [58.4, 36.6], [52, 37.0], [44, 37.2]], { top: TM.CLEAR, pa: 230, only: [TM.CLEAR, TM.MEADOW, TM.MOSS], seed: 65, amp: 0.5, scale: 1.2 });
  T.zone([[65.5, 57.9], [74, 57.6], [81.5, 57.9], [82.4, 60.2], [80.6, 62.6], [73, 62.2], [66.4, 62.7]], { top: TM.MOSS, pa: 90, only: [TM.GRASS], seed: 69, amp: 0.7, scale: 1.6 }); // graves terrace
  T.zone([[18, 6], [33, 5], [34, 13], [26, 15.5], [19, 14]], { top: TM.MOSS, pa: 40, only: [TM.MEADOW, TM.GRASS], seed: 65 }); // around the pool
  T.zone([[18, 14], [24, 15], [21, 40], [16, 40]], { top: TM.GRASS, pb: 60, only: [TM.MEADOW], seed: 66 });
  T.zone([[44, 13], [80, 12], [80, 17], [44, 18]], { top: TM.FLOOR, pb: 140, only: [TM.MEADOW, TM.CLEAR], seed: 67, amp: 1.6 }); yield 0.2; // litter under the north side of the crown
  // the old highway: narrow worn legs (2 m), the saddle stretch paved (石畳)
  T.road(ROAD.A, 2.0, { mat: TM.PATH, rut: 150, edge: 0.75 }); yield;
  T.road(ROAD.B, 1.9, { mat: TM.PATH, rut: 140, edge: 0.7 }); yield;
  T.road(ROAD.C, 1.9, { mat: TM.PATH, rut: 120, edge: 0.7 }); yield;
  T.road(ROAD.saddle, 2.2, { mat: TM.PAVE, moss: 120, wobble: 0.5 }); yield;
  T.road([[39, 40.6], [31, 38.6], [24.5, 36.6]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.7 }); yield;
  T.road([[18.5, 33.6], [12, 31.2], [4, 31], [-9, 30.4]], 1.5, { mat: TM.PATH, rut: 0, edge: 0.8 }); yield;
  T.road([[61.5, 37.5], [66.5, 33.5], [71.5, 30.5], [76.6, 28.9]], 1.5, { mat: TM.PATH, rut: 0, edge: 0.7 }); yield; // toward the NE steps
  T.road([[77.5, 23.6], [84, 19.4], [95, 17.6], [110, 17.2], [131, 16.4]], 1.5, { mat: TM.PATH, rut: 0, edge: 0.7 }); yield; // the north loop
  T.road([[39, 38], [31, 30], [27, 20], [26.5, 14.5]], 1.2, { mat: TM.PATH, rut: 0, edge: 0.8, wobble: 1 }); yield 0.25; // to the pool
  // stone steps: the three switchback flights (each reaching well into both levels), the NE climb, the west descent
  for (const [a, b, w, z0, z1, n] of ROAD.flights) T.stairs(a, b, w, z0, z1, n);
  T.stairs([77.3, 28.8], [77.3, 23.4], 2.6, 0, 3, 15);
  T.stairs([22.4, 37.6], [20.6, 33.4], 2.2, -1.5, 0, 8); yield;
  // water: the pool under the falls, the channel on the cliff top, the stream to the west valley
  T.stream([[25.5, -8], [25.5, -2], [25.6, 4.6]], 2.4, [8.06, 8.06, 8.06], { step: true, speed: 1.1, depth: 0.3 });
  T.pool(HOME.pool[0], HOME.pool[1], 5.2, 4.1, -0.6, 1.0, { seed: 9, amp: 0.85, rot: 0.25 }); yield;
  T.stream([[23.6, 11.4], [21.2, 15.2], [19.6, 18.4], [17.8, 22], [15.6, 27.5], [13.4, 33.6], [11.9, 38.6], [10.4, 42.2], [8.2, 48.4], [5.4, 55.2], [2.6, 61], [-1, 66], [-9, 71]], 1.9,
    [-0.68, -0.68, -1.62, -1.62, -1.62, -1.62, -1.62, -3.12, -3.12, -3.12, -3.12, -5.62, -8.62], { step: true, speed: 0.9, depth: 0.35 });
  yield 0.3;
}

/** named camera framings: target = the world point at the screen centre (metres) + follow speed */
export function homeShots() {
  const S = (x, z, y = 0, speed = 3) => ({ x, z, y, speed });
  return {
    saddle: S(50, 28.4, 0), hut: S(42.6, 31.4, 0), shrine: S(56.2, 31.2, 0),
    path: S(106.5, 67.4, -2.6), graves: S(75, 61, -1.5), dosojin: S(119.5, 70.6, -4.5), eastRoad: S(117, 72.5, -4.5),
    lookout: S(43, 65, 0), tower: S(100, 6.5, 3), waterfall: S(26, 9.5, 0),
    camphorTop: S(50, 20, 18),
    camphorFull: { from: S(50, 31.5, 0), to: S(50, 21, 21), duration: 7, ease: 'inOut' },
  };
}

/* ---------------------------------------------------------------------
   sprites: every painter the map (and the lead's scripts) may use
   --------------------------------------------------------------------- */
function registerSprites(K) {
  const S = (n, fn, meta) => K.sprite(n, fn, meta);
  // the great camphor: the trunk (generator painter), roots, crown lobes in v0.1's leaf-cluster language
  S('camphorTrunk', () => camphorTrunkG(3));
  ROOTS.forEach((r, i) => S('camphorRoot' + i, () => camphorRoot(i + 1, r[3], r[4], r[5], r[2], 0.6, r[6])));
  for (const l of LOBES) S(l[0], () => V.camphorLobeG(l[6], l[4], l[5]));
  // trees (v0.1 shapes): cedar spires in several sizes, thin suppressed cedars, layered pines and maples, bamboo
  const CED = [[140, 40], [156, 44], [168, 48], [180, 46], [196, 52], [150, 42]];
  CED.forEach(([h, w], i) => S('cedar' + i, () => V.cedar(i + 1, h, w)));
  for (let i = 0; i < 2; i++) S('cedarThin' + i, () => V.cedar(i + 21, 170 + i * 22, 40, { thin: 0.6 + i * 0.15 }));
  for (let i = 0; i < 3; i++) S('cedarBig' + i, () => V.cedar(i + 11, 212 + i * 14, 56 + i * 3));
  for (let i = 0; i < 4; i++) S('pine' + i, () => V.pine(i + 1, 96 + i * 10, 0));
  S('pineLean', () => V.pine(9, 118, 0.9));
  for (let i = 0; i < 3; i++) S('maple' + i, () => V.layered(i + 3, { W: 84 + i * 8, H: 88 + i * 8 }));
  for (let i = 0; i < 2; i++) S('mapleS' + i, () => V.layered(i + 31, { W: 64 + i * 6, H: 70 + i * 6, layers: 4 }));
  for (let i = 0; i < 2; i++) S('mapleRed' + i, () => V.layered(i + 9, { red: true, W: 88 + i * 6, H: 96 }));
  for (let i = 0; i < 4; i++) S('bamboo' + i, () => V.bamboo(i + 1, 160 + i * 14));
  // shrubs and undergrowth
  for (let i = 0; i < 4; i++) S('camellia' + i, () => V.shrub(i + 1, 'camellia', 30 + i * 4, 20 + (i % 2) * 6));
  for (let i = 0; i < 3; i++) S('azalea' + i, () => V.shrub(i + 11, 'azalea', 26 + i * 4, 16 + i * 2));
  for (let i = 0; i < 3; i++) S('hydrangea' + i, () => V.hydrangea(i + 1, 1 + (i === 2 ? 0.25 : 0)));
  for (let i = 0; i < 4; i++) S('fern' + i, () => V.fern(i + 1, 0.8 + (i % 3) * 0.12));
  for (let i = 0; i < 3; i++) S('sasa' + i, () => V.sasa(i + 1, 0.85 + i * 0.12));
  for (let i = 0; i < 5; i++) S('susuki' + i, () => V.susuki(i + 1, i < 4));
  for (let i = 0; i < 2; i++) S('lily' + i, () => V.lily(i + 1));
  for (let i = 0; i < 2; i++) S('kudzu' + i, () => V.kudzu(i + 1));
  for (let i = 0; i < 2; i++) S('dayflower' + i, () => V.dayflower(i + 1));
  for (let i = 0; i < 2; i++) S('mushroom' + i, () => V.mushroom(i + 1));
  for (let i = 0; i < 3; i++) S('higan' + i, () => V.higanbana(i + 1, i === 2 ? 2 : 0));
  for (let i = 0; i < 3; i++) S('moss' + i, () => F.mossClump(i + 1, 12 + i * 4));
  for (let i = 0; i < 8; i++) S('tuft' + i, () => F.tuft(i + 1, i < 4 ? 0 : i < 5 ? 1 : i < 6 ? 2 : 3));
  // made things
  S('hut', () => P.hut({})); S('hutLit', () => P.hut({ lit: true }));
  S('shrine', () => P.shrine()); S('shrineIntact', () => P.shrine({ intact: true })); S('eaveBeam', () => P.eaveBeam());
  S('dosojin', () => P.dosojin()); S('offeringLedge', () => P.offeringLedge());
  for (let v = 0; v < 9; v++) S('grave' + v, () => P.grave(v));
  for (let v = 0; v < 3; v++) S('lanternPole' + v, () => P.lanternPole(v));
  S('bonLantern', () => P.bonLantern(false)); S('bonLanternLit', () => P.bonLantern(true));
  S('spiritAnimals', () => P.spiritAnimals());
  S('oldBackFrame', () => P.oldBackFrame()); S('load', () => P.load());
  S('dango2', () => P.dango(2)); S('dango1', () => P.dango(1)); S('dangoPale', () => P.dango('pale'));
  S('michishirube', () => P.michishirube(1)); S('signboard', () => P.signboard()); S('ishidoro', () => P.ishidoro(2));
  for (let i = 0; i < 4; i++) S('rock' + i, () => P.rock(i + 1, 14 + i * 5, 10 + i * 3));
  for (let i = 0; i < 3; i++) S('boulder' + i, () => P.rock(i + 21, 34 + i * 8, 22 + i * 4, { warm: i === 1, moss: 0.6 }));
  for (let i = 0; i < 3; i++) S('stepStone' + i, () => P.stepStone(i + 1));
  S('stump', () => P.stump(true)); S('fence', () => P.fence(64)); S('logSeat', () => P.logSeat());
}

/* ---------------------------------------------------------------------
   placement (a generator: yields between placements for the async bake)
   --------------------------------------------------------------------- */
const AVOID = new Set([TM.PATH, TM.PAVE, TM.STEP, TM.ROOT, TM.BED]);
function* populateG(K) {
  const T = K.T, R = RNG(2026);
  registerSprites(K);
  // the heavy painters first, each in small steps
  for (const n of ['camphorTrunk', ...LOBES.map(l => l[0])]) { yield* K.rectG(n); yield 0.34; }
  const keep = []; // keep-out discs (metres)
  const free = (x, z, r) => { for (const k of keep) if (Math.hypot(k[0] - x, k[1] - z) < k[2] + r) return false; return true; };
  const ground = (x, z, m = 0.6) => { // not on roads, steps, roots or water, and not on a cliff lip
    for (const [dx, dz] of [[0, 0], [m, 0], [-m, 0], [0, m], [0, -m]]) { const t = T.topAt(x + dx, z + dz); if (AVOID.has(t) || t === TM.NONE) return false; if (T.waterAt(x + dx, z + dz)) return false; }
    const h = T.heightAt(x, z); for (const [dx, dz] of [[m, 0], [-m, 0], [0, m], [0, -m]]) if (Math.abs(T.heightAt(x + dx, z + dz) - h) > 0.25) return false;
    return true;
  };
  const place = (name, x, z, o = {}) => { const s = K.place(name, x, z, o); if (o.keep) keep.push([x, z, o.keep]); return s; };
  // ---- the great camphor
  const [tx, tz] = HOME.trunk;
  place('camphorTrunk', tx, tz + 2.45, { name: 'camphorTrunk', keep: 6 });
  K.colliders.push({ type: 'circle', x: tx, z: tz, r: 3.4 });
  ROOTS.forEach((r, i) => { place('camphorRoot' + i, tx + r[0], tz + r[1], { name: 'camphorRoot' + i }); if (r[4] > 20) K.colliders.push({ type: 'circle', x: tx + r[0] + Math.cos(r[2]) * 0.9, z: tz + r[1] + Math.sin(r[2]) * 0.9, r: 0.55 }); });
  const lobes = LOBES.map(l => { place(l[0], tx + l[1], tz + l[2], { y: l[3], name: l[0] }); return l[0]; });
  yield 0.4;
  // ---- home: the hut under the roots, her things, the chopping block, hydrangeas by the hut
  const [hx, hz] = HOME.hut;
  place('hut', hx, hz, { name: 'hut', box: [-2.85, -3.4, 2.85, 0.1], keep: 4.5 });
  place('oldBackFrame', hx + 3.4, hz + 0.35, { name: 'oldBackFrame', keep: 0.6 });
  place('load', tx - 2.6, tz + 3.9, { name: 'load', keep: 0.8 });
  place('stump', hx - 4.2, hz + 1.6, { name: 'stump', collide: 0.5, keep: 1 });
  place('hydrangea2', hx - 3.6, hz + 0.6, { name: 'hutHydrangeaW', keep: 1 });
  place('hydrangea0', hx + 4.9, hz + 0.9, { name: 'hutHydrangeaE', keep: 1 });
  place('dango2', HOME.shrine[0] - 0.55, HOME.shrine[1] + 0.25, { name: 'dango', y: 0.36 });
  // ---- the shrine and its fallen eave beam
  const [sx, sz] = HOME.shrine;
  place('shrine', sx, sz, { name: 'shrine', box: [-0.9, -1.0, 0.9, 0.05], keep: 1.8 });
  place('eaveBeam', sx + 2.5, sz + 2.0, { name: 'eaveBeam', keep: 1.4 });
  place('ishidoro', sx + 2.6, sz - 0.4, { name: 'ishidoro', collide: 0.45, keep: 0.8 });
  // ---- the paired dōsojin by the road near the east entrance, the offering ledge before them
  const [dx_, dz_] = HOME.dosojin;
  place('dosojin', dx_, dz_, { name: 'dosojin', collide: 0.6, keep: 1.6 });
  place('offeringLedge', dx_, dz_ + 0.75, { name: 'offeringLedge', box: [-0.7, -0.15, 0.7, 0.2] });
  // ---- the nine nameless graves on the top terrace of the zigzag, a lantern pole at each; higanbana before them
  const graves = [];
  for (let k = 0; k < 9; k++) {
    const gx = HOME.graves[0] + k * 1.22 + (hash2(k, 1, 3) - 0.5) * 0.18, gz = HOME.graves[1] + (hash2(k, 2, 3) - 0.5) * 0.22;
    place('grave' + k, gx, gz, { name: 'grave' + k, collide: 0.3, flip: k % 3 === 1 });
    const px = gx - 0.42, pz = gz - 0.12;
    place('lanternPole' + (k % 3), px, pz, { name: 'lanternPole' + k });
    const gy = T.heightAt(px, pz);
    graves.push({ x: gx, z: gz, y: T.heightAt(gx, gz), part: 'grave' + k, pole: 'lanternPole' + k, hook: { x: px + 0.2, z: pz + 0.01, y: gy + 1.0 } });
    keep.push([gx, gz, 0.9]);
  }
  place('spiritAnimals', HOME.graves[0] + 4.9, HOME.graves[1] + 1.25, { name: 'spiritAnimals' });
  keep.push([HOME.graves[0] + 4.9, HOME.graves[1] + 1.25, 1]);
  for (const [i, x, z] of [[0, 69.2, 59.9], [1, 72.4, 60.5], [2, 76.8, 60.6], [0, 79.6, 59.9], [1, 66.8, 60.8]]) { place('higan' + i, x, z, { name: 'higan' + i + '_' + x }); keep.push([x, z, 0.5]); }
  yield 0.45;
  // ---- signposts
  place('michishirube', 66.8, 34.6, { name: 'michishirube', collide: 0.3, keep: 1 });
  place('signboard', 88.2, 56.2, { name: 'signboard', collide: 0.3, keep: 1 });
  place('signboard', 126.2, 70.3, { name: 'signboardEast', collide: 0.3, keep: 1, flip: true });
  // ---- the lookout on the south rim: a leaning pine, a fence, a log seat
  place('pineLean', 37.6, 61.2, { name: 'lookoutPine', collide: 0.5, keep: 2 });
  place('fence', 44.5, 62.0, { name: 'lookoutFence', box: [-1.6, -0.2, 1.6, 0.25], keep: 2 });
  place('logSeat', 46.5, 60.2, { name: 'lookoutSeat', box: [-0.9, -0.3, 0.9, 0.2], keep: 1.4 });
  // ---- stepping stones across the stream on the west trail; rocks round the pool
  for (const [i, x, z] of [[0, 17.4, 32.6], [1, 16.0, 32.2], [2, 14.7, 31.9]]) place('stepStone' + i, x, z, { y: -1.55, name: 'stepStone' + i });
  for (const [n, x, z, c] of [['boulder0', 30.6, 6.0, 1.3], ['rock2', 20.6, 7.6, 0.6], ['rock1', 30.8, 10.6, 0.5], ['boulder2', 19.5, 4.9, 1.6], ['rock3', 33.5, 7.8, 0.7], ['rock0', 22.4, 12.6, 0.4]]) place(n, x, z, { collide: c, keep: c + 0.4 });
  yield 0.5;

  // ---- trees, in groves: mixed species and sizes round a centre, open ground between the groves
  const pick = list => { let t = R() * list.reduce((a, b) => a + b[1], 0); for (const [n, w] of list) { t -= w; if (t <= 0) return n; } return list[0][0]; };
  const CEDARS = [['cedar0', 2], ['cedar1', 2], ['cedar2', 2], ['cedar3', 2], ['cedar4', 1.5], ['cedar5', 2], ['cedarThin0', 1], ['cedarThin1', 1], ['cedarBig0', 1], ['cedarBig1', 1], ['cedarBig2', 1]];
  const MIXED = [['cedar1', 2], ['cedar3', 2], ['cedar5', 1], ['pine0', 2], ['pine1', 2], ['pine2', 1.5], ['pine3', 1], ['maple0', 1.5], ['maple1', 1.5], ['mapleS0', 1], ['camellia1', 1.5], ['camellia2', 1], ['azalea0', 1]];
  const OPEN = [['pine0', 2], ['pine1', 2], ['pine2', 2], ['pine3', 1.5], ['maple2', 1], ['mapleS1', 1], ['mapleRed0', 0.4]];
  const trunkR = n => n.startsWith('cedarBig') ? 0.6 : n.startsWith('cedar') || n.startsWith('pine') || n.startsWith('maple') ? 0.45 : 0;
  const grove = (cx, cz, r, n, species, o = {}) => {
    for (let k = 0, c = 0; k < n * 25 && c < n; k++) {
      const a = R() * Math.PI * 2, d = Math.sqrt(R()) * r, x = cx + Math.cos(a) * d, z = cz + Math.sin(a) * d * 0.8;
      if (!(o.force || ground(x, z, 0.5)) || !free(x, z, o.sp ?? 1.1)) continue;
      const nm = pick(species), cr = trunkR(nm);
      place(nm, x, z, { flip: R() < 0.5, collide: cr || undefined, keep: o.keep ?? 1.6 }); c++;
    }
  };
  // the north-west wood and the west edge: cedar groves with gaps
  for (const [x, z, r, n] of [[3, 7, 6, 7], [-2, 20, 5, 5], [6, 30, 4, 3], [0, 40, 5, 4], [3, 51, 5, 5], [7, 58.5, 3, 2], [14, 1, 4, 3], [36, 0, 5, 4]]) { grove(x, z, r, n, CEDARS, { force: true }); yield; }
  grove(22, 26, 3, 2, [['maple0', 1], ['mapleRed1', 1], ['camellia0', 1]]);
  grove(11, 21, 3, 2, MIXED); grove(10, 38, 3, 2, MIXED);
  // a bamboo grove on the west slope above the stream, a few kudzu tangles at its edge
  grove(2, 13, 3.5, 6, [['bamboo0', 1], ['bamboo1', 1], ['bamboo2', 1], ['bamboo3', 1]], { force: true, sp: 0.7, keep: 0.8 });
  for (const [x, z] of [[6.5, 16.5], [-1, 17.5]]) if (ground(x, z, 0.5)) place('kudzu' + (x > 0 ? 0 : 1), x, z, {});
  yield 0.55;
  // the north wood behind the camphor and the north-east ridge (the tower window over x 92–110 stays open)
  for (const [x, z, r, n, sp] of [[64, 2, 6, 6, CEDARS], [74, 4, 4, 3, MIXED], [80, 13, 3.5, 3, CEDARS], [116, 11, 5, 4, MIXED], [125, 19, 4, 3, CEDARS], [86, 22, 2, 1, OPEN], [113, 22, 2, 1, OPEN]]) { grove(x, z, r, n, sp, { force: x < 82 }); yield; }
  // around the camphor: camellias and hydrangeas in its shade, a red maple at the edge of the clearing
  for (const [n, x, z] of [['camellia0', 34.8, 31.8], ['camellia1', 36.4, 27.4], ['hydrangea1', 61.6, 33.9], ['camellia2', 63.2, 29.4], ['azalea1', 56.4, 25.4], ['azalea0', 35.4, 36.6], ['mapleRed0', 31.2, 12.6], ['maple2', 12.6, 20.6]]) if (ground(x, z)) place(n, x, z, { keep: 1.2, collide: n.startsWith('maple') ? 0.45 : undefined });
  // the open saddle east of the clearing: scattered pines in ones and twos, a cedar stand closing the east edge
  for (const [x, z, r, n, sp] of [[98.6, 38.4, 2.5, 2, OPEN], [109.4, 47.6, 2, 1, OPEN], [92.2, 29.6, 2, 1, OPEN], [86, 47, 2, 1, OPEN], [124, 35, 4, 4, CEDARS], [123.5, 50, 4, 3, CEDARS], [104, 54, 2.5, 2, MIXED]]) { grove(x, z, r, n, sp, { force: x > 120 }); yield; }
  yield 0.6;
  // the mountainside below the rims: on every step two loose rows of trees whose crowns top out about 2 m
  // above the walkable rim (sl.level) — species by the height wanted, positions jittered, gaps left —
  // so from a rim the canopy falls away row after row into the haze
  let nb = 0;
  for (const sl of SLOPES) for (const [k, h] of sl.steps.entries()) {
    const x0 = sl.rim[0][0], x1 = sl.rim[sl.rim.length - 1][0], want = sl.level + 2.2 - h;
    const SP = want < 2.6 ? [['camellia0', 1], ['camellia2', 1], ['azalea1', 1], ['sasa1', 1]]
      : want < 6.6 ? [['maple0', 2], ['maple1', 2], ['mapleS0', 1], ['mapleS1', 1], ['pine0', 1.5], ['pine1', 1.5], ['camellia1', 0.6]]
      : want < 9.8 ? [['cedar0', 2], ['cedar1', 2], ['cedar2', 2], ['cedar3', 2], ['cedar5', 2], ['cedarThin0', 1], ['pine2', 1], ['pine3', 1], ['maple1', 0.8]]
      : [['cedarBig0', 2], ['cedarBig1', 2], ['cedarBig2', 2], ['cedar4', 1.5], ['cedarThin1', 1], ['cedar2', 1]];
    const gap = want < 2.6 ? 2.2 : want < 6.6 ? 2.6 : 2.8;
    for (let row = 0; row < 2; row++) for (let x = x0 + R.range(0, gap) + row * gap * 0.5; x < x1; x += gap * R.range(0.7, 1.4)) {
      if (R() < 0.12) continue; // a gap in the canopy
      let zr = sl.rim[0][1]; for (let i = 0; i < sl.rim.length - 1; i++) if (x >= sl.rim[i][0] && x <= sl.rim[i + 1][0]) { const t = (x - sl.rim[i][0]) / (sl.rim[i + 1][0] - sl.rim[i][0]); zr = sl.rim[i][1] + (sl.rim[i + 1][1] - sl.rim[i][1]) * t; }
      const z = zr + sl.dz * k + (row ? R.range(1.6, sl.dz - 0.2) : R.range(0.5, 1.5)), xx = x + R.range(-0.6, 0.6);
      const g = T.heightAt(xx, z); if (g > h + 0.2 || g < h - 0.2) continue; // only on this step
      place(pick(SP), xx, z, { y: h, flip: R() < 0.5, name: 'slope' + nb++ });
    }
    yield;
  }
  yield 0.65;
  // the switchback hillside: groves on the wide part of the benches, shrubs and sasa along every bank, susuki
  // in the open; the legs of the road stay clear (no planting within 1.1 m of a road or a flight)
  const nearRoad = (x, z) => { for (const [dx, dz] of [[1.1, 0], [-1.1, 0], [0, 1.1], [0, -1.1], [0.8, 0.8], [-0.8, 0.8], [0.8, -0.8], [-0.8, -0.8]]) { const t = T.topAt(x + dx, z + dz); if (t === TM.PATH || t === TM.STEP || t === TM.PAVE) return true; } return false; };
  const fill = (x0, x1, z0, z1, h, n, pool) => {
    for (let k = 0, c = 0; k < n * 40 && c < n; k++) {
      const x = R.range(x0, x1), z = R.range(z0, z1);
      if (Math.abs(T.heightAt(x, z) - h) > 0.1 || !ground(x, z, 0.45) || !free(x, z, 0.7) || nearRoad(x, z)) continue;
      place(pick(pool), x, z, { flip: R() < 0.5 }); keep.push([x, z, 0.7]); c++;
    }
  };
  const UNDER = [['sasa0', 2], ['sasa1', 2], ['sasa2', 1.5], ['fern0', 1], ['fern1', 1], ['fern2', 1], ['azalea0', 1], ['azalea2', 1], ['camellia2', 0.8], ['susuki0', 1], ['susuki2', 1], ['susuki4', 1]];
  for (const [x, z, r, n] of [[72, 69, 4, 4], [83, 70.4, 3, 3], [70, 76.2, 3, 3], [80, 77, 2.5, 2], [124, 62.4, 2.5, 2], [104, 59.2, 2, 1]]) { grove(x, z, r, n, MIXED, { sp: 1.4 }); yield; }
  fill(64, 130, 57.5, 67.5, -1.5, 46, UNDER); yield;
  fill(64, 130, 64, 75.5, -3, 52, UNDER); yield;
  fill(62, 130, 69, 79.5, -4.5, 40, UNDER); yield 0.7;
  // undergrowth: ferns and sasa in the shade, susuki and lilies on the open saddle, moss at the roots' feet
  const under = (names, n, test, sp = 1.2) => { let c = 0; for (let k = 0; k < n * 30 && c < n; k++) { const x = R.range(-4, 124), z = R.range(4, 74); if (!test(x, z)) continue; if (!ground(x, z, 0.45) || !free(x, z, sp)) continue; place(R.pick(names), x, z, { flip: R() < 0.5 }); keep.push([x, z, sp * 0.8]); c++; } };
  const shade = (x, z) => Math.hypot(x - tx, (z - tz) * 1.2) < 16 || x < 22 || (x > 74 && z < 26);
  under(['fern0', 'fern1', 'fern2', 'fern3', 'sasa0', 'sasa1', 'mushroom0', 'mushroom1'], 70, (x, z) => shade(x, z) && fbm(x * 0.12, z * 0.12, 2, 5) > 0.45, 1.3); yield;
  under(['susuki0', 'susuki1', 'susuki2', 'susuki3', 'susuki4'], 54, (x, z) => x > 70 && z > 27 && z < 57 && fbm(x * 0.1, z * 0.1, 2, 7) > 0.48, 1.4); yield;
  under(['lily0', 'lily1', 'dayflower0', 'dayflower1'], 16, (x, z) => x > 64 && z > 28 && z < 56, 2.5);
  under(['moss0', 'moss1', 'moss2'], 24, (x, z) => Math.hypot(x - tx, z - tz) < 11 || (x < 34 && z < 16), 0.9);
  under(['hydrangea0', 'hydrangea1'], 5, (x, z) => x < 22 && z > 12 && z < 40, 2.5);
  under(['rock0', 'rock1', 'rock2', 'rock3'], 22, () => true, 2); yield 0.75;
  // grass tufts (sway, cast no shadow): dense in the meadow, thin in the clearing, none on roads
  for (let k = 0, c = 0; k < 60000 && c < 5200; k++) {
    if ((k & 1023) === 1023) yield;
    const x = R.range(-5, 125), z = R.range(-2, 79); const t = T.topAt(x, z);
    if (!(t === TM.GRASS || t === TM.MEADOW || t === TM.CLEAR || t === TM.MOSS)) continue;
    const dens = fbm(x * 0.09, z * 0.09, 3, 41) * (t === TM.MEADOW ? 1.25 : t === TM.CLEAR ? 0.45 : t === TM.MOSS ? 0.3 : 0.9);
    if (R() > dens * 1.3 - 0.25) continue; if (T.waterAt(x, z)) continue;
    const n = t === TM.MEADOW && R() < 0.15 ? 'tuft' + R.int(4, 7) : 'tuft' + R.int(0, 3);
    K.place(n, x, z, { flip: R() < 0.5 }); c++;
  }
  // the sprites the lead's scripts swap or add (keep them in the atlas)
  for (const n of ['hutLit', 'bonLantern', 'bonLanternLit', 'dango1', 'dangoPale', 'tuft7', 'shrineIntact']) { yield* K.rectG(n); }
  yield 0.8;
  // ---- emitters (world px)
  const px = v => v * PPM;
  K.emitters.push({ type: 'leaves', area: { x0: px(tx - 20), y0: px(tz - 10), x1: px(tx + 21), y1: px(tz + 10) }, z0: px(5), z1: px(17), rate: 2.4, windK: 1, colors: [[0.36, 0.5, 0.24], [0.5, 0.6, 0.28], [0.62, 0.5, 0.26], [0.7, 0.42, 0.22]] });
  K.emitters.push({ type: 'mist', area: { x0: px(23.4), y0: px(4.6), x1: px(27.6), y1: px(6.4) }, z0: 0, z1: px(1.5), rate: 14, color: [0.9, 0.95, 1], alpha: 0.32 });
  K.emitters.push({ type: 'spray', area: { x0: px(24), y0: px(4.8), x1: px(27), y1: px(5.6) }, z: px(-0.6), rate: 16 });
  K.emitters.push({ type: 'fireflies', night: true, area: { x0: px(4), y0: px(6), x1: px(30), y1: px(46) }, rate: 3 });
  K.emitters.push({ type: 'fireflies', night: true, area: { x0: px(66), y0: px(57), x1: px(84), y1: px(63) }, rate: 1.6 });
  K.emitters.push({ type: 'fireflies', night: true, area: { x0: px(30), y0: px(30), x1: px(70), y1: px(50) }, rate: 1.2 });
  K.emitters.push({ type: 'dust', day: true, area: { x0: px(36), y0: px(30), x1: px(66), y1: px(48) }, rate: 3 });
  K.emitters.push({ type: 'insects', day: true, area: { x0: px(8), y0: px(10), x1: px(26), y1: px(40) }, rate: 0.5 });
  K.emitters.push({ type: 'smoke', x: px(hx), y: px(hz - 1.9), z: px(4.9), rate: 1.2, life: 7, alpha: 0.3, name: 'hutSmoke' });
  // ---- the far layer beyond the north-east ridge
  const bd = yield* paintBackdropG();
  const par = [0.35, 0.3], camT = [px(100), px(6.5 - 3)], wsT = [px(101), 22], lpT = [bd.towerBase.x, bd.towerBase.y]; // (the tower shot frames the summit and its beacon)
  K.backdrop = { w: bd.w, h: bd.h, data: bd.data, par, x0: wsT[0] - camT[0] * (1 - par[0]) - lpT[0], y0: wsT[1] - camT[1] * (1 - par[1]) - lpT[1], red: bd.red };
  yield 0.85;
  // ---- named objects (metres) for the gameplay and the story scripts
  K.object('camphor', { x: tx, z: tz, y: 0, r: 3.4, parts: ['camphorTrunk', ...lobes, ...ROOTS.map((_, i) => 'camphorRoot' + i)], trunk: 'camphorTrunk', lobes, height: 27,
    // holds just in front of the bark (the trunk's front plane is z 29.45, curving back toward its sides),
    // so she draws on the trunk, never behind it
    climb: [{ x: 47.3, z: 30.2, y: 0.9 }, { x: 48.4, z: 29.85, y: 1.7 }, { x: 49.3, z: 29.85, y: 2.7 }, { x: 50.1, z: 29.85, y: 3.8 }, { x: 50.6, z: 29.85, y: 5.8 }, { x: 50.3, z: 29.85, y: 8.2 }],
    top: { x: 50.6, z: 18.2, y: 24.5 } });
  K.object('hut', { x: hx, z: hz, y: 0, parts: ['hut'], door: { x: hx + 1.25, z: hz + 0.35 }, lit: 'hutLit', unlit: 'hut', smoke: 'hutSmoke' });
  K.object('oldBackFrame', { x: hx + 3.4, z: hz + 0.35, parts: ['oldBackFrame'] });
  K.object('load', { x: tx - 2.6, z: tz + 3.9, parts: ['load'] });
  K.object('dango', { x: sx - 0.55, z: sz + 0.25, y: 0.36, parts: ['dango'], states: { two: 'dango2', one: 'dango1', pale: 'dangoPale' } });
  K.object('shrine', { x: sx, z: sz, y: 0, parts: ['shrine'], front: { x: sx, z: sz + 0.9 }, intact: 'shrineIntact', broken: 'shrine',
    beam: { x: sx + 2.5, z: sz + 2.0, part: 'eaveBeam', length: 2.4 } });
  K.object('statues', { x: dx_, z: dz_, y: T.heightAt(dx_, dz_), parts: ['dosojin'], stand: { x: 119.4, z: 71.4 }, ledge: { x: dx_, z: dz_ + 0.75, y: T.heightAt(dx_, dz_ + 0.75) + 0.2, part: 'offeringLedge' } });
  K.object('graves', { x: HOME.graves[0] + 4.9, z: HOME.graves[1], y: -1.5, list: graves, stand: { x: 82.2, z: 60.4 }, spiritAnimals: { x: HOME.graves[0] + 4.9, z: HOME.graves[1] + 1.25, part: 'spiritAnimals' }, parts: graves.map(g => g.part) });
  K.object('lookout', { x: 44.5, z: 61.2, y: 0, faces: 'south', parts: ['lookoutFence', 'lookoutSeat', 'lookoutPine'] });
  K.object('waterfall', { x: 25.6, z: 4.6, top: 8.06, pool: { x: HOME.pool[0], z: HOME.pool[1], surface: -0.6 } });
  const F3 = ROAD.flights;
  K.object('road', { entryEast: { x: 119, z: 72.4, y: -4.5 }, edge: { x: 120, z: 72.3 },
    bends: [{ x: F3[2][0][0], z: (F3[2][0][1] + F3[2][1][1]) / 2, y: -3.75 }, { x: F3[1][0][0], z: (F3[1][0][1] + F3[1][1][1]) / 2, y: -2.25 }, { x: F3[0][0][0], z: (F3[0][0][1] + F3[0][1][1]) / 2, y: -0.75 }],
    saddleTop: { x: 86, z: 56.6, y: 0 },
    path: [...ROAD.A.slice().reverse(), [95.5, 74.2], ...ROAD.B.slice().reverse(), [115.3, 65.8], ...ROAD.C.slice().reverse(), [86, 58.4], ...ROAD.saddle] });
  K.object('northLoop', { start: { x: 77.3, z: 28.8 }, exit: { x: 120, z: 16.6, y: 3 } });
  K.object('signposts', { list: [{ x: 66.8, z: 34.6, part: 'michishirube' }, { x: 88.2, z: 56.2, part: 'signboard' }, { x: 126.2, z: 70.3, part: 'signboardEast' }] });
  yield 0.9;
}

/** the morning after the Far (day 1): hut far, old back-frame far, half the crown faded, pale scars, dango pale */
export function applyDay1(R, map) {
  R.setFar('hut', 1); R.setFar('oldBackFrame', 1);
  for (const n of ['lobeW2', 'lobeW3', 'lobeC3', 'lobeE5', 'lobeW4', 'lobeE1']) R.setFar(n, 0.5);
  R.setImage('dango', 'dangoPale');
  const scars = [[44, 37.5, 4.2, 1.6, -0.35], [49, 45, 5.5, 1.3, 0.25], [58.5, 50.5, 4.4, 1.1, 0.1], [40.8, 33.2, 3.6, 2.4, 0], [66, 54, 3.8, 1.0, -0.2], [76, 60.4, 3, 0.9, 0.1], [53.5, 38.8, 2.6, 1.2, 0.6], [35, 44, 3.2, 0.9, -0.5]];
  for (const [x, z, rx, rz, a] of scars) R.paintFar({ x, z, rx, rz, angle: a, amount: 0.85, ragged: 0.45 });
  R.extraMist = 0.12;
}
/** light (or put out) the hut: the lit sprite (glowing door and windows) plus a warm light spilling
    from the door and a dimmer one from the side window; returns the light handles (or []) */
export function lightHome(R, map, on = true) {
  const h = map.objects.hut; R.setImage('hut', on ? h.lit : h.unlit);
  if (R._homeLights) { for (const l of R._homeLights) l.remove(); R._homeLights = null; }
  if (!on) return [];
  R._homeLights = [
    R.addLight({ x: h.door.x, z: h.door.z + 0.5, y: 1.0, color: [1, 0.62, 0.32], radius: 4.2, intensity: 0.95, flicker: 0.25 }),
    R.addLight({ x: h.x - 1.6, z: h.z + 0.6, y: 1.2, color: [1, 0.64, 0.36], radius: 2.8, intensity: 0.55, flicker: 0.2 }),
  ];
  return R._homeLights;
}
/** hang (and light) a bon lantern at each grave; returns the handles */
export function hangLanterns(R, map, lit = true) {
  const out = [];
  for (const g of map.objects.graves.list) {
    const sp = R.addSprite(lit ? 'bonLanternLit' : 'bonLantern', { x: g.hook.x, z: g.hook.z, y: g.hook.y, shadow: !lit });
    const L = lit ? R.addLight({ x: g.hook.x, z: g.hook.z + 0.05, y: g.hook.y - 0.3, color: [1, 0.6, 0.3], radius: 3.4, intensity: 0.9, flicker: 0.5 }) : null;
    out.push({ sprite: sp, light: L });
  }
  return out;
}

/* ---------------------------------------------------------------------
   createHomeMap(o) — bake the whole location (synchronous, ~4 s).
   createHomeMapAsync(o) — the same bake in slices of ~20 ms, so the page
   keeps animating; resolves to the same map. o.onProgress(k 0..1, label).
   o.free (default true) drops the bake buffers; o.populate(K) adds things.
   --------------------------------------------------------------------- */
function* homeG(o = {}) {
  const K = new MapKit({
    painted: { x0: -6, z0: -4, x1: 126, z1: 92 }, playable: { x0: 0, z0: 0, x1: 120, z1: 86 }, seed: 7,
    mistZ: 0, edgeFar: 0.65,
  });
  yield* layoutTerrainG(K.T);
  yield* populateG(K);
  if (o.populate) o.populate(K);
  K.spawn = { x: 52, z: 41.5, facing: 's' };
  K.shots = homeShots();
  const map = yield* K.bakeG({ free: o.free !== false });
  map.applyDay1 = R => applyDay1(R, map);
  map.hangLanterns = (R, lit) => hangLanterns(R, map, lit);
  map.lightHome = (R, on) => lightHome(R, map, on);
  return map;
}
export function createHomeMap(o = {}) { return drain(homeG(o)); }
export async function createHomeMapAsync(o = {}) {
  const g = homeG(o), slice = o.sliceMs ?? 20, now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());
  let prog = 0, longest = 0;
  for (;;) {
    const t0 = now(); let r;
    do { r = g.next(); if (typeof r.value === 'number') prog = Math.max(prog, r.value); } while (!r.done && now() - t0 < slice);
    longest = Math.max(longest, now() - t0);
    if (r.done) { r.value.bakeSlices = { longestMs: Math.round(longest) }; if (o.onProgress) o.onProgress(1, 'done'); return r.value; }
    if (o.onProgress) o.onProgress(prog, prog < 0.3 ? 'terrain' : prog < 0.9 ? 'plants' : 'paint');
    await new Promise(res => setTimeout(res, 0));
  }
}

/* =====================================================================
   API summary (what the gameplay, the story scripts and the renderer use)

   const map = createHomeMap()               synchronous: ~4 s in Node, ~4–5 s in a browser tab
   const map = await createHomeMapAsync({ onProgress(k, label) })   the same, in ~20 ms slices
                                             (map.bakeSlices.longestMs reports the longest slice)
   ---- gameplay (metres; x east, z south, y up; 1 m = 20 px = map.pxPerMetre)
   map.size {w, h}, map.playable {x0, z0, x1, z1}, map.painted {…}
   map.heightAt(x, z)      walkable surface height (m): saddle 0, the zigzag benches −1.5/−3/−4.5,
                           NE terrace +3, the slope steps below the rims down to −14 (cliffs, not walkable)
   map.waterAt(x, z)       {surface, depth} or null — water is reported here, never as a low height
   map.water(x, z)         depth (m) or 0
   map.material(x, z)      'grass' | 'clearing' | 'moss' | 'forest' | 'path' | 'paving' | 'steps' | …
   map.walkable(x, z)      nav grid (0.25 m): blocks deep water, steps > 0.3 m, colliders, the void
   map.nav {x0, z0, cell, w, h, data}, map.colliders [{type:'circle'|'box', …}]
   map.spawn {x, z, facing}
   map.sprites             atlas sprite names (an array that also answers by name: map.sprites.shrineIntact)
   map.objects             named things (metres), each with `parts` = sprite instance names:
     camphor   {x, z, r, height, trunk, lobes[], climb[6 holds {x, z, y}], top {x, z, y}}
     hut       {door, lit: 'hutLit', unlit: 'hut', smoke}
     oldBackFrame, load    (leaning against the hut wall / the camphor's roots)
     dango     {states: {two: 'dango2', one: 'dango1', pale: 'dangoPale'}}
     shrine    {front, intact: 'shrineIntact', broken: 'shrine', beam {x, z, part: 'eaveBeam', length 2.4}}
               (prologue: R.setImage('shrine', 'shrineIntact') and R.setHidden('eaveBeam', true); when the
               beam falls, swap back to 'shrine' and show 'eaveBeam')
     statues   (the paired 道祖神) {stand, ledge {x, z, y, part: 'offeringLedge'}}
     graves    {list[9] {x, z, y, part, pole, hook {x, z, y}}, stand, spiritAnimals {…}}
     lookout   {faces: 'south'}, waterfall {pool}, road {entryEast, edge, bends[3], saddleTop, path[]},
     northLoop {start, exit}, signposts {list}
   map.shots               named framings {x, z, y, speed}: saddle, hut, shrine, path, graves, dosojin,
                           eastRoad, lookout, tower, waterfall, camphorTop; camphorFull {from, to,
                           duration, ease} pans the trunk from its roots to the crown (no zoom ever)
   ---- presentation helpers (take the renderer)
   map.applyDay1(R)        the morning after the Far: hut and old back-frame far, half the crown at 0.5,
                           pale scars on the ground, the dango pale, a little more mist
   map.hangLanterns(R, lit)  a bon lantern on each grave's hook (+ a warm light when lit) → handles
   map.lightHome(R, on)    the hut lit at night (sprite swap + two warm lights) → light handles
   ---- renderer side: see src/gfx/renderer.js (setTime, setCamera, setFocus, setFar, paintFar,
   addSprite, addLight, loadSheet/addActor, setImage, setHidden)
   ===================================================================== */
