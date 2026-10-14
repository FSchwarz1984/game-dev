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
    this.city = [];
    const districts = [[.5, .25, .09, 420], [.66, .4, .06, 220], [.34, .5, .07, 200], [.2, .2, .04, 90], [.8, .15, .05, 110], [.58, .7, .05, 120]];
    for (const [cx0, d0, sp, n] of districts) for (let i = 0; i < n; i++) this.city.push([cx0 + R.gauss() * sp, clamp(d0 + R.gauss() * sp * 1.6, 0, 1), R(), R() < .06 ? 2 : 1, R()]);
    for (let r = 0; r < 5; r++) { const x0 = R(), y0 = R() * .8, a = R.range(-.5, .5); for (let i = 0; i < 40; i++) this.city.push([x0 + i * .012 * Math.cos(a), clamp(y0 + i * .012 * Math.sin(a) * 2, 0, 1), R(), 1, .9]); }
    this.lan = []; for (let i = 0; i < 90; i++) this.lan.push([i / 90, R()]);
    const ridge = (seed, n, amp, base) => { const out = []; for (let i = 0; i <= n; i++) out.push(base - (fbm(i / n * 3.2, seed, 4, seed) - .5) * amp - Math.sin(i / n * Math.PI) * amp * .3); return out; };
    this.hills = [ridge(1, 240, .14, .4), ridge(2, 240, .1, .74), ridge(3, 240, .2, .8)];
  },
  size() { const W = RD.W, H = RD.H; if (this.cv.width !== W || this.cv.height !== H) { this.cv.width = W; this.cv.height = H; if (this.tex) GL.gl.deleteTexture(this.tex); this.tex = GL.canvasTex(this.cv); } return [W, H]; },
  px(x, y, c) { this.g.fillStyle = c; this.g.fillRect(x | 0, y | 0, 1, 1); },
  // paint a static layer once into its own canvas
  layer(key, W, H, fn) {
    const k = key + W + "x" + H; this.cache = this.cache || {}; if (this.cache[k]) return this.cache[k];
    const cv = document.createElement("canvas"); cv.width = W; cv.height = H; const prev = this.g; this.g = cv.getContext("2d"); fn(this.g, W, H); this.g = prev; this.cache[k] = cv; return cv;
  },
  // the wave is a ring on the ground plane centred under the procession; a screen row y below
  // the horizon sees ground at depth Z = f / (y − horizon), so the ring creeps, widens, then rushes in
  waveGeo(W, H) { const py = H * .47, f = H - py, Z0 = 24; return { py, f, Z0, X0: W * .1 * Z0 / f, r: this.wave >= 1 ? 1e9 : 22.4 * clamp(this.wave / .9, 0, 1) }; },
  isFar(x, y, W, G) { if (this.wave < 0) return false; if (this.wave >= 1) return true; const Z = G.f / Math.max(.5, y - G.py), X = (x - W / 2) * Z / G.f; return hyp(X - G.X0, Z - G.Z0) < G.r; },
  // night: 0 = day, 1 = night; wave: progress of the pale front 0..1 (−1 none)
  draw(dt) {
    this.t += dt; const [W, H] = this.size(), g = this.g, t = this.t, night = (this.night ?? 1) > .5, far = this.wave, py = H * .47;
    g.drawImage(this.layer("sky" + night, W, H, (c) => this.paintSky(c, W, H, night)), 0, 0);
    if (night) { for (const [sx, sy, ph, sz] of this.stars) { const tw = .55 + .45 * Math.sin(t * (1 + ph * 3) + ph * 40); if (tw < .35) continue; g.globalAlpha = tw; g.fillStyle = "#e6ecff"; g.fillRect(sx * W | 0, sy * H | 0, sz, sz); } g.globalAlpha = 1; }
    else { for (let k = 0; k < 5; k++) { const cx = ((k * .27 + t * .004) % 1.2 - .1) * W, cy = H * (.08 + (k % 3) * .06), w = W * (.1 + (k % 2) * .07); g.globalAlpha = .45; g.fillStyle = "#f4f6f8"; g.fillRect(cx - w / 2 | 0, cy | 0, w | 0, 1); g.globalAlpha = .25; g.fillRect(cx - w / 3 | 0, cy + 1 | 0, w * .7 | 0, 1); g.fillRect(cx - w * .2 | 0, cy - 1 | 0, w * .35 | 0, 1); } g.globalAlpha = 1; }  // high cirrus drifting
    g.drawImage(this.layer("plain" + night, W, H, (c) => this.paintPlain(c, W, H, night)), 0, 0);
    // the city: lights by night, roofs by day; whatever the wave has passed keeps shining — distance-blue, and still
    const G = this.waveGeo(W, H), buckets = night ? ["#ffc878", "#ffe8c8", "#a9bdf0"] : ["#6a5a4c", "#4e4e58", "#7f90b8"];
    for (let bi = 0; bi < 3; bi++) {
      g.fillStyle = buckets[bi];
      for (let i = bi === 2 ? 0 : bi; i < this.city.length; i += bi === 2 ? 1 : 2) {
        const [cx, d, ph, sz] = this.city[i]; const x = cx * W, y = py + 2 + d * d * (H - py) * .55; if (y > H * .8) continue;
        const gone = this.isFar(x, y, W, G); if ((bi === 2) !== gone) continue;
        if (night) { if (!gone && Math.sin(t * 2 + ph * 30) < -.6) continue; g.globalAlpha = gone ? .8 : 1; g.fillRect(x | 0, y | 0, sz, 1); }
        else if (ph < .45) g.fillRect(x | 0, (y - 2) | 0, sz + 1, 2 + (ph * 4 | 0));
      }
    }
    g.globalAlpha = 1;
    // the procession: lanterns walking up out of the plain into the sky
    if (this.procession) for (const [p0, ph] of this.lan) {
      const p = (p0 + t * .018) % 1; const x = W * (.6 + Math.sin(p * 3 + ph) * .02 - p * .2), y = py + 6 - p * H * .46 - Math.sin(p * Math.PI) * H * .05;
      g.globalAlpha = clamp(p * 6, 0, 1) * clamp((1 - p) * 3, 0, 1) * (.75 + .25 * Math.sin(t * 6 + ph * 20));
      g.fillStyle = ph < .5 ? "#ff8a46" : "#ffb070"; g.fillRect(x | 0, y | 0, 1, 2); if (ph < .3) { g.fillStyle = "#ffe0b0"; g.fillRect(x | 0, (y - 1) | 0, 1, 1); }
    }
    g.globalAlpha = 1;
    // the pale wave: a ring of distance spreading over the plain from the foot of the procession —
    // a bright front, a glow just behind it, and behind that everything merely, quietly, far
    if (far >= 0) {
      const tint = night ? "#8094d0" : "#c2d0ee", glow = night ? "#c4d2ff" : "#eef2ff", edge = "#f2f6ff";
      if (far >= 1) { g.globalAlpha = night ? .2 : .24; g.fillStyle = tint; g.fillRect(0, Math.ceil(py), W, H); }
      else if (G.r > .05) {
        let pl = -1, pr = -1; const pulse = .78 + .18 * Math.sin(t * 9);
        for (let y = Math.ceil(py) + 1; y < H; y++) {
          const Z = G.f / (y - py), dz = Z - G.Z0;
          if (Math.abs(dz) >= G.r) {
            if (pl >= 0) { // the near edge: close the front, and let pale motes lift off it
              g.globalAlpha = pulse; g.fillStyle = edge; g.fillRect(pl | 0, y - 1, Math.max(1, (pr - pl) | 0), 1);
              g.fillStyle = glow; for (let x = pl | 0; x < pr; x += 2) { const h = hash2(x, t * 14 | 0, 3); if (h < .22) { g.globalAlpha = .7 - h * 2; g.fillRect(x, y - 2 - (h * 18 | 0), 1, 1); } }
              pl = -1;
            }
            if (dz < 0) break; continue;
          }
          const half = Math.sqrt(G.r * G.r - dz * dz), s = G.f / Z, xl = W / 2 + (G.X0 - half) * s, xr = W / 2 + (G.X0 + half) * s;
          g.fillStyle = tint; g.globalAlpha = .16 + ((y + (t * 10 | 0)) % 7 === 0 ? .06 : 0); g.fillRect(xl | 0, y, ((xr - xl) | 0) + 1, 1);
          g.fillStyle = glow; g.globalAlpha = .26; const ri = G.r - 1.4;
          if (ri > 0 && Math.abs(dz) < ri) { const hi = Math.sqrt(ri * ri - dz * dz), il = W / 2 + (G.X0 - hi) * s, ir = W / 2 + (G.X0 + hi) * s; g.fillRect(xl | 0, y, Math.max(1, (il - xl) | 0), 1); g.fillRect(ir | 0, y, Math.max(1, (xr - ir) | 0), 1); }
          else g.fillRect(xl | 0, y, ((xr - xl) | 0) + 1, 1);
          g.fillStyle = edge; g.globalAlpha = pulse;
          if (pl < 0) g.fillRect(xl | 0, y, ((xr - xl) | 0) + 1, 1);
          else { g.fillRect(Math.min(pl, xl) | 0, y, Math.max(1, Math.abs(xl - pl) | 0), 1); g.fillRect(Math.min(pr, xr) | 0, y, Math.max(1, Math.abs(xr - pr) | 0), 1); }
          pl = xl; pr = xr;
        }
      }
      g.globalAlpha = 1;
    }
    g.drawImage(this.layer("near" + night, W, H, (c) => this.treeline(c, this.hills[1], night ? [16, 18, 32] : [84, 104, 88], night ? "#2c3456" : "#a8bc9c", H * .06, W, H)), 0, 0);
    const sway = Math.round(Math.sin(t * 1.1) * 1);
    if (this.mode === "lookout") g.drawImage(this.layer("susuki" + night, W, H, (c) => this.susuki(W, H, night ? 1 : 0)), sway, 0);
    else g.drawImage(this.layer("branch" + night, W, H, (c) => this.branches(W, H, night ? 1 : 0)), sway, 0);
  },
  paintSky(g, W, H, night) {
    const sky = night ? [[11, 15, 38], [27, 33, 70], [58, 44, 78], [104, 62, 70]] : [[96, 140, 196], [148, 184, 214], [206, 214, 214], [226, 214, 196]];
    for (let y = 0; y < H; y++) { const k = y / (H * .62); const i = clamp(Math.floor(k * 3), 0, 2), f = clamp(k * 3 - i, 0, 1); const a = sky[i], b = sky[i + 1]; const d = (((y * 7) % 4) / 4 - .5) * .06; g.fillStyle = rgbHex(mixRGB(a, b, clamp(f + d, 0, 1))); g.fillRect(0, y, W, 1); }
    if (night) { // the Bon moon is full
      const mx = W * .22, my = H * .2, mr = Math.max(7, H * .045);
      for (let r = mr * 3.2; r > mr; r -= 1) { g.fillStyle = "rgba(200,210,255,.018)"; g.beginPath(); g.arc(mx, my, r, 0, TAU); g.fill(); }
      for (let y = -mr; y <= mr; y++) for (let x = -mr; x <= mr; x++) { const d = hyp(x, y) / mr; if (d > 1) continue; const sh = hash2(x + 9 | 0, y + 9 | 0, 3) < .12 || (fbm(x * .3 + 5, y * .3, 2, 4) > .62); g.fillStyle = sh ? "#d4d6e2" : d > .9 ? "#e8e6dc" : "#f4f1e4"; g.fillRect(mx + x | 0, my + y | 0, 1, 1); }
    }
    if (!night) { const R = RNG(5); this.cumulus(g, W * .74, H * .42, W * .14, H * .34, R); this.cumulus(g, W * .3, H * .43, W * .08, H * .17, R); this.cumulus(g, W * .05, H * .43, W * .05, H * .1, R); }
    this.ridgeTo(g, this.hills[0], night ? [44, 50, 86] : [150, 168, 196], H * .02, W, H);
  },
  cumulus(g, cx, by, w, h, R) { // a summer thunderhead behind the mountains: stacked billows, sunlit upper-left, blue shadows, a flat dark base
    const B = []; for (let r = 0; r < 8; r++) { const t = r / 7, rw = w * (1 - t * .6) * (.8 + R() * .3), yy = by - t * h * .82, n = 3 + (rw / 9 | 0); for (let i = 0; i < n; i++) B.push([cx + (R() - .5) * rw * 1.4 + t * w * .15, yy - R() * h * .08, rw / n * (1 + R() * .7) + 3]); }
    const pal = [[168, 180, 208], [196, 206, 226], [228, 232, 240], [250, 250, 246]];
    for (let y = (by - h * 1.1) | 0; y <= by; y++) for (let x = (cx - w * 1.2) | 0; x < cx + w * 1.3; x++) {
      let best = -1, nx = 0, ny = 0; for (const [bx, b2, br] of B) { const dx = x - bx, dy = y - b2, d = 1 - hyp(dx, dy) / br; if (d > best) { best = d; nx = dx / br; ny = dy / br; } }
      if (best < 0) continue;
      const v = clamp(-(nx + ny) * .62 + .48, 0, 1) * (.45 + .55 * clamp((by - y) / (h * .22), 0, 1)) + (best < .12 ? .1 : 0) + ((((x + y) & 1) ? .03 : -.03));
      g.fillStyle = rgbHex(pal[clamp(Math.floor(v * 4), 0, 3)]); g.fillRect(x, y, 1, 1);
    }
  },
  paintPlain(g, W, H, night) { // the plain in true perspective: Obon-season rice, levees, irrigation channels and ponds holding the sky, a river under the moon
    const py = H * .47, f = H - py, y0 = Math.floor(py), id = g.createImageData(W, H - y0), D = id.data, N = night;
    const riverX = Z => -3 - 3.5 * Math.sin(Z * .35), mx = W * .22;
    for (let y = y0; y < H; y++) {
      const k = (y - py) / (H - py), Z = f / Math.max(.4, y - py), zA = f / Math.max(.4, y + 1 - py);
      const base = N ? mixRGB([24, 22, 40], [12, 12, 22], k) : mixRGB([150, 168, 150], [92, 120, 70], k);
      const sky = N ? mixRGB([50, 48, 88], [32, 36, 70], k) : mixRGB([214, 222, 228], [176, 200, 224], k);
      const rice = N ? mixRGB([30, 32, 54], [20, 24, 38], k) : mixRGB([128, 160, 110], [86, 132, 56], k);
      const fadeR = clamp((16 - Z) / 9, 0, 1), fadeC = clamp((34 - Z) / 16, 0, 1), haze = N ? 0 : (1 - k) * (1 - k) * .55;
      const levRow = Math.floor(Z / 1.4) !== Math.floor(zA / 1.4), rx = W / 2 + riverX(Z) * f / Z, rw = Math.max(.6, .45 * f / Z);
      for (let x = 0; x < W; x++) {
        const X = (x - W / 2) * Z / f, X1 = (x + 1 - W / 2) * Z / f, cx = Math.floor(X / 2), cz = Math.floor(Z / 1.4), h = hash2(cx, cz, 17);
        let c = mixRGB(base, rice, fadeC * (.6 + h * .4));                                                     // rice, each field its own green
        if (!N && fadeC > 0 && hash2(x, y >> 1, 4) < .12) c = mixRGB(c, [150, 186, 96], .35 * fadeC);
        if (h < .06) c = mixRGB(base, sky, .7 * fadeC);                                                        // a pond
        else if (h > .93) c = mixRGB(base, N ? [8, 8, 16] : [52, 78, 50], fadeC);                              // a copse, a farmyard
        const levCol = Math.floor(X / 2) !== Math.floor(X1 / 2);
        if (levCol || levRow) {                                                                                // a levee; on some, a channel of water
          const wet = levCol ? hash2(Math.floor(X1 / 2), 0, 23) < .45 : hash2(0, Math.floor(Z / 1.4), 29) < .35;
          c = mixRGB(c, wet ? mixRGB(sky, base, .25) : mixRGB(base, [0, 0, 0], .2), .85 * fadeR);
        }
        const dr = Math.abs(x - rx);
        if (dr < rw) c = dr > rw - 1 && rw > 1.5 ? mixRGB(base, sky, .4) : mixRGB(sky, N ? [70, 78, 130] : [232, 238, 244], .35);
        const wetHere = dr < rw || h < .06;
        if (N && Math.abs(x - mx) < 5 + k * 6) { const m = 1 - Math.abs(x - mx) / (6 + k * 6); if (wetHere && hash2(x, y, 9) < .45 * m) c = [196, 204, 236]; else c = mixRGB(c, [70, 76, 110], .25 * m); }   // the moon's glitter path; a sheen on the rice
        if (haze) c = mixRGB(c, [206, 214, 218], haze);
        const i = ((y - y0) * W + x) * 4; D[i] = c[0]; D[i + 1] = c[1]; D[i + 2] = c[2]; D[i + 3] = 255;
      }
    }
    g.putImageData(id, 0, y0);
  },
  treeline(g, pts, c, rim, off, W, H) { // the forest of the pass below us: cedar spires and round broadleaf crowns, rimmed by the moon
    const top = new Float32Array(W), base = x => pts[Math.floor(clamp(x, 0, W - 1) / W * (pts.length - 1))] * H + off;
    for (let x = 0; x < W; x++) top[x] = base(x);
    const R = RNG(77); let x = -6;
    while (x < W + 6) {
      const cedar = R() < .55, w = cedar ? 5 + R() * 5 : 9 + R() * 9, h = cedar ? 7 + R() * 9 : 4 + R() * 6;
      for (let i = 0; i < w; i++) { const X = Math.round(x + i); if (X < 0 || X >= W) continue; const u = (i + .5) / w * 2 - 1, prof = cedar ? (1 - Math.abs(u)) * h + (i % 2) * .7 : Math.sqrt(Math.max(0, 1 - u * u)) * h + (hash2(X, 3, 4) - .5) * 1.4; top[X] = Math.min(top[X], base(X) - prof); }
      x += w * (cedar ? .55 + R() * .2 : .7);
    }
    g.fillStyle = "#8a96c8"; for (let y = 0; y < 18; y++) { g.globalAlpha = .011 * (18 - y); for (let x = 0; x < W; x += 2) g.fillRect(x, (base(x) | 0) - 3 - y, 2, 1); } g.globalAlpha = 1;   // a breath of mist lying on the forest
    g.fillStyle = rgbHex(c); for (let x = 0; x < W; x++) g.fillRect(x, top[x] | 0, 1, H);
    g.fillStyle = rim; for (let x = 1; x < W; x++) if (top[x] < top[x - 1] - .4 || hash2(x, 7, 2) < .35) g.fillRect(x, top[x] | 0, 1, 1);
  },
  ridgeTo(g, pts, c, off, W, H) { g.fillStyle = rgbHex(c); for (let x = 0; x < W; x++) { const y = pts[Math.floor(x / W * (pts.length - 1))] * H + off; g.fillRect(x, y | 0, 1, H - y); } },
  branches(W, H, night) { // the crown of the great camphor framing the view; her silhouette on a limb
    const N = night > .5, g = this.g, R = RNG(8), M = new Uint8Array(W * H);
    const C = N ? { dk: "#05060b", mid: "#0a0d18", lit: "#141a2e", rim: "#2a3354", glint: "#3a4874", bark: "#090a11", barkRim: "#262c44" }
      : { dk: "#1a2416", mid: "#26341f", lit: "#34472a", rim: "#4f6638", glint: "#6c8448", bark: "#2a241c", barkRim: "#5a4a36" };
    const set = (x, y, v) => { x |= 0; y |= 0; if (x >= 0 && y >= 0 && x < W && y < H) M[y * W + x] = v; };
    const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? 0 : M[y * W + x];
    const brush = (x, y, r) => { for (let j = -Math.ceil(r); j <= r; j++) for (let i = -Math.ceil(r); i <= r; i++) if (i * i + j * j <= r * r + .5) set(x + i, y + j, 2); };
    const limb = (pts, w0, w1) => { const L = pts.length - 1; for (let i = 0; i < L; i++) { const [ax, ay] = pts[i], [bx, by] = pts[i + 1], n = Math.max(1, Math.ceil(hyp(bx - ax, by - ay))); for (let k = 0; k <= n; k++) brush(lerp(ax, bx, k / n), lerp(ay, by, k / n), Math.max(.4, lerp(w0, w1, (i + k / n) / L) / 2)); } };
    const mass = (cx, cy, r) => { // a leaf mass: overlapping lobes with a softly scalloped edge and a chink of sky here and there
      const n = 7 + (r * .8 | 0), sd = R() * 99 | 0;
      for (let k = 0; k < n; k++) {
        const a = R() * TAU, d = Math.sqrt(R()) * r, lx = cx + Math.cos(a) * d, ly = cy + Math.sin(a) * d * .65, lr = 2.5 + R() * r * .38;
        for (let yy = -lr - 2; yy <= lr + 2; yy++) for (let xx = -lr - 2; xx <= lr + 2; xx++) {
          const X = lx + xx, Y = ly + yy, q = hyp(xx, yy * 1.15) / lr + (vnoise(X * .45, Y * .45, sd) - .5) * .55;
          if (q > 1 || (q > .5 && hash2(X >> 1, Y >> 1, sd + 7) < .05)) continue;
          set(X, Y, 1);
        }
      }
    };
    // wood: a bough from the unseen trunk on the right, twigs off it, a thinner one on the left, the limb she stands on
    const bough = [[W + 8, H * .3], [W * .86, H * .22], [W * .7, H * .1], [W * .52, -6]];
    limb(bough, 10, 3);
    limb([[W * .86, H * .22], [W * .93, H * .42], [W * .9, H * .55]], 4, 1.5);
    limb([[W * .7, H * .1], [W * .62, H * .2], [W * .58, H * .23]], 3, 1);
    limb([[-6, H * .42], [W * .05, H * .3], [W * .1, H * .14], [W * .08, -6]], 6, 2);
    limb([[W * .55, H * .66], [W * .7, H * .67], [W * .86, H * .72], [W + 8, H * .84]], 5, 15);
    for (let k = 0; k < 24; k++) { const x = R() * W; if (x > W * .12 && x < W * .34) continue; mass(x, -8 + R() * H * .08, 11 + R() * 13); }  // the canopy overhead
    for (let k = 0; k < 7; k++) mass(W * (.62 + R() * .3), H * (.08 + R() * .14), 8 + R() * 9);                                              // hanging from the bough
    for (let k = 0; k < 14; k++) mass(W - R() * W * .15, H * .12 + R() * H * .55, 8 + R() * 10);                                           // the right edge
    for (let k = 0; k < 5; k++) mass(R() * W * .09, H * .14 + R() * H * .3, 7 + R() * 7);                                                   // a little on the left
    mass(W * .6, H * .21, 7); mass(W * .9, H * .55, 6);                                                                                      // where the twigs end
    // the silhouette frays into single leaves
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) if (!M[y * W + x] && ((at(x + 1, y) === 1) + (at(x - 1, y) === 1) + (at(x, y + 1) === 1) + (at(x, y - 1) === 1)) > 0 && hash2(x, y, 21) < .16) M[y * W + x] = 3;
    // shade by the moon (upper-left): rim where the sky is right there, then lit, then the dark inside
    const id = g.createImageData(W, H), D = id.data, P = {}; for (const k in C) P[k] = hexRGB(C[k]);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const v = M[y * W + x]; if (!v) continue; let c;
      if (v === 2) c = at(x, y - 1) === 0 || at(x - 1, y - 1) === 0 ? P.barkRim : (hash2(x >> 2, y, 41) < .12 ? P.mid : P.bark);
      else {
        let o = 0; while (o < 4 && at(x - o - 1, y - o - 1)) o++;
        c = o === 0 ? P.rim : o === 1 ? P.lit : o <= 3 ? P.mid : P.dk;
        if (o >= 1 && o <= 2 && hash2(x >> 1, y, 31) < .12) c = P.glint;   // a glossy camphor leaf catching the moon
        if (!at(x + 1, y + 1)) c = P.dk;
      }
      const i = (y * W + x) * 4; D[i] = c[0]; D[i + 1] = c[1]; D[i + 2] = c[2]; D[i + 3] = 255;
    }
    g.putImageData(id, 0, 0);
    this.tsuzuraBack(W * .7 | 0, H * .67 - 2 | 0, C.dk, N ? "#3a4670" : null);
  },
  susuki(W, H, night) { // the lookout: a knoll in a sea of pampas grass, plumes leaning off downwind
    const N = night > .5, R = RNG(31);
    const C = N ? { stalk: "#0c0d18", blade: "#0a0b14", plume: "#363e5e", lit: "#7a86b4", tip: "#aab4dc", knoll: "#0b0c16", rim: "#262c48" }
      : { stalk: "#56603e", blade: "#4a5a36", plume: "#b4a484", lit: "#e2d8c0", tip: "#f6f0e0", knoll: "#3e4a32", rim: "#6a7a50" };
    const kx = W * .64, ky = H * .86, kw = W * .22;
    for (let x = kx - kw; x < kx + kw; x++) {
      const u = (x - kx) / kw, top = ky + u * u * H * .1 + (hash2(x | 0, 1, 3) - .5) * 1.2;
      this.g.fillStyle = C.knoll; this.g.fillRect(x | 0, top | 0, 1, H);
      if (hash2(x | 0, 5, 1) < .35) this.g.fillRect(x | 0, (top - 1 - hash2(x | 0, 6, 1) * 2) | 0, 1, 3);
      else if (u < .1 || hash2(x | 0, 2, 3) < .3) { this.g.fillStyle = C.rim; this.g.fillRect(x | 0, top | 0, 1, 1); }
    }
    for (const [n, y0, y1, h0, h1] of [[110, .72, .8, .06, .1], [80, .8, .92, .1, .17], [44, .96, 1.06, .2, .3]]) {
      for (let k = 0; k < n; k++) {
        const bx = R() * W, by = H * (y0 + R() * (y1 - y0)), h = H * (h0 + R() * (h1 - h0)), lean = .2 + R() * .25;
        if (Math.abs(bx + h * lean * .6 - kx) < 18 && by > ky - 6) continue;           // leave her standing in the open
        for (let j = 0; j < 3; j++) { const sd = R() < .5 ? -1 : 1, L = h * (.3 + R() * .3); for (let i = 0; i < L; i++) { const t = i / L; this.px(bx + sd * t * t * L * .6, by - t * L * (1 - t * .55), C.blade); } }
        let x = bx, y = by; for (let i = 0; i < h; i++) { const t = i / h; x = bx + t * t * h * lean; y = by - i; this.px(x, y, C.stalk); }
        const pl = 4 + R() * 5 + h * .04;
        for (let sd = 0; sd < 3; sd++) for (let i = 0; i < pl; i++) { const t = i / pl; this.px(x + i * .9 + sd * .5, y - 1 + sd + t * t * pl * .7 + Math.sin(t * 3 + sd) * .5, t > .78 ? C.tip : sd === 0 ? C.lit : C.plume); }
      }
    }
    this.tsuzuraBack(kx | 0, ky + 1 | 0, N ? "#06070d" : "#22242c", N ? "#3a4670" : null);
  },
  tsuzuraBack(x, y, c, rim) { // a small silhouette from behind: round ears, the frame's poles, the tail; backlit by the moon
    const pts = ["...k.......k...", "..kkk.kkk.kkk..", "...kkkkkkkkk...", "...kkkkkkkkk...", "..kkkkkkkkkkk..", "..kkkkkkkkkkk..", "...kkkkkkkkk...", "....kkkkkkk....", "...kkkkkkkkk...", "...kkkkkkkkkk..", "...kkkkkkkkkkkk", "....kkkkkkkkkkk", "....kkkk.kkk.kk", "....kk....kk...", "....kk....kk..."];
    const S = new Set(), key = (i, j) => (i | 0) * 4096 + (j | 0);
    for (let j = 0; j < pts.length; j++) for (let i = 0; i < pts[j].length; i++) if (pts[j][i] === "k") S.add(key(x + i - 7, y + j - pts.length));
    for (let j = 0; j < 22; j++) { S.add(key(x - 5, y - 15 - j * .5 - 4)); S.add(key(x + 5, y - 15 - j * .5 - 4)); }
    for (const k of S) { const i = Math.floor(k / 4096), j = k - i * 4096; this.px(i, j, rim && j < y - 3 && (!S.has(key(i - 1, j)) || !S.has(key(i, j - 1))) ? rim : c); }
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
    await UI.fade(1, .8); UI.showHud(false); this.on = true; this.mode = "lookout"; this.night = GAME.tod > 19.3 || GAME.tod < 5 ? 1 : 0; this.wave = 1; this.procession = this.night > .5; this.t = 0;
    await UI.fade(0, 1.2); AU.stinger("discover");
    await CINE.wait(2);
    if (this.night > .5) await CINE.say(T("soft", "……那些灯。"), T("soft", "一盏也没有少。"), T("thinking", "全都变成了远山的颜色。"));
    else await CINE.say(T("surprised", "……城还在。"), T("thinking", "屋顶、烟囱、河上的桥，一样都没少。"), T("soft", "就是全都变成了远山的颜色。"));
    await UI.fade(1, .8); this.on = false; UI.showHud(true); await UI.fade(0, .8);
    GAME.cine = false;
  },
};
