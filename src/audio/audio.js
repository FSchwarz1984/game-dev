/* =====================================================================
   AUDIO — procedural WebAudio engine for 「ツヅラ —遠囃子—」
   ===================================================================== */
// Pure WebAudio synthesis: no samples, no libs. Ported from v0.1 (legacy/v0.1/src/audio.js),
// which the user rated well overall. Exports one object (AU). Every public method is a silent
// no-op until AU.init() has succeeded (call it from a user gesture).
// Changes from v0.1: the wind "creak" event is removed — its sawtooth-through-resonator synthesis
// read as an electronic buzz near the stream in strong wind (docs/knowledge/05). Natural ambience
// should move to CC0 field recordings; synthesis stays for music and magic.
export const AU = (() => {

/* =====================================================================
   CORE — state, math helpers, guarded AudioParam automation
   ===================================================================== */
let ctx = null, ready = false, SR = 44100, timer = 0;
const TICK_MS = 25;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
// ?audiodebug=1 reports errors that are otherwise swallowed (the game must never stop for audio).
const AUDIO_DEBUG = typeof location !== "undefined" && /[?&]audiodebug=1/.test(location.search);
const rnd = (a = 0, b = 1) => a + Math.random() * (b - a);
const rint = (a, b) => Math.floor(rnd(a, b + 1));
const pick = (a) => a[(Math.random() * a.length) | 0];
const chance = (p) => Math.random() < p;
const num = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);
const u01 = (v, d = 0) => clamp(num(v, d), 0, 1);
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const expMap = (a, b, t) => a * Math.pow(b / a, clamp(t, 0, 1));
const nyq = (f) => clamp(f, 10, SR * 0.45);

// 陽音階 (yo scale) on D — D E G A B — across octaves, plus diatonic shifting.
const YO = [];
for (let o = 26; o <= 98; o += 12) for (const s of [0, 2, 5, 7, 9]) YO.push(o + s);
const yoIdx = (m) => { let i = 0; while (i < YO.length - 1 && YO[i + 1] <= m) i++; return i; };
const dshift = (m, k) => YO[clamp(yoIdx(m) + k, 0, YO.length - 1)];

// World state mirrored from update(); sane defaults so ambience works before the first frame.
const S = {
  tod: 12, rain: 0, wind: 0.3, near: 1, water: 0, fall: 0, heavy: 0,
  indoor: false, cinematic: false, paused: false, L: { x: 0, y: 0 },
  biome: { forest: 1, bamboo: 0, stream: 0, meadow: 0, shrine: 0 },
};

// Change-detected setTargetAtTime for persistent params (cheap to call every frame).
const lastTgt = new WeakMap();
function tgt(p, v, tc = 0.12, t) {
  if (!p || !Number.isFinite(v)) return;
  const prev = lastTgt.get(p);
  if (prev !== undefined && Math.abs(prev - v) <= 1e-4 + Math.abs(v) * 0.003) return;
  lastTgt.set(p, v);
  try { p.setTargetAtTime(v, t === undefined ? ctx.currentTime : t, Math.max(0.004, tc)); } catch (e) { /* ignore */ }
}
function holdAt(p, t) { // freeze automation at t (cancel the future) before re-shaping a param
  try { if (p.cancelAndHoldAtTime) p.cancelAndHoldAtTime(t); else p.cancelScheduledValues(t); } catch (e) { /* ignore */ }
  lastTgt.delete(p);
}
// percussive envelope: 0 → peak (linear, a) → exponential decay over d
function perc(p, t, a, peak, d) {
  if (!(peak > 0)) return;
  p.setValueAtTime(0, t);
  p.linearRampToValueAtTime(peak, t + a);
  p.exponentialRampToValueAtTime(peak * 1e-4 + 1e-7, t + a + d);
}
// swell envelope: 0 → peak over a, hold, release (setTarget) over r
function swell(p, t, a, peak, hold, r) {
  p.setValueAtTime(0, t);
  p.linearRampToValueAtTime(peak, t + a);
  p.setValueAtTime(peak, t + a + hold);
  p.setTargetAtTime(0, t + a + hold, Math.max(0.005, r / 4));
}
// granular envelope (crunch, rustle, grit): n irregular micro-bursts over span seconds
function grains(p, t, n, span, peak) {
  p.setValueAtTime(0, t);
  let tt = t;
  for (let i = 0; i < n; i++) {
    const pk = peak * rnd(0.35, 1) * (1 - (i / (n + 1)) * 0.5);
    p.linearRampToValueAtTime(pk, tt + 0.002);
    tt += (span / n) * rnd(0.5, 1.5);
    p.exponentialRampToValueAtTime(pk * 0.05 + 1e-6, tt);
  }
  p.linearRampToValueAtTime(0, tt + 0.01);
  return tt + 0.01;
}

/* =====================================================================
   BUFFERS — pooled noise loops and generated impulse responses
   ===================================================================== */
const NZ = {};
function makeNoise(sec, kind) {
  const len = Math.floor(SR * sec), F = 2048, b = ctx.createBuffer(2, len, SR);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    if (kind === "white") { for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * 0.7; continue; }
    const x = new Float32Array(len + F);
    let b0 = 0, b1 = 0, b2 = 0, br = 0;
    for (let i = 0; i < len + F; i++) {
      const w = Math.random() * 2 - 1;
      if (kind === "pink") {
        b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
        x[i] = (b0 + b1 + b2 + w * 0.1848) * 0.2;
      } else { br = (br + 0.02 * w) / 1.02; x[i] = br * 3.2; }
    }
    for (let i = 0; i < len; i++) d[i] = i < F ? x[i] * (i / F) + x[len + i] * (1 - i / F) : x[i]; // seamless loop
  }
  return b;
}
// One channel of a decaying noise IR whose lowpass darkens over time. o: {pre, att, lp0, lp1, er}
function irChan(b, sec, o, c) {
  const len = b.length, pre = Math.floor((o.pre || 0) * SR), n = len - pre, d = b.getChannelData(c);
  const kEnv = Math.exp(-6.4 / (sec * 0.92 * SR)), kAtt = o.att ? Math.exp(-1 / (o.att * SR)) : 0;
  let y1 = 0, y2 = 0, k = 0, env = 1, att = 1;
  for (let i = 0; i < n; i++) {
    if ((i & 63) === 0) k = Math.exp((-2 * Math.PI * o.lp0 * Math.pow(o.lp1 / o.lp0, i / n)) / SR);
    const w = Math.random() * 2 - 1;
    y1 = w + k * (y1 - w); y2 = y1 + k * (y2 - y1);
    d[pre + i] = y2 * env * (1 - i / n) * (1 - att);
    env *= kEnv; att *= kAtt;
  }
  for (let j = 0; j < (o.er || 0); j++) { // sparse early reflections (tree trunks, stones)
    const p = pre + Math.floor(rnd(0.004, 0.075) * SR);
    if (p < len) d[p] += rnd(-0.35, 0.35) * (1 - (p - pre) / (0.09 * SR));
  }
}

/* =====================================================================
   MIXER — buses → master → hush → filters → compressor → destination
   ===================================================================== */
const BUS = {};
const VOL = { master: 0.85, music: 0.75, amb: 0.85, sfx: 0.85, voice: 0.75, far: 0.9 };
let master, hush, waveLP, pauseLP, pauseG, comp, outG, roomIn, farIn;
const G = (v = 1) => { const g = ctx.createGain(); g.gain.value = v; return g; };
const BQ_ = (type, f, q, gdb) => {
  const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = nyq(f);
  if (q !== undefined) b.Q.value = q;
  if (gdb !== undefined) b.gain.value = gdb;
  return b;
};
function chain(...n) { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; }
function mkBus(name, room, far) {
  const v = VOL[name], b = {
    inp: G(), vol: G(v), duck: G(), wet: G(), wvol: G(v), wduck: G(), fwet: G(), fvol: G(v), fduck: G(),
  };
  chain(b.inp, b.vol, b.duck, master);
  if (room > 0) chain(b.duck, G(room), roomIn);
  if (far > 0) chain(b.duck, G(far), farIn);
  chain(b.wet, b.wvol, b.wduck, roomIn);
  chain(b.fwet, b.fvol, b.fduck, farIn);
  b.vols = [b.vol.gain, b.wvol.gain, b.fvol.gain];
  b.ducks = [b.duck.gain, b.wduck.gain, b.fduck.gain];
  BUS[name] = b;
}
function buildGraph() {
  master = G(VOL.master); hush = G(1);
  waveLP = BQ_("lowpass", 20000, 0); pauseLP = BQ_("lowpass", 20000, 0); pauseG = G(1);
  comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -15; comp.knee.value = 12; comp.ratio.value = 3;
  comp.attack.value = 0.006; comp.release.value = 0.28;
  outG = G(0.55); // Chrome's compressor adds ~+3.6 dB makeup; trim it back (net ≈ −1.6 dB, clip needs > +20 dBFS in)
  chain(master, hush, waveLP, pauseLP, pauseG, comp, outG, ctx.destination);
  // Reverbs start empty (silent) and receive their generated IRs from the background queue,
  // keeping init() well under budget: room ≈ 2.8 s forest air, far ≈ 5.5 s dark, slow-blooming.
  const cv = (sec, o) => {
    const c = ctx.createConvolver(), b = ctx.createBuffer(2, Math.floor(sec * SR), SR);
    c.normalize = true;
    BQ.unshift(() => irChan(b, sec, o, 0), () => irChan(b, sec, o, 1), () => { c.buffer = b; });
    return c;
  };
  roomIn = G(); chain(roomIn, cv(2.8, { pre: 0.012, lp0: 9000, lp1: 2200, er: 14 }), G(0.7), master);
  farIn = G(); chain(farIn, cv(5.5, { pre: 0.07, att: 0.18, lp0: 3800, lp1: 380 }), G(0.85), master);
  mkBus("music", 0.16, 0); mkBus("amb", 0.08, 0); mkBus("sfx", 0.1, 0);
  mkBus("voice", 0.04, 0); mkBus("far", 0, 0.35);
}

/* =====================================================================
   VOICES — short-lived node groups with pooled caps and auto-cleanup
   ===================================================================== */
const POOLS = { sfx: { n: 0, max: 48 }, bg: { n: 0, max: 80 } };
let FLW = null, FIFEW = null; // PeriodicWaves (flute, shinobue)
const VP = {
  g(v = 1) { const n = G(v); this.ns.push(n); return n; },
  f(type, fr, q, gdb) { const n = BQ_(type, fr, q, gdb); this.ns.push(n); return n; },
  p(pan) { const n = ctx.createStereoPanner(); n.pan.value = clamp(num(pan), -1, 1); this.ns.push(n); return n; },
  o(type, fr, t, t1) {
    const n = ctx.createOscillator();
    if (type === "fl" && FLW) n.setPeriodicWave(FLW); else n.type = type === "fl" ? "triangle" : type;
    n.frequency.value = clamp(fr, 1, SR * 0.45); n.start(t); n.stop(Math.max(t1, t + 0.01));
    this.mark(t1); this.ns.push(n); return n;
  },
  n(kind, t, t1, rate = 1) {
    const b = NZ[kind] || NZ.white, n = ctx.createBufferSource();
    n.buffer = b; n.loop = true; n.playbackRate.value = rate;
    n.start(t, Math.random() * (b.duration - 0.1)); n.stop(Math.max(t1, t + 0.01));
    this.mark(t1); this.ns.push(n); return n;
  },
  b(e, t, rate = 1) {
    const n = ctx.createBufferSource(), r = clamp(rate * (e.r || 1), 0.05, 16);
    n.buffer = e.b; n.playbackRate.value = r; n.start(t);
    const end = t + e.b.duration / r + 0.02; n.stop(end);
    this.mark(end); this.ns.push(n); return n;
  },
  mark(t) { if (t > this.end) this.end = t; },
  // route to a bus with spatial info sp {g, pan, d}; wet/fw = room/far sends
  out(bus, sp, lvl, wet = 0, fw = 0) {
    const B = BUS[bus] || BUS.sfx, g = this.g(lvl * sp.g);
    let o = g;
    if (sp.pan) { const p = this.p(sp.pan); g.connect(p); o = p; }
    o.connect(B.inp);
    const w = wet + (sp.d ? (1 - sp.g) * 0.4 : 0);
    if (w > 0.001) { const s = this.g(w); o.connect(s); s.connect(B.wet); }
    if (fw > 0.001) { const s = this.g(fw); o.connect(s); s.connect(B.fwet); }
    return g;
  },
};
function reap(v) {
  const left = v.end - ctx.currentTime;
  setTimeout(() => {
    if (ctx && ctx.state === "running" && v.end - ctx.currentTime > 0.05) { reap(v); return; }
    if (v.done) return;
    v.done = true; v.pool.n--;
    for (const n of v.ns) { try { n.disconnect(); } catch (e) { /* ignore */ } }
    v.ns = null;
  }, Math.min(5000, Math.max(30, left * 1000 + 150)));
}
// Build a voice with fn(v); always reaped, even if fn throws. Returns false if the pool is full.
function play(pool, fn) {
  const P = POOLS[pool] || POOLS.sfx;
  if (!ctx || P.n >= P.max) return false;
  P.n++;
  const v = Object.create(VP);
  v.ns = []; v.end = ctx.currentTime; v.pool = P; v.done = false;
  try { fn(v); } catch (e) { if (AUDIO_DEBUG) console.error('sfx voice', e); }
  reap(v);
  return true;
}
// Spatial helper: {g, pan, d} or null when inaudible.
function spatial(o) {
  if (o && Number.isFinite(o.x) && Number.isFinite(o.y)) {
    const dx = o.x - S.L.x, dy = o.y - S.L.y, d = Math.hypot(dx, dy), g = 1 / (1 + (d / 260) * (d / 260));
    if (g < 0.012) return null;
    return { g, pan: clamp(dx / 320, -1, 1), d };
  }
  return { g: 1, pan: o && Number.isFinite(o.pan) ? clamp(o.pan, -1, 1) : 0, d: 0 };
}
const SP0 = { g: 1, pan: 0, d: 0 };

/* =====================================================================
   BAKERY — cached procedural buffers (plucks, bells, drums, loops)
   ===================================================================== */
const BK = new Map();          // key → {b: AudioBuffer, r: playbackRate correction}
let BSR = 44100;               // sample rate of the buffer currently being baked
const BQ = [];                 // background bake queue (run in small slices by the scheduler)
// div > 1 bakes low-frequency material at SR/div (the source node resamples on playback).
function bake(key, sec, ch, fn, loop, div = 1) {
  let e = BK.get(key);
  if (e) return e;
  BSR = Math.max(8000, SR / div);
  const len = Math.max(256, Math.floor(sec * BSR)), b = ctx.createBuffer(ch, len, BSR);
  e = { b, r: 1 };
  try { const r = fn(b, len); if (r > 0) e.r = r; } catch (err) { /* ignore */ }
  const nf = loop ? 0 : Math.min(len >> 2, Math.floor(BSR * 0.03)); // one-shots fade out; loops stay seamless
  for (let c = 0; c < ch; c++) { const d = b.getChannelData(c); for (let i = 0; i < nf; i++) d[len - 1 - i] *= i / nf; }
  BK.set(key, e);
  BSR = SR;
  return e;
}
function bakeTick() {
  const t0 = performance.now();
  while (BQ.length && performance.now() - t0 < 5) { try { BQ.shift()(); } catch (e) { /* ignore */ } }
}
// Sum of exponentially decaying sines via phasor recursion. parts: [f, amp, tau, attack, phase]
function addPartials(d, parts, start = 0) {
  for (const p of parts) {
    const f = p[0], tau = p[2], A = Math.max(1, (p[3] || 0.002) * BSR);
    if (!(f > 0) || f > BSR * 0.45) continue;
    const w = (2 * Math.PI * f) / BSR, c = Math.cos(w), s = Math.sin(w), k = Math.exp(-1 / (tau * BSR));
    let re = Math.cos(p[4] || 0), im = Math.sin(p[4] || 0), env = p[1];
    const n = Math.min(d.length - start, Math.ceil(tau * BSR * 6.5));
    for (let i = 0; i < n; i++) {
      const r2 = re * c - im * s; im = re * s + im * c; re = r2;
      d[start + i] += im * env * (i < A ? i / A : 1);
      env *= k;
      if ((i & 4095) === 0) { const m = 1 / Math.hypot(re, im); re *= m; im *= m; }
    }
  }
}
// Decaying sine whose pitch falls exponentially f0 → f1 (drums, thumps).
function addChirp(d, f0, f1, tp, amp, tau, start = 0) {
  const n = Math.min(d.length - start, Math.ceil(tau * BSR * 7)), kd = Math.exp(-1 / (tau * BSR)), kp = Math.exp(-1 / (tp * BSR));
  let ph = 0, env = amp, df = f0 - f1;
  for (let i = 0; i < n; i++) {
    ph += (2 * Math.PI * (f1 + df)) / BSR; df *= kp;
    d[start + i] += Math.sin(ph) * env * (i < 24 ? i / 24 : 1); env *= kd;
  }
}
// Decaying noise burst; lp = one-pole coefficient (0 = white), hp = differentiate.
function addNoise(d, amp, tau, lp = 0, hp = false, start = 0) {
  const n = Math.min(d.length - start, Math.ceil(tau * BSR * 7)), kd = Math.exp(-1 / (tau * BSR));
  let env = amp, y = 0, prev = 0;
  for (let i = 0; i < n; i++) {
    const w = Math.random() * 2 - 1;
    y = lp ? y + (w - y) * lp : w;
    let o = y;
    if (hp) { o = y - prev; prev = y; }
    d[start + i] += o * env; env *= kd;
  }
}

