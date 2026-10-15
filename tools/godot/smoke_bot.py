#!/usr/bin/env python3
# Smoke playtest of the Godot project with REAL input (CLAUDE.md §4): the game runs in a real X11
# window on Xvfb (Mesa software Vulkan, the Mobile renderer), and this bot presses keys and drags and
# taps the mouse through xdotool, which uses XTEST, so the X server delivers them like a physical
# keyboard and mouse. Mouse presses reach the game as emulated touches
# (input_devices/pointing/emulate_touch_from_mouse). The game only REPORTS its state (debug builds,
# core/debug_bridge.gd, --bot-state); nothing here calls game functions.
#
#   python3 -I tools/godot/smoke_bot.py --out DIR [--size 1280x720] [--mode keys|touch] [--display :93]
#                                       [--binary exported_debug_build]
#
# keys mode (desktop): arrows walk her across the terraces and up both staircases (a cliff must stop
#   her), 1 takes 重 from the stone lantern, Shift+1 gives it to the old back-frame, E opens the
#   signpost's dialogue and E advances it to the end.
# touch mode (phone landscape, touch UI on): the floating stick walks her the same way, a tap on the
#   lantern targets it, a tap on the 重 key takes, a swipe up on it gives, the context key opens the
#   dialogue and taps advance it; then a long press in the one-key scheme gives her own weight away
#   and the bot waits for it to come back by itself.
# Writes DIR/<mode>-<size>/: screenshots (X screen captures; plus engine captures through
# --bot-cmd), log.txt, steps.json; exit code 1 when any check failed.
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GODOT = os.environ.get("GODOT_BIN", "/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64")


class Fail(Exception):
    pass


