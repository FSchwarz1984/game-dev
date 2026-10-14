// Dev server: esbuild watches src/ and serves the repo root, with the bundle at /.dev/main.js
// (served from memory, rebuilt on change). Open the printed URL; add ?debug=1 for stats.

import path from 'node:path';
import url from 'node:url';
import { context } from 'esbuild';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.PORT) || 8080;

const ctx = await context({
  entryPoints: [path.join(ROOT, 'src/main.js')],
  bundle: true,
  format: 'iife',
  target: 'es2020',
  sourcemap: true,
  outfile: path.join(ROOT, '.dev/main.js'),
  logLevel: 'info',
  loader: { '.png': 'dataurl', '.webp': 'dataurl', '.mp3': 'dataurl' }, // art assets ship inside the single-file build
});
await ctx.watch();
const { hosts } = await ctx.serve({ servedir: ROOT, port });
console.log(`dev server: http://${hosts[0] === '0.0.0.0' ? 'localhost' : hosts[0]}:${port}/index.html`);
