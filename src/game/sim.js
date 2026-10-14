// The gray-box gameplay simulation: entities on a ground plane, her body, the transfer verb,
// the crew, a construction site, a farm plot and a yokai. Pure logic on (x, z); the render
// layer reads `sim.entities`, `sim.player` and the event queue and draws them. Nothing here
// is story content: names are functional placeholders until G1 is approved.

import { Ledger, makeHolder, stateOf, bodyState, QUALITY_INFO } from './qualities.js';
import { Targeting } from './targeting.js';
import { Crew } from './crew.js';
import { Site } from './build.js';
import { Plot } from './farm.js';

const hyp = Math.hypot;

// What each kind of thing is made of, how the target system ranks it, and what E does to it.
const KINDS = {
  rock: { name: '岩', material: 'stone', priority: 0, solid: true, r: 0.8 },
  log: { name: '原木', material: 'wood', priority: 1, haul: 'log', r: 0.5 },
  stone: { name: '石块', material: 'stone', priority: 1, haul: 'stone', r: 0.4 },
  pond: { name: '池', material: 'water', priority: 0, r: 3.2 },
  brazier: { name: '火盆', material: 'thing', priority: 0, solid: true, r: 0.5 },
  lantern: { name: '灯笼', material: 'lantern', priority: 0, solid: true, r: 0.4 },
  bell: { name: '钟', material: 'bell', priority: 0, solid: true, r: 0.6 },
  falls: { name: '瀑布', material: 'water', priority: 0, r: 1.2 },
  weeds: { name: '杂草', material: 'plant', priority: 0, r: 0.8 },
  plot: { name: '田', material: 'soil', priority: 1, r: 1.0 },
  site: { name: '工地', material: 'thing', priority: 1, r: 1.6 },
  yard: { name: '资材堆', material: 'thing', priority: 1, r: 1.0 },
  shrine: { name: '神棚', material: 'thing', priority: 1, solid: true, r: 0.6, sacred: true },
  plate: { name: '压板', material: 'stone', priority: 0, r: 0.7 },
  gate: { name: '门', material: 'thing', priority: 0, r: 1.0 },
  bridge: { name: '朽桥', material: 'wood', priority: 0, r: 1.0 },
  yokai: { name: '鬼火', material: 'yokai', priority: 2, r: 0.5 },
};

export class Sim {
  constructor() {
    this.L = new Ledger();
    this.entities = [];
    this.events = [];
    this.targeting = new Targeting();
    this.crew = new Crew();
    this.hour = 9;            // game clock
    this.hourPerSec = 1 / 30; // one game hour every 30 s in the gray box
    this.blocks = [];   // impassable strips (a ditch), crossable only on an unbroken bridge
    this.haulJobs = [];
    this.kills = 0;
    this.pacified = 0;
    this.nextId = 1;
    this.player = {
      x: 0, z: 0, fx: 0, fz: 1, speed: 4.2, cap: 3, iframes: 0, carrying: null,
      holder: this.L.add(makeHolder({ material: 'body', amounts: { w: 2, h: 1, l: 0, s: 1, v: 3 }, max: { w: 9, h: 9, l: 9, s: 9, v: 9 } })),
    };
    this.L.on(e => this.events.push(e));
  }

  get isDay() { const h = this.hour % 24; return h >= 6 && h < 19; }

  add(kind, x, z, opt = {}) {
    const K = KINDS[kind];
    const e = {
      id: this.nextId++, kind, x, z, name: opt.name || K.name, r: opt.r ?? K.r, priority: K.priority,
      solid: K.solid || false, haul: K.haul || null, state: {}, dead: false, ...opt.extra,
      holder: this.L.add(makeHolder({ material: K.material, amounts: opt.q, base: opt.base, max: opt.max, sacred: opt.sacred ?? K.sacred, source: opt.source })),
    };
    this.entities.push(e);
    return e;
  }

  remove(e) { e.dead = true; this.L.remove(e.holder); this.entities = this.entities.filter(x => x !== e); }

