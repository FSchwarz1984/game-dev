// Bake of the 「隔」 tower insert (src/vista/tower.js, HEAD) for Godot: from the canopy, the summit
// ridge with the steel lattice tower, its red lamp, the tunnel's ventilation shaft, the sky shore's
// light behind the ridge. A fixed hour (21:00), so every layer is a finished RGBA image.
//
// Layout: the JS 480x270 frame, on a larger canvas so any logical view (up to 1024 x 560) keeps it:
//   land group (sky, stars, the ridge, the tower): canvas Wc x Hc, the reference frame at (ox, oy);
//     placed so the ridge and the tower keep their place above the view's bottom
//   ghost (the faint hanging sky shore): hangs from the view's top, as wide as the canvas
//   leaves framing the shot: top-left, bottom-left, bottom-right, each stuck to its corner
// Twinkling stars and the lamp are drawn live in Godot (lists in the JSON).

import { clamp, lerp, smooth, rng, hash2, vnoise, fbm, ridged, makeCanvas, ctx2d, mix3, pack, IndexLayer, I, run } from '../../../src/vista/util.js';
import { todEnv, palette, skyAt } from '../../../src/vista/tod.js';
import { makeStars } from '../../../src/vista/sky.js';
import { paintCanopyGen, FOLIAGE_MATS } from '../../../src/vista/foliage.js';

const REF_W = 480, REF_H = 270;
const M = { ridge: 1, ridgeRim: 2, far: 3, steel: 4, steelRim: 5, concrete: 6, concreteDark: 7, wire: 8, farRim: 9 };
const STAR_A = [0.32, 0.55, 0.8, 1];

