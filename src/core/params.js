// URL switches used by players, the lead and the headless tests.
//   ?q=low|high                 force a quality tier (also disables the adaptive fallback)
//   ?t=morning|noon|evening|night
//   ?dof=0                      depth of field / tilt-shift off
//   ?debug=1                    FPS, draw calls, triangles and tier overlay
//   ?view=render                the render foundation's test scene instead of the gray box
//   ?touch=1                    show the touch controls on a desktop browser

const q = new URLSearchParams(window.location.search);
const pick = (key, allowed, fallback) => (allowed.includes(q.get(key)) ? q.get(key) : fallback);

export const params = Object.freeze({
  quality: pick('q', ['low', 'high'], null),
  time: pick('t', ['morning', 'noon', 'evening', 'night'], 'noon'),
  dof: q.get('dof') !== '0',
  debug: q.get('debug') === '1',
  view: q.get('view') === 'render' ? 'render' : 'game',
  touch: q.get('touch') === '1',
});
