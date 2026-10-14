// Headless-Chromium check of the field-recording layer on top of the real engine.
//
//   node tools/audio/field_browser_check.mjs [out_dir] [--sweep]
//
// 1. Decoding: every assets/audio/*.mp3 decodes with the browser's decodeAudioData (from the same
//    data: URLs the single-file build inlines); the decoded length against the encoded PCM length
//    (equal = the decoder honours the LAME gapless header and trims delay and padding), and that each
//    loop's padding still repeats its head one loop length later (the loop period survived).
// 2. Loop seams through real WebAudio looping: each loop is rendered in an OfflineAudioContext with
//    loopStart/loopEnd from META, wrapping at t = 1 s; the sample step at the wrap is ranked against
//    400 ordinary steps inside the loop (a click would rank at the top).
// 3. Integration: AU.init() + createFieldAmbience(AU).load(), then the engine and the layer are driven
//    like the game loop (AU.update, amb.update) at dusk, night, morning and morning seen from "far";
//    the output reaching the destination is recorded to WAV, with the synth-only engine as the
//    baseline. Prints loudness, which engine layers were muted, and console errors.
// 4. Failure: a broken source must leave its synthesized layer unmuted and throw nothing.
// --sweep adds a 60 s capture with the clock running 17:30 -> 21:00.
// Needs: Playwright (global, see the playtest-capture skill), esbuild (repo), ffmpeg.

import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import url from 'node:url';
import { execFileSync } from 'node:child_process';
import { build } from 'esbuild';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..', '..');
const OUT = path.resolve(process.argv.slice(2).find((a) => !a.startsWith('--')) || path.join(os.tmpdir(), 'field-browser-check'));
const SWEEP = process.argv.includes('--sweep');
fs.mkdirSync(OUT, { recursive: true });
const NAMES = fs.readdirSync(path.join(ROOT, 'assets/audio')).filter((f) => f.endsWith('.mp3')).map((f) => f.slice(0, -4));

