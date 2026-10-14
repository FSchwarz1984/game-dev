// The gray-box stations fitted to the real test terrain (no rendering): the routes and blocks the
// layout promises actually hold on the ground they stand on.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Terrain } from '../src/world/terrain.js';
import { Sim } from '../src/game/sim.js';
import { FIELD } from '../src/play/layout.js';
import { attachTerrain } from '../src/play/ground.js';

const terrain = new Terrain();
const make = () => { const s = Sim.arena(FIELD); const q = attachTerrain(s, terrain, []); return { s, q }; };
const DT = 1 / 30;
const walk = (s, sec, mx, mz) => { for (let t = 0; t < sec; t += DT) s.update(DT, { mx, mz }); };

test('every station stands on dry, walkable ground (except the water ones)', () => {
  const { s, q } = make();
  for (const e of s.entities) {
    if (e.kind === 'pond' || e.kind === 'bridge') { assert.ok(q.isWater(e.x, e.z), `${e.kind} is over water`); continue; }
    assert.ok(terrain.walkable(e.x, e.z) && !q.isWater(e.x, e.z), `${e.kind} at ${e.x},${e.z}`);
  }
});

test('the south bank is reached over the main bridge only; the shut gate closes it to her and the crew', () => {
  const { s, q } = make();
  const log = s.entities.find(e => e.kind === 'log'), yard = s.yardEntity;
  assert.equal(q.nav.route(log.x, log.z, yard.x, yard.z), null, 'no way round the gate');
  // she cannot walk over the bridge past it either
  s.player.x = 3.5; s.player.z = 11.5;
  walk(s, 2, 0, 1);
  assert.ok(s.player.z < 13, `stopped at the gate (z ${s.player.z.toFixed(2)})`);
  s.gateEntity.state.open = true;
  const r = q.nav.route(log.x, log.z, yard.x, yard.z);
  assert.ok(r && r.length >= 2, 'a route over the bridge');
  walk(s, 2.5, 0, 1);
  assert.ok(s.player.z > 16, `she crossed the bridge (z ${s.player.z.toFixed(2)})`);
});

test('the stream stops her; ice or the rotten bridge carries her; heavy, the bridge gives way', () => {
  const { s } = make();
  const P = s.player;
  P.x = -9.5; P.z = 7.6;
  walk(s, 2, 0, 1);
  assert.ok(P.z < 9.2, 'the water stopped her');
  s.entities.find(e => e.kind === 'pond').holder.q.h = 0; // frozen
  walk(s, 2, 0, 1);
  assert.ok(P.z > 12, `she crossed on the ice (z ${P.z.toFixed(2)})`);

  const b = make().s, Q = b.player;
  Q.x = -13.5; Q.z = 7.4;
  walk(b, 2.5, 0, 1);
  assert.ok(Q.z > 12.4, `light enough, over the planks (z ${Q.z.toFixed(2)})`);
  const c = make().s, R = c.player;
  R.holder.q.w = 5;
  R.x = -13.5; R.z = 7.4;
  walk(c, 2.5, 0, 1);
  assert.equal(c.bridgeEntity.state.broken, true);
  assert.ok(R.z < 9.2, `she dropped back to the bank she came from (z ${R.z.toFixed(2)})`);
});
