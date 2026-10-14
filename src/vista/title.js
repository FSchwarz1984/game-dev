// TITLE: night under the great camphor. Its canopy hangs over the top of the frame, rimmed by a
// moon half hidden in the leaves; below, the plain: hamlets and their lamps, lantern lines along
// the roads, Obon fires, flooded paddies holding the stars. Calm space centre-left for the title.
// One small wrongness for those who look: in a paddy near the middle, a few pale jade lights are
// reflected whose source is nowhere in the sky (the sky shore is not shown yet).
// Gentle life: stars, a few hanging sprays of leaves stirring, two fireflies, flickering fires.

import { clamp, lerp, smooth, rng, hash2, vnoise, makeCanvas, ctx2d, scale3, TAU, pack, run } from './util.js';
import { todEnv, palette } from './tod.js';
import { paintSky, makeStars, starCanvas, drawTwinklers } from './sky.js';
import { buildGroundGen, GROUND_MATS, G } from './ground.js';
import { paintBuildings, roadLanterns } from './buildings.js';
import { paintCanopy, paintGrass, FOLIAGE_MATS } from './foliage.js';
import { COL, glow, px, LightTiles, AddBuffer } from './lights.js';

export function buildTitle(W, H, seed) { return run(titleGen(W, H, seed)); }

