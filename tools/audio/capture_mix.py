#!/usr/bin/env python3
"""Records what the game really sounds like (decision 7, category 4) for tools/audio/check_mix.py.

  python3 -I tools/audio/capture_mix.py --project godot --out DIR --plan PLAN [--display :141]

Two ways, by what the plan has to prove:
  movie   the menu: the showcase in a real X11 window on Xvfb (Mesa software Vulkan) under Godot's Movie Maker
          (fixed 30 fps: picture and sound frame-exact), keys through xdotool (XTEST: the X server delivers them
          like a keyboard). For the time from a key to its sound. (The 3D sample renders at a few frames a second
          or less in software, too slow for long recordings this way.)
  record  the sample and the screens over minutes, in real time: the game records its own master bus
          (Audio: -- --audio-record=FILE --audio-record-secs=N) with the dummy audio driver. "headless" plans need
          no keys (the sample's own route driver walks her: it holds W/A/S/D for her exactly as keys would, through
          the same code); "xvfb" plans press real keys (xdotool) in a real window.
Plans:
  menu      movie: the title, three Downs and an Up (key to sound)
  home      record, headless: the home area at 9:30, her walk round the yard, the shrine and the camphor (--route=walk)
  brook     record, headless: standing by the brook at noon in a strong wind (the brook-and-wind check, G5R3-65 2.3)
  brook_rain  the same in heavy rain (rain 0.85; the rain makes it windier too): the weather's loudness
  vista     record, headless: the prologue's treetop vista, whole
  lookout   record, headless: she walks onto the lookout and looks out (--route=lookout)
  approach  record, headless: in through the east gate's fog to the hut (--route=approach; the barrier, 5c)
  gallery   record, xvfb: the portraits for 20 s, then the staged dialogue (Space presses): the ducking under it
Writes DIR/<plan>.wav, DIR/<plan>_plays.jsonl (every sound chosen), DIR/<plan>_keys.json, DIR/<plan>_log.txt.
"""
import argparse
import json
import os
import subprocess
import time

GODOT = os.environ.get("GODOT_BIN", "/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64")
FPS = 30

PLANS = {
    "menu": {"how": "movie", "args": ["--mode=menu"], "secs": 22,
             "keys": [(10.0, "Down"), (11.5, "Down"), (13.0, "Down"), (14.5, "Up")]},
    "home": {"how": "headless", "args": ["--mode=home", "--route=walk"], "secs": 90},
    "brook": {"how": "headless", "args": ["--mode=home", "--at=-9.0,-38.6", "--hours=12.5", "--audio-wind=0.9"], "secs": 70},
    "brook_rain": {"how": "headless", "args": ["--mode=home", "--at=-9.0,-38.6", "--rain=0.85", "--hours=12.5"], "secs": 70},
    "vista": {"how": "headless", "args": ["--mode=vista"], "secs": 85},
    "lookout": {"how": "headless", "args": ["--mode=lookout", "--route=lookout"], "secs": 70},
    "approach": {"how": "headless", "args": ["--mode=home", "--route=approach", "--hours=17.0"], "secs": 70},
    "gallery": {"how": "xvfb", "args": ["--mode=gallery"], "secs": 52,
                "keys": [(20.0, "space"), (24.0, "space"), (28.0, "space"), (32.0, "space"), (36.0, "space"),
                         (40.0, "space"), (44.0, "space")]},
}


