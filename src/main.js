// Entry: wires the HD-2D render foundation to the gray-box test scene and a tiny test controller.
// Test hooks: window.DONE after the first rendered frame; window.APP exposes tick(dt) and the
// renderer, camera and systems. ?q=low|high, ?t=morning|noon|evening|night, ?dof=0, ?debug=1.

import * as THREE from 'three';
import { params } from './core/params.js';
import { Input } from './core/input.js';
import { Hud } from './core/hud.js';
import { approach, clamp } from './core/math.js';
import { RenderContext, detectTier } from './render/renderer.js';
import { CameraRig } from './render/camera.js';
import { Lighting, PRESET_ORDER } from './render/lighting.js';
import { PostChain } from './render/post.js';
import { OcclusionCutout } from './render/occlusion.js';
import { Highlighter } from './render/highlight.js';
import { ProxySet } from './render/proxies.js';
import { shared } from './render/materials.js';
import { createSprite } from './render/sprites.js';
import { pixelTexture } from './render/textures.js';
import { characterSheet, SHEET } from './world/art.js';
import { buildTestScene } from './world/testScene.js';
import { SITE } from './world/terrain.js';

const app = document.getElementById('app');
const canvas = document.createElement('canvas');
canvas.className = 'view';
const ui = document.createElement('div');
ui.className = 'ui';
app.append(canvas, ui);

const ctx = new RenderContext(canvas, { tier: params.quality ?? detectTier(), auto: !params.quality });
const renderer = ctx.renderer;
const scene = new THREE.Scene();
const rig = new CameraRig({ fov: 24, pitch: 32 });
const proxies = new ProxySet();
const lighting = new Lighting(scene, proxies, ctx.tier);
const world = buildTestScene({ scene, lighting, proxies });
const post = new PostChain(renderer, scene, rig.camera, ctx.tier, { dof: params.dof });
const occlusion = new OcclusionCutout(proxies);
const highlighter = new Highlighter(scene);
const input = new Input(canvas, ui);
const hud = new Hud(ui, input, { debug: params.debug });

// --- Player stand-in (protected character sprite) and a minimal controller for testing ---------

const player = createSprite({
  sheet: { texture: pixelTexture(characterSheet()), frameW: SHEET.frameW, frameH: SHEET.frameH },
  size: [SHEET.frameW / SHEET.pxPerMetre, SHEET.frameH / SHEET.pxPerMetre],
  kind: 'character',
});
player.name = 'player';
scene.add(player);

const SPEED = 4.2;          // m/s
const BODY_R = 0.25;        // collision radius
const MAX_STEP = 0.6;       // highest ledge walked up without stairs or a ramp
const FOOT = SHEET.footPad / SHEET.pxPerMetre;
const ROWS = { front: 0, back: 1, side: 2 };

const controller = {
  pos: SITE.spawn.clone(),
  vel: new THREE.Vector3(),
  dir: new THREE.Vector2(0, -1), // world facing (x, z)
  view: 'back',                  // facing as seen by the camera
  mirror: false,
  walk: 0,

  blocked(x, z) {
    const t = world.terrain;
    const here = t.heightAt(this.pos.x, this.pos.z);
    for (const [dx, dz] of [[0, 0], [BODY_R, 0], [-BODY_R, 0], [0, BODY_R], [0, -BODY_R]]) {
      if (!t.walkable(x + dx, z + dz) || t.heightAt(x + dx, z + dz) > here + MAX_STEP) return true;
    }
    for (const c of world.colliders) {
      if (c.r !== undefined ? Math.hypot(x - c.x, z - c.z) < c.r + BODY_R
        : x > c.minX - BODY_R && x < c.maxX + BODY_R && z > c.minZ - BODY_R && z < c.maxZ + BODY_R) return true;
    }
    return false;
  },

  update(dt, move) {
    const tx = (rig.right.x * move.x + rig.forward.x * move.y) * SPEED;
    const tz = (rig.right.z * move.x + rig.forward.z * move.y) * SPEED;
    this.vel.x = approach(this.vel.x, tx, 14, dt);
    this.vel.z = approach(this.vel.z, tz, 14, dt);
    const nx = this.pos.x + this.vel.x * dt, nz = this.pos.z + this.vel.z * dt;
    if (!this.blocked(nx, this.pos.z)) this.pos.x = nx; else this.vel.x = 0;
    if (!this.blocked(this.pos.x, nz)) this.pos.z = nz; else this.vel.z = 0;
    const ground = world.terrain.heightAt(this.pos.x, this.pos.z);
    this.pos.y = approach(this.pos.y, ground, ground > this.pos.y ? 22 : 12, dt);

    const speed = Math.hypot(this.vel.x, this.vel.z);
    if (Math.hypot(tx, tz) > 0.5) this.dir.set(tx, tz).normalize();
    this.walk = speed > 0.4 ? this.walk + dt * speed * 1.45 : 0;

    // Facing relative to the camera, with hysteresis so diagonals do not flicker between rows.
    const fx = this.dir.x * rig.right.x + this.dir.y * rig.right.z;
    const fy = this.dir.x * rig.forward.x + this.dir.y * rig.forward.z;
    const sideNow = this.view === 'side';
    if (Math.abs(fx) > Math.abs(fy) * (sideNow ? 0.8 : 1.25)) { this.view = 'side'; this.mirror = fx < 0; }
    else if (Math.abs(fy) > Math.abs(fx) * (sideNow ? 1.25 : 0.8)) this.view = fy > 0 ? 'back' : 'front';
    const col = speed > 0.4 ? 1 + (Math.floor(this.walk) % 2) : 0;
    player.userData.sprite.setFrame(col, ROWS[this.view], this.view === 'side' && this.mirror);
    player.position.set(this.pos.x, this.pos.y - FOOT * shared.uStretch.value, this.pos.z);
  },
};
controller.pos.y = world.terrain.heightAt(controller.pos.x, controller.pos.z);