/* =====================================================================
   INSTRUMENTS — Karplus–Strong strings, bells, drums, flute, pads
   ===================================================================== */
// Plucked strings, baked per note: koto (long, soft tsume) and shamisen (bright, sawari buzz, bachi).
const KS = {
  koto: { s: 0.3, br: 0.6, pos: 0.18, t60: 3.6, dur: 3.4, buzz: 0, lvl: 0.55 },
  sham: { s: 0.48, br: 0.9, pos: 0.12, t60: 1.3, dur: 1.7, buzz: 0.3, lvl: 0.5 },
};
function ksE(kind, m) {
  m = Math.round(clamp(m, 26, 100));
  const P = KS[kind] || KS.koto, f = mtof(m), hi = clamp((m - 55) / 36, 0, 1);
  const t60 = P.t60 * (1 - 0.5 * hi), dur = P.dur * (1 - 0.4 * hi);
  return bake(kind + m, dur, 1, (b, len) => {
    const d = b.getChannelData(0), N = Math.max(4, Math.floor(SR / f + P.s)), line = new Float32Array(N);
    let y = 0, mx = 1e-9, mean = 0;
    for (let i = 0; i < N; i++) { y += (Math.random() * 2 - 1 - y) * P.br; line[i] = y; }
    const pp = Math.max(1, Math.round(N * P.pos)), ex = line.slice();
    for (let i = 0; i < N; i++) { line[i] = ex[i] - 0.9 * ex[(i + pp) % N]; mean += line[i] / N; }
    for (let i = 0; i < N; i++) { line[i] -= mean; mx = Math.max(mx, Math.abs(line[i])); }
    for (let i = 0; i < N; i++) line[i] /= mx;
    const loss = Math.pow(0.001, 1 / (f * t60)), s = P.s;
    let p = 0, px = 0, py = 0;
    for (let n = 0; n < len; n++) {
      const a = line[p], c = line[p + 1 < N ? p + 1 : 0];
      line[p] = loss * (a + (c - a) * s);
      let o = a;
      if (P.buzz) { o += P.buzz * Math.abs(a); const h = o - px + 0.995 * py; px = o; py = h; o = h; }
      d[n] = o * 0.5;
      if (++p >= N) p = 0;
    }
    if (kind === "sham") { addNoise(d, 0.35, 0.004, 0.5); addChirp(d, 240, 160, 0.02, 0.18, 0.035); }
    else addNoise(d, 0.08, 0.002, 0, true);
    return (f * (N - s)) / SR; // playbackRate correction → exact pitch
  });
}
// Additive bells with beating pairs (stereo: slightly different beat per ear). parts: [ratio, amp, tau, beatHz]
function bellE(key, sec, f0, parts, strike, ch = 2, div = 1) {
  return bake(key, sec, ch, (b) => {
    for (let c = 0; c < ch; c++) {
      const d = b.getChannelData(c), L = [];
      for (const [r, a, tau, bt] of parts) {
        const f = f0 * r * (c ? 1.0004 : 0.9996);
        if (bt) L.push([f, a * 0.55, tau, 0.002, rnd(0, 6)], [f + bt * (c ? 1.15 : 0.87), a * 0.45, tau * 0.93, 0.002, rnd(0, 6)]);
        else L.push([f, a, tau, 0.002, rnd(0, 6)]);
      }
      addPartials(d, L);
      if (strike) strike(d);
    }
  }, false, div);
}
const SND = {
  rin: () => bellE("rin", 4.2, 1174.7, [[1, 0.5, 0.95, 1.7], [2.71, 0.3, 0.5, 2.4], [5.15, 0.14, 0.28, 3.3], [8.3, 0.06, 0.14, 0]], (d) => addNoise(d, 0.06, 0.0015, 0, true)),
  bell: () => bellE("bell", 8, 146.8, [[0.5, 0.32, 3.4, 0.6], [1, 0.42, 2.2, 1.1], [1.19, 0.2, 1.6, 0], [1.5, 0.18, 1.3, 0.8], [2, 0.2, 1.0, 0], [2.66, 0.12, 0.65, 1.4], [3.4, 0.07, 0.4, 0], [4.6, 0.04, 0.25, 0]],
    (d) => { addChirp(d, 95, 60, 0.04, 0.3, 0.07); addNoise(d, 0.12, 0.012, 0.3); }, 2, 4),
  gong: () => bellE("gong", 3.2, 73.4, [[1, 0.5, 1.0, 0.6], [1.48, 0.32, 0.75, 0.9], [2.09, 0.22, 0.5, 1.3], [2.76, 0.13, 0.32, 0], [3.9, 0.07, 0.2, 0]], (d) => addNoise(d, 0.1, 0.01, 0.4), 2, 4),
  glass: () => bellE("glass", 2.2, 2349, [[1, 0.5, 0.45, 2.2], [2.32, 0.24, 0.25, 0], [4.1, 0.1, 0.12, 0], [5.8, 0.04, 0.07, 0]], (d) => addNoise(d, 0.05, 0.001, 0, true)),
  suzu: () => bellE("suzu", 0.35, 3100, [[1, 0.5, 0.03], [1.516, 0.35, 0.025], [2.48, 0.08, 0.012]], (d) => {
    addPartials(d, [[3112, 0.22, 0.028, 0.001], [4690, 0.16, 0.022, 0.001]], Math.floor(0.018 * SR)); // the pellet rattles twice
    addNoise(d, 0.08, 0.001, 0, true);
  }, 1),
  kaneO: () => bellE("kaneO", 0.9, 1480, [[1, 0.35, 0.2], [1.54, 0.3, 0.15], [2.31, 0.24, 0.1], [2.79, 0.2, 0.08], [3.73, 0.12, 0.055], [4.4, 0.08, 0.04]], (d) => addNoise(d, 0.35, 0.0025, 0, true), 1),
  kaneD: () => bellE("kaneD", 0.25, 1480, [[1, 0.3, 0.045], [1.54, 0.28, 0.035], [2.31, 0.22, 0.025], [2.79, 0.18, 0.02], [3.73, 0.1, 0.015]], (d) => addNoise(d, 0.3, 0.002, 0, true), 1),
  shime: () => bake("shime", 0.45, 1, (b) => { const d = b.getChannelData(0); addChirp(d, 560, 400, 0.012, 0.55, 0.06); addChirp(d, 900, 640, 0.01, 0.2, 0.035); addNoise(d, 0.45, 0.004, 0, true); addNoise(d, 0.15, 0.03, 0.3); }),
  taiko: () => bake("taiko", 1.6, 1, (b) => { const d = b.getChannelData(0); addChirp(d, 170, 104, 0.03, 0.75, 0.24); addChirp(d, 280, 170, 0.02, 0.2, 0.1); addNoise(d, 0.3, 0.01, 0.24); }, false, 2),
  odaiko: () => bake("odaiko", 2.6, 1, (b) => { const d = b.getChannelData(0); addChirp(d, 105, 56, 0.05, 0.85, 0.5); addChirp(d, 165, 92, 0.04, 0.25, 0.22); addNoise(d, 0.35, 0.02, 0.12); addNoise(d, 0.06, 0.25, 0.04); }, false, 2),
  knock: () => bellE("knock", 0.4, 520, [[1, 0.55, 0.05], [2.3, 0.3, 0.025], [4.1, 0.14, 0.012]], (d) => { addChirp(d, 190, 120, 0.02, 0.3, 0.04); addNoise(d, 0.25, 0.003, 0.4); }, 1),
  wood: () => bellE("wood", 0.5, 700, [[1, 0.5, 0.065], [2.71, 0.28, 0.03], [5.13, 0.1, 0.014]], (d) => addNoise(d, 0.25, 0.002, 0.5), 1),
  tick: () => bellE("tick", 0.15, 2200, [[1, 0.5, 0.012], [2.62, 0.3, 0.006]], (d) => addNoise(d, 0.3, 0.0012, 0, true), 1),
};
const snd = (k) => BK.get(k) || SND[k]();
function celE(m) {
  m = Math.round(m); const f = mtof(m);
  return bake("cel" + m, 2.4, 1, (b) => addPartials(b.getChannelData(0), [[f, 0.45, 0.5, 0.0015], [2 * f, 0.18, 0.2, 0.001], [3 * f, 0.09, 0.1, 0.001], [4.2 * f, 0.03, 0.05, 0.001]]));
}
function harmE(m) { // koto harmonic (flageolet): pure, glassy, soft attack
  m = Math.round(m); const f = mtof(m);
  return bake("harm" + m, 3, 1, (b) => addPartials(b.getChannelData(0), [[f, 0.5, 0.85, 0.006], [2 * f, 0.06, 0.3, 0.004], [3 * f, 0.025, 0.18, 0.004]]));
}
// One-shot buffer hit into a strip {i}. Returns true if played.
function hit(t, key, vel, st, rate = 1, pool = "bg") {
  const e = typeof key === "string" ? snd(key) : key;
  return play(pool, (v) => { const s = v.b(e, t, rate), g = v.g(vel); s.connect(g); g.connect(st.i); });
}
function pluck(kind, t, m, vel, st, o) {
  const e = ksE(kind, m);
  return play("bg", (v) => {
    const s = v.b(e, t, 1), g = v.g(vel * KS[kind].lvl);
    if (o && o.bend) { // oshide: press the string behind the bridge after the attack
      const r = s.playbackRate, r0 = r.value;
      r.setValueAtTime(r0, t + 0.14); r.linearRampToValueAtTime(r0 * Math.pow(2, o.bend / 12), t + 0.32);
    }
    s.connect(g); g.connect(st.i);
  });
}
const koto = (t, m, d, vel, st, o) => pluck("koto", t, m, vel, st, o);
const sham = (t, m, d, vel, st, o) => pluck("sham", t, m, vel, st, o);
const cel = (t, m, d, vel, st) => hit(t, celE(m), vel * 0.5, st);
const harm = (t, m, d, vel, st) => hit(t, harmE(m), vel * 0.55, st);
// Breathy flute (shakuhachi/ryūteki-ish): scooped onset, chiff, delayed vibrato.
function flute(t, m, dur, vel, st, o = {}) {
  return play("bg", (v) => {
    const f = mtof(m), end = t + dur + 0.5, rel = t + Math.max(0.08, dur);
    const osc = v.o("fl", f, t, end), g = v.g(0), nz = v.n("white", t, end), bp = v.f("bandpass", f * 1.5, 1.4), ng = v.g(0);
    osc.frequency.setValueAtTime(f * 0.97, t); osc.frequency.setTargetAtTime(f, t, 0.03);
    const lfo = v.o("sine", rnd(4.8, 5.6), t, end), lg = v.g(0);
    lfo.connect(lg); lg.connect(osc.detune);
    lg.gain.setValueAtTime(0, t + Math.min(0.3, dur * 0.4));
    lg.gain.linearRampToValueAtTime(o.vib || 13, t + Math.min(0.75, dur * 0.8) + 0.01);
    const pk = vel * 0.3;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(pk, t + 0.07);
    g.gain.setTargetAtTime(pk * 0.82, t + 0.07, 0.4); g.gain.setTargetAtTime(0, rel, 0.07);
    ng.gain.setValueAtTime(0, t); ng.gain.linearRampToValueAtTime(vel * 0.6, t + 0.025);
    ng.gain.setTargetAtTime(vel * 0.17, t + 0.025, 0.1); ng.gain.setTargetAtTime(0, rel, 0.05);
    chain(osc, g, st.i); chain(nz, bp, ng, st.i);
  });
}
// Soft pad: detuned saws through a slowly opening lowpass.
function pad(t, ms, dur, vel, st, o = {}) {
  return play("bg", (v) => {
    const a = o.att || 1.5, r = o.rel || 2.5, end = t + Math.max(a, dur) + r * 1.6, cut = o.cut || 900;
    const lp = v.f("lowpass", cut * 0.5, -1), g = v.g(0);
    lp.frequency.setValueAtTime(nyq(cut * 0.5), t); lp.frequency.linearRampToValueAtTime(nyq(cut), t + a + dur * 0.4);
    for (const m of ms) for (const dt of [-7, 7]) { const x = v.o("sawtooth", mtof(m), t, end); x.detune.value = dt + rnd(-3, 3); x.connect(lp); }
    swell(g.gain, t, a, (vel * 0.22) / Math.sqrt(ms.length), Math.max(0, dur - a), r);
    chain(lp, g, st.i);
  });
}
// Sustained voice (drone / rising cluster). Returns {stop(t)} or null.
function held(t, ms, vel, st, o = {}) {
  let H = null;
  play("bg", (v) => {
    const end = t + (o.dur || 600), over = o.over || 40, lp = v.f("lowpass", o.cut0 || 300, 2), g = v.g(0), xs = [];
    for (const m of ms) for (const dt of o.sub ? [0] : [-1, 1]) {
      const x = v.o(o.sub ? "sine" : "sawtooth", mtof(m), t, end); xs.push(x); x.connect(lp);
      x.detune.setValueAtTime(dt * (o.spread0 || 6), t);
      if (o.spread1) x.detune.linearRampToValueAtTime(dt * o.spread1, t + over);
      if (o.rise) { x.frequency.setValueAtTime(mtof(m), t); x.frequency.exponentialRampToValueAtTime(mtof(m + o.rise), t + over); }
    }
    if (o.cut1) { lp.frequency.setValueAtTime(nyq(o.cut0 || 300), t); lp.frequency.exponentialRampToValueAtTime(nyq(o.cut1), t + over); }
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel / Math.sqrt(xs.length), t + (o.att || 6));
    chain(lp, g, st.i);
    H = { stop(t1) { try { holdAt(g.gain, t1); g.gain.setTargetAtTime(0, t1, 0.7); for (const x of xs) x.stop(t1 + 4); v.end = t1 + 4; } catch (e) { /* ignore */ } } };
  });
  return H;
}
// Breath noise (tension): inhale = rising band, exhale = falling band.
function breath(t, dur, vel, st, inhale) {
  return play("bg", (v) => {
    const nz = v.n("pink", t, t + dur + 0.3), bp = v.f("bandpass", inhale ? 700 : 1300, 1.2), g = v.g(0);
    bp.frequency.setValueAtTime(inhale ? 700 : 1400, t); bp.frequency.linearRampToValueAtTime(inhale ? 1500 : 650, t + dur);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + dur * (inhale ? 0.85 : 0.2)); g.gain.linearRampToValueAtTime(0, t + dur);
    chain(nz, bp, g, st.i);
  });
}
// Heartbeat-like taiko "lub-dub".
function heart(t, vel, st) {
  hit(t, "taiko", vel, st, 0.55);
  hit(t + rnd(0.24, 0.3), "taiko", vel * 0.6, st, 0.48);
}

/* =====================================================================
   SFX — one-shot sound effects (AU.sfx)
   ===================================================================== */
