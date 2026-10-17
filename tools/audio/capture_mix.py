#!/usr/bin/env python3
"""Records what the game really sounds like (decision 7, category 4): the showcase runs in a real X11 window on
Xvfb (Mesa software Vulkan) under Godot's Movie Maker (fixed 30 fps: picture and sound frame-exact), and keys go
in through xdotool (XTEST: the X server delivers them like a keyboard; nothing calls game functions). The
recording's sound is then measured by tools/audio/check_mix.py.

  python3 -I tools/audio/capture_mix.py --project godot --out DIR --plan menu|home|brook|gallery|vista|lookout
                                        [--display :141] [--frames N]
Plans (game time; software rendering runs the game far slower than the clock, so keys are held by frames:
the movie's own frame count is watched, see hold()):
  menu     the title: 10 s, then three presses of Down (the menu's sound; key-to-sound latency), 8 s more
  home     the home area at 9:30: stand 8 s, walk round the yard and the camphor (W/D/S/A), stand
  brook    by the brook in rain and wind (--at near the stream, --rain): stand, walk along it, stand
  gallery  the portraits, then the staged dialogue (Space): the ducking under a dialogue
  vista    the prologue's treetop vista, whole (65.6 s and the hold)
  lookout  she walks onto the lookout rock and looks out (the wonder piece)
Writes DIR/<plan>.avi (MJPEG + PCM), DIR/<plan>.wav, DIR/<plan>_keys.json (frame of each key event), DIR/log.txt.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

GODOT = os.environ.get("GODOT_BIN", "/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64")
FPS = 30

PLANS = {
    "menu": {"args": ["--mode=menu"], "frames": 30 * 22,
             "keys": [(10.0, "Down"), (11.5, "Down"), (13.0, "Down"), (14.5, "Up")]},
    "home": {"args": ["--mode=home"], "frames": 30 * 75,
             "keys": [(8.0, "+w"), (14.0, "-w"), (14.0, "+d"), (19.0, "-d"), (19.0, "+s"), (25.0, "-s"), (25.0, "+a"),
                      (31.0, "-a"), (40.0, "+w"), (44.0, "-w")]},
    "brook": {"args": ["--mode=home", "--at=-9.0,-38.6", "--rain=0.85", "--hours=12.5"], "frames": 30 * 60,
              "keys": [(20.0, "+d"), (26.0, "-d"), (26.0, "+a"), (32.0, "-a")]},
    "gallery": {"args": ["--mode=gallery"], "frames": 30 * 40,
                "keys": [(6.0, "space"), (13.0, "space"), (17.0, "space"), (21.0, "space"), (25.0, "space"),
                         (29.0, "space"), (33.0, "space")]},
    "vista": {"args": ["--mode=vista"], "frames": 30 * 80, "keys": []},
    "lookout": {"args": ["--mode=lookout"], "frames": 30 * 50,
                "keys": [(4.0, "+s"), (7.0, "-s")]},
}


class Run:
    def __init__(self, a):
        self.a = a
        self.out = os.path.abspath(a.out)
        os.makedirs(self.out, exist_ok=True)
        self.env = dict(os.environ, DISPLAY=a.display)
        self.events = []
        self._pos, self._count, self._tail = 0, 0, b""

    def start(self, plan):
        # -ardelay / -arinterval: no key auto-repeat to speak of. The game runs far slower than the clock here, so a
        # key held for two of its frames is held for most of a second of the clock, and the server would send
        # repeats a player's quick press never makes
        self.xvfb = subprocess.Popen(["Xvfb", self.a.display, "-screen", "0", "1280x720x24", "-nolisten", "tcp",
                                      "-ardelay", "30000", "-arinterval", "30000"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if subprocess.run(["xdpyinfo"], env=self.env, capture_output=True).returncode == 0:
                break
            time.sleep(0.1)
        P = PLANS[plan]
        frames = self.a.frames or P["frames"]
        self.movie = os.path.join(self.out, plan + ".avi")
        cmd = [GODOT, "--path", os.path.abspath(self.a.project), "--rendering-method", "forward_plus",
               "--resolution", "640x360", "--fixed-fps", str(FPS), "--write-movie", self.movie,
               "--quit-after", str(frames), "res://showcase/showcase.tscn", "--",
               "--windowed", "--audio-log=" + os.path.join(self.out, plan + "_plays.jsonl")] + P["args"] + self.a.game_args.split()
        self.log = open(os.path.join(self.out, plan + "_log.txt"), "w")
        self.game = subprocess.Popen(cmd, env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        self.frames = frames
        self.plan = P

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

    def key(self, k):
        w = self.window()
        if w:
            subprocess.run(["xdotool", "windowactivate", "--sync", w], env=self.env, capture_output=True)
        if k.startswith("+"):
            subprocess.run(["xdotool", "keydown", k[1:]], env=self.env)
        elif k.startswith("-"):
            subprocess.run(["xdotool", "keyup", k[1:]], env=self.env)
        else:
            subprocess.run(["xdotool", "keydown", k], env=self.env)
            # held until the game has drawn two more frames (it reads the key in between)
            f0 = self.frame_now()
            t0 = time.time()
            while self.frame_now() < f0 + 2 and time.time() - t0 < 60:
                time.sleep(0.02)
            subprocess.run(["xdotool", "keyup", k], env=self.env)

    def run(self, plan):
        self.start(plan)
        for at, k in self.plan["keys"]:
            target = int(at * FPS)
            while self.game.poll() is None and self.frame_now() < target:
                time.sleep(0.1)
            if self.game.poll() is not None:
                break
            f = self.frame_now()
            self.key(k)
            self.events.append({"frame": f, "time": round(f / FPS, 3), "key": k})
        self.game.wait()
        self.xvfb.terminate()
        wav = os.path.join(self.out, plan + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.movie, "-vn", "-acodec", "pcm_s16le", wav], check=True)
        json.dump({"plan": plan, "fps": FPS, "frames": self.frames, "events": self.events,
                   "args": self.plan["args"] + self.a.game_args.split()},
                  open(os.path.join(self.out, plan + "_keys.json"), "w"), indent=1)
        print("wrote", wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="godot")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", required=True, choices=sorted(PLANS))
    ap.add_argument("--display", default=":141")
    ap.add_argument("--frames", type=int, default=0)
    ap.add_argument("--game-args", default="")
    a = ap.parse_args()
    Run(a).run(a.plan)


if __name__ == "__main__":
    main()
