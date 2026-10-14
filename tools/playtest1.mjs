// Plays segment 1 in headless Chromium through the real input paths — keys on desktop; on a
// phone the floating stick, the context key, a tap on 「重」 and a swipe up on it — and saves
// screenshots at the moments that matter. The page runs with ?manual=1: this script advances
// the game clock itself (fast, no drawing) and draws only the frames it photographs. It reads
// state from window.APP to decide where to go, but every action goes through input events.
//
//   node tools/playtest1.mjs [--mode=desk|phone|portrait] [--out=dir] [--file=dist/game.html]
// Exit code 1 if the run does not reach the end card.

import path from 'node:path';
import url from 'node:url';
import fs from 'node:fs';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const arg = k => (process.argv.find(a => a.startsWith(`--${k}=`)) || '').split('=')[1];
const mode = arg('mode') || 'desk';
const out = arg('out') || path.join(ROOT, '.shots', 'seg1-' + mode);
const file = arg('file') || path.join(ROOT, 'dist/game.html');
const from = arg('scene') || '';   // 'day1' starts at the first morning (skips the title and prologue)
fs.mkdirSync(out, { recursive: true });

const VIEW = { desk: { width: 1280, height: 720, dpr: 1, touch: false }, phone: { width: 844, height: 390, dpr: 3, touch: true }, portrait: { width: 390, height: 844, dpr: 3, touch: true } }[mode];
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: VIEW.width, height: VIEW.height }, deviceScaleFactor: VIEW.dpr, hasTouch: VIEW.touch, isMobile: VIEW.touch });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
const cdp = VIEW.touch ? await page.context().newCDPSession(page) : null;

await page.goto('file://' + file + '?manual=1' + (VIEW.touch ? '&touch=1' : '') + (from ? '&scene=' + from : ''));
await page.waitForFunction(() => window.APP && window.APP.G);

const log = (...a) => console.log(`[${mode}]`, ...a);
let shotN = 0;
async function shot(name) {
  await page.waitForTimeout(900);            // let CSS fades and cards settle (they run on the wall clock)
  await page.evaluate(() => window.APP.render());
  await page.waitForTimeout(60);
  const f = path.join(out, `${String(++shotN).padStart(2, '0')}-${name}.png`);
  await page.screenshot({ path: f });
  const st = await state();
  const hud = await page.evaluate(() => ({ prompt: document.querySelector('.tgt')?.className, tip: document.querySelector('.hud-tip.on')?.textContent || '' }));
  log('shot', path.basename(f), JSON.stringify({ target: st.target, label: st.label, control: st.control, w: st.w, ...hud }));
}
const state = () => page.evaluate(() => {
  const { G } = window.APP, f = G.f, P = f.player;
  return { x: P.x, z: P.z, control: f.control, busy: G.D.busy, blocking: G.ui.blocking, dlg: !!G.ui.dlg, target: f.target?.id || null, label: f.contextLabel(), w: P.holder.q.w, saved: localStorage.getItem('amagishi.save') };
});
// advance the clock n frames of 1/30 s without drawing
const ticks = n => page.evaluate(n => { for (let i = 0; i < n; i++) window.APP.tick(1 / 30); }, n);

// ---------------------------------------------------------------- input primitives
let held = new Set();
async function holdKeys(keys) {
  for (const k of held) if (!keys.includes(k)) await page.keyboard.up(k);
  for (const k of keys) if (!held.has(k)) await page.keyboard.down(k);
  held = new Set(keys);
}
let stick = null;
async function touchStick(dx, dz) {
  const x0 = VIEW.width * 0.22, y0 = VIEW.height * 0.62, r = 60;
  if (dx === 0 && dz === 0) {
    if (stick) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); stick = null; }
    return;
  }
  const pt = { x: x0 + dx * r, y: y0 + dz * r, id: 7 };
  if (!stick) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x0, y: y0, id: 7 }] }); stick = true; }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [pt] });
}
async function steer(dx, dz) {
  if (VIEW.touch) return touchStick(dx, dz);
  const keys = [];
  if (dx > 0.38) keys.push('ArrowRight'); if (dx < -0.38) keys.push('ArrowLeft');
  if (dz > 0.38) keys.push('ArrowDown'); if (dz < -0.38) keys.push('ArrowUp');
  return holdKeys(keys);
}
async function rect(sel) { return page.evaluate(s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }, sel); }
async function tap(sel) { const r = await rect(sel); if (!r) throw new Error('no element ' + sel); await page.touchscreen.tap(r.x, r.y); }
async function swipeUp(sel) {
  const r = await rect(sel);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: r.x, y: r.y, id: 3 }] });
  for (let i = 1; i <= 4; i++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: r.x, y: r.y - i * 12, id: 3 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}
