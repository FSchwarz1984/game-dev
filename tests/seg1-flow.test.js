// Plays segment 1 from the first step on the road to the end card, with a bot at the controls
// and no renderer: every scene must hand control back, every gate must open, nothing softlocks.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Field } from '../src/game/field.js';
import { Director } from '../src/story/cine.js';
import { prologue, day1 } from '../src/story/seg1.js';

const DT = 1 / 30;
const tickle = () => new Promise(r => setImmediate(r));

const PLACES = {
  start: [40, 20], roadUp: [[36, 18], [32, 16]],
  dosojin: [28, 13], dosojinStand: [28, 15], dosojinZone: { x: 28, z: 15, r: 2.5 },
  graves: Array.from({ length: 9 }, (_, i) => [10 + i * 1.2, 7]), gravesStand: [14, 9.5], gravesZone: { x0: 8, x1: 22, z0: 5, z1: 11 },
  camphor: [0, 0], camphorFoot: [0, 2.4], loadSpot: [-1.3, 2.2],
  wake: [-1.6, 3.2], hut: [-9, 1], hutDoor: [-9, 3.8], frame: [-6, 4.2],
  shrine: [6, -2], beam: [6, 0.4], shrineZone: { x: 6, z: 1, r: 3 },
  rocks: [[3, 7], [-3, 9]],
  eastExit: { x0: 44, x1: 70, z0: -30, z1: 50 },
};

