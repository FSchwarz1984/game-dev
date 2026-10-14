// The director: async helpers for cutscenes, after v0.1's CINE. Every wait runs on the game
// clock, which the main loop advances with tick(dt); a paused game pauses the scene, and the
// tests drive it without a browser. The renderer, the actors and the sound are reached only
// through the `stage` adapter, so the same scene script runs on any renderer:
//
//   stage.shot(name, { cut, speed })    frame a named camera shot from the map
//   stage.cam(x, z, { cut, speed, y })  frame a point (metres; y lifts the view, e.g. up a tree)
//   stage.follow({ speed })             give the camera back to the player (speed: how tightly it
//                                       follows; lower is a slower, lagging crane)
//   stage.tod(hour)                     time of day
//   stage.actor(id)                     { x, z, face, play(anim, opts) -> seconds, idle() }
//
// Lines, cards and fades go to the StoryUI (src/story/ui.js); music and effects to the audio
// engine (src/audio/audio.js).

const clamp01 = v => Math.max(0, Math.min(1, v));
const smooth = k => k * k * (3 - 2 * k);

export class Director {
  constructor({ ui = null, stage = null, audio = null } = {}) {
    this.ui = ui;
    this.stage = stage;
    this.audio = audio;
    this.t = 0;
    this.rate = 1;          // > 1 while the player holds the skip key
    this.timers = [];       // { at, resolve }
    this.watches = [];      // { fn, resolve }
    this.running = 0;       // scenes in progress
  }

  /** Advance the scene clock; called once per frame by the main loop. */
  tick(dt) {
    this.t += dt * this.rate;
    if (this.timers.length) {
      const due = this.timers.filter(w => w.at <= this.t);
      if (due.length) { this.timers = this.timers.filter(w => w.at > this.t); for (const w of due) w.resolve(); }
    }
    if (this.watches.length) {
      const done = [];
      for (const w of this.watches) { let ok = false; try { ok = w.fn(dt); } catch (e) { ok = true; console.error(e); } if (ok) done.push(w); }
      if (done.length) { this.watches = this.watches.filter(w => !done.includes(w)); for (const w of done) w.resolve(); }
    }
  }

  /** Drop every pending wait (back to the title): the scenes waiting on them never resume. */
  reset() { this.timers = []; this.watches = []; this.running = 0; this.rate = 1; }

  get busy() { return this.running > 0; }

  /** Run a scene; `busy` is true until it ends. */
  async scene(fn) {
    this.running += 1;
    try { return await fn(this); } finally { this.running = Math.max(0, this.running - 1); }
  }

  wait(s) { return new Promise(resolve => this.timers.push({ at: this.t + Math.max(0, s), resolve })); }

  /** Resolve when fn(dt) is true; it is polled once per frame. */
  until(fn) { return new Promise(resolve => { if (fn(0)) resolve(); else this.watches.push({ fn, resolve }); }); }

  /** Run fn(k) for k from 0 to 1 over `dur` seconds (smoothed unless ease is false). */
  tween(dur, fn, { ease = true } = {}) {
    const t0 = this.t;
    return this.until(() => {
      const k = clamp01((this.t - t0) / Math.max(1e-6, dur));
      fn(ease ? smooth(k) : k);
      return k >= 1;
    });
  }

  // ---------------------------------------------------------------- camera and world

  shot(name, opts) { this.stage?.shot(name, opts); }
  cam(x, z, opts) { this.stage?.cam(x, z, opts); }
  follow(opts) { this.stage?.follow(opts); }
  tod(hour) { this.stage?.tod(hour); }

  /** Run the clock from hour a to b over dur seconds. */
  timelapse(a, b, dur) { return this.tween(dur, k => this.tod(a + (b - a) * k)); }

  // ---------------------------------------------------------------- actors

  actor(id) { return this.stage?.actor(id); }

  /**
   * Walk an actor through points [[x, z], ...] at `speed` m/s; resolves on arrival.
   * The actor faces its direction of travel and plays its walk loop meanwhile.
   */
  move(id, points, { speed = 2.2, anim = 'walk' } = {}) {
    const a = this.actor(id);
    if (!a || !points.length) return Promise.resolve();
    const path = points.map(p => [p[0], p[1]]);
    let i = 0;
    a.play?.(anim, { loop: true });
    return this.until(dt => {
      let step = speed * dt * this.rate;
      while (step > 0 && i < path.length) {
        const [tx, tz] = path[i], dx = tx - a.x, dz = tz - a.z, d = Math.hypot(dx, dz);
        if (d > 1e-4) a.face = faceOf(dx, dz);
        if (d <= step) { a.x = tx; a.z = tz; step -= d; i += 1; }
        else { a.x += dx / d * step; a.z += dz / d * step; step = 0; }
      }
      if (i >= path.length) { a.idle?.(); return true; }
      return false;
    });
  }

  face(id, dir) { const a = this.actor(id); if (a) a.face = dir; }

  /** Play a one-shot animation and resolve when it ends (or after `hold` seconds for loops). */
  async play(id, anim, { hold = 0, loop = false } = {}) {
    const a = this.actor(id);
    if (!a) return;
    const dur = a.play?.(anim, { loop }) ?? 0;
    await this.wait(loop ? hold : Math.max(dur, hold));
  }

  // ---------------------------------------------------------------- screen and sound

  say(...lines) { return this.ui ? this.ui.say(lines.flat()) : Promise.resolve(); }
  card(head, sub, dur) { return this.ui?.card(head, sub, dur); }
  title(head, sub, dur) { return this.ui?.title(head, sub, dur); }
  sub(text, dur) { return this.ui?.sub(text, dur); }
  fade(a, dur, color) { return this.ui?.fade(a, dur, color); }
  letterbox(on) { return this.ui?.letterbox(on); }
  music(name, opts) { this.audio?.music?.(name, opts); }
  sfx(name, opts) { return this.audio?.sfx?.(name, opts); }
}

/** Facing from a direction of travel in the 3/4 view: 'front' (south), 'back', 'left', 'right'. */
export function faceOf(dx, dz) {
  if (Math.abs(dx) > Math.abs(dz) * 1.15) return dx < 0 ? 'left' : 'right';
  return dz < 0 ? 'back' : 'front';
}
