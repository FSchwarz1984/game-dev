// The title screen's DOM layer: the name 「天岸」 set vertically over the night vista (drawn by
// the vista module underneath), a small seal, and the menu: 开始 / 继续 / 设置. Keyboard
// (↑ ↓, Enter / E / Space), mouse and touch. Settings: volume and text speed, kept in
// localStorage when it is available (the page must work without it).

const PREFS_KEY = 'amagishi.prefs';

export function loadPrefs() {
  try { return { volume: 0.8, textSpeed: 1, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') }; }
  catch (e) { return { volume: 0.8, textSpeed: 1 }; }
}

function savePrefs(p) { try { localStorage.setItem(PREFS_KEY, JSON.stringify(p)); } catch (e) { /* private mode */ } }

export class TitleScreen {
  /**
   * onChoose(action): 'start' | 'continue'; onPrefs(prefs) when a setting changes;
   * onFirstInput() once, on the first key or touch (audio may start only after a gesture).
   */
  constructor(root, { canContinue = false, touch = false, onChoose, onPrefs, onFirstInput } = {}) {
    injectStyle();
    this.prefs = loadPrefs();
    this.onChoose = onChoose; this.onPrefs = onPrefs; this.onFirstInput = onFirstInput;
    this.el = document.createElement('div');
    this.el.className = 'ttl';
    this.el.innerHTML = `
      <div class="ttl-name" aria-label="天岸"><h1><span>天</span><span>岸</span></h1><p>あまぎし</p><i class="ttl-seal">九十九<br>折</i></div>
      <nav class="ttl-menu">
        <button data-a="start">开始</button>
        <button data-a="continue"${canContinue ? '' : ' disabled'}>继续</button>
        <button data-a="settings">设置</button>
      </nav>
      <div class="ttl-set" hidden>
        <label>音量<input type="range" min="0" max="100" step="5" data-p="volume"></label>
        <div class="ttl-speed">文字速度
          <button data-s="0.6">慢</button><button data-s="1">中</button><button data-s="1.8">快</button></div>
        <button data-a="back" class="ttl-back">返回</button>
      </div>
      <div class="ttl-keys">${touch ? '左半屏拖动：走　右下角大键：调查　性质键：点一下取，上滑予' : 'WASD 走　E 调查　1–5 取　Shift+1–5 予　Space 推进对话'}</div>`;
    root.appendChild(this.el);
    this.items = [...this.el.querySelectorAll('.ttl-menu button')];
    this.sel = 0;
    this.focus(0);
    this.el.querySelector('[data-p="volume"]').value = Math.round(this.prefs.volume * 100);
    this.markSpeed();

    this.el.addEventListener('pointerdown', () => this.first(), { capture: true });
    for (const b of this.items) {
      b.addEventListener('pointerenter', () => this.focus(this.items.indexOf(b)));
      b.addEventListener('click', () => this.choose(b.dataset.a));
    }
    this.el.querySelector('.ttl-back').addEventListener('click', () => this.settings(false));
    this.el.querySelector('[data-p="volume"]').addEventListener('input', e => { this.prefs.volume = e.target.value / 100; this.changed(); });
    for (const b of this.el.querySelectorAll('[data-s]')) b.addEventListener('click', () => { this.prefs.textSpeed = +b.dataset.s; this.markSpeed(); this.changed(); });
    this.onKey = e => {
      if (!this.el.isConnected || this.el.classList.contains('gone')) return;
      this.first();
      if (!this.setEl().hidden) { if (e.code === 'Escape') this.settings(false); return; }
      if (e.code === 'ArrowDown' || e.code === 'KeyS') { e.preventDefault(); this.move(1); }
      else if (e.code === 'ArrowUp' || e.code === 'KeyW') { e.preventDefault(); this.move(-1); }
      else if (e.code === 'Enter' || e.code === 'Space' || e.code === 'KeyE') { e.preventDefault(); this.choose(this.items[this.sel].dataset.a); }
    };
    addEventListener('keydown', this.onKey);
  }

  setEl() { return this.el.querySelector('.ttl-set'); }

  first() { if (this.onFirstInput) { const f = this.onFirstInput; this.onFirstInput = null; f(); } }

  focus(i) {
    this.sel = i;
    this.items.forEach((b, k) => b.classList.toggle('sel', k === i));
  }

  move(d) {
    let i = this.sel;
    do { i = (i + d + this.items.length) % this.items.length; } while (this.items[i].disabled);
    this.focus(i);
  }

  choose(a) {
    if (a === 'settings') return this.settings(true);
    if (a === 'continue' && this.items[1].disabled) return;
    this.onChoose?.(a);
  }

  settings(on) {
    this.setEl().hidden = !on;
    this.el.querySelector('.ttl-menu').hidden = on;
  }

  markSpeed() { for (const b of this.el.querySelectorAll('[data-s]')) b.classList.toggle('on', +b.dataset.s === this.prefs.textSpeed); }
  changed() { savePrefs(this.prefs); this.onPrefs?.(this.prefs); }

  /** Fade the title away (the music is cut by the caller, mid-phrase). */
  hide() { this.el.classList.add('gone'); setTimeout(() => this.dispose(), 1200); }

  dispose() { removeEventListener('keydown', this.onKey); this.el.remove(); }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .ttl { position: fixed; inset: 0; z-index: 40; pointer-events: auto; color: #f3ecdc; font-family: "Noto Serif SC", "Shippori Mincho", serif; transition: opacity 1s ease; user-select: none; -webkit-user-select: none; }
  .ttl.gone { opacity: 0; pointer-events: none; }   /* .ttl turns pointer events back on: its parent .ui has them off */
  .ttl-name { position: absolute; right: max(9vw, calc(24px + env(safe-area-inset-right, 0px))); top: 12vh; display: flex; flex-direction: row-reverse; align-items: flex-start; gap: 14px; pointer-events: none; }
  .ttl-name h1 { margin: 0; display: flex; flex-direction: column; gap: .14em; font: 700 clamp(60px, 14vh, 128px)/1 "Shippori Mincho B1", "Shippori Mincho", "Noto Serif SC", serif; color: #f6f0e2; text-shadow: 0 0 18px rgba(255, 226, 170, .22), 0 2px 0 rgba(0, 0, 0, .55); }
  .ttl-name h1 span { display: block; width: 1em; height: 1em; text-align: center; }
  .ttl-name p { margin: 6px 0 0; writing-mode: vertical-rl; font: 600 clamp(13px, 2.4vh, 18px)/1 "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", "IPAMincho", "IPAGothic", "Noto Serif SC", serif; letter-spacing: .5em; color: #d8c9a4; }
  .ttl-seal { align-self: flex-end; margin-bottom: -6px; font: 700 11px/1.15 "Noto Serif SC", serif; font-style: normal; text-align: center; padding: 4px 4px; color: #f6e7d2; background: #b2382c; border-radius: 2px; box-shadow: inset 0 0 0 1px rgba(255, 240, 220, .35); writing-mode: horizontal-tb; }
  .ttl-menu { position: absolute; left: max(7vw, calc(24px + env(safe-area-inset-left, 0px))); bottom: 18vh; display: flex; flex-direction: column; gap: 6px; }
  .ttl-menu[hidden], .ttl-set[hidden] { display: none; }
  .ttl button { all: unset; cursor: pointer; }
  .ttl-menu button { position: relative; padding: 6px 14px 6px 18px; font-size: 18px; letter-spacing: .4em; color: #cdbf9f; transition: color .15s; min-height: 32px; }
  .ttl-menu button::before { content: ""; position: absolute; left: 0; top: 50%; width: 3px; height: 0; background: #c8402f; transform: translateY(-50%); transition: height .15s; }
  .ttl-menu button.sel { color: #fbf4e4; }
  .ttl-menu button.sel::before { height: 70%; }
  .ttl-menu button[disabled] { color: #6f6757; cursor: default; }
  .ttl-set { position: absolute; left: max(7vw, calc(24px + env(safe-area-inset-left, 0px))); bottom: 16vh; display: flex; flex-direction: column; gap: 14px; padding: 16px 20px; background: rgba(10, 9, 14, .72); box-shadow: inset 0 0 0 1px rgba(214, 178, 106, .4); font-size: 15px; letter-spacing: .1em; }
  .ttl-set label { display: flex; align-items: center; gap: 12px; }
  .ttl-set input { width: 160px; accent-color: #c8402f; }
  .ttl-speed { display: flex; align-items: center; gap: 10px; }
  .ttl-speed button { padding: 4px 10px; color: #b6a888; box-shadow: inset 0 0 0 1px rgba(214, 178, 106, .3); }
  .ttl-speed button.on { color: #fbf4e4; box-shadow: inset 0 0 0 1px #c8402f; }
  .ttl-back { align-self: flex-start; padding: 4px 0; color: #cdbf9f; letter-spacing: .3em; }
  .ttl-keys { position: absolute; left: 0; right: 0; bottom: max(14px, env(safe-area-inset-bottom, 0px)); text-align: center; font: 500 12px/1.4 "Noto Sans SC", system-ui, sans-serif; color: rgba(230, 220, 196, .55); letter-spacing: .08em; pointer-events: none; padding: 0 12px; text-wrap: balance; }
  @media (max-height: 460px) { .ttl-name { top: 8vh; } .ttl-menu { bottom: 14vh; } .ttl-menu button { font-size: 16px; padding: 4px 12px 4px 16px; } }
  `;
  document.head.appendChild(s);
}
