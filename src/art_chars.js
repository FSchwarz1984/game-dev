/* =====================================================================
   ART · CHARACTERS — ツヅラ (Tsuzura), a marten yokai of the pass.
   Gold hair with dark-brown tips (a marten's winter coat), round ears,
   amber eyes, one small fang. Indigo kasuri kimono cut short for the
   road, sleeves tied back with a red tasuki, a little brass bell at the
   obi, dark leg-wraps and straw sandals. A wooden back-frame (背負子)
   whose poles stand above her head — the silhouette people remember.
   Built from parts so every frame can be composed on the fly.
   ===================================================================== */
"use strict";
const TZ = {
  W: 32, H: 44, // frame canvas; feet at y = H-3, centre x = 16
  C: null,
  init() {
    const c = (h) => hexRGB(h);
    this.C = {
      k: c("#2b1a14"), K: c("#1d120e"),                      // outline (warm dark), deepest
      H: c("#f8d27a"), h: c("#e8ac48"), j: c("#c27d2c"), J: c("#8d4f1c"), t: c("#5b3319"), T: c("#3e2212"), // hair & marten tips
      E: c("#f4e3c6"),                                          // inner ear / cream fur
      s: c("#f7e0c6"), S: c("#e6bd99"), Z: c("#cf9a78"),        // skin
      w: c("#fffaf2"), e: c("#d2741f"), q: c("#f2a646"), p: c("#2a140c"), // eye white, iris, iris light, pupil
      b: c("#f08f80"), m: c("#8e3428"), f: c("#ffffff"),        // blush, mouth, fang
      i: c("#4c5f9e"), I: c("#33467e"), n: c("#22305c"), N: c("#172041"), x: c("#7d8fc6"), // indigo & kasuri
      c: c("#f2e6cd"), C: c("#d9c9a8"),                         // collar (juban)
      r: c("#e3553f"), R: c("#b5332a"), D: c("#7d2219"),        // tasuki red
      o: c("#4a2d1d"), O: c("#6b4429"),                         // obi
      g: c("#f0c64e"), G: c("#a8822c"),                         // brass bell
      l: c("#3b2619"), L: c("#5a3b27"),                         // leg wraps
      y: c("#cfae6a"), Y: c("#9d7f45"),                         // straw sandals
      wd: c("#8a6747"), wD: c("#5d432d"), wL: c("#a8845f"),     // back-frame wood
    };
  },
  // paint helpers into a SB with depth so parts layer like volume
  P(s, x, y, ch, z, m) { if (ch === "." || ch === " ") return; const col = this.C[ch]; if (!col) return; s.pz(x, y, col, z, { m, b: z * .35 }); },
  rows(s, ox, oy, rows, z, m, flip = false) {
    for (let y = 0; y < rows.length; y++) { const r = rows[y]; for (let x = 0; x < r.length; x++) { const ch = r[flip ? r.length - 1 - x : x]; this.P(s, ox + x, oy + y, ch, typeof z === "function" ? z(x, y) : z, m); } }
  },
};

/* ---------------------------------------------------------------------
   BODY BUILDER — shapes, not stamps. Frame 32×46; feet rest on y = 43.
   Light is keyed from the upper left in the albedo (one step only);
   the renderer's dynamic light does the rest.
   --------------------------------------------------------------------- */
