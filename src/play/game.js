// The playable gray box (G3): the HD-2D render foundation, the simulation fitted to the test
// terrain, the approved control scheme A on keyboard and touch, and the five-step feedback for
// every transfer (target shown before pressing → cast → stream → arrival → the thing changes).
// Test hooks: window.APP (sim, tick, rig, stats, …) and window.DONE after the first frame.
// URL: ?q=low|high, ?t=morning|noon|evening|night, ?dof=0, ?debug=1, ?touch=1.

import * as THREE from 'three';
import { params } from '../core/params.js';
import { Input } from '../core/input.js';
import { clamp } from '../core/math.js';
import { RenderContext, detectTier } from '../render/renderer.js';
import { CameraRig } from '../render/camera.js';
import { Lighting, PRESET_ORDER } from '../render/lighting.js';
import { PostChain } from '../render/post.js';
import { OcclusionCutout } from '../render/occlusion.js';
import { Highlighter } from '../render/highlight.js';
import { ProxySet } from '../render/proxies.js';
import { shared } from '../render/materials.js';
import { layerArray } from '../render/textures.js';
import { terrainLayers } from '../world/art.js';
import { buildTestScene } from '../world/testScene.js';
import { WATER_Y } from '../world/terrain.js';
import { Sim } from '../game/sim.js';
import { bodyState, QUALITY_INFO } from '../game/qualities.js';
import { Actions } from '../ui/actions.js';
import { TargetPrompt } from '../ui/prompt.js';
import { BodyGauge } from '../ui/body.js';
import { TransferFx } from '../fx/transfer.js';
import { AU } from '../audio/audio.js';
import { FIELD } from './layout.js';
import { attachTerrain } from './ground.js';
import { StationViews } from './views.js';
import { Actors } from './actors.js';

const PRESET_HOURS = { morning: 7, noon: 12, evening: 17.5, night: 22 };
const presetFor = h => { h = ((h % 24) + 24) % 24; return h >= 5 && h < 9.5 ? 'morning' : h < 16 ? 'noon' : h < 19 ? 'evening' : 'night'; };

