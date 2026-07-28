"""Store screenshot: SPLIT VIEW, one translation interleaved with another.

Built for the en-IN Play listing, where the selling point is the Indian texts
but the listing itself is in English. A localized single-column shot
(screenshot_reader_ta.png) puts Tamil in the top bar too, so it reads as a
Tamil-language listing; this one keeps the UI English and shows the Tamil
Bible as CONTENT, while also demonstrating the verse-locked parallel reader —
the app's single most distinctive feature.

Layout matches the real device capture (store-assets/rustore/120307.jpg,
KJV ‖ Синодальный, Titus 1): the two translations are INTERLEAVED VERTICALLY,
not set in side-by-side columns. Per verse: primary line(s) in bright ink,
then the same verse in the secondary in dimmer ink, then a hairline divider.
Both lines carry the verse number. Do not "improve" this into two columns —
it would no longer show what the app does.

Serif (Georgia) is used for the Latin text deliberately: this shot ships
alongside the real captures in the same upload set, and those are serif. The
other generated reader shots use Segoe UI, so this one intentionally differs.

Tamil is shaped by tools/render_text.ps1 (WPF/DirectWrite) — PIL cannot do
Indic reordering.

Usage: python make_split_shot.py            # all SHOTS below
       python make_split_shot.py kjv_ta     # just one
"""
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# ⚠ MUST MIRROR Bible.kt parseAsset, or the shot shows text no user ever sees.
# The raw KJV asset carries ~7,859 translator margin notes as "{term: alt}".
# The app strips any brace group CONTAINING A COLON and collapses the
# resulting whitespace; brace groups WITHOUT a colon are supplied words and
# are kept. Reading the asset raw put "{comprehended: or, did not admit, or,
# receive}" into John 1:5 of the first draft of this screenshot.
#   Bible.kt: Regex("""\s*\{([^{}]*:[^{}]*)\}""") then Regex("""\s+""")
MARGIN_NOTE = re.compile(r'\s*\{[^{}]*:[^{}]*\}')
MULTI_SPACE = re.compile(r'\s+')


def display_text(raw):
    """Verse text as the READER renders it, not as the asset stores it."""
    return MULTI_SPACE.sub(' ', MARGIN_NOTE.sub('', raw)).strip()

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")
OUT = os.path.join(HERE, "..", "store-assets")

W, H = 1080, 1920
BG = (0x18, 0x14, 0x11)
INK = (0xE9, 0xE2, 0xD4)        # primary translation
INK2 = (0xC3, 0xBA, 0xAA)       # secondary — dimmer, as in the real capture
GOLD = (0xD6, 0xA2, 0x5E)
NUM = (0xC9, 0x93, 0x50)
ICON = (0xE0, 0xD8, 0xC8)
DIVIDER = (0x3A, 0x35, 0x2F)

WIN_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# key, primary asset, secondary asset, book idx, chapter idx, English title,
# secondary WPF family (None = render the secondary with PIL too)
SHOTS = [
    ("kjv_ta", "en_kjv.json", "ta_irv.json", 42, 0, "John 1", "Nirmala UI"),
]

LATIN_FONTS = ["georgia.ttf", "constan.ttf", "times.ttf"]


def font_of(names, size):
    for n in names:
        p = os.path.join(WIN_FONTS, n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    raise SystemExit(f"no font among {names}")


def wrap_words(draw, text, font, maxw):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def render_via_wpf(items):
    mf = os.path.join(tempfile.gettempdir(), "hexapla_split_text.json")
    with open(mf, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", os.path.join(HERE, "render_text.ps1"), "-Manifest", mf],
        check=True, stdout=subprocess.DEVNULL)


def draw_topbar(d, title, tfont):
    y = 165
    d.line((70, y, 130, y), fill=ICON, width=7)
    d.line((70, y, 100, y - 28), fill=ICON, width=7)
    d.line((70, y, 100, y + 28), fill=ICON, width=7)
    w = d.textlength(title, font=tfont)
    d.text(((W - w) / 2 - 60, y - 30), title, font=tfont, fill=GOLD)
    d.ellipse((715, y - 26, 755, y + 14), outline=ICON, width=6)
    d.line((752, y + 10, 775, y + 32), fill=ICON, width=7)
    d.polygon([(845, y - 8), (868, y - 8), (896, y - 32), (896, y + 32),
               (868, y + 8), (845, y + 8)], fill=ICON)
    d.arc((900, y - 20, 934, y + 20), -50, 50, fill=ICON, width=5)
    d.line((950, y, 1010, y), fill=ICON, width=7)
    d.line((1010, y, 980, y - 28), fill=ICON, width=7)
    d.line((1010, y, 980, y + 28), fill=ICON, width=7)
    d.line((0, 232, W, 232), fill=DIVIDER, width=2)


def hexc(rgb):
    return "#%02X%02X%02X" % rgb


def build(key, a_asset, b_asset, book_idx, ch_idx, title, b_family):
    a_books = json.load(open(os.path.join(ASSETS, a_asset), encoding="utf-8"))
    b_books = json.load(open(os.path.join(ASSETS, b_asset), encoding="utf-8"))
    a_verses = [display_text(v) for v in a_books[book_idx]["chapters"][ch_idx]]
    b_verses = [display_text(v) for v in b_books[book_idx]["chapters"][ch_idx]]
    n = min(len(a_verses), len(b_verses))

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    tfont = font_of(LATIN_FONTS, 48)
    vfont = font_of(LATIN_FONTS, 44)
    nfont = font_of(["segoeui.ttf"] + LATIN_FONTS, 26)

    x_num, x_text = 48, 100
    maxw = W - x_text - 52
    line_h, pair_gap, verse_gap = 58, 10, 30

    draw_topbar(d, title, tfont)

    # Pre-shape the secondary (Tamil) verses in WPF; only as many as can fit.
    b_png = {}
    if b_family:
        tmp = tempfile.gettempdir()
        items, outs = [], {}
        for i in range(n):
            o = os.path.join(tmp, f"hex_split_{key}_{i}.png")
            outs[i] = o
            items.append({"text": b_verses[i], "font": b_family, "size": 42,
                          "color": hexc(INK2), "wrap": True, "maxwidth": maxw,
                          "out": o, "rtl": False})
        render_via_wpf(items)
        for i, o in outs.items():
            if os.path.exists(o):
                b_png[i] = Image.open(o)

    y = 300
    drawn = 0
    for i in range(n):
        a_lines = wrap_words(d, a_verses[i], vfont, maxw)
        a_h = len(a_lines) * line_h
        b_h = b_png[i].height if i in b_png else 0
        if y + a_h + pair_gap + b_h > H - 40:
            break

        d.text((x_num, y + 12), str(i + 1), font=nfont, fill=NUM)
        for line in a_lines:
            d.text((x_text, y), line, font=vfont, fill=INK)
            y += line_h
        y += pair_gap

        d.text((x_num, y + 12), str(i + 1), font=nfont, fill=NUM)
        if i in b_png:
            img.paste(b_png[i], (x_text, y), b_png[i])
            y += b_h
        y += verse_gap
        drawn += 1

        if y < H - 60:
            d.line((0, y - verse_gap // 2, W, y - verse_gap // 2),
                   fill=DIVIDER, width=2)

    out = os.path.join(OUT, f"screenshot_split_{key}.png")
    img.save(out)
    print(f"saved {out}  ({drawn} verse pairs)")


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    for shot in SHOTS:
        if only and shot[0] not in only:
            continue
        build(*shot)


if __name__ == "__main__":
    main()
