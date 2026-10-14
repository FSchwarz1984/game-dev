/* =====================================================================
   env/actor — a procedural placeholder for the protagonist until the
   character agent's sheets land (src/art/characters.js, assets/sprites/).
   ~36 px tall, a very wide straw hat (笠) tied with a red cord, indigo
   work clothes, a red sash, a wooden back-frame. 3/4 view, light from
   the top-left. Output: an albedo sheet and a tangent-space normal
   sheet (RGB, OpenGL convention: green = up), both RGBA byte arrays,
   plus a frame table — the same shape the renderer takes from real
   PNG sheets (R.loadSheet / R.addActor).
   Frames (32×46 each, anchor at the feet: 16, 44):
     row 0 south: idle, walk1..4    row 1 north: idle, walk1..4
     row 2 east (flip for west): idle, walk1..4    row 3: climb1, climb2 (back view)
   ===================================================================== */
import { SB, PX, POST, MAT } from './paint.js';
import { PAL } from './palette.js';
import { clamp } from './core.js';

export const FW = 32, FH = 46, AX = 16, AY = 44;

/** the straw hat: a wide shallow cone; cx, cy = brim centre */
function hat(s, cx, cy, side) {
  const rx = side ? 13 : 14, ry = side ? 3.6 : 4.5, coneH = 6.5, H = PAL.hat;
  for (let y = Math.floor(cy - coneH - 1); y <= Math.ceil(cy + ry + 1); y++) for (let x = Math.floor(cx - rx - 1); x <= Math.ceil(cx + rx + 1); x++) {
    const u = (x + 0.5 - cx) / rx, v = (y + 0.5 - cy) / ry;
    const inBrim = u * u + v * v <= 1;
    const k = (cy - (y + 0.5)) / coneH; const inCone = k >= 0 && k <= 1 && Math.abs(u) <= (1 - k) * 0.95;
    if (!inBrim && !inCone) continue;
    // weave rings: radial distance from the apex on the hat surface
    const ay = cy - coneH * 0.62; const rr = Math.hypot((x + 0.5 - cx) / rx, (y + 0.5 - ay) / (ry + coneH * 0.62));
    let t = 0.58 - u * 0.24 + (inCone && !inBrim ? 0.1 : 0) - (v > 0.2 && inBrim ? 0.14 : 0);
    if (Math.floor(rr * 6.5) % 2 === 1) t -= 0.07;
    const edge = inBrim && u * u + v * v > 0.8 && v > -0.2;
    if (edge) t -= 0.2;
    s.pz(x, y, PX.rc(H, clamp(t, 0, 1), x, y, 0.25), 40 - v * 2 + (inCone ? 3 : 0), { m: MAT.STRAW, b: 9 + (inCone ? 3 : 0) });
  }
  // underside crescent (front views)
  for (let x = Math.ceil(cx - rx + 2); x <= Math.floor(cx + rx - 2); x++) { const u = (x + 0.5 - cx) / rx; const y = Math.floor(cy + ry * Math.sqrt(Math.max(0, 1 - u * u))) + 1; s.pz(x, y, H[0], 30, { m: MAT.STRAW, b: 7 }); }
  // apex knot
  s.pz(Math.round(cx - 0.5), Math.round(cy - coneH - 0.5), H[4], 45, { m: MAT.STRAW, b: 12 });
}

