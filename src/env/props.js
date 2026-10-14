/* =====================================================================
   env/props — the made things of the pass, all in the same 3/4 view
   (tops and front faces, light from the top-left), Q-version buildings:
     hut (歩荷小屋) · shrine (祠) with a sagging eave corner + its fallen
     eave beam · paired 道祖神 (one figure under a very wide hat) and the
     stone offering ledge · nine nameless graves (無縁仏) · bamboo lantern
     poles · bon lanterns (盆提灯, lit/unlit) · 精霊馬 (cucumber horse and
     eggplant cow) · old back-frame (旧背負子) · her load (葛籠 + bundles)
     · dango plates (two / one / pale) · stone 道標 and a wooden sign ·
     stone lantern · rocks · stepping stones · the lookout fence · stump.
   Each painter returns {s, meta}; meta.ax/ay is the ground anchor.
   Lying objects use flat(s, ay): per-pixel bulge so they lie on the
   ground plane (correct depth against characters stepping over them).
   ===================================================================== */
import { SB, PX, POST, MAT, mass, cylN } from './paint.js';
import { PAL } from './palette.js';
import { RNG, clamp, lerp, hash2, hyp, ramp, hexRGB, vnoise } from './core.js';
import { shide } from './camphor.js';

const rc = (r, t, x, y, sp = 0.4) => PX.rc(r, clamp(t, 0, 1), x, y, sp);
/** a box in 3/4 view: x0..x1 wide, top face of depth d px above the front face of height h; front face bottom at yb */
function box(s, x0, x1, yb, h, d, o) {
  const top = yb - h - d + 1;
  for (let y = top; y <= yb; y++) for (let x = x0; x <= x1; x++) {
    const front = y > yb - h; const u = (x - x0) / Math.max(1, x1 - x0);
    const t = front ? o.front(x, y, u, (yb - y) / Math.max(1, h - 1)) : o.top(x, y, u, (y - top) / Math.max(1, d - 1));
    s.pz(x, y, t[0], o.z + (front ? 0 : 1), { m: o.m, b: (o.b || 0) + (front ? 0 : -(y - top)), n: front ? [0, 0, 1] : [0, 0.7, 0.7] });
  }
}
/** lying objects: make every pixel sit on the ground plane north of the anchor row */
function flat(s, ay, lift = 0) { for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) { const i = y * s.w + x; if (s.c[i * 4 + 3]) s.b[i] = -2 * (ay - y) + lift + s.z[i] * 0.3; } }
const WOOD = PAL.woodGrey, WDK = PAL.woodDark, STR = PAL.straw, ST = PAL.stone, STW = PAL.stoneWarm;