const SFX = {};
let stepN = 0;
const MAT = { // [filter Hz, Q, decay s, level, filter type]
  grass: [3000, 0.9, 0.055, 0.2, "bandpass"], soil: [800, 0, 0.06, 0.3, "lowpass"],
  stone: [2600, 1.4, 0.035, 0.24, "bandpass"], wood: [480, 3.5, 0.075, 0.3, "bandpass"],
  water: [1400, 1.1, 0.09, 0.26, "bandpass"], leaves: [3800, 0.7, 0.085, 0.2, "bandpass"],
  sand: [3400, 1.0, 0.065, 0.16, "bandpass"], moss: [520, 0, 0.045, 0.15, "lowpass"],
};
const bufTo = (v, key, t, rate, lvl, out) => { const s = v.b(typeof key === "string" ? snd(key) : key, t, rate), g = v.g(lvl); chain(s, g, out); return s; };
function thump(v, out, t, f0, f1, lvl, d) {
  const x = v.o("sine", f0, t, t + d + 0.1), g = v.g(0);
  x.frequency.setValueAtTime(f0, t); x.frequency.exponentialRampToValueAtTime(f1, t + d * 0.8); perc(g.gain, t, 0.004, lvl, d); chain(x, g, out);
}
function noiseHit(v, out, kind, t, type, f, q, lvl, d) {
  const nz = v.n(kind, t, t + d + 0.08), fl = v.f(type, f, q), g = v.g(0);
  perc(g.gain, t, 0.002, lvl, d); chain(nz, fl, g, out); return fl;
}
SFX.step = (o, sp, t) => {
  const mat = MAT[o.mat] ? o.mat : "soil", M = MAT[mat], w = u01(o.weight), run = !!o.run;
  play("sfx", (v) => {
    const f = M[0] * (1 - 0.45 * w) * rnd(0.85, 1.15), d = M[2] * (run ? 0.8 : 1) * (1 + 0.5 * w);
    const lvl = M[3] * 1.8 * (1 + 0.6 * w) * (run ? 1.15 : 1) * rnd(0.8, 1.05), out = v.out("sfx", sp, 1, 0.04);
    const nz = v.n("white", t, t + d * 2.5 + 0.06, rnd(0.8, 1.2)), fl = v.f(M[4], f, M[1]), g = v.g(0);
    chain(nz, fl, g, out);
    if (mat === "leaves" || mat === "sand" || mat === "grass") grains(g.gain, t, mat === "grass" ? 2 : 3, d * 1.3, lvl);
    else perc(g.gain, t, 0.003, lvl, d);
    if (mat === "water") { const b = v.o("sine", 380, t, t + 0.07), bg = v.g(0); b.frequency.exponentialRampToValueAtTime(1100, t + 0.04); perc(bg.gain, t, 0.004, lvl * 0.25, 0.04); chain(b, bg, out); }
    if (mat === "wood") bufTo(v, "knock", t, rnd(0.7, 0.85) * (1 - 0.25 * w), lvl * 0.5, out);
    if (mat === "stone") bufTo(v, "tick", t, rnd(0.5, 0.7), lvl * 0.35, out);
    if (w > 0.2) thump(v, out, t, 85, 42, 0.3 * w, 0.12);
    if (w < 0.5 && ++stepN % 2 === 0 && chance(0.8)) // her little brass bell (鈴), barely there
      bufTo(v, "suzu", t + rnd(0.01, 0.04), rnd(0.96, 1.04), rnd(0.018, 0.035) * (1 - w), out);
  });
};
SFX.pickup = (o, sp, t) => {
  const z = u01(o.size, 0.4);
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.06), bp = noiseHit(v, out, "white", t, "bandpass", 800, 1.5, 0.18, 0.12);
    bp.frequency.exponentialRampToValueAtTime(2600 - z * 1200, t + 0.12);
    bufTo(v, "knock", t + 0.03, lerp(1.5, 0.75, z), 0.22 + z * 0.15, out);
  });
};
SFX.drop = (o, sp, t) => {
  const z = u01(o.size, 0.4);
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.05);
    thump(v, out, t, 120 - z * 40, 48, 0.35 + z * 0.3, 0.16 + z * 0.12);
    noiseHit(v, out, "brown", t, "lowpass", 900 - z * 400, 0, 0.5, 0.08 + z * 0.06);
    bufTo(v, "knock", t + 0.005, lerp(1.1, 0.6, z), 0.2, out);
  });
};
SFX.stack = (o, sp, t) => { // pitch climbs the yo scale with stack height
  const n = clamp(Math.round(num(o.n, 1)), 0, 30), m = dshift(62, Math.min(n, 16));
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.08);
    bufTo(v, "knock", t, mtof(m) / 520, 0.3, out);
    bufTo(v, ksE("koto", m + 12), t + 0.01, 1, 0.07, out);
  });
};
SFX.wobble = (o, sp, t) => { // wooden back-frame creak: stick-slip pulses into body resonances
  const a = u01(o.amt, 0.5), dur = 0.25 + a * 0.45;
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.05), saw = v.o("sawtooth", 20, t, t + dur + 0.1);
    const bp = v.f("bandpass", rnd(180, 260), 9), bp2 = v.f("bandpass", rnd(420, 560), 7), g2 = v.g(0.4), g = v.g(0);
    saw.frequency.setValueAtTime(rnd(16, 24), t); saw.frequency.linearRampToValueAtTime(rnd(26, 40), t + dur * 0.6); saw.frequency.linearRampToValueAtTime(rnd(14, 22), t + dur);
    swell(g.gain, t, dur * 0.3, 1.2 + a * 1.8, dur * 0.4, dur * 0.3);
    saw.connect(bp); saw.connect(bp2); bp.connect(g); chain(bp2, g2, g); g.connect(out);
  });
};
SFX.fall = (o, sp, t) => {
  const z = u01(o.size, 0.5), n = 3 + Math.round(z * 4);
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.06);
    let tt = t;
    for (let i = 0; i < n; i++) { bufTo(v, i % 3 === 2 ? "wood" : "knock", tt, rnd(0.6, 1.4), rnd(0.12, 0.3) * (1 - i / (n + 2)), out); tt += rnd(0.04, 0.14) * (1 + i * 0.15); }
    thump(v, out, t + 0.02, 95, 44, 0.3 + 0.35 * z, 0.25);
    noiseHit(v, out, "brown", t, "lowpass", 700, 0, 0.35, 0.25 + z * 0.2);
  });
};
SFX.land = (o, sp, t) => {
  const h = u01(o.h, 0.4);
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.04);
    thump(v, out, t, 110, 40, 0.25 + h * 0.4, 0.15 + h * 0.15);
    noiseHit(v, out, "pink", t, "lowpass", 500 + h * 600, 0, 0.25 + h * 0.3, 0.1 + h * 0.1);
  });
};
SFX.take = (o, sp, t) => play("sfx", (v) => { // a muted gong pulled inward
  const out = v.out("sfx", sp, 1, 0.2, 0.05), lp = v.f("lowpass", 1400, 1), g = v.g(0);
  for (const [r, a] of [[1, 0.5], [1.48, 0.3], [2.09, 0.2], [2.76, 0.1]]) {
    const x = v.o("sine", 135 * r, t, t + 0.75); x.frequency.exponentialRampToValueAtTime(70 * r, t + 0.6); chain(x, v.g(a), lp);
  }
  lp.frequency.exponentialRampToValueAtTime(260, t + 0.6);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.42, t + 0.48); g.gain.linearRampToValueAtTime(0, t + 0.64);
  chain(lp, g, out);
  const nz = v.n("pink", t, t + 0.7), bp = v.f("bandpass", 1600, 1), ng = v.g(0);
  bp.frequency.exponentialRampToValueAtTime(220, t + 0.6);
  ng.gain.setValueAtTime(0, t); ng.gain.linearRampToValueAtTime(0.2, t + 0.5); ng.gain.linearRampToValueAtTime(0, t + 0.62);
  chain(nz, bp, ng, out);
});
function airSweep(v, out, t, f0, f1, dur, lvl, peakAt = 0.6) {
  const nz = v.n("pink", t, t + dur + 0.1), bp = v.f("bandpass", f0, 1.3), g = v.g(0);
  bp.frequency.setValueAtTime(f0, t); bp.frequency.exponentialRampToValueAtTime(f1, t + dur * 0.8);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(lvl, t + dur * peakAt); g.gain.linearRampToValueAtTime(0, t + dur);
  chain(nz, bp, g, out);
}
SFX.give = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.25);
  airSweep(v, out, t, 380, 3600, 0.75, 0.5, 0.65);
  bufTo(v, "glass", t + 0.45, 0.75, 0.26, out);
});
// The five qualities (重熱光音生): one timbre each, played when a transfer lands (AU.sfx("qual",
// {k, verb, n})). The cast itself uses take/give/release; this is the arrival. n = how much she
// holds afterwards (0..9): the tonal part sits on the yo scale at that step, so a full body is
// audible without looking. take runs each figure inward (falling), give/release outward (rising).
const QBASE = { w: 45, h: 57, l: 74, s: 69, v: 62 };
SFX.qual = (o, sp, t) => {
  const k = QBASE[o.k] !== undefined ? o.k : "w", inn = o.verb !== "give" && o.verb !== "release";
  const n = clamp(Math.round(num(o.n, 3)), 0, 9), m = dshift(QBASE[k], n - 3), r = mtof(m) / mtof(QBASE[k]);
  const lvl = o.verb === "release" ? 1.25 : 1;
  play("sfx", (v) => {
    const out = v.out("sfx", sp, lvl, k === "s" || k === "l" ? 0.3 : 0.16, 0.03);
    if (k === "w") { // a stone settling: low thump, a gong far under it, grit
      thump(v, out, t, 95 * r, 38, 0.5, 0.24);
      bufTo(v, "gong", t, 0.48 * r, 0.22, out);
      noiseHit(v, out, "brown", t, "lowpass", 600, 0, 0.35, 0.12);
    } else if (k === "h") { // embers: crackle grains over a breath of air (catching, or being smothered)
      const nz = v.n("white", t, t + 0.45), bp = v.f("bandpass", rnd(2600, 3400), 0.8), g = v.g(0);
      grains(g.gain, t, 7, 0.32, 0.28); chain(nz, bp, g, out);
      const b = v.n("brown", t, t + 0.4), lp = v.f("lowpass", inn ? 1500 : 260, 0), bg = v.g(0);
      lp.frequency.exponentialRampToValueAtTime(inn ? 240 : 1600, t + 0.3); perc(bg.gain, t, 0.03, 0.55, 0.3); chain(b, lp, bg, out);
      bufTo(v, "tick", t + 0.02, 0.55 * r, 0.1, out);
    } else if (k === "l") { // glass: three partials, a harmonic on top
      [1, 1.5, 2].forEach((x, i) => bufTo(v, "glass", t + 0.05 * (inn ? 2 - i : i), x * r, 0.13, out));
      bufTo(v, harmE(m + 12), t + 0.08, 1, 0.1, out);
    } else if (k === "s") { // the rin: struck when given, drawn in (swelling, then cut) when taken
      const s = v.b(snd("rin"), t, 0.9 * r), g = v.g(0);
      if (inn) { g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.32, t + 0.32); g.gain.linearRampToValueAtTime(0, t + 0.36); }
      else perc(g.gain, t, 0.003, 0.34, 0.9);
      chain(s, g, out);
      bufTo(v, "suzu", t + (inn ? 0.34 : 0.05), rnd(0.96, 1.04), 0.06, out);
    } else { // life: koto harmonics a third apart, and leaves
      bufTo(v, harmE(m), t, 1, 0.16, out);
      bufTo(v, harmE(dshift(m, inn ? -2 : 2)), t + 0.09, 1, 0.13, out);
      airSweep(v, out, t, inn ? 4800 : 700, inn ? 700 : 4800, 0.45, 0.22, 0.3);
    }
  });
};
SFX.release = (o, sp, t) => play("sfx", (v) => { // letting go: a burst of air outward with a low bloom
  const out = v.out("sfx", sp, 1, 0.3, 0.05);
  airSweep(v, out, t, 300, 4200, 0.5, 0.55, 0.25);
  thump(v, out, t, 80, 40, 0.4, 0.3);
});
SFX.stone = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.22, 0.08);
  bufTo(v, "gong", t, 0.92, 0.6, out);
  thump(v, out, t, 70, 38, 0.45, 0.35);
  const nz = v.n("white", t, t + 0.7), lp = v.f("lowpass", 2400, 0), ng = v.g(0); grains(ng.gain, t + 0.01, 9, 0.38, 0.35); chain(nz, lp, ng, out);
});
SFX.unstone = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.2);
  const nz = v.n("white", t, t + 0.8), bp = v.f("bandpass", 1800, 0.8), ng = v.g(0); grains(ng.gain, t, 12, 0.45, 0.4); chain(nz, bp, ng, out);
  airSweep(v, out, t + 0.1, 500, 2800, 0.6, 0.33, 0.75);
  bufTo(v, "glass", t + 0.55, 0.6, 0.16, out);
});
SFX.leaf = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.3);
  airSweep(v, out, t, 600, 5200, 0.9, 0.45, 0.2);
  for (const [dt, r] of [[0.08, 1], [0.16, 1.5], [0.27, 1.335]]) bufTo(v, "glass", t + dt, r, 0.14, out);
});
SFX.unleaf = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.2);
  airSweep(v, out, t, 4200, 450, 0.6, 0.38, 0.15);
  bufTo(v, "knock", t + 0.42, 0.55, 0.3, out);
});
SFX.deny = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.03);
  thump(v, out, t, 190, 120, 0.35, 0.08);
  noiseHit(v, out, "white", t, "lowpass", 900, 0, 0.15, 0.02);
});
SFX.offering = (o, sp, t) => play("sfx", (v) => { // the rin: bright singing bowl with a shimmering octave
  const out = v.out("sfx", sp, 1, 0.35, 0.12);
  bufTo(v, "rin", t, 1, 0.5, out);
  const sh = v.b(snd("rin"), t + 0.035, 2), tr = v.g(0.6), lfo = v.o("sine", 6.5, t, t + 2.4), lg = v.g(0.4), env = v.g(0);
  chain(lfo, lg, tr.gain); env.gain.setValueAtTime(0.12, t); env.gain.linearRampToValueAtTime(0, t + 2.3);
  chain(sh, tr, env, out);
});
const COUNT9 = [74, 76, 79, 81, 83, 86, 88, 91, 93]; // D5 … A6: nine steps, never a tenth
SFX.count = (o, sp, t) => {
  const n = Math.max(0, Math.round(num(o.n, 1)));
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.05);
    if (n >= 100) { bufTo(v, "knock", t, 0.5, 0.1, out); return; } // past ninety-nine: only a dull tok
    const m = COUNT9[(Math.max(1, n) - 1) % 9];
    bufTo(v, "tick", t, (mtof(m + 12) / 2200) * rnd(0.99, 1.01), 0.22, out);
    bufTo(v, "wood", t, mtof(m - 12) / 700, 0.08, out);
    if (n === 99) bufTo(v, "suzu", t + 0.12, 0.94, 0.06, out);
  });
};
SFX.build = (o, sp, t) => play("sfx", (v) => { // kon-kon
  const out = v.out("sfx", sp, 1, 0.1), n = chance(0.5) ? 2 : 3;
  for (let i = 0; i < n; i++) {
    const tt = t + i * rnd(0.2, 0.26);
    bufTo(v, "knock", tt, rnd(0.82, 0.9), i === n - 1 ? 0.5 : 0.4, out);
    thump(v, out, tt, 160, 90, 0.25, 0.07);
  }
});
SFX.place = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.06);
  bufTo(v, "knock", t, rnd(0.55, 0.7), 0.3, out);
  thump(v, out, t, 100, 50, 0.35, 0.14);
  const nz = v.n("white", t, t + 0.35), lp = v.f("lowpass", 1800, 0), ng = v.g(0); grains(ng.gain, t + 0.01, 4, 0.12, 0.12); chain(nz, lp, ng, out);
});
SFX.build_done = (o, sp, t) => {
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.3);
    [50, 57, 62, 64, 69].forEach((m, i) => bufTo(v, ksE("koto", m), t + i * 0.045, 1, 0.22, out));
    bufTo(v, "rin", t + 0.25, 1, 0.3, out);
    for (let i = 0; i < 5; i++) bufTo(v, "glass", t + 0.5 + rnd(0, 1.4), pick([1, 1.122, 1.335, 1.5, 0.89]), rnd(0.04, 0.09), out);
  });
  pad(t, [50, 57, 64, 71], 1.5, 0.5, { i: BUS.sfx.inp }, { att: 0.4, rel: 2, cut: 1100 });
};
SFX.blip = (o, sp, t) => { // dialogue voice blips
  const vc = o.voice || "tsuzura", i = Math.round(num(o.i, 0));
  play("sfx", (v) => {
    const out = v.out("voice", sp, 1, 0.02);
    if (vc === "kago") {
      bufTo(v, "knock", t, (220 / 520) * rnd(0.95, 1.05), 0.35, out);
      thump(v, out, t, 230, 205, 0.12, 0.05);
    } else if (vc === "old") {
      noiseHit(v, out, "pink", t, "bandpass", 520 + (i % 5) * 30, 2.5, 0.55, 0.07);
      thump(v, out, t, 165 + (i % 4) * 9, 150, 0.2, 0.07);
    } else if (vc === "radio") {
      noiseHit(v, out, "white", t, "bandpass", 2200, 1.5, 0.7, 0.018);
      const x = v.o("square", 900 + (i % 3) * 140, t, t + 0.03), g = v.g(0); perc(g.gain, t, 0.001, 0.06, 0.015); chain(x, g, out);
    } else if (vc === "crow") {
      const x = v.o("sawtooth", 560 + (i % 4) * 30, t, t + 0.08), vca = v.g(0.55), nz = v.n("white", t, t + 0.08, 0.5), bp = v.f("bandpass", 1300, 2), g = v.g(0);
      chain(nz, v.g(0.45), vca.gain); perc(g.gain, t, 0.004, 0.8, 0.05); chain(x, vca, bp, g, out);
    } else { // tsuzura: bright, quick, a little squeaky
      const f = 650 + ((i * 37) % 11) * 28 + rnd(-15, 15);
      const a = v.o("triangle", f, t, t + 0.06), b = v.o("square", f * 1.003, t, t + 0.06), lp = v.f("lowpass", 3200, 0), g = v.g(0);
      a.frequency.setValueAtTime(f * 1.06, t); a.frequency.exponentialRampToValueAtTime(f, t + 0.012);
      chain(b, v.g(0.22), lp); a.connect(lp); perc(g.gain, t, 0.002, 0.2, 0.035); chain(lp, g, out);
    }
  });
};
SFX.ui_move = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.02);
  noiseHit(v, out, "white", t, "highpass", 3500, 0, 0.09, 0.012);
  bufTo(v, "tick", t, 0.72, 0.12, out);
});
function uiPair(m1, m2, wr) {
  return (o, sp, t) => play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.08);
    bufTo(v, ksE("koto", m1), t, 1, 0.22, out); bufTo(v, ksE("koto", m2), t + 0.07, 1, 0.2, out);
    bufTo(v, "wood", t, wr, 0.1, out);
  });
}
SFX.ui_ok = uiPair(74, 81, 1.2);
SFX.ui_back = uiPair(69, 64, 0.9);
SFX.ui_open = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.1);
  airSweep(v, out, t, 1200, 4200, 0.2, 0.14, 0.5);
  bufTo(v, harmE(79), t + 0.08, 1, 0.17, out);
});
SFX.ui_close = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.06);
  airSweep(v, out, t, 4000, 1000, 0.18, 0.13, 0.4);
  bufTo(v, "tick", t + 0.12, 0.6, 0.1, out);
});
SFX.splash = (o, sp, t) => {
  const z = u01(o.size, 0.5);
  play("sfx", (v) => {
    const out = v.out("sfx", sp, 1, 0.1), lp = noiseHit(v, out, "white", t, "lowpass", 5000, 0, 0.3 + z * 0.3, 0.25 + z * 0.35);
    lp.frequency.exponentialRampToValueAtTime(500, t + 0.3 + z * 0.3);
    for (let i = 0; i < 3 + z * 5; i++) {
      const tt = t + rnd(0.02, 0.35 + z * 0.3), f = rnd(350, 900), b = v.o("sine", f, tt, tt + 0.08), bg = v.g(0);
      b.frequency.exponentialRampToValueAtTime(f * rnd(1.8, 2.6), tt + 0.05); perc(bg.gain, tt, 0.003, rnd(0.04, 0.12), 0.05); chain(b, bg, out);
    }
  });
};
SFX.gust = (o, sp, t) => play("sfx", (v) => {
  const dur = rnd(2, 3), out = v.out("sfx", sp, 1, 0.1), pn = v.p(-0.6);
  const nz = v.n("pink", t, t + dur + 0.2), bp = v.f("bandpass", 300, 0.7), g = v.g(0);
  bp.frequency.exponentialRampToValueAtTime(1100, t + dur * 0.45); bp.frequency.exponentialRampToValueAtTime(380, t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.55, t + dur * 0.45); g.gain.linearRampToValueAtTime(0, t + dur);
  pn.pan.linearRampToValueAtTime(0.6, t + dur);
  chain(nz, bp, g, pn, out);
  const n2 = v.n("white", t, t + dur + 0.1), b2 = v.f("bandpass", 4000, 0.8), g2 = v.g(0); // leaves rushing along
  g2.gain.setValueAtTime(0, t); g2.gain.linearRampToValueAtTime(0.07, t + dur * 0.5); g2.gain.linearRampToValueAtTime(0, t + dur);
  chain(n2, b2, g2, pn);
});
SFX.thunder = (o, sp, t) => play("sfx", (v) => { // distant, long, rolling
  const dist = u01(o.dist, 0.7), out = v.out(o._bus === "ambx" ? "ambx" : "sfx", sp, 1, 0.3, 0.2), g = v.g(0), n = rint(3, 5);
  g.gain.setValueAtTime(0, t);
  let tt = t + rnd(0.05, 0.3);
  for (let i = 0; i < n; i++) {
    const pk = rnd(0.4, 1) * (1 - i / (n + 1)) * lerp(0.55, 0.3, dist);
    g.gain.linearRampToValueAtTime(pk, tt + rnd(0.15, 0.5)); tt += rnd(0.6, 1.6); g.gain.linearRampToValueAtTime(pk * 0.3, tt);
  }
  const end = tt + rnd(1.2, 2);
  g.gain.linearRampToValueAtTime(0, end);
  chain(v.n("brown", t, end + 0.05), v.f("lowpass", lerp(420, 170, dist), 0), g, out);
  noiseHit(v, out, "white", t, "bandpass", 1400, 0.7, 0.12 * (1 - dist * 0.7), 0.4); // the crack, muffled by distance
});
function caw(v, out, t, n, base) { // crow: buzzy saw through beak formants, noise-modulated rasp
  let tt = t;
  for (let i = 0; i < n; i++) {
    const d = rnd(0.22, 0.34), f = base * rnd(0.95, 1.05), x = v.o("sawtooth", f, tt, tt + d + 0.05), sq = v.o("square", f * 0.5, tt, tt + d + 0.05);
    x.frequency.setValueAtTime(f * 1.12, tt); x.frequency.linearRampToValueAtTime(f, tt + 0.06); x.frequency.linearRampToValueAtTime(f * 0.86, tt + d);
    const vca = v.g(0.55), f1 = v.f("bandpass", 1250, 3), f2 = v.f("bandpass", 2400, 4), env = v.g(0);
    chain(v.n("white", tt, tt + d + 0.05, 0.5), v.g(0.45), vca.gain);
    x.connect(vca); chain(sq, v.g(0.3), vca); vca.connect(f1); vca.connect(f2); f1.connect(env); f2.connect(env); env.connect(out);
    env.gain.setValueAtTime(0, tt); env.gain.linearRampToValueAtTime(0.9, tt + 0.03); env.gain.setValueAtTime(0.9, tt + d * 0.6); env.gain.linearRampToValueAtTime(0, tt + d);
    tt += d + rnd(0.18, 0.35);
  }
  return tt - t;
}
SFX.crow = (o, sp, t) => play("sfx", (v) => caw(v, v.out("sfx", sp, 1, 0.25), t, rint(1, 3), rnd(480, 560)));
SFX.deer = (o, sp, t) => play("sfx", (v) => { // sika deer: a high, lonely "pyuu—"
  const out = v.out("sfx", sp, 1, 0.45), f = rnd(1900, 2200), g = v.g(0);
  for (const [k, a] of [[1, 1], [2, 0.08]]) {
    const x = v.o("sine", f * k * 0.86, t, t + 1.25), xg = v.g(a);
    x.frequency.exponentialRampToValueAtTime(f * k * 1.06, t + 0.13); x.frequency.exponentialRampToValueAtTime(f * k * 0.72, t + 1.05);
    chain(x, xg, g);
  }
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.3, t + 0.08); g.gain.linearRampToValueAtTime(0.2, t + 0.35); g.gain.linearRampToValueAtTime(0, t + 1.1);
  g.connect(out);
  noiseHit(v, out, "white", t, "bandpass", f, 4, 0.1, 0.5);
});
SFX.wings = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.15), g = v.g(0), pn = v.p(0), n = rint(6, 10);
  let tt = t, per = rnd(0.06, 0.08);
  g.gain.setValueAtTime(0, t);
  for (let i = 0; i < n; i++) {
    const a = 0.45 * Math.pow(1 - i / n, 1.2) + 0.02;
    g.gain.linearRampToValueAtTime(a, tt + per * 0.25); g.gain.linearRampToValueAtTime(a * 0.08, tt + per * 0.9); tt += per; per *= 1.09;
  }
  g.gain.linearRampToValueAtTime(0, tt + 0.05);
  pn.pan.linearRampToValueAtTime(chance(0.5) ? 0.7 : -0.7, tt);
  chain(v.n("pink", t, tt + 0.1), v.f("bandpass", 900, 0.9), g, pn, out);
});
SFX.rustle = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.08), dur = rnd(0.35, 0.7), g = v.g(0), g2 = v.g(0);
  const e1 = grains(g.gain, t, rint(10, 18), dur, 0.3), e2 = grains(g2.gain, t, 6, dur, 0.15);
  chain(v.n("white", t, e1 + 0.05), v.f("bandpass", rnd(2800, 4200), 0.7), g, out);
  chain(v.n("pink", t, e2 + 0.05), v.f("bandpass", 900, 0.8), g2, out);
});
SFX.branch = (o, sp, t) => play("sfx", (v) => { // twig snap: sharp crack + woody ring, two aftershocks
  const out = v.out("sfx", sp, 1, 0.12);
  for (const [dt, a] of [[0, 0.5], [rnd(0.03, 0.06), 0.25], [rnd(0.08, 0.13), 0.12]]) {
    const tt = t + dt;
    noiseHit(v, out, "white", tt, "highpass", 1500, 0, a * 0.6, 0.006);
    noiseHit(v, out, "white", tt, "bandpass", rnd(1800, 3200), 6, a * 2.2, 0.035);
  }
});
SFX.far_wave = (o, sp, t) => { // the Far sweeps over the mountain: swell, smear, then nothing
  const T = rnd(6.6, 7.6), end = t + T;
  play("sfx", (v) => {
    const out = v.out("far", SP0, 0.55, 0, 0.45);
    const rise = (p, peak) => { p.setValueAtTime(0.0006, t); p.exponentialRampToValueAtTime(peak, end - 0.03); p.linearRampToValueAtTime(0, end); };
    for (const [f, a] of [[36, 0.5], [54, 0.22]]) {
      const x = v.o("sine", f * 1.25, t, end + 0.05), g = v.g(0);
      x.frequency.setValueAtTime(f * 1.25, t); x.frequency.exponentialRampToValueAtTime(f, end); rise(g.gain, a); chain(x, g, out);
    }
    const ng = v.g(0); rise(ng.gain, 0.6); chain(v.n("brown", t, end + 0.05), v.f("lowpass", 150, 2), ng, out);
    for (const r of [1, 1.5, 2.71, 3.4, 5.15]) { // inverted shimmer: bell partials swelling backwards, trembling
      const x = v.o("sine", 587.3 * r * rnd(0.997, 1.003), t, end + 0.05), tr = v.g(0.6), g = v.g(0);
      chain(v.o("sine", rnd(4, 9), t, end), v.g(0.4), tr.gain); rise(g.gain, 0.05 / Math.sqrt(r)); chain(x, tr, g, out);
    }
    const fl = v.f("lowpass", 1400, 1), fg = v.g(0); rise(fg.gain, 1); // the festival itself, slowed and pitched down
    fl.frequency.setValueAtTime(1400, t); fl.frequency.exponentialRampToValueAtTime(380, end);
    chain(fl, fg, out);
    const st = { i: fl };
    let tt = t + 0.3, k = 0;
    while (tt < end - 0.25) {
      hit(tt, "odaiko", 0.5, st, 0.62, "sfx");
      if (k++ % 2) hit(tt + 0.27, "kaneO", 0.05, st, 0.55, "sfx");
      tt += lerp(1.1, 0.45, (tt - t) / T);
    }
    const mel = [86, 84, 81, 84, 86, 81, 79, 81], nd = (T - 1.2) / mel.length;
    mel.forEach((m, i) => flute(t + 0.6 + i * nd, m - 19, nd * 0.95, 0.5, st, { vib: 30 }));
  });
  try { // everything filtered, then a hard cut to silence
    const f = waveLP.frequency, h = hush.gain;
    holdAt(f, t); f.setValueAtTime(nyq(20000), t); f.exponentialRampToValueAtTime(650, end); f.setValueAtTime(nyq(20000), end + 2.2);
    holdAt(h, t); h.setValueAtTime(1, end - 0.012); h.linearRampToValueAtTime(0, end + 0.004);
    h.setValueAtTime(0, end + 2.4); h.setTargetAtTime(1, end + 2.4, 1.1);
  } catch (e) { /* ignore */ }
};
SFX.far_touch = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("far", sp, 0.8, 0.1, 0.6);
  bufTo(v, "glass", t, 1.335, 0.12, out);
  for (const f of [3520, 4228]) {
    const x = v.o("sine", f, t, t + 1.6), tr = v.g(0.6), g = v.g(0);
    chain(v.o("sine", rnd(9, 13), t, t + 1.6), v.g(0.4), tr.gain);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.03, t + 0.15); g.gain.linearRampToValueAtTime(0, t + 1.5);
    chain(x, tr, g, out);
  }
  const k = v.b(snd("taiko"), t + 0.05, 0.85); chain(k, v.f("lowpass", 380, 0), v.g(0.5), out);
});
SFX.far_pulse = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("far", sp, 0.25, 0.1, 1);
  chain(v.b(snd("odaiko"), t, 0.92), v.f("lowpass", 420, 0), v.g(0.6), out);
  chain(v.b(snd("rin"), t + 0.02, 0.5), v.f("lowpass", 1800, 0), v.g(0.35), out);
});
SFX.awaken = (o, sp, t) => play("sfx", (v) => { // tsukumogami: rattle, nine-note koto run, little bell
  const out = v.out("sfx", sp, 1, 0.25);
  let tt = t, per = 0.11;
  for (let i = 0; i < 10; i++) { bufTo(v, i % 2 ? "wood" : "knock", tt, rnd(0.8, 1.6), 0.12 + i * 0.012, out); tt += per; per *= 0.85; }
  [62, 64, 67, 69, 71, 74, 76, 79, 81].forEach((m, i) => bufTo(v, ksE("koto", m), tt + i * 0.045, 1, 0.12 + i * 0.012, out));
  bufTo(v, "suzu", tt + 0.45, 1, 0.1, out); bufTo(v, "suzu", tt + 0.6, 1.06, 0.07, out);
});
SFX.sleep = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.3);
  [[81, 0], [76, 0.35], [74, 0.8]].forEach(([m, dt]) => bufTo(v, harmE(m), t + dt, 1, 0.16, out));
  airSweep(v, out, t, 1200, 350, 1.9, 0.08, 0.2);
});
SFX.bell_big = (o, sp, t) => play("sfx", (v) => bufTo(v, "bell", t, 1, 0.6, v.out("sfx", sp, 1, 0.35, 0.25)));
SFX.heartbeat = (o, sp, t) => play("sfx", (v) => {
  const out = v.out("sfx", sp, 1, 0.02);
  thump(v, out, t, 62, 40, 0.55, 0.16); thump(v, out, t + 0.27, 52, 34, 0.38, 0.16);
  noiseHit(v, out, "brown", t, "lowpass", 160, 0, 0.25, 0.1);
});