function makeGame() {
  const f = new Field();
  const listeners = new Set();
  const log = [];
  const actors = {};
  const mkActor = (id, base) => {
    const a = base || { x: 0, z: 0 };
    Object.assign(a, { face: 'front', visible: false, variant: 'none', pose: null, follow: null, ride: null, anims: [] });
    a.play = function (anim) { this.anims.push(anim); return 0.4; };
    a.idle = function () {};
    actors[id] = a;
    return a;
  };
  // her actor is a view of the field's player, so scenes and play move the same body
  const herBody = { get x() { return f.player.x; }, set x(v) { f.player.x = v; }, get z() { return f.player.z; }, set z(v) { f.player.z = v; } };
  mkActor('tsuzumi', herBody);
  mkActor('saji');
  const props = {};
  const stage = {
    shots: [],
    shot(name) { this.shots.push(name); }, cam() {}, follow() {}, tod(h) { this.hour = h; },
    actor: id => actors[id],
    prop: id => (props[id] ||= { id, state: null, visible: false }),
    climbPoints: () => [[0, 1, 1], [0, 0.5, 3], [0, 0, 6], [0, 0, 9]],
    vista(v) { this.vistaState = v; if (v) this.vistaSeen = true; },
    inset(kind, on) { if (on) log.push('inset:' + kind); },
    morning() { log.push('morning'); }, beamFall() { log.push('beamFall'); },
  };
  let D;
  let talking = 0;
  const ui = {
    get blocking() { return talking > 0; },
    say(lines) { talking++; log.push(...lines.map(l => `${l.who}:${l.text}`)); return D.wait(0.3 * lines.length).then(() => { talking--; }); },
    card(h, s, d = 3) { log.push('card:' + h); return D.wait(d); },
    title(h, s, d = 4) { log.push('title:' + h); return D.wait(d); },
    sub(t, d = 2) { return D.wait(d); },
    fade(a, d = 0.6) { return D.wait(d); },
    letterbox() {}, hint() {},
  };
  D = new Director({ ui, stage, audio: null });
  const tips = new Map();
  const hud = { shown: true, unlocked: new Set(), show(on) { this.shown = on; }, unlock(k) { this.unlocked.add(k); }, tip(key, text) { tips.set(key, text); }, untip(key) { tips.delete(key); } };
  const au = { music() {}, festival() {}, sfx() {}, stinger() {}, duck() {} };
  const G = {
    D, f, stage, ui, hud, au, P: PLACES, touch: false, log, tips, saved: null,
    on(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    save(s) { this.saved = s; },
  };
  return { G, step: input => {
    f.update(DT, input);
    for (const e of f.drain()) for (const fn of [...listeners]) fn(e);
    D.tick(DT);
  } };
}

/** The bot: walk to a point, face things, press keys; the clock runs while it waits. */
function bot({ G, step }) {
  const f = G.f;
  const run = async (n = 1, input) => { for (let i = 0; i < n; i++) { step(input); await tickle(); } };
  const self = {
    async idle(sec) { await run(Math.round(sec / DT)); },
    async until(cond, sec = 240) { for (let i = 0; i < sec / DT; i++) { if (cond()) return; await run(1); } throw new Error('timed out waiting; last lines: ' + G.log.slice(-4).join(' | ')); },
    async control() { await self.until(() => f.control && !G.D.busy && !G.ui.blocking); },
    async walk([x, z], tol = 0.3) {
      await self.control();
      for (let i = 0; i < 30 / DT; i++) {
        const dx = x - f.player.x, dz = z - f.player.z, d = Math.hypot(dx, dz);
        if (d < tol) return;
        if (!f.control) { await run(1); continue; }
        await run(1, { mx: dx / d, mz: dz / d });
      }
      throw new Error(`could not reach ${x},${z} (at ${f.player.x.toFixed(2)},${f.player.z.toFixed(2)})`);
    },
    async aim(e) {
      const dx = e.x - f.player.x, dz = e.z - f.player.z, d = Math.hypot(dx, dz);
      f.player.fx = dx / d; f.player.fz = dz / d;
      await self.until(() => f.target === e, 5).catch(err => {
        throw new Error(`cannot target ${e.id} from ${f.player.x.toFixed(2)},${f.player.z.toFixed(2)}: target=${f.target?.id} control=${f.control} ranked=${(f.targeting.ranked || []).map(c => c.ref.id)}; ${err.message}`);
      });
    },
    async press(e) { await self.control(); await self.aim(e); const r = f.context(); await run(2); return r; },
    async verb(verb, k, e) { await self.control(); await self.aim(e); const r = f.transfer(verb, k); await run(2); return r; },
  };
  return self;
}

test('segment 1 plays through from the road to the end card', async () => {
  const game = makeGame(), { G } = game, B = bot(game), f = G.f;

  const pro = prologue(G);
  await B.control();
  assert.ok(G.log.includes('card:盆の十六日　暮れ六つ'));
  // the statues greet her at the entrance, before she has control
  assert.ok(G.log.includes('tsuzumi:戴斗笠的这位，这一颗我替您吃了。'));
  assert.equal(G.stage.prop('dango').state, 'one');
  // going back down the road is refused, with a reason
  await B.walk([43.6, 20]);
  await B.idle(0.3);
  // the graves: hang nine lanterns
  await B.walk(PLACES.gravesStand, 1.2);
  await B.control();
  for (let i = 0; i < 9; i++) {
    const g = f.get('grave' + i);
    await B.walk([g.x, g.z + 1.1], 0.35);
    assert.equal(await B.press(g), '挂灯笼');
  }
  await B.until(() => G.log.includes('tsuzumi:……这排墓，九座。'));
  await B.until(() => G.log.includes('tsuzumi:今年的囃子，近。'));
  assert.equal(G.stage.prop('lantern9').attachTo, 'tsuzumi');
  // the camphor
  await B.control();
  const camphor = f.get('camphor');
  await B.walk([0, 2.5], 0.3);
  assert.equal(await B.press(camphor), '爬');
  await B.until(() => G.stage.vistaSeen);
  await B.until(() => G.log.includes('title:天岸'), 300);
  await B.until(() => G.saved === 'day1', 60);
  await pro;

  // ---------------------------------------------------------------- day 1
  const d1 = day1(G);
  await B.control();
  assert.ok(G.log.includes('inset:hat'));
  // the east road is closed until she carries something
  await B.walk([43.2, 10]);
  await B.walk([44.4, 10]).catch(() => {});
  assert.ok(f.player.x < 44, 'the east exit is closed');
  // the hut: her hand passes through
  const hut = f.get('hut');
  await B.walk(PLACES.hutDoor, 0.4);
  assert.equal(await B.press(hut), '推门');
  await B.until(() => G.log.includes('tsuzumi:……门闩是我昨天才修的。'));
  // a give on the far hut is refused (and she has not learned it yet anyway)
  // the beam falls on Saji
  await B.until(() => G.log.includes('beamFall'), 60);
  await B.walk([6, 2.0], 0.3);
  await B.until(() => G.log.includes('saji:看什么看，背箱的！抬啊！'));
  const beam = f.get('beam');
  assert.equal(await B.press(beam), '抬');
  await B.until(() => G.hud.unlocked.has('w'));
  for (let i = 0; i < 3; i++) assert.equal((await B.verb('take', 'w', beam)).type, 'transfer');
  assert.equal(f.player.holder.q.w, 5);
  await B.until(() => G.log.includes('tsuzumi:梁有多重，我现在就有多重。'));
  await B.until(() => G.log.some(l => l.startsWith('saji:昨晚全')));
  // the shrine refuses: shimenawa
  const shrine = f.get('shrine');
  await B.walk([6, -0.4], 0.4);
  assert.equal((await B.verb('take', 'w', shrine)).reason, 'sacred');
  // the far hut refuses a gift: out of reach
  await B.walk(PLACES.hutDoor, 0.4);
  assert.equal((await B.verb('give', 'w', hut)).reason, 'far');
  // the old frame: give it its weight back
  const frame = f.get('frame');
  await B.walk([-6, 5.3], 0.4);
  for (let i = 0; i < 3; i++) assert.equal((await B.verb('give', 'w', frame)).type, 'transfer');
  assert.equal(frame.far, 0);
  assert.equal(f.player.holder.q.w, 2);
  await B.until(() => G.log.includes('tsuzumi:它本来就这么重。'));
  assert.equal(await B.press(frame), '背上');
  await B.until(() => G.log.includes('tsuzumi:宿场。那边旧东西多。'));
  assert.equal(G.stage.actor('saji').ride, 'tsuzumi');
  assert.equal(G.stage.actor('tsuzumi').variant, 'frame');
  // out by the statues and the east road
  await B.walk(PLACES.dosojinStand, 1.5);
  await B.walk([45, 15], 0.5);
  await B.until(() => G.log.includes('card:九十九折峠'));
  await B.until(() => G.saved === 'end', 60);
  await d1;
});

test('if she gives the beam its weight back, Saji objects, and she can still finish', async () => {
  const game = makeGame(), { G } = game, B = bot(game), f = G.f;
  // jump to day 1 directly
  G.stage.prop('lantern9');
  const d1 = day1(G);
  await B.control();
  await B.until(() => G.log.includes('beamFall'), 80);
  await B.walk([6, 2.0], 0.3);
  await B.until(() => G.log.includes('saji:看什么看，背箱的！抬啊！'));
  const beam = f.get('beam');
  await B.press(beam);
  await B.until(() => G.hud.unlocked.has('w'));
  await B.verb('take', 'w', beam);
  await B.verb('give', 'w', beam);
  await B.until(() => G.log.includes('saji:更重了！你在干什么啦！'));
  // take a rock's weight first: she can only carry so much more
  const rock = f.get('rock0');
  await B.walk([3, 6], 0.6);
  await B.verb('take', 'w', rock); await B.verb('take', 'w', rock);
  await B.walk([6, 2.0], 0.3);
  await B.verb('take', 'w', beam);
  assert.equal((await B.verb('take', 'w', beam)).reason, 'overload');
  // the shrine puts her back to herself; then the beam
  await B.walk([6, -0.4], 0.4);
  assert.equal(await B.press(f.get('shrine')), '归还');
  await B.walk([6, 2.0], 0.3);
  // Saji is still pinned; the beam still holds what is left
  while (beam.holder.q.w > 0) await B.verb('take', 'w', beam);
  await B.until(() => G.log.some(l => l.startsWith('saji:昨晚全')));
  // the frame wants three: she carries 2 + 3 from the beam - 1 given back... whatever she has, the rocks make up the rest
  const frame = f.get('frame');
  await B.walk([-6, 5.3], 0.4);
  while (frame.far > 0) {
    const r = await B.verb('give', 'w', frame);
    if (r.type !== 'transfer') {
      await B.walk([-3, 8], 0.6);
      await B.verb('take', 'w', f.get('rock1'));
      await B.walk([-6, 5.3], 0.4);
    }
  }
  assert.equal(await B.press(frame), '背上');
  await B.until(() => G.log.includes('tsuzumi:宿场。那边旧东西多。'));
  await B.walk([45, 15], 0.5);
  await B.until(() => G.saved === 'end', 60);
  await d1;
});