async function contextKey() { if (VIEW.touch) await tap('.act-ctx'); else await page.keyboard.press('KeyE'); }
async function take() { if (VIEW.touch) await tap('.act-q[data-k="w"]'); else await page.keyboard.press('Digit1'); }
async function give() {
  if (VIEW.touch) await swipeUp('.act-q[data-k="w"]');
  else { await page.keyboard.down('Shift'); await page.keyboard.press('Digit1'); await page.keyboard.up('Shift'); }
}
async function advance() { if (VIEW.touch) await tap('.st-dlg'); else await page.keyboard.press('Space'); }

// ---------------------------------------------------------------- behaviours
/** Run the clock until cond(state) holds; dialogue is advanced as it comes. */
async function until(cond, label, max = 9000) {
  for (let i = 0; i < max; i += 6) {
    const s = await state();
    if (cond(s)) return s;
    if (s.dlg) { await ticks(20); await advance(); }
    await ticks(6);
  }
  throw new Error('timed out: ' + label);
}
// A path over the map's walkable grid (0.5 m BFS, computed in the page), so the bot goes round
// walls and up the stairs like a player who can see them.
const route = (x, z) => page.evaluate(([tx, tz]) => {
  const { G } = window.APP, map = G.stage.map, f = G.f, c = 0.5, X0 = -6, Z0 = -4, W = 270, H = 200;
  const idx = (i, j) => j * W + i, ci = x => Math.round((x - X0) / c), cj = z => Math.round((z - Z0) / c);
  const ok = (i, j) => i >= 0 && j >= 0 && i < W && j < H && map.walkable(X0 + i * c, Z0 + j * c) && f.canStand(X0 + i * c, Z0 + j * c);
  const s = idx(ci(f.player.x), cj(f.player.z)), t = idx(ci(tx), cj(tz));
  const prev = new Int32Array(W * H).fill(-1); prev[s] = s; const q = [s];
  for (let h = 0; h < q.length && prev[t] < 0; h++) {
    const k = q[h], i = k % W, j = (k / W) | 0;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const a = i + di, b = j + dj, n = idx(a, b);
      if (prev[n] >= 0 || !ok(a, b) || (di && dj && (!ok(i + di, j) || !ok(i, j + dj)))) continue;
      prev[n] = k; q.push(n);
    }
  }
  if (prev[t] < 0) return null;
  const pts = []; for (let k = t; k !== s; k = prev[k]) pts.push([X0 + (k % W) * c, Z0 + ((k / W) | 0) * c]);
  pts.reverse();
  return pts.filter((p, n) => n % 2 === 1 || n === pts.length - 1);
}, [x, z]);
async function walk(target, tol = 0.35) {
  await until(s => s.control && !s.busy && !s.blocking, 'control before walking to ' + target);
  const pts = await route(target[0], target[1]);
  if (!pts) throw new Error('no route to ' + target);
  for (const p of pts.slice(0, -1)) await walkStraight(p, 0.45, true);
  return walkStraight(target, tol);
}
async function walkStraight([x, z], tol = 0.35, soft = false) {
  let best = 1e9, still = 0;
  for (let i = 0; i < 2400; i++) {
    const s = await state();
    if (s.dlg) { await steer(0, 0); await ticks(15); await advance(); continue; }
    const dx = x - s.x, dz = z - s.z, d = Math.hypot(dx, dz);
    if (d < tol) { await steer(0, 0); await ticks(2); return; }
    if (d < best - 0.05) { best = d; still = 0; } else if (++still > 40) { if (soft) return; throw new Error(`stuck short of ${x},${z} at ${s.x.toFixed(2)},${s.z.toFixed(2)}`); }
    await steer(dx / d, dz / d);
    await ticks(3);
  }
  await steer(0, 0);
  throw new Error(`could not reach ${x},${z}`);
}
async function face(id) {
  // nudge toward the thing until it is the target (a real player turns the stick a little)
  for (let i = 0; i < 40; i++) {
    const s = await state();
    if (s.target === id) { await steer(0, 0); return; }
    const e = await page.evaluate(id => { const e = window.APP.G.f.get(id); return e && { x: e.x, z: e.z }; }, id);
    const dx = e.x - s.x, dz = e.z - s.z, d = Math.hypot(dx, dz);
    await steer(dx / d, dz / d); await ticks(1); await steer(0, 0); await ticks(2);
  }
  throw new Error('cannot target ' + id);
}
const places = () => page.evaluate(() => window.APP.G.P);