function figure(dir, frame, climb) {
  const s = new SB(FW, FH); const cx = AX, foot = AY; // dir 0 south, 1 north, 2 east
  const walk = frame > 0 && !climb, ph = (frame - 1) / 4 * Math.PI * 2;
  const bob = walk && (frame === 2 || frame === 4) ? -1 : 0;
  const I = PAL.indigo, SK = PAL.skin, RD = PAL.sash, CR = PAL.cream, WD = PAL.woodNew, HR = PAL.hair, ST = PAL.straw;
  const back = dir === 1 || climb, side = dir === 2;
  const swing = walk ? Math.sin(ph) : 0;
  // --- back-frame behind her (front and side views)
  const frameWood = (z, x0, x1) => {
    for (const fx of [x0, x1]) for (let y = foot - 37 + bob; y <= foot - 15 + bob; y++) s.pz(fx, y, WD[fx === x0 ? 3 : 1], z, { m: MAT.WOOD, b: z - 3 });
    for (const fy of [foot - 32, foot - 24, foot - 17]) for (let x = x0; x <= x1; x++) s.pz(x, fy + bob, WD[2], z + 0.2, { m: MAT.WOOD, b: z - 3 });
  };
  if (!back) { if (side) frameWood(2, cx - 6, cx - 4); else frameWood(2, cx - 7, cx + 6); }
  // --- legs and sandals
  const legs = side ? [[cx - 1, Math.round(swing * 2)], [cx + 1, -Math.round(swing * 2)]] : [[cx - 3, 0], [cx + 1, 0]];
  legs.forEach(([lx, off], k) => {
    const lift = side ? 0 : (walk ? Math.max(0, Math.round((k ? -1 : 1) * swing * 1.6)) : 0);
    for (let y = foot - 7; y <= foot - 1 - lift; y++) for (let x = lx + off; x <= lx + off + 1; x++) s.pz(x, y, I[x === lx + off ? 2 : 1], 8 + k, { m: MAT.CLOTH, b: 5 });
    s.pz(lx + off, foot - lift, ST[2], 9, { m: MAT.STRAW, b: 5 }); s.pz(lx + off + 1, foot - lift, ST[1], 9, { m: MAT.STRAW, b: 5 });
  });
  // --- kimono body: A-line, shoulders 10 px, hem 12 px
  const by0 = foot - 21 + bob, by1 = foot - 8 + bob;
  for (let y = by0; y <= by1; y++) {
    const t = (y - by0) / (by1 - by0); const hw = side ? 3.5 + t * 1.2 : 5 + t * 1.2;
    for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw - 1); x++) {
      const u = (x + 0.5 - cx) / hw; let tt = 0.5 - u * 0.25 - t * 0.08;
      if (Math.abs(u) > 0.85) tt -= 0.12;
      s.pz(x, y, PX.rc(I, clamp(tt, 0, 1), x, y, 0.3), 12 + (1 - Math.abs(u)) * 3, { m: MAT.CLOTH, b: 6 + (1 - Math.abs(u)) * 2 });
    }
  }
  // sash
  for (let y = foot - 13 + bob; y <= foot - 12 + bob; y++) for (let x = cx - (side ? 4 : 6); x <= cx + (side ? 4 : 5); x++) if (s.a(x, y)) s.px(x, y, RD[y === foot - 13 + bob ? 3 : 2], { m: MAT.CLOTH, z: 16, b: 9 });
  // collar (front)
  if (!back && !side) for (let k = 0; k < 5; k++) { s.pz(cx - 2 + (k >> 1), by0 + k, CR[2], 16, { m: MAT.CLOTH, b: 9 }); s.pz(cx + 1 - (k >> 1), by0 + k, CR[1], 16, { m: MAT.CLOTH, b: 9 }); }
  if (side) for (let k = 0; k < 4; k++) s.pz(cx + 2 - (k >> 1), by0 + k, CR[2], 16, { m: MAT.CLOTH, b: 9 });
  // sleeves and hands
  if (!side) for (const [sx, sg] of [[cx - 7, -1], [cx + 6, 1]]) { const sw = Math.round(swing * 1.2) * (sg < 0 ? 1 : -1);
    for (let y = by0 + 1; y <= by0 + 9; y++) { s.pz(sx, y + (y > by0 + 5 ? sw : 0), I[sg < 0 ? 3 : 1], 11, { m: MAT.CLOTH, b: 5 }); if (y < by0 + 8) s.pz(sx - sg, y, I[2], 11.5, { m: MAT.CLOTH, b: 5 }); }
    if (!back) s.pz(sx, by0 + 10 + sw, SK[2], 11, { m: MAT.SKIN, b: 5 }); }
  else { const sw = Math.round(swing * 2); for (let y = by0 + 1; y <= by0 + 8; y++) { s.pz(cx + Math.round(sw * (y - by0) / 8), y, I[3], 17, { m: MAT.CLOTH, b: 10 }); s.pz(cx - 1 + Math.round(sw * (y - by0) / 8), y, I[2], 17, { m: MAT.CLOTH, b: 10 }); }
    s.pz(cx + sw, by0 + 9, SK[2], 17, { m: MAT.SKIN, b: 10 }); }
  // --- head under the brim
  const hy = by0 - 4;
  PX.ell(cx - 0.5 + (side ? 0.5 : 0), hy, 3.7, 3.4, (x, y, u, v, d) => {
    const hair = back || (side ? u < 0.15 : Math.abs(u) > 0.6) || v < -0.5;
    s.pz(x, y, hair ? HR[clamp(Math.round(2.2 - u * 0.8 - v), 0, 4)] : PX.rc(SK, clamp(0.66 - u * 0.25 - v * 0.15, 0, 1), x, y, 0.2), 20 + (1 - d) * 2, { m: hair ? MAT.HAIR : MAT.SKIN, b: 11 + (1 - d) * 2 });
  });
  if (!back) {
    const eye = [52, 38, 46];
    if (!side) { s.px(cx - 2, hy + 1, eye, { m: MAT.SKIN, z: 23, b: 13 }); s.px(cx + 1, hy + 1, eye, { m: MAT.SKIN, z: 23, b: 13 }); s.px(cx - 3, hy + 3, RD[2], { m: MAT.CLOTH, z: 23, b: 13 }); s.px(cx + 2, hy + 3, RD[2], { m: MAT.CLOTH, z: 23, b: 13 }); }
    else { s.px(cx + 2, hy + 1, eye, { m: MAT.SKIN, z: 23, b: 13 }); s.px(cx, hy + 3, RD[2], { m: MAT.CLOTH, z: 23, b: 13 }); }
  }
  // --- back-frame over her back (back views)
  if (back) {
    frameWood(24, cx - 6, cx + 5);
    for (let y = by0 + 1; y <= by0 + 6; y++) { s.pz(cx - 4, y, ST[1], 25, { m: MAT.ROPE, b: 14 }); s.pz(cx + 3, y, ST[1], 25, { m: MAT.ROPE, b: 14 }); }
  }
  hat(s, cx - 0.5, hy - 3, side);
  if (climb) { const up = frame % 2 === 0;
    for (const [ax, o] of [[cx - 7, up ? -4 : 0], [cx + 6, up ? 0 : -4]]) { for (let y = by0 - 3 + o; y <= by0 + 4; y++) s.pz(ax, y, I[2], 26, { m: MAT.CLOTH, b: 15 }); s.pz(ax, by0 - 4 + o, SK[2], 26, { m: MAT.SKIN, b: 15 }); } }
  POST.outline(s, { k: 0.48, hue: 0.02 });
  POST.normals(s, 1.1);
  return s;
}

