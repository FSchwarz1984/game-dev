// Her sprite, the crew's sprites, and what her body looks like with what she carries in it.
// The body is the main HUD: heavy squashes her and slows the walk cycle, light lifts her off the
// ground, heat and light colour her key light, sound and life leave marks around her feet.

import * as THREE from 'three';
import { createSprite } from '../render/sprites.js';
import { pixelTexture } from '../render/textures.js';
import { shared } from '../render/materials.js';
import { approach } from '../core/math.js';
import { characterSheet, SHEET } from '../world/art.js';
import { WATER_Y } from '../world/terrain.js';
import { bodyState } from '../game/qualities.js';
import { CELL, crewSheet, glowSprite, onibiSheet } from './art.js';
import { UPRIGHT_QUAD } from '../render/materials.js';

const ROWS = { front: 0, back: 1, side: 2 };
const FOOT = SHEET.footPad / SHEET.pxPerMetre;

/** Camera-relative facing with hysteresis, so diagonals do not flicker between rows. */
function face(state, dx, dz, rig) {
  const fx = dx * rig.right.x + dz * rig.right.z;
  const fy = dx * rig.forward.x + dz * rig.forward.z;
  const sideNow = state.view === 'side';
  if (Math.abs(fx) > Math.abs(fy) * (sideNow ? 0.8 : 1.25)) { state.view = 'side'; state.mirror = fx < 0; }
  else if (Math.abs(fy) > Math.abs(fx) * (sideNow ? 1.25 : 0.8)) state.view = fy > 0 ? 'back' : 'front';
}

export class Actors {
  constructor({ scene, sim, terrain, rig, lighting, fx }) {
    Object.assign(this, { scene, sim, terrain, rig, lighting, fx });
    this.player = createSprite({
      sheet: { texture: pixelTexture(characterSheet()), frameW: SHEET.frameW, frameH: SHEET.frameH },
      size: [SHEET.frameW / SHEET.pxPerMetre, SHEET.frameH / SHEET.pxPerMetre],
      kind: 'character',
    });
    this.player.name = 'player';
    scene.add(this.player);
    this.pState = { view: 'back', mirror: false, walk: 0, y: null, lastX: sim.player.x, lastZ: sim.player.z, speed: 0, squash: 0, lift: 0, ring: 0, blink: 0 };
    const glowTex = pixelTexture(glowSprite());
    this.halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xfff0b0, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
    this.halo.scale.setScalar(2.4);
    scene.add(this.halo);
    this.heat = new THREE.Color();

    this.crewTex = pixelTexture(crewSheet());
    this.onibiTex = pixelTexture(onibiSheet());
    this.glowTex = glowTex;
    this.crew = new Map(); // member → { sprite, state }
  }

  /** Height her feet stand at: the deck, the ice or the water surface where the ground is water. */
  standY(x, z) {
    const h = this.terrain.heightAt(x, z);
    if (h > WATER_Y - 0.2) return h;
    return this.sim.onBridge(x, z) ? 0.06 : WATER_Y + 0.02;
  }

  /** All sprites that need protected character lighting this frame. */
  get characters() { return [this.player, ...[...this.crew.values()].filter(c => !c.onibi).map(c => c.sprite)]; }

  update(dt, time) {
    this.updatePlayer(dt, time);
    this.updateCrew(dt, time);
  }

  updatePlayer(dt, time) {
    const P = this.sim.player, s = this.pState, body = bodyState(P.holder);
    const moved = Math.hypot(P.x - s.lastX, P.z - s.lastZ);
    s.speed = approach(s.speed, dt > 0 ? moved / dt : 0, 12, dt);
    if (moved > 1e-4) face(s, P.x - s.lastX, P.z - s.lastZ, this.rig);
    else if (P.fx || P.fz) face(s, P.fx * 0.01, P.fz * 0.01, this.rig);
    s.lastX = P.x; s.lastZ = P.z;
    // a heavy body walks a slower, heavier cycle
    s.walk = s.speed > 0.4 ? s.walk + dt * s.speed * (body.heavy ? 1.1 : 1.45) : 0;
    const col = s.speed > 0.4 ? 1 + (Math.floor(s.walk) % 2) : 0;
    this.player.userData.sprite.setFrame(col, ROWS[s.view], s.view === 'side' && s.mirror);

    const gy = this.standY(P.x, P.z);
    s.y = s.y === null ? gy : approach(s.y, gy, gy > s.y ? 22 : 12, dt);
    s.lift = approach(s.lift, body.light ? 0.22 + Math.sin(time * 2.2) * 0.06 : 0, 6, dt);
    s.squash = approach(s.squash, body.heavy ? Math.min(1, (P.holder.q.w - P.holder.base.w) / 4) : 0, 8, dt);
    const [w, h] = this.player.userData.sprite.size;
    this.player.scale.set(w * (1 + 0.1 * s.squash), h * (1 - 0.1 * s.squash), 1);
    this.player.position.set(P.x, s.y + s.lift - FOOT * shared.uStretch.value, P.z);

    // hurt: blink while invulnerable
    this.player.visible = P.iframes <= 0 || Math.floor(time * 16) % 2 === 0;

    // light she holds shines around her; sound and life leave marks at her feet
    const glow = Math.max(0, P.holder.q.l - P.holder.base.l);
    this.halo.material.opacity = approach(this.halo.material.opacity, Math.min(1, glow / 3) * 0.75, 6, dt);
    this.halo.position.set(P.x, s.y + s.lift + 0.9, P.z);
    s.ring -= dt;
    if (s.ring <= 0 && (body.loud || body.lively)) {
      s.ring = body.loud ? 0.9 : 1.4;
      this.fx?.ring(new THREE.Vector3(P.x, s.y + 0.05, P.z), body.loud ? 0x9fd0ff : 0x8fdc7a, body.loud ? 1.6 : 0.9);
    }
  }

