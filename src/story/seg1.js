// Segment 1: the prologue 「送魂夜」 and the first morning (docs/design/script-01.md).
// The scenes are written against the game context G, which the main module builds:
//
//   G.D       Director (src/story/cine.js) — waits, shots, moves, lines, cards, fades
//   G.f       Field (src/game/field.js)    — her body, the things, the verbs, zones, events
//   G.stage   renderer adapter: actor(id), prop(id), light(def), vista(state|null), scar(...),
//             setFar(id, amount), shot/cam/follow/tod, climbPoints(), inset(kind, on)
//   G.hud     gameplay HUD: show(on), unlock(k), tip(key, text, entity|null), untip(key)
//   G.au      audio engine (AU)
//   G.P       places on the map, in metres (see PLACES below)
//   G.on(fn)  field events, one at a time, after the main loop drains them
//   G.save(stage)
//
// Lines follow .claude/skills/dialogue-writing (no explained feelings, a world-only detail in
// every exchange, the box never longer than two lines).

const T = text => ({ who: 'tsuzumi', text });
const S = text => ({ who: 'saji', text });

/**
 * The places this segment needs from the map (metres; x east, z south):
 *   start, roadUp[]       where the prologue begins on the east road, and the way up it
 *   dosojin, dosojinStand the paired statues, and where she stands to bow
 *   graves[9], gravesStand the nine nameless graves, and the head of their terrace
 *   camphor, camphorFoot, loadSpot   the tree, where she starts to climb, where her load rests
 *   wake, hut, hutDoor, frame        day 1: where she wakes, the far hut, its door, the old frame
 *   shrine, beam, rocks[]            the shrine, its fallen eave beam, loose stones
 *   eastExit {x0,x1,z0,z1}, gravesZone, dosojinZone, shrineZone (rects or circles)
 */
export const PLACES = ['start', 'roadUp', 'dosojin', 'dosojinStand', 'graves', 'gravesStand', 'camphor', 'camphorFoot', 'loadSpot', 'wake', 'hut', 'hutDoor', 'frame', 'shrine', 'beam', 'rocks', 'eastExit', 'gravesZone', 'dosojinZone', 'shrineZone'];

/** Resolve on the first field event matching pred. */
function once(G, pred) {
  return new Promise(res => { const off = G.on(e => { if (pred(e)) { off(); res(e); } }); });
}

/** Run a scene with her controls off and the HUD hidden; give them back afterwards. */
async function cut(G, fn, { follow = true } = {}) {
  const { D, f } = G;
  f.control = false; G.hud.show(false);
  try { await D.scene(fn); }
  finally {
    if (follow) D.follow();
    f.control = true; G.hud.show(true);
  }
}

/** Ease the clock toward hour h over dur seconds; a newer call takes over from an older one. */
function todTo(G, h, dur) {
  const gen = (G.todGen = (G.todGen || 0) + 1), h0 = G.hour ?? h;
  return G.D.tween(dur, k => { if (G.todGen === gen) { G.hour = h0 + (h - h0) * k; G.D.tod(G.hour); } }, { ease: false });
}

// =====================================================================================
// PROLOGUE — 送魂夜
// =====================================================================================

