"""SVG -> PNG with the preinstalled headless Chromium shell (Playwright's chromium_headless_shell).
The SVG is opened as a local file; nothing is fetched (all fonts and images are data URIs)."""
from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path


def find_shell():
    env = os.environ.get("VD_CHROME")
    if env and Path(env).exists():
        return env
    for pat in ("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell",
                "/opt/pw-browsers/chromium-*/chrome-linux/chrome"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    raise SystemExit("no headless Chromium found (set VD_CHROME)")


def svg_to_png(svg_path, png_path, width, height, scale=2):
    shell = find_shell()
    args = [shell, "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=%g" % scale,
            "--window-size=%d,%d" % (int(round(width)), int(round(height))), "--default-background-color=00000000",
            "--screenshot=%s" % Path(png_path).resolve(), "file://%s" % Path(svg_path).resolve()]
    if shell.endswith("/chrome"):
        args.insert(1, "--headless=old")
    r = subprocess.run(args, capture_output=True, text=True, timeout=180)
    if not Path(png_path).exists():
        raise SystemExit("chromium failed: %s" % r.stderr[-2000:])