  /** Build the gray-box arena: one station per quality, plus crew, building, farm and a yokai. */
  static arena() {
    const s = new Sim();
    const isDay = () => s.isDay;
    s.add('shrine', 0, -3);
    // 重: a boulder, a pressure plate that opens a gate, a rotten plank bridge
    s.add('rock', -7, 2, { q: { w: 3 } });
    s.add('plate', -10, 6, { q: { w: 0 } });
    s.gateEntity = s.add('gate', -10, 10);
    s.bridgeEntity = s.add('bridge', -4, 9, { q: { w: 1 } });
    s.blocks.push({ x0: -9, x1: 1, z0: 8.4, z1: 9.6, bridge: s.bridgeEntity });
    // 熱: a pond to freeze, a brazier that refills its heat
    s.add('pond', 8, 6, { q: { h: 1 } });
    s.add('brazier', 4, 2, { q: { h: 3 }, source: { k: 'h', rate: 0.5, cap: 3 } });
    // 光: a lantern fed by daylight
    s.add('lantern', 12, -2, { q: { l: 1 }, source: { k: 'l', rate: 0.4, cap: 3, active: isDay } });
    // 音: a bell and a waterfall
    s.add('bell', -12, -4, { q: { s: 0 } });
    s.add('falls', 14, 10, { q: { s: 3 }, source: { k: 's', rate: 0.3, cap: 3 } });
    // 生: weeds that keep growing
    s.add('weeds', -3, -8, { q: { v: 2 }, source: { k: 'v', rate: 0.1, cap: 3 } });
    // farm, building, logistics
    s.plotEntity = s.add('plot', 3, -9);
    s.plotEntity.plot = new Plot({ amounts: { l: 1, h: 1 } });
    s.L.holders.delete(s.plotEntity.holder);
    s.plotEntity.holder = s.L.add(s.plotEntity.plot.holder);
    s.yardEntity = s.add('yard', -8, -10);
    s.yardEntity.store = { log: 0, stone: 0 };
    s.siteEntity = s.add('site', -13, -12);
    s.siteEntity.site = new Site({ clear: { work: 2 }, stones: { needs: { stone: 2 }, work: 3 }, pillars: { needs: { log: 2 }, work: 3 }, beam: { needs: { log: 1 }, work: 3 } });
    for (let i = 0; i < 3; i++) s.add('log', 6 + i * 1.4, -6, { q: { w: 2 } });
    for (let i = 0; i < 2; i++) s.add('stone', 9, -8 - i * 1.2, { q: { w: 1 } });
    // a hungry onibi: too much heat, wanders near the weeds
    s.add('yokai', -1, -12, { q: { h: 4, v: 2 }, base: { h: 1 }, extra: { home: { x: -1, z: -12 } } });
    for (let i = 0; i < 3; i++) s.crew.add(-1 - i, 1);
    return s;
  }

  // ---------------------------------------------------------------- per frame

  /** input: { mx, mz } camera-relative movement already turned into world axes (−1..1). */
  update(dt, input = { mx: 0, mz: 0 }) {
    const P = this.player, body = bodyState(P.holder);
    this.hour += dt * this.hourPerSec;
    this.L.tick(dt);

    // movement: her body follows what she carries
    let speed = P.speed * (body.heavy ? 0.7 : 1) * (body.light ? 1.25 : 1) * (P.carrying ? 0.8 : 1);
    const len = hyp(input.mx, input.mz);
    if (len > 0.05) {
      const ux = input.mx / Math.max(1, len), uz = input.mz / Math.max(1, len);
      P.fx = input.mx / len; P.fz = input.mz / len;
      this.tryMove(P.x + ux * speed * dt, P.z + uz * speed * dt);
    }
    P.iframes = Math.max(0, P.iframes - dt);
    this.crew.lead(P.x, P.z);

    this.updateWorld(dt);
    this.crew.update(dt);
    this.updateHauls();

    // the target, shown before any button is pressed
    const cands = this.entities.filter(e => !e.dead && e !== P.carrying).map(e => ({ x: e.x, z: e.z, priority: e.priority, reach: 1.6 + e.r, ref: e }));
    const t = this.targeting.update(dt, P, cands);
    this.target = t ? t.ref : null;
  }

  tryMove(nx, nz) {
    const P = this.player, body = bodyState(P.holder);
    for (const e of this.entities) {
      const d = hyp(nx - e.x, nz - e.z);
      if (e.solid && d < e.r + 0.35) return;
      if (e.kind === 'pond' && d < e.r && !stateOf(e.holder).frozen && !body.light) return;   // water: walk on it only when frozen (or light enough)
      if (e.kind === 'gate' && !e.state.open && d < e.r) return;
    }
    for (const b of this.blocks) {
      if (nx < b.x0 || nx > b.x1 || nz < b.z0 || nz > b.z1) continue;
      const onBridge = b.bridge && !b.bridge.state.broken && hyp(nx - b.bridge.x, nz - b.bridge.z) < b.bridge.r;
      if (!onBridge) return;
    }
    // the rotten bridge gives way under a heavy body
    const br = this.bridgeEntity;
    if (br && !br.state.broken && hyp(nx - br.x, nz - br.z) < br.r && P.holder.q.w > 2) {
      br.state.broken = true;
      this.events.push({ type: 'broke', e: br });
      return;
    }
    P.x = nx; P.z = nz;
  }