export async function prologue(G) {
  const { D, f, stage, P, au } = G;
  const her = stage.actor('tsuzumi');
  her.variant = 'load'; her.visible = true;
  stage.actor('saji').visible = false;
  f.player.x = P.start[0]; f.player.z = P.start[1];
  f.control = false; G.hud.show(false);
  G.hour = 17.6; D.tod(G.hour);
  au.music('prologue', { fade: 2 });
  au.festival(0);

  // ---- 1 the east entrance at dusk: she comes up the road under a tall load, and stops at the
  // paired statues (one of them wears a hat as wide as hers)
  await D.fade(1, 0);
  D.letterbox(true);
  D.shot('dosojin', { cut: true });
  D.fade(0, 2.4);
  const walkIn = D.move('tsuzumi', P.roadUp, { speed: 1.5 });
  await D.wait(1.6);
  await D.card('盆の十六日　暮れ六つ', '盂兰盆，十六日，傍晚');
  await walkIn;
  await D.scene(async () => {
    D.face('tsuzumi', faceTo(her, P.dosojin));
    await D.wait(0.6);
    await D.say(T('借过。'));
    await D.play('tsuzumi', 'bow', { hold: 0.9 });
    await D.wait(0.4);
    stage.prop('dango').state = 'one';
    au.sfx('pickup');
    await D.play('tsuzumi', 'eat', { hold: 1.1 });
    await D.wait(0.5);
    await D.say(T('戴斗笠的这位，这一颗我替您吃了。'));
    await D.wait(0.4);
  });
  D.letterbox(false);
  D.follow();
  f.control = true; G.hud.show(true);
  G.hud.tip('move', G.touch ? '左半边屏幕按住拖动：走' : 'WASD / 方向键：走', null);
  once(G, e => e.type === 'moved').then(() => G.hud.untip('move'));
  todTo(G, 18.5, 150); // the dusk deepens while she climbs the switchbacks

  const blockDown = f.zone({ ...P.eastExit, id: 'eastExit', block: '灯笼还在背上呢。' });
  f.zone({ ...P.gravesZone, id: 'graves' });

  // ---- the nine nameless graves, ten lanterns
  await once(G, e => e.type === 'enter' && e.zone === 'graves');
  await cut(G, async () => {
    D.shot('graves', { speed: 1.2 });
    await D.move('tsuzumi', [P.gravesStand], { speed: 1.6 });
    await D.wait(0.8);
  });
  let hung = 0;
  const graves = P.graves.map((g, i) => f.add({
    id: 'grave' + i, kind: 'grave', name: '无缘墓', x: g[0], z: g[1], r: 0.35, solid: true, priority: 1,
    ctx: {
      label: () => (graves[i].data.lit ? '' : '挂灯笼'),
      run: () => { hang(G, graves[i], i); hung += 1; G.hud.untip('lantern'); return '挂灯笼'; },
    },
  }));
  G.hud.tip('lantern', G.touch ? '点右下角的大键：挂灯笼' : 'E：挂灯笼', graves[0]);
  await D.until(() => hung >= 9 && !G.D.busy);

  // ---- 2 the hayashi, from everywhere at once; and the tenth lantern
  await cut(G, async () => {
    await D.wait(0.8);
    D.shot('graves', { speed: 0.8 });
    await D.say(T('庄屋给了十盏。'), T('……这排墓，九座。'));
    await D.wait(0.6);
    await D.play('tsuzumi', 'reachUp', { hold: 0.9 });
    stage.prop('lantern9').attachTo = 'tsuzumi';     // the tenth hangs from her own frame
    stage.prop('lantern9').state = 'lit';
    au.sfx('offering');
    await D.wait(1.6);

    au.music('none', { fade: 3 });
    todTo(G, 19.1, 20);
    au.festival(0.35, { near: 0.5 });
    await D.wait(2.4);
    D.face('tsuzumi', 'back'); await D.wait(0.7);
    D.face('tsuzumi', 'left'); await D.wait(0.6);
    D.face('tsuzumi', 'right'); await D.wait(0.8);
    D.face('tsuzumi', 'front');
    await D.say(T('今年的囃子，近。'));
    await D.wait(0.5);
    au.festival(0.12, { near: 0.5 });
    au.stinger('hum');
    await D.wait(4.4);           // her half phrase (HALF_PHRASE: ~3.9 s)
    await D.wait(1.0);           // two beats of nothing
    au.stinger('echo');          // a flute far off plays it back, note for note
    await D.wait(4.6);
    au.festival(0, {});          // she stops; the flute stops too
    await D.wait(2.2);           // wind
    au.festival(0.4, { near: 0.8 }); // and the music starts again from another side, as if nothing happened
    await D.wait(1.6);
    D.face('tsuzumi', 'back');
    D.shot('saddle', { speed: 0.7 });           // up on the saddle, the camphor: where the music seems to come from
    await D.wait(3.4);
  });
  blockDown.block = '囃子是从上面来的。';

  // ---- 3 the camphor: lean the load on the roots and climb
  const camphor = f.add({
    // the trunk is several metres wide: the map blocks it; this only makes it choosable from its foot
    id: 'camphor', kind: 'camphor', name: '大楠', x: P.camphor[0], z: P.camphor[1], r: P.camphorR || 3.4, priority: 1, sacred: true, q: { v: 9 },
    ctx: { label: () => '爬', run: () => { climb(G); return '爬'; } },
  });
  G.hud.tip('climb', G.touch ? '点右下角的大键：爬' : 'E：爬', camphor);
  await once(G, e => e.type === 'climbed');
  f.remove(camphor);

  // ---- 4 the lights rise; the sky opens; the far comes up the mountain
  await rise(G);
  f.zones.splice(f.zones.indexOf(blockDown), 1);
  for (const g of graves) g.hidden = true;
  G.save('day1');
}

