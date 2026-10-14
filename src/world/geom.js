// Geometry helpers for the environment master material.

import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const UP = new THREE.Vector3(0, 1, 0);
const _q = new THREE.Quaternion(), _d = new THREE.Vector3();

/**
 * Adds the attributes createEnvMaterial expects: aLayer (layer, no lip), colour = tint x ao(y),
 * and aWind = wind(x, y, z) when given. Drops uv (UVs come from world space).
 */
export function env(geo, { layer, tint = 0xffffff, ao = null, wind = null }) {
  geo.deleteAttribute('uv');
  const pos = geo.attributes.position, n = pos.count;
  const layers = new Float32Array(n * 2), col = new Float32Array(n * 3);
  const winds = wind ? new Float32Array(n) : null;
  const c = new THREE.Color(tint);
  for (let i = 0; i < n; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    layers[i * 2] = layer;
    layers[i * 2 + 1] = -1;
    const k = ao ? ao(y) : 1;
    col[i * 3] = c.r * k; col[i * 3 + 1] = c.g * k; col[i * 3 + 2] = c.b * k;
    if (winds) winds[i] = wind(x, y, z);
  }
  geo.setAttribute('aLayer', new THREE.BufferAttribute(layers, 2));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  if (winds) geo.setAttribute('aWind', new THREE.BufferAttribute(winds, 1));
  return geo;
}

/** Box with its base centred on (x, y, z), optionally turned about Y. */
export function box(w, h, d, x = 0, y = 0, z = 0, ry = 0) {
  const g = new THREE.BoxGeometry(w, h, d).translate(0, h / 2, 0);
  if (ry) g.rotateY(ry);
  return g.translate(x, y, z);
}

/** Tapered cylinder from a to b (radius r0 at a, r1 at b). */
export function limb(a, b, r0, r1, segments = 7) {
  _d.subVectors(b, a);
  const len = _d.length();
  const g = new THREE.CylinderGeometry(r1, r0, len, segments, 1).translate(0, len / 2, 0);
  g.applyQuaternion(_q.setFromUnitVectors(UP, _d.normalize()));
  return g.translate(a.x, a.y, a.z);
}

/** Cylinder standing on (x, y, z). */
export function post(r0, r1, h, x, y, z, segments = 8) {
  return new THREE.CylinderGeometry(r1, r0, h, segments).translate(x, y + h / 2, z);
}

export const merge = geos => mergeGeometries(geos, false);
