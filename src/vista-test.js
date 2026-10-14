// Preview page for the vistas (not part of the game build). Bundled by tools/vista/build.mjs.
//   ?shot=title|south|tower  &tod=17.5..21 &pan= &rise= &sky= &wave= &tower=0|1
//   &w=&h=          force the native size (otherwise from the viewport, integer scale)
//   &fig=0          hide the stand-in figure (the real sprite is drawn by the host)
//   &manual=1       no animation loop; drive with window.VT.render(state, frames, dt)
//   &seq=1          play the prologue sequence on a loop (dusk pan, rise, sky, wave); &seqt0=s starts it at s
// window.DONE is set after the first frame.

import { createVista } from './vista/index.js';

const q = new URLSearchParams(location.search);
const num = (k, d) => (q.has(k) ? parseFloat(q.get(k)) : d);

document.body.style.cssText = 'margin:0;background:#000;overflow:hidden;height:100vh';
if (q.has('tune')) globalThis.VISTA_TUNE = JSON.parse(q.get('tune'));   // temporary tuning hook
const v = createVista({ seed: num('seed', 7) });
const cv = v.canvas;
cv.style.cssText = 'position:absolute;image-rendering:pixelated;image-rendering:crisp-edges';
document.body.appendChild(cv);

let scale = 1;
function fit() {
  const iw = innerWidth, ih = innerHeight;
  if (q.has('w') && q.has('h')) {
    v.resize(num('w', 480), num('h', 270));
    scale = Math.max(1, Math.floor(Math.min(iw / v.W, ih / v.H)));
  } else {
    scale = Math.max(1, Math.round(Math.min(iw / 480, ih / 250)));
    v.resize(Math.ceil(iw / scale), Math.ceil(ih / scale));
  }
  cv.style.width = v.W * scale + 'px';
  cv.style.height = v.H * scale + 'px';
  cv.style.left = Math.floor((iw - v.W * scale) / 2) + 'px';
  cv.style.top = Math.floor((ih - v.H * scale) / 2) + 'px';
}
fit();
addEventListener('resize', fit);

// Stand-in for the host's sprite of Tsuzumi (seen from behind): a wide hat, long dark hair, a white
// haori. Only for judging composition in previews.
function standIn(g, a, st) {
  const p = st.standing ? a.stand : a.branch;
  if (!p) return;
  const x = Math.round(p.x), y = Math.round(p.y);
  const hat = '#2b3157', band = '#8c2a33', hair = '#1a1424', haori = '#c9c4b8', haoriS = '#8f8c86', ink = '#0d0d14';
  const R = (c, X, Y, w, h) => { g.fillStyle = c; g.fillRect(x + X, y + Y, w, h); };
  if (st.standing) {
    R(ink, -3, -4, 2, 4); R(ink, 1, -4, 2, 4);            // legs
    R(haori, -5, -20, 10, 16); R(haoriS, 2, -20, 3, 16);  // body
    R(hair, -3, -26, 6, 18);                              // hair down the back
    R(haori, -8, -20, 3, 9); R(haori, 5, -20, 3, 9);      // sleeves
    R(hat, -10, -30, 20, 3); R(hat, -6, -33, 12, 3); R(band, -6, -30, 12, 1);
  } else {
    R(haori, -5, -13, 10, 11); R(haoriS, 2, -13, 3, 11);
    R(hair, -3, -18, 6, 14);
    R(ink, -6, -2, 12, 2);                                // folded legs on the limb
    R(hat, -10, -22, 20, 3); R(hat, -6, -25, 12, 3); R(band, -6, -22, 12, 1);
  }
}

const state = {
  shot: q.get('shot') || 'title', tod: num('tod', 21), pan: num('pan', 1), rise: num('rise', 0), sky: num('sky', 0),
  wave: num('wave', -1), tower: num('tower', 1), standing: q.get('stand') === '1',
};
const showFig = q.get('fig') !== '0';
state.figure = showFig ? (g, a) => standIn(g, a, state) : null;

// the prologue on a loop: (seconds) 0-6 pan at dusk, 6-12 dusk to night, 12-40 rise, 26-36 sky, 38-48 wave
function sequence(T) {
  const k = (a, b) => Math.min(1, Math.max(0, (T - a) / (b - a)));
  state.shot = 'south';
  state.pan = k(0, 6);
  state.tod = 17.5 + 3.4 * k(5, 12);
  state.rise = k(12, 40);
  state.sky = k(24, 34);
  state.wave = T < 38 ? -1 : k(38, 48);
  state.standing = T > 40;
}

window.VT = {
  v, state,
  render(over = {}, frames = 1, dt = 1 / 60) {
    Object.assign(state, over);
    for (let i = 0; i < frames; i++) v.draw(dt, state);
    return { ms: v.stats.ms, build: v.stats.build, anchors: v.anchors, W: v.W, H: v.H, scale, info: v.info && v.info() };
  },
};

if (q.get('manual') === '1') {
  v.draw(1 / 60, state);
  window.DONE = true;
} else {
  let last = performance.now(), T0 = last - num('seqt0', 0) * 1000, first = true;
  const loop = now => {
    const dt = (now - last) / 1000; last = now;
    if (q.get('seq') === '1') sequence(((now - T0) / 1000) % 52);
    v.draw(dt, state);
    if (first) { first = false; window.DONE = true; }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}
