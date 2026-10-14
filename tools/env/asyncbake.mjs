// The non-blocking bake in a real browser: loads the test page with ?async=1 and reports how long the
// bake took, the longest slice, and the longest gap between animation frames while it ran.
//   node tools/env/asyncbake.mjs
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const SCR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad';
const PAGE = process.env.PAGE_DIR || SCR + '/env/page';
function serve(dir) {
  const srv = http.createServer((req, res) => { const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
    fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': p.endsWith('.js') ? 'text/javascript' : 'text/html' }); res.end(d); }); });
  return new Promise(r => srv.listen(0, () => r(srv)));
}
const srv = await serve(PAGE); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`http://localhost:${port}/index.html?hud=0&async=1&shot=saddle`);
await page.waitForFunction(() => window.READY || window.ERR, null, { timeout: 180000 });
const B = await page.evaluate(() => window.BAKE);
console.log(`async bake: ${Math.round(B.ms)} ms, ${B.frames} animation frames during it, longest frame gap ${Math.round(B.maxGap)} ms, longest slice ${B.longestSlice} ms, progress steps ${B.progress.length}`);
if (B.slow && B.slow.length) console.log('steps over 30 ms [ms, progress]:', JSON.stringify(B.slow));
if (errs.length) console.log('errors:', errs.slice(0, 5).join(' | '));
await browser.close(); srv.close();
