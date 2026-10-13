/* =====================================================================
   UI — DOM over the canvas. Dialogue (portrait, name in brush, text that
   types itself with her voice), cinematic subtitles, barks that float
   over her head, the offering count written vertically, the weight in
   her tail, the load on her back, prompts, the shrine card, title.
   ===================================================================== */
"use strict";
const UI = {
  el: {}, dlg: null, subP: null, barkQ: [], blockN: 0,
  css: `
#ui{font-family:"Noto Serif SC","Shippori Mincho","Songti SC",serif;--ink:#0d0c12;--paper:#efe6d2;--paper2:#cfc3aa;--dim:#8f8674;--ver:#c8432f;--gold:#e8b04a;--ind:#2c3c6b}
#ui *{box-sizing:border-box}
.fade{position:absolute;inset:0;background:#000;opacity:0;pointer-events:none;transition:opacity .6s;z-index:4}
#sub,#tcard{z-index:6}
#dlg{z-index:7}
#barks{position:absolute;inset:0;pointer-events:none;z-index:3}
#title{z-index:2}
#pause{z-index:8}
#loading{z-index:9}
/* dialogue */
#dlg{position:absolute;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);width:min(900px,94vw);min-height:148px;padding:18px 26px 20px 196px;
  background:linear-gradient(180deg,rgba(14,13,20,.92),rgba(10,9,15,.95));border-top:1px solid rgba(239,230,210,.38);border-bottom:1px solid rgba(239,230,210,.38);
  box-shadow:0 0 0 1px rgba(0,0,0,.6),0 18px 40px rgba(0,0,0,.45);pointer-events:auto;opacity:0;transition:opacity .25s,transform .25s}
#dlg.on{opacity:1}
#dlg::before,#dlg::after{content:"";position:absolute;left:0;right:0;height:1px;background:rgba(239,230,210,.14)}
#dlg::before{top:4px} #dlg::after{bottom:4px}
#dlg.noport{padding-left:30px}
#dlg .port{position:absolute;left:10px;bottom:6px;width:176px;height:176px;image-rendering:pixelated;filter:drop-shadow(0 4px 0 rgba(0,0,0,.35));transition:transform .18s}
#dlg .port.bump{transform:translateY(-3px)}
#dlg .name{font-family:"Zhi Mang Xing","Yuji Syuku",serif;font-size:26px;line-height:1;color:var(--gold);letter-spacing:.06em;margin-bottom:10px;display:flex;align-items:center;gap:10px}
#dlg .name i{display:inline-block;width:9px;height:9px;background:var(--ver);transform:rotate(45deg)}
#dlg .name small{font-family:"Shippori Mincho",serif;font-size:13px;color:var(--dim);letter-spacing:.2em}
#dlg .txt{font-size:clamp(16px,2.1vw,20px);line-height:1.8;color:var(--paper);letter-spacing:.04em;min-height:2.6em;white-space:pre-wrap}
#dlg .txt .ruby{color:var(--paper2)}
#dlg .nx{position:absolute;right:20px;bottom:14px;width:10px;height:10px;border-right:2px solid var(--paper2);border-bottom:2px solid var(--paper2);transform:rotate(45deg);animation:nx 1s ease-in-out infinite;opacity:0}
#dlg.done .nx{opacity:1}
@keyframes nx{50%{transform:translateY(3px) rotate(45deg)}}
#dlg.radio .txt{color:#a9c4c8;font-family:"DotGothic16","Noto Serif SC",monospace;letter-spacing:.08em;text-shadow:0 0 6px rgba(120,190,200,.35)}
#dlg.radio .name{color:#8fb3b8}
/* cinematic subtitles */
#sub{position:absolute;left:50%;bottom:16%;transform:translateX(-50%);width:min(860px,92vw);text-align:center;font-size:clamp(17px,2.4vw,24px);line-height:1.9;letter-spacing:.14em;color:var(--paper);
  text-shadow:0 2px 0 #000,0 0 18px rgba(0,0,0,.8);opacity:0;transition:opacity .9s;pointer-events:none;white-space:pre-wrap}
#sub.on{opacity:1}
#sub.mid{bottom:auto;top:50%;transform:translate(-50%,-50%)}
/* barks */
.bark{position:absolute;transform:translate(-50%,-100%);padding:5px 11px 6px;background:rgba(239,230,210,.94);color:#2a1d16;font-size:14px;line-height:1.5;letter-spacing:.04em;
  border-radius:3px;box-shadow:0 2px 0 rgba(0,0,0,.35);white-space:nowrap;pointer-events:none;transition:opacity .3s;max-width:70vw}
.bark::after{content:"";position:absolute;left:50%;bottom:-5px;margin-left:-5px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:5px solid rgba(239,230,210,.94)}
.emote{position:absolute;transform:translate(-50%,-100%);font-family:"DotGothic16",monospace;font-size:20px;color:#fff;text-shadow:0 2px 0 #000;pointer-events:none}
/* HUD */
#hud{position:absolute;left:calc(14px + env(safe-area-inset-left,0px));top:calc(12px + env(safe-area-inset-top,0px));display:flex;gap:12px;align-items:flex-start;pointer-events:none;transition:opacity .6s}
#count{writing-mode:vertical-rl;font-family:"Zhi Mang Xing","Yuji Syuku",serif;font-size:30px;line-height:1;color:var(--paper);text-shadow:0 2px 0 rgba(0,0,0,.6),0 0 12px rgba(0,0,0,.4);
  padding:10px 6px;background:linear-gradient(90deg,rgba(14,13,20,.0),rgba(14,13,20,.55),rgba(14,13,20,0));letter-spacing:.06em}
#count b{font-weight:400;color:var(--gold)}
#count small{font-family:"Shippori Mincho",serif;font-size:13px;color:var(--dim);margin-top:8px;letter-spacing:.3em}
#count.pop b{animation:pop .6s ease-out}
@keyframes pop{0%{transform:scale(1.5);color:#fff}100%{transform:none}}
#gauges{position:absolute;left:calc(14px + env(safe-area-inset-left,0px));bottom:calc(16px + env(safe-area-inset-bottom,0px));display:flex;flex-direction:column;gap:7px;pointer-events:none;transition:opacity .5s;
  font-family:"Shippori Mincho",serif;font-size:13px;color:var(--paper2);letter-spacing:.1em;text-shadow:0 1px 0 #000}
.g{display:flex;align-items:center;gap:8px}
.g em{font-style:normal;font-family:"Zhi Mang Xing",serif;font-size:20px;color:var(--paper);width:20px;text-align:center}
.pips{display:flex;gap:3px}.pips i{width:9px;height:9px;border:1px solid rgba(232,176,74,.7);transform:rotate(45deg);margin:2px}
.pips i.f{background:var(--gold);box-shadow:0 0 8px rgba(232,176,74,.8)}
.bar{width:112px;height:6px;background:rgba(239,230,210,.12);border:1px solid rgba(239,230,210,.25);position:relative}
.bar i{position:absolute;left:0;top:0;bottom:0;background:var(--paper2)}
.bar.warn i{background:var(--ver)}
/* prompts */
#prm{position:absolute;left:50%;bottom:calc(22px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);display:flex;gap:14px;pointer-events:none;transition:opacity .2s}
.pr{display:flex;align-items:center;gap:7px;padding:5px 11px 6px 6px;background:rgba(12,11,17,.72);border-left:2px solid var(--gold);font-size:14px;color:var(--paper);letter-spacing:.05em;white-space:nowrap}
.pr kbd{font-family:"DotGothic16",monospace;font-size:12px;min-width:22px;padding:2px 5px;text-align:center;background:var(--paper);color:#1b1612;border-radius:2px}
.pr b{font-family:"Zhi Mang Xing",serif;font-weight:400;font-size:19px;color:var(--gold)}
.pr span{color:var(--paper2);font-size:13px}
/* shrine card */
#site{position:absolute;right:calc(16px + env(safe-area-inset-right,0px));top:calc(16px + env(safe-area-inset-top,0px));width:200px;padding:14px 16px 12px;background:rgba(239,230,210,.94);color:#2a1d16;
  box-shadow:0 3px 0 rgba(0,0,0,.35);pointer-events:none;opacity:0;transform:translateY(-6px);transition:opacity .35s,transform .35s}
#site.on{opacity:1;transform:none}
#site h3{margin:0 0 8px;font-family:"Zhi Mang Xing",serif;font-weight:400;font-size:24px;letter-spacing:.1em;display:flex;justify-content:space-between;align-items:baseline}
#site h3 small{font-family:"Shippori Mincho",serif;font-size:12px;color:#7a6b58;letter-spacing:.2em}
#site ul{list-style:none;margin:0;padding:0;font-size:14px;line-height:1.9}
#site li{display:flex;justify-content:space-between;border-bottom:1px dashed rgba(42,29,22,.2)}
#site li.ok{color:#8a7d6a;text-decoration:line-through}
#site .st{margin-top:8px;font-size:12px;color:#7a6b58;letter-spacing:.15em}
/* offering note */
#note{position:absolute;right:calc(16px + env(safe-area-inset-right,0px));bottom:calc(90px + env(safe-area-inset-bottom,0px));width:min(340px,80vw);padding:12px 16px;background:rgba(14,13,20,.86);border-left:2px solid var(--gold);
  color:var(--paper);font-size:15px;line-height:1.75;letter-spacing:.03em;pointer-events:none;opacity:0;transform:translateX(8px);transition:opacity .4s,transform .4s}
#note.on{opacity:1;transform:none}
#note h4{margin:0 0 4px;font-family:"Zhi Mang Xing",serif;font-weight:400;font-size:20px;color:var(--gold);letter-spacing:.1em}
/* title */
#title{position:absolute;inset:0;display:flex;align-items:center;justify-content:flex-end;padding:0 10vw;pointer-events:auto;transition:opacity 1.2s}
#title .tt{display:flex;flex-direction:row-reverse;gap:22px;align-items:flex-start}
#title h1{margin:0;writing-mode:vertical-rl;font-family:"Yuji Syuku","Zhi Mang Xing",serif;font-weight:400;font-size:clamp(64px,11vw,132px);line-height:1;color:var(--paper);letter-spacing:.04em;text-shadow:0 4px 0 rgba(0,0,0,.45),0 0 40px rgba(0,0,0,.4)}
#title h2{margin:28px 0 0;writing-mode:vertical-rl;font-family:"Yuji Syuku",serif;font-weight:400;font-size:clamp(22px,3vw,34px);color:var(--gold);letter-spacing:.3em;text-shadow:0 2px 0 rgba(0,0,0,.5)}
#title .seal{width:46px;height:46px;background:var(--ver);color:#f6e7d2;font-family:"Zhi Mang Xing",serif;font-size:21px;display:flex;align-items:center;justify-content:center;line-height:1.05;text-align:center;margin-top:18px;box-shadow:0 2px 0 rgba(0,0,0,.4)}
#title nav{position:absolute;left:10vw;bottom:14vh;display:flex;flex-direction:column;gap:10px}
#title button{all:unset;cursor:pointer;font-family:"Shippori Mincho",serif;font-size:18px;letter-spacing:.3em;color:var(--paper2);padding:6px 0 6px 18px;border-left:2px solid transparent;transition:color .2s,border-color .2s}
#title button:hover,#title button:focus-visible,#title button.sel{color:var(--paper);border-left-color:var(--ver)}
#title .hint{position:absolute;left:10vw;bottom:7vh;font-size:12px;color:var(--dim);letter-spacing:.2em}
#tcard{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;pointer-events:none;opacity:0;transition:opacity 1.6s}
#tcard.on{opacity:1}
#tcard h1{margin:0;font-family:"Yuji Syuku",serif;font-weight:400;font-size:clamp(46px,8vw,96px);color:var(--paper);letter-spacing:.2em;text-shadow:0 0 30px rgba(0,0,0,.8)}
#tcard p{margin:0;font-family:"Shippori Mincho",serif;font-size:clamp(14px,1.8vw,18px);color:var(--paper2);letter-spacing:.5em}
#toast{position:absolute;left:50%;top:calc(12% + env(safe-area-inset-top,0px));transform:translateX(-50%);padding:6px 18px;background:rgba(12,11,17,.75);border-top:1px solid rgba(239,230,210,.25);border-bottom:1px solid rgba(239,230,210,.25);
  font-size:15px;letter-spacing:.14em;color:var(--paper);opacity:0;transition:opacity .4s;pointer-events:none;white-space:nowrap}
#toast.on{opacity:1}
#pause{position:absolute;inset:0;background:rgba(8,7,12,.62);display:flex;align-items:center;justify-content:center;pointer-events:auto}
#pause .pn{min-width:min(420px,88vw);padding:26px 30px;background:rgba(239,230,210,.95);color:#2a1d16;box-shadow:0 4px 0 rgba(0,0,0,.4)}
#pause h3{margin:0 0 14px;font-family:"Zhi Mang Xing",serif;font-weight:400;font-size:30px;letter-spacing:.2em}
#pause p{margin:6px 0;font-size:14px;line-height:1.8;color:#4a3d30}
#pause kbd{font-family:"DotGothic16",monospace;font-size:12px;padding:1px 5px;background:#2a1d16;color:#efe6d2;border-radius:2px}
#pause button{all:unset;cursor:pointer;margin-top:16px;margin-right:18px;font-size:15px;letter-spacing:.2em;border-bottom:1px solid #2a1d16}
#loading{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;background:#0c0b10;z-index:9}
#loading .k{font-family:"Yuji Syuku","Zhi Mang Xing",serif;font-size:clamp(40px,8vw,84px);letter-spacing:.08em;color:var(--paper)}
#loading .b{width:min(300px,64vw);height:2px;background:#26222e}
#loading .b i{display:block;height:100%;width:0;background:var(--ver);transition:width .2s}
#loading .t{font-size:13px;color:var(--dim);letter-spacing:.3em}
#touch{position:absolute;right:calc(14px + env(safe-area-inset-right,0px));bottom:calc(14px + env(safe-area-inset-bottom,0px));display:grid;grid-template-columns:repeat(3,58px);gap:8px;pointer-events:auto}
#touch button{all:unset;width:58px;height:58px;border-radius:50%;background:rgba(14,13,20,.5);border:1px solid rgba(239,230,210,.3);color:var(--paper);font-family:"Zhi Mang Xing",serif;font-size:22px;display:flex;align-items:center;justify-content:center;touch-action:none}
@media (prefers-reduced-motion:reduce){#dlg .nx{animation:none}#count.pop b{animation:none}}
`,
  init() {
    const st = document.createElement("style"); st.textContent = this.css; document.head.appendChild(st);
    const ui = document.getElementById("ui");
    ui.innerHTML = `
<div id="hud" style="opacity:0"><div id="count"><b>三</b><small>供物</small></div></div>
<div id="gauges" style="opacity:0"><div class="g"><em>重</em><div class="pips" id="pips"></div></div><div class="g"><em>負</em><div class="bar" id="load"><i></i></div><span id="loadT"></span></div><div class="g"><em>息</em><div class="bar" id="stam"><i></i></div></div></div>
<div id="prm"></div>
<div id="site"><h3>祠<small>再建</small></h3><ul id="siteL"></ul><div class="st" id="siteS"></div></div>
<div id="note"><h4 id="noteH"></h4><div id="noteT"></div></div>
<div id="barks"></div>
<div id="sub"></div>
<div id="dlg"><canvas class="port" width="96" height="96"></canvas><div class="name"><i></i><span></span><small></small></div><div class="txt"></div><div class="nx"></div></div>
<div id="toast"></div>
<div id="tcard"><h1></h1><p></p></div>
<div class="fade" id="fade"></div>`;
    for (const id of ["hud", "count", "gauges", "pips", "load", "loadT", "stam", "prm", "site", "siteL", "siteS", "note", "noteH", "noteT", "barks", "sub", "dlg", "toast", "tcard", "fade"]) this.el[id] = document.getElementById(id);
    this.el.port = this.el.dlg.querySelector(".port"); this.el.name = this.el.dlg.querySelector(".name span"); this.el.nameS = this.el.dlg.querySelector(".name small"); this.el.txt = this.el.dlg.querySelector(".txt");
    this.el.pips.innerHTML = "<i></i>".repeat(6);
    this.el.dlg.addEventListener("pointerdown", () => { this.advanceReq = true; });
    if (IS_TOUCH) this.touchUI();
  },
  blocking() { return !!this.dlg || this.blockN > 0; },
  /* ---------- dialogue ---------- */
  WHO: { tsuzura: { name: "葛笼", sub: "ツヅラ", voice: "tsuzura" }, radio: { name: "铁匣子", sub: "", voice: "radio", cls: "radio" }, kago: { name: "籠丸", sub: "カゴマル", voice: "kago" }, narr: { name: "", sub: "", voice: null } },
  say(lines) {
    return new Promise(res => {
      const D = this.dlg = { lines, i: 0, ch: 0, t: 0, res, done: false };
      this.el.dlg.classList.add("on");
      this.showLine();
      AU.duck && AU.duck(.35, 99);
    });
  },
  showLine() {
    const D = this.dlg, L = D.lines[D.i]; const W = this.WHO[L.who || "tsuzura"];
    this.el.dlg.classList.toggle("radio", W.cls === "radio");
    this.el.dlg.classList.toggle("noport", L.who !== "tsuzura");
    this.el.name.textContent = W.name; this.el.nameS.textContent = W.sub;
    this.el.dlg.querySelector(".name i").style.display = W.name ? "" : "none";
    if (L.who === "tsuzura" || !L.who) { const pc = PORTRAIT.tsuzura(L.expr || "normal"); const g = this.el.port.getContext("2d"); g.clearRect(0, 0, 96, 96); g.drawImage(pc, 0, 0); this.el.port.style.display = ""; this.el.port.classList.add("bump"); setTimeout(() => this.el.port.classList.remove("bump"), 160); if (PL.e && L.expr) { PL.e.expr = L.expr; PL.e.exprT = 99; } }
    else this.el.port.style.display = "none";
    D.ch = 0; D.t = 0; D.done = false; this.el.txt.textContent = ""; this.el.dlg.classList.remove("done");
  },
  tickDialogue(dt) {
    const D = this.dlg; if (!D) return;
    const L = D.lines[D.i], txt = L.text; const W = this.WHO[L.who || "tsuzura"];
    if (QS.auto && D.done) { D.autoT = (D.autoT || 0) + dt; if (D.autoT > .9) { D.autoT = 0; this.advanceReq = true; } }
    const adv = IN.hit.ok || IN.hit.skip || this.advanceReq; this.advanceReq = false;
    if (!D.done) {
      D.t += dt * (IN.act.skip ? 4 : 1);
      const speed = L.slow ? 16 : 34;
      while (D.t > 1 / speed && D.ch < txt.length) {
        const c = txt[D.ch]; D.t -= 1 / speed; D.ch++;
        if ("，、".includes(c)) D.t -= .09; else if ("。！？…—".includes(c)) D.t -= .2;
        if (W.voice && c.trim() && !"，。、！？…—「」（）".includes(c) && D.ch % 2 === 1) AU.sfx("blip", { voice: W.voice, i: D.ch });
      }
      this.el.txt.textContent = txt.slice(0, D.ch);
      if (D.ch >= txt.length) { D.done = true; this.el.dlg.classList.add("done"); }
      else if (adv) { D.ch = txt.length; this.el.txt.textContent = txt; D.done = true; this.el.dlg.classList.add("done"); }
    } else if (adv) {
      AU.sfx("ui_move");
      D.i++; if (D.i >= D.lines.length) { this.el.dlg.classList.remove("on"); this.dlg = null; if (PL.e) { PL.e.exprT = .01; } AU.duck && AU.duck(0, .5); setTimeout(() => D.res(), 120); }
      else this.showLine();
    }
  },
  /* ---------- subtitles (cinematic) ---------- */
  sub(text, o = {}) {
    return new Promise(res => {
      const el = this.el.sub; el.classList.toggle("mid", !!o.mid); el.textContent = text; el.classList.add("on");
      const dur = o.dur ?? Math.max(2.6, text.length * .16);
      this.blockN++;
      after(dur, () => { el.classList.remove("on"); after(.9, () => { this.blockN--; res(); }); });
    });
  },
  /* ---------- barks: short lines over her head ---------- */
  bark(text, o = {}) {
    if (!PL.e) return;
    const b = document.createElement("div"); b.className = "bark"; b.textContent = text; this.el.barks.appendChild(b);
    const item = { el: b, t: o.dur ?? Math.max(2.2, text.length * .17), who: o.who || PL.e };
    this.barkQ.push(item);
    // only the newest few stay
    while (this.barkQ.length > 2) { const old = this.barkQ.shift(); old.el.remove(); }
    if (o.expr && PL.e) { PL.e.expr = o.expr; PL.e.exprT = item.t; }
    let n = 0; for (const c of text) if (c.trim() && n++ % 3 === 0 && n < 18) after(n * .03, () => AU.sfx("blip", { voice: "tsuzura", i: n }));
  },
  emote(e) {
    if (!this.emEl) { this.emEl = document.createElement("div"); this.emEl.className = "emote"; this.el.barks.appendChild(this.emEl); }
    const [sx, sy] = RD.worldToScreen(e.x, e.y, e.z + 52); this.emEl.style.left = sx + "px"; this.emEl.style.top = sy + "px"; this.emEl.textContent = e.emote; this.emEl.style.opacity = e.emote ? 1 : 0;
  },
  /* ---------- HUD ---------- */
  showHud(on) { this.el.hud.style.opacity = on ? 1 : 0; this.el.gauges.style.opacity = on ? 1 : 0; this.hudOn = on; },
  countPop(n, art, first) {
    const c = this.el.count; c.querySelector("b").textContent = kanjiNum(n); c.classList.remove("pop"); void c.offsetWidth; c.classList.add("pop");
    if (!first) { this.bark(kanjiNum(n) + "。", { dur: 1.4 }); AU.sfx("count", { n }); }
  },
  note(title, text, dur = 6) { this.el.noteH.textContent = title; this.el.noteT.textContent = text; this.el.note.classList.add("on"); clearTimeout(this.noteTO); this.noteTO = setTimeout(() => this.el.note.classList.remove("on"), dur * 1000); },
  siteCard(force) {
    const P = PL.e; const near = P && SITE.e && hyp(SITE.e.x - P.x, SITE.e.y - P.y) < 120 && GAME.state === "play" && !GAME.cine;
    const on = (near || force) && SITE.stage < 4;
    this.el.site.classList.toggle("on", !!on);
    if (!on) return;
    const n = SITE.cur(), names = { base: "平石（礎石）", pillar: "柱 · 杉木或竹竿", roof: "杉树皮", rope: "葛藤（注连绳）", god: "御神体 · 穴石" };
    this.el.siteL.innerHTML = Object.keys(n).map(k => `<li class="${SITE.have[k] >= n[k] ? "ok" : ""}"><span>${names[k]}</span><span>${SITE.have[k]}/${n[k]}</span></li>`).join("");
    this.el.siteS.textContent = ["其一 · 礎", "其二 · 柱", "其三 · 屋根", "其四 · 御神体"][SITE.stage] || "";
  },
  prompts(list) {
    const k = JSON.stringify(list); if (k === this.lastPrm) return; this.lastPrm = k;
    this.el.prm.innerHTML = (list || []).map(([a, v, d]) => `<div class="pr"><kbd>${IN.glyph(a)}</kbd><b>${v}</b><span>${d}</span></div>`).join("");
  },
  toast(t, dur = 2.4) { const el = this.el.toast; el.textContent = t; el.classList.add("on"); clearTimeout(this.toastTO); this.toastTO = setTimeout(() => el.classList.remove("on"), dur * 1000); },
  titleCard(h, p, dur = 4) { return new Promise(res => { const c = this.el.tcard; c.querySelector("h1").textContent = h; c.querySelector("p").textContent = p || ""; c.classList.add("on"); this.blockN++; after(dur, () => { c.classList.remove("on"); after(1.6, () => { this.blockN--; res(); }); }); }); },
  fade(a, dur = .6, col = "#000") { const f = this.el.fade; f.style.background = col; f.style.transition = `opacity ${dur}s`; f.style.opacity = a; return new Promise(r => after(dur, r)); },
  update(dt) {
    this.tickDialogue(dt);
    // barks follow her
    for (let i = this.barkQ.length - 1; i >= 0; i--) { const b = this.barkQ[i]; b.t -= dt; const w = b.who; const [sx, sy] = RD.worldToScreen(w.x, w.y, (w.z || 0) + (w === PL.e ? 50 + PL.stackH() : 30)); b.el.style.left = sx + "px"; b.el.style.top = sy + "px"; if (b.t < .3) b.el.style.opacity = Math.max(0, b.t / .3); if (b.t <= 0) { b.el.remove(); this.barkQ.splice(i, 1); } }
    const P = PL.e; if (!P || !this.hudOn) return;
    const pips = this.el.pips.children; for (let i = 0; i < 6; i++) pips[i].classList.toggle("f", i < P.tail);
    const W = PL.stackW(); this.el.load.querySelector("i").style.width = clamp(W / PL.CAP, 0, 1) * 100 + "%"; this.el.load.classList.toggle("warn", W > PL.CAP * .75); this.el.loadT.textContent = W ? W + "/" + PL.CAP : "";
    this.el.stam.querySelector("i").style.width = P.stamina * 100 + "%";
    this.prompts(GAME.canControl() ? PL.prompts : []);
    this.siteCard();
  },
  touchUI() {
    const t = document.createElement("div"); t.id = "touch";
    t.innerHTML = [["take", "取"], ["act", "拾"], ["give", "予"], ["drop", "卸"], ["run", "奔"], ["pause", "‖"]].map(([a, l]) => `<button data-a="${a}">${l}</button>`).join("");
    document.getElementById("ui").appendChild(t);
    t.querySelectorAll("button").forEach(b => { const a = b.dataset.a; b.addEventListener("pointerdown", e => { e.preventDefault(); IN.tbtn(a, true); if (a === "act") IN.tbtn("ok", true); }); b.addEventListener("pointerup", () => { IN.tbtn(a, false); IN.tbtn("ok", false); }); b.addEventListener("pointercancel", () => IN.tbtn(a, false)); });
  },
};
