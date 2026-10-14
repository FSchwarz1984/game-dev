// Bundles the vista preview page (src/vista-test.js) into a folder with an index.html.
//   node tools/vista/build.mjs [outDir]
// Default outDir: $VISTA_OUT or .shots/vista-preview in the repository (git-ignored). Not part of the game build.

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';
import { build } from 'esbuild';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../..');
const OUT = path.resolve(process.argv[2] || process.env.VISTA_OUT || path.join(ROOT, '.shots/vista-preview'));

fs.mkdirSync(OUT, { recursive: true });
await build({
  entryPoints: [path.join(ROOT, 'src/vista-test.js')],
  bundle: true, minify: false, format: 'iife', target: 'es2020', charset: 'ascii',
  outfile: path.join(OUT, 'vista-test.js'), logLevel: 'warning', sourcemap: false,
});
fs.writeFileSync(path.join(OUT, 'index.html'), `<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Vista preview</title></head><body><script src="vista-test.js"></script></body></html>
`);
console.log('built', OUT);
