// Segment 1, assembled: the title, the prologue 「送魂夜」 and the first morning.
// Owns the frame loop and wires the pieces together; each piece stays testable alone:
//   field (src/game/field.js), director (src/story/cine.js), scenes (src/story/seg1.js),
//   story UI and title (src/story/*), HUD (src/ui/hud.js), the renderer behind the stage
//   adapter (src/app/stage.js), audio (src/audio/audio.js).
// URL switches for checking: ?scene=prologue|day1 skips the title, ?fast=N runs the scene
// clock N times faster, ?touch=1 forces the touch controls, ?manual=1 hands the clock to a
// checking tool (window.APP.tick / APP.render).

import { params } from '../core/params.js';
import { Input } from '../core/input.js';
import { AU } from '../audio/audio.js';
import { Field } from '../game/field.js';
import { Director } from '../story/cine.js';
import { StoryUI } from '../story/ui.js';
import { TitleScreen, loadPrefs } from '../story/title.js';
import { Insets } from '../story/inset.js';
import { prologue, day1 } from '../story/seg1.js';
import { HUD } from '../ui/hud.js';
import { createStage } from './stage.js';
import { createVistaView } from './vistaview.js';
import { loadSave, writeSave } from './save.js';
import { portraits } from './portraits.js';
import { createFieldAmbience } from '../audio/field.js';
import night from '../../assets/audio/night.mp3';
import night2 from '../../assets/audio/night2.mp3';
import wind from '../../assets/audio/wind.mp3';
import stream from '../../assets/audio/stream.mp3';
import fall from '../../assets/audio/fall.mp3';
import crow from '../../assets/audio/crow.mp3';
import birds from '../../assets/audio/birds.mp3';

const PX = 20; // native pixels per metre: the audio engine's distances are in pixels

