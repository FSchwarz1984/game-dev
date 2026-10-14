// Bake of the title backdrop (src/vista/title.js, HEAD) for Godot: night under the great camphor, the
// moon half hidden in its leaves, the plain below with its lamps, fires and flooded paddies holding
// the stars, a few pale jade reflections whose source is nowhere in the sky. Visual only: the title
// menu belongs to the core. A fixed hour, so the layers are finished RGBA images.
//
// Layout: the JS 480x270 frame on a larger canvas (any logical view up to 1024 x 560):
//   back group (sky + still stars, the plain, its still lamps and the pool of moonlight): stands on
//     the view's bottom (the JS kept the plain under the horizon at a fixed height for tall frames)
//   top group (the canopy overhead, its hanging sprays, the moon in the leaves): hangs from the top
//   grass (three bands that stir): along the bottom
// Live in Godot: twinkling stars, stars on the water (three groups), the moon's glitter on the water,
// the jade reflections, fires, fireflies, the stirring.

import { clamp, lerp, smooth, rng, hash2, vnoise, makeCanvas, ctx2d, scale3, TAU, pack, run } from '../../../src/vista/util.js';
import { todEnv, palette } from '../../../src/vista/tod.js';
import { makeStars } from '../../../src/vista/sky.js';
import { buildGroundGen, GROUND_MATS, G } from '../../../src/vista/ground.js';
import { paintBuildings, roadLanterns } from '../../../src/vista/buildings.js';
import { paintCanopy, paintCanopyGen, paintGrass, FOLIAGE_MATS } from '../../../src/vista/foliage.js';
import { COL, glow, px } from '../../../src/vista/lights.js';

const REF_W = 480, REF_H = 270;
const STAR_A = [0.32, 0.55, 0.8, 1];

