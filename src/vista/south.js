// TREETOP SOUTH: from the crown of the great camphor on the pass, south over the plain, dusk to
// night. The camera cranes up out of the leaves (pan); lamps come on across the plain as it gets
// dark; then the lights leave the ground and rise in streams toward the gate above the pass
// (rise); the cloud deck, lit from below, parts and the sky shore hangs there upside down (sky);
// a ring of pale distance spreads from the plain under it and comes up the mountain (wave).
//
// Layers (back to front): sky, stars, sky shore, cloud deck, ground (with the wave composite),
// lights on the ground, the wave's curtain, rising lights, canopy (back), figure callback,
// canopy (front), close leaves (only during the pan), vignette.

import { clamp, lerp, smooth, rng, hash2, makeCanvas, ctx2d, mix3, scale3, TAU } from './util.js';
import { todEnv, palette, skyAt, farTransform } from './tod.js';
import { paintSky, makeStars, starCanvas, drawTwinklers, CloudDeck, cloudPalette } from './sky.js';
import { buildGround, GROUND_MATS, G, TOWN, HEADMAN, HAMLETS, RIVER } from './ground.js';
import { paintBuildings, roadLanterns } from './buildings.js';
import { buildSkyShore, skyShorePalette } from './skyshore.js';
import { paintCanopy, FOLIAGE_MATS } from './foliage.js';
import { Wave } from './wave.js';
import { COL, glow, px, riseColor, cssOf } from './lights.js';

const P = { far: 0.08, canopy: 1, front: 1.9 };