  updateWorld(dt) {
    const P = this.player;
    for (const e of this.entities) {
      if (e.kind === 'plate') {
        // pressed by anything heavy enough standing on it (a rock rolled onto it, or her own weight)
        // pressed by its own weight (give it 重), by something heavy on it, or by her when she is heavy
        const heavyHere = e.holder.q.w >= 3 || this.entities.some(o => o !== e && o.holder.q.w >= 3 && hyp(o.x - e.x, o.z - e.z) < e.r) || (hyp(P.x - e.x, P.z - e.z) < e.r && P.holder.q.w >= 3);
        if (heavyHere !== !!e.state.pressed) { e.state.pressed = heavyHere; this.gateEntity.state.open = heavyHere; this.events.push({ type: 'gate', open: heavyHere }); }
      }
      if (e.kind === 'plot') {
        e.plot.tick(dt * this.hourPerSec);
        if (e.plot.absorbLife()) this.events.push({ type: 'grew', e });
      }
      if (e.kind === 'site') {
        const workers = this.crew.members.filter(m => m.state === 'follow' && hyp(m.x - e.x, m.z - e.z) < 3).length;
        e.site.work(dt, workers);
        for (const ev of e.site.drain()) this.events.push({ ...ev, e });
      }
      if (e.kind === 'yokai') this.updateYokai(e, dt);
      if (e.kind === 'weeds') {
        if (!e.state.burning && bodyState(P.holder).hot && hyp(P.x - e.x, P.z - e.z) < e.r + 0.4) { e.state.burning = 3; this.events.push({ type: 'ignite', e }); }
        if (e.state.burning) {
          e.state.burning -= dt;
          if (e.holder.q.v > 0 && Math.random() < dt * 2) { e.holder.q.v -= 1; this.L.air.v += 1; }
          if (e.state.burning <= 0) { e.state.burning = 0; this.events.push({ type: 'burnt', e }); }
        }
      }
    }
  }

  updateYokai(y, dt) {
    const st = stateOf(y.holder), P = this.player;
    if (st.dead) {
      this.kills += 1;
      this.events.push({ type: 'killed', e: y });
      this.remove(y);
      return;
    }
    y.state.calm = st.calm;
    const d = hyp(P.x - y.x, P.z - y.z);
    let tx = y.home.x + Math.sin(this.hour * 3 + y.id) * 2, tz = y.home.z + Math.cos(this.hour * 2) * 2;
    if (!st.calm && d < 7) { tx = P.x; tz = P.z; }
    const dd = hyp(tx - y.x, tz - y.z);
    if (dd > 0.05) { const s = Math.min(dd, (st.calm ? 1.2 : 2.4) * dt); y.x += (tx - y.x) / dd * s; y.z += (tz - y.z) / dd * s; }
    // a hungry onibi steals warmth on contact
    if (!st.calm && d < 0.9 && P.iframes <= 0) {
      P.iframes = 1.2;
      if (P.holder.q.h > 0) { P.holder.q.h -= 1; y.holder.q.h += 1; this.events.push({ type: 'stolen', k: 'h', e: y }); }
      this.events.push({ type: 'hurt' });
    }
  }

  updateHauls() {
    for (const job of [...this.haulJobs]) {
      if (!job.crewJob.delivered) continue;
      const item = job.item;
      if (job.to === 'yard') { this.yardEntity.store[item.haul] += 1; this.events.push({ type: 'stored', item: item.haul, e: this.yardEntity }); }
      else { this.siteEntity.site.deliver(item.haul); this.events.push({ type: 'delivered', item: item.haul, e: this.siteEntity }); }
      this.remove(item);
      this.haulJobs.splice(this.haulJobs.indexOf(job), 1);
    }
    // whenever the site wants something that is in the stockpile, a free crew member carries it over
    const site = this.siteEntity?.site, yard = this.yardEntity;
    if (!site || site.complete) return;
    for (const [m, n] of Object.entries(site.missing())) {
      const inFlight = this.haulJobs.filter(j => j.to === 'site' && j.item.haul === m).length;
      if (inFlight >= n || yard.store[m] <= 0 || !this.crew.members.some(c => c.state === 'follow')) continue;
      yard.store[m] -= 1;
      const item = this.add(m, yard.x + 0.6, yard.z, { q: { w: m === 'log' ? 2 : 1 } });
      this.sendHaul(item, this.siteEntity, 'site');
    }
  }

