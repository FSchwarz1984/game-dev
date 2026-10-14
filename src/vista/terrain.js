// Voxel-space ("Comanche") renderer for side-view landscapes: a heightfield seen from a camera
// looking along +Z with a level horizon. One march per screen column, near to far; every pixel is
// written once, by the nearest surface that covers it. Out come material indices plus the ground
// position (X, Z) of every pixel, which the wave of distance uses to know when it gets there.
//
// The same renderer draws the sky shore: a ceiling hanging upside down, marched the same way but
// mirrored (surfaces project upward from the horizon, near ones to the top of the frame).

import { clamp } from './util.js';

/**
 * @param {object} o
 *   w, h        layer size; cx: screen x of the view axis; yh: horizon row
 *   f           focal length in pixels (screen y = yh + f * (camY - t) / Z)
 *   camY        camera height
 *   z0, z1      march range; k: step factor (dz = k * Z), kFar for Z > zFar
 *   height(X,Z) surface height
 *   gaps        optional [[za, zb]] ranges where the ground is flat (t = 0) and can be filled per row
 *   ceiling     true: the surface hangs from above (height = height above camera of the underside)
 * @returns {{ X: Float32Array, Z: Float32Array, mask: Uint8Array }}
 */
export function march(o) {
  const { w, h, cx, yh, f, camY = 1, z0, z1, height, ceiling = false } = o;
  const k = o.k || 0.012, kFar = o.kFar || k, zFar = o.zFar ?? Infinity;
  const PX = new Float32Array(w * h), PZ = new Float32Array(w * h), M = new Uint8Array(w * h);
  for (let x = 0; x < w; x++) {
    const dir = (x + 0.5 - cx) / f;
    let lim = ceiling ? 0 : h;          // first unwritten row (ground: rows above lim are free; ceiling: rows below)
    let pZ = z0, pX = dir * z0, py = ceiling ? -1e9 : 1e9;
    let Z = z0;
    const gaps = o.gapsFor ? o.gapsFor(dir) : o.gaps;
    while (Z < z1) {
      if (gaps) { // flat stretches of plain: jump them (rows are filled analytically by the caller's fill)
        let jumped = false;
        for (const [za, zb] of gaps) if (Z > za && Z < zb) {
          const yA = yh + f * camY / Z, yB = yh + f * camY / zb; // plain rows from here to the gap's far end
          const top = Math.max(0, Math.ceil(yB - 0.5));
          for (let y = Math.min(lim - 1, Math.floor(yA)); y >= top; y--) {
            const zz = f * camY / Math.max(0.01, y + 0.5 - yh);
            if (zz < za || zz > zb) continue;
            const i = y * w + x; PX[i] = dir * zz; PZ[i] = zz; M[i] = 1;
          }
          lim = Math.min(lim, top); Z = zb; pZ = zb; pX = dir * zb; py = yB; jumped = true; break;
        }
        if (jumped) continue;
      }
      const X = dir * Z, t = height(X, Z);
      const y = ceiling ? yh - f * (t) / Z : yh + f * (camY - t) / Z;
      if (!ceiling) {
        const yi = Math.ceil(y - 0.5);
        if (yi < lim) {
          const a = Math.max(0, yi), span = Math.max(1e-6, py - y);
          for (let r = lim - 1; r >= a; r--) { // interpolate depth across the run (no vertical streaks)
            const u = clamp((r + 0.5 - y) / span, 0, 1);
            const i = r * w + x; PZ[i] = Z + (pZ - Z) * u; PX[i] = dir * PZ[i]; M[i] = 1;
          }
          lim = a;
          if (lim <= 0) break;
        }
      } else {
        const yi = Math.floor(y + 0.5);
        if (yi > lim) {
          const b = Math.min(h, yi), span = Math.max(1e-6, y - py);
          for (let r = lim; r < b; r++) {
            const u = clamp((y - (r + 0.5)) / span, 0, 1);
            const i = r * w + x; PZ[i] = Z + (pZ - Z) * u; PX[i] = dir * PZ[i]; M[i] = 1;
          }
          lim = b;
          if (lim >= h) break;
        }
      }
      pZ = Z; pX = X; py = y;
      Z += Math.max(0.0015, (Z > zFar ? kFar : k) * Z);
    }
  }
  return { X: PX, Z: PZ, mask: M };
}

// surface normal by central differences, eps grows with distance (filters detail we cannot show)
export function normalAt(height, X, Z, eps) {
  const hx = height(X + eps, Z) - height(X - eps, Z);
  const hz = height(X, Z + eps) - height(X, Z - eps);
  const nx = -hx, ny = 2 * eps, nz = -hz, l = Math.hypot(nx, ny, nz) || 1;
  return [nx / l, ny / l, nz / l];
}

// Sun shadows on a heightfield, swept along -X (the low western sun casts shadows east = left).
// Grid: nx columns over [xa, xb], rows at log-spaced Z. Returns lookup(X, Z) -> 0 (shadow) .. 1 (lit).
export function sunShadows(height, { xa, xb, za, zb, nx = 512, nz = 256, slope = 0.18, soft = 0.04 }) {
  const S = new Float32Array(nx * nz), la = Math.log(za), lb = Math.log(zb), dx = (xb - xa) / (nx - 1);
  for (let j = 0; j < nz; j++) {
    const Z = Math.exp(la + (lb - la) * j / (nz - 1));
    let sh = -1e9;
    for (let i = nx - 1; i >= 0; i--) {
      const X = xa + i * dx, t = height(X, Z);
      sh -= dx * slope;
      S[j * nx + i] = clamp(1 - (sh - t) / soft, 0, 1);
      if (t > sh) sh = t;
    }
  }
  return (X, Z) => {
    const fi = (X - xa) / dx, fj = (Math.log(clamp(Z, za, zb)) - la) / (lb - la) * (nz - 1);
    const i = clamp(Math.round(fi), 0, nx - 1), j = clamp(Math.round(fj), 0, nz - 1);
    return S[j * nx + i];
  };
}