export function buildSouth(W, H, seed) {
  const R = rng(seed * 7 + 3);
  const TM = {}, t00 = performance.now(); let tl = t00;
  const lap = k => { const n = performance.now(); TM[k] = Math.round(n - tl); tl = n; };
  const yh = Math.round(clamp(H * 0.475, H - 165, H - 118));
  const cx = Math.round(W / 2), f = 360, S = Math.max(110, yh * 1.1);
  const D = Math.round(H * 0.8);                 // camera rise over the pan (px at parallax 1)
  const padTop = Math.ceil(D * P.far) + 2;       // the far group is drawn up to this much higher
  const yl = yh + padTop;                        // horizon row in far-group layer coordinates
  const gh = H + padTop;
  const sun = { dir: norm([0.85, 0.27, -0.45]), slope: 0.3 };

  // ---------------- ground, buildings, lights on the ground
  const ground = buildGround({ w: W, h: gh, cx, yh: yl, f, S, sun, seed });
  lap('ground');
  const cam = { cx, yh: yl, f, height: ground.height };
  const lights = paintBuildings(ground.layer, ground.X, ground.Z, cam, ground.hamlets, seed);
  lights.push(...roadLanterns(cam, ground.Z, W, gh));
  // big bonfires on the river bank (送り火)
  for (const u of [3.2, 5.6, 8.4]) {
    const i = Math.floor(u), t = u - i, [ax, az] = RIVER[i], [bx, bz] = RIVER[i + 1];
    const X = lerp(ax, bx, t) + 0.16, Z = lerp(az, bz, t);
    const x = Math.round(cx + f * X / Z), y = Math.round(yl + f / Z);
    if (x > 0 && x < W && ground.Z[y * W + x] > Z * 0.9) lights.push({ x, y, X, Z, kind: 'bonfire' });
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
  const Hs = 9, Zf = 21;
  const tipX = cx - Math.round(W * 0.05), tipY = Math.round(yh * 0.3) + padTop;
  const Fn = { X: (tipX - cx) * Zf / f, Z: Zf, D: Hs - (yl - tipY) * Zf / f, R: 6.5 };
  const at = (fx, fy, Z) => ({ X: fx * W * Z / f, Z, y: yl - fy * yh });  // place on the ceiling by screen position
  const towns = [
    { X: (-0.3 * W) * 38 / f, Z: 38, r: 3.2 },
    { X: (0.28 * W) * 44 / f, Z: 44, r: 3.6 },
    { X: (0.02 * W) * 62 / f, Z: 62, r: 4.5 },
  ];
  const ringC = { X: (0.2 * W) * 31 / f, Z: 31, r: 0.95 };
  towns.push({ X: ringC.X, Z: ringC.Z, r: 2.0 });
  const hazeEdgeY = yl - Math.round(clamp(yh * 0.36, 34, 58));
  const shoreH = hazeEdgeY + 10;
  const shore = buildSkyShore({ w: W, h: shoreH, cx, yh: yl, f, Hs, funnel: Fn, towns, hazeEdgeY, zNear: 24, zFar: 80, seed });
  lap('lights+shore');
  const T = shore.proj(Fn.X, Fn.Z); T[1] += 1;   // the mouth, where the streams go in
  const ring = [];
  for (let k = 0; k < 22; k++) ring.push(k / 22 * TAU);

  // ---------------- cloud deck between the shores
  const Hcl = 2.6;
  const deck = new CloudDeck({ w: W, h: yl, cx, yh: yl, f, Hc: Hcl, seed: seed * 5 + 2, cover: 0.5, bottom: yl - 30 });
  const hole = { X: Fn.X * Hcl / (Hs - Fn.D), Z: Fn.Z * Hcl / (Hs - Fn.D), r: 0 }; // where the line to the mouth crosses the deck
  const deckC = makeCanvas(W, yl), deckG = ctx2d(deckC);
  lap('clouds');

  // ---------------- rising: clusters, order, paths
  const clusters = [{ X: TOWN.X, Z: TOWN.Z }, { X: HEADMAN.X, Z: HEADMAN.Z }, ...HAMLETS.map(h => ({ X: h.X, Z: h.Z }))];
  for (const L of lights) {
    let best = 0, bd = 1e9;
    for (let k = 0; k < clusters.length; k++) { const d = Math.hypot(L.X - clusters[k].X, L.Z - clusters[k].Z); if (d < bd) { bd = d; best = k; } }
    L.cl = L.kind === 'star' ? 100 + Math.floor(L.x / 40) : best;
    L.on = L.kind === 'star' ? 19.4 + R() * 0.6 : L.kind === 'window' ? 18.25 + R() * 1.1 : L.kind === 'lantern' ? 18.6 + R() * 0.7 : 19.0 + R() * 0.7;
    L.ph = L.ph ?? R() * TAU;
  }
  // departure order: two lone lights first, then every cluster emits its lights at its own steady
  // pace across the whole rise (a queue per place, all places at once)
  const byCl = new Map();
  for (const L of lights) { if (!byCl.has(L.cl)) byCl.set(L.cl, []); byCl.get(L.cl).push(L); }
  const first = lights.find(L => L.kind === 'window' && Math.abs(L.X - HEADMAN.X) < 0.3 && Math.abs(L.Z - HEADMAN.Z) < 0.3);
  const second = lights.find(L => L.kind === 'bonfire' && L !== first) || lights[1];
  for (const [k, arr] of byCl) {
    arr.sort(() => R() - 0.5);
    const rest = arr.filter(L => L !== first && L !== second), n = rest.length;
    const c = clusters[k], d = c ? Math.hypot(c.X - TOWN.X, c.Z - TOWN.Z) : 12;
    const start = 0.17 + clamp(d / 40, 0, 1) * 0.1 + R() * 0.03;         // nearer the town starts sooner
    rest.forEach((L, i) => { L.r = start + (0.96 - start) * (i + R() * 0.5) / Math.max(1, n); });
  }
  if (first) first.r = 0.03;
  if (second) second.r = 0.11;
  const clCentre = new Map();
  for (const [k, arr] of [...byCl.entries()]) {
    const all = lights.filter(L => L.cl === k);
    const mx = all.reduce((s, L) => s + L.x, 0) / all.length, my = all.reduce((s, L) => s + L.y, 0) / all.length;
    clCentre.set(k, [mx, my]);
  }
  const clJit = new Map();
  for (const k of byCl.keys()) clJit.set(k, [(R() - 0.5) * 14, (R() - 0.5) * 10, 16 + R() * 18]);
  for (const L of lights) {
    const [mx, my] = clCentre.get(L.cl), [jx, jy, cl] = clJit.get(L.cl);
    const lift = cl + R() * 8;
    L.p1 = [L.x + (R() - 0.5) * 3, L.y - lift];
    const sx = lerp(T[0], mx, 0.62) + jx + (R() - 0.5) * 3, sy = lerp(T[1], my - 40, 0.45) + jy + (R() - 0.5) * 3;
    L.p2 = [sx, sy];
    L.p3 = [T[0] + (R() - 0.5) * 3, T[1] + (R() - 0.5) * 2];
    L.dur = 7.2 + hash2(L.cl, 7, 41) * 2.4 + R() * 0.3;   // one pace per stream: they keep their spacing, like a queue
    L.el = -1;
  }

  // ---------------- the wave
  const Xc = TOWN.X + 0.2, Zc = TOWN.Z - 0.6;
  const wave = new Wave({ w: W, h: gh, X: ground.X, Z: ground.Z, mask: ground.mask, Xc, Zc, R: Math.hypot(Xc, Zc) - 0.05, f });
  for (const L of lights) L.arr = wave.arrivalOf(L.X, L.Z);
  lap('rise+wave');

  // ---------------- the canopy
  const CT = 66, CH = CT + D + 40;            // canopy layer: CT px visible at pan 1, then the mass below
  const back = canopyBack(W, CH, CT, R), frontC = canopyFront(W, CH, CT, R);
  const nearL = nearLeaves(W, H, R);
  lap('canopy');
  const anchorsLocal = {
    branch: { x: Math.round(W * 0.62), y: back.limbTop(Math.round(W * 0.62)) },
    stand: { x: Math.round(W * 0.69), y: back.limbTop(Math.round(W * 0.69)) },
  };

  // ---------------- per-frame state
  let t = 0, lastRise = 0;
  const arrivals = [];
  const skyCache = new Map();
  let vign = null, vignKey = '';
  const shot = {
    anchors: {},
    info: { yh, padTop, T, ground: ground.ms, lights: lights.length, TM },
    draw(g, dt, st) {
      t += dt;
      const tod = clamp(st.tod ?? 21, 16.5, 24);
      const tq = Math.round(tod * 20) / 20, key = tq.toFixed(2);
      const env = todEnv(tq);
      const envG = { ...env, sun: env.sun.map(v => v * (1 - 0.8 * env.night)) };
      const pan = smooth(0, 1, clamp(st.pan ?? 1, 0, 1));
      const dy = (1 - pan) * D;
      const oFar = -Math.round(dy * P.far) - padTop;
      const rise = clamp(st.rise ?? 0, 0, 1), skyK = clamp(st.sky ?? 0, 0, 1);
      const wv = st.wave == null ? -1 : st.wave;
      const night = env.night;

      // sky
      let sky = skyCache.get(key);
      if (!sky) { sky = paintSky(W, gh, yl, S, env); skyCache.set(key, sky); if (skyCache.size > 3) skyCache.delete(skyCache.keys().next().value); }
      g.drawImage(sky, 0, oFar);
      // stars
      const fade = y => smooth(yl, yl - 36, y);
      if (env.stars > 0.02) {
        if (!shot.starC) shot.starC = starCanvas(W, yl, stars, fade);
        g.globalAlpha = env.stars; g.drawImage(shot.starC, 0, oFar); g.globalAlpha = 1;
        drawTwinklers(g, stars, t, env.stars, 0, oFar, fade);
      }

      // the sky shore: materialises as the clouds part
      const reveal = smooth(0.05, 0.75, skyK);
      if (reveal > 0) {
        const hazeCol = skyAt(env, 0.3, 0.5);
        const sc = shore.layer.canvas('s' + key, skyShorePalette(mix3(hazeCol, [80, 90, 128], 0.55)));
        g.globalAlpha = reveal; g.drawImage(sc, 0, oFar); g.globalAlpha = 1;
        drawShoreLights(g, shore, ring, ringC, t, reveal, oFar, T, arrivals, hazeEdgeY);
      }

      // the cloud deck (its own canvas, so the light from below only lights the clouds)
      const hr = Math.round(Math.pow(skyK, 1.15) * 48) / 48;
      hole.r = hr * 9.5;
      const envC = { ...env, sun: mix3(env.sun.map(v => v * 0.9), [0.42, 0.27, 0.2], night) };
      const dk = deck.render(hole, key, cloudPalette(envC), [0.82 - 0.7 * night, 0.58 + 0.3 * night]);
      deckG.clearRect(0, 0, W, yl);
      deckG.drawImage(dk, 0, 0);
      const inFlight = lights.reduce((n, L) => n + (L.el >= 0 && L.el < L.dur ? 1 : 0), 0);
      const flux = clamp(inFlight / 40, 0, 1);
      if (flux > 0.01 || reveal > 0) {
        deckG.globalCompositeOperation = 'source-atop';
        glow(deckG, T[0], T[1] + 30, 70, [255, 176, 120], 0.5 * flux);
        glow(deckG, T[0], T[1] + 10, 56, [170, 236, 216], 0.45 * reveal);
        deckG.globalCompositeOperation = 'source-over';
      }
      g.drawImage(deckC, 0, oFar);

      // ground (or the wave's composite of near and far)
      const gpal = palette(GROUND_MATS, envG, { haze: env.mist });
      let gc;
      if (wv >= 0) {
        if (wave.key !== key) wave.base(key, ground.layer.pixels(gpal), ground.layer.pixels(palette(GROUND_MATS, envG, { haze: env.mist, far: true })));
        gc = wave.update(wv);
      } else gc = ground.layer.canvas('g' + key, gpal);
      g.drawImage(gc, 0, oFar);

      // lights on the ground
      drawGroundLights(g, lights, river, ground, cam, tod, rise, wv, t, oFar, dt, W);
      // the wave's curtain of motes
      if (wv >= 0) wave.drawFront(g, 0, oFar, wv, t, dt, 1);
      // rising lights
      updateRise(lights, rise, dt, arrivals, t);
      drawRising(g, lights, t, skyK, oFar);

      // canopy, figure, leaves in front of her
      const oC = Math.round(H - CT - dy * P.canopy);
      const fpal = palette(FOLIAGE_MATS, { ...env, sun: env.sun.map(v => v * (1 - 0.7 * env.night)) });
      g.drawImage(back.layer.canvas('f' + key, fpal), 0, oC);
      drawStir(g, back, key, fpal, oC, t);
      const a = shot.anchors;
      a.branch = { x: anchorsLocal.branch.x, y: anchorsLocal.branch.y + oC };
      a.stand = { x: anchorsLocal.stand.x, y: anchorsLocal.stand.y + oC };
      if (st.figure) { g.save(); st.figure(g, a); g.restore(); }
      g.drawImage(frontC.layer.canvas('f' + key, fpal), 0, oC);
      // close leaves, sliding out of frame as the camera rises
      const oN = Math.round(H + 8 - dy * P.front);
      if (oN < H) g.drawImage(nearL.canvas('n' + key, fpal), 0, oN);

      // vignette, and the end of the wave washing everything pale
      const vk = W + 'x' + H;
      if (vignKey !== vk) { vign = vignette(W, H); vignKey = vk; }
      g.globalAlpha = lerp(0.35, 0.6, night); g.drawImage(vign, 0, 0); g.globalAlpha = 1;
      if (wv > 0.9) { g.fillStyle = '#dfe6f6'; g.globalAlpha = smooth(0.9, 1.0, wv) * 0.55; g.fillRect(0, 0, W, H); g.globalAlpha = 1; }
    },
  };
  return shot;

  // ---------------------------------------------------------------- helpers using the closure

  function drawGroundLights(g, lights, river, ground, cam, tod, rise, wv, t, oy, dt) {
    g.globalCompositeOperation = 'source-over';
    for (const L of lights) {
      let a = smooth(L.on, L.on + 0.25, tod);
      if (a <= 0) continue;
      if (L.el >= 0) { // gone up; a fire leaves its embers
        if (L.kind === 'fire' || L.kind === 'bonfire') px(g, L.x, L.y + oy, COL.ember, 0.55 * a * (1 - smooth(L.arr, L.arr + 0.02, wv)));
        continue;
      }
      if (wv >= 0) a *= 1 - smooth(L.arr - 0.004, L.arr + 0.012, wv);
      if (a <= 0.02) continue;
      const x = L.x, y = L.y + oy, ph = L.ph;
      switch (L.kind) {
        case 'window': {
          const c = L.far ? COL.windowDim : COL.window;
          px(g, x, y, c, a * (L.far ? 0.75 : 0.95));
          if (!L.far) glow(g, x, y, 2, scale3(COL.window, 0.35), a);
          break;
        }
        case 'lantern': px(g, x, y, COL.lantern, a * 0.9); glow(g, x, y, 2, scale3(COL.lantern, 0.4), a); break;
        case 'fire': {
          const fl = 0.75 + 0.25 * Math.sin(t * 11 + ph * 9) * Math.sin(t * 7.3 + ph * 3);
          px(g, x, y, fl > 0.85 ? COL.fireHot : COL.fire, a);
          if (fl > 0.7) px(g, x, y - 1, COL.lantern, a * 0.6);
          glow(g, x, y, 3, scale3(COL.lantern, 0.45 * fl), a);
          break;
        }
        case 'bonfire': {
          const fl = 0.78 + 0.22 * Math.sin(t * 9 + ph * 9) * Math.sin(t * 5.1 + ph * 3);
          px(g, x - 1, y, COL.fire, a, 2, 1);
          px(g, x, y - 1, fl > 0.8 ? COL.fireHot : COL.fire, a);
          if (fl > 0.86) px(g, x - 1 + (Math.sin(t * 13 + ph) > 0 ? 1 : 0), y - 2, COL.lantern, a * 0.7);
          glow(g, x, y - 1, 6, scale3(COL.lantern, 0.5 * fl), a);
          break;
        }
        case 'star': {
          const tw = 0.55 + 0.45 * Math.sin(t * 1.7 + ph) * Math.sin(t * 0.6 + ph * 2);
          px(g, x, y, COL.star, a * 0.55 * tw * (1 - smooth(0.25, 0.5, rise) * 0)); // stars rise with the rest
          break;
        }
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
      px(g, x, y + oy, COL.lantern, a * 0.85);
      px(g, x, y + oy + 1, COL.lantern, a * 0.3); // its reflection
      glow(g, x, y + oy, 2, scale3(COL.lantern, 0.35), a);
    }
  }
}

// ---------------------------------------------------------------- rising

function updateRise(lights, rise, dt, arrivals, t) {
  for (const L of lights) {
    if (L.r == null) continue;
    if (rise >= L.r) {
      if (L.el < 0) L.el = (rise - L.r) * 30;  // as if it left when rise passed its turn
      else {
        const before = L.el;
        L.el += dt;
        if (before < L.dur && L.el >= L.dur) arrivals.push(t);
      }
    } else L.el = -1;
  }
  while (arrivals.length && arrivals[0] < t - 1.5) arrivals.shift();
}

function bez(L, s) {
  const u = 1 - s, a = u * u * u, b = 3 * u * u * s, c = 3 * u * s * s, d = s * s * s;
  return [a * L.x + b * L.p1[0] + c * L.p2[0] + d * L.p3[0], a * L.y + b * L.p1[1] + c * L.p2[1] + d * L.p3[1]];
}

function drawRising(g, lights, t, skyK, oy) {
  for (const L of lights) {
    if (L.el < 0 || L.el >= L.dur) continue;
    const u = L.el / L.dur;
    const s = u * 0.62 + u * u * (3 - 2 * u) * 0.38;
    const [x, y] = bez(L, s);
    const base = L.kind === 'star' ? COL.star : L.kind === 'window' ? COL.window : L.kind === 'lantern' ? COL.lantern : COL.fire;
    const c = riseColor(base, s);
    let a = smooth(0, 0.06, u) * (L.kind === 'star' ? 0.75 : 1);
    a *= 1 - (1 - smooth(0.15, 0.6, skyK)) * smooth(0.8, 0.97, s); // into the clouds while they are closed
    a *= 1 - smooth(0.96, 1, s) * 0.6;
    if (a <= 0.02) continue;
    const big = L.kind === 'bonfire' || L.kind === 'fire';
    // a short tail
    for (let k = 1; k <= 4; k++) {
      const [tx, ty] = bez(L, Math.max(0, s - k * 0.012));
      px(g, tx, ty + oy, c, a * (0.5 - k * 0.1));
    }
    px(g, x, y + oy, mix3(c, [255, 255, 255], 0.3), a, big ? 2 : 1, big ? 2 : 1);
    glow(g, x + (big ? 0.5 : 0), y + oy, big ? 5 : 3, scale3(c, 0.55), a);
  }
}

// ---------------------------------------------------------------- the sky shore's lights

function drawShoreLights(g, shore, ring, ringC, t, reveal, oy, T, arrivals, hazeEdgeY) {
  for (const L of shore.lights) {
    const fadeEdge = smooth(hazeEdgeY + 2, hazeEdgeY - 10, L.y);
    const tw = 0.75 + 0.25 * Math.sin(t * 0.9 + L.ph * 40);
    const a = reveal * L.b * tw * fadeEdge * (1 - smooth(30, 75, L.Z) * 0.5);
    if (a < 0.03) continue;
    px(g, L.x, L.y + oy, COL.jadeCore, a);
    if (L.b > 0.8 && L.Z < 50) glow(g, L.x, L.y + oy, 2, scale3(COL.jade, 0.35), a);
  }
  // the dance ring: lanterns round the plaza, the circle of dancers passing in front of them
  const [rx, ry] = shore.proj(ringC.X, ringC.Z);
  for (let k = 0; k < ring.length; k++) {
    const th = ring[k];
    const X = ringC.X + Math.cos(th) * ringC.r, Z = ringC.Z + Math.sin(th) * ringC.r;
    const [x, y] = shore.proj(X, Z);
    const b = 0.6 + 0.4 * Math.sin(th * 2 - t * 1.3);
    px(g, x, y + oy, COL.jadeCore, reveal * b);
    glow(g, x, y + oy, 2, scale3(COL.jade, 0.45), reveal * b);
  }
  // the yagura at its centre and the strings of lanterns from it
  px(g, rx, ry + oy, COL.jadeCore, reveal);
  glow(g, rx, ry + oy, 4, scale3(COL.jade, 0.5), reveal);
  for (let k = 0; k < 8; k++) {
    const th = k / 8 * TAU + 0.2;
    for (let j = 1; j <= 3; j++) {
      const X = ringC.X + Math.cos(th) * ringC.r * j / 4, Z = ringC.Z + Math.sin(th) * ringC.r * j / 4;
      const [x, y] = shore.proj(X, Z);
      px(g, x, y + oy, COL.jade, reveal * 0.55);
    }
  }
  // the gate's mouth: glowing with what goes in
  const inflow = clamp(arrivals.length / 12, 0, 1);
  const pulse = 0.85 + 0.15 * Math.sin(t * 2.2);
  glow(g, T[0], T[1] + oy, 9, scale3(COL.jade, 0.5), reveal * (0.35 + 0.65 * inflow) * pulse);
  glow(g, T[0], T[1] + oy, 3, scale3(COL.jadeCore, 0.8), reveal * (0.5 + 0.5 * inflow));
  px(g, T[0], T[1] + oy, COL.jadeCore, reveal);
}

// ---------------------------------------------------------------- canopy

function canopyBack(W, CH, CT, R) {
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
  const layer = paintCanopy(W, CH, { clumps, limbs: [{ pts: limb, z: 1.5 }], light: [0.72, -0.42, 0.45] }, 41);
  const limbTop = x => {
    for (let y = 0; y < CH; y++) { const v = layer.idx[y * W + x]; if (v && ((v >> 8) === 6 || (v >> 8) === 7)) return y; }
    return CT - 40;
  };
  return { layer, limbTop };
}

function canopyFront(W, CH, CT, R) {
  // clumps in front of the limb, around her: they overlap the limb's underside and her lap
  const P = (fx, y, rx, ry, z) => ({ x: W * fx, y, rx, ry, z });
  const clumps = [
    P(0.61, CT - 21, 13, 9, 3.2), P(0.71, CT - 17, 17, 11, 3.1), P(0.52, CT - 14, 15, 10, 3.15),
    P(0.84, CT - 12, 22, 14, 3.1), P(0.98, CT - 20, 20, 14, 3), P(0.4, CT - 4, 22, 13, 3),
    P(0.22, CT - 2, 24, 14, 3), P(0.05, CT - 8, 24, 15, 3),
  ].map(c => ({ ...c, glint: false }));
  return { layer: paintCanopy(W, CH, { clumps, limbs: [], light: [0.72, -0.42, 0.45] }, 43) };
}

function nearLeaves(W, H, R) {
  // big leaves right in front of the lens: only seen while the camera rises through them
  const h = H + 80, clumps = [];
  for (let y = 20, row = 0; y < h - 10; y += 46, row++) for (let x = (row % 2) * 40 - 20; x < W + 40; x += 78 + R() * 30) {
    clumps.push({ x, y: y + R() * 16, rx: 34 + R() * 16, ry: 26 + R() * 10, z: R() });
  }
  return paintCanopy(W, h, { clumps, limbs: [], light: [0.72, -0.42, 0.45], cell: 6.5 }, 47);
}

function drawStir(g, back, key, fpal, oC, t) { /* leaf stirring: see title */ }

function vignette(W, H) {
  const c = makeCanvas(W, H), g = ctx2d(c);
  const gr = g.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.35, W / 2, H * 0.45, Math.hypot(W, H) * 0.62);
  gr.addColorStop(0, 'rgba(4,5,12,0)'); gr.addColorStop(1, 'rgba(4,5,12,1)');
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
  return c;
}

function norm(v) { const l = Math.hypot(...v); return v.map(q => q / l); }
