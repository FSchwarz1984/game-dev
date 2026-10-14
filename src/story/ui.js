// Story presentation layer (DOM, renderer-independent): the dialogue box with the user's
// illustrations as bust portraits, typewriter text with per-character voice blips, caption cards
// (字幕卡), subtitles, title cards, letterbox bars, fades and first-time hints. Ported from v0.1's
// UI (the part of v0.1 the owner liked: its cinematic presentation) and rebuilt for phones.
//
//   const ui = new StoryUI(root, { audio, portraits: { tsuzumi: url, saji: url, ... } });
//   await ui.say([{ who: 'tsuzumi', text: '借过。' }, { who: 'saji', text: '……' }]);
//   await ui.card('盆の十六日　暮れ六つ', '盂兰盆，十六日，傍晚');
//   await ui.fade(1, 0.6, '#fff');  ui.letterbox(true);  ui.hint('选中目标，取它的「重」', x, y)
// Advance: tap/click the box, or E / Space / Enter; hold to fast-forward.

export const CAST = {
  tsuzumi: { name: '百々つゞみ', kana: 'もも つづみ', voice: 'tsuzumi' },
  saji: { name: '家守さぢ', kana: 'やもり さじ', voice: 'saji' },
  shione: { name: '垣外しをね', kana: 'かいと しおね', voice: 'shione' },
  narr: { name: '', kana: '', voice: null },
};

const PAUSE_SHORT = '，、';
const PAUSE_LONG = '。！？…—';
const SILENT = '，。、！？…—「」（）『』 ';

