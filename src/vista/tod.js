// Time of day for the vistas: light, sky and grade, keyed by hour. The light and grade columns are
// v0.1's TOD table (legacy/v0.1/src/render.js) so the vistas match the game's dusk and night; the
// sky columns are the painted gradient (v0.1 title: indigo zenith, violet band, a dusky rose
// glow on the horizon).

import { clamp, smooth, mix3, mul3, scale3, add3, lum, keyed, pack } from './util.js';

const TOD = [
  // h,   sun col,           sky (amb),         ground bounce,    mist rgb,         lift,               gain,              sat
  [12, [1.16, 1.06, .9], [.44, .54, .74], [.3, .3, .22], [.8, .84, .88], [.02, .02, .025], [1.02, 1.01, 1.0], 1.0],
  [16, [1.16, .97, .72], [.46, .52, .7], [.3, .26, .2], [.84, .78, .72], [.025, .02, .02], [1.04, 1.0, .95], 1.0],
  [17.8, [1.3, .8, .48], [.56, .48, .56], [.32, .22, .19], [.92, .7, .58], [.04, .02, .03], [1.07, .97, .9], .97],
  [18.9, [.6, .38, .5], [.34, .29, .46], [.13, .1, .15], [.5, .36, .5], [.04, .02, .06], [.98, .94, 1.04], .84],
  [20, [.36, .45, .74], [.21, .26, .44], [.06, .07, .12], [.16, .2, .32], [.02, .025, .05], [.9, .95, 1.08], .64],
  [24, [.36, .45, .74], [.21, .26, .44], [.06, .07, .12], [.16, .2, .32], [.02, .025, .05], [.9, .95, 1.08], .62],
];

// The painted sky, top to horizon, 0..255. glow: the sunset side (west = right when facing south).
const SKY = [
  //  h,    zenith,          upper,            lower,            horizon,          glow (west),      glow amount, star alpha
  [17.0, [92, 124, 170], [140, 160, 186], [204, 192, 170], [232, 206, 164], [255, 222, 168], .7, 0],
  [17.8, [80, 104, 156], [132, 136, 170], [212, 168, 146], [240, 186, 132], [255, 198, 128], .85, 0],
  [18.5, [58, 70, 122], [108, 100, 144], [190, 128, 124], [230, 150, 110], [255, 172, 112], .8, .05],
  [19.1, [34, 42, 86], [72, 64, 112], [128, 82, 108], [178, 104, 98], [214, 120, 96], .45, .35],
  [19.7, [18, 23, 54], [38, 40, 82], [70, 52, 88], [118, 70, 82], [138, 78, 82], .18, .8],
  [20.4, [11, 15, 38], [27, 33, 70], [58, 44, 78], [104, 62, 70], [104, 62, 70], 0, 1],
  [24, [10, 13, 34], [24, 30, 64], [54, 42, 76], [98, 60, 70], [98, 60, 70], 0, 1],
];

export function todEnv(tod) {
  const L = i => keyed(TOD, tod, i);
  const S = i => keyed(SKY, tod, i);
  const night = smooth(18.9, 20.2, tod);
  const warm = clamp(1 - Math.abs(tod - 17.9) / 1.3, 0, 1);
  const env = {
    tod, night, warm,
    sun: L(1), amb: L(2), bounce: L(3), mist: L(4),
    lift: L(5), gain: L(6), sat: L(7),
    shT: [-.012 - .012 * night, -.004, .024 + .022 * night],
    hiT: [.024 * warm + .006, .012 * warm, -.01 * warm],
    sky: [S(1), S(2), S(3), S(4)], glow: S(5), glowAmt: S(6), stars: S(7),
  };
  return env;
}

// v0.1's composite grade, applied once when palettes are built (no per-frame post)
export function grade(c, env) {
  // c in 0..1
  let r = c[0], g = c[1], b = c[2];
  const tone = v => { const e = Math.max(v - .82, 0); return Math.min(v, .82) + .18 * (1 - Math.exp(-e / .18)); };
  r = tone(r); g = tone(g); b = tone(b);
  const l = r * .299 + g * .587 + b * .114;
  r = l + (r - l) * env.sat; g = l + (g - l) * env.sat; b = l + (b - l) * env.sat;
  const { lift, gain } = env;
  r = lift[0] + r * (gain[0] - lift[0]); g = lift[1] + g * (gain[1] - lift[1]); b = lift[2] + b * (gain[2] - lift[2]);
  const l2 = r * .299 + g * .587 + b * .114;
  const s = 1 - smooth(0, .5, l2), h = smooth(.45, 1, l2);
  r += env.shT[0] * s + env.hiT[0] * h; g += env.shT[1] * s + env.hiT[1] * h; b += env.shT[2] * s + env.hiT[2] * h;
  return [clamp(r, 0, 1) * 255, clamp(g, 0, 1) * 255, clamp(b, 0, 1) * 255];
}