const TZA = {
  FY: 43,
  // ---- the head, any facing. f: 'front' | 'back' | 'side' (facing right)
  head(s, f, cx, cy, o = {}) {
    const C = TZ.C, P = (x, y, ch, z, m = MAT.FUR) => TZ.P(s, x, y, ch, z, m);
    const rx = 7.6, ry = 7.2;
    const hairAt = (x, y, u, v, d) => { // tone for a hair pixel
      if (d > .9) return "k";
      const ring = Math.abs(v + .42 + u * u * .25) < .09 && Math.abs(u) < .75; // the sheen across the crown
      if (ring) return "H";
      if (v > .55) return u > .2 ? "J" : "j";
      return u < -.5 && v < -.1 && v > -.75 ? "H" : u > .4 || v > .3 ? "j" : "h";
    };
    // ears first (behind the hair outline): round, cream inside, set wide
    const ear = (ex, ey, dir) => { for (let y = -2; y <= 1; y++) for (let x = -2; x <= 2; x++) { const d = hyp(x * 1.1, y * 1.2); if (d > 2.4) continue; const edge = d > 1.6; P(Math.round(ex + x), Math.round(ey + y), edge ? "k" : (x * dir > -.5 && y > -1 ? "E" : "h"), 2); } };
    if (f === "side") ear(cx - 1.5, cy - 7.2, 1); else { ear(cx - 7, cy - 5.6, 1); ear(cx + 7, cy - 5.6, -1); }
    // back hair mass: falls past the jaw and darkens to marten-brown at the ends
    for (let y = Math.floor(cy - ry - 1); y <= cy + 11; y++) for (let x = Math.floor(cx - rx - 1); x <= cx + rx + 1; x++) {
      const u = (x + .5 - cx) / rx, v = (y + .5 - cy) / ry; let d = Math.sqrt(u * u + v * v);
      if (y > cy + 2) { // the lower curtain of hair (behind the face/neck): narrower, ends in points
        const w = (f === "side" ? .78 : 1) * (1 - Math.pow((y - cy - 2) / 9.5, 2) * .35); const ue = Math.abs(u + (f === "side" ? .25 : 0)) / w;
        const tip = cy + (f === "back" ? 8 : 6) + (Math.abs(Math.round(x * 1.7)) % 3); if (ue > 1 || y > tip) continue;
        if (f === "front" && Math.abs(u) < .62) continue;   // in front the curtain only shows past the cheeks
        const end = y > tip - 2.2; P(x, y, ue > .86 ? "k" : end ? (y > tip - 1 ? "T" : "t") : u > .2 ? "J" : "j", 3); continue;
      }
      if (d > 1) continue; P(x, y, hairAt(x, y, u, v, d), 4);
    }
    if (f === "back") return;
    // face
    const fx = f === "side" ? cx + 2.2 : cx, frx = f === "side" ? 4.4 : 5.5, fry = 5.2, fcy = cy + 2.2;
    for (let y = Math.floor(fcy - fry); y <= fcy + fry + 1; y++) for (let x = Math.floor(fx - frx - 1); x <= fx + frx + 1; x++) {
      const u = (x + .5 - fx) / frx, v = (y + .5 - fcy) / fry; let d = Math.sqrt(u * u + Math.pow(v * (v > 0 ? 1 + v * .35 : 1), 2)); // pointed chin
      if (d > 1) continue; const edge = d > .88 && v > -.2;
      P(x, y, edge ? "k" : (u > .45 || v > .62) ? "S" : "s", 7, MAT.SKIN);
    }
    if (f === "side") { P(Math.round(fx + frx), Math.round(fcy + .5), "s", 7.2, MAT.SKIN); P(Math.round(fx + frx), Math.round(fcy - .5), "s", 7.2, MAT.SKIN); }
    // eyes, blush, mouth
    const eyes = o.eyes || "open", ey = Math.round(cy + 1);
    const eye = (ex, dir) => {
      if (eyes === "closed" || eyes === "happy") { P(ex - 1, ey + 1, "k", 9, MAT.SKIN); P(ex, ey + 1 + (eyes === "happy" ? -1 : 0), "k", 9, MAT.SKIN); P(ex + 1, ey + 1, "k", 9, MAT.SKIN); return; }
      const half = eyes === "half" || eyes === "smug";
      if (!half) { P(ex - 1, ey - 1, "k", 9, MAT.SKIN); P(ex, ey - 1, "k", 9, MAT.SKIN); P(ex + 1, ey - 1, "k", 9, MAT.SKIN); P(ex + dir * 2, ey - 2, "k", 9, MAT.SKIN); }
      else { P(ex - 1, ey, "k", 9, MAT.SKIN); P(ex, ey, "k", 9, MAT.SKIN); P(ex + 1, ey, "k", 9, MAT.SKIN); P(ex + dir * 2, ey - 1, "k", 9, MAT.SKIN); }
      if (!half) { P(ex - dir, ey, "w", 9, MAT.SKIN); P(ex, ey, "p", 9, MAT.SKIN); P(ex + dir, ey, "e", 9, MAT.SKIN); }
      P(ex - 1, ey + 1, "e", 9, MAT.SKIN); P(ex, ey + 1, eyes === "smug" ? "p" : "e", 9, MAT.SKIN); P(ex + 1, ey + 1, "q", 9, MAT.SKIN);
      P(ex, ey + 2, "q", 9, MAT.SKIN);
    };
    if (f === "side") { eye(Math.round(cx + 4), 1); P(Math.round(cx + 2), ey + 3, "b", 8, MAT.SKIN); }
    else { eye(Math.round(cx - 3), -1); eye(Math.round(cx + 2), 1); P(Math.round(cx - 5), ey + 3, "b", 8, MAT.SKIN); P(Math.round(cx + 4), ey + 3, "b", 8, MAT.SKIN); }
    const mx = f === "side" ? Math.round(cx + 5) : Math.round(cx - .5), my = ey + 4, mo = o.mouth || "idle";
    if (mo === "open" || mo === "o") { P(mx, my, "m", 9, MAT.SKIN); P(mx + 1, my, "m", 9, MAT.SKIN); P(mx, my + 1, "D", 9, MAT.SKIN); P(mx + 1, my + 1, "m", 9, MAT.SKIN); }
    else if (mo === "fang") { P(mx, my, "m", 9, MAT.SKIN); P(mx + 1, my, "m", 9, MAT.SKIN); P(mx + 1, my + 1, "f", 9, MAT.SKIN); }
    else if (mo === "smile") { P(mx - 1, my - 1, "m", 9, MAT.SKIN); P(mx, my, "m", 9, MAT.SKIN); P(mx + 1, my, "m", 9, MAT.SKIN); P(mx + 2, my - 1, "m", 9, MAT.SKIN); }
    else P(mx + (f === "side" ? 0 : 1), my, "m", 9, MAT.SKIN);
    // bangs: five locks with pointed tips; parting a little to her right
    const locks = f === "side" ? [[1.4, 3, 2.2], [3.6, 2.8, 1.8], [5.4, 2, 1.2]] : [[-5.4, 3.2, 2.4], [-2.6, 3.4, 3], [.4, 3, 1.6], [3.1, 3.3, 2.8], [5.7, 3, 2.2]];
    for (const [lx, lw, ll] of locks) {
      const x0 = cx + lx; const top = cy - 5.4;
      for (let y = Math.floor(top); y <= top + 2.4 + ll; y++) { const t = (y - top - 2.4) / ll; const w = t < 0 ? lw : lw * (1 - t); if (w <= .2) continue;
        for (let x = Math.floor(x0 - w / 2); x <= Math.floor(x0 + w / 2 - .01); x++) { const edge = x === Math.floor(x0 - w / 2) && t > 0; P(x, y, t > .55 ? "j" : edge ? "j" : y < top + 1.5 && lx < 0 ? "H" : "h", 10); } }
    }
    // side locks framing the face, ending in dark tips
    const sideLock = (lx, dir) => { for (let y = Math.round(cy - 1); y <= cy + 8; y++) { const t = (y - cy + 1) / 9; const w = t > .7 ? 1 : 2; for (let q = 0; q < w; q++) P(lx + q * dir, y, t > .78 ? "t" : t > .6 ? "J" : q === 0 ? "j" : "h", 9.5); } P(lx, Math.round(cy + 9), "T", 9.5); };
    if (f === "side") sideLock(Math.round(cx + .5), 1);
    else { sideLock(Math.round(cx - 6), 1); sideLock(Math.round(cx + 5), -1); }
  },
  // ---- the wooden back-frame 背負子: two poles and rungs. Drawn behind (front view) or over (back view)
  frame(s, cx, topY, botY, f, z) {
    const P = (x, y, ch) => TZ.P(s, x, y, ch, z, MAT.WOOD);
    if (f === "side") { const x0 = cx - 7; for (let y = topY; y <= botY; y++) { P(x0, y, "wD"); P(x0 + 1, y, "wd"); } for (let y = topY + 2; y < botY; y += 6) for (let x = x0 - 1; x <= x0 + 2; x++) P(x, y, "wL"); for (let x = x0 - 1; x <= x0 + 3; x++) P(x, botY, "wD"); return; }
    for (const px of [cx - 5, cx + 4]) for (let y = topY; y <= botY; y++) { P(px, y, f === "back" ? "wd" : "wD"); P(px + 1, y, f === "back" ? "wL" : "wd"); }
    if (f === "back") for (let y = topY + 3; y < botY; y += 7) for (let x = cx - 4; x <= cx + 4; x++) P(x, y, (x & 1) ? "wd" : "wL");
    P(cx - 5, topY - 1, "wL"); P(cx + 5, topY - 1, "wL");
  },
  // ---- one full frame. o: {f:'front'|'back'|'side', eyes, mouth, step (-1..1 gait phase), bob, arms:'idle'|'swing'|'up'|'hold'|'count', frame:true}
  compose(o = {}) {
    const f = o.f || "front", s = new SB(32, 46), cx = 15.5, FY = TZA.FY, bob = o.bob || 0, step = o.step || 0;
    const P = (x, y, ch, z, m) => TZ.P(s, x, y, ch, z, m);
    const ka = (x, y) => ((x * 2 + y * 3) % 7 === 0 && y % 2 === 0);
    // legs: momohiki (tights) above, kyahan (wraps) below, waraji on the feet
    const legs = f === "side" ? [[-1, step], [1, -step]] : [[-1, 0], [1, 0]];
    for (const [side, ph] of legs) {
      const lift = f === "side" ? (ph > .55 ? 1 : 0) : ((side < 0 ? step : -step) > .45 ? 1 : 0);
      const fx = f === "side" ? Math.round(cx - 1 + ph * 2.4) : Math.round(cx + (side < 0 ? -3 : 1));
      const near = f === "side" ? side > 0 : true;
      for (let y = 32; y <= FY - 2; y++) {
        const t = (y - 32) / (FY - 34); const x0 = f === "side" ? Math.round(lerp(cx - 1, fx, t)) : fx;
        for (let x = x0; x < x0 + 3; x++) { const wrap = y >= 36; const tie = y === 36 || (y === 39 && x === x0 + 1);
          P(x, y - lift + bob, tie ? "C" : wrap ? (x === x0 && near ? "L" : "l") : (x === x0 ? "O" : "l"), near ? 2.4 : 1.8, MAT.CLOTH); }
      }
      for (let x = fx - (f === "side" ? 0 : side < 0 ? 1 : 0); x < fx + 3 + (f === "side" ? 1 : side > 0 ? 1 : 0); x++) P(x, FY - 1 - lift + bob, near ? "y" : "Y", near ? 2.6 : 2, MAT.STRAW);
      P(fx + 1, FY - 2 - lift + bob, "R", near ? 2.7 : 2.1, MAT.CLOTH);
    }
    // the short kimono: torso, then a skirt that stops above the knee
    const tw = f === "side" ? 4 : 5;
    for (let y = 19; y <= 31; y++) {
      const hw = y <= 26 ? tw : tw + (y - 26) * .35, xa = Math.floor(cx - hw + .5), xb = Math.ceil(cx + hw - .5);
      for (let x = xa; x <= xb; x++) {
        const edge = x === xa || x === xb || y === 31; const sh = (x - cx) / hw;
        let ch = edge ? "k" : ka(x, y) ? "x" : sh < -.45 ? "i" : sh > .5 ? "n" : "I";
        if (f === "front" && y >= 27 && !edge && Math.abs(x - (cx + 1.5 - (y - 27) * .5)) < .6) ch = "N"; // the front overlap of the skirt
        P(x, y + bob, ch, (f === "back" ? 4 : 5) + (1 - Math.abs(sh)) * 2, MAT.CLOTH);
      }
    }
    if (f !== "back") { // collar: left over right
      if (f === "front") { for (let k = 0; k < 6; k++) { P(Math.round(cx + 1 - k * .9), 19 + k + bob, "c", 8, MAT.CLOTH); P(Math.round(cx + 2 - k * .9), 19 + k + bob, "C", 8, MAT.CLOTH); } for (let k = 0; k < 3; k++) P(Math.round(cx + 2 + k), 19 + k + bob, "c", 7.8, MAT.CLOTH); }
      else for (let k = 0; k < 5; k++) P(Math.round(cx + 3 - k * .2), 19 + k + bob, k < 4 ? "c" : "C", 7, MAT.CLOTH);
    }
    // obi + bell
    for (let x = Math.floor(cx - tw + .5); x <= Math.ceil(cx + tw - .5); x++) { P(x, 25 + bob, "O", 8, MAT.CLOTH); P(x, 26 + bob, "o", 8, MAT.CLOTH); }
    if (f === "back") for (const [dx, dy, ch] of [[-2, -1, "o"], [-1, -1, "O"], [1, -1, "O"], [2, -1, "o"], [0, 0, "k"], [-1, 1, "o"], [1, 1, "o"]]) P(Math.round(cx + dx), 25 + dy + bob, ch, 9, MAT.CLOTH);
    else { const bx = f === "side" ? Math.round(cx + 3) : Math.round(cx - 3); P(bx, 27 + bob, "G", 9, MAT.METAL); P(bx, 28 + bob, "g", 9, MAT.METAL); P(bx + 1, 28 + bob, "G", 9, MAT.METAL); }
    // tasuki: over the shoulders in front, a red X on the back
    if (f === "front") for (const sd of [-1, 1]) for (let k = 0; k < 4; k++) P(Math.round(cx + sd * (4.2 - k * .4) - .5), 19 + k + bob, k ? "R" : "r", 8.6, MAT.CLOTH);
    if (f === "side") for (let k = 0; k < 6; k++) P(Math.round(cx - 3 + k * .55), 19 + k + bob, k % 2 ? "R" : "r", 7.5, MAT.CLOTH);
    if (f === "back") for (let k = 0; k < 7; k++) { P(Math.round(cx - 3.5 + k), 19 + k + bob, "R", 9.5, MAT.CLOTH); P(Math.round(cx + 3.5 - k), 19 + k + bob, k === 3 ? "r" : "D", 9.6, MAT.CLOTH); }
    // arms
    const arms = o.arms || "idle";
    const arm = (side, sw) => {
      const ax = Math.round(cx + side * (tw + 1) - (side > 0 ? 1 : 0));
      if (arms === "up") { for (let y = 13; y <= 21; y++) { const skin = y < 17; P(ax + side, y + bob, skin ? "s" : (side < 0 ? "i" : "n"), 10, skin ? MAT.SKIN : MAT.CLOTH); P(ax, y + bob, skin ? "S" : "I", 10, skin ? MAT.SKIN : MAT.CLOTH); } return; }
      if (arms === "hold" || arms === "count") { for (let y = 20; y <= 24; y++) { const skin = y > 22; P(ax - side * (y > 22 ? 1 : 0), y + bob, skin ? "s" : "I", 10, skin ? MAT.SKIN : MAT.CLOTH); P(ax + side - side * (y > 22 ? 1 : 0), y + bob, skin ? "S" : "n", 10, skin ? MAT.SKIN : MAT.CLOTH); } if (arms === "count") P(ax - side * 2, 21 + bob, "s", 10.5, MAT.SKIN); return; }
      for (let y = 20; y <= 27; y++) { const sh = Math.round(sw * (y - 20) / 7); const skin = y >= 24;
        for (let q = 0; q < 2; q++) P(ax + q + sh, y + bob, skin ? (q === 0 ? "s" : "S") : (q === 0 ? (side < 0 ? "i" : "I") : (side < 0 ? "I" : "n")), f === "back" ? 6 : 9, skin ? MAT.SKIN : MAT.CLOTH); }
      P(ax + Math.round(sw) + (side > 0 ? 1 : 0), 28 + bob, "S", f === "back" ? 6 : 9, MAT.SKIN);
    };
    if (f === "side") arm(1, -step * 2.2); else { arm(-1, arms === "swing" ? step * 1.5 : 0); arm(1, arms === "swing" ? -step * 1.5 : 0); }
    // head
    TZA.head(s, f, cx, 10 + bob, o);
    // the back-frame
    if (o.frame !== false) { if (f === "back") TZA.frame(s, Math.round(cx), 2 + bob, 33 + bob, f, 11); else if (f === "side") TZA.frame(s, Math.round(cx) - 2, 1 + bob, 31 + bob, f, 4.5); }
    return s;
  },
  finish(s) { PX.normals(s, .9); return s; },
};
/* ---------------------------------------------------------------------
   TAIL — drawn per frame: a chain of fluffy discs from the small of her
   back, swaying; the last discs turn marten-brown.
   --------------------------------------------------------------------- */