/* ===================== the porter's hut 歩荷小屋 ===================== */
export function hut(o = {}) {
  const W = 168, H = 156, s = new SB(W, H), cx = 84, gy = H - 4; // gy: ground line of the front wall
  const R = RNG(5);
  const wl = cx - 54, wr = cx + 53, wallH = 42;
  // foundation stones under the sill
  for (let x = wl - 2; x <= wr + 2; x += 9) PX.ell(x + 4, gy - 1, 5, 2.6, (xx, yy, u, v, d) => s.pz(xx, yy, rc(ST, 0.62 - v * 0.3 - u * 0.12, xx, yy), 2, { m: MAT.STONE, b: 2 }));
  // front wall: vertical cedar boards with battens, a sill and a head beam
  for (let y = gy - wallH; y <= gy - 3; y++) for (let x = wl; x <= wr; x++) {
    const board = Math.floor((x - wl) / 6), batten = (x - wl) % 18 === 0, edge = (x - wl) % 6 === 0;
    let t = 0.36 + hash2(board, 3, 7) * 0.16 - (edge ? 0.14 : 0) + (batten ? 0.12 : 0) - (y > gy - 8 ? 0.08 : 0) + (hash2(x, y >> 2, 9) - 0.5) * 0.06;
    if ((y - (gy - wallH)) < 3) t -= 0.18; // shade under the eave
    s.pz(x, y, rc(WDK, t + 0.12, x, y, 0.3), 4, { m: MAT.WOOD, b: 0 });
  }
  for (const px of [wl, cx - 1, wr]) for (let y = gy - wallH; y <= gy - 2; y++) for (let x = px - 2; x <= px + 2; x++) s.pz(x, y, rc(WDK, 0.5 - (x - px) * 0.1 + (x === px - 2 ? 0.15 : 0), x, y, 0.2), 6, { m: MAT.WOOD, b: 1 }); // posts
  for (let x = wl - 2; x <= wr + 2; x++) { s.pz(x, gy - 3, WDK[3], 6, { m: MAT.WOOD, b: 1 }); s.pz(x, gy - 2, WDK[1], 6, { m: MAT.WOOD, b: 1 }); s.pz(x, gy - wallH, WDK[4], 6, { m: MAT.WOOD, b: 1 }); s.pz(x, gy - wallH + 1, WDK[2], 6, { m: MAT.WOOD, b: 1 }); }
  // the door: a sliding board door half open, a dark room behind with the hearth's glow (emissive when lit)
  const dl = cx + 6, dr = cx + 27, dt = gy - 34;
  for (let y = dt; y <= gy - 4; y++) for (let x = dl; x <= dr; x++) {
    const inside = x < dl + 12; const hearth = inside && y > gy - 16 && o.lit;
    const c = inside ? (hearth ? [150 - (gy - y) * 2, 72, 30] : [26 + (y - dt) * 0.3, 21, 22]) : rc(WOOD, 0.46 + ((x - dr) % 5 === 0 ? -0.15 : 0) + hash2(x >> 2, 1, 3) * 0.1, x, y, 0.3);
    s.pz(x, y, c, 7, { m: inside ? MAT.WOOD : MAT.WOOD, b: inside ? -4 : 1, e: hearth ? 4 : 0 });
  }
  if (o.lit) for (let y = dt + 2; y <= gy - 5; y++) { const x = dl + 11 - ((y * 3) % 2); if (s.a(x, y)) s.px(x, y, [120, 66, 34], { m: MAT.WOOD, z: 7, b: -4, e: 2 }); }
  for (let x = dl - 1; x <= dr + 1; x++) s.pz(x, dt - 1, WDK[1], 8, { m: MAT.WOOD, b: 1 });
  // doorstep stone
  PX.ell(dl + 8, gy + 1, 9, 3, (x, y, u, v) => s.pz(x, y, rc(STW, 0.66 - v * 0.35, x, y), 3, { m: MAT.STONE, b: 6 }));
  // the window: bamboo lattice over a paper screen (glows when lit)
  const wx0 = wl + 12, wx1 = wl + 34, wy0 = gy - 32, wy1 = gy - 20;
  for (let y = wy0; y <= wy1; y++) for (let x = wx0; x <= wx1; x++) {
    const bar = (x - wx0) % 3 === 0; const frame = x === wx0 || x === wx1 || y === wy0 || y === wy1;
    const c = frame ? WDK[1] : bar ? PAL.bambooOld[2] : o.lit ? [236, 196, 128] : [188, 178, 156];
    s.pz(x, y, c, 7, { m: frame || bar ? MAT.WOOD : MAT.PAPER, b: 1, e: (!frame && !bar && o.lit) ? 5 : 0 });
  }
  // firewood stacked under the eave (left)
  for (let r = 0; r < 4; r++) for (let k = 0; k < 7; k++) { const lx = wl - 1 + k * 4 + (r % 2) * 2, ly = gy - 4 - r * 4; PX.ell(lx + 2, ly, 2.2, 2, (x, y, u, v, d) => s.pz(x, y, d > 0.7 ? PAL.barkCedar[1] : [176 - r * 6, 138, 92], 12 + (1 - d), { m: MAT.WOOD, b: 4 + r })); }
  // straw bundles (藁束) and a barrel (right)
  for (let k = 0; k < 3; k++) { const bx = wr - 14 + k * 7, by = gy - 2; for (let y = by - 16; y <= by; y++) for (let x = bx - 3; x <= bx + 3; x++) { const tie = y === by - 11 || y === by - 4; s.pz(x, y, tie ? PAL.rope[1] : rc(STR, 0.5 - (x - bx) * 0.08 + (y < by - 13 ? 0.15 : 0) + hash2(x, y >> 1, k) * 0.12, x, y), 13, { m: MAT.STRAW, b: 5 }); } }
  { const bx = wl + 44, by = gy; for (let y = by - 13; y <= by; y++) for (let x = bx - 5; x <= bx + 5; x++) { const hoop = y === by - 11 || y === by - 3; const sx = (x - bx) / 5.5; s.pz(x, y, hoop ? PAL.bambooOld[1] : rc(PAL.wood, 0.55 - sx * 0.3, x, y), 14, { m: MAT.WOOD, b: 6, n: cylN(sx) }); }
    PX.ell(bx, by - 14, 5, 1.6, (x, y) => s.pz(x, y, [44, 62, 66], 15, { m: MAT.GLASS, b: 6 })); }
  // the rack of back-frames (背負子) beside the door
  for (let k = 0; k < 2; k++) { const fx = dr + 6 + k * 9;
    for (let y = gy - 30; y <= gy - 3; y++) { s.pz(fx, y, PAL.woodNew[2], 15, { m: MAT.WOOD, b: 7 }); s.pz(fx + 6, y, PAL.woodNew[1], 15, { m: MAT.WOOD, b: 7 }); }
    for (const cy of [gy - 26, gy - 18, gy - 8]) for (let x = fx; x <= fx + 6; x++) s.pz(x, cy, PAL.woodNew[3], 15.5, { m: MAT.WOOD, b: 7 });
    for (let y = gy - 24; y <= gy - 12; y++) { s.pz(fx + 1, y, PAL.rope[2], 16, { m: MAT.ROPE, b: 7 }); s.pz(fx + 5, y, PAL.rope[1], 16, { m: MAT.ROPE, b: 7 }); } }
  // hanging under the eave: a straw raincoat, dried persimmons, a coil of rope, the lantern
  for (let y = gy - 38; y <= gy - 22; y++) { const hw = 2 + (y - (gy - 38)) * 0.35; for (let x = Math.round(wl + 6 - hw); x <= wl + 6 + hw; x++) s.pz(x, y, rc(STR, 0.35 + hash2(x, y >> 1, 2) * 0.25 - Math.abs(x - wl - 6) * 0.04, x, y), 9, { m: MAT.STRAW, b: 3 }); }
  for (const kx of [wx1 + 4, wx1 + 8]) for (let k = 0; k < 4; k++) { const y = gy - 36 + k * 3; s.pz(kx, y, [206, 104, 44], 10, { m: MAT.FOOD, b: 3 }); s.pz(kx + 1, y, [168, 80, 34], 10, { m: MAT.FOOD, b: 3 }); s.pz(kx, y + 1, [150, 70, 30], 10, { m: MAT.FOOD, b: 3 }); }
  PX.ell(dr + 4, gy - 35, 3, 2.5, (x, y, u, v, d) => { if (d > 0.45) s.pz(x, y, PAL.rope[d > 0.8 ? 1 : 3], 10, { m: MAT.ROPE, b: 3 }); });
  { const lx = dl - 4, ly = gy - 37; // a paper lantern by the door
    s.pz(lx, ly - 3, WDK[0], 11, { m: MAT.WOOD, b: 3 }); s.pz(lx, ly - 2, WDK[0], 11, { m: MAT.WOOD, b: 3 });
    PX.ell(lx, ly + 3, 3, 4.5, (x, y, u, v, d) => s.pz(x, y, o.lit ? [255 - d * 40, 196 - d * 50, 110 - d * 40] : rc(PAL.paper, 0.6 - u * 0.25 - v * 0.15, x, y), 12, { m: o.lit ? MAT.LAMP : MAT.PAPER, b: 4, e: o.lit ? 6 : 0 }));
    for (let x = lx - 2; x <= lx + 2; x++) { s.pz(x, ly - 1, WDK[0], 12.5, { m: MAT.WOOD, b: 4 }); s.pz(x, ly + 7, WDK[0], 12.5, { m: MAT.WOOD, b: 4 }); } }
  // ---- the roof: a hipped thatch roof seen from the south and above. Front slope (trapezoid), a lit
  // west hip and a shaded east hip, rounded courses, a thick trimmed eave, moss where it stays damp.
  const eaveY = gy - wallH - 1, ridgeY = eaveY - 60, eaveHalf = 70, ridgeHalf = 30;
  const thick = 10;
  for (let y = ridgeY; y <= eaveY + thick; y++) {
    const t = clamp((y - ridgeY) / (eaveY - ridgeY), 0, 1);
    const ow = lerp(eaveHalf - 16, eaveHalf, Math.sqrt(t));        // outline, rounded outward
    const fw = lerp(ridgeHalf, eaveHalf - 6, t);                    // the front facet
    for (let x = Math.round(cx - ow); x <= Math.round(cx + ow); x++) {
      const dx = x - cx, ad = Math.abs(dx), u = dx / eaveHalf;
      let c, mat = MAT.STRAW, n, bulge;
      if (y > eaveY) { // the cut face of the eave: straw butts, lighter, a dark line underneath
        const k = y - eaveY; const butt = hash2(x, 7, 3);
        c = k >= thick - 1 ? WDK[0] : rc(PAL.thatch, 0.66 - k * 0.04 + (butt - 0.5) * 0.16 - u * 0.12 - (k > thick - 4 ? 0.12 : 0), x, y, 0.25);
        n = [u * 0.4, -0.1, 1]; bulge = 14;
      } else {
        const hip = ad > fw; const course = Math.floor((y - ridgeY + (hip ? 4 : 0)) / 9), cf = ((y - ridgeY + (hip ? 4 : 0)) % 9) / 9;
        const strand = hash2(x, course * 13 + (y >> 2), 11);
        let tt = 0.5 + (strand - 0.5) * 0.18 + (cf < 0.35 ? 0.08 : cf > 0.8 ? -0.12 : 0) - u * 0.1;
        if (hip) tt += dx < 0 ? 0.1 : -0.13;
        if (ad > ow - 2) tt -= 0.1;
        c = rc(PAL.thatch, tt, x, y, 0.3); n = hip ? [dx < 0 ? -0.6 : 0.6, 0.4, 0.7] : [0, 0.55, 0.83];
        // moss: organic patches, damper toward the eave and on the shaded side
        const mz = vnoise(x * 0.07, y * 0.09, 21) * 0.7 + vnoise(x * 0.25, y * 0.25, 22) * 0.3 + t * 0.12 + u * 0.08;
        if (mz > 0.8) { c = rc(PAL.mossDeep, 0.42 + (mz - 0.8) * 2.2 - u * 0.15 + (cf < 0.35 ? 0.1 : 0), x, y); mat = MAT.MOSS; }
        bulge = lerp(-40, 12, t);
      }
      s.pz(x, y, c, 30 + (1 - t) * 3, { m: mat, b: bulge, n });
    }
  }
  // a few weeds sprouting from the thatch
  for (let k = 0; k < 7; k++) { const x = Math.round(cx + (hash2(k, 1, 31) - 0.5) * 90), y = Math.round(ridgeY + 20 + hash2(k, 2, 31) * 30); for (let j = 0; j < 3; j++) if (s.a(x + (j - 1), y - j)) s.px(x + (j - 1) * (j & 1), y - j, PAL.fern[3 + (j & 1)], { m: MAT.LEAF, z: 36, b: -10 }); }
  // the ridge: bundled straw wrapped in bark, bamboo ties, crossed poles at both ends
  for (let y = ridgeY - 8; y <= ridgeY + 1; y++) for (let x = cx - ridgeHalf - 6; x <= cx + ridgeHalf + 6; x++) {
    const v = (y - (ridgeY - 8)) / 9, tie = (x - cx + 64) % 12 < 2;
    s.pz(x, y, tie ? PAL.bambooOld[v < 0.5 ? 3 : 1] : v < 0.55 ? rc(PAL.barkCedar, 0.66 - v * 0.6, x, y) : rc(PAL.thatch, 0.34 - (v - 0.55) * 0.5, x, y), 40, { m: v < 0.55 ? MAT.BARK : MAT.STRAW, b: -40 });
  }
  for (const ex of [cx - ridgeHalf - 2, cx + ridgeHalf + 2]) for (let k = -6; k <= 6; k++) { s.pz(ex + k * 0.55, ridgeY - 9 - Math.abs(k) * 0.9, WDK[2], 42, { m: MAT.WOOD, b: -38 }); s.pz(ex - k * 0.55, ridgeY - 9 - Math.abs(k) * 0.9, WDK[3], 42, { m: MAT.WOOD, b: -38 }); }
  POST.ao(s, 2, 0.16); POST.outline(s, { k: 0.6 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, sway: 0, occluder: true, kind: 'building', smokeH: gy - ridgeY + 6 } };
}

