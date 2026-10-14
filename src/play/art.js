// Gray-box pixel sprites for the playable arena: crew stand-ins, the onibi, fire, crop stages,
// weeds, shide paper and an ice sheet. Placeholder art (G4 replaces it), but every sprite keeps a
// one-pixel dark outline and a distinct silhouette so it reads at a glance. 40 px per metre.

import { makeCanvas } from '../render/textures.js';
import { makeRng } from '../core/math.js';

const hex = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

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
  alpha(x, y) { return x < 0 || y < 0 || x >= this.w || y >= this.h ? 0 : this.d[(y * this.w + x) * 4 + 3]; }
  rect(x, y, w, h, c) { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, c); }
  disc(cx, cy, r, c) { for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r + r * 0.6) this.set(cx + x, cy + y, c); }
  /** One-pixel outline around opaque texels inside a cell, darker and cooler than what it borders. */
  outline(ox, oy, w, h, col = [26, 18, 34]) {
    const add = [];
    for (let y = oy; y < oy + h; y++) for (let x = ox; x < ox + w; x++) {
      if (this.alpha(x, y)) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < ox || ny < oy || nx >= ox + w || ny >= oy + h || !this.alpha(nx, ny)) continue;
        add.push([x, y]); break;
      }
    }
    for (const [x, y] of add) this.set(x, y, col);
  }
  finish() { this.ctx.putImageData(this.img, 0, 0); return this.canvas; }
}

export const CELL = 32;

/** Crew stand-ins (tsukumogami placeholders): row = kind (jar, bucket, kettle), col 0 stand, 1 hop. */
export function crewSheet() {
  const p = new Pix(CELL * 2, CELL * 3);
  const eye = hex('#1a1222'), shine = hex('#fff6dc');
  const face = (ox, oy, y) => { p.rect(ox + 12, oy + y, 2, 2, eye); p.rect(ox + 18, oy + y, 2, 2, eye); p.set(ox + 12, oy + y, shine); p.set(ox + 18, oy + y, shine); };
  for (let col = 0; col < 2; col++) {
    const squash = col === 1 ? -2 : 0;
    // jar: terracotta, rope band
    {
      const ox = col * CELL, oy = 0, body = hex('#b8683f'), hi = hex('#e09a68'), lo = hex('#7e4128'), rope = hex('#e2cf94');
      for (let y = 10 + squash; y <= 29; y++) {
        const t = (y - 10 - squash) / (19 - squash), half = Math.round(4 + Math.sin(t * Math.PI * 0.95) * (6 + (col ? 1 : 0)));
        for (let x = -half; x <= half; x++) p.set(ox + 16 + x, oy + y, x < -half * 0.45 ? hi : x > half * 0.5 ? lo : body);
      }
      p.rect(ox + 12, oy + 8 + squash, 9, 2, lo); p.rect(ox + 13, oy + 7 + squash, 7, 1, hi);
      p.rect(ox + 10, oy + 13 + squash, 13, 1, rope);
      face(ox, oy, 18 + squash);
      p.outline(ox, oy, CELL, CELL);
    }
    // bucket: wooden staves, iron hoops, a rope handle
    {
      const ox = col * CELL, oy = CELL, wood = hex('#a87a46'), hi = hex('#d2a464'), lo = hex('#6e4a2a'), hoop = hex('#4a4a58');
      for (let y = 14 + squash; y <= 29; y++) {
        const half = 7 - Math.round((y - 14) * 0.12);
        for (let x = -half; x <= half; x++) p.set(ox + 16 + x, oy + y, (x + 16) % 4 === 0 ? lo : x < -half * 0.4 ? hi : wood);
      }
      p.rect(ox + 9, oy + 16 + squash, 15, 1, hoop); p.rect(ox + 10, oy + 26, 13, 1, hoop);
      for (let a = 0; a <= 12; a++) { const ang = Math.PI * a / 12; p.set(ox + 16 - Math.cos(ang) * 7, oy + 14 + squash - Math.sin(ang) * 6, hex('#d8c48a')); }
      face(ox, oy, 20 + squash);
      p.outline(ox, oy, CELL, CELL);
    }
    // kettle: iron, lid knob, spout
    {
      const ox = col * CELL, oy = CELL * 2, iron = hex('#4c4e5e'), hi = hex('#7a7e94'), lo = hex('#2c2c38');
      for (let y = 13 + squash; y <= 28; y++) {
        const t = (y - 13 - squash) / (15 - squash), half = Math.round(5 + Math.sin(t * Math.PI) * 4);
        for (let x = -half; x <= half; x++) p.set(ox + 16 + x, oy + y, x < -half * 0.4 ? hi : x > half * 0.5 ? lo : iron);
      }
      p.rect(ox + 14, oy + 10 + squash, 5, 3, hi); p.rect(ox + 15, oy + 9 + squash, 3, 1, lo);
      for (let i = 0; i < 6; i++) p.set(ox + 25 + i, oy + 21 + squash - i, iron);
      face(ox, oy, 19 + squash);
      p.outline(ox, oy, CELL, CELL);
    }
  }
  return p.finish();
}