/* =====================================================================
   AMBIENCE — breathing forest beds + scheduled creatures (update-driven)
   ===================================================================== */
const AMB = { on: false, act: 1, wet: 0, gust: 0.6, nextGust: 0, nextLeaf: 0, nextWander: 0 };
let ambIn, ambLP, ambG, ambWIn, ambWLP, ambWG;
const W = {}, LV = {}, SS = {}, ST = {}, FA = {}, RN = {}, BEDS = {}, ACT = {}, PEND = [];
function bed(name, specs) { BEDS[name] = { specs, srcs: [], live: false, idle: 0 }; }
function startLoop(sp) {
  const buf = NZ[sp[0]] || (BK.get(sp[0]) || {}).b;
  if (!buf) return null;
  const s = ctx.createBufferSource();
  s.buffer = buf; s.loop = true; s.playbackRate.value = sp[2] || 1;
  s.connect(sp[1]); s.start(ctx.currentTime + 0.01, Math.random() * buf.duration * 0.9);
  return s;
}
// Beds run only while wanted: sources start on demand and stop after 4 s of silence.
function bedWant(name, lvl, dt) {
  const b = BEDS[name];
  if (lvl > 0.0006) {
    b.idle = 0; b.live = true;
    for (let i = 0; i < b.specs.length; i++) if (!b.srcs[i]) b.srcs[i] = startLoop(b.specs[i]);
  } else if (b.live && (b.idle += dt) > 4) {
    b.live = false;
    for (const s of b.srcs) if (s) { try { s.stop(); s.disconnect(); } catch (e) { /* ignore */ } }
    b.srcs = [];
  }
}
// Seamless ambience loops, baked in background slices: one job per channel, registered when done.
function loopJobs(key, sec, fill) {
  const b = ctx.createBuffer(2, Math.floor(sec * SR), SR);
  return [() => fill(b.getChannelData(0), b.length), () => fill(b.getChannelData(1), b.length), () => BK.set(key, { b, r: 1 })];
}
function droplets(perSec, a0, a1) { // rain patter: tiny resonant pings with a click
  return (d, len) => {
    for (let i = 0, n = Math.floor((len / SR) * perSec); i < n; i++) {
      const st = Math.floor(Math.random() * (len - SR * 0.04)), a = rnd(a0, a1) * (chance(0.15) ? 2 : 1);
      addPartials(d, [[rnd(1800, 7000), a, rnd(0.0015, 0.005), 0.0003]], st);
      addNoise(d, a * 0.6, 0.0008, 0, true, st);
    }
  };
}
function babble(d, len) { // brook bubbles: Minnaert-like rising "bloops" (phasor chirps)
  for (let i = 0; i < 64; i++) {
    const st = Math.floor(Math.random() * (len - SR * 0.2)), f0 = rnd(250, 1100), dur = rnd(0.012, 0.045), k = rnd(8, 30);
    const nn = Math.floor(dur * SR * 3.5), kd = Math.exp(-1 / (dur * SR));
    let re = 1, im = 0, c = 1, s = 0, env = rnd(0.05, 0.18);
    for (let j = 0; j < nn; j++) {
      if ((j & 15) === 0) { const w = (2 * Math.PI * f0 * (1 + (k * j) / SR)) / SR; c = Math.cos(w); s = Math.sin(w); }
      const r2 = re * c - im * s; im = re * s + im * c; re = r2;
      d[st + j] += im * env * Math.min(1, j / 30); env *= kd;
    }
  }
}
function bakeCrackle() {
  bake("crackle", 4, 1, (b, len) => {
    const d = b.getChannelData(0);
    for (let i = 0; i < 160; i++) addNoise(d, Math.pow(Math.random(), 3) * 0.9, rnd(0.0003, 0.002), 0.5, false, Math.floor(Math.random() * (len - 900)));
  }, true);
}
function buildAmb() {
  ambIn = G(); ambLP = BQ_("lowpass", 18000, 0); ambG = G(0); chain(ambIn, ambLP, ambG, BUS.amb.inp);
  ambWIn = G(); ambWLP = BQ_("lowpass", 18000, 0); ambWG = G(0); chain(ambWIn, ambWLP, ambWG, BUS.amb.wet);
  BUS.ambx = { inp: ambIn, wet: ambWIn, fwet: BUS.amb.fwet }; // pseudo-bus: through the nearness filter
  W.lp = BQ_("lowpass", 600, 0); W.gust = G(0.6); W.g = G(0);
  chain(W.lp, BQ_("highpass", 50, 0), W.gust, W.g, ambIn); bed("wind", [["pink", W.lp, 1]]);
  LV.bp = BQ_("bandpass", 3600, 0.8); LV.burst = G(0.2); LV.g = G(0);
  chain(LV.bp, LV.burst, LV.g, ambIn); bed("leaves", [["white", LV.bp, 1]]);
  SS.hp = BQ_("highpass", 4200, 0); SS.burst = G(0.3); SS.g = G(0);
  chain(SS.hp, BQ_("peaking", 7200, 1.2, 5), SS.burst, SS.g, ambIn); bed("sasa", [["white", SS.hp, 0.9]]);
  ST.g = G(0); ST.g.connect(ambIn); ST.in = G(1); ST.bp = []; ST.fg = [];
  ST.r = [[280, 520], [600, 1100], [1200, 2100], [2300, 3600]];
  for (let i = 0; i < 4; i++) {
    const b = BQ_("bandpass", (ST.r[i][0] + ST.r[i][1]) / 2, [5, 7, 8, 9][i]), g = G(1);
    chain(ST.in, b, g, ST.g); ST.bp.push(b); ST.fg.push(g);
  }
  ST.bab = G(0.8); ST.bab.connect(ST.g);
  bed("stream", [["white", ST.in, 1], ["babble", ST.bab, 0.93], ["babble", ST.bab, 1.07]]);
  FA.g = G(0); FA.g.connect(ambIn); FA.lp = BQ_("lowpass", 420, 0); FA.hp = BQ_("bandpass", 2600, 0.5);
  chain(FA.lp, FA.g); chain(FA.hp, G(0.35), FA.g);
  bed("fall", [["brown", FA.lp, 1], ["white", FA.hp, 1]]);
  RN.hp = BQ_("highpass", 2400, 0); RN.hg = G(0); chain(RN.hp, BQ_("lowpass", 9000, 0), RN.hg, ambIn);
  RN.body = BQ_("bandpass", 800, 0.6); RN.bg = G(0); chain(RN.body, RN.bg, ambIn);
  RN.dl = G(0); RN.dh = G(0); RN.dl.connect(ambIn); RN.dh.connect(ambIn);
  bed("rain", [["white", RN.hp, 1], ["pink", RN.body, 1], ["rainL", RN.dl, 1], ["rainH", RN.dh, 1]]);
  BQ.push(...loopJobs("rainL", 3, droplets(16, 0.05, 0.25)), ...loopJobs("rainH", 3, droplets(90, 0.03, 0.16)), ...loopJobs("babble", 6, babble), bakeCrackle);
}
// Per-frame bed levels (cheap: change-detected targets only).
function ambUpdate(dt) {
  const b = S.biome, near = S.near, rain = S.rain, wind = S.wind;
  const nearG = (0.03 + 0.97 * sstep(0, 0.6, near)) * (S.cinematic ? 0.7 : 1) * (S.indoor ? 0.5 : 1) * (AMB.on ? 1 : 0);
  const lpF = Math.min(near >= 0.6 ? 18000 : expMap(320, 18000, near / 0.6), S.indoor ? 1300 : 18000, lerp(18000, 4500, S.heavy));
  tgt(ambLP.frequency, nyq(lpF), 0.25); tgt(ambWLP.frequency, nyq(lpF), 0.25);
  tgt(ambG.gain, nearG, 0.35); tgt(ambWG.gain, nearG, 0.35);
  AMB.act = sstep(0.04, 0.6, near) * (S.indoor ? 0.4 : 1);
  const open = clamp(b.forest + b.bamboo + 1.3 * b.meadow + b.shrine + 0.5 * b.stream, 0.3, 1.3);
  const wv = (0.1 + 0.6 * wind) * open * 0.55;
  tgt(W.g.gain, wv, 0.6); tgt(W.lp.frequency, lerp(300, 1200, wind) * (1 + 0.25 * b.meadow), 0.8); bedWant("wind", wv, dt);
  const lv = b.forest * (0.15 + 0.85 * wind) * 0.3; tgt(LV.g.gain, lv, 0.5); bedWant("leaves", lv, dt);
  const sv = b.bamboo * (0.2 + 0.8 * wind) * 0.14; tgt(SS.g.gain, sv, 0.5); bedWant("sasa", sv, dt);
  const st = S.water * 0.75; tgt(ST.g.gain, st, 0.5); bedWant("stream", st, dt);
  const fv = S.fall * 0.5; tgt(FA.g.gain, fv, 0.5); bedWant("fall", fv, dt);
  AMB.wet = clamp(AMB.wet + (rain - AMB.wet) * (rain > AMB.wet ? dt / 3 : dt / 90), 0, 1); // leaves keep dripping after rain
  tgt(RN.hg.gain, rain * 0.32, 0.6); tgt(RN.bg.gain, Math.pow(rain, 1.5) * 0.28, 0.6);
  tgt(RN.dl.gain, sstep(0, 0.4, rain) * 0.5, 0.6); tgt(RN.dh.gain, sstep(0.35, 1, rain) * 0.55, 0.6);
  bedWant("rain", rain, dt);
}
// Daily window weight: 1 inside [a,b] (wrapping past midnight), easing in/out over f hours.
const circ = (x) => ((x % 24) + 24) % 24;
function dayW(h, a, b, f) {
  const inside = a <= b ? h >= a && h <= b : h >= a || h <= b;
  return inside ? Math.min(1, Math.min(circ(h - a), circ(b - h)) / f) : 0;
}
// Fire event fn at Poisson rate (per s), respecting a per-kind concurrency cap.
function maybe(k, rate, dt, t, fn, max) {
  if (!(rate > 0) || Math.random() >= rate * dt) return;
  const a = ACT[k] || (ACT[k] = []);
  for (let i = a.length - 1; i >= 0; i--) if (a[i] < t) a.splice(i, 1);
  if (a.length >= max) return;
  const dur = fn(t + rnd(0.02, 0.1));
  if (dur > 0) a.push(t + dur);
}
function ambOut(v, pan, lvl, wet, lp) {
  const g = v.g(lvl * 0.75), p = v.p(pan);
  if (lp) chain(g, v.f("lowpass", lp, 0), p); else g.connect(p);
  p.connect(ambIn);
  if (wet) chain(p, v.g(wet), ambWIn);
  return g;
}
function ambTick(t, dt) {
  if (!AMB.on) return;
  const s = S, wnd = s.wind, b = s.biome, h = s.tod;
  if (BEDS.wind.live && t >= AMB.nextGust) { // gusts: random walk of level + brightness
    const g = clamp(0.62 + (Math.random() - 0.5) * (0.35 + 0.9 * wnd), 0.15, 1.25), tc = rnd(0.35, 1.4) * (1.3 - wnd * 0.6);
    AMB.gust = g;
    W.gust.gain.setTargetAtTime(g, t, tc); W.lp.detune.setTargetAtTime((g - 0.62) * 1100, t, tc);
    SS.burst.gain.setTargetAtTime(clamp(g * 0.6, 0.1, 1), t, tc);
    AMB.nextGust = t + rnd(0.4, 1.8);
  }
  if (BEDS.leaves.live && t >= AMB.nextLeaf) { // irregular rustle bursts riding the gusts
    const p = LV.burst.gain;
    p.setTargetAtTime(rnd(0.25, 1) * (0.4 + AMB.gust * 0.6), t, rnd(0.02, 0.06));
    p.setTargetAtTime(rnd(0.05, 0.2), t + rnd(0.06, 0.35), rnd(0.1, 0.3));
    LV.bp.frequency.setTargetAtTime(rnd(2200, 5800), t, 0.05);
    AMB.nextLeaf = t + rnd(0.08, 0.7) / (0.35 + wnd);
  }
  if (BEDS.stream.live && t >= AMB.nextWander) { // babbling: wandering resonances + amplitude flutter
    for (let i = 0; i < 4; i++) {
      ST.bp[i].frequency.setTargetAtTime(rnd(ST.r[i][0], ST.r[i][1]), t, rnd(0.05, 0.25));
      ST.fg[i].gain.setTargetAtTime(rnd(0.3, 1.8), t, rnd(0.02, 0.12));
    }
    AMB.nextWander = t + rnd(0.07, 0.25);
  }
  for (let i = PEND.length - 1; i >= 0; i--) if (PEND[i].t < t + 0.15) { const p = PEND.splice(i, 1)[0]; if (p.t > t - 0.2) p.fn(Math.max(p.t, t + 0.01)); }
  const act = AMB.act * (s.paused ? 0 : 1);
  if (act < 0.02) return;
  const woods = b.forest + 0.6 * b.bamboo + 0.4 * b.shrine, dry = 1 - 0.9 * s.rain;
  maybe("minmin", dayW(h, 9, 16.5, 0.6) * (woods + 0.5 * b.meadow) * dry * act * 0.1, dt, t, evMinmin, 3);
  maybe("higu", (dayW(h, 16.5, 19, 0.35) + dayW(h, 4.5, 5.75, 0.3)) * (woods + 0.25) * dry * act * 0.2, dt, t, evHigurashi, 4);
  maybe("ugu", dayW(h, 5, 11, 0.5) * (b.forest + b.bamboo + 0.5 * b.shrine) * dry * act * 0.035, dt, t, evUguisu, 1);
  maybe("tit", dayW(h, 6, 17, 0.5) * (woods + 0.3) * dry * act * 0.045, dt, t, evTit, 2);
  maybe("crow", dayW(h, 5, 18.8, 0.5) * (1 + dayW(h, 5, 7, 0.5) + dayW(h, 16.5, 18.5, 0.5)) * act * 0.014, dt, t, evCrow, 1);
  maybe("suzu", dayW(h, 19.5, 4.5, 0.5) * (0.4 + b.meadow + 0.6 * b.forest + 0.5 * b.shrine) * (1 - s.rain) * act * 0.9, dt, t, evSuzumushi, 6);
  maybe("kajika", (dayW(h, 18.5, 4.5, 0.5) * 0.8 + 0.25) * s.water * (1 - 0.5 * s.rain) * act * 0.16, dt, t, evKajika, 2);
  maybe("clack", b.bamboo * (0.04 + 0.55 * wnd) * act, dt, t, evClack, 3);
  maybe("furin", b.shrine * (0.05 + 0.4 * wnd) * dayW(h, 6, 22.5, 1) * act * 0.5, dt, t, evFurin, 2);
  maybe("drip", AMB.wet * (0.4 + 2.6 * s.rain) * (b.forest + b.bamboo + 0.3) * act, dt, t, evDrip, 4);
  if (s.rain > 0.7) maybe("thunder", (s.rain - 0.7) * 0.07 * act, dt, t, (tt) => (SFX.thunder({ dist: rnd(0.6, 1), _bus: "ambx" }, { g: 1, pan: rnd(-0.7, 0.7), d: 0 }, tt), 8), 1);
}
function evMinmin(t) { // ミンミンゼミ: "miin-min-min-min-meee"
  const len = rnd(4, 7), f0 = rnd(3200, 3800);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.9, 0.9), rnd(0.035, 0.07), 0.5, rnd(5000, 9000));
    const car = v.o("sine", f0 * 0.9, t, t + len + 0.1), am = v.g(0.5), env = v.g(0);
    chain(v.o("square", rnd(95, 130), t, t + len + 0.1), v.g(0.5), am.gain); // buzzy pulse modulation
    chain(car, am, env, out);
    const p = env.gain, fr = car.frequency, syl = rnd(0.16, 0.22);
    p.setValueAtTime(0, t); fr.setValueAtTime(f0 * 0.9, t);
    p.linearRampToValueAtTime(0.8, t + 0.5); fr.linearRampToValueAtTime(f0, t + 0.5);
    let tt = t + 0.75; p.linearRampToValueAtTime(0.3, tt);
    while (tt < t + len - 1.2) {
      fr.setValueAtTime(f0 * 0.96, tt); fr.linearRampToValueAtTime(f0 * 1.02, tt + syl * 0.4);
      p.linearRampToValueAtTime(1, tt + syl * 0.35); p.linearRampToValueAtTime(0.25, tt + syl);
      tt += syl;
    }
    p.linearRampToValueAtTime(0.9, tt + 0.15); p.linearRampToValueAtTime(0, tt + 1.1); fr.linearRampToValueAtTime(f0 * 0.88, tt + 1.1);
  });
  return len;
}
function evHigurashi(t, chainN = 0) { // ヒグラシ: "kana-kana-kana…", falling and fading; others answer
  const len = rnd(3, 5), f0 = rnd(4200, 5000), rate0 = rnd(7.5, 9.5);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.95, 0.95), rnd(0.03, 0.055), 0.95, rnd(7000, 10000));
    const car = v.o("sine", f0, t, t + len + 0.2), env = v.g(0), nz = v.n("white", t, t + len + 0.2), bp = v.f("bandpass", f0, 9), ng = v.g(0.9);
    chain(car, env, out); chain(nz, bp, ng, env);
    const p = env.gain, fr = car.frequency, bf = bp.frequency;
    let tt = t, k = 0;
    p.setValueAtTime(0, t);
    while (tt < t + len) {
      const u = (tt - t) / len, amp = Math.pow(1 - u, 1.4) * Math.min(1, u / 0.06 + 0.15), per = 1 / (rate0 * (1 - 0.28 * u));
      const f = f0 * (1 - 0.08 * u) * (k % 2 ? 0.982 : 1);
      fr.setValueAtTime(f * 1.03, tt); fr.exponentialRampToValueAtTime(f * 0.965, tt + per * 0.75); bf.setValueAtTime(f, tt);
      p.setValueAtTime(0.0005, tt); p.linearRampToValueAtTime(amp, tt + per * 0.16); p.exponentialRampToValueAtTime(amp * 0.04 + 1e-4, tt + per * 0.88);
      tt += per; k++;
    }
    p.linearRampToValueAtTime(0, tt + 0.05);
  });
  if (chainN < 3 && chance(0.6)) PEND.push({ t: t + len + rnd(-1.2, 1.5), fn: (tt) => { if (AMB.act > 0.1) evHigurashi(tt, chainN + 1); } });
  return len;
}
function evUguisu(t) { // ウグイス: "hoo—— hokekyo"
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.8, 0.8), rnd(0.05, 0.085), 0.6), o = v.o("sine", 1100, t, t + 2.4), g = v.g(0);
    chain(o, g, out);
    const fr = o.frequency, p = g.gain, t2 = t + 0.95 + rnd(0.12, 0.2);
    fr.setValueAtTime(rnd(1050, 1150), t); fr.linearRampToValueAtTime(rnd(1350, 1450), t + 0.9);
    p.setValueAtTime(0, t); p.linearRampToValueAtTime(0.7, t + 0.25); p.linearRampToValueAtTime(0.85, t + 0.85); p.linearRampToValueAtTime(0, t + 0.95);
    for (const [dt, fa, fb, d, a] of [[0, 1650, 1550, 0.11, 0.7], [0.16, 2500, 2420, 0.08, 0.8], [0.29, 3400, 2700, 0.22, 0.9]]) {
      const tt = t2 + dt;
      fr.setValueAtTime(fa, tt); fr.linearRampToValueAtTime(fb, tt + d);
      p.setValueAtTime(0, tt); p.linearRampToValueAtTime(a, tt + 0.015); p.linearRampToValueAtTime(a * 0.7, tt + d - 0.02); p.linearRampToValueAtTime(0, tt + d);
    }
  });
  return 2.5;
}
function evTit(t) { // シジュウカラ: "tsupi-tsupi-tsupi"
  const n = rint(3, 6), per = rnd(0.2, 0.28), f1 = rnd(3800, 4400), f2 = rnd(5600, 6400);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.9, 0.9), rnd(0.025, 0.05), 0.5, 9000), o = v.o("sine", f1, t, t + n * per + 0.2), g = v.g(0);
    chain(o, g, out);
    const fr = o.frequency, p = g.gain;
    p.setValueAtTime(0, t);
    for (let i = 0; i < n; i++) {
      const a = t + i * per, b2 = a + per * 0.45;
      fr.setValueAtTime(f1 * 1.05, a); fr.linearRampToValueAtTime(f1 * 0.92, a + 0.06);
      p.setValueAtTime(0, a); p.linearRampToValueAtTime(0.6, a + 0.01); p.linearRampToValueAtTime(0, a + 0.065);
      fr.setValueAtTime(f2, b2); fr.linearRampToValueAtTime(f2 * 0.96, b2 + 0.05);
      p.setValueAtTime(0, b2); p.linearRampToValueAtTime(0.8, b2 + 0.008); p.linearRampToValueAtTime(0, b2 + 0.055);
    }
  });
  return n * per + 0.2;
}
function evCrow(t) {
  let d = 1.5;
  play("bg", (v) => { d = caw(v, ambOut(v, rnd(-0.9, 0.9), rnd(0.05, 0.09), 0.7, 2600), t, rint(1, 3), rnd(470, 540)); });
  return d;
}
function evSuzumushi(t) { // スズムシ: "riiin" — a tiny bell trill
  const len = rnd(1, 2), f = rnd(4300, 4600);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-1, 1), rnd(0.012, 0.028), 0.5, 8000), o = v.o("sine", f, t, t + len + 0.1), am = v.g(0.5), env = v.g(0);
    chain(v.o("sine", rnd(38, 48), t, t + len + 0.1), v.g(0.5), am.gain);
    chain(o, am, env, out);
    const p = env.gain;
    p.setValueAtTime(0, t); p.linearRampToValueAtTime(1, t + 0.06); p.linearRampToValueAtTime(0.7, t + len - 0.15); p.linearRampToValueAtTime(0, t + len);
  });
  return len;
}
function evKajika(t) { // カジカガエル: "fi-fi-fi-fiiii", bird-like over the water
  const n = rint(4, 8), base = rnd(1800, 2100);
  let tt = t, per = rnd(0.16, 0.22);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.8, 0.8), rnd(0.04, 0.07), 0.6), o = v.o("sine", base, t, t + 3), g = v.g(0);
    chain(o, g, out);
    const fr = o.frequency, p = g.gain;
    p.setValueAtTime(0, t);
    for (let i = 0; i < n; i++) {
      const f = base * (1 + i * 0.035), d = per * 0.55;
      fr.setValueAtTime(f * 0.97, tt); fr.linearRampToValueAtTime(f * 1.02, tt + d);
      p.setValueAtTime(0, tt); p.linearRampToValueAtTime(0.7, tt + 0.012); p.linearRampToValueAtTime(0, tt + d);
      tt += per; per *= 0.9;
    }
    const f = Math.min(2600, base * 1.28);
    fr.setValueAtTime(f * 0.96, tt); fr.linearRampToValueAtTime(f, tt + 0.1);
    for (let j = 0; j < 4; j++) fr.linearRampToValueAtTime(f * (j % 2 ? 1.012 : 0.988), tt + 0.18 + j * 0.1);
    p.setValueAtTime(0, tt); p.linearRampToValueAtTime(0.85, tt + 0.03); p.linearRampToValueAtTime(0.6, tt + 0.5); p.linearRampToValueAtTime(0, tt + 0.62);
    tt += 0.7;
  });
  return tt - t;
}
function evClack(t) { // bamboo culms knocking: "kon-koro"
  const n = rint(1, 3), r = rnd(0.6, 1.3);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.9, 0.9), rnd(0.06, 0.14), 0.5);
    for (let i = 0; i < n; i++) bufTo(v, "wood", t + i * rnd(0.06, 0.15), r * rnd(0.97, 1.08), 1 - i * 0.25, out);
  });
  return 0.6;
}
function evFurin(t) { // shrine wind chime (風鈴)
  const n = rint(1, 3), r = pick([1, 1.122, 0.89]);
  play("bg", (v) => {
    const out = ambOut(v, rnd(-0.6, 0.6), rnd(0.05, 0.1), 0.5);
    for (let i = 0; i < n; i++) bufTo(v, "glass", t + i * rnd(0.12, 0.3), r * rnd(0.995, 1.005), 1 - i * 0.3, out);
  });
  return 2;
}
function evDrip(t) { // leaf drip patter
  play("bg", (v) => {
    const out = ambOut(v, rnd(-1, 1), rnd(0.02, 0.06), 0.3), f = rnd(1500, 3500), o = v.o("sine", f, t, t + 0.05), g = v.g(0);
    o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * rnd(1.2, 1.6), t + 0.02);
    perc(g.gain, t, 0.001, 1, 0.025); chain(o, g, out);
  });
  return 0.05;
}