/** build the sheet: returns {albedo:{w,h,data}, normal:{w,h,data}, anims, frameW, frameH, anchor} */
export function buildPlaceholderSheet() {
  const cols = 5, rows = 4, W = cols * FW, H = rows * FH;
  const alb = new Uint8Array(W * H * 4), nrm = new Uint8Array(W * H * 4);
  const put = (s, c, r) => {
    for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
      const i = y * FW + x, k = i * 4; const t = ((r * FH + y) * W + c * FW + x) * 4;
      if (!s.c[k + 3]) { nrm[t] = 128; nrm[t + 1] = 128; nrm[t + 2] = 255; continue; }
      alb[t] = s.c[k]; alb[t + 1] = s.c[k + 1]; alb[t + 2] = s.c[k + 2]; alb[t + 3] = 255;
      nrm[t] = clamp(Math.round(s.N[i * 3] * 127.5 + 127.5), 0, 255); nrm[t + 1] = clamp(Math.round(s.N[i * 3 + 1] * 127.5 + 127.5), 0, 255); nrm[t + 2] = clamp(Math.round(s.N[i * 3 + 2] * 127.5 + 127.5), 0, 255); nrm[t + 3] = 255;
    }
  };
  for (let f = 0; f < 5; f++) { put(figure(0, f), f, 0); put(figure(1, f), f, 1); put(figure(2, f), f, 2); }
  put(figure(1, 1, true), 0, 3); put(figure(1, 2, true), 1, 3);
  const fr = (c, r) => [c * FW, r * FH, FW, FH];
  const anims = {
    idle_s: [fr(0, 0)], walk_s: [1, 2, 3, 4].map(c => fr(c, 0)),
    idle_n: [fr(0, 1)], walk_n: [1, 2, 3, 4].map(c => fr(c, 1)),
    idle_e: [fr(0, 2)], walk_e: [1, 2, 3, 4].map(c => fr(c, 2)),
    climb: [fr(0, 3), fr(1, 3)],
  };
  return { albedo: { w: W, h: H, data: alb }, normal: { w: W, h: H, data: nrm }, anims, frameW: FW, frameH: FH, anchor: [AX, AY] };
}
