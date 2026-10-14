// The segment-1 field and the cutscene director, without a browser.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Field, farness } from '../src/game/field.js';
import { QUALITIES } from '../src/game/qualities.js';
import { Director, faceOf } from '../src/story/cine.js';

const DT = 1 / 30;
const facing = (f, e) => { const P = f.player, dx = e.x - P.x, dz = e.z - P.z, d = Math.hypot(dx, dz); P.fx = dx / d; P.fz = dz / d; };
const settle = f => { for (let i = 0; i < 10; i++) f.update(DT); };

test('taking a quality pushes a thing away; giving it back brings it near', () => {
  const f = new Field();
  f.allow('w');
  const beam = f.add({ id: 'beam', name: '梁', x: 1, z: 0, q: { w: 3 } });
  const frame = f.add({ id: 'frame', name: '旧背負子', x: -1, z: 0, q: { w: 0 }, base: { w: 3 } });
  assert.equal(farness(beam), 0);
  assert.equal(farness(frame), 1);

  facing(f, beam); settle(f);
  assert.equal(f.target, beam);
  for (let i = 0; i < 3; i++) assert.equal(f.transfer('take', 'w').type, 'transfer');
  assert.equal(beam.holder.q.w, 0);
  assert.equal(beam.far, 1);
  assert.equal(f.player.holder.q.w, 5);
  assert.ok(f.drain().some(e => e.type === 'far' && e.e === beam));

  facing(f, frame); settle(f);
  assert.equal(f.target, frame);
  f.transfer('give', 'w');
  assert.ok(Math.abs(frame.far - 2 / 3) < 1e-9, 'each unit brings back a third');
  f.transfer('give', 'w'); f.transfer('give', 'w');
  assert.equal(frame.far, 0);
  assert.ok(f.drain().some(e => e.type === 'near' && e.e === frame));
  assert.equal(f.player.holder.q.w, 2);
});

test('a deep-far thing cannot be touched or reached', () => {
  const f = new Field();
  f.allow('w');
  const hut = f.add({ id: 'hut', name: '小屋', x: 3, z: 0, r: 1.5, deep: true });
  f.player.fx = 1; f.player.fz = 0;
  let closest = 1e9;
  for (let i = 0; i < 90; i++) { f.update(DT, { mx: 1, mz: 0 }); closest = Math.min(closest, Math.hypot(f.player.x - 3, f.player.z)); }
  assert.ok(closest >= 1.5 + 0.5, `she stays a step away (closest ${closest.toFixed(2)} m)`);
  f.player.x = 0; f.player.z = 0; f.player.fx = 1; f.player.fz = 0;
  for (let i = 0; i < 5; i++) f.update(DT);
  assert.equal(f.target, hut);
  const e = f.transfer('give', 'w');
  assert.equal(e.type, 'refused');
  assert.equal(e.reason, 'far');
  assert.equal(hut.far, 1);
});

test('verbs she has not learned do nothing, and nothing changes hands', () => {
  const f = new Field();
  const rock = f.add({ id: 'rock', x: 1, z: 0, q: { w: 2 } });
  f.player.fx = 1; f.player.fz = 0; settle(f);
  assert.equal(f.transfer('take', 'w'), null);
  assert.equal(rock.holder.q.w, 2);
  f.allow('w', ['take']);
  assert.equal(f.transfer('give', 'w'), null);
  assert.equal(f.transfer('take', 'w').type, 'transfer');
});

test('a blocking zone turns her back once per approach and says why', () => {
  const f = new Field();
  f.zone({ id: 'east', x0: 5, x1: 20, z0: -10, z1: 10, block: '还没背上背负子。' });
  for (let i = 0; i < 120; i++) f.update(DT, { mx: 1, mz: 0 });
  assert.ok(f.player.x < 5);
  const ev = f.drain().filter(e => e.type === 'blocked');
  assert.equal(ev.length, 1);
  assert.equal(ev[0].say, '还没背上背负子。');
});

test('the shrine puts her body back and the books stay balanced', () => {
  const f = new Field();
  f.allow('w');
  f.add({ id: 'rock', x: 1, z: 0, q: { w: 3 } });
  f.player.fx = 1; f.player.fz = 0; settle(f);
  const before = QUALITIES.map(k => f.L.total(k));
  f.transfer('take', 'w'); f.transfer('take', 'w');
  f.restoreBody();
  assert.equal(f.player.holder.q.w, 2);
  assert.deepEqual(QUALITIES.map(k => f.L.total(k)), before);
});

test('the context key runs the target\'s action only when it offers one', () => {
  const f = new Field();
  let hung = 0;
  f.add({ id: 'grave', x: 1, z: 0, ctx: { label: () => (hung ? '' : '挂灯笼'), run: () => { hung += 1; return '挂上了'; } } });
  f.player.fx = 1; f.player.fz = 0; settle(f);
  assert.equal(f.contextLabel(), '挂灯笼');
  assert.equal(f.context(), '挂上了');
  assert.equal(f.contextLabel(), '');
  assert.equal(f.context(), null);
  assert.equal(hung, 1);
});

test('the director waits on the game clock and walks actors along a path', async () => {
  const stage = { actors: { a: { x: 0, z: 0, face: 'front', play() { return 0; }, idle() { this.idled = true; } } }, actor(id) { return this.actors[id]; } };
  const D = new Director({ stage });
  const log = [];
  const run = D.scene(async d => {
    await d.wait(0.5); log.push('waited');
    await d.move('a', [[2, 0], [2, -2]], { speed: 2 }); log.push('arrived');
    let k = 0; await d.tween(1, v => { k = v; }); log.push('tweened ' + k);
  });
  for (let i = 0; i < 200 && D.busy; i++) { D.tick(0.05); await Promise.resolve(); await Promise.resolve(); }
  await run;
  assert.deepEqual(log, ['waited', 'arrived', 'tweened 1']);
  const a = stage.actors.a;
  assert.equal(a.x, 2); assert.equal(a.z, -2);
  assert.equal(a.face, 'back');
  assert.ok(a.idled);
  assert.equal(faceOf(-1, 0.2), 'left');
});

test('standing still, she still chooses the thing beside her even if a scene turned her away', () => {
  const f = new Field();
  const beam = f.add({ id: 'beam', x: 0, z: -1.6, r: 0.7, q: { w: 3 } });
  f.player.fx = 1; f.player.fz = 0;          // turned to the east by a scene; the beam is north
  for (let i = 0; i < 10; i++) f.update(DT);
  assert.equal(f.target, beam);
  // walking east, the cone narrows again and the beam behind her shoulder drops out
  for (let i = 0; i < 10; i++) f.update(DT, { mx: 1, mz: 0 });
  assert.notEqual(f.target, beam);
});

test('pushing into a slanted wall, she slides along it instead of sticking', () => {
  // ground below the line z = x is walkable; above it is a wall (a diagonal bank)
  const f = new Field({ ground: (x, z) => (z > x ? 'ground' : 'wall') });
  f.player.x = 0; f.player.z = 1;
  for (let i = 0; i < 60; i++) f.update(DT, { mx: 1, mz: 0 });   // push east, straight into the slant
  assert.ok(f.player.x > 1, `she moved along the bank (x=${f.player.x.toFixed(2)})`);
  assert.ok(f.player.z > f.player.x, 'and never through it');
});
