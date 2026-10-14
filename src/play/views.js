// What each gray-box station looks like, driven every frame by the simulation's state. Every
// change of a quality has a visible consequence on the thing itself (a stone with no weight
// floats, a pond with no heat is ice, a bell with sound swings), so the world, not the HUD, says
// what happened. Static parts use the environment material; moving parts use plain lit
// materials so their textures do not slide in world space.

import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { createEnvMaterial, UPRIGHT_QUAD } from '../render/materials.js';
import { createSprite } from '../render/sprites.js';
import { pixelTexture } from '../render/textures.js';
import { approach } from '../core/math.js';
import { env, box, post, merge } from '../world/geom.js';
import { L, terrainLayers } from '../world/art.js';
import { WATER_Y } from '../world/terrain.js';
import { stateOf } from '../game/qualities.js';
import { CELL, fireSheet, cropSheet, weedsSheet, shideSprite, iceTexture, glowSprite, onibiSheet } from './art.js';

const TAU = Math.PI * 2;

/** Builds and updates one view per simulation entity; views come and go with the entities. */
export class StationViews {
  constructor({ scene, sim, terrain, layers, propsGroup, fx, sound }) {
    Object.assign(this, { scene, sim, terrain, fx, sound });
    this.solid = createEnvMaterial(layers);
    this.layerCanvases = terrainLayers();
    this.props = propsGroup;
    this.views = new Map();
    this.time = 0;
    this.tex = {
      fire: pixelTexture(fireSheet()), crop: pixelTexture(cropSheet()), weeds: pixelTexture(weedsSheet()),
      shide: pixelTexture(shideSprite()), ice: crisp(pixelTexture(iceTexture())), glow: pixelTexture(glowSprite()),
      onibi: pixelTexture(onibiSheet()),
    };
    this.lambert = {};
    this.sync(0);
  }

  /** A lit material for moving parts, textured with one environment layer through ordinary UVs. */
  mat(layer, tint = 0xffffff) {
    const key = layer + ':' + tint;
    if (!this.lambert[key]) {
      const t = crisp(pixelTexture(this.layerCanvases[layer], { repeat: true }));
      this.lambert[key] = new THREE.MeshLambertMaterial({ map: t, color: tint });
    }
    return this.lambert[key];
  }

  ground(x, z) { return this.terrain.heightAt(x, z); }

  /** The object the highlighter should outline for an entity. */
  objectFor(e) { return this.views.get(e)?.hl || null; }

  sync(dt) {
    this.time += dt;
    const live = new Set(this.sim.entities);
    for (const [e, v] of this.views) if (!live.has(e)) { v.dispose?.(); if (v.own !== false) this.scene.remove(v.root); this.views.delete(e); }
    for (const e of this.sim.entities) {
      if (!this.views.has(e)) {
        const v = this.build(e);
        if (!v) continue;
        if (v.own !== false) this.scene.add(v.root);
        this.views.set(e, v);
      }
      this.views.get(e).sync(e, dt, this.time);
    }
  }

  build(e) {
    const f = this['make_' + e.kind];
    return f ? f.call(this, e) : null;
  }

  // ------------------------------------------------------------------ helpers

  mesh(geo, material, { cast = true, receive = true } = {}) {
    const m = new THREE.Mesh(geo, material);
    m.castShadow = cast; m.receiveShadow = receive;
    return m;
  }

  sprite(texture, frames, size, kind = 'prop', frameW = CELL, frameH = CELL) {
    const s = createSprite({ sheet: { texture, frameW, frameH }, size, kind });
    s.userData.frames = frames;
    return s;
  }

  glow(color, size) {
    const m = new THREE.SpriteMaterial({ map: this.tex.glow, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: true });
    const s = new THREE.Sprite(m);
    s.scale.set(size, size, 1);
    return s;
  }

  /** Where a haulable item is drawn: on the ground, above her head, or on the crew's heads. */
  carriedY(e, groundY) {
    const P = this.sim.player;
    if (P.carrying === e) return groundY + 1.75;
    const job = this.sim.haulJobs.find(j => j.item === e);
    if (job && job.crewJob.state === 'carry') return groundY + 0.78;
    if (stateOf(e.holder).floats) return groundY + 0.55 + Math.sin(this.time * 2 + e.id) * 0.06;
    return groundY;
  }

  // ------------------------------------------------------------------ 重

