/* =====================================================================
   STORY — the prologue (a dusk of counting, a night of music, the Far
   arriving), the waking (a beam, a stone, a lantern), and the first day
   of rebuilding. Every line is hers or the radio's; the narration only
   speaks twice.
   ===================================================================== */
"use strict";
const CINE = {
  wait(s) { return new Promise(r => after(s, r)); },
  until(fn) { return new Promise(r => { const chk = () => { if (fn()) r(); else after(.05, chk); }; chk(); }); },
  cam(x, y, z, k = 2.5) { GAME.camT = { x, y, z: z ?? WORLD.heightAt(x, y), k }; },
  free() { GAME.camT = null; },
  async box(on) { GAME.boxT = on ? 1 : 0; await this.wait(.6); },
  say(...lines) { return UI.say(lines.map(l => typeof l === "string" ? { who: "tsuzura", text: l } : l)); },
};
const T = (expr, text) => ({ who: "tsuzura", expr, text });
const R_ = text => ({ who: "radio", text });
const K_ = text => ({ who: "kago", text });
const N_ = text => ({ who: "narr", text });

const STORY = {
  stage: "title", barkCD: {}, areas: {}, radioN: 0,
  /* ================= PROLOGUE ================= */
  async prologue() {
    this.stage = "prologue"; GAME.cine = true; GAME.todLock = true; GAME.tod = 17.55; GAME.noSave = true;
    const [sx, sy] = LM.shrine; const P = PL.init(sx + 2, sy + 22); P.face = "front"; P.expr = "count"; P.exprT = 99;
    PROLOGUE.setup();
    UI.showHud(false);
    CINE.cam(sx, sy - 14, WD.shrineZ, 99); await CINE.box(true);
    const from = QS.from || "";
    if (from === "vista" || from === "wave") { GAME.tod = 20.8; for (const l of WORLDSETUP.lanterns) l.lit = true; await UI.fade(0, .3); if (from === "vista") { await UI.fade(1, .2); await VISTA.prologueShot(); } return this.afterVista(); }
    AU.music("prologue", { fade: 4 });
    await UI.fade(0, 3.2);
    await CINE.wait(1.2);
    await CINE.say(T("count", "……九十六。九十七。"), T("thinking", "九十八。"));
    P.face = "back"; await CINE.wait(.7); P.face = "side"; P.flip = true; await CINE.wait(.5);
    PROLOGUE.cap = true; AU.sfx("offering"); P.face = "front";
    await CINE.say(T("surprised", "——九十九。"), T("smug", "好。今天也是九十九。"));
    PROLOGUE.crow = mkCrow(sx + 2, sy + 66, WD.shrineZ + 50); AU.sfx("wings", { x: sx, y: sy + 60 });
    await CINE.wait(1.1);
    P.expr = "smug"; P.exprT = 99;
    await CINE.say(T("smug", "吾乃九十九折峠之主，葛笼是也！"));
    await CINE.wait(1.3);
    await CINE.say(T("normal", "……这种时候，你应该鼓掌。"));
    PROLOGUE.crow.state = "fly"; PROLOGUE.crow.vx = 70; PROLOGUE.crow.vy = -20; PROLOGUE.crow.vz = 60; AU.sfx("crow", { x: sx, y: sy + 60 }); AU.sfx("wings", { x: sx, y: sy + 60 });
    await CINE.wait(.8);
    await CINE.say(T("angry", "没礼貌。一枚瓶盖都没供过的家伙。"));
    // she looks down the old road
    P.face = "front"; CINE.cam(ROAD[3][0] + 60, ROAD[3][1], null, 1.2); await CINE.wait(2.6);
    await CINE.say(T("soft", "上一个走这条路的人，是三年前的夏天。"), T("soft", "留下这个瓶盖，许愿说想变瘦。"), T("grin", "……这个愿望有点难。本座还在考虑。"));
    CINE.cam(sx, sy + 6, WD.shrineZ, 1.4);
    // dusk falls into night
    await CINE.wait(1.2); AU.music("none", { fade: 6 });
    after(4, () => { for (const l of WORLDSETUP.lanterns) l.lit = true; AU.sfx("ui_ok"); });
    await PROLOGUE.timelapse(17.6, 20.6, 7);
    P.expr = "normal"; await CINE.wait(1.2);
    PROLOGUE.radioOn = true; AU.radio(true, { x: sx - 14, y: sy + 2, signal: .2 });
    await CINE.wait(1.6);
    await CINE.say(T("surprised", "……嗯？"), R_("……沙……沙沙……"), T("thinking", "你不是四十年前就坏了吗。"));
    AU.festival(.25, { near: 0 }); AU.radio(true, { x: sx - 14, y: sy + 2, signal: .8 });
    await CINE.wait(3);
    await CINE.say(T("thinking", "……祭囃子？"), T("soft", "今天十六号。送魂的晚上。"), T("soft", "山下在跳盆舞吧。"));
    AU.festival(.55, { near: .2 }); await CINE.wait(2.5);
    await CINE.say(T("worried", "……不对。"), T("worried", "声音不是从山下来的。"), T("surprised", "是从四面八方。"));
    // the climb, then the view from the crown of the great camphor
    await UI.fade(1, 1.2);
    AU.radio(false);
    await VISTA.prologueShot();
    return this.afterVista();
  },
  async afterVista() {
    // back on the pass: the wave arrives
    await PROLOGUE.wave();
    await CINE.wait(1.5);
    AU.festival(0, { near: 0 });
    await UI.sub("那一夜，所有的东西，都离得远了一点。", { mid: true, dur: 5.5 });
    await CINE.wait(.8);
    AU.stinger("title_hit");
    await UI.titleCard("ツヅラ", "遠 囃 子", 4.2);
    await CINE.wait(.6);
    PROLOGUE.teardown();
    await this.wake();
  },
  /* ================= WAKING ================= */
  async wake() {
    this.stage = "wake"; GAME.cine = true; GAME.noSave = true;
    const [sx, sy] = LM.shrine; GAME.tod = 6.35; GAME.todLock = false;
    const P = PL.init(sx + 26, sy + 28); P.state = "pinned"; P.face = "front"; P.expr = "dazed"; P.exprT = 99;
    WORLDSETUP.afterFar();
    const beam = mkItem("beam", P.x + 2, P.y + 3, { carry: false }); beam.pin = true; this.beam = beam;
    GAME.extraMist = .35;
    CINE.cam(P.x, P.y - 6, P.z, 99);
    await CINE.wait(1.5);
    AU.music("none"); await UI.fade(0, 4);
    await CINE.say(T("dazed", "……"), T("dazed", "……重。"), T("angry", "好重。哪个混账把柱子扔在本座身上了。"));
    GAME.cine = false; GAME.tutorial = true; GAME.flags.knowsWeight = true; this.tut = "take";
    UI.toast("把压在身上的重量拿过来——" + IN.glyph("take") + "  取", 6);
  },
  tutorialWeight(how, t) {
    const P = PL.e;
    if (this.tut === "take" && how === "take") {
      // the whole beam pours into her at once — and she is a stone
      if (this.beam) { const left = this.beam.w; this.beam.w = 0; this.beam.carry = true; P.tail = Math.min(6, P.tail + left); this.beam.pin = false; PL.setForm("stone"); }
      this.tut = "give"; P.state = "play";
      (async () => { GAME.cine = true; await CINE.wait(1.1); await CINE.say(T("dazed", "…………"), T("normal", "……这下轮到我重了。")); GAME.cine = false; UI.toast("把重量交给旁边的石灯笼——" + IN.glyph("give") + "  予", 6); })();
    } else if (this.tut === "give" && how === "give" && P.tail <= 3) {
      this.tut = null; GAME.tutorial = false;
      (async () => {
        GAME.cine = true; await CINE.wait(.5);
        await CINE.say(T("smug", "哼。灯笼本来就该稳重一点。"), T("thinking", "这根梁……轻得像纸一样了。"), T("grin", "还能用。修祠的时候当柱子。"));
        await this.firstLook(); GAME.cine = false;
      })();
    }
  },
  async firstLook() {
    const [sx, sy] = LM.shrine; const P = PL.e;
    CINE.cam(sx, sy - 70, null, 1.2); await CINE.wait(2.4);
    await CINE.say(T("surprised", "……大楠？"), T("worried", "颜色不对。像是隔着一层雾，又像是画上去的。"));
    CINE.cam(sx, sy, WD.shrineZ, 1.6); await CINE.wait(1.8);
    await CINE.say(T("worried", "祠也……只剩一半了。"), T("count", "供品呢。"), T("count", "一、二、三。"), T("shout", "……三？！"), T("angry", "本座的九十九呢！"));
    await CINE.wait(.6);
    await CINE.say(T("thinking", "……昨晚的风。吹到山里去了。"), T("smug", "好。那就一个一个捡回来。"), T("grin", "顺便，把家也修了。"));
    CINE.free(); GAME.extraMist = 0; GAME.noSave = false; GAME.flags.knowsLeaf = true;
    this.stage = "free"; UI.showHud(true); UI.countPop(GAME.count, null, true);
    AU.music("explore");
    UI.toast("九十九折峠", 3);
    GAME.save();
  },
  /* ================= the free day ================= */
  update(dt) {
    for (const k in this.barkCD) this.barkCD[k] -= dt;
    if (this.stage !== "free") return;
    const P = PL.e; if (!P || GAME.cine) return;
    const at = (n, x, y, r) => { if (!this.areas[n] && hyp(P.x - x, P.y - y) < r) { this.areas[n] = true; GAME.flags["area_" + n] = true; return true; } return false; };
    if (GAME.flags["area_hut"]) this.areas.hut = true;
    if (at("camphor", LM.shrine[0], LM.shrine[1] - 60, 30)) this.bark2("camphorNear");
    if (at("hut", LM.hut[0], LM.hut[1] + 20, 70)) this.line([T("normal", "烧炭的老爷爷的小屋。"), T("soft", "门没锁。他从来不锁门。")]);
    if (at("tunnel", LM.tunnel[0] - 30, LM.tunnel[1] + 30, 110)) this.line([T("thinking", "铁的蛇。"), T("angry", "三十年前它钻进山里以后，就再没人走九十九折了。"), T("soft", "……现在它也停下了。")]);
    if (at("inner", STAIR[2][0], STAIR[2][1], 60)) this.line([T("surprised", "奥之院……连奥之院也去远了。"), T("thinking", "那边的神，脾气比我还坏。"), T("grin", "现在大概更生气了。")]);
    if (at("pond", LM.pond[0], LM.pond[1] - 70, 90)) this.bark2("pond");
    if (at("fall", LM.pool[0], LM.pool[1], 90)) this.bark2("fall");
    if (at("bridge", 1300, 1680, 70)) this.line([T("surprised", "独木桥——"), T("worried", "……摸不到。")]);
    if (at("lookout", LM.lookout[0], LM.lookout[1] + 10, 46)) VISTA.lookoutShot();
    // the basket comes home and wakes
    if (!GAME.flags.kagoAwake && P.stack.some(s => s.kind === "basket") && hyp(P.x - LM.shrine[0], P.y - LM.shrine[1]) < 70) this.kagoWake();
  },
  line(lines) { (async () => { GAME.cine = true; await UI.say(lines); GAME.cine = false; })(); },
  BARKS: {
    shed: ["哇——！", "掉了掉了！", "……刚才那个不算。", "跑太快了。", "堆得太高，风一吹就晃。"],
    tooHeavy: ["背不动。……先把它的重量拿过来？", "太重了。先用尾巴把重量吸走。"],
    tooTall: ["再堆就要倒了。"],
    noTake: ["这附近没有能拿的重量。"],
    noGive: ["没有能接住重量的东西。"],
    emptyTail: ["尾巴里空空的。"],
    full: ["它已经装不下了。"],
    stone: ["…………", "动、动不了……"],
    leaf: ["轻飘飘的……", "哇，风！"],
    cliff: ["太高了，爬不上去。", "绕路吧。路是给人走的。"],
    climbLoad: ["背着这么多爬不上去。"],
    deep: ["水太深。……要是身子再重一点，就能在河底走过去。"],
    farAgain: ["又是这里。", "路还在，就是走不过去。", "祭囃子……在那边。"],
    delivered: ["放好了。", "嗯，像个样子了。", "再来几根。"],
    radioPick: ["……你也要跟我走？"],
    camphorNear: ["走过去，没有变近。", "明明就在眼前。"],
    pond: ["池子还在。青蛙也在。"],
    fall: ["瀑布的声音……还是近的。"],
  },
  bark(name, arg) {
    if ((this.barkCD[name] || 0) > 0) return; const L = this.BARKS[name]; if (!L) return;
    this.barkCD[name] = name === "shed" ? 3 : 8;
    const i = (this.barkN = (this.barkN || 0) + 1);
    UI.bark(L[i % L.length], { expr: { shed: "surprised", stone: "dazed", tooHeavy: "worried", leaf: "surprised", cliff: "thinking", deep: "thinking", farAgain: "worried" }[name] });
  },
  bark2(name) { const L = this.BARKS[name]; if (!L) return; L.forEach((t, i) => after(i * 2.4, () => UI.bark(t))); },
  /* ---------- one-off events ---------- */
  event(name) {
    if (name === "farTouch") this.line([T("worried", "……？"), T("worried", "明明看得见对面的树。"), T("thinking", "走了好久，它一点都没有变近。"), T("soft", "……和大楠一样。")]);
    if (name === "basket") this.line([T("surprised", "葛笼。"), T("normal", "好结实。编的人很用心。"), T("smug", "……和本座同名。"), T("grin", "那就是本座的家臣了。走，回家。")]);
    if (name === "holed") this.line([T("grin", "找到了！御神体！"), T("worried", "……掉进潭里这种事，可不能让别人知道。")]);
  },
  async kagoWake() {
    GAME.flags.kagoAwake = true; GAME.cine = true; const P = PL.e;
    const i = P.stack.findIndex(s => s.kind === "basket"); const it = P.stack.splice(i, 1)[0];
    const bx = P.x + 18, by = P.y + 8; const tmp = mkItem("basket", bx, by, { carry: false });
    AU.sfx("place"); await CINE.wait(1);
    AU.sfx("awaken"); for (let k = 0; k < 3; k++) { tmp.vz = 60; await CINE.wait(.45); }
    await CINE.say(T("surprised", "……嗯？"));
    tmp.dead = true; tmp.gone = true; KAGOMARU.wake(bx, by); KAGOMARU.e.open = 1;
    FX.burst("glint", bx, by, P.z + 10, 16, { life: 1, c: [1, .9, .6], speed: .8, up: 1, add: true, drag: 2 });
    await CINE.wait(.8);
    await UI.say([T("surprised", "你——"), T("grin", "醒了？"), K_("咔哒。咔哒。"), T("soft", "被人用了几十年，又被本座背了一路。"), T("soft", "你也到年纪了。"),
      T("smug", "从今天起，你叫籠丸。本座的家臣，第一号。"), K_("咔哒。"), T("normal", "……第一号也是唯一一号。不许骄傲。")]);
    UI.toast("籠丸会跟着你。站在它旁边按 " + IN.glyph("drop") + "，可以把东西放进去。", 5);
    GAME.cine = false; GAME.save();
  },
  /* ---------- the radio ---------- */
  radio() {
    const n = this.radioN++; AU.radio(true, { x: LM.shrine[0] - 14, y: LM.shrine[1] + 2, signal: .9 });
    const F = [
      [R_("……沙……沙沙……"), T("thinking", "还在响。……你到底收的是哪个台？")],
      [R_("……本台消息……昨夜二十三时起……各地相继出现……所谓『远化』现象……"), T("thinking", "……远化？")],
      [R_("……请市民不要靠近变色区域……也请不要……呼唤……已经走远的家人……"), T("sad", "……")],
      [R_("……军方否认……此事与『隔』计划……有任何关联……"), T("thinking", GAME.flags.readDiary ? "『隔』。烧炭爷爷的孙女，也说过这个字。" : "『隔』……？")],
      [R_("……听得见吗……这里是……第七……我们还在……还在这里……"), T("worried", "……喂？"), T("shout", "喂！"), R_("……沙沙……")],
    ];
    const lines = F[n] || [T("normal", "又只剩祭囃子了。")];
    this.line(lines);
    after(12, () => AU.radio(false));
  },
  diary() {
    GAME.flags.readDiary = true;
    this.line([N_("八月十二日。晴。出了一窑好炭。"), N_("八月十四日。孙女来信，说城里在建一个叫『隔』的东西。建成了，打仗就打不到咱们这边。"), N_("她说是好事。只是往后见面，要提前申请。"),
      N_("见自己的爷爷，申请什么。"), N_("八月十五日。明天上峠，给貂大人送柿子。"), T("sad", "……柿子。"), T("soft", "每年都是他自己吃掉一半。"), T("sad", "十六号，他没有来。")]);
  },
  jizo() { const L = [["地藏，借你的肩膀歇一下。"], ["……还是不说话。好习惯。"], ["替我看着路。"]]; const t = L[(this.jz = (this.jz || 0) + 1) % L.length]; UI.bark(t[0]); GAME.save(); UI.toast("记下了。", 1.4); PL.e.stamina = 1; },
  /* ---------- offerings: who left them ---------- */
  OFFER: {
    coin: ["五円硬币", "五円，“御缘”。想和谁结缘的人，总是给五円。"],
    sandal: ["旧草鞋", "走坏的草鞋。挑夫把它挂在这里，换一个平安翻山。"],
    crane: ["纸鹤", "折的人手很笨，脖子歪了。……所以记得特别清楚。"],
    marble: ["弹珠", "一个小鬼拿它换了“明天别下雨”。第二天下了。我到现在还欠他一个晴天。"],
    top: ["陀螺", "转得最久的那个孩子，后来去了城里。"],
    comb: ["木梳", "出嫁那天，新娘走九十九折下山，把旧梳子留在这里。"],
    harmonica: ["口琴", "一个兵吹着它上山，又吹着它下山，打仗去了。"],
    bell: ["铃铛", "……和我身上这个是一对。另一个，是谁的来着。"],
    letter: ["没寄出的信", "收信人的名字被雨泡掉了。"],
    doll: ["人偶", "供它的人说：替我女儿生病吧。女儿后来好了。人偶的脸，有点发白。"],
    button: ["第二颗纽扣", "学生制服的第二颗。听说这一颗特别值钱。"],
    ribbon: ["发带", "“希望下次见面，他认得出我。”"],
    pipe: ["烟斗", "烧炭的老爷爷每年春天来抽一斗，说是供给本座的。烟都是他自己抽了。"],
    cap: ["瓶盖", "三年前那个夏天的。最新的一个。"],
    fan: ["扇子", "盆舞的时候用的。扇面上的金箔，掉得差不多了。"],
    candle: ["蜡烛", "没点过。供它的人说，等回来再点。"],
    omamori: ["别家的御守", "拿别人家的护身符来拜本座。胆子不小。"],
    sake: ["酒壶", "空的。……不是本座喝的。是风。"],
    pinwheel: ["风车", "山顶风大，它转了好几年，有一天自己停了。"],
    glasses: ["眼镜", "“希望能看清楚一点。”看清楚什么，他没说。"],
    tin: ["糖果罐", "里面的糖……被老鼠吃了。是老鼠。"],
    soldier: ["锡兵", "一个男孩说：替爸爸站岗。"],
    photo: ["全家福", "中间那个人的脸，被拇指摸得最白。"],
    persimmon: ["柿蒂", "柿子本身，本座替神明尝过了。"],
    inkstone: ["砚台", "落榜的书生留下的，说再也不写了。第二年他回来，又借走了。"],
    key: ["钥匙", "“等我回来开门。”门在哪儿，他没说。"],
  },
  offering(art) { const o = this.OFFER[art]; if (o) UI.note(o[0], o[1], 7); },
  /* ---------- the shrine, stage by stage ---------- */
  onStage(st) {
    AU.sfx("build_done"); AU.stinger("build"); RD.cam.shake = 2;
    FX.burst("glint", SITE.e.x, SITE.e.y, SITE.e.z + 20, 24, { life: 1.2, c: [1, .9, .6], speed: 1, up: 1.2, add: true, drag: 2 });
    if (st === 1) this.line([T("grin", "基础打好了。"), T("normal", "接下来是柱子。")]);
    if (st === 2) this.line([T("smug", "有骨头了。"), T("thinking", "屋顶……杉树皮。倒下的杉木旁边应该有。")]);
    if (st === 3) this.line([T("soft", "屋顶有了。今晚可以睡在里面。"), T("thinking", "还差注连绳……和御神体。")]);
    if (st === 4) this.ending();
  },
  async ending() {
    GAME.cine = true; GAME.flags.shrineDone = true; const [sx, sy] = LM.shrine;
    CINE.cam(sx, sy, WD.shrineZ, 1.2); await CINE.box(true);
    await CINE.wait(1.2);
    AU.stinger("complete"); NEARMAP.startWave(sx, sy, 420, 1);
    for (const g of GHOSTS.list) if (g.tag === "camphor") g.par = .7;
    await CINE.wait(3.2);
    await CINE.say(T("soft", "……回来了一点。"), T("soft", "就一点点。"));
    if (GAME.tod > 6 && GAME.tod < 19.5) await PROLOGUE.timelapse(GAME.tod, 20.4, 6);
    await CINE.wait(1);
    await CINE.say(T("count", "今天捡回来的供品……"), T("count", "……" + kanjiNum(GAME.count) + "。"), T("smug", "离九十九还远。"));
    ENDING.lanterns = true; CINE.cam(ROAD[13][0], ROAD[13][1], null, .5);
    await CINE.wait(5);
    await CINE.say(T("surprised", "……灯。"), T("surprised", "有人在爬九十九折。"), T("soft", "三年来，第一次。"));
    await CINE.wait(1.5);
    await UI.titleCard("第一章　九十九折の宿", "つ づ く", 5);
    CINE.free(); await CINE.box(false); GAME.cine = false; GAME.flags.ended = true; GAME.save();
  },
};