class Bot:
    def __init__(self, out, size, mode, display, binary=None):
        self.binary = binary
        self.out = out
        self.w, self.h = (int(v) for v in size.split("x"))
        self.mode = mode
        self.display = display
        self.env = dict(os.environ, DISPLAY=display)
        self.state_path = os.path.join(out, "state.json")
        self.cmd_path = os.path.join(out, "cmd.json")
        self.steps = []
        self.cmd_id = 0
        self.procs = []
        self.held = set()
        self.t0 = time.time()

    # ---------------------------------------------------------------- process

    def start(self):
        os.makedirs(self.out, exist_ok=True)
        for p in (self.state_path, self.cmd_path):
            if os.path.exists(p):
                os.remove(p)
        import shutil
        shutil.rmtree(os.path.join(self.out, "userdata"), ignore_errors=True)  # every run starts clean
        xvfb = subprocess.Popen(["Xvfb", self.display, "-screen", "0", "%dx%dx24" % (self.w, self.h), "-nolisten", "tcp"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.procs.append(xvfb)
        for _ in range(50):
            if subprocess.run(["xdpyinfo"], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(0.1)
        head = [self.binary] if self.binary else [GODOT, "--path", os.path.join(ROOT, "godot")]
        args = head + ["--rendering-method", os.environ.get("METHOD", "forward_plus"), "--rendering-driver", "vulkan",
                "--resolution", "%dx%d" % (self.w, self.h), "--position", "0,0", "--",
                "--bot-state=" + self.state_path, "--bot-cmd=" + self.cmd_path, "--bot-log",
                "--save-root=" + os.path.join(self.out, "userdata"),
                "--scheme=explicit", "--body=draft", "--font=pixel", "--touch-ui=" + ("on" if self.mode == "touch" else "off")]
        self.log = open(os.path.join(self.out, "log.txt"), "w")
        self.game = subprocess.Popen(args, env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        self.procs.append(self.game)
        self.wait_for(lambda s: s.get("ready"), 60, "the game is up and reporting")
        # focus its window (no window manager on Xvfb)
        wid = subprocess.run(["xdotool", "search", "--sync", "--onlyvisible", "--pid", str(self.game.pid)], env=self.env,
                             capture_output=True, text=True, timeout=20).stdout.split()
        if wid:
            subprocess.run(["xdotool", "windowfocus", "--sync", wid[0]], env=self.env, timeout=10)
        time.sleep(1.0)

    def stop(self):
        for k in list(self.held):
            self.keyup(k)
        try:
            self.command({"cmd": "quit"}, wait=False)
            self.game.wait(timeout=10)
        except Exception:
            pass
        for p in reversed(self.procs):
            if p.poll() is None:
                p.kill()
        self.log.close()

    # ---------------------------------------------------------------- state and checks

    def state(self):
        for _ in range(50):
            try:
                with open(self.state_path) as f:
                    return json.load(f)
            except (OSError, ValueError):
                time.sleep(0.02)
        raise Fail("no state file")

    def wait_for(self, pred, timeout, what):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = self.state()
                if pred(last):
                    return last
            except Fail:
                pass
            if self.game.poll() is not None:
                raise Fail("the game exited while waiting for: " + what)
            time.sleep(0.05)
        raise Fail("timed out waiting for: %s (last player %s)" % (what, (last or {}).get("player", {}).get("x")))

    def check(self, name, ok, detail=""):
        self.steps.append({"t": round(time.time() - self.t0, 1), "check": name, "ok": bool(ok), "detail": detail})
        print(("  ok   " if ok else "  FAIL ") + name + (("  (" + detail + ")") if detail else ""), flush=True)
        if not ok:
            raise Fail(name + ": " + detail)

    def note(self, text):
        self.steps.append({"t": round(time.time() - self.t0, 1), "note": text})
        print("  ..   " + text, flush=True)

    # ---------------------------------------------------------------- real input

    def xdo(self, *args):
        subprocess.run(["xdotool", *args], env=self.env, timeout=10)

    def keydown(self, k):
        self.xdo("keydown", k)
        self.held.add(k)

    def keyup(self, k):
        self.xdo("keyup", k)
        self.held.discard(k)

    def tap_key(self, k, hold=0.06):
        self.keydown(k)
        time.sleep(hold)
        self.keyup(k)

    def mouse(self, *args):
        self.xdo(*args)

    def tap(self, x, y, hold=0.08):
        self.mouse("mousemove", str(int(x)), str(int(y)))
        time.sleep(0.03)
        self.mouse("mousedown", "1")
        time.sleep(hold)
        self.mouse("mouseup", "1")

    def command(self, c, wait=True):
        self.cmd_id += 1
        c = dict(c, id=self.cmd_id)
        with open(self.cmd_path + ".tmp", "w") as f:
            json.dump(c, f)
        os.replace(self.cmd_path + ".tmp", self.cmd_path)
        if wait:
            self.wait_for(lambda s: s.get("cmd_ack", -1) >= self.cmd_id, 20, "command %s" % c["cmd"])

    def shot(self, name):
        path = os.path.join(self.out, name + ".png")
        subprocess.run(["import", "-window", "root", path], env=self.env, timeout=20)
        self.note("screenshot " + os.path.basename(path))

    def engine_shot(self, name):
        path = os.path.join(self.out, name + ".engine.png")
        self.command({"cmd": "shot", "path": path})
        self.note("engine capture " + os.path.basename(path))

    # ---------------------------------------------------------------- walking

    def walk_to(self, x, z, tol=0.2, timeout=20.0):
        """Closed loop on her reported position: hold arrow keys, or drag the touch stick."""
        if self.mode == "touch":
            return self.stick_to(x, z, tol, timeout)
        end = time.time() + timeout
        while time.time() < end:
            p = self.state()["player"]
            dx, dz = x - p["x"], z - p["z"]
            if abs(dx) <= tol and abs(dz) <= tol:
                break
            want = set()
            if abs(dx) > tol:
                want.add("Right" if dx > 0 else "Left")
            if abs(dz) > tol:
                want.add("Down" if dz > 0 else "Up")
            near = max(abs(dx), abs(dz)) < 0.7
            for k in self.held - want:
                self.keyup(k)
            for k in want - self.held:
                self.keydown(k)
            if near:  # short pulses near the goal, so she does not overshoot
                time.sleep(0.05)
                for k in list(self.held):
                    self.keyup(k)
                time.sleep(0.08)
            else:
                time.sleep(0.03)
        for k in list(self.held):
            self.keyup(k)
        time.sleep(0.15)
        return self.state()["player"]

    def stick_to(self, x, z, tol, timeout):
        s = self.state()
        scale = s["scale"]
        bx, by = int(self.w * 0.22), int(self.h * 0.62)  # a thumb on the left half
        r = 30 * scale
        self.mouse("mousemove", str(bx), str(by))
        time.sleep(0.03)
        self.mouse("mousedown", "1")
        time.sleep(0.05)
        end = time.time() + timeout
        saw_stick = False
        while time.time() < end:
            s = self.state()
            p = s["player"]
            saw_stick = saw_stick or s.get("stick", False)
            dx, dz = x - p["x"], z - p["z"]
            d = (dx * dx + dz * dz) ** 0.5
            if d <= tol:
                break
            k = 1.0 if d > 0.8 else max(0.35, d / 0.8)  # ease in near the goal
            self.mouse("mousemove", str(int(bx + dx / d * r * k)), str(int(by + dz / d * r * k)))
            time.sleep(0.04)
        self.mouse("mousemove", str(bx), str(by))
        time.sleep(0.05)
        self.mouse("mouseup", "1")
        time.sleep(0.2)
        if not saw_stick:
            raise Fail("the touch stick never appeared")
        return self.state()["player"]

    def push(self, direction, seconds):
        """Hold one direction for a while (to show that something blocks her)."""
        if self.mode == "touch":
            s = self.state()
            bx, by = int(self.w * 0.22), int(self.h * 0.62)
            r = 30 * s["scale"]
            v = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}[direction]
            self.mouse("mousemove", str(bx), str(by))
            self.mouse("mousedown", "1")
            time.sleep(0.05)
            self.mouse("mousemove", str(bx + v[0] * r), str(by + v[1] * r))
            time.sleep(seconds)
            self.mouse("mouseup", "1")
        else:
            self.keydown(direction)
            time.sleep(seconds)
            self.keyup(direction)
        time.sleep(0.15)
        return self.state()["player"]

    def face(self, direction):
        """Turn toward a direction with a very short nudge."""
        if self.mode == "touch":
            self.push(direction, 0.09)
        else:
            self.tap_key(direction, 0.05)
        time.sleep(0.2)

    def entity(self, s, eid):
        for e in s["entities"]:
            if e["id"] == eid:
                return e
        raise Fail("no entity " + eid)

    # ---------------------------------------------------------------- the run

    def run(self):
        s = self.state()
        self.note("window %s logical %s scale %s margin %s" % (s["window"], s["logical"], s["scale"], s["margin"]))
        self.check("window filled at an integer scale, no bars",
                   0 <= s["window"][0] - s["logical"][0] * s["scale"] < s["scale"] and 0 <= s["window"][1] - s["logical"][1] * s["scale"] < s["scale"],
                   "logical %s x %d vs window %s" % (s["logical"], s["scale"], s["window"]))
        totals0 = s["ledger"]["totals"]
        self.check("things stand on their terrace (the lantern on the 1.5 m plateau)", abs(self.entity(s, "lantern")["h"] - 1.5) < 1e-3,
                   "h %.2f" % self.entity(s, "lantern")["h"])
        self.shot("01-start")

        # --- terraces and stairs
        p = self.walk_to(10.25, 15.0)
        self.check("walked north on the lowest level", abs(p["z"] - 15.0) < 0.4 and abs(p["h"]) < 1e-3, "z %.2f h %.2f" % (p["z"], p["h"]))
        p = self.walk_to(10.25, 12.2)
        self.check("first staircase carries her up 0.5 m", abs(p["h"] - 0.5) < 1e-3, "z %.2f h %.2f" % (p["z"], p["h"]))
        self.shot("02-terrace")
        p = self.walk_to(4.0, 9.0)
        p = self.push("Up", 1.2)
        self.check("the 1.0 m cliff stops her", p["z"] >= 8.0 and abs(p["h"] - 0.5) < 1e-3, "z %.2f h %.2f" % (p["z"], p["h"]))
        p = self.walk_to(10.25, 9.0)
        p = self.walk_to(10.25, 5.2)
        self.check("second staircase carries her up to the plateau (1.5 m)", abs(p["h"] - 1.5) < 1e-3, "z %.2f h %.2f" % (p["z"], p["h"]))
        self.shot("03-plateau")

        # --- target the stone lantern and take its weight
        p = self.walk_to(7.45, 3.0)
        lantern = self.entity(self.state(), "lantern")
        if self.mode == "touch":
            sx, sy = lantern["screen"]
            self.tap(sx, sy)
            s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "lantern", 3, "a tap on the lantern targets it")
        else:
            self.face("Left")
            s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "lantern", 3, "facing the lantern targets it")
        self.check("targeted the stone lantern", s["target"]["id"] == "lantern")
        s = self.wait_for(lambda s: abs(s["actors"]["saji"]["h"] - 1.5) < 1e-3, 6, "Saji follows her onto the plateau")
        self.check("Saji followed her up both staircases", True, "saji at %s" % s["actors"]["saji"])
        self.check("the key says what a press does now: take", s["hud"]["plans"].get("w", {}).get("verb") == "take"
                   and s["hud"]["plans"]["w"]["reason"] == "", str(s["hud"]["plans"].get("w")))
        self.shot("04-target")
        w0 = s["player"]["q"]["w"]
        lw0 = self.entity(s, "lantern")["q"]["w"]
        if self.mode == "touch":
            k = s["keys"]["q_w"]
            self.check("the 重 key is on screen and live", k["visible"], str(k))
            x, y, kw, kh = k["rect"]
            self.tap(x + kw / 2, y + kh / 2)
        else:
            self.tap_key("1")
        s = self.wait_for(lambda s: s["player"]["q"]["w"] == w0 + 1, 3, "her weight goes up")
        self.check("take: 重 moved from the lantern to her", self.entity(s, "lantern")["q"]["w"] == lw0 - 1,
                   "her w %d lantern w %d" % (s["player"]["q"]["w"], self.entity(s, "lantern")["q"]["w"]))
        self.check("her body changed: extra weight (level 2), slower", s["player"]["levels"]["w"] == 2 and s["player"]["speed"] < 3.0,
                   "speed %.2f" % s["player"]["speed"])
        self.check("the take made a sound", "take" in s["sounds"], str(s["sounds"][-4:]))
        time.sleep(0.25)
        self.shot("05-heavy")
        if self.mode != "touch":
            self.tap_key("1")
            s = self.wait_for(lambda s: any(e.get("type") == "refused" for e in s["events"][-3:]), 2, "a refusal")
            ev = [e for e in s["events"] if e.get("type") == "refused"][-1]
            self.check("a second unit is refused at capacity 1, with its reason", ev.get("reason") == "overload"
                       and s["player"]["q"]["w"] == w0 + 1, str(ev))

        # --- down to the old back-frame and give the weight to it
        p = self.walk_to(10.25, 5.2)
        p = self.walk_to(10.25, 11.3)
        self.check("back down on the middle terrace", abs(p["h"] - 0.5) < 1e-3, "h %.2f" % p["h"])
        p = self.walk_to(14.15, 11.3)
        frame = self.entity(self.state(), "frame")
        if self.mode == "touch":
            sx, sy = frame["screen"]
            self.tap(sx, sy)
        else:
            self.face("Right")
        s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "frame", 3, "the old frame is targeted")
        fw0 = self.entity(s, "frame")["q"]["w"]
        far0 = self.entity(s, "frame")["far"]
        if self.mode == "touch":
            x, y, kw, kh = s["keys"]["q_w"]["rect"]
            cx, cy = x + kw / 2, y + kh / 2
            self.mouse("mousemove", str(int(cx)), str(int(cy)))
            self.mouse("mousedown", "1")
            time.sleep(0.06)
            for dy in (10, 20, 30, 40):
                self.mouse("mousemove", str(int(cx)), str(int(cy - dy * s["scale"] / 2)))
                time.sleep(0.03)
            time.sleep(0.05)
            self.mouse("mouseup", "1")
        else:
            self.xdo("keydown", "shift")
            time.sleep(0.05)
            self.tap_key("1")
            self.xdo("keyup", "shift")
        s = self.wait_for(lambda s: self.entity(s, "frame")["q"]["w"] == fw0 + 1, 3, "the frame gains weight")
        self.check("give: 重 moved from her to the frame", s["player"]["q"]["w"] == w0,
                   "her w %d frame w %d" % (s["player"]["q"]["w"], self.entity(s, "frame")["q"]["w"]))
        self.check("the frame came nearer (遠化 eases)", self.entity(s, "frame")["far"] < far0,
                   "far %.2f -> %.2f" % (far0, self.entity(s, "frame")["far"]))
        self.check("the books balance after take and give", s["ledger"]["totals"] == totals0, str(s["ledger"]["totals"]))
        self.shot("06-gave")

        # --- the signpost's dialogue
        p = self.walk_to(10.25, 11.3)
        p = self.walk_to(10.25, 15.5)
        self.check("down the first staircase again", abs(p["h"]) < 1e-3, "h %.2f" % p["h"])
        p = self.walk_to(11.45, 21.0)
        if self.mode == "touch":
            self.tap(*self.entity(self.state(), "sign")["screen"])
        else:
            self.face("Right")
        s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "sign", 3, "the signpost is targeted")
        if self.mode == "touch":
            x, y, kw, kh = s["keys"]["ctx"]["rect"]
            self.tap(x + kw / 2, y + kh / 2)
        else:
            self.tap_key("e")
        s = self.wait_for(lambda s: s["dialogue"].get("open"), 3, "the dialogue opens")
        self.check("dialogue open, control taken from her", not s["player"]["control"])
        time.sleep(2.2)
        s = self.state()
        d = s["dialogue"]
        self.check("the narration line has no portrait and uses the full width", d["card"][2] == 0, str(d.get("card")))
        self.shot("07-dialogue-narration")
        self.engine_shot("07-dialogue-narration")
        self.advance(s)
        s = self.wait_for(lambda s: not s["dialogue"].get("open"), 6, "the dialogue closes")
        s = self.wait_for(lambda s: s["player"]["control"], 2, "control returns after the scene")
        self.check("dialogue closed, control back", s["player"]["control"])

        # --- Saji's dialogue: portraits beside the text, never over it
        sj = self.entity(s, "saji")
        p = self.walk_to(sj["x"] - 0.9, sj["z"] + 0.1, tol=0.3)
        s = self.state()
        sj = self.entity(s, "saji")
        if self.mode == "touch":
            self.tap(*sj["screen"])
        else:
            self.face("Right" if sj["x"] > s["player"]["x"] else "Left")
        s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "saji", 4, "Saji is targeted")
        if self.mode == "touch":
            x, y, kw, kh = s["keys"]["ctx"]["rect"]
            self.tap(x + kw / 2, y + kh / 2)
        else:
            self.tap_key("e")
        s = self.wait_for(lambda s: s["dialogue"].get("open"), 3, "Saji's dialogue opens")
        lines = s["dialogue"]["count"]
        for i in range(lines):
            s = self.wait_for(lambda s: s["dialogue"].get("open") and s["dialogue"]["index"] == i, 4, "line %d" % (i + 1))
            d = s["dialogue"]
            card, text = d["card_win"], d["text_rect_win"]
            self.check("line %d: the portrait card ends left of the text column" % (i + 1),
                       card[2] > 0 and card[0] + card[2] <= text[0], "card %s text %s" % (card, text))
            time.sleep(1.0)
            if i == 1:
                self.shot("08-dialogue-portrait")
            s = self.state()
            idx = s["dialogue"]["index"]
            self.advance(s)
            if i < lines - 1:
                self.wait_for(lambda s: not s["dialogue"].get("open") or s["dialogue"]["index"] > idx, 4, "advance past line %d" % (i + 1))
        s = self.wait_for(lambda s: not s["dialogue"].get("open"), 6, "Saji's dialogue closes")
        s = self.wait_for(lambda s: s["player"]["control"], 2, "control returns after the scene")
        self.check("all %d lines read, control back" % lines, s["player"]["control"])

        if self.mode == "touch":
            self.one_key_long_press()
        else:
            self.cinema_check()
            self.vector_font()
        self.shot("10-end")
        s = self.state()
        self.note("fps %s" % s["fps"])

    def cinema_check(self):
        """F10 (debug builds): the director's verbs in one scene. The fade must stay under the words."""
        self.tap_key("F10")
        s = self.wait_for(lambda s: s["dialogue"].get("fade", 0) >= 0.99 and s["dialogue"]["labels"].get("card", {}).get("alpha", 0) >= 0.99,
                          15, "the caption card over a black fade")
        self.shot("11-fade-card")
        self.note("actors during the scene: %s" % s["actors"])
        img = self.pixels("11-fade-card")
        x, y, w, h = [v * s["scale"] for v in s["dialogue"]["labels"]["card"]["rect"]]
        bright = sum(1 for yy in range(int(y), int(y + h)) for xx in range(int(x), int(x + w)) if max(img.getpixel((xx, yy))[:3]) > 200)
        self.check("the card's words are drawn over the black fade", bright > 40, "%d bright pixels in the card" % bright)
        from PIL import ImageStat
        corner = img.crop((0, int(self.h * 0.3), int(self.w * 0.25), int(self.h * 0.6))).convert("L")
        mean = ImageStat.Stat(corner).mean[0]
        self.check("the fade covers the world", mean < 6, "mean %.1f" % mean)
        s = self.wait_for(lambda s: s["dialogue"]["labels"].get("title", {}).get("alpha", 0) >= 0.99, 12, "the title drop over white")
        self.shot("12-title")
        s = self.wait_for(lambda s: s["player"]["control"] and not s["dialogue"]["blocking"], 20, "the scene ends")
        states = {k: v["state"] for k, v in s["actors"].items()}
        self.check("after the scene every actor is back in locomotion", set(states.values()) == {"locomotion"}, str(states))

    def vector_font(self):
        """F7 (debug builds): the vector font theme, in Saji's dialogue."""
        self.tap_key("F7")
        s = self.wait_for(lambda s: s["settings"]["font"] == "vector", 3, "font theme vector")
        sj = self.entity(s, "saji")
        self.face("Right" if sj["x"] > s["player"]["x"] else "Left")
        s = self.wait_for(lambda s: (s["target"] or {}).get("id") == "saji", 4, "Saji is targeted")
        self.tap_key("e")
        s = self.wait_for(lambda s: s["dialogue"].get("open") and s["dialogue"]["index"] == 0, 3, "dialogue (vector font)")
        time.sleep(2.6)
        self.shot("13-vector-font")
        self.advance(s)
        self.advance(self.state())
        self.advance(self.state())
        s = self.wait_for(lambda s: not s["dialogue"].get("open") and s["player"]["control"], 6, "closed")
        self.tap_key("F7")
        self.wait_for(lambda s: s["settings"]["font"] == "pixel", 3, "back to the pixel font")

    def pixels(self, name):
        from PIL import Image
        return Image.open(os.path.join(self.out, name + ".png")).convert("RGB")

    def advance(self, s):
        """Advance the open dialogue to its end, with the real input of the mode."""
        while True:
            s = self.state()
            if not s["dialogue"].get("open"):
                return
            idx, done = s["dialogue"]["index"], s["dialogue"]["done"]
            if self.mode == "touch":
                self.tap(self.w * 0.5, self.h * 0.4)
            else:
                self.tap_key("e")
            try:
                self.wait_for(lambda t: not t["dialogue"].get("open") or t["dialogue"]["index"] != idx or t["dialogue"]["done"] != done,
                              2, "the line reacts")
            except Fail:
                pass
            s = self.state()
            if not s["dialogue"].get("open") or s["dialogue"]["index"] != idx:
                return

    def one_key_long_press(self):
        """The one-key scheme (pending): a long press on 重 gives her own weight to the target or the
        air; it returns by itself after about 9 s."""
        self.tap_key("F6")  # debug builds: control scheme -> obvious
        s = self.wait_for(lambda s: s["settings"]["scheme"] == "obvious", 3, "scheme switched to obvious")
        w0 = s["player"]["q"]["w"]
        x, y, kw, kh = s["keys"]["q_w"]["rect"]
        self.mouse("mousemove", str(int(x + kw / 2)), str(int(y + kh / 2)))
        self.mouse("mousedown", "1")
        time.sleep(0.6)
        s = self.state()
        self.check("long press previews the reverse action on the key", s["hud"]["plans"]["w"]["gesture"] == "alt", str(s["hud"]["plans"]["w"]))
        self.mouse("mouseup", "1")
        s = self.wait_for(lambda s: s["player"]["q"]["w"] == w0 - 1, 3, "her own weight leaves")
        self.check("long press gave her own share: light, hovering", s["player"]["levels"]["w"] == 0 and s["player"]["look"]["hover_m"] > 0.2,
                   "levels %s hover %.2f" % (s["player"]["levels"], s["player"]["look"]["hover_m"]))
        time.sleep(0.3)
        self.shot("09-light")
        t = time.time()
        s = self.wait_for(lambda s: s["player"]["q"]["w"] == w0, 14, "her weight comes back by itself")
        self.check("her own share came back by itself", True, "after %.1f s" % (time.time() - t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--mode", default="keys", choices=["keys", "touch"])
    ap.add_argument("--display", default=":93")
    ap.add_argument("--binary", default=None, help="an exported DEBUG build to run instead of the project")
    a = ap.parse_args()
    out = os.path.join(os.path.abspath(a.out), "%s-%s%s" % (a.mode, a.size, "-export" if a.binary else ""))
    bot = Bot(out, a.size, a.mode, a.display, os.path.abspath(a.binary) if a.binary else None)
    ok = True
    print("smoke playtest: %s at %s -> %s" % (a.mode, a.size, out), flush=True)
    try:
        bot.start()
        bot.run()
    except Fail as e:
        ok = False
        print("  FAILED: %s" % e, flush=True)
        try:
            bot.shot("zz-failure")
        except Exception:
            pass
    finally:
        bot.stop()
        with open(os.path.join(out, "steps.json"), "w") as f:
            json.dump({"ok": ok, "mode": a.mode, "size": a.size, "steps": bot.steps}, f, ensure_ascii=False, indent=1)
    print("RESULT %s %s %s" % ("PASS" if ok else "FAIL", a.mode, a.size), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