export function bakeTitle(o = {}) {
  const seed = o.seed ?? 7;
  const W = REF_W, H = REF_H;
  const Wc = o.Wc ?? W, Hc = o.Hc ?? H;
  const ox = Math.round((Wc - W) / 2), oy = Hc - H;           // back group: the frame at the canvas bottom
  const R = rng(seed * 11 + 5);
  const yh = Math.round(clamp(H * 0.6, H - 118, H - 80));
  const cx = ox + Math.round(W / 2), f = 360, S = Math.max(110, yh * 0.95);
  const env = todEnv(21);
  const lift = { lift: env.lift.map((v, i) => v + [0.014, 0.018, 0.028][i]) };
  const envG = { ...env, ...lift, sun: env.sun.map(v => v * 0.62), amb: env.amb.map(v => v * 1.08) };
  const sun = { dir: norm([0.6, 0.45, -0.35]), slope: 0.45 };
  const YH = yh + oy;                                           // horizon row in the back canvas
  const ground = run(buildGroundGen({ w: Wc, h: Hc, cx, yh: YH, f, S, sun, seed }));
  const cam = { cx, yh: YH, f, height: ground.height };
  const lights = paintBuildings(ground.layer, ground.X, ground.Z, cam, ground.hamlets, seed);
  lights.push(...roadLanterns(cam, ground.Z, Wc, Hc));
  const moonR = Math.max(8, Math.round(H * 0.044));
  const moon = { x: Math.round(W * 0.7), y: 0, r: moonR };          // reference coords (top group)
  moon.y = Math.round(canopyEdge(W, H, moon.x) + moonR * 2.0);
  const stars = makeStars(Wc, YH, seed * 3 + 2, { density: 1.1 });
  const water = [];
  for (let y = YH + 2; y < Hc; y++) for (let x = 0; x < Wc; x++) {
    const m = ground.layer.idx[y * Wc + x] >> 8;
    if ((m === G.paddy || m === G.pond || m === G.river) && hash2(x, y, 41) < 0.11 * (1 - smooth(50, 100, y - YH))) water.push({ x, y, ph: hash2(x, y, 42) * TAU, b: 0.45 + hash2(x, y, 43) * 0.55 });
  }
  // the hook: jade reflections of a ring that is not in the sky
  const hook = [];
  {
    let best = null;
    for (let y = YH + 14; y < YH + 30 && !best; y++) for (let x = Math.round(ox + W * 0.52); x < ox + W * 0.68; x++) {
      let ok = 0; for (let k = -5; k <= 5; k++) { const m = ground.layer.idx[y * Wc + x + k] >> 8; if (m === G.paddy || m === G.pond) ok++; }
      if (ok >= 9) { best = [x, y]; break; }
    }
    if (best) for (let k = 0; k < 7; k++) {
      const a = (k / 7) * Math.PI;
      const x = Math.round(best[0] + Math.cos(a) * 5), y = Math.round(best[1] + Math.sin(a) * 1.4);
      const m = ground.layer.idx[y * Wc + x] >> 8;
      if (m === G.paddy || m === G.pond) hook.push({ x, y, ph: k * 0.9 });
    }
  }
  // the canopy overhead (top group: reference coords, a margin at the sides and above)
  const mX = ox, mT = 40;
  const canopy = run(titleCanopy(W, H, moon, R, Wc, mX, mT));
  const gh = Math.round(clamp(H * 0.3, 50, 110));
  const grass = [0, 1, 2].map(k => ({ layer: paintGrass(Wc + 4, gh, seed * 17 + k, { n: Math.round(Wc * (1.1 - k * 0.3)), rimSide: 1, hMin: 0.1 + k * 0.08, hMax: 0.36 + k * 0.2, plumes: 0.05 + k * 0.04 }), ph: k * 2.1 }));
  const flies = [{ x: W * 0.2, y: H * 0.84, ph: 0.3 }, { x: W * 0.84, y: H * 0.8, ph: 2.1 }, { x: W * 0.58, y: H * 0.88, ph: 4.0 }];
  for (const L of lights) L.ph = R() * TAU;

  // ---- the back: sky and still stars; the plain with its still lamps and the moon's pool
  const skyC = paintSkyC(Wc, Hc, YH, S, env, ox, W);
  const sg = ctx2d(skyC);
  for (const s of stars) {
    if (s.tw) continue;
    const a = STAR_A[s.mag] * smooth(YH, YH - 30, s.y);
    if (a <= 0.02) continue;
    sg.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${a.toFixed(3)})`;
    sg.fillRect(s.x, s.y, 1, 1);
  }
  const groundC = ground.layer.canvas('t', palette(GROUND_MATS, envG, { haze: env.mist }));
  const back = makeCanvas(Wc, Hc), bg = ctx2d(back);
  bg.drawImage(groundC, 0, 0);
  // the still lamps of the plain (title.js tiles: windows and lanterns), added like the JS did
  bg.globalCompositeOperation = 'lighter';
  for (const L of lights) {
    if (L.kind === 'window') { px(bg, L.x, L.y, L.far ? COL.windowDim : COL.window, L.far ? 0.7 : 0.92); if (!L.far) glow(bg, L.x, L.y, 2, scale3(COL.window, 0.35), 1); }
    else if (L.kind === 'lantern') { px(bg, L.x, L.y, COL.lantern, 0.88); glow(bg, L.x, L.y, 2, scale3(COL.lantern, 0.4), 1); }
  }
  bg.globalCompositeOperation = 'source-over';
  // a pool of moonlight on the plain under the moon, and the mist over it catching the light
  const pool = makeCanvas(Wc, Hc), pg = ctx2d(pool);
  pg.globalCompositeOperation = 'lighter';
  const moonX = ox + moon.x;
  for (let k = 0; k < 6; k++) {
    const r = W * (0.5 - k * 0.07), cy = YH + (Hc - YH) * 0.3;
    const gr2 = pg.createRadialGradient(moonX - W * 0.04, cy, 0, moonX - W * 0.04, cy, r);
    gr2.addColorStop(0, 'rgba(120,138,190,0.035)'); gr2.addColorStop(1, 'rgba(120,138,190,0)');
    pg.fillStyle = gr2; pg.fillRect(0, YH - 6, Wc, Hc - YH + 6);
  }
  // pool into both: the sky rows just over the horizon and the ground
  for (const c of [skyC, back]) { const g2 = ctx2d(c); g2.globalCompositeOperation = c === back ? 'source-atop' : 'lighter'; g2.drawImage(pool, 0, 0); g2.globalCompositeOperation = 'source-over'; }
  // the moon: a disc with maria, a stepped halo (top group)
  const mr = moon.r, hr = mr * 5;
  const moonImg = new Uint8Array((hr * 2 + 1) * (hr * 2 + 1) * 4), mw = hr * 2 + 1;
  for (let y = -hr; y <= hr; y++) for (let x = -hr; x <= hr; x++) {
    const d = Math.hypot(x, y), i = ((y + hr) * mw + (x + hr)) * 4;
    let c = null, a = 255;
    if (d <= mr) {
      const u = x / mr, v = y / mr;
      const blob = (cx_, cy_, r_) => Math.hypot(u - cx_, (v - cy_) * 1.1) < r_ + (vnoise(x * 0.5, y * 0.5, 79) - 0.5) * 0.18;
      const mare = blob(-0.28, -0.32, 0.3) || blob(0.12, -0.28, 0.24) || blob(0.3, 0.05, 0.22) || blob(-0.5, 0.18, 0.26) || blob(-0.25, 0.45, 0.16);
      const edge = d > mr - 1.2;
      c = edge ? [226, 226, 214] : mare ? [210, 212, 214] : [244, 240, 226];
    } else {
      const k = Math.pow(1 - (d - mr) / (hr - mr), 2.4);
      a = Math.round(Math.round(k * 24) / 24 * 0.5 * 255);
      if (a > 0) c = [196, 206, 240];
    }
    if (c) { moonImg[i] = c[0]; moonImg[i + 1] = c[1]; moonImg[i + 2] = c[2]; moonImg[i + 3] = a; }
  }
  // glitter: the moon's path on the water straight below it
  const glitter = [];
  for (let y = YH + 1; y < Hc; y++) {
    const half = 2 + (y - YH) * 0.12;
    for (let x = Math.round(moonX - half); x <= moonX + half; x++) {
      if (x < 0 || x >= Wc) continue;
      const m = ground.layer.idx[y * Wc + x] >> 8;
      if ((m === G.paddy || m === G.pond || m === G.river) && hash2(x, y, 51) < 0.5) glitter.push([x, y, +(hash2(x, y, 52) * TAU).toFixed(3), +(1 - Math.abs(x - moonX) / (half + 1)).toFixed(3)]);
    }
  }
  const fpal = palette(FOLIAGE_MATS, { ...env, ...lift, sun: [0.46, 0.53, 0.72] });

  return {
    meta: { shot: 'title', seed, refW: W, refH: H, Wc, Hc, ox, oy, yh, YH, moon, mX, mT, gh,
      canopy: { w: canopy.layer.w, h: canopy.layer.h }, text: { x: Math.round(W * 0.34), y: Math.round(H * 0.45) },
      vignette: { cx: 0.45, cy: 0.5, r0: 0.3, r1: 0.62, a: 0.32 } },
    stars: stars.filter(s => s.tw).map(s => [s.x, s.y, s.mag, s.col[0], s.col[1], s.col[2], +s.ph.toFixed(3), +s.sp.toFixed(3), 1]),
    water: water.map(s => [s.x, s.y, +s.ph.toFixed(3), +s.b.toFixed(3)]),
    glitter, hook: hook.map(h => [h.x, h.y, +h.ph.toFixed(3)]),
    fires: lights.filter(L => L.kind === 'fire' || L.kind === 'bonfire').map(L => [L.x, L.y, L.kind === 'bonfire' ? 4 : 3, +L.ph.toFixed(3)]),
    flies: flies.map(fl => [+fl.x.toFixed(2), +fl.y.toFixed(2), fl.ph]),
    sprays: canopy.sprays.map(sp => ({ x: sp.x, y: sp.y, ph: +sp.ph.toFixed(3), w: sp.layer.w, h: sp.layer.h })),
    grass: grass.map(gr => ({ ph: gr.ph, w: gr.layer.w, h: gr.layer.h })),
    images: {
      sky: canvasImage(skyC),
      back: canvasImage(back),
      moon: { w: mw, h: mw, data: moonImg },
      canopy: layerImage(canopy.layer, fpal),
      ...Object.fromEntries(canopy.sprays.map((sp, k) => ['spray' + k, layerImage(sp.layer, fpal)])),
      ...Object.fromEntries(grass.map((gr, k) => ['grass' + k, layerImage(gr.layer, fpal)])),
    },
  };
}

function paintSkyC(w, h, yh, S, env, ox, W) {
  const c = makeCanvas(w, h), g = ctx2d(c), id = g.createImageData(w, h), U = new Uint32Array(id.data.buffer);
  const NU = 24, q = v => Math.round(v / 2) * 2;
  for (let y = 0; y < h; y++) {
    const e = (yh - y) / S;
    for (let x = 0; x < w; x++) {
      const k = Math.round(((x - ox) / (W - 1)) * NU);
      const col = skyAtC(env, e, k / NU);
      U[y * w + x] = pack([q(col[0]), q(col[1]), q(col[2])]);
    }
  }
  g.putImageData(id, 0, 0);
  return c;
}

import { skyAt } from '../../../src/vista/tod.js';
const skyAtC = (env, e, u) => skyAt(env, e, u);

function canvasImage(c) {
  const d = ctx2d(c).getImageData(0, 0, c.width, c.height).data;
  return { w: c.width, h: c.height, data: new Uint8Array(d.buffer.slice(0)) };
}

function layerImage(L, pal) {
  const out = new Uint8Array(L.w * L.h * 4), lut = new Map();
  for (let i = 0; i < L.idx.length; i++) {
    const v = L.idx[i];
    if (!v) continue;
    let p = lut.get(v);
    if (p === undefined) { p = pal(v) >>> 0; lut.set(v, p); }
    out[i * 4] = p & 255; out[i * 4 + 1] = (p >> 8) & 255; out[i * 4 + 2] = (p >> 16) & 255; out[i * 4 + 3] = (p >>> 24) & 255;
  }
  return { w: L.w, h: L.h, data: out };
}

// lower edge of the canopy (px): low at both sides, high over the centre-left (reference coords)
function canopyEdge(W, H, x) {
  const u = x / W;
  return H * (0.15 + 0.2 * Math.pow(Math.abs(u - 0.38) / 0.62, 1.6)) + (u > 0.6 ? (u - 0.6) * H * 0.22 : 0);
}

// title.js titleCanopy, in a canvas mX wider on both sides and mT taller above the reference frame;
// the reference clumps are the JS ones, the extension continues them (own draws)
function* titleCanopy(W, H, moon, R, Wc, mX, mT) {
  const light = [0.55, -0.55, -0.6];
  const clumps = [];
  const edge = x => Math.min(canopyEdge(W, H, x), H * 0.62);
  const C = (o) => ({ ...o, x: o.x + mX, y: o.y + mT });
  for (let x = -20; x < W + 30; x += 22 + R() * 12) {
    const e = canopyEdge(W, H, x);
    clumps.push(C({ x, y: e - 6 + R() * 6, rx: 20 + R() * 10, ry: 13 + R() * 5, z: 1 + R() * 0.4 }));
    for (let y = e - 26; y > -30; y -= 22 + R() * 6) clumps.push(C({ x: x + (R() - 0.5) * 16, y, rx: 22 + R() * 10, ry: 15 + R() * 5, z: 0.4 + R() * 0.5, ao: 1 }));
  }
  const RX = rng(9091);
  for (const [a, b] of [[-mX - 30, -20], [W + 30, W + mX + 30]]) for (let x = a; x < b; x += 22 + RX() * 12) {
    const e = edge(x);
    clumps.push(C({ x, y: e - 6 + RX() * 6, rx: 20 + RX() * 10, ry: 13 + RX() * 5, z: 1 + RX() * 0.4 }));
    for (let y = e - 26; y > -30 - mT; y -= 22 + RX() * 6) clumps.push(C({ x: x + (RX() - 0.5) * 16, y, rx: 22 + RX() * 10, ry: 15 + RX() * 5, z: 0.4 + RX() * 0.5, ao: 1 }));
  }
  const curve = (a, b, bend, n, r0, r1) => {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, mx = (a[0] + b[0]) / 2 - (b[1] - a[1]) * bend, my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * bend;
      const x = (1 - t) * (1 - t) * a[0] + 2 * (1 - t) * t * mx + t * t * b[0], y = (1 - t) * (1 - t) * a[1] + 2 * (1 - t) * t * my + t * t * b[1];
      pts.push([x + Math.sin(t * 9 + a[0]) * 1.2 + mX, y + Math.cos(t * 7) * 1.2 + mT, lerp(r0, r1, Math.pow(t, 0.8))]);
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
  const ch = mT + Math.round(H * 0.72);
  const layer = yield* paintCanopyGen(Wc, ch, { clumps, limbs, light, cell: 3.4, cellSeed: 9, rimBelow: { x: moon.x + mX, y: moon.y + mT, r: moon.r * 9 } }, 61);
  const sprays = [];
  for (let k = 0; k < 7; k++) {
    const x = Math.round(W * (0.06 + k * 0.14 + (R() - 0.5) * 0.05)), e = Math.round(canopyEdge(W, H, x));
    const w = 30, h = 22, L = paintCanopy(w, h, { clumps: [{ x: 15, y: 9, rx: 9 + R() * 3, ry: 6 + R() * 2, z: 2 }], limbs: [], light, cell: 3.0, cellSeed: 11 + k, rimBelow: { x: moon.x - (x - 15), y: moon.y - (e - 2), r: moon.r * 9 } }, 70 + k);
    sprays.push({ layer: L, x: x - 15, y: e - 2, ph: R() * TAU });
  }
  return { layer, sprays };
}

function norm(v) { const l = Math.hypot(...v); return v.map(q => q / l); }
