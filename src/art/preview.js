// Character art preview for the 2D pipeline: a 480x270 native canvas, integer-upscaled, with a
// small ground, every character in a few poses (Saji riding on Tsuzumi's frame via anchors) and
// per-pixel lighting from the normal maps (sun + a moving lantern). Not part of the game.
//   ?t=noon|dusk   lighting preset      ?time=SECONDS   freeze the clock (for screenshots)
// Sets window.DONE = true after the first full frame.

import { TSUZUMI, SAJI, SHIONE, CHARACTERS, frameAt, riderOrder } from './characters.js';

const W = 480, H = 270;
const params = new URLSearchParams(location.search);
const PRESET = params.get('t') === 'dusk' ? 'dusk' : 'noon';
const FIXED = params.has('time') ? parseFloat(params.get('time')) : null;

const LIGHT = {
  noon: { ambient: [0.62, 0.66, 0.74], sun: [0.62, 0.58, 0.5], dir: [-0.45, 0.55, 0.7], lamp: 0, grade: [1, 1, 1] },
  dusk: { ambient: [0.36, 0.33, 0.48], sun: [0.75, 0.42, 0.22], dir: [-0.85, 0.25, 0.47], lamp: 1, grade: [1.02, 0.97, 0.95] },
}[PRESET];

// --- page --------------------------------------------------------------------------------------
document.documentElement.style.cssText = 'height:100%;overflow:hidden';
document.body.style.cssText = 'margin:0;height:100%;background:#101218;color:#cfd3dc;font:12px/1.4 system-ui,sans-serif;overflow:hidden';
const canvas = document.createElement('canvas');
canvas.width = W; canvas.height = H;
canvas.style.cssText = 'position:fixed;display:block;image-rendering:pixelated;image-rendering:crisp-edges';
document.body.appendChild(canvas);
const ctx = canvas.getContext('2d');
// Integer upscale, centred. Portrait screens keep the height (like the game) and crop the sides.
// The canvas is position:fixed so it never widens the layout (a mobile browser would zoom out).
function fit() {
  const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const portrait = vh > vw;
  const s = Math.max(1, Math.floor(portrait ? vh / H : Math.min(vw / W, vh / H)));
  canvas.style.width = W * s + 'px';
  canvas.style.height = H * s + 'px';
  canvas.style.left = Math.floor((vw - W * s) / 2) + 'px';
  canvas.style.top = Math.floor((vh - H * s) / 2) + 'px';
}
addEventListener('resize', fit);
fit();

// --- images -> pixel arrays ----------------------------------------------------------------------
function loadPixels(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = img.width; c.height = img.height;
      const g = c.getContext('2d');
      g.drawImage(img, 0, 0);
      resolve({ w: img.width, h: img.height, data: g.getImageData(0, 0, img.width, img.height).data });
    };
    img.onerror = reject;
    img.src = url;
  });
}

const PIX = new Map();
async function loadAll() {
  for (const ch of Object.values(CHARACTERS)) {
    if (!ch) continue;
    for (const s of Object.values(ch.sheets)) {
      PIX.set(s.albedo, await loadPixels(s.albedo));
      PIX.set(s.normal, await loadPixels(s.normal));
    }
  }
}

