#!/usr/bin/env python3
# Real-input check of the delivered art sample (godot/showcase, G5R3-0; CLAUDE.md §4): the exported
# build runs in a real X11 window on Xvfb (Mesa software Vulkan), and this script presses keys
# through xdotool, which uses XTEST, so the X server delivers them like a physical keyboard. Nothing
# here calls game functions; it only presses keys, waits and takes X screenshots, which a person
# then looks at. Gamepad input cannot be checked this way.
#
#   python3 -I tools/godot/showcase_check.py --binary <tengan.x86_64 | tengan.exe> --out DIR
#                                            [--display :94] [--plan full|smoke]
# full  (Linux export): menu; home area (walk, time of day, rain, time flow, hints); lookout (walk onto
#       the rock, the far view, turning the head); the prologue vista (plays, holds, replays);
#       portraits (expressions, characters, the staged demo dialogue); reduced motion; fullscreen
#       toggle; quit from the menu.
# smoke (Windows export under wine): menu, home area, a walk, back to the menu, quit.
# Writes DIR/NN_name.png (X screen), DIR/log.txt (engine output), DIR/steps.txt; exit code 1 when
# the engine died, printed a script error, or a step that must change the screen did not.
import argparse
import os
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageStat

WINE = "/usr/lib/wine/wine64"
WINE_ENV = {"WINEPREFIX": "/home/user/godotengine/wine-prefix", "WINEDEBUG": "-all",
            # dinput8 off: wine 9.0 crashes in Godot's joypad init (knowledge/10 §5.2)
            "WINEDLLOVERRIDES": "mscoree,mshtml=;dinput8=d;winedbg.exe=d"}