/* ===================== the shrine 祠 (one eave corner fallen) ===================== */
export function shrine(o = {}) {
  const W = 64, H = 70, s = new SB(W, H), cx = 32, gy = H - 3, R = RNG(8);
  // two-tier stone base
  box(s, cx - 17, cx + 16, gy, 6, 5, { z: 2, m: MAT.STONE, top: (x, y, u) => [rc(ST, 0.7 - u * 0.15 + (hash2(x >> 2, y, 3) - 0.5) * 0.15, x, y)], front: (x, y, u, v) => [rc(ST, 0.42 - u * 0.12 + (hash2(x >> 3, 1, 3) - 0.5) * 0.2 + v * 0.1, x, y)] });
  box(s, cx - 12, cx + 11, gy - 10, 5, 4, { z: 4, m: MAT.STONE, b: -5, top: (x, y, u) => [rc(ST, 0.72 - u * 0.15, x, y)], front: (x, y, u, v) => [rc(ST, 0.45 - u * 0.12 + v * 0.1, x, y)] });
  for (let k = 0; k < 18; k++) { const x = cx - 17 + R.int(0, 33), y = gy - R.int(0, 9); if (s.a(x, y) && R() < 0.6) s.px(x, y, PAL.moss[R.int(2, 4)], { m: MAT.MOSS }); }
  // the wooden body with latticed doors
  const bt = gy - 38, bb = gy - 18;
  for (let y = bt; y <= bb; y++) for (let x = cx - 10; x <= cx + 9; x++) {
    const post = x <= cx - 9 || x >= cx + 8; const lat = !post && ((x - cx) % 3 === 0 || (y - bt) % 4 === 0); const inside = !post && !lat;
    s.pz(x, y, post ? rc(WOOD, 0.5 - (x > cx ? 0.2 : 0), x, y) : lat ? rc(PAL.wood, 0.55, x, y) : [36, 30, 30], 8, { m: MAT.WOOD, b: -8 });
  }
  // the holed stone inside, faintly lit
  PX.ell(cx, bb - 6, 2.6, 2.6, (x, y, u, v, d) => { if (d > 0.4) s.pz(x, y, rc(ST, 0.7 - v * 0.3, x, y), 9, { m: MAT.STONE, b: -8, e: 1 }); });
  // shimenawa across the front, shide hanging
  for (let x = cx - 12; x <= cx + 11; x++) { const y = bt + 2 + Math.round(Math.pow((x - cx) / 12, 2) * -2 + 2); s.pz(x, y, PAL.rope[(x & 2) ? 3 : 1], 12, { m: MAT.ROPE, b: -4 }); s.pz(x, y + 1, PAL.rope[0], 11.8, { m: MAT.ROPE, b: -4 }); }
  for (const sx of [-7, 0, 7]) shide(s, cx + sx, bt + 4, 12.5);
  // offerings on the base: a sake cup, a sprig of sakaki in a vase
  s.pz(cx - 8, gy - 11, [230, 226, 214], 10, { m: MAT.LACQUER, b: -3 }); s.pz(cx - 7, gy - 11, [210, 206, 196], 10, { m: MAT.LACQUER, b: -3 });
  for (let y = gy - 16; y <= gy - 11; y++) s.pz(cx + 8, y, [120, 140, 150], 10, { m: MAT.GLASS, b: -3 });
  PX.ell(cx + 8, gy - 19, 3, 3, (x, y, u, v, d) => s.pz(x, y, rc(PAL.broad, 0.6 - v * 0.3, x, y), 10.5, { m: MAT.LEAF, b: -3 }));
  // the roof: bark-shingled gable seen from above; the right eave corner has lost its beam and sags
  const re = gy - 40, rt = re - 22;
  for (let y = rt; y <= re + 3; y++) {
    const t = (y - rt) / (re + 3 - rt);
    const hw = lerp(8, 25, Math.pow(t, 0.75));
    for (let x = Math.round(cx - hw); x <= Math.round(cx + hw); x++) {
      const u = (x - cx) / 25; let yy = y;
      if (u > 0.45) { // the broken corner: boards drooping, gaps
        const k = (u - 0.45) / 0.55; yy = Math.round(y + k * k * 9 + (t > 0.8 ? k * 3 : 0)); if (hash2(x, y >> 1, 4) < k * 0.35) continue;
      }
      const row = Math.floor((y - rt) / 3), shingle = (x + (row % 2) * 2) % 4 === 0;
      let tt = 0.52 - u * 0.2 + (row % 2 ? 0.06 : -0.02) - (shingle ? 0.16 : 0) + (y === rt ? 0.18 : 0);
      if (y > re) tt = 0.25 - (y - re) * 0.05;
      s.pz(x, yy, rc(PAL.barkCedar, tt, x, yy), 20 + (1 - Math.abs(u)) * 3 - t * 2, { m: MAT.WOOD, b: lerp(-20, 4, t) });
    }
  }
  // the surviving front beam (left half) and exposed rafter ends on the right
  for (let x = cx - 26; x <= cx + 10; x++) { const e = Math.abs(x - cx) / 26, y = re + 3 - Math.round(Math.pow(e, 3) * 3); s.pz(x, y, PAL.woodGrey[4], 24, { m: MAT.WOOD, b: 5 }); s.pz(x, y + 1, PAL.woodGrey[1], 23, { m: MAT.WOOD, b: 5 }); }
  for (const rx of [cx + 14, cx + 18, cx + 22]) for (let k = 0; k < 4; k++) s.pz(rx, re + 2 + k + Math.round((rx - cx - 12) * 0.4), PAL.woodGrey[2 - (k >> 1)], 23, { m: MAT.WOOD, b: 4 });
  for (let x = cx - 5; x <= cx + 5; x++) s.pz(x, rt - 1, PAL.barkCedar[5], 25, { m: MAT.WOOD, b: -20 }); // ridge
  POST.ao(s, 2, 0.15); POST.outline(s, { k: 0.62 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, sway: 0, occluder: false, kind: 'shrine' } };
}

