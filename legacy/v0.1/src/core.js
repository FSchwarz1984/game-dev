/* =====================================================================
   CORE — math, deterministic randomness, noise, small helpers.
   Everything else in the game is built on these; keep them pure.
   ===================================================================== */
"use strict";
const TAU = Math.PI * 2;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const ilerp = (a, b, v) => (v - a) / (b - a);
const sstep = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const fract = v => v - Math.floor(v);
const hyp = Math.hypot;
const sign = v => (v < 0 ? -1 : v > 0 ? 1 : 0);
const approach = (v, t, d) => (v < t ? Math.min(t, v + d) : Math.max(t, v - d));
const damp = (a, b, k, dt) => lerp(a, b, 1 - Math.exp(-k * dt));
const angDiff = (a, b) => { let d = (b - a) % TAU; if (d > Math.PI) d -= TAU; if (d < -Math.PI) d += TAU; return d; };
const easeInOut = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = t => 1 - Math.pow(1 - t, 3);
const easeIn = t => t * t * t;
const IS_TOUCH = (() => { try { return matchMedia("(pointer:coarse)").matches || ("ontouchstart" in window); } catch (e) { return false; } })();
const NOW = () => performance.now() / 1000;

/* ---------- hashing / RNG ---------- */
function hash2(x, y, s = 0) {
  let h = (x | 0) * 374761393 + (y | 0) * 668265263 + (s | 0) * 2147483647;
  h = (h ^ (h >>> 13)) * 1274126177; h ^= h >>> 16; return (h >>> 0) / 4294967296;
}
function hash1(n) { return hash2(n, n * 7 + 3, 11); }
function RNG(seed) {
  let a = seed >>> 0;
  const f = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  f.range = (lo, hi) => lo + (hi - lo) * f();
  f.int = (lo, hi) => Math.floor(lo + (hi - lo + 1) * f());
  f.pick = arr => arr[Math.floor(f() * arr.length)];
  f.chance = p => f() < p;
  f.sign = () => (f() < .5 ? -1 : 1);
  f.gauss = () => (f() + f() + f() - 1.5) / 1.5;
  return f;
}

/* ---------- value noise / fbm (CPU side; GPU has its own copies) ---------- */
function vnoise(x, y, s = 0) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return lerp(lerp(a, b, u), lerp(c, d, u), v);
}
function fbm(x, y, o = 4, s = 0) {
  let t = 0, a = .5, f = 1, n = 0;
  for (let i = 0; i < o; i++) { t += a * vnoise(x * f, y * f, s + i * 17); n += a; a *= .5; f *= 2.03; }
  return t / n;
}
// ridged noise for rock strata and mountain crests
function ridge(x, y, o = 4, s = 0) {
  let t = 0, a = .5, f = 1, n = 0;
  for (let i = 0; i < o; i++) { t += a * (1 - Math.abs(vnoise(x * f, y * f, s + i * 31) * 2 - 1)); n += a; a *= .5; f *= 2.1; }
  return t / n;
}
// domain-warped fbm — the organic look used for moss, ground cover and mist
function warp(x, y, o = 4, s = 0, k = 1.2) {
  const qx = fbm(x + 3.1, y + 7.7, 3, s + 5), qy = fbm(x - 5.3, y + 1.9, 3, s + 9);
  return fbm(x + qx * k * 4, y + qy * k * 4, o, s);
}

/* ---------- colour ---------- */
function hexRGB(h) { if (typeof h !== "string") return h; const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function rgbHex(c) { return "#" + c.map(v => clamp(Math.round(v), 0, 255).toString(16).padStart(2, "0")).join(""); }
function mixRGB(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; }
function rgb01(h) { const c = hexRGB(h); return [c[0] / 255, c[1] / 255, c[2] / 255]; }
function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); let h = 0, s = 0; const l = (mx + mn) / 2;
  if (mx !== mn) { const d = mx - mn; s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
    h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6; }
  return [h, s, l];
}
function hslToRgb(h, s, l) {
  h = ((h % 1) + 1) % 1; if (s === 0) return [l * 255, l * 255, l * 255];
  const q = l < .5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = t => { t = ((t % 1) + 1) % 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < .5) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p; };
  return [f(h + 1 / 3) * 255, f(h) * 255, f(h - 1 / 3) * 255];
}
// a hue-shifted ramp: shadows drift toward cool violet-blue, highlights toward warm yellow.
// This is what keeps procedural pixel art from looking like "texture times light".
function ramp(base, n = 5, o = {}) {
  const c = hexRGB(base); const [h, s, l] = rgbToHsl(c[0], c[1], c[2]);
  const out = []; const lo = o.lo ?? .42, hi = o.hi ?? .38, hs = o.hueShift ?? .055, ss = o.satShift ?? .1;
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? .5 : i / (n - 1); const k = t - .5;
    // toward shadow: hue rotates toward ~0.66 (blue-violet); toward light: toward ~0.14 (warm yellow)
    const targetH = k < 0 ? .68 : .13; const dh = angDiff(h * TAU, targetH * TAU) / TAU;
    const hh = h + dh * Math.abs(k) * 2 * hs * 4;
    const ll = clamp(l + (k < 0 ? k * 2 * lo * l : k * 2 * hi * (1 - l)), 0, 1);
    const sat = clamp(s + (k < 0 ? Math.abs(k) * ss : -Math.abs(k) * ss * .8), 0, 1);
    out.push(hslToRgb(hh, sat, ll));
  }
  return out;
}

/* ---------- misc ---------- */
const later = []; // small timer list driven by the game loop: {t, fn}
function after(sec, fn) { later.push({ t: sec, fn }); }
function tickLater(dt) { for (let i = later.length - 1; i >= 0; i--) { const L = later[i]; L.t -= dt; if (L.t <= 0) { later.splice(i, 1); try { L.fn(); } catch (e) { console.error(e); } } } }
const ZH_NUM = ["〇", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
// kanji numerals the way she counts them out loud: 九十九, 四十二, 十七
function kanjiNum(n) {
  n = n | 0; if (n < 10) return ZH_NUM[n];
  if (n < 100) { const t = Math.floor(n / 10), o = n % 10; return (t > 1 ? ZH_NUM[t] : "") + "十" + (o ? ZH_NUM[o] : ""); }
  return String(n);
}
function shuffle(a, r = Math.random) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function store(key, val) { try { if (val === undefined) return JSON.parse(localStorage.getItem(key)); localStorage.setItem(key, JSON.stringify(val)); } catch (e) { return null; } }
const QS = (() => { const o = {}; try { new URLSearchParams(location.search).forEach((v, k) => o[k] = v); } catch (e) { } return o; })();
