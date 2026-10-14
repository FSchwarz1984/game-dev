// Construction sites (systems.md §3, approved G1-9): a building rises in seven visible
// stages. Each stage needs physical materials delivered to the site (by her or the crew)
// and then work time from the crew on site. Nothing is spent from an abstract inventory.
// Pure logic; the presentation layer shows the stockpile and the stage geometry.

export const STAGES = [
  { id: 'clear', label: '清地' },
  { id: 'stones', label: '础石' },
  { id: 'pillars', label: '立柱' },
  { id: 'beam', label: '上梁' },    // completing this stage triggers the roof-raising ceremony
  { id: 'walls', label: '墙' },
  { id: 'roof', label: '屋顶' },
  { id: 'finish', label: '装修' },
];

/**
 * plan: { [stageId]: { needs: { [material]: count }, work: seconds of crew labour } }
 * Stages missing from the plan are skipped (a shed has no beam ceremony).
 */
export class Site {
  constructor(plan) {
    this.stages = STAGES.filter(s => plan[s.id]).map(s => ({ ...s, needs: { ...(plan[s.id].needs || {}) }, work: plan[s.id].work ?? 4, got: {}, done: 0 }));
    this.index = 0;
    this.events = [];
  }

  get stage() { return this.stages[this.index] || null; }
  get complete() { return this.index >= this.stages.length; }

  /** Materials still missing for the current stage, e.g. { log: 2 } (shown over the site). */
  missing() {
    const s = this.stage;
    if (!s) return {};
    const out = {};
    for (const [m, n] of Object.entries(s.needs)) if ((s.got[m] || 0) < n) out[m] = n - (s.got[m] || 0);
    return out;
  }

  /** Does the current stage still want this material? (crew and player check before hauling) */
  wants(material) { return (this.missing()[material] || 0) > 0; }

  /** A physical item arrives at the site. Returns false when it is not needed right now. */
  deliver(material) {
    if (!this.wants(material)) return false;
    const s = this.stage;
    s.got[material] = (s.got[material] || 0) + 1;
    this.events.push({ type: 'delivered', stage: s.id, material });
    return true;
  }

  /** Crew labour; only counts once every material for the stage is on site. */
  work(dt, workers) {
    const s = this.stage;
    if (!s || workers <= 0 || Object.keys(this.missing()).length) return;
    s.done += dt * workers;
    if (s.done >= s.work) {
      this.events.push({ type: 'stage', stage: s.id });
      if (s.id === 'beam') this.events.push({ type: 'ceremony' });
      this.index += 1;
      if (this.complete) this.events.push({ type: 'complete' });
    }
  }

  /** 0..1 progress of the current stage's labour (for the scaffold animation). */
  get labour() { const s = this.stage; return s ? Math.min(1, s.done / s.work) : 1; }

  drain() { const e = this.events; this.events = []; return e; }
}