const TAIL = {
  // a bushy marten tail: a curve of fluff discs with ragged fur at the edge; the last third goes dark brown
  draw(s, bx, by, dir, t, o = {}) {
    const n = 10, pts = []; let x = bx, y = by, a = (o.a0 ?? -Math.PI / 2 + dir * 1.25) + Math.sin(t * 1.6) * .1 * dir + (o.lift || 0) * -dir * .6;
    for (let i = 0; i < n; i++) { pts.push([x, y]); a += dir * (-.17 + Math.sin(t * 2.2 - i * .6) * .06) + (o.droop || 0) * dir * .07; x += Math.cos(a) * 1.75; y += Math.sin(a) * 1.75; }
    const z0 = o.z ?? 1;
    for (let i = n - 1; i >= 0; i--) {
      const [px, py] = pts[i], r = 1.4 + Math.sin(Math.min(1, i / (n - 2)) * Math.PI * .92) * 2.9;
      const tip = i >= n - 3, mid = i === n - 4;
      for (let yy = Math.floor(py - r - 2); yy <= py + r + 2; yy++) for (let xx = Math.floor(px - r - 2); xx <= px + r + 2; xx++) {
        const u = (xx + .5 - px) / r, v = (yy + .5 - py) / r; let d = Math.sqrt(u * u + v * v);
        d -= (hash2(xx, yy, 77) - .5) * .32;                 // ragged fur
        if (d > 1) continue;
        const edge = d > .78;
        let ch = tip ? (edge ? "t" : v < -.3 ? "j" : "J") : mid ? (edge ? "J" : v < -.3 ? "h" : "j") : (edge ? "j" : (v < -.35 && u * dir < .3) ? "H" : u * dir > .4 ? "j" : "h");
        if (!tip && !edge && (xx + yy * 2) % 7 === 0) ch = mid ? "j" : "H";   // a few combed highlights
        s.pz(xx, yy, TZ.C[ch], z0 + (1 - Math.min(1, d)) * 1.6 + i * .04, { m: MAT.FUR, b: z0 * .35 });
      }
    }
  },
};