// ---- harness page (bundled with the repo's esbuild; the .mp3 files become data: URLs as in the build)
const entry = `
import { AU } from ${JSON.stringify(path.join(ROOT, 'src/audio/audio.js'))};
import { createFieldAmbience } from ${JSON.stringify(path.join(ROOT, 'src/audio/field.js'))};
${NAMES.map((n) => `import ${n} from ${JSON.stringify(path.join(ROOT, 'assets/audio', n + '.mp3'))};`).join('\n')}
const SOURCES = { ${NAMES.join(', ')} };
const REC = { on: false, L: [], R: [], sr: 0 };
const connect = AudioNode.prototype.connect;
AudioNode.prototype.connect = function (dest, ...rest) { // tap whatever reaches the speakers
  const r = connect.call(this, dest, ...rest);
  if (dest instanceof AudioDestinationNode && !this.__tap) {
    this.__tap = true;
    const ctx = this.context;
    if (!ctx.__rec) {
      const sp = ctx.createScriptProcessor(4096, 2, 2), z = ctx.createGain();
      z.gain.value = 0; connect.call(sp, z); connect.call(z, ctx.destination);
      sp.onaudioprocess = (e) => { if (REC.on) { REC.L.push(new Float32Array(e.inputBuffer.getChannelData(0))); REC.R.push(new Float32Array(e.inputBuffer.getChannelData(1))); } };
      ctx.__rec = sp; REC.sr = ctx.sampleRate;
    }
    connect.call(this, ctx.__rec);
  }
  return r;
};
function bytes(u) { const b = atob(u.slice(u.indexOf(',') + 1)), a = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) a[i] = b.charCodeAt(i); return a.buffer; }
window.T = {
  names: Object.keys(SOURCES),
  async decodeAll(meta) {
    const ctx = new OfflineAudioContext(1, 44100, 44100), out = {};
    for (const [n, u] of Object.entries(SOURCES)) {
      try {
        const b = await ctx.decodeAudioData(bytes(u)), d = b.getChannelData(0);
        let first = 0; while (first < d.length && Math.abs(d[first]) < 1e-6) first++;
        const r = { ok: true, dur: b.duration, sr: b.sampleRate, meta: meta[n].dur, firstNonZero: first };
        if (meta[n].kind === 'loop') { // where does the padding repeat the loop head? (0 = delay trimmed)
          const sr = b.sampleRate, i0 = Math.round(meta[n].loopStart * sr), i1 = Math.round(meta[n].loopEnd * sr), k = Math.round(0.1 * sr);
          let best = -2, lag = 0;
          for (let s = -1300; s <= 1300; s++) {
            let xy = 0, xx = 0, yy = 0;
            for (let i = 0; i < k; i += 2) { const a = d[i0 + i], c = d[i1 + s + i]; xy += a * c; xx += a * a; yy += c * c; }
            const r2 = xy / Math.sqrt(xx * yy + 1e-20); if (r2 > best) { best = r2; lag = s; }
          }
          r.periodLagSamples = lag; r.periodCorr = +best.toFixed(3);
        }
        out[n] = r;
      } catch (e) { out[n] = { ok: false, err: String(e) }; }
    }
    return out;
  },
  async seams(meta) { // real WebAudio looping, wrap at t = 1 s
    const out = {};
    for (const [n, m] of Object.entries(meta)) {
      if (m.kind !== 'loop') continue;
      const dec = new OfflineAudioContext(1, 44100, 44100), buf = await dec.decodeAudioData(bytes(SOURCES[n]));
      const L = m.loopEnd - m.loopStart, sr = buf.sampleRate;
      const ctx = new OfflineAudioContext(1, Math.round(sr * (L + 2)), sr), s = ctx.createBufferSource();
      s.buffer = buf; s.loop = true; s.loopStart = m.loopStart; s.loopEnd = m.loopEnd; s.connect(ctx.destination);
      s.start(0, m.loopEnd - 1.0);
      const y = (await ctx.startRendering()).getChannelData(0), w = Math.round(sr);
      const steps = []; for (let i = w + 2000; i < y.length - 2000; i += 7) steps.push(Math.abs(y[i] - y[i - 1]));
      const st = Math.abs(y[w] - y[w - 1]), pct = steps.filter((v) => v < st).length / steps.length * 100;
      let near = 0; for (let i = w - 3; i <= w + 3; i++) near = Math.max(near, Math.abs(y[i] - y[i - 1]));
      out[n] = { wrapStepPct: +pct.toFixed(1), maxStepAroundWrapPct: +(steps.filter((v) => v < near).length / steps.length * 100).toFixed(1) };
    }
    return out;
  },
  async start(mode) {
    const ok = AU.init(); AU.resume();
    const r = { ok, sr: AU.context() && AU.context().sampleRate };
    if (mode !== 'synth') {
      const src = { ...SOURCES };
      if (mode === 'broken') src.night = src.night2 = 'data:audio/mpeg;base64,AAAA'; // both undecodable
      window.amb = createFieldAmbience(AU, { sources: src });
      r.loaded = await window.amb.load();
      r.stats = window.amb.stats();
    }
    return r;
  },
  run(p) {
    if (T.timer) clearInterval(T.timer);
    T.p = Object.assign({ tod: 18, near: 1, wind: 0.3, waterDist: 35, rate: 0 }, p);
    let last = performance.now();
    T.timer = setInterval(() => {
      const now = performance.now(), dt = (now - last) / 1000; last = now;
      T.p.tod += T.p.rate * dt;
      AU.update(dt, { tod: T.p.tod, near: T.p.near, wind: T.p.wind, listener: { x: 0, y: 0 } });
      if (window.amb) window.amb.update(dt, { waterDist: T.p.waterDist });
    }, 16);
  },
  rec(on) { if (on) { REC.L = []; REC.R = []; } REC.on = on; },
  take() {
    const n = REC.L.reduce((a, b) => a + b.length, 0), o = new Int16Array(n * 2); let k = 0;
    for (let i = 0; i < REC.L.length; i++) for (let j = 0; j < REC.L[i].length; j++) { o[k++] = Math.max(-32768, Math.min(32767, REC.L[i][j] * 32767)); o[k++] = Math.max(-32768, Math.min(32767, REC.R[i][j] * 32767)); }
    const u8 = new Uint8Array(o.buffer); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    return { sr: REC.sr, b64: btoa(s) };
  },
};
window.READY = true;
`;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'field-harness-'));
fs.writeFileSync(path.join(tmp, 'entry.js'), entry);
await build({ entryPoints: [path.join(tmp, 'entry.js')], bundle: true, format: 'iife', target: 'es2020', outfile: path.join(tmp, 'bundle.js'), loader: { '.mp3': 'dataurl' }, logLevel: 'warning' });
fs.writeFileSync(path.join(tmp, 'index.html'), '<!doctype html><meta charset="utf-8"><title>field check</title><script src="bundle.js"></script>');
const META = JSON.parse(fs.readFileSync(path.join(ROOT, 'src/audio/field.js'), 'utf8').match(/const META = (\{.*?\});\n\/\/ META:END/s)[1]);

