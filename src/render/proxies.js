// Analytic stand-in volumes (spheres, vertical cylinders, boxes, a heightfield) for things that
// block the sun or the camera's view of the player. Protected characters are lit from these CPU
// queries instead of the shadow map, so swaying leaf shadows can never flicker on them.

import { smoothstep } from '../core/math.js';

const SPHERE = 0, CYLINDER = 1, BOX = 2;

export class ProxySet {
  constructor() {
    this.items = [];
    this.groundHeight = null;
  }

  /** opts.density: how much light the volume stops (foliage < 1); opts.shade / opts.view: which queries see it. */
  addSphere(x, y, z, r, opts) { this.items.push({ type: SPHERE, x, y, z, r, ...flags(opts) }); }
  addCylinder(x, z, r, y0, y1, opts) { this.items.push({ type: CYLINDER, x, z, r, y0, y1, ...flags(opts) }); }
  addBox(min, max, opts) { this.items.push({ type: BOX, min: min.slice(), max: max.slice(), ...flags(opts) }); }
  /** fn(x, z) -> ground height; terrain then blocks both queries. */
  setGround(fn) { this.groundHeight = fn; }

  /** Fraction of light passing from a to b: 1 = clear, 0 = blocked. mask is 'shade' or 'view'. */
  transmittance(a, b, mask) {
    let t = 1;
    if (this.groundHeight && this.groundBlocks(a, b)) return 0;
    for (const it of this.items) {
      if (!it[mask]) continue;
      const c = coverage(it, a, b);
      if (c > 0) t *= 1 - c * it.density;
      if (t < 0.01) return 0;
    }
    return t;
  }

  groundBlocks(a, b) {
    const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
    const steps = Math.ceil(Math.hypot(dx, dz) / 0.5);
    for (let i = 1; i < steps; i++) {
      const s = i / steps;
      if (this.groundHeight(a.x + dx * s, a.z + dz * s) > a.y + dy * s + 0.05) return true;
    }
    return false;
  }
}

const flags = ({ density = 1, shade = true, view = true } = {}) => ({ density, shade, view });

function coverage(it, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
  if (it.type === SPHERE) {
    const len2 = dx * dx + dy * dy + dz * dz;
    const s = Math.max(0, Math.min(1, ((it.x - a.x) * dx + (it.y - a.y) * dy + (it.z - a.z) * dz) / len2));
    const d = Math.hypot(a.x + dx * s - it.x, a.y + dy * s - it.y, a.z + dz * s - it.z);
    return 1 - smoothstep(it.r * 0.55, it.r, d);
  }
  if (it.type === CYLINDER) {
    const len2 = dx * dx + dz * dz;
    const s = len2 > 1e-6 ? Math.max(0, Math.min(1, ((it.x - a.x) * dx + (it.z - a.z) * dz) / len2)) : 0;
    const y = a.y + dy * s;
    if (y < it.y0 || y > it.y1) return 0;
    return 1 - smoothstep(it.r * 0.6, it.r, Math.hypot(a.x + dx * s - it.x, a.z + dz * s - it.z));
  }
  // Box: slab test, hard edge (callers smooth over time).
  let t0 = 0, t1 = 1;
  const o = [a.x, a.y, a.z], d = [dx, dy, dz];
  for (let k = 0; k < 3; k++) {
    if (Math.abs(d[k]) < 1e-9) {
      if (o[k] < it.min[k] || o[k] > it.max[k]) return 0;
      continue;
    }
    let n = (it.min[k] - o[k]) / d[k], f = (it.max[k] - o[k]) / d[k];
    if (n > f) [n, f] = [f, n];
    t0 = Math.max(t0, n);
    t1 = Math.min(t1, f);
    if (t0 > t1) return 0;
  }
  return 1;
}
