/* =====================================================================
   PLAYER — ツヅラ. Walking is the game: slope, ground, water, load and
   the Far all bend her speed. The back-frame carries a stack that sways
   with every bump and turn and sheds its top when she pushes her luck.
   Her one borrowed nature is weight (重): J draws weight out of a thing
   into her tail, K gives it back to something. Six in the tail and she
   is a stone; none of her own and she is a leaf on the wind.
   ===================================================================== */
"use strict";
const PL = {
  e: null, CAP: 8, HMAX: 64,
  init(x, y) {
    this.e = { x, y, z: WORLD.heightAt(x, y), vx: 0, vy: 0, hop: 0, vh: 0, face: "front", flip: false, stepT: 0, dist: 0, stamina: 1, run: false,
      tail: 0, self: 2, form: "normal", stack: [], theta: 0, omega: 0, state: "play", climbT: 0, climb: null, blink: 0, expr: null, exprT: 0, idleT: 0,
      pushT: 0, farT: 0, wet: 0, lastSafe: { x, y }, emote: null, emoteT: 0, carryDist: {} };
    return this.e;
  },
  stackW() { return this.e.stack.reduce((s, i) => s + i.w, 0); },
  stackH() { return this.e.stack.reduce((s, i) => s + ITEM[i.kind].hgt, 0); },
  heavy() { return this.e.tail >= 4; },
  weightless() { return this.e.self <= 0; },
  /* ---------------- update ---------------- */
  update(dt) {
    const e = this.e; if (!e) return;
    e.blink -= dt; if (e.blink < -.12) e.blink = 2 + Math.random() * 3;
    if (e.exprT > 0) { e.exprT -= dt; if (e.exprT <= 0) e.expr = null; }
    if (e.emoteT > 0) { e.emoteT -= dt; if (e.emoteT <= 0) e.emote = null; }
    const ctl = GAME.canControl() && e.state === "play";
    let [ax, ay, am] = ctl ? IN.axis() : [0, 0, 0];
    if (e.form === "stone") { if (am > .2 && Math.random() < dt * 8) { e.wobble = .25; } ax = ay = am = 0; }
    this.actions(dt, ctl);
    this.move(dt, ax, ay, am);
    this.sway(dt, ax, ay, am);
    // facing
    if (am > .2) { if (Math.abs(ax) > Math.abs(ay) * 1.1) { e.face = "side"; e.flip = ax < 0; } else e.face = ay < 0 ? "back" : "front"; e.idleT = 0; } else e.idleT += dt;
  },
  /* ---------------- walking ---------------- */
  move(dt, ax, ay, am) {
    const e = this.e;
    const W = this.stackW(), heavy = this.heavy(), leaf = this.weightless();
    const run = IN.act.run && am > .3 && e.stamina > .05 && !heavy && !leaf && e.form === "normal";
    e.run = run;
    let sp = run ? 94 : 56;
    sp *= 1 - clamp((W - 3) / 12, 0, .55);           // load
    sp *= 1 - e.tail * .07;                          // a heavy tail drags
    const gz = WORLD.heightAt(e.x, e.y), mat = WORLD.matAt(e.x, e.y), wl = WORLD.waterAt(e.x, e.y), depth = wl > -500 ? wl - gz : 0;
    const wear = WORLD.wearAt(e.x, e.y), near = WORLD.nearAt(e.x, e.y);
    if (mat === 4 || mat === 7) sp *= 1.1; if (mat === 9) sp *= .72;
    sp *= 1 + wear * .22;
    if (depth > 0 && !leaf) sp *= clamp(1 - depth / 13, .3, 1);
    // slope along the way she is heading
    if (am > .05) { const ahead = WORLD.heightAt(e.x + ax * 5, e.y + ay * 5) - gz; const g = ahead / 5; sp *= g > 0 ? clamp(1 - g * 1.25, .35, 1) : clamp(1 - g * .25, 1, 1.2); }
    // the Far: the ground keeps moving under her feet and she gets nowhere
    const farK = clamp((near - .03) / .14, 0, 1);
    if (near < .17 && am > .1) { e.farT += dt; GAME.onFarTouch(e.farT); } else e.farT = Math.max(0, e.farT - dt * 2);
    sp *= leaf ? .85 : 1;
    let tvx = ax * am * sp * farK, tvy = ay * am * sp * farK;
    if (leaf) { const wnd = RD.env.wind; tvx += wnd[0] * 26 * (.6 + wnd[2]); tvy += wnd[1] * 18; if (depth > 0) { const [fx, fy] = WORLD.flowAt(e.x, e.y); tvx += fx * 60; tvy += fy * 60; } }
    const acc = leaf ? 3 : e.form === "stone" ? 20 : 14;
    const k = 1 - Math.exp(-acc * dt); e.vx += (tvx - e.vx) * k; e.vy += (tvy - e.vy) * k;
    if (run) e.stamina = Math.max(0, e.stamina - dt * (.16 + W * .02)); else e.stamina = Math.min(1, e.stamina + dt * (am > .1 ? .1 : .22));
    // integrate with collision, a pixel at a time
    const steps = Math.max(1, Math.ceil(Math.max(Math.abs(e.vx), Math.abs(e.vy)) * dt / 1.5));
    for (let s = 0; s < steps; s++) {
      const sx = e.vx * dt / steps, sy = e.vy * dt / steps;
      if (sx && this.canStep(e.x + sx, e.y, sx, 0)) e.x += sx; else if (sx) { e.vx *= .3; this.bump(sx, 0, dt); }
      if (sy && this.canStep(e.x, e.y + sy, 0, sy)) e.y += sy; else if (sy) { e.vy *= .3; this.bump(0, sy, dt); }
    }
    this.pushOut();
    // vertical: follow the ground, fall off ledges, float when weightless
    const g2 = WORLD.heightAt(e.x, e.y), w2 = WORLD.waterAt(e.x, e.y);
    const floor = leaf && w2 > g2 ? w2 : g2;
    if (e.climb) { e.climbT += dt; const t = clamp(e.climbT / .5, 0, 1); e.z = lerp(e.climb.z0, floor, easeOut(t)); if (t >= 1) { e.climb = null; AU.sfx("land", { h: .2 }); } }
    else if (e.z > floor + 1.5) { e.vh -= (leaf ? 60 : 420) * dt; if (leaf) e.vh = Math.max(e.vh, -18); e.z += e.vh * dt; if (e.z <= floor) { const v = -e.vh; e.z = floor; e.vh = 0; this.land(v); } }
    else { e.z = floor; e.vh = 0; }
    if (leaf) e.hop = 5 + Math.sin(GAME.t * 2.2) * 1.5; else e.hop = 0;
    // footsteps
    const spd = hyp(e.vx, e.vy);
    if (spd > 4 && e.z <= floor + .5) {
      e.stepT += spd * dt; e.dist += spd * dt;
      if (e.stepT > (run ? 11 : 9)) { e.stepT = 0; this.footstep(depth, mat); }
      for (const it of e.stack) it.dist = (it.dist || 0) + spd * dt;
    }
    if (depth > 2 && !leaf) e.wet = Math.min(1, e.wet + dt * .5); else e.wet = Math.max(0, e.wet - dt * .05);
    if (near > .3 && depth < 4 && !e.climb) e.lastSafe = { x: e.x, y: e.y };
  },
  canStep(nx, ny, dx, dy) {
    const e = this.e, gz = WORLD.heightAt(e.x, e.y), nz = WORLD.heightAt(nx, ny);
    if (nx < 8 || ny < 8 || nx > WD.W - 8 || ny > WD.H - 8) return false;
    if (WORLD.nearAt(nx, ny) < .02) return false;
    const dirx = Math.sign(dx), diry = Math.sign(dy);
    const ahead = WORLD.heightAt(nx + dirx * 3, ny + diry * 3);
    const rise = Math.max(nz, ahead) - Math.max(gz, e.z);
    if (rise > 6 && !this.weightless()) { this.wall = { rise, dx: dirx, dy: diry }; return false; }
    // deep water: only the heavy walk the bed; the weightless float
    const wl = WORLD.waterAt(nx, ny); if (wl > -500 && wl - nz > 10 && !this.heavy() && !this.weightless()) { this.deep = true; return false; }
    // scenery trunks and stones
    for (const o of PL.colliders(nx, ny)) if (hyp(nx - o[0], ny - o[1]) < o[2] + 3) return false;
    return true;
  },
  colliders(x, y) { const out = []; const g = WORLD.grid; if (!g) return out; const cx = Math.floor(x / 64), cy = Math.floor(y / 64);
    for (let j = cy - 1; j <= cy + 1; j++) for (let i = cx - 1; i <= cx + 1; i++) { const b = g.get(j * 1000 + i); if (b) for (const o of b) out.push(o); }
    for (const en of EN.list) if (!en.dead && en.solid) out.push([en.x, en.y, en.solid]);
    return out; },
  pushOut() { const e = this.e; for (const o of this.colliders(e.x, e.y)) { const dx = e.x - o[0], dy = e.y - o[1], d = hyp(dx, dy), m = o[2] + 3; if (d < m && d > .01) { e.x = o[0] + dx / d * m; e.y = o[1] + dy / d * m; } } },
  // pushing into a ledge: after a beat she hauls herself (and her load) up, if it isn't too high
  bump(dx, dy, dt) {
    const e = this.e, w = this.wall; this.wall = null; if (!w || e.climb || e.form !== "normal") return;
    e.pushT += dt * 3;
    if (e.pushT > .45 && w.rise < 30 && this.stackW() <= 5 && e.stamina > .15) {
      const tx = e.x + w.dx * 7, ty = e.y + w.dy * 7, tz = WORLD.heightAt(tx, ty);
      if (tz - e.z < 30 && WORLD.nearAt(tx, ty) > .05) { e.climb = { z0: e.z }; e.climbT = 0; e.x = tx; e.y = ty; e.stamina -= .2; e.pushT = 0; AU.sfx("rustle", { x: e.x, y: e.y }); this.jolt(.12); FX.burst("dust", e.x, e.y, tz, 6, { life: .5, c: [.62, .56, .46], speed: .4, up: .4, drag: 4, a: .7 }); }
    } else if (e.pushT > .45 && w.rise >= 30 && !GAME.flags.toldCliff) { GAME.flags.toldCliff = true; STORY.bark("cliff"); }
    else if (e.pushT > .45 && this.stackW() > 5 && !GAME.flags.toldClimbLoad) { GAME.flags.toldClimbLoad = true; STORY.bark("climbLoad"); }
    if (this.deep && !GAME.flags.toldDeep) { GAME.flags.toldDeep = true; STORY.bark("deep"); }
    this.deep = false;
  },
  land(v) {
    const e = this.e; if (v < 60) return;
    AU.sfx("land", { h: clamp(v / 200, 0, 1) }); FX.burst("dust", e.x, e.y, e.z, 8, { life: .6, c: [.6, .55, .46], speed: .7, up: .3, drag: 4, a: .7 });
    this.jolt(clamp(v / 400, 0, .5)); RD.cam.shake = Math.min(3, v / 120);
  },
  footstep(depth, mat) {
    const e = this.e, W = this.stackW() + e.tail;
    const m = depth > 0 ? "water" : mat === 7 ? "stone" : mat === 4 ? "soil" : mat === 2 ? "leaves" : mat === 8 ? "sand" : mat === 6 ? "moss" : mat === 3 ? "stone" : "grass";
    AU.sfx("step", { mat: m, weight: clamp(W / 10, 0, 1), run: e.run, x: e.x, y: e.y });
    NEARMAP.step(e.x, e.y, W);
    if (depth > 0) FX.burst("splash", e.x, e.y, e.z + depth, 4, { life: .4, c: [.85, .94, 1], speed: .4, up: .9, g: 300, size: 1 });
    else if (e.run || W > 6) FX.burst("dust", e.x, e.y, e.z, 2, { life: .45, c: [.62, .56, .46], speed: .3, up: .2, drag: 4, a: .6 });
    // rough ground jostles the load
    if (m === "grass" || m === "leaves" || m === "moss") this.jolt((e.run ? .05 : .018) * (1 + this.stackH() / 40) * (Math.random() < .5 ? -1 : 1));
  },
  jolt(a) { this.e.omega += a * (Math.random() < .5 ? -1 : 1) * 6; },
  /* ---------------- the stack on her back ---------------- */
  sway(dt, ax, ay, am) {
    const e = this.e; const H = this.stackH(); if (!e.stack.length) { e.theta *= .8; e.omega = 0; return; }
    // turning hard, starting, stopping and wind all push the load sideways
    const lat = (e.face === "side" ? 0 : (e.vx - (e.pvx || 0))) + (e.face === "side" ? (e.vy - (e.pvy || 0)) * (e.flip ? -1 : 1) : 0);
    e.pvx = e.vx; e.pvy = e.vy;
    const top = e.stack[e.stack.length - 1];
    const windF = RD.env.wind[0] * RD.env.wind[2] * (H / 40) * (top.w === 0 ? 3 : 1) * (.5 + .5 * Math.sin(GAME.t * .7));
    const stiff = 9 + e.tail * 4 + (am < .1 ? 6 : 0);
    e.omega += (-lat * .022 * (1 + H / 36) + windF * .9) * 1;
    e.omega += (-stiff * e.theta - 2.6 * e.omega) * dt;
    e.theta += e.omega * dt;
    const tmax = clamp(.52 - H / 150, .2, .52) + e.tail * .03;
    if (Math.abs(e.theta) > tmax) this.shed(Math.sign(e.theta));
    if (Math.abs(e.omega) > 1.2 && Math.random() < dt * 3) AU.sfx("wobble", { amt: clamp(Math.abs(e.theta) / tmax, 0, 1) });
  },
  shed(dir) {
    const e = this.e; const it = e.stack.pop(); if (!it) return;
    const ent = mkItem(it.kind, e.x + dir * 6, e.y + 2, { z: e.z + 28 + this.stackH(), vz: 40, vx: dir * 40, vy: 10, w: it.w });
    e.theta *= .4; e.omega *= -.3;
    AU.sfx("fall", { size: clamp(it.w / 6, .2, 1), x: e.x, y: e.y });
    STORY.bark("shed");
    return ent;
  },
  /* ---------------- verbs ---------------- */
  target(r = 30, f) {
    const e = this.e; let best = null, bs = 1e9; const fx = e.face === "side" ? (e.flip ? -1 : 1) : 0, fy = e.face === "front" ? 1 : e.face === "back" ? -1 : 0;
    for (const o of EN.list) { if (o.dead || !f(o)) continue; const dx = o.x - e.x, dy = o.y - e.y, d = hyp(dx, dy); if (d > r) continue; const s = d - (dx * fx + dy * fy) / Math.max(d, 1) * 8; if (s < bs) { bs = s; best = o; } }
    return best;
  },
  weightTargets() { return o => (o.type === "item" || o.type === "lantern" || o.type === "kago") && o.w != null; },
  actions(dt, ctl) {
    const e = this.e; for (const o of EN.list) o.hl = 0;
    this.prompts = [];
    if (!ctl) return;
    // what is in front of her
    const pick = this.target(26, o => o.type === "item" && o.carry && o.vz === 0);
    const off = this.target(18, o => o.type === "offering");
    const site = SITE.e && hyp(SITE.e.x - e.x, SITE.e.y - e.y) < 46 ? SITE.e : null;
    const inter = this.target(28, o => o.interact);
    const wt = this.target(30, this.weightTargets());
    // offerings are scooped up as she passes
    if (off && hyp(off.x - e.x, off.y - e.y) < 12) GAME.collectOffering(off);
    if (e.form === "stone") { this.prompts.push(["give", "予", "把重量交出去"]); if (wt) wt.hl = 1; }
    // act: deliver to the shrine > talk/use > pick up
    if (site && e.stack.length && SITE.accepts(e.stack[e.stack.length - 1].kind)) { this.prompts.push(["act", "献", "放进祠里"]); site.hl = 1; if (IN.hit.act) { IN.consume("act"); GAME.deliver(); } }
    else if (inter) { inter.hl = 1; this.prompts.push(["act", inter.verb || "看", inter.label || ""]); if (IN.hit.act) { IN.consume("act"); inter.interact(); } }
    else if (pick && e.form === "normal") {
      pick.hl = 1; const K = ITEM[pick.kind]; const okW = this.stackW() + pick.w <= this.CAP, okH = this.stackH() + K.hgt <= this.HMAX;
      this.prompts.push(["act", "背", K.zh + (pick.w === 0 ? "（无重）" : "")]);
      if (IN.hit.act) { IN.consume("act");
        if (!okW) { STORY.bark("tooHeavy", pick); AU.sfx("deny"); }
        else if (!okH) { STORY.bark("tooTall"); AU.sfx("deny"); }
        else { e.stack.push({ kind: pick.kind, w: pick.w, dist: 0 }); pick.dead = true; pick.gone = true; AU.sfx("pickup", { size: clamp(pick.w / 6, .1, 1) }); AU.sfx("stack", { n: e.stack.length }); this.jolt(.06 * pick.w); GAME.onPick(pick.kind); }
      }
    }
    // drop the top item (hold to unload everything); next to Kagomaru it goes into the trunk instead
    if (e.stack.length && e.form === "normal") {
      const kg = KAGOMARU.e && hyp(KAGOMARU.e.x - e.x, KAGOMARU.e.y - e.y) < 30 ? KAGOMARU.e : null;
      this.prompts.push(["drop", "卸", kg ? "交给籠丸" : "放下"]);
      if (IN.hit.drop) { IN.consume("drop"); const it = e.stack.pop();
        if (kg && KAGOMARU.cap() + it.w <= 4) { KAGOMARU.items.push(it); kg.open = 1; AU.sfx("place"); }
        else { const fx = e.face === "side" ? (e.flip ? -12 : 12) : 0, fy = e.face === "front" ? 10 : e.face === "back" ? -10 : 4; mkItem(it.kind, e.x + fx, e.y + fy, { w: it.w }); AU.sfx("drop", { size: clamp(it.w / 6, .1, 1) }); } }
    } else if (KAGOMARU.items.length && KAGOMARU.e && hyp(KAGOMARU.e.x - e.x, KAGOMARU.e.y - e.y) < 30 && IN.hit.drop) {
      IN.consume("drop"); const it = KAGOMARU.items.pop(); e.stack.push(it); KAGOMARU.e.open = 1; AU.sfx("pickup", { size: .3 });
    }
    // 取 take weight: from the thing in front of her, or failing that from the heaviest thing on her back
    if (GAME.flags.knowsWeight || GAME.tutorial) {
      if (wt && (wt.w > 0)) { wt.hl = 1; this.prompts.push(["take", "取", "重 " + wt.w]); }
      else if (e.stack.length && e.stack.some(s => s.w > 0)) this.prompts.push(["take", "取", "背上的重量"]);
      if (wt && e.tail > 0) this.prompts.push(["give", "予", "交给它"]);
      if (IN.hit.take) { IN.consume("take"); this.take(wt); }
      if (IN.hit.give) { IN.consume("give"); this.give(wt); }
    }
  },
  take(t) {
    const e = this.e;
    if (this.weightless()) { if (!t || t.w <= 0) { AU.sfx("deny"); return; } t.w--; e.self++; FX.stream([t.x, t.y, (t.z || 0) + 8], [e.x, e.y, e.z + 20], [1, .8, .4], 14); AU.sfx("unleaf"); if (e.self >= 2) this.setForm("normal"); return; }
    if (e.tail >= 6) { AU.sfx("deny"); return; }
    let from = null;
    if (t && t.w > 0) from = t;
    else { let best = null; for (const s of e.stack) if (s.w > 0 && (!best || s.w > best.w)) best = s; if (best) from = best; }
    if (!from) { STORY.bark("noTake"); AU.sfx("deny"); return; }
    from.w--; e.tail++;
    const src = from === t ? [t.x, t.y, (t.z || 0) + 6] : [e.x, e.y, e.z + 30];
    FX.stream(src, [e.x + (e.flip ? 6 : -6), e.y, e.z + 10], [1, .78, .36], 20);
    AU.sfx("take"); GAME.onWeight("take", from);
    if (e.tail >= 6) this.setForm("stone");
  },
  give(t) {
    const e = this.e;
    if (!t) { STORY.bark("noGive"); AU.sfx("deny"); return; }
    if (t.w >= (t.wmax ?? 9)) { STORY.bark("full"); AU.sfx("deny"); return; }
    if (e.tail > 0) { e.tail--; t.w++; }
    else if (e.self > 0 && GAME.flags.knowsLeaf) { e.self--; t.w++; if (e.self <= 0) this.setForm("leaf"); }
    else { STORY.bark("emptyTail"); AU.sfx("deny"); return; }
    FX.stream([e.x, e.y, e.z + 12], [t.x, t.y, (t.z || 0) + 8], [1, .78, .36], 20);
    AU.sfx("give"); GAME.onWeight("give", t);
    if (e.form === "stone" && e.tail < 6) this.setForm("normal");
    if (t.type === "lantern") RD.cam.shake = 1;
  },
  setForm(f) {
    const e = this.e, was = e.form; e.form = f;
    if (f === "stone") { AU.sfx("stone"); RD.cam.shake = 3; FX.burst("dust", e.x, e.y, e.z, 14, { life: .7, c: [.6, .58, .55], speed: .8, up: .4, drag: 3, a: .8 }); STORY.bark("stone"); }
    if (f === "leaf") { AU.sfx("leaf"); FX.burst("leaf", e.x, e.y, e.z + 10, 10, { life: 2, c: [.5, .66, .3], speed: .6, up: .6, g: 20 }); STORY.bark("leaf"); }
    if (f === "normal" && was === "stone") { AU.sfx("unstone"); FX.burst("dust", e.x, e.y, e.z, 8, { life: .5, c: [.6, .58, .55], speed: .6, up: .3, drag: 3, a: .7 }); }
  },
  /* ---------------- drawing ---------------- */
  draw() {
    const e = this.e; if (!e || e.hidden) return;
    const spd = hyp(e.vx, e.vy), moving = spd > 4 && e.form !== "stone";
    const ph = moving ? (e.dist / (e.run ? 22 : 18)) % 1 : 0;
    const step = moving ? Math.sin(ph * TAU) : 0, bob = moving ? (Math.abs(Math.sin(ph * TAU)) > .7 ? -1 : 0) : (Math.sin(GAME.t * 2) > .8 ? -0 : 0);
    let eyes = e.blink < 0 ? "closed" : "open", mouth = "idle";
    if (e.expr) ({ eyes = eyes, mouth = mouth } = PL.EXPR[e.expr] || {});
    if (e.form === "stone") { eyes = "closed"; mouth = "flat"; }
    const arms = e.stack.length ? "idle" : moving ? "swing" : (e.expr === "count" ? "count" : "idle");
    const s = TZA.compose({ f: e.face, eyes, mouth, step, bob, arms });
    // the tail: behind her; it glows with the weight it holds
    const td = e.face === "side" ? -1 : 1, tx = e.face === "side" ? 10 : e.face === "back" ? 16 : 21, ty = e.face === "back" ? 30 : 31 + bob;
    TAIL.draw(s, tx, ty, td, GAME.t * (moving ? 1.8 : 1), { z: e.face === "back" ? 12 : .4, a0: e.face === "back" ? Math.PI / 2 + .5 : e.face === "side" ? undefined : -.25, lift: moving ? .4 : 0, droop: e.form === "stone" ? 2 : 0 });
    if (e.form === "stone") PL.petrify(s);
    if (e.tail > 0 && e.form !== "stone") PL.tailGlow(s, e.tail);
    TZA.finish(s);
    const r = RD.dynSlot(0, s, 16, 43);
    const flip = e.face === "side" && e.flip;
    const wob = e.wobble > 0 ? (e.wobble -= GAME.dt, Math.round(Math.sin(GAME.t * 60) * 1)) : 0;
    RD.charSprite({ x: e.x + wob, y: e.y, z: e.z + e.hop, r, flip, bulge: 1 });
    RD.blob(e.x, e.y, e.z, 13, 5, e.hop ? .4 : .85);
    RD.bend(e.x, e.y, 12, 1);
    // the stack: logs and stones lashed to the back-frame
    if (e.stack.length) {
      const behind = e.face === "back" ? 3 : -3; let h = 30 + (e.face === "side" ? 0 : 0);
      for (let i = 0; i < e.stack.length; i++) {
        const it = e.stack[i], K = ITEM[it.kind], rr = ATLAS.rects[K.rect];
        const off = Math.round(Math.sin(e.theta) * (h - 26) * 1.1) + (e.face === "side" ? (e.flip ? 4 : -4) : 0);
        RD.sprite({ x: e.x + off, y: e.y + behind, z: e.z + e.hop + h + bob, r: rr, tint: it.w === 0 ? [1.1, 1.08, 1.02, 0] : T4, flip: e.flip && e.face === "side" });
        h += K.hgt;
      }
    }
    // the light she gives off when she holds weight, and the glow of a pale night
    if (e.tail > 0) RD.light(e.x + (e.flip ? 8 : -8), e.y, e.z + 12, 18 + e.tail * 6, .5 * e.tail / 6 + .2, .32 * e.tail / 6 + .1, .08);
    if (e.emote) UI.emote(e);
  },
  EXPR: { smug: { eyes: "smug", mouth: "fang" }, grin: { eyes: "happy", mouth: "fang" }, surprised: { eyes: "open", mouth: "o" }, sad: { eyes: "half", mouth: "idle" }, angry: { eyes: "half", mouth: "open" }, shout: { eyes: "closed", mouth: "open" }, soft: { eyes: "half", mouth: "smile" }, thinking: { eyes: "half", mouth: "idle" }, worried: { eyes: "open", mouth: "idle" }, count: { eyes: "open", mouth: "o" } },
  petrify(s) { // recolour into a little moss-flecked stone statue
    for (let i = 0; i < s.w * s.h; i++) { const q = i * 4; if (!s.c[q + 3]) continue; const l = (s.c[q] * .3 + s.c[q + 1] * .59 + s.c[q + 2] * .11) / 255; const st = PAL.stone[clamp(Math.round(l * 6.5), 0, 6)]; s.c[q] = st[0]; s.c[q + 1] = st[1]; s.c[q + 2] = st[2]; s.m[i] = MAT.STONE; if (hash2(i, 7, 3) < .04) { const m = PAL.moss[3]; s.c[q] = m[0]; s.c[q + 1] = m[1]; s.c[q + 2] = m[2]; } }
  },
  tailGlow(s, n) { // fur warms toward amber with each unit she carries
    const k = n / 6; for (let i = 0; i < s.w * s.h; i++) { if (s.m[i] !== MAT.FUR || !s.c[i * 4 + 3]) continue; const x = i % s.w, y = (i / s.w) | 0; if (y < 26) continue; const q = i * 4; s.c[q] = Math.min(255, s.c[q] + 40 * k); s.c[q + 1] = Math.min(255, s.c[q + 1] + 18 * k); s.e[i] = Math.round(2 * k); }
  },
};
