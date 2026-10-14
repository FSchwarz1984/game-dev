// TREETOP SOUTH: from the crown of the great camphor on the pass, south over the plain, dusk to
// night. The camera cranes up out of the leaves (pan); lamps come on across the plain as it gets
// dark; then the lights leave the ground and rise in streams toward the gate above the pass
// (rise); the cloud deck, lit from below, parts and the sky shore hangs there upside down (sky);
// a ring of pale distance spreads from the plain under it and comes up the mountain (wave).
//
// Layers (back to front): sky, stars, sky shore, cloud deck, ground (with the wave composite),
// lights on the ground, the wave's curtain, rising lights, canopy (back), figure callback,
// canopy (front), close leaves (only during the pan), vignette.

import { clamp, lerp, smooth, rng, hash2, makeCanvas, ctx2d, mix3, scale3, TAU, run } from './util.js';
import { todEnv, palette, skyAt } from './tod.js';
import { paintSky, makeStars, starCanvas, drawTwinklers, CloudDeck, cloudPalette } from './sky.js';
import { buildGroundGen, GROUND_MATS, G, TOWN, HEADMAN, HAMLETS, RIVER, SWITCHBACKS } from './ground.js';
import { paintBuildings, roadLanterns } from './buildings.js';
import { buildSkyShoreGen, skyShorePalette } from './skyshore.js';
import { paintCanopy, paintCanopyGen, FOLIAGE_MATS } from './foliage.js';
import { Wave } from './wave.js';
import { COL, glow, px, LightTiles, AddBuffer } from './lights.js';

const P = { far: 0.1, canopy: 1, front: 2.4 };

export function buildSouth(W, H, seed) { return run(southGen(W, H, seed)); }

