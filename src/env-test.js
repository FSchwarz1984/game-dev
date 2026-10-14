/* =====================================================================
   env-test — a page to view and walk the home area with the 2D renderer.
   Build: node tools/env/build.mjs  (→ scratchpad page, see tools/env/)
   URL switches:
     ?t=dusk|night|morning|noon|<hours>   time of day (default 17.6)
     ?shot=<name>    camera framing from map.shots (path, dosojin, graves, saddle, camphorFull, hut, shrine, eastRoad, lookout, tower, waterfall)
     ?x=&z=          start position (metres)  ?y= her height (a climb hold)  ?q=high|mid|low
     ?day1=1         the morning after the Far (hut far, scars, half-faded camphor)
     ?lanterns=1     bon lanterns hung and lit at the graves (evening/night also light the hut and
                     give her a carried lantern; ?carry=1 forces the carried lantern)
     ?frames=N       set window.DONE after N frames  ?pause=1  freeze time
     ?ph=1           the placeholder character instead of her sprite sheet (src/art)
     ?cam=x,z,y      a fixed camera target (metres)
     ?async=1        bake with createHomeMapAsync (window.BAKE: frames, maxGap, longestSlice)
   Keys: WASD/arrows walk, T cycles the time, F toggles day-1, L lanterns.
   window.ENV exposes {R, map, actor, setTime, shot, walkTo} for scripted shots.
   ===================================================================== */
import { Renderer } from './gfx/renderer.js';
import { createHomeMap, createHomeMapAsync } from './env/home.js';
import { buildPlaceholderSheet } from './env/actor.js';
import { TSUZUMI, frameAt } from './art/characters.js';

const qs = new URLSearchParams(location.search);
const app = document.getElementById('app') || document.body;
const cv = document.createElement('canvas'); cv.className = 'view'; app.appendChild(cv);
Object.assign(cv.style, { width: '100%', height: '100%', display: 'block', imageRendering: 'pixelated' });
const hud = document.createElement('pre'); Object.assign(hud.style, { position: 'fixed', left: '6px', top: '4px', margin: 0, color: '#e8eee0', font: '11px/1.3 monospace', textShadow: '0 1px 2px #000', pointerEvents: 'none', display: qs.get('hud') === '0' ? 'none' : 'block' });
app.appendChild(hud);

const loadImg = url => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = url; });
/** her sprite sheet (src/art, the character agent's work) when it loads; the placeholder otherwise or with ?ph=1 */
async function sheetOf() {
  if (qs.get('ph') !== '1') try {
    const sh = TSUZUMI && TSUZUMI.sheets.load; if (sh && sh.albedo) { const [a, n] = await Promise.all([loadImg(sh.albedo), loadImg(sh.normal)]); return { real: true, a, n }; }
  } catch (e) { console.warn('character sheet not loaded, using the placeholder', e); }
  return { real: false };
}

