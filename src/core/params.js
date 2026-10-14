// URL switches used by players, the lead and the headless tests.
//   ?q=low|mid|high             force a quality tier
//   ?touch=1                    show the touch controls on a desktop browser
//   ?scene=prologue|day1        skip the title and start there (checking)
//   ?fast=N                     run the scene clock N times faster (checking)
//   ?manual=1                   the checking tools drive the clock (window.APP.tick / APP.render)
//   ?debug=1                    stats overlay

const q = new URLSearchParams(window.location.search);
const pick = (key, allowed, fallback) => (allowed.includes(q.get(key)) ? q.get(key) : fallback);

export const params = Object.freeze({
  quality: pick('q', ['low', 'mid', 'high'], null),
  touch: q.get('touch') === '1',
  scene: pick('scene', ['prologue', 'day1'], null),
  fast: Math.max(1, Math.min(16, Number(q.get('fast')) || 1)),
  manual: q.get('manual') === '1',
  debug: q.get('debug') === '1',
  // retired gray-box switches, kept so its code still builds
  time: pick('t', ['morning', 'noon', 'evening', 'night'], 'noon'),
  dof: q.get('dof') !== '0',
  view: q.get('view') === 'render' ? 'render' : 'game',
});