export function* southGen(W, H, seed) {
  const R = rng(seed * 7 + 3);
  const TM = {}, t00 = performance.now(); let tl = t00;
  const lap = k => { const n = performance.now(); TM[k] = Math.round(n - tl); tl = n; };
  const yh = Math.round(clamp(H * 0.475, H - 165, H - 118));
  const cx = Math.round(W / 2), f = 360, S = Math.max(110, yh * 1.1);
  const CT = 66;                                 // canopy rows visible at pan 1
  // camera rise over the pan (px at parallax 1): at pan 0 the crown's top surface stands at ~36% of
  // the frame, hiding the plain; it sinks to the bottom as the camera rises over it
  const D = Math.max(40, Math.round(H - CT - H * 0.36));
  const padTop = Math.ceil(D * P.far) + 2;       // the far group is drawn up to this much higher
  const yl = yh + padTop;                        // horizon row in far-group layer coordinates
  const gh = H + padTop;
  const sun = { dir: norm([0.85, 0.27, -0.45]), slope: 0.3 };

  // ---------------- ground, buildings, lights on the ground
  const ground = yield* buildGroundGen({ w: W, h: gh, cx, yh: yl, f, S, sun, seed });
  lap('ground');
  const cam = { cx, yh: yl, f, height: ground.height };
  const lights = paintBuildings(ground.layer, ground.X, ground.Z, cam, ground.hamlets, seed);
  yield;
  lights.push(...roadLanterns(cam, ground.Z, W, gh));
  // Obon lanterns up the old road's switchbacks, from the plain to the pass
  for (let i = 0; i < SWITCHBACKS.length - 1; i++) {
    const [ax, az] = SWITCHBACKS[i], [bx, bz] = SWITCHBACKS[i + 1], len = Math.hypot(bx - ax, bz - az);
    for (let d = 0.05; d < len; d += 0.17) {
      const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
      const x = Math.round(cx + f * X / Z), y = Math.round(yl + f * (1 - ground.height(X, Z)) / Z) - 1;
      if (x < 0 || x >= W || y < 0 || y >= gh) continue;
      if (ground.Z[(y + 1) * W + x] < Z * 0.85) continue;
      lights.push({ x, y, X, Z, kind: 'lantern', path: true });
    }
  }
  // big bonfires on the river bank (送り火)
  for (const u of [3.2, 5.6, 8.4]) {
    const i = Math.floor(u), t = u - i, [ax, az] = RIVER[i], [bx, bz] = RIVER[i + 1];
    const X = lerp(ax, bx, t) + 0.16, Z = lerp(az, bz, t);
    const x = Math.round(cx + f * X / Z), y = Math.round(yl + f / Z);
    if (x > 0 && x < W && ground.Z[y * W + x] > Z * 0.9) lights.push({ x, y, X, Z, kind: 'bonfire', river: true });
  }
  // floating lanterns on the river (灯籠流し): drift downstream (toward us)
  const river = [];
  for (let k = 0; k < 26; k++) river.push({ u0: 3 + R() * 7.5, ph: R(), side: (R() - 0.5) * 0.06 });
  // stars in the paddies: points on still water
  const stars = makeStars(W, yl, seed * 3 + 1);
  const paddyStars = [];
  for (let y = yl + 2; y < gh; y++) for (let x = 0; x < W; x++) {
    const v = ground.layer.idx[y * W + x], m = v >> 8;
    if (m !== G.paddy && m !== G.pond && m !== G.river) continue;
    if (hash2(x, y, 211) < 0.05 * (1 - smooth(60, 110, y - yl))) paddyStars.push({ x, y, X: ground.X[y * W + x], Z: ground.Z[y * W + x], kind: 'star', ph: hash2(x, y, 212) * TAU });
  }
  lights.push(...paddyStars);

  // ---------------- the gate (funnel) and the sky shore
  const Hs = 9 * Math.min(1, yh / 114), Zf = 21;   // lower on short frames, so a phone sees the same stretch of it
  const tipX = cx - Math.round(W * 0.05), tipY = Math.round(yh * 0.3) + padTop;
  const Fn = { X: (tipX - cx) * Zf / f, Z: Zf, D: Hs - (yl - tipY) * Zf / f, R: 6.5 };
  const towns = [
    { X: (-0.3 * W) * 38 / f, Z: 38, r: 3.2 },
    { X: (0.28 * W) * 44 / f, Z: 44, r: 3.6 },
    { X: (0.02 * W) * 62 / f, Z: 62, r: 4.5 },
  ];
  const ringC = { X: (0.2 * W) * 31 / f, Z: 31, r: 0.95 };
  towns.push({ X: ringC.X, Z: ringC.Z, r: 2.0 });
  const hazeEdgeY = yl - Math.round(clamp(yh * 0.36, 26, 58));
  const shoreH = hazeEdgeY + 10;
  yield;
  const shore = yield* buildSkyShoreGen({ w: W, h: shoreH, cx, yh: yl, f, Hs, funnel: Fn, towns, hazeEdgeY, pagoda: { X: ringC.X + 1.15, Z: ringC.Z + 0.5 }, seed });
  lap('lights+shore');
  const T = shore.proj(Fn.X, Fn.Z); T[1] += 1;   // the mouth, where the streams go in
  const ring = [];
  for (let k = 0; k < 22; k++) ring.push(k / 22 * TAU);

  // ---------------- cloud deck between the shores
  const Hcl = 2.6;
  yield;
  const deck = new CloudDeck({ w: W, h: yl, cx, yh: yl, f, Hc: Hcl, seed: seed * 5 + 2, cover: 0.5, bottom: yl - 16 });
  const hole = { X: Fn.X * Hcl / (Hs - Fn.D), Z: Fn.Z * Hcl / (Hs - Fn.D), r: 0 }; // where the line to the mouth crosses the deck
  const deckC = makeCanvas(W, yl), deckG = ctx2d(deckC);
  lap('clouds');

  // ---------------- rising: processions
  // The lights leave the plain in processions, one per place: the headman's house, the bonfires on
  // the river bank, two stretches of paddies, the town, a hamlet at each side. Each rises one light
  // after another at a steady pace along its own gentle S-curve into a faint column of light that
  // stands over the town and goes up into the gate. The lamps of a place go out from its edge
  // inward while its procession leaves, the place itself last. Two lights go first, alone.
  const colX = T[0], colTop = T[1] + 2;
  const projG = (X, Z) => [cx + f * X / Z, yl + f * (1 - ground.height(X, Z)) / Z];
  const visible = ([x, y]) => x > 6 && x < W - 6 && y > yl + 2 && y < gh - 2 && ground.Z[Math.round(y) * W + Math.round(x)] > 0;
  const fires = lights.filter(L => L.kind === 'bonfire' && L.river).sort((a, b2) => a.x - b2.x);
  // where the stars on the water are densest, on one side of the column
  const stretch = (xa, xb) => {
    const pts = paddyStars.filter(L => L.x > xa && L.x < xb && L.y > yl + 10 && L.y < yl + 44);
    let best = null, bn = 0;
    for (const P of pts) {
      let n = 0;
      for (const Q of pts) if (Math.abs(Q.x - P.x) < 12 && Math.abs(Q.y - P.y) < 4) n++;
      if (n > bn) { bn = n; best = P; }
    }
    return best ? [best.x, best.y] : null;
  };
  const spread = W * 0.21;                       // places this far either side of the column: the lines rise steeply
  const near = p => p && Math.abs(p[0] - colX) < spread * 1.08;
  const hamletAt = (side, k) => {
    const cands = [];
    for (const h of HAMLETS) {
      if (h.Z > 30) continue;
      const p = projG(h.X, h.Z), dx = (p[0] - colX) * side;
      if (visible(p) && near(p) && dx > 20) cands.push([dx, p]);
    }
    cands.sort((u, v) => v[0] - u[0]);
    return cands[k] ? cands[k][1] : null;
  };
  const streams = [];
  const addStream = (at, r0, base, kind) => {
    if (!at || !visible(at) || !near(at)) return null;
    for (const O of streams) if (Math.abs(O.sx - at[0]) < 20 && Math.abs(O.sy - at[1]) < 14) return null;   // one place, one procession
    const S = { sx: at[0], sy: at[1] - 1, r0, r1: 0.9 + R() * 0.05, base, kind };
    streams.push(S);
    return S;
  };
  const sHead = addStream(projG(HEADMAN.X, HEADMAN.Z), 0.17, COL.window, 'window');
  const sFireA = fires[0] ? addStream([fires[0].x, fires[0].y - 1], 0.2, COL.fire, 'fire') : null;
  addStream(projG(TOWN.X, TOWN.Z + 0.4), 0.23, COL.window, 'window');
  addStream(stretch(colX - spread, colX - 28), 0.26, PADDY_LIGHT, 'paddy');
  for (const F of fires.slice(1)) addStream([F.x, F.y - 1], 0.29, COL.fire, 'fire');
  addStream(stretch(colX + 28, colX + spread), 0.32, PADDY_LIGHT, 'paddy');
  addStream(hamletAt(-1, 0), 0.36, COL.window, 'window');
  addStream(hamletAt(1, 0), 0.4, COL.window, 'window');
  addStream(hamletAt(-1, 1), 0.44, COL.window, 'window');
  addStream(hamletAt(1, 1), 0.47, COL.window, 'window');
  // each procession's path: an S from its place, leaving straight up and joining the column going
  // up. On each side the farther places join higher, so no two lines cross; the two sides join in
  // turn. Sampled into a polyline with arc lengths.
  for (const side of [-1, 1]) {
    const mine = streams.filter(S => (S.sx - colX) * side >= 0 && !(side > 0 && S.sx - colX === 0)).sort((u, v) => Math.abs(u.sx - colX) - Math.abs(v.sx - colX));
    mine.forEach((S, i) => { S.rank = i; S.side = side; });
  }
  const yJ0 = yl + 4;
  for (const S of streams) {
    const dx = S.sx - colX;
    S.jx = colX + (Math.abs(dx) > 3 ? S.side : 0);
    S.jy = Math.min(S.sy - 16, yJ0 - S.rank * 13 - (S.side > 0 ? 6 : 0));
    S.jy = Math.max(colTop + 14, Math.min(S.jy, S.sy - Math.abs(dx) * 1.1));
    const h = S.sy - S.jy;
    const bulge = (S.side || 1) * (6 + Math.abs(dx) * 0.25);   // out a little first, then in: an S
    S.path = samplePath([[S.sx, S.sy], [S.sx + bulge, S.sy - h * 0.52], [S.jx, S.jy + h * 0.5], [S.jx, S.jy]], 40);
    S.join = S.path.len;
    // then up the column to the gate
    extendPath(S.path, [[S.jx, S.jy], [colX, S.jy - 8], [colX, colTop]], 24);
    // one light every PACE seconds (at rise animated over ~30 s) between r0 and r1
    S.e = [];
    for (let r = S.r0; r <= S.r1; r += PACE / 30) S.e.push(r);
    S.el = new Float32Array(S.e.length).fill(-1);
    S.ph = R() * TAU;
  }
  // the two that go first, alone: a window of the headman's house, then a light out of a bonfire
  const firstL = lights.find(L => L.kind === 'window' && Math.abs(L.X - HEADMAN.X) < 0.3 && Math.abs(L.Z - HEADMAN.Z) < 0.3);
  const solos = [];
  if (sHead) solos.push({ S: sHead, r: 0.03, el: -1, base: COL.window, from: firstL });
  if (sFireA) solos.push({ S: sFireA, r: 0.11, el: -1, base: COL.fire });
  // every lamp belongs to the nearest place; they go out from its edge inward, the place itself last
  for (const L of lights) {
    let best = null, bd = 1e9;
    for (const S of streams) { const d = Math.hypot(L.x - S.sx, (L.y - S.sy) * 2.2); if (d < bd) { bd = d; best = S; } }
    L.st = best; L.sd = bd;
    L.on = L.kind === 'star' ? 19.4 + R() * 0.6 : L.kind === 'window' ? 18.25 + R() * 1.1 : L.kind === 'lantern' ? 18.6 + R() * 0.7 : 19.0 + R() * 0.7;
    L.ph = L.ph ?? R() * TAU;
  }
  for (const S of streams) {
    const mine = lights.filter(L => L.st === S).sort((a, b2) => b2.sd - a.sd);
    mine.forEach((L, i) => { L.r = S.r0 + 0.02 + (S.r1 - S.r0) * (i + R() * 0.7) / Math.max(1, mine.length); });
  }
  for (const L of lights) if (L.r == null) L.r = 0.9;
  if (firstL) firstL.r = 0.03;
  let colK = 0;                                  // how much light the column carries (smoothed)
  const colBase = Math.round(Math.max(yl - 4, ...streams.map(S => S.jy + 4)));

  // ---------------- the wave
  const Xc = TOWN.X + 0.2, Zc = TOWN.Z - 0.6;
  yield;
  const noFront = new Uint8Array(W * gh);
  for (let i = 0; i < noFront.length; i++) { const m = ground.layer.idx[i] >> 8; noFront[i] = m === G.roof || m === G.roofLit || m === G.thatch || m === G.wall || m === G.kura || m === G.wood ? 1 : 0; }
  const wave = new Wave({ w: W, h: gh, X: ground.X, Z: ground.Z, mask: ground.mask, Xc, Zc, R: Math.hypot(Xc, Zc) - 0.05, f, noFront });
  for (const L of lights) L.arr = wave.arrivalOf(L.X, L.Z);
  // static lights (windows, lanterns, the stars on the water in three twinkling groups) live in tiles
  const drawStatic = (tg, L, q, x, y) => {
    const a = q / 6;
    if (L.kind === 'window') { px(tg, x, y, L.far ? COL.windowDim : COL.window, a * (L.far ? 0.75 : 0.95)); if (!L.far) glow(tg, x, y, 2, scale3(COL.window, 0.35), a); }
    else if (L.kind === 'lantern') { px(tg, x, y, COL.lantern, a * (L.path ? 0.75 : 0.9)); glow(tg, x, y, 2, scale3(COL.lantern, 0.4), a * (L.path ? 0.8 : 1)); }
    else if (L.kind === 'star') px(tg, x, y, COL.star, a * 0.6);
  };
  const statics = lights.filter(L => L.kind === 'window' || L.kind === 'lantern');
  const tilesMain = new LightTiles(statics, drawStatic, { tw: 96, th: 48 });
  const tilesStars = [0, 1, 2].map(k => new LightTiles(lights.filter(L => L.kind === 'star' && (Math.floor(L.ph * 7) % 3) === k), drawStatic, { tw: 128, th: 64 }));
  lap('rise+wave');

  // ---------------- the canopy
  const CH = CT + D + 40;                     // canopy layer: CT px visible at pan 1, then the mass below
  yield;
  const back = yield* canopyBack(W, CH, CT, R);
  yield;
  const frontC = yield* canopyFront(W, CH, CT, R);
  yield;
  const nearL = yield* nearLeaves(W, H, R);
  // sprays on the crown's top edge that stir (kept away from where she sits)
  const stir = [];
  for (const fx of [0.05, 0.17, 0.3, 0.88, 0.97]) {
    const x = Math.round(W * fx);
    let top = 0; while (top < CH - 1 && !back.layer.idx[top * W + x]) top++;
    const lay = paintCanopy(26, 20, { clumps: [{ x: 13, y: 11, rx: 9 + R() * 2, ry: 6.5, z: 2, glint: false }], limbs: [], light: [0.72, -0.42, 0.45], cell: 3.4, cellSeed: 31 }, 120 + Math.round(fx * 100));
    stir.push({ layer: lay, x: x - 13, y: top - 12, ph: R() * TAU });
  }
  lap('canopy');
  const anchorsLocal = {
    branch: { x: Math.round(W * 0.62), y: back.limbTop(Math.round(W * 0.62)) },
    stand: { x: Math.round(W * 0.69), y: back.limbTop(Math.round(W * 0.69)) },
  };

  // ---------------- per-frame state
  let t = 0, endMotes = [];
  const AB = new AddBuffer(W, gh);              // lights of this shore, the wave's motes (far-group coordinates)
  const ABs = new AddBuffer(W, shoreH);         // lights of the sky shore (behind the clouds)
  const skyCache = new Map(), shoreCache = new Map();
  let curKey = null, warm = null, warmKey = null;
  const envMemo = new Map();
  const envOf = k => { let e = envMemo.get(k); if (!e) { e = todEnv(parseFloat(k)); envMemo.set(k, e); if (envMemo.size > 8) envMemo.delete(envMemo.keys().next().value); } return e; };
  const envGOf = k => { const e = envOf(k); return e._g || (e._g = { ...e, sun: e.sun.map(v => v * (1 - 0.8 * e.night)) }); };
  const groundPalOf = k => { const e = envOf(k); return e._gp || (e._gp = palette(GROUND_MATS, envGOf(k), { haze: e.mist })); };
  const foliagePalOf = k => { const e = envOf(k); return e._fp || (e._fp = palette(FOLIAGE_MATS, { ...e, sun: e.sun.map(v => v * (1 - 0.7 * e.night)) })); };
  const cloudPalOf = k => { const e = envOf(k); return e._cp || (e._cp = cloudPalette({ ...e, sun: mix3(e.sun.map(v => v * 0.9), [0.42, 0.27, 0.2], e.night) })); };
  const skyOf = k => {
    let c = skyCache.get(k);
    if (!c) { c = paintSky(W, gh, yl, S, envOf(k)); skyCache.set(k, c); if (skyCache.size > 3) skyCache.delete(skyCache.keys().next().value); }
    return c;
  };
  const shoreOf = k => {
    let sc = shoreCache.get(k);
    if (sc) return sc;
    const env = envOf(k), hazeCol = skyAt(env, 0.3, 0.5);
    // the land overhead is lit only near the horizon (by the plain's glow); far above, its underside
    // goes dark, so a tall frame does not get a ceiling of rock pressing down
    const raw = shore.layer.canvas('s' + k, skyShorePalette(mix3(hazeCol, [80, 90, 128], 0.55)));
    sc = makeCanvas(W, raw.height); const sg = ctx2d(sc);
    sg.drawImage(raw, 0, 0);
    const y1 = yl - Math.min(yh, 124) * 1.05, y0 = y1 - 46;
    if (y1 > 0) {
      const top = skyAt(env, 1, 0.5).map(v => Math.round(v * 1.25));
      sg.globalCompositeOperation = 'source-atop';
      for (let y = 0; y < Math.ceil(y1); y++) {
        const a = 1 - smooth(y0, y1, y + 0.5);
        if (a <= 0.004) continue;
        sg.fillStyle = `rgba(${top[0]},${top[1]},${top[2]},${a.toFixed(3)})`;
        sg.fillRect(0, y, W, 1);
      }
      sg.globalCompositeOperation = 'source-over';
    }
    // its town lights, pre-rendered (static), faded with the land
    for (const L of shore.lights) {
      const a = L.b * smooth(hazeEdgeY + 2, hazeEdgeY - 10, L.y) * smooth(y1 - 30, y1, L.y) * (1 - smooth(30, 75, L.Z) * 0.5);
      if (a < 0.03) continue;
      if (L.win) { px(sg, L.x, L.y, COL.warmJade, a); glow(sg, L.x, L.y, 2, scale3(COL.warmJade, 0.3), a); continue; }
      px(sg, L.x, L.y, COL.jadeCore, a);
      if (L.b > 0.8 && L.Z < 50) glow(sg, L.x, L.y, 2, scale3(COL.jade, 0.35), a);
    }
    // the far edge dissolves into the cloud sea instead of ending on a line
    sg.globalCompositeOperation = 'destination-out';
    for (let y = hazeEdgeY - 16; y < sc.height; y++) {
      const a = smooth(hazeEdgeY - 16, hazeEdgeY + 2, y);
      sg.fillStyle = `rgba(0,0,0,${a.toFixed(3)})`; sg.fillRect(0, y, W, 1);
    }
    // behind its far edge, the light between the shores: its ranges hang dark against it
    sg.globalCompositeOperation = 'destination-over';
    const gc = mix3(hazeCol, [118, 150, 164], 0.6).map(Math.round);
    for (let y = Math.max(0, hazeEdgeY - 44); y < sc.height; y++) {
      const a = smooth(hazeEdgeY - 44, hazeEdgeY - 8, y) * (1 - smooth(hazeEdgeY - 2, hazeEdgeY + 9, y)) * 0.62;
      if (a < 0.01) continue;
      sg.fillStyle = `rgba(${gc[0]},${gc[1]},${gc[2]},${a.toFixed(3)})`; sg.fillRect(0, y, W, 1);
    }
    sg.globalCompositeOperation = 'source-over';
    shoreCache.set(k, sc); if (shoreCache.size > 2) shoreCache.delete(shoreCache.keys().next().value);
    return sc;
  };
  let wavePrep = null, deckPrep = null;
  function* waveBaseGen(k) {
    const nrm = ground.layer.pixels(groundPalOf(k)); yield;
    const e = envOf(k), far = ground.layer.pixels(palette(GROUND_MATS, envGOf(k), { haze: e.mist, far: true })); yield;
    wave.base(k, nrm, far);
  }
  function* warmGen(k, withShore, withNear) {
    skyOf(k); yield;
    yield* ground.layer.canvasGen('g' + k, groundPalOf(k)); yield;
    yield* back.layer.canvasGen('f' + k, foliagePalOf(k)); yield;
    yield* frontC.layer.canvasGen('f' + k, foliagePalOf(k)); for (const sp of stir) sp.layer.canvas('f' + k, foliagePalOf(k)); yield;
    if (withNear) { yield* nearL.canvasGen('n' + k, foliagePalOf(k)); yield; }
    if (withShore) { shoreOf(k); yield; }
  }
  let vign = null, vignKey = '';
  const shot = {
    debug: { streams, solos },
    anchors: {},
    info: { yh, padTop, T, ground: ground.ms, lights: lights.length, TM, streams: streams.map(S => [S.kind, Math.round(S.sx), Math.round(S.sy), Math.round(S.jy), +S.r0.toFixed(2), S.e.length, Math.round(S.join), Math.round(S.path.len)]) },
    draw(g, dt, st) {
      t += dt;
      const tod = clamp(st.tod ?? 21, 16.5, 24);
      const want = (Math.round(tod * 20) / 20).toFixed(2);
      const pan = smooth(0, 1, clamp(st.pan ?? 1, 0, 1));
      const dy = (1 - pan) * D;
      const oFar = -Math.round(dy * P.far) - padTop;
      const rise = clamp(st.rise ?? 0, 0, 1), skyK = clamp(st.sky ?? 0, 0, 1);
      const wv = st.wave == null ? -1 : st.wave;
      const reveal = smooth(0.05, 0.75, skyK);
      // palettes change with the time of day: the layers of a new time are prepared one per frame
      // (the previous time keeps being drawn meanwhile), so a moving tod never costs a long frame
      if (curKey === null) { run(warmGen(want, reveal > 0, pan < 1)); curKey = want; }
      else if (want !== curKey) {
        if (warmKey !== want) { warm = warmGen(want, reveal > 0, pan < 1); warmKey = want; }
        if (warm.next().done) { curKey = want; warm = null; warmKey = null; }
      }
      const key = curKey, env = envOf(key);
      const night = env.night;

      // sky
      g.drawImage(skyOf(key), 0, oFar);
      // stars
      const fade = y => smooth(yl, yl - 36, y);
      if (env.stars > 0.02) {
        if (!shot.starC) shot.starC = starCanvas(W, yl, stars, fade);
        g.globalAlpha = env.stars; g.drawImage(shot.starC, 0, oFar); g.globalAlpha = 1;
        drawTwinklers(g, stars, t, env.stars, 0, oFar, fade);
      }

      // the sky shore: materialises as the clouds part
      if (reveal > 0) {
        const sc = shoreOf(key);
        g.globalAlpha = reveal; g.drawImage(sc, 0, oFar); g.globalAlpha = 1;
        drawShoreLights(ABs, shore, ring, ringC, t, reveal, T, colK);
        ABs.flush(g, 0, oFar);
      }

      // the cloud deck (its own canvas, so the light from below only lights the clouds)
      const hr = Math.round(Math.pow(skyK, 1.15) * 32) / 32;
      hole.r = hr * 9.5;
      const dlight = [0.82 - 0.7 * night, 0.58 + 0.3 * night], dwant = key + '|' + hole.r.toFixed(2);
      if (deck.key !== dwant) {
        if (deck.key == null) deck.render(hole, key, cloudPalOf(key), dlight);
        else {
          if (!deckPrep || deckPrep.want !== dwant) { deckPrep = deck.renderGen(hole, key, cloudPalOf(key), dlight); deckPrep.want = dwant; }
          if (deckPrep.next().done) deckPrep = null;
        }
      }
      const dk = deck.canvas;
      deckG.clearRect(0, 0, W, yl);
      deckG.drawImage(dk, 0, 0);
      const flux = colK;
      if (flux > 0.01 || reveal > 0) {
        deckG.globalCompositeOperation = 'source-atop';
        glow(deckG, T[0], T[1] + 30, 70, [255, 176, 120], 0.5 * flux);
        glow(deckG, T[0], T[1] + 10, 56, [170, 236, 216], 0.45 * reveal);
        deckG.globalCompositeOperation = 'source-over';
      }
      g.drawImage(deckC, 0, oFar);

      // ground (or the wave's composite of near and far)
      let gc;
      // the wave's near/far pixel sets are prepared ahead, a step per frame, once the sky is open
      if (wave.key !== key && (wv >= 0 || skyK > 0.4)) {
        if (!wavePrep || wavePrep.key !== key) { wavePrep = waveBaseGen(key); wavePrep.key = key; }
        if (wv >= 0) run(wavePrep); else wavePrep.next();
      }
      if (wv >= 0) gc = wave.update(wv);
      else gc = ground.layer.canvas('g' + key, groundPalOf(key));
      g.drawImage(gc, 0, oFar);

      // lights on the ground
      drawGroundLights(g, lights, river, ground, cam, tod, rise, wv, t, oFar, dt, W);
      // the wave's curtain of motes
      if (wv >= 0) wave.drawFront(AB, wv, t, dt, 1);
      // rising lights
      updateRise(rise, dt);
      drawRising(AB, t, dt, skyK);
      AB.flush(g, 0, oFar);

      // canopy, figure, leaves in front of her
      const oC = Math.round(H - CT - dy * P.canopy);
      const fpal = foliagePalOf(key);
      const clipDraw = (c, oy) => { const sy = Math.max(0, -oy), sh = Math.min(c.height, H - oy) - sy; if (sh > 0) g.drawImage(c, 0, sy, W, sh, 0, oy + sy, W, sh); };
      clipDraw(back.layer.canvas('f' + key, fpal), oC);
      for (const sp of stir) {                     // a few sprays on the crown's edge stir in the evening air
        const k = Math.sin(t * 0.8 + sp.ph) + 0.35 * Math.sin(t * 2.1 + sp.ph * 2);
        g.drawImage(sp.layer.canvas('f' + key, fpal), sp.x + Math.round(k * 0.8), sp.y + oC + Math.round(Math.max(0, -k) * 0.6));
      }
      const a = shot.anchors;
      a.branch = { x: anchorsLocal.branch.x, y: anchorsLocal.branch.y + oC };
      a.stand = { x: anchorsLocal.stand.x, y: anchorsLocal.stand.y + oC };
      if (st.figure) { g.save(); st.figure(g, a); g.restore(); }
      clipDraw(frontC.layer.canvas('f' + key, fpal), oC);
      // close leaves, sliding out of frame as the camera rises
      const oN = Math.round(H + 4 - dy * P.front);
      if (oN < H) clipDraw(nearL.canvas('n' + key, fpal), oN);

      // the end of the wave: the pale front comes up the trunk and over the crown, motes rushing past
      if (wv > 0.84) {
        const k = smooth(0.84, 1.0, wv);
        if (!shot.endG) {
          const c = makeCanvas(W, H), cg = ctx2d(c), gr = cg.createLinearGradient(0, H * 0.35, 0, H);
          gr.addColorStop(0, 'rgba(214,224,246,0)'); gr.addColorStop(0.6, 'rgba(214,224,246,0.45)'); gr.addColorStop(1, 'rgba(226,232,250,0.85)');
          cg.fillStyle = gr; cg.fillRect(0, 0, W, H); shot.endG = c;
        }
        g.globalAlpha = k * 0.8; g.drawImage(shot.endG, 0, Math.round((1 - k) * H * 0.55)); g.globalAlpha = 1;
        const n = Math.round(k * 14 * Math.min(1, dt * 60 + 0.01));
        for (let q = 0; q < n; q++) endMotes.push({ x: R() * W, y: H + 2 - R() * 20, vy: -(80 + 120 * R()) * (0.6 + k), vx: (R() - 0.5) * 20, life: 0.6 + R() * 0.8, age: 0, big: R() < 0.35 });
      }
      if (endMotes.length) {
        g.fillStyle = '#eef2ff';
        for (const m of endMotes) {
          m.age += dt; m.x += m.vx * dt; m.y += m.vy * dt;
          if (m.age >= m.life) continue;
          g.globalAlpha = (1 - m.age / m.life) * 0.85;
          g.fillRect(Math.round(m.x), Math.round(m.y), m.big ? 2 : 1, m.big ? 2 : 1);
        }
        g.globalAlpha = 1;
        endMotes = endMotes.filter(m => m.age < m.life && m.y > -4);
        if (wv < 0.8) endMotes.length = 0;
      }
      // vignette, and the end of the wave washing everything pale
      const vk = W + 'x' + H;
      if (vignKey !== vk) { vign = vignette(W, H); vignKey = vk; }
      g.globalAlpha = lerp(0.35, 0.6, night); g.drawImage(vign, 0, 0); g.globalAlpha = 1;
      if (wv > 0.9) { g.fillStyle = '#dfe6f6'; g.globalAlpha = smooth(0.9, 1.0, wv) * 0.55; g.fillRect(0, 0, W, H); g.globalAlpha = 1; }
    },
  };
  return shot;

  // ---------------------------------------------------------------- helpers using the closure

  function updateRise(rise, dt) {
    for (const S of streams) {
      const e = S.e, el = S.el;
      for (let k = 0; k < e.length; k++) {
        if (rise >= e[k]) el[k] = el[k] < 0 ? (rise - e[k]) * 30 : el[k] + dt;   // a jump: as if rise had run at 1/30 s
        else el[k] = -1;
      }
    }
    for (const L of solos) L.el = rise >= L.r ? (L.el < 0 ? (rise - L.r) * 30 : L.el + dt) : -1;
  }

  // light passing over the cloud deck is hidden where the deck is (until it parts)
  function cover(x, y, closed) {
    if (closed <= 0 || y >= yl - 27) return 1;
    const xi = x | 0, yi = y | 0, dv = deck.val;
    if (!dv || xi < 0 || xi >= W || yi < 0 || yi >= deck.yb) return 1;
    return 1 - closed * clamp(dv[yi * W + xi] * 3, 0, 1) * 0.94;
  }

  function drawRising(AB, t, dt, skyK) {
    const closed = 1 - smooth(0.12, 0.55, skyK);
    let feed = 0;
    for (const S of streams) {
      const P = S.path, E = S.el;
      for (let k = 0; k < E.length; k++) {
        const el = E[k];
        if (el < 0) continue;
        const d = el * SPEED, past = d - S.join;
        if (past > MERGE) continue;                               // gone into the column
        if (past > 0) feed++;
        let a = smooth(0, 1.4, el) * (past > 0 ? 1 - smooth(0, MERGE, past) : 1);
        pathAt(P, d);
        const x = PT[0] + Math.sin(el * 0.8 + k * 1.7 + S.ph) * 0.4 * (1 - smooth(-20, 0, past)), y = PT[1];
        a *= cover(x, y, closed);
        if (a > 0.02) lightAt(AB, P, d, x, y, S.base, a, k * 0.7 + S.ph, false);
      }
    }
    for (const L of solos) {
      if (L.el < 0) continue;
      const P = L.S.path, d = L.el * SPEED;
      if (d > P.len) continue;
      pathAt(P, d);
      const x = PT[0], y = PT[1];
      const a = smooth(0, 1.6, L.el) * (1 - smooth(P.len - 12, P.len, d) * 0.8) * cover(x, y, closed);
      if (a > 0.02) lightAt(AB, P, d, x, y, L.base, a, 0, true);
    }
    // the column carries what the processions bring: it brightens as they feed it, fades when they stop
    colK += (clamp(feed / 5, 0, 1) - colK) * Math.min(1, dt * 0.7);
    if (colK > 0.01) drawColumn(AB, t, closed);
  }

  // one light: a 2x2 core with a soft halo and a short trail along its path; amber near the
  // ground, pale jade as it nears the sky shore
  function lightAt(AB, P, d, x, y, base, a, ph, solo) {
    const kk = clamp((yl + 8 - y) / (yl + 8 - T[1]), 0, 1), k = kk * kk * (3 - 2 * kk) * 0.92;
    RC[0] = base[0] + (COL.jade[0] - base[0]) * k; RC[1] = base[1] + (COL.jade[1] - base[1]) * k; RC[2] = base[2] + (COL.jade[2] - base[2]) * k;
    const br = a * (0.88 + 0.12 * Math.sin(ph * 2.3 + t * 1.7));
    RC2[0] = RC[0] * 0.74; RC2[1] = RC[1] * 0.74; RC2[2] = RC[2] * 0.74;
    const xi = Math.round(x - 0.5), yi = Math.round(y - 0.5);
    RC3[0] = RC[0] * 0.3; RC3[1] = RC[1] * 0.3; RC3[2] = RC[2] * 0.3;
    AB.glow2(xi, yi, solo ? 6 : 5, RC3, br);
    for (let q = 1; q <= 2; q++) {
      pathAt(P, d - q * 2.2);
      AB.px(Math.round(PT[0] - 0.5), Math.round(PT[1] - 0.5) + 1, RC, br * (q === 1 ? 0.32 : 0.14), 2, 1);
    }
    AB.px(xi, yi, RC2, br, 2, 2);
  }

  // the column: a soft, faint haze of light standing over the town, ripples running up it
  function drawColumn(AB, t, closed) {
    const y0 = colBase, y1 = colTop;
    for (let y = y0; y >= y1; y--) {
      const u = (y0 - y) / (y0 - y1);
      const flow = 0.72 + 0.28 * Math.sin(y * 0.27 + t * 2.0);
      const a = colK * 0.085 * smooth(0, 0.18, u) * flow * cover(colX, y, closed);
      if (a < 0.003) continue;
      const kk = u * u * (3 - 2 * u);
      RC[0] = 255 + (COL.jade[0] - 255) * kk; RC[1] = 190 + (COL.jade[1] - 190) * kk; RC[2] = 134 + (COL.jade[2] - 134) * kk;
      const sg = 2.4 + u * 1.6;
      for (let dx = -8; dx <= 8; dx++) {
        const w = Math.exp(-dx * dx / (2 * sg * sg));
        if (w > 0.06) AB.px(colX + dx, y, RC, a * w);
      }
    }
  }

  function drawGroundLights(g, lights, river, ground, cam, tod, rise, wv, t, oy, dt) {
    g.globalCompositeOperation = 'source-over';
    const level = L => {
      let a = smooth(L.on, L.on + 0.25, tod) * (1 - smooth(L.r, L.r + 0.015, rise));
      if (a <= 0) return 0;
      if (wv >= 0) a *= 1 - smooth(L.arr - 0.004, L.arr + 0.012, wv);
      return Math.round(a * 6);
    };
    tilesMain.update(level); tilesMain.draw(g, 0, oy);
    for (let k = 0; k < 3; k++) {
      tilesStars[k].update(level);
      const prev = g.globalAlpha;
      g.globalAlpha = 0.55 + 0.45 * Math.sin(t * (1.1 + k * 0.37) + k * 2.1);
      tilesStars[k].draw(g, 0, oy);
      g.globalAlpha = prev;
    }
    // fires flicker: drawn every frame (few)
    for (const L of lights) {
      if (L.kind !== 'fire' && L.kind !== 'bonfire') continue;
      let a = smooth(L.on, L.on + 0.25, tod);
      if (a <= 0) continue;
      if (rise >= L.r) { AB.px(L.x, L.y, COL.ember, 0.5 * a * (1 - smooth(L.r, L.r + 0.08, rise)) * (1 - smooth(L.arr, L.arr + 0.02, wv))); continue; }
      if (wv >= 0) a *= 1 - smooth(L.arr - 0.004, L.arr + 0.012, wv);
      if (a <= 0.02) continue;
      const x = L.x, y = L.y, ph = L.ph;
      if (L.kind === 'fire') {
        const fl = 0.75 + 0.25 * Math.sin(t * 11 + ph * 9) * Math.sin(t * 7.3 + ph * 3);
        AB.px(x, y, fl > 0.85 ? COL.fireHot : COL.fire, a);
        if (fl > 0.7) AB.px(x, y - 1, COL.lantern, a * 0.6);
        AB.glow(x, y, 3, scale3(COL.lantern, 0.45 * fl), a);
      } else {
        const fl = 0.78 + 0.22 * Math.sin(t * 9 + ph * 9) * Math.sin(t * 5.1 + ph * 3);
        AB.px(x - 1, y, COL.fire, a, 2, 1);
        AB.px(x, y - 1, fl > 0.8 ? COL.fireHot : COL.fire, a);
        if (fl > 0.86) AB.px(x - 1 + (Math.sin(t * 13 + ph) > 0 ? 1 : 0), y - 2, COL.lantern, a * 0.7);
        AB.glow(x, y - 1, 6, scale3(COL.lantern, 0.5 * fl), a);
      }
    }
    // floating lanterns on the river, drifting down toward us
    const ra = smooth(19.1, 19.5, tod) * (1 - smooth(0.12, 0.6, rise));
    if (ra > 0.02) for (const fl of river) {
      const u = fl.u0 - ((t * 0.02 + fl.ph * 3) % 3);
      if (u < 0.5) continue;
      const i = Math.floor(u), k = u - i, [ax, az] = RIVER[i], [bx, bz] = RIVER[i + 1] || RIVER[i];
      const X = lerp(ax, bx, k) + fl.side, Z = lerp(az, bz, k);
      const x = Math.round(cam.cx + cam.f * X / Z), y = Math.round(cam.yh + cam.f / Z);
      if (x < 0 || x >= W || y < 0 || y >= gh || ground.Z[y * W + x] < Z * 0.9) continue;
      let a = ra;
      if (wv >= 0) a *= 1 - smooth(wave.arrivalOf(X, Z) - 0.004, wave.arrivalOf(X, Z) + 0.012, wv);
      AB.px(x, y, COL.lantern, a * 0.85);
      AB.px(x, y + 1, COL.lantern, a * 0.3); // its reflection
      AB.glow(x, y, 2, scale3(COL.lantern, 0.35), a);
    }
  }
}

