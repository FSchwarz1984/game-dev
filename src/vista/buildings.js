// Houses on the plain, drawn small and clear: a roof (tile or thatch) with its sunward side lit, a
// strip of wall under the eaves. Painted into the ground's index layer with a depth test against
// the terrain, so folds of the range hide what is behind them. Each building also reports where
// its windows, gate lanterns and gate fires are, for the lights.

import { clamp, rng, I } from './util.js';
import { G, HEADMAN, TOWN, ROADS } from './ground.js';

// sun bits for the lit and shaded faces
const LIT = 6, SHD = 2;

function hazeOf(Z) { return clamp(Math.floor((1 - Math.exp(-Z / 62)) * 8), 0, 7); }

// one house: w px wide (>= 2). thatch: tall rounded roof; else a low tile roof. kura: white store.
function houseSprite(w, kind) {
  const px = []; // [dx, dy, mat, sun]  (dy <= 0, anchored bottom centre)
  const half = w / 2;
  if (kind === 'kura') {
    const hW = Math.max(2, Math.round(w * 0.9)), rH = Math.max(1, Math.round(w * 0.35));
    for (let y = 0; y < hW; y++) for (let x = 0; x < w; x++) px.push([x - Math.floor(half), -y, G.kura, x >= half ? SHD + 1 : LIT]);
    for (let y = 0; y < rH; y++) for (let x = -1; x <= w; x++) if (x >= y - 1 && x <= w - y) px.push([x - Math.floor(half), -hW - y, G.roof, x >= half ? LIT : SHD]);
    return px;
  }
  const wallH = Math.max(1, Math.round(w * 0.28));
  const roofH = kind === 'thatch' ? Math.max(2, Math.round(w * 0.55)) : Math.max(1, Math.round(w * 0.36));
  const roofMat = kind === 'thatch' ? G.thatch : G.roof;
  for (let y = 0; y < wallH; y++) for (let x = 0; x < w; x++) {
    const m = (x === 0 || x === w - 1) && w > 4 ? G.wood : G.wall;
    px.push([x - Math.floor(half), -y, y === wallH - 1 && w > 3 ? G.wood : m, x >= half ? LIT - 1 : SHD]);
  }
  for (let y = 0; y < roofH; y++) {
    const inset = kind === 'thatch' ? Math.round((y / roofH) ** 1.6 * (half - 0.5)) : Math.round(y * (half / roofH) * 0.85);
    for (let x = -1 + inset; x <= w - inset; x++) {
      const ridge = y === roofH - 1;
      px.push([x - Math.floor(half), -wallH - y, roofMat === G.roof && ridge ? G.roofLit : roofMat, x >= half - 0.5 ? LIT : SHD]);
    }
  }
  return px;
}

/**
 * @param {IndexLayer} L ground layer; Zb, Xb its per-pixel ground position (updated for building pixels)
 * @param {object} cam { cx, yh, f, height }
 * @returns lights: [{x, y, X, Z, kind}]
 */
