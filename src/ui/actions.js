// Semantic actions for the approved control scheme A (decision-log D13): choose the target
// first, then the quality. Keyboard: 1–5 take, Shift+1–5 give, L release, E context,
// F dispatch, R recall, Tab cycle target, Space dodge, [ ] rotate camera.
// Touch: a large context button with the five quality keys around it (tap = take,
// swipe up = give, swipe down = release), plus dispatch / recall / dodge / rotate keys.
// Every key is at least 48 CSS px and shows a glow ring wider than a fingertip.
// Movement axes are not handled here (the input module owns the stick and WASD).

import { QUALITIES, QUALITY_INFO } from '../game/qualities.js';

const KEY_QUALITY = { Digit1: 'w', Digit2: 'h', Digit3: 'l', Digit4: 's', Digit5: 'v' };
const KEY_ACTION = {
  KeyE: 'context', KeyF: 'dispatch', KeyR: 'recall', Tab: 'cycle', Space: 'dodge',
  BracketLeft: 'rotateLeft', BracketRight: 'rotateRight', KeyL: 'releaseMenu',
};

export class Actions {
  constructor(root = document.body) {
    this.root = root;
    this.handlers = new Set();
    this.pendingRelease = false; // L then a number releases that quality
    this.contextLabel = '';
    this.qualityAmounts = null;
    this.onKey = this.onKey.bind(this);
    window.addEventListener('keydown', this.onKey);
    this.pad = null;
  }

  on(fn) { this.handlers.add(fn); return () => this.handlers.delete(fn); }
  emit(a) { for (const fn of this.handlers) fn(a); }

  onKey(e) {
    if (e.repeat) return;
    const k = KEY_QUALITY[e.code];
    if (k) {
      e.preventDefault();
      const verb = this.pendingRelease ? 'release' : e.shiftKey ? 'give' : 'take';
      this.pendingRelease = false;
      this.emit({ type: verb, k });
      return;
    }
    const act = KEY_ACTION[e.code];
    if (!act) return;
    e.preventDefault();
    if (act === 'releaseMenu') { this.pendingRelease = true; this.emit({ type: 'releaseArmed' }); return; }
    this.emit({ type: act });
  }

  /**
   * Build the touch pad. Call once when the device has touch (or with ?touch=1).
   * opts.secondary: which of dispatch / dodge / recall to show; opts.rotate: the camera keys
   * (none in the 2D game); opts.qualities: the quality keys shown at first (see setQualities).
   */
  mountTouchPad({ secondary = ['dispatch', 'dodge', 'recall'], rotate = true, qualities = QUALITIES } = {}) {
    if (this.pad) return this.pad;
    const SEC = { dispatch: ['派遣', '派'], dodge: ['闪避', '避'], recall: ['召回', '召'] };
    const pad = document.createElement('div');
    pad.className = 'act-pad';
    pad.innerHTML = `
      <button class="act-ctx" data-a="context" aria-label="情境动作"><span></span></button>
      ${QUALITIES.map(k => `<button class="act-q" data-k="${k}" style="--qc:${QUALITY_INFO[k].color}" aria-label="${QUALITY_INFO[k].kanji}：点一下取，上滑予，下滑放"><b>${QUALITY_INFO[k].kanji}</b><i></i></button>`).join('')}
      ${secondary.map(a => `<button class="act-s act-o" data-a="${a}" aria-label="${SEC[a][0]}">${SEC[a][1]}</button>`).join('')}
      ${rotate ? `<div class="act-rot">
        <button class="act-s" data-a="rotateLeft" aria-label="镜头左转">↺</button>
        <button class="act-s" data-a="rotateRight" aria-label="镜头右转">↻</button>
      </div>` : ''}`;
    this.root.appendChild(pad);
    injectStyle();
    this.shownQualities = [...qualities];
    // Layout: the five quality keys on a 108° arc around the context button (from just below
    // horizontal-left to just right of vertical), radius following the screen width, with at least
    // 6 px between keys; the secondary keys in a column on the right edge above the arc, or in a
    // row along the bottom on short (landscape) screens. Everything stays in the right half, so
    // the left half is the stick's.
    const layout = () => {
      const R = Math.max(112, Math.min(130, innerWidth * 0.3)), cx = 42, cy = 42;
      const place = (el, a, r, half) => {
        el.style.right = (cx - half - Math.cos(a) * r).toFixed(1) + 'px';
        el.style.bottom = (cy - half + Math.sin(a) * r).toFixed(1) + 'px';
      };
      let slot = 0;
      pad.querySelectorAll('.act-q').forEach(b => {
        const on = this.shownQualities.includes(b.dataset.k);
        b.hidden = !on;
        if (on) place(b, (190 - slot++ * 27) * Math.PI / 180, R, 26);
      });
      const short = innerHeight < 520;
      pad.querySelectorAll('.act-o').forEach((b, i) => {
        const along = (cx + R + 56 + i * 60 - 24).toFixed(1) + 'px';
        b.style.right = short ? along : '0px';
        b.style.bottom = short ? '0px' : along;
      });
    };
    this.layout = layout;
    layout();
    addEventListener('resize', layout);
    const glow = el => { el.classList.add('down'); try { navigator.vibrate?.(8); } catch (e) { /* not supported */ } };
    const unglow = el => el.classList.remove('down');

    for (const b of pad.querySelectorAll('[data-a]')) {
      b.addEventListener('pointerdown', ev => { ev.preventDefault(); glow(b); this.emit({ type: b.dataset.a }); });
      for (const t of ['pointerup', 'pointercancel', 'pointerleave']) b.addEventListener(t, () => unglow(b));
    }
    for (const b of pad.querySelectorAll('.act-q')) {
      let y0 = 0, active = false;
      b.addEventListener('pointerdown', ev => { ev.preventDefault(); active = true; y0 = ev.clientY; glow(b); b.setPointerCapture?.(ev.pointerId); });
      b.addEventListener('pointermove', ev => {
        if (!active) return;
        const dy = ev.clientY - y0;
        b.dataset.dir = dy < -22 ? 'give' : dy > 22 ? 'release' : 'take';
      });
      const end = () => {
        if (!active) return;
        active = false; unglow(b);
        const verb = b.dataset.dir || 'take';
        delete b.dataset.dir;
        this.emit({ type: verb, k: b.dataset.k });
      };
      b.addEventListener('pointerup', end);
      b.addEventListener('pointercancel', () => { active = false; unglow(b); delete b.dataset.dir; });
    }
    this.pad = pad;
    return pad;
  }