// ---------------------------------------------------------------- rising

const PACE = 1.45;            // seconds between two lights of one procession (rise animated over ~30 s)
const SPEED = 6.5;            // px per second along the path: a walking pace, seen from the pass
const MERGE = 14;             // px after the join over which a light fades into the column
const PADDY_LIGHT = [255, 226, 178];
const RC = [0, 0, 0], RC2 = [0, 0, 0], RC3 = [0, 0, 0];

// a cubic Bezier sampled into a polyline with cumulative lengths (lights move at constant speed
// along it, so a procession keeps its spacing)
function samplePath(c, n) {
  const P = { xs: [], ys: [], ls: [], len: 0 };
  for (let i = 0; i <= n; i++) {
    const s = i / n, u = 1 - s, a = u * u * u, b = 3 * u * u * s, cc = 3 * u * s * s, d = s * s * s;
    pushPt(P, a * c[0][0] + b * c[1][0] + cc * c[2][0] + d * c[3][0], a * c[0][1] + b * c[1][1] + cc * c[2][1] + d * c[3][1]);
  }
  return P;
}
// continue a path along a quadratic Bezier
function extendPath(P, c, n) {
  for (let i = 1; i <= n; i++) {
    const s = i / n, u = 1 - s;
    pushPt(P, u * u * c[0][0] + 2 * u * s * c[1][0] + s * s * c[2][0], u * u * c[0][1] + 2 * u * s * c[1][1] + s * s * c[2][1]);
  }
}
function pushPt(P, x, y) {
  const n = P.xs.length;
  if (n) P.len += Math.hypot(x - P.xs[n - 1], y - P.ys[n - 1]);
  P.xs.push(x); P.ys.push(y); P.ls.push(P.len);
}
const PT = [0, 0];
function pathAt(P, d) {
  const ls = P.ls, last = ls.length - 1;
  if (d <= 0) { PT[0] = P.xs[0]; PT[1] = P.ys[0]; return PT; }
  if (d >= P.len) { PT[0] = P.xs[last]; PT[1] = P.ys[last]; return PT; }
  let lo = 0, hi = last;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (ls[m] < d) lo = m; else hi = m; }
  const k = (d - ls[lo]) / (ls[hi] - ls[lo] || 1);
  PT[0] = P.xs[lo] + (P.xs[hi] - P.xs[lo]) * k; PT[1] = P.ys[lo] + (P.ys[hi] - P.ys[lo]) * k;
  return PT;
}