  sendHaul(item, dest, to) {
    const proxy = { get x() { return item.x; }, set x(v) { item.x = v; }, get z() { return item.z; }, set z(v) { item.z = v; }, get weight() { return item.holder.q.w; }, ref: item };
    const crewJob = this.crew.dispatch(proxy, dest);
    if (!crewJob) return null;
    if (!this.haulJobs.some(j => j.item === item)) this.haulJobs.push({ item, crewJob, to });
    return crewJob;
  }

  // ---------------------------------------------------------------- verbs

  /** 取 / 予 / 放 on the current target with quality k. */
  transfer(verb, k) {
    const P = this.player, t = this.target;
    let e;
    if (verb === 'release') e = this.L.release(P.holder, k, P.cap);
    else if (!t) return this.events.push({ type: 'refused', verb, k, reason: 'none' });
    else if (verb === 'take') e = this.L.take(P.holder, t.holder, k, P.cap);
    else e = this.L.give(P.holder, t.holder, k, P.cap);
    if (e && e.type === 'transfer') this.events.push({ type: 'fx', verb, k, from: verb === 'take' ? t : 'player', to: verb === 'take' ? 'player' : t, color: QUALITY_INFO[k].color });
    if (e && e.type === 'release') this.releaseBurst(k);
    if (t && t.kind === 'yokai' && stateOf(t.holder).calm && !t.state.calmAnnounced) { t.state.calmAnnounced = true; this.events.push({ type: 'calmed', e: t }); }
  }

  /** 放: the released unit acts on everything around her. */
  releaseBurst(k) {
    const P = this.player;
    this.events.push({ type: 'burst', k, x: P.x, z: P.z });
    for (const e of this.entities) {
      const d = hyp(e.x - P.x, e.z - P.z);
      if (d > 3) continue;
      if (k === 'w' && e.kind === 'yokai') { e.x += (e.x - P.x) / (d || 1) * 2; e.z += (e.z - P.z) / (d || 1) * 2; }
      if (k === 'h' && e.kind === 'weeds') e.state.burning = 4;
    }
  }

  /** E: the context action for the current target. Returns a short label of what happened. */
  context() {
    const P = this.player, t = this.target;
    if (P.carrying) {
      if (t && t.kind === 'yard' && P.carrying.haul) { this.yardEntity.store[P.carrying.haul] += 1; this.remove(P.carrying); P.carrying = null; this.events.push({ type: 'stored' }); return '放进资材堆'; }
      P.carrying.x = P.x + P.fx; P.carrying.z = P.z + P.fz; P.carrying = null; return '放下';
    }
    if (!t) return null;
    if (t.haul) {
      // she can lift what is light enough for her; taking its weight first makes it so
      if (t.holder.q.w <= 1) { P.carrying = t; return '背起'; }
      this.events.push({ type: 'refused', verb: 'lift', reason: 'heavy', e: t });
      return '太重了';
    }
    if (t.kind === 'plot') {
      const p = t.plot;
      if (p.ripe) { this.events.push({ type: 'harvest', crop: p.harvest() }); return '收获'; }
      if (!p.crop) { p.plant('cucumber'); p.watered = true; return '种下胡瓜'; }
      return p.check() ? '缺：' + p.check() : '正在长';
    }
    if (t.kind === 'shrine') {
      // return what she carries to its natural state (safe experimentation)
      const h = P.holder;
      for (const k of Object.keys(h.q)) while (h.q[k] !== h.base[k]) { if (h.q[k] > h.base[k]) { h.q[k] -= 1; this.L.air[k] += 1; } else { h.q[k] += 1; this.L.air[k] -= 1; } }
      this.events.push({ type: 'returned' });
      return '归还';
    }
    if (t.kind === 'yokai' && t.state.calm && !t.state.joined) {
      t.state.joined = true; this.pacified += 1;
      this.crew.add(t.x, t.z);
      this.remove(t);
      this.events.push({ type: 'joined' });
      return '邀请加入';
    }
    if (t.kind === 'bell') return t.holder.q.s > 0 ? '钟在响' : '没有声音';
    return null;
  }

  /** F: send the crew to haul the current target to the stockpile. */
  dispatch() {
    const t = this.target;
    if (!t || !t.haul) return null;
    const crewJob = this.sendHaul(t, this.yardEntity, 'yard');
    if (!crewJob) return '没有空闲的小伙伴';
    return this.crew.shortfall(crewJob) ? `还需要 ${this.crew.shortfall(crewJob)}` : '去搬';
  }

  recall() { this.crew.recall(); this.haulJobs = []; }

  drain() { const e = this.events; this.events = []; return e; }
}
