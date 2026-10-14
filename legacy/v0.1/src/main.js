/* =====================================================================
   MAIN — boot (generate the art, raise the mountain), the title, the
   frame loop, the camera, pause.
   ===================================================================== */
"use strict";
if (typeof AU === "undefined") window.AU = new Proxy({}, { get: (o, k) => k === "ready" ? false : () => {} });
const APP = {
  cam: { x: 0, y: 0 }, paused: false, started: false,
  async boot() {
    UI.init();
    const ld = document.createElement("div"); ld.id = "loading"; ld.innerHTML = `<div class="k">ツヅラ</div><div class="b"><i></i></div><div class="t">九十九折峠</div>`; document.getElementById("ui").appendChild(ld);
    const bar = ld.querySelector("i"), step = (k, msg) => new Promise(r => { bar.style.width = (k * 100) + "%"; if (msg) ld.querySelector(".t").textContent = msg; setTimeout(r, 30); });
    const cv = document.getElementById("cv");
    IN.init(cv); IN.onDevice = () => RD.resize();
    if (!RD.init(cv)) { ld.querySelector(".t").textContent = "这台设备不支持 WebGL2。"; return; }
    await step(.08, "削竹 · 编笼");
    ARTREG.build(k => {});
    await step(.5, "起山 · 引水");
    WORLD.build(); WORLD.buildGrid();
    await step(.8, "点灯");
    RD.buildWorld(WD); VISTA.init();
    WORLDSETUP.base();
    await step(1, "");
    setTimeout(() => ld.remove(), 300);
    IN.onAny = () => { if (!AU.ready) { try { AU.init(); AU.resume(); } catch (e) { } } else AU.resume(); };
    this.loop();
    if (QS.skip) this.start(QS.skip === "free" ? "free" : QS.skip === "wake" ? "wake" : "new"); else this.title();
    if (QS.auto) after(1.5, () => { if (GAME.state === "title") { this.started = true; const t = document.getElementById("title"); t && t.remove(); this.start("new"); } });
  },
  /* ---------- title ---------- */
  title() {
    GAME.state = "title"; VISTA.on = true; VISTA.mode = "title"; VISTA.night = 1; VISTA.wave = -1; VISTA.procession = false;
    const hasSave = !!GAME.load();
    const t = document.createElement("div"); t.id = "title";
    t.innerHTML = `<div class="tt"><h1>ツヅラ</h1><div><h2>遠囃子</h2><div class="seal">九十<br>九折</div></div></div>
      <nav><button id="bNew">从头开始</button>${hasSave ? `<button id="bCont">继续旅途</button>` : ""}</nav><div class="hint">WASD 移动 · E 拾/调查 · J 取 · K 予 · Q 卸 · Shift 奔</div>`;
    document.getElementById("ui").appendChild(t);
    const btns = [...t.querySelectorAll("button")]; let sel = hasSave ? 1 : 0; const mark = () => btns.forEach((b, i) => b.classList.toggle("sel", i === sel)); mark();
    const go = which => { if (this.started) return; this.started = true; AU.init(); AU.resume(); AU.sfx("ui_ok"); t.style.opacity = 0; setTimeout(() => t.remove(), 1200); this.start(which); };
    document.getElementById("bNew").onclick = () => go("new"); if (hasSave) document.getElementById("bCont").onclick = () => go("cont");
    this.titleKeys = () => { if (IN.hit.up || IN.hit.down) { sel = (sel + 1) % btns.length; mark(); AU.sfx("ui_move"); } if (IN.hit.ok) go(sel === 0 ? "new" : "cont"); };
    UI.fade(0, 2);
    AU.music("title", { fade: 3 });
  },
  async start(which) {
    this.titleKeys = null;
    if (which === "cont") { const s = GAME.load(); if (s) { await UI.fade(1, 1); VISTA.on = false; WORLDSETUP.afterFar(); GAME.applySave(s); GAME.state = "play"; STORY.stage = "free"; GAME.noSave = false; UI.showHud(true); UI.countPop(GAME.count, null, true); AU.music("explore", { fade: 4 }); this.snapCam(); await UI.fade(0, 1.6); return; } }
    if (which === "free") { VISTA.on = false; WORLDSETUP.afterFar(); const [sx, sy] = LM.shrine; PL.init(+(QS.x || sx + 20), +(QS.y || sy + 40)); GAME.state = "play"; STORY.stage = "free"; GAME.flags.knowsWeight = true; GAME.flags.knowsLeaf = true; GAME.tod = +(QS.t || 9); UI.showHud(true); UI.countPop(GAME.count, null, true); this.snapCam(); UI.fade(0, .3); return; }
    if (which === "wake") { VISTA.on = false; GAME.state = "play"; GAME.tod = 6.3; STORY.wake().then(() => {}); this.snapCam(); return; }
    try { localStorage.removeItem("tsuzura.save.v1"); } catch (e) { }
    await UI.fade(1, 1.4); VISTA.on = false; AU.music("none", { fade: 1 });
    GAME.state = "play"; this.snapCam();
    STORY.prologue();
  },
  snapCam() { const P = PL.e; if (!P) return; this.cam.x = P.x; this.cam.y = P.y - P.z; },
  /* ---------- the loop ---------- */
  loop() {
    let last = performance.now(), frames = 0;
    const frame = () => {
      const now = performance.now(); let dt = Math.min(.05, (now - last) / 1000) * (+(QS.speed) || 1); last = now;
      try { this.tick(dt); } catch (e) { console.error(e && e.stack || e); }
      frames++; if (frames === (+(QS.frames) || 4)) window.DONE = true;
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  },
  tick(dt) {
    IN.update(dt);
    if (this.titleKeys) this.titleKeys();
    if (IN.hit.pause && GAME.state === "play" && !UI.dlg) this.togglePause();
    const run = !this.paused;
    if (run) { tickLater(dt); GAME.tick(dt); }
    RD.t = GAME.t;
    RD.box = damp(RD.box, GAME.boxT || 0, 4, dt);
    const env = RD.env = GAME.env();
    if (VISTA.on || GAME.state === "title") { if (run) VISTA.draw(dt); GL.canvasSub(VISTA.tex, VISTA.cv, true); RD.renderOverlay(VISTA.tex, VISTA.night > .5 ? .55 : .86); UI.update(dt); this.audio(dt, true); return; }
    if (GAME.state !== "play" || !PL.e) { RD.renderOverlay(VISTA.tex || ATLAS.tAlb); return; }
    if (run) {
      STORY.update(dt); PL.update(dt); EN.update(dt); FX.update(dt); FX.ambient(dt, env); NEARMAP.update(dt);
    }
    // camera: follow her with a little look-ahead, or obey the cinematic
    const P = PL.e; let tx, ty;
    if (GAME.camT) { tx = GAME.camT.x; ty = GAME.camT.y - GAME.camT.z; const k = GAME.camT.k; this.cam.x = k > 50 ? tx : damp(this.cam.x, tx, k, dt); this.cam.y = k > 50 ? ty : damp(this.cam.y, ty, k, dt); if (k > 50) GAME.camT.k = 2.5; }
    else { tx = P.x + P.vx * .35; ty = P.y - P.z - 14 + P.vy * .3 - PL.stackH() * .3; this.cam.x = damp(this.cam.x, tx, 4, dt); this.cam.y = damp(this.cam.y, ty, 4, dt); }
    RD.cam.shake = Math.max(0, RD.cam.shake - dt * 8);
    RD.setCamera(this.cam.x, this.cam.y);
    // the Far at the edges of sight
    const near = WORLD.nearAt(P.x, P.y); RD.farFx = damp(RD.farFx, clamp((.45 - near) / .4, 0, 1), 3, dt);
    // draw
    GHOSTS.draw(); EN.draw(); PL.draw(); PROLOGUE.draw(); ENDING.draw(); FX.draw();
    RD.render();
    UI.update(dt);
    this.audio(dt, false);
    if (!GAME.cine && GAME.state === "play" && !this.paused) { this.saveT = (this.saveT || 0) + dt; if (this.saveT > 20) { this.saveT = 0; GAME.save(); } }
  },
  audio(dt, vista) {
    if (!AU.ready) return;
    const P = PL.e; const env = RD.env;
    let s = { tod: GAME.tod, rain: env.rain, wind: env.wind[2], listener: { x: P ? P.x : 0, y: P ? P.y : 0 }, near: 1, biome: { forest: 0, bamboo: 0, stream: 0, meadow: 0, shrine: 0 }, water: 0, fall: 0, cinematic: GAME.cine, paused: this.paused, heavy: P ? P.tail / 6 : 0 };
    if (vista) { s.near = 1; s.biome.forest = .6; AU.update(dt, s); return; }
    if (P) {
      s.near = WORLD.nearAt(P.x, P.y);
      const Z = WD.zones; s.biome.forest = Z.cedarZone(P.x, P.y) ? 1 : .3; s.biome.bamboo = Z.bambooZone(P.x, P.y) ? 1 : 0; s.biome.meadow = Z.meadow(P.x, P.y) ? 1 : 0; s.biome.shrine = hyp(P.x - LM.shrine[0], P.y - LM.shrine[1]) < 140 ? 1 : 0;
      let wd = 999; for (let r = 8; r <= 120 && wd > 900; r += 16) for (let a = 0; a < 8; a++) if (WORLD.waterAt(P.x + Math.cos(a / 8 * TAU) * r, P.y + Math.sin(a / 8 * TAU) * r) > -500) { wd = r; break; }
      s.water = clamp(1 - wd / 130, 0, 1); s.biome.stream = s.water;
      s.fall = clamp(1 - hyp(P.x - LM.fallTop[0], P.y - LM.fallTop[1] - 40) / 260, 0, 1);
      if (STORY.stage === "free") AU.festival(clamp((.55 - s.near) / .5, 0, 1) * .8, { near: 0 });
    }
    AU.update(dt, s);
  },
  togglePause() {
    this.paused = !this.paused; AU.sfx(this.paused ? "ui_open" : "ui_close");
    if (this.paused) {
      const p = document.createElement("div"); p.id = "pause";
      p.innerHTML = `<div class="pn"><h3>小憩</h3><p><kbd>WASD</kbd> 走 · <kbd>Shift</kbd> 奔跑 · <kbd>E</kbd> 背起 / 调查 / 献给祠</p><p><kbd>Q</kbd> 放下最上面的东西 · <kbd>J</kbd> 取：把重量吸进尾巴 · <kbd>K</kbd> 予：把重量交给别的东西</p>
        <p>尾巴里装满六份重量，会变成石头。背得太高、跑得太快，背上的东西会掉。</p><p>第 ${GAME.day} 日 · ${String(Math.floor(GAME.tod)).padStart(2, "0")}:${String(Math.floor((GAME.tod % 1) * 60)).padStart(2, "0")} · 供物 ${kanjiNum(GAME.count)}</p>
        <button id="pRes">继续</button><button id="pSave">记下</button></div>`;
      document.getElementById("ui").appendChild(p);
      p.querySelector("#pRes").onclick = () => this.togglePause(); p.querySelector("#pSave").onclick = () => { GAME.save(); UI.toast("记下了。"); };
    } else { const p = document.getElementById("pause"); p && p.remove(); }
  },
};
addEventListener("load", () => { APP.boot().catch(e => { console.error(e && e.stack || e); document.title = "ERR " + e.message; window.DONE = true; }); });