// The sky colour at elevation e (0 = horizon, 1 = top of the painted sky) and horizontal position u
// (0 = left/east, 1 = right/west), 0..255.
export function skyAt(env, e, u = .5) {
  const [z, up, lo, ho] = env.sky;
  e = clamp(e, 0, 1);
  let c;
  if (e < .16) c = mix3(ho, lo, smooth(0, .16, e));
  else if (e < .5) c = mix3(lo, up, smooth(.16, .5, e));
  else c = mix3(up, z, smooth(.5, 1, e));
  // the sunset side: warmer and brighter low on the right
  const gw = env.glowAmt * Math.pow(clamp(u, 0, 1), 2.2) * Math.pow(1 - clamp(e / .55, 0, 1), 1.6);
  if (gw > 0) c = mix3(c, env.glow, clamp(gw, 0, 1) * .85);
  return c;
}

// ---------------------------------------------------------------- materials and palettes

// Sun-level and sky-level lookup (index bits -> light amounts)
export const SUNLV = [0, .1, .22, .36, .5, .66, .83, 1];
export const SKYLV = [.42, .62, .82, 1];
export const HAZELV = [0, .12, .24, .37, .5, .63, .77, .9];

// A material: albedo (0..1), optional { gloss, emit, water, rim, haze }.
//   water: colour is the reflected sky (sun bits = reflection band 0..7, see waterBand)
//   rim: colour is the sky light catching an edge (sun bits = strength)
export function shade(mat, i, env, hazeCol) {
  const s = (i >> 5) & 7, k = (i >> 3) & 3, h = i & 7;
  let c;
  if (mat.water) {
    // reflected sky: band 0 = just under the horizon (reflects the horizon glow) .. 7 = high sky
    const e = Math.pow(s / 7, 1.3) * .9;
    const sky = skyAt(env, e, mat.u ?? .5);
    c = add3(scale3(sky, (mat.refl ?? .62) / 255), scale3(mat.albedo, .08 + .1 * env.amb[1]));
    if (k < 3) c = scale3(c, .6 + k * .13); // shadowed / ruffled water reads darker
  } else if (mat.rim) {
    const sky = scale3(skyAt(env, .35, .5), 1 / 255);
    const base = mul3(mat.albedo, add3(scale3(env.amb, .6), scale3(env.sun, .15)));
    const rimCol = add3(add3(scale3(mul3(sky, [1.05, 1.1, 1.2]), 1 - (mat.warmRim ?? 0) * (1 - env.night) * .6), scale3(env.sun, (.25 + (mat.warmRim ?? 0) * .5) * (1 - env.night))), scale3(env.sun, .75 * env.night));
    c = mix3(base, rimCol, (mat.rimK ?? .55) * (s + 1) / 8);
  } else {
    const direct = SUNLV[s], skyv = SKYLV[k];
    const light = add3(add3(scale3(env.amb, skyv * (mat.ambK ?? 1)), scale3(env.sun, direct * (mat.sunK ?? 1))), scale3(env.bounce, (1 - skyv) * .6));
    c = mul3(mat.albedo, light);
    if (mat.gloss && s >= 6) c = add3(c, scale3(add3(env.sun, env.amb), mat.gloss * .25));
    if (mat.emit) c = add3(c, mat.emit);
  }
  if (h) c = mix3(c, hazeCol, HAZELV[h] * (mat.hazeK ?? 1));
  return c;
}

// palette function for an IndexLayer: index -> packed graded colour
export function palette(mats, env, opts = {}) {
  const haze = opts.haze || scale3(skyAt(env, .04, .5), 1 / 255);
  const cache = new Map();
  return i => {
    let v = cache.get(i);
    if (v !== undefined) return v;
    const mat = mats[i >> 8];
    if (!mat) { cache.set(i, 0); return 0; }
    let c;
    if (opts.far && !mat.noFar && !mat.fixed) c = ghost(mat, i);
    else {
      c = mat.fixed ? scale3(mat.fixed, 1 / 255) : shade(mat, i, env, mat.hazeCol || haze);
      c = mat.fixed ? scale3(c, 255) : grade(c, env);
    }
    v = pack(c, 255);
    cache.set(i, v);
    return v;
  };
}

// The look of a thing gone "far" (the wave of distance): everything is still there, fields, roads
// and roofs keep their own lightness, but drained of colour, lifted and blue-grey, lit by nothing in
// particular, as if seen across a great distance. 0..255.
const GHOST_HAZE = [0.6, 0.66, 0.78];
export function ghost(mat, i) {
  const s = (i >> 5) & 7, k = (i >> 3) & 3, h = i & 7;
  let c;
  if (mat.water) c = scale3([0.6, 0.66, 0.76], 0.62 + (mat.refl ?? 0.6) * 0.4);   // the light of a sky that is not there
  else if (mat.rim) c = scale3(mat.albedo, 1.2);
  else c = scale3(mat.albedo, 0.66 + 0.42 * SUNLV[s] + 0.12 * SKYLV[k]);
  const l = clamp(lum(c), 0, 1), L2 = 0.24 + 0.58 * Math.pow(l, 0.85);
  let out = mix3([L2 * 0.86, L2 * 0.92, L2 * 1.07], c, 0.1);
  if (h) out = mix3(out, GHOST_HAZE, HAZELV[h] * 0.6);
  return scale3(out, 255);
}

// water reflection band for a screen row dy pixels under the horizon, sky height S pixels
export const waterBand = (dy, S) => clamp(Math.round(Math.pow(clamp(dy / (S * .9), 0, 1), 1 / 1.3) * 7), 0, 7);
