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

export const HOME = {
  trunk: [50, 27], hut: [40.8, 34.2], shrine: [57.6, 33.2],
  pool: [25.5, 8.0], dosojin: [113.5, 67.9], graves: [70.6, 58.75], lookout: [42.5, 60.2],
};

/** the terrain layout (shared by the bake and by tests) */
export function layoutTerrain(T) {
  const L = (poly, Z, o) => T.level(poly, Z, o);
  // base: the saddle (0 m), sun-bleached meadow
  L([[-8, -8], [130, -8], [130, 108], [-8, 108]], 0, { raw: true, top: TM.MEADOW, wall: WM.ROCK, pa: 60, pb: 110 });
  // west: the stream valley in two steps
  L([[-8, 3], [20.5, 5.5], [21.8, 16], [20.2, 25], [19.4, 33], [18.2, 39.6], [-8, 41]], -1.5, { top: TM.GRASS, wall: WM.EARTH, seed: 21, amp: 0.7, pb: 140 });
  L([[-8, 40.4], [16.4, 39.8], [15.2, 47], [12.5, 55], [8.5, 63], [-8, 66]], -3, { top: TM.GRASS, wall: WM.ROCK, seed: 23, amp: 0.6, pb: 120 });
  // the drop toward the plain (south), far below
  L([[-8, 63.5], [8, 61.5], [22, 61.2], [33, 62.3], [41, 63.2], [47, 62.6], [55, 61.2], [62.5, 60.4], [66.5, 63], [62, 68], [60.5, 74.6], [78, 75.2], [98, 74.6], [130, 75.3], [130, 108], [-8, 108]], -14, { top: TM.FLOOR, wall: WM.DROP, seed: 31, amp: 0.9, scale: 4, pb: 150 });
  // north-west: the cliff the waterfall pours over (+8 m), upper wood on top
  L([[-8, -8], [47, -8], [45.5, 1.5], [41, 3.4], [35.5, 3.9], [29.5, 4.3], [21.5, 4.6], [15, 3.5], [8, 4.4], [2, 3.2], [-8, 4]], 8, { top: TM.FLOOR, wall: WM.ROCK, seed: 41, amp: 0.45, scale: 2.5, pb: 160 });
  // north wood behind the camphor (+1.5 m, an earth bank)
  L([[44, -8], [80, -8], [79, 6], [74, 10.5], [66, 12.5], [58, 13.8], [50, 13.2], [46, 10], [44.5, 4]], 1.5, { top: TM.FLOOR, wall: WM.EARTH, seed: 43, amp: 0.6, pb: 180 });
  // north-east terrace (+3 m): the path toward the temple; the ridge beyond opens to the summit
  L([[73.5, 8], [80, 6.5], [95, 7.5], [108, 6.2], [130, 7], [130, 26.5], [114, 25.6], [100, 26.8], [90, 25.4], [82.5, 24.3], [77.5, 21.5], [74.5, 15]], 3, { top: TM.GRASS, wall: WM.MOSSROCK, seed: 47, amp: 0.55, scale: 2.5, pa: 30, pb: 90 });
  // beyond the NE ridge: nothing is painted, the backdrop (summit, tower) shows
  T.level([[74, -8], [130, -8], [130, 7.4], [108, 6.6], [95, 7.9], [80, 6.9], [73.8, 8.4]], 3, { top: TM.NONE, seed: 47, amp: 0.4, scale: 2.2 });
  // the switchback terraces of the old highway (九十九折): C −1.5, B −3, A −4.5
  L([[64.5, 57.9], [130, 57.6], [130, 62.6], [96, 62.9], [80, 62.4], [67.5, 62.8], [65.5, 60.5]], -1.5, { top: TM.GRASS, wall: WM.STONEWALL, seed: 51, amp: 0.25, scale: 3, pa: 90, pb: 60 });
  L([[66.4, 62.4], [130, 62.4], [130, 67.2], [100, 67.4], [80, 66.9], [66.2, 67.4], [64.6, 64.5]], -3, { top: TM.GRASS, wall: WM.STONEWALL, seed: 53, amp: 0.25, scale: 3, pa: 90, pb: 50 });
  L([[64.6, 67], [130, 66.9], [130, 74.4], [110, 74.8], [90, 74.2], [70, 74.6], [62.6, 74.2], [62.2, 70]], -4.5, { top: TM.GRASS, wall: WM.DROP, seed: 55, amp: 0.4, scale: 3, pa: 90, pb: 70 });
  // the saddle's south rim above terrace C is a dry-stone wall; the lookout rim is natural rock
  T.zone([[63, 50], [130, 50], [130, 58.2], [63, 58.2]], { wall: WM.STONEWALL, raw: true });
  // material zones
  T.zone([[33, 25], [44, 22.5], [58, 23], [68, 27.5], [70, 36], [66, 45], [56, 49.5], [42, 48.5], [33, 42], [31, 33]], { top: TM.CLEAR, pa: 110, only: [TM.MEADOW], seed: 61, amp: 1.2 });
  T.zone([[40.5, 22.5], [49, 20.5], [58, 22], [61.5, 27.5], [60.8, 33.5], [55, 31], [50, 30.6], [45, 31], [39, 31.5]], { top: TM.MOSS, pa: 60, only: [TM.CLEAR, TM.MEADOW], seed: 63, amp: 0.8 });
  T.zone([[66, 58], [81, 58], [81, 62.5], [66, 62.5]], { top: TM.MOSS, pa: 90, raw: true, only: [TM.GRASS] }); // graves terrace
  T.zone([[18, 6], [33, 5], [34, 13], [26, 15.5], [19, 14]], { top: TM.MOSS, pa: 40, only: [TM.MEADOW, TM.GRASS], seed: 65 }); // around the pool
  T.zone([[18, 14], [24, 15], [21, 40], [16, 40]], { top: TM.GRASS, pb: 60, only: [TM.MEADOW], seed: 66 });
  T.zone([[44, 13], [80, 12], [80, 17], [44, 18]], { top: TM.FLOOR, pb: 140, only: [TM.MEADOW, TM.CLEAR], seed: 67, amp: 1.6 }); // litter under the north side of the crown
  // the old highway: switchback roads (trodden earth with ruts), the saddle stretch paved (石畳)
  T.road([[131, 70.6], [118, 70.9], [100, 70.7], [84, 70.5], [72.5, 71.4]], 2.6, { mat: TM.PATH, rut: 150, edge: 0.7 });
  T.road([[69.2, 66.3], [76, 64.9], [95, 64.7], [108.4, 65.1]], 2.4, { mat: TM.PATH, rut: 140, edge: 0.6 });
  T.road([[110.6, 61.9], [100, 60.3], [90, 60.2], [85, 61.1]], 2.4, { mat: TM.PATH, rut: 120, edge: 0.6 });
  T.road([[83.4, 57.4], [80.5, 54.6], [74, 49.6], [65, 45.2], [56, 42.2], [46.5, 40.8], [39, 40.6]], 2.6, { mat: TM.PAVE, moss: 120, wobble: 0.5 });
  T.road([[39, 40.6], [31, 38.6], [24.5, 36.6]], 1.8, { mat: TM.PATH, rut: 0, edge: 0.6 });
  T.road([[18.5, 33.6], [12, 31.2], [4, 31], [-9, 30.4]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.7 });
  T.road([[61.5, 37.5], [66.5, 33.5], [71.5, 30.5], [76.6, 28.9]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.6 }); // toward the NE steps
  T.road([[77.5, 23.6], [84, 19.4], [95, 17.6], [110, 17.2], [131, 16.4]], 1.6, { mat: TM.PATH, rut: 0, edge: 0.6 }); // the north loop
  T.road([[39, 38], [31, 30], [27, 20], [26.5, 14.5]], 1.2, { mat: TM.PATH, rut: 0, edge: 0.8, wobble: 1 }); // to the pool
  // stone steps: the three switchback bends, the NE climb, the west descent
  T.stairs([83.6, 61.9], [83.6, 57.5], 3.0, -1.5, 0, 8);
  T.stairs([110.2, 66.5], [110.2, 62.2], 3.0, -3, -1.5, 8);
  T.stairs([69.6, 71.2], [69.6, 66.7], 3.0, -4.5, -3, 8);
  T.stairs([77.3, 28.8], [77.3, 23.4], 2.6, 0, 3, 15);
  T.stairs([22.4, 37.6], [20.6, 33.4], 2.2, -1.5, 0, 8);
  // the camphor's surface roots: raised, bark on top, walk around them
  const [tx, tz] = HOME.trunk;
  const root = (pts, w0, w1, h0, h1) => T.root(pts.map(p => [tx + p[0], tz + p[1]]), w0, w1, h0, h1, { base: 0 });
  root([[-1.4, 1.6], [-3.5, 3.0], [-5.6, 4.6], [-7.6, 6.6], [-9.0, 8.4]], 1.6, 0.35, 1.0, 0.1);
  root([[1.6, 1.7], [3.4, 3.2], [5.8, 4.0], [7.6, 5.9]], 1.5, 0.35, 0.95, 0.1);
  root([[0.3, 2.3], [0.8, 4.0], [0.4, 5.8], [-0.6, 7.2]], 1.0, 0.3, 0.55, 0.06);
  root([[-2.4, 0.4], [-4.8, -0.2], [-7.4, 0.4], [-10.6, 0.0]], 1.4, 0.35, 0.85, 0.1);
  root([[2.4, 0.2], [5.2, -0.6], [8.8, 0.6], [12, 0.2]], 1.4, 0.35, 0.85, 0.1);
  root([[-2.2, 1.2], [-4.6, 2.2], [-6.2, 2.4]], 0.9, 0.3, 0.6, 0.1);
  root([[2.2, 1.0], [3.9, 2.0], [4.2, 3.6]], 0.8, 0.3, 0.5, 0.05);
  // water: the pool under the falls, the channel on the cliff top, the stream to the west valley
  T.stream([[25.5, -8], [25.5, -2], [25.6, 4.6]], 2.4, [8.06, 8.06, 8.06], { step: true, speed: 1.1, depth: 0.3 });
  T.pool(HOME.pool[0], HOME.pool[1], 5.2, 4.1, -0.6, 1.0, { seed: 9, amp: 0.3 });
  T.stream([[23.6, 11.4], [21.2, 15.2], [19.6, 18.4], [17.8, 22], [15.6, 27.5], [13.4, 33.6], [11.9, 38.6], [10.4, 42.2], [8.2, 48.4], [5.4, 55.2], [2.6, 61], [-1, 66], [-9, 71]], 1.9,
    [-0.68, -0.68, -1.62, -1.62, -1.62, -1.62, -1.62, -3.12, -3.12, -3.12, -3.12, -14.1, -14.1], { step: true, speed: 0.9, depth: 0.35 });
}

