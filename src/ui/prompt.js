// The prompt that hangs over the current target: its name, the qualities it holds as pips
// (e.g. 重 ●●○), and a short line when a transfer is refused. The caller projects the
// target's world position to screen pixels each frame; this module only draws DOM.

import { QUALITIES, QUALITY_INFO, REFUSAL } from '../game/qualities.js';

const REFUSAL_TEXT = {
  [REFUSAL.sacred]: '注连绳：动不了',
  [REFUSAL.empty]: q => `没有${QUALITY_INFO[q].kanji}了`,
  [REFUSAL.full]: '装不下了',
  [REFUSAL.overload]: '身体承受不住了',
  far: '太远了',
  none: '附近没有可以对它用的东西',
  heavy: '太重了，背不动',
};

export class TargetPrompt {
  constructor(root = document.body) {
    injectStyle();
    this.el = document.createElement('div');
    this.el.className = 'tgt';
    this.el.innerHTML = '<div class="tgt-name"></div><div class="tgt-q"></div><div class="tgt-st"></div><div class="tgt-say"></div>';
    root.appendChild(this.el);
    this.nameEl = this.el.querySelector('.tgt-name');
    this.qEl = this.el.querySelector('.tgt-q');
    this.sayEl = this.el.querySelector('.tgt-say');
    this.stEl = this.el.querySelector('.tgt-st');
    this.key = '';
    this.sayT = 0;
  }

  /**
   * target: { name, holder?, status? } or null; status is a short line such as a building
   * stage or what a crop is missing. (sx, sy): projected screen position of the point
   * above the target, in CSS pixels.
   */
  update(dt, target, sx, sy) {
    if (!target) { this.el.classList.remove('on'); return; }
    this.el.classList.add('on');
    const w = this.el.offsetWidth, h = this.el.offsetHeight;
    const x = Math.max(8, Math.min(innerWidth - w - 8, sx - w / 2));
    const y = Math.max(8, Math.min(innerHeight - h - 8, sy - h - 6));
    this.el.style.transform = `translate(${x.toFixed(0)}px, ${y.toFixed(0)}px)`;

    const hd = target.holder;
    const key = target.name + '|' + (target.status || '') + '|' + (hd ? QUALITIES.map(k => hd.q[k] + '/' + hd.max[k]).join(',') + (hd.sacred ? '!' : '') : '');
    if (key !== this.key) {
      this.key = key;
      this.nameEl.textContent = target.name;
      this.stEl.textContent = target.status || '';
      this.qEl.innerHTML = hd ? QUALITIES.filter(k => hd.q[k] > 0 || hd.base[k] > 0).map(k => {
        const n = hd.q[k], cap = Math.max(n, hd.base[k], 1);
        return `<span style="--qc:${QUALITY_INFO[k].color}"><b>${QUALITY_INFO[k].kanji}</b>${'●'.repeat(n)}${'○'.repeat(Math.max(0, cap - n))}</span>`;
      }).join('') + (hd.sacred ? '<span class="tgt-sacred">注连绳</span>' : '') : '';
    }
    if (this.sayT > 0) { this.sayT -= dt; if (this.sayT <= 0) this.sayEl.classList.remove('on'); }
  }

  /** A short line under the prompt, e.g. after a refused transfer. */
  say(reason, k) {
    const t = REFUSAL_TEXT[reason];
    this.sayEl.textContent = typeof t === 'function' ? t(k) : (t || reason);
    this.sayEl.classList.add('on');
    this.sayT = 1.6;
  }

  dispose() { this.el.remove(); }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .tgt { position: fixed; left: 0; top: 0; z-index: 15; pointer-events: none; opacity: 0; transition: opacity .12s; font: 500 13px/1.35 "Noto Sans SC", "PingFang SC", system-ui, sans-serif; color: #f4f1ea; text-shadow: 0 1px 2px rgba(0,0,0,.6); }
  .tgt.on { opacity: 1; }
  .tgt-name { font: 700 14px/1.2 "Noto Serif SC", "Shippori Mincho", serif; text-align: center; }
  .tgt-q { display: flex; gap: 6px; justify-content: center; margin-top: 2px; white-space: nowrap; }
  .tgt-q span { color: var(--qc); letter-spacing: 1px; }
  .tgt-q b { color: #f4f1ea; margin-right: 2px; font-weight: 700; }
  .tgt-st { text-align: center; font-size: 12px; color: #e9dfc4; margin-top: 1px; }
  .tgt-st:empty { display: none; }
  .tgt-sacred { color: #f0b7a8 !important; }
  .tgt-say { margin-top: 3px; text-align: center; color: #ffd9a8; opacity: 0; transform: translateY(4px); transition: opacity .12s, transform .12s; }
  .tgt-say.on { opacity: 1; transform: none; }
  @media (prefers-reduced-motion: reduce) { .tgt, .tgt-say { transition: none; } }
  `;
  document.head.appendChild(s);
}
