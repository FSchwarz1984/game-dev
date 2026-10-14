// Frame cost per quality tier on the env test page (headless Chromium, SwiftShader = CPU raster, so
// the numbers are relative: they rank the tiers and catch regressions, they are not GPU timings).
//   node tools/env/perf.mjs [frames]
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const SCR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad';
const PAGE = process.env.PAGE_DIR || SCR + '/env/page';
const N = +(process.argv[2] || 24);
const CASES = [
  ['high 1280x720 saddle dusk', { width: 1280, height: 720 }, 'q=high&shot=saddle&t=17.6'],
  ['mid  1280x720 saddle dusk', { width: 1280, height: 720 }, 'q=mid&shot=saddle&t=17.6'],
  ['low  1280x720 saddle dusk', { width: 1280, height: 720 }, 'q=low&shot=saddle&t=17.6'],
  ['high 1280x720 graves night (9 lanterns)', { width: 1280, height: 720 }, 'q=high&shot=graves&t=21&lanterns=1'],
  ['low  1280x720 graves night (9 lanterns)', { width: 1280, height: 720 }, 'q=low&shot=graves&t=21&lanterns=1'],
];
function serve(dir) {
  const srv = http.createServer((req, res) => { const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
    fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': p.endsWith('.js') ? 'text/javascript' : 'text/html' }); res.end(d); }); });
  return new Promise(r => srv.listen(0, () => r(srv)));
}
const srv = await serve(PAGE); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const [name, vp, q] of CASES) {
  const ctx = await browser.newContext({ viewport: vp }); const page = await ctx.newPage();
  await page.goto(`http://localhost:${port}/index.html?hud=0&${q}`);
  await page.waitForFunction(() => window.READY || window.ERR, null, { timeout: 120000 });
  await page.waitForFunction(() => (window.FR || 0) >= 6, null, { timeout: 120000 });
  const r = await page.evaluate(n => new Promise(ok => { const f0 = window.FR, t0 = performance.now(); let cpu = 0, k = 0;
    const tick = () => { cpu += ENV.R.stats.ms; k++; if (window.FR - f0 >= n) ok({ ms: (performance.now() - t0) / (window.FR - f0), cpu: cpu / k, s: ENV.R.stats }); else requestAnimationFrame(tick); }; requestAnimationFrame(tick); }), N);
  console.log(`${name}: ${r.ms.toFixed(1)} ms/frame (SwiftShader) | render() cpu ${r.cpu.toFixed(2)} ms | native ${r.s.native.join('x')} x${r.s.scale} | calls ${r.s.calls} | passes ${r.s.passes} | lights ${r.s.lights} | particles ${r.s.particles}`);
  await ctx.close();
}
await browser.close(); srv.close();
