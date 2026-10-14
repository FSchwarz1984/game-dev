// Gray-box placeholder pixel art, drawn procedurally (deterministic). Not final art: it only has to
// be readable and stylised (limited palettes, hue-shifted shading) so the renderer can be judged.
//   terrainLayers(): 64x64 tileable layers at 16 px/m for the environment texture array
//   clumpAtlas():    foliage clump cards (grey-scale, tinted per instance)
//   groundAtlas():   grass tufts and flowers
//   characterSheet(): girl-like stand-in with a large conical hat, 3 facings x (stand + 2 walk frames)
//   jarSprite():     a highlightable prop sprite

import { makeCanvas } from '../render/textures.js';
import { makeRng, hash2, lerp, clamp } from '../core/math.js';

const hex = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mul = (a, k) => a.map(v => clamp(Math.round(v * k), 0, 255));

class Pix {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.canvas = makeCanvas(w, h);
    this.ctx = this.canvas.getContext('2d');
    this.img = this.ctx.createImageData(w, h);
    this.d = this.img.data;
  }
  set(x, y, c, a = 255) {
    x = Math.floor(x); y = Math.floor(y);
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const i = (y * this.w + x) * 4;
    this.d[i] = c[0]; this.d[i + 1] = c[1]; this.d[i + 2] = c[2]; this.d[i + 3] = a;
  }
  wrap(x, y, c) { this.set(((x % this.w) + this.w) % this.w, ((y % this.h) + this.h) % this.h, c); }
  alpha(x, y) { return x < 0 || y < 0 || x >= this.w || y >= this.h ? 0 : this.d[(y * this.w + x) * 4 + 3]; }
  get(x, y) { const i = (y * this.w + x) * 4; return [this.d[i], this.d[i + 1], this.d[i + 2]]; }
  rect(x, y, w, h, c) { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, c); }
  finish() { this.ctx.putImageData(this.img, 0, 0); return this.canvas; }
}

// Tileable value noise (period 64 texels).
function tnoise(x, y, cell, seed) {
  const n = 64 / cell, fx = x / cell, fy = y / cell;
  const xi = Math.floor(fx), yi = Math.floor(fy);
  const tx = fx - xi, ty = fy - yi, u = tx * tx * (3 - 2 * tx), v = ty * ty * (3 - 2 * ty);
  const h = (i, j) => hash2(((i % n) + n) % n, ((j % n) + n) % n, seed);
  return lerp(lerp(h(xi, yi), h(xi + 1, yi), u), lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v);
}
const pick = (pal, v) => pal[clamp(Math.floor(v * pal.length), 0, pal.length - 1)];

// ---------------------------------------------------------------------------------------------
// Environment layers (index order = texture array layer).

export const L = {
  GRASS: 0, MOSS: 1, PATH: 2, CLIFF: 3, EARTH: 4, PAVING: 5, SAND: 6, PLANK: 7, PLASTER: 8,
  THATCH: 9, BARK: 10, VERMILION: 11, ROCK: 12, DARKWOOD: 13, COPPER: 14, BIGBARK: 15,
  LACQUER: 16, GRANITE: 17, BAMBOO: 18,
};

function speckled(seed, pal, cells = [16, 8], weights = [0.6, 0.25], grain = 0.15) {
  const p = new Pix(64, 64);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const v = tnoise(x, y, cells[0], seed) * weights[0] + tnoise(x, y, cells[1], seed + 1) * weights[1] + hash2(x, y, seed + 2) * grain;
    p.set(x, y, pick(pal, v));
  }
  return p;
}

function grassLayer(seed, pal, tufts) {
  const p = speckled(seed, [pal[0], pal[1], pal[1], pal[2], pal[2], pal[3]]);
  const r = makeRng(seed + 9);
  for (let i = 0; i < tufts; i++) {
    const x = r.int(0, 63), y = r.int(0, 63), len = r.int(2, 3);
    p.wrap(x, y + 1, pal[0]);
    for (let k = 0; k < len; k++) p.wrap(x + (k === len - 1 && r() < 0.5 ? 1 : 0), y - k, k === len - 1 ? pal[4] : pal[3]);
  }
  return p.finish();
}