async function boot() {
  const SH = await sheetOf();
  const t0 = performance.now();
  let map;
  if (qs.get('async') === '1') {
    // the non-blocking bake: count animation frames and the longest gap between them while it runs
    const B = window.BAKE = { frames: 0, maxGap: 0, last: performance.now(), progress: [] };
    let on = true; const tick = now => { if (!on) return; B.maxGap = Math.max(B.maxGap, now - B.last); B.last = now; B.frames++; requestAnimationFrame(tick); }; requestAnimationFrame(tick);
    map = await createHomeMapAsync({ onProgress: (k, label) => { B.progress.push(Math.round(k * 100)); document.title = 'baking ' + Math.round(k * 100) + '% ' + label; } });
    on = false; B.ms = performance.now() - t0; B.longestSlice = map.bakeSlices.longestMs; B.slow = map.bakeSlices.slowSteps;
  } else map = createHomeMap({});
  const bakeMs = performance.now() - t0;
  const R = new Renderer(cv, { quality: qs.get('q') || 'auto', preserve: qs.has('shotmode') });
  R.loadMap(map);
  const S = buildPlaceholderSheet();
  if (SH.real) R.loadSheet('tsuzumi', SH.a, SH.n); else R.loadSheet('tsuzumi', S.albedo, S.normal);
  const anchor = SH.real ? [TSUZUMI.pivot.x, TSUZUMI.pivot.y] : S.anchor;
  const sp = map.spawn; const pos = { x: +(qs.get('x') ?? sp.x), z: +(qs.get('z') ?? sp.z) };
  const actor = R.addActor('tsuzumi', { x: pos.x, z: pos.z, y: map.heightAt(pos.x, pos.z), frame: S.anims.idle_s[0], anchor, slot: 0 });
  const tq = qs.get('t'); let hour = tq == null ? 17.6 : isNaN(+tq) ? ({ dusk: 17.6, night: 21, morning: 7, noon: 12.5, evening: 18.4 })[tq] ?? 17.6 : +tq;
  R.setTime(hour);
  const st = { dir: 's', anim: 0, follow: true };
  const ENV = window.ENV = {
    R, map, actor, S, bakeMs,
    setTime: h => { hour = h; R.setTime(h); },
    shot: name => { const s = map.shots[name]; if (!s) return false; st.follow = false; R.setCamera(s.to || s, 0); R.camera.snap(); return true; },
    follow: () => { st.follow = true; },
    place: (x, z, y) => { actor.x = x; actor.z = z; actor.y = y ?? map.heightAt(x, z); R.setFocus(x, z, actor.y); R.setCamera({ x, z, y: actor.y, lift: 0.9 }, 0); },
  };
  R.debug = +(qs.get('debug') || 0); R.noTerrainShadow = qs.get('nots') === '1';
  if (qs.get('day1') === '1' && map.applyDay1) map.applyDay1(R);
  if (qs.get('lanterns') === '1' && map.hangLanterns) map.hangLanterns(R, true);
  // evening and night: the hut is lit, and she carries her lantern on the back-frame (a light that moves with her)
  const dark = hour >= 18.6 || hour < 5.5;
  if (dark && map.lightHome) map.lightHome(R, true);
  ENV.carry = dark || qs.get('carry') === '1' ? R.addLight({ x: pos.x, z: pos.z, y: map.heightAt(pos.x, pos.z) + 1.7, color: [1, 0.72, 0.42], radius: 3.4, intensity: 0.9, flicker: 0.35 }) : null;
  ENV.place(pos.x, pos.z, qs.get('y') != null ? +qs.get('y') : undefined);
  if (qs.get('y') != null) st.lockY = +qs.get('y');
  if (qs.get('shot')) ENV.shot(qs.get('shot'));
  if (qs.get('cam')) { const [cx, cz, cy] = qs.get('cam').split(',').map(Number); st.follow = false; R.setCamera({ x: cx, z: cz, y: cy || 0 }, 0); R.camera.snap(); }
  const keys = new Set();
  addEventListener('keydown', e => { keys.add(e.code); if (e.code === 'KeyT') ENV.setTime((hour + 1.5) % 24); if (e.code === 'KeyF' && map.applyDay1) map.applyDay1(R); if (e.code === 'KeyL' && map.hangLanterns) map.hangLanterns(R, true); });
  addEventListener('keyup', e => keys.delete(e.code));
  // touch: drag anywhere to walk
  let touch = null; cv.addEventListener('pointerdown', e => { touch = { x0: e.clientX, y0: e.clientY, x: 0, y: 0 }; });
  addEventListener('pointermove', e => { if (touch) { touch.x = e.clientX - touch.x0; touch.y = e.clientY - touch.y0; } });
  addEventListener('pointerup', () => { touch = null; });
  let last = performance.now(), frames = 0; const maxF = +(qs.get('frames') || 0);
  const pause = qs.get('pause') === '1';
  function tick() {
    const now = performance.now(); const dt = Math.min(0.05, (now - last) / 1000); last = now;
    let mx = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) - (keys.has('KeyA') || keys.has('ArrowLeft') ? 1 : 0);
    let mz = (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0) - (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0);
    if (touch && Math.hypot(touch.x, touch.y) > 12) { const l = Math.hypot(touch.x, touch.y); mx = touch.x / l; mz = touch.y / l; }
    const moving = mx || mz;
    if (moving) {
      st.follow = true; const l = Math.hypot(mx, mz), sp = 4.2 * dt; const nx = actor.x + mx / l * sp, nz = actor.z + mz / l * sp;
      if (map.walkable(nx, actor.z)) actor.x = nx; if (map.walkable(actor.x, nz)) actor.z = nz;
      actor.y = st.lockY ?? map.heightAt(actor.x, actor.z);
      st.dir = Math.abs(mx) > Math.abs(mz) ? (mx > 0 ? 'e' : 'w') : (mz > 0 ? 's' : 'n');
    }
    st.anim += dt * (moving ? 8 : 0); st.t = (st.t || 0) + (pause ? 0 : dt);
    if (SH.real) {
      const f = frameAt(TSUZUMI, 'load', moving ? 'walk' : 'idle', { s: 'down', n: 'up', e: 'right', w: 'left' }[st.dir], st.t);
      if (f) { actor.frame = [f.sx, f.sy, f.sw, f.sh]; actor.flip = !!f.mirror; }
    } else {
      const d = st.dir === 'w' ? 'e' : st.dir; const A = S.anims[(moving ? 'walk_' : 'idle_') + d];
      actor.frame = A[Math.floor(st.anim) % A.length]; actor.flip = st.dir === 'w';
    }
    R.setFocus(actor.x, actor.z, actor.y);
    if (ENV.carry) ENV.carry.set({ x: actor.x + (actor.flip ? 0.25 : -0.25), z: actor.z - 0.15, y: actor.y + 1.7 });
    if (st.follow) R.setCamera({ x: actor.x, z: actor.z, y: actor.y, lift: 0.9 }, 5);
    R.render(pause ? 0 : dt);
    frames++; window.FR = frames;
    if (frames % 10 === 0) { const s = R.stats; hud.textContent = `${s.native[0]}x${s.native[1]} x${s.scale} ${s.quality} | ${s.ms.toFixed(1)} ms cpu | calls ${s.calls} | passes ${s.passes} | lights ${s.lights} | parts ${s.particles} | bake ${bakeMs.toFixed(0)} ms | ${hour.toFixed(1)}h | ${actor.x.toFixed(1)}, ${actor.z.toFixed(1)}`; }
    if (maxF && frames === maxF) window.DONE = true;
    requestAnimationFrame(tick);
  }
  window.READY = true;
  requestAnimationFrame(tick);
}
boot().catch(e => { console.error(e && e.stack || e); document.title = 'ERR ' + e.message; window.DONE = true; window.ERR = String(e && e.stack || e); });
