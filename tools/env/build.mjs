// Builds the env test page (src/env-test.js) into a folder with index.html + env.js.
//   node tools/env/build.mjs [outDir]     default: $ENV_OUT or the session scratchpad env/page
// After bundling it bakes the map in Node and runs the reachability check (NO_REACH=1 skips it).
// The page is for internal review only (never delivered): it shows the 2D renderer and the home area.
import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';
import { build } from 'esbuild';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../..');
const OUT = process.argv[2] || process.env.ENV_OUT || '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad/env/page';
fs.mkdirSync(OUT, { recursive: true });
const t0 = Date.now();
await build({
  entryPoints: [path.join(ROOT, 'src/env-test.js')], bundle: true, format: 'iife', target: 'es2020', charset: 'ascii',
  minify: !!process.env.MINIFY, sourcemap: false, outfile: path.join(OUT, 'env.js'), logLevel: 'warning',
  loader: { '.png': 'dataurl', '.webp': 'dataurl' },
});
fs.writeFileSync(path.join(OUT, 'index.html'), `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>home 2D</title>
<style>html,body{margin:0;height:100%;background:#0d0f14;overflow:hidden;overscroll-behavior:none}body{touch-action:none;user-select:none}#app{position:fixed;inset:0;overflow:hidden}</style>
</head><body><div id="app"></div><script src="env.js"></script></body></html>
`);
console.log(`built ${OUT}/index.html + env.js (${(fs.statSync(path.join(OUT, 'env.js')).size / 1024).toFixed(0)} KB) in ${Date.now() - t0} ms`);
// every bake is checked: the story's places must be reachable from the road (src/env/reach.js)
if (!process.env.NO_REACH) {
  const { createHomeMap } = await import('../../src/env/home.js');
  const { checkReach } = await import('../../src/env/reach.js');
  const r = checkReach(createHomeMap({}));
  const bad = r.results.filter(t => !t.ok);
  if (bad.length) { for (const t of bad) console.error(`REACH FAIL ${t.name} (${t.x}, ${t.z}): ${t.why}`); process.exit(1); }
  console.log(`reach: all ${r.results.length} places reachable from the road entry`);
}