function pathLayer(seed) {
  const pal = ['#7d6347', '#8e7353', '#a08560', '#b09670'].map(hex);
  const p = speckled(seed, pal, [16, 4], [0.55, 0.3]);
  const r = makeRng(seed + 3);
  for (let i = 0; i < 26; i++) { // pebbles
    const x = r.int(0, 63), y = r.int(0, 63);
    p.wrap(x, y, hex('#c4ab84')); p.wrap(x + 1, y, hex('#b59d76')); p.wrap(x, y + 1, hex('#6a523a')); p.wrap(x + 1, y + 1, hex('#6a523a'));
  }
  return p.finish();
}

function strataLayer(seed, base, bandH) {
  const pal = base.map(hex);
  const p = new Pix(64, 64);
  const r = makeRng(seed);
  const bands = [];
  for (let y = 0; y < 64;) { const h = bandH[0] + r.int(0, bandH[1]); bands.push([y, h, r.int(0, pal.length - 2)]); y += h; }
  for (const [y0, h, tone] of bands) {
    for (let y = y0; y < Math.min(64, y0 + h); y++) for (let x = 0; x < 64; x++) {
      const n = tnoise(x, y, 8, seed + y0) * 0.5 + hash2(x, y, seed) * 0.2;
      let c = pal[clamp(tone + (n > 0.45 ? 1 : 0), 0, pal.length - 1)];
      if (y === y0) c = mul(c, 1.18);                 // lit top edge of each stone band
      if (y === y0 + h - 1) c = mul(c, 0.62);         // dark seam
      p.set(x, y, c);
    }
    for (let i = 0; i < 4; i++) { // vertical cracks
      const x = r.int(0, 63);
      for (let y = y0 + 1; y < Math.min(64, y0 + h - 1); y++) p.set(x, y, mul(pal[0], 0.6));
    }
  }
  return p.finish();
}

function earthLayer(seed) {
  const pal = ['#4f3a28', '#5f4630', '#6e5238', '#7f6143'].map(hex);
  const p = speckled(seed, pal, [8, 4], [0.5, 0.3], 0.2);
  const r = makeRng(seed + 5);
  for (let i = 0; i < 7; i++) { // roots
    let x = r.int(0, 63), y = r.int(0, 63);
    for (let k = 0; k < 10; k++) { p.wrap(x, y, hex('#3a2a1c')); x += r.int(-1, 1); y += 1; }
  }
  for (let i = 0; i < 12; i++) { const x = r.int(0, 63), y = r.int(0, 63); p.wrap(x, y, hex('#9a8a72')); p.wrap(x + 1, y, hex('#857560')); }
  return p.finish();
}

function slabLayer(seed, base, slab, offset) {
  const pal = base.map(hex);
  const p = speckled(seed, pal, [16, 4], [0.45, 0.3], 0.25);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const row = Math.floor(y / slab);
    const sx = (x + (row % 2) * offset) % slab;
    if (y % slab === 0 || sx === 0) p.set(x, y, mul(pal[0], 0.55));
    else if (y % slab === 1 || sx === 1) p.set(x, y, mul(p.get(x, y), 1.12));
  }
  return p.finish();
}

function plankLayer(seed, base, width) {
  const pal = base.map(hex);
  const p = new Pix(64, 64);
  for (let x = 0; x < 64; x++) {
    const plank = Math.floor(x / width), tone = hash2(plank, 0, seed);
    for (let y = 0; y < 64; y++) {
      const grain = tnoise(x * 4, y, 16, seed + plank) * 0.5 + hash2(x, y, seed) * 0.15;
      let c = pick(pal, tone * 0.5 + grain * 0.6);
      if (x % width === 0) c = mul(pal[0], 0.55);
      else if (x % width === 1) c = mul(c, 1.1);
      p.set(x, y, c);
    }
  }
  return p.finish();
}

function plasterLayer(seed) {
  const p = speckled(seed, ['#d6cdb8', '#e0d8c4', '#e8e1cf', '#efe9da'].map(hex), [16, 4], [0.5, 0.2], 0.3);
  return p.finish();
}

function thatchLayer(seed) {
  const pal = ['#7a6234', '#937a45', '#ab9156', '#c4a96a', '#d8c07f'].map(hex);
  const p = new Pix(64, 64);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const v = tnoise(x + y * 0.5, y * 3, 8, seed) * 0.5 + hash2(x, Math.floor(y / 2), seed) * 0.4;
    let c = pick(pal, v);
    if (y % 8 === 7) c = mul(pal[0], 0.7); // course edges
    p.set(x, y, c);
  }
  return p.finish();
}

