import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Targeting, score } from '../src/game/targeting.js';

const actor = (x = 0, z = 0, fx = 0, fz = 1) => ({ x, z, fx, fz });
const c = (ref, x, z, extra = {}) => ({ ref, x, z, ...extra });

test('things behind her are ignored unless they are right at her feet', () => {
  assert.equal(score(actor(), c('a', 0, -2)), -Infinity);
  assert.ok(score(actor(), c('b', 0, -0.5)) > -Infinity);
  assert.ok(score(actor(), c('c', 0, 2)) > -Infinity);
});

test('type priority wins over a slightly better position', () => {
  const t = new Targeting();
  const got = t.update(0.016, actor(), [c('rock', 0.2, 1.0), c('npc', 0.6, 1.6, { priority: 1 })]);
  assert.equal(got.ref, 'npc');
});

test('the target does not flicker when two candidates are nearly tied', () => {
  const t = new Targeting();
  const cands = [c('a', -0.3, 1.2), c('b', 0.3, 1.2)];
  const first = t.update(0.016, actor(), cands).ref;
  for (let i = 0; i < 60; i++) {
    const wobble = (i % 2 ? 0.05 : -0.05);
    assert.equal(t.update(0.016, actor(0, 0, wobble, 1), cands).ref, first);
  }
});

test('a clearly better challenger takes over after the dwell time', () => {
  const t = new Targeting();
  t.update(0.016, actor(), [c('far', 0, 2.4)]);
  const cands = [c('far', 0, 2.4), c('near', 0, 0.6, { priority: 1 })];
  assert.equal(t.update(0.05, actor(), cands).ref, 'far');
  assert.equal(t.update(0.1, actor(), cands).ref, 'near');
});

test('cycling and touch picks hold until the pick expires or leaves reach', () => {
  const t = new Targeting();
  const cands = [c('a', 0, 1), c('b', 0.4, 1.4)];
  t.update(0.016, actor(), cands);
  const next = t.cycle();
  assert.notEqual(next.ref, 'a');
  for (let i = 0; i < 30; i++) assert.equal(t.update(0.016, actor(), cands).ref, next.ref);
  assert.equal(t.update(0.016, actor(), [c('a', 0, 1)]).ref, 'a');
});
