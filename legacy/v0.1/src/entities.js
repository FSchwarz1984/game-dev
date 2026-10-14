/* =====================================================================
   ENTITIES — the things she can touch: loose materials, the offerings,
   the shrine site, the radio, stone lanterns that will hold weight, the
   jizō, the charcoal-burner's note, the ghosts of what went Far, the
   crow and the deer, and later Kagomaru.
   ===================================================================== */
"use strict";
const ITEM = {
  // w: weight (貫) · hgt: height on the back-frame · build: what it counts toward at the shrine
  beam:   { zh: "祠的横梁", rect: "log1", w: 6, hgt: 11, build: { pillar: 2 } },
  log:    { zh: "杉木段", rect: "log0", w: 5, hgt: 11, build: { pillar: 2 } },
  pole:   { zh: "竹竿", rect: "pole", w: 1, hgt: 6, build: { pillar: 1 } },
  bark:   { zh: "杉树皮", rect: "bark", w: 1, hgt: 7, build: { roof: 1 } },
  vine:   { zh: "葛藤", rect: "vine", w: 1, hgt: 8, build: { rope: 1 } },
  flat:   { zh: "平石", rect: "flatstone", w: 4, hgt: 9, build: { base: 1 } },
  holed:  { zh: "穴石——御神体", rect: "holed", w: 2, hgt: 10, build: { god: 1 } },
  basket: { zh: "葛笼", rect: "basket", w: 1, hgt: 16 },
  radio:  { zh: "铁匣子", rect: "radio", w: 1, hgt: 12 },
};
const EN = {
  list: [], nid: 1,
  add(e) { e.id = this.nid++; e.dead = false; this.list.push(e); return e; },
  near(x, y, r, f) { const out = []; for (const e of this.list) if (!e.dead && hyp(e.x - x, e.y - y) < r && (!f || f(e))) out.push(e); return out; },
  find(f) { return this.list.find(e => !e.dead && f(e)); },
  update(dt) { for (const e of this.list) if (!e.dead && e.update) e.update(dt); for (let i = this.list.length - 1; i >= 0; i--) if (this.list[i].dead && this.list[i].gone) this.list.splice(i, 1); },
  draw() { const c = RD.cam; for (const e of this.list) { if (e.dead || !e.draw) continue; if (e.x < c.vx0 - 160 || e.x > c.vx1 + 160 || e.y - (e.z || 0) < c.vy0 - 200 || e.y - (e.z || 0) > c.vy1 + 260) continue; e.draw(); } },
};
/* ---------- loose things she can carry ---------- */
function mkItem(kind, x, y, o = {}) {
  const K = ITEM[kind];
  const e = EN.add(Object.assign({ type: "item", kind, x, y, z: WORLD.heightAt(x, y), vz: 0, w: K.w, w0: K.w, wmax: 9, carry: true, t: Math.random() * 6 }, o));
  e.update = dt => {
    e.t += dt;
    const gz = WORLD.heightAt(e.x, e.y), wl = WORLD.waterAt(e.x, e.y);
    if (e.vz || e.z > gz + .1) { e.vz -= 400 * dt; e.z += e.vz * dt; e.x += (e.vx || 0) * dt; e.y += (e.vy || 0) * dt; if (e.z <= gz) { if (e.vz < -60) { AU.sfx("fall", { size: clamp(e.w / 6, .2, 1), x: e.x, y: e.y }); FX.burst("dust", e.x, e.y, gz + 1, 6, { life: .5, c: [.6, .55, .46], speed: .5, up: .3, drag: 4, size: 1, a: .6 }); } e.z = gz; e.vz = 0; e.vx = e.vy = 0; } }
    // weightless things lift a little and drift on the wind; light things float on water and are carried downstream
    if (e.w === 0) { e.x += RD.env.wind[0] * 3 * dt * (1 + Math.sin(e.t)); }
    if (wl > gz + 3 && e.w <= 1) { const [fx, fy] = WORLD.flowAt(e.x, e.y); e.x += fx * 26 * dt; e.y += fy * 26 * dt; e.z = wl - 1; }
  };
  e.draw = () => {
    const r = ATLAS.rects[K.rect]; const lift = e.w === 0 ? 4 + Math.sin(e.t * 2.2) * 1.5 : 0; const heavy = e.w > e.w0;
    RD.sprite({ x: e.x, y: e.y, z: e.z + lift - (heavy ? 1 : 0), r, tint: heavy ? [.86, .84, .82, 0] : e.hl ? [1.15, 1.12, 1.05, 0] : T4, shadow: 1 });
    RD.blob(e.x, e.y, e.z, r.w * .8, 5, e.w === 0 ? .4 : .8);
    if (e.w === 0 && Math.random() < .1) FX.spawn("mote", e.x + (Math.random() - .5) * r.w * .6, e.y, e.z + 4, { life: .8, c: [1, .86, .5], vz: 8, add: true, a: .8 });
  };
  return e;
}
/* ---------- offerings: the ninety-nine small things ---------- */
function mkOffering(art, x, y, idx) {
  const e = EN.add({ type: "offering", art, idx, x, y, z: WORLD.heightAt(x, y), t: Math.random() * 9 });
  e.update = dt => { e.t += dt; };
  e.draw = () => {
    const r = ATLAS.rects["off_" + e.art]; RD.sprite({ x: e.x, y: e.y, z: e.z + Math.round(Math.sin(e.t * 2) * .6), r, shadow: 0 });
    if (Math.sin(e.t * 1.3 + e.idx) > .985) FX.spawn("glint", e.x + (Math.random() - .5) * 4, e.y, e.z + 6, { life: .5, c: [1, .95, .7], add: true, size: 1 });
    if (e.t % 4 < .03) FX.spawn("glint", e.x, e.y, e.z + 8, { life: .6, c: [1, .92, .6], add: true, size: 2, a: .8, fade: .6 });
  };
  return e;
}
/* ---------- stone lanterns: things that can hold weight ---------- */
function mkLantern(x, y, o = {}) {
  const e = EN.add(Object.assign({ type: "lantern", x, y, z: WORLD.heightAt(x, y), w: 4, w0: 4, wmax: 12, lit: false, solid: 6 }, o));
  e.draw = () => {
    const r = ATLAS.rects[e.lit ? "toroLit" : "toro"]; const sink = clamp(e.w - e.w0, 0, 6) * .4;
    RD.sprite({ x: e.x, y: e.y, z: e.z - sink, r, tint: e.hl ? [1.15, 1.12, 1.05, 0] : T4 });
    if (e.lit || (RD.env.night > .5 && GAME.flags.shrineDone)) { RD.light(e.x, e.y + 2, e.z + 28, 60, 1.1, .72, .4); RD.glow(1, e.x, e.y + 1, e.z + 28, 26, 26, .55, .34, .14, .7); }
  };
  return e;
}
/* ---------- the shrine site: five states, fed by what she carries ---------- */
const SITE = {
  e: null, stage: 0,
  needs: [ { base: 1 }, { pillar: 4 }, { roof: 3 }, { rope: 1, god: 1 } ],
  have: { base: 0, pillar: 0, roof: 0, rope: 0, god: 0 },
  label: { base: "礎石", pillar: "柱", roof: "屋根", rope: "注连绳", god: "御神体" },
  init() {
    const [x, y] = LM.shrine;
    this.e = EN.add({ type: "site", x, y: y - 8, z: WD.shrineZ, solid: 15 });
    this.e.draw = () => { const r = ATLAS.rects["hokora" + this.stage]; RD.sprite({ x: this.e.x, y: this.e.y, z: this.e.z, r, tint: this.e.hl ? [1.1, 1.08, 1.02, 0] : T4 });
      if (this.stage >= 4) { const k = .7 + .3 * Math.sin(GAME.t * 1.3); RD.light(this.e.x, this.e.y + 4, this.e.z + 22, 70, .9 * k, .78 * k, .5 * k); } };
  },
  cur() { return this.needs[Math.min(this.stage, this.needs.length - 1)]; },
  missing() { if (this.stage >= 4) return {}; const n = this.cur(), out = {}; for (const k in n) if (this.have[k] < n[k]) out[k] = n[k] - this.have[k]; return out; },
  accepts(kind) { const b = ITEM[kind] && ITEM[kind].build; if (!b || this.stage >= 4) return false; const m = this.missing(); for (const k in b) if (m[k]) return true; return false; },
  give(kind) {
    const b = ITEM[kind].build; for (const k in b) this.have[k] = Math.min(this.have[k] + b[k], this.cur()[k] ?? this.have[k] + b[k]);
    if (Object.keys(this.missing()).length === 0) { for (const k in this.have) this.have[k] = 0; this.stage++; STORY.onStage(this.stage); return true; }
    return false;
  },
};
/* ---------- radio, notes, rest stones ---------- */
function mkInteract(type, x, y, o) { const e = EN.add(Object.assign({ type, x, y, z: WORLD.heightAt(x, y), t: 0 }, o)); return e; }
/* ---------- ghosts: what went Far. Drawn pale, and they keep their distance ---------- */
const GHOSTS = {
  list: [],
  add(rect, x, y, o = {}) { const g = Object.assign({ rect, x, y, z: o.z ?? WORLD.heightAt(x, y), par: o.par ?? .82, range: o.range ?? 520, a: 1, flip: false, wob: 1 }, o); this.list.push(g); return g; },
  draw() {
    const c = RD.cam; const P = PL.e; if (!P) return;
    for (const g of this.list) {
      if (g.hidden) continue;
      const camY = c.sy + (g.z || 0); // the camera centre's ground row near the ghost's height
      const d = hyp(c.sx - g.x, camY - g.y); if (d > g.range * 1.6) continue;
      const k = g.par * clamp(1 - d / (g.range * 1.6), 0, 1);
      const x = g.x + (c.sx - g.x) * k, y = g.y + (camY - g.y) * k;
      const a = clamp(1.25 - d / g.range, 0, 1) * (g.a ?? 1);
      if (a <= .02) continue;
      RD.ghostSprite({ x, y, z: g.z, r: ATLAS.rects[g.rect], flip: g.flip, tint: [a, 1, 1, g.wob], near: 0 });
    }
  },
};
/* ---------- the crow on the torii, the deer in the meadow ---------- */
function mkCrow(x, y, z) {
  const e = EN.add({ type: "crow", x, y, z, state: "perch", t: 0, vx: 0, vy: 0, vz: 0 });
  e.update = dt => {
    e.t += dt; const P = PL.e;
    if (e.state === "perch" && P && hyp(P.x - e.x, P.y - e.y) < 40 && !GAME.cine) { e.state = "fly"; e.vx = (e.x - P.x > 0 ? 1 : -1) * 60; e.vy = -30; e.vz = 50; AU.sfx("wings", { x: e.x, y: e.y }); if (Math.random() < .6) AU.sfx("crow", { x: e.x, y: e.y }); }
    if (e.state === "fly") { e.x += e.vx * dt; e.y += e.vy * dt; e.z += e.vz * dt; e.vz += 10 * dt; if (e.t > 30) e.dead = true; }
  };
  e.draw = () => { // a crow, 9 px of black with a glint
    const fr = e.state === "fly" ? (Math.floor(e.t * 10) % 2) : 0;
    const cols = [[22, 20, 26], [40, 38, 50], [70, 74, 96]];
    const pts = fr ? [[-3, 0], [-2, -1], [-1, 0], [0, 0], [1, 0], [2, -1], [3, 0], [0, 1], [1, 1], [-1, -1]] : [[0, 0], [1, 0], [-1, 0], [0, -1], [1, -1], [2, -2], [-1, 1], [0, 1], [1, 1], [-2, 1]];
    for (const [dx, dz] of pts) RD.part(e.x + dx, e.y, e.z - dz + 1, 1, cols[dz < 0 ? 1 : 0][0] / 255, cols[0][1] / 255, cols[0][2] / 255, 1);
    RD.part(e.x + (fr ? 0 : 2), e.y, e.z + 2, 1, .4, .45, .6, 1);
  };
  return e;
}
function mkDeer(x, y) {
  const e = EN.add({ type: "deer", x, y, z: WORLD.heightAt(x, y), t: Math.random() * 9, dir: Math.random() < .5 ? -1 : 1, flee: 0, gx: x, gy: y });
  e.update = dt => {
    e.t += dt; const P = PL.e;
    if (P && hyp(P.x - e.x, P.y - e.y) < 70 && !e.flee) { e.flee = 3; e.vx = (e.x - P.x) / hyp(e.x - P.x, e.y - P.y) * 110; e.vy = (e.y - P.y) / hyp(e.x - P.x, e.y - P.y) * 80; e.dir = e.vx > 0 ? 1 : -1; AU.sfx("deer", { x: e.x, y: e.y }); }
    if (e.flee > 0) { e.flee -= dt; e.x += e.vx * dt; e.y += e.vy * dt; if (WORLD.nearAt(e.x, e.y) < .3) { e.vx = -e.vx; e.vy = -e.vy; } if (e.flee <= 0) e.flee = 0; }
    else { e.x += Math.sin(e.t * .3) * 3 * dt; }
    e.z = WORLD.heightAt(e.x, e.y);
  };
  e.draw = () => { // sika deer: fawn coat with white spots, drawn as pixels
    const run = e.flee > 0, ph = run ? Math.floor(e.t * 12) % 2 : 0, D = e.dir;
    const body = [.62, .44, .28], dark = [.38, .26, .17], spot = [.92, .86, .74];
    const px = (dx, dz, c) => RD.part(e.x + dx * D, e.y, e.z + dz, 1, c[0], c[1], c[2], 1);
    for (let dx = -4; dx <= 4; dx++) for (let dz = 7; dz <= 10; dz++) px(dx, dz, dz === 7 ? dark : (dx + dz) % 4 === 0 && dz > 8 ? spot : body);
    for (const lx of [-3, -2, 2, 3]) for (let dz = 1; dz <= 6; dz++) px(lx + (run && dz < 4 ? (lx < 0 ? -ph : ph) : 0), dz, dark);
    for (let dz = 10; dz <= 14; dz++) px(5, dz, body); px(6, 14, body); px(7, 14, body); px(7, 13, dark); px(5, 15, dark); px(6, 16, dark);
    px(-5, 10, spot); px(-5, 11, spot);
    RD.blob(e.x, e.y, e.z, 12, 4, .6);
  };
  return e;
}
/* ---------- Kagomaru: the wicker trunk, awake ---------- */
const KAGOMARU = {
  e: null, items: [],
  wake(x, y) {
    this.e = EN.add({ type: "kago", x, y, z: WORLD.heightAt(x, y), t: 0, step: 0, open: 0, blink: 0, solid: 5 });
    const e = this.e;
    e.update = dt => {
      e.t += dt; const P = PL.e; if (!P || GAME.cine) return;
      const dx = P.x - e.x, dy = P.y - e.y, d = hyp(dx, dy);
      if (d > 34) { const sp = Math.min(90, (d - 30) * 2.4); e.x += dx / d * sp * dt; e.y += dy / d * sp * dt; e.step += dt * 9; if (Math.random() < dt * 4) AU.sfx("step", { mat: "wood", weight: .1, x: e.x, y: e.y }); }
      e.z = WORLD.heightAt(e.x, e.y);
      e.blink = (e.t % 4) < .12;
      e.open = Math.max(0, e.open - dt * 3);
    };
    e.draw = () => {
      const s = KAGO.frame(e.t, { step: e.step % 1, open: e.open, blink: e.blink });
      const r = RD.dynSlot(5, s, 14, 28); RD.charSprite({ x: e.x, y: e.y, z: e.z, r, flip: PL.e && PL.e.x < e.x });
      let z = e.z + 26; for (const it of this.items) { const rr = ATLAS.rects[ITEM[it.kind].rect]; RD.sprite({ x: e.x, y: e.y + 1, z, r: rr }); z += ITEM[it.kind].hgt; }
      RD.blob(e.x, e.y, e.z, 16, 5, .7);
    };
  },
  cap() { return this.items.reduce((s, i) => s + i.w, 0); },
};