function barkLayer(seed, base, groove) {
  const pal = base.map(hex);
  const p = new Pix(64, 64);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const v = tnoise(x * 3, y * 0.5, 8, seed) * 0.6 + tnoise(x, y, 4, seed + 1) * 0.25 + hash2(x, y, seed) * 0.15;
    let c = pick(pal, v);
    if (tnoise(x * 2, y * 0.25, 4, seed + 7) > 1 - groove) c = mul(pal[0], 0.7); // fissures
    p.set(x, y, c);
  }
  return p.finish();
}

function paintLayer(seed, base) {
  const pal = base.map(hex);
  const p = new Pix(64, 64);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const v = tnoise(x * 4, y, 16, seed) * 0.35 + 0.4 + hash2(x, y, seed) * 0.15;
    p.set(x, y, pick(pal, v));
  }
  return p.finish();
}

function rockLayer(seed) {
  const pal = ['#5d5c57', '#6f6e67', '#807e75', '#939186', '#a6a397'].map(hex);
  const p = speckled(seed, pal, [16, 8], [0.5, 0.35], 0.15);
  const r = makeRng(seed);
  for (let i = 0; i < 40; i++) p.wrap(r.int(0, 63), r.int(0, 63), hex('#4a4944'));
  for (let i = 0; i < 18; i++) { const x = r.int(0, 63), y = r.int(0, 63); p.wrap(x, y, hex('#6f8a4a')); p.wrap(x + 1, y, hex('#5d7840')); }
  return p.finish();
}

function bambooLayer(seed) {
  const pal = ['#5c7f3a', '#6f9445', '#82a851', '#9cbd63'].map(hex);
  const p = new Pix(64, 64);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    let c = pick(pal, tnoise(x * 4, y, 16, seed) * 0.6 + hash2(x, y, seed) * 0.2 + 0.15);
    if (y % 10 === 0) c = hex('#c8d08a');     // node ring
    else if (y % 10 === 1) c = mul(pal[0], 0.7);
    p.set(x, y, c);
  }
  return p.finish();
}

export function terrainLayers() {
  const layers = [];
  layers[L.GRASS] = grassLayer(11, ['#3d6a2c', '#4a7f33', '#579236', '#6aa541', '#82b74f'].map(hex), 80);
  layers[L.MOSS] = grassLayer(12, ['#36502a', '#425f30', '#4f6f36', '#61823f', '#78974c'].map(hex), 50);
  layers[L.PATH] = pathLayer(13);
  layers[L.CLIFF] = strataLayer(14, ['#5f584f', '#6f675c', '#7f776a', '#908778', '#a09685'], [5, 6]);
  layers[L.EARTH] = earthLayer(15);
  layers[L.PAVING] = slabLayer(16, ['#8a8378', '#988f82', '#a59c8d', '#b2a998'], 16, 8);
  layers[L.SAND] = speckled(17, ['#a8977a', '#b8a787', '#c5b592', '#d2c39f'].map(hex), [8, 4], [0.4, 0.3], 0.3).finish();
  layers[L.PLANK] = plankLayer(18, ['#6b4c30', '#7d5a39', '#8e6842', '#9f764b'], 8);
  layers[L.PLASTER] = plasterLayer(19);
  layers[L.THATCH] = thatchLayer(20);
  layers[L.BARK] = barkLayer(21, ['#4f4236', '#5f5042', '#6f5f4e', '#80705c'], 0.18);
  layers[L.VERMILION] = paintLayer(22, ['#b8381f', '#c84426', '#d24e2c', '#dc5a34']);
  layers[L.ROCK] = rockLayer(23);
  layers[L.DARKWOOD] = plankLayer(24, ['#3b2a1e', '#463224', '#523b2a', '#5d4431'], 8);
  layers[L.COPPER] = speckled(25, ['#3f7a68', '#4d8c78', '#5f9e88', '#76b29a'].map(hex), [8, 4], [0.4, 0.3], 0.3).finish();
  layers[L.BIGBARK] = barkLayer(26, ['#4a3a2c', '#5a4736', '#6b5641', '#7c654d', '#8c7458'], 0.24);
  layers[L.LACQUER] = paintLayer(27, ['#211c1b', '#2a2422', '#332c29']);
  layers[L.GRANITE] = speckled(28, ['#8f8b80', '#a19d91', '#b0aca0', '#bdb9ad'].map(hex), [8, 4], [0.35, 0.3], 0.35).finish();
  layers[L.BAMBOO] = bambooLayer(29);
  return layers;
}

