// Phones are played held sideways (decision P-3: no upright layout). A touch device held upright
// gets this full-screen prompt instead of the game; the caller stops the clock and the sound under
// it (onChange) until the phone is turned back.

export function createRotatePrompt(root, { touch = false, onChange } = {}) {
  injectStyle();
  const el = document.createElement('div');
  el.className = 'rot';
  el.hidden = true;
  el.setAttribute('role', 'alertdialog');
  el.setAttribute('aria-label', '请把手机横过来');
  el.innerHTML = `
    <div class="rot-in">
      <svg class="rot-ico" viewBox="0 0 64 64" aria-hidden="true">
        <path class="rot-arc" d="M50 22 A22 22 0 0 0 22 12" />
        <path class="rot-arc" d="M22 12 l4 -4 M22 12 l5 3" />
        <g class="rot-phone"><rect x="22" y="18" width="20" height="34" rx="3.5" /><path d="M29 22 h6" /></g>
      </svg>
      <p>请把手机横过来</p>
      <i></i>
    </div>`;
  root.appendChild(el);
  const portrait = matchMedia('(orientation: portrait)');
  const check = () => {
    const on = !!touch && portrait.matches;
    if (on === !el.hidden) return;
    el.hidden = !on;
    onChange?.(on);
  };
  if (portrait.addEventListener) portrait.addEventListener('change', check); else portrait.addListener?.(check);
  addEventListener('resize', check);
  check();
  return { get shown() { return !el.hidden; } };
}

let styled = false;
function injectStyle() {
  if (styled) return; styled = true;
  const s = document.createElement('style');
  s.textContent = `
  .rot { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; pointer-events: auto; touch-action: none;
    background: radial-gradient(ellipse at 50% 42%, #161a24 0%, #0d0f14 62%, #08090c 100%); color: #e8dcc0; }
  .rot[hidden] { display: none; }
  .rot-in { display: flex; flex-direction: column; align-items: center; gap: 18px; padding: 0 24px; text-align: center; }
  .rot-ico { width: 84px; height: 84px; overflow: visible; }
  .rot-ico rect, .rot-ico path { fill: none; stroke: #e8dcc0; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
  .rot-ico .rot-arc { stroke: #c4462e; stroke-width: 2; }
  .rot-phone { transform-origin: 32px 35px; animation: rot-turn 2.8s ease-in-out infinite; }
  @keyframes rot-turn { 0%, 22% { transform: rotate(0deg); } 50%, 78% { transform: rotate(-90deg); } 100% { transform: rotate(0deg); } }
  .rot p { margin: 0; font: 600 17px/1.5 "Noto Serif SC", "Songti SC", serif; letter-spacing: .3em; text-indent: .3em; }
  .rot i { display: block; width: 26px; height: 2px; background: #c4462e; opacity: .8; }
  @media (prefers-reduced-motion: reduce) { .rot-phone { animation: none; transform: rotate(-90deg); } }
  `;
  document.head.appendChild(s);
}