/** the fallen eave beam: a ~2.4 m weathered timber lying on the ground, one end splintered */
export function eaveBeam() {
  const W = 56, H = 18, s = new SB(W, H), L = 48, ang = 0.22;
  const x0 = 4, y0 = 5;
  for (let k = 0; k < L; k++) for (let w = 0; w < 4; w++) {
    const x = Math.round(x0 + k * Math.cos(ang)), y = Math.round(y0 + k * Math.sin(ang) + w);
    const top = w < 2; const grain = hash2(k >> 2, w, 3);
    let t = top ? 0.6 + grain * 0.14 - (w === 1 ? 0.06 : 0) : 0.3 + grain * 0.1;
    if (k === 14 || k === 31) t -= 0.25; // nail holes
    s.pz(x, y, rc(PAL.woodGrey, t, x, y), 3 - w * 0.2, { m: MAT.WOOD });
  }
  for (let k = 0; k < 6; k++) { const x = Math.round(x0 + (L + k * 0.5) * Math.cos(ang)), y = Math.round(y0 + (L) * Math.sin(ang) + (k % 3)); s.pz(x, y, PAL.woodNew[2 + (k % 2)], 3, { m: MAT.WOOD }); } // splinters
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  flat(s, 13, 2);
  return { s, meta: { ax: 28, ay: 13, sway: 0, kind: 'item' } };
}

/* ===================== 道祖神: a pair of figures in relief, one under a very wide hat ===================== */
export function dosojin() {
  // 双体道祖神: a natural slab with a deep boat-shaped niche and two figures in high relief, shoulder
  // to shoulder, hands joined; the left one under a very wide hat. Readable as two people at 1×: the
  // niche is near-black, the figures are lit, a dark seam separates them down to the joined hands,
  // and the hat brim is twice the width of a head and throws a hard shadow.
  const W = 44, H = 48, s = new SB(W, H), cx = 22, gy = H - 2;
  const SW = ramp('#8e877a', 8, { lo: 0.72, hi: 0.52, hueShift: 0.05 });
  const st = (x, y, t, z, b, n) => s.pz(x, y, SW[clamp(Math.round(t), 0, 7)], z, { m: MAT.STONE, b, n });
  // a low base stone
  PX.ell(cx, gy - 1, 14, 3, (x, y, u, v, d) => st(x, y, 3.2 - u * 1.2 - v * 1.4, 2, 1 + (1 - d) * 2, [u * 0.5, -v * 0.6, 0.6]), { amp: 0.15, seed: 8 });
  // the slab
  PX.ell(cx, gy - 20, 16.5, 21.5, (x, y, u, v, d) => { if (y > gy - 2) return; st(x, y, 3.6 - u * 1.6 - v * 0.9 + (hash2(x >> 1, y >> 1, 4) - 0.5) * 0.7 - (d > 0.9 ? 0.6 : 0), 4 + (1 - d) * 3, 3 + (1 - d) * 4, [u * 0.6, -v * 0.5, 0.7]); }, { amp: 0.1, seed: 3 });
  // the niche: deep shade inside (the figures stand out against it), a lit lower lip
  PX.ell(cx, gy - 19, 13.5, 17.5, (x, y, u, v, d) => { if (y > gy - 4) return; const lip = d > 0.88; st(x, y, lip ? (v > 0.3 ? 4.6 : u < -0.2 ? 3.2 : 0.4) : 0.55 + Math.max(0, v) * 0.7 + (hash2(x >> 1, y >> 1, 9) < 0.15 ? 0.6 : 0), 8, 4); });
  // the figures (heads, shoulders, robes); lit = base tone (left brighter: it faces the light).
  const fig = (fx, lit, hat, side) => {
    for (let y = gy - 20; y <= gy - 5; y++) { const k = (y - (gy - 20)) / 15, hw = 2.3 + Math.sqrt(k) * 1.9; for (let x = Math.round(fx - hw); x <= Math.round(fx + hw); x++) { const u = (x - fx) / hw; st(x, y, lit + 1 - u * 1.6 - (Math.abs(u) > 0.8 ? 1 : 0), 10, 6, [u * 0.6, 0, 0.8]); } }
    for (let y = gy - 16; y <= gy - 8; y += 4) st(Math.round(fx + side), y, lit - 0.9, 10.5, 6);       // robe folds
    PX.ell(fx, gy - 23.5, 3, 3.1, (x, y, u, v) => st(x, y, lit + 1.7 - u * 1.5 - v * 0.9, 11, 7, [u * 0.7, -v * 0.6, 0.6]));
    if (hat) { // a very wide flat hat: lit top, dark brim, against the dark of the niche above it
      for (let x = Math.round(fx - 7); x <= Math.round(fx + 7); x++) { const u = (x - fx) / 7;
        st(x, gy - 28, lit + 2.4 - u * 1.4, 12, 8); st(x, gy - 27, lit - 1.5 - u * 0.4, 12, 8);
        if (Math.abs(u) < 0.55) st(x, gy - 29, lit + 2.2 - u * 1.4, 12, 8);
        if (Math.abs(u) < 0.2) st(x, gy - 30, lit + 2, 12, 8); }
    }
  };
  fig(cx - 5, 4.4, true, 1); fig(cx + 5, 3.3, false, -1);
  for (let x = cx - 2; x <= cx + 2; x++) { st(x, gy - 12, 5.2, 11, 6); st(x, gy - 11, 4, 11, 6); st(x, gy - 10, 1.6, 11, 6); } // joined hands
  // weathering: moss on the crown and down the shaded side, lichen spots
  for (let k = 0; k < 60; k++) { const x = Math.round(cx - 14 + hash2(k, 1, 5) * 28), y = Math.round(gy - 40 + hash2(k, 2, 5) * 6 + (x > cx + 9 ? hash2(k, 7, 5) * 20 : 0)); if (s.a(x, y) && s.z[y * W + x] < 8 && hash2(k, 3, 5) < 0.8) s.px(x, y, PAL.moss[2 + (k % 3)], { m: MAT.MOSS }); }
  for (let k = 0; k < 14; k++) { const x = Math.round(cx - 13 + hash2(k, 4, 5) * 26), y = Math.round(gy - 36 + hash2(k, 6, 5) * 30); if (s.a(x, y) && s.m[y * W + x] === MAT.STONE && s.z[y * W + x] < 8) s.px(x, y, PAL.lichen[2], { m: MAT.STONE }); }
  POST.outline(s, { k: 0.6 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, kind: 'statue' } };
}
/** the stone offering ledge before the statues, with small offerings */
export function offeringLedge() {
  const W = 30, H = 14, s = new SB(W, H), gy = H - 2;
  for (const lx of [6, 23]) box(s, lx - 2, lx + 2, gy, 3, 2, { z: 1, m: MAT.STONE, top: (x, y) => [ST[4]], front: (x, y, u) => [rc(ST, 0.4 - u * 0.1, x, y)] });
  box(s, 2, 27, gy - 3, 2, 5, { z: 3, m: MAT.STONE, b: 0, top: (x, y, u, v) => [rc(PAL.stoneWarm, 0.68 - u * 0.12 - v * 0.08 + (hash2(x, y, 6) - 0.5) * 0.1, x, y)], front: (x, y, u) => [rc(PAL.stoneWarm, 0.36 - u * 0.1, x, y)] });
  // a tiny cup, a sandal (waraji), coins, a few flowers
  s.pz(7, gy - 7, [232, 228, 216], 6, { m: MAT.LACQUER }); s.pz(8, gy - 7, [206, 200, 190], 6, { m: MAT.LACQUER });
  for (let y = gy - 9; y <= gy - 6; y++) for (let x = 12; x <= 14; x++) s.pz(x, y, (x + y) % 2 ? STR[3] : STR[2], 6, { m: MAT.STRAW });
  s.pz(18, gy - 7, [176, 140, 64], 6, { m: MAT.METAL }); s.pz(20, gy - 8, [150, 118, 54], 6, { m: MAT.METAL });
  for (const [x, c] of [[23, PAL.flowerYellow], [24, PAL.flowerWhite], [22, PAL.flowerPink]]) { s.pz(x, gy - 10, c, 7, { m: MAT.PETAL }); s.pz(x, gy - 9, PAL.fern[2], 6.5, { m: MAT.LEAF }); }
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  flat(s, gy + 1, 4);
  return { s, meta: { ax: 15, ay: gy + 1, kind: 'item' } };
}