/* =====================================================================
   MUSIC — lookahead sequencer, motif tools, generative pieces
   ===================================================================== */
// Tsuzura's leitmotif, yo scale on D. [midi, beats]; 0 = rest; -1 = THE HOLE: the tenth
// note of her count never sounds (she never reaches a hundred). Bar 2 is 5 beats as written.
const M1 = [[69, 0.5], [71, 0.5], [74, 1], [71, 0.5], [69, 0.5], [67, 1]];
const M2 = [[64, 0.5], [67, 0.5], [69, 1.5], [67, 0.5], [64, 2]];
const M3 = [[62, 0.5], [64, 0.5], [67, 0.5], [69, 0.5], [71, 0.5], [74, 0.5], [76, 0.5], [79, 0.5]];
const M4 = [[81, 0.5], [-1, 0.5], [71, 0.5], [69, 1.5], [0, 1]];
const MOTIF = [...M1, ...M2, ...M3, ...M4]; // 17 beats
const CADENCE = [[0, 0.5], [64, 0.5], [67, 0.5], [62, 2.5]];
const MUS = { cur: null, name: "none", prev: "none" };

// Append a melodic line to ev. o: {v, tr, ds (diatonic shift), st (stretch), leg, drop, grace, bend, hole}
function line(ev, inst, b0, notes, o = {}) {
  let b = b0;
  for (const [m0, d0] of notes) {
    const d = d0 * (o.st || 1);
    if (m0 === -1) { if (o.hole !== false) ev.push({ b, i: "hole", d }); }
    else if (m0 > 0 && !(o.drop && chance(o.drop))) {
      const m = (o.ds ? dshift(m0, o.ds) : m0) + (o.tr || 0);
      const e = { b, i: inst, m, d: d * (o.leg || 0.92), v: (o.v || 0.6) * rnd(0.9, 1.05) };
      if (o.bend && d0 >= 1 && chance(o.bend)) e.o = { bend: dshift(m, 1) - m }; // press up to the next yo note
      ev.push(e);
      if (o.grace && d0 >= 1 && b - b0 >= 0.25 && chance(o.grace)) ev.push({ b: b - 0.13, i: inst, m: dshift(m, 1), d: 0.12, v: e.v * 0.55 });
    }
    b += d;
  }
  return b;
}
// Koto + pad accompaniment under the 17-beat motif. The low koto counts along in bar 3.
function accomp(ev, b0, v, padV) {
  const K = (b, m, vv) => ev.push({ b: b0 + b, i: "koto", m, d: 1, v: vv === undefined ? v : vv });
  K(0, 55); K(0, 62, v * 0.7); K(2, 62, v * 0.6);
  K(4, 52); K(4, 59, v * 0.7); K(6.5, 57, v * 0.55); K(8, 55, v * 0.5);
  [50, 50, 52, 52, 55, 55, 57, 57].forEach((m, j) => K(9 + j * 0.5, m, v * (0.45 + j * 0.05)));
  K(13, 45); K(13, 57, v * 0.8); K(14, 43, v * 0.7); K(14, 50, v * 0.6); K(14.5, 57, v * 0.5);
  if (!padV) return;
  const P = (b, ms, d, vv, att, rel) => ev.push({ b: b0 + b, i: "pad", ms, d, v: vv, o: { att, rel } });
  P(0, [55, 62, 69], 4, padV, 1.2, 1.5); P(4, [52, 59, 64], 5, padV, 1.2, 1.5);
  P(9, [50, 57, 64], 4, padV * 0.8, 1.5, 0.4); P(14, [43, 50, 57, 64], 3, padV, 0.8, 2.5);
}
function shimeLight(ev, b0, beats, v, dense) {
  for (let b = 0; b < beats; b++) {
    if (b % 2 === 1 || dense) ev.push({ b: b0 + b, i: "shime", v: v * (b % 2 ? 1 : 0.6), r: rnd(0.98, 1.02) });
    if (dense && b % 2 === 1) ev.push({ b: b0 + b + 0.5, i: "shime", v: v * 0.5 });
  }
}
// Remove everything that would sound inside a hole: the missing beat must be felt by all parts.
function carve(ev) {
  const holes = ev.filter((e) => e.i === "hole");
  if (!holes.length) return ev;
  return ev.filter((e) => e.i === "hole" || !holes.some((h) => e.b >= h.b - 0.01 && e.b < h.b + h.d - 0.01));
}

