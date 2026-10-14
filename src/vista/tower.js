// TOWER INSERT: from the canopy, north-north-east to the summit ridge. The steel lattice tower of
// 「隔」 stands on it, its red aviation lamp blinking; beside it the squat ventilation shaft of the
// old railway tunnel; behind the ridge the sky glows pale jade with the sky shore (only its light
// and the faintest hanging silhouettes: the reveal belongs to the south shot).
//   state.tower: 1 = blinking. Set 0: one last blink, then dark for good.

import { clamp, lerp, smooth, rng, hash2, vnoise, fbm, ridged, makeCanvas, ctx2d, mix3, pack, IndexLayer, I } from './util.js';
import { todEnv, palette } from './tod.js';
import { paintSky, makeStars, starCanvas, drawTwinklers } from './sky.js';
import { paintCanopy, FOLIAGE_MATS } from './foliage.js';
import { glow, px } from './lights.js';

const M = { ridge: 1, ridgeRim: 2, far: 3, steel: 4, steelRim: 5, concrete: 6, concreteDark: 7, wire: 8, farRim: 9 };

export function* towerGen(W, H, seed) { yield; return buildTower(W, H, seed); }

export function buildTower(W, H, seed) {
  const R = rng(seed * 13 + 9);
  const env = todEnv(21);
  const cx = Math.round(W / 2);
  const yh = Math.round(H * 0.78);                          // the horizon (hidden behind the ridge)
  const sky = paintSky(W, H, yh, Math.max(110, H * 0.75), env, (c, e, u) => {
    // the sky shore's light behind the ridge: pale jade, strongest low and right of centre
    const k = Math.exp(-Math.pow((u - 0.58) / 0.42, 2)) * Math.exp(-Math.pow((e - 0.32) / 0.42, 2));
    return mix3(c, [96, 150, 150], k * 0.55);
  });
  const stars = makeStars(W, yh, seed * 5 + 3, { density: 0.8 });
  // ridges: the summit ridge (near, dark, cedars on the line) and a farther one behind it
  const tx = Math.round(cx + W * 0.11);                     // the tower's foot
  const ridgeTop = x => {
    const u = (x - tx) / W;
    let y = H * 0.5 + Math.pow(Math.abs(u) * 2.2, 1.35) * H * 0.2 + (u < 0 ? -u * H * 0.06 : 0);
    y += (ridged(x * 0.012, 3, 3, seed) - 0.5) * H * 0.05;
    return y;
  };
  const farTop = x => H * 0.47 + (fbm(x * 0.006 + 5, 1, 3, seed + 3) - 0.5) * H * 0.18 + Math.abs((x - cx) / W) * H * 0.08;
  const L = new IndexLayer(W, H);
  const top = new Float32Array(W), ftop = new Float32Array(W);
  for (let x = 0; x < W; x++) {
    ftop[x] = farTop(x);
    // cedars on the summit ridge: pointed crowns along the line (bigger toward the frame edges: nearer)
    let t0 = ridgeTop(x);
    top[x] = t0;
  }
  // stamp cedar crowns along the ridge line
  for (let x = -6; x < W + 6; x += 3 + Math.floor(R() * 4)) {
    const base = ridgeTop(clamp(x, 0, W - 1));
    if (Math.abs(x - tx) < 10) continue;                     // the clearing around the tower
    const hgt = 5 + R() * 9 * (0.6 + Math.abs(x - tx) / W), wid = hgt * (0.35 + R() * 0.12);
    for (let dx = -Math.ceil(wid); dx <= Math.ceil(wid); dx++) {
      const X = x + dx; if (X < 0 || X >= W) continue;
      const v = base - hgt * (1 - Math.abs(dx) / (wid + 0.5)) + (Math.abs(dx) % 2) * 0.6;
      if (v < top[X]) top[X] = v;
    }
  }
  for (let x = 0; x < W; x++) {
    for (let y = Math.max(0, Math.floor(ftop[x])); y < H; y++) L.idx[y * W + x] = I(M.far, 3, 3, 0);
    if (hash2(x, 1, 5) < 0.6) L.idx[Math.max(0, Math.floor(ftop[x])) * W + x] = I(M.farRim, 4, 3, 0);
    const ty = Math.max(0, Math.round(top[x]));
    for (let y = ty; y < H; y++) {
      const d = y - ty;
      // rows of cedar crowns down the slope: a lit tip line every few px, broken up
      const row = (y + Math.floor(vnoise(x * 0.08, 3, 8) * 4)) % 6;
      const n = vnoise(x * 0.3, y * 0.15, 7);
      const tip = d < 36 && row === 0 && n > 0.45 + d / 80 && ((x + Math.floor(y / 6)) % 3 !== 0);
      L.idx[y * W + x] = I(M.ridge, d < 2 ? 3 : tip ? 2 : 1, 1, 0);
    }
    // rim of jade light where the ridge line meets the glowing sky (left/right slopes)
    const slope = top[Math.min(W - 1, x + 1)] - top[Math.max(0, x - 1)];
    L.idx[ty * W + x] = I(M.ridgeRim, slope > 0.6 ? 5 : slope < -0.6 ? 3 : 4, 3, 0);
  }
  // the ventilation shaft of the tunnel under the ridge, left of the tower
  const vx = Math.round(tx - W * 0.17), vy = Math.round(ridgeTop(vx));
  const vw = Math.max(7, Math.round(H * 0.035)), vh = Math.max(10, Math.round(H * 0.05));
  for (let y = vy - vh; y < vy + 2; y++) for (let x = vx - vw; x <= vx + vw; x++) {
    if (x < 0 || x >= W || y < 0) continue;
    const edge = x === vx + vw || y === vy - vh;
    const louver = y < vy - vh + 4 && y > vy - vh && (x - vx) % 2 === 0;
    L.idx[y * W + x] = I(louver ? M.concreteDark : M.concrete, edge ? 5 : x > vx ? 3 : 2, 3, 0);
  }
  // the tower: four legs (two seen), struts, cross bracing, a platform and the mast with the lamp
  const Ht = Math.round(H * 0.4), baseY = Math.round(ridgeTop(tx)) + 1, topY = baseY - Ht;
  const halfB = Math.round(Ht * 0.17), halfT = Math.max(2, Math.round(Ht * 0.045));
  const legX = (y, side) => tx + side * lerp(halfB, halfT, (baseY - y) / (baseY - topY - Ht * 0.12));
  const steel = (x, y, rim) => { x = Math.round(x); y = Math.round(y); if (x >= 0 && y >= 0 && x < W && y < H) L.idx[y * W + x] = I(rim ? M.steelRim : M.steel, rim ? 5 : 2, 2, 0); };
  const line = (x0, y0, x1, y1, rim) => { const n = Math.ceil(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))); for (let k = 0; k <= n; k++) steel(lerp(x0, x1, k / n), lerp(y0, y1, k / n), rim); };
  const bodyTop = topY + Math.round(Ht * 0.12);
  for (let y = bodyTop; y <= baseY; y++) for (const side of [-1, 1]) { const x = legX(y, side); steel(x, y, side > 0); steel(x - side, y, false); }
  const levels = [];
  for (let k = 0, y = baseY; y > bodyTop; k++) { levels.push(y); y -= Math.max(5, Math.round((y - bodyTop) * 0.24 + 4)); }
  levels.push(bodyTop);
  for (let k = 0; k < levels.length; k++) {
    const y = levels[k];
    line(legX(y, -1), y, legX(y, 1), y, false);
    if (k + 1 < levels.length) { const y2 = levels[k + 1]; line(legX(y, -1), y, legX(y2, 1), y2, false); line(legX(y, 1), y, legX(y2, -1), y2, true); }
  }
  // platform with a rail, then the mast
  const py = bodyTop;
  for (let x = tx - halfT - 3; x <= tx + halfT + 3; x++) { steel(x, py, false); if ((x - tx) % 2 === 0) steel(x, py - 2, x > tx); }
  line(tx - halfT - 3, py - 2, tx + halfT + 3, py - 2, false);
  const mastTop = topY;
  line(tx, py, tx, mastTop + 1, false); line(tx + 1, py, tx + 1, mastTop + 3, true);
  // old cables from the tower down the ridge to the right
  const wires = [];
  for (let k = 0; k < 2; k++) {
    const x0 = tx + 2, y0 = bodyTop + 6 + k * 5, x1 = W + 4, y1 = Math.round(ridgeTop(W - 1)) - 8 + k * 6;
    for (let x = x0; x <= x1; x++) {
      const u = (x - x0) / (x1 - x0), y = lerp(y0, y1, u) + Math.sin(u * Math.PI) * (8 + k * 3);
      const xi = Math.round(x), yi = Math.round(y);
      if (xi >= 0 && xi < W && yi >= 0 && yi < H && !L.idx[yi * W + xi]) wires.push(yi * W + xi);
    }
  }
  for (const i of wires) L.idx[i] = I(M.wire, 2, 2, 0);
  const lamp = { x: tx, y: mastTop };
  // the canopy framing the shot: a mass at the lower left, a spray at the right edge
  const clumps = [];
  for (let k = 0; k < 9; k++) clumps.push({ x: W * (-0.04 + R() * 0.26), y: H * (0.78 + R() * 0.3), rx: 18 + R() * 10, ry: 13 + R() * 5, z: R() });
  for (let k = 0; k < 4; k++) clumps.push({ x: W * (0.94 + R() * 0.1), y: H * (0.9 + R() * 0.14), rx: 16 + R() * 8, ry: 12 + R() * 4, z: R() });
  clumps.push({ x: W * 0.05, y: H * 0.1, rx: 22, ry: 14, z: 1 }, { x: W * 0.13, y: H * 0.03, rx: 18, ry: 12, z: 1.2 }, { x: -6, y: H * 0.22, rx: 16, ry: 12, z: 1.1 });
  const canopy = paintCanopy(W, H, { clumps, limbs: [{ pts: [[-10, H * 0.26, 4.5], [W * 0.08, H * 0.12, 3], [W * 0.16, -4, 2]], z: 0.8, dark: 1 }], light: [0.6, -0.4, -0.5], cell: 3.4, cellSeed: 13, rimBelow: { x: W * 0.6, y: H * 0.4, r: W } }, 91);

  // palettes
  const glowCol = [96, 150, 150];
  const pal = i => {
    const m = i >> 8, s = (i >> 5) & 7;
    let c;
    switch (m) {
      case M.ridge: c = s >= 3 ? [26, 33, 47] : s === 2 ? [22, 28, 41] : [15, 19, 30]; break;
      case M.ridgeRim: c = mix3([30, 40, 52], glowCol, 0.22 + s * 0.05); break;
      case M.far: c = [40, 48, 72]; break;
      case M.farRim: c = [50, 64, 84]; break;
      case M.steel: c = [26, 22, 26]; break;
      case M.steelRim: c = [70, 84, 88]; break;
      case M.concrete: c = s >= 5 ? [74, 86, 96] : s >= 3 ? [46, 52, 62] : [34, 38, 48]; break;
      case M.concreteDark: c = [16, 18, 24]; break;
      case M.wire: c = [30, 30, 40]; break;
      default: return 0;
    }
    return pack(c);
  };

  let t = 0, prevOn = null, dying = false, dyingT = 0, dead = false;
  let cache = null;
  const shot = {
    anchors: { lamp: { x: lamp.x, y: lamp.y }, shaft: { x: vx, y: vy - vh } },
    info: { lamp },
    draw(g, dt, st) {
      t += dt;
      if (!cache) {
        cache = {
          sky, stars: starCanvas(W, H, stars, y => smooth(H * 0.62, H * 0.3, y)),
          land: L.canvas('t', pal), canopy: canopy.canvas('t', palette(FOLIAGE_MATS, { ...env, sun: [0.2, 0.32, 0.32] })),
          vign: (() => { const c = makeCanvas(W, H), vg = ctx2d(c); const gr = vg.createRadialGradient(W * 0.55, H * 0.45, Math.min(W, H) * 0.3, W * 0.55, H * 0.45, Math.hypot(W, H) * 0.6); gr.addColorStop(0, 'rgba(4,5,12,0)'); gr.addColorStop(1, 'rgba(4,5,12,1)'); vg.fillStyle = gr; vg.fillRect(0, 0, W, H); return c; })(),
        };
      }
      g.drawImage(cache.sky, 0, 0);
      g.drawImage(cache.stars, 0, 0);
      drawTwinklers(g, stars, t, 1, 0, 0, y => smooth(H * 0.62, H * 0.3, y));
      // the faintest hanging silhouettes in the glow (the sky shore, far behind the ridge)
      ghostShore(g, W, H, t);
      g.drawImage(cache.land, 0, 0);
      // the lamp: 1.5 s cycle, 0.4 s on. Off: one last blink, then nothing.
      const on = (st.tower ?? 1) > 0.5;
      if (prevOn === null) { dead = !on; prevOn = on; }
      if (prevOn && !on) { dying = true; dyingT = 0; }
      if (on && dead) { dead = false; dying = false; }
      prevOn = on;
      let k = 0;
      const ph = (t % 1.5) / 1.5;
      if (!dead && !dying) k = ph < 0.27 ? smooth(0, 0.04, ph) * (1 - smooth(0.22, 0.27, ph)) : 0;
      if (dying) {
        dyingT += dt;
        // a last blink a beat later, a little longer, guttering, then gone
        const u = dyingT - 0.35;
        k = u < 0 ? 0 : u < 0.5 ? (0.85 + 0.15 * Math.sin(u * 60)) * (1 - smooth(0.3, 0.5, u)) : 0;
        if (u > 0.6) { dying = false; dead = true; }
      }
      if (k > 0.01) {
        glow(g, lamp.x, lamp.y, 10, [255, 70, 50], 0.5 * k);
        glow(g, lamp.x, lamp.y, 4, [255, 120, 90], 0.8 * k);
        px(g, lamp.x, lamp.y, [255, 200, 180], k);
        // the red catches the top of the lattice
        g.globalAlpha = 0.5 * k; g.fillStyle = '#b8342a';
        for (let y = lamp.y + 2; y < lamp.y + Math.round(H * 0.07); y += 1) { g.fillRect(lamp.x + 1, y, 1, 1); }
        g.globalAlpha = 1;
      } else if (!dead) px(g, lamp.x, lamp.y, [90, 30, 30], 0.9);
      else px(g, lamp.x, lamp.y, [40, 26, 30], 0.9);
      g.drawImage(cache.canopy, 0, 0);
      g.globalAlpha = 0.5; g.drawImage(cache.vign, 0, 0); g.globalAlpha = 1;
    },
  };
  return shot;
}