/* ===================== nine nameless graves 無縁仏 ===================== */
export function grave(v) {
  const W = 16, H = 20, s = new SB(W, H), cx = 8, gy = H - 2, R = RNG(v * 13 + 7);
  const SG = R() < 0.5 ? ramp('#7c7a72', 6, { lo: 0.55, hi: 0.45 }) : ramp('#86806f', 6, { lo: 0.55, hi: 0.45 });
  const tilt = [0, 0.12, -0.08, 0, 0.2, 0, -0.15, 0.06, 0][v % 9];
  const kind = [0, 1, 2, 0, 3, 1, 0, 4, 2][v % 9];
  const P = (x, y, t, z = 4, m = MAT.STONE) => { const xx = Math.round(cx + (x - cx) + (gy - y) * tilt); s.pz(xx, y, rc(SG, t, xx, y), z, { m, b: 2 }); };
  if (kind === 0) { // boat-shaped stele with a worn seated Buddha in relief
    for (let y = gy - 13; y <= gy; y++) { const k = (y - (gy - 13)) / 13; const hw = k < 0.3 ? 2 + k * 10 : 5; for (let x = cx - hw; x <= cx + hw - 1; x++) P(x, y, 0.55 - (x - cx) * 0.06 - k * 0.1); }
    for (let y = gy - 9; y <= gy - 2; y++) for (let x = cx - 2; x <= cx + 1; x++) if (y > gy - 8 || Math.abs(x - cx + 0.5) < 1) P(x, y, 0.36, 5);
    P(cx - 1, gy - 10, 0.4, 5); P(cx, gy - 10, 0.4, 5);
  } else if (kind === 1) { // a rounded natural stone
    PX.ell(cx, gy - 5, 5, 5.5, (x, y, u, vv, d) => P(x, y, 0.62 - u * 0.25 - vv * 0.2));
  } else if (kind === 2) { // a square post with a worn inscription
    for (let y = gy - 12; y <= gy; y++) for (let x = cx - 3; x <= cx + 2; x++) P(x, y, y < gy - 11 ? 0.72 : 0.5 - (x - cx) * 0.08 - (x === cx - 1 && y > gy - 10 && y < gy - 2 && (y & 1) ? 0.22 : 0));
  } else if (kind === 3) { // a five-ring pagoda fragment: cube, sphere, a broken top
    for (let y = gy - 4; y <= gy; y++) for (let x = cx - 4; x <= cx + 3; x++) P(x, y, 0.5 - (x - cx) * 0.06);
    PX.ell(cx - 0.5, gy - 7, 3.2, 3, (x, y, u, vv) => P(x, y, 0.62 - u * 0.25 - vv * 0.2, 5));
    for (let x = cx - 3; x <= cx + 2; x++) P(x, gy - 11 + (x > cx ? 1 : 0), 0.6 - (x - cx) * 0.08, 6);
  } else { // a broken stele, its top lying beside it
    for (let y = gy - 7; y <= gy; y++) for (let x = cx - 3; x <= cx + 2; x++) P(x, y, 0.5 - (x - cx) * 0.08 + (y === gy - 7 ? 0.15 : 0));
    for (let x = cx + 3; x <= cx + 7; x++) for (let y = gy - 1; y <= gy; y++) s.pz(x, y, rc(SG, 0.55 - (y - gy + 1) * 0.2, x, y), 3, { m: MAT.STONE, b: 4 });
  }
  // moss on the shoulders, a dark foot
  for (let k = 0; k < 12; k++) { const x = R.int(cx - 5, cx + 5), y = R.int(gy - 14, gy - 4); if (s.a(x, y) && !s.a(x, y - 1)) s.px(x, y, PAL.moss[R.int(2, 4)], { m: MAT.MOSS }); }
  for (let x = 0; x < W; x++) if (s.a(x, gy)) s.mul(x, gy, 0.8);
  POST.outline(s, { k: 0.6 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, kind: 'grave' } };
}
/** a short bamboo pole with a hook at the top for a bon lantern; the hook is 1.05 m up */
export function lanternPole(v = 0) {
  const W = 8, H = 26, s = new SB(W, H), cx = 3, gy = H - 2;
  for (let y = 4; y <= gy; y++) { const node = (y + v) % 8 === 0; s.pz(cx, y, PAL.bambooOld[node ? 1 : 3], 3, { m: MAT.BAMBOO, b: 1 }); s.pz(cx + 1, y, PAL.bambooOld[node ? 0 : 2], 3, { m: MAT.BAMBOO, b: 1 }); }
  for (let k = 0; k < 3; k++) s.pz(cx + 2 + k, 4 - (k === 2 ? 1 : 0), PAL.bambooOld[2], 3.5, { m: MAT.BAMBOO, b: 1 }); // the arm
  s.pz(cx + 4, 4, WDK[0], 3.6, { m: MAT.METAL, b: 1 }); s.pz(cx + 4, 5, WDK[0], 3.6, { m: MAT.METAL, b: 1 }); // the hook
  POST.outline(s, { k: 0.7 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, kind: 'pole', hook: [cx + 4, 5] } };
}
/** 盆提灯: a white paper bon lantern, faint crest; anchor at its hanging point (top) */
export function bonLantern(lit = false) {
  const W = 9, H = 16, s = new SB(W, H), cx = 4;
  s.pz(cx, 0, WDK[0], 2, { m: MAT.ROPE }); s.pz(cx, 1, WDK[0], 2, { m: MAT.ROPE }); // cord
  for (let x = cx - 2; x <= cx + 2; x++) { s.pz(x, 2, PAL.lacquer[1], 3, { m: MAT.LACQUER }); s.pz(x, 3, PAL.lacquer[2], 3, { m: MAT.LACQUER }); s.pz(x, 13, PAL.lacquer[1], 3, { m: MAT.LACQUER }); }
  PX.ell(cx + 0.5, 8.5, 4, 5, (x, y, u, v, d) => {
    if (y < 4 || y > 12) return;
    const rib = (y - 4) % 2 === 0;
    const c = lit ? [255 - d * 30 - (rib ? 18 : 0), 226 - d * 60 - (rib ? 24 : 0), 150 - d * 70 - (rib ? 20 : 0)] : rc(PAL.paper, 0.74 - u * 0.3 - v * 0.1 - (rib ? 0.12 : 0), x, y);
    s.pz(x, y, c, 4 + (1 - d), { m: lit ? MAT.LAMP : MAT.PAPER, e: lit ? (d < 0.6 ? 7 : 5) : 0, n: [u * 0.8, -v * 0.3, Math.sqrt(Math.max(0.1, 1 - u * u))] });
  });
  // a faint family crest (a small ring)
  for (const [dx, dy] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) { const x = cx + dx, y = 8 + dy; if (s.a(x, y)) s.px(x, y, lit ? [222, 168, 100] : [150, 150, 152], { m: lit ? MAT.LAMP : MAT.PAPER, e: lit ? 4 : 0 }); }
  s.pz(cx, 14, PAL.rope[1], 3, { m: MAT.ROPE }); // tassel
  if (!lit) POST.outline(s, { k: 0.72 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: 0, kind: 'lantern', shadow: lit ? 0 : 1 } };
}
/** 精霊馬: a cucumber horse and an eggplant cow on a flat stone */
export function spiritAnimals() {
  const W = 22, H = 12, s = new SB(W, H), gy = H - 2;
  box(s, 1, 20, gy, 2, 4, { z: 1, m: MAT.STONE, top: (x, y, u, v) => [rc(PAL.stoneWarm, 0.66 - u * 0.15 - v * 0.08, x, y)], front: (x, y, u) => [rc(PAL.stoneWarm, 0.34 - u * 0.1, x, y)] });
  const animal = (x0, len, h, col, colD) => {
    for (const lx of [x0 + 1, x0 + 2, x0 + len - 3, x0 + len - 2]) for (let y = gy - 5; y <= gy - 4; y++) s.pz(lx, y, [196, 168, 112], 4, { m: MAT.WOOD }); // stick legs
    for (let x = x0; x < x0 + len; x++) for (let y = gy - 5 - h; y < gy - 5; y++) { const top = y === gy - 5 - h; s.pz(x, y, top ? col : colD, 5, { m: MAT.FOOD }); }
    s.pz(x0 - 1, gy - 6 - h + 1, colD, 5, { m: MAT.FOOD }); // the stem end as a head
  };
  animal(3, 8, 2, [116, 160, 74], [70, 112, 50]);   // cucumber horse: long and green
  animal(13, 6, 3, [98, 64, 118], [62, 38, 82]);    // eggplant cow: short and purple
  s.pz(12, gy - 9, [92, 120, 60], 6, { m: MAT.FOOD }); // the eggplant's calyx
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  flat(s, gy + 1, 3);
  return { s, meta: { ax: 11, ay: gy + 1, kind: 'item' } };
}