  /** Show only these quality keys (the ones she has learned); a newly shown key announces itself. */
  setQualities(ks) {
    const fresh = ks.filter(k => !(this.shownQualities || []).includes(k));
    this.shownQualities = [...ks];
    if (!this.pad) return;
    this.layout();
    for (const k of fresh) {
      const b = this.pad.querySelector(`.act-q[data-k="${k}"]`);
      b.classList.remove('fresh'); void b.offsetWidth; b.classList.add('fresh');
    }
  }

  /** Show or hide the whole pad (hidden during scenes). */
  setVisible(on) { if (this.pad) this.pad.classList.toggle('off', !on); }

  /** Keep the touch pad in sync with what the context button would do and what she carries. */
  setContext(label, amounts) {
    if (!this.pad) return;
    if (label !== this.contextLabel) {
      this.contextLabel = label;
      this.pad.querySelector('.act-ctx span').textContent = label || '';
      this.pad.querySelector('.act-ctx').classList.toggle('idle', !label);
    }
    if (amounts) for (const b of this.pad.querySelectorAll('.act-q')) b.querySelector('i').textContent = amounts[b.dataset.k] ?? '';
  }

  dispose() {
    window.removeEventListener('keydown', this.onKey);
    this.pad?.remove();
  }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .act-pad { position: fixed; right: calc(14px + env(safe-area-inset-right, 0px)); bottom: calc(14px + env(safe-area-inset-bottom, 0px)); width: 236px; height: 236px; z-index: 20; touch-action: none; user-select: none; -webkit-user-select: none; pointer-events: none; }
  .act-pad button, .act-rot { pointer-events: auto; } /* the overlay root is pointer-events: none so the stick can see the canvas; the keys must opt back in */
  .act-pad button { position: absolute; border: 0; padding: 0; font: 700 18px/1 "Noto Serif SC", "Shippori Mincho", serif; color: #f4f1ea; background: rgba(16, 18, 28, .62); box-shadow: inset 0 0 0 1.5px rgba(244, 241, 234, .35); border-radius: 50%; touch-action: none; }
  .act-pad button::after { content: ""; position: absolute; inset: -10px; border-radius: 50%; border: 2px solid rgba(255, 236, 190, 0); transition: border-color .12s, inset .12s; pointer-events: none; }
  .act-pad button.down::after { border-color: rgba(255, 236, 190, .9); inset: -16px; }
  .act-ctx { right: 0; bottom: 0; width: 84px; height: 84px; font-size: 22px !important; }
  .act-ctx.idle { opacity: .55; }
  .act-q { width: 52px; height: 52px; box-shadow: inset 0 0 0 2px var(--qc) !important; }
  .act-q b { display: block; font-size: 19px; }
  .act-q i { position: absolute; right: -2px; top: -4px; min-width: 18px; font: 600 11px/18px system-ui, sans-serif; font-style: normal; background: var(--qc); color: #1b1d26; border-radius: 9px; }
  .act-q i:empty { display: none; }
  .act-q[data-dir="give"] { transform: translateY(-10px); }
  .act-q[data-dir="release"] { transform: translateY(10px); }
  .act-s { width: 48px; height: 48px; font-size: 16px !important; }
  .act-rot { position: fixed; right: calc(16px + env(safe-area-inset-right, 0px)); top: calc(16px + env(safe-area-inset-top, 0px)); display: flex; gap: 12px; }
  .act-rot .act-s { position: relative; }
  .act-pad.off { opacity: 0; visibility: hidden; transition: opacity .25s, visibility 0s .25s; }
  .act-pad { transition: opacity .25s; }
  .act-q[hidden] { display: none; }
  .act-q.fresh { animation: act-fresh 1.6s ease-out; }
  @keyframes act-fresh { 0% { transform: scale(.2); opacity: 0; } 30% { transform: scale(1.25); opacity: 1; box-shadow: 0 0 0 10px color-mix(in srgb, var(--qc) 50%, transparent), inset 0 0 0 2px var(--qc); } 100% { transform: none; } }
  @media (prefers-reduced-motion: reduce) { .act-pad button::after { transition: none; } }
  `;
  document.head.appendChild(s);
}
