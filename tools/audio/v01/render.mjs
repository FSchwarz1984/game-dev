// Offline renders of the v0.1 synthesizer (G5R3-63, G5R3-65): the WebAudio engine the user rated well
// (legacy/v0.1/src/audio.js, and its JS-version port src/audio/audio.js) runs unchanged in headless
// Chromium on an OfflineAudioContext, driven by a virtual clock instead of setInterval / setTimeout.
//
//   node tools/audio/v01/render.mjs <jobs.json> <out_dir> [--engine=js|legacy] [--only=name,name]
//
// jobs.json: [{ "name": "step_grass_w_01", "type": "sfx", "seed": 11, "dur": 1.2, ... }, ...]
// Each job writes <out_dir>/<name>.f32.wav (32-bit float, 44.1 kHz, stereo) and a line in
// <out_dir>/render_log.jsonl with the job and what the engine reported (peak, length, events).
//
// The source is patched as text before it runs; every patch must match exactly once (else the
// render stops), so a change in the engine cannot silently skip one. Two kinds:
//   harness  needed to run offline at all (virtual clock, no compressor, all buffers baked first,
//            internals exposed). They change no sound.
//   fix      the A-phase sound fixes (docs/knowledge/30 §12), applied unless the job sets "v01": true:
//            the far festival in tune (no +6..13 cent sharpening, no pitch wow, no chorus or phasing,
//            no random stumble), her steps without the bell (8.1: the bell is さぢ's), take rising and
//            give falling (8.2), events on a fixed pan (Godot places them in 3D).
// Job types are documented at JOB_TYPES below. Needs Playwright (/opt/node22) and Chromium.

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..', '..', '..');
const args = process.argv.slice(2);
const opt = (k, d) => { const a = args.find((x) => x.startsWith(`--${k}=`)); return a ? a.slice(k.length + 3) : d; };
const pos = args.filter((x) => !x.startsWith('--'));
if (pos.length < 2) { console.error('usage: node render.mjs <jobs.json> <out_dir> [--engine=js|legacy] [--only=a,b]'); process.exit(2); }
const JOBS = JSON.parse(fs.readFileSync(pos[0], 'utf8'));
const OUT = path.resolve(pos[1]);
const ENGINE = opt('engine', 'js');
const ONLY = opt('only', '') ? new Set(opt('only', '').split(',')) : null;
fs.mkdirSync(OUT, { recursive: true });