const PIECES = {
  title(k) { // full statement, ~70 s per pass, loops with variation
    const sec = k % 6, alt = ((k / 6) | 0) % 2 === 1, ev = [];
    let beats = 17;
    if (sec === 0) {
      ev.push({ b: 0, i: "pad", ms: [50, 57, 64], d: 8, v: 0.12, o: { att: 3, rel: 3, cut: 800 } }, { b: 0, i: "rin", v: 0.1 });
      const arp = alt ? [62, 69, 74, 76, 69, 74, 71, 69] : [62, 69, 74, 69, 76, 74, 69, 67];
      for (let j = 2; j < 16; j++) ev.push({ b: j * 0.5, i: "koto", m: arp[j % 8], d: 1, v: j % 2 ? 0.22 : 0.32 });
      beats = 8;
    } else if (sec === 1) {
      const lead = alt ? "koto" : "flute";
      line(ev, lead, 0, MOTIF, { v: 0.62, grace: 0.25, bend: 0.2 });
      accomp(ev, 0, 0.3, 0.09);
    } else if (sec === 2) {
      line(ev, "koto", 0, MOTIF, { v: 0.6, tr: alt ? 12 : 0, grace: 0.2, bend: 0.2 });
      line(ev, "flute", 0, [[74, 4], [71, 4.5]], { v: 0.36, leg: 0.97 });
      accomp(ev, 0, 0.25, 0.08); shimeLight(ev, 0, 17, 0.14, false);
    } else if (sec === 3) { // development: the motif climbs diatonically, the flute answers
      line(ev, "koto", 0, M1, { v: 0.55, ds: 1 }); line(ev, "koto", 4, M1, { v: 0.5, ds: 2, drop: 0.15 });
      line(ev, "flute", 8, M2, { v: 0.55, ds: -1 }); line(ev, "flute", 13, [[74, 1], [76, 1], [74, 1]], { v: 0.45 });
      [[0, [55, 62, 69]], [4, [52, 59, 64]], [8, [57, 64, 71]], [12, [50, 57, 64]]].forEach(([b, ms]) => ev.push({ b, i: "pad", ms, d: 4, v: 0.1 }));
      for (let b = 0; b < 16; b += 4) ev.push({ b, i: "odaiko", v: 0.22 });
      shimeLight(ev, 0, 16, 0.16, true);
      beats = 16;
    } else if (sec === 4) { // tutti: flute + low koto in octaves; all fall silent in the hole
      line(ev, "flute", 0, MOTIF, { v: 0.7, grace: 0.3 });
      line(ev, "koto", 0, MOTIF, { v: 0.45, tr: -12, hole: false });
      accomp(ev, 0, 0.28, 0.1); shimeLight(ev, 0, 17, 0.16, true);
      [0, 4, 9, 13].forEach((b) => ev.push({ b, i: "odaiko", v: 0.25 }));
    } else { // coda: resolve to D, harmonics like stars, then breathe
      ev.push({ b: 0, i: "pad", ms: [50, 57, 62, 69], d: 6, v: 0.13, o: { att: 1, rel: 4 } }, { b: 0, i: "rin", v: 0.12 }, { b: 0.5, i: "flute", m: 74, d: 4, v: 0.45 });
      [[0, 74], [1.5, 81], [3, 88]].forEach(([b, m]) => ev.push({ b, i: "harm", m, v: 0.4 }));
      beats = 12;
    }
    return { ev, beats, bpm: 72 };
  },
  prologue(k) { // dusk at the shrine: slow, low, leaves the high register to the higurashi
    const sec = k % 4, thin = Math.min(0.5, ((k / 4) | 0) * 0.16), ev = [];
    let beats = 10;
    if (sec === 0) {
      [[0, 38, 0.5], [0, 45, 0.35], [3, 45, 0.3], [5, 50, 0.3]].forEach(([b, m, v]) => ev.push({ b, i: "sham", m, v }));
      ev.push({ b: 2, i: "harm", m: 69, v: 0.3 }, { b: 6.5, i: "harm", m: 74, v: 0.25 }, { b: 0, i: "pad", ms: [38, 45], d: 8, v: 0.08, o: { att: 3, rel: 3, cut: 500 } });
      beats = 9;
    } else if (sec === 1) {
      line(ev, "sham", 0, [...M1, ...M2], { v: 0.55, tr: -12, drop: thin * 0.5 });
      [[0, 43], [4, 40], [6.5, 45]].forEach(([b, m]) => { if (!chance(thin)) ev.push({ b, i: "koto", m, v: 0.3 }); });
      beats = 12;
    } else if (sec === 2) { // the counting motif, featured
      line(ev, "koto", 0, [...M3, ...M4], { v: 0.5, drop: thin * 0.3 });
      ev.push({ b: 0, i: "sham", m: 38, v: 0.4 }, { b: 4, i: "sham", m: 38, v: 0.3 });
    } else {
      line(ev, "sham", 0, M1.slice(0, 3), { v: 0.5, tr: -12, drop: thin });
      line(ev, "koto", 3, [[71, 1], [69, 1], [67, 2]], { v: 0.4, drop: thin });
      if (!chance(thin)) ev.push({ b: 7, i: "harm", m: 74, v: 0.25 });
    }
    return { ev, beats, bpm: 60 };
  },
  explore(k) { // mostly silence; a short phrase every 25–70 s, coloured by the hour
    if (k % 2 === 0) return { ev: [], beats: k === 0 ? rnd(8, 22) : rnd(25, 70), bpm: 60 };
    const h = S.tod, ev = [], mode = h >= 5 && h < 11 ? 0 : h >= 11 && h < 16.5 ? 1 : h >= 16.5 && h < 19.5 ? 2 : 3;
    const notes = [].concat(...pick([[M1, M2], [M3, M4], [M1, M3, M4], [M1, CADENCE]]));
    const ds = chance(0.3) ? pick([-1, 1, 2]) : 0;
    let bpm = 84, end;
    if (mode === 0) { // morning: flute over a light koto
      end = line(ev, "flute", 0, notes, { v: 0.5, ds, grace: 0.3 });
      for (let b = 0; b < end - 1; b += 4) { const [r, f] = pick([[50, 57], [55, 62], [52, 59]]); ev.push({ b, i: "koto", m: r, v: 0.24 }, { b: b + 0.06, i: "koto", m: f, v: 0.18 }); }
      end += 3;
    } else if (mode === 1) { bpm = 80; end = line(ev, "koto", 0, notes, { v: 0.45, ds, drop: 0.25, st: 1.25, bend: 0.25 }) + 3; } // noon: koto alone, sparse
    else if (mode === 2) { bpm = 64; end = line(ev, "sham", 0, notes, { v: 0.5, ds, tr: -12, drop: 0.1 }); ev.push({ b: end, i: "harm", m: 74, v: 0.22 }); end += 4; } // dusk
    else { bpm = 60; end = line(ev, chance(0.5) ? "cel" : "harm", 0, notes, { v: 0.35, ds, tr: chance(0.5) ? 12 : 0, drop: 0.15 }) + 4; } // night
    if (chance(mode === 1 ? 0.2 : 0.5)) ev.push({ b: 0, i: "pad", ms: mode === 2 ? [38, 45] : [50, 57], d: end - 2, v: mode === 3 ? 0.05 : 0.07, o: { att: 3, rel: 3, cut: 600 } });
    return { ev, beats: end, bpm };
  },
  home(k) { // warm, slow koto arpeggios; the flute sings every other pass
    const ev = [], chords = [[50, 57, 62, 64, 69, 64, 62, 57], [43, 50, 55, 57, 62, 57, 55, 50], [40, 47, 52, 55, 59, 55, 52, 47], [45, 52, 57, 59, 64, 59, 57, 52]];
    chords.forEach((c, j) => c.forEach((m, i) => ev.push({ b: j * 4 + i * 0.5, i: "koto", m, d: 1, v: (i === 0 ? 0.32 : 0.19) * rnd(0.85, 1.05) })));
    if (k % 2 === 1) line(ev, "flute", 0, [...M1, ...M2], { v: 0.38, leg: 0.97 });
    else if (k % 4 === 2) line(ev, "flute", 4, [...M3, ...M4], { v: 0.34 });
    if (chance(0.5)) ev.push({ b: 15, i: "cel", m: pick([86, 88, 91]), v: 0.2 });
    ev.push({ b: 0, i: "pad", ms: [50, 57, 64], d: 15, v: 0.06, o: { att: 4, rel: 3, cut: 650 } });
    return { ev, beats: 16, bpm: 60 };
  },
  tension(k) { // the Far Wave approaches: drone, rising cluster, irregular heart-taiko, breath
    const ev = [];
    if (k === 0) {
      ev.push({ b: 0, i: "held", ms: [26, 38], v: 0.3, o: { sub: true, att: 4, cut0: 200 } });
      ev.push({ b: 0, i: "held", ms: [45, 46, 48, 51], v: 0.16, o: { att: 30, rise: 5, over: 40, spread0: 5, spread1: 28, cut0: 220, cut1: 1800 } });
      for (let b = 2; b < 40;) { const u = b / 40; ev.push({ b, i: "heart", v: 0.25 + 0.45 * u }); b += lerp(1.7, 0.66, u) * rnd(0.85, 1.25) + (chance(0.1) ? 0.6 : 0); }
      for (let b = rnd(3, 6); b < 40; b += rnd(3.5, 7) * (1 - b / 80)) ev.push({ b, i: "breath", d: rnd(1.2, 2), v: 0.06 + (0.1 * b) / 40, inh: chance(0.5) });
      return { ev, beats: 40, bpm: 60 };
    }
    for (let b = 0; b < 8; b += 0.66 * rnd(0.9, 1.15)) ev.push({ b, i: "heart", v: 0.7 });
    ev.push({ b: rnd(0, 4), i: "breath", d: 1.6, v: 0.16, inh: chance(0.5) });
    if (chance(0.4)) ev.push({ b: 4, i: "odaiko", v: 0.18 });
    return { ev, beats: 8, bpm: 60 };
  },
  wonder(k) { // a vista: pad swell, koto runs, the flute reaches — and this time resolves
    if (k > 0) return null;
    const ev = [], run = [62, 64, 67, 69, 71, 74, 76, 79];
    ev.push({ b: 0, i: "pad", ms: [50, 57, 64, 71], d: 22, v: 0.15, o: { att: 5, rel: 5, cut: 1300 } }, { b: 0, i: "rin", v: 0.12 });
    for (let bar = 0; bar < 4; bar++) run.forEach((m, j) => ev.push({ b: bar * 4 + j * 0.25, i: "koto", m, d: 1, v: (0.18 + j * 0.02) * (bar === 3 ? 0.7 : 1) }));
    line(ev, "flute", 4, M1, { v: 0.55, st: 1.5 });
    line(ev, "flute", 10, [...M3, [81, 0.5], [-1, 0.5], [74, 5]], { v: 0.6 });
    ev.push({ b: 16, i: "rin", v: 0.1 }, { b: 16, i: "pad", ms: [43, 50, 57, 62], d: 8, v: 0.12, o: { att: 3, rel: 5 } });
    [[18, 86], [19.5, 81], [21, 79]].forEach(([b, m]) => ev.push({ b, i: "harm", m, v: 0.3 }));
    return { ev, beats: 28, bpm: 70 };
  },
};