// --- Wiring --------------------------------------------------------------------------------------

lighting.onPreset(p => post.applyPreset(p));
lighting.setPreset(params.time);

function resize() {
  ctx.resize();
  rig.resize(ctx.width, ctx.height);
  post.setSize(ctx.width, ctx.height);
}
window.addEventListener('resize', resize);
ctx.onTierChange(tier => {
  lighting.setTier(tier);
  post.build(tier);
  resize();
});
resize();
rig.snap(controller.pos);

function cycleHighlight() {
  const p = controller.pos;
  const near = world.highlightables
    .map(o => ({ o, d: Math.hypot(o.position.x - p.x, o.position.z - p.z) }))
    .filter(e => e.d < 14)
    .sort((a, b) => a.d - b.d)
    .map(e => e.o);
  const i = near.indexOf(highlighter.target);
  highlighter.highlight(near.length ? near[(i + 1) % near.length] : null);
}

function handleActions() {
  if (input.consume('rotateLeft')) rig.rotate(-1);
  if (input.consume('rotateRight')) rig.rotate(1);
  if (input.consume('zoom')) rig.cycleZoom();
  if (input.consume('cycle')) cycleHighlight();
  if (input.consume('time')) lighting.setPreset(PRESET_ORDER[(PRESET_ORDER.indexOf(lighting.presetName) + 1) % PRESET_ORDER.length]);
}

const shadowCenter = new THREE.Vector3();
const focus = new THREE.Vector3();
let rendered = false;

function tick(dt) {
  dt = Math.min(dt, 0.1);
  input.update();
  handleActions();
  controller.update(dt, input.move);
  rig.update(dt, controller.pos, controller.vel);
  shared.uTime.value += dt;
  shared.uStretch.value = rig.billboardStretch;

  // The sun's shadow frustum covers the visible ground: a little ahead of the focus point.
  const zoomScale = clamp(rig.dist.x / 26, 0.9, 2.6);
  lighting.extentScale = zoomScale;
  shadowCenter.copy(rig.focus).addScaledVector(rig.forward, 4 * zoomScale);
  shadowCenter.y = controller.pos.y;
  lighting.update(dt, shadowCenter, rig.camera, [player]);
  occlusion.update(dt, rig.camera, renderer, player);
  highlighter.update(dt, renderer);

  renderer.info.reset();
  post.render(dt, focus.set(controller.pos.x, controller.pos.y + 0.7, controller.pos.z));
  if (!rendered) { rendered = true; window.DONE = true; }
}

function stats() {
  const r = renderer.info.render;
  return {
    calls: r.calls,
    triangles: r.triangles,
    tier: ctx.tier.name,
    dpr: +renderer.getPixelRatio().toFixed(3),
    size: `${ctx.width}x${ctx.height}`,
    passes: post.describe(),
  };
}

window.APP = {
  tick, renderer, scene, rig, camera: rig.camera, lighting, post, player, controller, world, highlighter,
  highlight: (object, opts) => highlighter.highlight(object, opts),
  setTime: name => lighting.setPreset(name),
  setTier: name => ctx.setTier(name),
  stats,
};

controller.update(0, input.move);
lighting.updateCharacter(player, 0, true);
let last = performance.now();
function frame(now) {
  requestAnimationFrame(frame);
  const ms = now - last;
  last = now;
  ctx.sampleFrame(ms, now);
  window.APP.tick(ms / 1000);
  if (params.debug) hud.updateDebug(ms, stats());
}
requestAnimationFrame(frame);
