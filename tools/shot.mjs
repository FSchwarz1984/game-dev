// Headless verification: serves the repo, opens dist/game.html in Playwright Chromium (SwiftShader),
// waits for window.DONE, advances by frames (SwiftShader runs at single-digit fps, so never by
// milliseconds) and captures screenshots, render stats and console errors.
//   node tools/shot.mjs                 all shots
//   node tools/shot.mjs noon night      a subset
// The flicker-* shots also compare 8 consecutive frames: the share of pixels that change inside the
// idle character versus an equal box of nearby ground (v0.1 measured 13-20 % on its character).
// Output: $SHOT_DIR or the session scratchpad (see DEFAULT_DIR). One browser at a time.

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import url from 'node:url';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const DEFAULT_DIR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad/shots/g3';
const OUT = process.env.SHOT_DIR || DEFAULT_DIR;
const PAGE = process.env.SHOT_PAGE || 'dist/game.html';

const DESKTOP = { viewport: { width: 960, height: 540 } };
const PHONE = { isMobile: true, hasTouch: true, deviceScaleFactor: 3 };

// Each shot: page query, context options, and optional steps run before the capture.
const SHOTS = {
  noon: { query: 'view=render&q=high&t=noon', ctx: DESKTOP },
  evening: { query: 'view=render&q=high&t=evening', ctx: DESKTOP },
  night: { query: 'view=render&q=high&t=night', ctx: DESKTOP },
  rot90: { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [rotate(1)] },
  rot180: { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [rotate(1), rotate(1)] },
  'phone-portrait': { query: 'view=render&q=low&t=noon', ctx: { ...PHONE, viewport: { width: 390, height: 844 } } },
  'phone-landscape': { query: 'view=render&q=low&t=noon', ctx: { ...PHONE, viewport: { width: 844, height: 390 } } },
  'canopy-noon': { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [teleport(-1.5, -9.5)] },
  'canopy-night': { query: 'view=render&q=high&t=night', ctx: DESKTOP, steps: [teleport(-1.5, -9.5)] },
  highlight: { query: 'view=render&q=high&t=evening', ctx: DESKTOP, steps: [teleport(1.5, 0.5), cycle()] },
  'highlight-sprite': { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [teleport(-8.8, 7.4), cycle()] },
  occlusion: { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [teleport(-12, -0.2)] },
  'occlusion-cliff': { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [teleport(4, -20.4), rotate(1), rotate(1)] },
  morning: { query: 'view=render&q=high&t=morning', ctx: DESKTOP },
  vista: { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [zoom(), zoom()] },
  'low-desktop': { query: 'view=render&q=low&t=noon', ctx: DESKTOP },
  'flicker-canopy': { query: 'view=render&q=high&t=noon', ctx: DESKTOP, steps: [teleport(-1.5, -9.5)], flicker: true },
  'flicker-low': { query: 'view=render&q=low&t=evening', ctx: DESKTOP, steps: [teleport(-1.5, -9.5)], flicker: true },
};