export function* titleGen(W, H, seed) {
  const R = rng(seed * 11 + 5);
  const yh = Math.round(clamp(H * 0.6, H - 118, H - 80));
  const cx = Math.round(W / 2), f = 360, S = Math.max(110, yh * 0.95);
  const env = todEnv(21);
  const envG = { ...env, sun: env.sun.map(v => v * 0.35) };   // moonlight, weak, from the upper right
  const sun = { dir: norm([0.6, 0.45, -0.35]), slope: 0.45 };
  const ground = yield* buildGroundGen({ w: W, h: H, cx, yh, f, S, sun, seed });
  yield;
  const cam = { cx, yh, f, height: ground.height };
  const lights = paintBuildings(ground.layer, ground.X, ground.Z, cam, ground.hamlets, seed);
  lights.push(...roadLanterns(cam, ground.Z, W, H));
  // the moon (veiled by leaves) and its path on the water
  const moonR = Math.max(8, Math.round(H * 0.044));
  const moon = { x: Math.round(W * 0.7), y: 0, r: moonR };
  moon.y = Math.round(canopyEdge(W, H, moon.x) + moonR * 2.0);
  // stars on still water: mirrors of the sky's, where there is water
  const stars = makeStars(W, yh, seed * 3 + 2, { density: 1.1 });
  const water = [];
  for (let y = yh + 2; y < H; y++) for (let x = 0; x < W; x++) {
    const m = ground.layer.idx[y * W + x] >> 8;
    if ((m === G.paddy || m === G.pond || m === G.river) && hash2(x, y, 41) < 0.11 * (1 - smooth(50, 100, y - yh))) water.push({ x, y, ph: hash2(x, y, 42) * TAU, b: 0.45 + hash2(x, y, 43) * 0.55 });
  }
  // the hook: jade reflections of a ring that is not in the sky
  const hook = [];
  {
    // find a stretch of water a little right of centre, 14-26 rows under the horizon
    let best = null;
    for (let y = yh + 14; y < yh + 30 && !best; y++) for (let x = Math.round(W * 0.52); x < W * 0.68; x++) {
      let ok = 0; for (let k = -5; k <= 5; k++) { const m = ground.layer.idx[y * W + x + k] >> 8; if (m === G.paddy || m === G.pond) ok++; }
      if (ok >= 9) { best = [x, y]; break; }
    }
    if (best) for (let k = 0; k < 7; k++) {
      const a = (k / 7) * Math.PI;     // a half ring, seen mirrored
      const x = Math.round(best[0] + Math.cos(a) * 5), y = Math.round(best[1] + Math.sin(a) * 1.4);
      const m = ground.layer.idx[y * W + x] >> 8;
      if (m === G.paddy || m === G.pond) hook.push({ x, y, ph: k * 0.9 });
    }
  }
  // the canopy overhead, seen from below: dark undersides, rims toward the moon and the open sky
  yield;
  const canopy = titleCanopy(W, H, yh, moon, R);
  yield;
  const sprays = canopy.sprays;
  // grass along the bottom edge, in three bands that stir with their own phase
  const gh = Math.round(clamp(H * 0.3, 50, 110));
  const grass = [0, 1, 2].map(k => ({ layer: paintGrass(W + 4, gh, seed * 17 + k, { n: Math.round(W * (1.1 - k * 0.3)), rimSide: 1, hMin: 0.1 + k * 0.08, hMax: 0.36 + k * 0.2, plumes: 0.05 + k * 0.04 }), ph: k * 2.1 }));
  // fireflies over the slope at the bottom
  const flies = [{ x: W * 0.2, y: H * 0.84, ph: 0.3 }, { x: W * 0.84, y: H * 0.8, ph: 2.1 }, { x: W * 0.58, y: H * 0.88, ph: 4.0 }];
  for (const L of lights) { L.ph = R() * TAU; }
  // static lights in tiles; stars on the water in three groups that twinkle out of step
  const drawStatic = (tg, L, q, x, y) => {
    const a = q / 6;
    if (L.kind === 'window') { px(tg, x, y, L.far ? COL.windowDim : COL.window, L.far ? 0.7 : 0.92); if (!L.far) glow(tg, x, y, 2, scale3(COL.window, 0.35), 1); }
    else if (L.kind === 'lantern') { px(tg, x, y, COL.lantern, 0.88); glow(tg, x, y, 2, scale3(COL.lantern, 0.4), 1); }
    else if (L.kind === 'wstar') px(tg, x, y, COL.star, L.b * a);
  };
  const tiles = new LightTiles(lights.filter(L => L.kind === 'window' || L.kind === 'lantern'), drawStatic, { tw: 160, th: 64 });
  for (const s_ of water) s_.kind = 'wstar';
  const wtiles = [0, 1, 2].map(k => new LightTiles(water.filter(s_ => Math.floor(s_.ph * 5) % 3 === k), drawStatic, { tw: 1024, th: 1024, margin: 0 }));
  const AB = new AddBuffer(W, H);

  let t = 0, cache = null;
  const shot = {
    anchors: { moon: { x: moon.x, y: moon.y }, text: { x: Math.round(W * 0.34), y: Math.round(H * 0.45) } },
    info: { yh, ground: ground.ms, lights: lights.length, hook: hook.length },
    draw(g, dt, st) {
      t += dt;
      if (!cache) cache = staticLayers();
      g.drawImage(cache.back, 0, 0);                 // sky, stars, the moon, the ground: all static
      drawTwinklers(g, stars, t, 1, 0, 0, y => smooth(yh, yh - 30, y));
      // water: stars (three groups twinkling out of step) and the moon's glitter
      for (let k = 0; k < 3; k++) {
        wtiles[k].update(() => 6);
        g.globalAlpha = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(t * (0.9 + k * 0.31) + k * 2.2));
        wtiles[k].draw(g, 0, 0);
      }
      g.globalAlpha = 1;
      for (const gl of cache.glitter) {
        const tw = Math.sin(t * 2.1 + gl.ph) * Math.sin(t * 0.9 + gl.ph * 3);
        if (tw > 0.2) AB.px(gl.x, gl.y, [214, 220, 240], (tw - 0.2) * 1.1 * gl.b);
      }
      for (const h of hook) {
        const tw = 0.7 + 0.3 * Math.sin(t * 0.8 + h.ph);
        AB.px(h.x, h.y, COL.jade, 0.4 * tw);
      }
      tiles.update(() => 6);
      tiles.draw(g, 0, 0);
      drawFires(AB, lights, t);
      AB.flush(g, 0, 0);
      // canopy, its stirring sprays, fireflies
      g.drawImage(cache.canopy, 0, 0);
      for (const sp of sprays) {
        const k = Math.sin(t * 0.7 + sp.ph) + 0.35 * Math.sin(t * 1.9 + sp.ph * 2);
        const ox = Math.round(k * 0.8), oy = Math.round(Math.max(0, k) * 0.6);
        g.drawImage(sp.c, sp.x + ox, sp.y + oy);
      }
      for (const fl of flies) {
        const u = t * 0.18 + fl.ph;
        const x = fl.x + Math.sin(u * 1.3) * 14 + Math.sin(u * 3.1) * 3, y = fl.y + Math.sin(u * 0.9) * 6;
        const on = Math.max(0, Math.sin(t * 1.4 + fl.ph * 3)), a = Math.pow(on, 3);
        if (a > 0.05) { AB.px(x, y, COL.firefly, a); AB.glow(x, y, 3, scale3(COL.firefly, 0.6), a * 0.7); }
      }
      AB.flush(g, 0, 0);
      for (const gr of cache.grass) {
        const k = Math.sin(t * 0.55 + gr.ph) + 0.3 * Math.sin(t * 1.7 + gr.ph * 3);
        g.drawImage(gr.c, -2 + Math.round(k * 0.9), H - gr.c.height);
      }
      g.globalAlpha = 0.42; g.drawImage(cache.vign, 0, 0); g.globalAlpha = 1;
    },
  };
  return shot;

  function staticLayers() {
    const sky = paintSky(W, H, yh, S, env);
    const starC = starCanvas(W, H, stars, y => smooth(yh, yh - 30, y));
    const ground_ = ground.layer.canvas('t', palette(GROUND_MATS, envG, { haze: env.mist }));
    const fpal = palette(FOLIAGE_MATS, { ...env, sun: [0.42, 0.48, 0.66] });
    const canopyC = canopy.layer.canvas('t', fpal);
    for (const sp of sprays) sp.c = sp.layer.canvas('t', fpal);
    // the moon: a disc with maria, a stepped halo
    const mr = moon.r, hr = mr * 5;
    const mc = makeCanvas(hr * 2 + 1, hr * 2 + 1), mg = ctx2d(mc), id = mg.createImageData(mc.width, mc.height), U = new Uint32Array(id.data.buffer);
    for (let y = -hr; y <= hr; y++) for (let x = -hr; x <= hr; x++) {
      const d = Math.hypot(x, y), i = (y + hr) * mc.width + (x + hr);
      if (d <= mr) {
        // maria where the real ones are (upper left and middle, a long one lower left): no accidental face
        const u = x / mr, v = y / mr;
        const blob = (cx_, cy_, r_) => Math.hypot(u - cx_, (v - cy_) * 1.1) < r_ + (vnoise(x * 0.5, y * 0.5, 79) - 0.5) * 0.18;
        const mare = blob(-0.28, -0.32, 0.3) || blob(0.12, -0.28, 0.24) || blob(0.3, 0.05, 0.22) || blob(-0.5, 0.18, 0.26) || blob(-0.25, 0.45, 0.16);
        const edge = d > mr - 1.2;
        U[i] = pack(edge ? [226, 226, 214] : mare ? [210, 212, 214] : [244, 240, 226]);
      } else {
        const k = Math.pow(1 - (d - mr) / (hr - mr), 2.4);
        const a = Math.round(k * 24) / 24 * 0.5;
        if (a > 0) U[i] = pack([196, 206, 240], Math.round(a * 255));
      }
    }
    mg.putImageData(id, 0, 0);
    // glitter: the moon's path on water straight below it
    const glitter = [];
    for (let y = yh + 1; y < H; y++) {
      const half = 2 + (y - yh) * 0.12;
      for (let x = Math.round(moon.x - half); x <= moon.x + half; x++) {
        if (x < 0 || x >= W) continue;
        const m = ground.layer.idx[y * W + x] >> 8;
        if ((m === G.paddy || m === G.pond || m === G.river) && hash2(x, y, 51) < 0.5) glitter.push({ x, y, ph: hash2(x, y, 52) * TAU, b: 1 - Math.abs(x - moon.x) / (half + 1) });
      }
    }
    const vign = makeCanvas(W, H), vg = ctx2d(vign);
    const gr = vg.createRadialGradient(W * 0.45, H * 0.5, Math.min(W, H) * 0.3, W * 0.45, H * 0.5, Math.hypot(W, H) * 0.62);
    gr.addColorStop(0, 'rgba(4,5,12,0)'); gr.addColorStop(1, 'rgba(4,5,12,1)');
    vg.fillStyle = gr; vg.fillRect(0, 0, W, H);
    const grassC = grass.map(gr => ({ c: gr.layer.canvas('t', fpal), ph: gr.ph }));
    const back = makeCanvas(W, H), bg = ctx2d(back);
    bg.drawImage(sky, 0, 0); bg.drawImage(starC, 0, 0);
    bg.drawImage(mc, moon.x - mc.width / 2, moon.y - mc.height / 2);
    bg.drawImage(ground_, 0, 0);
    return { back, canopy: canopyC, glitter, vign, grass: grassC };
  }
}

