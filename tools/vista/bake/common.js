// Shared helpers for the vista bake (runs in Chromium, see tools/vista/bake.mjs).
//
// The JS vista painted every static layer once as 16-bit material/shade indices and turned them into
// colours with a palette per time of day (src/vista/util.js IndexLayer). The bake keeps that split:
// each layer becomes a compact id map (0 = empty) and a look-up table, one row per time of day, made
// by the JS palette functions themselves; Godot interpolates between rows on the GPU.

import { clamp } from '../../../src/vista/util.js';

// Times of day of the LUT rows (hours). The treetop sequence runs ~17.5 .. 21.
export const TOD0 = 17.0, TOD_STEP = 0.05, TOD_ROWS = 91;      // 17.00 .. 21.50
export const todOfRow = r => +(TOD0 + r * TOD_STEP).toFixed(2);

/** Shared id space over several Uint16 index arrays: id 1..n for each distinct non-zero value. */
export class IdSpace {
  constructor() { this.idOf = new Map(); this.values = [0]; }
  add(idx) {
    for (let i = 0; i < idx.length; i++) {
      const v = idx[i];
      if (v && !this.idOf.has(v)) { this.idOf.set(v, this.values.length); this.values.push(v); }
    }
    return this;
  }
  map(idx) {
    const out = new Uint16Array(idx.length);
    for (let i = 0; i < idx.length; i++) { const v = idx[i]; if (v) out[i] = this.idOf.get(v); }
    return out;
  }
  get size() { return this.values.length; }
}

/** RGBA8 LUT: width = id count (id 0 transparent), one row per palette in `pals` (palette: value -> packed). */
export function lutRows(space, pals) {
  const w = space.size, out = new Uint8Array(w * pals.length * 4);
  pals.forEach((pal, r) => {
    for (let id = 1; id < w; id++) {
      const p = pal(space.values[id]) >>> 0, o = (r * w + id) * 4;
      out[o] = p & 255; out[o + 1] = (p >> 8) & 255; out[o + 2] = (p >> 16) & 255; out[o + 3] = p ? 255 : 0;
    }
  });
  return { w, h: pals.length, data: out };
}

/** An id map as RGBA8: R/G = id (low/high byte), B = extra byte, A = 255 where the id is set. */
export function idImage(ids, w, h, extra = null) {
  const out = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const id = ids[i];
    out[i * 4] = id & 255; out[i * 4 + 1] = id >> 8; out[i * 4 + 2] = extra ? extra[i] : 0; out[i * 4 + 3] = id ? 255 : 0;
  }
  return { w, h, data: out };
}

/** Floats as signed 16-bit fixed point (two bytes, little endian): q = round(v * scale) + 32768, so
 *  zero is exact (the cloud deck's faded rows must stay empty). */
export function fixedS16(src, scale) {
  const out = new Uint8Array(src.length * 2);
  for (let i = 0; i < src.length; i++) {
    const q = Math.round(clamp(src[i] * scale + 32768, 0, 65535));
    out[i * 2] = q & 255; out[i * 2 + 1] = q >> 8;
  }
  return out;
}

/** Floats as 16-bit fixed point (two bytes, little endian) over [lo, hi]. */
export function fixed16(src, lo, hi) {
  const out = new Uint8Array(src.length * 2), k = 65535 / (hi - lo);
  for (let i = 0; i < src.length; i++) {
    const q = Math.round(clamp((src[i] - lo) * k, 0, 65535));
    out[i * 2] = q & 255; out[i * 2 + 1] = q >> 8;
  }
  return out;
}

/** Copy rows y0..y1 of a w-wide typed array. */
export const rows = (arr, w, y0, y1) => arr.slice(y0 * w, y1 * w);

export function b64(u8) {
  const bytes = u8 instanceof Uint8Array ? u8 : new Uint8Array(u8.buffer, u8.byteOffset, u8.byteLength);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

export const unpack = p => [p & 255, (p >> 8) & 255, (p >> 16) & 255, (p >>> 24) & 255];
export const r2 = v => Math.round(v * 100) / 100;
export const r3 = v => Math.round(v * 1000) / 1000;