export class StoryUI {
  constructor(root, { audio = null, portraits = {}, wait = null } = {}) {
    injectStyle();
    this.audio = audio;
    // cards and fades wait on the game clock when the director lends its own (src/story/cine.js)
    this.wait = wait || (s => new Promise(r => setTimeout(r, s * 1000)));
    this.portraits = portraits;
    this.el = document.createElement('div');
    this.el.className = 'story';
    this.el.innerHTML = `
      <div class="st-box st-top"></div><div class="st-box st-bot"></div>
      <div class="st-dlg" role="dialog" aria-live="polite">
        <img class="st-port" alt="">
        <div class="st-panel">
          <div class="st-name"><i></i><b></b><small></small></div>
          <div class="st-txt"></div>
          <div class="st-next" aria-hidden="true"></div>
        </div>
      </div>
      <div class="st-sub"></div>
      <div class="st-card"><h2></h2><p></p></div>
      <div class="st-title"><h1></h1><p></p></div>
      <div class="st-hint"></div>
      <div class="st-fade"></div>`;
    root.appendChild(this.el);
    const q = s => this.el.querySelector(s);
    Object.assign(this, {
      dlgEl: q('.st-dlg'), portEl: q('.st-port'), nameEl: q('.st-name b'), kanaEl: q('.st-name small'), txtEl: q('.st-txt'),
      subEl: q('.st-sub'), cardEl: q('.st-card'), titleEl: q('.st-title'), hintEl: q('.st-hint'), fadeEl: q('.st-fade'),
    });
    this.dlg = null;
    this.blockN = 0;
    this.advanceReq = false;
    this.fastHeld = false;
    this.dlgEl.addEventListener('pointerdown', e => { e.preventDefault(); this.advanceReq = true; this.fastHeld = true; });
    addEventListener('pointerup', () => { this.fastHeld = false; });
    this.onKey = e => {
      if (!this.dlg || e.repeat) return;
      if (e.code === 'KeyE' || e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); e.stopPropagation(); this.advanceReq = true; }
    };
    addEventListener('keydown', this.onKey, true);
  }

  /** True while a line, card or fade wants the game to wait (inputs other than advancing are paused). */
  get blocking() { return !!this.dlg || this.blockN > 0; }

  // ---------------------------------------------------------------- dialogue

  /** lines: [{ who, text, slow? }]; resolves when the last line is dismissed. */
  say(lines) {
    if (!Array.isArray(lines)) lines = [lines];
    return new Promise(res => {
      this.dlg = { lines, i: 0, ch: 0, t: 0, done: false, res };
      this.dlgEl.classList.add('on');
      this.showLine();
      this.audio?.duck?.(0.35, 99);
    });
  }

  showLine() {
    const D = this.dlg, L = D.lines[D.i], who = CAST[L.who] || CAST.narr;
    this.dlgEl.classList.toggle('narr', !who.name);
    this.nameEl.textContent = who.name;
    this.kanaEl.textContent = who.kana;
    const url = this.portraits[L.who];
    if (url) {
      if (this.portEl.dataset.who !== L.who) { this.portEl.src = url; this.portEl.dataset.who = L.who; this.portEl.classList.remove('in'); void this.portEl.offsetWidth; this.portEl.classList.add('in'); }
      this.portEl.hidden = false;
      this.dlgEl.classList.add('has-port');
    } else {
      this.portEl.hidden = true;
      this.dlgEl.classList.remove('has-port');
    }
    D.ch = 0; D.t = 0; D.done = false;
    this.txtEl.textContent = '';
    this.dlgEl.classList.remove('done');
  }

  /** Call every frame (dt in seconds). */
  update(dt) {
    const D = this.dlg;
    if (!D) { this.advanceReq = false; return; }
    const L = D.lines[D.i], text = L.text, who = CAST[L.who] || CAST.narr;
    const adv = this.advanceReq;
    this.advanceReq = false;
    if (!D.done) {
      D.t += dt * (this.fastHeld ? 3 : 1) * (this.speed || 1);
      const speed = L.slow ? 14 : 30;
      while (D.t > 1 / speed && D.ch < text.length) {
        const c = text[D.ch];
        D.t -= 1 / speed; D.ch++;
        if (PAUSE_SHORT.includes(c)) D.t -= 0.09;
        else if (PAUSE_LONG.includes(c)) D.t -= 0.22;
        if (who.voice && !SILENT.includes(c) && D.ch % 2 === 1) this.audio?.sfx?.('blip', { voice: who.voice, i: D.ch });
      }
      this.txtEl.textContent = text.slice(0, D.ch);
      if (D.ch >= text.length) { D.done = true; this.dlgEl.classList.add('done'); }
      else if (adv) { D.ch = text.length; this.txtEl.textContent = text; D.done = true; this.dlgEl.classList.add('done'); }
    } else if (adv) {
      this.audio?.sfx?.('ui_move');
      D.i++;
      if (D.i >= D.lines.length) {
        this.dlgEl.classList.remove('on');
        this.dlg = null;
        this.audio?.duck?.(0, 0.5);
        this.wait(0.12).then(() => D.res());
      } else this.showLine();
    }
  }

  // ---------------------------------------------------------------- cinematic text

  /** A caption card (字幕卡): a place or time, centred low on screen. */
  card(head, sub = '', dur = 3.6) {
    return this.hold(dur + 1.4, () => {
      this.cardEl.querySelector('h2').textContent = head;
      this.cardEl.querySelector('p').textContent = sub;
      this.cardEl.classList.add('on');
      return () => this.cardEl.classList.remove('on');
    }, dur);
  }

  /** The title drop. */
  title(head, sub = '', dur = 4.5) {
    return this.hold(dur + 1.8, () => {
      this.titleEl.querySelector('h1').textContent = head;
      this.titleEl.querySelector('p').textContent = sub;
      this.titleEl.classList.add('on');
      return () => this.titleEl.classList.remove('on');
    }, dur);
  }

  /** A spoken line without the box (cinematic subtitles). */
  sub(text, dur) {
    dur = dur ?? Math.max(2.4, text.length * 0.16);
    return this.hold(dur + 0.8, () => {
      this.subEl.textContent = text;
      this.subEl.classList.add('on');
      return () => this.subEl.classList.remove('on');
    }, dur);
  }

  hold(total, show, visible) {
    return new Promise(res => {
      this.blockN++;
      const hide = show();
      this.wait(visible).then(hide);
      this.wait(total).then(() => { this.blockN--; res(); });
    });
  }

  letterbox(on) { this.el.classList.toggle('boxed', on); }

  fade(a, dur = 0.6, color = '#000') {
    this.fadeEl.style.background = color;
    this.fadeEl.style.transition = `opacity ${dur}s ease`;
    this.fadeEl.style.opacity = a;
    return this.wait(dur);
  }

  /** A first-time hint anchored above a screen point (CSS px), or null to hide. */
  hint(text, x, y) {
    if (!text) { this.hintEl.classList.remove('on'); return; }
    this.hintEl.textContent = text;
    this.hintEl.classList.add('on');
    const w = this.hintEl.offsetWidth, h = this.hintEl.offsetHeight;
    const px = Math.max(8, Math.min(innerWidth - w - 8, x - w / 2)), py = Math.max(8, Math.min(innerHeight - h - 8, y - h - 12));
    this.hintEl.style.transform = `translate(${px.toFixed(0)}px, ${py.toFixed(0)}px)`;
  }

  dispose() { removeEventListener('keydown', this.onKey, true); this.el.remove(); }
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .story { position: fixed; inset: 0; z-index: 30; pointer-events: none; font-family: "Noto Serif SC", "Shippori Mincho", "Songti SC", serif; color: #f3ecdc; }
  .st-box { position: absolute; left: 0; right: 0; height: 0; background: #07080b; transition: height .6s ease; }
  .st-top { top: 0; } .st-bot { bottom: 0; }
  .story.boxed .st-box { height: 11vh; }
  .st-dlg { position: absolute; left: 50%; bottom: calc(18px + env(safe-area-inset-bottom, 0px)); width: min(900px, calc(100% - 28px)); transform: translate(-50%, 16px); opacity: 0; transition: opacity .18s, transform .18s; pointer-events: none; }
  .st-dlg.on { opacity: 1; transform: translate(-50%, 0); pointer-events: auto; }
  .st-panel { position: relative; min-height: 118px; padding: 30px 26px 20px; background: linear-gradient(180deg, rgba(18,15,22,.92), rgba(10,9,13,.95)); border: 1px solid rgba(214,182,120,.45); border-radius: 6px; box-shadow: 0 10px 40px rgba(0,0,0,.45), inset 0 0 0 3px rgba(10,9,13,.9), inset 0 0 0 4px rgba(214,182,120,.18); }
  .st-dlg.has-port .st-panel { padding-left: clamp(150px, 26%, 230px); }
  .st-port { position: absolute; left: clamp(-6px, 1%, 10px); bottom: 0; height: clamp(190px, 38vh, 330px); width: auto; object-fit: contain; object-position: bottom; filter: drop-shadow(0 6px 14px rgba(0,0,0,.55)); z-index: 1; }
  .st-port.in { animation: st-port-in .22s ease-out; }
  @keyframes st-port-in { from { transform: translateY(8px); opacity: .4; } to { transform: none; opacity: 1; } }
  .st-name { position: absolute; top: -15px; display: flex; align-items: baseline; gap: 8px; padding: 4px 14px 5px 10px; background: #1a1418; border: 1px solid rgba(214,182,120,.5); border-radius: 3px; }
  .st-dlg.has-port .st-name { left: clamp(150px, 26%, 230px); } .st-dlg:not(.has-port) .st-name { left: 22px; }
  .st-name i { width: 9px; height: 9px; background: #c4462e; transform: rotate(45deg); align-self: center; }
  .st-name b { font-weight: 700; font-size: 17px; letter-spacing: .06em; color: #f6eedb; }
  .st-name small { font-family: "Noto Sans SC", system-ui, sans-serif; font-size: 11px; color: #bba985; letter-spacing: .12em; }
  .st-dlg.narr .st-name { display: none; }
  .st-txt { font-size: 20px; line-height: 1.75; letter-spacing: .03em; min-height: 3.5em; white-space: pre-wrap; text-shadow: 0 1px 0 rgba(0,0,0,.6); }
  .st-next { position: absolute; right: 18px; bottom: 12px; width: 10px; height: 10px; border-right: 2px solid #d6b678; border-bottom: 2px solid #d6b678; transform: rotate(45deg); opacity: 0; }
  .st-dlg.done .st-next { opacity: .9; animation: st-bob 1s ease-in-out infinite; }
  @keyframes st-bob { 50% { transform: translateY(4px) rotate(45deg); } }
  .st-sub { position: absolute; left: 50%; bottom: calc(15vh + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); max-width: calc(100% - 40px); font-size: 21px; letter-spacing: .08em; text-align: center; text-shadow: 0 2px 6px rgba(0,0,0,.85); opacity: 0; transition: opacity .7s; }
  .st-sub.on { opacity: 1; }
  .st-card { position: absolute; left: 0; right: 0; bottom: 22vh; text-align: center; opacity: 0; transition: opacity 1.2s; }
  .st-card.on { opacity: 1; }
  .st-card h2 { margin: 0; font-family: "Shippori Mincho", "Noto Serif SC", serif; font-weight: 700; font-size: clamp(22px, 3.2vw, 34px); letter-spacing: .32em; text-shadow: 0 2px 10px rgba(0,0,0,.8); }
  .st-card p { margin: 6px 0 0; font-size: 14px; letter-spacing: .2em; color: #d8c9a6; text-shadow: 0 1px 6px rgba(0,0,0,.8); }
  .st-title { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; opacity: 0; transition: opacity 1.6s; }
  .st-title.on { opacity: 1; }
  .st-title h1 { margin: 0; font-family: "Shippori Mincho", "Noto Serif SC", serif; font-weight: 800; font-size: clamp(56px, 11vw, 120px); letter-spacing: .5em; text-indent: .5em; color: #2a2230; text-shadow: 0 0 30px rgba(255,255,255,.6); }
  .st-title p { margin: 10px 0 0; font-size: 15px; letter-spacing: .6em; text-indent: .6em; color: #5b4c5e; }
  .st-hint { position: fixed; left: 0; top: 0; padding: 6px 12px; background: rgba(16,14,20,.85); border: 1px solid rgba(214,182,120,.55); border-radius: 4px; font-family: "Noto Sans SC", system-ui, sans-serif; font-size: 14px; color: #f3ecdc; opacity: 0; transition: opacity .25s; white-space: nowrap; }
  .st-hint.on { opacity: 1; }
  .st-fade { position: absolute; inset: 0; opacity: 0; background: #000; }
  @media (max-width: 600px) {
    .st-panel { min-height: 104px; padding: 26px 16px 16px; }
    .st-dlg.has-port .st-panel { padding-left: 108px; }
    .st-dlg.has-port .st-name { left: 108px; }
    .st-port { height: clamp(150px, 26vh, 210px); left: -4px; }
    .st-txt { font-size: 17px; }
    .st-sub { font-size: 17px; }
  }
  @media (prefers-reduced-motion: reduce) { .st-port.in, .st-dlg.done .st-next { animation: none; } }
  `;
  document.head.appendChild(s);
}
