// The side-view vista (src/vista) on its own canvas over the game: integer-scaled, pixelated,
// letterboxed when the screen is too tall or too narrow for its native range (400–640 × 190–400).
// An upright phone gets an upright frame instead (360–640 wide, up to 2.4 times as tall): the
// shots are built for the size they are given, with more sky above the plain, so the view fills
// the screen rather than sitting in a band between two black ones.
// Created first, so the title backdrop is on screen while the map is still being baked.

import { createVista } from '../vista/index.js';

export function createVistaView(root) {
  const vista = createVista({ seed: 7 });
  const cv = vista.canvas;
  Object.assign(cv.style, { position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', imageRendering: 'pixelated', display: 'none', zIndex: 1 });
  root.appendChild(cv);
  const fit = () => {
    const dpr = Math.min(devicePixelRatio || 1, 3), Wd = innerWidth * dpr, Hd = innerHeight * dpr;
    const upright = Hd > Wd * 1.2, minW = upright ? 360 : 400, maxH = upright ? 900 : 400;
    const size = s => [Math.min(640, Math.max(minW, Math.ceil(Wd / s))), Math.min(maxH, Math.max(190, Math.ceil(Hd / s)))];
    // the largest integer scale whose native frame still fits the vista's range and the screen
    let s = 8;
    while (s > 1 && (Math.ceil(Wd / s) < minW || Math.ceil(Hd / s) < 190)) s--;
    let [W, H] = size(s);
    while (s > 1 && (W * s > Wd + s || H * s > Hd + s)) { s--; [W, H] = size(s); }
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
