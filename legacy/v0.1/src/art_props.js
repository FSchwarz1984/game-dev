/* =====================================================================
   ART · PROPS — rocks with chiselled facets, the pass shrine in every
   state of ruin and repair, stone lanterns, jizō, torii, way-markers,
   building materials, the 99 offerings, the radio, the railway.
   ===================================================================== */
"use strict";
const PROPS = {
  /* ---------------- rocks: Voronoi facets on a dome, moss on what faces up ---------------- */
  rock(seed, w = 24, h = 18, o = {}) {
    const R = RNG(seed * 17 + 5), W = w + 4, H = h + 4, s = new SB(W, H), cx = W / 2, cy = H / 2 + 1;
    const rr = o.warm ? PAL.stoneWarm : PAL.stone; const mossK = o.moss ?? .55;
    const sites = []; const ns = Math.max(5, Math.round(w * h / 38));
    for (let i = 0; i < ns; i++) sites.push({ x: cx + R.range(-w / 2, w / 2), y: cy + R.range(-h / 2, h / 2), j: [R.range(-.35, .35), R.range(-.3, .3)], t: R() });
    const rx = w / 2, ry = h / 2;
    PX.ell(cx, cy, rx, ry, (x, y, u, v, d) => {
      // flatter top so the rock sits like a boulder seen from above-front
      let best = null, bd = 1e9, b2 = 1e9; for (const p of sites) { const dd = hyp(x + .5 - p.x, y + .5 - p.y); if (dd < bd) { b2 = bd; bd = dd; best = p; } else if (dd < b2) b2 = dd; }
      const pu = (best.x - cx) / rx, pv = (best.y - cy) / ry, pd = Math.min(.98, hyp(pu, pv));
      let nx = pu * .9 + best.j[0], ny = -pv * .95 + best.j[1] + .25, nz = Math.sqrt(Math.max(.05, 1 - pd * pd)) + .2; const l = hyp(nx, ny, nz); nx /= l; ny /= l; nz /= l;
      const up = ny * .7 + nz * .7; // how much the facet faces the sky
      const crack = b2 - bd < .9 && best.t > .55;
      let t = .52 + (best.t - .5) * .25 - (crack ? .28 : 0) - (v > .55 ? .12 : 0);
      const i = y * W + x; if (!s.nx) s.nx = new Float32Array(W * H * 3);
      const mz = Math.sqrt(Math.max(0, 1 - d * d)) * Math.min(rx, ry);
      if (up > .82 && vnoise(x * .32, y * .32, seed) > 1 - mossK && !crack) {
        s.px(x, y, PAL.moss[clamp(Math.round((.5 + (hash2(x >> 1, y >> 1, seed) - .5) * .4) * 5), 0, 5)], { z: mz + 1, m: MAT.MOSS, b: mz * .4 });
      } else {
        if (hash2(x, y, seed + 3) < .03) t += .2; // lichen fleck
        s.px(x, y, rr[clamp(Math.round(t * (rr.length - 1)), 0, rr.length - 1)], { z: mz, m: MAT.STONE, b: mz * .4 });
      }
      s.nx[i * 3] = nx; s.nx[i * 3 + 1] = ny; s.nx[i * 3 + 2] = nz;
    }, { amp: .22, seed: seed + 2, freq: 2.6 });
    PX.selout(s, { k: .7 });
    PX.normals(s, 1);
    return s;
  },
  pebbles(seed) { const R = RNG(seed), s = new SB(18, 10); for (let k = 0; k < 6; k++) { const x = R.range(3, 15), y = R.range(3, 8), r = R.range(1.2, 2.2); PX.ell(x, y, r, r * .75, (xx, yy, u, v, d) => s.pz(xx, yy, PAL.stone[clamp(Math.round((.6 - v * .25) * 6), 0, 6)], (1 - d) * 2, { m: MAT.STONE })); } PX.normals(s, 1); return s; },
  /* ---------------- the pass shrine 祠 — five states ---------------- */
  // stage: 0 wreck, 1 foundation, 2 frame, 3 roofed, 4 complete
  hokora(stage) {
    const W = 56, H = 64, s = new SB(W, H), cx = 28, by = H - 2;
    const wood = PAL.wood, red = PAL.woodRed, st = PAL.stone;
    const box = (x0, y0, x1, y1, col, z, m, b = 0) => { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) s.pz(x, y, col(x, y), z(x, y), { m, b }); };
    // stone plinth (always present, cracked in the wreck)
    if (stage >= 1 || stage === 0) {
      box(cx - 17, by - 9, cx + 17, by, (x, y) => st[clamp(Math.round((y < by - 6 ? .66 : .48) * 6 + (hash2(x >> 2, y >> 1, 7) - .5) * 1.2), 0, 6)], (x, y) => (y < by - 6 ? 6 : 3), MAT.STONE, 2);
      for (let x = cx - 17; x <= cx + 17; x += 7) for (let y = by - 9; y <= by; y++) s.mul(x, y, .8);
      if (stage === 0) for (let y = by - 9; y <= by; y++) { const x = cx + 4 + ((y * 3) % 5) - 2; s.mul(x, y, .55); }
    }
    if (stage === 0) {
      // the wreck: a slewed half-roof on the plinth, splintered boards, the back half simply… not here
      for (let k = 0; k < 6; k++) { const x0 = cx - 15 + k * 5, a = (k % 2 ? .3 : -.2); PX.stroke(x0, by - 10, x0 + 9 * Math.cos(a), by - 12 - 4 * Math.sin(a) + (k % 3), 1.2, 1.2, (x, y, t) => s.pz(x, y, wood[clamp(2 + (k % 2), 0, 5)], 8 + t, { m: MAT.WOOD, b: 3 })); }
      PX.poly([[cx - 20, by - 18], [cx + 6, by - 30], [cx + 18, by - 20], [cx - 6, by - 10]], (x, y) => s.pz(x, y, ((x + y) % 4 === 0) ? PAL.barkCedar[1] : PAL.barkCedar[2 + ((y >> 1) & 1)], 12, { m: MAT.WOOD, b: 5 }));
      for (let x = cx - 20; x < cx + 18; x++) { const y = Math.round(lerp(by - 18, by - 30, (x - cx + 20) / 26)); if (x < cx + 6) s.pz(x, y, PAL.barkCedar[4], 13, { m: MAT.WOOD, b: 5 }); }
      // the cut: one clean vertical edge where the shrine stops
      for (let y = by - 30; y < by - 9; y++) s.pz(cx + 13, y, wood[4], 10, { m: MAT.WOOD, b: 4 });
      PX.selout(s, { k: .7 }); PX.normals(s, 1);
      return s;
    }
    const postsUp = stage >= 2;
    if (postsUp) {
      for (const px of [cx - 13, cx + 12]) box(px, by - 40, px + 2, by - 9, (x, y) => wood[clamp(Math.round((.5 + (x === px ? .2 : 0) - (y > by - 12 ? .1 : 0)) * 5), 0, 5)], () => 8, MAT.WOOD, 3);
      box(cx - 13, by - 41, cx + 14, by - 39, (x, y) => red[clamp(Math.round((.5 + (y === by - 41 ? .25 : 0)) * 4), 0, 4)], () => 9, MAT.WOOD, 3);
      // inner sanctum box with lattice doors
      box(cx - 10, by - 36, cx + 9, by - 10, (x, y) => { const lat = (x - cx + 20) % 4 === 0 || (y - by + 40) % 5 === 0; return lat ? wood[1] : (stage >= 4 ? [58, 44, 34] : [40, 32, 28]); }, () => 6, MAT.WOOD, 2);
      box(cx - 10, by - 12, cx + 9, by - 10, () => wood[3], () => 7, MAT.WOOD, 2);
    }
    if (stage >= 3) {
      // shingled cedar-bark roof with curved eaves
      for (let y = by - 58; y <= by - 40; y++) {
        const t = (y - (by - 58)) / 18; const hw = lerp(4, 24, Math.pow(t, .75)) + (t > .85 ? (t - .85) * 18 : 0);
        for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw); x++) {
          const row = Math.floor((y - by + 58) / 3), shingle = (x + (row % 2) * 2) % 4 === 0;
          let tt = .45 + (row % 2 ? .08 : -.02) - (shingle ? .18 : 0) + (y === by - 58 ? .2 : 0);
          s.pz(x, y, PAL.barkCedar[clamp(Math.round(tt * 5), 0, 5)], 12 + (1 - Math.abs(x - cx) / hw) * 3 - t * 2, { m: MAT.WOOD, b: 6 + (1 - t) * 3 });
        }
      }
      for (let x = cx - 26; x <= cx + 26; x++) { const e = Math.abs(x - cx) / 26, y = by - 40 - Math.round(Math.pow(e, 3) * 4); s.pz(x, y, PAL.barkCedar[4], 14, { m: MAT.WOOD, b: 7 }); s.pz(x, y + 1, PAL.barkCedar[1], 13, { m: MAT.WOOD, b: 7 }); }
      // ridge cap
      for (let x = cx - 6; x <= cx + 6; x++) s.pz(x, by - 59, PAL.barkCedar[5], 15, { m: MAT.WOOD, b: 8 });
    }
    if (stage >= 4) {
      // a fresh shimenawa across the front and the holed stone glowing faintly inside
      for (let x = cx - 12; x <= cx + 12; x++) { const y = by - 37 + Math.round(Math.pow((x - cx) / 12, 2) * -2 + 2); s.pz(x, y, PAL.straw[(x & 2) ? 4 : 2], 11, { m: MAT.STRAW, b: 5 }); s.pz(x, y + 1, PAL.straw[1], 10.8, { m: MAT.STRAW, b: 5 }); }
      for (const sx of [-7, 0, 7]) FLORA.shide(s, cx + sx, by - 35, 12);
      PX.ell(cx, by - 20, 3.2, 3.2, (x, y, u, v, d) => { if (d < .38) return; s.pz(x, y, PAL.stone[clamp(Math.round((.75 - v * .3) * 6), 0, 6)], 9, { m: MAT.STONE, b: 3, e: 2 }); });
    }
    PX.selout(s, { k: .7 }); PX.normals(s, 1);
    return s;
  },
  // the back half of the shrine, as it now hangs in the Far (rendered pale by the ghost pass)
  hokoraGhost() { const s = PROPS.hokora(4); return s; },
  ishidoro(seed = 1, lit = false) { // stone lantern 石灯籠
    const W = 20, H = 42, s = new SB(W, H), cx = 10, by = H - 1, st = PAL.stone;
    const tier = (y0, y1, hw0, hw1, z) => { for (let y = y0; y <= y1; y++) { const t = (y - y0) / Math.max(1, y1 - y0), hw = lerp(hw0, hw1, t); for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw - 1); x++) { const sx = (x + .5 - cx) / hw; s.pz(x, y, st[clamp(Math.round((.55 - sx * .15 + (y === y0 ? .2 : 0) + (hash2(x, y, seed) - .5) * .15) * 6), 0, 6)], z + (1 - Math.abs(sx)) * 2, { m: MAT.STONE, b: 2 }); } } };
    tier(by - 4, by, 8, 9, 2); tier(by - 18, by - 5, 2.5, 3, 3); tier(by - 22, by - 19, 6, 7, 4);
    tier(by - 31, by - 23, 5, 5, 4);
    for (let y = by - 29; y <= by - 25; y++) for (let x = cx - 2; x <= cx + 1; x++) s.px(x, y, lit ? [255, 214, 140] : [36, 32, 36], { z: 6, m: lit ? MAT.LAMP : MAT.STONE, e: lit ? 6 : 0, b: 2 });
    tier(by - 37, by - 32, 3, 9, 6); tier(by - 40, by - 38, 1, 2, 7);
    if (seed % 2) for (let k = 0; k < 14; k++) { const x = cx - 8 + (hash2(k, 1, seed) * 16 | 0), y = by - 36 + (hash2(k, 2, seed) * 4 | 0); if (s.a(x, y)) s.px(x, y, PAL.moss[3], { m: MAT.MOSS }); }
    PX.selout(s, { k: .7 }); PX.normals(s, 1);
    return s;
  },
  jizo(seed = 1) { // 地蔵 with a faded red bib
    const W = 18, H = 26, s = new SB(W, H), cx = 9, by = H - 1, st = PAL.stoneWarm;
    PX.ell(cx, by - 2, 7, 2.6, (x, y, u, v) => s.pz(x, y, st[2], 1, { m: MAT.STONE }));
    PX.ell(cx, by - 9, 5.5, 8, (x, y, u, v, d) => s.pz(x, y, st[clamp(Math.round((.55 - u * .15 - v * .1) * 5), 0, 5)], Math.sqrt(1 - d * d) * 5, { m: MAT.STONE, b: 2 }));
    PX.ell(cx, by - 19, 4.2, 4.4, (x, y, u, v, d) => s.pz(x, y, st[clamp(Math.round((.6 - u * .15 - v * .15) * 5), 0, 5)], 5 + Math.sqrt(1 - d * d) * 4, { m: MAT.STONE, b: 3 }));
    s.px(cx - 2, by - 19, st[0], { m: MAT.STONE }); s.px(cx + 1, by - 19, st[0], { m: MAT.STONE });
    const bib = ramp("#b23a2e", 4, { lo: .45, hi: .35 });
    PX.poly([[cx - 5, by - 15], [cx + 5, by - 15], [cx + 4, by - 9], [cx - 4, by - 9]], (x, y) => s.pz(x, y, bib[clamp(Math.round((.5 + (y === by - 15 ? .2 : 0) - (x > cx ? .1 : 0)) * 3), 0, 3)], 9, { m: MAT.CLOTH, b: 3 }));
    if (seed % 3 === 0) for (let k = 0; k < 6; k++) s.px(cx - 3 + k, by - 23 + (k % 2), PAL.moss[3], { m: MAT.MOSS });
    PX.selout(s, { k: .7 }); PX.normals(s, 1);
    return s;
  },
  torii(w = 46, h = 50) { // a small weathered torii, vermilion gone to rust
    const s = new SB(w, h), red = PAL.woodRed, by = h - 1;
    for (const px of [8, w - 11]) for (let y = 9; y <= by; y++) for (let x = px; x <= px + 2; x++) s.pz(x, y, red[clamp(Math.round((.5 + (x === px ? .2 : x === px + 2 ? -.15 : 0) - (y > by - 5 ? .25 : 0)) * 4), 0, 4)], 4, { m: MAT.WOOD, b: 2 });
    for (let y = 2; y <= 6; y++) for (let x = 1; x < w - 1; x++) { const e = Math.abs(x - w / 2) / (w / 2); const yy = y - Math.round(Math.pow(e, 3) * 2); s.pz(x, yy, y < 4 ? [46, 40, 40] : red[clamp(Math.round((.55 - (y - 4) * .1) * 4), 0, 4)], 6, { m: MAT.WOOD, b: 3 }); }
    for (let y = 12; y <= 14; y++) for (let x = 5; x < w - 5; x++) s.pz(x, y, red[y === 12 ? 3 : 2], 5, { m: MAT.WOOD, b: 3 });
    for (let y = 7; y <= 11; y++) for (let x = w / 2 - 3; x <= w / 2 + 2; x++) s.pz(x, y, PAL.wood[2], 5.5, { m: MAT.WOOD, b: 3 });
    PX.selout(s, { k: .72 }); PX.normals(s, 1);
    return s;
  },
  michishirube(seed = 1) { // 道標 — a stone post with carved characters
    const W = 12, H = 30, s = new SB(W, H), st = PAL.stoneWarm;
    for (let y = 2; y < H; y++) for (let x = 2; x < W - 2; x++) { const top = y < 4 && (x === 2 || x === W - 3); if (top) continue; s.px(x, y, st[clamp(Math.round((.55 - (x - 2) / (W - 4) * .25 + (y < 4 ? .2 : 0) + (hash2(x, y, seed) - .5) * .15) * 5), 0, 5)], { z: 3, m: MAT.STONE, b: 2 }); }
    for (let y = 7; y < H - 4; y += 3) for (let x = 4; x < W - 4; x++) if (hash2(x, y, seed) < .6) s.px(x, y, st[0], { z: 2.4, m: MAT.STONE, b: 2 });
    PX.selout(s, { k: .72 }); PX.normals(s, 1); return s;
  },
  /* ---------------- building materials & loose things ---------------- */
  log(seed, L = 46) { // a fallen cedar log seen from the side, end grain toward the camera
    const R = RNG(seed), W = L + 4, H = 16, s = new SB(W, H), r = 6;
    for (let x = 2; x < W - 6; x++) for (let y = H - 2 - 2 * r; y <= H - 2; y++) { const v = (y - (H - 2 - r)) / r; if (Math.abs(v) > 1) continue; const f = hash2(Math.floor(x / 5), y, seed);
      s.px(x, y, PAL.barkCedar[clamp(Math.round((.5 - v * .2 + (f - .5) * .3) * 5), 0, 5)], { z: Math.sqrt(1 - v * v) * r, m: MAT.BARK, b: 3 }); }
    PX.ell(W - 6, H - 2 - r, 3.3, r, (x, y, u, v, d) => { const ring = Math.floor(d * 4) % 2; s.pz(x, y, d > .85 ? PAL.barkCedar[1] : ring ? [206, 168, 118] : [184, 140, 92], r + 1, { m: MAT.WOOD, b: 4 }); });
    for (let k = 0; k < 5; k++) { const x = R.int(4, W - 10), y = H - 2 - 2 * r + R.int(0, 2); s.px(x, y, PAL.moss[3], { z: r + .5, m: MAT.MOSS }); s.px(x + 1, y, PAL.moss[2], { z: r + .5, m: MAT.MOSS }); }
    PX.selout(s, { k: .7 }); PX.normals(s, 1); return s;
  },
  pole(seed, L = 40) { // a bamboo pole lying down
    const W = L + 2, H = 7, s = new SB(W, H);
    for (let x = 1; x < W - 1; x++) for (let y = 1; y < 6; y++) { const v = (y - 3.5) / 2.5; const node = x % 12 === 0; s.px(x, y, PAL.bamboo[clamp(Math.round((.55 - v * .25 - (node ? .3 : 0)) * 5), 0, 5)], { z: (1 - Math.abs(v)) * 2.5, m: MAT.BAMBOO, b: 2 }); }
    PX.selout(s, { k: .75 }); PX.normals(s, 1); return s;
  },
  bark(seed) { // a sheet of stripped cedar bark, rolled at the edges
    const W = 18, H = 12, s = new SB(W, H);
    for (let y = 2; y < H - 1; y++) for (let x = 1; x < W - 1; x++) { const v = (y - 6) / 5; if (Math.abs(v) > 1) continue; const f = hash2(x, Math.floor(y / 2), seed);
      s.px(x, y, PAL.barkCedar[clamp(Math.round((.55 - Math.abs(v) * .25 + (f - .5) * .4 + (x % 5 === 0 ? -.2 : 0)) * 5), 0, 5)], { z: (1 - v * v) * 2, m: MAT.WOOD, b: 2 }); }
    PX.selout(s, { k: .72 }); PX.normals(s, 1); return s;
  },
  vine(seed) { // a coil of kudzu vine
    const W = 16, H = 12, s = new SB(W, H);
    for (let k = 0; k < 3; k++) PX.ell(8, 7, 6 - k, 4 - k * .6, (x, y, u, v, d) => { if (d < .72) return; s.pz(x, y, PAL.kudzu[clamp(1 + ((x + y + k) % 3 === 0 ? 2 : 1), 0, 5)].map((c, i) => c * (i === 1 ? .85 : .7)), 3 + k, { m: MAT.WOOD, b: 2 }); });
    for (let k = 0; k < 3; k++) { const x = 4 + k * 4, y = 3 + (k % 2); s.pz(x, y, PAL.kudzu[3], 6, { m: MAT.LEAF, b: 3 }); s.pz(x + 1, y, PAL.kudzu[4], 6, { m: MAT.LEAF, b: 3 }); s.pz(x, y + 1, PAL.kudzu[2], 6, { m: MAT.LEAF, b: 3 }); }
    PX.selout(s, { k: .75 }); PX.normals(s, 1); return s;
  },
  flatstone(seed) { const s = PROPS.rock(seed + 300, 20, 9, { moss: .2 }); return s; },
  holedstone() { // 穴あき石 — the god-body of the pass: a river stone with a hole worn through
    const W = 14, H = 13, s = new SB(W, H);
    PX.ell(7, 6.5, 5.6, 5.2, (x, y, u, v, d) => { const hole = hyp(u + .1, v + .05) < .32; if (hole) return; s.px(x, y, PAL.stone[clamp(Math.round((.62 - u * .15 - v * .2) * 6), 0, 6)], { z: Math.sqrt(1 - d * d) * 4, m: MAT.STONE, b: 2, e: 1 }); });
    PX.selout(s, { k: .7 }); PX.normals(s, 1); return s;
  },
  basket(open = false) { // 葛籠 — a wicker trunk of plaited kudzu; later it walks
    const W = 22, H = 20, s = new SB(W, H), wv = ramp("#a17a45", 5, { lo: .5, hi: .4 });
    for (let y = 5; y < H - 1; y++) for (let x = 2; x < W - 2; x++) { const weave = ((x >> 1) + (y >> 1)) % 2; const edge = x === 2 || x === W - 3 || y === 5 || y === H - 2;
      s.px(x, y, edge ? wv[1] : wv[clamp(Math.round((.5 + (weave ? .14 : -.08) - (x - 2) / (W - 4) * .15) * 4), 0, 4)], { z: 4, m: MAT.STRAW, b: 3 }); }
    for (let y = 2; y < 6; y++) for (let x = 1; x < W - 1; x++) s.px(x, y - (open ? 2 : 0), wv[clamp(Math.round((.68 - (y - 2) * .08 + (((x >> 1) + y) % 2 ? .08 : 0)) * 4), 0, 4)], { z: 6, m: MAT.STRAW, b: 4 });
    for (let x = 4; x < W - 4; x++) s.px(x, 11, [124, 52, 40], { z: 4.5, m: MAT.CLOTH, b: 3 }); // a red cord
    PX.selout(s, { k: .68 }); PX.normals(s, 1); return s;
  },
  radio() { // a cracked bakelite valve radio, offered by someone long ago
    const W = 18, H = 14, s = new SB(W, H), bk = ramp("#5a3a2a", 5, { lo: .5, hi: .4 });
    for (let y = 2; y < H - 1; y++) for (let x = 1; x < W - 1; x++) { const r = y < 4 && (x < 3 || x > W - 4); if (r) continue; s.px(x, y, bk[clamp(Math.round((.55 - (y - 2) / 12 * .2 + (y === 2 ? .2 : 0)) * 4), 0, 4)], { z: 4, m: MAT.LACQUER, b: 2 }); }
    for (let y = 4; y < H - 3; y++) for (let x = 3; x < 9; x++) s.px(x, y, ((x + y) % 2) ? [150, 128, 96] : [118, 98, 74], { z: 3.5, m: MAT.CLOTH, b: 2 });
    PX.ell(13, 7, 2.6, 2.6, (x, y, u, v, d) => s.px(x, y, d > .7 ? [70, 60, 50] : [214, 196, 150], { z: 4.5, m: MAT.GLASS, b: 2, e: 0 }));
    s.px(13, 7, [120, 40, 30], { z: 5, m: MAT.METAL });
    for (let x = 4; x < 9; x++) s.px(x, 3, [200, 170, 110], { z: 4.2, m: MAT.METAL });
    PX.selout(s, { k: .7 }); PX.normals(s, 1); return s;
  },
  /* ---------------- offerings: small things people left at the pass ---------------- */
  offering(kind) {
    const W = 12, H = 12, s = new SB(W, H), P = (x, y, c, m = MAT.CLOTH, z = 2, e = 0) => s.px(x, y, typeof c === "string" ? hexRGB(c) : c, { z, m, e, b: 1 });
    const draw = OFFER_ART[kind] || OFFER_ART.coin; draw(P, s);
    PX.selout(s, { k: .72 }); PX.normals(s, 1); return s;
  },
  /* ---------------- the line through the mountain ---------------- */
  tunnel() { // a stone-faced railway portal
    const W = 132, H = 96, s = new SB(W, H), cx = 66, by = H - 1, st = PAL.stoneWarm;
    for (let y = 8; y <= by; y++) for (let x = 6; x < W - 6; x++) {
      const dx = x - cx, ay = by - y; const inArch = (Math.abs(dx) < 30 && ay < 46) || hyp(dx, (ay - 46) * 1.15) < 30;
      if (inArch) continue;
      const row = Math.floor(y / 6), col = Math.floor((x + (row % 2) * 6) / 12); const mortar = y % 6 === 0 || (x + (row % 2) * 6) % 12 === 0;
      const t = mortar ? .25 : .5 + (hash2(col, row, 3) - .5) * .3 + (y < 14 ? .15 : 0);
      s.px(x, y, st[clamp(Math.round(t * 5), 0, 5)], { z: 6, m: MAT.STONE, b: 2 });
    }
    // voussoirs and the dark throat
    for (let a = 0; a <= Math.PI; a += .012) { for (let r = 30; r < 36; r++) { const x = Math.round(cx + Math.cos(a) * r), y = Math.round(by - 46 - Math.sin(a) * r / 1.15); const seg = Math.floor(a / .2) % 2; s.px(x, y, st[seg ? 3 : 4], { z: 7, m: MAT.STONE, b: 3 }); } }
    for (let y = 8; y <= by; y++) for (let x = 6; x < W - 6; x++) { const dx = x - cx, ay = by - y; const inArch = (Math.abs(dx) < 30 && ay < 46) || hyp(dx, (ay - 46) * 1.15) < 30; if (inArch && !s.a(x, y)) s.px(x, y, [14, 13, 16], { z: -20, m: MAT.ROCK, b: 0 }); }
    PX.selout(s, { k: .75, inner: true }); PX.normals(s, 1); return s;
  },
  train() { // a two-tone carriage, seen end-on leaving the tunnel; it is mostly drawn as a Far ghost
    const W = 70, H = 60, s = new SB(W, H), body = ramp("#4a3b36", 5, { lo: .5, hi: .4 }), cream = PAL.cream;
    for (let y = 4; y < H - 6; y++) for (let x = 4; x < W - 4; x++) { const roof = y < 10; const win = y > 14 && y < 26 && ((x - 6) % 14) < 9 && x > 6 && x < W - 6;
      s.px(x, y, win ? [190, 200, 210] : roof ? body[3] : y > 32 ? body[1] : cream[2], { z: 6, m: win ? MAT.GLASS : MAT.METAL, b: 2 }); }
    for (const wx of [14, W - 14]) PX.ell(wx, H - 5, 5, 4, (x, y) => s.px(x, y, [30, 28, 30], { z: 4, m: MAT.METAL }));
    PX.selout(s, { k: .7 }); PX.normals(s, 1); return s;
  },
  hut() { // the charcoal-burner's hut 炭焼き小屋: thatch over dark boards
    const W = 96, H = 80, s = new SB(W, H), cx = 48, by = H - 2, th = ramp("#8a7442", 6, { lo: .5, hi: .4 });
    for (let y = by - 30; y <= by; y++) for (let x = cx - 34; x <= cx + 34; x++) { const plank = (x - cx + 64) % 6 === 0; const door = x > cx - 7 && x < cx + 7 && y > by - 24;
      s.px(x, y, door ? [26, 22, 22] : PAL.wood[clamp(Math.round((.32 + (plank ? -.15 : 0) + (hash2(x >> 1, y >> 3, 4) - .5) * .15) * 5), 0, 5)], { z: 8, m: MAT.WOOD, b: 2 }); }
    for (let y = by - 72; y <= by - 26; y++) { const t = (y - by + 72) / 46, hw = lerp(6, 46, Math.pow(t, .8)); for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw); x++) {
      const strand = hash2(x, Math.floor(y / 4), 9); const tt = .5 + (strand - .5) * .35 - (y % 8 === 0 ? .15 : 0) + (t < .1 ? .1 : 0) - (t > .92 ? .2 : 0);
      s.pz(x, y, th[clamp(Math.round(tt * 5), 0, 5)], 14 + (1 - Math.abs(x - cx) / hw) * 5, { m: MAT.STRAW, b: 8 }); } }
    for (let y = by - 76; y < by - 70; y++) for (let x = cx - 8; x <= cx + 8; x++) s.pz(x, y, th[1], 20, { m: MAT.STRAW, b: 9 });
    PX.selout(s, { k: .72 }); PX.normals(s, 1); return s;
  },
  kiln() { // 炭窯 — a clay dome, cold now
    const W = 60, H = 40, s = new SB(W, H), clay = ramp("#8a6a52", 6, { lo: .5, hi: .4 });
    PX.ell(30, 26, 26, 14, (x, y, u, v, d) => s.pz(x, y, clay[clamp(Math.round((.55 - v * .25 - u * .1 + (hash2(x >> 1, y >> 1, 3) - .5) * .15) * 5), 0, 5)], Math.sqrt(1 - d * d) * 12, { m: MAT.STONE, b: 6 }), { amp: .1, seed: 2 });
    PX.ell(30, 32, 5, 5, (x, y) => s.px(x, y, [24, 20, 20], { z: 12, m: MAT.ROCK }));
    PX.selout(s, { k: .72 }); PX.normals(s, .9); return s;
  },
  steps(n = 4) { // a short flight of stone steps (decal-ish prop for the old road)
    const W = 30, H = 6 + n * 5, s = new SB(W, H), st = PAL.stoneWarm;
    for (let k = 0; k < n; k++) { const y0 = H - 1 - k * 5; for (let y = y0 - 4; y <= y0; y++) for (let x = 2 + (k % 2); x < W - 2 - (k % 2); x++) s.px(x, y, st[clamp(Math.round(((y === y0 - 4) ? .72 : .42) * 5 + (hash2(x >> 2, k, 3) - .5)), 0, 5)], { z: k * 4, m: MAT.STONE, b: 1 }); }
    PX.normals(s, 1); return s;
  },
};

