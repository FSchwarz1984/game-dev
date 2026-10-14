/* =====================================================================
   env/home — 「大楠と道祖神（家）」: the pass summit where she lives.
   The first location of the game (segment 1: prologue dusk → night,
   the first morning after the Far). ~120 × 100 m playable.

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
     z 58  ── saddle's south edge: lookout (W) │ nine graves, switchbacks (E)
     z 62..74 ── three terraces of the 九十九折 zigzag, entrance at the east edge
     z 75+ ── the drop toward the plain: treetops and haze

   createHomeMap() → the gameplay map (heightAt, waterAt, walkable,
   colliders, objects, spawn, shots, climb points) plus map.render for
   the renderer. See the API summary at the end of this file.
   ===================================================================== */
import { MapKit } from './mapkit.js';
import { Terrain, PPM } from './terrain.js';
import { TM, WM } from './groundmat.js';
import { RNG, hash2, fbm, clamp, polyDist } from './core.js';
import * as F from './flora.js';
import * as P from './props.js';
import { camphorTrunk, camphorLobe, camphorRoot, LOBES, ROOTS } from './camphor.js';
import { paintBackdrop } from './backdrop.js';

export const HOME = {
  trunk: [50, 27], hut: [40.8, 34.2], shrine: [57.6, 33.2],
  pool: [25.5, 8.0], dosojin: [121.5, 69.95], graves: [70.6, 58.75], lookout: [42.5, 60.2],
};

/** the mountainside below the south rims: rim polyline (m), the step heights from the rim down, step depth (m) */
export const SLOPES = [
  { rim: [[9, 61.8], [16, 61.3], [22, 61.2], [33, 62.3], [41, 63.2], [47, 62.6], [55, 61.2], [62.5, 60.4], [67, 60.8]], steps: [-2.5, -5.5, -8.5, -11.5, -14], dz: 3.1, seed: 0, level: 0 },
  { rim: [[-8, 63.8], [2, 63.2], [8.5, 62.2], [12, 62.4]], steps: [-5.5, -8.5, -11.5, -14], dz: 3.1, seed: 3, level: -3 },
  { rim: [[60, 74.3], [70, 74.4], [78, 75.0], [90, 74.2], [98, 74.6], [110, 74.7], [130, 75.0]], steps: [-7.5, -10.5, -14], dz: 2.9, seed: 5, level: -4.5 },
];