// ---------------------------------------------------------------- the engine source, patched
function engineSource(kind) {
  const file = kind === 'legacy' ? 'legacy/v0.1/src/audio.js' : 'src/audio/audio.js';
  let s = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const used = [];
  const P = (find, repl, tag = 'harness', all = false) => {
    const n = s.split(find).length - 1;
    if (all ? n < 1 : n !== 1) throw new Error(`patch "${find.slice(0, 70)}" matched ${n} times in ${file}`);
    s = all ? s.split(find).join(repl) : s.replace(find, () => repl);
    used.push(tag + ': ' + find.slice(0, 60));
  };
  s = s.replace(/^"use strict";\s*/, '');
  s = s.replace(/^export const AU = /m, 'const AU = ');
  // ---- harness: virtual clock, offline context, everything baked before the first sample
  P('try { ctx = new C({ latencyHint: "interactive" }); } catch (e) { ctx = new C(); }', 'ctx = __H.ctx;');
  P('timer = setInterval(tick, TICK_MS);', '__H.tick = tick; timer = 1;');
  P('setTimeout(', '__H.timeout(', 'harness', true);
  P('if (ctx.state !== "running") return;', '');
  P('if (ctx && ctx.state === "running" && v.end - ctx.currentTime > 0.05)', 'if (ctx && v.end - ctx.currentTime > 0.05)');
  P('while (BQ.length && performance.now() - t0 < 5)', 'while (BQ.length)');
  // no master compressor (Godot's master bus does that job, over the whole mix); unity output
  P('outG = G(0.55);', 'outG = G(__H.comp ? 0.55 : 1);');
  P('chain(master, hush, waveLP, pauseLP, pauseG, comp, outG, ctx.destination);',
    'if (__H.comp) chain(master, hush, waveLP, pauseLP, pauseG, comp, outG, ctx.destination); else chain(master, hush, waveLP, pauseLP, pauseG, outG, ctx.destination);');
  // bed solo masks and event filters (renders of one layer at a time)
  P('tgt(W.g.gain, wv, 0.6);', 'tgt(W.g.gain, wv * __H.mask("wind"), 0.6);');
  P('tgt(LV.g.gain, lv, 0.5);', 'tgt(LV.g.gain, lv * __H.mask("leaves"), 0.5);');
  P('tgt(SS.g.gain, sv, 0.5);', 'tgt(SS.g.gain, sv * __H.mask("sasa"), 0.5);');
  P('tgt(ST.g.gain, st, 0.5);', 'tgt(ST.g.gain, st * __H.mask("stream"), 0.5);');
  P('tgt(FA.g.gain, fv, 0.5);', 'tgt(FA.g.gain, fv * __H.mask("fall"), 0.5);');
  P('tgt(RN.hg.gain, rain * 0.32, 0.6); tgt(RN.bg.gain, Math.pow(rain, 1.5) * 0.28, 0.6);',
    'tgt(RN.hg.gain, rain * 0.32 * __H.mask("rain"), 0.6); tgt(RN.bg.gain, Math.pow(rain, 1.5) * 0.28 * __H.mask("rain"), 0.6);');
  P('tgt(RN.dl.gain, sstep(0, 0.4, rain) * 0.5, 0.6); tgt(RN.dh.gain, sstep(0.35, 1, rain) * 0.55, 0.6);',
    'tgt(RN.dl.gain, sstep(0, 0.4, rain) * 0.5 * __H.mask("rain"), 0.6); tgt(RN.dh.gain, sstep(0.35, 1, rain) * 0.55 * __H.mask("rain"), 0.6);');
  // an event that is filtered out still runs (so every random draw, and every later gust, stays the same
  // as in the full mix) but its voice reaches nothing
  P('p.connect(ambIn);\n  if (wet) chain(p, v.g(wet), ambWIn);',
    'if (__H.cur === null || __H.ev(__H.cur)) { p.connect(ambIn); if (wet) chain(p, v.g(wet), ambWIn); }');
  P('if (p.t > t - 0.2) p.fn(Math.max(p.t, t + 0.01)); }', 'if (p.t > t - 0.2) { __H.cur = "higu"; p.fn(Math.max(p.t, t + 0.01)); __H.cur = null; } }');
  P('AMB.gust = g;', 'AMB.gust = g; __H.log("gust", t, g, tc);');
  // events placed in 3D by Godot: render them on a fixed pan
  P('const g = v.g(lvl * 0.75), p = v.p(pan);', 'const g = v.g(lvl * 0.75), p = v.p(__H.pan === null ? pan : __H.pan);');
  // a log line per event fired by the scheduler
  P('const dur = fn(t + rnd(0.02, 0.1));', '__H.cur = k; const dur = fn(t + rnd(0.02, 0.1)); __H.cur = null; __H.log("event", t, k, dur);');
  // ---- fixes (A phase); each is guarded by __H.fix so the original v0.1 can still be measured
  P('const FEST = { a: 0, near: 0, n: null, t: 0, step: 0, bpm: 108, tune: 1.0035 };',
    'const FEST = { a: 0, near: 0, n: null, t: 0, step: 0, bpm: 108, tune: __H.fix ? 1 : 1.0035 };', 'fix');
  P('FEST.tune = 1.0035 + nr * 0.004;', 'FEST.tune = __H.fix ? 1 : 1.0035 + nr * 0.004;', 'fix');
  P('chain(osc("sine", 0.13), k(G(0.0085)), n.wow.delayTime); chain(osc("sine", 0.047), k(G(0.004)), n.wow.delayTime);',
    'if (!__H.fix) { chain(osc("sine", 0.13), k(G(0.0085)), n.wow.delayTime); chain(osc("sine", 0.047), k(G(0.004)), n.wow.delayTime); }', 'fix');
  P('tgt(n.chG.gain, nr * 0.7, 0.5);', 'tgt(n.chG.gain, __H.fix ? 0 : nr * 0.7, 0.5);', 'fix');
  P('n.phG.gain.setTargetAtTime(rnd(0.35, 0.6), t, 0.8);', 'n.phG.gain.setTargetAtTime(__H.fix ? 0 : rnd(0.35, 0.6), t, 0.8);', 'fix');
  P('FEST.t += s16 * (chance(0.003) ? 1.5 : 1);', 'FEST.t += s16 * (!__H.fix && chance(0.003) ? 1.5 : 1);', 'fix');
  if (s.includes('if (w < 0.5 && ++stepN % 2 === 0 && chance(0.8))'))
    P('if (w < 0.5 && ++stepN % 2 === 0 && chance(0.8))', 'if (__H.bell && w < 0.5 && ++stepN % 2 === 0 && chance(0.8))', 'fix');
  // the beds' noise: v0.1 looped one 2-second buffer per colour (wind, leaves, brook and rain all read the
  // same two seconds; measured: the beds repeat every 2.0 s, knowledge/30 §12). Long buffers of different
  // lengths instead, and longer bubble, rain-drop and crackle loops.
  P('NZ.white = makeNoise(2, "white"); NZ.pink = makeNoise(2, "pink"); NZ.brown = makeNoise(2, "brown");',
    'NZ.white = makeNoise(__H.fix ? 37.3 : 2, "white"); NZ.pink = makeNoise(__H.fix ? 41.9 : 2, "pink"); NZ.brown = makeNoise(__H.fix ? 29.1 : 2, "brown");', 'fix');
  P('BQ.push(...loopJobs("rainL", 3, droplets(16, 0.05, 0.25)), ...loopJobs("rainH", 3, droplets(90, 0.03, 0.16)), ...loopJobs("babble", 6, babble), bakeCrackle);',
    'BQ.push(...loopJobs("rainL", __H.fix ? 17.3 : 3, droplets(16, 0.05, 0.25)), ...loopJobs("rainH", __H.fix ? 19.7 : 3, droplets(90, 0.03, 0.16)), ...loopJobs("babble", __H.fix ? 23.9 : 6, babble), bakeCrackle);', 'fix');
  P('function babble(d, len) { // brook bubbles: Minnaert-like rising "bloops" (phasor chirps)\n  for (let i = 0; i < 64; i++) {',
    'function babble(d, len) { // brook bubbles: Minnaert-like rising "bloops" (phasor chirps)\n  for (let i = 0, nb = Math.round(64 * len / (6 * SR)); i < nb; i++) {', 'fix');
  P('bake("crackle", 4, 1, (b, len) => {', 'bake("crackle", __H.fix ? 13.1 : 4, 1, (b, len) => {', 'fix');
  P('for (let i = 0; i < 160; i++) addNoise(', 'for (let i = 0, nc = Math.round(160 * len / (4 * SR)); i < nc; i++) addNoise(', 'fix');
  // the brook's four resonances: Q 5..9 made narrow whistles that stand out once the wind covers the rest
  // of the water (measured, knowledge/30 §12); wider bands keep the babble without the whistling
  P('[5, 7, 8, 9][i]), g = G(1);', '(__H.fix ? __H.streamQ : [5, 7, 8, 9])[i]), g = G(1);', 'fix');
  // 8.2 (G5R3-65): take rises, give falls (v0.1 had them the other way round)
  P('const x = v.o("sine", 135 * r, t, t + 0.75); x.frequency.exponentialRampToValueAtTime(70 * r, t + 0.6); chain(x, v.g(a), lp);',
    'const x = v.o("sine", (__H.fix ? 70 : 135) * r, t, t + 0.75); x.frequency.exponentialRampToValueAtTime((__H.fix ? 135 : 70) * r, t + 0.6); chain(x, v.g(a), lp);', 'fix');
  P('lp.frequency.exponentialRampToValueAtTime(260, t + 0.6);', 'if (__H.fix) { lp.frequency.setValueAtTime(260, t); lp.frequency.exponentialRampToValueAtTime(1400, t + 0.6); } else lp.frequency.exponentialRampToValueAtTime(260, t + 0.6);', 'fix');
  P('bp.frequency.exponentialRampToValueAtTime(220, t + 0.6);', 'if (__H.fix) { bp.frequency.setValueAtTime(220, t); bp.frequency.exponentialRampToValueAtTime(1600, t + 0.6); } else bp.frequency.exponentialRampToValueAtTime(220, t + 0.6);', 'fix');
  P('airSweep(v, out, t, 380, 3600, 0.75, 0.5, 0.65);\n  bufTo(v, "glass", t + 0.45, 0.75, 0.26, out);',
    'if (__H.fix) { bufTo(v, "glass", t + 0.01, 0.75, 0.26, out); airSweep(v, out, t, 3600, 380, 0.75, 0.5, 0.3); } else { airSweep(v, out, t, 380, 3600, 0.75, 0.5, 0.65);\n  bufTo(v, "glass", t + 0.45, 0.75, 0.26, out); }', 'fix');
  if (s.includes('inn = o.verb !== "give" && o.verb !== "release";')) {
    P('inn = o.verb !== "give" && o.verb !== "release";', 'inn = __H.fix ? o.verb === "give" : (o.verb !== "give" && o.verb !== "release"), drawIn = o.verb !== "give" && o.verb !== "release";', 'fix');
    P('if (inn) { g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.32, t + 0.32);', 'if (drawIn) { g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.32, t + 0.32);', 'fix');
    P('bufTo(v, "suzu", t + (inn ? 0.34 : 0.05), rnd(0.96, 1.04), 0.06, out);', 'bufTo(v, "suzu", t + (drawIn ? 0.34 : 0.05), rnd(0.96, 1.04), 0.06, out);', 'fix');
    P('thump(v, out, t, 95 * r, 38, 0.5, 0.24);', 'if (__H.fix && o.verb !== "give") thump(v, out, t, 48, 95 * r, 0.5, 0.24); else thump(v, out, t, 95 * r, 38, 0.5, 0.24);', 'fix');
  }
  // where each section of a piece starts (the build cuts loops on these boundaries)
  P('P.seg = seg; P.i = 0; P.segT = Math.max(P.nextT, t);', 'P.seg = seg; P.i = 0; P.segT = Math.max(P.nextT, t); __H.log("seg", P.name, P.k - 1, P.segT, seg.beats, seg.bpm);');
  // ---- internals for the jobs
  const expose = `
  __: () => ({ S, BUS, SFX, PIECES, MUS, FEST, RADIO, STING, AMB, BEDS, W, LV, SS, ST, FA, RN, BK, NZ, YO, KS,
    ambUpdate, ambTick, musicSet, festSync, play, hit, koto, sham, flute, pad, cel, harm, line, accomp, carve, ksE, harmE, celE,
    snd, bake, mtof, dshift, caw, airSweep, thump, noiseHit, bufTo, ambOut, perc, grains, swell, strip: typeof strip === "function" ? strip : null,
    hum: typeof hum === "function" ? hum : null, HALF_PHRASE: typeof HALF_PHRASE !== "undefined" ? HALF_PHRASE : null,
    M1, M2, M3, M4, MOTIF, CADENCE, FMEL, SHIME_A, SHIME_B, KANE, COUNT9,
    ev: { evMinmin, evHigurashi, evUguisu, evTit, evCrow, evSuzumushi, evKajika, evClack, evFurin, evDrip,
          evCreak: typeof evCreak === "function" ? evCreak : null },
    flush() { while (BQ.length) { try { BQ.shift()(); } catch (e) { /* ignore */ } } },
    nodes: () => ({ master, hush, waveLP, comp, outG, roomIn, farIn, ambIn, ambG, ambLP, ambWIn }),
  }),`;
  P('const api = {', 'const api = {' + expose);
  return { src: `window.__makeEngine = function (__H) {\n${s}\nreturn AU;\n};`, used };
}