/* the offerings — each a tiny drawing; names and the lines she says live in story.js */
const OFFER_ART = {
  coin: P => { for (const [x, y] of [[4, 4], [5, 4], [6, 4], [3, 5], [7, 5], [3, 6], [7, 6], [4, 7], [5, 7], [6, 7]]) P(x, y, "#b08a3c", MAT.METAL, 2); for (const [x, y] of [[4, 5], [6, 5], [4, 6], [6, 6]]) P(x, y, "#d8b45a", MAT.METAL, 2.4); P(5, 5, "#3a2e22", MAT.METAL); P(5, 6, "#3a2e22", MAT.METAL); },
  sandal: P => { for (let y = 2; y < 11; y++) for (let x = 4; x < 8; x++) P(x, y, (y + x) % 3 ? "#b89a5c" : "#9c7f48", MAT.STRAW, 1.5); P(5, 3, "#7a2c24", MAT.CLOTH, 2.5); P(6, 3, "#7a2c24", MAT.CLOTH, 2.5); P(5, 5, "#7a2c24", MAT.CLOTH, 2.5); },
  crane: P => { const pts = [[2, 7], [3, 6], [4, 6], [5, 5], [6, 4], [7, 4], [8, 3], [9, 2], [5, 6], [6, 6], [7, 6], [6, 7], [4, 7], [8, 4]]; for (const [x, y] of pts) P(x, y, y < 5 ? "#e8e0cf" : "#cfc5b0", MAT.PAPER, 2); P(9, 2, "#c43c2e", MAT.PAPER, 2.5); },
  marble: P => { for (let y = 4; y < 9; y++) for (let x = 4; x < 9; x++) { const d = hyp(x - 6, y - 6); if (d > 2.4) continue; P(x, y, d < 1 ? "#cfe8f0" : (x + y) % 2 ? "#4f8fb0" : "#6fb0c8", MAT.GLASS, 2 + (2.4 - d)); } P(5, 5, "#ffffff", MAT.GLASS, 4); },
  top: P => { for (let y = 3; y < 9; y++) { const hw = y < 6 ? (y - 2) : (9 - y); for (let x = 6 - hw; x <= 5 + hw; x++) P(x, y, y === 5 ? "#c43c2e" : y < 5 ? "#e3b04b" : "#3a6a9a", MAT.WOOD, 2); } P(5, 2, "#6a4a30", MAT.WOOD, 3); P(6, 2, "#6a4a30", MAT.WOOD, 3); P(5, 9, "#6a4a30", MAT.WOOD, 2); },
  comb: P => { for (let x = 2; x < 10; x++) { P(x, 4, "#7a3a2a", MAT.LACQUER, 3); P(x, 5, "#9a4a32", MAT.LACQUER, 3); if (x % 2 === 0) { P(x, 6, "#6a2e22", MAT.LACQUER, 2); P(x, 7, "#6a2e22", MAT.LACQUER, 2); } } P(5, 4, "#d8b45a", MAT.METAL, 3.3); },
  harmonica: P => { for (let x = 2; x < 10; x++) for (let y = 5; y < 8; y++) P(x, y, y === 5 ? "#d0d4d8" : y === 7 ? "#8a9096" : (x % 2 ? "#202024" : "#b0b6bc"), MAT.METAL, 2); },
  bell: P => { for (let y = 3; y < 9; y++) { const hw = Math.min(3, (y - 2) * .8 + .5); for (let x = Math.round(6 - hw); x <= Math.round(5 + hw); x++) P(x, y, y < 5 ? "#e0c070" : "#b08a3c", MAT.METAL, 2 + (3 - Math.abs(x - 5.5))); } P(5, 2, "#c43c2e", MAT.CLOTH); P(6, 2, "#c43c2e", MAT.CLOTH); P(5, 9, "#6a5020", MAT.METAL); },
  letter: P => { for (let y = 3; y < 9; y++) for (let x = 2; x < 10; x++) P(x, y, (y === 3 || y === 8 || x === 2 || x === 9) ? "#d8ccb4" : "#efe6d2", MAT.PAPER, 1.5); for (let x = 4; x < 8; x++) P(x, 5 + (x % 2), "#4a4a6a", MAT.PAPER, 1.6); P(8, 4, "#c43c2e", MAT.PAPER, 1.8); },
  doll: P => { for (let y = 5; y < 11; y++) for (let x = 4; x < 8; x++) P(x, y, y < 7 ? "#c43c2e" : "#a8302a", MAT.CLOTH, 2); for (let y = 2; y < 5; y++) for (let x = 4; x < 8; x++) P(x, y, y === 2 || x === 4 || x === 7 ? "#2a2024" : "#f0dcc0", MAT.SKIN, 2.5); },
  button: P => { for (let y = 4; y < 9; y++) for (let x = 4; x < 9; x++) { const d = hyp(x - 6, y - 6); if (d > 2.3) continue; P(x, y, "#c8b48a", MAT.METAL, 2); } P(5, 5, "#5a4a30"); P(7, 5, "#5a4a30"); P(5, 7, "#5a4a30"); P(7, 7, "#5a4a30"); },
  ribbon: P => { for (const [x, y] of [[2, 4], [3, 5], [4, 5], [5, 6], [6, 6], [7, 5], [8, 5], [9, 4], [5, 7], [4, 8], [6, 7], [7, 8]]) P(x, y, "#d06a8a", MAT.CLOTH, 2); P(5, 6, "#a04a6a", MAT.CLOTH, 2.4); },
  pipe: P => { for (let x = 2; x < 10; x++) P(x, 6, "#4a3424", MAT.WOOD, 2); for (let y = 3; y < 7; y++) { P(8, y, "#6a4a30", MAT.WOOD, 2.5); P(9, y, "#5a3e28", MAT.WOOD, 2.5); } P(8, 3, "#2a2020"); },
  cap: P => { for (let y = 4; y < 9; y++) for (let x = 3; x < 9; x++) { const d = hyp(x - 5.5, y - 6.5); if (d > 2.6) continue; P(x, y, d > 2 ? "#8a8070" : "#c0a050", MAT.METAL, 1.5); } },
  fan: P => { for (let a = 0; a <= 1; a += .07) for (let r = 2; r < 6; r++) { const x = Math.round(6 + Math.cos(-.4 - a * 2.4) * r), y = Math.round(9 + Math.sin(-.4 - a * 2.4) * r * .9); P(x, y, r < 3 ? "#6a4a30" : (Math.round(a * 14) % 2 ? "#e8dcc0" : "#d0c0a0"), MAT.PAPER, 2); } P(5, 9, "#c43c2e"); },
  candle: P => { for (let y = 4; y < 10; y++) { P(5, y, "#efe6d2", MAT.PAPER, 2); P(6, y, "#d8ccb4", MAT.PAPER, 2); } P(5, 3, "#3a2a20"); P(5, 2, "#ffd27a", MAT.LAMP, 3, 4); P(6, 9, "#c43c2e"); },
  omamori: P => { for (let y = 3; y < 10; y++) for (let x = 4; x < 8; x++) P(x, y, y === 3 ? "#e0c070" : "#7a3a8a", MAT.CLOTH, 2); P(5, 2, "#e0c070"); P(6, 2, "#e0c070"); for (let y = 5; y < 8; y++) P(5, y, "#e0c070", MAT.CLOTH, 2.2); },
  sake: P => { for (let y = 3; y < 10; y++) { const hw = y < 5 ? 1 : 2; for (let x = 6 - hw; x <= 5 + hw; x++) P(x, y, y < 5 ? "#e8e0d0" : (x === 6 - hw ? "#a8a090" : "#d8d0c0"), MAT.LACQUER, 2); } P(5, 6, "#3a3a6a"); P(6, 6, "#3a3a6a"); },
  pinwheel: P => { for (let y = 6; y < 11; y++) P(6, y, "#8a6a40", MAT.WOOD, 2); for (const [x, y, c] of [[5, 3, "#c43c2e"], [6, 3, "#c43c2e"], [7, 4, "#e3b04b"], [7, 5, "#e3b04b"], [6, 6, "#3a6a9a"], [5, 6, "#3a6a9a"], [4, 5, "#4f8a4a"], [4, 4, "#4f8a4a"]]) P(x, y, c, MAT.PAPER, 2.5); P(6, 5, "#efe6d2", MAT.PAPER, 3); },
  glasses: P => { for (const cx of [4, 8]) for (let a = 0; a < TAU; a += .5) P(Math.round(cx + Math.cos(a) * 1.6), Math.round(6 + Math.sin(a) * 1.4), "#3a3030", MAT.METAL, 2); P(6, 6, "#3a3030", MAT.METAL); P(4, 6, "#c8d8e0", MAT.GLASS, 1.5); P(8, 6, "#c8d8e0", MAT.GLASS, 1.5); },
  tin: P => { for (let y = 3; y < 10; y++) for (let x = 3; x < 9; x++) P(x, y, y < 5 ? "#c8b48a" : (x + y) % 4 === 0 ? "#2a5a8a" : "#3a6aa0", MAT.METAL, 2); P(5, 6, "#e3b04b"); P(6, 7, "#e3b04b"); },
  soldier: P => { for (let y = 5; y < 10; y++) for (let x = 5; x < 7; x++) P(x, y, y < 8 ? "#5a6a3a" : "#3a3020", MAT.METAL, 2); P(5, 4, "#d8b48a", MAT.METAL, 2.5); P(6, 4, "#d8b48a", MAT.METAL, 2.5); P(5, 3, "#4a5a30", MAT.METAL, 2.6); P(6, 3, "#4a5a30", MAT.METAL, 2.6); P(7, 6, "#3a3a3a", MAT.METAL); P(7, 5, "#3a3a3a", MAT.METAL); },
  photo: P => { for (let y = 2; y < 10; y++) for (let x = 3; x < 9; x++) P(x, y, (x === 3 || x === 8 || y === 2 || y === 9) ? "#e8e0d0" : (hash2(x, y, 4) < .5 ? "#8a8070" : "#a09888"), MAT.PAPER, 1.4); for (const [x, y] of [[5, 4], [6, 4], [5, 5], [6, 5], [4, 7], [5, 6], [6, 6], [7, 7]]) P(x, y, "#4a4038", MAT.PAPER, 1.5); },
  persimmon: P => { for (let y = 4; y < 10; y++) for (let x = 3; x < 9; x++) { const d = hyp(x - 5.5, (y - 6.8) * 1.15); if (d > 2.8) continue; P(x, y, d < 1.2 && x < 6 ? "#f0a050" : "#d86a28", MAT.PETAL, 2 + (2.8 - d)); } P(5, 4, "#4a6a2a", MAT.LEAF, 4); P(6, 4, "#3a5a22", MAT.LEAF, 4); P(5, 3, "#5a4020", MAT.WOOD, 4); },
  inkstone: P => { for (let y = 4; y < 10; y++) for (let x = 2; x < 10; x++) P(x, y, (x === 2 || x === 9 || y === 4 || y === 9) ? "#3a3a40" : y < 6 ? "#18181c" : "#2a2a30", MAT.STONE, 2); P(4, 5, "#40404a"); },
  key: P => { for (let a = 0; a < TAU; a += .6) P(Math.round(3.5 + Math.cos(a) * 1.5), Math.round(6 + Math.sin(a) * 1.5), "#b08a3c", MAT.METAL, 2); for (let x = 5; x < 10; x++) P(x, 6, "#b08a3c", MAT.METAL, 2); P(8, 7, "#b08a3c", MAT.METAL); P(9, 7, "#b08a3c", MAT.METAL); },
};
