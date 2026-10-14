/* =====================================================================
   gfx/tod — time of day → light, sky, mist and grade. Keys are hours.
   Ported from legacy/v0.1/src/render.js (TOD, todEnv) — the table that
   gave v0.1 its long blue dawn, white noon, honey-gold hour, violet
   dusk and moonlit indigo night — and extended with the segment-1 keys:
   dusk 17:30 → night 21:00 (the prologue walk) and a misty 07:00.
   The sun keeps the art direction's top-left: shadows always fall to
   the lower right; only their length, colour and the ambient change.
   ===================================================================== */

const K = [
  // h,   sun col,            sky (ambient),     ground bounce,      mist rgb,          mist, lift,                 gain,               sat,  cloud, shafts, elev°
  [0,     [0.44, 0.54, 0.84], [0.25, 0.3, 0.5], [0.07, 0.08, 0.13], [0.16, 0.2, 0.33], 0.16, [0.03, 0.035, 0.065], [0.98, 1.02, 1.14], 0.66, 0.3, 0, 48],
  [4.2,   [0.42, 0.5, 0.8], [0.26, 0.3, 0.5], [0.08, 0.08, 0.13], [0.24, 0.26, 0.4], 0.3, [0.035, 0.035, 0.065], [0.98, 1.0, 1.1], 0.68, 0.3, 0, 40],
  [5.2,   [0.78, 0.56, 0.58], [0.42, 0.4, 0.56], [0.16, 0.13, 0.17], [0.62, 0.56, 0.66], 0.55, [0.04, 0.03, 0.06], [1.0, 0.97, 1.0], 0.8, 0.35, 0.35, 14],
  [6.2,   [1.22, 0.86, 0.6], [0.54, 0.52, 0.64], [0.28, 0.23, 0.2], [0.9, 0.8, 0.74], 0.48, [0.03, 0.02, 0.04], [1.04, 1.0, 0.96], 0.94, 0.3, 1.0, 20],
  [7.0,   [1.08, 0.92, 0.74], [0.48, 0.53, 0.68], [0.27, 0.25, 0.22], [0.76, 0.78, 0.82], 0.24, [0.03, 0.025, 0.035], [1.02, 1.01, 0.99], 0.9, 0.35, 0.42, 26],
  [8.5,   [1.12, 0.99, 0.8], [0.46, 0.53, 0.7], [0.28, 0.27, 0.21], [0.8, 0.82, 0.84], 0.16, [0.02, 0.02, 0.03], [1.02, 1.01, 0.99], 1.0, 0.4, 0.5, 40],
  [12,    [1.16, 1.06, 0.9], [0.44, 0.54, 0.74], [0.3, 0.3, 0.22], [0.8, 0.84, 0.88], 0.08, [0.02, 0.02, 0.025], [1.02, 1.01, 1.0], 1.0, 0.5, 0.1, 60],
  [16,    [1.12, 0.96, 0.74], [0.46, 0.52, 0.7], [0.3, 0.26, 0.2], [0.8, 0.76, 0.72], 0.07, [0.025, 0.02, 0.02], [1.03, 1.0, 0.96], 1.0, 0.45, 0.35, 40],
  [17.5,  [1.16, 0.78, 0.5], [0.5, 0.45, 0.55], [0.3, 0.22, 0.19], [0.78, 0.6, 0.52], 0.14, [0.035, 0.02, 0.03], [1.04, 0.97, 0.92], 0.96, 0.4, 0.8, 26],
  [18.3,  [1.0, 0.56, 0.42], [0.42, 0.34, 0.46], [0.22, 0.15, 0.15], [0.62, 0.45, 0.5], 0.2, [0.04, 0.02, 0.04], [1.02, 0.95, 0.96], 0.9, 0.4, 0.6, 22],
  [19.1,  [0.55, 0.36, 0.5], [0.3, 0.27, 0.45], [0.11, 0.09, 0.14], [0.42, 0.33, 0.5], 0.3, [0.04, 0.02, 0.06], [0.97, 0.93, 1.04], 0.82, 0.35, 0.15, 30],
  [20,    [0.46, 0.55, 0.86], [0.27, 0.31, 0.52], [0.08, 0.09, 0.14], [0.2, 0.24, 0.38], 0.2, [0.03, 0.035, 0.065], [0.98, 1.02, 1.14], 0.68, 0.3, 0, 45],
  [21,    [0.44, 0.54, 0.84], [0.25, 0.3, 0.5], [0.07, 0.08, 0.13], [0.16, 0.2, 0.33], 0.17, [0.03, 0.035, 0.065], [0.98, 1.02, 1.14], 0.66, 0.3, 0, 48],
  [24,    [0.44, 0.54, 0.84], [0.25, 0.3, 0.5], [0.07, 0.08, 0.13], [0.16, 0.2, 0.33], 0.16, [0.03, 0.035, 0.065], [0.98, 1.02, 1.14], 0.66, 0.3, 0, 48],
];