export function startGame(app) {
  const canvas = document.createElement('canvas');
  canvas.className = 'view';
  const ui = document.createElement('div');
  ui.className = 'ui';
  app.append(canvas, ui);

  // ---- render stack (as in the render test) ------------------------------------------------
  const ctx = new RenderContext(canvas, { tier: params.quality ?? detectTier(), auto: !params.quality });
  const renderer = ctx.renderer;
  const scene = new THREE.Scene();
  const rig = new CameraRig({ fov: 24, pitch: 32 });
  const proxies = new ProxySet();
  const lighting = new Lighting(scene, proxies, ctx.tier);
  const world = buildTestScene({ scene, lighting, proxies });
  const jar = scene.getObjectByName('jar'); // the render test's highlight probe; not part of the gray box
  if (jar) { jar.removeFromParent(); world.colliders = world.colliders.filter(c => !(c.r === 0.35 && Math.abs(c.x - jar.position.x) < 0.01)); }
  const post = new PostChain(renderer, scene, rig.camera, ctx.tier, { dof: params.dof });
  const occlusion = new OcclusionCutout(proxies);
  const highlighter = new Highlighter(scene);
  const input = new Input(canvas, ui);
  const terrain = world.terrain;

  // ---- simulation fitted to the terrain ----------------------------------------------------
  const sim = Sim.arena(FIELD);
  sim.hour = PRESET_HOURS[params.time] ?? 12;
  const { nav } = attachTerrain(sim, terrain, world.colliders);

  // ---- presentation ------------------------------------------------------------------------
  const fx = new TransferFx(scene);
  const sound = (name, e, k = 1) => {
    if (name === 'bell') AU.sfx('offering', { ...at(e), gain: k });
    if (name === 'clack') AU.sfx('place', at(e));
  };
  const at = e => ({ x: e.x * 20, y: e.z * 20 }); // audio space: the legacy mixer works in 20 px per metre
  const views = new StationViews({ scene, sim, terrain, layers: layerArray(terrainLayers()), propsGroup: scene, fx, sound });
  views.camera = rig.camera;
  const actors = new Actors({ scene, sim, terrain, rig, lighting, fx });
  const actions = new Actions(ui);
  const prompt = new TargetPrompt(ui);
  const gauge = new BodyGauge(ui);
  const help = helpCard(ui);
  const touch = params.touch || matchMedia?.('(pointer: coarse)').matches || navigator.maxTouchPoints > 0;
  if (touch) { actions.mountTouchPad(); help.hide(); }
  input.onTouch = () => { actions.mountTouchPad(); help.hide(); };

  // audio needs a gesture
  const wake = () => { if (!AU.ready) AU.init(); AU.resume(); AU.music?.('none'); };
  addEventListener('pointerdown', wake, { capture: true });
  addEventListener('keydown', wake, { capture: true });

  // ---- verbs ---------------------------------------------------------------------------------
  const queue = [];
  actions.on(a => queue.push(a));
  const say = text => { if (text) prompt.say(text); };

  function handle(a) {
    const P = sim.player;
    switch (a.type) {
      case 'take': case 'give': case 'release':
        sim.transfer(a.type, a.k);
        break;
      case 'context': {
        const label = sim.context();
        if (label) { say(label); AU.sfx(label === '太重了' ? 'deny' : label === '归还' ? 'offering' : label === '收获' ? 'build_done' : 'pickup', at(P)); }
        break;
      }
      case 'dispatch': {
        const label = sim.dispatch();
        say(label || (sim.target ? '搬不了这个' : ''));
        if (label) AU.sfx(label === '去搬' ? 'ui_ok' : 'ui_move', at(P));
        break;
      }
      case 'recall': sim.recall(); say('回来'); AU.sfx('ui_back', at(P)); break;
      case 'cycle': sim.targeting.cycle(); AU.sfx('ui_move', at(P)); break;
      case 'dodge': if (sim.dodge()) AU.sfx('wobble', { ...at(P), amt: 0.2 }); break;
      case 'rotateLeft': rig.rotate(-1); break;
      case 'rotateRight': rig.rotate(1); break;
      case 'releaseArmed': say('放：选一种性质'); break;
      default: break;
    }
  }

  const posOf = (e, lift = 0.8) => {
    if (e === 'player') { const p = actors.player.position; return new THREE.Vector3(p.x, p.y + 0.9, p.z); }
    return new THREE.Vector3(e.x, (e.kind === 'pond' ? WATER_Y : terrain.heightAt(e.x, e.z)) + lift, e.z);
  };

  function react(ev) {
    const P = sim.player;
    switch (ev.type) {
      case 'fx': {
        const from = posOf(ev.from), to = posOf(ev.to);
        AU.sfx(ev.verb === 'take' ? 'take' : 'give', at(P));
        fx.stream(from, to, new THREE.Color(ev.color), {
          onLand: () => {
            fx.ring(to.clone().setY(to.y - 0.7), new THREE.Color(ev.color), 1.4);
            AU.sfx('qual', { ...at(P), k: ev.k, verb: ev.verb, n: P.holder.q[ev.k] });
          },
        });
        break;
      }
      case 'burst': {
        const c = new THREE.Color(QUALITY_INFO[ev.k].color);
        fx.ring(posOf('player').setY(actors.player.position.y + 0.05), c, 3.2);
        AU.sfx('release', at(P));
        AU.sfx('qual', { ...at(P), k: ev.k, verb: 'release', n: P.holder.q[ev.k] });
        break;
      }
      case 'refused':
        prompt.say(ev.reason, ev.k);
        AU.sfx('deny', at(P));
        shake = 0.18;
        break;
      case 'gate': AU.sfx(ev.open ? 'unstone' : 'stone', at(sim.gateEntity)); break;
      case 'broke': AU.sfx('fall', { ...at(ev.e), size: 0.7 }); break;
      case 'fell': AU.sfx('splash', { ...at(P), size: 0.6 }); say('扑通'); break;
      case 'stored': case 'delivered': AU.sfx('place', at(ev.e || P)); break;
      case 'stage': AU.sfx('build', at(ev.e)); break;
      case 'ceremony': AU.sfx('build_done', at(ev.e)); fx.ring(posOf(ev.e, 2.6), new THREE.Color(0xffe08a), 4); break;
      case 'complete': AU.sfx('build_done', at(ev.e)); break;
      case 'grew': AU.sfx('leaf', at(ev.e)); break;
      case 'harvest': break;
      case 'ignite': AU.sfx('qual', { ...at(ev.e), k: 'h', verb: 'give', n: 6 }); break;
      case 'stolen': prompt.say('热被偷走了'); AU.sfx('unleaf', at(P)); break;
      case 'hurt': shake = 0.25; break;
      case 'calmed': say('平静下来了'); AU.sfx('offering', at(ev.e)); break;
      case 'killed': say('……消散了'); AU.sfx('unleaf', at(ev.e)); fx.ring(posOf(ev.e, 0.3), new THREE.Color(0x88aacc), 2.4); break;
      case 'joined': say('加入了队伍'); AU.sfx('ui_ok', at(P)); break;
      case 'returned': fx.ring(posOf('player').setY(actors.player.position.y + 0.05), new THREE.Color(0xffffff), 2.2); break;
      default: break;
    }
  }

  // ---- frame ---------------------------------------------------------------------------------
  lighting.onPreset(p => post.applyPreset(p));
  lighting.setPreset(presetFor(sim.hour));
  function resize() { ctx.resize(); rig.resize(ctx.width, ctx.height); post.setSize(ctx.width, ctx.height); }
  addEventListener('resize', resize);
  ctx.onTierChange(tier => { lighting.setTier(tier); post.build(tier); resize(); });
  resize();

  let shake = 0, lastTarget = null, rendered = false, time = 0;
  const focus = new THREE.Vector3(), shadowCenter = new THREE.Vector3(), vel = new THREE.Vector3(), lastPos = new THREE.Vector3();
  const tmp = new THREE.Vector3();
  const lanternLight = () => lighting.lights.find(l => Math.hypot(l.position.x - FIELD.lantern[0], l.position.z - FIELD.lantern[1]) < 0.5);

  /** One frame. render = false advances everything but skips drawing (scripted tests). */
  function tick(dt, render = true) {
    dt = Math.min(dt, 0.1);
    time += dt;
    input.update();
    for (const a of ['rotateLeft', 'rotateRight', 'cycle']) input.consume(a); // owned by the action layer
    if (input.consume('zoom')) rig.cycleZoom();
    if (input.consume('time')) { const next = PRESET_ORDER[(PRESET_ORDER.indexOf(lighting.presetName) + 1) % PRESET_ORDER.length]; sim.hour = PRESET_HOURS[next]; }
    while (queue.length) handle(queue.shift());

    const m = input.move;
    const mx = rig.right.x * m.x + rig.forward.x * m.y, mz = rig.right.z * m.x + rig.forward.z * m.y;
    sim.update(dt, { mx, mz });
    for (const ev of sim.drain()) react(ev);
    if (presetFor(sim.hour) !== lighting.presetName) lighting.setPreset(presetFor(sim.hour));

    views.lanternLevel = lighting.preset?.lanterns ?? 0;
    views.sync(dt);
    actors.update(dt, time);
    fx.update(dt);

    // target: outline + prompt, shown before any button is pressed
    if (sim.target !== lastTarget) {
      lastTarget = sim.target;
      highlighter.highlight(sim.target ? views.objectFor(sim.target) : null, { color: sim.target?.holder.sacred ? 0xffffff : 0xffe27a });
      if (sim.target) AU.sfx('ui_move', { pan: 0, gain: 0.4 });
    }
    const P = sim.player, t = sim.target;
    if (t) {
      tmp.copy(posOf(t, t.kind === 'site' ? 3.2 : t.kind === 'gate' || t.kind === 'bell' ? 2.6 : 1.5)).project(rig.camera);
      prompt.update(dt, { name: t.name, holder: t.holder, status: statusOf(t) }, (tmp.x + 1) / 2 * innerWidth, (1 - tmp.y) / 2 * innerHeight);
    } else prompt.update(dt, null);
    actions.setContext(sim.contextLabel(), P.holder.q);
    gauge.update(P.holder);

    // camera follows her body (with the dodge/hurt shake)
    const pos = actors.player.position;
    vel.subVectors(pos, lastPos).divideScalar(Math.max(dt, 1e-3)); lastPos.copy(pos);
    shake = Math.max(0, shake - dt);
    focus.set(pos.x + (Math.random() - 0.5) * shake * 0.6, pos.y, pos.z + (Math.random() - 0.5) * shake * 0.6);
    rig.update(dt, focus, vel);
    shared.uTime.value += dt;
    shared.uStretch.value = rig.billboardStretch;

    const zoomScale = clamp(rig.dist.x / 26, 0.9, 2.6);
    lighting.extentScale = zoomScale;
    shadowCenter.copy(rig.focus).addScaledVector(rig.forward, 4 * zoomScale);
    shadowCenter.y = pos.y;
    lighting.update(dt, shadowCenter, rig.camera, actors.characters);
    actors.tintPlayer();
    const lamp = lanternLight();
    const lanternE = sim.entities.find(e => e.kind === 'lantern');
    if (lamp && lanternE) lamp.intensity = lamp.userData.base * (lighting.preset?.lanterns ?? 0) * Math.min(1, lanternE.holder.q.l);
    occlusion.update(dt, rig.camera, renderer, actors.player);
    highlighter.update(dt, renderer);
    AU.update(dt, {
      tod: sim.hour % 24, listener: at(P), wind: 0.25, heavy: Math.min(1, Math.max(0, P.holder.q.w - P.holder.base.w) / 4),
      water: clamp(1 - Math.abs(P.z - 11) / 9, 0, 1), biome: { forest: 0.7, stream: clamp(1 - Math.abs(P.z - 11) / 7, 0, 1), meadow: 0.5, shrine: clamp(1 - Math.hypot(P.x + 2.5, P.z + 7.2) / 10, 0, 1) },
    });

    if (!render) return;
    renderer.info.reset();
    post.render(dt, focus.set(pos.x, pos.y + 0.7, pos.z));
    if (!rendered) { rendered = true; window.DONE = true; }
  }

  function statusOf(t) {
    if (t.kind === 'site') {
      const s = t.site;
      if (s.complete) return '完工';
      const miss = Object.entries(s.missing()).map(([m, n]) => `${m === 'log' ? '原木' : m === 'stone' ? '石块' : m}×${n}`).join(' ');
      return `${s.stage.label} ${'▮'.repeat(Math.round(s.labour * 5))}${'▯'.repeat(5 - Math.round(s.labour * 5))}${miss ? ' · 缺 ' + miss : ' · 需要小伙伴在旁'}`;
    }
    if (t.kind === 'plot') {
      const p = t.plot;
      if (!p.crop) return '空地';
      if (p.ripe) return '可以收获';
      const why = p.check();
      return `胡瓜 ${p.stage}/4${why ? ' · 缺' + ({ l: '光', h: '热', water: '水', shade: '阴凉', cold: '寒' }[why] || why) : ''}`;
    }
    if (t.kind === 'yard') return `原木 ${t.store.log} · 石块 ${t.store.stone}`;
    if (t.kind === 'gate') return t.state.open ? '开着' : '关着 · 压板连着它';
    if (t.kind === 'plate') return t.state.pressed ? '压下了' : '要有足够的重量';
    if (t.kind === 'bridge') return t.state.broken ? '塌了' : '朽了，太重会塌';
    if (t.kind === 'pond') return t.holder.q.h <= 0 ? '结冰了' : '';
    if (t.kind === 'yokai') return t.state.calm ? '平静' : '饥饿：太热了';
    if (t.haul) { const job = sim.crew.jobs.find(j => j.item.ref === t); return job ? (sim.crew.shortfall(job) ? `还需要 ${sim.crew.shortfall(job)} 个` : '正在搬') : t.holder.q.w <= 1 ? '可以背起' : `需要 ${Math.ceil(t.holder.q.w)} 个小伙伴`; }
    return '';
  }

  function stats() {
    const r = renderer.info.render;
    return { calls: r.calls, triangles: r.triangles, tier: ctx.tier.name, dpr: +renderer.getPixelRatio().toFixed(3), size: `${ctx.width}x${ctx.height}`, passes: post.describe() };
  }

  const simulate = sec => { for (let i = Math.round(sec * 30); i > 0; i--) tick(1 / 30, i === 1); };
  window.APP = { tick, simulate, sim, rig, renderer, scene, camera: rig.camera, lighting, post, actors, views, highlighter, nav, actions, prompt, stats, handle };
  rig.snap(actors.player.position);
  actors.update(0, 0);
  views.sync(0);
  lighting.updateCharacter(actors.player, 0, true);
  let last = performance.now();
  function frame(now) {
    requestAnimationFrame(frame);
    const ms = now - last;
    last = now;
    ctx.sampleFrame(ms, now);
    if (!window.MANUAL) tick(ms / 1000);
  }
  requestAnimationFrame(frame);
}