const server = http.createServer((req, res) => {
  const f = path.join(tmp, req.url.split('?')[0].replace(/^\/+/, '') || 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': f.endsWith('.html') ? 'text/html' : 'text/javascript' }); fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/index.html?audiodebug=1`;
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const problems = [], consoleErrors = [];
const wav = (file, d) => {
  const pcm = Buffer.from(d.b64, 'base64'), h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + pcm.length, 4); h.write('WAVE', 8); h.write('fmt ', 12); h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20); h.writeUInt16LE(2, 22); h.writeUInt32LE(d.sr, 24); h.writeUInt32LE(d.sr * 4, 28); h.writeUInt16LE(4, 32);
  h.writeUInt16LE(16, 34); h.write('data', 36); h.writeUInt32LE(pcm.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, pcm]));
};
function ebur128(file) { // ffmpeg prints the loudness summary on stderr
  try { return execFileSync('sh', ['-c', `ffmpeg -nostats -i "${file}" -filter_complex ebur128 -f null - 2>&1`], { encoding: 'utf8' }); } catch (e) { return String(e.stdout || ''); }
}
async function page(expectDecodeWarnings = false) {
  const p = await browser.newPage();
  p.on('console', (m) => {
    const t = m.text();
    if (/ScriptProcessorNode/.test(t)) return; // the recorder tap, not the game
    if (expectDecodeWarnings && /field audio: night2? EncodingError/.test(t)) return; // the failure test's own files
    if (m.type() === 'error' || m.type() === 'warning') consoleErrors.push(t);
  });
  p.on('pageerror', (e) => consoleErrors.push(String(e)));
  await p.goto(base); await p.waitForFunction(() => window.READY);
  return p;
}

// 1 + 2: decoding and seams
{
  const p = await page();
  const dec = await p.evaluate((m) => T.decodeAll(m), META);
  console.log('decode (Chromium decodeAudioData):');
  for (const [n, r] of Object.entries(dec)) {
    const trimmed = r.ok && Math.abs(r.dur - META[n].dur) < 0.002; // encoded PCM length == META.dur
    console.log(`  ${n.padEnd(7)} ${r.ok ? 'ok' : 'FAIL'} ${r.ok ? `${r.dur.toFixed(3)} s (encoded ${META[n].dur} s: encoder delay/padding ${trimmed ? 'trimmed' : 'NOT trimmed'})${r.periodLagSamples !== undefined ? `; loop period intact (padding repeats the head at lag ${r.periodLagSamples}, r=${r.periodCorr})` : ''}` : r.err}`);
    if (!r.ok || r.dur < META[n].dur - 0.06) problems.push(`decode ${n}`);
    if (r.periodCorr !== undefined && (Math.abs(r.periodLagSamples) > 2 || r.periodCorr < 0.8)) problems.push(`loop period ${n}`);
  }
  const seams = await p.evaluate((m) => T.seams(m), META);
  console.log('loop seams (OfflineAudioContext, real loopStart/loopEnd; percentile of the wrap step among ordinary steps):');
  for (const [n, r] of Object.entries(seams)) {
    console.log(`  ${n.padEnd(7)} wrap step at ${r.wrapStepPct} %, largest step within +-3 samples at ${r.maxStepAroundWrapPct} %`);
    if (r.maxStepAroundWrapPct > 99.5) problems.push(`seam ${n}`);
  }
  await p.close();
}

