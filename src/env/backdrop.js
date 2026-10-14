/* =====================================================================
   env/backdrop — the far layer seen where nothing is painted (beyond
   the north-east ridge): layered ridges toward the summit (NNE), the
   rusted 「隔」 iron tower on the summit (its red light blinks at night;
   the renderer draws the light at layer.red), and the kiln smoke rising
   in the east. Colours here are greys with a depth in alpha (1 near …
   0.1 far); the renderer tints them with the time of day's sky and haze,
   so one painting serves morning, noon, dusk and night.
   Parallax: the layer scrolls at `par` of the camera speed.
   ===================================================================== */
import { RNG, clamp, lerp, fbm, hash2, hyp } from './core.js';

export function paintBackdrop(o = {}) {
  const W = 1600, H = 480, d = new Uint8Array(W * H * 4);
  const put = (x, y, g, a) => { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const k = (y * W + x) * 4; d[k] = g[0]; d[k + 1] = g[1]; d[k + 2] = g[2]; d[k + 3] = Math.round(clamp(a, 0, 1) * 255); };
  const R = RNG(17);
  // ridge layers from far to near: [base y, amplitude, grey, depth, roughness]
  const tx = 900, tBase = 318; // the tower stands on the summit here
  const layers = [
    [262, 46, [190, 198, 214], 0.12, 2.2, 11],
    [300, 40, [150, 160, 180], 0.26, 3.0, 23],
    [318, 30, [112, 122, 140], 0.46, 4.2, 37],   // the summit range
    [372, 24, [74, 86, 92], 0.7, 6.5, 41],
    [420, 18, [44, 54, 52], 0.9, 9, 53],
  ];
  const tops = [];
  layers.forEach(([by, amp, g, dep, rough, seed], li) => {
    const top = new Float32Array(W);
    for (let x = 0; x < W; x++) {
      let y = by - (fbm(x / W * rough, seed * 0.1, 4, seed) - 0.45) * amp * 2;
      if (li === 2) y -= Math.exp(-Math.pow((x - tx) / 120, 2)) * 64 - Math.exp(-Math.pow((x - tx - 150) / 90, 2)) * 10; // the summit
      if (li >= 3) y += Math.sin(x * 0.05 + seed) * 2 + (hash2(x >> 2, li, seed) - 0.5) * (li - 2) * 3; // forest tops get ragged
      top[x] = y;
    }
    tops.push(top);
    for (let x = 0; x < W; x++) for (let y = Math.max(0, Math.floor(top[x])); y < H; y++) {
      const k = (y - top[x]) / 60; const shade = clamp(1 - k * 0.25, 0.7, 1) * (li >= 3 && hash2(x >> 1, y >> 1, li) < 0.1 ? 0.9 : 1);
      put(x, y, g.map(v => v * shade), dep + (1 - dep) * clamp(k * 0.1, 0, 0.2));
    }
  });
  // the summit's iron tower: a lattice pylon, rusted, with a beacon at the top
  const towerH = 54, ty0 = Math.floor(tops[2][tx]) + 2;
  for (let y = ty0 - towerH; y <= ty0; y++) {
    const k = (ty0 - y) / towerH, hw = lerp(9, 1.2, Math.pow(k, 0.8));
    const g = [58, 46, 44];
    put(tx - hw, y, g, 0.62); put(tx + hw, y, g, 0.62);
    if (((ty0 - y) % 7) === 0) for (let x = Math.round(tx - hw); x <= tx + hw; x++) put(x, y, g, 0.62);
    if (((ty0 - y) % 7) < 7) { const f = ((ty0 - y) % 7) / 7; put(lerp(tx - hw, tx + hw, f), y, g, 0.6); put(lerp(tx + hw, tx - hw, f), y, g, 0.6); }
  }
  for (let x = tx - 6; x <= tx + 6; x++) put(x, ty0 - towerH + 8, [58, 46, 44], 0.62); // a crossarm
  const red = { x: tx, y: ty0 - towerH - 1 };
  // the kiln smoke in the east: a soft column bending downwind
  for (let y = 360; y > 120; y--) {
    const k = (360 - y) / 240; const cx = 1290 - k * k * 90 + Math.sin(k * 7) * 6, hw = 3 + k * 16;
    for (let x = Math.floor(cx - hw); x <= cx + hw; x++) {
      const u = (x - cx) / hw; const den = (1 - u * u) * (1 - k * 0.75) * (0.7 + 0.3 * fbm(x * 0.05, y * 0.04, 3, 61));
      if (den < 0.25) continue; const kk = (y * W + x) * 4; if (d[kk + 3] && d[kk + 3] / 255 > 0.3) continue;
      put(x, y, [214, 212, 208].map(v => v * (0.85 + 0.15 * (u < 0 ? 1 : 0.6))), 0.22 + den * 0.1);
    }
  }
  // a few high clouds
  for (let c = 0; c < 6; c++) { const cx = R.range(0, W), cy = R.range(40, 160), w = R.range(60, 160);
    for (let y = Math.floor(cy - 6); y <= cy + 6; y++) for (let x = Math.floor(cx - w); x <= cx + w; x++) { const u = (x - cx) / w, v = (y - cy) / 6; if (u * u + v * v * (1 + fbm(x * 0.02, y * 0.1, 2, c) * 2) > 1) continue; const kk = (y * W + x) * 4; if (d[kk + 3]) continue; put(x, y, [236, 238, 242].map(q => q * (v < 0 ? 1 : 0.86)), 0.05); } }
  return { w: W, h: H, data: d, red, towerBase: { x: tx, y: ty0 } };
}