const sstep = (a, b, v) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
const mixA = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
const norm = v => { const l = Math.hypot(...v); return v.map(x => x / l); };

export const PRESETS = { morning: 7.0, noon: 12.5, dusk: 17.6, evening: 18.4, night: 21.0, dawn: 5.6 };

/** hours → environment for the renderer. w: {mist, rain, wind:[x,y,strength], overcast} */
export function todEnv(hour, w = {}) {
  let tod = ((hour % 24) + 24) % 24;
  let a = K[0], b = K[1];
  for (let i = 0; i < K.length - 1; i++) if (tod >= K[i][0] && tod <= K[i + 1][0]) { a = K[i]; b = K[i + 1]; break; }
  const t = sstep(0, 1, (tod - a[0]) / Math.max(1e-3, b[0] - a[0]));
  const L = i => Array.isArray(a[i]) ? mixA(a[i], b[i], t) : lerp(a[i], b[i], t);
  const nightK = tod < 5.3 || tod > 19.4 ? 1 : tod < 6 ? (6 - tod) / 0.7 : tod > 18.7 ? (tod - 18.7) / 0.7 : 0;
  const warm = Math.max(0, 1 - Math.abs(tod - 6.3) / 1.3) + Math.max(0, 1 - Math.abs(tod - 17.8) / 1.4);
  const overcast = w.overcast || 0;
  const elev = L(11) * Math.PI / 180;
  // the sun (or moon) always from the upper left: west-north-west, so shadows fall to the lower right
  const sunDir = norm([-0.8 * Math.cos(elev), -0.6 * Math.cos(elev), Math.sin(elev)]);
  const sun = L(1).map(v => v * (1 - overcast * 0.6)), sky = L(2).map(v => v * (1 + overcast * 0.15)), gnd = L(3);
  const mistA = Math.min(0.9, L(5) + (w.mist || 0));
  const skyTop = nightK > 0.5 ? [0.04, 0.06, 0.13] : mixA(sky, [0.36, 0.52, 0.78], 0.55);
  const skyHor = nightK > 0.5 ? [0.1, 0.12, 0.2] : mixA(L(4), [0.92, 0.9, 0.86], 0.3);
  // the Far: pale blue-grey haze; at night it stays faintly luminous so it still reads
  const farCol = nightK > 0.5 ? [0.36, 0.42, 0.58] : mixA([0.7, 0.77, 0.88], L(4), 0.15).map(v => v * (0.85 + 0.15 * L(7)[2]));
  return {
    hour: tod, sunDir, shadeDir: norm([-0.55, 0.12, 0.83]), sunCol: sun, skyCol: sky, gndCol: gnd,
    mist: [...L(4), mistA], fog: L(4), lift: L(6), gain: L(7), sat: L(8), cloud: Math.min(1, L(9) + overcast * 0.4), shafts: L(10) * (1 - overcast),
    night: nightK, warm, wind: w.wind || [1, 0.25, 0.3],
    shT: [-0.012 - 0.012 * nightK, -0.004, 0.024 + 0.022 * nightK], hiT: [0.024 * warm + 0.006, 0.012 * warm, -0.01 * warm],
    skyTop, skyHor, farCol, haze: mixA(skyHor, L(4), 0.5),
    bloomK: 0.5 + nightK * 0.3, bloomThr: 0.86 - nightK * 0.28, vig: 0.42 + nightK * 0.22, expo: 1,
    charK: [0.42 + nightK * 0.12, 0.22 + nightK * 0.18, 0.55 + nightK * 0.35, 0], // floor, fill, rim
    flecks: nightK > 0.5 ? 0 : 1,
  };
}