/** named camera framings: target = the world point at the screen centre (metres) + follow speed */
export function homeShots() {
  const S = (x, z, y = 0, speed = 3) => ({ x, z, y, speed });
  return {
    saddle: S(50, 33.2, 0), hut: S(41.5, 34.8, 0), shrine: S(57.5, 34.5, 0),
    path: S(92, 65.5, -2.6), graves: S(75, 61, -1.5), dosojin: S(110, 70, -4.5), eastRoad: S(112, 71.5, -4.5),
    lookout: S(43, 62.5, 0), tower: S(102, 16.5, 3), waterfall: S(26, 9.5, 0),
    camphorTop: S(50, 20, 18),
    camphorFull: { from: S(50, 31.5, 0), to: S(50, 21, 21), duration: 7, ease: 'inOut' },
  };
}

/* ---------------------------------------------------------------------
   createHomeMap(o) — bake the whole location.
   o.onProgress(k, label) optional; o.free (default true) drops bake buffers.
   --------------------------------------------------------------------- */
export function createHomeMap(o = {}) {
  const K = new MapKit({
    painted: { x0: -6, z0: -4, x1: 126, z1: 104 }, playable: { x0: 0, z0: 0, x1: 120, z1: 100 }, seed: 7,
    mistZ: 0, edgeFar: 0.65,
  });
  const T = K.T;
  layoutTerrain(T);
  if (o.populate) o.populate(K);
  K.spawn = { x: 52, z: 41.5, facing: 's' };
  K.shots = homeShots();
  const map = K.bake({ free: o.free !== false });
  return map;
}