/* ===================== her things ===================== */
/** 旧背負子: an old wooden back-frame with straw straps, leaning (against a wall) */
export function oldBackFrame() {
  const W = 18, H = 30, s = new SB(W, H), gy = H - 2, lean = 0.18;
  const P = (x, y, c, z = 4, m = MAT.WOOD) => s.pz(Math.round(x + (gy - y) * lean), y, c, z, { m, b: 2 });
  for (let y = gy - 25; y <= gy; y++) { P(4, y, WOOD[3]); P(5, y, WOOD[2]); P(11, y, WOOD[2]); P(12, y, WOOD[1]); }
  for (const cy of [gy - 22, gy - 15, gy - 8]) for (let x = 4; x <= 12; x++) P(x, cy, WOOD[cy === gy - 15 ? 4 : 3]);
  for (let x = 2; x <= 14; x++) { P(x, gy - 2, WOOD[3], 5); P(x, gy - 1, WOOD[1], 5); } // the shelf
  for (let y = gy - 21; y <= gy - 9; y++) { P(6.5 - (y > gy - 12 ? 1 : 0), y, PAL.rope[2], 5, MAT.ROPE); P(10 + (y > gy - 12 ? 1 : 0), y, PAL.rope[1], 5, MAT.ROPE); }
  POST.outline(s, { k: 0.64 }); POST.normals(s, 1);
  return { s, meta: { ax: 9, ay: gy + 1, kind: 'item' } };
}
/** her load: a wicker box (葛籠) and cloth bundles, leanable against the camphor's roots */
export function load() {
  const W = 22, H = 24, s = new SB(W, H), gy = H - 2, WK = PAL.wicker;
  for (let y = gy - 12; y <= gy; y++) for (let x = 3; x <= 18; x++) { const weave = ((x >> 1) + (y >> 1)) % 2; const edge = x === 3 || x === 18 || y === gy - 12; s.pz(x, y, edge ? WK[1] : rc(WK, 0.55 + (weave ? 0.12 : -0.08) - (x - 3) / 15 * 0.2, x, y), 4, { m: MAT.STRAW, b: 3 }); }
  for (let x = 2; x <= 19; x++) for (let y = gy - 15; y <= gy - 12; y++) s.pz(x, y, rc(WK, 0.7 - (y - gy + 15) * 0.1 - (x - 2) / 17 * 0.15, x, y), 5, { m: MAT.STRAW, b: 3 });
  for (let x = 3; x <= 18; x++) s.pz(x, gy - 6, PAL.clothRed[2], 4.5, { m: MAT.CLOTH, b: 3 }); // a red cord
  // cloth bundles on top: indigo and ochre, knotted
  PX.ell(8, gy - 18, 5, 3.5, (x, y, u, v) => s.pz(x, y, rc(PAL.cloth, 0.6 - u * 0.25 - v * 0.2, x, y), 7, { m: MAT.CLOTH, b: 4 }));
  PX.ell(15, gy - 18, 4, 3, (x, y, u, v) => s.pz(x, y, rc(PAL.clothOchre, 0.6 - u * 0.25 - v * 0.2, x, y), 6.5, { m: MAT.CLOTH, b: 4 }));
  for (const [x, y] of [[7, gy - 22], [8, gy - 22], [9, gy - 21], [6, gy - 21]]) s.pz(x, y, PAL.cloth[2], 8, { m: MAT.CLOTH, b: 4 }); // the knot
  POST.outline(s, { k: 0.62 }); POST.normals(s, 1);
  return { s, meta: { ax: 11, ay: gy + 1, kind: 'item' } };
}
/** a dango plate: state 2 (two white dango), 1 (one), 'pale' (one, gone pale) */
export function dango(state = 2) {
  const W = 12, H = 8, s = new SB(W, H), gy = H - 2;
  PX.ell(6, gy - 1, 5, 1.8, (x, y, u, v, d) => s.pz(x, y, d > 0.75 ? [150, 140, 128] : [214, 206, 190], 1, { m: MAT.LACQUER }));
  const ball = (bx, pale) => PX.ell(bx, gy - 3, 1.8, 1.7, (x, y, u, v, d) => s.pz(x, y, pale ? [196, 204, 220].map(c => c - d * 18) : [252 - d * 30, 248 - d * 34, 236 - d * 40], 3, { m: MAT.FOOD }));
  if (state === 2) { ball(4.5, false); ball(7.5, false); } else ball(6, state === 'pale');
  POST.outline(s, { k: 0.7 }); POST.normals(s, 1);
  return { s, meta: { ax: 6, ay: gy + 1, kind: 'item', shadow: 0 } };
}

