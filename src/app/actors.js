// The characters on stage: which sheet, animation, view and frame each one shows, from what
// the field and the scenes ask of them. Renderer-independent: draw() returns plain sprite
// records (sheet images, source rect, foot position in metres, mirror, anchors) that the
// stage hands to the 2D renderer. Sprite data: src/art/characters.js (tools/art/build.py).
//
//   actor.play(anim, { loop }) -> seconds     a one-shot (or held loop) chosen by a scene
//   actor.pose = 'sleep' | 'pinned' | ...     a held pose that overrides everything else
//   actor.variant = 'load' | 'plain' | 'frame' (Tsuzumi: with the load, without, with the old frame)
//   actor.follow = 'tsuzumi'                   Saji walks after her
//   actor.ride = 'tsuzumi'                     Saji sits on the frame (drawn at its loadTop)
//   actor.climbTo = [x, z, heightM]            Tsuzumi up the camphor, hold by hold

import { CHARACTERS, frameAt, duration, riderOrder } from '../art/characters.js';

const DIR = { front: 'down', back: 'up', left: 'left', right: 'right' };

// The scenes' names for things → the sprite sheet's names, per character.
const ALIAS = {
  tsuzumi: { heavy: 'heavyIdle', sleep: 'asleep', unshoulder: 'shoulder', sit: 'sitBranch', stand: 'idle' },
  saji: { bell: 'bellStand', talk: 'sitTalk', point: 'pointStand', lookBack: 'lookBack' },
};
// Animations that only exist without the load: she has set it down for them.
const PLAIN_ONLY = new Set(['strain', 'asleep', 'sitUp', 'sit']);

export class Actor {
  constructor(id, body = null) {
    this.id = id;
    this.char = CHARACTERS[id];
    this.body = body || { x: 0, z: 0 };   // Tsuzumi's body is the field's player
    this.face = 'front';
    this.visible = true;
    this.variant = id === 'tsuzumi' ? 'load' : 'main';
    this.pose = null;
    this.one = null;          // { anim, t, loop, reverse }
    this.t = 0;               // time in the current loop
    this.loopAnim = 'idle';
    this.follow = null;
    this.ride = null;
    this.climbTo = null;
    this.lift = 0;            // metres above the ground (climbing, hopping)
    this.moving = false;
    this.heavy = false;
    this.lastX = this.body.x; this.lastZ = this.body.z;
  }

  get x() { return this.body.x; } set x(v) { this.body.x = v; }
  get z() { return this.body.z; } set z(v) { this.body.z = v; }

  sheet(anim) {
    if (this.id !== 'tsuzumi') return 'main';
    const meta = this.char.anims[anim];
    if (PLAIN_ONLY.has(anim)) return 'plain';
    let s = this.variant === 'none' ? 'plain' : this.variant;
    if (meta && !meta.sheets.includes(s)) s = meta.sheets.includes('plain') ? 'plain' : meta.sheets[0];
    return s;
  }

  name(anim) { return ALIAS[this.id]?.[anim] || anim; }

  /** Start a one-shot (or a held loop); returns its length in seconds. */
  play(anim, { loop = false } = {}) {
    const a = this.name(anim);
    if (!this.char.anims[a]) { this.one = null; return 0; }
    if (a === 'walk' && loop) { this.one = null; this.loopAnim = 'walk'; this.scripted = true; return 0; }
    this.one = { anim: a, t: 0, loop, reverse: anim === 'unshoulder' };
    return loop ? 0 : duration(this.char, a, this.sheet(a), DIR[this.face]);
  }

  /** Back to standing (the director calls this when a scripted walk ends). */
  idle() { this.one = null; this.scripted = false; this.loopAnim = 'idle'; }

