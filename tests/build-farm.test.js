import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Site } from '../src/game/build.js';
import { Plot } from '../src/game/farm.js';
import { Ledger, makeHolder } from '../src/game/qualities.js';

const inn = () => new Site({
  clear: { work: 1 },
  stones: { needs: { stone: 2 }, work: 2 },
  pillars: { needs: { log: 2 }, work: 2 },
  beam: { needs: { log: 1 }, work: 2 },
  roof: { needs: { thatch: 2 }, work: 2 },
});

test('a stage only starts once its materials are physically on site', () => {
  const s = inn();
  s.work(1, 1);
  assert.equal(s.stage.id, 'stones');
  s.work(5, 3);
  assert.equal(s.stage.id, 'stones', 'no stones delivered yet');
  assert.equal(s.deliver('log'), false, 'logs are not wanted yet');
  s.deliver('stone'); s.deliver('stone');
  assert.equal(s.deliver('stone'), false, 'only two needed');
  s.work(1, 2);
  assert.equal(s.stage.id, 'pillars');
});

test('raising the beam triggers the ceremony, and the site completes', () => {
  const s = inn();
  s.work(1, 1); s.deliver('stone'); s.deliver('stone'); s.work(2, 1);
  s.deliver('log'); s.deliver('log'); s.work(2, 1);
  s.deliver('log'); s.work(2, 1);
  const ev = s.drain().map(e => e.type);
  assert.ok(ev.includes('ceremony'));
  s.deliver('thatch'); s.deliver('thatch'); s.work(2, 1);
  assert.equal(s.complete, true);
});

test('a crop grows only when its conditions (qualities) are met', () => {
  const p = new Plot({ amounts: { l: 0 } });
  p.plant('cucumber');
  p.watered = true;
  p.tick(10);
  assert.equal(p.stage, 0);
  assert.equal(p.why, 'l', 'too dark');
  const L = new Ledger();
  const me = L.add(makeHolder({ material: 'body', amounts: { l: 2 } }));
  L.add(p.holder);
  L.give(me, p.holder, 'l', 3);
  p.tick(6);
  assert.equal(p.ripe, true);
  assert.equal(p.harvest(), 'cucumber');
});

test('giving life moves the crop on by whole stages', () => {
  const L = new Ledger();
  const me = L.add(makeHolder({ material: 'body', amounts: { v: 4 }, max: { v: 9 } }));
  const p = new Plot();
  L.add(p.holder);
  p.plant('soba');
  L.give(me, p.holder, 'v', 9); L.give(me, p.holder, 'v', 9);
  assert.equal(p.absorbLife(), 2);
  assert.equal(p.stage, 2);
});