function faceTo(a, [x, z]) {
  const dx = x - a.x, dz = z - a.z;
  if (Math.abs(dx) > Math.abs(dz) * 1.15) return dx < 0 ? 'left' : 'right';
  return dz < 0 ? 'back' : 'front';
}

function hang(G, grave, i) {
  const { D, stage, au, f } = G;
  grave.data.lit = true;
  D.scene(async () => {
    f.control = false;
    D.face('tsuzumi', faceTo(stage.actor('tsuzumi'), [grave.x, grave.z]));
    await D.play('tsuzumi', 'reachUp', { hold: 0.55 });
    const lantern = stage.prop('lantern' + i);
    lantern.state = 'lit';
    au.sfx('offering', { x: grave.x, y: grave.z });
    await D.wait(0.25);
    f.control = true;
  });
}

async function climb(G) {
  const { D, f, stage, P, au } = G;
  G.hud.untip('climb');
  await cut(G, async () => {
    const her = stage.actor('tsuzumi');
    await D.move('tsuzumi', [P.camphorFoot], { speed: 1.6 });
    D.face('tsuzumi', 'back');
    await D.play('tsuzumi', 'unshoulder', { hold: 0.6 }); // she sets the load down against the roots
    const load = stage.prop('load');
    load.visible = true; load.x = P.loadSpot[0]; load.z = P.loadSpot[1];
    stage.prop('lantern9').attachTo = 'load';
    her.variant = 'none';
    au.sfx('drop');
    await D.wait(0.8);
    D.shot('camphorFull', { speed: 0.5 });
    // up the roots and the trunk, hold by hold; it cannot fail
    for (const p of stage.climbPoints()) {
      her.climbTo = p;
      await D.play('tsuzumi', 'climb', { hold: 0.75 });
      au.sfx('rustle', { x: P.camphor[0], y: P.camphor[1] });
    }
    await D.wait(0.4);
  }, { follow: false });
  f.push({ type: 'climbed' });
}

