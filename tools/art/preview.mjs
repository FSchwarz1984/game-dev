// Bundles src/art/preview.js (sprites inlined as data URLs) and screenshots it in headless
// Chromium: noon and dusk, desktop 1280x720 and phone 390x844, plus the native 480x270 canvas
// and its exact x4 upscale. Usage: node tools/art/preview.mjs [outDir]
// Default output: the session scratchpad shots/chars directory (or $SHOT_DIR).

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';
import { build } from 'esbuild';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..', '..');
const OUT = process.argv[2] || process.env.SHOT_DIR || '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad/shots/chars';
fs.mkdirSync(OUT, { recursive: true });

const result = await build({
  entryPoints: [path.join(ROOT, 'src/art/preview.js')],
  bundle: true, format: 'iife', target: 'es2020', write: false, logLevel: 'warning',
  loader: { '.png': 'dataurl', '.webp': 'dataurl' },
});
const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Character preview</title><body><script>${result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script')}</script>`;
const page = path.join(OUT, 'preview.html');
fs.writeFileSync(page, html);
console.log(`bundled ${(html.length / 1024).toFixed(0)} KB -> ${page}`);

const browser = await chromium.launch();
const errors = [];
const shots = [
  { name: 'desktop', ctx: { viewport: { width: 1280, height: 720 } } },
  { name: 'phone', ctx: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 } },
];
for (const preset of ['noon', 'dusk']) {
  for (const s of shots) {
    const context = await browser.newContext(s.ctx);
    const p = await context.newPage();
    p.on('console', m => { if (m.type() === 'error') errors.push(`${preset}/${s.name}: ${m.text()}`); });
    p.on('pageerror', e => errors.push(`${preset}/${s.name}: ${e.message}`));
    await p.goto(url.pathToFileURL(page).href + `?t=${preset}&time=1.3`);
    await p.waitForFunction(() => window.DONE === true, null, { timeout: 60000 });
    const file = path.join(OUT, `preview_${preset}_${s.name}.png`);
    await p.screenshot({ path: file });
    console.log('shot', file);
    if (s.name === 'desktop') {
      const data = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/png'));
      fs.writeFileSync(path.join(OUT, `preview_${preset}_native.png`), Buffer.from(data.split(',')[1], 'base64'));
    }
    await context.close();
  }
}
await browser.close();
if (errors.length) { console.log('console errors:\n' + errors.join('\n')); process.exitCode = 1; }
else console.log('no console errors');
