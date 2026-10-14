// Side-view vistas: the title backdrop, the prologue's treetop view south over the plain (dusk to
// night: the lights rise, the sky shore appears, the wave of distance comes up the mountain), and
// the insert of the 「隔」 tower on the summit ridge. Canvas2D at native resolution, no dependencies.
//
//   const v = createVista({ seed });
//   v.resize(W, H);              // the host's native size (W 400..640, H ~190..400); rebuilds lazily
//   v.draw(dt, state);           // dt in seconds (clamped to 0.1)
//   v.canvas                     // native-resolution canvas: scale it up by an integer, pixelated
//   v.anchors                    // after draw, in canvas pixels:
//                                //   south: branch {x,y} (top of the limb where she sits; seat there),
//                                //          stand {x,y} (top of the limb where her feet go standing)
//                                //   title: moon {x,y}, text {x,y} (a calm spot for the title, centre-left)
//                                //   tower: lamp {x,y}, shaft {x,y}
//
// state = {
//   shot:  'title' | 'south' | 'tower'
//   tod:   17.5..21   south: 17.5 golden dusk -> ~18.6 sunset -> ~19.3 blue hour -> 20.5+ night
//   pan:   0..1       south: the crane up out of the crown (0 = among the leaves, 1 = over the plain)
//   rise:  0..1       south: the lights leave the plain in processions. 0.03 one light leaves the
//                     headman's house alone, 0.11 another a bonfire; from 0.21 each place (the
//                     headman's house, the bonfires, stretches of paddies, hamlets) sends its lights up
//                     one after another, a steady queue on a gentle S-curve, into a faint column of
//                     light over the town that goes up to the gate; its lamps go out from the edge in.
//                     Animate it (~25-40 s for 0..1; the pacing assumes ~30 s); a jump places the
//                     lights as if rise had run at 1/30 s. 60-120 lights in the air at once.
//   sky:   0..1       south: the cloud deck parts, the sky shore materialises (fully at ~0.75)
//   wave:  -1 | 0..1  south: -1 off; 0.2 ring round the town, 0.6 at the mountain foot, 0.85 at the
//                     tree (the foreground fills with motes), white at 1. Behind the front the land
//                     stays, a pale blue-grey ghost of itself, its lamps out.
//   tower: 1 | 0      tower: blinking; switching to 0 gives one last blink, then dark
//   figure: (g, anchors) => {}   south: called after the limb, before the leaves in front of it
// }
//
// Static layers are painted once per shot and size as material indices; palettes give the time of
// day (a new time is mapped a band per frame, the old one shown meanwhile). Each frame composites
// cached canvases at whole-pixel offsets; dynamic lights are summed into one additive buffer.
//   v.prepare(shot)          build now (desktop ~0.2-0.6 s for the south shot)
//   v.prepareAsync(shot, ms) build in slices of ~ms per tick (resolves when ready); call it early,
//                            e.g. prepare 'south' while the title or the walk up the pass is shown
//   v.ready(shot), v.stats { ms (last draw), build {shot: ms} }

import { makeCanvas, ctx2d, run } from './util.js';
import { southGen } from './south.js';
import { titleGen } from './title.js';
import { towerGen } from './tower.js';

const BUILDERS = { south: southGen, title: titleGen, tower: towerGen };

export function createVista({ seed = 7 } = {}) {
  let W = 480, H = 270;
  const canvas = makeCanvas(W, H), g = ctx2d(canvas);
  g.imageSmoothingEnabled = false;
  const shots = {}, pending = {};
  const start = name => {
    const B = BUILDERS[name];
    if (!B) throw new Error('vista: unknown shot ' + name);
    return (pending[name] = { gen: B(W, H, seed), ms: 0, size: W + 'x' + H });
  };
  const get = name => {
    let s = shots[name];
    if (!s) {
      const p = pending[name] || start(name);
      const t0 = performance.now();
      s = shots[name] = run(p.gen);
      delete pending[name];
      v.stats.build[name] = Math.round(p.ms + performance.now() - t0);
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
      for (const k in pending) delete pending[k];
    },
    prepare(name) { get(name); },
    // Build a shot in slices of ~budget ms per tick (setTimeout), so a phone keeps drawing frames
    // while it is prepared. Resolves when ready; draw() of that shot then costs no build time.
    prepareAsync(name, budget = 6) {
      if (shots[name]) return Promise.resolve();
      const p = pending[name] || start(name);
      if (p.promise) return p.promise;
      p.promise = new Promise((resolve, reject) => {
        const step = () => {
          if (shots[name]) { resolve(); return; }
          if (p.size !== W + 'x' + H) { delete pending[name]; v.prepareAsync(name, budget).then(resolve, reject); return; } // resized meanwhile
          const t0 = performance.now();
          try {
            let r;
            do { r = p.gen.next(); } while (!r.done && performance.now() - t0 < budget);
            p.ms += performance.now() - t0;
            if (r.done) { shots[name] = r.value; delete pending[name]; v.stats.build[name] = Math.round(p.ms); resolve(); }
            else setTimeout(step, 0);
          } catch (e) { reject(e); }
        };
        step();
      });
      return p.promise;
    },
    ready(name) { return !!shots[name]; },
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
