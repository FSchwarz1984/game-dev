// Screen-space circular cutout so trees, roofs and cliffs never hide the player.
// A cheap CPU test (proxy volumes + terrain) decides when the hole opens; the occluder shaders
// (see CUTOUT in glsl.js) drop fragments inside the circle that are nearer than the player and
// above her feet, so the ground she stands on is never cut.

import * as THREE from 'three';
import { shared } from './materials.js';
import { approach, smoothstep } from '../core/math.js';

const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _p = new THREE.Vector3();
const _size = new THREE.Vector2();

export class OcclusionCutout {
  constructor(proxies) {
    this.proxies = proxies;
    this.open = 0;
  }

  /** player: a sprite mesh (pivot at the feet). */
  update(dt, camera, renderer, player) {
    const p = player.position;
    const h = player.userData.sprite.size[1] * shared.uStretch.value;
    let blocked = false;
    for (const f of [0.5, 0.95]) {
      _a.set(p.x, p.y + f * h, p.z);
      if (this.proxies.transmittance(_a, camera.position, 'view') < 0.9) { blocked = true; break; }
    }
    this.open = approach(this.open, blocked ? 1 : 0, 9, dt);

    renderer.getDrawingBufferSize(_size);
    const toPx = (v, out) => {
      _p.copy(v).project(camera);
      return out.set((_p.x * 0.5 + 0.5) * _size.x, (_p.y * 0.5 + 0.5) * _size.y, 0);
    };
    toPx(_a.set(p.x, p.y, p.z), _a);
    toPx(_b.set(p.x, p.y + h, p.z), _b);
    const projected = _a.distanceTo(_b);

    _p.set(p.x, p.y + 0.55 * h, p.z);
    const depth = -_p.applyMatrix4(camera.matrixWorldInverse).z;
    toPx(_p.set(p.x, p.y + 0.55 * h, p.z), _p);

    const radius = projected * 0.85 + 6;
    shared.uCutCenter.value.set(_p.x, _p.y);
    shared.uCutRadius.value = radius * smoothstep(0, 1, this.open);
    shared.uCutDepth.value = depth - 0.6;
    shared.uCutFloor.value = p.y + 0.5;
    shared.uCutBottom.value = _a.y - 0.12 * radius; // the dithered lower edge ends at her feet
  }
}