/** The onibi: row 0 hungry (hot, red-orange, sharp), row 1 calm (pale blue, round); 4 flicker frames. */
export function onibiSheet() {
  const p = new Pix(CELL * 4, CELL * 2);
  const rows = [
    { core: '#fff2b0', mid: '#ffa040', out: '#e8402a', eye: '#2a0a0a', tall: 1.0 },
    { core: '#f4fbff', mid: '#9fd8ff', out: '#4f86d8', eye: '#162238', tall: 0.8 },
  ];
  rows.forEach((r, row) => {
    for (let f = 0; f < 4; f++) {
      const ox = f * CELL, oy = row * CELL, rng = makeRng(31 + f + row * 7);
      const base = 25, top = Math.round(base - 20 * r.tall - (f % 2));
      for (let y = top; y <= base + 3; y++) {
        const t = (y - top) / (base + 3 - top);
        const sway = Math.sin(t * 3 + f * 1.4) * (1 - t) * 2.5;
        const half = Math.max(0, Math.round(Math.sin(Math.min(1, t * 1.15) * Math.PI * 0.62) * 8 - (t > 0.92 ? (t - 0.92) * 40 : 0)));
        for (let x = -half; x <= half; x++) {
          const e = Math.abs(x) / Math.max(1, half);
          const c = e > 0.72 || t < 0.18 ? r.out : e > 0.38 || t < 0.4 ? r.mid : r.core;
          if (t < 0.25 && rng() < 0.25) continue;
          p.set(ox + 16 + x + sway, oy + y, hex(c));
        }
      }
      // eyes: angry slants when hungry, soft arcs when calm
      const ey = base - 6;
      if (row === 0) { p.rect(ox + 12, oy + ey, 2, 2, hex(r.eye)); p.rect(ox + 18, oy + ey, 2, 2, hex(r.eye)); p.set(ox + 11, oy + ey - 1, hex(r.eye)); p.set(ox + 20, oy + ey - 1, hex(r.eye)); }
      else { p.rect(ox + 12, oy + ey, 2, 1, hex(r.eye)); p.rect(ox + 18, oy + ey, 2, 1, hex(r.eye)); p.set(ox + 15, oy + ey + 3, hex(r.eye)); p.set(ox + 16, oy + ey + 3, hex(r.eye)); }
    }
  });
  return p.finish();
}

/** Brazier fire, 4 flicker frames. */
export function fireSheet() {
  const p = new Pix(CELL * 4, CELL);
  for (let f = 0; f < 4; f++) {
    const ox = f * CELL, rng = makeRng(70 + f);
    for (let tongue = 0; tongue < 3; tongue++) {
      const cx = 16 + (tongue - 1) * 5 + (rng() - 0.5) * 2, hgt = [13, 20, 12][tongue] + Math.round(rng() * 4);
      for (let y = 0; y < hgt; y++) {
        const t = y / hgt, half = Math.round((1 - t) * (tongue === 1 ? 5 : 3.5));
        const sway = Math.sin(t * 4 + f + tongue) * t * 2;
        for (let x = -half; x <= half; x++) {
          const e = Math.abs(x) / Math.max(1, half);
          p.set(ox + cx + x + sway, 31 - y, hex(e > 0.6 || t > 0.75 ? '#e2462a' : e > 0.25 || t > 0.45 ? '#ff9a36' : '#ffe9a0'));
        }
      }
    }
    if (f % 2) for (let i = 0; i < 3; i++) p.set(ox + 10 + rng() * 12, 4 + rng() * 6, hex('#ffcf6a'));
  }
  return p.finish();
}