export async function boot(app) {
  const touch = params.touch || matchMedia('(pointer: coarse)').matches;
  const ui = el('div', 'ui', app);

  // ---- audio: silent until the first gesture; distances in metres become pixels
  let audioOn = false;
  // real field recordings for wind, water, insects and birds (assets/audio, CC0 / public domain)
  const fieldAmb = createFieldAmbience(AU, { sources: { night, night2, wind, stream, fall, crow, birds } });
  const startAudio = () => {
    if (audioOn) return; audioOn = AU.init(); AU.resume?.();
    if (audioOn) fieldAmb.load();
    applyPrefs(loadPrefs());
  };
  const au = {
    ...AU,
    sfx: (n, o) => AU.sfx(n, o && Number.isFinite(o.x) ? { ...o, x: o.x * PX, y: o.y * PX } : o),
  };
  const applyPrefs = p => { AU.setVolume?.('master', p.volume); story.speed = p.textSpeed; };

  // ---- the pieces
  const D = new Director({ audio: au });
  const story = new StoryUI(ui, { audio: au, portraits, wait: s => D.wait(s) });
  D.ui = story;
  const f = new Field();
  // the title is on screen at once, over its own backdrop; the map bakes behind it
  const vv = createVistaView(app);
  const skipTitle = !!params.scene;
  let titleRun = null;
  if (!skipTitle) {
    vv.show({ shot: 'title', tod: 21 });
    let t0 = performance.now();
    const pre = now => { if (!titleRun?.stagedUp) { vv.draw(Math.min(0.1, (now - t0) / 1000)); t0 = now; requestAnimationFrame(pre); } };
    requestAnimationFrame(pre);
    titleRun = showTitle();
    await new Promise(r => setTimeout(r, 60));   // let the title paint before the bake blocks
  }
  const stage = await createStage({ root: app, field: f, vistaView: vv });
  if (titleRun) titleRun.stagedUp = true;
  f.ground = stage.ground;
  D.stage = stage;
  const insets = new Insets(ui);
  stage.inset = (kind, on) => insets.show(kind, on);
  const input = new Input(stage.canvas, ui);
  const hud = new HUD(ui, { field: f, project: (x, z, h) => stage.project(x, z, h), audio: au, touch });
  input.onTouch = () => { hud.mountTouch(); startAudio(); };
  stage.canvas.addEventListener('pointerdown', e => {   // tap a thing to choose it
    startAudio();
    if (!f.control) return;
    const e2 = stage.pick(e.clientX, e.clientY);
    if (e2) f.targeting.pick({ x: e2.x, z: e2.z, priority: e2.priority, ref: e2 });
  });
  addEventListener('keydown', startAudio, { once: true });
  applyPrefs(loadPrefs());

  const listeners = new Set();
  const G = {
    D, f, stage, ui: story, hud, au, P: stage.places, touch,
    on(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    save(s) { writeSave(s); },
  };
  window.APP = { G, AU };

  // ---- the frame loop
  let last = performance.now();
  if (params.fast > 1) D.rate = params.fast;
  const frame = now => {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    tick(dt);
    stage.render();
    requestAnimationFrame(frame);
  };
  function tick(dt) {
    input.update();
    const blocked = story.blocking;
    f.update(dt, blocked ? { mx: 0, mz: 0 } : { mx: input.move.x, mz: -input.move.y });
    for (const e of f.drain()) { stage.fx?.(e); for (const fn of [...listeners]) fn(e); }
    D.tick(dt);
    story.update(dt * (D.rate || 1));
    stage.update(dt);
    hud.update(dt);
    if (audioOn) {
      AU.update(dt, { tod: G.hour ?? 12, listener: { x: f.player.x * PX, y: f.player.z * PX }, near: stage.nearness?.() ?? 1, cinematic: D.busy, wind: 0.3, biome: stage.biome?.() });
      const wf = stage.places?.waterfall;
      fieldAmb.update(dt, wf ? { waterDist: Math.hypot(wf[0] - f.player.x, wf[1] - f.player.z), waterPan: Math.max(-1, Math.min(1, (wf[0] - f.player.x) / 30)) } : {});
    }
  }
  window.APP.tick = tick;
  window.APP.render = () => stage.render();
  // ?manual=1: the checking tools drive the clock themselves (tick without drawing, draw on demand)
  if (!params.manual) requestAnimationFrame(frame);

  stage.prepareVista?.();   // the treetop shots are built in slices while she climbs the pass
  // ---- title → prologue → day 1 → end card → title
  const run = async from => {
    if (from === 'prologue') { await prologue(G); from = 'day1'; }
    if (from === 'day1') { stage.reset?.('day1'); await day1(G); }
    await D.wait(1.5);
    location.reload(); // back to the title, with 继续 offered from the save
  };
  if (skipTitle) { stage.reset?.(params.scene); run(params.scene); }
  else {
    stage.vista({ shot: 'title', tod: 21 });
    const choice = await titleRun.choice;
    AU.music('none', { fade: 0.04 });          // the flute stops mid-phrase
    titleRun.screen.hide();
    await story.fade(1, 1.0);
    stage.vista(null);
    stage.reset?.(choice);
    run(choice);
  }

  /** The title menu; resolves with where to begin once the player chooses (the bake may still run). */
  function showTitle() {
    const saved = loadSave();
    let chosen = false, done;
    const choice = new Promise(r => { done = r; });
    const screen = new TitleScreen(ui, {
      canContinue: !!saved && saved.stage !== 'prologue', touch,
      onFirstInput: () => { startAudio(); setTimeout(() => { if (!chosen) AU.music('title', { fade: 1, restart: true }); }, 250); },
      onPrefs: applyPrefs,
      onChoose: a => {
        if (chosen) return;
        chosen = true;
        startAudio();
        done(a === 'continue' ? 'day1' : 'prologue');
      },
    });
    return { screen, choice };
  }
}

function el(tag, cls, parent) { const e = document.createElement(tag); e.className = cls; parent.appendChild(e); return e; }
