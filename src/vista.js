/* =====================================================================
   VISTA — the side-view shots: the title, the treetop on the night of
   the Far (the plain, its lights, a procession of lanterns walking up
   into the sky, the pale wave), and the meadow lookout afterwards.
   Painted per frame into a low-res canvas, then graded and bloomed by
   the same composite as the world.
   ===================================================================== */
"use strict";
const VISTA = {
  cv: null, g: null, tex: null, on: false, mode: "title", t: 0, wave: -1, city: null, stars: null, hills: null,
  init() {
    this.cv = document.createElement("canvas"); this.g = this.cv.getContext("2d");
    const R = RNG(42);
    this.stars = []; for (let i = 0; i < 260; i++) this.stars.push([R(), Math.pow(R(), 1.6) * .62, R(), R() < .1 ? 2 : 1]);
    this.city = []; for (let i = 0; i < 2600; i++) { const cx = R.gauss() * .22 + .52 + (R() < .3 ? R.range(-.3, .3) : 0), d = Math.pow(R(), .6); this.city.push([cx, d, R(), R() < .08 ? 2 : 1, R()]); }
    this.lan = []; for (let i = 0; i < 90; i++) this.lan.push([i / 90, R()]);
    const ridge = (seed, n, amp, base) => { const out = []; for (let i = 0; i <= n; i++) out.push(base - (fbm(i / n * 3.2, seed, 4, seed) - .5) * amp - Math.sin(i / n * Math.PI) * amp * .3); return out; };
    this.hills = [ridge(1, 240, .16, .52), ridge(2, 240, .12, .6), ridge(3, 240, .2, .74)];
  },
  size() { const W = RD.W, H = RD.H; if (this.cv.width !== W || this.cv.height !== H) { this.cv.width = W; this.cv.height = H; if (this.tex) GL.gl.deleteTexture(this.tex); this.tex = GL.canvasTex(this.cv); } return [W, H]; },
  px(x, y, c) { this.g.fillStyle = c; this.g.fillRect(x | 0, y | 0, 1, 1); },
  // night: 0 = day, 1 = night; far: progress of the pale wave 0..1 (−1 none)
  draw(dt) {
    this.t += dt; const [W, H] = this.size(), g = this.g, t = this.t, night = this.night ?? 1, far = this.wave;
    const sky = night > .5 ? [[11, 15, 38], [27, 33, 70], [58, 44, 78], [104, 62, 70]] : [[96, 140, 196], [148, 184, 214], [206, 214, 214], [226, 214, 196]];
    // sky
    for (let y = 0; y < H; y++) { const k = y / (H * .62); const i = clamp(Math.floor(k * 3), 0, 2), f = clamp(k * 3 - i, 0, 1); const a = sky[i], b = sky[i + 1]; const d = (((y * 7) % 4) / 4 - .5) * .06;
      g.fillStyle = rgbHex(mixRGB(a, b, clamp(f + d, 0, 1))); g.fillRect(0, y, W, 1); }
    // stars & the Bon moon
    if (night > .5) {
      for (const [sx, sy, ph, s] of this.stars) { const tw = .55 + .45 * Math.sin(t * (1 + ph * 3) + ph * 40); if (tw < .3) continue; g.fillStyle = `rgba(230,236,255,${tw})`; g.fillRect(sx * W | 0, sy * H | 0, s, s); }
      const mx = W * .22, my = H * .2, mr = Math.max(7, H * .045);
      for (let r = mr * 3.2; r > mr; r -= 1) { g.fillStyle = `rgba(200,210,255,${.018})`; g.beginPath(); g.arc(mx, my, r, 0, TAU); g.fill(); }
      for (let y = -mr; y <= mr; y++) for (let x = -mr; x <= mr; x++) { const d = hyp(x, y) / mr; if (d > 1) continue; const sh = hash2(x + 9 | 0, y + 9 | 0, 3) < .12 || (fbm(x * .3 + 5, y * .3, 2, 4) > .62); this.px(mx + x, my + y, sh ? "#d4d6e2" : d > .9 ? "#e8e6dc" : "#f4f1e4"); }
    } else {
      // day: a few flat clouds
      for (let k = 0; k < 6; k++) { const cx = ((k * .23 + t * .004) % 1.2 - .1) * W, cy = H * (.12 + (k % 3) * .07), w = W * (.12 + (k % 2) * .08); for (let y = 0; y < 6; y++) { g.fillStyle = y < 2 ? "#f2f2ee" : y < 4 ? "#e4e6e6" : "#cfd6dc"; g.fillRect(cx - w / 2 + y * 2, cy + y, w - y * 4, 1); } }
    }
    // the far range
    const farC = night > .5 ? [44, 50, 86] : [150, 168, 196];
    this.ridge(this.hills[0], farC, H * .02);
    // the plain and the city
    const py = H * .62;
    for (let y = Math.floor(py); y < H; y++) { const k = (y - py) / (H - py); g.fillStyle = rgbHex(night > .5 ? mixRGB([24, 22, 40], [12, 12, 22], k) : mixRGB([170, 180, 176], [120, 140, 120], k)); g.fillRect(0, y, W, 1); }
    // the river catching the moon
    for (let x = 0; x < W; x++) { const y = py + H * .05 + Math.sin(x / W * 7 + 1) * H * .015 + x / W * H * .06; this.px(x, y, night > .5 ? (x % 3 === 0 ? "#8a94c8" : "#4a5288") : "#d8e2e6"); }
    for (const [cx, d, ph, s, warm] of this.city) {
      const x = cx * W, y = py + 2 + d * (H - py) * .7; if (y > H * .9) continue;
      const wx = (x / W - .5), dist = hyp(wx * 1.2, (y - py) / (H - py) * .7);
      const gone = far >= 0 && dist < far * 1.3;
      if (night > .5) { const tw = .7 + .3 * Math.sin(t * 2 + ph * 30); g.fillStyle = gone ? `rgba(170,190,240,${.35 * tw})` : warm < .7 ? `rgba(255,200,120,${tw})` : `rgba(255,236,200,${tw})`; g.fillRect(x | 0, y | 0, s, 1); }
      else if (ph < .45) { g.fillStyle = gone || far >= 0 ? "#a8b6d4" : (warm < .5 ? "#7a6a5a" : "#5a5a62"); g.fillRect(x | 0, (y - 2) | 0, s + 1, 2 + (ph * 4 | 0)); }
    }
    // the procession: lanterns walking up out of the plain into the sky
    if (this.procession) {
      for (const [p0, ph] of this.lan) {
        const p = (p0 + t * .018) % 1; const x = W * (.6 + Math.sin(p * 3 + ph) * .02 - p * .18), y = py - p * H * .58 - Math.sin(p * Math.PI) * H * .05;
        const a = clamp(p * 6, 0, 1) * clamp((1 - p) * 3, 0, 1) * (.75 + .25 * Math.sin(t * 6 + ph * 20));
        g.fillStyle = `rgba(255,${120 + ph * 60 | 0},70,${a})`; g.fillRect(x | 0, y | 0, 1, 2); if (ph < .3) { g.fillStyle = `rgba(255,210,150,${a * .6})`; g.fillRect(x | 0, (y - 1) | 0, 1, 1); }
      }
    }
    // the pale wave: a band of distance-blue racing over the plain toward us
    if (far >= 0) {
      const fy = py + (H - py) * clamp(far, 0, 1);
      for (let y = Math.floor(py); y < Math.min(H, fy); y++) for (let x = 0; x < W; x += 1) { const k = (fy - y) / 30; if (hash2(x, y, (t * 8) | 0) < .14 + clamp(k, 0, .5)) { g.fillStyle = `rgba(190,206,240,${.18 + clamp(k * .1, 0, .3)})`; g.fillRect(x, y, 1, 1); } }
      for (let x = 0; x < W; x++) if (hash2(x, (t * 10) | 0, 4) < .5) this.px(x, fy + Math.sin(x * .2 + t * 6) * 1.5, "rgba(230,238,255,.8)");
    }
    // near hills and foreground
    this.ridge(this.hills[1], night > .5 ? [20, 22, 38] : [92, 112, 96], H * .06);
    if (this.mode === "lookout") this.susuki(W, H, night); else this.branches(W, H, night);
  },
  ridge(pts, c, off) { const g = this.g, W = this.cv.width, H = this.cv.height; g.fillStyle = rgbHex(c); for (let x = 0; x < W; x++) { const y = pts[Math.floor(x / W * (pts.length - 1))] * H + off; g.fillRect(x, y | 0, 1, H - y); } },
  branches(W, H, night) { // the crown of the great camphor framing the view; her silhouette on a limb
    const g = this.g, R = RNG(8), dk = night > .5 ? "#07080e" : "#22301e", mid = night > .5 ? "#0e1120" : "#3a4a30";
    for (let k = 0; k < 70; k++) { const top = k < 40; const x = top ? R() * W : (k % 2 ? R() * W * .2 : W - R() * W * .2), y = top ? R() * H * .16 : H * .3 + R() * H * .7, r = 6 + R() * 14;
      for (let yy = -r; yy <= r; yy++) for (let xx = -r; xx <= r; xx++) { const d = hyp(xx, yy) / r - (hash2(x + xx | 0, y + yy | 0, 5) - .5) * .25; if (d > 1) continue; const sw = Math.sin(this.t * 1.1 + x * .02) * (top ? 1 : .5); this.px(x + xx + sw, y + yy, d > .8 || yy > r * .3 ? dk : mid); } }
    // the limb she stands on
    g.fillStyle = dk; for (let x = W * .48; x < W; x++) { const y = H * .86 - (x - W * .48) * .12; g.fillRect(x | 0, y | 0, 1, 5 + (x - W * .48) * .04); }
    this.tsuzuraBack(W * .72 | 0, H * .82 - (W * .72 - W * .48) * .12 | 0, dk);
  },
  susuki(W, H, night) { const g = this.g; for (let k = 0; k < 160; k++) { const x = hash1(k) * W, h = H * (.12 + hash1(k + 9) * .18), sw = Math.sin(this.t * 1.4 + k) * 2; for (let i = 0; i < h; i++) { const t = i / h; this.px(x + sw * t * t + t * 4 * (k % 2 ? 1 : -1), H - i, night > .5 ? "#141626" : (t > .75 ? "#d8d0c0" : "#5a6a46")); } }
    g.fillStyle = night > .5 ? "#0d0e18" : "#4a4e46"; g.beginPath(); g.ellipse(W * .64, H * 1.02, W * .2, H * .16, 0, 0, TAU); g.fill();
    this.tsuzuraBack(W * .64 | 0, H * .88 | 0, night > .5 ? "#0b0c16" : "#2a2a30"); },
  tsuzuraBack(x, y, c) { // a small silhouette from behind: round ears, the frame's poles, the tail
    const pts = ["...k.......k...", "..kkk.kkk.kkk..", "...kkkkkkkkk...", "...kkkkkkkkk...", "..kkkkkkkkkkk..", "..kkkkkkkkkkk..", "...kkkkkkkkk...", "....kkkkkkk....", "...kkkkkkkkk...", "...kkkkkkkkkk..", "...kkkkkkkkkkkk", "....kkkkkkkkkkk", "....kkkk.kkk.kk", "....kk....kk...", "....kk....kk..."];
    for (let j = 0; j < pts.length; j++) for (let i = 0; i < pts[j].length; i++) if (pts[j][i] === "k") this.px(x + i - 7, y + j - pts.length, c);
    for (let j = 0; j < 22; j++) { this.px(x - 5, y - 15 - j * .5 - 4, c); this.px(x + 5, y - 15 - j * .5 - 4, c); }
  },
  /* ---------- shots ---------- */
  async prologueShot() {
    this.on = true; this.mode = "treetop"; this.night = 1; this.wave = -1; this.procession = false; this.t = 0;
    await UI.fade(0, 1.8);
    await CINE.wait(1.6);
    this.procession = true; AU.festival(.7, { near: .3 });
    await CINE.wait(3.2);
    await CINE.say(T("surprised", "……灯，在往天上走。"));
    await CINE.wait(1.2);
    AU.music("tension", { fade: 3 });
    const t0 = GAME.t; this.wave = 0;
    await CINE.until(() => { this.wave = clamp((GAME.t - t0) / 7, 0, 1) * .9; AU.festival(.7 + this.wave * .3, { near: .3 + this.wave * .6 }); return this.wave >= .9; });
    await CINE.say(T("shout", "喂——！"), T("shout", "那边的人——"));
    await UI.fade(1, .5, "#dfe6f6");
    this.on = false;
  },
  async lookoutShot() {
    if (GAME.cine) return; GAME.cine = true;
    await UI.fade(1, .8); this.on = true; this.mode = "lookout"; this.night = GAME.tod > 19.3 || GAME.tod < 5 ? 1 : 0; this.wave = 1; this.procession = this.night > .5; this.t = 0;
    await UI.fade(0, 1.2); AU.stinger("discover");
    await CINE.wait(2);
    if (this.night > .5) await CINE.say(T("soft", "……那些灯。"), T("soft", "一盏也没有少。"), T("thinking", "全都变成了远山的颜色。"));
    else await CINE.say(T("surprised", "……城还在。"), T("thinking", "屋顶、烟囱、河上的桥，一样都没少。"), T("soft", "就是全都变成了远山的颜色。"));
    await UI.fade(1, .8); this.on = false; await UI.fade(0, .8);
    GAME.cine = false;
  },
};