class Check:
    def __init__(self, a):
        self.a = a
        self.out = os.path.abspath(a.out)
        os.makedirs(self.out, exist_ok=True)
        self.env = dict(os.environ, DISPLAY=a.display)
        self.n = 0
        self.steps = []
        self.failed = []
        self.last = None
        self.menu_pos = 0

    # ------------------------------------------------------------------ process

    def start(self):
        self.xvfb = subprocess.Popen(["Xvfb", self.a.display, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if subprocess.run(["xdpyinfo"], env=self.env, capture_output=True).returncode == 0:
                break
            time.sleep(0.1)
        cmd = [self.a.binary]
        env = dict(self.env)
        if self.a.binary.endswith(".exe"):
            cmd = [WINE, self.a.binary]
            env.update(WINE_ENV)
        self.log = open(os.path.join(self.out, "log.txt"), "w")
        self.t0 = time.time()
        self.game = subprocess.Popen(cmd, env=env, stdout=self.log, stderr=subprocess.STDOUT,
                                     cwd=os.path.dirname(os.path.abspath(self.a.binary)))
        self.note("start %s" % " ".join(cmd))

    def stop(self):
        if self.game.poll() is None:
            self.game.terminate()
            try:
                self.game.wait(5)
            except subprocess.TimeoutExpired:
                self.game.kill()
        if self.a.binary.endswith(".exe"):
            subprocess.run(["/usr/lib/wine/wineserver64", "-k"], env=dict(self.env, **WINE_ENV), capture_output=True)
        self.xvfb.terminate()
        self.log.close()

    def alive(self):
        return self.game.poll() is None

    # ------------------------------------------------------------------ input and capture

    def note(self, text):
        line = "%7.1f s  %s" % (time.time() - self.t0 if hasattr(self, "t0") else 0.0, text)
        self.steps.append(line)
        print(line, flush=True)

    def focus(self):
        r = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(self.game.pid)],
                           env=self.env, capture_output=True, text=True)
        wid = r.stdout.split()[-1] if r.stdout.split() else None
        if wid is None:      # wine windows belong to another process; take the newest visible window
            r = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "."], env=self.env,
                               capture_output=True, text=True)
            wid = r.stdout.split()[-1] if r.stdout.split() else None
        if wid:
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], env=self.env, capture_output=True)
            subprocess.run(["xdotool", "windowfocus", wid], env=self.env, capture_output=True)
        return wid

    def key(self, *keys):
        for k in keys:
            subprocess.run(["xdotool", "key", "--delay", "90", k], env=self.env)
            time.sleep(0.25)
        self.note("key " + " ".join(keys))

    def hold(self, k, secs):
        subprocess.run(["xdotool", "keydown", k], env=self.env)
        time.sleep(secs)
        subprocess.run(["xdotool", "keyup", k], env=self.env)
        self.note("hold %s %.1f s" % (k, secs))

    def grab(self):
        path = os.path.join(self.out, "_grab.png")
        subprocess.run(["import", "-window", "root", path], env=self.env, capture_output=True)
        return Image.open(path).convert("RGB")

    def shot(self, name, must_change=False):
        img = self.grab()
        self.n += 1
        path = os.path.join(self.out, "%02d_%s.png" % (self.n, name))
        img.save(path)
        mean = sum(ImageStat.Stat(img).mean) / 3
        diff = None
        if self.last is not None:
            d = ImageChops.difference(img, self.last).convert("L")
            diff = sum(1 for v in d.getdata() if v > 12) / (img.width * img.height)
        self.note("shot %s  mean %.1f  changed %s" % (os.path.basename(path), mean,
                                                       "-" if diff is None else "%.1f%%" % (diff * 100)))
        if must_change and diff is not None and diff < 0.002:
            self.failed.append("%s: the screen did not change" % name)
        self.last = img
        return img

    def wait_loaded(self, name, min_mean=18.0, timeout=180.0, settle=4.0):
        """waits until the screen is past the dark veil and stops changing much, then shoots"""
        t = time.time()
        prev = None
        while time.time() - t < timeout:
            if not self.alive():
                self.failed.append("%s: the engine exited" % name)
                return None
            img = self.grab()
            mean = sum(ImageStat.Stat(img).mean) / 3
            if mean >= min_mean and prev is not None:
                d = ImageChops.difference(img, prev).convert("L")
                if sum(1 for v in d.resize((480, 270)).getdata() if v > 40) / (480 * 270) < 0.05:
                    break
            prev = img
            time.sleep(2.0)
        else:
            self.failed.append("%s: not loaded after %d s" % (name, timeout))
        time.sleep(settle)
        self.note("loaded %s after %.0f s" % (name, time.time() - t))
        return self.shot(name)

    # ------------------------------------------------------------------ plans

    MENU = 7            # 家一带 眺望岩 序章·树顶远景 立绘 减少晃动 全屏 退出; the cursor wraps

    def menu_to(self, index):
        """moves the menu cursor to an item and presses Enter. The menu reopens on the item last
        chosen, so the cursor is tracked here (self.menu_pos)."""
        steps = (index - self.menu_pos) % self.MENU
        if steps:
            self.key(*(["Down"] * steps))
        self.menu_pos = index
        self.key("Return")

    def plan_smoke(self):
        self.wait_loaded("menu", timeout=240)
        self.focus()
        self.menu_to(0)
        self.wait_loaded("home", timeout=300)
        self.hold("d", 2.0)
        self.shot("home_walked_right", must_change=True)
        self.key("4")
        time.sleep(3)
        self.shot("home_night", must_change=True)
        self.key("Escape")
        self.wait_loaded("menu_again", timeout=120)
        self.menu_to(6)          # 退出
        time.sleep(8)
        self.note("engine running after 退出: %s" % self.alive())
        if self.alive():
            self.failed.append("退出 did not quit")

    def plan_full(self):
        self.wait_loaded("menu", timeout=240)
        self.focus()
        # home area
        self.menu_to(0)
        self.wait_loaded("home", timeout=300)
        for k, secs in (("d", 1.6), ("s", 1.4), ("a", 1.6), ("w", 1.4)):
            self.hold(k, secs)
            self.shot("home_walk_" + k, must_change=True)
        for k, name in (("1", "dawn"), ("2", "noon"), ("3", "dusk"), ("4", "night")):
            self.key(k)
            time.sleep(3)
            self.shot("home_" + name, must_change=True)
        self.key("2")
        time.sleep(2)
        self.hold("e", 2.5)
        self.shot("home_time_forward", must_change=True)
        self.hold("q", 2.5)
        self.shot("home_time_back", must_change=True)
        self.key("r")
        time.sleep(5)
        self.shot("home_rain", must_change=True)
        self.key("r")
        time.sleep(4)
        self.key("t")
        time.sleep(6)
        self.shot("home_time_flows")
        self.key("t")
        self.key("h")
        time.sleep(1)
        self.shot("home_hints_hidden", must_change=True)
        self.key("h")
        self.key("Escape")
        self.wait_loaded("menu_from_home", timeout=120)
        # lookout
        self.menu_to(1)
        self.wait_loaded("lookout", timeout=300)
        self.hold("s", 1.6)      # the start is about 4.3 m north of the rock (showcase.gd _lookout_start)
        self.shot("lookout_walked")
        time.sleep(6)
        self.shot("lookout_far_view")
        self.hold("a", 1.2)
        self.shot("lookout_head_left", must_change=True)
        self.hold("d", 2.4)
        self.shot("lookout_head_right", must_change=True)
        self.hold("w", 1.5)
        time.sleep(3)
        self.shot("lookout_back", must_change=True)
        self.key("Escape")
        self.wait_loaded("menu_from_lookout", timeout=120)
        # prologue vista
        self.menu_to(2)
        time.sleep(8)
        self.shot("vista_08s")
        time.sleep(20)
        self.shot("vista_28s", must_change=True)
        time.sleep(30)
        self.shot("vista_58s", must_change=True)
        time.sleep(40)
        self.shot("vista_98s")
        self.key("Return")
        time.sleep(6)
        self.shot("vista_replayed", must_change=True)
        self.key("Escape")
        self.wait_loaded("menu_from_vista", timeout=120)
        # portraits and the staged demo dialogue
        self.menu_to(3)
        time.sleep(4)
        self.shot("gallery")
        self.key("Down")
        time.sleep(1)
        self.shot("gallery_next_face", must_change=True)
        self.key("Right")
        time.sleep(1)
        self.shot("gallery_next_character", must_change=True)
        self.key("space")
        for i in range(8):
            time.sleep(2.5)
            self.shot("dialogue_%d" % i)
            self.key("space")
        self.key("Escape")
        time.sleep(2)
        self.key("Escape")
        self.wait_loaded("menu_from_gallery", timeout=60)
        # reduced motion: toggle, then the same dialogue
        self.menu_to(4)
        time.sleep(1)
        self.shot("menu_reduce_motion_on", must_change=True)
        self.menu_to(3)
        time.sleep(4)
        self.key("Right")
        self.key("space")
        for i in range(4):
            time.sleep(2.5)
            self.shot("dialogue_reduced_%d" % i)
            self.key("space")
        self.key("Escape")
        time.sleep(2)
        self.key("Escape")
        self.wait_loaded("menu_back", timeout=60)
        # fullscreen toggle (F11), then quit through 退出
        self.key("F11")
        time.sleep(3)
        self.shot("windowed", must_change=True)
        self.key("F11")
        time.sleep(3)
        self.shot("fullscreen_again", must_change=True)
        self.focus()
        self.menu_to(6)          # 退出
        time.sleep(8)
        self.note("engine running after 退出: %s" % self.alive())
        if self.alive():
            self.failed.append("退出 did not quit")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--binary", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--display", default=":94")
    p.add_argument("--plan", default="full", choices=["full", "smoke"])
    a = p.parse_args()
    c = Check(a)
    c.start()
    try:
        getattr(c, "plan_" + a.plan)()
    finally:
        c.stop()
    log = open(os.path.join(c.out, "log.txt"), encoding="utf-8", errors="replace").read()
    errors = [ln for ln in log.splitlines() if "SCRIPT ERROR" in ln or "Parse Error" in ln or "SHADER ERROR" in ln]
    if errors:
        c.failed.append("%d script or shader errors in the log (first: %s)" % (len(errors), errors[0][:160]))
    open(os.path.join(c.out, "steps.txt"), "w").write("\n".join(c.steps + ["", "FAILED:"] + c.failed) + "\n")
    print("\n".join(["FAILED: " + f for f in c.failed]) or "all steps passed")
    sys.exit(1 if c.failed else 0)


if __name__ == "__main__":
    main()
