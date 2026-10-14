import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NavGrid } from '../src/game/nav.js';
import { Crew } from '../src/game/crew.js';

// 20 x 20 m field with a wall at z = 10 (x < 15) and a raised shelf at x > 16 reached by no ramp
const ground = (x, z) => (z >= 10 && z < 11 && x < 15 ? null : x > 16 ? 2 : 0);
const grid = () => new NavGrid({ x0: 0, z0: 0, w: 20, h: 20, cell: 1, ground });

test('a route goes around the wall through the gap, straight where it can', () => {
  const r = grid().route(2, 5, 2, 15);
  assert.ok(r, 'reachable');
  assert.ok(r.some(p => p.x >= 15 && p.z >= 9 && p.z <= 12), 'passes the gap');
  assert.ok(r.length <= 4, `string-pulled to ${r.length} waypoints`);
  assert.deepEqual(r[r.length - 1], { x: 2, z: 15 });
});

test('cliffs are not walked, closed gates are not walked', () => {
  const g = grid();
  assert.equal(g.route(2, 5, 18, 5), null, 'a 2 m shelf with no ramp');
  g.blocked = (x, z) => x >= 15 && z >= 10 && z < 11; // shut the gap
  assert.equal(g.route(2, 5, 2, 15), null);
  g.blocked = null;
  assert.ok(g.route(2, 5, 2, 15));
});

test('carriers walk around the wall instead of through it', () => {
  const g = grid();
  const crew = new Crew({ route: (a, b, c, d) => g.route(a, b, c, d) });
  crew.add(2, 4);
  const item = { x: 2, z: 5, weight: 1, ref: {} }, dest = { x: 2, z: 15 };
  crew.dispatch(item, dest);
  let crossedWall = false;
  for (let t = 0; t < 40 && !crew.members[0].job?.delivered && crew.jobs.length; t += 1 / 30) {
    crew.update(1 / 30);
    if (item.z > 10 && item.z < 11 && item.x < 15) crossedWall = true;
  }
  assert.equal(crew.jobs.length, 0, 'delivered');
  assert.equal(crossedWall, false);
  assert.ok(Math.hypot(item.x - 2, item.z - 15) < 0.5);
});
