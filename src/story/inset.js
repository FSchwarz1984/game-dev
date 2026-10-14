// Full-screen pixel-art inserts for scenes. The first: the inside of her hat, seen for a
// moment as she lifts it off her face on the first morning — woven rings of split bamboo,
// the ribs, the dark apex, and two columns of ink: 本来無東西　何処有南北.
// Painted once into a low-resolution canvas and shown at an integer scale, pixels crisp.

import inkUrl from '../../assets/insets/hat-ink.png';

const W = 320, H = 180;
const INK = typeof Image !== 'undefined' ? Object.assign(new Image(), { src: inkUrl }) : null;

export class Insets {
  constructor(root) {
    injectStyle();
    this.el = document.createElement('div');
    this.el.className = 'inset';
    root.appendChild(this.el);
    this.cache = {};
  }

  /** Show (or hide) an insert by name; currently 'hat'. */
  show(kind, on) {
    if (!on) { this.el.classList.remove('on'); return; }
    let cv = this.cache[kind];
    if (!cv || !cv.inked) { cv = this.cache[kind] = paint(kind); cv.inked = !!(INK?.complete && INK.naturalWidth); }
    if (this.el.firstChild !== cv) { this.el.replaceChildren(cv); }
    this.fit(cv);
    this.el.classList.add('on');
  }

  fit(cv) {
    const dpr = devicePixelRatio || 1;
    const s = Math.max(1, Math.floor(Math.min(innerWidth * dpr / W, innerHeight * dpr / H)));
    cv.style.width = (W * s / dpr) + 'px';
    cv.style.height = (H * s / dpr) + 'px';
  }
}

function paint(kind) {
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  if (kind === 'hat') paintHat(cv.getContext('2d'));
  return cv;
}

// A small deterministic RNG so the weave never shimmers between runs.
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

function paintHat(g) {
  const img = g.createImageData(W, H), d = img.data;
  const cx = W / 2 + 6, cy = H / 2 + 4;
  // palette: lit sedge to the deep inside of the cone; light from the upper left
  const straw = [[236, 212, 158], [218, 190, 132], [198, 166, 110], [174, 142, 92], [146, 116, 76], [116, 90, 62], [86, 64, 48], [58, 42, 36], [36, 26, 26]];
  const ribs = 24;
  const hash = (a, b) => { let h = (a * 374761393 + b * 668265263) >>> 0; h = (h ^ (h >>> 13)) * 1274126177 >>> 0; return (h >>> 8) / 16777216; };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const dx = x - cx, dy = (y - cy) * 1.06, r = Math.hypot(dx, dy), a = Math.atan2(dy, dx);
    const ring = r / 4.6, ri = Math.floor(ring), rf = ring - ri;
    const sp = (a / (Math.PI * 2) + 0.5) * ribs, si = Math.floor(sp), sf = sp - si;
    // each strip between two ribs has its own slight tone (woven, not noisy)
    let tone = 1.6 + Math.min(4.8, Math.pow(r / 150, 1.2) * 5);   // darker toward the brim
    tone -= Math.max(0, -Math.cos(a + 0.8)) * 1.1;                // the upper-left catches light
    tone += (hash(ri, si) - 0.5) * 0.9;
    if (rf > 0.78) tone += 1.3;                                   // the shadow line under each strip
    else if (rf < 0.22) tone -= 0.45;                             // its lit lip
    if (sf < 0.06) tone += 1.6;                                   // a rib: dark line…
    else if (sf < 0.11) tone -= 0.6;                              // …with a lit edge
    const c = straw[Math.max(0, Math.min(straw.length - 1, Math.round(tone)))];
    const i = (y * W + x) * 4;
    d[i] = c[0]; d[i + 1] = c[1]; d[i + 2] = c[2]; d[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  // the head pad: an indigo cloth ring, sewn in, with the apex knot inside it
  ring(g, cx, cy, 15, 6, ['#14172a', '#1e2440', '#2a3358', '#3a4570']);
  ring(g, cx, cy, 3, 7, ['#241a18', '#30231e', '#3e2e25', '#4c3a2c']);
  // the red chin cords hang out of the frame
  cord(g, cx - 12, cy + 14, cx - 40, cy + 100);
  cord(g, cx + 12, cy + 14, cx + 30, cy + 100);
  // the ink, baked from a brush hand into hard pixels (tools/story/hat_ink.py)
  if (INK.complete && INK.naturalWidth) g.drawImage(INK, 0, 0);
  // the brim's shadow closes the frame
  const vg = g.createRadialGradient(cx, cy, 60, cx, cy, 200);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(10,6,8,.8)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
}

// a cloth ring of width w around radius r: four tones, lit from the upper left
function ring(g, cx, cy, r, w, tones) {
  for (let y = Math.floor(cy - r - w); y <= cy + r + w; y++) for (let x = Math.floor(cx - r - w); x <= cx + r + w; x++) {
    const dx = x - cx, dy = y - cy, d = Math.hypot(dx, dy), wob = Math.sin(Math.atan2(dy, dx) * 3 + r) * 0.9;
    if (Math.abs(d - r - wob) > w / 2) continue;
    const across = (d - r) / (w / 2);                          // -1 inner edge … 1 outer edge
    const lit = -(dx + dy) / (d || 1) * 0.5 + 0.5;            // 1 facing the light
    let t = Math.round(1 + lit * 1.6 - Math.abs(across) * 1.2);
    t = Math.max(0, Math.min(tones.length - 1, t));
    g.fillStyle = tones[t]; g.fillRect(x, y, 1, 1);
  }
}

// a red cord, two pixels wide, sagging a little; the upper-left edge lit
function cord(g, x0, y0, x1, y1) {
  const n = Math.ceil(Math.hypot(x1 - x0, y1 - y0));
  for (let i = 0; i <= n; i++) {
    const k = i / n, sag = Math.sin(k * Math.PI) * 6;
    const x = Math.round(x0 + (x1 - x0) * k + sag * 0.6), y = Math.round(y0 + (y1 - y0) * k);
    g.fillStyle = '#5e1a1c'; g.fillRect(x + 1, y, 1, 1);
    g.fillStyle = '#a3302c'; g.fillRect(x, y, 1, 1);
    if (i % 5 === 0) { g.fillStyle = '#d8584a'; g.fillRect(x, y, 1, 1); }   // the twist catches the light
  }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .inset { position: fixed; inset: 0; z-index: 28; display: grid; place-items: center; background: #0a0608; opacity: 0; visibility: hidden; transition: opacity .35s ease, visibility 0s .35s; pointer-events: none; }
  .inset.on { opacity: 1; visibility: visible; transition: opacity .25s ease; }
  .inset canvas { image-rendering: pixelated; image-rendering: crisp-edges; }
  `;
  document.head.appendChild(s);
}
