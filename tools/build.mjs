// Bundles the game into single self-contained HTML files (no network loads at runtime):
//   dist/game.html          standalone page
//   dist/game.artifact.html body-only variant (title, style, markup, script) for hosts that wrap
//                           the page in their own skeleton
// Both are pure ASCII so no host or missing charset can mis-decode them (v0.1 showed mojibake):
// non-ASCII becomes \uXXXX in JS and &#x...; in HTML (approach from legacy/v0.1/tools/build.mjs).

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';
import { build } from 'esbuild';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');

const asciiJS = s => s.replace(/[^\x00-\x7f]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
const asciiHTML = s => s.replace(/[^\x00-\x7f]/gu, c => '&#x' + c.codePointAt(0).toString(16) + ';');
const asciiCSS = s => s.replace(/[^\x00-\x7f]/gu, c => '\\' + c.codePointAt(0).toString(16) + ' ');

const result = await build({
  entryPoints: [path.join(ROOT, 'src/main.js')],
  bundle: true,
  minify: true,
  format: 'iife',
  target: 'es2020',
  charset: 'ascii',
  legalComments: 'none',
  write: false,
  logLevel: 'warning',
});
const js = asciiJS(result.outputFiles[0].text).replace(/<\/script/gi, '<\\/script');

const page = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const css = asciiCSS(page.match(/<style id="app-style">([\s\S]*?)<\/style>/)[1].trim());
const title = asciiHTML(page.match(/<title>([\s\S]*?)<\/title>/)[1]);
const markup = '<div id="app"></div>';
const viewport = '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">';

const full = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
${viewport}
<title>${title}</title>
<style>
${css}
</style>
</head>
<body>
${markup}
<script>
${js}
</script>
</body>
</html>
`;

// The artifact host allows Google Fonts; the standalone page stays offline (system fallbacks).
const fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@500;700&family=Noto+Serif+SC:wght@700&display=swap">';
const artifact = `<title>${title}</title>
${fonts}
<style>
:root{color-scheme:dark}
body{background:#0d0f14}
${css}
</style>
${markup}
<script>
${js}
</script>
`;

fs.mkdirSync(path.join(ROOT, 'dist'), { recursive: true });
for (const [name, text] of [['game.html', full], ['game.artifact.html', artifact]]) {
  const bad = text.search(/[^\x00-\x7f]/);
  if (bad >= 0) throw new Error(`${name}: non-ASCII character at offset ${bad}`);
  fs.writeFileSync(path.join(ROOT, 'dist', name), text);
}
console.log(`built dist/game.html (${(full.length / 1024).toFixed(0)} KB) and dist/game.artifact.html, pure ASCII`);