// --- ground (deterministic pixel texture) ------------------------------------------------------
const hash = (x, y) => { let h = (x * 374761393 + y * 668265263) ^ 0x5bd1e995; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const GRASS = [[74, 112, 58], [84, 126, 63], [96, 140, 70], [110, 154, 78]];
const DIRT = [[132, 104, 76], [146, 116, 84], [158, 128, 92], [170, 140, 102]];
function groundAt(x, y) {
  const road = Math.abs(y - (152 + Math.sin(x * 0.02) * 6)) < 20;
  const n = hash(x >> 2, y >> 2) * 0.6 + hash(x, y) * 0.4;
  const pal = road ? DIRT : GRASS;
  let c = pal[Math.min(3, Math.floor(n * 4))];
  if (!road && hash(x, y * 3) > 0.985) c = [132, 172, 88]; // grass blades
  if (road && hash(x * 7, y) > 0.99) c = [186, 160, 124];   // pebbles
  return c;
}

// --- scene ---------------------------------------------------------------------------------------
// Each actor: character, sheet, anim, dir, position (pivot), and optional rider (Saji on the load).
const SCENE = [
  { ch: TSUZUMI, sheet: 'load', anim: 'idle', dir: 'down', x: 40, y: 118, rider: { anim: 'sitTalk' } },
  { ch: TSUZUMI, sheet: 'load', anim: 'walk', dir: 'right', x: 100, y: 118, rider: { anim: 'sit' } },
  { ch: TSUZUMI, sheet: 'load', anim: 'walk', dir: 'up', x: 160, y: 118, rider: { anim: 'sit' } },
  { ch: TSUZUMI, sheet: 'frame', anim: 'walk', dir: 'left', x: 220, y: 118, rider: { anim: 'sitBell' } },
  { ch: TSUZUMI, sheet: 'frame', anim: 'idle', dir: 'down', x: 280, y: 118, rider: { anim: 'sit' } },
  { ch: TSUZUMI, sheet: 'load', anim: 'bow', dir: 'right', x: 338, y: 118 },
  { ch: TSUZUMI, sheet: 'frame', anim: 'shoulder', dir: 'right', x: 394, y: 118 },
  { ch: SHIONE, sheet: 'main', anim: 'idle', dir: 'down', x: 450, y: 118 },
  { ch: TSUZUMI, sheet: 'plain', anim: 'idle', dir: 'down', x: 36, y: 236 },
  { ch: TSUZUMI, sheet: 'plain', anim: 'walk', dir: 'right', x: 84, y: 236 },
  { ch: TSUZUMI, sheet: 'plain', anim: 'eat', dir: 'down', x: 132, y: 236 },
  { ch: TSUZUMI, sheet: 'plain', anim: 'asleep', dir: 'right', x: 190, y: 236 },
  { ch: SAJI, sheet: 'main', anim: 'idle', dir: 'down', x: 250, y: 236 },
  { ch: SAJI, sheet: 'main', anim: 'walk', dir: 'right', x: 280, y: 236 },
  { ch: SAJI, sheet: 'main', anim: 'hop', dir: 'down', x: 310, y: 236 },
  { ch: SAJI, sheet: 'main', anim: 'pointStand', dir: 'right', x: 340, y: 236 },
  { ch: SAJI, sheet: 'main', anim: 'float', dir: 'up', x: 374, y: 236 },
  { ch: SHIONE, sheet: 'main', anim: 'carryWalk', dir: 'right', x: 432, y: 236 },
];

// G-buffer: albedo rgb + normal xyz + coverage
const alb = new Float32Array(W * H * 3);
const nrm = new Float32Array(W * H * 3);
const shadow = new Float32Array(W * H);

function blitFrame(f, px, py) {
  const A = PIX.get(f.albedo), N = PIX.get(f.normal);
  const ch = f.ch;
  const ox = px - ch.pivot.x, oy = py - ch.pivot.y;
  for (let y = 0; y < f.sh; y++) {
    const ty = oy + y;
    if (ty < 0 || ty >= H) continue;
    for (let x = 0; x < f.sw; x++) {
      const sxl = f.mirror ? f.sw - 1 - x : x;
      const si = ((f.sy + y) * A.w + f.sx + sxl) * 4;
      if (A.data[si + 3] < 128) continue;
      const tx = ox + x;
      if (tx < 0 || tx >= W) continue;
      const ti = ty * W + tx;
      alb[ti * 3] = A.data[si] / 255; alb[ti * 3 + 1] = A.data[si + 1] / 255; alb[ti * 3 + 2] = A.data[si + 2] / 255;
      let nx = N.data[si] / 127.5 - 1, ny = N.data[si + 1] / 127.5 - 1, nz = N.data[si + 2] / 127.5 - 1;
      if (f.mirror) nx = -nx;
      nrm[ti * 3] = nx; nrm[ti * 3 + 1] = ny; nrm[ti * 3 + 2] = nz;
    }
  }
}

function blobShadow(x, y, rx, ry) {
  for (let j = -ry; j <= ry; j++) for (let i = -rx; i <= rx; i++) {
    const d = (i * i) / (rx * rx) + (j * j) / (ry * ry);
    if (d > 1) continue;
    const tx = x + i, ty = y + j;
    if (tx < 0 || ty < 0 || tx >= W || ty >= H) continue;
    shadow[ty * W + tx] = Math.max(shadow[ty * W + tx], d < 0.55 ? 0.42 : 0.26);
  }
}

function render(time) {
  // ground
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x, c = groundAt(x, y);
    alb[i * 3] = c[0] / 255; alb[i * 3 + 1] = c[1] / 255; alb[i * 3 + 2] = c[2] / 255;
    nrm[i * 3] = 0; nrm[i * 3 + 1] = 0.62; nrm[i * 3 + 2] = 0.78;
    shadow[i] = 0;
  }
  // actors back to front (by y)
  const actors = [...SCENE].sort((a, b) => a.y - b.y);
  for (const a of actors) blobShadow(a.x, a.y, a.ch === SAJI ? 6 : 9, 3);
  for (const a of actors) {
    const f = frameAt(a.ch, a.sheet, a.anim, a.dir, time % 4, { rider: !!a.rider });
    if (!f) continue;
    f.ch = a.ch;
    let rider = null;
    if (a.rider && f.anchors.loadTop) {
      const r = frameAt(SAJI, 'main', a.rider.anim, a.dir, time % 4);
      r.ch = SAJI;
      const seat = r.anchors.seat || { x: 0, y: 0 };
      rider = () => blitFrame(r, a.x + f.anchors.loadTop.x - seat.x, a.y + f.anchors.loadTop.y - seat.y);
    }
    // front and side: Saji first (the hat brim covers her skirt); back: Saji over the frame
    if (rider && riderOrder(a.ch, f) === 'behind') rider();
    blitFrame(f, a.x, a.y);
    if (rider && riderOrder(a.ch, f) !== 'behind') rider();
  }
  // light
  const L = LIGHT, d = L.dir, dl = Math.hypot(d[0], d[1], d[2]);
  const lx = d[0] / dl, ly = d[1] / dl, lz = d[2] / dl;
  const lamp = { x: 240 + Math.cos(time * 0.9) * 150, y: 150 + Math.sin(time * 0.9) * 60, h: 26 };
  const img = ctx.createImageData(W, H);
  const o = img.data;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    const nx = nrm[i * 3], ny = nrm[i * 3 + 1], nz = nrm[i * 3 + 2];
    const sh = 1 - shadow[i];
    const sun = Math.max(0, nx * lx + ny * ly + nz * lz) * sh;
    let r = L.ambient[0] * (0.75 + 0.25 * sh) + L.sun[0] * sun;
    let g = L.ambient[1] * (0.75 + 0.25 * sh) + L.sun[1] * sun;
    let b = L.ambient[2] * (0.75 + 0.25 * sh) + L.sun[2] * sun;
    if (L.lamp) {
      const dx = lamp.x - x, dy = y - lamp.y, dist = Math.hypot(dx, dy, lamp.h);
      const ndl = Math.max(0, (nx * dx - ny * dy * 0.6 + nz * lamp.h) / dist);
      const att = Math.max(0, 1 - dist / 120) ** 2;
      r += 1.1 * att * ndl; g += 0.72 * att * ndl; b += 0.36 * att * ndl;
    }
    o[i * 4] = Math.min(255, alb[i * 3] * r * L.grade[0] * 255);
    o[i * 4 + 1] = Math.min(255, alb[i * 3 + 1] * g * L.grade[1] * 255);
    o[i * 4 + 2] = Math.min(255, alb[i * 3 + 2] * b * L.grade[2] * 255);
    o[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  if (L.lamp) { // the lantern itself
    ctx.fillStyle = '#ffd27a';
    ctx.fillRect(Math.round(lamp.x) - 1, Math.round(lamp.y) - 2, 3, 4);
  }
}

loadAll().then(() => {
  const t0 = performance.now();
  const loop = () => {
    const time = FIXED ?? (performance.now() - t0) / 1000;
    render(time);
    window.DONE = true;
    if (FIXED === null) requestAnimationFrame(loop);
  };
  loop();
}).catch(e => { document.body.textContent = 'preview failed: ' + e; window.DONE = true; });