// ---------------------------------------------------------------------------------------------
// Foliage clumps: 4 x 2 atlas of 64 px cards. Grey-scale with a hue shift (cool gaps, warm tops)
// so the per-instance tint gives each species its colour.

export const CLUMP = { ROUND_A: 0, ROUND_B: 1, ROUND_C: 2, PAD: 3, TIER: 4, BAMBOO: 5, MAPLE: 6, BUSH: 7 };
const LEAF = { edge: hex('#69737b'), gap: hex('#7e8990'), dark: hex('#a3ada5'), mid: hex('#c3c8b6'), light: hex('#dbdbc0'), top: hex('#ece9cf') };

function lobesMask(lobes, seed) {
  return (x, y) => {
    for (const [cx, cy, rx, ry = rx] of lobes) {
      const dx = (x - cx) / rx, dy = (y - cy) / ry;
      const wobble = (hash2(x, y, seed) - 0.5) * 0.18 + (tnoise(x, y, 8, seed) - 0.5) * 0.3;
      if (dx * dx + dy * dy < 1 + wobble) return true;
    }
    return false;
  };
}

function paintClump(p, ox, oy, inside, seed, { blobs = 70, blobR = [2, 3], holes = 0 } = {}) {
  const r = makeRng(seed);
  const m = new Uint8Array(64 * 64);
  for (let y = 1; y < 63; y++) for (let x = 1; x < 63; x++) if (inside(x, y) && hash2(x, y, seed + 5) >= holes) m[y * 64 + x] = 1;
  const val = new Float32Array(64 * 64); // 0 = gap
  for (let i = 0; i < blobs * 4 && blobs > 0; i++) {
    const cx = r.int(2, 61), cy = r.int(2, 61);
    if (!m[cy * 64 + cx]) continue;
    const br = r.range(blobR[0], blobR[1]);
    for (let y = -3; y <= 3; y++) for (let x = -3; x <= 3; x++) {
      if (x * x + y * y > br * br) continue;
      const k = (cy + y) * 64 + cx + x;
      if (m[k]) val[k] = Math.max(val[k], y < -br * 0.35 ? 3 : y < br * 0.3 ? 2 : 1);
    }
  }
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const k = y * 64 + x;
    if (!m[k]) continue;
    const edge = !m[k - 1] || !m[k + 1] || !m[k - 64] || !m[k + 64];
    const upper = y < 30 + (tnoise(x, y, 16, seed) - 0.5) * 20;
    let c = [LEAF.gap, LEAF.dark, LEAF.mid, upper ? LEAF.top : LEAF.light][val[k]];
    if (edge) c = !m[k - 64] && upper ? LEAF.light : LEAF.edge;
    p.set(ox + x, oy + y, c);
  }
}