function mkPiece(name) {
  const P = { name, gen: PIECES[name], k: 0, seg: null, segT: 0, i: 0, nextT: ctx.currentTime + 0.15, held: [], strips: {}, nodes: [], dead: false };
  P.g = G(0); P.h = G(1); P.wg = G(0); P.wh = G(1);
  chain(P.g, P.h, BUS.music.inp); chain(P.wg, P.wh, BUS.music.wet);
  P.nodes.push(P.g, P.h, P.wg, P.wh);
  return P;
}
function strip(P, name, pan, wet) {
  let s = P.strips[name];
  if (!s) {
    const i = G(1), p = ctx.createStereoPanner(), w = G(wet);
    p.pan.value = pan; chain(i, p, P.g); chain(p, w, P.wg);
    s = P.strips[name] = { i }; P.nodes.push(i, p, w);
  }
  return s;
}
function pieceFade(P, v, secs) {
  const t = ctx.currentTime;
  for (const p of [P.g.gain, P.wg.gain]) { holdAt(p, t); if (secs > 0.02) p.setTargetAtTime(v, t, secs / 3); else p.setValueAtTime(v, t); }
}
function pieceKill(P, fade) {
  P.dead = true;
  pieceFade(P, 0, fade);
  for (const h of P.held) if (h) h.stop(ctx.currentTime + fade);
  setTimeout(() => { for (const n of P.nodes) { try { n.disconnect(); } catch (e) { /* ignore */ } } }, (fade * 1.6 + 4.5) * 1000);
}
function musicSet(name, fade, restart) {
  if (name !== "none" && !PIECES[name]) return;
  if (name === MUS.name && !restart) return;
  const old = MUS.cur;
  if (old) pieceKill(old, Math.max(0.05, fade));
  MUS.prev = MUS.name; MUS.name = name; MUS.cur = null;
  if (name === "none") return;
  const P = mkPiece(name);
  pieceFade(P, 1, old ? Math.max(0.05, fade * 0.6) : 0.05);
  MUS.cur = P;
}
function musicEnded(P) { // a one-shot piece (wonder) finished: hand back to silence / exploration
  if (MUS.cur !== P) return;
  const back = MUS.prev === "explore" ? "explore" : "none";
  MUS.cur = null; MUS.name = "none";
  pieceKill(P, 4);
  if (back !== "none") musicSet(back, 0.1);
}
function hole(P, t, d) { // the missing tenth: every part holds its breath
  for (const p of [P.h.gain, P.wh.gain]) { p.setTargetAtTime(0.08, t - 0.01, 0.012); p.setTargetAtTime(1, t + d - 0.02, 0.025); }
}
function playEv(P, e, t, spb) {
  const d = (e.d || 1) * spb, v = e.v === undefined ? 0.6 : e.v;
  switch (e.i) {
    case "koto": koto(t, e.m, d, v, strip(P, "koto", -0.2, 0.28), e.o); break;
    case "sham": sham(t, e.m, d, v, strip(P, "sham", 0.12, 0.24)); break;
    case "flute": flute(t, e.m, d, v, strip(P, "flute", 0.22, 0.4), e.o || {}); break;
    case "cel": cel(t, e.m, d, v, strip(P, "cel", 0.08, 0.45)); break;
    case "harm": harm(t, e.m, d, v, strip(P, "harm", -0.1, 0.5)); break;
    case "pad": pad(t, e.ms, d, v, strip(P, "pad", 0, 0.35), e.o || {}); break;
    case "hole": hole(P, t, d); break;
    case "heart": heart(t, v, strip(P, "drum", 0, 0.3)); break;
    case "breath": breath(t, d, v, strip(P, "breath", 0, 0.5), e.inh); break;
    case "held": { const h = held(t, e.ms, v, strip(P, "pad", 0, 0.35), e.o || {}); if (h) P.held.push(h); break; }
    default: if (SND[e.i]) hit(t, e.i, v, strip(P, "perc", 0, 0.3), e.r || 1);
  }
}
function musicTick(t, ahead) {
  const P = MUS.cur;
  if (!P || P.dead) return;
  for (let guard = 0; guard < 64; guard++) {
    if (!P.seg) {
      let seg = null;
      try { seg = P.gen(P.k++); } catch (e) { seg = null; }
      if (!seg) { musicEnded(P); return; }
      seg.ev = carve(seg.ev).sort((a, b) => a.b - b.b);
      P.seg = seg; P.i = 0; P.segT = Math.max(P.nextT, t);
    }
    const seg = P.seg, spb = 60 / seg.bpm;
    while (P.i < seg.ev.length) {
      const e = seg.ev[P.i], when = P.segT + e.b * spb;
      if (when > ahead) return;
      P.i++;
      if (when < t - 0.08) continue; // too late (tab asleep): drop rather than pile up
      try { playEv(P, e, Math.max(when, t + 0.005), spb); } catch (err) { /* ignore */ }
    }
    const end = P.segT + seg.beats * spb;
    if (end > ahead) return;
    P.nextT = end; P.seg = null;
  }
}

/* =====================================================================
   FAR FESTIVAL — generated 祭囃子, heard from impossibly far away
   ===================================================================== */
// Shinobue melody in a minyō/ritsu colour on D (D F G A C). 16 bars of [midi, 16ths]; 0 = breath.
const FMEL = [
  [[86, 4], [84, 2], [81, 2], [84, 2], [86, 2], [81, 4]], [[79, 2], [81, 2], [84, 2], [81, 2], [79, 2], [77, 2], [74, 4]],
  [[77, 2], [79, 2], [81, 4], [84, 2], [81, 2], [79, 2], [81, 2]], [[86, 6], [84, 2], [81, 8]],
  [[81, 2], [84, 2], [86, 2], [89, 2], [86, 2], [84, 2], [81, 4]], [[84, 2], [81, 2], [79, 2], [77, 2], [79, 4], [81, 4]],
  [[74, 2], [77, 2], [79, 2], [81, 2], [84, 2], [81, 2], [79, 2], [77, 2]], [[74, 12], [0, 4]],
  [[86, 2], [89, 2], [91, 4], [89, 2], [86, 2], [84, 4]], [[86, 2], [84, 2], [81, 2], [84, 2], [86, 8]],
  [[89, 2], [86, 2], [84, 2], [86, 2], [81, 4], [79, 4]], [[81, 2], [84, 2], [86, 4], [84, 2], [81, 2], [79, 4]],
  [[77, 2], [79, 2], [81, 2], [84, 2], [86, 4], [84, 2], [86, 2]], [[89, 4], [86, 2], [84, 2], [81, 4], [84, 4]],
  [[86, 2], [84, 2], [81, 2], [79, 2], [77, 2], [79, 2], [81, 4]], [[74, 8], [0, 8]],
];
const FSTEP = new Array(256).fill(null);
{ let s = 0; for (const bar of FMEL) for (const [m, d] of bar) { if (s < 256) FSTEP[s] = [m, d]; s += d; } }
const FSC = [74, 77, 79, 81, 84, 86, 89, 91, 93, 96];
const fUp = (m) => FSC.find((x) => x > m) || m + 2;
// 16-step drum patterns. Shime: テン テン ツク テン ツク テン テン ツク / テケ テン テケ テン…  Kane: チャン チキ …
const SHIME_A = [0.9, 0, 0.7, 0, 0.6, 0.45, 0.8, 0, 0.6, 0.45, 0.75, 0, 0.85, 0, 0.6, 0.45];
const SHIME_B = [0.85, 0.5, 0.8, 0, 0.6, 0.45, 0.8, 0, 0.9, 0, 0.8, 0, 0.6, 0.45, 0.6, 0.45];
const KANE = [0.8, 0, 0.45, 0.35, 0.8, 0, 0.45, 0.35, 0.8, 0, 0.45, 0.35, 0.8, 0, 0.45, 0.35];
const FEST = { a: 0, near: 0, n: null, t: 0, step: 0, bpm: 108, tune: 1.0035 };

function festStart() {
  const t = ctx.currentTime, n = { nodes: [], stopping: false, nextGust: t, nextPan: t, nextPhase: t + rnd(6, 12), choir: null };
  const k = (x) => (n.nodes.push(x), x);
  const osc = (type, f) => { const o = k(ctx.createOscillator()); o.type = type; o.frequency.value = f; o.start(t); return o; };
  n.src = k(G(0.9)); n.tap = k(G(1)); n.src.connect(n.tap); // dry mix; tap feeds the radio
  // Far chain: slow pitch wow (±12 c) → [near: chorus] [sometimes: phasing] → steep lowpass → wind gusts → drifting pan
  n.wow = k(ctx.createDelay(0.2)); n.wow.delayTime.value = 0.03;
  chain(osc("sine", 0.13), k(G(0.0085)), n.wow.delayTime); chain(osc("sine", 0.047), k(G(0.004)), n.wow.delayTime);
  n.ch = k(ctx.createDelay(0.2)); n.ch.delayTime.value = 0.022; chain(osc("sine", 0.83), k(G(0.0026)), n.ch.delayTime);
  n.ph = k(ctx.createDelay(0.05)); n.ph.delayTime.value = 0.004; chain(osc("sine", 0.09), k(G(0.0028)), n.ph.delayTime);
  n.chG = k(G(0)); n.phG = k(G(0));
  n.lp1 = k(BQ_("lowpass", 700, 0)); n.lp2 = k(BQ_("lowpass", 900, -3));
  n.gust = k(G(0.7)); n.pan = k(ctx.createStereoPanner()); n.out = k(G(0)); n.dry = k(G(0.25)); n.wet = k(G(1));
  chain(n.src, n.wow, n.lp1); chain(n.src, n.ch, n.chG, n.lp1); chain(n.src, n.ph, n.phG, n.lp1);
  chain(n.lp1, n.lp2, n.gust, n.pan, n.out); chain(n.out, n.dry, BUS.far.inp); chain(n.out, n.wet, BUS.far.fwet);
  // The shinobue: a single legato voice steered by automation (no per-note nodes).
  n.fo = k(ctx.createOscillator()); n.fo.setPeriodicWave(FIFEW); n.fo.frequency.value = mtof(74); n.fo.start(t);
  n.vg = k(G(0)); chain(osc("sine", 5.7), n.vg, n.fo.detune);
  n.fg = k(G(0)); chain(n.fo, n.fg, n.src);
  const nz = k(ctx.createBufferSource()); nz.buffer = NZ.white; nz.loop = true; nz.start(t, rnd(0, 2));
  n.fbp = k(BQ_("bandpass", 1600, 1.4)); n.fbr = k(G(0.6)); chain(nz, n.fbp, n.fbr, n.fg);
  const pn = (p) => { const x = k(ctx.createStereoPanner()); x.pan.value = p; x.connect(n.src); return { i: x }; };
  n.shP = pn(-0.3); n.kaP = pn(0.35); n.odP = pn(0.05);
  FEST.n = n; FEST.t = t + 0.08; FEST.step = 0;
}
function choirStart(n) { // near=1: a low formant "choir" on a D-minor-ish cluster under the joy
  const t = ctx.currentTime, k = (x) => (n.nodes.push(x), x), mix = k(G(1)), c = { g: k(G(0)) };
  for (const m of [50, 53, 57, 64]) for (const d of [-9, 8]) {
    const o = k(ctx.createOscillator()); o.type = "sawtooth"; o.frequency.value = mtof(m); o.detune.value = d + rnd(-3, 3); o.start(t); o.connect(mix);
  }
  c.f = [[730, 7, 1], [1090, 8, 0.5], [2440, 9, 0.22]].map(([f, q, a]) => { const b = k(BQ_("bandpass", f, q)); chain(mix, b, k(G(a)), c.g); return b; });
  c.g.connect(n.lp1);
  n.choir = c;
}
function festStop() { // fade, then tear everything down: the scheduler idles at intensity 0
  const n = FEST.n;
  if (!n) return;
  FEST.n = null; n.stopping = true;
  const t = ctx.currentTime;
  for (const p of [n.out.gain, n.fg.gain]) { holdAt(p, t); p.setTargetAtTime(0, t, 0.4); }
  setTimeout(() => {
    for (const x of n.nodes) { try { if (x.stop) x.stop(); } catch (e) { /* ignore */ } try { x.disconnect(); } catch (e) { /* ignore */ } }
    n.nodes = [];
  }, 3500);
}
function festParams() {
  const n = FEST.n;
  if (!n) return;
  const a = FEST.a, nr = FEST.near, on = a > 0.001;
  const cut = Math.exp(lerp(Math.log(expMap(450, 2500, sstep(0, 1, a))), Math.log(19000), nr * nr));
  tgt(n.lp1.frequency, nyq(cut), 0.5); tgt(n.lp2.frequency, nyq(cut * 1.25), 0.5);
  tgt(n.out.gain, on ? Math.pow(a, 1.2) * lerp(0.35, 0.85, nr) : 0, 0.6);
  tgt(n.dry.gain, lerp(0.25, 0.95, nr), 0.5); tgt(n.wet.gain, lerp(1, 0.45, nr), 0.5); tgt(n.chG.gain, nr * 0.7, 0.5);
  FEST.tune = 1.0035 + nr * 0.004; // a touch sharp: joyful, and wrong
  if (on && nr > 0.02 && !n.choir) choirStart(n);
  if (n.choir) tgt(n.choir.g.gain, on ? Math.pow(nr, 1.5) * 0.3 * a : 0, 0.8);
}
function festSync() {
  if (FEST.a > 0.001 || RADIO.on) { if (!FEST.n) festStart(); festParams(); }
  else if (FEST.n) festStop();
}
function fifeNote(n, t, m, dur) {
  const g = n.fg.gain, lvl = 0.2;
  if (!m) { g.setTargetAtTime(0, t, 0.035); return; }
  const f = mtof(m) * FEST.tune, fr = n.fo.frequency;
  if (dur > 0.25 && chance(0.35)) fr.setTargetAtTime(mtof(fUp(m)) * FEST.tune, t - 0.055, 0.004); // grace from above
  fr.setTargetAtTime(f, t, 0.006);
  n.fbp.frequency.setTargetAtTime(nyq(f * 1.4), t, 0.01);
  g.setTargetAtTime(lvl * 0.45, t - 0.02, 0.006); g.setTargetAtTime(lvl, t + 0.01, 0.018); // finger "uchi"
  n.fbr.gain.setTargetAtTime(1.6, t, 0.004); n.fbr.gain.setTargetAtTime(0.6, t + 0.035, 0.05); // breath accent
  n.vg.gain.setTargetAtTime(0, t, 0.01);
  if (dur > 0.4) n.vg.gain.setTargetAtTime(16, t + 0.16, 0.12);
}
function festStep(n, t, st, s16) {
  const bar = st >> 4, pos = st & 15, tt = t + (pos % 4 === 2 ? s16 * 0.2 : 0); // lilting swing on the off-8ths
  const sh = ((bar & 3) === 3 ? SHIME_B : SHIME_A)[pos];
  if (sh) hit(tt + rnd(-0.004, 0.006), "shime", sh * 0.32, n.shP, rnd(0.97, 1.03));
  const ka = KANE[pos];
  if (ka) hit(tt + rnd(-0.003, 0.008), ka > 0.6 ? "kaneO" : "kaneD", ka * 0.16, n.kaP, rnd(0.985, 1.015));
  let od = 0;
  if (pos === 0) od = 1;
  else if (pos === 8 && bar & 1) od = 0.75;
  else if ((bar & 3) === 3 && (pos === 12 || pos === 14)) od = pos === 12 ? 0.7 : 0.5;
  if (od) hit(tt, "odaiko", od * 0.45, n.odP, rnd(0.98, 1.02));
  const mn = FSTEP[st];
  if (mn) fifeNote(n, tt, mn[0], mn[1] * s16);
}
function festTick(t, ahead) {
  const n = FEST.n;
  if (!n) return;
  const s16 = 60 / FEST.bpm / 4, nr = FEST.near;
  if (FEST.t < t - 0.25) FEST.t = t + 0.05;
  for (let guard = 0; FEST.t < ahead && guard < 48; guard++) {
    festStep(n, FEST.t, FEST.step, s16);
    FEST.t += s16 * (chance(0.003) ? 1.5 : 1); // now and then the music stumbles
    FEST.step = (FEST.step + 1) & 255;
  }
  if (t >= n.nextGust) { // carried by the wind
    n.gust.gain.setTargetAtTime(lerp(rnd(0.22, 1), rnd(0.85, 1), nr), t, rnd(0.5, 2.2));
    n.nextGust = t + rnd(0.6, 2.8);
  }
  if (t >= n.nextPan) {
    n.pan.pan.setTargetAtTime(rnd(-0.7, 0.7) * (1 - 0.6 * nr), t, rnd(2, 5));
    n.nextPan = t + rnd(3, 8);
  }
  if (t >= n.nextPhase) {
    const d = rnd(3, 6);
    n.phG.gain.setTargetAtTime(rnd(0.35, 0.6), t, 0.8); n.phG.gain.setTargetAtTime(0, t + d, 1.2);
    if (n.choir) for (const [i, b] of n.choir.f.entries()) b.frequency.setTargetAtTime(nyq([rnd(430, 760), rnd(800, 1150), rnd(2300, 2600)][i]), t, 2.5);
    n.nextPhase = t + d + rnd(6, 16);
  }
}

