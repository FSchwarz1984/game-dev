// In-browser entry of the vista bake (bundled by tools/vista/bake.mjs, run in headless Chromium so
// the JS vista code runs exactly as it did in the game, canvas and all).
//   window.BAKE.south(opts) / title(opts) / tower(opts) -> { meta, lists..., images: {name: {w, h, fmt, b64}} }
//   window.BAKE.preview(shot, opts) -> PNG data URL of the static layers (a quick look, not exported)

import { bakeSouth } from './south.js';
import { setW3 } from './plain.js';
import { bakeTitle } from './title.js';
import { bakeTower } from './tower.js';
import { b64 } from './common.js';
import { makeCanvas, ctx2d, clamp } from '../../../src/vista/util.js';
import { todEnv, palette, skyAt } from '../../../src/vista/tod.js';
import { paintSky } from '../../../src/vista/sky.js';

const cache = {};

function serialize(d) {
  const out = {};
  for (const k in d) {
    if (k.startsWith('_')) continue;
    if (k === 'images') {
      out.images = {};
      for (const name in d.images) {
        const im = d.images[name];
        out.images[name] = { w: im.w, h: im.h, fmt: im.fmt || 'rgba8', b64: b64(im.data) };
      }
    } else out[k] = d[k];
  }
  return out;
}

function lutPal(space, lut, row) {
  return v => {
    const id = space.idOf.get(v);
    if (!id) return 0;
    const o = (row * lut.w + id) * 4, D = lut.data;
    return ((D[o + 3] << 24) | (D[o + 2] << 16) | (D[o + 1] << 8) | D[o]) >>> 0;
  };
}

// the 3D lookout's land for the south shot's plain (written next to the page by tools/vista/bake.mjs)
async function loadW3() {
  const json = await (await fetch('w3.json')).json();
  const map = async (k) => {
    const data = new Uint8Array(await (await fetch(`w3_${k}.bin`)).arrayBuffer());
    const [w, h] = json[k + 'Size'];
    return { w, h, x0: json[k].x0, z0: json[k].z0, cell: json[k].cell, data };
  };
  setW3({ json, far: await map('far'), mid: await map('mid'), plain: await map('plain') });
  return true;
}

window.BAKE = {
  loadW3,
  south(opts) { const d = bakeSouth(opts); cache.south = d; return serialize(d); },
  title(opts) { const d = bakeTitle(opts); cache.title = d; return serialize(d); },
  tower(opts) { const d = bakeTower(opts); cache.tower = d; return serialize(d); },
  // static layers of the last south bake for a view W x H (pan 1, sky shore shown), at a time of day
  preview(shot, { W = 480, H = 270, tod = 20.3, reveal = 1 } = {}) {
    const d = cache[shot];
    if (!d || shot !== 'south') return null;
    const m = d.meta, L = d._layers, row = Math.round(clamp((tod - m.tod0) / m.todStep, 0, m.todRows - 1));
    const c = makeCanvas(W, H), g = ctx2d(c);
    const yh = Math.round(clamp(H * 0.475, H - 165, H - 118));
    const fx = Math.round((W - m.refW) / 2) - m.ox, fy = yh - m.YL;      // far group offset (pan 1)
    const env = todEnv(tod);
    g.drawImage(paintSky(m.Wc, m.GH, m.YL, m.S, env), fx, fy);
    if (reveal > 0) { g.globalAlpha = reveal; g.drawImage(L.shore.layer.canvas('p' + row, lutPal(L.sSpace, d.images.lutShore, row)), fx, fy); g.globalAlpha = 1; }
    g.drawImage(L.ground.layer.canvas('p' + row, lutPal(L.gSpace, d.images.lutGround, row)), fx, fy);
    const cy = H - m.CT - m.oyC;                                            // canopy group (pan 1)
    g.drawImage(L.back.layer.canvas('p' + row, lutPal(L.fSpace, d.images.lutFoliage, row)), fx, cy);
    g.drawImage(L.frontC.layer.canvas('p' + row, lutPal(L.fSpace, d.images.lutFoliage, row)), fx, cy);
    g.fillStyle = '#f0e0d0';
    const a = m.anchors.branch; g.fillRect(a.x + fx - 2, a.y + cy - 12, 4, 12);
    g.fillStyle = '#ff4060';
    g.fillRect(Math.round(m.T[0]) + fx, Math.round(m.T[1]) + fy, 1, 1);
    void skyAt; void palette;
    return c.toDataURL('image/png');
  },
};
window.BAKE_READY = true;