export function clumpAtlas() {
  const p = new Pix(256, 128);
  const at = i => [(i % 4) * 64, Math.floor(i / 4) * 64];
  const draw = (i, inside, seed, opts) => { const [ox, oy] = at(i); paintClump(p, ox, oy, inside, seed, opts); };
  draw(CLUMP.ROUND_A, lobesMask([[32, 36, 21], [21, 25, 13], [43, 24, 13]], 1), 101);
  draw(CLUMP.ROUND_B, lobesMask([[32, 38, 22, 18], [17, 30, 12], [47, 30, 12], [32, 18, 13]], 2), 102);
  draw(CLUMP.ROUND_C, lobesMask([[32, 32, 13], [20, 36, 10], [44, 36, 10], [24, 20, 10], [40, 20, 10], [32, 46, 11]], 3), 103, { blobR: [1.5, 2.5] });
  draw(CLUMP.PAD, lobesMask([[32, 38, 29, 11], [22, 31, 12, 8], [42, 31, 13, 8]], 4), 104);
  draw(CLUMP.TIER, (x, y) => {
    const halfW = (y - 6) * 0.56 + (y % 6 < 3 ? 2 : -1) + (hash2(x, y, 5) - 0.5) * 2;
    return y > 6 && y < 58 && Math.abs(x - 32) < halfW;
  }, 105, { blobR: [1.5, 2.2] });
  draw(CLUMP.BAMBOO, (x, y) => {
    const r = makeRng(7);
    for (let i = 0; i < 26; i++) {
      const a = r.range(-2.6, -0.5), len = r.range(12, 24), sx = 32 + r.range(-8, 8), sy = 34 + r.range(-8, 12);
      const dx = x - sx, dy = y - sy, t = (dx * Math.cos(a) + dy * Math.sin(a)) / len;
      const off = Math.abs(-dx * Math.sin(a) + dy * Math.cos(a));
      if (t > 0 && t < 1 && off < 2.2 * Math.sin(t * Math.PI)) return true;
    }
    return false;
  }, 106, { blobs: 30, blobR: [1, 1.8] });
  draw(CLUMP.MAPLE, lobesMask([[32, 34, 17], [18, 28, 10], [46, 28, 10], [26, 18, 9], [40, 18, 9], [32, 48, 10]], 8), 107, { blobR: [1.5, 2.5], holes: 0.05 });
  draw(CLUMP.BUSH, lobesMask([[17, 44, 14, 12], [32, 40, 18, 16], [47, 44, 14, 12]], 9), 108);
  return p.finish();
}

// ---------------------------------------------------------------------------------------------
// Ground cover: 8 x 1 atlas of 16 px sprites (1 m at 16 px/m), pivot at the bottom row.

export const GROUND = { TUFT_A: 0, TUFT_B: 1, TUFT_C: 2, REEDS: 3, WHITE: 4, YELLOW: 5, PINK: 6, FERN: 7 };

export function groundAtlas() {
  const p = new Pix(128, 16);
  const G = ['#2f5a24', '#3f7a2c', '#559a37', '#73b548', '#94cc5e'].map(hex);
  const blade = (ox, x0, len, lean, shade) => {
    for (let k = 0; k < len; k++) p.set(ox + x0 + Math.round(lean * k / len), 15 - k, G[clamp(shade + (k > len * 0.6 ? 1 : 0), 0, 4)]);
  };
  const tuft = (i, blades, seed) => {
    const r = makeRng(seed);
    for (let b = 0; b < blades; b++) blade(i * 16, r.int(3, 12), r.int(4, 10), r.range(-3, 3), r.int(1, 3));
  };
  tuft(GROUND.TUFT_A, 9, 1);
  tuft(GROUND.TUFT_B, 12, 2);
  tuft(GROUND.TUFT_C, 6, 3);
  const r = makeRng(4);
  for (let b = 0; b < 7; b++) blade(GROUND.REEDS * 16, r.int(4, 11), r.int(10, 15), r.range(-2, 2), r.int(0, 2));
  const flowers = (i, petal, centre, seed) => {
    tuft(i, 6, seed);
    const fr = makeRng(seed + 1);
    for (let f = 0; f < 4; f++) {
      const x = i * 16 + fr.int(3, 12), y = fr.int(5, 10);
      p.set(x - 1, y, petal); p.set(x + 1, y, petal); p.set(x, y - 1, petal); p.set(x, y + 1, mul(petal, 0.8)); p.set(x, y, centre);
    }
  };
  flowers(GROUND.WHITE, hex('#f4f1e6'), hex('#e8c040'), 5);
  flowers(GROUND.YELLOW, hex('#f2cf3a'), hex('#c8781c'), 6);
  flowers(GROUND.PINK, hex('#ee8aa8'), hex('#fff0a0'), 7);
  const fx = GROUND.FERN * 16;
  for (let side = -1; side <= 1; side += 2) for (let k = 0; k < 9; k++) {
    const x = fx + 8 + side * Math.round(k * 0.6), y = 15 - k;
    p.set(x, y, G[2]);
    for (let l = 1; l <= 3 - Math.floor(k / 4); l++) p.set(x + side * l, y + (l > 1 ? 1 : 0), G[l % 2 ? 3 : 1]);
  }
  return p.finish();
}

// ---------------------------------------------------------------------------------------------
// Character stand-in: 48 x 64 frames at 40 px/m (about 1.35 m tall including the hat).
// Columns: stand, walk A, walk B. Rows: front, back, side (facing right; mirror for left).

