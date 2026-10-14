/* =====================================================================
   gfx/particles — pixel particles and the small life of the mountain:
   dust in the sun, fireflies at night, camphor leaves drifting down,
   waterfall spray and mist, hearth and kiln smoke, insects over water,
   the pale motes of the Far. Ported from legacy/v0.1/src/fx.js.
   Units: world px (X east, Y south, Z up). Emitters come from the map
   (map.render.emitters) and run around the camera.
   ===================================================================== */

const TAU = Math.PI * 2;
const lerp = (a, b, t) => a + (b - a) * t;

export class Particles {
  constructor(max = 5000) { this.P = []; this.max = max; this.emitters = []; this.groundZ = () => 0; this.scale = 1; this.t = 0; }
  setMap(groundZ, emitters) { this.groundZ = groundZ || (() => 0); this.emitters = emitters || []; }
  spawn(type, x, y, z, o = {}) {
    if (this.P.length >= this.max) return null;
    const p = {
      type, x, y, z, vx: o.vx || 0, vy: o.vy || 0, vz: o.vz || 0, t: 0, life: o.life || 1, size: o.size || 1, c: o.c || [1, 1, 1], a: o.a ?? 1,
      g: o.g || 0, drag: o.drag ?? 0, fade: o.fade ?? 0.3, blink: o.blink || 0, ph: Math.random() * TAU, wob: o.wob || 0, add: !!o.add,
      light: o.light || 0, ground: o.ground ?? true, grow: o.grow || 0, flutter: o.flutter || 0, cs: o.cs,
    };
    this.P.push(p); return p;
  }
  burst(type, x, y, z, n, o = {}) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU, sp = (o.speed || 1) * (0.4 + Math.random() * 0.6);
      this.spawn(type, x + (Math.random() - 0.5) * (o.spread || 2), y + (Math.random() - 0.5) * (o.spread || 2) * 0.6, z + (Math.random() - 0.5) * (o.spreadZ || 1), Object.assign({}, o, {
        vx: Math.cos(a) * sp * 30 + (o.vx || 0), vy: Math.sin(a) * sp * 18 + (o.vy || 0), vz: (Math.random() * 0.6 + 0.4) * (o.up ?? 1) * 40 * (o.speed || 1) + (o.vz || 0),
        life: (o.life || 1) * (0.6 + Math.random() * 0.6), c: o.cs ? o.cs[(Math.random() * o.cs.length) | 0] : o.c,
      }));
    }
  }
  update(dt, env, view) {
    this.t += dt; const P = this.P, gz = this.groundZ;
    for (let i = P.length - 1; i >= 0; i--) {
      const p = P[i]; p.t += dt; if (p.t >= p.life) { P[i] = P[P.length - 1]; P.pop(); continue; }
      if (p.wob) { p.vx += Math.sin(p.t * 9 + p.ph) * p.wob * dt * 90; p.vy += Math.cos(p.t * 7 + p.ph) * p.wob * dt * 60; }
      p.vz -= p.g * dt; if (p.drag) { const d = Math.exp(-p.drag * dt); p.vx *= d; p.vy *= d; p.vz *= d; }
      if (p.flutter) { p.vx += Math.sin(p.t * 2.4 + p.ph) * dt * 28 * p.flutter; p.vz += Math.cos(p.t * 3.1 + p.ph) * dt * 6 * p.flutter; }
      p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
      if (p.grow) p.size += p.grow * dt;
      if (p.type === 'leaf' || p.type === 'petal') {
        const g = gz(p.x, p.y); if (p.z < g + 0.5) { p.z = g + 0.5; p.vx = p.vy = p.vz = 0; p.g = 0; p.flutter = 0; if (!p.landed) { p.landed = true; p.life = Math.min(p.life, p.t + 4); } }
      } else if (p.ground && p.g > 0) {
        const g = gz(p.x, p.y); if (p.z < g) { if (p.type === 'splash' || p.type === 'spray') { p.t = p.life; continue; } p.z = g; p.vz *= -0.25; p.vx *= 0.5; p.vy *= 0.5; }
      }
    }
    if (view) this.ambient(dt, env, view);
  }
  /** emitters around the camera; view = {x0, y0, x1, y1} in world-screen px */
  ambient(dt, env, v) {
    const day = 1 - env.night, wind = env.wind;
    const inView = (x, y, z, m = 40) => x > v.x0 - m && x < v.x1 + m && (y - z) > v.y0 - m && (y - z) < v.y1 + m;
    for (const e of this.emitters) {
      if (e.night && env.night < 0.5) continue; if (e.day && day < 0.5) continue;
      if (e.area) { const A = e.area; if (A.x1 < v.x0 - 60 || A.x0 > v.x1 + 60 || A.y1 - (A.z0 || 0) < v.y0 - 200 || A.y0 - (A.z1 || 0) > v.y1 + 120) continue; }
      const rate = (e.rate || 1) * (e.windK ? 1 + wind[2] * e.windK : 1) * (e.rateK || 1);
      let n = rate * dt; while (n > 0) {
        if (n < 1 && Math.random() > n) break; n -= 1;
        this.emit(e, env, wind, inView);
      }
    }
  }
  emit(e, env, wind, inView) {
    const R = Math.random; const A = e.area;
    const ax = A ? lerp(A.x0, A.x1, R()) : e.x, ay = A ? lerp(A.y0, A.y1, R()) : e.y;
    switch (e.type) {
      case 'leaves': { const z = lerp(e.z0, e.z1, R()); if (!inView(ax, ay, z, 120)) return; const cs = e.colors;
        this.spawn('leaf', ax, ay, z, { life: 14, c: cs[(R() * cs.length) | 0], vx: wind[0] * 10 + (R() - 0.5) * 6, vy: wind[1] * 6, vz: -8 - R() * 5, flutter: 1, fade: 0.15, size: R() < 0.3 ? 2 : 1 }); break; }
      case 'dust': { const g = this.groundZ(ax, ay); const z = g + 6 + R() * 60; if (!inView(ax, ay, z)) return;
        this.spawn('dust', ax, ay, z, { life: 5 + R() * 4, c: [1, 0.95, 0.78], a: 0.5, vx: wind[0] * 5 + (R() - 0.5) * 2, vy: (R() - 0.5) * 2, vz: 0.6, wob: 0.03, fade: 0.4, add: true }); break; }
      case 'fireflies': { const g = this.groundZ(ax, ay); const z = g + 4 + R() * 26; if (!inView(ax, ay, z)) return;
        this.spawn('firefly', ax, ay, z, { life: 6 + R() * 6, c: [0.78, 1, 0.42], size: 1, a: 1, wob: 0.12, blink: 1.6 + R() * 1.6, light: 22, fade: 0.3, add: true }); break; }
      case 'mist': { const z = lerp(e.z0 ?? 0, e.z1 ?? 20, R()); if (!inView(ax, ay, z, 80)) return;
        this.spawn('mist', ax, ay, z, { life: 3 + R() * 2.5, c: e.color || [0.9, 0.95, 1], a: e.alpha ?? 0.3, size: 2 + (R() * 2 | 0), vx: (R() - 0.5) * 8 + wind[0] * 4, vy: e.vy ?? 4 + R() * 6, vz: e.vz ?? 6 + R() * 10, drag: 0.5, fade: 0.6, grow: 0.3 }); break; }
      case 'spray': { if (!inView(ax, ay, e.z || 0)) return;
        this.spawn('spray', ax, ay, (e.z || 0) + 1, { life: 0.7, c: [0.94, 0.98, 1], a: 0.9, vx: (R() - 0.5) * 40, vy: 8 + R() * 26, vz: 26 + R() * 46, g: 240 }); break; }
      case 'smoke': { if (!inView(ax, ay, e.z || 0, 200)) return;
        this.spawn('smoke', ax + (R() - 0.5) * 2, ay, e.z || 0, { life: e.life || 6, c: e.color || [0.62, 0.62, 0.64], a: e.alpha ?? 0.35, size: 1, grow: 0.5, vx: wind[0] * 10 + (R() - 0.5) * 3, vy: wind[1] * 3, vz: 12 + R() * 6, drag: 0.15, fade: 0.6, wob: 0.02 }); break; }
      case 'insects': { const g = this.groundZ(ax, ay); if (!inView(ax, ay, g + 10)) return;
        this.spawn('fly', ax, ay, g + 8 + R() * 10, { life: 4, c: e.color || [0.3, 0.5, 0.85], size: 1, a: 1, vx: (R() - 0.5) * 50, vy: (R() - 0.5) * 30, wob: 2.4, fade: 0.2, ground: false }); break; }
      case 'farmotes': { const g = this.groundZ(ax, ay); if (!inView(ax, ay, g)) return;
        this.spawn('farmote', ax, ay, g + R() * 10, { life: 4 + R() * 3, c: [0.8, 0.86, 1], a: 0.65, vz: 5 + R() * 6, vx: (R() - 0.5) * 4, wob: 0.05, fade: 0.5, add: true, ground: false }); break; }
    }
  }
  /** push into the renderer's per-frame lists */
  draw(R) {
    for (const p of this.P) {
      const k = p.t / p.life; let a = p.a * (k < 0.1 ? k / 0.1 : 1) * (k > 1 - p.fade ? (1 - k) / p.fade : 1);
      if (p.blink) a *= 0.25 + 0.75 * Math.max(0, Math.sin(p.t * p.blink + p.ph));
      if (p.type === 'smoke' || p.type === 'mist') { // soft puffs: a dithered cluster of pixels
        const s = Math.max(1, Math.round(p.size)); R.part(p.x, p.y, p.z, s, p.c[0], p.c[1], p.c[2], a * 0.8, false);
        continue;
      }
      R.part(p.x, p.y, p.z, Math.max(1, Math.round(p.size)), p.c[0], p.c[1], p.c[2], a, p.add);
      if (p.light && a > 0.3) R.pointLight(p.x, p.y, p.z, p.light, p.c[0] * 0.4 * a, p.c[1] * 0.4 * a, p.c[2] * 0.4 * a);
    }
  }
}