// ---------------------------------------------------------------- the run
try {
  if (from !== 'day1') await prologueRun();
  await dayOneRun();
  log('reached the end card; errors:', errors.length);
} catch (e) {
  log('FAILED:', e.message);
  await shot('failure').catch(() => {});
  process.exitCode = 1;
}
if (errors.length) { log('page errors:\n' + errors.slice(0, 10).join('\n')); process.exitCode = 1; }
await browser.close();

async function prologueRun() {
  await ticks(40);
  await shot('title');
  if (VIEW.touch) await tap('.ttl-menu button[data-a="start"]'); else await page.keyboard.press('Enter');
  await ticks(120); await shot('entrance-dusk');
  const P = await places();
  await until(s => s.dlg, 'statues line'); await shot('statues');
  await until(s => s.control && !s.busy, 'control on the road');
  // up the switchbacks: the road's own bends (map.objects.road.path), then the graves terrace
  await walk([96, 72.4], 0.8);
  await shot('switchbacks');
  await walk(P.gravesStand, 1.4);
  for (let i = 0; i < 9; i++) {
    const g = await page.evaluate(i => { const e = window.APP.G.f.get('grave' + i); return [e.x, e.z + 1.1]; }, i);
    await walk(g, 0.4); await face('grave' + i); await contextKey(); await ticks(30);
    if (i === 4) await shot('graves-half');
  }
  await until(s => s.dlg, 'ten lanterns'); await shot('graves-lit');
  await until(s => s.control && !s.busy, 'after the hayashi');
  await shot('night-camphor');
  await walk(P.camphorFoot, 0.4); await face('camphor'); await contextKey();
  await ticks(200); await shot('climb');
  await until(s => !s.control && s.dlg, 'treetop line'); await shot('vista-treetop');
  for (const [n, f] of [['rise', 700], ['sky', 500], ['wave', 400]]) { await ticks(f); await shot('vista-' + n); }
  await until(s => s.saved && s.saved.includes('day1'), 'prologue saved');
}

async function dayOneRun() {
  const P = await places();
  await ticks(90); await shot('waking');
  await until(s => s.control, 'control on day 1');
  await shot('morning');
  await walk([P.hutDoor[0], P.hutDoor[1] + 1.9], 0.4); await face('hut'); await contextKey();   // the far hut keeps her a step away
  await until(s => s.dlg, 'hut line'); await shot('hut');
  await until(s => s.control && !s.busy, 'beam falls');
  await walk([P.beam[0], P.beam[1] + 1.6], 0.4);
  await until(s => s.control && !s.busy && !s.blocking, 'Saji asks');
  await face('beam'); await contextKey();
  await until(s => s.control && !s.busy, 'lift attempt'); await shot('beam-pips');
  for (let i = 0; i < 3; i++) { await face('beam'); await take(); await ticks(30); }
  await shot('beam-taken');
  await until(s => s.control && !s.busy && !s.blocking, 'Saji free');
  await walk([P.frame[0], P.frame[1] + 1.1], 0.4);
  for (let i = 0; i < 3; i++) { await face('frame'); await give(); await ticks(30); }
  await shot('frame-given');
  await until(s => s.control && !s.busy && !s.blocking, 'banter');
  await face('frame');
  await until(s => s.label === '背上', 'the frame offers to be shouldered');
  await contextKey();
  await until(s => s.dlg, 'Saji moves in'); await shot('saji-rides');
  await until(s => s.control && !s.busy, 'setting out');
  await walk([119.2, P.dosojinStand[1]], 0.6);
  await until(s => s.saved && s.saved.includes('end'), 'end card', 3000);
  await shot('end');
}
