import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Sim } from '../src/game/sim.js';
import { QUALITIES, stateOf } from '../src/game/qualities.js';

const DT = 1 / 30;
const find = (s, kind) => s.entities.find(e => e.kind === kind);
// stand next to e, facing it, and let the targeting settle on it
const face = (s, e, side = 1.2) => {
  const P = s.player;
  P.x = e.x; P.z = e.z - (e.r + side); P.fx = 0; P.fz = 1;
  for (let i = 0; i < 10; i++) s.update(DT);
  assert.equal(s.target, e, `targeting ${e.kind}`);
};
const run = (s, seconds, input) => { for (let t = 0; t < seconds; t += DT) s.update(DT, input); };
const totals = s => QUALITIES.map(k => s.L.total(k));

test('weight carried from the boulder to the plate opens the gate; the books stay balanced', () => {
  const s = Sim.arena();
  const before = totals(s);
  const rock = find(s, 'rock'), plate = find(s, 'plate');
  face(s, rock);
  for (let i = 0; i < 3; i++) s.transfer('take', 'w');
  assert.equal(s.player.holder.q.w, 5);
  face(s, plate, 0.9);
  for (let i = 0; i < 3; i++) s.transfer('give', 'w');
  run(s, 0.2);
  assert.equal(s.gateEntity.state.open, true);
  run(s, 3);
  assert.deepEqual(totals(s), before);
});

test('a heavy body breaks the rotten bridge; a cold pond can be walked on', () => {
  const s = Sim.arena();
  const rock = find(s, 'rock');
  face(s, rock);
  s.transfer('take', 'w');
  const P = s.player, br = s.bridgeEntity;
  P.x = br.x; P.z = br.z - 2;
  run(s, 1.5, { mx: 0, mz: 1 });
  assert.equal(br.state.broken, true);
  const pond = find(s, 'pond');
  face(s, pond, 0.6);
  s.transfer('take', 'h');
  assert.equal(stateOf(pond.holder).frozen, true);
  run(s, 1.5, { mx: 0, mz: 1 });
  assert.ok(Math.hypot(P.x - pond.x, P.z - pond.z) < pond.r, 'she walked onto the ice');
});

test('logs are hauled visibly: to the stockpile, then on to the site, which rises', () => {
  const s = Sim.arena();
  const site = s.siteEntity.site;
  for (const log of s.entities.filter(e => e.kind === 'log')) {
    face(s, log, 0.4);
    assert.match(s.dispatch() || '', /去搬|还需要/);
    run(s, 12);
  }
  for (const st of s.entities.filter(e => e.kind === 'stone')) { face(s, st, 0.4); s.dispatch(); run(s, 12); }
  assert.equal(s.entities.filter(e => e.kind === 'log').length + s.yardEntity.store.log + (site.stages[2].got.log || 0) + (site.stages[3]?.got.log || 0) >= 3, true);
  // lead the crew to the site: they carry from the stockpile and build while they are near
  const P = s.player;
  P.x = s.siteEntity.x + 2; P.z = s.siteEntity.z;
  let sawHaulToSite = false;
  for (let t = 0; t < 90 && !site.complete; t += DT) { s.update(DT); if (s.haulJobs.some(j => j.to === 'site')) sawHaulToSite = true; }
  assert.equal(sawHaulToSite, true, 'materials were carried, not teleported');
  assert.ok(site.index >= 3, `site reached stage ${site.index}`);
});

test('the onibi can be pacified and invited, or killed — and the world counts', () => {
  const a = Sim.arena();
  const oni = find(a, 'yokai');
  face(a, oni, 0.8);
  // it steals warmth back on contact, so keep taking until it is back at its natural heat
  for (let i = 0; i < 6 && !oni.state.calm; i++) { a.target = oni; a.transfer('take', 'h'); a.update(DT); }
  assert.equal(oni.state.calm, true);
  const crewBefore = a.crew.members.length;
  a.target = oni;
  assert.equal(a.context(), '邀请加入');
  assert.equal(a.crew.members.length, crewBefore + 1);
  assert.equal(a.pacified, 1);

  const b = Sim.arena();
  const oni2 = find(b, 'yokai');
  face(b, oni2, 0.8);
  b.transfer('take', 'v'); b.transfer('take', 'v');
  b.update(DT);
  assert.equal(b.kills, 1);
  assert.equal(find(b, 'yokai'), undefined);
});

test('plant, give life, harvest', () => {
  const s = Sim.arena();
  const plot = s.plotEntity;
  face(s, plot, 0.6);
  assert.equal(s.context(), '种下胡瓜');
  for (let i = 0; i < 2; i++) s.transfer('give', 'v');
  s.update(DT);
  assert.equal(plot.plot.stage, 2);
  run(s, 200);  // the rest grows in game hours
  s.target = plot;
  assert.equal(s.context(), '收获');
});