async function rise(G) {
  const { D, f, stage, au, ui } = G;
  f.control = false; G.hud.show(false);
  await D.scene(async () => {
    await D.fade(1, 0.6);
    const v = { shot: 'south', tod: 19.4, pan: 0, rise: 0, sky: 0, wave: -1, tower: 1, pose: 'sit' };
    stage.vista(v);
    D.letterbox(true);
    await D.fade(0, 1.2);
    // the camera leaves the leaves behind and the plain opens below
    await D.tween(7, k => { v.pan = k; v.tod = 19.4 + k * 0.4; });
    await D.wait(1.5);
    await D.sub('十六号。送魂的晚上。', 3.2);     // over the view, not in a box: nothing covers her on the branch
    await D.wait(1.0);

    // one light leaves the ground; another; then all of them, in no hurry
    au.festival(0.25, { near: 0.6 });
    await D.tween(6, k => { v.rise = k * 0.06; }, { ease: false });
    await D.wait(1.5);
    au.music('none', { fade: 2 });
    au.festival(0.1, { near: 0.3 });   // the music thins out to wind
    await D.tween(16, k => { v.rise = 0.06 + k * 0.6; v.tod = 19.8 + k * 0.5; });
    au.festival(0, {});

    // the clouds part: another land hangs upside down in the sky
    await D.tween(10, k => { v.sky = k; v.rise = 0.66 + k * 0.34; });
    au.festival(0.55, { near: 1 });     // the hayashi was theirs
    await D.wait(4.5);

    // the summit tower: its red light blinks once more and goes out
    v.shot = 'tower'; v.tower = 1;
    await D.wait(2.0);
    v.tower = 0;
    au.sfx('far_pulse');
    await D.wait(1.8);
    v.shot = 'south';

    // the far: a pale ring spreads from under the sky land and comes up the mountain
    au.music('tension', { fade: 1 });
    au.sfx('far_wave');
    await D.tween(5.5, k => { v.wave = k * 0.55; }, { ease: false });
    v.pose = 'stand';
    await D.wait(0.4);
    v.pose = 'shout';
    au.sfx('blip', { voice: 'tsuzumi', i: 1 });
    await D.sub('喂——那边的人——', 2.6);
    await D.tween(2.6, k => { v.wave = 0.55 + k * 0.45; }, { ease: false });
    await D.fade(1, 0.15, '#f4f1ea');
    au.music('none', { fade: 0.1 });
    au.festival(0, {});
    stage.vista(null);
    D.letterbox(false);
    await D.wait(0.8);
    await ui.title('天岸', 'あまぎし', 4.2);
    await D.fade(1, 1.4, '#000');
    await D.wait(1.0);
  });
}

// =====================================================================================
// DAY 1 — the first morning
// =====================================================================================