/* ---------------------------------------------------------------------
   PROLOGUE staging — the intact pass before the Far, the wave itself.
   --------------------------------------------------------------------- */
const PROLOGUE = {
  on: false, cap: false, radioOn: false, wavePos: -1, offs: [],
  setup() {
    this.on = true; SITE.stage = 4; const [sx, sy] = LM.shrine;
    for (const g of GHOSTS.list) g.hidden = true;
    const arts = Object.keys(OFFER_ART); this.offs = [];
    for (let i = 0; i < 18; i++) this.offs.push({ art: arts[i % arts.length], x: sx - 17 + (i % 9) * 4, y: sy + 4 + Math.floor(i / 9) * 4 });
  },
  teardown() { this.on = false; this.wavePos = -1; for (const g of GHOSTS.list) g.hidden = false; for (const l of WORLDSETUP.lanterns) l.lit = false; },
  draw() {
    if (!this.on) return; const [sx, sy] = LM.shrine;
    // the great camphor, still near
    if (this.wavePos < 0 || this.wavePos > -1e9) { const passed = this.wavePos >= 0 && this.wavePos < sy - 70; if (!passed) RD.sprite({ x: sx + 4, y: sy - 70, z: WORLD.heightAt(sx + 4, sy - 70), r: ATLAS.rects.camphor, sway: .7 }); }
    for (const o of this.offs) if (!o.gone) RD.sprite({ x: o.x, y: o.y, z: WD.shrineZ + 9, r: ATLAS.rects["off_" + o.art], shadow: 0 });
    if (this.cap) RD.sprite({ x: sx + 18, y: sy + 8, z: WD.shrineZ + 9, r: ATLAS.rects.off_cap, shadow: 0 });
    RD.sprite({ x: sx - 14, y: sy + 2, z: WD.shrineZ, r: ATLAS.rects.radio });
    if (this.radioOn) { const k = .6 + Math.random() * .4; RD.light(sx - 12, sy + 4, WD.shrineZ + 8, 30, .9 * k, .7 * k, .4 * k); }
  },
  async timelapse(a, b, dur) { const t0 = GAME.t; GAME.todLock = true; await CINE.until(() => { const k = clamp((GAME.t - t0) / dur, 0, 1); GAME.tod = lerp(a, b, sstep(0, 1, k)); return k >= 1; }); },
  // the front of the Far sweeps up the mountain: everything behind it goes pale and drifts
  async wave() {
    const [sx, sy] = LM.shrine; GAME.tod = 21; CINE.cam(sx, sy + 10, WD.shrineZ, 99);
    await UI.fade(0, .6);
    AU.festival(1, { near: 1 }); AU.sfx("far_wave"); AU.music("tension", { fade: 1 });
    PL.e.expr = "shout"; PL.e.exprT = 99; PL.e.face = "front";
    const y0 = sy + 260, y1 = sy - 260, dur = 6.5, t0 = GAME.t;
    await CINE.until(() => {
      const k = clamp((GAME.t - t0) / dur, 0, 1); this.wavePos = lerp(y0, y1, easeIn(k) * .6 + k * .4); RD.cam.shake = 1 + k * 3;
      // the front: a curtain of pale motes and scattered offerings
      for (let i = 0; i < 18; i++) FX.spawn("farmote", sx + (Math.random() - .5) * 520, this.wavePos + (Math.random() - .5) * 10, WORLD.heightAt(sx, this.wavePos) + Math.random() * 60, { life: 1.6, c: [.82, .88, 1], a: .9, vz: 30 + Math.random() * 40, vy: -40, add: true, fade: .6 });
      if (this.wavePos < sy + 20) for (const o of this.offs) if (!o.gone && Math.random() < .06) { o.gone = true; FX.spawn("leaf", o.x, o.y, WD.shrineZ + 10, { life: 3, c: [.95, .85, .6], vx: (Math.random() - .5) * 200, vy: -80 - Math.random() * 100, vz: 120, g: 120, size: 2, fade: .5 }); }
      if (this.wavePos < sy && SITE.stage === 4) { SITE.stage = 0; for (const g of GHOSTS.list) if (g.tag === "hokora" || g.tag === "camphor") g.hidden = false; AU.sfx("thud"); RD.cam.shake = 6; PL.e.state = "pinned"; }
      RD.farWave = this.wavePos;
      return k >= 1;
    });
    RD.farWave = null;
    await UI.fade(1, .15, "#f4f1ea"); await CINE.wait(.3); AU.music("none", { fade: .1 });
    await UI.fade(1, 1.2, "#000");
  },
};
const ENDING = { lanterns: false, t: 0,
  draw() { if (!this.lanterns) return; this.t += GAME.dt; const n = 7;
    for (let i = 0; i < n; i++) { const p = clamp((this.t * .012 + i * .035) % 1, 0, 1) * .45; const s = (ROAD.length - 1) * (1 - p) ; const a = Math.floor(s), f = s - a; const A = ROAD[Math.min(a, ROAD.length - 1)], B = ROAD[Math.min(a + 1, ROAD.length - 1)]; const x = lerp(A[0], B[0], f), y = lerp(A[1], B[1], f), z = WORLD.heightAt(x, y) + 14;
      RD.light(x, y, z, 50, .9, .55, .25); RD.glow(1, x, y, z, 14, 14, .9, .5, .2, .9); RD.part(x, y, z, 2, 1, .8, .4, 1, true); } } };

