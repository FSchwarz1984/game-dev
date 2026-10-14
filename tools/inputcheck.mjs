// Real-input check: drives the built page through the same input paths a player uses (touch taps
// and swipes on the on-screen keys, keyboard keys on desktop) and asserts the game reacted.
// Never call game functions to perform the action under test; only to set up the scene.
// Usage: node tools/inputcheck.mjs [dist/game.html]
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs'; // pre-installed in this container (see tools/shot.mjs)
import path from 'node:path';

const page_ = path.resolve(process.argv[2] || 'dist/game.html');
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let failed = 0;
const check = (ok, what) => { console.log(`${ok ? 'ok  ' : 'FAIL'}  ${what}`); if (!ok) failed++; };

async function open(ctxOpts, query) {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.goto('file://' + page_ + query);
  await page.waitForFunction(() => window.DONE, null, { timeout: 120000 });
  // set up only: stand next to the boulder, facing it, and let the targeting settle
  await page.evaluate(() => {
    window.MANUAL = true;
    const S = APP.sim, r = S.entities.find(e => e.kind === 'rock');
    S.player.x = r.x; S.player.z = r.z + r.r + 1.0; S.player.fx = 0; S.player.fz = -1;
    APP.simulate(0.5);
  });
  return { ctx, page, errs };
}
const weight = page => page.evaluate(() => APP.sim.player.holder.q.w);
const centre = (page, sel) => page.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, sel);

// --- phone: tap = take, swipe up = give, context key, through real touch events --------------
{
  const { ctx, page, errs } = await open({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }, '?q=low&touch=1');
  check(await page.evaluate(() => APP.sim.target?.kind === 'rock'), 'phone: the boulder is targeted');
  const w0 = await weight(page);
  const key = await centre(page, '.act-q[data-k="w"]');
  await page.touchscreen.tap(key.x, key.y);
  await page.evaluate(() => APP.simulate(0.3));
  check(await weight(page) === w0 + 1, `phone: tapping 重 takes weight (${w0} → ${await weight(page)})`);
  // swipe up on the same key gives it back
  const cdp = await ctx.newCDPSession(page);
  const touch = (type, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: key.x, y }] });
  await touch('touchStart', key.y); await touch('touchMove', key.y - 15); await touch('touchMove', key.y - 40); await touch('touchEnd');
  await page.evaluate(() => APP.simulate(0.3));
  check(await weight(page) === w0, `phone: swiping 重 up gives weight back (now ${await weight(page)})`);
  // the context key answers (the shrine resets her body)
  await page.evaluate(() => { const S = APP.sim, s = S.entities.find(e => e.kind === 'shrine'); S.player.holder.q.h = 3; S.player.x = s.x; S.player.z = s.z + s.r + 1.2; S.player.fx = 0; S.player.fz = -1; APP.simulate(0.5); });
  const ctxKey = await centre(page, '.act-ctx');
  await page.touchscreen.tap(ctxKey.x, ctxKey.y);
  await page.evaluate(() => APP.simulate(0.2));
  check(await page.evaluate(() => APP.sim.player.holder.q.h === APP.sim.player.holder.base.h), 'phone: the context key at the shrine returns her heat');
  // the stick still works: a touch on the left half moves her
  const x0 = await page.evaluate(() => APP.sim.player.x);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 90, y: 600 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 150, y: 600 }] });
  await page.evaluate(() => APP.simulate(0.5));
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  check(await page.evaluate(() => APP.sim.player.x) !== x0, 'phone: the stick moves her');
  check(errs.length === 0, `phone: no page errors ${errs.join(' | ')}`);
  await ctx.close();
}

// --- desktop: keyboard keys after a click on the page ------------------------------------------
{
  const { ctx, page, errs } = await open({ viewport: { width: 1280, height: 720 } }, '?q=low');
  await page.mouse.click(640, 360);
  const w0 = await weight(page);
  await page.keyboard.press('Digit1');
  await page.evaluate(() => APP.simulate(0.3));
  check(await weight(page) === w0 + 1, `desktop: key 1 takes weight (${w0} → ${await weight(page)})`);
  await page.keyboard.down('Shift'); await page.keyboard.press('Digit1'); await page.keyboard.up('Shift');
  await page.evaluate(() => APP.simulate(0.3));
  check(await weight(page) === w0, 'desktop: Shift+1 gives it back');
  check(errs.length === 0, `desktop: no page errors ${errs.join(' | ')}`);
  await ctx.close();
}
await browser.close();
console.log(failed ? `${failed} check(s) failed` : 'all input checks passed');
process.exit(failed ? 1 : 0);