  /** After lighting.updateCharacter: tint her key light with the heat or cold she holds. */
  tintPlayer() {
    const P = this.sim.player, u = this.player.userData.sprite.uniforms;
    const d = P.holder.q.h - P.holder.base.h, l = P.holder.q.l - P.holder.base.l;
    this.heat.setRGB(0, 0, 0);
    if (d > 0) this.heat.setRGB(0.55 * d, 0.2 * d, 0.02 * d);
    if (d < 0) this.heat.setRGB(0.02, 0.12 * -d, 0.3 * -d);
    if (l > 0) this.heat.r += 0.25 * l, this.heat.g += 0.24 * l, this.heat.b += 0.16 * l;
    u.uKeyColor.value.add(this.heat);
  }

  makeOnibi() {
    const tex = this.onibiTex.clone();
    tex.needsUpdate = true;
    tex.repeat.set(1 / 4, 1 / 2);
    const quad = new THREE.Mesh(UPRIGHT_QUAD, new THREE.MeshBasicMaterial({ map: tex, transparent: true, alphaTest: 0.4, fog: true }));
    quad.scale.set(0.75, 0.75, 1);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glowTex, color: 0x9fd8ff, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.6 }));
    halo.scale.setScalar(1.8);
    halo.position.y = 0.4;
    const g = new THREE.Group();
    g.add(halo, quad);
    return { sprite: g, onibi: true, quad, tex };
  }

  updateCrew(dt, time) {
    const members = this.sim.crew.members, live = new Set(members);
    for (const [m, c] of this.crew) if (!live.has(m)) { this.scene.remove(c.sprite); this.crew.delete(m); }
    members.forEach((m, i) => {
      let c = this.crew.get(m);
      if (!c) {
        c = m.kind === 'onibi' ? this.makeOnibi() : { sprite: createSprite({ sheet: { texture: this.crewTex, frameW: CELL, frameH: CELL }, size: [0.8, 0.8], kind: 'character' }), row: this.crew.size % 3 };
        Object.assign(c, { lastX: m.x, lastZ: m.z, hop: Math.random() * 6, mirror: false, y: null });
        this.scene.add(c.sprite);
        this.crew.set(m, c);
      }
      if (c.onibi) { // a pacified onibi floats along in the line, pale and calm
        c.y = c.y === null ? this.standY(m.x, m.z) : approach(c.y, this.standY(m.x, m.z), 8, dt);
        c.sprite.position.set(m.x, c.y + 0.3 + Math.sin(time * 2.4 + i) * 0.1, m.z);
        c.tex.offset.set((Math.floor(time * 8 + i) % 4) / 4, 0);
        c.quad.quaternion.copy(this.rig.camera.quaternion);
        c.lastX = m.x; c.lastZ = m.z;
        return;
      }
      const moved = Math.hypot(m.x - c.lastX, m.z - c.lastZ);
      const fx = (m.x - c.lastX) * this.rig.right.x + (m.z - c.lastZ) * this.rig.right.z;
      if (Math.abs(fx) > 1e-3) c.mirror = fx < 0;
      c.lastX = m.x; c.lastZ = m.z;
      const walking = moved > 1e-3;
      c.hop = walking ? c.hop + dt * 9 : 0;
      const bounce = walking ? Math.abs(Math.sin(c.hop)) * 0.12 : 0;
      const gy = this.standY(m.x, m.z);
      c.y = c.y === null ? gy : approach(c.y, gy, 14, dt);
      c.sprite.userData.sprite.setFrame(walking && Math.sin(c.hop) < 0 ? 1 : 0, c.row, c.mirror);
      c.sprite.position.set(m.x, c.y + bounce - 0.06, m.z);
    });
  }
}
