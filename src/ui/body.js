// Her body gauge: the five qualities she holds, one row each, with her natural level marked.
// The body itself shows the state in the world; this is the exact count, kept small in a corner
// and flashed when a number changes so the eye is drawn to it only then.

import { QUALITIES, QUALITY_INFO } from '../game/qualities.js';

export class BodyGauge {
  constructor(root = document.body) {
    injectStyle();
    this.el = document.createElement('div');
    this.el.className = 'body-g';
    this.el.innerHTML = QUALITIES.map(k => `<div class="bg-row" data-k="${k}" style="--qc:${QUALITY_INFO[k].color}"><b>${QUALITY_INFO[k].kanji}</b><span></span></div>`).join('');
    root.appendChild(this.el);
    this.rows = Object.fromEntries([...this.el.querySelectorAll('.bg-row')].map(r => [r.dataset.k, r]));
    this.last = {};
  }

  /** Show only the rows of qualities she has learned (none: the gauge hides). */
  setQualities(ks) {
    this.shown = [...ks];
    for (const k of QUALITIES) this.rows[k].hidden = !ks.includes(k);
    this.el.classList.toggle('off', !ks.length);
  }

  setVisible(on) { this.el.classList.toggle('hide', !on); }

  update(holder) {
    for (const k of QUALITIES) {
      const n = holder.q[k], base = holder.base[k], max = Math.max(holder.max[k] ?? 9, n);
      const key = n + '/' + base;
      if (this.last[k] === key) continue;
      const row = this.rows[k];
      if (this.last[k] !== undefined) { row.classList.remove('flash'); void row.offsetWidth; row.classList.add('flash'); }
      this.last[k] = key;
      let pips = '';
      for (let i = 1; i <= max; i++) pips += `<i class="${i <= n ? 'on' : ''}${i === base ? ' base' : ''}"></i>`;
      row.querySelector('span').innerHTML = pips;
    }
  }

  dispose() { this.el.remove(); }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .body-g { position: fixed; left: calc(12px + env(safe-area-inset-left, 0px)); top: calc(12px + env(safe-area-inset-top, 0px)); z-index: 14; pointer-events: none; padding: 7px 9px 6px; border-radius: 8px; background: rgba(20, 16, 24, .42); backdrop-filter: blur(2px); font: 700 13px/1 "Noto Serif SC", "Shippori Mincho", serif; color: #f4f1ea; }
  .bg-row { display: flex; align-items: center; gap: 6px; height: 17px; }
  .bg-row[hidden] { display: none; }
  .body-g.off, .body-g.hide { opacity: 0; } .body-g { transition: opacity .25s; }
  .bg-row b { width: 14px; text-align: center; text-shadow: 0 1px 2px rgba(0,0,0,.7); }
  .bg-row span { display: flex; gap: 2px; }
  .bg-row i { width: 7px; height: 7px; border-radius: 50%; box-sizing: border-box; border: 1.5px solid color-mix(in srgb, var(--qc) 55%, transparent); }
  .bg-row i.on { background: var(--qc); border-color: var(--qc); box-shadow: 0 0 5px color-mix(in srgb, var(--qc) 70%, transparent); }
  .bg-row i.base { outline: 1px solid rgba(255,255,255,.75); outline-offset: 1px; }
  .bg-row.flash { animation: bg-flash .5s ease-out; }
  @keyframes bg-flash { 0% { transform: translateX(4px) scale(1.08); filter: brightness(1.8); } 100% { transform: none; filter: none; } }
  @media (max-width: 520px) { .body-g { left: calc(8px + env(safe-area-inset-left, 0px)); top: calc(8px + env(safe-area-inset-top, 0px)); padding: 5px 7px; font-size: 12px; } .bg-row { height: 15px; } .bg-row i { width: 6px; height: 6px; } }
  `;
  document.head.appendChild(s);
}
