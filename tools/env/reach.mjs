// Connectivity check for the home map (see src/env/reach.js): bakes the map in Node (~4 s) and BFSes
// over map.walkable from the road's east entry to every place the story needs. Exits 1, loudly, if one
// is cut off. Also run by tools/env/build.mjs, so it runs on every bake of the test page.
//   node tools/env/reach.mjs
import { createHomeMap } from '../../src/env/home.js';
import { checkReach } from '../../src/env/reach.js';

const r = checkReach(createHomeMap({}));
for (const t of r.results) console.log(`${t.ok ? 'ok  ' : 'FAIL'} ${t.name.padEnd(30)} (${t.x.toFixed(1)}, ${t.z.toFixed(1)})${t.why ? '  — ' + t.why : ''}`);
console.log(`reachable cells: ${r.reached} of ${r.walkable} walkable`);
if (!r.ok) { console.error(`\nFAIL: ${r.results.filter(t => !t.ok).length} place(s) cannot be reached from the road entry`); process.exit(1); }
console.log('all places reachable');
