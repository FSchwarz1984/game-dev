// Headless screenshots of the env test page (Playwright Chromium, SwiftShader).
//   node tools/env/shots.mjs [name ...]          shots from the list below (default: all)
//   SHOT_DIR=... PAGE_DIR=... node tools/env/shots.mjs
// Waits by frames (SwiftShader runs at a few fps), never by milliseconds. Prints render stats and
// console errors per shot. One browser, one page per viewport.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const SCR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad';
const PAGE = process.env.PAGE_DIR || SCR + '/env/page';
const OUT = process.env.SHOT_DIR || SCR + '/shots/home2d';
fs.mkdirSync(OUT, { recursive: true });

const D720 = { viewport: { width: 1280, height: 720 } };
const D1080 = { viewport: { width: 1920, height: 1080 } };
const PORT = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 };
const LAND = { viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 };

// name: [ctx, query, frames]
export const SHOTS = {
  'saddle-dusk': [D720, 'shot=saddle&t=17.6'],
  'saddle-noon': [D720, 'shot=saddle&t=12.5'],
  'saddle-morning': [D720, 'shot=saddle&t=7&day1=1'],
  'saddle-night': [D720, 'shot=saddle&t=21&lanterns=1'],
  'hut-dusk': [D720, 'shot=hut&t=17.6'],
  'shrine-noon': [D720, 'shot=shrine&t=12.5'],
  'path-dusk': [D720, 'shot=path&t=17.6'],
  'graves-night': [D720, 'shot=graves&t=21&lanterns=1'],
  'dosojin-dusk': [D720, 'shot=dosojin&t=17.8'],
  'eastroad-morning': [D720, 'shot=eastRoad&t=7&day1=1'],
  'clearing-morning': [D720, 'x=47&z=41&t=7&day1=1'],
  'clearing-noon': [D720, 'x=47&z=41&t=12.5'],
  'lookout-dusk': [D720, 'shot=lookout&t=18.2'],
  'tower-night': [D720, 'shot=tower&t=21'],
  'waterfall-noon': [D720, 'shot=waterfall&t=12.5'],
  'camphor-top': [D720, 'shot=camphorTop&t=17.6'],
  'saddle-1080': [D1080, 'shot=saddle&t=17.6'],
  'portrait-saddle': [PORT, 'shot=saddle&t=17.6&q=mid'],
  'landscape-path': [LAND, 'shot=path&t=12.5&q=mid'],
  'dbg-vis': [D720, 'shot=saddle&t=12.5&debug=1'],
  'dbg-n': [D720, 'shot=saddle&t=12.5&debug=2'],
  'dbg-alb': [D720, 'shot=saddle&t=12.5&debug=3'],
  'dbg-pos': [D720, 'shot=saddle&t=12.5&debug=4'],
  'dbg-dep': [D720, 'shot=saddle&t=12.5&debug=5'],
  'dbg-vis-nots': [D720, 'shot=saddle&t=12.5&debug=1&nots=1'],
  'dbg-shtex': [D720, 'shot=saddle&t=12.5&debug=8&nots=1'],
  'dbg-lsp': [D720, 'shot=saddle&t=12.5&debug=6'],
  'dbg-shm': [D720, 'shot=saddle&t=12.5&debug=7'],
};

function serve(dir) {
  const srv = http.createServer((req, res) => {
    const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
    fs.readFile(p.endsWith('/') ? p + 'index.html' : p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': p.endsWith('.js') ? 'text/javascript' : p.endsWith('.html') ? 'text/html' : 'application/octet-stream' }); res.end(d); });
  });
  return new Promise(r => srv.listen(0, () => r(srv)));
}

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(SHOTS);
const srv = await serve(PAGE); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctxs = new Map();
for (const name of names) {
  const spec = SHOTS[name]; if (!spec) { console.log('no shot', name); continue; }
  const [ctxO, query, frames = 4] = spec;
  const key = JSON.stringify(ctxO);
  if (!ctxs.has(key)) ctxs.set(key, await browser.newContext(ctxO));
  const page = await ctxs.get(key).newPage();
  const errs = []; page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); }); page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  const t0 = Date.now();
  await page.goto(`http://localhost:${port}/index.html?shotmode=1&hud=0&${query}`);
  try {
    await page.waitForFunction(() => window.READY || window.ERR, null, { timeout: 120000 });
    const err = await page.evaluate(() => window.ERR || null); if (err) { console.log(name, 'ERROR', err); await page.close(); continue; }
    const f0 = await page.evaluate(() => window.FR || 0);
    await page.waitForFunction(n => (window.FR || 0) >= n, f0 + frames, { timeout: 180000 });
    await page.screenshot({ path: path.join(OUT, name + '.png') });
    const st = await page.evaluate(() => ({ stats: ENV.R.stats, bake: Math.round(ENV.bakeMs), timings: ENV.map.render.timings }));
    console.log(`${name}: ${Date.now() - t0} ms | native ${st.stats.native} x${st.stats.scale} ${st.stats.quality} | calls ${st.stats.calls} passes ${st.stats.passes} lights ${st.stats.lights} | bake ${st.bake} ms ${JSON.stringify(st.timings)}`);
  } catch (e) { console.log(name, 'FAILED', e.message.split('\n')[0]); }
  if (errs.length) console.log('  console:', errs.slice(0, 8).join('\n  '));
  await page.close();
}
await browser.close(); srv.close();