// ---------------------------------------------------------------- the sky shore's lights

function drawShoreLights(AB, shore, ring, ringC, t, reveal, T, inflow) {
  // glints running up the rivers, away from the gate: their water flows the other way from ours
  for (const p of shore.flow) {
    const k = Math.sin(p.u * 0.9 - t * 1.6 + p.ri * 2.1);
    if (k < 0.82) continue;
    AB.px(p.x, p.y, COL.jadeCore, reveal * (k - 0.82) / 0.18 * (1 - smooth(30, 70, p.Z) * 0.6));
  }
  // the dance ring: lanterns round the plaza, the circle of dancers passing in front of them
  const [rx, ry] = shore.proj(ringC.X, ringC.Z);
  for (let k = 0; k < ring.length; k++) {
    const th = ring[k];
    const [x, y] = shore.proj(ringC.X + Math.cos(th) * ringC.r, ringC.Z + Math.sin(th) * ringC.r);
    const b = 0.6 + 0.4 * Math.sin(th * 2 - t * 1.3);
    AB.px(x, y, COL.jadeCore, reveal * b);
    AB.glow(x, y, 2, scale3(COL.jade, 0.45), reveal * b);
  }
  // the yagura at its centre and the strings of lanterns from it
  AB.px(rx, ry, COL.jadeCore, reveal);
  AB.glow(rx, ry, 4, scale3(COL.jade, 0.5), reveal);
  for (let k = 0; k < 8; k++) {
    const th = k / 8 * TAU + 0.2;
    for (let j = 1; j <= 3; j++) {
      const [x, y] = shore.proj(ringC.X + Math.cos(th) * ringC.r * j / 4, ringC.Z + Math.sin(th) * ringC.r * j / 4);
      AB.px(x, y, COL.jade, reveal * 0.55);
    }
  }
  // the gate's mouth: a soft glow, brighter with what goes in
  const pulse = 0.9 + 0.1 * Math.sin(t * 1.6);
  AB.glow(T[0], T[1], 8, scale3(COL.jade, 0.28), reveal * (0.45 + 0.55 * inflow) * pulse);
  AB.glow(T[0], T[1], 3, scale3(COL.jadeCore, 0.35), reveal * (0.4 + 0.6 * inflow));
}