/** Crop stages for the cucumber (0 seeded mound … 4 ripe), on a bamboo stake from stage 2. */
export function cropSheet() {
  const p = new Pix(CELL * 5, CELL);
  const soil = hex('#5e4330'), soilHi = hex('#7a5a40'), leaf = hex('#5aa83e'), leafHi = hex('#8ad05a'), leafLo = hex('#33722e');
  const stake = hex('#c8b070'), flower = hex('#ffd84a'), fruit = hex('#2f7a3a'), fruitHi = hex('#66b45a');
  const leafAt = (ox, x, y, s) => { p.disc(ox + x, y, s, leaf); p.set(ox + x - 1, y - 1, leafHi); p.set(ox + x + s - 1, y + 1, leafLo); };
  for (let st = 0; st < 5; st++) {
    const ox = st * CELL;
    for (let x = 8; x <= 24; x++) { const h = Math.round(Math.sin((x - 8) / 16 * Math.PI) * 3); for (let y = 0; y <= h; y++) p.set(ox + x, 31 - y, y === h ? soilHi : soil); }
    if (st === 0) { p.set(ox + 14, 27, hex('#e8d8a0')); p.set(ox + 18, 27, hex('#e8d8a0')); }
    if (st >= 1) { p.rect(ox + 16, 23, 1, 5, leafLo); leafAt(ox, 14, 23, 1); leafAt(ox, 18, 22, 1); }
    if (st >= 2) {
      p.rect(ox + 21, 6, 1, 23, stake); p.rect(ox + 22, 6, 1, 23, hex('#9a8450'));
      for (let y = 22; y > 10; y -= 3) p.set(ox + 20 - ((y / 3) % 2), y, leafLo);
      leafAt(ox, 13, 19, 2); leafAt(ox, 19, 16, 2); leafAt(ox, 15, 13, 2);
    }
    if (st >= 3) { leafAt(ox, 11, 10, 2); leafAt(ox, 19, 8, 2); p.set(ox + 14, 17, flower); p.set(ox + 17, 11, flower); p.set(ox + 12, 15, flower); }
    if (st >= 4) for (const [x, y] of [[13, 17], [18, 12], [11, 11]]) { p.rect(ox + x, y, 2, 6, fruit); p.set(ox + x, y + 1, fruitHi); p.set(ox + x, y, leafLo); }
    p.outline(ox, 0, CELL, CELL);
  }
  return p.finish();
}

/** Weeds: 0 lush, 1 burning, 2 burnt stubble. */
export function weedsSheet() {
  const p = new Pix(CELL * 3, CELL);
  for (let s = 0; s < 3; s++) {
    const ox = s * CELL, rng = makeRng(90);
    for (let b = 0; b < 15; b++) {
      const x0 = 5 + rng() * 22, h = s === 2 ? 2 + rng() * 3 : 10 + rng() * 17, lean = (rng() - 0.5) * 7;
      const col = s === 2 ? hex(rng() < 0.5 ? '#2e2620' : '#4a3a2e') : hex(['#4f8a34', '#6aa83e', '#3c6e2c', '#86b84a'][b % 4]);
      for (let y = 0; y < h; y++) {
        const t = y / h, x = x0 + lean * t * t;
        p.set(ox + x, 31 - y, s === 1 && t > 0.6 ? hex(t > 0.85 ? '#ffe08a' : '#ff8a3a') : col);
      }
      if (s === 0 && b % 5 === 0) p.set(ox + x0 + lean, 31 - h, hex('#e8e0b0')); // seed heads
    }
    p.outline(ox, 0, CELL, CELL);
  }
  return p.finish();
}

/** Shide: zig-zag paper streamers for the shimenawa (32 x 32, one strip). */
export function shideSprite() {
  const p = new Pix(16, 32);
  const paper = hex('#fbf7ea'), shade = hex('#cfc8b4');
  for (let k = 0; k < 4; k++) {
    const x = k % 2 === 0 ? 4 : 8, y = 2 + k * 7;
    p.rect(x, y, 5, 7, paper); p.rect(x + 4, y, 1, 7, shade);
  }
  p.outline(0, 0, 16, 32);
  return p.finish();
}

/** Ice sheet (radial, cracked), 64 x 64, transparent outside the disc. */
export function iceTexture() {
  const p = new Pix(64, 64), rng = makeRng(5);
  for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
    const dx = x - 31.5, dy = y - 31.5, d = Math.hypot(dx, dy) / 32;
    if (d > 1 - rng() * 0.08) continue;
    const v = 0.5 + 0.5 * Math.sin(dx * 0.31 + dy * 0.17) * Math.cos(dy * 0.23);
    p.set(x, y, hex(d > 0.9 ? '#e8f6ff' : v > 0.7 ? '#cfeaff' : v > 0.35 ? '#a8d6f4' : '#8cc2ea'), d > 0.9 ? 230 : 205);
  }
  for (let c = 0; c < 7; c++) { // cracks
    let x = 32, y = 32, a = rng() * Math.PI * 2;
    for (let s = 0; s < 26; s++) { x += Math.cos(a); y += Math.sin(a); a += (rng() - 0.5) * 0.7; if (Math.hypot(x - 32, y - 32) > 29) break; p.set(x, y, hex('#f4fbff'), 240); }
  }
  return p.finish();
}

/** A soft round glow (additive), 32 x 32. */
export function glowSprite() {
  const p = new Pix(32, 32);
  for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) {
    const d = Math.hypot(x - 15.5, y - 15.5) / 16;
    if (d < 1) { const a = Math.pow(1 - d, 2.2); p.set(x, y, [255, 255, 255], Math.round(a * 255)); }
  }
  return p.finish();
}