// ---------------------------------------------------------------- the page: clock and job types
const PAGE = String.raw`
function mulberry32(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const SR = 44100, STEP = 0.025;
// JOB_TYPES: what each job does at t = 0 and on every tick of the virtual clock (25 ms, the engine's TICK_MS)
const JOB_TYPES = {
  // one sound effect: AU.sfx(name, opts) at job.at (default 0.05 s)
  sfx: { tick(j, AU, I, now, st) { if (!st.done && now >= (j.at || 0.05)) { st.done = true; AU.sfx(j.sfx || j.name, j.opts || {}); } } },
  // a stinger (musical cue): AU.stinger(name)
  stinger: { tick(j, AU, I, now, st) { if (!st.done && now >= (j.at || 0.05)) { st.done = true; AU.stinger(j.stinger); } } },
  // a piece of the sequencer. job.ks: the generator's sections in this order (else its own k = 0, 1, 2 ...);
  // job.tod: the hour the explore piece reads; job.gen: replaced generator source (a function of k)
  music: {
    setup(j, AU, I) {
      I.S.tod = j.tod === undefined ? 12 : j.tod;
      const g = j.gen ? (0, eval)('(' + j.gen + ')') : I.PIECES[j.piece];
      if (j.ks || j.gen) { const ks = j.ks; let i = 0; I.PIECES[j.piece] = (k) => (ks ? (i < ks.length ? g(ks[i++], I) : null) : g(k, I)); }
      AU.music(j.piece, { fade: 0.02 });
    },
  },
  // the far festival at intensity a, nearness near (AU.festival); optional radio {signal}
  festival: {
    setup(j, AU, I) {
      if (j.fest) AU.festival(j.fest.a, { near: j.fest.near });
      if (j.radio) AU.radio(true, { signal: j.radio.signal });
    },
    tick(j, AU, I, now, st) {
      for (const c of j.cues || []) if (!c.done && now >= c.t) { c.done = true; if (c.fest) AU.festival(c.fest.a, { near: c.fest.near }); if (c.radio) AU.radio(true, { signal: c.radio.signal }); }
    },
  },
  // a snippet of the engine's own instrument and voice functions, for layers no public call makes on
  // its own (a step's body thump alone, one caw, さぢ's bell): job.code is the body of
  // function (I, t, play, out) where out(v, bus, lvl, wet, fw) routes a voice to a bus at the centre
  code: {
    tick(j, AU, I, now, st) {
      if (st.done || now < (j.at || 0.05)) return;
      st.done = true;
      const SP0 = { g: 1, pan: 0, d: 0 };
      const out = (v, bus, lvl, wet, fw) => v.out(bus || 'sfx', SP0, lvl === undefined ? 1 : lvl, wet || 0, fw || 0);
      const f = new Function('I', 't', 'play', 'out', j.code);
      st.ret = f(I, now + 0.005, I.play, out);
    },
  },
  // the ambience: AU.update(dt, state) on every tick (beds solo'd with job.mask, events with job.events / job.evkinds)
  amb: { tick(j, AU, I, now) { AU.update(STEP, j.state); } },
  // one creature or weather event called directly (no scheduler), routed like the scheduler's
  event: {
    setup(j, AU, I) { AU.update(STEP, { tod: 12, near: 1, wind: 0, rain: 0, water: 0, fall: 0, biome: {} }); },
    tick(j, AU, I, now, st) {
      AU.update(STEP, { tod: 12, near: 1, wind: 0, rain: 0, water: 0, fall: 0, biome: {} });
      if (!st.done && now >= (j.at || 0.25)) { st.done = true; st.ret = I.ev[j.ev](now + 0.01, ...(j.evargs || [])); }
    },
  },
};
window.__render = async function (job) {
  Math.random = mulberry32(job.seed >>> 0);
  const len = Math.ceil(job.dur * SR);
  const ctx = new OfflineAudioContext(2, len, SR);
  const timers = [], logs = [];
  const mask = job.mask || null, evOn = job.events === undefined ? true : !!job.events, evk = job.evkinds ? new Set(job.evkinds) : null;
  const H = {
    ctx, tick: null, cur: null, comp: !!job.comp, streamQ: job.streamQ || [2.5, 3, 3.5, 4], fix: !job.v01, bell: !!job.bell, pan: job.v01 && job.pan === undefined ? null : (job.pan === undefined ? 0 : job.pan),
    timeout(fn, ms) { timers.push({ t: ctx.currentTime + (ms || 0) / 1000, fn }); return 0; },
    mask(name) { return !mask ? 1 : (mask[name] === undefined ? 0 : mask[name]); },
    ev(k) { return evOn && (!evk || evk.has(k)); },
    log(...a) { if (logs.length < 20000) logs.push(a.map((x) => (typeof x === 'number' ? +x.toFixed(4) : x))); },
  };
  const AU = window.__makeEngine(H);
  if (!AU.init()) throw new Error('AU.init failed');
  const I = AU.__();
  I.flush();                                    // instruments, noise loops, reverb impulses: all baked now
  const T = JOB_TYPES[job.type];
  if (!T) throw new Error('unknown job type ' + job.type);
  const st = {};
  if (T.setup) T.setup(job, AU, I, st);
  const runTimers = () => { const now = ctx.currentTime; for (let i = timers.length - 1; i >= 0; i--) if (timers[i].t <= now) { const x = timers.splice(i, 1)[0]; try { x.fn(); } catch (e) { /* ignore */ } } };
  const onTick = () => {
    const now = ctx.currentTime;
    try { if (T.tick) T.tick(job, AU, I, now, st); } catch (e) { logs.push(['error', String(e)]); }
    runTimers();
    try { H.tick(); } catch (e) { logs.push(['error', String(e)]); }
  };
  onTick();
  const sched = (t) => ctx.suspend(t).then(() => { onTick(); if (t + STEP < job.dur - STEP) sched(t + STEP); ctx.resume(); });
  sched(STEP);
  const buf = await ctx.startRendering();
  window.__last = buf;
  let peak = 0;
  for (let c = 0; c < 2; c++) { const d = buf.getChannelData(c); for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > peak) peak = a; } }
  return { len: buf.length, peak, logs: logs.slice(0, 4000), ret: st.ret === undefined ? null : st.ret };
};
window.__chunk = function (c, start, n) {
  const d = window.__last.getChannelData(c).subarray(start, start + n);
  const b = new Uint8Array(d.buffer, d.byteOffset, d.byteLength);
  let s = ''; for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return btoa(s);
};
`;

