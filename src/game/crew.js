// Crew logic for the gray box: followers walk in a line along the exact path she walked
// (a small night parade, not a blob), and can be dispatched to haul a physical item to a
// stockpile. Hauling is visible by construction: carriers walk to the item, wait until
// enough of them are there, lift together and walk it home. Taking the item's weight
// (the 重 quality) lowers how many carriers it needs — the crew runs on the same verb.
// Pure logic on (x, z); species, names and art are not decided yet (see docs/decisions).

const dist = (ax, az, bx, bz) => Math.hypot(bx - ax, bz - az);

export const CREW_DEFAULTS = {
  spacing: 0.9,      // metres between followers in the line
  crumb: 0.25,       // breadcrumb spacing along her path
  speed: 3.4,        // follower walking speed (m/s)
  carrySpeed: 1.6,   // speed while carrying
  strength: 1,       // weight units one carrier can lift
  arrive: 0.35,      // how close counts as "arrived"
  route: null,       // optional pathfinder (x0, z0, x1, z1) => [{x, z}, ...] | null; straight lines without it
};

/** Carriers needed for an item of weight w (an item with no weight still needs one pair of hands). */
export function carriersNeeded(weight, strength = CREW_DEFAULTS.strength) {
  return Math.max(1, Math.ceil(weight / strength));
}

export class Crew {
  constructor(opt = {}) {
    this.opt = { ...CREW_DEFAULTS, ...opt };
    this.members = [];
    this.trail = [];     // her recent path, newest first: [{x, z}]
    this.jobs = [];
  }

  add(x, z) {
    const m = { x, z, state: 'follow', job: null, slot: 0 };
    this.members.push(m);
    return m;
  }

  /** Record her position; keeps enough path for the whole line. */
  lead(x, z) {
    const t = this.trail;
    if (!t.length || dist(t[0].x, t[0].z, x, z) >= this.opt.crumb) t.unshift({ x, z });
    const keep = Math.ceil((this.members.length + 2) * this.opt.spacing / this.opt.crumb) + 4;
    if (t.length > keep) t.length = keep;
  }

  /** The point `along` metres behind her on the recorded path. */
  pointBehind(along) {
    const t = this.trail;
    if (!t.length) return null;
    let acc = 0;
    for (let i = 1; i < t.length; i++) {
      const seg = dist(t[i - 1].x, t[i - 1].z, t[i].x, t[i].z);
      if (acc + seg >= along) {
        const f = (along - acc) / seg;
        return { x: t[i - 1].x + (t[i].x - t[i - 1].x) * f, z: t[i - 1].z + (t[i].z - t[i - 1].z) * f };
      }
      acc += seg;
    }
    return t[t.length - 1];
  }

  /**
   * Send followers to haul `item` ({x, z, weight, ref}) to `dest` ({x, z, ref, count}).
   * Takes the closest idle followers; returns the job, or null when nobody is free.
   */
  dispatch(item, dest) {
    const idle = this.members.filter(m => m.state === 'follow')
      .sort((a, b) => dist(a.x, a.z, item.x, item.z) - dist(b.x, b.z, item.x, item.z));
    const existing = this.jobs.find(j => j.item.ref === item.ref);
    if (existing) {
      // dispatching again at an item that is still short of hands sends more helpers
      if (existing.state !== 'gather') return existing;
      const more = idle.slice(0, this.shortfall(existing));
      more.forEach(m => { m.state = 'toItem'; m.job = existing; existing.carriers.push(m); });
      return existing;
    }
    if (!idle.length) return null;
    const need = carriersNeeded(item.weight, this.opt.strength);
    const job = { item, dest, carriers: idle.slice(0, need), state: 'gather', delivered: false };
    job.carriers.forEach((m, i) => { m.state = 'toItem'; m.job = job; m.slot = i; });
    this.jobs.push(job);
    return job;
  }

  /** How many more hands a job still needs (shown above the item: "还需要 N"). */
  shortfall(job) {
    return Math.max(0, carriersNeeded(job.item.weight, this.opt.strength) - job.carriers.length);
  }

  /** Everyone drops what they are doing and rejoins the line; carried items stay where they are. */
  recall() {
    for (const j of this.jobs) j.state = 'dropped';
    this.jobs = [];
    for (const m of this.members) { m.state = 'follow'; m.job = null; }
  }

  update(dt) {
    const o = this.opt;
    const step = (m, tx, tz, speed) => {
      const d = dist(m.x, m.z, tx, tz);
      if (d < 1e-6) return 0;
      const s = Math.min(d, speed * dt);
      m.x += (tx - m.x) / d * s; m.z += (tz - m.z) / d * s;
      return d - s;
    };
    // walk toward (tx, tz) along a route when a pathfinder is set; returns the distance still to go
    const go = (m, tx, tz, speed) => {
      if (!o.route || dist(m.x, m.z, tx, tz) < 1.2) { m.path = null; return step(m, tx, tz, speed); }
      if (!m.path || dist(m.goalX, m.goalZ, tx, tz) > 0.6) {
        m.path = o.route(m.x, m.z, tx, tz) || [{ x: tx, z: tz }];
        m.goalX = tx; m.goalZ = tz;
      }
      while (m.path.length > 1 && dist(m.x, m.z, m.path[0].x, m.path[0].z) < 0.25) m.path.shift();
      step(m, m.path[0].x, m.path[0].z, speed);
      return dist(m.x, m.z, tx, tz);
    };

    // followers in line, in the order they joined; one that has fallen far behind finds its way back
    let rank = 0;
    for (const m of this.members) {
      if (m.state !== 'follow') continue;
      rank += 1;
      const p = this.pointBehind(rank * o.spacing);
      if (p) (dist(m.x, m.z, p.x, p.z) > 2.5 ? go(m, p.x, p.z, o.speed * 1.3) : step(m, p.x, p.z, o.speed));
    }

    for (const job of [...this.jobs]) {
      const it = job.item;
      // ring positions around the item so carriers don't stack on one point
      const ring = (i, n) => ({ x: it.x + Math.cos(i / n * Math.PI * 2) * 0.45, z: it.z + Math.sin(i / n * Math.PI * 2) * 0.45 });
      if (job.state === 'gather') {
        let arrived = 0;
        job.carriers.forEach((m, i) => {
          const p = ring(i, job.carriers.length);
          if (go(m, p.x, p.z, o.speed) <= o.arrive) arrived += 1;
        });
        if (arrived === job.carriers.length && this.shortfall(job) === 0) {
          job.state = 'carry';
          for (const m of job.carriers) { m.state = 'carry'; m.path = null; }
        }
      } else if (job.state === 'carry') {
        const left = go(it, job.dest.x, job.dest.z, o.carrySpeed);
        job.carriers.forEach((m, i) => { const p = ring(i, job.carriers.length); m.x = p.x; m.z = p.z; });
        if (left <= o.arrive) {
          job.state = 'done'; job.delivered = true;
          job.dest.count = (job.dest.count || 0) + 1;
          for (const m of job.carriers) { m.state = 'follow'; m.job = null; }
          this.jobs.splice(this.jobs.indexOf(job), 1);
        }
      }
    }
  }
}