// The sky shore beyond the ridge (already revealed by the time of this insert): a band of hanging
// peaks high up, pale and hazy, their lower edges catching the light, a few of their lamps.
function ghostShore(g, W, H, t) {
  if (!ghostShore.c || ghostShore.c.width !== W || ghostShore.c.height !== H) {
    const c = makeCanvas(W, H), gg = ctx2d(c), id = gg.createImageData(W, H), U = new Uint32Array(id.data.buffer);
    const edge = new Float32Array(W), edge2 = new Float32Array(W);
    for (let x = 0; x < W; x++) {
      edge[x] = H * 0.07 + Math.pow(ridged(x * 0.012 + 2, 5, 3, 31), 2.2) * H * 0.2;
      edge2[x] = H * 0.12 + Math.pow(ridged(x * 0.02 + 9, 7, 3, 37), 2.4) * H * 0.13;
    }
    for (let x = 0; x < W; x++) {
      // far layer (paler), then the near layer over it
      for (let y = 0; y < edge2[x]; y++) U[y * W + x] = pack([60, 78, 104], Math.round(0.7 * smooth(0, H * 0.05, y) * 255));
      const e2 = Math.floor(edge2[x]); if (e2 >= 0 && e2 < H) U[e2 * W + x] = pack([96, 132, 140], Math.round(0.5 * 255));
      for (let y = 0; y < edge[x]; y++) {
        // faces of the hanging peaks: which way the edge slopes below, followed up and a little aslant
        const x2 = Math.max(1, Math.min(W - 2, Math.round(x + (y - edge[x]) * 0.35)));
        const shade = edge[x2 + 1] - edge[x2 - 1] > 0 ? 1 : 0;
        U[y * W + x] = pack(shade ? [40, 54, 80] : [48, 63, 89], Math.round(0.9 * smooth(0, H * 0.04, y) * 255));
      }
      const e = Math.floor(edge[x]); if (e >= 0 && e < H) U[e * W + x] = pack([104, 148, 150], Math.round(0.55 * 255));
    }
    // their lamps, pale jade, in the high valleys
    for (let k = 0; k < Math.round(W / 9); k++) {
      const x = Math.floor(hash2(k, 1, 41) * W), y = Math.floor(edge[x] * (0.35 + hash2(k, 2, 41) * 0.5));
      if (y > 2) U[y * W + x] = pack([200, 246, 228], Math.round((0.35 + hash2(k, 3, 41) * 0.4) * 255));
    }
    gg.putImageData(id, 0, 0);
    ghostShore.c = c;
  }
  g.drawImage(ghostShore.c, 0, 0);
}
