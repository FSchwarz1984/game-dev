// Where the gray-box stations sit in the render test terrain (world metres, x east, z south).
// Fitted to src/world/terrain.js: the stream crosses the map and only the main bridge (x 2-5)
// spans it on dry planks, so the south bank is enclosed (tests/field.test.js checks this); the
// boulder, the stone lantern and the shrine are existing props. Functional layout for testing verbs and feel, not the
// approved map (that is G5, docs/design/map.md).

export const FIELD = {
  spawn: [0.5, 5],
  crew: [[-0.5, 6.2], [0.5, 6.6], [1.5, 6.2]],
  shrine: [-2.5, -7.2],               // the shrine prop; sacred (shimenawa): 归还 resets her body

  // 重 — the stream crosses the whole map; the main bridge is the crew's only dry way over it.
  // A gate stands mid-bridge, roped to a stone plate at the bridge head: take the boulder's weight,
  // give it to the plate, and the gate stays open (the plate keeps the weight). Timber lies on the
  // south bank. She has two more ways over the water (ice, or the rotten bridge while light).
  rock: [6.8, 4.6],                   // the boulder prop
  plate: [3.5, 10.4],
  gate: [3.5, 13.2], gateR: 1.7,
  gateRect: { x0: 1.8, x1: 5.2, z0: 12.8, z1: 13.6 },  // covers the crew grid's cell centres
  logs: [[-3.0, 19.0], [-1.2, 20.2], [0.6, 18.8]],
  stones: [[9.2, 6.6], [10.6, 5.8]],

  // 熱 — a brazier by the west path; the stream west of the house freezes into a crossing
  brazier: [-7, 1.9],
  pond: [-9.5, 10.6], pondR: 2.6,

  // 光 — the stone lantern by the steps, fed by daylight
  lantern: [0.9, -2.0],

  // 音 — a shishi-odoshi by the house refills sound; a hanging bell west of the torii
  falls: [-16.6, 7.0],
  bell: [-7.0, -4.6],

  // 生 — an overgrown patch to clear, and a field plot next to it
  weeds: [-8.2, 6.4],
  plot: [-4.6, 6.6],

  // logistics and building on the open ground east of the torii
  yard: [7.6, -1.6],
  site: [14.0, -2.6],

  // a rotten plank bridge over the stream, west of the house
  bridge: [-13.5, 10.5], bridgeRect: { x0: -14.3, x1: -12.7, z0: 8.4, z1: 12.6 },
  ditch: null,

  // a hungry onibi in the low ground to the north-west
  yokai: [-16.5, -8.5],

  // functional names for things the flat arena calls otherwise
  names: { falls: '鹿威し', bell: '吊钟', pond: '溪水' },

  // radii that differ from the flat arena (props that already exist)
  radius: { rock: 1.0, lantern: 0.45, shrine: 0.9, falls: 0.6 },
};
