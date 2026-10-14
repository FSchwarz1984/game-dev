// Lights: one or two crisp pixels for the source plus a pre-blurred, stepped additive glow, so the
// frame looks finished without any external bloom. Colours are kept warm for this shore and
// pale jade for the sky shore.

import { clamp, lerp, mix3, glowSprite, css } from './util.js';

export const COL = {
  window: [255, 196, 122],
  windowDim: [226, 150, 92],
  lantern: [255, 152, 88],
  fire: [255, 206, 136],
  fireHot: [255, 238, 196],
  ember: [196, 72, 40],
  star: [206, 216, 255],
  jade: [196, 246, 226],
  jadeCore: [236, 255, 248],
  jadeDeep: [120, 210, 190],
  red: [255, 66, 48],
  firefly: [214, 255, 150],
};

const coreCache = new Map();
export const cssOf = (c, a = 1) => {
  const k = c.join(',') + '|' + a.toFixed(2);
  let s = coreCache.get(k);
  if (!s) { s = css(c, a); coreCache.set(k, s); }
  return s;
};

// draw one glow centred on (x, y) (integer pixel centre), additive
export function glow(g, x, y, r, rgb, a) {
  if (a <= 0.01) return;
  const spr = glowSprite(r, rgb.map(v => Math.round(v)), 6, 1.7);
  const prev = g.globalAlpha, op = g.globalCompositeOperation;
  g.globalAlpha = clamp(a, 0, 1);
  if (op !== 'source-atop') g.globalCompositeOperation = 'lighter';
  g.drawImage(spr, Math.round(x) - r, Math.round(y) - r);
  g.globalAlpha = prev; g.globalCompositeOperation = op;
}

export function px(g, x, y, rgb, a = 1, w = 1, h = 1) {
  if (a <= 0.01) return;
  g.fillStyle = cssOf(rgb, Math.round(clamp(a, 0, 1) * 20) / 20);
  g.fillRect(Math.round(x), Math.round(y), w, h);
}

// colour along a rising light's path: our amber turning to their pale jade as it arrives
export function riseColor(base, s) {
  const k = clamp((s - 0.55) / 0.4, 0, 1);
  return mix3(base, COL.jade, k * k * (3 - 2 * k));
}