function drawFires(AB, lights, t) {
  for (const L of lights) {
    const x = L.x, y = L.y, ph = L.ph;
    if (L.kind === 'fire') {
      const fl = 0.75 + 0.25 * Math.sin(t * 11 + ph * 9) * Math.sin(t * 7.3 + ph * 3);
      AB.px(x, y, fl > 0.85 ? COL.fireHot : COL.fire, 1);
      if (fl > 0.7) AB.px(x, y - 1, COL.lantern, 0.6);
      AB.glow(x, y, 3, scale3(COL.lantern, 0.45 * fl), 1);
    } else if (L.kind === 'bonfire') {
      const fl = 0.78 + 0.22 * Math.sin(t * 9 + ph * 9) * Math.sin(t * 5.1 + ph * 3);
      AB.px(x - 1, y, COL.fire, 1, 2, 1); AB.px(x, y - 1, fl > 0.8 ? COL.fireHot : COL.fire, 1);
      AB.glow(x, y - 1, 6, scale3(COL.lantern, 0.5 * fl), 1);
    }
  }
}

function canopyEdge(W, H, x) { // lower edge of the canopy (px): low at both sides, high over the centre-left
  const u = x / W;
  return H * (0.15 + 0.2 * Math.pow(Math.abs(u - 0.38) / 0.62, 1.6)) + (u > 0.6 ? (u - 0.6) * H * 0.22 : 0);
}

