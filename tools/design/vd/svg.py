"""A small SVG writer for the drawings: layers, a plan-to-paper transform, text that remembers which
glyphs each font needs (for subsetting), and the house style (palette, line weights, type)."""
from __future__ import annotations

import html
from pathlib import Path

from .fonts import LICENSE

# ---- house style -----------------------------------------------------------------------------------
PAPER = "#f3efe6"
INK = "#2f2a24"
INK2 = "#5b5248"
INK3 = "#8a7f72"
RULE = "#b9ad9b"
VERMILION = "#b4472e"        # 朱: the realm's boundary and thresholds only
WATER = "#a9c8d3"
WATER_EDGE = "#4f8399"
MOSS = "#a7bb86"
GRASS = "#c9c79b"
SUSUKI = "#cfc596"
CEDAR = "#6f8a6e"
BROAD = "#93a97f"
MAPLE = "#a8b783"
PINE = "#7f9772"
BAMBOO = "#7a8a5d"
ROCK = "#a39d91"
ROCK_EDGE = "#5d5850"
THATCH = "#c9b58a"
WOOD = "#8a6f55"
PATH_SHIN = "#d8d2c4"
PATH_GYO = "#e2d8c3"
PATH_SO = "#e6dcc3"
PLOT = "#cdbb8e"
SKY = "#5b6f8a"              # sightlines / view frustums

CLASSES = {
    # class: (css, font key)
    "title": ('font-family:"VD Serif";font-weight:700;font-size:30px;fill:%s' % INK, "serif700"),
    "title2": ('font-family:"VD Serif";font-weight:600;font-size:17px;fill:%s' % INK2, "serif600"),
    "head": ('font-family:"VD Serif";font-weight:700;font-size:15px;fill:%s' % INK, "serif700"),
    "zone": ('font-family:"VD Serif";font-weight:600;font-size:13px;fill:%s' % INK, "serif600"),
    "zone-s": ('font-family:"VD Serif";font-weight:600;font-size:11px;fill:%s' % INK2, "serif600"),
    "lab": ('font-family:"VD Sans";font-weight:500;font-size:8.5px;fill:%s' % INK, "sans500"),
    "lab-b": ('font-family:"VD Sans";font-weight:700;font-size:9.5px;fill:%s' % INK, "sans700"),
    "lab-s": ('font-family:"VD Sans";font-weight:400;font-size:7.5px;fill:%s' % INK2, "sans400"),
    "note": ('font-family:"VD Sans";font-weight:400;font-size:11px;fill:%s' % INK, "sans400"),
    "note-b": ('font-family:"VD Sans";font-weight:700;font-size:11px;fill:%s' % INK, "sans700"),
    "note-s": ('font-family:"VD Sans";font-weight:400;font-size:9.5px;fill:%s' % INK2, "sans400"),
    "leg": ('font-family:"VD Sans";font-weight:400;font-size:10.5px;fill:%s' % INK, "sans400"),
    "num": ('font-family:"VD Sans";font-weight:500;font-size:9px;fill:%s' % INK2, "sans500"),
    "red": ('font-family:"VD Sans";font-weight:700;font-size:10px;fill:%s' % VERMILION, "sans700"),
}


def f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def esc(s):
    return html.escape(str(s), quote=True)