// Runs inside the page: copies the WebGL canvas right after each tick (same task, so the drawing
// buffer is intact) and counts pixels whose RGB changes by more than 12/255 between frames.
function measureFlicker(frameCount) {
  const src = document.querySelector('canvas.view');
  const copy = document.createElement('canvas');
  copy.width = src.width; copy.height = src.height;
  const g = copy.getContext('2d', { willReadFrequently: true });
  const { player, camera, renderer } = APP;
  const toPx = v => { const p = v.clone().project(camera); return [(p.x * 0.5 + 0.5) * src.width, (0.5 - p.y * 0.5) * src.height]; };
  const feet = toPx(player.position);
  const head = toPx(player.position.clone().setY(player.position.y + player.scale.y * 1.1));
  const h = feet[1] - head[1], w = Math.max(4, Math.round(h * 0.22));
  const y0 = Math.round(head[1] + h * 0.25), bh = Math.max(4, Math.round(h * 0.6));
  const boxes = { character: [Math.round(feet[0] - w / 2), y0, w, bh], ground: [Math.round(feet[0] + w * 3), y0, w, bh] };
  const frames = [];
  return new Promise(resolve => {
    const tick = APP.tick;
    APP.tick = dt => {
      tick(dt);
      g.drawImage(src, 0, 0);
      frames.push(Object.fromEntries(Object.entries(boxes).map(([k, b]) => [k, g.getImageData(...b).data])));
      if (frames.length > frameCount) {
        APP.tick = tick;
        const out = {};
        for (const k of Object.keys(boxes)) {
          const ratios = [];
          for (let f = 1; f < frames.length; f++) {
            const a = frames[f - 1][k], b = frames[f][k];
            let changed = 0;
            for (let i = 0; i < a.length; i += 4) {
              if (Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2])) > 12) changed++;
            }
            ratios.push(changed / (a.length / 4));
          }
          out[k] = (100 * ratios.reduce((s, r) => s + r, 0) / ratios.length).toFixed(2) + ' %';
        }
        out.box = boxes.character.join(',');
        out.dpr = renderer.getPixelRatio();
        resolve(out);
      }
    };
  });
}

function rotate(dir) {
  return async (page, frames) => { await page.evaluate(d => APP.rig.rotate(d), dir); await frames(12); };
}
function teleport(x, z) {
  return async (page, frames) => {
    await page.evaluate(([px, pz]) => {
      const c = APP.controller;
      c.pos.set(px, APP.world.terrain.heightAt(px, pz), pz);
      APP.rig.snap(c.pos);
    }, [x, z]);
    await frames(6);
  };
}
function cycle() {
  return async (page, frames) => { await page.keyboard.press('Tab'); await frames(4); };
}
function zoom() {
  return async (page, frames) => { await page.keyboard.press('KeyZ'); await frames(14); };
}

function serve() {
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.png': 'image/png' };
  const server = http.createServer((req, res) => {
    const file = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404).end(); return; }
    res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

async function shoot(browser, base, name, shot) {
  const context = await browser.newContext(shot.ctx);
  const page = await context.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(`${base}/${PAGE}?${shot.query}`);
  await page.waitForFunction(() => window.DONE === true, null, { timeout: 240000 });
  await page.evaluate(() => {
    window.__fr = 0;
    const tick = APP.tick;
    APP.tick = dt => { window.__fr++; return tick(dt); };
  });
  const frames = async n => {
    const f0 = await page.evaluate(() => window.__fr);
    await page.waitForFunction(t => window.__fr >= t, f0 + n, { timeout: 240000 });
  };
  await frames(8);
  for (const step of shot.steps || []) await step(page, frames);
  await frames(6);
  const flicker = shot.flicker ? await page.evaluate(measureFlicker, 8) : null;
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file });
  const info = await page.evaluate(() => ({
    ...APP.stats(),
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  await context.close();
  return { name, file, info, errors, flicker };
}

fs.mkdirSync(OUT, { recursive: true });
const wanted = process.argv.slice(2);
const names = wanted.length ? wanted : Object.keys(SHOTS);
const server = await serve();
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let failed = false;
try {
  for (const name of names) {
    if (!SHOTS[name]) throw new Error(`unknown shot ${name}`);
    const r = await shoot(browser, base, name, SHOTS[name]);
    const i = r.info;
    console.log(`${name}: ${r.file}\n  tier ${i.tier} dpr ${i.dpr} ${i.size} | calls ${i.calls} | tris ${i.triangles} | overflowX ${i.overflowX}\n  passes ${i.passes}`);
    if (r.flicker) console.log(`  changed pixels per frame: character ${r.flicker.character}, nearby ground ${r.flicker.ground} (box ${r.flicker.box})`);
    for (const e of r.errors) { console.log(`  console error: ${e}`); failed = true; }
  }
} finally {
  await browser.close();
  server.close();
}
console.log(failed ? 'console errors found' : 'no console errors');
process.exitCode = failed ? 1 : 0;