function titleCanopy(W, H, yh, moon, R) {
  const light = [0.55, -0.55, -0.6]; // the moon is up and behind the leaves: we see their shaded side
  const clumps = [];
  const edge = x => canopyEdge(W, H, x);
  for (let x = -20; x < W + 30; x += 22 + R() * 12) {
    const e = edge(x);
    clumps.push({ x, y: e - 6 + R() * 6, rx: 20 + R() * 10, ry: 13 + R() * 5, z: 1 + R() * 0.4 });
    for (let y = e - 26; y > -30; y -= 22 + R() * 6) clumps.push({ x: x + (R() - 0.5) * 16, y, rx: 22 + R() * 10, ry: 15 + R() * 5, z: 0.4 + R() * 0.5, ao: 1 });
  }
  // the bough and its branches (dark against the gaps)
  const curve = (a, b, bend, n, r0, r1) => { // a bough: quadratic curve from a to b, bent sideways
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, mx = (a[0] + b[0]) / 2 - (b[1] - a[1]) * bend, my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * bend;
      const x = (1 - t) * (1 - t) * a[0] + 2 * (1 - t) * t * mx + t * t * b[0], y = (1 - t) * (1 - t) * a[1] + 2 * (1 - t) * t * my + t * t * b[1];
      pts.push([x + Math.sin(t * 9 + a[0]) * 1.2, y + Math.cos(t * 7) * 1.2, lerp(r0, r1, Math.pow(t, 0.8))]);
    }
    return pts;
  };
  const limbs = [
    { pts: curve([-12, H * 0.36], [W * 0.6, H * 0.0], 0.16, 16, 8, 2.2), z: 0.9, dark: 1 },
    { pts: curve([W * 0.26, H * 0.16], [W * 0.38, H * 0.28], -0.25, 7, 2.8, 0.9), z: 0.95, dark: 1 },
    { pts: curve([W * 0.12, H * 0.26], [W * 0.17, H * 0.36], 0.3, 5, 2.2, 0.8), z: 0.95, dark: 1 },
    { pts: curve([W + 12, H * 0.48], [W * 0.8, H * 0.02], -0.14, 14, 7.5, 2), z: 0.9, dark: 1 },
    { pts: curve([W * 0.88, H * 0.27], [W * 0.97, H * 0.38], 0.2, 6, 2.6, 0.9), z: 0.95, dark: 1 },
  ];
  const layer = paintCanopy(W, H, { clumps, limbs, light, cell: 3.4, cellSeed: 9, rimBelow: { x: moon.x, y: moon.y, r: moon.r * 9 } }, 61);
  // hanging sprays, painted separately so they can stir
  const sprays = [];
  for (let k = 0; k < 7; k++) {
    const x = Math.round(W * (0.06 + k * 0.14 + (R() - 0.5) * 0.05)), e = Math.round(edge(x));
    const w = 30, h = 22, L = paintCanopy(w, h, { clumps: [{ x: 15, y: 9, rx: 9 + R() * 3, ry: 6 + R() * 2, z: 2 }], limbs: [], light, cell: 3.0, cellSeed: 11 + k, rimBelow: { x: moon.x - (x - 15), y: moon.y - (e - 2), r: moon.r * 9 } }, 70 + k);
    sprays.push({ layer: L, x: x - 15, y: e - 2, ph: R() * TAU });
  }
  return { layer, sprays };
}

function norm(v) { const l = Math.hypot(...v); return v.map(q => q / l); }
