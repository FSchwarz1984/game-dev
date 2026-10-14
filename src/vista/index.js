// Side-view vistas: the title backdrop, the prologue's treetop view south over the plain (dusk to
// night: the lights rise, the sky shore appears, the wave of distance comes up the mountain), and
// the insert of the 「隔」 tower on the summit ridge.
//
//   const v = createVista({ seed });
//   v.resize(W, H);          // native size, W 400..640, H 200..400
//   v.draw(dt, state);       // dt in seconds
//   v.canvas                 // native-resolution canvas; scale it up by an integer
//   v.anchors                // per shot, after draw: e.g. south: { branch: {x, y}, stand: {x, y} }
//
// state = { shot: 'title' | 'south' | 'tower', tod: 17.5..21, pan: 0..1, rise: 0..1, sky: 0..1,
//           wave: -1 | 0..1, tower: 0 | 1, figure: (g, anchors) => {} }
//
// Static layers are painted once per shot and size (index buffers + palettes per time of day);
// each frame only composites cached canvases at whole-pixel offsets and draws the moving lights.
// v.prepare(shot) builds a shot ahead of time (do it under a fade: ~100-300 ms on a desktop).

import { makeCanvas, ctx2d } from './util.js';
import { buildSouth } from './south.js';
import { buildTitle } from './title.js';
import { buildTower } from './tower.js';

const BUILDERS = { south: buildSouth, title: buildTitle, tower: buildTower };

export function createVista({ seed = 7 } = {}) {
  let W = 480, H = 270;
  const canvas = makeCanvas(W, H), g = ctx2d(canvas);
  g.imageSmoothingEnabled = false;
  const shots = {};
  const get = name => {
    let s = shots[name];
    if (!s) {
      const B = BUILDERS[name];
      if (!B) throw new Error('vista: unknown shot ' + name);
      const t0 = performance.now();
      s = shots[name] = B(W, H, seed);
      v.stats.build[name] = Math.round(performance.now() - t0);
    }
    return s;
  };
  const v = {
    canvas, anchors: {}, stats: { ms: 0, build: {} },
    get W() { return W; }, get H() { return H; },
    resize(w, h) {
      w = Math.max(64, Math.round(w)); h = Math.max(64, Math.round(h));
      if (w === W && h === H) return;
      W = w; H = h; canvas.width = W; canvas.height = H; g.imageSmoothingEnabled = false;
      for (const k in shots) delete shots[k];
    },
    prepare(name) { get(name); },
    info() { const o = {}; for (const k in shots) o[k] = shots[k].info; return o; },
    draw(dt, state = {}) {
      const s = get(state.shot || 'title');
      const t0 = performance.now();
      g.save();
      g.imageSmoothingEnabled = false;
      s.draw(g, Math.min(0.1, Math.max(0, dt || 0)), state);
      g.restore();
      v.anchors = s.anchors || {};
      v.stats.ms = performance.now() - t0;
    },
  };
  return v;
}