class Run:
    def __init__(self, a):
        self.a = a
        self.out = os.path.abspath(a.out)
        os.makedirs(self.out, exist_ok=True)
        self.env = dict(os.environ, DISPLAY=a.display)
        self.events = []
        self._pos, self._count, self._tail = 0, 0, b""

    def xvfb(self):
        # -ardelay / -arinterval: no key auto-repeat to speak of (in the movie, the game runs far slower than the
        # clock, so a key held for two of its frames is held for most of a second)
        self.xv = subprocess.Popen(["Xvfb", self.a.display, "-screen", "0", "1280x720x24", "-nolisten", "tcp",
                                    "-ardelay", "30000", "-arinterval", "30000"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if subprocess.run(["xdpyinfo"], env=self.env, capture_output=True).returncode == 0:
                break
            time.sleep(0.1)

    def frame_now(self):
        # Movie Maker prints nothing per frame; the AVI grows by one audio chunk a frame: count the 01wb chunks
        # (read on from where the last count stopped, keeping 3 bytes for a tag split across two reads)
        try:
            with open(self.movie, "rb") as f:
                f.seek(self._pos)
                b = self._tail + f.read()
        except OSError:
            return self._count
        self._count += b.count(b"01wb")
        self._pos += len(b) - len(self._tail)
        self._tail = b[-3:] if len(b) >= 3 else b
        return self._count

    def window(self):
        r = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "Godot"], env=self.env, capture_output=True, text=True)
        ids = r.stdout.split()
        return ids[-1] if ids else None

    def key(self, k, movie):
        w = self.window()
        if w:
            subprocess.run(["xdotool", "windowactivate", "--sync", w], env=self.env, capture_output=True)
        subprocess.run(["xdotool", "keydown", k], env=self.env)
        if movie:
            f0 = self.frame_now()
            t0 = time.time()
            while self.frame_now() < f0 + 2 and time.time() - t0 < 60:
                time.sleep(0.02)
        else:
            time.sleep(0.08)
        subprocess.run(["xdotool", "keyup", k], env=self.env)

    def run(self, plan):
        P = dict(PLANS[plan])
        if self.a.secs > 0:
            P["secs"] = self.a.secs
        logp = os.path.join(self.out, plan + "_log.txt")
        log = open(logp, "w")
        plays = os.path.join(self.out, plan + "_plays.jsonl")
        wav = os.path.join(self.out, plan + ".wav")
        user = ["--windowed", "--audio-log=" + plays] + P["args"] + self.a.game_args.split()
        how = P["how"]
        if how == "movie":
            self.xvfb()
            self.movie = os.path.join(self.out, plan + ".avi")
            cmd = [GODOT, "--path", os.path.abspath(self.a.project), "--rendering-method", "forward_plus",
                   "--fixed-fps", str(FPS), "--write-movie", self.movie, "--quit-after", str(P["secs"] * FPS),
                   "res://showcase/showcase.tscn", "--"] + user
            game = subprocess.Popen(cmd, env=self.env, stdout=log, stderr=subprocess.STDOUT)
            for at, k in P.get("keys", []):
                while game.poll() is None and self.frame_now() < int(at * FPS):
                    time.sleep(0.1)
                if game.poll() is not None:
                    break
                f = self.frame_now()
                self.key(k, True)
                self.events.append({"frame": f, "time": round(f / FPS, 3), "key": k})
            game.wait()
            self.xv.terminate()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.movie, "-vn", "-acodec", "pcm_s16le", wav], check=True)
            os.remove(self.movie)
        else:
            user += ["--audio-record=" + wav, "--audio-record-secs=%g" % P["secs"]]
            head = ["--headless"] if how == "headless" else ["--rendering-method", "forward_plus"]
            if how == "xvfb":
                self.xvfb()
            cmd = [GODOT] + head + ["--path", os.path.abspath(self.a.project), "--max-fps", "60",
                                    "res://showcase/showcase.tscn", "--"] + user
            t0 = time.time()
            game = subprocess.Popen(cmd, env=self.env, stdout=log, stderr=subprocess.STDOUT)
            # key times are counted from the moment the game starts recording (its own "AUDIO recording" line)
            started = None
            for at, k in P.get("keys", []):
                while game.poll() is None:
                    if started is None:
                        try:
                            if "AUDIO recording the master bus" in open(logp).read():
                                started = time.time()
                        except OSError:
                            pass
                    if started is not None and time.time() - started >= at:
                        break
                    time.sleep(0.05)
                if game.poll() is not None:
                    break
                tk = time.time() - started
                self.key(k, False)
                self.events.append({"time": round(tk, 3), "key": k})
            game.wait()
            if how == "xvfb":
                self.xv.terminate()
            print("ran %.1f s" % (time.time() - t0))
        json.dump({"plan": plan, "fps": FPS, "how": how, "events": self.events, "args": user},
                  open(os.path.join(self.out, plan + "_keys.json"), "w"), indent=1)
        print("wrote", wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="godot")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", required=True, choices=sorted(PLANS))
    ap.add_argument("--display", default=":141")
    ap.add_argument("--game-args", default="")
    ap.add_argument("--secs", type=float, default=0.0, help="record this long instead of the plan's own length")
    a = ap.parse_args()
    Run(a).run(a.plan)


if __name__ == "__main__":
    main()