/* ===================== signs, stones, small things ===================== */
/** 道標: a squared stone post with carved characters */
export function michishirube(seed = 1) {
  const W = 12, H = 28, s = new SB(W, H), gy = H - 2;
  box(s, 3, 8, gy, 20, 3, { z: 3, m: MAT.STONE, top: (x, y, u) => [rc(PAL.stoneWarm, 0.75 - u * 0.2, x, y)], front: (x, y, u, v) => { const carve = x === 5 || x === 6; const mark = carve && ((gy - y) % 3 !== 0) && (gy - y) > 3 && (gy - y) < 18 && hash2(x, y, seed) < 0.7; return [rc(PAL.stoneWarm, mark ? 0.2 : 0.52 - u * 0.25 + (hash2(x, y >> 1, seed + 2) - 0.5) * 0.1, x, y)]; } });
  for (let k = 0; k < 6; k++) { const x = 3 + (k % 3) * 2, y = gy - 21 + (k >> 1); if (s.a(x, y)) s.px(x, y, PAL.moss[3], { m: MAT.MOSS }); }
  POST.outline(s, { k: 0.64 }); POST.normals(s, 1);
  return { s, meta: { ax: 6, ay: gy + 1, kind: 'sign' } };
}
/** a wooden signboard on a post, weathered ink */
export function signboard() {
  const W = 26, H = 32, s = new SB(W, H), gy = H - 2;
  for (let y = gy - 26; y <= gy; y++) { s.pz(12, y, WOOD[3], 3, { m: MAT.WOOD }); s.pz(13, y, WOOD[1], 3, { m: MAT.WOOD }); }
  box(s, 3, 22, gy - 16, 8, 2, { z: 5, m: MAT.WOOD, top: (x, y) => [WOOD[4]], front: (x, y, u, v) => { const ink = x > 5 && x < 20 && ((x - 6) % 4 < 2) && v > 0.2 && v < 0.85 && hash2(x, y, 4) < 0.6; return [ink ? [58, 52, 50] : rc(WOOD, 0.58 - u * 0.2 + ((x * 7 + y) % 5 === 0 ? -0.08 : 0), x, y)]; } });
  s.pz(22, gy - 25, PAL.moss[3], 6, { m: MAT.MOSS }); s.pz(21, gy - 25, PAL.moss[2], 6, { m: MAT.MOSS });
  POST.outline(s, { k: 0.64 }); POST.normals(s, 1);
  return { s, meta: { ax: 12, ay: gy + 1, kind: 'sign' } };
}
/** stone lantern 石灯籠 (unlit, mossy) */
export function ishidoro(seed = 1) {
  const W = 22, H = 44, s = new SB(W, H), cx = 11, by = H - 2, SL = PAL.stone;
  const tier = (y0, y1, hw0, hw1, z) => { for (let y = y0; y <= y1; y++) { const t = (y - y0) / Math.max(1, y1 - y0), hw = lerp(hw0, hw1, t); for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw - 1); x++) { const sx = (x + 0.5 - cx) / hw; s.pz(x, y, rc(SL, 0.56 - sx * 0.2 + (y === y0 ? 0.18 : 0) + (hash2(x, y, seed) - 0.5) * 0.12, x, y), z + (1 - Math.abs(sx)) * 2, { m: MAT.STONE, b: 2 + (1 - Math.abs(sx)) * 2 }); } } };
  tier(by - 4, by, 8, 9, 2); tier(by - 18, by - 5, 2.5, 3, 3); tier(by - 22, by - 19, 6, 7, 4); tier(by - 31, by - 23, 5, 5, 4);
  for (let y = by - 29; y <= by - 25; y++) for (let x = cx - 2; x <= cx + 1; x++) s.px(x, y, [34, 30, 34], { z: 6, m: MAT.STONE, b: 2 });
  tier(by - 37, by - 32, 3, 9, 6); tier(by - 40, by - 38, 1, 2, 7);
  for (let k = 0; k < 22; k++) { const x = cx - 8 + (hash2(k, 1, seed) * 16 | 0), y = by - 37 + (hash2(k, 2, seed) * 5 | 0); if (s.a(x, y)) s.px(x, y, PAL.moss[2 + (k % 3)], { m: MAT.MOSS }); }
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: by + 1, kind: 'lantern' } };
}
/** a boulder: chiselled facets on a dome, moss on what faces up */
export function rock(seed, w = 24, h = 16, o = {}) {
  const R = RNG(seed * 17 + 5), W = w + 4, H = h + 4, s = new SB(W, H), cx = W / 2, cy = H / 2 + 1;
  const rr = o.warm ? PAL.stoneWarm : PAL.stone, mossK = o.moss ?? 0.5;
  const sites = []; const ns = Math.max(5, Math.round(w * h / 36));
  for (let i = 0; i < ns; i++) sites.push({ x: cx + R.range(-w / 2, w / 2), y: cy + R.range(-h / 2, h / 2), j: [R.range(-0.35, 0.35), R.range(-0.3, 0.3)], t: R() });
  const rx = w / 2, ry = h / 2;
  if (!s.N) s.N = new Float32Array(W * H * 3);
  PX.ell(cx, cy, rx, ry, (x, y, u, v, d) => {
    let best = null, bd = 1e9, b2 = 1e9; for (const p of sites) { const dd = hyp(x + 0.5 - p.x, y + 0.5 - p.y); if (dd < bd) { b2 = bd; bd = dd; best = p; } else if (dd < b2) b2 = dd; }
    const pu = (best.x - cx) / rx, pv = (best.y - cy) / ry, pd = Math.min(0.98, hyp(pu, pv));
    let nx = pu * 0.9 + best.j[0], ny = -pv * 0.95 + best.j[1] + 0.25, nz = Math.sqrt(Math.max(0.05, 1 - pd * pd)) + 0.2; const l = hyp(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const up = ny * 0.7 + nz * 0.7, crack = b2 - bd < 0.9 && best.t > 0.55;
    let t = 0.5 + (best.t - 0.5) * 0.22 + (-nx * 0.3 + ny * 0.25) - (crack ? 0.3 : 0) - (v > 0.55 ? 0.12 : 0);
    const mz = Math.sqrt(Math.max(0, 1 - d * d)) * Math.min(rx, ry);
    if (up > 0.8 && hash2(x >> 1, y >> 1, seed) > 1 - mossK && !crack) s.px(x, y, rc(PAL.moss, 0.42 + (hash2(x, y, seed) - 0.5) * 0.3 - nx * 0.2, x, y), { z: mz + 1, m: MAT.MOSS, b: mz * 0.4, n: [nx, ny, nz] });
    else { if (hash2(x, y, seed + 3) < 0.03) t += 0.2; s.px(x, y, rc(rr, t, x, y, 0.35), { z: mz, m: MAT.STONE, b: mz * 0.4, n: [nx, ny, nz] }); }
  }, { amp: 0.22, seed: seed + 2, freq: 2.6 });
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: Math.round(cy + ry * 0.75), kind: 'rock' } };
}
/** a flat stepping stone (lies on the ground / in the stream) */
export function stepStone(seed) { const r = rock(seed + 300, 18, 8, { moss: 0.2 }); flat(r.s, r.meta.ay, 3); return r; }
/** a cut stump with an axe in it (the chopping block) */
export function stump(axe = true) {
  const W = 22, H = 20, s = new SB(W, H), cx = 11, gy = H - 2;
  for (let y = gy - 8; y <= gy; y++) for (let x = cx - 6; x <= cx + 6; x++) { const sx = (x - cx) / 6.5; s.pz(x, y, rc(PAL.barkCedar, 0.5 - sx * 0.3 + (hash2(x, y >> 1, 4) - 0.5) * 0.15, x, y), 3, { m: MAT.BARK, b: 3, n: cylN(sx) }); }
  PX.ell(cx, gy - 9, 6.5, 2.6, (x, y, u, v, d) => s.pz(x, y, Math.floor(d * 4) % 2 ? [196, 160, 112] : [176, 138, 92], 5, { m: MAT.WOOD, b: 3 }));
  if (axe) { for (let k = 0; k < 9; k++) s.pz(cx + 2 + k, gy - 10 - k * 0.8, PAL.woodNew[2], 6, { m: MAT.WOOD, b: 3 }); for (let y = gy - 11; y <= gy - 8; y++) for (let x = cx; x <= cx + 2; x++) s.pz(x, y, PAL.metal[y === gy - 11 ? 4 : 2], 6, { m: MAT.METAL, b: 3 }); }
  POST.outline(s, { k: 0.64 }); POST.normals(s, 1);
  return { s, meta: { ax: cx, ay: gy + 1, kind: 'item' } };
}
/** the lookout: a weathered two-rail fence along the edge */
export function fence(len = 60) {
  const W = len + 4, H = 22, s = new SB(W, H), gy = H - 2;
  for (let x = 2; x < W - 2; x += 15) for (let y = gy - 16; y <= gy; y++) { s.pz(x, y, WOOD[3], 4, { m: MAT.WOOD }); s.pz(x + 1, y, WOOD[1], 4, { m: MAT.WOOD }); }
  for (const ry of [gy - 14, gy - 7]) for (let x = 2; x < W - 2; x++) { const sag = Math.round(Math.sin(((x - 2) % 15) / 15 * Math.PI) * 1); s.pz(x, ry + sag, WOOD[4], 5, { m: MAT.WOOD }); s.pz(x, ry + sag + 1, WOOD[2], 5, { m: MAT.WOOD }); }
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  return { s, meta: { ax: Math.round(W / 2), ay: gy + 1, kind: 'fence' } };
}
/** a log seat by the lookout */
export function logSeat() {
  const W = 40, H = 16, s = new SB(W, H), gy = H - 2, r = 5;
  for (let x = 2; x < W - 6; x++) for (let y = gy - 2 * r; y <= gy; y++) { const v = (y - (gy - r)) / r; if (Math.abs(v) > 1) continue; s.px(x, y, rc(PAL.barkCedar, 0.5 - v * 0.25 + (hash2(x >> 2, y, 3) - 0.5) * 0.2, x, y), { z: Math.sqrt(1 - v * v) * r, m: MAT.BARK, b: 3 }); }
  PX.ell(W - 6, gy - r, 3.2, r, (x, y, u, v, d) => s.pz(x, y, d > 0.85 ? PAL.barkCedar[1] : Math.floor(d * 4) % 2 ? [206, 168, 118] : [184, 140, 92], r + 1, { m: MAT.WOOD, b: 4 }));
  for (let x = 6; x < W - 10; x += 5) { s.px(x, gy - 2 * r, PAL.moss[3], { m: MAT.MOSS, z: r, b: 3 }); }
  POST.outline(s, { k: 0.66 }); POST.normals(s, 1);
  return { s, meta: { ax: W / 2, ay: gy + 1, kind: 'item' } };
}

/** preview for tools/env/sheet.mjs */
export function PREVIEW() {
  return [
    ['hut', () => hut({})], ['hutLit', () => hut({ lit: true })], ['shrine', () => shrine()], ['beam', () => eaveBeam()],
    ['dosojin', () => dosojin()], ['ledge', () => offeringLedge()],
    ...[0, 1, 2, 3, 4, 5, 6, 7, 8].map(v => ['grave' + v, () => grave(v)]), ['pole', () => lanternPole(0)],
    ['lantern', () => bonLantern(false)], ['lanternLit', () => bonLantern(true)], ['spirit', () => spiritAnimals()],
    ['backframe', () => oldBackFrame()], ['load', () => load()], ['dango2', () => dango(2)], ['dango1', () => dango(1)], ['dangoP', () => dango('pale')],
    ['michi', () => michishirube()], ['sign', () => signboard()], ['toro', () => ishidoro()],
    ['rock1', () => rock(1, 24, 16)], ['rock2', () => rock(2, 40, 26, { warm: true })], ['step', () => stepStone(1)], ['stump', () => stump()], ['fence', () => fence()], ['log', () => logSeat()],
  ];
}
