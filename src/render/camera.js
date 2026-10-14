// HD-2D camera rig: narrow-FOV perspective at a fixed pitch, critically damped follow with a
// little look-ahead, yaw in 90-degree steps with an eased turn, zoom presets and trauma shake.

import * as THREE from 'three';
import { springTo, easeInOutCubic, lerp } from '../core/math.js';

const DEG = Math.PI / 180;

/** distance: metres from the focus point; pitch: degrees down (null = the rig's pitch). */
export const ZOOMS = {
  gameplay: { distance: 26, pitch: null, minWidth: 8.5 },
  close: { distance: 15, pitch: null, minWidth: 6 },
  vista: { distance: 62, pitch: 42, minWidth: 22 },
};
const ZOOM_ORDER = ['gameplay', 'close', 'vista'];

const SHAKE_DECAY = 1.1;       // trauma lost per second
const SHAKE_MAX_OFFSET = 0.35; // metres
const SHAKE_MAX_ANGLE = 1.8 * DEG;

// Smooth pseudo-noise in [-1, 1]; incommensurate sines are enough for shake.
const wobble = (t, seed) =>
  (Math.sin(t * 13.1 + seed) + 0.6 * Math.sin(t * 7.7 + seed * 2.3) + 0.3 * Math.sin(t * 23.3 + seed * 0.7)) / 1.9;

export class CameraRig {
  constructor({ fov = 24, pitch = 32, rotateDuration = 0.35, followOmega = 7, lookAhead = 0.35, maxLookAhead = 2.2, focusHeight = 0.9, focusAhead = 1.5 } = {}) {
    this.camera = new THREE.PerspectiveCamera(fov, 1, 0.5, 600);
    this.pitchDeg = pitch;
    this.rotateDuration = rotateDuration;
    this.followOmega = followOmega;
    this.lookAheadTime = lookAhead;
    this.maxLookAhead = maxLookAhead;
    this.focusHeight = focusHeight;
    this.focusAhead = focusAhead; // metres: the player sits a little below centre, showing more ahead

    this.focus = new THREE.Vector3();
    this.fx = { x: 0, v: 0 }; this.fy = { x: 0, v: 0 }; this.fz = { x: 0, v: 0 };
    this.leadX = { x: 0, v: 0 }; this.leadZ = { x: 0, v: 0 };

    this.yawIndex = 0; this.yaw = 0; this.yawFrom = 0; this.yawTo = 0; this.rotT = 1;
    this.zoomName = 'gameplay';
    this.dist = { x: ZOOMS.gameplay.distance, v: 0 };
    this.pitch = { x: pitch * DEG, v: 0 };
    this.trauma = 0; this.shakeT = 0;

    /** Camera-relative movement basis on the ground plane (follows the eased yaw). */
    this.forward = new THREE.Vector3(0, 0, -1);
    this.right = new THREE.Vector3(1, 0, 0);
  }

  get isRotating() { return this.rotT < 1; }
  /** Vertical stretch that keeps upright billboards' pixels square at the current pitch. */
  get billboardStretch() { return 1 / Math.cos(this.pitch.x); }

  /** dir = +1 orbits the camera to its right (90 degrees), -1 to its left. */
  rotate(dir) {
    this.yawIndex += Math.sign(dir);
    this.yawFrom = this.yaw;
    this.yawTo = this.yawIndex * Math.PI / 2;
    this.rotT = 0;
  }

  setZoom(name) { if (ZOOMS[name]) this.zoomName = name; }
  cycleZoom() { this.setZoom(ZOOM_ORDER[(ZOOM_ORDER.indexOf(this.zoomName) + 1) % ZOOM_ORDER.length]); }

  /** Trauma model (Eiserloh): shake = trauma^2, trauma decays linearly. */
  addTrauma(amount) { this.trauma = Math.min(1, this.trauma + amount); }

  resize(width, height) {
    this.camera.aspect = width / Math.max(1, height);
    this.camera.updateProjectionMatrix();
  }

  /** Jump straight to the target (spawn, teleport). */
  snap(target) {
    const fx = target.x + this.forward.x * this.focusAhead, fz = target.z + this.forward.z * this.focusAhead;
    for (const [s, v] of [[this.fx, fx], [this.fy, target.y + this.focusHeight], [this.fz, fz]]) { s.x = v; s.v = 0; }
    this.leadX.x = this.leadZ.x = this.leadX.v = this.leadZ.v = 0;
    this.dist.x = this.fitDistance(ZOOMS[this.zoomName]); this.dist.v = 0;
  }

  /** Portrait screens back the camera off so the visible width never drops below minWidth. */
  fitDistance(zoom) {
    const halfV = Math.tan(this.camera.fov * DEG / 2);
    return Math.max(zoom.distance, zoom.minWidth / (2 * halfV * this.camera.aspect));
  }

  update(dt, target, velocity) {
    if (this.rotT < 1) {
      this.rotT = Math.min(1, this.rotT + dt / this.rotateDuration);
      this.yaw = lerp(this.yawFrom, this.yawTo, easeInOutCubic(this.rotT));
    }
    const sy = Math.sin(this.yaw), cy = Math.cos(this.yaw);
    this.forward.set(-sy, 0, -cy);
    this.right.set(cy, 0, -sy);

    let lx = velocity.x * this.lookAheadTime, lz = velocity.z * this.lookAheadTime;
    const l = Math.hypot(lx, lz);
    if (l > this.maxLookAhead) { lx *= this.maxLookAhead / l; lz *= this.maxLookAhead / l; }
    springTo(this.leadX, lx, 2.5, dt);
    springTo(this.leadZ, lz, 2.5, dt);

    const w = this.followOmega;
    springTo(this.fx, target.x + this.leadX.x + this.forward.x * this.focusAhead, w, dt);
    springTo(this.fy, target.y + this.focusHeight, w, dt);
    springTo(this.fz, target.z + this.leadZ.x + this.forward.z * this.focusAhead, w, dt);
    this.focus.set(this.fx.x, this.fy.x, this.fz.x);

    const zoom = ZOOMS[this.zoomName];
    springTo(this.dist, this.fitDistance(zoom), 5, dt);
    springTo(this.pitch, (zoom.pitch ?? this.pitchDeg) * DEG, 5, dt);

    const cam = this.camera;
    const p = this.pitch.x, d = this.dist.x, h = Math.cos(p) * d;
    cam.position.set(this.focus.x + sy * h, this.focus.y + Math.sin(p) * d, this.focus.z + cy * h);
    cam.lookAt(this.focus);

    this.trauma = Math.max(0, this.trauma - SHAKE_DECAY * dt);
    const shake = this.trauma * this.trauma;
    if (shake > 0) {
      this.shakeT += dt;
      const t = this.shakeT;
      cam.position.addScaledVector(this.right, SHAKE_MAX_OFFSET * shake * wobble(t, 1.3));
      cam.position.y += SHAKE_MAX_OFFSET * shake * wobble(t, 4.1);
      cam.rotateZ(SHAKE_MAX_ANGLE * shake * wobble(t, 7.9));
    }
    cam.updateMatrixWorld();
  }
}