function wavF32(file, L, R) {
  const n = L.length, data = Buffer.alloc(n * 8);
  for (let i = 0; i < n; i++) { data.writeFloatLE(L[i], i * 8); data.writeFloatLE(R[i], i * 8 + 4); }
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8); h.write('fmt ', 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(3, 20); h.writeUInt16LE(2, 22); h.writeUInt32LE(44100, 24);
  h.writeUInt32LE(44100 * 8, 28); h.writeUInt16LE(8, 32); h.writeUInt16LE(32, 34); h.write('data', 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, data]));
}

const { src, used } = engineSource(ENGINE);
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'] });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
await page.setContent('<!doctype html><meta charset="utf-8"><title>v01 render</title>');
await page.addScriptTag({ content: src });
await page.addScriptTag({ content: PAGE });
const logPath = path.join(OUT, 'render_log.jsonl');
let done = 0;
const t0 = Date.now();
for (const job of JOBS) {
  if (ONLY && !ONLY.has(job.name)) continue;
  const r0 = Date.now();
  let res;
  try { res = await page.evaluate((j) => window.__render(j), job); }
  catch (e) { console.error(`FAIL ${job.name}: ${String(e).slice(0, 300)}`); fs.appendFileSync(logPath, JSON.stringify({ name: job.name, error: String(e) }) + '\n'); continue; }
  const CH = 1 << 20, chans = [];
  for (let c = 0; c < 2; c++) {
    const parts = [];
    for (let s = 0; s < res.len; s += CH) parts.push(Buffer.from(await page.evaluate(([cc, ss, nn]) => window.__chunk(cc, ss, nn), [c, s, Math.min(CH, res.len - s)]), 'base64'));
    const b = Buffer.concat(parts);
    chans.push(new Float32Array(b.buffer, b.byteOffset, b.length / 4));
  }
  wavF32(path.join(OUT, job.name + '.f32.wav'), chans[0], chans[1]);
  fs.appendFileSync(logPath, JSON.stringify({ name: job.name, engine: ENGINE, job, peak: +res.peak.toFixed(5), seconds: +(res.len / 44100).toFixed(3), ret: res.ret, logs: res.logs, render_ms: Date.now() - r0 }) + '\n');
  done++;
  if (done % 20 === 0) console.log(`${done} rendered (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
}
await browser.close();
if (errors.length) console.error('page errors:', errors.slice(0, 5));
console.log(`done: ${done} jobs in ${((Date.now() - t0) / 1000).toFixed(1)} s; engine ${ENGINE}; patches ${used.length}`);
