// The play HUD: the action keys, the prompt over the current target, her body gauge and the
// first-time tips, wired to the field (src/game/field.js). Renderer-independent: the caller
// supplies project(x, z, h) -> { x, y } in CSS pixels for a point h metres above the ground.

import { Actions } from './actions.js';
import { TargetPrompt } from './prompt.js';
import { BodyGauge } from './body.js';
import { QUALITY_INFO } from '../game/qualities.js';

const TIP_NEAR = 7; // metres: a tip on a thing shows only once she is this close

export class HUD {
  constructor(root, { field, project, audio = null, touch = false }) {
    injectStyle();
    this.f = field;
    this.project = project;
    this.audio = audio;
    this.visible = true;
    this.learned = [];
    this.actions = new Actions(root);
    this.prompt = new TargetPrompt(root);
    this.gauge = new BodyGauge(root);
    this.gauge.setQualities([]);
    this.tips = new Map();
    this.tipEl = document.createElement('div');
    this.tipEl.className = 'hud-tip';
    root.appendChild(this.tipEl);
    this.tipKey = null;
    if (touch) this.mountTouch();
    this.actions.on(a => this.onAction(a));
  }

  mountTouch() {
    if (this.actions.pad) return;
    this.actions.mountTouchPad({ secondary: [], rotate: false, qualities: this.learned });
    this.actions.setVisible(this.visible);
    this.touch = true;
  }

  show(on) {
    this.visible = on;
    this.actions.setVisible(on);
    this.gauge.setVisible(on);
    if (!on) { this.prompt.update(0, null); this.tipEl.classList.remove('on'); }
  }

  /** She has learned quality k: its key and its row in the gauge appear. */
  unlock(k) {
    if (this.learned.includes(k)) return;
    this.learned.push(k);
    this.actions.setQualities(this.learned);
    this.gauge.setQualities(this.learned);
  }

  tip(key, text, entity = null) { this.tips.set(key, { text, entity, t: 0 }); }
  untip(key) { this.tips.delete(key); }

  onAction(a) {
    const f = this.f, au = this.audio;
    if (!this.visible || !f.control) return;
    if (a.type === 'take' || a.type === 'give' || a.type === 'release') {
      const e = f.transfer(a.type, a.k);
      if (!e) return; // not learned: the key is not even shown
      if (e.type === 'refused') { this.prompt.say(e.reason, a.k); au?.sfx('deny'); }
      else {
        au?.sfx(a.type === 'take' ? 'take' : a.type === 'give' ? 'give' : 'release');
        au?.sfx('qual', { k: a.k, verb: a.type, n: f.player.holder.q[a.k] });
      }
    } else if (a.type === 'context') {
      if (f.context() === null && f.target) au?.sfx('deny');
    } else if (a.type === 'cycle') {
      f.targeting.cycle();
    }
  }

  update(dt) {
    const f = this.f;
    this.gauge.update(f.player.holder);
    const t = this.visible && f.control ? f.target : null;
    if (t) {
      const p = this.project(t.x, t.z, t.data.promptH ?? 1.6);
      const view = {
        name: t.name,
        tag: t.deep || t.far >= 0.99 ? '远' : '',
        holder: t.deep || t.data.showQualities === false || t.data.decor ? null : t.holder,
      };
      this.prompt.update(dt, view, p.x, p.y);
    } else this.prompt.update(dt, null);
    this.actions.setContext(this.visible ? f.contextLabel() : '', this.learned.length ? f.player.holder.q : null);

    // the newest tip whose thing is near enough; tips without a thing sit low in the middle
    let show = null;
    for (const [key, tp] of this.tips) {
      if (tp.entity && Math.hypot(tp.entity.x - f.player.x, tp.entity.z - f.player.z) > TIP_NEAR) continue;
      show = [key, tp];
    }
    if (!show || !this.visible || !f.control) { this.tipEl.classList.remove('on'); this.tipKey = null; return; }
    const [key, tp] = show;
    if (key !== this.tipKey) { this.tipKey = key; this.tipEl.innerHTML = colorize(tp.text); }
    this.tipEl.classList.add('on');
    let x = innerWidth / 2, y = innerHeight * 0.74;
    if (tp.entity) { const p = this.project(tp.entity.x, tp.entity.z, (tp.entity.data.promptH ?? 1.6) + 0.9); x = p.x; y = p.y - 34; }
    const w = this.tipEl.offsetWidth, h = this.tipEl.offsetHeight;
    const px = Math.max(8, Math.min(innerWidth - w - 8, x - w / 2)), py = Math.max(8, Math.min(innerHeight - h - 8, y - h));
    this.tipEl.style.transform = `translate(${px.toFixed(0)}px, ${py.toFixed(0)}px)`;
  }
}

// 「重」 and the like take their quality colour.
function colorize(text) {
  const esc = text.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  return esc.replace(/「(.)」/g, (m, ch) => {
    const info = Object.values(QUALITY_INFO).find(q => q.kanji === ch);
    return info ? `<b style="color:${info.color}">「${ch}」</b>` : m;
  });
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .hud-tip { position: fixed; left: 0; top: 0; z-index: 16; pointer-events: none; opacity: 0; transition: opacity .2s; padding: 6px 12px 7px; border-radius: 4px; background: rgba(14, 12, 18, .78); box-shadow: inset 0 0 0 1px rgba(214, 178, 106, .55); font: 600 14px/1.3 "Noto Serif SC", "Shippori Mincho", serif; color: #f3ecdc; white-space: nowrap; letter-spacing: .02em; }
  .hud-tip.on { opacity: 1; }
  .hud-tip b { font-weight: 700; }
  @media (max-width: 520px) { .hud-tip { font-size: 13px; padding: 5px 10px 6px; } }
  `;
  document.head.appendChild(s);
}
