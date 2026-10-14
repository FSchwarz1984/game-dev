// Movement axes and test-scene actions from keyboard, gamepad and touch.
// move: screen-relative (x right, y up), length <= 1; the caller maps it through the camera basis.
// Actions are edge-triggered: rotateLeft, rotateRight, cycle, zoom, time.
// Rotation is on [ and ] (E is the context action in the approved scheme), gamepad shoulders and
// the on-screen buttons. A floating stick appears wherever a thumb lands on the left half.

const KEY_ACTIONS = {
  BracketLeft: 'rotateLeft', BracketRight: 'rotateRight',
  Tab: 'cycle', KeyH: 'cycle', KeyZ: 'zoom', KeyT: 'time',
};
const PAD_ACTIONS = { 4: 'rotateLeft', 5: 'rotateRight', 12: 'zoom', 15: 'cycle' }; // LB, RB, d-pad up/right
const PREVENT = new Set(['Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space']);
const DEADZONE = 0.18;

export class Input {
  constructor(surface, stickRoot) {
    this.keys = new Set();
    this.pressed = new Set();
    this.move = { x: 0, y: 0 };
    this.padButtons = [];
    this.stick = null;
    this.onTouch = null; // called once when touch input is first seen

    window.addEventListener('keydown', e => {
      if (PREVENT.has(e.code)) e.preventDefault();
      this.keys.add(e.code);
      if (!e.repeat && KEY_ACTIONS[e.code]) this.trigger(KEY_ACTIONS[e.code]);
    });
    window.addEventListener('keyup', e => this.keys.delete(e.code));
    window.addEventListener('blur', () => { this.keys.clear(); this.endStick(); });

    this.stickBase = div('stick-base', stickRoot);
    this.stickKnob = div('stick-knob', this.stickBase);
    surface.addEventListener('pointerdown', e => this.startStick(e));
    window.addEventListener('pointermove', e => this.moveStick(e));
    window.addEventListener('pointerup', e => { if (this.stick?.id === e.pointerId) this.endStick(); });
    window.addEventListener('pointercancel', e => { if (this.stick?.id === e.pointerId) this.endStick(); });
  }

  trigger(action) { this.pressed.add(action); }
  /** True once per press. */
  consume(action) { return this.pressed.delete(action); }

  startStick(e) {
    if (e.pointerType === 'mouse' || this.stick || e.clientX > window.innerWidth * 0.5) return;
    if (this.onTouch) { this.onTouch(); this.onTouch = null; }
    const r = Math.max(44, Math.min(70, Math.min(window.innerWidth, window.innerHeight) * 0.12));
    this.stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: 0, y: 0, r };
    Object.assign(this.stickBase.style, { left: `${e.clientX}px`, top: `${e.clientY}px`, width: `${r * 2}px`, height: `${r * 2}px`, display: 'block' });
    this.moveStick(e);
  }

  moveStick(e) {
    const s = this.stick;
    if (!s || s.id !== e.pointerId) return;
    let dx = e.clientX - s.x0, dy = e.clientY - s.y0;
    const d = Math.hypot(dx, dy), maxD = s.r * 1.3;
    if (d > maxD) { // the base follows the thumb
      s.x0 = e.clientX - dx / d * maxD; s.y0 = e.clientY - dy / d * maxD;
      dx = e.clientX - s.x0; dy = e.clientY - s.y0;
      Object.assign(this.stickBase.style, { left: `${s.x0}px`, top: `${s.y0}px` });
    }
    const m = Math.min(1, Math.hypot(dx, dy) / s.r);
    const a = Math.atan2(-dy, dx);
    s.x = m < 0.12 ? 0 : Math.cos(a) * m;
    s.y = m < 0.12 ? 0 : Math.sin(a) * m;
    this.stickKnob.style.transform = `translate(${s.x * s.r}px, ${-s.y * s.r}px)`;
  }

  endStick() {
    this.stick = null;
    this.stickBase.style.display = 'none';
    this.stickKnob.style.transform = '';
  }

  update() {
    const k = this.keys;
    let x = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    let y = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    if (x && y) { x *= Math.SQRT1_2; y *= Math.SQRT1_2; }

    const pad = firstPad();
    if (pad) {
      const ax = pad.axes[0] || 0, ay = -(pad.axes[1] || 0);
      const m = Math.hypot(ax, ay);
      if (m > DEADZONE) { // radial dead zone, rescaled so motion starts at zero
        const s = Math.min(1, (m - DEADZONE) / (1 - DEADZONE)) / m;
        x = ax * s; y = ay * s;
      }
      pad.buttons.forEach((b, i) => {
        if (b.pressed && !this.padButtons[i] && PAD_ACTIONS[i]) this.trigger(PAD_ACTIONS[i]);
        this.padButtons[i] = b.pressed;
      });
    }
    if (this.stick && (this.stick.x || this.stick.y)) { x = this.stick.x; y = this.stick.y; }
    this.move.x = x;
    this.move.y = y;
  }
}

function firstPad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const p of pads) if (p && p.connected) return p;
  return null;
}

function div(className, parent) {
  const el = document.createElement('div');
  el.className = className;
  parent.appendChild(el);
  return el;
}
