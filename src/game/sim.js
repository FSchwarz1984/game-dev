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
const inRect = (r, x, z) => x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1;

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

/** The flat default arena (tests). Positions are [x, z] in metres. */
export const ARENA = {
  spawn: [0, 0], shrine: [0, -3],
  rock: [-7, 2], plate: [-10, 6], gate: [-10, 10], bridge: [-4, 9], ditch: { x0: -9, x1: 1, z0: 8.4, z1: 9.6 },
  pond: [8, 6], pondR: 3.2, brazier: [4, 2], lantern: [12, -2], bell: [-12, -4], falls: [14, 10], weeds: [-3, -8],
  plot: [3, -9], yard: [-8, -10], site: [-13, -12],
  logs: [[6, -6], [7.4, -6], [8.8, -6]], stones: [[9, -8], [9, -9.2]],
  yokai: [-1, -12], crew: [[-1, 1], [-2, 1], [-3, 1]],
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
    this.ground = null; // optional terrain hook (x, z, fromX, fromZ) => 'ground' | 'water' | 'wall'
    this.player = {
      x: 0, z: 0, fx: 0, fz: 1, speed: 4.2, cap: 3, iframes: 0, carrying: null, lastLand: [0, 0],
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

  /**
   * Build the gray-box arena: one station per quality, plus crew, building, farm and a yokai.
   * layout: positions in metres; the render layer passes one fitted to its terrain, the tests use
   * the flat default.
   */
  static arena(layout = ARENA) {
    const A = { ...ARENA, ...layout };
    const s = new Sim();
    const isDay = () => s.isDay;
    const at = (kind, [x, z], opt = {}) => s.add(kind, x, z, { r: A.radius?.[kind], name: A.names?.[kind], ...opt });
    [s.player.x, s.player.z] = A.spawn;
    s.player.lastLand = [...A.spawn];
    at('shrine', A.shrine);
    // 重: a boulder, a pressure plate that opens a gate, a rotten plank bridge over a ditch
    at('rock', A.rock, { q: { w: 3 } });
    at('plate', A.plate, { q: { w: 0 } });
    s.gateEntity = at('gate', A.gate, { r: A.gateR });
    if (A.gateRect) s.gateEntity.rect = A.gateRect;
    s.bridgeEntity = at('bridge', A.bridge, { q: { w: 1 } });
    if (A.bridgeRect) s.bridgeEntity.rect = A.bridgeRect;
    if (A.ditch) s.blocks.push({ ...A.ditch, bridge: s.bridgeEntity });
    // 熱: a pond to freeze, a brazier that refills its heat
    at('pond', A.pond, { q: { h: 1 }, r: A.pondR });
    at('brazier', A.brazier, { q: { h: 3 }, source: { k: 'h', rate: 0.5, cap: 3 } });
    // 光: a lantern fed by daylight
    at('lantern', A.lantern, { q: { l: 1 }, source: { k: 'l', rate: 0.4, cap: 3, active: isDay } });
    // 音: a bell and a waterfall
    at('bell', A.bell, { q: { s: 0 } });
    at('falls', A.falls, { q: { s: 3 }, source: { k: 's', rate: 0.3, cap: 3 } });
    // 生: weeds that keep growing
    at('weeds', A.weeds, { q: { v: 2 }, source: { k: 'v', rate: 0.1, cap: 3 } });
    // farm, building, logistics
    s.plotEntity = at('plot', A.plot);
    s.plotEntity.plot = new Plot({ amounts: { l: 1, h: 1 } });
    s.L.holders.delete(s.plotEntity.holder);
    s.plotEntity.holder = s.L.add(s.plotEntity.plot.holder);
    s.yardEntity = at('yard', A.yard);
    s.yardEntity.store = { log: 0, stone: 0 };
    s.siteEntity = at('site', A.site);
    s.siteEntity.site = new Site({ clear: { work: 2 }, stones: { needs: { stone: 2 }, work: 3 }, pillars: { needs: { log: 2 }, work: 3 }, beam: { needs: { log: 1 }, work: 3 } });
    for (const p of A.logs) at('log', p, { q: { w: 2 } });
    for (const p of A.stones) at('stone', p, { q: { w: 1 } });
    // a hungry onibi: too much heat, wanders near the weeds
    at('yokai', A.yokai, { q: { h: 4, v: 2 }, base: { h: 1 }, extra: { home: { x: A.yokai[0], z: A.yokai[1] } } });
    for (const [x, z] of A.crew) s.crew.add(x, z);
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
    P.dodgeCd = Math.max(0, (P.dodgeCd || 0) - dt);
    if (P.dash) {
      const k = Math.min(dt, P.dash.t);
      this.tryMove(P.x + P.dash.vx * k, P.z + P.dash.vz * k);
      P.dash.t -= dt;
      if (P.dash.t <= 0) P.dash = null;
    }
    this.crew.lead(P.x, P.z);

    this.updateWorld(dt);
    this.crew.update(dt);
    this.updateHauls();

    // the target, shown before any button is pressed
    const cands = this.entities.filter(e => !e.dead && e !== P.carrying).map(e => ({ x: e.x, z: e.z, priority: e.priority, reach: 1.6 + e.r, ref: e }));
    const t = this.targeting.update(dt, P, cands);
    this.target = t ? t.ref : null;
  }

  /** Move toward (nx, nz), sliding along whatever blocks one axis (no snagging on corners). */
  tryMove(nx, nz) {
    const P = this.player;
    if (this.canStand(nx, nz)) { P.x = nx; P.z = nz; }
    else if (this.canStand(nx, P.z)) P.x = nx;
    else if (this.canStand(P.x, nz)) P.z = nz;
    // the rotten bridge gives way under a heavy body, and she drops back to the bank she came from
    const br = this.bridgeEntity;
    if (br && !br.state.broken && this.onBridge(P.x, P.z) && P.holder.q.w > 2) {
      br.state.broken = true;
      this.events.push({ type: 'broke', e: br });
      if (this.ground) { this.events.push({ type: 'fell', x: P.x, z: P.z }); [P.x, P.z] = P.lastLand; }
    }
    if (!this.ground || this.ground(P.x, P.z, P.x, P.z) === 'ground') P.lastLand = [P.x, P.z];
  }

  /** Can her body stand at (x, z)? Terrain (via the optional ground hook) and the stations. */
  canStand(x, z) {
    const P = this.player, body = bodyState(P.holder);
    let water = false;
    if (this.ground) {
      const g = this.ground(x, z, P.x, P.z);
      if (g === 'wall') return false;
      water = g === 'water';
    }
    for (const e of this.entities) {
      const d = hyp(x - e.x, z - e.z);
      if (e.solid && d < e.r + 0.35 && d < hyp(P.x - e.x, P.z - e.z)) return false;  // never trap her inside
      // a pond: ice where it is frozen; without terrain the circle itself is the water
      if (e.kind === 'pond' && d < e.r) { if (stateOf(e.holder).frozen) water = false; else if (!this.ground) water = true; }
      if (e.kind === 'gate' && !e.state.open && (e.rect ? inRect(e.rect, x, z) : d < e.r)) return false;
    }
    if (water && this.onBridge(x, z)) water = false;
    if (water && !body.light) return false;   // light enough, she skims over water
    for (const b of this.blocks) {
      if (x < b.x0 || x > b.x1 || z < b.z0 || z > b.z1) continue;
      if (!this.onBridge(x, z)) return false;
    }
    return true;
  }

  /** On the unbroken rotten bridge (a rectangle when the layout gives one, else its circle)? */
  onBridge(x, z) {
    const b = this.bridgeEntity;
    if (!b || b.state.broken) return false;
    return b.rect ? inRect(b.rect, x, z) : hyp(x - b.x, z - b.z) < b.r;
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
      this.crew.add(t.x, t.z).kind = 'onibi';
      this.remove(t);
      this.events.push({ type: 'joined' });
      return '邀请加入';
    }
    if (t.kind === 'bell') return t.holder.q.s > 0 ? '钟在响' : '没有声音';
    return null;
  }

  /** What E would do right now, without doing it (shown on the context button and the prompt). */
  contextLabel() {
    const P = this.player, t = this.target;
    if (P.carrying) return t && t.kind === 'yard' && P.carrying.haul ? '放进资材堆' : '放下';
    if (!t) return '';
    if (t.haul) return t.holder.q.w <= 1 ? '背起' : '太重了';
    if (t.kind === 'plot') return t.plot.ripe ? '收获' : !t.plot.crop ? '种下胡瓜' : '';
    if (t.kind === 'shrine') return '归还';
    if (t.kind === 'yokai' && t.state.calm && !t.state.joined) return '邀请加入';
    return '';
  }

  /** A short dash along her facing, with a moment of invulnerability. */
  dodge() {
    const P = this.player;
    if (P.dodgeCd > 0 || P.dash) return false;
    const speed = bodyState(P.holder).heavy ? 7 : 11;
    P.dash = { t: 0.2, vx: P.fx * speed, vz: P.fz * speed };
    P.iframes = Math.max(P.iframes, 0.35);
    P.dodgeCd = 0.6;
    this.events.push({ type: 'dodge' });
    return true;
  }

  /** Dynamic obstacles for crew routes: a shut gate and solid stations. */
  navBlocked(x, z) {
    for (const e of this.entities) {
      if (e.kind === 'gate' && !e.state.open && (e.rect ? inRect(e.rect, x, z) : hyp(x - e.x, z - e.z) < e.r)) return true;
      if (e.solid && hyp(x - e.x, z - e.z) < e.r + 0.2) return true;
    }
    return false;
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
