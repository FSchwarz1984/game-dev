// The playable field: her body, the things around her, the transfer verb and the context
// action, on a map supplied by the renderer side. Pure logic on (x, z) in metres; the
// presentation reads `entities`, `player`, `target` and the event queue.
//
// 遠化 in one rule: a thing is as far as the share of its natural qualities it has lost.
// Taking a quality from something pushes it away (it turns pale); giving the quality back
// brings it near again. A thing that lost everything (`deep`) cannot be reached at all:
// her hand passes through it, and it stays a step away however close she walks.

import { Ledger, makeHolder, bodyState, QUALITIES, QUALITY_INFO } from './qualities.js';
import { Targeting } from './targeting.js';

const hyp = Math.hypot;

/** How far a holder has gone: 0 near … 1 far, from the natural qualities it lacks. */
export function farness(e) {
  if (e.deep) return 1;
  const h = e.holder;
  let lost = 0, natural = 0;
  for (const k of QUALITIES) {
    if (h.base[k] <= 0) continue;
    natural += h.base[k];
    lost += Math.max(0, h.base[k] - h.q[k]);
  }
  return natural > 0 ? lost / natural : 0;
}

export class Field {
  /**
   * ground(x, z, fromX, fromZ) -> 'ground' | 'water' | 'wall' — the map's answer for a step;
   * without one the field is open ground (tests).
   */
  constructor({ ground = null } = {}) {
    this.L = new Ledger();
    this.ground = ground;
    this.entities = [];
    this.byId = new Map();
    this.events = [];
    this.zones = [];
    this.targeting = new Targeting();
    this.target = null;
    this.control = true;                   // false while a scene moves her
    this.verbs = { take: [], give: [], release: [] }; // qualities she may use with each verb
    this.player = {
      x: 0, z: 0, fx: 0, fz: 1, speed: 3.4, cap: 3, moving: false,
      holder: this.L.add(makeHolder({ material: 'body', amounts: { w: 2, h: 1, l: 0, s: 1, v: 3 } })),
    };
    this.L.on(e => this.events.push(e));
  }

  /**
   * def: { id, kind, name, x, z, r, solid, priority, q, base, max, sacred, deep, targetable,
   *        reach, ctx: { label: () => string, run: () => string|void } }
   * `q` is what it holds now; `base` its natural state (defaults to q).
   */
  add(def) {
    const e = {
      id: def.id ?? `e${this.entities.length + 1}`, kind: def.kind ?? 'thing', name: def.name ?? '',
      x: def.x ?? 0, z: def.z ?? 0, r: def.r ?? 0.5, solid: !!def.solid, priority: def.priority ?? 0,
      deep: !!def.deep, targetable: def.targetable !== false, hidden: false, reach: def.reach,
      ctx: def.ctx ?? null, far: 0, data: def.data ?? {},
      holder: this.L.add(makeHolder({ amounts: def.q, base: def.base, max: def.max, sacred: def.sacred, material: def.material ?? 'thing' })),
    };
    e.far = farness(e);
    this.entities.push(e);
    this.byId.set(e.id, e);
    return e;
  }

  get(id) { return this.byId.get(id); }

  remove(e) {
    this.entities = this.entities.filter(x => x !== e);
    this.byId.delete(e.id);
    this.L.holders.delete(e.holder); // its qualities leave the books with it (story props only)
    if (this.target === e) this.target = null;
  }

  /** A region the story listens to: { id, x0, x1, z0, z1 } or { id, x, z, r }; `block` turns her back. */
  zone(def) { const z = { inside: false, block: null, ...def }; this.zones.push(z); return z; }

  /** Let her use quality k with these verbs (the story unlocks them as they are taught). */
  allow(k, verbs = ['take', 'give']) { for (const v of verbs) if (!this.verbs[v].includes(k)) this.verbs[v].push(k); }

  setDeep(e, deep) { e.deep = deep; this.refresh(e); }

  // ---------------------------------------------------------------- per frame

  /** input: { mx, mz } world-axis movement (−1..1). */
  update(dt, input = { mx: 0, mz: 0 }) {
    const P = this.player;
    this.L.tick(dt);
    const wasMoving = P.moving;
    P.moving = false;
    if (this.control) {
      const len = hyp(input.mx, input.mz);
      if (len > 0.05) {
        const body = bodyState(P.holder);
        const speed = P.speed * (body.heavy ? 0.7 : 1) * (body.light ? 1.2 : 1) * Math.min(1, len);
        P.fx = input.mx / len; P.fz = input.mz / len;
        this.tryMove(P.x + P.fx * speed * dt, P.z + P.fz * speed * dt);
        P.moving = true;
        if (!wasMoving) this.events.push({ type: 'moved' });
      }
    }
    this.checkZones();
    for (const e of this.entities) this.refresh(e);

    const cands = [];
    for (const e of this.entities) {
      if (e.hidden || !e.targetable) continue;
      cands.push({ x: e.x, z: e.z, priority: e.priority, reach: e.reach ?? 1.6 + e.r, ref: e });
    }
    const t = this.control ? this.targeting.update(dt, P, cands) : null;
    const was = this.target;
    this.target = t ? t.ref : null;
    if (this.target && this.target !== was) this.events.push({ type: 'target', e: this.target });
  }