export function paintBuildings(L, Xb, Zb, cam, hamlets, seed) {
  const R = rng(seed + 101), { cx, yh, f, height } = cam, lights = [];
  const list = [];
  const sizeAt = (Z, k = 1) => Math.max(2, Math.round((f * 0.05 / Z) * k * 2.2));
  for (const h of hamlets) for (const ho of h.houses) list.push({ X: ho.X, Z: ho.Z, w: sizeAt(ho.Z, ho.big ? 1.25 : 1), kind: ho.thatch ? 'thatch' : 'tile', fire: R() < 0.5, lantern: R() < 0.35 });
  // the headman's compound: a big thatched main house, a white kura, a gate with lanterns
  const hz = HEADMAN.Z;
  list.push({ X: HEADMAN.X, Z: hz, w: sizeAt(hz, 2.0), kind: 'thatch', headman: true, fire: true, lantern: true });
  list.push({ X: HEADMAN.X + 0.19, Z: hz + 0.05, w: sizeAt(hz, 0.95), kind: 'kura' });
  list.push({ X: HEADMAN.X - 0.17, Z: hz - 0.06, w: sizeAt(hz, 1.1), kind: 'tile', lantern: true });
  // the town: rows of houses along its streets, a temple roof in the middle
  for (let i = 0; i < 110; i++) {
    const a = R() * Math.PI * 2, d = Math.sqrt(R()) * TOWN.r;
    const X = TOWN.X + Math.cos(a) * d, Z = TOWN.Z + Math.sin(a) * d / 0.8;
    list.push({ X, Z, w: sizeAt(Z, 0.8 + R() * 0.5), kind: R() < 0.82 ? 'tile' : 'thatch', town: true, fire: R() < 0.18, lantern: R() < 0.22 });
  }
  list.push({ X: TOWN.X + 0.35, Z: TOWN.Z + 0.5, w: sizeAt(TOWN.Z, 2.6), kind: 'tile', temple: true, fire: true });
  // far to near
  list.sort((a, b) => b.Z - a.Z);
  const { w: W, h: H, idx } = L;
  for (const b of list) {
    const x0 = Math.round(cx + f * b.X / b.Z), y0 = Math.round(yh + f * (1 - height(b.X, b.Z)) / b.Z);
    if (x0 < -20 || x0 > W + 20 || y0 < 0 || y0 >= H) continue;
    // hidden behind something nearer (a fold of the range)? test the ground under the house
    const gi = y0 * W + clamp(x0, 0, W - 1);
    if (Zb[gi] < b.Z * 0.92) continue;
    const hz8 = hazeOf(b.Z);
    for (const [dx, dy, mat, sun] of houseSprite(b.w, b.kind)) {
      const x = x0 + dx, y = y0 + dy;
      if (x < 0 || y < 0 || x >= W || y >= H) continue;
      const i = y * W + x;
      if (Zb[i] < b.Z * 0.9) continue;
      idx[i] = I(mat, sun, 3, hz8);
      Xb[i] = b.X; Zb[i] = b.Z;
    }
    // lights: windows under the eaves, gate lanterns, the fire at the gate
    const wallY = y0 - 1;
    const nWin = b.temple ? 3 : b.headman ? 4 : b.w >= 5 ? 2 : 1;
    for (let k = 0; k < nWin; k++) {
      const dx = Math.round((k + 0.5) / nWin * b.w - b.w / 2);
      lights.push({ x: x0 + dx, y: wallY, X: b.X, Z: b.Z, kind: 'window', far: b.Z > 18 });
    }
    if (b.lantern) lights.push({ x: x0 + Math.round(b.w / 2) + 1, y: y0 - 1, X: b.X, Z: b.Z, kind: 'lantern' });
    if (b.fire) lights.push({ x: x0 - Math.round(b.w / 2) - 1, y: y0, X: b.X, Z: b.Z, kind: b.headman || b.temple ? 'bonfire' : 'fire' });
  }
  L.used = null;
  return lights;
}

// Obon lanterns along the roads, every `step` units, on the plain only
export function roadLanterns(cam, Zb, W, H) {
  const { cx, yh, f, height } = cam, out = [];
  for (const r of ROADS) {
    if (!r.lanterns) continue;
    let acc = 0;
    for (let i = 0; i < r.pts.length - 1; i++) {
      const [ax, az] = r.pts[i], [bx, bz] = r.pts[i + 1], len = Math.hypot(bx - ax, bz - az);
      for (let d = acc; d < len; d += r.lanterns) {
        const X = ax + (bx - ax) * d / len, Z = az + (bz - az) * d / len;
        const x = Math.round(cx + f * X / Z), y = Math.round(yh + f * (1 - height(X, Z)) / Z) - 1;
        if (x < 0 || x >= W || y < 0 || y >= H) continue;
        if (Zb[(y + 1) * W + x] < Z * 0.9) continue;
        out.push({ x, y, X, Z, kind: 'lantern', road: r.main ? 0 : 1 });
      }
      acc = (acc - len) % r.lanterns; if (acc < 0) acc += r.lanterns;
    }
  }
  return out;
}
