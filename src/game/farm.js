// Farm plots (systems.md §4, approved G1-10): a crop's growing conditions are qualities.
// The plot is a quality holder; light, heat and life on it are what the crop feeds on.
// Giving 生 to a planted plot moves the crop on by a stage at once (the verb is the farming
// system, not a tool used on the farm). Pure logic; growth is measured in game hours.

import { makeHolder } from './qualities.js';

/** First-pass crop table for the gray box; numbers will be tuned in playtests. */
export const CROPS = {
  cucumber: { label: '胡瓜', stages: 4, hours: 6, needs: { l: 1 }, water: true },
  eggplant: { label: '茄子', stages: 4, hours: 7, needs: { h: 2 }, water: true },
  hozuki: { label: '鬼灯', stages: 3, hours: 5, needs: { l: 1 }, water: false, storesLight: true },
  soba: { label: '蕎麦', stages: 3, hours: 4, needs: {}, water: false },
  myoga: { label: '茗荷', stages: 3, hours: 6, needs: {}, shade: true, water: true },
  wasabi: { label: '山葵', stages: 4, hours: 10, needs: {}, cold: true, water: true },
};

export class Plot {
  constructor({ amounts } = {}) {
    this.holder = makeHolder({ material: 'soil', amounts: { l: 1, h: 1, v: 0, ...(amounts || {}) }, max: { v: 4 } });
    this.crop = null;
    this.stage = 0;
    this.hours = 0;
    this.watered = false;
    this.why = null; // the condition currently missing, for feedback ("太暗了" etc.)
  }

  plant(kind) {
    if (this.crop || !CROPS[kind]) return false;
    this.crop = kind; this.stage = 0; this.hours = 0;
    return true;
  }

  get ripe() { return !!this.crop && this.stage >= CROPS[this.crop].stages; }

  /** Which condition is missing right now, or null when the crop can grow. */
  check() {
    if (!this.crop || this.ripe) return null;
    const c = CROPS[this.crop], q = this.holder.q;
    for (const [k, n] of Object.entries(c.needs)) if (q[k] < n) return k;
    if (c.water && !this.watered) return 'water';
    if (c.shade && q.l > 0) return 'shade';
    if (c.cold && q.h > 0) return 'cold';
    return null;
  }

  /** Advance by game hours (not real seconds). */
  tick(hours) {
    if (!this.crop || this.ripe) return;
    this.why = this.check();
    if (this.why) return;
    this.hours += hours;
    const per = CROPS[this.crop].hours / CROPS[this.crop].stages;
    while (this.hours >= per && !this.ripe) { this.hours -= per; this.stage += 1; }
  }

  /** Life given to the plot is taken up by the crop as a whole stage. */
  absorbLife() {
    let grew = 0;
    while (this.crop && !this.ripe && this.holder.q.v > 0) { this.holder.q.v -= 1; this.stage += 1; grew += 1; }
    return grew;
  }

  harvest() {
    if (!this.ripe) return null;
    const kind = this.crop;
    this.crop = null; this.stage = 0; this.hours = 0; this.watered = false;
    return kind;
  }
}