/* =====================================================================
   RADIO — a broken transistor radio by the shrine
   ===================================================================== */
const RADIO = { on: false, x: NaN, y: NaN, sig: 0.6, n: null };
let SATCURVE = null;
function radioStart() {
  const t = ctx.currentTime, n = { nodes: [], next: t + rnd(1, 3), nextFl: t, tapOf: null, crk: null };
  const k = (x) => (n.nodes.push(x), x);
  n.out = k(G(0)); n.pan = k(ctx.createStereoPanner());
  chain(n.out, n.pan, BUS.sfx.inp); chain(n.pan, k(G(0.12)), BUS.sfx.wet);
  n.mix = k(G(1)); chain(n.mix, k(BQ_("highpass", 330, 4)), k(BQ_("lowpass", 3200, 5)), k(BQ_("peaking", 1200, 1.5, 4)), n.out); // tiny speaker
  const nz = k(ctx.createBufferSource()); nz.buffer = NZ.white; nz.loop = true; nz.start(t, rnd(0, 2));
  n.stG = k(G(0)); n.stS = k(G(1)); chain(nz, k(BQ_("bandpass", 1900, 0.6)), n.stG, n.stS, n.mix);
  n.crG = k(G(0.3)); n.crG.connect(n.mix);
  n.fIn = k(BQ_("highpass", 400, 0)); n.sig = k(G(0));
  const shp = k(ctx.createWaveShaper()); shp.curve = SATCURVE; shp.oversample = "2x";
  chain(n.fIn, k(BQ_("lowpass", 2800, 0)), k(G(2.2)), shp, n.sig, n.mix);
  n.wh = k(ctx.createOscillator()); n.wh.frequency.value = 1200; n.wh.start(t); n.whG = k(G(0)); chain(n.wh, n.whG, n.mix);
  const hum = k(ctx.createOscillator()); hum.type = "sawtooth"; hum.frequency.value = 50; hum.start(t);
  chain(hum, k(BQ_("lowpass", 400, 0)), k(G(0.006)), n.mix);
  RADIO.n = n;
}
function radioStop() {
  const n = RADIO.n;
  if (!n) return;
  RADIO.n = null;
  holdAt(n.out.gain, ctx.currentTime); n.out.gain.setTargetAtTime(0, ctx.currentTime, 0.08);
  setTimeout(() => { for (const x of n.nodes) { try { if (x.stop) x.stop(); } catch (e) { /* ignore */ } try { x.disconnect(); } catch (e) { /* ignore */ } } }, 1200);
}
function radioParams() {
  const n = RADIO.n;
  if (!n) return;
  const sp = Number.isFinite(RADIO.x) && Number.isFinite(RADIO.y) ? spatial({ x: RADIO.x, y: RADIO.y }) : SP0;
  tgt(n.out.gain, sp ? sp.g * 0.4 : 0, 0.1); tgt(n.pan.pan, sp ? sp.pan : 0, 0.1);
  tgt(n.stG.gain, 0.05 + 0.22 * (1 - RADIO.sig), 0.2);
}
function radioTick(t) {
  const n = RADIO.n;
  if (!n) return;
  if (FEST.n && n.tapOf !== FEST.n) { try { FEST.n.tap.connect(n.fIn); n.tapOf = FEST.n; } catch (e) { /* ignore */ } }
  if (!n.crk && BK.get("crackle")) { n.crk = startLoop(["crackle", n.crG, 1]); if (n.crk) n.nodes.push(n.crk); }
  const sig = RADIO.sig;
  if (t >= n.nextFl) { // fading reception
    n.sig.gain.setTargetAtTime(0.6 * sig * rnd(lerp(0.15, 0.75, sig), 1), t, rnd(0.08, 0.4));
    n.nextFl = t + rnd(0.25, 1.4);
  }
  if (t >= n.next) { // someone (no one) turns the dial: heterodyne whistle, static surge, dropout
    const d = rnd(0.6, 1.5), up = chance(0.5), lo = rnd(250, 600), hi = rnd(1800, 3200), wf = n.wh.frequency, wg = n.whG.gain;
    wf.setValueAtTime(up ? lo : hi, t + 0.02); wf.exponentialRampToValueAtTime(up ? hi : lo, t + d);
    wg.setTargetAtTime(0.035, t + 0.02, 0.05); wg.setTargetAtTime(0, t + d, 0.08);
    n.sig.gain.setTargetAtTime(0.08 * sig, t + 0.02, 0.05);
    n.stS.gain.setTargetAtTime(2.6, t + 0.02, 0.06); n.stS.gain.setTargetAtTime(1, t + d, 0.2);
    n.next = t + d + rnd(2.5, 8) * (0.5 + sig);
    n.nextFl = t + d + 0.05;
  }
}

/* =====================================================================
   STINGERS — short musical cues in the same palette (AU.stinger)
   ===================================================================== */
let STR = null;
function stingStrip() {
  if (!STR) { const i = G(1); i.connect(BUS.music.inp); chain(i, G(0.4), BUS.music.wet); STR = { i }; }
  return STR;
}
const STING = {
  discover(t, s) {
    [62, 67, 69, 74].forEach((m, i) => koto(t + i * 0.11, m, 1, 0.5, s));
    flute(t + 0.46, 81, 1.6, 0.5, s); hit(t + 0.44, "rin", 0.1, s);
    pad(t, [62, 69, 76], 2, 0.5, s, { att: 0.4, rel: 2, cut: 1200 });
  },
  offering(t, s) { hit(t, "rin", 0.18, s); [79, 81, 83].forEach((m, i) => cel(t + 0.18 + i * 0.16, m, 1, 0.5, s)); },
  build(t, s) { hit(t, "knock", 0.25, s, 0.86); hit(t + 0.22, "knock", 0.3, s, 0.86); koto(t + 0.42, 69, 1, 0.5, s); koto(t + 0.58, 74, 1, 0.55, s); },
  complete(t, s) {
    pad(t, [50, 57, 64, 71], 3, 0.8, s, { att: 0.5, rel: 3, cut: 1300 });
    [62, 69, 74, 76, 81].forEach((m, i) => koto(t + i * 0.09, m, 1, 0.5, s));
    flute(t + 0.5, 74, 0.45, 0.5, s); flute(t + 1.0, 81, 2.2, 0.55, s); hit(t + 1.0, "rin", 0.1, s);
  },
  awaken(t, s) { // nine notes up — never the tenth
    [62, 64, 67, 69, 71, 74, 76, 79, 81].forEach((m, i) => koto(t + i * 0.05, m, 1, 0.3 + i * 0.03, s));
    hit(t + 0.5, "suzu", 0.12, s); cel(t + 0.55, 93, 1, 0.4, s);
  },
  far(t, s) { // pale, unreachable
    pad(t, [50, 51, 57], 2.5, 0.8, s, { att: 1.2, rel: 2.5, cut: 500 });
    hit(t + 0.1, "odaiko", 0.3, { i: BUS.far.fwet }, 0.8); hit(t + 0.6, "rin", 0.1, { i: BUS.far.fwet }, 0.5);
    harm(t + 1.1, 88, 1, 0.25, s);
  },
  title_hit(t, s) {
    hit(t, "odaiko", 0.6, s);
    [38, 50, 57, 62, 64, 69].forEach((m, i) => koto(t + i * 0.03, m, 1, 0.55, s));
    for (let i = 0; i < 6; i++) hit(t + 0.5 + i * 0.07, "shime", 0.1 + i * 0.03, s);
    hit(t + 0.95, "shime", 0.35, s); hit(t + 0.95, "odaiko", 0.4, s); hit(t + 1, "rin", 0.14, s);
  },
  night(t, s) { [79, 76, 74, 71, 69].forEach((m, i) => cel(t + i * 0.42, m, 1, 0.4 - i * 0.04, s)); pad(t, [50, 57], 3, 0.4, s, { att: 1, rel: 3, cut: 600 }); },
  dawn(t, s) {
    pad(t, [62, 69, 76], 3, 0.6, s, { att: 1.5, rel: 2.5, cut: 1100 });
    [74, 76, 79, 81].forEach((m, i) => flute(t + 0.3 + i * 0.32, m, i === 3 ? 1.8 : 0.3, 0.45, s));
    harm(t + 1.5, 93, 1, 0.3, s);
  },
};

/* =====================================================================
   SCHEDULER — one lookahead loop for music, festival, ambience, radio
   ===================================================================== */
let lastTick = 0;
function tick() {
  if (!ctx) return;
  try {
    const t = ctx.currentTime, dt = clamp(t - lastTick, 0, 0.25);
    lastTick = t;
    if (ctx.state !== "running") return;
    const ahead = t + (typeof document !== "undefined" && document.hidden ? 1.2 : 0.12);
    musicTick(t, ahead);
    festTick(t, ahead);
    if (dt > 0) ambTick(t, dt);
    radioTick(t);
    bakeTick();
  } catch (e) { /* the scheduler never throws */ }
}

/* =====================================================================
   API — public surface; every method is a silent no-op until ready
   ===================================================================== */
const TRIM = { master: 0.85, music: 0.75, amb: 0.85, sfx: 0.85, voice: 0.75, far: 0.9 }; // internal mix
function mkWave(h) {
  const re = new Float32Array(h.length + 1), im = new Float32Array(h.length + 1);
  h.forEach((a, i) => { im[i + 1] = a; });
  return ctx.createPeriodicWave(re, im);
}
function resume() {
  try { if (ctx && ctx.state === "suspended") { const p = ctx.resume(); if (p && p.catch) p.catch(() => {}); } } catch (e) { /* ignore */ }
}
function init() {
  if (ctx) { resume(); return ready; }
  try {
    const C = typeof window !== "undefined" && (window.AudioContext || window.webkitAudioContext);
    if (!C) return false;
    try { ctx = new C({ latencyHint: "interactive" }); } catch (e) { ctx = new C(); }
    SR = ctx.sampleRate; BSR = SR;
    NZ.white = makeNoise(2, "white"); NZ.pink = makeNoise(2, "pink"); NZ.brown = makeNoise(2, "brown");
    FLW = mkWave([1, 0.22, 0.09, 0.04, 0.015]); FIFEW = mkWave([1, 0.32, 0.16, 0.08, 0.04, 0.02]);
    SATCURVE = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) SATCURVE[i] = Math.tanh((i / 511.5 - 1) * 2.5) / Math.tanh(2.5);
    for (const k in TRIM) VOL[k] = TRIM[k];
    buildGraph(); buildAmb();
    for (const k of ["shime", "kaneO", "kaneD", "odaiko", "suzu", "knock", "tick", "wood", "taiko", "rin", "glass", "gong"]) BQ.push(() => snd(k));
    const yo = (a, b) => YO.filter((m) => m >= a && m <= b);
    for (const m of yo(40, 95)) BQ.push(() => ksE("koto", m));
    for (const m of yo(38, 71)) BQ.push(() => ksE("sham", m));
    for (const m of yo(67, 98)) BQ.push(() => celE(m), () => harmE(m));
    BQ.push(() => snd("bell"));
    lastTick = ctx.currentTime;
    timer = setInterval(tick, TICK_MS);
    ready = true;
    resume();
  } catch (e) {
    ready = false;
    try { if (timer) clearInterval(timer); if (ctx) ctx.close(); } catch (e2) { /* ignore */ }
    ctx = null;
  }
  return ready;
}
function setVolume(bus, v) {
  v = u01(v, 1);
  if (bus === "master") { tgt(master.gain, TRIM.master * v, 0.05); return; }
  const B = BUS[bus];
  if (!B || !B.vols || !(bus in TRIM)) return;
  for (const p of B.vols) tgt(p, TRIM[bus] * v, 0.05);
}
function update(dt, s) {
  if (!s || typeof s !== "object") return;
  dt = clamp(num(dt, 1 / 60), 0, 0.25);
  if (s.tod !== undefined) S.tod = circ(num(s.tod, S.tod));
  S.rain = u01(s.rain, S.rain); S.wind = u01(s.wind, S.wind); S.near = u01(s.near, S.near);
  S.water = u01(s.water, S.water); S.fall = u01(s.fall, S.fall); S.heavy = u01(s.heavy, S.heavy);
  S.indoor = !!s.indoor; S.cinematic = !!s.cinematic; S.paused = !!s.paused;
  if (s.listener) { S.L.x = num(s.listener.x, S.L.x); S.L.y = num(s.listener.y, S.L.y); }
  if (s.biome && typeof s.biome === "object") for (const k in S.biome) S.biome[k] = u01(s.biome[k], 0);
  AMB.on = true;
  ambUpdate(dt);
  tgt(pauseG.gain, S.paused ? 0.15 : 1, 0.12); tgt(pauseLP.frequency, nyq(S.paused ? 700 : 20000), 0.12);
  radioParams();
}
function sfx(name, o) {
  const fn = SFX[name];
  if (!fn) return;
  o = o && typeof o === "object" ? o : {};
  const sp = spatial(o);
  if (sp) fn(o, sp, ctx.currentTime + 0.005);
}
function duck(amount, secs) {
  const a = u01(amount, 0.5), t = ctx.currentTime, lvl = 1 - 0.92 * a, hold = num(secs, 0);
  for (const name of ["music", "amb"]) for (const p of BUS[name].ducks) {
    holdAt(p, t); p.setTargetAtTime(lvl, t, 0.08);
    if (hold > 0) p.setTargetAtTime(1, t + hold, 0.35);
  }
}
const guard = (fn) => (...a) => { if (!ready) return; try { fn(...a); } catch (e) { if (AUDIO_DEBUG) console.error('audio', e); } };
const api = {
  init() { try { return init(); } catch (e) { return false; } },
  resume: guard(resume),
  get ready() { return ready; },
  setVolume: guard(setVolume),
  update: guard(update),
  sfx: guard(sfx),
  music: guard((name, o) => musicSet(String(name || "none"), num(o && o.fade, 1.5), !!(o && o.restart))),
  festival: guard((a, o) => { FEST.a = u01(a, 0); FEST.near = u01(o && o.near, 0); festSync(); }),
  radio: guard((on, o) => {
    o = o && typeof o === "object" ? o : {};
    RADIO.on = !!on;
    if (Number.isFinite(o.x)) RADIO.x = o.x;
    if (Number.isFinite(o.y)) RADIO.y = o.y;
    if (o.signal !== undefined) RADIO.sig = u01(o.signal, RADIO.sig);
    if (RADIO.on && !RADIO.n) radioStart();
    else if (!RADIO.on && RADIO.n) radioStop();
    festSync(); radioParams();
  }),
  stinger: guard((name) => { const f = STING[name]; if (f) f(ctx.currentTime + 0.02, stingStrip()); }),
  duck: guard(duck),
};
return api;
})();