export function bakeTower(o = {}) {
  const seed = o.seed ?? 7;
  const W = REF_W, H = REF_H;
  const Wc = o.Wc ?? W, Hc = o.Hc ?? H;
  const ox = Math.round((Wc - W) / 2), oy = Hc - H;          // the reference frame sits at the canvas bottom
  const R = rng(seed * 13 + 9);
  const env = todEnv(21);
  const cx = Math.round(W / 2);
  const yh = Math.round(H * 0.78);
  const S = Math.max(110, H * 0.75);
  // sky (paintSky with the jade glow of the sky shore behind the ridge), over the whole canvas
  const extra = (c, e, u) => {
    const k = Math.exp(-Math.pow((u - 0.58) / 0.42, 2)) * Math.exp(-Math.pow((e - 0.32) / 0.42, 2));
    return mix3(c, [96, 150, 150], k * 0.55);
  };
  const sky = makeCanvas(Wc, Hc), sg = ctx2d(sky), sid = sg.createImageData(Wc, Hc), SU = new Uint32Array(sid.data.buffer);
  const NU = Math.ceil(W / 2), q2 = v => Math.round(v / 2) * 2;
  for (let y = 0; y < Hc; y++) {
    const e = (yh - (y - oy)) / S;
    for (let x = 0; x < Wc; x++) {
      const k = Math.round(((x - ox) / (W - 1)) * NU), u = k / NU;
      const col = extra(skyAt(env, e, u), e, u);
      SU[y * Wc + x] = pack([q2(col[0]), q2(col[1]), q2(col[2])]);
    }
  }
  sg.putImageData(sid, 0, 0);
  // stars over the sky (the canvas's sky rows); the still ones are painted in, twinklers listed
  const stars = makeStars(Wc, yh + oy, seed * 5 + 3, { density: 0.8 });
  const fadeS = y => smooth(H * 0.62, H * 0.3, y - oy);
  for (const s of stars) {
    if (s.tw) continue;
    const a = STAR_A[s.mag] * fadeS(s.y);
    if (a <= 0.02) continue;
    sg.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${a.toFixed(3)})`;
    sg.fillRect(s.x, s.y, 1, 1);
  }

  // ridges (tower.js L29-72), x and y in reference-frame coordinates, painted into the canvas
  const tx = Math.round(cx + W * 0.11);
  const ridgeTop = x => {
    const u = (x - tx) / W;
    let y = H * 0.5 + Math.pow(Math.abs(u) * 2.2, 1.35) * H * 0.2 + (u < 0 ? -u * H * 0.06 : 0);
    y += (ridged(x * 0.012, 3, 3, seed) - 0.5) * H * 0.05;
    return y;
  };
  const farTop = x => H * 0.47 + (fbm(x * 0.006 + 5, 1, 3, seed + 3) - 0.5) * H * 0.18 + Math.abs((x - cx) / W) * H * 0.08;
  const L = new IndexLayer(Wc, Hc);
  const set = (x, y, v) => L.set(x + ox, y + oy, v);
  const get = (x, y) => L.get(x + ox, y + oy);
  const xa = -ox, xb = Wc - ox;
  const top = new Map(), ftop = new Map();
  for (let x = xa; x < xb; x++) { ftop.set(x, farTop(x)); top.set(x, ridgeTop(x)); }
  for (let x = -6; x < W + 6; x += 3 + Math.floor(R() * 4)) stampCedar(x);
  // the same rows of cedars along the ridge where the canvas is wider than the frame (own draws)
  const RX = rng(seed * 131 + 7);
  for (let x = xa - 6; x < -6; x += 3 + Math.floor(RX() * 4)) stampCedar(x, RX);
  for (let x = W + 6; x < xb + 6; x += 3 + Math.floor(RX() * 4)) stampCedar(x, RX);
  function stampCedar(x, Rr = R) {
    const base = ridgeTop(clamp(x, xa, xb - 1));
    if (Math.abs(x - tx) < 10) return;
    const hgt = 5 + Rr() * 9 * (0.6 + Math.abs(x - tx) / W), wid = hgt * (0.35 + Rr() * 0.12);
    for (let dx = -Math.ceil(wid); dx <= Math.ceil(wid); dx++) {
      const X = x + dx; if (X < xa || X >= xb) continue;
      const v = base - hgt * (1 - Math.abs(dx) / (wid + 0.5)) + (Math.abs(dx) % 2) * 0.6;
      if (v < top.get(X)) top.set(X, v);
    }
  }
  for (let x = xa; x < xb; x++) {
    for (let y = Math.max(-oy, Math.floor(ftop.get(x))); y < Hc - oy; y++) set(x, y, I(M.far, 3, 3, 0));
    if (hash2(x, 1, 5) < 0.6) set(x, Math.max(-oy, Math.floor(ftop.get(x))), I(M.farRim, 4, 3, 0));
    const ty = Math.max(-oy, Math.round(top.get(x)));
    for (let y = ty; y < Hc - oy; y++) {
      const d = y - ty;
      const row = (((y + Math.floor(vnoise(x * 0.08, 3, 8) * 4)) % 6) + 6) % 6;
      const n = vnoise(x * 0.3, y * 0.15, 7);
      const tip = d < 36 && row === 0 && n > 0.45 + d / 80 && ((((x + Math.floor(y / 6)) % 3) + 3) % 3 !== 0);
      set(x, y, I(M.ridge, d < 2 ? 3 : tip ? 2 : 1, 1, 0));
    }
    const slope = top.get(Math.min(xb - 1, x + 1)) - top.get(Math.max(xa, x - 1));
    set(x, ty, I(M.ridgeRim, slope > 0.6 ? 5 : slope < -0.6 ? 3 : 4, 3, 0));
  }
  // the ventilation shaft (L74-82)
  const vx = Math.round(tx - W * 0.17), vy = Math.round(ridgeTop(vx));
  const vw = Math.max(7, Math.round(H * 0.035)), vh = Math.max(10, Math.round(H * 0.05));
  for (let y = vy - vh; y < vy + 2; y++) for (let x = vx - vw; x <= vx + vw; x++) {
    const edge = x === vx + vw || y === vy - vh;
    const louver = y < vy - vh + 4 && y > vy - vh && (x - vx) % 2 === 0;
    set(x, y, I(louver ? M.concreteDark : M.concrete, edge ? 5 : x > vx ? 3 : 2, 3, 0));
  }
  // the tower (L83-115)
  const Ht = Math.round(H * 0.4), baseY = Math.round(ridgeTop(tx)) + 1, topY = baseY - Ht;
  const halfB = Math.round(Ht * 0.17), halfT = Math.max(2, Math.round(Ht * 0.045));
  const legX = (y, side) => tx + side * lerp(halfB, halfT, (baseY - y) / (baseY - topY - Ht * 0.12));
  const steel = (x, y, rim) => { x = Math.round(x); y = Math.round(y); set(x, y, I(rim ? M.steelRim : M.steel, rim ? 5 : 2, 2, 0)); };
  const line = (x0, y0, x1, y1, rim) => { const n = Math.ceil(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))); for (let k = 0; k <= n; k++) steel(lerp(x0, x1, k / n), lerp(y0, y1, k / n), rim); };
  const bodyTop = topY + Math.round(Ht * 0.12);
  for (let y = bodyTop; y <= baseY; y++) for (const side of [-1, 1]) { const x = legX(y, side); steel(x, y, side > 0); steel(x - side, y, false); }
  const levels = [];
  for (let y = baseY; y > bodyTop;) { levels.push(y); y -= Math.max(5, Math.round((y - bodyTop) * 0.24 + 4)); }
  levels.push(bodyTop);
  for (let k = 0; k < levels.length; k++) {
    const y = levels[k];
    line(legX(y, -1), y, legX(y, 1), y, false);
    if (k + 1 < levels.length) { const y2 = levels[k + 1]; line(legX(y, -1), y, legX(y2, 1), y2, false); line(legX(y, 1), y, legX(y2, -1), y2, true); }
  }
  const py = bodyTop;
  for (let x = tx - halfT - 3; x <= tx + halfT + 3; x++) { steel(x, py, false); if ((x - tx) % 2 === 0) steel(x, py - 2, x > tx); }
  line(tx - halfT - 3, py - 2, tx + halfT + 3, py - 2, false);
  const mastTop = topY;
  line(tx, py, tx, mastTop + 1, false); line(tx + 1, py, tx + 1, mastTop + 3, true);
  const wires = [];
  for (let k = 0; k < 2; k++) {
    const x0 = tx + 2, y0 = bodyTop + 6 + k * 5, x1 = W + 4, y1 = Math.round(ridgeTop(W - 1)) - 8 + k * 6;
    for (let x = x0; x <= x1; x++) {
      const u = (x - x0) / (x1 - x0), y = lerp(y0, y1, u) + Math.sin(u * Math.PI) * (8 + k * 3);
      const xi = Math.round(x), yi = Math.round(y);
      if (xi >= xa && xi < xb && !get(xi, yi)) wires.push([xi, yi]);
    }
  }
  for (const [x, y] of wires) set(x, y, I(M.wire, 2, 2, 0));
  const lamp = { x: tx, y: mastTop };
  // the canopy framing the shot (L118-123), split into its three corners
  const clumpsBL = [], clumpsBR = [], clumpsTL = [];
  for (let k = 0; k < 9; k++) clumpsBL.push({ x: W * (-0.04 + R() * 0.26), y: H * (0.78 + R() * 0.3), rx: 18 + R() * 10, ry: 13 + R() * 5, z: R() });
  for (let k = 0; k < 4; k++) clumpsBR.push({ x: W * (0.94 + R() * 0.1), y: H * (0.9 + R() * 0.14), rx: 16 + R() * 8, ry: 12 + R() * 4, z: R() });
  clumpsTL.push({ x: W * 0.05, y: H * 0.1, rx: 22, ry: 14, z: 1 }, { x: W * 0.13, y: H * 0.03, rx: 18, ry: 12, z: 1.2 }, { x: -6, y: H * 0.22, rx: 16, ry: 12, z: 1.1 });
  const limbTL = [{ pts: [[-10, H * 0.26, 4.5], [W * 0.08, H * 0.12, 3], [W * 0.16, -4, 2]], z: 0.8, dark: 1 }];
  // wider canvases: the same leaves reach on past the reference frame's edges (own draws)
  for (let k = 0; k < 7; k++) clumpsBL.push({ x: W * (-0.04 - RX() * 0.5), y: H * (0.7 + RX() * 0.38), rx: 18 + RX() * 10, ry: 13 + RX() * 5, z: RX() });
  for (let k = 0; k < 5; k++) clumpsBR.push({ x: W * (1.04 + RX() * 0.45), y: H * (0.84 + RX() * 0.22), rx: 16 + RX() * 8, ry: 12 + RX() * 4, z: RX() });
  for (let k = 0; k < 4; k++) clumpsTL.push({ x: -W * (0.06 + RX() * 0.4), y: H * (RX() * 0.25), rx: 16 + RX() * 8, ry: 12 + RX() * 4, z: 0.9 + RX() * 0.3 });
  // G5R3-50: the leaves in the corners hung in the air (the user: "切到信號塔那裡的時候左下角枝幹的樹葉
  // 像是懸在空中沒有連接"): HEAD's clumps lie about the corners with nothing holding them, and in the
  // bottom left two of them float free over the dark ridge (more of them, in every corner, on wide
  // views). Each corner gets the camphor's lower bough the clumps rest on, reaching in from outside the
  // frame (from the left for the two left corners, from the right for the bottom right), behind every
  // clump (it shows only between them); the clumps themselves are painted exactly as before. Its
  // points are in the reference frame's coordinates, drawn [x, y, radius], root first.
  const boughs = {
    // under the clumps of the bottom left: in from the far left, sagging a little, its tip in the
    // clump that hangs over the ridge right of the corner (the two that floated rest on it)
    BL: [{ pts: [[-282, 254, 5.6], [-210, 243, 5], [-140, 238, 4.4], [-70, 236, 3.8], [-10, 232, 3.3], [40, 229, 2.8], [72, 231, 2.3], [94, 237, 1.7], [106, 242, 1.2]], z: -0.5, dark: 1 }],
    // the bottom right (on wide views): in from the far right, through its clumps to the corner's mass
    BR: [{ pts: [[762, 254, 5.6], [700, 247, 4.6], [640, 247, 3.9], [584, 249, 3.2], [532, 254, 2.5], [486, 262, 1.7], [462, 268, 1.2]], z: -0.5, dark: 1 }],
    // the top left (on wide views): in from the far left, rising to the clumps under the old limb
    TL: [{ pts: [[-284, 60, 5.2], [-236, 41, 4.5], [-196, 27, 3.8], [-166, 32, 3.2], [-122, 36, 2.6], [-80, 40, 2.1], [-46, 44, 1.6]], z: -0.5, dark: 1 }],
  };
  const light = [0.6, -0.4, -0.5];
  const fpal = palette(FOLIAGE_MATS, { ...env, sun: [0.2, 0.32, 0.32] });
  // each corner painted on its own canvas (same coordinates as the reference frame plus a margin);
  // `out`: where the layer runs out of every view (sides of the layer, and rows / columns of the
  // reference frame past its edges): every piece of it must reach there (hang())
  const corner = (clumps, limbs, x0, y0, w, h, cellSeed, bough, out) => {
    const shifted = clumps.map(c => ({ ...c, x: c.x - x0, y: c.y - y0 }));
    const ls = limbs.map(l => ({ ...l, pts: l.pts.map(([x, y, r]) => [x - x0, y - y0, r]) }));
    const rim = { x: W * 0.6 - x0, y: H * 0.4 - y0, r: W };
    const layer = run(paintCanopyGen(w, h, { clumps: shifted, limbs: ls, light, cell: 3.4, cellSeed, rimBelow: rim }, 91));
    if (bough) {
      // the bough on its own (its own draws: the clumps keep theirs), then laid behind the leaves
      const bs = bough.map(l => ({ ...l, pts: l.pts.map(([x, y, r]) => [x - x0, y - y0, r]) }));
      const B = run(paintCanopyGen(w, h, { clumps: [], limbs: bs, light, cell: 3.4, cellSeed, rimBelow: rim }, 92));
      for (let i = 0; i < w * h; i++) if (B.idx[i] && (!layer.idx[i] || B.depth[i] > layer.depth[i])) layer.idx[i] = B.idx[i];
    }
    const dropped = hang(layer, out(x0, y0, w, h));
    return { img: layerImage(layer, fpal), x0, y0, dropped };
  };
  const mX = ox, mY = Hc - H;      // how far the canvas reaches past the frame on each side
  // where each corner runs out of the frame on every view the canvas serves: below the frame's bottom
  // row (the corners keep their place above the view's bottom), the layer's outer side (off the
  // widest view's edge), above the frame's top row (the top left hangs from the view's top)
  const below = (x0, y0, w, h) => (x, y) => y + y0 >= H;
  const BL = corner(clumpsBL, [], -mX, Math.round(H * 0.55), mX + Math.round(W * 0.45), Math.round(H * 0.45) + 60, 13, boughs.BL,
    (x0, y0, w, h) => (x, y) => x === 0 || below(x0, y0, w, h)(x, y));
  const BR = corner(clumpsBR, [], Math.round(W * 0.8), Math.round(H * 0.7), Math.round(W * 0.2) + mX, Math.round(H * 0.3) + 60, 13, boughs.BR,
    (x0, y0, w, h) => (x, y) => x === w - 1 || below(x0, y0, w, h)(x, y));
  const TL = corner(clumpsTL, limbTL, -mX, -mY, mX + Math.round(W * 0.3), mY + Math.round(H * 0.42), 13, boughs.TL,
    (x0, y0) => (x, y) => x === 0 || y + y0 <= 0);

  // the land, coloured (tower.js pal)
  const glowCol = [96, 150, 150];
  const lpal = i => {
    const m = i >> 8, s = (i >> 5) & 7;
    let c;
    switch (m) {
      case M.ridge: c = s >= 3 ? [26, 33, 47] : s === 2 ? [22, 28, 41] : [15, 19, 30]; break;
      case M.ridgeRim: c = mix3([30, 40, 52], glowCol, 0.22 + s * 0.05); break;
      case M.far: c = [40, 48, 72]; break;
      case M.farRim: c = [50, 64, 84]; break;
      case M.steel: c = [26, 22, 26]; break;
      case M.steelRim: c = [70, 84, 88]; break;
      case M.concrete: c = s >= 5 ? [74, 86, 96] : s >= 3 ? [46, 52, 62] : [34, 38, 48]; break;
      case M.concreteDark: c = [16, 18, 24]; break;
      case M.wire: c = [30, 30, 40]; break;
      default: return 0;
    }
    return pack(c);
  };
  // the faint hanging sky shore beyond the ridge (ghostShore, L198-229), as wide as the canvas
  const ghost = ghostShore(Wc, H, ox);

  return {
    meta: { shot: 'tower', seed, refW: W, refH: H, Wc, Hc, ox, oy, lamp, shaft: { x: vx, y: vy - vh }, yh,
      corners: { BL: { x: BL.x0, y: BL.y0, w: BL.img.w, h: BL.img.h, dropped: BL.dropped }, BR: { x: BR.x0, y: BR.y0, w: BR.img.w, h: BR.img.h, dropped: BR.dropped }, TL: { x: TL.x0, y: TL.y0, w: TL.img.w, h: TL.img.h, dropped: TL.dropped } },
      vignette: { cx: 0.55, cy: 0.45, r0: 0.3, r1: 0.6, a: 0.5 } },
    stars: stars.filter(s => s.tw).map(s => [s.x, s.y, s.mag, s.col[0], s.col[1], s.col[2], +s.ph.toFixed(3), +s.sp.toFixed(3), 1]),
    images: {
      sky: canvasImage(sky),
      land: layerImage(L, lpal),
      ghost,
      leavesBL: BL.img, leavesBR: BR.img, leavesTL: TL.img,
    },
  };
}

function canvasImage(c) {
  const d = ctx2d(c).getImageData(0, 0, c.width, c.height).data;
  return { w: c.width, h: c.height, data: new Uint8Array(d.buffer.slice(0)) };
}

// Keeps what hangs (8-connected) from where the layer runs out of the frame (isOut(x, y)); clears the
// rest. Only stray specks may be left over once the boughs are in (a whole clump would be a design
// error: it throws). Returns how many pixels it cleared.
function hang(L, isOut) {
  const { w, h, idx } = L, seen = new Uint8Array(w * h), stack = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (idx[i] && isOut(x, y)) { seen[i] = 1; stack.push(i); }
  }
  while (stack.length) {
    const i = stack.pop(), x = i % w, y = (i - x) / w;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const xx = x + dx, yy = y + dy;
      if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
      const j = yy * w + xx;
      if (idx[j] && !seen[j]) { seen[j] = 1; stack.push(j); }
    }
  }
  // the pieces left over, by size
  let n = 0;
  const lone = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) if (idx[i] && !seen[i]) lone[i] = 1;
  for (let i = 0; i < w * h; i++) {
    if (!lone[i]) continue;
    const st = [i]; lone[i] = 0; let size = 0;
    while (st.length) {
      const k = st.pop(), x = k % w, y = (k - x) / w; size++; idx[k] = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const j = yy * w + xx;
        if (lone[j]) { lone[j] = 0; st.push(j); }
      }
    }
    if (size > 40) throw new Error(`tower: a piece of ${size} px of the corner leaves hangs from nothing at (${i % w}, ${(i / w) | 0})`);
    n += size;
  }
  L.used = null;
  return n;
}

function layerImage(L, pal) {
  const out = new Uint8Array(L.w * L.h * 4), lut = new Map();
  for (let i = 0; i < L.idx.length; i++) {
    const v = L.idx[i];
    if (!v) continue;
    let p = lut.get(v);
    if (p === undefined) { p = pal(v) >>> 0; lut.set(v, p); }
    out[i * 4] = p & 255; out[i * 4 + 1] = (p >> 8) & 255; out[i * 4 + 2] = (p >> 16) & 255; out[i * 4 + 3] = (p >>> 24) & 255;
  }
  return { w: L.w, h: L.h, data: out };
}

// tower.js ghostShore(), x in reference-frame coordinates over a canvas Wc wide
function ghostShore(Wc, H, ox) {
  const out = new Uint8Array(Wc * H * 4);
  const put = (x, y, c, a) => { const i = (y * Wc + x) * 4; out[i] = c[0]; out[i + 1] = c[1]; out[i + 2] = c[2]; out[i + 3] = a; };
  const edge = new Float32Array(Wc), edge2 = new Float32Array(Wc);
  for (let x = 0; x < Wc; x++) {
    const X = x - ox;
    edge[x] = H * 0.07 + Math.pow(ridged(X * 0.012 + 2, 5, 3, 31), 2.2) * H * 0.2;
    edge2[x] = H * 0.12 + Math.pow(ridged(X * 0.02 + 9, 7, 3, 37), 2.4) * H * 0.13;
  }
  for (let x = 0; x < Wc; x++) {
    for (let y = 0; y < edge2[x]; y++) put(x, y, [60, 78, 104], Math.round(0.7 * smooth(0, H * 0.05, y) * 255));
    const e2 = Math.floor(edge2[x]); if (e2 >= 0 && e2 < H) put(x, e2, [96, 132, 140], Math.round(0.5 * 255));
    for (let y = 0; y < edge[x]; y++) {
      const x2 = Math.max(1, Math.min(Wc - 2, Math.round(x + (y - edge[x]) * 0.35)));
      const shade = edge[x2 + 1] - edge[x2 - 1] > 0 ? 1 : 0;
      put(x, y, shade ? [40, 54, 80] : [48, 63, 89], Math.round(0.9 * smooth(0, H * 0.04, y) * 255));
    }
    const e = Math.floor(edge[x]); if (e >= 0 && e < H) put(x, e, [104, 148, 150], Math.round(0.55 * 255));
  }
  for (let k = 0; k < Math.round(480 / 9 * Wc / 480); k++) {
    const x = Math.floor(hash2(k, 1, 41) * Wc), y = Math.floor(edge[x] * (0.35 + hash2(k, 2, 41) * 0.5));
    if (y > 2) put(x, y, [200, 246, 228], Math.round((0.35 + hash2(k, 3, 41) * 0.4) * 255));
  }
  return { w: Wc, h: H, data: out };
}