/* ---------------------------------------------------------------------
   KAGO — the wicker trunk, awake: little legs, a lid that talks
   --------------------------------------------------------------------- */
const KAGO = {
  frame(t, o = {}) {
    const s = new SB(28, 30), cx = 14, wv = ramp("#a17a45", 5, { lo: .5, hi: .4 }), step = o.step || 0, open = o.open || 0;
    for (const [lx, ph] of [[cx - 5, 1], [cx + 3, -1]]) { const lift = Math.max(0, Math.sin(step * Math.PI) * ph) > .4 ? 1 : 0; for (let y = 22; y <= 27; y++) { s.pz(lx, y - lift, TZ.C.wD, 1, { m: MAT.WOOD }); s.pz(lx + 1, y - lift, TZ.C.wd, 1, { m: MAT.WOOD }); } s.pz(lx - 1, 27 - lift, TZ.C.y, 1.2, { m: MAT.STRAW }); s.pz(lx + 2, 27 - lift, TZ.C.y, 1.2, { m: MAT.STRAW }); }
    for (let y = 10; y < 23; y++) for (let x = 4; x < 24; x++) { const weave = ((x >> 1) + (y >> 1)) % 2, edge = x === 4 || x === 23 || y === 22;
      s.pz(x, y, edge ? wv[1] : wv[clamp(Math.round((.5 + (weave ? .14 : -.08) - (x - 4) / 20 * .15) * 4), 0, 4)], 4, { m: MAT.STRAW, b: 3 }); }
    for (let x = 6; x < 22; x++) s.pz(x, 16, [124, 52, 40], 4.5, { m: MAT.CLOTH, b: 3 });
    const ly = 10 - Math.round(open * 4);
    for (let y = ly - 4; y < ly; y++) for (let x = 3; x < 25; x++) s.pz(x, y, wv[clamp(Math.round((.7 - (y - ly + 4) * .08 + (((x >> 1) + y) % 2 ? .08 : 0)) * 4), 0, 4)], 6, { m: MAT.STRAW, b: 4 });
    // two eye-holes in the weave that blink
    if (!o.blink) for (const ex of [10, 17]) { s.pz(ex, 13, [22, 16, 14], 5, { m: MAT.STRAW }); s.pz(ex, 14, [22, 16, 14], 5, { m: MAT.STRAW }); }
    else for (const ex of [10, 17]) s.pz(ex, 14, [40, 30, 24], 5, { m: MAT.STRAW });
    if (open > .2) for (let x = 7; x < 21; x++) s.pz(x, ly, [30, 20, 18], 5.5, { m: MAT.STRAW });
    PX.selout(s, { k: .7 }); PX.normals(s, 1);
    return s;
  },
};

