/* =====================================================================
   SYSTEMS — what the walking does to the world, and the game's state.
   NEARMAP: every step wears a trail and gives a little nearness back
   to pale ground; a rebuilt shrine pushes a ring of it outward.
   GAME: time, weather, offerings, delivery, Far contact, saving.
   ===================================================================== */
"use strict";
const NEARMAP = {
  dirty: null,
  mark(i0, j0, i1, j1) { const d = this.dirty; if (!d) this.dirty = [i0, j0, i1, j1]; else { d[0] = Math.min(d[0], i0); d[1] = Math.min(d[1], j0); d[2] = Math.max(d[2], i1); d[3] = Math.max(d[3], j1); } },
  step(x, y, load) {
    const ci = Math.floor(x / 8), cj = Math.floor(y / 8); const R = 1;
    for (let j = cj - R; j <= cj + R; j++) for (let i = ci - R; i <= ci + R; i++) {
      if (i < 0 || j < 0 || i >= WD.nw || j >= WD.nh) continue; const k = j * WD.nw + i; const w = (i === ci && j === cj) ? 1 : .35;
      WD.wear[k] = Math.min(1, WD.wear[k] + .022 * w * (1 + load * .08));
      // walking gives nearness back only where the Far has thinned the world, never at the hard edge
      if (WD.near[k] > .14 && WD.near[k] < 1) WD.near[k] = Math.min(WD.nearMax ? WD.nearMax[k] : 1, WD.near[k] + .012 * w);
    }
    this.mark(ci - R, cj - R, ci + R, cj + R);
  },
  // a ring of nearness spreading from a point (the restored shrine)
  wave: null,
  startWave(x, y, r, to) { this.wave = { x, y, r: 0, R: r, to }; },
  update(dt) {
    const w = this.wave;
    if (w) { const r0 = w.r; w.r += dt * 90; const i0 = Math.floor((w.x - w.r) / 8), i1 = Math.ceil((w.x + w.r) / 8), j0 = Math.floor((w.y - w.r) / 8), j1 = Math.ceil((w.y + w.r) / 8);
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { if (i < 0 || j < 0 || i >= WD.nw || j >= WD.nh) continue; const d = hyp(i * 8 + 4 - w.x, j * 8 + 4 - w.y); if (d > w.r || d < r0 - 8) continue; const k = j * WD.nw + i; const tgt = w.to * (1 - sstep(w.R * .6, w.R, d)); if (WD.near[k] > .1 && WD.near[k] < tgt) WD.near[k] = tgt; }
      this.mark(Math.max(0, i0), Math.max(0, j0), Math.min(WD.nw - 1, i1), Math.min(WD.nh - 1, j1));
      if (w.r > w.R) this.wave = null; }
    if (this.dirty) { const d = this.dirty; RD.uploadNear(false, [clamp(d[0], 0, WD.nw - 1), clamp(d[1], 0, WD.nh - 1), clamp(d[2], 0, WD.nw - 1), clamp(d[3], 0, WD.nh - 1)]); this.dirty = null; }
  },
  // pale pockets left behind by the night of the Far
  scar(x, y, r, v) { for (let j = Math.floor((y - r) / 8); j <= (y + r) / 8; j++) for (let i = Math.floor((x - r) / 8); i <= (x + r) / 8; i++) { if (i < 0 || j < 0 || i >= WD.nw || j >= WD.nh) continue; const d = hyp(i * 8 + 4 - x, j * 8 + 4 - y) / r; if (d > 1) continue; const k = j * WD.nw + i; const nv = lerp(v, WD.near[k], sstep(.55, 1, d) * 1); if (WD.near[k] > .1) WD.near[k] = Math.min(WD.near[k], nv); } },
};

