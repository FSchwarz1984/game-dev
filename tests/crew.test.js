import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Crew, carriersNeeded } from '../src/game/crew.js';

const run = (crew, seconds, leader) => {
  const dt = 1 / 60;
  for (let t = 0; t < seconds; t += dt) {
    if (leader) { leader.x += leader.vx * dt; leader.z += leader.vz * dt; crew.lead(leader.x, leader.z); }
    crew.update(dt);
  }
};

test('followers walk in a line along her path, not in a clump', () => {
  const crew = new Crew();
  for (let i = 0; i < 4; i++) crew.add(0, 0);
  const her = { x: 0, z: 0, vx: 2, vz: 0 };
  run(crew, 3, her);
  her.vx = 0; her.vz = 2;   // she turns a corner
  run(crew, 2, her);
  const m = crew.members;
  for (let i = 1; i < m.length; i++) {
    const gap = Math.hypot(m[i].x - m[i - 1].x, m[i].z - m[i - 1].z);
    assert.ok(gap > 0.6 && gap < 1.3, `gap ${gap.toFixed(2)} between follower ${i - 1} and ${i}`);
  }
  // the last follower is still on the first leg of the path (x axis), i.e. it follows the corner
  assert.ok(Math.abs(m[3].z) < 0.6 || m[3].x > 5, 'the line traces the path around the corner');
});

test('a heavy item waits for enough hands, and taking its weight needs fewer', () => {
  assert.equal(carriersNeeded(3), 3);
  assert.equal(carriersNeeded(0), 1);
  const crew = new Crew();
  crew.add(0, 0); crew.add(0, 0);
  const log = { x: 4, z: 0, weight: 3, ref: 'log' };
  const yard = { x: 0, z: 4, ref: 'yard', count: 0 };
  const job = crew.dispatch(log, yard);
  assert.equal(crew.shortfall(job), 1);
  run(crew, 4);
  assert.equal(job.state, 'gather', 'two carriers cannot lift a weight-3 log');
  log.weight = 2;   // she took one unit of its weight
  run(crew, 8);
  assert.equal(job.delivered, true);
  assert.equal(yard.count, 1);
  assert.ok(Math.hypot(log.x - yard.x, log.z - yard.z) < 0.5);
  assert.ok(crew.members.every(m => m.state === 'follow'));
});

test('dispatching again sends more helpers to an item that is short of hands', () => {
  const crew = new Crew();
  const a = crew.add(0, 0);
  const rock = { x: 3, z: 0, weight: 2, ref: 'rock' };
  const job = crew.dispatch(rock, { x: 0, z: 3, ref: 'yard' });
  assert.equal(crew.shortfall(job), 1);
  const b = crew.add(0, 0);
  crew.dispatch(rock, job.dest);
  assert.equal(crew.shortfall(job), 0);
  assert.ok(job.carriers.includes(a) && job.carriers.includes(b));
});

test('recall drops the load where it is and everyone rejoins the line', () => {
  const crew = new Crew();
  crew.add(0, 0);
  const box = { x: 3, z: 0, weight: 1, ref: 'box' };
  crew.dispatch(box, { x: -6, z: 0, ref: 'yard' });
  run(crew, 2.5);
  crew.recall();
  const where = { x: box.x, z: box.z };
  run(crew, 1);
  assert.deepEqual({ x: box.x, z: box.z }, where);
  assert.equal(crew.members[0].state, 'follow');
});