// 3: integration, synth baseline vs field
const SCENES = [
  { name: 'dusk', p: { tod: 18.0 }, settle: 3, sec: 12 },
  { name: 'night', p: { tod: 20.5 }, settle: 14, sec: 12 },
  { name: 'morning', p: { tod: 7.0 }, settle: 8, sec: 20 },
  { name: 'morning-far', p: { tod: 7.0, near: 0.35 }, settle: 3, sec: 12 },
];
if (SWEEP) SCENES.push({ name: 'sweep', p: { tod: 17.5, rate: 3.5 / 60 }, settle: 0.1, sec: 60, fresh: true });
const results = {};
for (const mode of ['synth', 'field']) {
  let p = await page();
  const info = await p.evaluate((m) => T.start(m), mode);
  console.log(`${mode}: init ${info.ok}, sample rate ${info.sr}${info.loaded ? `, loaded ${info.loaded.join(' ')}; engine layers muted: ${info.stats.muted.join(' ')}` : ''}`);
  if (mode === 'field') {
    const want = new Set(info.loaded.flatMap((n) => ({ night: ['suzu'], night2: ['suzu'], wind: ['wind', 'leaves'], stream: ['stream'], fall: ['fall'], crow: ['crow'], birds: ['ugu', 'tit'], dusk: ['higu'], higu: ['higu'] }[n] || [])));
    if ([...want].sort().join() !== [...info.stats.muted].sort().join()) problems.push('muted set');
  }
  for (const sc of SCENES) {
    if (sc.fresh) { if (mode === 'synth') continue; await p.close(); p = await page(); await p.evaluate((m) => T.start(m), mode); }
    await p.evaluate((x) => T.run(x), sc.p);
    await p.waitForTimeout(sc.settle * 1000);
    await p.evaluate(() => T.rec(true));
    await p.waitForTimeout(sc.sec * 1000);
    await p.evaluate(() => T.rec(false));
    const file = path.join(OUT, `${mode}-${sc.name}.wav`);
    wav(file, await p.evaluate(() => T.take()));
    const I = +((ebur128(file).split('Summary').pop().match(/I:\s+(-?[\d.]+) LUFS/) || [])[1]);
    results[`${mode}-${sc.name}`] = I;
    const st = mode === 'field' ? await p.evaluate(() => window.amb.stats()) : null;
    console.log(`  ${sc.name.padEnd(11)} ${I.toFixed(1)} LUFS -> ${path.basename(file)}${st ? `  beds ${Object.entries(st.levels).filter(([, v]) => v.live).map(([k, v]) => `${k} ${v.level}`).join(', ')}` : ''}`);
  }
  await p.close();
}

// 4: failure path
{
  const p = await page(true);
  const info = await p.evaluate(() => T.start('broken'));
  console.log(`broken night + night2 sources: loaded ${info.loaded.join(' ')}; engine layers muted: ${info.stats.muted.join(' ')}`);
  if (info.loaded.includes('night') || info.loaded.includes('night2')) problems.push('broken source reported as loaded');
  if (info.stats.muted.includes('suzu')) problems.push('synthesized suzumushi muted without a night recording');
  if (!info.stats.muted.includes('wind')) problems.push('a broken file stopped the others from loading');
  await p.close();
}
await browser.close(); server.close();
if (consoleErrors.length) { console.log('console errors:\n  ' + consoleErrors.join('\n  ')); problems.push('console errors'); }
console.log(problems.length ? `PROBLEMS: ${problems.join(', ')}` : 'all browser checks passed');
console.log(`recordings in ${OUT}`);
process.exit(problems.length ? 1 : 0);
