/* =====================================================================
   INPUT — named actions with latched presses (a tap shorter than a
   frame still counts), keyboard, gamepad, and a floating touch stick
   with DOM buttons. Last-used device drives the on-screen glyphs.
   ===================================================================== */
"use strict";
const IN = {
  keys: new Set(), evk: new Set(), act: {}, prev: {}, hit: {}, rel: {}, held: {},
  bind: {
    up: ["KeyW", "ArrowUp"], down: ["KeyS", "ArrowDown"], left: ["KeyA", "ArrowLeft"], right: ["KeyD", "ArrowRight"],
    run: ["ShiftLeft", "ShiftRight"],
    act: ["KeyE", "KeyF"],            // pick up / talk / deliver / use
    drop: ["KeyQ"],                    // set the top of the stack down (hold: unload everything)
    take: ["KeyJ", "Digit1"],          // 取 — draw weight out of a thing into her tail
    give: ["KeyK", "Digit2"],          // 予 — give the weight in her tail to a thing
    map: ["KeyM", "Tab"], pause: ["Escape", "KeyP"],
    ok: ["Enter", "Space", "KeyE", "KeyF"], cancel: ["Escape", "Backspace"],
    skip: ["Space", "Enter"],
  },
  touch: { stick: null, sx: 0, sy: 0, x: 0, y: 0, vx: 0, vy: 0, btn: {}, evb: {}, ptr: new Map() },
  pad: { on: false, ax: 0, ay: 0, btn: [] },
  mouse: { x: 0, y: 0, down: false, ev: false },
  device: IS_TOUCH ? "touch" : "kb",
  onDevice: null, onAny: null,
  init(cv) {
    addEventListener("keydown", e => {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      this.keys.add(e.code); this.evk.add(e.code); this.setDevice("kb");
      if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab"].includes(e.code)) e.preventDefault();
      this.onAny && this.onAny();
    });
    addEventListener("keyup", e => this.keys.delete(e.code));
    addEventListener("blur", () => { this.keys.clear(); this.touch.btn = {}; });
    cv.addEventListener("contextmenu", e => e.preventDefault());
    cv.addEventListener("pointerdown", e => this.pdown(e, cv));
    cv.addEventListener("pointermove", e => this.pmove(e));
    cv.addEventListener("pointerup", e => this.pup(e));
    cv.addEventListener("pointercancel", e => this.pup(e));
    addEventListener("pointerdown", e => { if (e.pointerType === "touch" || e.pointerType === "pen") this.setDevice("touch"); this.onAny && this.onAny(); }, { capture: true });
  },
  setDevice(d) { if (this.device !== d) { this.device = d; this.onDevice && this.onDevice(d); } },
  pdown(e, cv) {
    if (e.pointerType === "mouse") { this.mouse.down = true; this.mouse.ev = true; this.mouse.x = e.clientX; this.mouse.y = e.clientY; return; }
    this.setDevice("touch");
    try { cv.setPointerCapture(e.pointerId); } catch (err) { }
    if (e.clientX < innerWidth * .55 && this.touch.stick == null) {
      const T = this.touch; T.stick = e.pointerId; T.sx = T.x = e.clientX; T.sy = T.y = e.clientY; T.vx = T.vy = 0; T.ptr.set(e.pointerId, "stick");
    }
  },
  pmove(e) {
    if (e.pointerType === "mouse") { this.mouse.x = e.clientX; this.mouse.y = e.clientY; return; }
    const T = this.touch; if (T.ptr.get(e.pointerId) !== "stick") return;
    const R0 = Math.min(64, Math.min(innerWidth, innerHeight) * .11);
    let dx = e.clientX - T.sx, dy = e.clientY - T.sy; const d = hyp(dx, dy);
    if (d > R0 * 1.4) { T.sx = e.clientX - dx / d * R0 * 1.4; T.sy = e.clientY - dy / d * R0 * 1.4; dx = e.clientX - T.sx; dy = e.clientY - T.sy; }
    T.x = e.clientX; T.y = e.clientY;
    const m = Math.min(1, hyp(dx, dy) / R0), a = Math.atan2(dy, dx);
    if (hyp(dx, dy) < R0 * .15) { T.vx = T.vy = 0; } else { T.vx = Math.cos(a) * m; T.vy = Math.sin(a) * m; }
  },
  pup(e) {
    if (e.pointerType === "mouse") { this.mouse.down = false; return; }
    const T = this.touch, k = T.ptr.get(e.pointerId); if (!k) return; T.ptr.delete(e.pointerId);
    if (k === "stick") { T.stick = null; T.vx = T.vy = 0; }
  },
  // DOM touch buttons call this
  tbtn(id, down) { const T = this.touch; this.setDevice("touch"); if (down) { T.btn[id] = true; T.evb[id] = true; } else T.btn[id] = false; if (down) this.onAny && this.onAny(); },
  pollPad() {
    let gp = null; try { const P = navigator.getGamepads ? navigator.getGamepads() : null; gp = P && [...P].find(g => g && g.connected); } catch (e) { }
    if (!gp) { this.pad.on = false; return; }
    const dz = v => (Math.abs(v) < .18 ? 0 : v);
    const ax = dz(gp.axes[0] || 0), ay = dz(gp.axes[1] || 0), b = gp.buttons.map(x => x.pressed);
    if (ax || ay || b.some(x => x)) this.setDevice("pad");
    this.pad.on = true; this.pad.ax = ax; this.pad.ay = ay; this.pad.btn = b;
  },
  update(dt) {
    this.pollPad();
    for (const k in this.act) this.prev[k] = this.act[k];
    const A = this.act, K = this.keys, T = this.touch.btn, EB = this.touch.evb;
    for (const name in this.bind) { let v = false; for (const c of this.bind[name]) if (K.has(c) || this.evk.has(c)) v = true; A[name] = v; }
    for (const id in T) if (T[id]) A[id] = true;
    for (const id in EB) if (EB[id]) A[id] = true;
    if (this.pad.on) {
      const p = i => !!this.pad.btn[i];
      if (p(0)) A.act = A.ok = A.skip = true;         // A / cross
      if (p(1)) A.cancel = A.drop = true;             // B / circle
      if (p(2)) A.take = true;                        // X / square
      if (p(3)) A.give = true;                        // Y / triangle
      if (p(4) || p(6)) A.run = true;                 // LB / LT
      if (p(5) || p(7)) A.run = true;                 // RB / RT
      if (p(8)) A.map = true; if (p(9)) A.pause = true;
      if (p(12)) A.up = true; if (p(13)) A.down = true; if (p(14)) A.left = true; if (p(15)) A.right = true;
    }
    for (const k in A) {
      const latched = this.evkHit(k) || (!!EB[k] && !T[k]);
      this.hit[k] = A[k] && (!this.prev[k] || latched);
      this.rel[k] = !A[k] && !!this.prev[k];
      this.held[k] = A[k] ? (this.held[k] || 0) + dt : 0;
    }
    this.evk.clear(); this.touch.evb = {}; this.mouse.ev = false;
  },
  evkHit(name) { for (const c of this.bind[name] || []) if (this.evk.has(c) && !this.keys.has(c)) return true; return false; },
  consume(...names) { for (const n of names) { this.hit[n] = false; } },
  axis() {
    let x = 0, y = 0; const A = this.act;
    if (A.left) x -= 1; if (A.right) x += 1; if (A.up) y -= 1; if (A.down) y += 1;
    if (x || y) { const d = hyp(x, y); return [x / d, y / d, 1]; }
    const T = this.touch; if (T.vx || T.vy) { const m = hyp(T.vx, T.vy); return [T.vx / m, T.vy / m, m]; }
    if (this.pad.on && (this.pad.ax || this.pad.ay)) { const m = Math.min(1, hyp(this.pad.ax, this.pad.ay)); return [this.pad.ax / hyp(this.pad.ax, this.pad.ay), this.pad.ay / hyp(this.pad.ax, this.pad.ay), m]; }
    return [0, 0, 0];
  },
  // the key glyph to show for an action on the current device
  glyph(a) {
    const kb = { act: "E", drop: "Q", take: "J", give: "K", run: "Shift", map: "M", pause: "Esc", ok: "E", skip: "Space" };
    const pad = { act: "A", drop: "B", take: "X", give: "Y", run: "RB", map: "Select", pause: "Start", ok: "A", skip: "A" };
    const tch = { act: "拾", drop: "放", take: "取", give: "予", run: "奔", map: "图", pause: "‖", ok: "▶", skip: "▶" };
    return (this.device === "pad" ? pad : this.device === "touch" ? tch : kb)[a] || a;
  },
};