/** the terrain layout (shared by the bake and by tests) */
export function layoutTerrain(T) {
  const L = (poly, Z, o) => T.level(poly, Z, o);
  // base: the saddle (0 m), sun-bleached meadow
  L([[-8, -8], [130, -8], [130, 108], [-8, 108]], 0, { raw: true, top: TM.MEADOW, wall: WM.ROCK, pa: 60, pb: 110 });
  // west: the stream valley in two steps
  L([[-8, 3], [20.5, 5.5], [21.8, 16], [20.2, 25], [19.4, 33], [18.2, 39.6], [-8, 41]], -1.5, { top: TM.GRASS, wall: WM.EARTH, seed: 21, amp: 0.7, pb: 140 });
  L([[-8, 40.4], [16.4, 39.8], [15.2, 47], [12.5, 55], [8.5, 63], [-8, 66]], -3, { top: TM.GRASS, wall: WM.ROCK, seed: 23, amp: 0.6, pb: 120 });
  // the drop toward the plain (south): a steep wooded mountainside in 3 m steps below the rims
  // (each step's face hides behind the crowns of the trees standing on the step below it; see
  // SLOPES and populate), mist thickening with depth
  for (const sl of SLOPES) sl.steps.forEach((h, k) => {
    const off = sl.dz * k, rim = sl.rim.map(([x, z]) => [x, z + off + (k ? (hash2(Math.round(x), k, 5) - 0.5) * 0.8 : 0)]);
    L([...rim, [sl.rim[sl.rim.length - 1][0], 108], [sl.rim[0][0], 108]], h, { top: TM.FLOOR, wall: k % 2 ? WM.EARTH : WM.MOSSROCK, seed: 31 + k * 7 + sl.seed, amp: 0.5, scale: 2.6, pb: 150 });
  });
  // north-west: the cliff the waterfall pours over (+8 m), upper wood on top
  L([[-8, -8], [47, -8], [45.5, 1.5], [41, 3.4], [35.5, 3.9], [29.5, 4.3], [21.5, 4.6], [15, 3.5], [8, 4.4], [2, 3.2], [-8, 4]], 8, { top: TM.FLOOR, wall: WM.ROCK, seed: 41, amp: 0.45, scale: 2.5, pb: 160 });
  // north wood behind the camphor (+1.5 m, an earth bank)
  L([[44, -8], [80, -8], [79, 6], [74, 10.5], [66, 12.5], [58, 13.8], [50, 13.2], [46, 10], [44.5, 4]], 1.5, { top: TM.FLOOR, wall: WM.EARTH, seed: 43, amp: 0.6, pb: 180 });
  // north-east terrace (+3 m): the path toward the temple; the ridge beyond opens to the summit
  L([[73.5, 8], [80, 6.5], [95, 7.5], [108, 6.2], [130, 7], [130, 26.5], [114, 25.6], [100, 26.8], [90, 25.4], [82.5, 24.3], [77.5, 21.5], [74.5, 15]], 3, { top: TM.GRASS, wall: WM.MOSSROCK, seed: 47, amp: 0.55, scale: 2.5, pa: 30, pb: 90 });
  // beyond the NE ridge: nothing is painted, the backdrop (summit, tower) shows
  T.level([[74, -8], [130, -8], [130, 7.4], [108, 6.6], [95, 7.9], [80, 6.9], [73.8, 8.4]], 3, { top: TM.NONE, seed: 47, amp: 0.4, scale: 2.2 });
  // the switchback terraces of the old highway (九十九折): C −1.5, B −3, A −4.5. Each road runs
  // diagonally across its terrace and the next one turns back at a short flight of steps, so the
  // zigzag reads from above; dry-stone walls only where a road runs along a terrace edge or a flight
  // lands, grassy earth banks elsewhere.
  L([[64.5, 57.9], [130, 57.6], [130, 63.4], [112, 63.6], [96, 63.1], [80, 63.6], [67.5, 63.5], [65.2, 61]], -1.5, { top: TM.GRASS, wall: WM.EARTH, seed: 51, amp: 0.45, scale: 3, pa: 90, pb: 60 });
  L([[66.4, 63.2], [130, 63.2], [130, 69.2], [110, 69.4], [92, 68.8], [78, 69.3], [66, 69.0], [64.6, 66]], -3, { top: TM.GRASS, wall: WM.EARTH, seed: 53, amp: 0.45, scale: 3, pa: 90, pb: 50 });
  L([[64.6, 68.8], [130, 68.9], [130, 75.1], [110, 74.9], [90, 74.4], [78, 75.2], [70, 74.6], [62.6, 74.2], [62.2, 71]], -4.5, { top: TM.GRASS, wall: WM.MOSSROCK, seed: 55, amp: 0.4, scale: 3, pa: 90, pb: 70 });
  // the saddle's south rim above terrace C: a dry-stone wall by the graves and the top flight, a bank further east
  T.zone([[63, 50], [101, 50], [101, 58.2], [63, 58.2]], { wall: WM.STONEWALL, raw: true });
  T.zone([[97, 61.5], [126, 61.5], [126, 64.6], [97, 64.6]], { wall: WM.STONEWALL, raw: true });   // under road C's east end
  T.zone([[63, 67.2], [86, 67.2], [86, 70.4], [63, 70.4]], { wall: WM.STONEWALL, raw: true });     // under road B's west end
  // material zones
  T.zone([[33, 25], [44, 22.5], [58, 23], [68, 27.5], [70, 36], [66, 45], [56, 49.5], [42, 48.5], [33, 42], [31, 33]], { top: TM.CLEAR, pa: 110, only: [TM.MEADOW], seed: 61, amp: 1.2 });
  T.zone([[40.5, 22.5], [49, 20.5], [58, 22], [61.5, 27.5], [60.8, 33.5], [55, 31], [50, 30.6], [45, 31], [39, 31.5]], { top: TM.MOSS, pa: 60, only: [TM.CLEAR, TM.MEADOW], seed: 63, amp: 0.8 });
  T.zone([[65.5, 57.6], [74, 57.4], [81.5, 57.8], [82.4, 60.2], [80.6, 62.8], [73, 62.2], [66.4, 62.9]], { top: TM.MOSS, pa: 90, only: [TM.GRASS], seed: 69, amp: 0.7, scale: 1.6 }); // graves terrace
  T.zone([[18, 6], [33, 5], [34, 13], [26, 15.5], [19, 14]], { top: TM.MOSS, pa: 40, only: [TM.MEADOW, TM.GRASS], seed: 65 }); // around the pool
  T.zone([[18, 14], [24, 15], [21, 40], [16, 40]], { top: TM.GRASS, pb: 60, only: [TM.MEADOW], seed: 66 });
  T.zone([[44, 13], [80, 12], [80, 17], [44, 18]], { top: TM.FLOOR, pb: 140, only: [TM.MEADOW, TM.CLEAR], seed: 67, amp: 1.6 }); // litter under the north side of the crown
  // the old highway: switchback roads (trodden earth with ruts), the saddle stretch paved (石畳)
  T.road([[131, 71.8], [122, 72.1], [112, 72.4], [100, 72.6], [88, 72.4], [76, 72.0], [68.4, 71.4]], 2.5, { mat: TM.PATH, rut: 150, edge: 0.7 });
  T.road([[68.6, 68.1], [72, 68.0], [80, 67.6], [92, 67.0], [104, 66.5], [113.8, 65.8]], 2.3, { mat: TM.PATH, rut: 140, edge: 0.6 });
  T.road([[113.8, 62.9], [108, 62.2], [100, 61.2], [90, 60.0], [84, 59.6]], 2.3, { mat: TM.PATH, rut: 120, edge: 0.6 });
  T.road([[84, 57.3], [80.5, 54.6], [74, 49.6], [65, 45.2], [56, 42.2], [46.5, 40.8], [39, 40.6]], 2.6, { mat: TM.PAVE, moss: 120, wobble: 0.5 });
  T.road([[39, 40.6], [31, 38.6], [24.5, 36.6]], 1.8, { mat: TM.PATH, rut: 0, edge: 0.6 });
  T.road([[18.5, 33.6], [12, 31.2], [4, 31], [-9, 30.4]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.7 });
  T.road([[61.5, 37.5], [66.5, 33.5], [71.5, 30.5], [76.6, 28.9]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.6 }); // toward the NE steps
  T.road([[77.5, 23.6], [84, 19.4], [95, 17.6], [110, 17.2], [131, 16.4]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.6 }); // the north loop
  T.road([[39, 38], [31, 30], [27, 20], [26.5, 14.5]], 1.2, { mat: TM.PATH, rut: 0, edge: 0.8, wobble: 1 }); // to the pool
  // stone steps: the three switchback bends, the NE climb, the west descent
  T.stairs([84, 60.0], [84, 57.2], 2.8, -1.5, 0, 6);
  T.stairs([113.8, 65.8], [113.8, 62.9], 2.8, -3, -1.5, 6);
  T.stairs([68.4, 71.4], [68.4, 68.4], 2.8, -4.5, -3, 6);
  T.stairs([77.3, 28.8], [77.3, 23.4], 2.6, 0, 3, 15);
  T.stairs([22.4, 37.6], [20.6, 33.4], 2.2, -1.5, 0, 8);
  // (the surface roots are lying sprites placed in populate(); the trunk's foot covers their bases)
  const [tx, tz] = HOME.trunk;
  // water: the pool under the falls, the channel on the cliff top, the stream to the west valley
  T.stream([[25.5, -8], [25.5, -2], [25.6, 4.6]], 2.4, [8.06, 8.06, 8.06], { step: true, speed: 1.1, depth: 0.3 });
  T.pool(HOME.pool[0], HOME.pool[1], 5.2, 4.1, -0.6, 1.0, { seed: 9, amp: 0.85, rot: 0.25 });
  T.stream([[23.6, 11.4], [21.2, 15.2], [19.6, 18.4], [17.8, 22], [15.6, 27.5], [13.4, 33.6], [11.9, 38.6], [10.4, 42.2], [8.2, 48.4], [5.4, 55.2], [2.6, 61], [-1, 66], [-9, 71]], 1.9,
    [-0.68, -0.68, -1.62, -1.62, -1.62, -1.62, -1.62, -3.12, -3.12, -3.12, -3.12, -5.62, -8.62], { step: true, speed: 0.9, depth: 0.35 });
}

