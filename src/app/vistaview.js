// The side-view vista (src/vista) on its own canvas over the game: integer-scaled, pixelated,
// letterboxed when the screen is too tall or too narrow for its native range (400–640 × 190–400).
// Created first, so the title backdrop is on screen while the map is still being baked.

import { createVista } from '../vista/index.js';

export function createVistaView(root) {
  const vista = createVista({ seed: 7 });
  const cv = vista.canvas;
  Object.assign(cv.style, { position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', imageRendering: 'pixelated', display: 'none', zIndex: 1 });
  root.appendChild(cv);
  const fit = () => {
    const dpr = Math.min(devicePixelRatio || 1, 3), Wd = innerWidth * dpr, Hd = innerHeight * dpr;
    // the largest integer scale whose native frame still fits the vista's range and the screen
    let s = 8;
    while (s > 1 && (Math.ceil(Wd / s) < 400 || Math.ceil(Hd / s) < 190)) s--;
    let W = Math.min(640, Math.max(400, Math.ceil(Wd / s))), H = Math.min(400, Math.max(190, Math.ceil(Hd / s)));
    while (s > 1 && (W * s > Wd + s || H * s > Hd + s)) { s--; W = Math.min(640, Math.max(400, Math.ceil(Wd / s))); H = Math.min(400, Math.max(190, Math.ceil(Hd / s))); }
    vista.resize(W, H);
    cv.style.width = (W * s / dpr) + 'px'; cv.style.height = (H * s / dpr) + 'px';
  };
  fit();
  addEventListener('resize', fit);
  let state = null;
  return {
    vista, canvas: cv,
    get state() { return state; },
    show(s) { state = s; cv.style.display = s ? 'block' : 'none'; },
    draw(dt) { if (state) vista.draw(dt, state); },
  };
}