/* ---------------------------------------------------------------------
   WORLDSETUP — populate the pass after the Far: loose materials, the
   offerings, ghosts, lanterns, notes, animals.
   --------------------------------------------------------------------- */
const WORLDSETUP = {
  done: false,
  base() {
    const [sx, sy] = LM.shrine;
    SITE.init();
    this.lanterns = [mkLantern(sx - 34, sy + 40), mkLantern(sx + 34, sy + 40)];
    // the radio among what is left of the offerings
    mkInteract("radio", sx - 14, sy + 2, { verb: "听", label: "铁匣子", interact: () => STORY.radio(), draw() { RD.sprite({ x: this.x, y: this.y, z: this.z, r: ATLAS.rects.radio, tint: this.hl ? [1.15, 1.12, 1.05, 0] : T4 }); } });
    // ghosts of what went Far
    GHOSTS.add("camphor", sx + 4, sy - 70, { par: .86, range: 560, tag: "camphor" });
    GHOSTS.add("hokora4", sx + 6, sy - 26, { par: .9, range: 300, tag: "hokora", z: WD.shrineZ });
    GHOSTS.add("train", LM.train[0], LM.train[1], { par: .8, range: 420 });
    GHOSTS.add("log1", 1300, 1680, { par: .75, range: 260, tag: "bridge" });
    GHOSTS.add("hut", LM.inner[0], LM.inner[1] - 10, { par: .88, range: 520, z: WORLD.heightAt(LM.inner[0], LM.inner[1]) + 40 });
    GHOSTS.add("toriiBig", 1150, 400, { par: .85, range: 300 });
    for (const g of GHOSTS.list) if (g.tag === "camphor" || g.tag === "hokora") g.hidden = true;
    // jizō along the road keep her place
    for (const p of WD.props) if (p.kind === "jizo") mkInteract("jizo", p.x, p.y, { verb: "拜", label: "地藏", interact: () => STORY.jizo(), solid: 0 });
    mkInteract("note", LM.hut[0] + 6, LM.hut[1] + 14, { verb: "读", label: "炭焼き日誌", interact: () => STORY.diary() });
    mkCrow(sx + 150, sy + 120, WORLD.heightAt(sx + 150, sy + 120) + 40);
    for (let i = 0; i < 4; i++) mkDeer(1900 + i * 40, 1420 + (i % 2) * 30);
  },
  afterFar() {
    if (this.done) return; this.done = true;
    const [sx, sy] = LM.shrine; const R = RNG(99);
    for (const g of GHOSTS.list) if (g.tag === "camphor" || g.tag === "hokora") g.hidden = false;
    // the pale scars of the night
    NEARMAP.scar(sx, sy - 20, 150, .42); NEARMAP.scar(1300, 1680, 90, .3); NEARMAP.scar(LM.inner[0], LM.inner[1] + 60, 110, .35); NEARMAP.scar(1720, 1460, 120, .5); NEARMAP.scar(780, 1180, 110, .5);
    RD.uploadNear(true);
    // building materials, where a mountain would leave them
    const put = (k, x, y) => mkItem(k, x, y);
    put("flat", 1418, 690); put("flat", 1640, 1120); put("flat", 1180, 1752);
    for (const [x, y] of [[690, 820], [760, 1010], [560, 1140], [880, 640]]) put("log", x, y);
    for (const [x, y] of [[530, 1490], [536, 1500], [524, 1512], [330, 1700], [600, 1780]]) put("pole", x, y);
    for (const [x, y] of [[706, 836], [772, 1028], [574, 1156], [640, 980], [900, 660]]) put("bark", x, y);
    for (const [x, y] of [[960, 900], [1330, 1270], [820, 1350]]) put("vine", x, y);
    put("holed", 1690, 1088);
    put("basket", LM.hut[0] - 20, LM.hut[1] + 26);
    // the offerings, flung across the mountain by the night wind
    const arts = Object.keys(OFFER_ART); let idx = 0;
    const spots = [];
    for (let k = 0; k < 4000 && spots.length < 46; k++) {
      const a = R() * TAU, d = Math.pow(R(), .7) * 900, x = sx + Math.cos(a) * d * 1.1, y = sy + 120 + Math.sin(a) * d * .9 + 300;
      if (WORLD.nearAt(x, y) < .4 || WORLD.waterAt(x, y) > -500) continue; const s = Math.abs(WORLD.heightAt(x - 3, y) - WORLD.heightAt(x + 3, y)); if (s > 6) continue;
      if (spots.some(p => hyp(p[0] - x, p[1] - y) < 60)) continue; spots.push([x, y]);
    }
    for (const [x, y] of spots) mkOffering(arts[idx % arts.length], x, y, idx++);
    // three left on the plinth: the count she wakes up to
    GAME.count = 3;
  },
};