// ---------------------------------------------------------------- canopy

function* canopyBack(W, CH, CT, R) {
  const P = (fx, y, r) => [W * fx, y, r];
  // the limb she sits on: out of the crown on the right, reaching left over the drop, tapering
  const limb = [P(1.06, CT - 12, 9), P(0.96, CT - 22, 8), P(0.86, CT - 29, 7), P(0.77, CT - 33, 6.4), P(0.69, CT - 35, 5.9),
    P(0.61, CT - 36, 5.3), P(0.54, CT - 36.5, 4.6), P(0.48, CT - 38, 3.6), P(0.44, CT - 41, 2.6), P(0.41, CT - 45, 1.6), P(0.39, CT - 49, 1)];
  const clumps = [];
  const rise = u => Math.pow(Math.abs(u - 0.48) * 2, 2.2) * 20 + (u > 0.88 ? (u - 0.88) * 140 : 0);
  // the crown's top surface behind and below the limb, three rows deep: back rows in more shade
  for (let x = -30; x < W + 40; x += 36 + R() * 14) {
    const u = x / W;
    clumps.push({ x, y: CT - 22 - rise(u) + R() * 6, rx: 30 + R() * 10, ry: 18 + R() * 5, z: 0.3 + R() * 0.1, ao: 1, glint: false });
  }
  for (let x = -14; x < W + 40; x += 34 + R() * 14) {
    const u = x / W;
    clumps.push({ x, y: CT - 4 - rise(u) * 0.6 + R() * 6, rx: 30 + R() * 10, ry: 19 + R() * 5, z: 0.7 + R() * 0.1, glint: false });
  }
  for (let x = -24; x < W + 40; x += 38 + R() * 12) clumps.push({ x, y: CT + 14 + R() * 6, rx: 34 + R() * 8, ry: 22 + R() * 4, z: 1.0 + R() * 0.1, glint: false });
  // the mass below the top (seen while the camera rises past it)
  for (let y = CT + 46, row = 0; y < CH + 24; y += 26, row++) for (let x = -20 + (row % 2) * 20; x < W + 30; x += 40 + R() * 12) {
    clumps.push({ x, y: y + R() * 8, rx: 30 + R() * 10, ry: 20 + R() * 5, z: 1.1 + row * 0.2 + R() * 0.1, ao: row % 3 === 0 ? 1 : 0, glint: false });
  }
  // the crown around the limb's root (in front of it)
  for (let k = 0; k < 4; k++) clumps.push({ x: W * (0.95 + R() * 0.1), y: CT - 40 + k * 12 + R() * 6, rx: 16 + R() * 8, ry: 12 + R() * 4, z: 1.7 + R() * 0.2, glint: false });
  // a spray at the limb's tip, and sprigs along it
  clumps.push({ x: W * 0.39, y: CT - 56, rx: 11, ry: 8, z: 1.8, glint: false }, { x: W * 0.36, y: CT - 51, rx: 9, ry: 6, z: 1.75, glint: false }, { x: W * 0.415, y: CT - 62, rx: 7, ry: 5, z: 1.8, young: 0.5, glint: false });
  clumps.push({ x: W * 0.5, y: CT - 45, rx: 6, ry: 4, z: 1.6, glint: false }, { x: W * 0.8, y: CT - 41, rx: 7, ry: 5, z: 1.6, young: 0.4, glint: false });
  // sprays rising at the far left
  for (let k = 0; k < 3; k++) clumps.push({ x: W * (0.01 + R() * 0.08), y: CT - 56 + R() * 18, rx: 14 + R() * 6, ry: 10 + R() * 4, z: 1.2 + R() * 0.3, glint: false });
  const layer = yield* paintCanopyGen(W, CH, { clumps, limbs: [{ pts: limb, z: 1.5 }], light: [0.72, -0.42, 0.45] }, 41);
  const limbTop = x => {
    for (let y = 0; y < CH; y++) { const v = layer.idx[y * W + x]; if (v && ((v >> 8) === 6 || (v >> 8) === 7)) return y; }
    return CT - 40;
  };
  return { layer, limbTop };
}