  update(dt, stage) {
    // where she is going, if a scene or Saji's own legs move her
    if (this.ride) { this.moving = false; }
    else if (this.follow && !this.one && !this.pose) this.followStep(dt, stage);
    const dx = this.x - this.lastX, dz = this.z - this.lastZ, moved = Math.hypot(dx, dz);
    if (moved > 1e-4 && !this.ride) {
      if (!this.pose && !this.one) this.face = faceOf(dx, dz, this.face);
      this.moving = true;
    } else if (!this.scripted) this.moving = false;
    this.lastX = this.x; this.lastZ = this.z;
    if (this.one) {
      this.one.t += dt;
      const meta = this.char.anims[this.one.anim];
      const len = duration(this.char, this.one.anim, this.sheet(this.one.anim), DIR[this.face]);
      if (!meta?.loop && !this.one.loop && this.one.t > len + 0.25) this.one = null; // hold the last frame a beat
    }
    this.t += dt;
    const want = this.moving ? 'walk' : this.heavy ? 'heavyIdle' : 'idle';
    if (want !== this.loopAnim) { this.loopAnim = want; this.t = 0; }
    // the climb: rise toward the next hold
    if (this.climbTo) {
      const [tx, tz, ty] = this.climbTo, k = Math.min(1, dt * 3);
      this.x += (tx - this.x) * k; this.z += (tz - this.z) * k; this.lift += (ty - this.lift) * k;
      this.lastX = this.x; this.lastZ = this.z;
    } else if (this.lift > 0 && !this.ride) this.lift = Math.max(0, this.lift - dt * 4);
  }

  followStep(dt, stage) {
    const lead = stage.actor(this.follow);
    // a little behind and to the side of her, never in front of the camera's view of her
    const bx = lead.x - (lead.face === 'left' ? -1.1 : lead.face === 'right' ? 1.1 : 0.7);
    const bz = lead.z - (lead.face === 'back' ? -1.0 : lead.face === 'front' ? 1.0 : 0.3);
    const dx = bx - this.x, dz = bz - this.z, d = Math.hypot(dx, dz);
    if (d < 0.5) return;
    const sp = Math.min(d, (d > 3 ? 4.6 : 3.2) * dt);
    this.x += dx / d * sp; this.z += dz / d * sp;
  }

  /** The sprite record for this frame, or null when hidden. */
  draw(stage) {
    if (!this.visible) return null;
    let anim, t, reverse = false;
    if (this.pose) { anim = this.name(this.pose); t = this.t; }
    else if (this.one) { anim = this.one.anim; t = this.one.t; reverse = this.one.reverse; }
    else if (this.ride) { anim = 'sit'; t = this.t; }
    else { anim = this.loopAnim; t = this.t; }
    const sheet = this.sheet(anim);
    // someone riding on her frame: from the front, cells without the post tips (they would stripe Saji)
    const carrying = this.id === 'tsuzumi' && stage.actor('saji')?.ride === 'tsuzumi' && stage.actor('saji').visible;
    const opts = carrying ? { rider: true } : {};
    let f = frameAt(this.char, sheet, anim, DIR[this.face], t, opts);
    if (!f) f = frameAt(this.char, sheet, 'idle', DIR[this.face], this.t, opts);
    if (!f) return null;
    if (reverse) f = frameAt(this.char, sheet, anim, DIR[this.face], (f.count - 1 - f.index) / (this.char.anims[anim]?.fps || 8), opts);
    let x = this.x, z = this.z, up = this.lift * 20;   // up: native pixels above the ground point
    if (this.ride) {
      // seated on Tsuzumi's frame: her loadTop, minus Saji's own seat point
      const lead = stage.actor(this.ride), lf = lead.lastFrame;
      if (lf?.anchors.loadTop) {
        const seat = f.anchors.seat || { x: 0, y: 0 };
        x = lead.x + (lf.anchors.loadTop.x - seat.x) / 20;
        // seen from the front or side she sits behind the hat (drawn first); from the back, over it
        z = lead.z + (riderOrder(lead.char, lf) === 'behind' ? -0.02 : 0.02);
        up = lead.lift * 20 - (lf.anchors.loadTop.y - seat.y);
        this.face = lead.face;
      }
    }
    this.lastFrame = f;
    return { id: this.id, ...f, pivot: this.char.pivot, x, z, up, character: true };
  }
}

/** Facing from a direction of travel in the 3/4 view, with a little hysteresis. */
export function faceOf(dx, dz, prev = 'front') {
  const ax = Math.abs(dx), az = Math.abs(dz);
  const side = prev === 'left' || prev === 'right';
  if (ax > az * (side ? 0.8 : 1.25)) return dx < 0 ? 'left' : 'right';
  return dz < 0 ? 'back' : 'front';
}
