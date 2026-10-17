// Bakes the vista data for Godot (godot/vista/data) from the JS vista code (src/vista at HEAD, plus
// the rising-light plan of 8196ebf), by running it in headless Chromium, then packs the images into
// Godot resources with a headless Godot script (tools/vista/pack.gd).
//
//   node tools/vista/bake.mjs                 the shipped data: godot/vista/data/<shot>.json + *.res
//   node tools/vista/bake.mjs --canon DIR     the 480x270 canonical variant (JS rows exactly) into DIR,
//                                             to check the Godot renderer against the JS one
//   options: --shots=south,title,tower  --preview DIR (PNG previews of the static layers)  --no-pack
//            --out DIR (pack into DIR instead of godot/vista/data: a trial bake for record.gd --data=DIR)
//
// Needs: node (esbuild from the repo), Playwright's Chromium (/opt/node22/lib/node_modules/playwright
// or $PLAYWRIGHT), and the Godot editor for packing ($GODOT_BIN or tools/godot/common.sh's default).
// Deterministic: the same sources give the same bytes (seeded generators; no time or network).

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import url from 'node:url';
import { execFileSync } from 'node:child_process';
import { build } from 'esbuild';
import { readPNG } from './pngread.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.findIndex(a => a === '--' + k || a.startsWith('--' + k + '=')); if (i < 0) return d; const a = args[i]; return a.includes('=') ? a.split('=')[1] : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const canonDir = opt('canon', null);
const previewDir = opt('preview', null);
const shots = String(opt('shots', 'south,title,tower')).split(',');
const outDir = opt('out', null);
const OUT = canonDir ? path.resolve(canonDir) : outDir ? path.resolve(outDir) : path.join(ROOT, 'godot/vista/data');
const RAW = path.join(ROOT, 'tools/vista/out', canonDir ? 'canon' : 'ship');
const { chromium } = await import(process.env.PLAYWRIGHT || '/opt/node22/lib/node_modules/playwright/index.mjs');

// The shipped canvas: wide and tall enough for every logical size the stage can make (480x270 up to
// 1024 x ~560, docs/knowledge/16 §2); the canon variant is the JS 480x270 frame exactly.
const VARIANTS = {
  ship: {
    south: { Wc: 1024, rowsAbove: 440, rowsBelow: 200, Dmax: 300, canopyTop: 140, canopyBottom: 20, classes: [270, 360, 450] },
    title: { Wc: 1024, Hc: 560 },
    tower: { Wc: 1024, Hc: 560 },
  },
  canon: { south: {}, title: {}, tower: {} },
};
const variant = canonDir ? 'canon' : 'ship';

const site = path.join(RAW, 'site');
fs.mkdirSync(site, { recursive: true });
// the 3D lookout's land (tools/world3d/w3terrain/vista.py output), which the south and title shots'
// plain is made from (tools/vista/bake/plain.js): its maps decoded here, byte for byte, for the page to fetch
if (shots.includes('south') || shots.includes('title')) {
  const W3DIR = path.join(ROOT, 'godot/world3d/terrain/saddle');
  const json = JSON.parse(fs.readFileSync(path.join(W3DIR, 'vista.json'), 'utf8'));
  const keep = {};
  for (const k of ['far', 'mid', 'plain', 'villages', 'plain_houses', 'plain_lamps', 'railway', 'road', 'landmarks', 'mist']) keep[k] = json[k];
  fs.writeFileSync(path.join(site, 'w3.json'), JSON.stringify(keep));
  for (const k of ['far', 'mid', 'plain']) {
    const p = readPNG(path.join(W3DIR, json[k].file));
    fs.writeFileSync(path.join(site, `w3_${k}.bin`), p.data);
    keep[k + 'Size'] = [p.w, p.h];
  }
  // the mid grid's land use (vista_mat.png: R cultivated, G road, B rock, A dry-stone wall)
  {
    const p = readPNG(path.join(W3DIR, json.mid.mat));
    fs.writeFileSync(path.join(site, 'w3_mat.bin'), p.data);
    keep.matSize = [p.w, p.h];
  }
  fs.writeFileSync(path.join(site, 'w3.json'), JSON.stringify(keep));
}
await build({ entryPoints: [path.join(ROOT, 'tools/vista/bake/page.js')], bundle: true, format: 'iife', target: 'es2020', charset: 'ascii', outfile: path.join(site, 'bake.js'), logLevel: 'warning' });
fs.writeFileSync(path.join(site, 'index.html'), '<!doctype html><html><head><meta charset="utf-8"></head><body><script src="bake.js"></script></body></html>');
const server = http.createServer((req, res) => {
  const p = path.join(site, decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : p.endsWith('.js') ? 'text/javascript' : 'application/octet-stream' }); res.end(d); });
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => window.BAKE_READY === true);
if (shots.includes('south') || shots.includes('title')) await page.evaluate(() => window.BAKE.loadW3());

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(RAW, { recursive: true });
let headDraws = null;
for (const shot of shots) {
  const t0 = Date.now();
  const o = { ...VARIANTS[variant][shot] };
  // (the south canopy's clumps come from the same random draws as the 480x270 JS frame: bakeSouth skips
  // to HEAD's frozen count, HEAD_DRAWS, before painting them)
  const d = await page.evaluate(([s, o2]) => window.BAKE[s](o2), [shot, o]);
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  const images = {};
  for (const [name, im] of Object.entries(d.images)) {
    const file = `${shot}_${name}.bin`;
    fs.writeFileSync(path.join(RAW, file), Buffer.from(im.b64, 'base64'));
    images[name] = { w: im.w, h: im.h, fmt: im.fmt, file };
  }
  delete d.images;
  d.imageFiles = images;
  fs.writeFileSync(path.join(RAW, `${shot}.json`), JSON.stringify(d));
  console.log(`${shot}: ${Date.now() - t0} ms, ${Object.keys(images).length} images${d.meta && d.meta.counts ? ', ' + JSON.stringify(d.meta.counts) : ''}`);
  if (previewDir && shot === 'south') {
    fs.mkdirSync(previewDir, { recursive: true });
    for (const [W, H] of [[480, 270], [600, 270], [640, 360], [1024, 560]]) {
      const png = await page.evaluate(([W2, H2]) => window.BAKE.preview('south', { W: W2, H: H2 }), [W, H]);
      if (png) fs.writeFileSync(path.join(previewDir, `south_static_${W}x${H}.png`), Buffer.from(png.split(',')[1], 'base64'));
    }
  }
}
await browser.close();
server.close();
void headDraws;

if (opt('no-pack', false)) process.exit(0);
// pack: raw images -> Godot Image resources (.res), lists -> JSON next to them
const godot = process.env.GODOT_BIN || '/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64';
execFileSync(godot, ['--headless', '--path', path.join(ROOT, 'godot'), '-s', path.join(ROOT, 'tools/vista/pack.gd'), '--', `--in=${RAW}`, `--out=${OUT}`, `--shots=${shots.join(',')}`], { stdio: 'inherit' });
