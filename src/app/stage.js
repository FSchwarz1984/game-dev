// The stage: the 2D renderer (src/gfx) and the home map (src/env/home.js) behind the small
// adapter the scenes and the field use (see src/story/cine.js and src/story/seg1.js):
//   shot / cam / follow / tod, actor(id), prop(id), light(def), vista(state|null), setFar,
//   climbPoints(), morning(), beamFall(), places, ground(), project(), pick(), fx(event).
// Positions are metres (x east, z south, y up); the renderer works in native pixels (1 m = 20).

import { Renderer } from '../gfx/renderer.js';
import * as HOME from '../env/home.js';
import { CHARACTERS, frameAt } from '../art/characters.js';
import { QUALITY_INFO } from '../game/qualities.js';
import { Actor } from './actors.js';

const PPM = 20;
const loadImg = url => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = url; });
const hexRGB = h => { const n = parseInt(h.slice(1), 16); return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; };

/** Which renderer object each field entity is drawn by (map object or part names). */
const ENTITY_ART = { hut: 'hut', load: 'load', frame: 'oldBackFrame', shrine: 'shrine', camphor: 'camphor' };

export async function createStage({ root, field, vistaView, onProgress = null }) {
  const canvas = document.createElement('canvas');
  canvas.className = 'view';
  Object.assign(canvas.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', display: 'block', imageRendering: 'pixelated', touchAction: 'none' });
  root.appendChild(canvas);

  // ---- the map (baked once) and the renderer
  const map = HOME.createHomeMapAsync ? await HOME.createHomeMapAsync({ onProgress }) : HOME.createHomeMap({});
  const R = new Renderer(canvas, { quality: new URLSearchParams(location.search).get('q') || 'auto' });
  R.loadMap(map);
  const O = map.objects;

  // ---- character sheets: albedo + normal per sheet, keyed by albedo URL
  const sheetByUrl = new Map();
  await Promise.all(Object.values(CHARACTERS).flatMap(ch => Object.entries(ch.sheets).map(async ([key, s]) => {
    const [a, n] = await Promise.all([loadImg(s.albedo), loadImg(s.normal)]);
    sheetByUrl.set(s.albedo, R.loadSheet(ch.name + '_' + key, a, n));
    sheetByUrl.set(s.albedo + '#img', a);
  })));

  // ---- the actors: her body is the field's player
  const actors = {
    tsuzumi: new Actor('tsuzumi', field.player),
    saji: new Actor('saji'),
  };
  const ra = {};
  let slot = 0;
  for (const id of Object.keys(actors)) ra[id] = R.addActor(sheetByUrl.get(CHARACTERS[id].sheets[Object.keys(CHARACTERS[id].sheets)[0]].albedo), { slot: slot++, char: true });

  // ---- places the scenes need (src/story/seg1.js PLACES)
  const G9 = O.graves.list;
  const places = {
    start: [125, 72.1], roadUp: [[121.6, 72.2], [119.4, 71.4]],
    dosojin: [O.statues.x, O.statues.z], dosojinStand: O.statues.stand ? [O.statues.stand.x, O.statues.stand.z] : [119.4, 71.4],
    dosojinZone: { x: 116.6, z: 71.2, r: 2.4 },
    graves: G9.map(g => [g.x, g.z]), gravesStand: O.graves.stand ? [O.graves.stand.x, O.graves.stand.z] : [82.2, 60.4],
    gravesZone: { x0: Math.min(...G9.map(g => g.x)) - 2, x1: Math.max(...G9.map(g => g.x)) + 3.2, z0: G9[0].z - 1.4, z1: G9[0].z + 3.0 },
    camphor: [O.camphor.x, O.camphor.z], camphorR: O.camphor.r, camphorFoot: [O.camphor.climb[0].x, O.camphor.climb[0].z + 0.5], loadSpot: [O.load.x, O.load.z],
    wake: [O.load.x - 0.9, O.load.z + 0.8], hut: [O.hut.x, O.hut.z], hutDoor: [O.hut.door.x, O.hut.door.z + 0.9], frame: [O.oldBackFrame.x, O.oldBackFrame.z],
    shrine: [O.shrine.x, O.shrine.z], beam: [O.shrine.beam.x, O.shrine.beam.z], shrineZone: { x: O.shrine.beam.x - 0.6, z: O.shrine.beam.z + 0.8, r: 3.2 },
    rocks: [[53.2, 39.6], [46.1, 40.4]],
    eastExit: { x0: 119.75, x1: 140, z0: 66, z1: 78 },
    waterfall: [O.waterfall.x, O.waterfall.z],
  };
  // the day-1 way out sits just inside the walkable edge
  places.leave = { x0: 118.4, x1: 140, z0: 66, z1: 78 };

  // ---- props drawn as dynamic sprites
  const ground = (x, z) => map.heightAt(x, z);
  R.setHidden('dango', true);   // the plate goes on the statues' ledge, not by the shrine
  R.setHidden('load', true);    // she carries it until she leans it on the roots
  if (map.sprites.shrineIntact) R.setImage('shrine', 'shrineIntact');
  R.setHidden('eaveBeam', true);
  const L = O.statues.ledge;
  const dango = R.addSprite('dango2', { x: L.x, z: L.z, y: L.y });
  const lanterns = [];
  for (let i = 0; i < 10; i++) {
    const h = i < 9 ? G9[i].hook : null;
    const sp = R.addSprite('bonLantern', { x: h ? h.x : 0, z: h ? h.z : 0, y: h ? h.y : 0, shadow: true });
    sp.set({ hidden: i < 9 });
    lanterns.push({ sp, light: null, state: null, attachTo: null, home: h });
  }
  const rocks = places.rocks.map(([x, z], i) => R.addSprite('rock' + (i + 1), { x, z, y: ground(x, z), shadow: true }));
  let beamSprite = null;

  // prop proxies the scenes write to (state / attachTo / visible / x / z)
  const propTable = {
    dango: { set state(v) { dango.set({ image: v === 'one' ? 'dango1' : v === 'pale' ? 'dangoPale' : 'dango2' }); } },
    load: {
      _x: O.load.x, _z: O.load.z,
      set visible(v) { R.setHidden('load', !v); }, set x(v) { this._x = v; }, set z(v) { this._z = v; },
    },
  };
  for (let i = 0; i < 10; i++) {
    const ln = lanterns[i];
    propTable['lantern' + i] = {
      get state() { return ln.state; },
      set state(v) {
        ln.state = v;
        // the lit lantern's paper glows per pixel in its own sprite; marking the whole sprite
        // emissive would blow it out to a white blob (renderer note)
        ln.sp.set({ hidden: !v, image: v === 'lit' ? 'bonLanternLit' : 'bonLantern' });
        if (v === 'lit' && !ln.light) ln.light = R.addLight({ x: 0, z: 0, y: 0, color: [1, 0.68, 0.38], radius: 3.6, intensity: 1.05, flicker: 0.5 });
        if (v !== 'lit' && ln.light) { ln.light.remove(); ln.light = null; }
        placeLantern(ln);
      },
      get attachTo() { return ln.attachTo; },
      set attachTo(v) { ln.attachTo = v; placeLantern(ln); },
    };
  }
  function placeLantern(ln) {
    let x, z, y;
    if (ln.attachTo === 'tsuzumi') {
      const a = actors.tsuzumi, f = a.lastFrame, hook = f?.anchors.hook || { x: -8, y: -30 };
      x = a.x + hook.x / PPM; z = a.z - 0.05; y = ground(a.x, a.z) + a.lift + (-hook.y - 6) / PPM;
    } else if (ln.attachTo === 'load') {
      x = O.load.x + 0.35; z = O.load.z + 0.02; y = ground(O.load.x, O.load.z) + 1.1;
    } else if (ln.home) { x = ln.home.x; z = ln.home.z; y = ln.home.y; }
    else return;
    ln.sp.set({ x, z, y });
    ln.light?.set({ x, z: z + 0.05, y: y - 0.3 });
  }

  // ---- the vista overlay (title backdrop, the treetop sequence): created by main before the bake
  const VV = vistaView;
  let vstate = null;
  const figureImg = sheetByUrl.get(CHARACTERS.tsuzumi.sheets.plain.albedo + '#img');
  const figureT = { t: 0 };
  function drawFigure(g, anchors) {
    const pose = vstate?.pose || 'sit';
    const anim = pose === 'sit' ? 'sitBranch' : pose === 'shout' ? 'shout' : 'idle';
    const f = frameAt(CHARACTERS.tsuzumi, 'plain', anim, 'up', figureT.t);
    const at = pose === 'sit' ? anchors.branch : anchors.stand;
    if (!f || !at) return;
    const piv = CHARACTERS.tsuzumi.pivot, seat = pose === 'sit' ? (f.anchors.seat || { x: 0, y: 0 }) : { x: 0, y: 0 };
    const x = Math.round(at.x - piv.x - seat.x), y = Math.round(at.y - piv.y - seat.y);
    // night falls on her too: a cool shade over the sprite, a warm edge from the lights below
    const off = drawFigure.c || (drawFigure.c = document.createElement('canvas'));
    off.width = f.sw; off.height = f.sh;
    const o = off.getContext('2d');
    o.clearRect(0, 0, f.sw, f.sh);
    o.drawImage(figureImg, f.sx, f.sy, f.sw, f.sh, 0, 0, f.sw, f.sh);
    const night = Math.max(0, Math.min(1, ((vstate?.tod ?? 19) - 18.4) / 2));
    o.globalCompositeOperation = 'source-atop';
    o.fillStyle = `rgba(14, 18, 40, ${0.28 + night * 0.42})`;
    o.fillRect(0, 0, f.sw, f.sh);
    o.globalCompositeOperation = 'source-over';
    g.drawImage(off, x, y);
  }

  // ---- camera
  let follow = true, followSpeed = 4, lastHour = 12;
  const P = field.player;
  const camTo = (o, speed) => { follow = false; R.setCamera(o, speed); };

  // ---- the stage object
  const stage = {
    canvas, R, map, places,
    ground(x, z) {
      if (!map.walkable(x, z)) return 'wall';
      return map.water(x, z) > 0.35 ? 'water' : 'ground';
    },
    project(x, z, h = 0) { const [sx, sy] = R.worldToScreen(x, z, ground(x, z) + h); return { x: sx, y: sy }; },
    /** the field entity under a tapped screen point, if one is near it */
    pick(cx, cy) {
      const w = R.screenToWorld(cx, cy);
      let best = null, bd = 1.4;
      for (const e of field.entities) {
        if (e.hidden || !e.targetable) continue;
        const d = Math.hypot(e.x - w.x, e.z - w.z) - e.r * 0.6;
        if (d < bd) { bd = d; best = e; }
      }
      return best;
    },
    shot(name, { cut = false, speed } = {}) {
      const s = map.shots[name];
      if (!s) return;
      if (s.from) { camTo(s.from, 0); setTimeout(() => R.setCamera(s.to, 0.35), 0); return; } // a slow pan up the camphor
      camTo(s, cut ? 0 : speed ?? 1.4);
    },
    cam(x, z, { cut = false, speed = 1.4, y } = {}) { camTo({ x, z, y: ground(x, z) + (y || 0) }, cut ? 0 : speed); },
    follow({ speed = 4 } = {}) { follow = true; followSpeed = speed; },
    tod(h) { lastHour = h; R.setTime(h); },
    actor: id => actors[id],
    prop: id => propTable[id] || (propTable[id] = {}),
    light: def => R.addLight(def),
    setFar: (id, amount) => R.setFar(id, amount),
    scar: o => R.paintFar(o),
    climbPoints: () => [...O.camphor.climb.map(h => [h.x, h.z, h.y]), [O.camphor.top.x, O.camphor.top.z + 9, 12]],
    vista(state) {
      vstate = state;
      stage.vistaOn = !!state;
      if (state && !state.figure && state.shot !== 'title') state.figure = drawFigure;
      VV.show(state);
      canvas.style.visibility = state ? 'hidden' : 'visible';
    },
    /** the morning after the far: the marks, the pale crown, the pale dango, the dead lanterns */
    morning() {
      stage.day1 = true;
      map.applyDay1?.(R);
      dango.set({ image: 'dangoPale' });
      R.setHidden('load', false);
    },
    beamFall() {
      if (map.sprites.shrineIntact) R.setImage('shrine', 'shrine');
      const b = O.shrine.beam;
      beamSprite = R.addSprite('eaveBeam', { x: b.x, z: b.z, y: ground(b.x, b.z), shadow: true });
      R.camera.shake = 3;
    },
    reset() {},
    nearness: () => (stage.day1 ? 0.55 : 1),
    biome: () => ({ forest: 0.7, bamboo: 0, stream: 0.1, meadow: 0.4, shrine: 0.4 }),

    /** field events → what the eye sees (the sound is played by the HUD) */
    fx(e) {
      if (e.type === 'fx') {
        const src = e.verb === 'take' ? e.e : P, dst = e.verb === 'take' ? P : e.e;
        const c = hexRGB(QUALITY_INFO[e.k].color);
        const sy = ground(src.x, src.z) + 0.8, dy = ground(dst.x, dst.z) + 0.9;
        for (let i = 0; i < 14; i++) {
          const k = i / 14;
          R.fx.spawn('mote', src.x * PPM + (Math.random() - 0.5) * 10, src.z * PPM, sy * PPM + Math.random() * 8, {
            vx: (dst.x - src.x) * PPM / 0.55 * (0.8 + Math.random() * 0.4), vy: (dst.z - src.z) * PPM / 0.55, vz: ((dy - sy) * PPM + 18) / 0.55,
            g: 60, life: 0.55 + k * 0.12, c, a: 1, add: true, size: 2, fade: 0.3, light: 16, ground: false,
          });
        }
      } else if (e.type === 'refused') {
        const t = e.e || field.target;
        if (t) R.fx.burst('dust', t.x * PPM, t.z * PPM, (ground(t.x, t.z) + 0.6) * PPM, 6, { c: [0.85, 0.82, 0.78], life: 0.5, speed: 0.4, size: 1 });
      } else if (e.type === 'near') {
        const t = e.e;
        R.fx.burst('mote', t.x * PPM, t.z * PPM, (ground(t.x, t.z) + 0.5) * PPM, 22, { c: [1, 0.92, 0.7], life: 0.9, speed: 0.7, add: true, size: 1, up: 1.4 });
      } else if (e.type === 'far') {
        const t = e.e;
        R.fx.burst('mote', t.x * PPM, t.z * PPM, (ground(t.x, t.z) + 0.6) * PPM, 16, { c: [0.8, 0.86, 1], life: 1.2, speed: 0.4, add: true, size: 1, up: 1.8 });
      }
    },

    update(dt) {
      for (const a of Object.values(actors)) a.update(dt, stage);
      // while a scene turns her, her facing for choosing targets turns with her
      if (!field.control) {
        const F = { front: [0, 1], back: [0, -1], left: [-1, 0], right: [1, 0] }[actors.tsuzumi.face];
        if (F) { P.fx = F[0]; P.fz = F[1]; }
      }
      // her height follows the ground (plus a climb or a hop)
      const pairs = Object.entries(actors);
      for (const [id, a] of pairs) {
        const rec = a.draw(stage), h = ra[id];
        if (!rec) { h.set({ hidden: true }); continue; }
        let x = rec.x, z = rec.z, y = ground(a.x, a.z) + rec.up / PPM;
        // Saji on the frame: she stands on Tsuzumi's ground (her own body waits where she hopped on);
        // depth order behind the hat (front, side) or over it (back), same screen spot
        if (id === 'saji' && a.ride) {
          const lead = actors.tsuzumi, bias = z < lead.z ? -0.3 : 0.3;
          a.body.x = lead.x; a.body.z = lead.z;
          y = ground(lead.x, lead.z) + rec.up / PPM + bias; z = lead.z + bias;
        }
        h.set({ hidden: false, sheet: sheetByUrl.get(rec.albedo), frame: [rec.sx, rec.sy, rec.sw, rec.sh], anchor: [rec.pivot.x, rec.pivot.y], flip: !!rec.mirror, x, z, y });
      }
      for (const ln of lanterns) if (ln.attachTo) placeLantern(ln);
      // field entities: far amounts, the floating beam, the shouldered frame
      for (const e of field.entities) {
        const art = ENTITY_ART[e.id];
        if (art && e._far !== e.far) { e._far = e.far; R.setFar(art, e.deep ? 1 : e.far); }
        if (e.id === 'frame' && e.hidden !== e._hid) { e._hid = e.hidden; R.setHidden('oldBackFrame', e.hidden); }
        if (e.id === 'beam' && beamSprite) {
          const w = e.holder.q.w, lift = w <= 0 ? 0.55 + Math.sin(performance.now() / 420) * 0.08 : w === 1 ? 0.12 : 0;
          beamSprite.set({ y: ground(e.x, e.z) + lift, far: e.far });
        }
        if (e.id.startsWith('rock')) { const i = +e.id.slice(4); rocks[i]?.set({ far: e.far, y: ground(e.x, e.z) + (e.holder.q.w <= 0 ? 0.3 : 0) }); }
      }
      // the camera follows her, leading a little where she walks
      if (follow) {
        const a = actors.tsuzumi;
        R.setCamera({ x: a.x + P.fx * 0.9, z: a.z + P.fz * 0.6, y: ground(a.x, a.z) + a.lift, lift: 0.9 }, followSpeed);
      }
      R.setFocus(actors.tsuzumi.x, actors.tsuzumi.z, ground(actors.tsuzumi.x, actors.tsuzumi.z) + actors.tsuzumi.lift);
      figureT.t += dt;
      stage._dt = dt;
    },

    /** The checking tools tick without drawing: still move the camera, the particles and the fades. */
    advance(dt) {
      if (!R.env || vstate) return;
      R.t += dt; R.updateCamera(dt);
      R.fx.update(dt, R.env, R.view);
      R.updateFades(dt);
    },

    render() {
      const dt = stage._dt ?? 1 / 60;
      if (vstate) { VV.draw(dt); return; }
      R.render(dt);
    },
  };
  // the treetop sequence is prepared while the prologue is played
  stage.prepareVista = () => VV.vista.prepareAsync?.('south', 12).then(() => VV.vista.prepareAsync?.('tower', 12));
  return stage;
}
