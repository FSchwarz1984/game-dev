// Contact sheets of the env painters, rendered in Node (no browser): albedo on a mid ground colour,
// optionally scaled. Fast feedback while painting assets.
//   node tools/env/sheet.mjs flora|flora1|props|camphor [scale] [outfile]
import path from 'node:path';
import { writePNG } from './png.mjs';

const SCR = '/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad/env';
const which = process.argv[2] || 'flora', scale = +(process.argv[3] || 3);
const out = process.argv[4] || path.join(SCR, `sheet-${which}.png`);

async function items() {
  if (which === 'flora') {
    const F = await import('../../src/env/flora.js');
    return [
      ...[1, 2, 3].map(i => ['cedar' + i, () => F.cedar(i, 150 + i * 14, 46 + i * 3)]),
      ...[1, 2].map(i => ['pine' + i, () => F.pine(i, 110 + i * 10, i === 2 ? 0.8 : 0)]),
      ['maple', () => F.maple(1)], ['mapleR', () => F.maple(2, true)],
      ['cam1', () => F.bush(1, 'camellia', 34, 24)], ['aza', () => F.bush(2, 'azalea', 30, 18)], ['hyd', () => F.hydrangea(1)],
      ['fern', () => F.fern(1)], ['fern2', () => F.fern(2, 0.8)], ['sasa', () => F.sasa(1)], ['sus', () => F.susuki(1)], ['lily', () => F.lily(1)],
      ['moss', () => F.mossClump(1)], ['bam', () => F.bamboo(1)],
      ...[0, 1, 2, 3].map(k => ['tuft' + k, () => F.tuft(k + 1, k)]),
    ];
  }
  if (which === 'props') { const P = await import('../../src/env/props.js'); return P.PREVIEW(); }
  if (which === 'camphor') { const C = await import('../../src/env/camphor.js'); return C.PREVIEW(); }
  if (which === 'flora1') { const F = await import('../../src/env/flora1.js'); return F.PREVIEW(); }
  throw new Error('unknown sheet ' + which);
}

const list = await items(); const rendered = [];
for (const [name, fn] of list) { const t0 = Date.now(); const r = fn(); const s = r.s || r; rendered.push({ name, s, ms: Date.now() - t0 }); }
// shelf layout
const MAXW = 1400; let x = 0, y = 0, rowH = 0; for (const r of rendered) { if (x + r.s.w > MAXW) { x = 0; y += rowH + 6; rowH = 0; } r.x = x; r.y = y; x += r.s.w + 6; rowH = Math.max(rowH, r.s.h); }
const W = MAXW, H = y + rowH; const img = new Uint8Array(W * scale * H * scale * 4);
for (let i = 0; i < img.length; i += 4) { img[i] = 78; img[i + 1] = 104; img[i + 2] = 64; img[i + 3] = 255; }
for (const r of rendered) for (let yy = 0; yy < r.s.h; yy++) for (let xx = 0; xx < r.s.w; xx++) {
  const k = (yy * r.s.w + xx) * 4; if (!r.s.c[k + 3]) continue;
  for (let sy = 0; sy < scale; sy++) for (let sx = 0; sx < scale; sx++) { const d = (((r.y + yy) * scale + sy) * W * scale + (r.x + xx) * scale + sx) * 4; img[d] = r.s.c[k]; img[d + 1] = r.s.c[k + 1]; img[d + 2] = r.s.c[k + 2]; }
}
writePNG(out, W * scale, H * scale, img);
console.log(rendered.map(r => `${r.name} ${r.s.w}x${r.s.h} ${r.ms}ms`).join(' | '));
console.log('wrote', out);