/** Desktop key reference; hidden on touch devices and collapsible with H. */
function helpCard(root) {
  const el = document.createElement('div');
  el.className = 'help-card';
  el.innerHTML = `<b>操作</b>
    <div>WASD 移动 · [ ] 转镜头 · Z 缩放 · T 时段</div>
    <div>1–5 取 重熱光音生 · Shift+1–5 予 · L 再按 1–5 放</div>
    <div>E 情境动作 · F 派小伙伴搬 · R 召回 · Tab 换目标 · Space 闪避</div>
    <b>试一试</b>
    <div>取巨石的重，给桥头的压板，门就开了；按 F 让小伙伴把南岸的原木搬回来，再看工地一层层立起来。</div>
    <div>溪水取熱会结冰；身体轻了能走朽桥；神棚可以把身体还原。</div>
    <div class="dim">H 收起</div>`;
  root.appendChild(el);
  const s = document.createElement('style');
  s.textContent = `.help-card { position: fixed; right: calc(12px + env(safe-area-inset-right, 0px)); top: calc(12px + env(safe-area-inset-top, 0px)); z-index: 14; max-width: 330px; padding: 8px 11px; border-radius: 8px; background: rgba(20,16,24,.5); color: #f1ece0; font: 500 12px/1.6 "Noto Sans SC", system-ui, sans-serif; pointer-events: none; }
    .help-card b { font: 700 13px/1.4 "Noto Serif SC", serif; } .help-card .dim { opacity: .6; } .help-card.off { display: none; }`;
  document.head.appendChild(s);
  addEventListener('keydown', e => { if (e.code === 'KeyH') el.classList.toggle('off'); });
  return { hide() { el.classList.add('off'); } };
}
