// Entry: 《天岸》 segment 1 (title, the prologue 「送魂夜」, the first morning). The retired 3D gray
// box (src/play, src/render, src/world) is no longer reachable from here.
import { boot } from './app/main.js';

boot(document.getElementById('app')).catch(e => {
  console.error(e);
  const p = document.createElement('pre');
  p.textContent = '启动失败：' + (e && e.message || e);
  Object.assign(p.style, { position: 'fixed', left: '12px', top: '12px', color: '#f3ecdc', font: '13px/1.4 monospace', whiteSpace: 'pre-wrap' });
  document.body.appendChild(p);
});
