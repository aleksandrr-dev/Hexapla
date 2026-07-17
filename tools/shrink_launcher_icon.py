# -*- coding: utf-8 -*-
"""Shrink the launcher-icon scroll into the adaptive-icon safe zone.

Owner report 2026-07-17: the scroll reads edge-to-edge on the launcher
while other apps' icons sit centered. Cause: the foreground artwork
spanned ~57% of the 108dp adaptive canvas, and launchers mask to the
inner ~66% — so the scroll filled ~86% of the visible icon. This scales
every ic_launcher_foreground.png to 75% about its center (content then
~65% of the visible icon) and rebuilds the legacy ic_launcher.png as
background color + the shrunken scroll (legacy is barely used at
minSdk 26 — every API 26+ launcher takes the adaptive XML).

Usage: python shrink_launcher_icon.py
"""
import os
from PIL import Image

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "app", "src", "main", "res")
SCALE = 0.75
BG = (0x4a, 0x14, 0x1c, 255)   # colors.xml ic_launcher_bg (verify below)


def read_bg():
    import re
    for name in ("colors.xml", "ic_launcher_background.xml"):
        p = os.path.join(RES, "values", name)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read()
            m = re.search(r'name="ic_launcher_bg">#?([0-9a-fA-F]{6,8})<', t)
            if m:
                h = m.group(1)
                if len(h) == 8:
                    h = h[2:]      # drop alpha
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    return BG


def shrink(img, scale):
    w, h = img.size
    nw, nh = int(w * scale), int(h * scale)
    small = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(small, ((w - nw) // 2, (h - nh) // 2), small)
    return out


bg = read_bg()
print("background:", bg)
for dpi in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
    d = os.path.join(RES, f"mipmap-{dpi}")
    fg_path = os.path.join(d, "ic_launcher_foreground.png")
    fg = Image.open(fg_path).convert("RGBA")
    new_fg = shrink(fg, SCALE)
    new_fg.save(fg_path)
    # legacy: bg-color square + the shrunken scroll, slightly larger
    # (legacy icons are unmasked, so give the art a bit more room)
    legacy_path = os.path.join(d, "ic_launcher.png")
    size = Image.open(legacy_path).size
    legacy = Image.new("RGBA", size, bg)
    art = shrink(fg, 0.85).resize(size, Image.LANCZOS)
    legacy.alpha_composite(art)
    legacy.convert("RGB").save(legacy_path)
    print(f"{dpi}: foreground {fg.size} scaled x{SCALE}, legacy rebuilt {size}")
