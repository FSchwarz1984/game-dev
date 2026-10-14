// 「移」 — the one verb: take, give, release. Five qualities that are moved, never created:
// a transfer moves one unit; anything that seems to appear comes from an explicit source
// (sun, fire, waterfall…) and anything that vanishes goes to the air (a ledger sink).
// Pure logic: no rendering, no DOM. The presentation layer reads events and derived state.

export const QUALITIES = ['w', 'h', 'l', 's', 'v'];

export const QUALITY_INFO = {
  w: { kanji: '重', key: 'weight', color: '#d9c7a6' },
  h: { kanji: '熱', key: 'heat', color: '#ff8a4a' },
  l: { kanji: '光', key: 'light', color: '#ffe08a' },
  s: { kanji: '音', key: 'sound', color: '#9fd0ff' },
  v: { kanji: '生', key: 'life', color: '#8fdc7a' },
};

const perQuality = (src, fallback) => Object.fromEntries(QUALITIES.map(k => [k, src?.[k] ?? fallback]));

/**
 * Quality state for anything that holds qualities: an object, a creature, or her body.
 * `base` is the holder's natural state (yokai return to it when pacified; her body measures
 * how far she has drifted from it). `sacred` marks things bound with a shimenawa: their
 * qualities cannot be moved in either direction.
 */
export function makeHolder({ amounts, base, min, max, sacred = false, material = 'thing', source = null } = {}) {
  const q = perQuality(amounts, 0);
  return {
    q,
    base: { ...q, ...(base || {}) },
    min: perQuality(min, 0),
    max: perQuality(max, 9),
    sacred,
    material,
    source, // { k, rate (units/s), cap, active?: () => boolean }
    regen: 0,
  };
}

/** How far a holder has drifted from its natural state, summed over all qualities. */
export function deviation(h) {
  let d = 0;
  for (const k of QUALITIES) d += Math.abs(h.q[k] - h.base[k]);
  return d;
}

export function deviationAfter(h, k, delta) {
  return deviation(h) - Math.abs(h.q[k] - h.base[k]) + Math.abs(h.q[k] + delta - h.base[k]);
}

// Why a transfer was refused; the UI turns each into a line of feedback (never fail silently).
export const REFUSAL = {
  sacred: 'sacred',     // bound by a shimenawa
  empty: 'empty',       // nothing left to take or give
  full: 'full',         // the receiver cannot hold more
  overload: 'overload', // her body would drift beyond what she can carry
};

export function canTake(actor, target, k, cap) {
  if (target.sacred) return REFUSAL.sacred;
  if (target.q[k] <= target.min[k]) return REFUSAL.empty;
  if (actor.q[k] + 1 > actor.max[k]) return REFUSAL.full;
  if (deviationAfter(actor, k, +1) > cap) return REFUSAL.overload;
  return null;
}

export function canGive(actor, target, k, cap) {
  if (target.sacred) return REFUSAL.sacred;
  if (actor.q[k] <= actor.min[k]) return REFUSAL.empty;
  if (target.q[k] + 1 > target.max[k]) return REFUSAL.full;
  if (deviationAfter(actor, k, -1) > cap) return REFUSAL.overload;
  return null;
}

export function canRelease(actor, k, cap) {
  if (actor.q[k] <= actor.min[k]) return REFUSAL.empty;
  if (deviationAfter(actor, k, -1) > cap) return REFUSAL.overload;
  return null;
}

/**
 * Keeps the books: every unit is in a holder, in the air, or came from a source.
 * total(k) = Σ holders + air − sourced stays constant; the tests rely on it.
 */
export class Ledger {
  constructor() {
    this.holders = new Set();
    this.air = perQuality(null, 0);
    this.sourced = perQuality(null, 0);
    this.listeners = [];
  }

  add(h) { this.holders.add(h); return h; }
  remove(h) { this.holders.delete(h); for (const k of QUALITIES) this.air[k] += h.q[k]; }
  on(fn) { this.listeners.push(fn); }
  emit(e) { for (const fn of this.listeners) fn(e); return e; }

  total(k) {
    let t = this.air[k] - this.sourced[k];
    for (const h of this.holders) t += h.q[k];
    return t;
  }

  take(actor, target, k, cap) {
    const reason = canTake(actor, target, k, cap);
    if (reason) return this.emit({ type: 'refused', verb: 'take', k, actor, target, reason });
    target.q[k] -= 1; actor.q[k] += 1;
    return this.emit({ type: 'transfer', verb: 'take', k, from: target, to: actor });
  }

  give(actor, target, k, cap) {
    const reason = canGive(actor, target, k, cap);
    if (reason) return this.emit({ type: 'refused', verb: 'give', k, actor, target, reason });
    actor.q[k] -= 1; target.q[k] += 1;
    return this.emit({ type: 'transfer', verb: 'give', k, from: actor, to: target });
  }

  /** 放: one unit leaves her body as a burst; the presentation layer applies the area effect. */
  release(actor, k, cap) {
    const reason = canRelease(actor, k, cap);
    if (reason) return this.emit({ type: 'refused', verb: 'release', k, actor, reason });
    actor.q[k] -= 1; this.air[k] += 1;
    return this.emit({ type: 'release', verb: 'release', k, from: actor });
  }

  /** Sources (sun, fire, waterfall…) refill toward their cap while active. */
  tick(dt) {
    for (const h of this.holders) {
      const s = h.source;
      if (!s || (s.active && !s.active()) || h.q[s.k] >= s.cap) { h.regen = 0; continue; }
      h.regen += s.rate * dt;
      while (h.regen >= 1 && h.q[s.k] < s.cap) {
        h.regen -= 1; h.q[s.k] += 1; this.sourced[s.k] += 1;
        this.emit({ type: 'source', k: s.k, holder: h });
      }
    }
  }
}

/** What her body does with what she carries (systems.md §1.2–1.3). */
export function bodyState(h) {
  const d = k => h.q[k] - h.base[k];
  return {
    heavy: d('w') > 0, light: d('w') < 0,
    hot: d('h') > 0, cold: d('h') < 0,
    glowing: d('l') > 0, shadowed: d('l') < 0,
    loud: d('s') > 0, silent: d('s') < 0,
    lively: d('v') > 0, faint: d('v') < 0,
  };
}

/**
 * The chemistry table: derived state per material class. Things never change each other
 * directly; only their qualities change, and the state follows. Thresholds are first-pass
 * values for the gray box and will be tuned in playtests.
 */
export const MATERIALS = {
  thing: () => ({}),
  stone: h => ({ floats: h.q.w <= 0, anchored: h.q.w >= 3 }),
  wood: h => ({ floats: h.q.w <= 1, burning: h.q.h >= 3, sprouting: h.q.v >= 2 }),
  water: h => ({ frozen: h.q.h <= 0, steaming: h.q.h >= 3, silent: h.q.s <= 0 }),
  plant: h => ({ stage: Math.max(0, Math.min(4, h.q.v)), withered: h.q.v <= 0, burning: h.q.h >= 3 }),
  bell: h => ({ ringing: h.q.s >= 1 }),
  lantern: h => ({ lit: h.q.l >= 1, glow: h.q.l }),
  // A hungry yokai is spawned off its natural state; it calms once every quality except
  // life is back at base. Taking all of its life kills it — the same verb, the player's choice.
  yokai: h => ({ dead: h.q.v <= 0, calm: h.q.v > 0 && QUALITIES.every(k => k === 'v' || h.q[k] === h.base[k]) }),
  body: h => bodyState(h),
};

export function stateOf(h) {
  return (MATERIALS[h.material] || MATERIALS.thing)(h);
}