class Svg:
    def __init__(self, width, height, title=""):
        self.W, self.H = width, height
        self.title = title
        self.layers = {}
        self.order = []
        self.defs = []
        self.text_by_key = {}
        self.layer("base")

    def layer(self, name):
        if name not in self.layers:
            self.layers[name] = []
            self.order.append(name)
        self.cur = name
        return self

    def add(self, s):
        self.layers[self.cur].append(s)

    def defn(self, s):
        self.defs.append(s)

    @staticmethod
    def attrs(kw):
        out = []
        for k, v in kw.items():
            if v is None:
                continue
            k = k.rstrip("_").replace("_", "-")
            if isinstance(v, float):
                v = f(v)
            out.append('%s="%s"' % (k, esc(v)))
        return " ".join(out)

    def path(self, d, **kw):
        self.add('<path d="%s" %s/>' % (d, self.attrs(kw)))

    def poly(self, pts, closed=True, **kw):
        if len(pts) < 2:
            return
        d = "M" + " L".join("%s,%s" % (f(u), f(v)) for u, v in pts) + (" Z" if closed else "")
        self.path(d, **kw)

    def circle(self, u, v, r, **kw):
        self.add('<circle cx="%s" cy="%s" r="%s" %s/>' % (f(u), f(v), f(r), self.attrs(kw)))

    def rect(self, u, v, w, h, **kw):
        self.add('<rect x="%s" y="%s" width="%s" height="%s" %s/>' % (f(u), f(v), f(w), f(h), self.attrs(kw)))

    def line(self, u0, v0, u1, v1, **kw):
        self.add('<line x1="%s" y1="%s" x2="%s" y2="%s" %s/>' % (f(u0), f(v0), f(u1), f(v1), self.attrs(kw)))

    def text(self, u, v, s, cls="lab", anchor="start", rot=None, halo=False, **kw):
        s = str(s)
        key = CLASSES[cls][1]
        self.text_by_key[key] = self.text_by_key.get(key, "") + s
        tr = ' transform="rotate(%s %s %s)"' % (f(rot), f(u), f(v)) if rot else ""
        a = self.attrs(kw)
        if halo:
            self.add('<text x="%s" y="%s" class="%s" text-anchor="%s"%s style="stroke:%s;stroke-width:2.6px;'
                     'stroke-linejoin:round;paint-order:stroke" %s>%s</text>' % (f(u), f(v), cls, anchor, tr, halo if isinstance(halo, str) else PAPER, a, esc(s)))
        else:
            self.add('<text x="%s" y="%s" class="%s" text-anchor="%s"%s %s>%s</text>' % (f(u), f(v), cls, anchor, tr, a, esc(s)))

    def image(self, u, v, w, h, data_uri, **kw):
        self.add('<image x="%s" y="%s" width="%s" height="%s" href="%s" %s/>' % (f(u), f(v), f(w), f(h), data_uri, self.attrs(kw)))

    def raw(self, s):
        self.add(s)

    def to_string(self, fonts):
        css = "\n".join(".%s{%s}" % (k, v[0]) for k, v in CLASSES.items())
        font_css = fonts.css(self.text_by_key) if fonts else ""
        body = []
        for name in self.order:
            body.append('<g id="%s">' % esc(name))
            body.extend(self.layers[name])
            body.append("</g>")
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                'width="%d" height="%d" viewBox="0 0 %d %d">\n<title>%s</title>\n<!-- %s -->\n<defs>\n<style>\n%s\n%s\n</style>\n%s\n</defs>\n%s\n</svg>\n'
                % (self.W, self.H, self.W, self.H, esc(self.title), esc(LICENSE), font_css, css, "\n".join(self.defs), "\n".join(body)))

    def save(self, path, fonts):
        Path(path).write_text(self.to_string(fonts), encoding="utf-8")


class Frame:
    """Plan (x east, y north, metres) -> paper (u right, v down, px)."""

    def __init__(self, x0, y0, x1, y1, scale, u0, v0):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.s = scale
        self.u0, self.v0 = u0, v0
        self.w = (x1 - x0) * scale
        self.h = (y1 - y0) * scale

    def __call__(self, x, y):
        return self.u0 + (x - self.x0) * self.s, self.v0 + (self.y1 - y) * self.s

    def pts(self, P):
        return [self(p[0], p[1]) for p in P]

    def contains(self, x, y, margin=0.0):
        return self.x0 - margin <= x <= self.x1 + margin and self.y0 - margin <= y <= self.y1 + margin


def smooth_path(pts, closed=False, tension=0.5):
    """Catmull-Rom through paper points -> SVG path d."""
    P = list(pts)
    if len(P) < 3:
        return "M" + " L".join("%s,%s" % (f(u), f(v)) for u, v in P) + (" Z" if closed else "")
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0]] + P + [P[-1]]
    d = ["M%s,%s" % (f(P[1][0]), f(P[1][1]))]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        d.append("C%s,%s %s,%s %s,%s" % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1])))
    if closed:
        d.append("Z")
    return " ".join(d)