export const SHEET = { frameW: 48, frameH: 64, cols: 3, rows: 3, footPad: 3, pxPerMetre: 40 };

const C = {
  hatHi: hex('#ecd08a'), hat: hex('#d2ad62'), hatLo: hex('#a7823f'), hatBand: hex('#8c3a2c'),
  skin: hex('#f4cba6'), skinLo: hex('#d9a27e'), eye: hex('#2a1e2c'),
  hair: hex('#3a2a44'), hairHi: hex('#56406a'),
  robe: hex('#3f6f93'), robeHi: hex('#5d93b8'), robeLo: hex('#2b4c6c'),
  collar: hex('#f1ebdc'), obi: hex('#d0583a'), obiLo: hex('#9c3a26'),
  leg: hex('#3b3036'), sandal: hex('#7a5232'),
};

function drawHat(p, ox, oy, side) {
  // Wide shallow cone; brim widest at y = 21.
  for (let y = 7; y <= 22; y++) {
    const t = (y - 7) / 15, half = Math.round(1 + t * t * 14 + t * 1.5);
    const cx = ox + 24 + (side ? Math.round(t * 2) : 0);
    for (let x = -half; x <= half; x++) {
      const weave = (x + y) % 4 === 0;
      let c = x < -half * 0.35 ? C.hatHi : x > half * 0.45 ? C.hatLo : C.hat;
      if (weave && y > 9) c = mul(c, 0.86);
      p.set(cx + x, oy + y, c);
    }
  }
  for (let x = -14; x <= 14; x++) p.set(ox + 24 + x + (side ? 2 : 0), oy + 22, C.hatLo); // brim underside
  for (let x = -5; x <= 5; x++) p.set(ox + 24 + x + (side ? 1 : 0), oy + 15, C.hatBand);
}

function drawFigure(p, ox, oy, facing, step) {
  const bob = step ? -1 : 0;
  const y0 = oy + bob;
  const side = facing === 'side';
  // Legs and sandals
  const legs = side
    ? (step === 1 ? [[20, 2], [27, -1]] : step === 2 ? [[22, -1], [26, 2]] : [[22, 0], [25, 0]])
    : (step === 1 ? [[19, 1], [26, -1]] : step === 2 ? [[19, -1], [26, 1]] : [[19, 0], [26, 0]]);
  for (const [lx, ext] of legs) {
    for (let y = 52; y < 58 + ext; y++) p.rect(ox + lx, y0 + y, 3, 1, C.leg);
    p.rect(ox + lx - (side ? 0 : 0), y0 + 58 + ext, side ? 4 : 3, 2, C.sandal);
  }
  // Robe: trapezoid, darker hem and right side
  for (let y = 32; y <= 52; y++) {
    const t = (y - 32) / 20, half = Math.round((side ? 6 : 7) + t * (side ? 3 : 3));
    const cx = ox + 24 + (side ? 0 : 0);
    for (let x = -half; x <= half; x++) {
      let c = x < -half + 3 ? C.robeHi : x > half - 3 ? C.robeLo : C.robe;
      if (y >= 51) c = C.robeLo;
      p.set(cx + x, y0 + y, c);
    }
  }
  // Obi (sash)
  for (let y = 40; y <= 43; y++) for (let x = (side ? -6 : -7); x <= (side ? 6 : 7); x++) p.set(ox + 24 + x, y0 + y, y === 43 ? C.obiLo : C.obi);
  if (facing === 'back') { // bow
    for (let y = 38; y <= 45; y++) for (let x = -4; x <= 4; x++) if (Math.abs(x) + Math.abs(y - 41.5) < 6) p.set(ox + 24 + x, y0 + y, Math.abs(x) < 2 ? C.obiLo : C.obi);
  }
  // Arms
  const swing = step === 1 ? 1 : step === 2 ? -1 : 0;
  if (side) {
    for (let y = 34; y <= 44; y++) p.rect(ox + 23 + Math.round(swing * (y - 34) / 5), y0 + y, 3, 1, C.robeLo);
    p.rect(ox + 23 + swing * 2, y0 + 45, 3, 2, C.skin);
  } else {
    for (let y = 33; y <= 44; y++) { p.rect(ox + 14, y0 + y + swing, 3, 1, C.robeHi); p.rect(ox + 31, y0 + y - swing, 3, 1, C.robeLo); }
    p.rect(ox + 14, y0 + 45 + swing, 3, 2, C.skin);
    p.rect(ox + 31, y0 + 45 - swing, 3, 2, C.skinLo);
  }
  // Collar
  if (facing === 'front') for (let k = 0; k < 4; k++) { p.set(ox + 22 + k, y0 + 32 + k, C.collar); p.set(ox + 26 - k, y0 + 32 + k, C.collar); }
  // Head: hair behind, face
  if (facing === 'back') {
    for (let y = 22; y <= 36; y++) for (let x = -6; x <= 6; x++) p.set(ox + 24 + x, y0 + y, (x + y) % 5 === 0 ? C.hairHi : C.hair);
    for (let y = 36; y <= 41; y++) p.rect(ox + 23, y0 + y, 3, 1, C.hair); // tail
  } else if (side) {
    for (let y = 22; y <= 38; y++) for (let x = -7; x <= -1; x++) p.set(ox + 24 + x, y0 + y, (x + y) % 5 === 0 ? C.hairHi : C.hair);
    for (let y = 23; y <= 31; y++) for (let x = 0; x <= 6; x++) p.set(ox + 24 + x, y0 + y, y < 25 ? C.skinLo : C.skin);
    p.set(ox + 28, y0 + 27, C.eye); p.set(ox + 28, y0 + 28, C.eye);
    p.rect(ox + 24, y0 + 23, 3, 2, C.hair);
  } else {
    for (let y = 23; y <= 37; y++) { p.rect(ox + 17, y0 + y, 2, 1, C.hair); p.rect(ox + 30, y0 + y, 2, 1, C.hair); }
    for (let y = 23; y <= 31; y++) for (let x = -5; x <= 5; x++) p.set(ox + 24 + x, y0 + y, y < 25 ? C.skinLo : C.skin);
    p.rect(ox + 19, y0 + 23, 11, 1, C.hair); // fringe
    p.rect(ox + 21, y0 + 27, 2, 2, C.eye); p.rect(ox + 26, y0 + 27, 2, 2, C.eye);
    p.set(ox + 21, y0 + 27, C.collar); p.set(ox + 26, y0 + 27, C.collar);
    p.set(ox + 24, y0 + 30, C.skinLo);
  }
  drawHat(p, ox, y0, side);
}

