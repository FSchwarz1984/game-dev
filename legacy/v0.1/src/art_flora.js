/* =====================================================================
   ART · FLORA — cedar, the great camphor, maple, bamboo, undergrowth,
   grass. Foliage is built from leaf cells: small domes on a jittered
   grid, so silhouettes come out scalloped like hand-drawn clusters and
   the dynamic sun gives every cluster its own lit and shaded side.
   Albedo stays in a few discrete tones; the light does the rest.
   ===================================================================== */
"use strict";
const FLORA = {
  clump(s, cx, cy, rx, ry, z0, rr, o = {}) {
    const R = RNG((o.seed || 1) * 7 + 3), n = rr.length, base = o.base ?? 3, mat = o.mat ?? MAT.LEAF;
    const cell = o.cell ?? 3.4, droop = o.droop || 0, zk = o.zk ?? .85;
    const pts = [];
    for (let gy = -ry - cell; gy <= ry + cell; gy += cell * .82) for (let gx = -rx - cell; gx <= rx + cell; gx += cell) {
      const x = gx + (R() - .5) * cell * .7 + ((Math.round(gy / cell) & 1) ? cell * .5 : 0), y = gy + (R() - .5) * cell * .6;
      const u = x / rx, v = y / ry, d = Math.sqrt(u * u + v * v); if (d > 1.02 - (R() * .18)) continue;
      pts.push({ x: cx + x, y: cy + y + droop * u * u * ry * .35, r: cell * R.range(.62, .86), t: R(), d });
    }
    if (!pts.length) pts.push({ x: cx, y: cy, r: Math.max(rx, ry), t: .5, d: 0 });
    const x0 = Math.floor(cx - rx - cell * 2), x1 = Math.ceil(cx + rx + cell * 2), y0 = Math.floor(cy - ry - cell * 2), y1 = Math.ceil(cy + ry + cell * 2 + droop * ry * .4);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      let b1 = null, d1 = 1e9, d2 = 1e9;
      for (const p of pts) { const d = hyp(x + .5 - p.x, (y + .5 - p.y) * 1.15) / p.r; if (d < d1) { d2 = d1; d1 = d; b1 = p; } else if (d < d2) d2 = d; }
      if (!b1 || d1 > 1) continue;
      const u = (x + .5 - cx) / rx, v = (y + .5 - cy) / ry, D = Math.min(1, Math.sqrt(u * u + v * v));
      const dome = Math.sqrt(Math.max(0, 1 - D * D));
      const z = z0 + dome * Math.min(rx, ry) * zk + Math.sqrt(Math.max(0, 1 - d1 * d1)) * b1.r * .9;
      let t = base / (n - 1) + (b1.t < .22 ? -.17 : b1.t > .8 ? .14 : 0) - Math.max(0, v) * .16 - b1.d * .06 + (o.tint || 0);
      if (d2 - d1 < .12 && b1.t > .5) t -= .12;
      const idx = clamp(Math.round(t * (n - 1)), 0, n - 1);
      s.pz(x, y, rr[idx], z, { m: mat, b: (o.bulge ?? 0) + dome * (o.bk ?? 2) });
    }
  },
  trunk(s, cx, yTop, yBot, wTop, wBot, rr, o = {}) {
    const seed = o.seed || 1;
    for (let y = Math.floor(yTop); y <= yBot; y++) {
      const t = (y - yTop) / Math.max(1, yBot - yTop); let hw = lerp(wTop, wBot, t) / 2;
      if (o.flare && y > yBot - o.flare) hw += Math.pow((y - (yBot - o.flare)) / o.flare, 2) * (o.flareW || 3);
      const lean = (o.lean || 0) * (1 - t) + Math.sin(t * 3 + seed) * (o.wobble ?? .5);
      for (let x = Math.floor(cx + lean - hw - 1); x <= Math.ceil(cx + lean + hw + 1); x++) {
        const sx = (x + .5 - cx - lean) / hw; if (Math.abs(sx) > 1) continue;
        // fibres: columns of tone that wander slowly, broken now and then by a darker fissure
        const col = Math.floor((x - cx - lean + 40) * (o.fib ?? .7));
        const f = hash2(col, Math.floor(y / (o.seg ?? 9)), seed), fis = hash2(col, Math.floor(y / 4), seed + 9) < .1;
        let tt = .55 + (f - .5) * .3 - (fis ? .3 : 0) - (y > yBot - 3 ? .12 : 0);
        if (o.moss && y > yBot - o.moss && hash2(x >> 1, y >> 1, seed + 4) < .5 - (yBot - y) / o.moss * .4) { s.pz(x, y, PAL.moss[clamp(Math.round((.45 + (hash2(x, y, 2) - .5) * .3) * 5), 0, 5)], Math.sqrt(1 - sx * sx) * hw + .6, { m: MAT.MOSS, b: o.b ?? 1 }); continue; }
        s.pz(x, y, rr[clamp(Math.round(tt * (rr.length - 1)), 0, rr.length - 1)], Math.sqrt(1 - sx * sx) * hw + (fis ? -.6 : 0), { m: MAT.BARK, b: (o.b ?? 1) + Math.sqrt(1 - sx * sx) });
      }
    }
  },
  /* ---------------- cedar 杉: a slim spire of drooping tiers ---------------- */
  cedar(seed, H = 150, W = 46) {
    const R = RNG(seed * 13 + 1), w = W + 14, h = H + 4, s = new SB(w, h), cx = Math.round(w / 2 + R.range(-1, 1)), baseY = h - 2;
    const crownBot = Math.round(H * R.range(.56, .66)), top = 3;
    FLORA.trunk(s, cx, top + 10, baseY, 2, R.range(5.5, 7), PAL.barkCedar, { seed, flare: 7, flareW: 3.5, moss: 8, wobble: .3, b: 1 });
    const hwAt = y => { const t = clamp((y - top) / (crownBot - top), 0, 1); return (W / 2) * (Math.pow(t, .82) * (t > .86 ? 1 - (t - .86) * 1.2 : 1)) + 1.5; };
    // tiers from the bottom up: each tier is a row of drooping sprays, outer ones hang lower
    const tiers = []; let y = crownBot - 3, k = 0;
    while (y > top + 6) { tiers.push({ y, k }); y -= R.range(7.5, 10) * (y < top + 40 ? .78 : 1); k++; }
    // a dark heart so the gaps between tiers read as depth
    for (let yy = top + 4; yy < crownBot - 2; yy++) { const hw = hwAt(yy) * .55; for (let x = Math.floor(cx - hw); x <= Math.ceil(cx + hw); x++) s.pz(x, yy, PAL.cedarDeep[1 + ((x + yy) & 1 && hash2(x, yy, seed) < .3 ? 1 : 0)], 2, { m: MAT.LEAF, b: 2 }); }
    for (let i = tiers.length - 1; i >= 0; i--) {
      const T = tiers[i], hw = hwAt(T.y); const n = hw > 14 ? 4 : hw > 8 ? 3 : 2;
      for (let j = 0; j < n; j++) {
        const f = n === 1 ? 0 : j / (n - 1) * 2 - 1; const x = cx + f * hw * .72 + R.range(-1.5, 1.5);
        const rx = hw / n * 1.5 + 2.5, ry = R.range(3.6, 5) + hw * .06;
        const zf = 6 + (1 - Math.abs(f)) * 7 + (tiers.length - i) * .15;
        FLORA.clump(s, x, T.y + Math.abs(f) * 2.6, rx, ry, zf, PAL.cedar, { seed: seed * 31 + i * 7 + j, base: 3.2 + (i / tiers.length) * .5, cell: 2.8, droop: 1.3, bulge: 4 + (1 - Math.abs(f)) * 5, zk: .75 });
        // the shadowed underside of the tier
        for (let xx = Math.floor(x - rx * .8); xx <= x + rx * .8; xx++) { const yy = Math.round(T.y + ry * .9 + Math.abs(f) * 2.6 + Math.pow((xx - x) / rx, 2) * 2); if (s.a(xx, yy) && hash2(xx, yy, seed) < .7) s.mul(xx, yy, [.72, .76, .82]); }
      }
    }
    // the leader: a thin spike with a pair of sprigs
    for (let yy = 1; yy < top + 8; yy++) s.pz(cx, yy, PAL.cedar[yy < 3 ? 4 : 3], 14, { m: MAT.LEAF, b: 7 });
    for (const [dx, dy] of [[-1, 5], [1, 6], [-1, 8], [1, 9], [-2, 9], [2, 10]]) s.pz(cx + dx, top + dy, PAL.cedar[dx < 0 ? 2 : 4], 13, { m: MAT.LEAF, b: 7 });
    PX.ao(s, 2, .25); PX.selout(s, { k: .66 });
    PX.normals(s, .8);
    return s;
  },
  /* ---------------- the great camphor 楠 (御神木) ---------------- */
  camphor(seed = 7, W = 224, H = 200) {
    const R = RNG(seed), s = new SB(W, H), cx = W / 2, baseY = H - 3;
    const bark = PAL.barkGrey;
    for (let k = 0; k < 7; k++) {
      const a = lerp(-1.25, 1.25, k / 6) + R.range(-.1, .1), L = R.range(24, 44);
      PX.stroke(cx + Math.sin(a) * 8, baseY - 7, cx + Math.sin(a) * L, baseY - 1 + R.range(-1, 2), 6.5, 1.2, (x, y, t, sx) => {
        const z = (1 - Math.abs(sx)) * 4.5 * (1 - t) + 1; const f = hash2(Math.floor(x * .6), y >> 2, 4);
        s.pz(x, y, bark[clamp(Math.round((.5 - sx * .12 + (f - .5) * .2) * 5), 0, 5)], z, { m: MAT.BARK, b: 2 });
      });
    }
    FLORA.trunk(s, cx, 72, baseY - 3, 20, 30, bark, { seed, wobble: 2.5, lean: 2, fib: .45, seg: 12, moss: 60, b: 3 });
    // limbs
    for (let k = 0; k < 7; k++) {
      const a = lerp(-1.15, 1.15, k / 6), x1 = cx + Math.sin(a) * R.range(45, 70), y1 = R.range(58, 80);
      PX.stroke(cx + Math.sin(a) * 6, 84, x1, y1, 5.5, 2, (x, y, t, sx) => s.pz(x, y, bark[clamp(Math.round((.38 - sx * .12) * 5), 0, 5)], 8 + (1 - Math.abs(sx)) * 3, { m: MAT.BARK, b: 4 }));
    }
    // crown masses — cumulus of early-summer leaves, the uppermost still bright with new growth
    const masses = [];
    for (let i = 0; i < 40; i++) {
      const a = R.range(-Math.PI, 0), rr = Math.sqrt(R());
      masses.push({ x: cx + Math.cos(a) * rr * (W * .42), y: 92 + Math.sin(a) * rr * 82 + R.range(-5, 5), r: R.range(14, 23) * (1 - rr * .22), z: 10 + (1 - rr) * 26 + R() * 6 });
    }
    for (let i = 0; i < 9; i++) masses.push({ x: cx + R.range(-86, 86), y: R.range(86, 104), r: R.range(11, 15), z: 13 + R() * 8 });
    masses.sort((a, b) => a.z - b.z);
    PX.ell(cx, 70, W * .36, 38, (x, y) => s.pz(x, y, PAL.cedarDeep[1 + ((x ^ y) & 1)], 5, { m: MAT.LEAF, b: 6 }), { amp: .2, seed: 3 });
    masses.forEach((m, k) => FLORA.clump(s, m.x, m.y, m.r * 1.1, m.r * .9, m.z, m.y < 50 && R() < .75 ? PAL.camphorNew : PAL.camphor, { seed: seed * 101 + k, base: m.y < 50 ? 2.6 : 3.1, cell: 4.2, zk: .65, bulge: 10 + m.z * .35 }));
    // shimenawa (fat twisted rope) with zigzag shide
    const ry = 132;
    for (let x = Math.floor(cx - 20); x <= cx + 20; x++) {
      const sx = (x - cx) / 20; const yy = ry + Math.round(sx * sx * 4);
      for (let k = -2; k <= 2; k++) { const twist = ((x - k * 2 + 64) % 4) < 2; s.pz(x, yy + k, PAL.straw[clamp(2 + (twist ? 1 : -1) - (Math.abs(k) === 2 ? 1 : 0), 0, 4)], 26 - Math.abs(k), { m: MAT.STRAW, b: 9 }); }
    }
    for (const sx of [-.6, 0, .6]) FLORA.shide(s, Math.round(cx + sx * 20), ry + 3 + Math.round(sx * sx * 4), 27);
    PX.ao(s, 3, .26); PX.selout(s, { k: .7 });
    PX.normals(s, .7);
    return s;
  },
  // 紙垂: a strip of paper folded into a four-step zigzag
  shide(s, x, y, z) {
    const seq = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [2, 2], [3, 2], [1, 3], [2, 3], [3, 3], [3, 4], [4, 4], [2, 5], [3, 5], [4, 5]];
    for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2, PAL.paper[dy % 2 ? 2 : 3], z, { m: MAT.PAPER, b: 10 });
    for (const [dx, dy] of seq) s.pz(x + dx - 2, y + dy * 2 + 1, PAL.paper[1], z - .2, { m: MAT.PAPER, b: 10 });
  },
  /* ---------------- maple 楓: layered horizontal plates ---------------- */
  maple(seed, red = false) {
    const R = RNG(seed * 7 + 3), W = 92, H = 98, s = new SB(W, H), cx = W / 2 + R.range(-3, 3), baseY = H - 2;
    const lean = R.range(-8, 8);
    PX.stroke(cx, baseY, cx + lean, 42, 3.2, 1.7, (x, y, t, sx) => s.pz(x, y, PAL.barkGrey[clamp(Math.round((.52 - sx * .18 + (hash2(x >> 1, y >> 2, seed) - .5) * .15) * 5), 0, 5)], 2 + (1 - Math.abs(sx)) * 2, { m: MAT.BARK, b: 1 }));
    for (let k = 0; k < 5; k++) { const a = R.range(-1.3, 1.3); PX.stroke(cx + lean * .6, 54 + k * 2, cx + lean + Math.sin(a) * 30, 32 + R.range(-10, 6), 1.6, .8, (x, y) => s.pz(x, y, PAL.barkGrey[2], 4, { m: MAT.BARK, b: 2 })); }
    const rr = red ? ramp("#a32f2a", 7, { lo: .55, hi: .45, hueShift: .04 }) : PAL.maple;
    for (let L = 0; L < 5; L++) {
      const y = 18 + L * 9 + R.range(-2, 2), wv = 36 - Math.abs(L - 2) * 5;
      for (let k = 0; k < 4; k++) { const x = cx + lean * (1 - L / 6) + R.range(-wv * .7, wv * .7), r = R.range(7, 11);
        FLORA.clump(s, x, y + R.range(-2, 2), r * 1.55, r * .58, 6 + L * 2 + R() * 4, rr, { seed: seed * 17 + L * 9 + k, base: 3.3, cell: 2.6, zk: .5, bulge: 5, droop: .4 }); }
    }
    PX.ao(s, 2, .22); PX.selout(s, { k: .7 });
    PX.normals(s, .8);
    return s;
  },
  /* ---------------- bamboo 孟宗竹 ---------------- */
  bamboo(seed, H = 196) {
    const R = RNG(seed * 5 + 2), W = 54, s = new SB(W, H + 2), baseY = H, cx = W / 2 + R.range(-3, 3), old = R() < .3;
    const culm = old ? ramp("#9a9a58", 6, { lo: .5, hi: .4 }) : ramp("#6d9452", 6, { lo: .5, hi: .45, hueShift: .04 });
    const cw = R.range(2.3, 3), curve = R.range(-7, 7);
    const X = y => cx + curve * Math.pow(1 - y / H, 2);
    const nodeGap = R.int(14, 18), ph = R.int(0, 12);
    for (let y = 10; y <= baseY; y++) {
      const xc = X(y), node = (y + ph) % nodeGap;
      for (let x = Math.floor(xc - cw - 1); x <= Math.ceil(xc + cw + 1); x++) {
        const sx = (x + .5 - xc) / cw; if (Math.abs(sx) > 1) continue;
        let t = .56 + (node === 0 ? -.4 : node === 1 ? .3 : node < 5 ? .1 : 0) + (old && hash2(x, y >> 1, seed + 2) < .06 ? -.35 : 0);
        s.px(x, y, culm[clamp(Math.round(t * 5), 0, 5)], { z: Math.sqrt(1 - sx * sx) * cw + 1, m: MAT.BAMBOO, b: 1 });
      }
    }
    // canopy: branch fans from every node in the upper half, each ending in sprays of long drooping leaves
    const leaves = ramp("#4d7e3a", 6, { lo: .5, hi: .5, hueShift: .06 });
    const leaf = (x0, y0, a, L, z, k) => PX.stroke(x0, y0, x0 + Math.cos(a) * L, y0 + Math.sin(a) * L * .6 + L * .32, 1.25, .2, (x, y, t, sx) => {
      const mid = Math.abs(sx) < .3 && t > .1 && t < .7; s.pz(x, y, leaves[clamp(Math.round((.5 + (mid ? .16 : 0) + (k % 3 - 1) * .12 - t * .08) * 5), 0, 5)], z + (1 - t), { m: MAT.LEAF, b: 4 });
    });
    for (let y = 14; y < H * .56; y++) {
      if ((y + ph) % nodeGap !== 3) continue;
      for (const dir of [-1, 1]) {
        if (R() < .08) continue;
        const bl = R.range(8, 16) * (1 - y / H * .3), bx = X(y) + dir * bl, by = y - R.range(3, 7);
        PX.stroke(X(y), y, bx, by, .6, .5, (x, yy) => s.pz(x, yy, culm[1], 3, { m: MAT.BAMBOO, b: 2 }));
        const nl = R.int(8, 13);
        for (let k = 0; k < nl; k++) leaf(bx + R.range(-3, 3), by + R.range(-2, 2), (dir > 0 ? 0 : Math.PI) + dir * R.range(-.5, .9), R.range(7, 12), 5 + R() * 3, k);
      }
    }
    for (let k = 0; k < 18; k++) leaf(X(12) + R.range(-4, 4), R.range(4, 20), R.range(-3, 0) - .3, R.range(7, 12), 7, k);
    PX.selout(s, { k: .74 }); PX.normals(s, .85);
    return s;
  },
  /* ---------------- undergrowth ---------------- */
  fern(seed) { // a fountain of arching fronds; paired leaflets shrink toward each tip
    const R = RNG(seed * 3 + 9), W = 44, H = 32, s = new SB(W, H), cx = W / 2, by = H - 2;
    const nf = R.int(7, 9);
    const order = [...Array(nf).keys()].sort((p, q) => Math.abs(q - (nf - 1) / 2) - Math.abs(p - (nf - 1) / 2)); // outer fronds first, upright ones last (nearest)
    for (const f of order) {
      const u = f / (nf - 1) * 2 - 1, a0 = -Math.PI / 2 + u * 1.25 + R.range(-.1, .1), L = R.range(15, 21) * (1 - Math.abs(u) * .15);
      let x = cx + u * 2, y = by, a = a0; const pts = [[x, y]]; const curl = u * .11 + R.range(-.02, .02);
      for (let i = 0; i < 16; i++) { a += curl + .02 * Math.sign(u || 1); x += Math.cos(a) * L / 16; y += Math.sin(a) * L / 16 + i * .05 * Math.abs(u); pts.push([x, y]); }
      const zf = 3 + (1 - Math.abs(u)) * 3;
      for (let i = 1; i < pts.length; i++) {
        const t = i / pts.length, [px1, py1] = pts[i], [px0, py0] = pts[i - 1]; const dx = px1 - px0, dy = py1 - py0, dl = hyp(dx, dy) || 1;
        const nx = -dy / dl, ny = dx / dl, ll = (1 - t) * 3.4 + .8;
        for (const sd of [-1, 1]) for (let q = .5; q <= ll; q += .5) {
          const xx = px1 + nx * q * sd + dx / dl * q * .6, yy = py1 + ny * q * sd + dy / dl * q * .6 + q * .2;
          const tone = .5 + (sd * nx > 0 ? .1 : -.06) + ((i >> 1) % 2 ? .06 : -.04) - q / ll * .12 + (1 - Math.abs(u)) * .05;
          s.pz(xx, yy, PAL.fern[clamp(Math.round(tone * 5), 0, 5)], zf + (1 - t) * 2 - q * .3, { m: MAT.LEAF, b: 2 + zf * .3 });
        }
        s.pz(px1, py1, PAL.fern[1], zf + (1 - t) * 2 + .3, { m: MAT.LEAF, b: 2 + zf * .3 });
      }
    }
    PX.selout(s, { k: .72 }); PX.normals(s, 1);
    return s;
  },
  sasa(seed) { // 熊笹 — broad blades with pale margins, held up and out
    const R = RNG(seed * 11 + 5), W = 36, H = 30, s = new SB(W, H), cx = W / 2, by = H - 1;
    const n = R.int(9, 12), stems = [];
    for (let k = 0; k < n; k++) stems.push({ u: R.range(-1, 1), k });
    stems.sort((p, q) => Math.abs(q.u) - Math.abs(p.u));
    for (const st of stems) {
      const u = st.u, k = st.k, a = -Math.PI / 2 + u * 1.35 + R.range(-.15, .15), L = R.range(11, 15), bx = cx + u * 5;
      const mx = bx + Math.cos(a) * 4, my = by - 6, x1 = mx + Math.cos(a) * L, y1 = my + Math.sin(a) * L * .9 + Math.abs(u) * 4;
      PX.stroke(bx, by, mx, my, .5, .5, (x, y) => s.pz(x, y, PAL.sasa[1], 1, { m: MAT.LEAF }));
      const z0 = 2 + (1 - Math.abs(u)) * 3;
      PX.stroke(mx, my, x1, y1, 2.6, .3, (x, y, t, sx) => {
        const edge = Math.abs(sx) > .74 && t > .12 && t < .9, mid = Math.abs(sx) < .18 && t < .8;
        s.pz(x, y, edge ? PAL.susuki[3] : PAL.sasa[clamp(Math.round((.5 - sx * .14 + (mid ? .16 : 0) + (k % 2 ? .06 : -.06)) * 5), 0, 5)], z0 + t * 2 + (1 - Math.abs(sx)), { m: MAT.LEAF, b: 2 + z0 * .3 });
      });
    }
    PX.selout(s, { k: .72 }); PX.normals(s, 1);
    return s;
  },
  kudzu(seed) { // 葛 — trifoliate leaves smothering a bank; silver undersides flash; grape-purple spikes
    const R = RNG(seed * 19 + 4), W = 64, H = 38, s = new SB(W, H), rr = PAL.kudzu, under = ramp("#a3b18c", 4, { lo: .35, hi: .3 });
    const leaflet = (x, y, a, L, z, flip) => PX.stroke(x, y, x + Math.cos(a) * L, y + Math.sin(a) * L * .78, L * .5, .5, (xx, yy, t, sx) => {
      const vein = Math.abs(sx) < .14 && t < .88; const col = flip ? under[clamp(Math.round((.62 - sx * .1 + (vein ? .2 : 0)) * 3), 0, 3)] : rr[clamp(Math.round((.46 + (vein ? .2 : 0) - sx * .12 - t * .05) * 5), 0, 5)];
      s.pz(xx, yy, col, z + (1 - Math.abs(sx)) * 1.4 + t * .5, { m: MAT.LEAF, b: 2 });
    });
    const L = [];
    for (let k = 0; k < 30; k++) L.push({ x: R.range(7, W - 7), y: R.range(9, H - 5), sz: R.range(5, 7.5), a: R.range(-.5, .5) - Math.PI / 2, flip: R() < .12 });
    L.sort((p, q) => p.y - q.y);
    for (const l of L) { const z = 2 + l.y * .25; leaflet(l.x, l.y, l.a, l.sz, z, l.flip); leaflet(l.x, l.y, l.a - 1.3, l.sz * .85, z - .3, l.flip); leaflet(l.x, l.y, l.a + 1.3, l.sz * .85, z - .3, l.flip); }
    for (let k = 0; k < 5; k++) { const x = R.range(8, W - 8) | 0, y = R.range(3, H - 14) | 0; for (let j = 0; j < 9; j++) { const c = PAL.kudzuFlower[clamp(Math.round((.4 + (j % 2 ? .2 : -.1) + j / 9 * .3) * 3), 0, 3)]; s.pz(x + (j % 2), y + j, c, 18 - j * .2, { m: MAT.PETAL, b: 5 }); if (j % 2 === 0 && j < 7) s.pz(x - 1, y + j, PAL.kudzuFlower[1], 17, { m: MAT.PETAL, b: 5 }); } }
    PX.selout(s, { k: .74 }); PX.normals(s, .9);
    return s;
  },
  susuki(seed) { // 芒 — arching blades and the first silver plumes, combed by the wind
    const R = RNG(seed * 23 + 8), W = 44, H = 54, s = new SB(W, H), cx = W / 2, by = H - 1;
    const blade = ramp("#7f8f4c", 5, { lo: .45, hi: .4 }), plume = ramp("#ddd2c2", 4, { lo: .3, hi: .2, hueShift: .02 });
    for (let k = 0; k < 22; k++) {
      const a = R.range(-2.8, -.35), Lb = R.range(14, 27), bend = R.range(.35, .95) * (Math.cos(a) > 0 ? 1 : -1);
      let x = cx + R.range(-3, 3), y = by;
      for (let i = 0; i < Lb; i++) { const t = i / Lb, ang = a + bend * t * t; x += Math.cos(ang); y += Math.sin(ang); s.pz(x, y, blade[clamp(Math.round((.42 + t * .3 + (k % 3 - 1) * .1) * 4), 0, 4)], 2 + t * 4, { m: MAT.BLADE, b: 2 }); }
    }
    const np = R.int(3, 5);
    for (let k = 0; k < np; k++) {
      let x = cx + R.range(-4, 4), y = by - 6; const a = R.range(-2.05, -1.1), Lp = R.range(34, 46), lean = R.range(.5, .8) * (Math.cos(a) >= 0 ? 1 : -1);
      for (let i = 0; i < Lp; i++) {
        const t = i / Lp, ang = a + lean * t * t * 1.2; x += Math.cos(ang); y += Math.sin(ang);
        s.pz(x, y, t < .55 ? blade[2] : plume[2], 6 + t * 2, { m: MAT.BLADE, b: 3 });
        // fine hairs hanging off the down-wind side of the rachis
        if (t > .55 && i % 2 === 0) { const hl = 2 + Math.round((1 - Math.abs(t - .78) * 3.5) * 3); const ha = ang + lean * 1.9;
          for (let q = 1; q <= hl; q++) s.pz(x + Math.cos(ha) * q, y + Math.sin(ha) * q + q * .55, plume[clamp(3 - Math.floor(q / hl * 3), 0, 3)], 7 + t * 2 - q * .2, { m: MAT.BLADE, b: 3 }); }
      }
    }
    PX.selout(s, { k: .84 }); PX.normals(s, .8);
    return s;
  },
  lily(seed) { // 山百合 — heavy white trumpets with a golden band, crimson freckles
    const R = RNG(seed * 29 + 1), W = 24, H = 36, s = new SB(W, H), cx = W / 2 + R.range(-1, 1), by = H - 1;
    const top = R.int(10, 13);
    PX.stroke(cx, by, cx + R.range(-2, 2), top, .6, .6, (x, y) => s.pz(x, y, PAL.fern[2], 2, { m: MAT.LEAF }));
    for (let k = 0; k < 7; k++) { const y = by - 3 - k * 3, d = k % 2 ? 1 : -1; PX.stroke(cx, y, cx + d * 6, y - 3, 1.2, .2, (x, yy, t, sx) => s.pz(x, yy, PAL.fern[clamp(3 - (sx > 0 ? 1 : 0), 0, 5)], 3, { m: MAT.LEAF, b: 1 })); }
    const nf = R.int(1, 3);
    for (let f = 0; f < nf; f++) {
      const fx = cx + (f - (nf - 1) / 2) * 7, fy = top + (f % 2) * 3;
      for (let p = 0; p < 6; p++) { const a = p / 6 * TAU + .3; PX.stroke(fx, fy, fx + Math.cos(a) * 5.5, fy + Math.sin(a) * 4.2 + 1, 1.7, .5, (x, y, t, sx) => {
        const stripe = Math.abs(sx) < .3 && t < .75; const dot = !stripe && hash2(x, y, f * 7 + p) < .16 && t > .25 && t < .8;
        s.pz(x, y, stripe ? [234, 192, 80] : dot ? [172, 46, 40] : PAL.lily[clamp(Math.round((.75 - t * .3 + (sx > 0 ? .1 : -.05)) * 3), 0, 3)], 8 + (1 - t) * 3, { m: MAT.PETAL, b: 4 }); }); }
      s.pz(fx, fy, [124, 82, 40], 12, { m: MAT.PETAL, b: 4 }); s.pz(fx + 1, fy - 1, [196, 120, 50], 12, { m: MAT.PETAL, b: 4 });
    }
    PX.selout(s, { k: .82 }); PX.normals(s, .9);
    return s;
  },
  hydrangea(seed) { // 紫陽花, past its best in August — blue going to dusty violet
    const R = RNG(seed * 31 + 2), W = 36, H = 30, s = new SB(W, H);
    for (let k = 0; k < 8; k++) FLORA.clump(s, R.range(7, W - 7), R.range(11, H - 6), R.range(5, 7.5), R.range(4, 5.5), 2 + R() * 3, PAL.sasa, { seed: seed + k, base: 2.6, cell: 3.2, zk: .6 });
    const fl = [ramp("#6f86c4", 5, { lo: .4, hi: .35 }), ramp("#9a7fbf", 5, { lo: .4, hi: .35 }), ramp("#8d9fc9", 5, { lo: .4, hi: .3 })];
    for (let k = 0; k < 5; k++) FLORA.clump(s, R.range(8, W - 8), R.range(8, H - 10), R.range(4, 5.5), R.range(3.6, 4.8), 9 + R() * 2, R.pick(fl), { seed: seed * 5 + k, base: 2.4, cell: 1.9, zk: .9, mat: MAT.PETAL, bulge: 3 });
    PX.selout(s, { k: .74 }); PX.normals(s, 1);
    return s;
  },
  dayflower(seed) { // 露草 — tiny blue flags in the wet grass
    const R = RNG(seed * 37 + 3), W = 16, H = 12, s = new SB(W, H);
    for (let k = 0; k < 5; k++) { const x = R.range(3, W - 3); PX.stroke(x, H - 1, x + R.range(-3, 3), R.range(3, H - 3), .5, .5, (xx, yy) => s.pz(xx, yy, PAL.fern[2 + (k & 1)], 1, { m: MAT.LEAF })); }
    for (let k = 0; k < 3; k++) { const x = R.range(3, W - 4) | 0, y = R.range(2, H - 6) | 0; s.pz(x, y, [58, 100, 196], 4, { m: MAT.PETAL, b: 2 }); s.pz(x + 1, y, [86, 132, 222], 4, { m: MAT.PETAL, b: 2 }); s.pz(x, y + 1, [242, 212, 90], 4, { m: MAT.PETAL, b: 2 }); }
    PX.normals(s, 1); return s;
  },
  mushroom(seed) {
    const R = RNG(seed * 41 + 6), W = 14, H = 11, s = new SB(W, H);
    const cap = R() < .5 ? ramp("#b07a4c", 4) : ramp("#d9cfb4", 4);
    for (let k = 0; k < 3; k++) { const x = 3 + k * 3.5 + R.range(-1, 1), h = R.range(3, 6), r = R.range(1.8, 2.8);
      PX.stroke(x, H - 1, x, H - 1 - h, .7, .6, (xx, yy) => s.pz(xx, yy, PAL.paper[2], 2, { m: MAT.PAPER }));
      PX.ell(x, H - 1 - h, r, r * .6, (xx, yy, u, v, d) => s.pz(xx, yy, cap[clamp(Math.round((.55 - v * .3) * 3), 0, 3)], 4 + (1 - d) * 2, { m: MAT.CLOTH, b: 2 })); }
    PX.normals(s, 1); return s;
  },
  // instanced ground tufts: grey encodes the shade band (dark/mid/light), red marks a flower pixel
  grassTufts() {
    const N = 12, W = 11, H = 13, cv = document.createElement("canvas"); cv.width = W; cv.height = H * N; const g = cv.getContext("2d");
    for (let v = 0; v < N; v++) {
      const R = RNG(v * 97 + 5), nb = R.int(5, 9);
      for (let b = 0; b < nb; b++) {
        let x = W / 2 + R.range(-3.5, 3.5), y = H - 1; const a = R.range(-2.2, -.95), L = R.range(5, 11), bend = R.range(-.5, .5);
        for (let i = 0; i < L; i++) { const t = i / L; x += Math.cos(a + bend * t); y += Math.sin(a + bend * t);
          const val = t < .3 ? 70 : t < .7 ? 150 : 225; g.fillStyle = `rgb(${val},${val},${val})`; g.fillRect(Math.round(x), Math.round(y) + v * H, 1, 1); }
      }
      if (v >= 9) { const fx = W / 2 + R.range(-2, 2) | 0, fy = R.int(1, 3); g.fillStyle = "rgb(255,0,0)"; g.fillRect(fx, fy + v * H, 2, 1); g.fillRect(fx, fy + 1 + v * H, 1, 1); }
    }
    return { cv, n: N, w: W, h: H };
  },
};
