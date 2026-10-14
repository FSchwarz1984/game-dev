/* =====================================================================
   FX — pixel particles and the small life of the mountain: dust in the
   sun, fireflies at night, cedar needles and maple seeds on the wind,
   dragonflies over water, spray at the fall, footstep puffs, the gold
   thread of borrowed weight, the pale motes of the Far.
   ===================================================================== */
"use strict";
const FX = {
  P: [], max: 4500, amb: { t: 0 }, falls: [],
  spawn(type, x, y, z, o = {}) {
    if (this.P.length >= this.max) return null;
    const p = { type, x, y, z, vx: o.vx || 0, vy: o.vy || 0, vz: o.vz || 0, t: 0, life: o.life || 1, size: o.size || 1, c: o.c || [1, 1, 1], a: o.a ?? 1, g: o.g || 0, drag: o.drag ?? 0,
      fade: o.fade ?? .3, blink: o.blink || 0, ph: Math.random() * TAU, tx: o.tx, ty: o.ty, tz: o.tz, home: o.home || 0, wob: o.wob || 0, add: !!o.add, light: o.light || 0, ground: o.ground ?? true };
    this.P.push(p); return p;
  },
  burst(type, x, y, z, n, o = {}) {
    for (let i = 0; i < n; i++) { const a = Math.random() * TAU, sp = (o.speed || 1) * (.4 + Math.random() * .6);
      this.spawn(type, x + (Math.random() - .5) * (o.spread || 2), y + (Math.random() - .5) * (o.spread || 2) * .6, z + (Math.random() - .5) * (o.spreadZ || 1), Object.assign({}, o, {
        vx: Math.cos(a) * sp * 30 + (o.vx || 0), vy: Math.sin(a) * sp * 18 + (o.vy || 0), vz: (Math.random() * .6 + .4) * (o.up ?? 1) * 40 * (o.speed || 1) + (o.vz || 0),
        life: (o.life || 1) * (.6 + Math.random() * .6), c: o.cs ? o.cs[(Math.random() * o.cs.length) | 0] : o.c })); }
  },
  // a thread of motes from one point to another (weight being borrowed or lent)
  stream(from, to, c, n = 24) {
    for (let i = 0; i < n; i++) { const d = i / n * .35; this.spawn("mote", from[0] + (Math.random() - .5) * 6, from[1] + (Math.random() - .5) * 4, from[2] + Math.random() * 8, { life: .5 + d, c, size: 1, add: true,
      tx: to[0], ty: to[1], tz: to[2], home: 5 + Math.random() * 3, wob: 1, vz: Math.random() * 40, a: 1, fade: .2 }); }
  },
  update(dt) {
    const P = this.P;
    for (let i = P.length - 1; i >= 0; i--) {
      const p = P[i]; p.t += dt; if (p.t >= p.life) { P[i] = P[P.length - 1]; P.pop(); continue; }
      if (p.home) { const k = Math.min(1, p.home * dt * (.5 + p.t * 2)); p.vx = lerp(p.vx, (p.tx - p.x) * 5, k); p.vy = lerp(p.vy, (p.ty - p.y) * 5, k); p.vz = lerp(p.vz, (p.tz - p.z) * 5, k); }
      if (p.wob) { p.vx += Math.sin(p.t * 9 + p.ph) * p.wob * dt * 90; p.vy += Math.cos(p.t * 7 + p.ph) * p.wob * dt * 60; }
      p.vz -= p.g * dt; if (p.drag) { const d = Math.exp(-p.drag * dt); p.vx *= d; p.vy *= d; p.vz *= d; }
      p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
      if (p.type === "leaf" || p.type === "seed" || p.type === "petal") { p.vx += Math.sin(p.t * 2.6 + p.ph) * dt * 30; const gz = WORLD.heightAt(p.x, p.y); if (p.z < gz + .5) { p.z = gz + .5; p.vx = p.vy = p.vz = 0; p.g = 0; if (!p.landed) { p.landed = true; p.life = Math.min(p.life, p.t + 3); } } }
      else if (p.type === "rain") { const gz = Math.max(WORLD.heightAt(p.x, p.y), WORLD.waterAt(p.x, p.y)); if (p.z < gz) { p.t = p.life; if (Math.random() < .3) this.spawn("splash", p.x, p.y, gz + 1, { life: .2, c: [.8, .86, .95], a: .6, vz: 18, g: 200 }); continue; } }
      else if (p.ground && p.g > 0) { const gz = Math.max(WORLD.heightAt(p.x, p.y), WORLD.waterAt(p.x, p.y)); if (p.z < gz) { if (p.type === "splash" || p.type === "rain") { p.t = p.life; continue; } p.z = gz; p.vz *= -.25; p.vx *= .5; p.vy *= .5; } }
    }
    for (const f of this.falls) f.t = (f.t || 0) + dt;
  },
  draw() {
    for (const p of this.P) {
      const k = p.t / p.life; let a = p.a * (k < .1 ? k / .1 : 1) * (k > 1 - p.fade ? (1 - k) / p.fade : 1);
      if (p.blink) a *= .3 + .7 * Math.max(0, Math.sin(p.t * p.blink + p.ph));
      RD.part(p.x, p.y, p.z, Math.max(1, Math.round(p.size)), p.c[0], p.c[1], p.c[2], a, p.add);
      if (p.light && a > .3) RD.light(p.x, p.y, p.z, p.light, p.c[0] * .45 * a, p.c[1] * .45 * a, p.c[2] * .45 * a);
    }
    // waterfalls: a sheet of falling streaks drawn as particles each frame
    for (const f of this.falls) this.drawFall(f);
  },
  drawFall(f) {
    const c = RD.cam; if (f.x1 < c.vx0 - 20 || f.x0 > c.vx1 + 20) return;
    const t = f.t || 0, H = f.top - f.bot;
    for (let x = Math.floor(f.x0); x <= f.x1; x++) {
      const s = hash2(x, 3, 9), sp = 70 + s * 50;
      for (let k = 0; k < 3; k++) { const ph = fract(t * sp / H + s + k / 3); const z = f.top - ph * H; const lit = hash2(x, k, 2) > .5;
        RD.part(x, f.y, z, 1, lit ? .92 : .66, lit ? .97 : .8, 1, .9); RD.part(x, f.y, z - 2, 1, .55, .7, .82, .7); RD.part(x, f.y, z - 4, 1, .5, .64, .76, .6); }
    }
    if (Math.random() < .5) this.spawn("mist", lerp(f.x0, f.x1, Math.random()), f.y + 6, f.bot + 2, { life: 2.4, c: [.9, .95, 1], a: .35, size: 2, vx: (Math.random() - .5) * 8, vy: 6 + Math.random() * 8, vz: 8 + Math.random() * 10, drag: .6, fade: .6 });
    if (Math.random() < .7) this.spawn("splash", lerp(f.x0, f.x1, Math.random()), f.y + 3, f.bot + 1, { life: .6, c: [.94, .98, 1], a: .9, vx: (Math.random() - .5) * 40, vy: 10 + Math.random() * 30, vz: 30 + Math.random() * 50, g: 260 });
  },
  /* ambient life around the camera */
  ambient(dt, env) {
    const c = RD.cam, A = this.amb; A.t += dt;
    const x0 = c.vx0 - 20, x1 = c.vx1 + 20, y0 = c.vy0, y1 = c.vy1 + 120;
    const rx = () => lerp(x0, x1, Math.random()), ry = () => lerp(y0, y1, Math.random());
    const day = 1 - env.night, wind = env.wind;
    // motes drifting in the sun
    if (day > .5 && Math.random() < dt * 9) { const x = rx(), y = ry(), gz = WORLD.heightAt(x, y); if (WORLD.nearAt(x, y) > .5) this.spawn("dust", x, y, gz + 6 + Math.random() * 40, { life: 5 + Math.random() * 4, c: [1, .96, .8], a: .55, vx: wind[0] * 6 + (Math.random() - .5) * 2, vy: (Math.random() - .5) * 2, vz: .4, wob: .03, fade: .4, add: true }); }
    // fireflies over grass and water at night
    if (env.night > .5 && Math.random() < dt * 7) { const x = rx(), y = ry(); const wet = WORLD.waterAt(x, y) > -500 || WORLD.matAt(x, y) === 8 || WORLD.matAt(x, y) === 6;
      if (WORLD.nearAt(x, y) > .4 && (wet || Math.random() < .35)) { const gz = Math.max(WORLD.heightAt(x, y), WORLD.waterAt(x, y)); this.spawn("firefly", x, y, gz + 4 + Math.random() * 22, { life: 6 + Math.random() * 6, c: [.8, 1, .42], size: 1, a: 1, wob: .12, blink: 2 + Math.random() * 2, light: 26, fade: .3, add: true }); } }
    // cedar needles, maple keys and leaves on the wind
    if (Math.random() < dt * (1.4 + wind[2] * 4)) { const x = rx(), y = ry(), gz = WORLD.heightAt(x, y); const forest = WD.zones.cedarZone(x, y);
      this.spawn("leaf", x, y, gz + 50 + Math.random() * 60, { life: 9, c: forest ? [.52, .34, .2] : (Math.random() < .5 ? [.42, .58, .26] : [.6, .5, .24]), vx: wind[0] * 14, vy: wind[1] * 10, vz: -9, g: 0, fade: .2 }); }
    // dragonflies over the stream and pond by day
    if (day > .5 && Math.random() < dt * .6) { const x = rx(), y = ry(); if (WORLD.waterAt(x, y) > -500) { const gz = WORLD.waterAt(x, y); this.spawn("dfly", x, y, gz + 12, { life: 5, c: [.3, .5, .85], size: 1, a: 1, vx: (Math.random() - .5) * 60, vy: (Math.random() - .5) * 40, wob: 2.6, fade: .2 }); } }
    // pale motes rising wherever the Far has eaten into the world
    if (Math.random() < dt * 14) { const x = rx(), y = ry(); const n = WORLD.nearAt(x, y); if (n < .6) { const gz = WORLD.heightAt(x, y); this.spawn("farmote", x, y, gz + Math.random() * 10, { life: 4 + Math.random() * 3, c: [.78, .85, 1], a: .7 * (1 - n), vz: 6 + Math.random() * 6, vx: (Math.random() - .5) * 4, wob: .05, fade: .5, add: true }); } }
    // rain
    if (env.rain > 0) { const n = Math.floor(env.rain * 220 * dt * 6); for (let i = 0; i < n; i++) { const x = rx(), y = ry(), gz = WORLD.heightAt(x, y); this.spawn("rain", x, y, gz + 60 + Math.random() * 40, { life: 1, c: [.7, .78, .9], a: .55, vx: wind[0] * 30, vz: -260, g: 0, fade: .1 }); }
      if (Math.random() < env.rain) { const x = rx(), y = ry(), gz = Math.max(WORLD.heightAt(x, y), WORLD.waterAt(x, y)); this.spawn("splash", x, y, gz + 1, { life: .25, c: [.8, .86, .95], a: .7, vz: 20, g: 200 }); } }
  },
};