  refresh(e) {
    const f = farness(e);
    if (f !== e.far) {
      const was = e.far;
      e.far = f;
      if (f === 0 && was > 0) this.events.push({ type: 'near', e });
      if (f > 0 && was === 0) this.events.push({ type: 'far', e });
    }
  }

  /**
   * Move toward (nx, nz). Against a round thing she slides around it along its tangent;
   * against anything else, along whichever axis is free. Never snags on a curve.
   */
  tryMove(nx, nz) {
    const P = this.player;
    const hit = this.blocker(nx, nz);
    if (!hit) { P.x = nx; P.z = nz; return; }
    if (hit.e) {
      const ox = P.x - hit.e.x, oz = P.z - hit.e.z, od = hyp(ox, oz) || 1;
      const tx = -oz / od, tz = ox / od, along = (nx - P.x) * tx + (nz - P.z) * tz;
      const sx = P.x + tx * along, sz = P.z + tz * along;
      if (Math.abs(along) > 1e-5 && !this.blocker(sx, sz)) { P.x = sx; P.z = sz; return; }
    }
    if (!this.blocker(nx, P.z)) P.x = nx;
    else if (!this.blocker(P.x, nz)) P.z = nz;
  }

  canStand(x, z) { return !this.blocker(x, z); }

  /** What stops her stepping to (x, z): null, { e } for a thing, or { wall: true }. */
  blocker(x, z) {
    const P = this.player;
    if (this.ground) {
      const g = this.ground(x, z, P.x, P.z);
      if (g === 'wall') return { wall: true };
      if (g === 'water' && !bodyState(P.holder).light) return { wall: true };
    }
    for (const e of this.entities) {
      if (e.hidden) continue;
      // deep-far things keep a step away; solid things block; neither may trap her inside
      const r = e.deep ? e.r + 0.55 : e.solid ? e.r + 0.3 : 0;
      if (!r) continue;
      const d = hyp(x - e.x, z - e.z);
      if (d < r && d < hyp(P.x - e.x, P.z - e.z)) return { e };
    }
    for (const zn of this.zones) if (zn.block && inZone(zn, x, z) && !inZone(zn, P.x, P.z)) return { wall: true };
    return null;
  }

  checkZones() {
    const P = this.player;
    for (const zn of this.zones) {
      const now = inZone(zn, P.x, P.z);
      if (now && !zn.inside) this.events.push({ type: 'enter', zone: zn.id });
      if (!now && zn.inside) this.events.push({ type: 'leave', zone: zn.id });
      zn.inside = now;
      // a blocking zone she touches from outside: the story says why she turns back
      if (zn.block && !now && nearZone(zn, P.x, P.z, 0.25) && P.moving) {
        if (!zn.touched) this.events.push({ type: 'blocked', zone: zn.id, say: zn.block });
        zn.touched = true;
      } else if (!nearZone(zn, P.x, P.z, 1.2)) zn.touched = false;
    }
  }

  // ---------------------------------------------------------------- verbs

  /** 取 / 予 / 放 with quality k on the current target. Returns the ledger event (or a refusal). */
  transfer(verb, k) {
    const P = this.player, t = this.target;
    if (!this.control || !this.verbs[verb]?.includes(k)) return null; // not taught yet: the key is not shown
    let e;
    if (verb === 'release') e = this.L.release(P.holder, k, P.cap);
    else if (!t) e = this.push({ type: 'refused', verb, k, reason: 'none' });
    else if (t.deep) e = this.push({ type: 'refused', verb, k, reason: 'far', target: t.holder, e: t });
    else e = verb === 'take' ? this.L.take(P.holder, t.holder, k, P.cap) : this.L.give(P.holder, t.holder, k, P.cap);
    if (e?.type === 'transfer') {
      this.push({ type: 'fx', verb, k, e: t, color: QUALITY_INFO[k].color });
      this.refresh(t);
    }
    return e;
  }

  /** E: the target's context action. Returns what happened, as a short label. */
  context() {
    if (!this.control) return null;
    const t = this.target;
    if (!t?.ctx) return null;
    if (t.ctx.label && !t.ctx.label()) return null;
    return t.ctx.run() ?? null;
  }

  /** What E would do now, without doing it (shown on the context key and the prompt). */
  contextLabel() {
    const t = this.target;
    return t?.ctx?.label ? t.ctx.label() || '' : '';
  }

  /** Put her body back to its natural state (the shrine's safety net); the units go to the air. */
  restoreBody() {
    const h = this.player.holder;
    for (const k of QUALITIES) {
      const d = h.q[k] - h.base[k];
      h.q[k] = h.base[k];
      this.L.air[k] += d;
    }
    this.push({ type: 'returned' });
  }

  push(e) { this.events.push(e); return e; }
  drain() { const e = this.events; this.events = []; return e; }
}

function inZone(z, x, zz) {
  if (z.r !== undefined) return hyp(x - z.x, zz - z.z) < z.r;
  return x >= z.x0 && x <= z.x1 && zz >= z.z0 && zz <= z.z1;
}

function nearZone(z, x, zz, m) {
  if (z.r !== undefined) return hyp(x - z.x, zz - z.z) < z.r + m;
  return x >= z.x0 - m && x <= z.x1 + m && zz >= z.z0 - m && zz <= z.z1 + m;
}
