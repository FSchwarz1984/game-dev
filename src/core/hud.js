// DOM overlay for the test scene: touch buttons (rotate, cycle highlight, zoom) and the ?debug=1
// readout. Plain DOM, outside the post-processing chain.

const ICONS = {
  rotateLeft: '<path d="M8 9a8 8 0 1 1-1 9" /><path d="M8 3v6h6" />',
  rotateRight: '<path d="M16 9a8 8 0 1 0 1 9" /><path d="M16 3v6h-6" />',
  cycle: '<circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" />',
  zoom: '<circle cx="10.5" cy="10.5" r="6" /><path d="M15 15l5 5" /><path d="M8 10.5h5M10.5 8v5" />',
};
const LABELS = { rotateLeft: 'Rotate camera left', rotateRight: 'Rotate camera right', cycle: 'Next target', zoom: 'Zoom' };

export class Hud {
  constructor(root, input, { debug }) {
    this.touch = document.createElement('div');
    this.touch.className = 'touch-ui';
    for (const action of ['cycle', 'zoom', 'rotateLeft', 'rotateRight']) {
      const b = document.createElement('button');
      b.className = `touch-btn btn-${action}`;
      b.setAttribute('aria-label', LABELS[action]);
      b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[action]}</svg>`;
      b.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); input.trigger(action); });
      this.touch.appendChild(b);
    }
    root.appendChild(this.touch);
    const coarse = window.matchMedia?.('(pointer: coarse)').matches;
    this.showTouch(coarse || navigator.maxTouchPoints > 0);
    input.onTouch = () => this.showTouch(true);

    this.debug = null;
    if (debug) {
      this.debug = document.createElement('pre');
      this.debug.className = 'debug';
      root.appendChild(this.debug);
      this.acc = 0; this.frames = 0; this.msSum = 0;
    }
  }

  showTouch(on) { this.touch.style.display = on ? '' : 'none'; }

  /** frameMs: real frame interval; stats: { calls, triangles, tier, dpr, size, passes }. */
  updateDebug(frameMs, stats) {
    if (!this.debug) return;
    this.acc += frameMs; this.frames++; this.msSum += frameMs;
    if (this.acc < 250) return;
    const ms = this.msSum / this.frames;
    this.debug.textContent =
      `${(1000 / ms).toFixed(0)} fps  ${ms.toFixed(1)} ms\n` +
      `calls ${stats.calls}  tris ${(stats.triangles / 1000).toFixed(1)}k\n` +
      `tier ${stats.tier}  dpr ${stats.dpr}  ${stats.size}\n` +
      `${stats.passes}`;
    this.acc = 0; this.frames = 0; this.msSum = 0;
  }
}