  make_rock(e) {
    // the boulder already exists as a prop; this view only moves it
    const m = this.props.getObjectByName('boulder');
    if (!m) return null;
    const baseY = m.position.y, baseRot = m.rotation.clone();
    return {
      root: m, hl: m, own: false, lift: 0,
      sync(e, dt, t) {
        const floats = e.holder.q.w <= 0;
        this.lift = approach(this.lift, floats ? 0.75 : 0, floats ? 2.2 : 6, dt);
        m.position.y = baseY + this.lift + (floats ? Math.sin(t * 1.7) * 0.07 : 0);
        m.rotation.set(baseRot.x + (floats ? Math.sin(t * 1.1) * 0.06 : 0), baseRot.y + this.lift * 0.3, baseRot.z);
      },
    };
  }

  make_plate(e) {
    const root = new THREE.Group();
    const y = this.ground(e.x, e.z);
    root.position.set(e.x, y, e.z);
    const slab = this.mesh(merge([env(box(1.3, 0.16, 1.3), { layer: L.GRANITE, tint: 0xd8d4cc }), env(box(0.9, 0.04, 0.9, 0, 0.16, 0), { layer: L.PAVING, tint: 0xbab4a8 })]), this.solid);
    const rune = new THREE.MeshLambertMaterial({ color: 0x3a3630, emissive: 0xffd36a, emissiveIntensity: 0 });
    const ring = this.mesh(new THREE.TorusGeometry(0.32, 0.035, 4, 24).rotateX(Math.PI / 2).translate(0, 0.2, 0), rune, { cast: false });
    root.add(slab, ring);
    // a straw rope with shide runs on the ground from the plate to the gate: cause and effect in sight
    const gate = this.sim.gateEntity;
    const rope = new THREE.MeshLambertMaterial({ color: 0xcdb27a, emissive: 0xffc860, emissiveIntensity: 0 });
    const ropeGeo = [], shide = [];
    const n = Math.ceil(Math.hypot(gate.x - e.x, gate.z - e.z) / 0.5);
    for (let i = 0; i < n; i++) {
      const ax = e.x + (gate.x - e.x) * i / n, az = e.z + (gate.z - e.z) * i / n;
      const bx = e.x + (gate.x - e.x) * (i + 1) / n, bz = e.z + (gate.z - e.z) * (i + 1) / n;
      const ay = Math.max(this.ground(ax, az), WATER_Y) + 0.05, by = Math.max(this.ground(bx, bz), WATER_Y) + 0.05;
      const g = new THREE.CylinderGeometry(0.035, 0.035, Math.hypot(bx - ax, by - ay, bz - az), 5);
      g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(bx - ax, by - ay, bz - az).normalize()));
      g.translate((ax + bx) / 2 - e.x, (ay + by) / 2 - y, (az + bz) / 2 - e.z);
      ropeGeo.push(g);
      if (i % 4 === 2) shide.push([ax, ay, az]);
    }
    const ropeMesh = this.mesh(merge(ropeGeo), rope, { cast: false });
    root.add(ropeMesh);
    for (const [x, sy, z] of shide) {
      const s = this.sprite(this.tex.shide, 1, [0.16, 0.32], 'prop', 16, 32);
      s.position.set(x - e.x, sy - y, z - e.z);
      root.add(s);
    }
    return {
      root, hl: slab, press: 0,
      sync(e, dt) {
        this.press = approach(this.press, e.state.pressed ? 1 : 0, 10, dt);
        slab.position.y = ring.position.y = -0.08 * this.press;
        rune.emissiveIntensity = rope.emissiveIntensity = 1.4 * this.press;
      },
    };
  }

  make_gate(e) {
    // the gate line runs along the rectangle's long side; leaves hinge on the two posts
    const r = e.rect, alongX = r ? r.x1 - r.x0 > r.z1 - r.z0 : false;
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    if (alongX) root.rotation.y = Math.PI / 2;
    const span = r ? Math.max(r.x1 - r.x0, r.z1 - r.z0) / 2 : e.r;   // half width across the way
    root.add(this.mesh(merge([
      env(post(0.13, 0.11, 2.3, 0, 0, -span), { layer: L.DARKWOOD }),
      env(post(0.13, 0.11, 2.3, 0, 0, span), { layer: L.DARKWOOD }),
      env(box(0.2, 0.16, span * 2 + 0.6, 0, 2.15, 0), { layer: L.DARKWOOD }),
      env(box(0.3, 0.1, span * 2 + 0.9, 0, 2.3, 0), { layer: L.LACQUER }),
    ]), this.solid));
    const wood = this.mat(L.PLANK, 0xc8a878);
    const leaf = side => {
      const hinge = new THREE.Group();
      hinge.position.set(0, 0, side * span);
      const bars = [];
      const w = span - 0.08;
      for (let i = 0; i < 4; i++) bars.push(new THREE.BoxGeometry(0.07, 1.5, 0.07).translate(0, 0.95, -side * (0.18 + i * (w - 0.2) / 3)));
      bars.push(new THREE.BoxGeometry(0.08, 0.1, w).translate(0, 1.6, -side * w / 2), new THREE.BoxGeometry(0.08, 0.1, w).translate(0, 0.35, -side * w / 2));
      hinge.add(this.mesh(merge(bars), wood));
      root.add(hinge);
      return hinge;
    };
    const left = leaf(-1), right = leaf(1);
    return {
      root, hl: root, open: 0,
      sync(e, dt) {
        this.open = approach(this.open, e.state.open ? 1 : 0, e.state.open ? 3 : 7, dt);
        // swing away from the plate side (toward +z in world before the turn)
        left.rotation.y = this.open * 1.45;
        right.rotation.y = -this.open * 1.45;
      },
    };
  }

  make_bridge(e) {
    const root = new THREE.Group();
    const r = e.rect;
    const w = r.x1 - r.x0, len = r.z1 - r.z0, deckY = 0.06;
    root.position.set(e.x, 0, (r.z0 + r.z1) / 2);
    const rot = this.mat(L.PLANK, 0x9a9a78);
    const planks = [];
    const n = 9;
    for (let i = 0; i < n; i++) {
      const p = this.mesh(new THREE.BoxGeometry(w, 0.07, len / n - 0.06), rot);
      p.position.set((i % 3 - 1) * 0.03, deckY, -len / 2 + (i + 0.5) * len / n);
      p.rotation.y = (i % 2 ? 1 : -1) * 0.03;
      root.add(p); planks.push(p);
    }
    root.add(this.mesh(merge([
      env(post(0.09, 0.08, 1.2, -w / 2, WATER_Y - 0.6, -len / 2 + 0.6), { layer: L.DARKWOOD, tint: 0x8a8a70 }),
      env(post(0.09, 0.08, 1.2, w / 2, WATER_Y - 0.6, -len / 2 + 0.6), { layer: L.DARKWOOD, tint: 0x8a8a70 }),
      env(post(0.09, 0.08, 1.2, -w / 2, WATER_Y - 0.6, len / 2 - 0.6), { layer: L.DARKWOOD, tint: 0x8a8a70 }),
      env(post(0.09, 0.08, 1.2, w / 2, WATER_Y - 0.6, len / 2 - 0.6), { layer: L.DARKWOOD, tint: 0x8a8a70 }),
    ]), this.solid));
    const self = this;
    return {
      root, hl: planks[4], fallen: false,
      sync(e, dt) {
        if (e.state.broken && !this.fallen) {
          this.fallen = true;
          planks.forEach((p, i) => { if (i >= 2 && i <= 6) p.userData.fall = { v: 0, spin: (Math.random() - 0.5) * 3 }; });
          self.fx?.ring(new THREE.Vector3(e.x, WATER_Y + 0.05, (r.z0 + r.z1) / 2), 0xbfe6ff, 2.2);
        }
        for (const p of planks) {
          const f = p.userData.fall;
          if (!f) continue;
          if (p.position.y > WATER_Y - 0.2) { f.v += 9.8 * dt; p.position.y -= f.v * dt; p.rotation.x += f.spin * dt; }
          else { p.position.y = WATER_Y - 0.05 + Math.sin(self.time * 2 + p.id) * 0.02; p.position.z += dt * 0.25; } // floats off downstream
        }
      },
    };
  }

  // ------------------------------------------------------------------ 熱

  make_pond(e) {
    const m = new THREE.MeshLambertMaterial({ map: this.tex.ice, transparent: true, depthWrite: false });
    const ice = this.mesh(new THREE.CircleGeometry(e.r, 28).rotateX(-Math.PI / 2), m, { cast: false });
    ice.position.set(e.x, WATER_Y + 0.04, e.z);
    ice.scale.setScalar(0.001);
    ice.renderOrder = 2;
    // an invisible thin drum: its outline hull draws the target ring on the water
    const marker = this.mesh(new THREE.CylinderGeometry(e.r * 0.8, e.r * 0.8, 0.04, 32), new THREE.MeshBasicMaterial({ visible: false }), { cast: false, receive: false });
    marker.position.set(e.x, WATER_Y + 0.02, e.z);
    const root = new THREE.Group();
    root.add(ice, marker);
    return {
      root, hl: marker, k: 0,
      sync(e, dt) {
        const frozen = stateOf(e.holder).frozen;
        this.k = approach(this.k, frozen ? 1 : 0, frozen ? 3 : 1.5, dt);
        ice.visible = this.k > 0.01;
        ice.scale.setScalar(Math.max(0.001, this.k));
      },
    };
  }

  make_brazier(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    const legs = [0, 1, 2].map(i => env(post(0.04, 0.035, 0.55, Math.cos(i / 3 * TAU) * 0.28, 0, Math.sin(i / 3 * TAU) * 0.28, 5), { layer: L.DARKWOOD, tint: 0x606070 }));
    const bowl = env(new THREE.CylinderGeometry(0.42, 0.26, 0.26, 10).translate(0, 0.62, 0), { layer: L.COPPER, tint: 0x55505a });
    const body = this.mesh(merge([...legs, bowl]), this.solid);
    const fire = this.sprite(this.tex.fire, 4, [0.95, 0.95]);
    fire.position.y = 0.7;
    const halo = this.glow(0xff9a40, 2.2);
    halo.position.y = 1.0;
    root.add(body, fire, halo);
    return {
      root, hl: body, s: 0,
      sync(e, dt, t) {
        const h = e.holder.q.h;
        this.s = approach(this.s, h <= 0 ? 0 : 0.45 + Math.min(h, 4) * 0.2, 6, dt);
        fire.visible = this.s > 0.05;
        fire.scale.set(0.95 * this.s, 0.95 * this.s, 1);
        fire.userData.sprite.setFrame(Math.floor(t * 9 + e.id) % 4, 0);
        halo.material.opacity = this.s * (0.55 + 0.1 * Math.sin(t * 13));
        halo.scale.setScalar(1.2 + this.s * 1.4);
      },
    };
  }

  // ------------------------------------------------------------------ 光

  make_lantern(e) {
    const g = this.props.getObjectByName('stone-lantern');
    if (!g) return null;
    const flame = g.children[1] || null;   // the paper window above the stone (props.js)
    const halo = this.glow(0xffd889, 1.6);
    halo.position.set(g.position.x, g.position.y + 1.27, g.position.z);
    this.scene.add(halo);
    const base = flame ? flame.material.color.clone() : null;
    const self = this;
    return {
      root: g, hl: g, own: false, k: 0,
      sync(e, dt, t) {
        const l = e.holder.q.l;
        this.k = approach(this.k, Math.min(l, 4) / 3, 5, dt);
        halo.material.opacity = this.k * (0.85 + 0.08 * Math.sin(t * 7));
        halo.scale.setScalar(0.8 + this.k * 1.3);
        if (flame) {
          flame.material.emissiveIntensity = 4 * (self.lanternLevel ?? 0) * Math.min(1, l) + this.k * 1.2;
          flame.material.color.copy(base).multiplyScalar(0.25 + 0.75 * Math.min(1, this.k));
        }
      },
      dispose() { halo.removeFromParent(); },
    };
  }

  // ------------------------------------------------------------------ 音

  make_bell(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    root.add(this.mesh(merge([
      env(post(0.08, 0.07, 2.4, -0.75, 0, 0, 6), { layer: L.DARKWOOD }),
      env(post(0.08, 0.07, 2.4, 0.75, 0, 0, 6), { layer: L.DARKWOOD }),
      env(box(1.9, 0.14, 0.18, 0, 2.3, 0), { layer: L.DARKWOOD }),
      env(box(2.2, 0.08, 0.7, 0, 2.45, 0), { layer: L.THATCH }),
    ]), this.solid));
    const pivot = new THREE.Group();
    pivot.position.y = 2.25;
    const profile = [[0.02, 0], [0.16, -0.05], [0.2, -0.2], [0.24, -0.5], [0.3, -0.62], [0.28, -0.66], [0.0, -0.66]].map(([x, y]) => new THREE.Vector2(x, y));
    const bell = this.mesh(new THREE.LatheGeometry(profile, 14), this.mat(L.COPPER, 0xc8a060));
    bell.position.y = -0.12;
    pivot.add(bell, this.mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.12, 4).translate(0, -0.06, 0), this.mat(L.THATCH)));
    root.add(pivot);
    const self = this;
    return {
      root, hl: bell, swing: 0, lastS: e.holder.q.s, echo: 0,
      sync(e, dt, t) {
        const s = e.holder.q.s;
        if (s > this.lastS) { this.swing = 1; this.ring(e, 1); }
        this.lastS = s;
        if (s > 0) { this.echo -= dt; if (this.echo <= 0) { this.echo = 5.5; this.swing = Math.max(this.swing, 0.35); this.ring(e, 0.4); } }
        this.swing = Math.max(0, this.swing - dt * 0.35);
        pivot.rotation.z = Math.sin(t * 5.2) * 0.32 * this.swing;
      },
      ring(e, k) {
        self.fx?.ring(new THREE.Vector3(e.x, root.position.y + 1.7, e.z), 0x9fd0ff, 2.5 + 2 * k);
        self.sound?.('bell', e, k);
      },
    };
  }

  /** The 音 source: a shishi-odoshi whose bamboo tube fills, tips and clacks on a stone. */
  make_falls(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    root.add(this.mesh(merge([
      env(new THREE.CylinderGeometry(0.42, 0.48, 0.32, 10).translate(0.55, 0.16, 0), { layer: L.GRANITE }),
      env(post(0.05, 0.05, 0.75, -0.05, 0, -0.16, 5), { layer: L.BAMBOO }),
      env(post(0.05, 0.05, 0.75, -0.05, 0, 0.16, 5), { layer: L.BAMBOO }),
      env(post(0.04, 0.04, 1.15, 1.0, 0, 0, 5), { layer: L.BAMBOO }),
      env(box(0.5, 0.05, 0.05, 0.8, 1.1, 0), { layer: L.BAMBOO }),
      env(mergeVertices(new THREE.DodecahedronGeometry(0.16).translate(-0.62, 0.12, 0)), { layer: L.ROCK }),
    ]), this.solid));
    const pivot = new THREE.Group();
    pivot.position.set(-0.05, 0.62, 0);
    const tube = this.mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.1, 8).rotateZ(Math.PI / 2).translate(0.15, 0, 0), this.mat(L.BAMBOO, 0xd8e0a0));
    pivot.add(tube);
    root.add(pivot);
    const self = this;
    return {
      root, hl: tube, fill: Math.random(), drop: 0,
      sync(e, dt) {
        this.fill += dt / 3.2;
        if (this.fill >= 1) { this.fill = 0; this.drop = 1; self.sound?.('clack', e, 1); }
        this.drop = Math.max(0, this.drop - dt * 2.5);
        // filling: the open end (+x) slowly dips; tipped: it snaps back and the far end knocks the stone
        pivot.rotation.z = -0.12 - this.fill * 0.4 + this.drop * 0.95;
      },
    };
  }

  // ------------------------------------------------------------------ 生

  make_weeds(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    const tufts = [];
    for (let i = 0; i < 7; i++) {
      const a = i * 2.4, r = i === 0 ? 0 : 0.35 + (i % 3) * 0.18;
      const s = this.sprite(this.tex.weeds, 3, [0.85, 0.85]);
      s.position.set(Math.cos(a) * r, -0.02, Math.sin(a) * r * 0.8);
      root.add(s); tufts.push(s);
    }
    const flame = this.glow(0xff7a30, 2.4);
    flame.position.y = 0.5;
    root.add(flame);
    return {
      root, hl: root, h: 1,
      sync(e, dt, t) {
        const v = e.holder.q.v, burning = e.state.burning > 0;
        this.h = approach(this.h, v <= 0 ? 0.35 : 0.5 + Math.min(v, 4) * 0.16, 3, dt);
        const frame = burning ? 1 : v <= 0 ? 2 : 0;
        tufts.forEach((s, i) => {
          s.userData.sprite.setFrame(frame, 0, i % 2 === 1);
          s.scale.set(0.85, 0.85 * (frame === 2 ? 1 : this.h), 1);
        });
        flame.visible = burning;
        flame.material.opacity = 0.6 + 0.3 * Math.sin(t * 17);
      },
    };
  }

  make_plot(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    const furrows = [env(box(2.0, 0.1, 1.7), { layer: L.EARTH, tint: 0x9a7a5a })];
    for (let i = 0; i < 3; i++) furrows.push(env(box(1.8, 0.06, 0.22, 0, 0.1, -0.5 + i * 0.5), { layer: L.EARTH, tint: 0xc09a70 }));
    const bed = this.mesh(merge(furrows), this.solid);
    root.add(bed);
    const plants = [-0.5, 0.5].map(x => {
      const s = this.sprite(this.tex.crop, 5, [0.9, 0.9]);
      s.position.set(x, 0.1, 0);
      root.add(s);
      return s;
    });
    const sparkle = this.glow(0xfff0a0, 0.8);
    sparkle.position.y = 1.0;
    root.add(sparkle);
    return {
      root, hl: root,
      sync(e, dt, t) {
        const p = e.plot;
        plants.forEach((s, i) => { s.visible = !!p.crop; s.userData.sprite.setFrame(Math.min(4, p.stage), 0, i === 1); });
        sparkle.visible = p.ripe;
        sparkle.material.opacity = 0.5 + 0.5 * Math.sin(t * 4);
      },
    };
  }

  // ------------------------------------------------------------------ logistics

  make_log(e) {
    const m = this.mesh(new THREE.CylinderGeometry(0.19, 0.21, 1.5, 9).rotateZ(Math.PI / 2), this.mat(L.BARK, 0xd8c0a0));
    const ends = this.mesh(merge([new THREE.CircleGeometry(0.19, 9).rotateY(Math.PI / 2).translate(0.751, 0, 0), new THREE.CircleGeometry(0.21, 9).rotateY(-Math.PI / 2).translate(-0.751, 0, 0)]), this.mat(L.PLANK, 0xf0d8a8));
    const root = new THREE.Group();
    root.add(m, ends);
    root.rotation.y = (e.id * 1.7) % Math.PI;
    const self = this;
    return {
      root, hl: m, y: null,
      sync(e, dt) {
        const gy = self.ground(e.x, e.z) + 0.2;
        const ty = self.carriedY(e, gy);
        this.y = this.y === null ? ty : approach(this.y, ty, 10, dt);
        root.position.set(e.x, this.y, e.z);
      },
    };
  }

  make_stone(e) {
    const m = this.mesh(new THREE.DodecahedronGeometry(0.3).scale(1.15, 0.8, 1), this.mat(L.GRANITE, 0xd0ccc4));
    m.rotation.y = e.id;
    const self = this;
    return {
      root: m, hl: m, y: null,
      sync(e, dt) {
        const ty = self.carriedY(e, self.ground(e.x, e.z) + 0.22);
        this.y = this.y === null ? ty : approach(this.y, ty, 10, dt);
        m.position.set(e.x, this.y, e.z);
      },
    };
  }

  make_yard(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    const pallet = this.mesh(merge([
      env(box(2.2, 0.12, 1.7), { layer: L.PLANK }),
      ...[[-1, -0.8], [1, -0.8], [-1, 0.8], [1, 0.8]].map(([x, z]) => env(post(0.05, 0.05, 0.7, x * 1.05, 0, z * 1.0, 5), { layer: L.DARKWOOD })),
    ]), this.solid);
    root.add(pallet);
    const pile = new THREE.Group();
    root.add(pile);
    const logMat = this.mat(L.BARK, 0xd8c0a0), stoneMat = this.mat(L.GRANITE, 0xd0ccc4);
    const logGeo = new THREE.CylinderGeometry(0.17, 0.19, 1.4, 8).rotateX(Math.PI / 2), stoneGeo = new THREE.DodecahedronGeometry(0.26).scale(1.1, 0.8, 1);
    return {
      root, hl: pallet, key: '',
      sync(e) {
        const key = e.store.log + ':' + e.store.stone;
        if (key === this.key) return;
        this.key = key;
        pile.clear();
        const slots = [[-0.45, 0.3], [0, 0.3], [0.45, 0.3], [-0.22, 0.62], [0.22, 0.62], [0, 0.94]];
        for (let i = 0; i < Math.min(e.store.log, slots.length); i++) {
          const m = new THREE.Mesh(logGeo, logMat);
          m.castShadow = m.receiveShadow = true;
          m.position.set(-0.45 + slots[i][0], slots[i][1] - 0.1, 0);
          pile.add(m);
        }
        for (let i = 0; i < Math.min(e.store.stone, 6); i++) {
          const m = new THREE.Mesh(stoneGeo, stoneMat);
          m.castShadow = m.receiveShadow = true;
          m.position.set(0.7, 0.3 + Math.floor(i / 3) * 0.4, -0.5 + (i % 3) * 0.5);
          m.rotation.y = i;
          pile.add(m);
        }
      },
    };
  }

  /** The site rises stage by stage; the stage in progress grows with the crew's labour. */
  make_site(e) {
    const root = new THREE.Group();
    root.position.set(e.x, this.ground(e.x, e.z), e.z);
    const H = 1.55; // half size of the footprint
    const corners = [[-H, -H], [H, -H], [-H, H], [H, H]];
    const stakes = corners.map(([x, z]) => env(post(0.04, 0.03, 0.6, x * 1.1, 0, z * 1.1, 4), { layer: L.PLANK }));
    const ropes = [[0, -H * 1.1, H * 2.2, 0.04], [0, H * 1.1, H * 2.2, 0.04], [-H * 1.1, 0, 0.04, H * 2.2], [H * 1.1, 0, 0.04, H * 2.2]]
      .map(([x, z, w, d]) => env(box(w, 0.03, d, x, 0.5, z), { layer: L.THATCH, tint: 0xfff2d0 }));
    const marker = this.mesh(merge([...stakes, ...ropes]), this.solid);
    root.add(marker);

    const part = (geo, layer, tint) => { const m = this.mesh(geo, this.mat(layer, tint)); root.add(m); return m; };
    const cleared = part(new THREE.BoxGeometry(H * 2.1, 0.04, H * 2.1).translate(0, 0.02, 0), L.EARTH, 0xb89870);
    const stones = corners.map(([x, z]) => part(new THREE.BoxGeometry(0.42, 0.24, 0.42).translate(0, 0.12, 0), L.GRANITE).translateX(x).translateZ(z));
    const pillars = corners.map(([x, z]) => part(new THREE.BoxGeometry(0.2, 2.2, 0.2).translate(0, 1.1, 0), L.DARKWOOD, 0xd8b088).translateX(x).translateY(0.24).translateZ(z));
    const beams = [
      part(new THREE.BoxGeometry(H * 2 + 0.4, 0.18, 0.2).translate(0, 2.5, -H), L.DARKWOOD, 0xd8b088),
      part(new THREE.BoxGeometry(H * 2 + 0.4, 0.18, 0.2).translate(0, 2.5, H), L.DARKWOOD, 0xd8b088),
      part(new THREE.BoxGeometry(0.2, 0.18, H * 2 + 0.4).translate(-H, 2.62, 0), L.DARKWOOD, 0xd8b088),
      part(new THREE.BoxGeometry(0.2, 0.18, H * 2 + 0.4).translate(H, 2.62, 0), L.DARKWOOD, 0xd8b088),
      part(new THREE.BoxGeometry(0.16, 0.6, 0.16).translate(0, 2.95, 0), L.DARKWOOD, 0xd8b088),
      part(new THREE.BoxGeometry(H * 2 + 0.6, 0.2, 0.22).translate(0, 3.3, 0), L.DARKWOOD, 0xe8c090),
    ];
    const gohei = this.sprite(this.tex.shide, 1, [0.3, 0.6], 'prop', 16, 32);
    gohei.position.y = 3.4;
    root.add(gohei);
    // delivered materials waiting to be used, beside the footprint
    const waiting = new THREE.Group();
    waiting.position.set(H + 0.9, 0, 0);
    root.add(waiting);
    const logMat = this.mat(L.BARK, 0xd8c0a0), stoneMat = this.mat(L.GRANITE, 0xd0ccc4);
    const logGeo = new THREE.CylinderGeometry(0.17, 0.19, 1.3, 8).rotateX(Math.PI / 2), stoneGeo = new THREE.DodecahedronGeometry(0.24).scale(1.1, 0.8, 1);

    const stageIndex = id => e.site.stages.findIndex(s => s.id === id);
    const grow = (meshes, k) => meshes.forEach(m => { m.visible = k > 0.01; m.scale.y = Math.max(0.01, k); });
    return {
      root, hl: marker, key: '',
      sync(e) {
        const site = e.site, idx = site.index;
        const progress = id => { const i = stageIndex(id); return i < 0 ? 0 : i < idx ? 1 : i === idx ? site.labour : 0; };
        cleared.visible = progress('clear') > 0.01; cleared.scale.set(Math.max(0.05, progress('clear')), 1, Math.max(0.05, progress('clear')));
        grow(stones, progress('stones'));
        grow(pillars, progress('pillars'));
        const b = progress('beam');
        beams.forEach((m, i) => { m.visible = b > i / beams.length; });
        gohei.visible = site.complete;
        const got = site.stage ? site.stage.got : {};
        const key = JSON.stringify(got) + idx;
        if (key !== this.key) {
          this.key = key;
          waiting.clear();
          for (let i = 0; i < (got.log || 0); i++) { const m = new THREE.Mesh(logGeo, logMat); m.castShadow = true; m.position.set(0, 0.18 + i * 0.36, 0); waiting.add(m); }
          for (let i = 0; i < (got.stone || 0); i++) { const m = new THREE.Mesh(stoneGeo, stoneMat); m.castShadow = true; m.position.set(0.1, 0.18, -0.9 + i * 0.5); waiting.add(m); }
        }
      },
    };
  }

  // ------------------------------------------------------------------ the shrine and the onibi

  make_shrine(e) {
    // the shrine is a prop; add the shimenawa that marks it as the one thing nothing can be taken from
    const shrine = this.props.getObjectByName('shrine') || null;
    const y = this.ground(e.x, e.z + 1.2);
    const root = new THREE.Group();
    root.position.set(e.x, y, e.z + 0.95);
    const pts = [];
    for (let i = 0; i <= 12; i++) { const t = i / 12; pts.push(new THREE.Vector3(-1.0 + 2 * t, 1.25 - Math.sin(t * Math.PI) * 0.16, 0)); }
    const rope = this.mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.065, 6), new THREE.MeshLambertMaterial({ color: 0xe0c888 }));
    root.add(rope);
    for (const x of [-0.5, 0, 0.5]) {
      const s = this.sprite(this.tex.shide, 1, [0.18, 0.36], 'prop', 16, 32);
      s.position.set(x, 1.25 - Math.sin((x + 1) / 2 * Math.PI) * 0.16 - 0.4, 0.02);
      root.add(s);
    }
    return { root, hl: shrine || rope, sync() {} };
  }

  make_yokai(e) {
    const root = new THREE.Group();
    const s = new THREE.Mesh(UPRIGHT_QUAD, new THREE.MeshBasicMaterial({ map: this.tex.onibi.clone(), transparent: true, alphaTest: 0.4, fog: true, depthWrite: true }));
    const tex = s.material.map;
    tex.needsUpdate = true;
    tex.repeat.set(1 / 4, 1 / 2);
    s.scale.set(0.95, 0.95, 1);
    s.userData.sprite = { size: [0.9, 0.9], setOutline() {} };
    const halo = this.glow(0xff8a4a, 2.2);
    halo.position.y = 0.5;
    root.add(halo, s);
    const self = this;
    return {
      root, hl: s, y: null, faceCam: true,
      sync(e, dt, t) {
        const calm = !!e.state.calm, h = e.holder.q.h;
        const size = 0.75 + Math.min(h, 5) * 0.12;
        s.scale.set(size, size, 1);
        tex.offset.set((Math.floor(t * 8 + e.id) % 4) / 4, calm ? 0 : 0.5);
        halo.material.color.set(calm ? 0x9fd8ff : 0xff8a4a);
        halo.material.opacity = 0.6 + 0.15 * Math.sin(t * 9);
        halo.scale.setScalar(1.4 + size);
        const gy = self.ground(e.x, e.z) + 0.35 + Math.sin(t * 2.4 + e.id) * 0.12;
        this.y = this.y === null ? gy : approach(this.y, gy, 6, dt);
        root.position.set(e.x, this.y, e.z);
        if (self.camera) s.quaternion.copy(self.camera.quaternion);
      },
    };
  }
}

function crisp(t) {
  t.magFilter = THREE.NearestFilter;
  return t;
}
