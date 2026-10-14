// Screenshots of the vista preview page (build it first: node tools/vista/build.mjs).
//   node tools/vista/shot.mjs name:query [name:query ...]
//     query: URL params for the page (shot=south&tod=21&rise=.5 ...); prefix the name with
//     "phone/" for an 844x390 viewport (default 1280x720), "big/" for 1920x1080.
//     Extra params: frames=N (frames drawn before the capture, dt 1/60), seqn=N&seqdt=S to capture
//     N native frames S seconds apart (name-000.png ...), with ramp=key,from,to[,u0,u1] (repeatable)
//     changing a state value every frame over the part u0..u1 of the sequence.
//   Output: $SHOT_DIR or .shots/vista in the repository (git-ignored); <name>.png (page) and
//   <name>.native.png (the native canvas, 1:1). The page is served from $VISTA_OUT or .shots/vista-preview.
//   Playwright: $PLAYWRIGHT or the global install under /opt/node22.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import url from 'node:url';

const { chromium } = await import(process.env.PLAYWRIGHT || '/opt/node22/lib/node_modules/playwright/index.mjs');
const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../..');
const SITE = path.resolve(process.env.VISTA_OUT || path.join(ROOT, '.shots/vista-preview'));
const OUT = path.resolve(process.env.SHOT_DIR || path.join(ROOT, '.shots/vista'));
fs.mkdirSync(OUT, { recursive: true });

const server = http.createServer((req, res) => {
  const p = path.join(SITE, decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  fs.readFile(p, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : 'text/javascript' });
    res.end(d);
  });
});
await new Promise(r => server.listen(0, r));
const port = server.address().port;

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const VIEW = { '': [1280, 720], phone: [844, 390], big: [1920, 1080], small: [960, 540] };
for (const arg of process.argv.slice(2)) {
  const ci = arg.indexOf(':');
  let name = arg.slice(0, ci), query = arg.slice(ci + 1);
  let vp = VIEW[''];
  const slash = name.indexOf('/');
  if (slash > 0 && VIEW[name.slice(0, slash)]) vp = VIEW[name.slice(0, slash)];
  const fileBase = name.replace(/\//g, '_');
  const page = await browser.newPage({ viewport: { width: vp[0], height: vp[1] } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const params = new URLSearchParams(query);
  const frames = parseInt(params.get('frames') || '30', 10);
  const seqn = parseInt(params.get('seqn') || '0', 10), seqdt = parseFloat(params.get('seqdt') || '0.1');
  await page.goto(`http://localhost:${port}/index.html?manual=1&${query}`);
  await page.waitForFunction(() => window.DONE === true, null, { timeout: 120000 });
  const st = {};
  for (const k of ['tod', 'pan', 'rise', 'sky', 'wave', 'tower']) if (params.has(k)) st[k] = parseFloat(params.get(k));
  if (params.has('shot')) st.shot = params.get('shot');
  if (params.has('stand')) st.standing = params.get('stand') === '1';
  const info = await page.evaluate(([s, n]) => window.VT.render(s, n), [st, frames]);
  if (seqn) {
    // optional parameter ramps over the whole sequence, applied every frame:
    // ramp=key,from,to[,u0,u1] (the change happens over the part u0..u1 of the sequence)
    const ramps = params.getAll('ramp').map(r => r.split(',').map((v, i) => (i ? +v : v)));
    const steps = Math.max(1, Math.round(seqdt * 60));
    for (let i = 0; i < seqn; i++) {
      await page.evaluate(([ramps, i, seqn, steps]) => {
        const total = Math.max(1, (seqn - 1) * steps);
        for (let j = 0; j < steps; j++) {
          const u = Math.min(1, ((i - 1) * steps + j + 1) / total), over = {};
          for (const [k, a, b, u0 = 0, u1 = 1] of ramps) over[k] = a + (b - a) * Math.min(1, Math.max(0, (u - u0) / (u1 - u0)));
          window.VT.render(i === 0 ? {} : over, 1);
        }
      }, [ramps, i, seqn, steps]);
      const data = await page.evaluate(() => window.VT.v.canvas.toDataURL('image/png'));
      fs.writeFileSync(path.join(OUT, `${fileBase}-${String(i).padStart(3, '0')}.png`), Buffer.from(data.split(',')[1], 'base64'));
    }
  } else {
    await page.screenshot({ path: path.join(OUT, fileBase + '.png') });
    const data = await page.evaluate(() => window.VT.v.canvas.toDataURL('image/png'));
    fs.writeFileSync(path.join(OUT, fileBase + '.native.png'), Buffer.from(data.split(',')[1], 'base64'));
  }
  // frame cost: average of a few more frames
  const cost = await page.evaluate(() => { const t0 = performance.now(); for (let i = 0; i < 20; i++) window.VT.v.draw(1 / 60, window.VT.state); return (performance.now() - t0) / 20; });
  console.log(`${name}: native ${info.W}x${info.H} x${info.scale} build ${JSON.stringify(info.build)} frame ${cost.toFixed(2)}ms anchors ${JSON.stringify(info.anchors)}${process.env.INFO ? '\n  ' + JSON.stringify(info.info) : ''}${errors.length ? '\n  ERRORS: ' + errors.join(' | ') : ''}`);
  await page.close();
}
await browser.close();
server.close();