function* canopyFront(W, CH, CT, R) {
  // clumps in front of the limb, around her: they overlap the limb's underside and her lap
  const P = (fx, y, rx, ry, z) => ({ x: W * fx, y, rx, ry, z });
  const clumps = [
    P(0.61, CT - 21, 13, 9, 3.2), P(0.71, CT - 17, 17, 11, 3.1), P(0.52, CT - 14, 15, 10, 3.15),
    P(0.84, CT - 12, 22, 14, 3.1), P(0.98, CT - 20, 20, 14, 3), P(0.4, CT - 4, 22, 13, 3),
    P(0.22, CT - 2, 24, 14, 3), P(0.05, CT - 8, 24, 15, 3),
  ].map(c => ({ ...c, glint: false }));
  return { layer: yield* paintCanopyGen(W, CH, { clumps, limbs: [], light: [0.72, -0.42, 0.45] }, 43) };
}

function* nearLeaves(W, H, R) {
  // sprays right in front of the lens, in shade: only seen while the camera rises past them
  const h = H + 40, clumps = [], limbs = [];
  const sprays = [[0.08, 0.35], [0.3, 0.75], [0.55, 0.3], [0.8, 0.62], [0.97, 0.2], [0.42, 1.0], [0.7, 0.98]];
  for (const [fx, fy] of sprays) {
    const x0 = W * fx, y0 = h * fy, dir = R() < 0.5 ? -1 : 1, len = 40 + R() * 40;
    const pts = [];
    for (let k = 0; k <= 4; k++) pts.push([x0 + dir * len * k / 4, y0 + h * 0.12 - k * 9 - Math.sin(k) * 4, lerp(3, 1, k / 4)]);
    limbs.push({ pts, z: 0.2, dark: 1 });
    for (let k = 1; k <= 4; k++) clumps.push({ x: pts[k][0] + (R() - 0.5) * 10, y: pts[k][1] - 4 + (R() - 0.5) * 8, rx: 16 + R() * 10, ry: 11 + R() * 6, z: 0.5 + R() * 0.4, ao: 1, glint: false, dark: true });
  }
  return yield* paintCanopyGen(W, h, { clumps, limbs, light: [0.72, -0.42, 0.45], cell: 4.6, cellSeed: 5 }, 47);
}


function vignette(W, H) {
  const c = makeCanvas(W, H), g = ctx2d(c);
  const gr = g.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.35, W / 2, H * 0.45, Math.hypot(W, H) * 0.62);
  gr.addColorStop(0, 'rgba(4,5,12,0)'); gr.addColorStop(1, 'rgba(4,5,12,1)');
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
  return c;
}

function norm(v) { const l = Math.hypot(...v); return v.map(q => q / l); }
