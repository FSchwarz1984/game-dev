// Bundle the game into single self-contained HTML files.
//   dist/tsuzura.html          — standalone page (open directly in a browser)
//   dist/tsuzura.artifact.html — body-only variant for hosts that wrap the page in their own skeleton
import fs from "fs"; import path from "path"; import url from "url";
const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const css = fs.readFileSync(path.join(ROOT, "src/style.css"), "utf8");
const block = html.match(/<!-- BUILD:SCRIPTS -->([\s\S]*?)<!-- \/BUILD:SCRIPTS -->/)[1];
const files = [...block.matchAll(/src="([^"]+)"/g)].map(m => m[1]);
let js = "";
for (const f of files) { const src = fs.readFileSync(path.join(ROOT, f), "utf8"); js += `\n/* ==== ${f} ==== */\n` + src.replace(/^"use strict";\s*/m, ""); }
js = '"use strict";\n' + js.replace(/<\/script/gi, "<\\/script");
// keep the bundles pure ASCII so no host or header can mis-decode them (in-game text is mostly CJK)
const asciiJS = s => s.replace(/[^\x00-\x7f]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
const asciiHTML = s => s.replace(/[^\x00-\x7f]/gu, c => "&#x" + c.codePointAt(0).toString(16) + ";");
const asciiCSS = s => s.replace(/[^\x00-\x7f]/gu, c => "\\" + c.codePointAt(0).toString(16) + " ");
js = asciiJS(js);
const fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;900&family=Shippori+Mincho:wght@500;800&family=Yuji+Syuku&family=DotGothic16&family=Zhi+Mang+Xing&display=swap">';
const body = `<div id="app"><canvas id="cv" aria-label="${asciiHTML("游戏画面")}"></canvas><div id="ui"></div></div>\n<script>\n${js}\n</script>`;
const title = asciiHTML("ツヅラ　遠囃子");
const full = `<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">\n<title>${title}</title>\n<meta name="theme-color" content="#0c0b10">\n${fonts}\n<style>\n${asciiCSS(css)}\n</style>\n</head>\n<body>\n${body}\n</body>\n</html>\n`;
const art = `<title>${title}</title>\n${fonts}\n<style>\n:root{color-scheme:dark}\nbody{background:#0c0b10}\n${asciiCSS(css)}\n</style>\n${body}\n`;
fs.mkdirSync(path.join(ROOT, "dist"), { recursive: true });
fs.writeFileSync(path.join(ROOT, "dist/tsuzura.html"), full);
fs.writeFileSync(path.join(ROOT, "dist/tsuzura.artifact.html"), art);
console.log("built", files.length, "files,", (full.length / 1024).toFixed(0) + " KB");