export async function day1(G) {
  const { D, f, stage, P, au } = G;
  const her = stage.actor('tsuzumi'), saji = stage.actor('saji');
  her.reset?.(); saji.reset?.();               // the night left her up the camphor: down on the roots
  her.variant = 'none'; her.visible = true;
  saji.visible = false;
  f.control = false; G.hud.show(false);
  f.player.x = P.wake[0]; f.player.z = P.wake[1];
  her.lastX = her.x; her.lastZ = her.z;
  G.todGen = (G.todGen || 0) + 1; G.hour = 7.0; D.tod(G.hour);
  au.music('none', { fade: 0.1 });
  stage.morning?.();                         // the far's marks: scars, the pale crown, the pale dango

  // what the night left: the hut and her load, pale and out of reach; the old frame, only emptied
  const hut = f.add({ id: 'hut', kind: 'hut', name: '小屋', x: P.hut[0], z: P.hut[1], r: 2.2, solid: true, deep: true, priority: 0 });
  const load = f.add({ id: 'load', kind: 'load', name: '货', x: P.loadSpot[0], z: P.loadSpot[1], r: 0.45, solid: true, deep: true });
  const frame = f.add({ id: 'frame', kind: 'frame', name: '旧背負子', x: P.frame[0], z: P.frame[1], r: 0.4, priority: 1, q: { w: 0 }, base: { w: 3 }, material: 'wood' });
  const shrine = f.add({ id: 'shrine', kind: 'shrine', name: '祠', x: P.shrine[0], z: P.shrine[1], r: 0.9, solid: true, sacred: true, priority: 0 });
  f.add({ id: 'camphor', kind: 'camphor', name: '大楠', x: P.camphor[0], z: P.camphor[1], r: P.camphorR || 3.4, sacred: true, q: { v: 9 }, targetable: false });
  for (const [i, r] of P.rocks.entries()) f.add({ id: 'rock' + i, kind: 'rock', name: '石', x: r[0], z: r[1], r: 0.4, q: { w: 2 }, material: 'stone' });
  stage.prop('load').visible = true;
  stage.prop('lantern9').attachTo = 'load';
  stage.prop('lantern9').state = 'unlit';
  for (let i = 0; i < 9; i++) stage.prop('lantern' + i).state = 'unlit';

  // ---- 5 waking under the hat
  await D.scene(async () => {
    D.cam(P.wake[0], P.wake[1], { cut: true });
    her.pose = 'sleep';
    await D.wait(0.6);
    D.fade(0, 2.6);
    au.sfx('wings');
    await D.wait(3.2);
    her.pose = null;
    await D.play('tsuzumi', 'sitUp', { hold: 0.4 });
    stage.inset('hat', true);                 // the inside of the hat, for a moment: 本来無東西　何処有南北
    await D.wait(1.6);
    stage.inset('hat', false);                // (she has stood up behind the insert)
    await D.wait(0.8);
    D.face('tsuzumi', 'back');                // the crown above has half lost its colour
    D.cam(P.camphor[0], P.camphor[1], { y: 6, speed: 0.6 });
    await D.wait(2.6);
    D.follow();
    await D.wait(0.6);
  });
  f.control = true; G.hud.show(true);
  au.music('explore', { fade: 4 });

  let hutSeen = false, sajiFree = false, frameOn = false;
  const blockEast = f.zone({ ...P.eastExit, id: 'eastExit', block: '空着手去宿场，什么也带不回来。' });

  // the hut door: her hand goes through it
  hut.ctx = {
    label: () => (hutSeen ? '' : '推门'),
    run: () => {
      hutSeen = true;
      cut(G, async () => {
        await D.move('tsuzumi', [P.hutDoor], { speed: 1.4 });
        D.face('tsuzumi', faceTo(her, P.hut));
        D.shot('hut', { speed: 1 });
        await D.play('tsuzumi', 'push', { hold: 0.9 });
        au.sfx('far_touch', { x: P.hut[0], y: P.hut[1] });
        await D.wait(1.1);
        await D.say(T('……门闩是我昨天才修的。'));
        await D.wait(0.5);
        D.cam(P.frame[0], P.frame[1], { speed: 1.2 });
        await D.wait(1.2);
        await D.say(T('师父的背负子也……'));
      });
      return '推门';
    },
  };

  // ---- 6 a thud by the shrine, then a scream: after the hut, or if she wanders long enough
  await Promise.race([D.until(() => hutSeen && !D.busy), D.wait(45)]);
  await D.until(() => !D.busy);
  const beam = f.add({ id: 'beam', kind: 'beam', name: '梁', x: P.beam[0], z: P.beam[1], r: 0.7, solid: true, priority: 2, q: { w: 3 }, material: 'wood' });
  beam.data.showQualities = false;            // its pips appear when Saji's bell rings
  await cut(G, async () => {
    stage.beamFall?.();
    au.sfx('fall', { x: P.beam[0], y: P.beam[1], size: 1 });
    saji.visible = true; saji.pose = 'pinned'; saji.x = P.beam[0]; saji.z = P.beam[1] + 0.15;
    await D.wait(0.35);
    au.sfx('blip', { voice: 'saji', i: 3 }); au.sfx('blip', { voice: 'saji', i: 7 });
    D.face('tsuzumi', faceTo(her, P.shrine));
    D.shot('shrine', { speed: 1.6 });
    await D.wait(2.0);
  });

  const shrineZone = f.zone({ ...P.shrineZone, id: 'shrine' });
  if (!shrineZone.inside && Math.hypot(f.player.x - (P.shrineZone.x ?? 1e9), f.player.z - (P.shrineZone.z ?? 1e9)) >= (P.shrineZone.r ?? 0)) await once(G, e => e.type === 'enter' && e.zone === 'shrine');
  await cut(G, async () => {
    D.shot('shrine', { speed: 1.4 });
    await D.say(S('救命！压扁了！要变成座敷饼了！'), T('……座敷童子？'), S('看什么看，背箱的！抬啊！'));
  });

  // she tries to lift it; the bell; the beam's weight shows
  let tried = false;
  beam.ctx = {
    label: () => (!tried ? '抬' : ''),
    run: () => {
      tried = true;
      cut(G, async () => {
        await D.play('tsuzumi', 'strain', { hold: 1.3 });
        au.sfx('wobble', { x: beam.x, y: beam.z });
        await D.wait(0.5);
        au.sfx('blip', { voice: 'saji', i: 1 });
        await D.play('saji', 'bell', { hold: 0.2 });
        au.sfx('offering', { x: beam.x, y: beam.z });
        beam.data.showQualities = true;
        f.allow('w');
        G.hud.unlock('w');
        // from the first transfer on, the shrine can always put her body back (safe experiments)
        shrine.ctx = {
          label: () => (bodyOff(f) ? '归还' : ''),
          run: () => { f.restoreBody(); au.sfx('offering', { x: shrine.x, y: shrine.z }); G.hud.untip('rope'); return '归还'; },
        };
        await D.wait(0.8);
      });
      return '抬';
    },
  };
  await D.until(() => tried && !D.busy);
  G.hud.tip('take', G.touch ? '点「重」键：取走梁的重' : '1：取走梁的重', beam);

  // a nudge from the bell when she does not try it; Saji's running commentary as the beam lightens
  const nudge = setNudge(G, () => beam.holder.q.w > 0, () => G.hud.tip('take', G.touch ? '点「重」键：取走梁的重' : '1：取走梁的重', beam));
  const offTalk = G.on(e => {
    if (e.type !== 'transfer' || (e.from !== beam.holder && e.to !== beam.holder)) return;
    G.hud.untip('take');
    const w = beam.holder.q.w;
    if (e.to === beam.holder) bark(G, S('更重了！你在干什么啦！'));
    else if (w === 2) bark(G, S('——松了一点！'));
    else if (w === 1) bark(G, S('腿能动了！'));
  });
  await D.until(() => beam.holder.q.w <= 0 && !D.busy);
  nudge.stop(); offTalk();
  sajiFree = true;

  await cut(G, async () => {
    au.sfx('unstone', { x: beam.x, y: beam.z });
    await D.wait(0.6);
    saji.pose = null;
    await D.play('saji', 'crawl', { hold: 0.9 });
    await D.move('saji', [[beam.x + 0.9, beam.z + 0.8]], { speed: 1.2, anim: 'crawl' });
    await D.play('saji', 'hop', { hold: 0.5 });
    D.face('saji', faceTo(saji, [her.x, her.z]));
    await D.wait(0.5);
    await D.say(S('你怎么陷下去了？'), T('梁有多重，我现在就有多重。'), S('……那你还是别靠近我家。'), T('您家在哪？'));
    await D.wait(0.9);                         // she opens her mouth; nothing comes out
    await D.say(S('山下的庄屋。……原来是。'), S('昨晚全「远」了。只有挂注连绳的地方「远」不进去，我就跑上来了。'));
  });
  G.hud.tip('rope', '挂注连绳的东西，性质动不了', shrine);
  once(G, e => e.type === 'refused' && e.reason === 'sacred').then(() => G.hud.untip('rope'));
  saji.follow = 'tsuzumi';

  // ---- 7 the old back-frame: give it its weight back
  const frameTip = () => G.hud.tip('give', G.touch ? '在「重」键上往上滑：把重给它' : 'Shift+1：把重给它', frame);
  let frameLine = hutSeen;
  const offFrame = G.on(e => {
    if (e.type === 'target' && e.e === frame) {
      if (!frameLine) { frameLine = true; bark(G, T('师父的背负子也……')); }
      frameTip();
    }
  });
  const nudge2 = setNudge(G, () => frame.far > 0, frameTip, 30);
  await once(G, e => e.type === 'near' && e.e === frame);
  nudge2.stop(); offFrame(); G.hud.untip('give');
  au.sfx('land', { x: frame.x, y: frame.z });
  await cut(G, async () => {
    await D.wait(0.7);
    await D.say(S('你把重的给它了？'), T('它本来就这么重。'));
  });

  G.hud.tip('shoulder', G.touch ? '点右下角的大键：背上' : 'E：背上', frame);
  frame.ctx = {
    label: () => (frame.far === 0 && !frameOn ? '背上' : ''),
    run: () => {
      frameOn = true;
      G.hud.untip('shoulder');
      cut(G, async () => {
        await D.move('tsuzumi', [[frame.x, frame.z + 0.6]], { speed: 1.4 });
        D.face('tsuzumi', 'back');
        await D.play('tsuzumi', 'shoulder', { hold: 0.8 });
        frame.hidden = true;
        her.variant = 'frame';
        au.sfx('wobble');
        await D.wait(0.4);
        saji.follow = null;
        await D.play('saji', 'hop', { hold: 0.45 });
        saji.ride = 'tsuzumi';                // she sits on top of the frame from now on
        au.sfx('land');
        await D.wait(0.5);
        await D.say(S('这里我住下了！从今天起这就是我家！'), T('这是我的背负子。'), S('背负子也是房子嘛！有柱子有横梁！'));
        await D.say(T('那么，房租请用供品支付。'), S('哪有座敷童子交房租的啦！'));
        await D.wait(0.6);
        // ---- 8 setting out
        D.face('saji', 'back');
        D.shot('hut', { speed: 0.8 });
        await D.wait(1.4);
        await D.say(S('你家怎么办？'), T('被拿走的，就找回来。'), S('去哪找？'), T('宿场。那边旧东西多。'));
      });
      return '背上';
    },
  };
  await D.until(() => frameOn && !D.busy);
  blockEast.block = null;
  f.zones.splice(f.zones.indexOf(blockEast), 1);
  G.hud.tip('east', '往东：九十九折宿', null);

  // passing the statues: the dango she left is pale now. Saji names it; nobody explains.
  // (Only if she passes them: the way out never depends on it.)
  const statues = f.zone({ ...P.dosojinZone, id: 'dosojin2' });
  const exit = f.zone({ ...(P.leave || P.eastExit), id: 'leave' });
  let passed = false;
  const offStatues = G.on(e => {
    if (e.type !== 'enter' || e.zone !== 'dosojin2' || passed) return;
    passed = true;
    G.hud.untip('east');
    cut(G, async () => {
      D.face('tsuzumi', faceTo(her, P.dosojin));
      D.shot('dosojin', { speed: 1.2 });
      await D.wait(1.6);
      await D.say(S('……团子大人。'));   // the one she left on the plate has gone pale
      await D.wait(0.8);
    });
  });
  await once(G, e => e.type === 'enter' && e.zone === 'leave');
  await D.until(() => !D.busy);
  offStatues(); G.hud.untip('east');
  f.zones.splice(f.zones.indexOf(statues), 1);
  f.zones.splice(f.zones.indexOf(exit), 1);
  await cut(G, async () => {
    D.letterbox(true);
    D.shot('eastRoad', { speed: 0.5 });
    const P2 = [f.player.x + 6, f.player.z + 1];
    D.move('tsuzumi', [P2], { speed: 1.3 });
    await D.wait(2.2);
    await D.card('九十九折峠', 'つづらおりとうげ', 4);
    await D.wait(1.0);
    await D.fade(1, 2.0);
    au.music('none', { fade: 2 });
    await D.card('第一段　完', '下一段：九十九折宿', 3.6);
  }, { follow: false });
  G.save('end');
}

/** Her body is off its natural state (the shrine can put it back). */
function bodyOff(f) {
  const h = f.player.holder;
  return Object.keys(h.q).some(k => h.q[k] !== h.base[k]);
}

/** A line said without stopping play (a bark): a subtitle at the top; queued behind the last one. */
function bark(G, line) {
  const { D, ui } = G;
  G.barkQ = (G.barkQ || Promise.resolve()).then(async () => {
    await D.until(() => !ui.blocking);
    if (ui.bark) await ui.bark(line); else await ui.say([line]);
  });
  return G.barkQ;
}

/** Every `every` seconds while need() holds and she is idle in play, Saji's bell rings and the tip returns. */
function setNudge(G, need, show, every = 22) {
  const { D, au } = G;
  let live = true, t = 0;
  D.until(dt => {
    if (!live) return true;
    if (!G.f.control || G.ui.blocking) return false;
    t += dt;
    if (t >= every && need()) {
      t = 0;
      const s = G.stage.actor('saji');
      if (s.visible) au.sfx('blip', { voice: 'saji', i: 2 });
      au.sfx('offering', { x: s.x, y: s.z });
      show();
    }
    return false;
  });
  return { stop() { live = false; } };
}