// One-texel selective outline: each transparent texel touching the figure takes a darkened,
// slightly purple version of its neighbour (reads on any background, softer than black).
function outline(p, ox, oy, w, h) {
  const add = [];
  for (let y = oy; y < oy + h; y++) for (let x = ox; x < ox + w; x++) {
    if (p.alpha(x, y)) continue;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy;
      if (nx < ox || ny < oy || nx >= ox + w || ny >= oy + h || !p.alpha(nx, ny)) continue;
      const c = p.get(nx, ny);
      add.push([x, y, [Math.round(c[0] * 0.32 + 18), Math.round(c[1] * 0.26 + 10), Math.round(c[2] * 0.32 + 26)]]);
      break;
    }
  }
  for (const [x, y, c] of add) p.set(x, y, c);
}

export function characterSheet() {
  const { frameW: fw, frameH: fh } = SHEET;
  const p = new Pix(fw * SHEET.cols, fh * SHEET.rows);
  ['front', 'back', 'side'].forEach((facing, row) => {
    for (let col = 0; col < 3; col++) {
      drawFigure(p, col * fw, row * fh - 1, facing, col);
      outline(p, col * fw, row * fh, fw, fh);
    }
  });
  return p.finish();
}

/** A terracotta jar, 32 x 32 at 40 px/m. */
export function jarSprite() {
  const p = new Pix(32, 32);
  const body = hex('#b8683f'), hi = hex('#d98c5c'), lo = hex('#8a4a2c'), rope = hex('#d8c48a');
  for (let y = 9; y <= 28; y++) {
    const t = (y - 9) / 19, half = Math.round(4 + Math.sin(t * Math.PI * 0.95) * 6);
    for (let x = -half; x <= half; x++) p.set(16 + x, y, x < -half * 0.4 ? hi : x > half * 0.5 ? lo : body);
  }
  p.rect(12, 7, 9, 2, lo);
  p.rect(13, 6, 7, 1, hi);
  p.rect(11, 12, 11, 1, rope);
  outline(p, 0, 0, 32, 32);
  return p.finish();
}