/** named camera framings: target = the world point at the screen centre (metres) + follow speed */
export function homeShots() {
  const S = (x, z, y = 0, speed = 3) => ({ x, z, y, speed });
  return {
    saddle: S(50, 28.4, 0), hut: S(42.6, 31.4, 0), shrine: S(56.2, 31.2, 0),
    path: S(107, 65.6, -2.4), graves: S(75, 61, -1.5), dosojin: S(119.5, 70.6, -4.5), eastRoad: S(117, 72.5, -4.5),
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
  S('camphorTrunk', () => camphorTrunk(3));
  ROOTS.forEach((r, i) => S('camphorRoot' + i, () => camphorRoot(i + 1, r[3], r[4], r[5], r[2], 0.6, r[6])));
  for (const l of LOBES) S(l[0], () => camphorLobe(l[6], l[4], l[5]));
  for (let i = 0; i < 5; i++) S('cedar' + i, () => F.cedar(i + 1, 150 + (i % 3) * 18, 40 + (i % 2) * 8));
  for (let i = 0; i < 3; i++) S('cedarBig' + i, () => F.cedar(i + 11, 210 + i * 14, 52));
  for (let i = 0; i < 3; i++) S('pine' + i, () => F.pine(i + 1, 104 + i * 12, 0));
  S('pineLean', () => F.pine(9, 118, 0.9));
  for (let i = 0; i < 3; i++) S('maple' + i, () => F.maple(i + 3, false, 92 + i * 8));
  for (let i = 0; i < 2; i++) S('mapleRed' + i, () => F.maple(i + 9, true, 96));
  for (let i = 0; i < 4; i++) S('camellia' + i, () => F.bush(i + 1, 'camellia', 30 + i * 4, 20 + (i % 2) * 6));
  for (let i = 0; i < 3; i++) S('azalea' + i, () => F.bush(i + 11, 'azalea', 26 + i * 4, 15 + i * 2));
  for (let i = 0; i < 2; i++) S('hydrangea' + i, () => F.hydrangea(i + 1));
  for (let i = 0; i < 4; i++) S('fern' + i, () => F.fern(i + 1, 0.75 + (i % 3) * 0.15));
  for (let i = 0; i < 3; i++) S('sasa' + i, () => F.sasa(i + 1, 0.8 + i * 0.15));
  for (let i = 0; i < 4; i++) S('susuki' + i, () => F.susuki(i + 1, i < 3));
  for (let i = 0; i < 2; i++) S('lily' + i, () => F.lily(i + 1));
  for (let i = 0; i < 3; i++) S('moss' + i, () => F.mossClump(i + 1, 12 + i * 4));
  for (let i = 0; i < 3; i++) S('bamboo' + i, () => F.bamboo(i + 1, 140 + i * 16));
  for (let i = 0; i < 8; i++) S('tuft' + i, () => F.tuft(i + 1, i < 4 ? 0 : i < 5 ? 1 : i < 6 ? 2 : 3));
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
   placement
   --------------------------------------------------------------------- */
const AVOID = new Set([TM.PATH, TM.PAVE, TM.STEP, TM.ROOT, TM.BED]);
function populate(K) {
  const T = K.T, R = RNG(2026);
  registerSprites(K);
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
  // ---- home: the hut under the roots, her things, the chopping block
  const [hx, hz] = HOME.hut;
  place('hut', hx, hz, { name: 'hut', box: [-2.85, -3.4, 2.85, 0.1], keep: 4.5 });
  place('oldBackFrame', hx + 3.4, hz + 0.35, { name: 'oldBackFrame', keep: 0.6 });
  place('load', tx - 2.6, tz + 3.9, { name: 'load', keep: 0.8 });
  place('stump', hx - 4.2, hz + 1.6, { name: 'stump', collide: 0.5, keep: 1 });
  place('dango2', HOME.shrine[0] - 0.55, HOME.shrine[1] + 0.25, { name: 'dango', y: 0.36 });
  // ---- the shrine and its fallen eave beam
  const [sx, sz] = HOME.shrine;
  place('shrine', sx, sz, { name: 'shrine', box: [-0.9, -1.0, 0.9, 0.05], keep: 1.8 });
  place('eaveBeam', sx + 2.5, sz + 2.0, { name: 'eaveBeam', keep: 1.4 });
  place('ishidoro', sx + 2.6, sz - 0.4, { name: 'ishidoro', collide: 0.45, keep: 0.8 });
  // ---- the paired dōsojin by the east entrance, the offering ledge before them
  const [dx_, dz_] = HOME.dosojin;
  place('dosojin', dx_, dz_, { name: 'dosojin', collide: 0.6, keep: 1.6 });
  place('offeringLedge', dx_, dz_ + 0.75, { name: 'offeringLedge', box: [-0.7, -0.15, 0.7, 0.2] });
  // ---- the nine nameless graves on the terrace just below the saddle, a lantern pole at each
  const graves = [];
  for (let k = 0; k < 9; k++) {
    const gx = HOME.graves[0] + k * 1.22 + (hash2(k, 1, 3) - 0.5) * 0.18, gz = HOME.graves[1] + (hash2(k, 2, 3) - 0.5) * 0.22;
    const gs = place('grave' + k, gx, gz, { name: 'grave' + k, collide: 0.3, flip: k % 3 === 1 });
    const px = gx - 0.42, pz = gz - 0.12;
    place('lanternPole' + (k % 3), px, pz, { name: 'lanternPole' + k });
    const gy = T.heightAt(px, pz);
    graves.push({ x: gx, z: gz, y: T.heightAt(gx, gz), part: 'grave' + k, pole: 'lanternPole' + k, hook: { x: px + 0.2, z: pz + 0.01, y: gy + 1.0 } });
    keep.push([gx, gz, 0.9]);
  }
  place('spiritAnimals', HOME.graves[0] + 4.9, HOME.graves[1] + 1.25, { name: 'spiritAnimals' });
  keep.push([HOME.graves[0] + 4.9, HOME.graves[1] + 1.25, 1]);
  // ---- signposts
  place('michishirube', 66.8, 34.6, { name: 'michishirube', collide: 0.3, keep: 1 });
  place('signboard', 86.4, 56.9, { name: 'signboard', collide: 0.3, keep: 1 });
  place('signboard', 126.2, 70.3, { name: 'signboardEast', collide: 0.3, keep: 1, flip: true });
  // ---- the lookout on the south rim: a leaning pine, a fence, a log seat
  place('pineLean', 37.6, 61.2, { name: 'lookoutPine', collide: 0.5, keep: 2 });
  place('fence', 44.5, 62.0, { name: 'lookoutFence', box: [-1.6, -0.2, 1.6, 0.25], keep: 2 });
  place('logSeat', 46.5, 60.2, { name: 'lookoutSeat', box: [-0.9, -0.3, 0.9, 0.2], keep: 1.4 });
  // ---- stepping stones across the stream on the west trail; rocks round the pool
  for (const [i, x, z] of [[0, 17.4, 32.6], [1, 16.0, 32.2], [2, 14.7, 31.9]]) place('stepStone' + i, x, z, { y: -1.55, name: 'stepStone' + i });
  for (const [n, x, z, c] of [['boulder0', 30.6, 6.0, 1.3], ['rock2', 20.6, 7.6, 0.6], ['rock1', 30.8, 10.6, 0.5], ['boulder2', 19.5, 4.9, 1.6], ['rock3', 33.5, 7.8, 0.7], ['rock0', 22.4, 12.6, 0.4]]) place(n, x, z, { collide: c, keep: c + 0.4 });
  // ---- trees: framing the clearing, the ridge window, the edges; clumped with open ground between
  const tree = (n, x, z, c = 0.55, o = {}) => { if (!o.force && !free(x, z, 1.2)) return null; return place(n, x, z, Object.assign({ collide: c, keep: 2.2, flip: R() < 0.5 }, o)); };
  // north-west wood and the west edge
  for (const [n, x, z] of [['cedarBig0', 3, 6], ['cedar1', 9, 9.5], ['cedarBig1', -2, 16], ['cedar3', 5, 24.5], ['cedarBig2', -1, 33], ['cedar0', 4.5, 44], ['cedar2', -1.5, 52], ['cedar4', 6.5, 58.5]]) tree(n, x, z, 0.6, { force: true });
  tree('mapleRed0', 31.2, 12.6, 0.4); tree('maple0', 12.6, 20.6); tree('maple1', 9, 37.6); tree('mapleRed1', 24.5, 27.4, 0.4);
  // around the camphor: camellias and hydrangeas in its shade
  for (const [n, x, z] of [['camellia0', 34.8, 31.8], ['camellia1', 36.4, 27.4], ['hydrangea0', 61.6, 33.9], ['camellia2', 63.2, 29.4], ['hydrangea1', 44.6, 36.6], ['camellia3', 56.4, 25.4], ['azalea0', 35.4, 36.4]]) if (ground(x, z)) place(n, x, z, { keep: 1 });
  // the north-east terrace and its ridge: pines against the sky, the window left open for the tower
  for (const [n, x, z] of [['cedarBig0', 77.2, 11.2], ['cedar2', 80.5, 14.6], ['pine0', 92.5, 12.4], ['pine2', 118.4, 12.6], ['cedar1', 124.5, 18.6], ['maple2', 88.4, 21.6]]) tree(n, x, z, 0.5, { force: true });
  // the east side of the saddle: a few pines in the meadow, cedars closing the east edge
  for (const [n, x, z] of [['pine1', 98.6, 38.4], ['pine0', 109.4, 47.6], ['cedar3', 123.6, 33.5], ['cedarBig1', 125.8, 44.2], ['cedar4', 122.6, 52.4], ['maple0', 92.2, 29.6]]) tree(n, x, z, 0.5, { force: true });
  // the mountainside below the rims: two staggered rows of trees on every step, each chosen so its
  // crown tops out about 2 m above the walkable rim (sl.level) — high enough to hide the step above,
  // never so high that it covers the road or the lookout — so from a rim one sees an unbroken canopy
  // falling away row after row into the haze: broadleaf just below the rim, then cedars.
  // (The drop is suggested, not shown; the plain itself is another layer's job.)
  let nb = 0;
  for (const sl of SLOPES) sl.steps.forEach((h, k) => {
    const x0 = sl.rim[0][0], x1 = sl.rim[sl.rim.length - 1][0], want = sl.level + 2.2 - h; // metres of tree
    const kind = want < 2.6 ? 'shrub' : want < 6.6 ? 'broad' : want < 9.8 ? 'cedar' : 'big';
    const gap = kind === 'shrub' ? 2.2 : kind === 'broad' ? 2.5 : kind === 'cedar' ? 2.5 : 2.9;
    for (let row = 0; row < 2; row++) for (let x = x0 + R.range(0, gap) + row * gap * 0.5; x < x1; x += gap * R.range(0.8, 1.2)) {
      let zr = sl.rim[0][1]; for (let i = 0; i < sl.rim.length - 1; i++) if (x >= sl.rim[i][0] && x <= sl.rim[i + 1][0]) { const t = (x - sl.rim[i][0]) / (sl.rim[i + 1][0] - sl.rim[i][0]); zr = sl.rim[i][1] + (sl.rim[i + 1][1] - sl.rim[i][1]) * t; }
      const z = zr + sl.dz * k + (row ? R.range(1.9, sl.dz - 0.3) : R.range(0.6, 1.4));
      const g = T.heightAt(x, z); if (g > h + 0.2 || g < h - 0.2) continue; // only on this step
      const name = 'slope' + nb++, flip = R() < 0.5;
      if (kind === 'shrub') place(R.pick(['camellia0', 'camellia2', 'azalea1', 'azalea2', 'sasa1', 'camellia3']), x, z, { y: h, flip, name });
      else if (kind === 'broad') place(R() < 0.8 ? 'maple' + R.int(0, 2) : 'pine' + R.int(0, 1), x, z, { y: h, flip, name });
      else if (kind === 'cedar') place(R() < 0.8 ? 'cedar' + R.int(0, 4) : 'maple' + R.int(0, 2), x, z, { y: h, flip, name });
      else place(R() < 0.7 ? 'cedarBig' + R.int(0, 2) : 'cedar' + R.int(0, 4), x, z, { y: h, flip, name });
    }
  });
  // the switchback terraces: shrubs and sasa at the foot of each bank and along each lip, a few small
  // trees and boulders, susuki on the open stretches — the hillside the road was cut into
  const verge = (x0, x1, zf, zl, h) => {
    for (let x = x0 + R.range(0, 2); x < x1; x += R.range(2.2, 4.4)) {
      for (const [z, pool] of [[zf + R.range(0.3, 0.9), ['sasa0', 'sasa1', 'sasa2', 'azalea0', 'azalea1', 'camellia1', 'fern1', 'fern2']], [zl - R.range(0.4, 0.9), ['azalea1', 'azalea2', 'sasa1', 'susuki0', 'susuki2', 'camellia3']]]) {
        if (R() < 0.3) continue; if (!ground(x, z, 0.4) || !free(x, z, 0.7)) continue; if (Math.abs(T.heightAt(x, z) - h) > 0.1) continue;
        place(R.pick(pool), x, z, { flip: R() < 0.5 }); keep.push([x, z, 0.8]);
      }
    }
  };
  verge(86, 128, 57.9, 63.2, -1.5); verge(66, 128, 63.4, 68.9, -3); verge(64, 128, 69.0, 74.6, -4.5);
  // and the ground between the roads is hillside undergrowth, not lawn: sasa, ferns, azaleas, susuki
  const fill = (x0, x1, z0, z1, h, n) => {
    for (let k = 0, c = 0; k < n * 40 && c < n; k++) {
      const x = R.range(x0, x1), z = R.range(z0, z1);
      if (Math.abs(T.heightAt(x, z) - h) > 0.1 || !ground(x, z, 0.5) || !free(x, z, 0.75)) continue;
      let road = false; for (const [dx, dz] of [[1.1, 0], [-1.1, 0], [0, 1.1], [0, -1.1], [0.8, 0.8], [-0.8, 0.8], [0.8, -0.8], [-0.8, -0.8]]) { const t = T.topAt(x + dx, z + dz); if (t === TM.PATH || t === TM.STEP || t === TM.PAVE) road = true; }
      if (road) continue;
      const sunny = fbm(x * 0.15, z * 0.15, 2, 77) > 0.52;
      place(R.pick(sunny ? ['susuki0', 'susuki1', 'susuki3', 'sasa1', 'azalea2', 'fern2'] : ['sasa0', 'sasa1', 'sasa2', 'fern0', 'fern1', 'fern3', 'azalea0', 'camellia2']), x, z, { flip: R() < 0.5 });
      keep.push([x, z, 0.75]); c++;
    }
  };
  fill(86, 128, 57.8, 63.4, -1.5, 46); fill(66, 128, 63.2, 69.2, -3, 56); fill(64, 128, 68.9, 74.8, -4.5, 46);
  for (const [n, x, z] of [['pine1', 124.6, 60.4], ['maple1', 101.5, 64.4], ['pine0', 91.6, 69.8], ['mapleRed0', 76.4, 64.6], ['maple2', 107.6, 69.9], ['boulder1', 95.4, 62.3], ['boulder0', 80.6, 73.6], ['rock3', 118.6, 67.2], ['boulder2', 104.4, 73.9]])
    if (ground(x, z, 0.5) && free(x, z, 1.2)) place(n, x, z, { flip: R() < 0.5, collide: n.startsWith('rock') || n.startsWith('boulder') ? 0.6 : 0.45, keep: 1.6 });
  // undergrowth: ferns and sasa in the shade, susuki and lilies on the open saddle, moss on the roots' feet
  const under = (names, n, test, sp = 1.2) => { let c = 0; for (let k = 0; k < n * 30 && c < n; k++) { const x = R.range(-4, 124), z = R.range(4, 74); if (!test(x, z)) continue; if (!ground(x, z, 0.45) || !free(x, z, sp)) continue; place(R.pick(names), x, z, { flip: R() < 0.5 }); keep.push([x, z, sp * 0.8]); c++; } };
  const shade = (x, z) => Math.hypot(x - tx, (z - tz) * 1.2) < 16 || x < 22 || (x > 74 && z < 26);
  under(['fern0', 'fern1', 'fern2', 'fern3', 'sasa0', 'sasa1'], 70, (x, z) => shade(x, z) && fbm(x * 0.12, z * 0.12, 2, 5) > 0.45, 1.3);
  under(['susuki0', 'susuki1', 'susuki2', 'susuki3'], 46, (x, z) => x > 70 && z > 27 && z < 57 && fbm(x * 0.1, z * 0.1, 2, 7) > 0.5, 1.6);
  under(['lily0', 'lily1'], 10, (x, z) => x > 64 && z > 28 && z < 56, 3);
  under(['moss0', 'moss1', 'moss2'], 24, (x, z) => Math.hypot(x - tx, z - tz) < 11 || (x < 34 && z < 16), 0.9);
  under(['hydrangea0', 'hydrangea1'], 5, (x, z) => x < 22 && z > 12 && z < 40, 2.5);
  under(['rock0', 'rock1', 'rock2', 'rock3'], 22, (x, z) => true, 2);
  // grass tufts (sway, cast no shadow): dense in the meadow, thin in the clearing, none on roads
  for (let k = 0, c = 0; k < 60000 && c < 5200; k++) {
    const x = R.range(-5, 125), z = R.range(-2, 75); const t = T.topAt(x, z);
    if (!(t === TM.GRASS || t === TM.MEADOW || t === TM.CLEAR || t === TM.MOSS)) continue;
    const dens = fbm(x * 0.09, z * 0.09, 3, 41) * (t === TM.MEADOW ? 1.25 : t === TM.CLEAR ? 0.45 : t === TM.MOSS ? 0.3 : 0.9);
    if (R() > dens * 1.3 - 0.25) continue; if (T.waterAt(x, z)) continue;
    const n = t === TM.MEADOW && R() < 0.15 ? 'tuft' + R.int(4, 7) : 'tuft' + R.int(0, 3);
    K.place(n, x, z, { flip: R() < 0.5 }); c++;
  }
  // the sprites the lead's scripts swap or add (keep them in the atlas)
  for (const n of ['hutLit', 'bonLantern', 'bonLanternLit', 'dango1', 'dangoPale', 'tuft7', 'shrineIntact']) K.rect(n);
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
  const bd = paintBackdrop();
  const par = [0.35, 0.3], camT = [px(100), px(6.5 - 3)], wsT = [px(101), 22], lpT = [bd.towerBase.x, bd.towerBase.y]; // (the tower shot frames the summit and its beacon)
  K.backdrop = { w: bd.w, h: bd.h, data: bd.data, par, x0: wsT[0] - camT[0] * (1 - par[0]) - lpT[0], y0: wsT[1] - camT[1] * (1 - par[1]) - lpT[1], red: bd.red };
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
  K.object('statues', { x: dx_, z: dz_, y: T.heightAt(dx_, dz_), parts: ['dosojin'], ledge: { x: dx_, z: dz_ + 0.75, y: T.heightAt(dx_, dz_ + 0.75) + 0.2, part: 'offeringLedge' } });
  K.object('graves', { x: HOME.graves[0] + 4.9, z: HOME.graves[1], y: -1.5, list: graves, spiritAnimals: { x: HOME.graves[0] + 4.9, z: HOME.graves[1] + 1.25, part: 'spiritAnimals' }, parts: graves.map(g => g.part) });
  K.object('lookout', { x: 44.5, z: 61.2, y: 0, faces: 'south', parts: ['lookoutFence', 'lookoutSeat', 'lookoutPine'] });
  K.object('waterfall', { x: 25.6, z: 4.6, top: 8.06, pool: { x: HOME.pool[0], z: HOME.pool[1], surface: -0.6 } });
  K.object('road', { entryEast: { x: 128, z: 71.9, y: -4.5 }, bends: [{ x: 68.4, z: 69.9, y: -3.75 }, { x: 113.8, z: 64.3, y: -2.25 }, { x: 84, z: 58.6, y: -0.75 }], saddleTop: { x: 84, z: 57.0, y: 0 },
    path: [[128, 71.9], [100, 72.6], [76, 72.0], [68.4, 71.4], [68.4, 68.4], [80, 67.6], [104, 66.5], [113.8, 65.8], [113.8, 62.9], [100, 61.2], [84, 59.6], [84, 57.2], [74, 49.6], [56, 42.2], [39, 40.6]] });
  K.object('northLoop', { start: { x: 77.3, z: 28.8 }, exit: { x: 120, z: 16.6, y: 3 } });
  K.object('signposts', { list: [{ x: 66.8, z: 34.6, part: 'michishirube' }, { x: 86.4, z: 56.9, part: 'signboard' }, { x: 126.2, z: 70.3, part: 'signboardEast' }] });
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
    R.addLight({ x: h.door.x, z: h.door.z + 0.5, y: 1.0, color: [1, 0.66, 0.36], radius: 4.2, intensity: 1.0, flicker: 0.25 }),
    R.addLight({ x: h.x - 1.6, z: h.z + 0.6, y: 1.2, color: [1, 0.7, 0.42], radius: 2.8, intensity: 0.6, flicker: 0.2 }),
  ];
  return R._homeLights;
}
/** hang (and light) a bon lantern at each grave; returns the handles */
export function hangLanterns(R, map, lit = true) {
  const out = [];
  for (const g of map.objects.graves.list) {
    const sp = R.addSprite(lit ? 'bonLanternLit' : 'bonLantern', { x: g.hook.x, z: g.hook.z, y: g.hook.y, shadow: !lit, emissive: lit });
    const L = lit ? R.addLight({ x: g.hook.x, z: g.hook.z + 0.05, y: g.hook.y - 0.3, color: [1, 0.7, 0.42], radius: 3.6, intensity: 1.1, flicker: 0.5 }) : null;
    out.push({ sprite: sp, light: L });
  }
  return out;
}

/* ---------------------------------------------------------------------
   createHomeMap(o) — bake the whole location.
   o.onProgress(k, label) optional; o.free (default true) drops bake buffers.
   --------------------------------------------------------------------- */
export function createHomeMap(o = {}) {
  const K = new MapKit({
    painted: { x0: -6, z0: -4, x1: 126, z1: 92 }, playable: { x0: 0, z0: 0, x1: 120, z1: 86 }, seed: 7,
    mistZ: 0, edgeFar: 0.65,
  });
  const T = K.T;
  layoutTerrain(T);
  populate(K);
  if (o.populate) o.populate(K);
  K.spawn = { x: 52, z: 41.5, facing: 's' };
  K.shots = homeShots();
  const map = K.bake({ free: o.free !== false });
  map.applyDay1 = R => applyDay1(R, map);
  map.hangLanterns = (R, lit) => hangLanterns(R, map, lit);
  map.lightHome = (R, on) => lightHome(R, map, on);
  return map;
}

/* =====================================================================
   API summary (what the gameplay, the story scripts and the renderer use)

   const map = createHomeMap()                       ~4.3 s in Node (terrain 2.5 s), ~4–5 s in a browser tab
   ---- gameplay (metres; x east, z south, y up; 1 m = 20 px = map.pxPerMetre)
   map.size {w, h}, map.playable {x0, z0, x1, z1}, map.painted {…}
   map.heightAt(x, z)      walkable surface height (m): saddle 0, terraces −1.5/−3/−4.5, NE terrace +3,
                           the slope steps below the rims down to −14 (not walkable: they are cliffs)
   map.waterAt(x, z)       {surface, depth} or null — water is reported here, never as a low height
   map.water(x, z)         depth (m) or 0
   map.material(x, z)      'grass' | 'clearing' | 'moss' | 'forest' | 'path' | 'paving' | 'steps' | …
   map.walkable(x, z)      nav grid (0.25 m): blocks deep water, steps > 0.3 m, colliders, the void
   map.nav {x0, z0, cell, w, h, data}, map.colliders [{type:'circle'|'box', …}]
   map.spawn {x, z, facing}
   map.objects             named things (metres), each with `parts` = sprite instance names:
     camphor   {x, z, r, height, trunk, lobes[], climb[6 holds {x, z, y}], top {x, z, y}}
     hut       {door, lit: 'hutLit', unlit: 'hut', smoke}
     oldBackFrame, load    (leaning against the hut wall / the camphor's roots)
     dango     {states: {two: 'dango2', one: 'dango1', pale: 'dangoPale'}}
     shrine    {front, intact: 'shrineIntact', broken: 'shrine', beam {x, z, part: 'eaveBeam', length 2.4}}
               (prologue: R.setImage('shrine', 'shrineIntact') and R.setHidden('eaveBeam', true); when the
               beam falls, swap back to 'shrine' and show 'eaveBeam')
     statues   (the paired 道祖神) {ledge {x, z, y, part: 'offeringLedge'}}
     graves    {list[9] {x, z, y, part, pole, hook {x, z, y}}, spiritAnimals {…}}
     lookout   {faces: 'south'}, waterfall {pool}, road {entryEast, bends[3], saddleTop, path[]},
     northLoop {start, exit}, signposts {list}
   map.shots               named framings {x, z, y, speed}: saddle, hut, shrine, path, graves, dosojin,
                           eastRoad, lookout, tower, waterfall, camphorTop; camphorFull {from, to,
                           duration, ease} pans the trunk from its roots to the crown (no zoom ever)
   ---- presentation helpers (take the renderer)
   map.applyDay1(R)        the morning after the Far: hut and old back-frame far, half the crown at 0.5,
                           pale scars on the ground, the dango pale, a little more mist
   map.hangLanterns(R, lit)  a bon lantern on each grave's hook (+ a light when lit) → handles
   map.lightHome(R, on)    the hut lit at night (sprite swap + two warm lights) → light handles
   ---- renderer side: see src/gfx/renderer.js (setTime, setCamera, setFocus, setFar, paintFar,
   addSprite, addLight, loadSheet/addActor, setImage, setHidden)
   ===================================================================== */