/* ---------------------------------------------------------------------
   PORTRAITS — 96×96 busts for the dialogue window. Built like a cel:
   flat tones in two or three steps, a warm dark line, hue-shifted
   shadow. Expressions swap eyes, brows, mouth; ears and tail act too.
   --------------------------------------------------------------------- */
const PORTRAIT = {
  cache: {},
  W: 96,
  tsuzura(expr = "normal") {
    if (this.cache[expr]) return this.cache[expr];
    const W = 96, buf = new Uint8ClampedArray(W * W * 4), Z = new Float32Array(W * W).fill(-1e9);
    const C = TZ.C, X = { // portrait-only tones
      hairHi: hexRGB("#fde7a6"), hairS2: hexRGB("#a8601f"), skinS2: hexRGB("#d9a07e"), lash: hexRGB("#3a1a10"), irisD: hexRGB("#8a3a10"), irisM: hexRGB("#d06a1c"), irisL: hexRGB("#f6b54a"),
      white: hexRGB("#fffdf8"), blush: hexRGB("#f2867a"), line: hexRGB("#3a2216"), earIn: hexRGB("#f6e6cf"), earInS: hexRGB("#e2c7a2"), cloth2: hexRGB("#5a6fb0"),
    };
    const put = (x, y, c, z = 0) => { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= W) return; const i = y * W + x; if (z < Z[i]) return; Z[i] = z; const q = i * 4; const col = typeof c === "string" ? (C[c] || hexRGB(c)) : c; buf[q] = col[0]; buf[q + 1] = col[1]; buf[q + 2] = col[2]; buf[q + 3] = 255; };
    const ell = (cx, cy, rx, ry, fn) => { for (let y = Math.floor(cy - ry - 1); y <= cy + ry + 1; y++) for (let x = Math.floor(cx - rx - 1); x <= cx + rx + 1; x++) { const u = (x + .5 - cx) / rx, v = (y + .5 - cy) / ry, d = Math.sqrt(u * u + v * v); if (d <= 1) fn(x, y, u, v, d); } };
    const bez = (p0, p1, p2, w, fn, steps = 60) => { for (let i = 0; i <= steps; i++) { const t = i / steps, a = (1 - t) * (1 - t), b = 2 * (1 - t) * t, c = t * t; const x = a * p0[0] + b * p1[0] + c * p2[0], y = a * p0[1] + b * p1[1] + c * p2[1]; const ww = typeof w === "function" ? w(t) : w; for (let oy = -ww; oy <= ww; oy += .5) for (let ox = -ww; ox <= ww; ox += .5) if (ox * ox + oy * oy <= ww * ww) fn(Math.round(x + ox), Math.round(y + oy), t); } };
    const M = PORTRAIT.moods[expr] || PORTRAIT.moods.normal;
    const cx = 48, tilt = M.tilt || 0;
    const HX = (y) => cx + tilt * (40 - y) * .06; // head axis leans with tilt
    // ---- tail behind the right shoulder
    const ty = 66 - (M.tail || 0) * 6;
    ell(80, ty, 11, 15, (x, y, u, v, d) => { if (y > 95) return; const fur = d - (hash2(x, y, 5) - .5) * .12; if (fur > 1) return; put(x, y, fur > .9 ? X.line : v < -.45 ? "J" : v < -.15 ? (u > .3 ? "j" : "h") : u < -.4 ? "H" : u > .4 ? "j" : "h", 1); });
    ell(80, ty - 12, 7, 6, (x, y, u, v, d) => put(x, y, d > .88 ? X.line : v < -.2 ? "t" : "J", 1.1));
    // ---- back hair (behind everything of the body)
    ell(HX(38), 38, 31, 31, (x, y, u, v, d) => { if (y > 80) return; put(x, y, d > .97 ? X.line : y > 66 ? (Math.abs(u) > .55 ? "t" : "J") : v > .4 ? "j" : u > .55 ? "j" : "h", 2); });
    for (const sd of [-1, 1]) for (let y = 44; y < 86; y++) { const w = 7 - Math.max(0, y - 76) * .7; for (let k = 0; k < w; k++) { const x = HX(y) + sd * (29 - k); put(x, y, k === 0 ? X.line : y > 78 ? "t" : y > 70 ? "J" : k < 3 ? "j" : "h", 2.5); } }
    // ---- shoulders, kimono, collar, tasuki
    for (let y = 72; y < W; y++) { const hw = 22 + (y - 72) * 1.05; for (let x = Math.floor(cx - hw); x <= cx + hw; x++) { const e = Math.abs(x - cx) > hw - 1.4; const ka = ((x * 2 + y * 3) % 9 === 0 && y % 3 === 0); put(x, y, e ? X.line : ka ? "x" : x < cx - 8 ? "i" : x > cx + 10 ? "n" : "I", 3); } }
    for (let k = 0; k < 24; k++) { const x = cx + 6 - k * .85, y = 72 + k; put(x, y, X.line, 4); put(x + 1, y, "c", 4); put(x + 2, y, "c", 4); put(x + 3, y, "C", 4); }
    for (let k = 0; k < 16; k++) { const x = cx + 9 + k * .55, y = 72 + k; put(x, y, "c", 3.9); put(x + 1, y, "C", 3.9); put(x + 2, y, X.line, 3.9); }
    for (const sd of [-1, 1]) for (let k = 0; k < 18; k++) { const x = cx + sd * (21 - k * .25), y = 74 + k; put(x, y, X.line, 4.2); put(x + sd, y, "R", 4.2); put(x + sd * 2, y, k % 4 ? "R" : "r", 4.2); put(x + sd * 3, y, X.line, 4.2); }
    put(cx + 15, 88, "G", 5); put(cx + 16, 88, "g", 5); put(cx + 15, 89, "g", 5); put(cx + 16, 89, "G", 5); put(cx + 15, 87, X.line, 5); put(cx + 16, 87, X.line, 5);
    // ---- neck
    for (let y = 60; y < 76; y++) for (let x = cx - 5; x <= cx + 5; x++) put(x, y, (x === cx - 5 || x === cx + 5) ? X.line : x > cx + 2 ? "S" : "s", 3.5);
    // ---- ears (move with mood): broad rounded marten ears on the upper sides; the base sinks into the hair
    for (const sd of [-1, 1]) {
      const ex = HX(18) + sd * (25 + (M.ears < 0 ? 2 : 0)), ey = 19 - (M.ears || 0) * 2.5 + (M.ears < 0 ? 3 : 0), ang = sd * (.5 + (M.ears < 0 ? .5 : 0));
      ell(ex, ey, 8.5, 8.5, (x, y, u, v, d) => { const ru = u * Math.cos(ang) + v * Math.sin(ang), rv = -u * Math.sin(ang) + v * Math.cos(ang); if (rv > .35) return;
        const fur = d - (hash2(x, y, 9) - .5) * .08; if (fur > 1) return;
        put(x, y, fur > .86 ? X.line : (Math.abs(ru) < .52 && rv > -.62 && rv < .3) ? (Math.abs(ru) < .28 ? X.earIn : X.earInS) : rv < -.55 ? X.hairHi : ru * sd > .3 ? "j" : "h", 7.5); });
    }
    // ---- face: full cheeks, tapering to a small pointed chin in the lower third
    const fcx = HX(46), fcy = 43, FR = 19.5;
    for (let y = 22; y < 68; y++) {
      const v = (y + .5 - fcy) / 20; if (v > 1) continue;
      const w = FR * (v < .2 ? Math.sqrt(Math.max(0, 1 - Math.pow(Math.min(0, v), 2))) : 1 - Math.pow((v - .2) / .8, 1.45) * .86);
      for (let x = Math.floor(fcx - w - 1); x <= fcx + w + 1; x++) { const u = (x + .5 - fcx) / Math.max(1, w); if (Math.abs(u) > 1) continue;
        const edge = Math.abs(u) > 1 - 1.3 / Math.max(1, w) || v > .97; put(x, y, edge && v > -.2 ? X.line : (u > .6 || (v > .55 && u > .1)) ? "S" : "s", 6); }
    }
    for (let y = 63; y < 67; y++) for (let x = fcx - 5; x <= fcx + 5; x++) put(x, y, X.skinS2, 3.6);
    // ---- eyes
    for (const sd of [-1, 1]) PORTRAIT.eye2(put, bez, ell, HX(46) + sd * 10.5, 47, sd, M, X);
    // brows over the bangs, the way anime draws them
    for (const sd of [-1, 1]) { const bx = HX(34) + sd * 10.5, by = 35 - (M.browUp || 0); bez([bx - sd * 5, by + (M.brow || 0) * .9], [bx, by - 1.5], [bx + sd * 5, by - (M.brow || 0) * .9], .5, (x, y) => put(x, y, M.brow < -1 ? X.line : "J", 12)); }
    // nose & mouth & blush
    put(HX(54), 55, X.skinS2, 7); put(HX(54) + 1, 55, "S", 7);
    PORTRAIT.mouth2(put, ell, HX(60), 60, M.mouth, X);
    if (M.blush) for (const sd of [-1, 1]) for (let k = 0; k < 3; k++) { const bx = HX(52) + sd * (13 + k * 2.2), by = 53; for (let j = 0; j < 3; j++) put(bx + j * .6 - 1, by + j - (sd > 0 ? 0 : 0), X.blush, 7); }
    // ---- crown & bangs: a round crown with a curved sheen; locks fan out from a parting and end in hooked points
    ell(HX(26), 27, 29, 21, (x, y, u, v, d) => { if (y > 33) return; const ring = Math.abs(d - .62) < .07 && v < -.1; put(x, y, d > .965 ? X.line : ring ? X.hairHi : v < -.7 ? "H" : u > .5 ? "j" : "h", 8); });
    const part = HX(30) + 4;
    const locks = [[-27, 6, 12, -.35], [-21, 7, 17, -.25], [-14, 8.5, 21, -.15], [-6.5, 7, 17, -.08], [-1, 5, 11, .05], [4.5, 8, 22, .12], [11.5, 8.5, 20, .2], [18.5, 7, 16, .28], [24.5, 6, 12, .36]];
    locks.forEach(([lx, lw, len, lean], i) => {
      const x0 = part + lx, y0 = 25 + Math.abs(lx) * .08;
      for (let k = 0; k < len; k++) { const t = k / len, w = lw * (1 - Math.pow(t, 1.4)) * .5; const xc = x0 + lean * k * (1 + t) + (t > .7 ? -Math.sign(lean || 1) * (t - .7) * 4 : 0);
        for (let q = -w; q <= w; q += .5) { const x = Math.round(xc + q), y = Math.round(y0 + k); const edge = q < -w + .9; const shade = edge ? X.line : t > .74 ? "J" : (q < 0 && t < .45 && i % 2 === 0) ? "H" : t > .5 || q > w * .5 ? "j" : "h"; put(x, y, shade, 9 + (i % 3) * .05); } }
    });
    // side locks framing the face: thin, a little wavy, ending in marten-dark points
    for (const sd of [-1, 1]) for (let y = 30; y < 78; y++) { const t = (y - 30) / 48; const w = 4.2 * (1 - Math.pow(t, 2)) + .8; for (let k = 0; k < w; k++) { const x = HX(y) + sd * (21.5 - k + Math.sin(t * 5.5) * 1.2 + t * 2); put(x, y, k === 0 ? X.line : k >= w - 1 ? "j" : t > .8 ? "t" : t > .64 ? "J" : k < 2 ? "j" : "h", 9.5); } }
    // extras
    if (M.sweat) { ell(HX(20) + 26, 30, 2.5, 3.6, (x, y, u, v, d) => put(x, y, d > .8 ? "#5a7ab0" : v < -.2 ? "#ffffff" : "#bcd4f0", 13)); }
    if (M.vein) for (const [dx, dy] of [[0, 0], [1, 0], [2, 1], [-1, 1], [0, 2], [2, 2], [1, 3]]) put(HX(20) + 22 + dx, 22 + dy, "#d23a2a", 13);
    if (M.spark) for (const [x, y] of [[14, 30], [82, 26], [78, 40]]) { put(x, y, "#fff6d0", 13); put(x - 1, y, "#f6d36a", 13); put(x + 1, y, "#f6d36a", 13); put(x, y - 1, "#f6d36a", 13); put(x, y + 1, "#f6d36a", 13); }
    const cv = document.createElement("canvas"); cv.width = W; cv.height = W; const g = cv.getContext("2d"); const id = g.createImageData(W, W); id.data.set(buf); g.putImageData(id, 0, 0);
    this.cache[expr] = cv; return cv;
  },
  eye2(put, bez, ell, ex, ey, sd, M, X) {
    const E = M.eye;
    if (E === "closed" || E === "happy") { bez([ex - 6, ey + (E === "happy" ? 2 : 0)], [ex, ey + (E === "happy" ? -4 : 2)], [ex + 6, ey + (E === "happy" ? 2 : 0)], .8, (x, y) => put(x, y, X.lash, 10)); return; }
    const h = E === "wide" ? 14 : E === "half" || E === "smug" || E === "angry" ? 9 : 12.5, top = ey - h * .6;
    // iris & white
    ell(ex, ey, 5.6, h / 2, (x, y, u, v, d) => {
      const vv = (y - (ey - h / 2)) / h; let c = vv < .35 ? X.irisD : vv < .7 ? X.irisM : X.irisL;
      if (Math.abs(u) > .78 && vv > .3) c = X.white;
      if (Math.abs(x + .5 - ex - sd * .3) < 1.6 && vv > .25 && vv < .82) c = "p";
      put(x, y, c, 10);
    });
    // lids: thick upper lash with an outward flick, thin lower line
    const lid = E === "half" || E === "smug" ? ey - h * .18 : E === "angry" ? ey - h * .25 : top + 1;
    const tiltIn = E === "angry" ? 2.5 : E === "sad" || M.sadLid ? -2 : 0;
    for (let y = Math.floor(top - 2); y < lid; y++) for (let x = Math.floor(ex - 6.5); x <= ex + 6.5; x++) put(x, y + (x - ex) * sd * tiltIn * .12, "s", 10.5);
    bez([ex - sd * 6.5, lid + 2 - (E === "angry" ? -tiltIn : 0)], [ex, lid - 1.8], [ex + sd * 7.5, lid + .5 + tiltIn * .3], 1.1, (x, y) => put(x, y, X.lash, 11));
    bez([ex + sd * 6.5, lid], [ex + sd * 8.5, lid - 1.2], [ex + sd * 9.5, lid - 2.6], .6, (x, y) => put(x, y, X.lash, 11));
    bez([ex - 4.5, ey + h / 2], [ex, ey + h / 2 + 1], [ex + 4.5, ey + h / 2], .4, (x, y) => put(x, y, X.irisD, 11));
    // highlights
    if (E !== "half" && E !== "angry" && E !== "smug") { ell(ex - sd * 1.8 - 1, ey - h * .18, 1.7, 1.9, (x, y) => put(x, y, X.white, 12)); put(ex + sd * 2, ey + h * .24, X.white, 12); }
    else put(ex - sd * 2, ey, X.white, 12);
  },
  mouth2(put, ell, mx, my, m, X) {
    const L = X.line, red = "#c2443a", dk = "#6a1f18";
    if (m === "idle") { put(mx - 1, my, L, 8); put(mx, my, L, 8); put(mx + 1, my, L, 8); return; }
    if (m === "smile") { for (let k = -3; k <= 3; k++) put(mx + k, my + Math.round(Math.cos(k / 3) * -1.5) + 1, L, 8); return; }
    if (m === "flat") { for (let k = -2; k <= 2; k++) put(mx + k, my, L, 8); return; }
    if (m === "pout") { put(mx - 2, my + 1, L, 8); put(mx - 1, my, L, 8); put(mx, my, L, 8); put(mx + 1, my + 1, L, 8); return; }
    if (m === "fang") { for (let k = -3; k <= 3; k++) put(mx + k, my + (Math.abs(k) === 3 ? -1 : 0), L, 8); put(mx + 2, my + 1, "#ffffff", 8.5); put(mx + 2, my + 2, "#ffffff", 8.5); put(mx + 1, my + 1, L, 8); return; }
    const rx = m === "o" ? 2.2 : m === "wail" ? 5 : 3.6, ry = m === "o" ? 2.6 : m === "wail" ? 4 : 2.6;
    ell(mx, my + 1, rx, ry, (x, y, u, v, d) => put(x, y, d > .8 ? L : v > .3 ? red : dk, 8));
  },
  moods: {
    normal: { eye: "open", brow: 0, mouth: "idle", ears: 0, tail: 0, blush: true },
    smug: { eye: "smug", brow: -1, mouth: "fang", ears: .6, tail: 1, blush: true, tilt: 1.5 },
    grin: { eye: "happy", brow: .4, mouth: "fang", ears: 1, tail: 1.5, blush: true, spark: true },
    surprised: { eye: "wide", brow: 1.6, browUp: 3, mouth: "o", ears: 1.5, tail: 1.7, blush: false },
    worried: { eye: "open", brow: 2, mouth: "flat", ears: -1, tail: -.5, blush: false, sweat: true, sadLid: true },
    sad: { eye: "half", brow: 2.2, mouth: "pout", ears: -1.5, tail: -1, blush: false, sadLid: true, tilt: -1.5 },
    angry: { eye: "angry", brow: -2.4, mouth: "open", ears: .4, tail: 1.2, blush: true, vein: true },
    thinking: { eye: "half", brow: .8, mouth: "flat", ears: .1, tail: 0, blush: false, tilt: 2 },
    shout: { eye: "closed", brow: -1.6, mouth: "wail", ears: 1.6, tail: 1.9, blush: true },
    soft: { eye: "half", brow: .5, mouth: "smile", ears: -.3, tail: .2, blush: true, tilt: -1 },
    dazed: { eye: "closed", brow: 1.5, mouth: "o", ears: -1.2, tail: -1, blush: false, sweat: true },
  },
};
