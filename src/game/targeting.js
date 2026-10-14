// Interaction targeting: one target at a time, chosen by score, shown before any button is
// pressed, and stable — a challenger must win clearly and for a moment before the target
// switches. Never require pixel-perfect positioning (v0.1 did; see knowledge/05).
// Pure logic on plain {x, z} positions; the caller supplies candidates each frame.

export const DEFAULTS = {
  reach: 2.6,          // metres; candidates may override with their own reach
  coneDeg: 75,         // half-angle of the facing cone; things very close are allowed anyway
  closeEnough: 0.9,    // inside this distance the facing cone is ignored
  switchMargin: 0.6,   // a challenger must beat the current score by this much…
  dwell: 0.12,         // …for this many seconds before the target switches
  pickHold: 2.0,       // a touch-picked target stays chosen this long unless it leaves reach
};

/**
 * Score one candidate for an actor at (x, z) facing (fx, fz) (unit vector; use the stick
 * direction when the stick is held). Returns -Infinity when the candidate is not eligible.
 * Higher is better: type priority dominates, then facing, then distance.
 */
export function score(actor, c, opt = DEFAULTS) {
  const dx = c.x - actor.x, dz = c.z - actor.z;
  const d = Math.hypot(dx, dz);
  const reach = c.reach ?? opt.reach;
  if (d > reach) return -Infinity;
  const facing = d > 1e-4 ? (dx * actor.fx + dz * actor.fz) / d : 1;
  if (d > opt.closeEnough && facing < Math.cos(opt.coneDeg * Math.PI / 180)) return -Infinity;
  return (c.priority ?? 0) * 4 + facing * 1.5 - (d / reach) * 2;
}

export class Targeting {
  constructor(opt = {}) {
    this.opt = { ...DEFAULTS, ...opt };
    this.current = null;
    this.challenger = null;
    this.challengeT = 0;
    this.picked = null;
    this.pickT = 0;
  }

  /** candidates: [{ x, z, priority?, reach?, ref }]. Returns the chosen candidate or null. */
  update(dt, actor, candidates) {
    const scored = [];
    for (const c of candidates) {
      const s = score(actor, c, this.opt);
      if (s > -Infinity) scored.push({ c, s });
    }
    scored.sort((a, b) => b.s - a.s);
    this.ranked = scored.map(e => e.c);

    // An explicit pick (touch tap or cycling) holds while it stays within reach.
    if (this.picked) {
      const still = scored.find(e => e.c.ref === this.picked.ref);
      this.pickT -= dt;
      if (still && this.pickT > 0) return (this.current = still.c);
      this.picked = null;
    }

    if (!scored.length) { this.current = null; this.challenger = null; return null; }
    const best = scored[0];
    const cur = this.current && scored.find(e => e.c.ref === this.current.ref);
    if (!cur) { this.challenger = null; return (this.current = best.c); }
    if (best.c.ref === cur.c.ref || best.s < cur.s + this.opt.switchMargin) {
      this.challenger = null; this.challengeT = 0;
      return (this.current = cur.c);
    }
    if (!this.challenger || this.challenger.ref !== best.c.ref) { this.challenger = best.c; this.challengeT = 0; }
    this.challengeT += dt;
    if (this.challengeT >= this.opt.dwell) { this.challenger = null; return (this.current = best.c); }
    return (this.current = cur.c);
  }

  /** Cycle to the next eligible candidate (Tab / shoulder button). */
  cycle() {
    const list = this.ranked || [];
    if (list.length < 2) return this.current;
    const i = Math.max(0, list.findIndex(c => this.current && c.ref === this.current.ref));
    return this.pick(list[(i + 1) % list.length]);
  }

  /** Choose a candidate explicitly (touch tap on the object, or cycling). */
  pick(c) {
    this.picked = c; this.pickT = this.opt.pickHold; this.current = c;
    return c;
  }
}
