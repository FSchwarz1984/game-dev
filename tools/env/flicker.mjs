// Character light stability while walking under the canopy: holds a direction key, captures a crop
// around her every few frames and prints the mean luminance of her pixels (they should drift slowly
// as she passes from light into shade, never jump frame to frame). Also saves the crops as a strip.
//   node tools/env/flicker.mjs [query]
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { writePNG } from './png.mjs';

const SCR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad';
const PAGE = process.env.PAGE_DIR || SCR + '/env/page';
const OUT = process.env.SHOT_DIR || SCR + '/shots/home2d';
const query = process.argv[2] || 'x=44&z=33.5&t=12.5';
function serve(dir) {
  const srv = http.createServer((req, res) => { const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
    fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': p.endsWith('.js') ? 'text/javascript' : 'text/html' }); res.end(d); }); });
  return new Promise(r => srv.listen(0, () => r(srv)));
}
const srv = await serve(PAGE); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
await page.goto(`http://localhost:${port}/index.html?hud=0&shotmode=1&${query}`);
await page.waitForFunction(() => window.READY || window.ERR, null, { timeout: 120000 });
await page.waitForFunction(() => (window.FR || 0) >= 4, null, { timeout: 60000 });
await page.keyboard.down('KeyD');
const crops = []; const lum = [];
for (let k = 0; k < 16; k++) {
  const f0 = await page.evaluate(() => window.FR); await page.waitForFunction(n => window.FR >= n, f0 + 2);
  const buf = await page.screenshot({ clip: { x: 640 - 60, y: 360 - 120, width: 120, height: 150 } });
  crops.push(buf);
}
await page.keyboard.up('KeyD');
const pos = await page.evaluate(() => [ENV.actor.x, ENV.actor.z]);
await browser.close(); srv.close();
// decode PNGs with the browser-free path: use Python (PIL) for luminance of non-ground pixels
fs.mkdirSync(OUT + '/flicker', { recursive: true });
crops.forEach((b, i) => fs.writeFileSync(`${OUT}/flicker/f${String(i).padStart(2, '0')}.png`, b));
console.log('frames saved to', OUT + '/flicker', 'end position', pos.map(v => v.toFixed(2)).join(', '));
