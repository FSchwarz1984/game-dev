/* =====================================================================
   env/reach — the connectivity check for a baked map: a BFS over
   map.walkable (the 0.25 m nav grid, 4-connected) from the road's entry
   must reach every place the story needs. Used by tools/env/reach.mjs and
   tools/env/build.mjs (so it runs on every bake); usable from tests.
   Each target is snapped to the nearest walkable cell within 1.2 m
   (props and colliders stand on some of them).
   ===================================================================== */
export function homeTargets(map) {
  const O = map.objects;
  return [
    // the lead's list (the segment-1 playthrough)
    ['road entry (119, 72)', 119, 72], ['graves terrace (82, 60.4)', 82, 60.4], ['saddle (74, 49.6)', 74, 49.6], ['camphor foot (47.3, 30.7)', 47.3, 30.7],
    ['hut door (42, 35.4)', 42, 35.4], ['shrine beam (60, 36.6)', 60, 36.6], ['old frame (44.2, 35.5)', 44.2, 35.5], ['lookout (44.5, 61.2)', 44.5, 61.2],
    // from the map's own objects
    ['statues stand', O.statues.stand.x, O.statues.stand.z], ['graves stand', O.graves.stand.x, O.graves.stand.z], ['saddle top', O.road.saddleTop.x, O.road.saddleTop.z],
    ...O.road.bends.map((b, i) => ['hairpin ' + (i + 1), b.x, b.z]),
    ['hut door (object)', O.hut.door.x, O.hut.door.z + 0.9], ['shrine front', O.shrine.front.x, O.shrine.front.z + 0.6], ['load', O.load.x, O.load.z + 0.6],
    ['first climb hold', O.camphor.climb[0].x, O.camphor.climb[0].z + 0.6], ['waterfall pool shore', O.waterfall.pool.x + 4.6, O.waterfall.pool.z + 3.6], ['north loop start', O.northLoop.start.x, O.northLoop.start.z],
  ];
}
/** → {ok, start, reached, walkable, results: [{name, x, z, ok, why}]} */
export function checkReach(map, targets = homeTargets(map), from = map.objects.road.entryEast) {
  const N = map.nav;
  const idx = (x, z) => { const i = Math.floor((x - N.x0) / N.cell), j = Math.floor((z - N.z0) / N.cell); return (i < 0 || j < 0 || i >= N.w || j >= N.h) ? -1 : j * N.w + i; };
  const snap = (x, z) => { let best = -1, bd = 1e9; for (let dz = -1.2; dz <= 1.2; dz += N.cell) for (let dx = -1.2; dx <= 1.2; dx += N.cell) { const d = Math.hypot(dx, dz); if (d > 1.2 || d >= bd) continue; const k = idx(x + dx, z + dz); if (k >= 0 && N.data[k]) { best = k; bd = d; } } return best; };
  const start = snap(from.x, from.z);
  const res = { ok: start >= 0, start: from, reached: 0, walkable: N.data.reduce((a, b) => a + b, 0), results: [] };
  if (start < 0) { res.results.push({ name: 'road entry', x: from.x, z: from.z, ok: false, why: 'the entry itself is not walkable' }); return res; }
  const seen = new Uint8Array(N.w * N.h), q = new Int32Array(N.w * N.h); let qh = 0, qt = 0;
  seen[start] = 1; q[qt++] = start;
  while (qh < qt) { const k = q[qh++], i = k % N.w, j = (k / N.w) | 0;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ii = i + di, jj = j + dj; if (ii < 0 || jj < 0 || ii >= N.w || jj >= N.h) continue; const kk = jj * N.w + ii; if (seen[kk] || !N.data[kk]) continue; seen[kk] = 1; q[qt++] = kk; } }
  res.reached = qt;
  for (const [name, x, z] of targets) {
    const k = snap(x, z), ok = k >= 0 && !!seen[k];
    if (!ok) res.ok = false;
    res.results.push({ name, x, z, ok, why: k < 0 ? 'no walkable cell within 1.2 m' : ok ? '' : 'walkable but cut off from the road' });
  }
  return res;
}
