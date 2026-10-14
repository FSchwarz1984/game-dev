import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Ledger, makeHolder, stateOf, bodyState, QUALITIES, REFUSAL } from '../src/game/qualities.js';

const her = () => makeHolder({ material: 'body', amounts: { w: 2, h: 1, l: 0, s: 1, v: 2 } });

test('a transfer moves one unit and the books stay balanced', () => {
  const L = new Ledger();
  const me = L.add(her());
  const rock = L.add(makeHolder({ material: 'stone', amounts: { w: 3 } }));
  const before = QUALITIES.map(k => L.total(k));
  const e = L.take(me, rock, 'w', 3);
  assert.equal(e.type, 'transfer');
  assert.equal(rock.q.w, 2);
  assert.equal(me.q.w, 3);
  L.give(me, rock, 'w', 3);
  L.release(me, 'h', 3);
  assert.deepEqual(QUALITIES.map(k => L.total(k)), before);
});

test('refusals name their reason, so the UI never fails silently', () => {
  const L = new Ledger();
  const me = L.add(her());
  const camphor = L.add(makeHolder({ material: 'plant', amounts: { v: 9 }, sacred: true }));
  const empty = L.add(makeHolder({ material: 'stone', amounts: { w: 0 } }));
  assert.equal(L.take(me, camphor, 'v', 3).reason, REFUSAL.sacred);
  assert.equal(L.give(me, camphor, 'v', 3).reason, REFUSAL.sacred);
  assert.equal(L.take(me, empty, 'w', 3).reason, REFUSAL.empty);
  assert.equal(L.release(me, 'l', 3).reason, REFUSAL.empty);
});

test('her capacity is how far she may drift from her own natural state', () => {
  const L = new Ledger();
  const me = L.add(her());
  const rock = L.add(makeHolder({ material: 'stone', amounts: { w: 9 } }));
  const pond = L.add(makeHolder({ material: 'water', amounts: { h: 1 } }));
  assert.equal(L.take(me, rock, 'w', 2).type, 'transfer');
  assert.equal(L.take(me, rock, 'w', 2).type, 'transfer');
  assert.equal(L.take(me, rock, 'w', 2).reason, REFUSAL.overload);
  // giving away her own heat also counts as drifting
  assert.equal(L.give(me, pond, 'h', 2).reason, REFUSAL.overload);
  L.give(me, rock, 'w', 2);
  assert.equal(L.give(me, pond, 'h', 2).type, 'transfer');
  assert.ok(bodyState(me).heavy && bodyState(me).cold);
});

test('state follows qualities: water freezes and boils, stone floats', () => {
  const L = new Ledger();
  const me = L.add(her());
  const pond = L.add(makeHolder({ material: 'water', amounts: { h: 1 } }));
  const rock = L.add(makeHolder({ material: 'stone', amounts: { w: 1 } }));
  assert.equal(stateOf(pond).frozen, false);
  L.take(me, pond, 'h', 4);
  assert.equal(stateOf(pond).frozen, true);
  L.take(me, rock, 'w', 4);
  assert.equal(stateOf(rock).floats, true);
});

test('a yokai calms when rebalanced and dies when its life is taken', () => {
  const L = new Ledger();
  const me = L.add(makeHolder({ material: 'body', amounts: { v: 2 }, max: { v: 9 } }));
  const onibi = L.add(makeHolder({ material: 'yokai', amounts: { h: 4, v: 2 }, base: { h: 1 } }));
  assert.equal(stateOf(onibi).calm, false);
  for (let i = 0; i < 3; i++) L.take(me, onibi, 'h', 9);
  assert.equal(stateOf(onibi).calm, true);
  const kappa = L.add(makeHolder({ material: 'yokai', amounts: { w: 3, v: 2 }, base: { w: 1 } }));
  L.take(me, kappa, 'v', 9); L.take(me, kappa, 'v', 9);
  assert.equal(stateOf(kappa).dead, true);
});

test('sources refill only while active, and the ledger records it', () => {
  const L = new Ledger();
  let day = true;
  const sun = L.add(makeHolder({ amounts: { l: 0 }, source: { k: 'l', rate: 2, cap: 3, active: () => day } }));
  const before = L.total('l');
  L.tick(1);
  assert.equal(sun.q.l, 2);
  day = false;
  L.tick(5);
  assert.equal(sun.q.l, 2);
  assert.equal(L.total('l'), before);
});