const GAME = {
  t: 0, dt: 0, tod: 17.4, day: 1, timeScale: 1 / 40, // one game hour per 40 s
  state: "boot", cine: false, flags: {}, tutorial: false,
  found: new Set(), count: 3, offerings: [],
  weather: { rain: 0, overcast: 0, mist: 0, wind: [1, .25, .3], target: { rain: 0, overcast: 0 }, next: 240 },
  canControl() { return this.state === "play" && !this.cine && !UI.blocking(); },
  /* ---------- time & weather ---------- */
  tick(dt) {
    this.t += dt; this.dt = dt;
    if (!this.todLock) { this.tod += dt * this.timeScale; if (this.tod >= 24) { this.tod -= 24; this.day++; } }
    const W = this.weather;
    W.next -= dt; if (W.next <= 0 && !this.cine) { W.next = 200 + Math.random() * 260; const r = Math.random(); W.target = r < .22 ? { rain: .6 + Math.random() * .4, overcast: .8 } : r < .45 ? { rain: 0, overcast: .5 } : { rain: 0, overcast: 0 }; }
    W.rain = approach(W.rain, W.target.rain, dt * .03); W.overcast = approach(W.overcast, W.target.overcast, dt * .04);
    const gust = .25 + .2 * Math.sin(this.t * .13) + .15 * Math.sin(this.t * .41) + W.rain * .3;
    W.wind = [.9, .3, clamp(gust, 0, 1)];
    // mist pools at dawn and after rain
    W.mist = clamp(1 - Math.abs(this.tod - 5.8) / 1.6, 0, 1) * .35 + W.rain * .2;
    WD.wet = clamp((WD.wet || 0) + (W.rain > .1 ? dt * .02 : -dt * .004), 0, 1);
  },
  env() { const W = this.weather; return todEnv(this.tod, { rain: W.rain, overcast: W.overcast, mist: W.mist + (this.extraMist || 0), wind: W.wind }); },
  /* ---------- offerings ---------- */
  collectOffering(o) {
    if (o.dead) return; o.dead = true; o.gone = true; this.found.add(o.idx); this.count = Math.min(99, this.count + 1);
    AU.sfx("offering"); FX.burst("glint", o.x, o.y, o.z + 4, 10, { life: .8, c: [1, .9, .6], speed: .6, up: 1, add: true, drag: 2 });
    const first = !this.flags["off_" + o.art]; this.flags["off_" + o.art] = true;
    UI.countPop(this.count, o.art, first);
    if (first) STORY.offering(o.art);
    this.save();
  },
  /* ---------- the shrine ---------- */
  deliver() {
    const P = PL.e; const it = P.stack[P.stack.length - 1]; if (!it || !SITE.accepts(it.kind)) return;
    P.stack.pop(); AU.sfx("build"); FX.stream([P.x, P.y, P.z + 30], [SITE.e.x, SITE.e.y, SITE.e.z + 16], [.95, .85, .6], 16);
    FX.burst("dust", SITE.e.x, SITE.e.y + 4, SITE.e.z, 10, { life: .6, c: [.7, .64, .54], speed: .7, up: .4, drag: 3, a: .7 });
    const advanced = SITE.give(it.kind);
    UI.siteCard(true);
    if (!advanced) STORY.bark("delivered", it.kind);
    this.save();
  },
  onPick(kind) {
    if (kind === "basket" && !this.flags.gotBasket) { this.flags.gotBasket = true; STORY.event("basket"); }
    if (kind === "holed" && !this.flags.gotHoled) { this.flags.gotHoled = true; STORY.event("holed"); }
    if (kind === "radio") STORY.bark("radioPick");
  },
  onWeight(how, target) {
    if (this.tutorial) STORY.tutorialWeight(how, target);
    if (!this.flags.knowsWeight) this.flags.knowsWeight = true;
  },
  onFarTouch(t) {
    if (t > .9 && !this.flags.farTouched) { this.flags.farTouched = true; STORY.event("farTouch"); }
    else if (t > 2.4 && Math.random() < .004) STORY.bark("farAgain");
  },
  /* ---------- saving ---------- */
  save() {
    if (this.state !== "play" || this.noSave) return;
    const P = PL.e;
    const items = EN.list.filter(e => e.type === "item" && !e.dead).map(e => [e.kind, Math.round(e.x), Math.round(e.y), e.w]);
    const enc = arr => { let s = ""; for (let i = 0; i < arr.length; i++) s += String.fromCharCode(48 + Math.round(clamp(arr[i], 0, 1) * 63)); return s; };
    const lanterns = EN.list.filter(e => e.type === "lantern").map(e => e.w);
    store("tsuzura.save.v1", { v: 1, x: P.x, y: P.y, stack: P.stack, tail: P.tail, self: P.self, tod: this.tod, day: this.day, flags: this.flags, found: [...this.found], count: this.count,
      stage: SITE.stage, have: SITE.have, items, near: enc(WD.near), wear: enc(WD.wear), kago: !!KAGOMARU.e, kagoItems: KAGOMARU.items, lanterns, story: STORY.stage });
  },
  load() { return store("tsuzura.save.v1"); },
  applySave(s) {
    const dec = (str, arr) => { if (!str) return; for (let i = 0; i < Math.min(str.length, arr.length); i++) arr[i] = (str.charCodeAt(i) - 48) / 63; };
    dec(s.near, WD.near); dec(s.wear, WD.wear); RD.uploadNear(true);
    this.tod = s.tod; this.day = s.day; this.flags = s.flags || {}; this.found = new Set(s.found || []); this.count = s.count || 3;
    SITE.stage = s.stage || 0; Object.assign(SITE.have, s.have || {});
    for (const e of EN.list) if (e.type === "item") { e.dead = true; e.gone = true; }
    for (const [k, x, y, w] of s.items || []) mkItem(k, x, y, { w });
    for (const e of EN.list) if (e.type === "offering" && this.found.has(e.idx)) { e.dead = true; e.gone = true; }
    const L = EN.list.filter(e => e.type === "lantern"); (s.lanterns || []).forEach((w, i) => { if (L[i]) L[i].w = w; });
    const P = PL.init(s.x, s.y); P.stack = s.stack || []; P.tail = s.tail || 0; P.self = s.self ?? 2; if (P.tail >= 6) P.form = "stone"; if (P.self <= 0) P.form = "leaf";
    if (s.kago) { KAGOMARU.wake(s.x + 20, s.y + 10); KAGOMARU.items = s.kagoItems || []; }
    STORY.stage = s.story || "free";
  },
};
