# -*- coding: utf-8 -*-
"""Build the launcher / store icon: the web header's illuminated H as the
cover of a bound Bible, on the header's parchment (owner 2026-10-02).

The artwork is the SVG in this file; the H outline is crest.tsx's H_D
(UnifrakturMaguntia, SIL OFL 1.1). Rendered once with headless Edge/Chrome,
downsampled with Pillow.

Writes (with --apply; the default is a dry run that only lists them):
  app/src/main/res/mipmap-*/ic_launcher_foreground.png   adaptive foreground
  app/src/main/res/mipmap-*/ic_launcher.png              legacy, rounded
  store-assets/icon_1024.png, icon_512_store.png         full-bleed, no alpha
  store-assets/icon_preview_96.png                       rounded preview
  store-assets/icon_master.svg                           the artwork itself
Always writes store-assets/icon-candidates/final_sheet.png: the icon as a
launcher shows it (background + foreground, cropped to the visible 72 of
108 dp, squircle and circle masks) - look at it before --apply.

The adaptive BACKGROUND is res/drawable/ic_launcher_background.xml (a radial
gradient with the same stops as BG below); keep the two in step by hand.

Usage: python tools/build_launcher_icon.py [--apply]
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = os.path.join(ROOT, "app", "src", "main", "res")
STORE = os.path.join(ROOT, "store-assets")

BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)

H_D = "M4.6 180.9Q3 179.1 4.9 177Q18.4 163.4 28.8 158.8Q39.2 154.1 53.4 170Q62 179.4 68.5 182.2Q74.9 185.1 81.1 179Q88.5 171.6 81.2 160.5Q73.9 149.4 54 124.5Q31.4 96.1 31.2 78.5Q31.2 61 59.5 37.5Q101.6 2.6 119.2 28.1Q123.4 34.1 129.2 37.6Q135 41.1 137.5 39.5Q140.2 37.5 142 39.2Q143.6 41.1 141 43.8Q128.6 55 118.2 58Q107.8 61.1 95.8 46.6Q87.4 36.5 79.9 35Q72.4 33.4 63 41.9Q51.9 51.9 56.5 66.2Q61.2 80.6 80.8 103.5Q82 104.9 83.5 103.9L136.4 69.2Q138 68.2 138.8 68.6Q139.6 69 139.9 70.1Q140.2 73.8 148.5 80.6Q162 92.1 172.2 108.8Q182.6 125.4 181.5 147.1Q179.6 179.4 152.2 204.5Q124.9 229.5 91 235.1Q87.1 235.9 86.8 233.2Q86.4 230.6 89.8 229.9Q135.8 218.6 148 181.2Q160.4 144 131.8 111.5Q123.2 102.1 114.5 100Q105.8 98 92.2 106.6L88.2 109Q86.4 110.2 87.8 112Q102.9 131.5 104.9 147Q106.9 162.6 86.9 181.5Q66.6 200.6 56.4 203.4Q46.1 206.1 30.9 190.2Q27 186.4 21 181.4Q15 176.4 8.6 181Q6.4 182.5 4.6 180.9Z"

# The H centred on (267, 228) at 0.84; the glyph's own centre is (92.5, 129).
H_T = "translate(%.2f %.2f) scale(0.84)" % (267 - 92.5 * 0.84, 228 - 129 * 0.84)

DEFS = """
<defs>
  <filter id="blur" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="9"/></filter>
  <radialGradient id="bg" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="#f6ecd0"/><stop offset="1" stop-color="#d6bf8b"/></radialGradient>
  <linearGradient id="cover" x1="0" x2="1"><stop offset="0" stop-color="#7a2323"/><stop offset=".18" stop-color="#8f2c2c"/><stop offset="1" stop-color="#701f1f"/></linearGradient>
  <linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".10"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".16"/></linearGradient>
  <linearGradient id="gd" gradientUnits="userSpaceOnUse" x1="118" y1="76" x2="402" y2="442"><stop offset="0" stop-color="#ecc874"/><stop offset=".5" stop-color="#c79840"/><stop offset="1" stop-color="#e2ba5e"/></linearGradient>
  <linearGradient id="pages" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6ecd0"/><stop offset="1" stop-color="#e6d4a6"/></linearGradient>
</defs>
"""

# Book bbox 118..402 x 76..470 with the ribbon; drawn at 0.9 about its centre
# so it fills ~69 % of the visible icon (the 2026-07-17 edge-to-edge report)
# and every corner sits inside the 66 dp safe circle.
BOOK = """
<g transform="translate(256 256) scale(0.9) translate(-260 -266)">
  <ellipse cx="262" cy="452" rx="150" ry="14" fill="#2a1505" opacity=".5" filter="url(#blur)"/>
  <rect x="124" y="82" width="278" height="360" rx="11" fill="#451212"/>
  <rect x="130" y="88" width="264" height="346" rx="5" fill="url(#pages)"/>
  <path d="M385 96v330M390 96v330M138 424h250M138 430h250" stroke="#c9b17c" stroke-width="2" fill="none"/>
  <path d="M316 432h26v38l-13-11-13 11z" fill="#b5352f"/>
  <path d="M316 432h13v27l-13 11z" fill="#8f2622"/>
  <rect x="118" y="76" width="264" height="344" rx="10" fill="url(#cover)"/>
  <rect x="118" y="76" width="264" height="344" rx="10" fill="url(#sheen)"/>
  <path d="M128 76h22v344h-22a10 10 0 0 1-10-10V86a10 10 0 0 1 10-10z" fill="#561616"/>
  <rect x="150" y="76" width="3" height="344" fill="#3c0f0f" opacity=".7"/>
  <g fill="url(#gd)"><rect x="118" y="116" width="32" height="4"/><rect x="118" y="127" width="32" height="4"/><rect x="118" y="365" width="32" height="4"/><rect x="118" y="376" width="32" height="4"/></g>
  <rect x="172" y="98" width="190" height="300" fill="#671b1b" stroke="url(#gd)" stroke-width="6"/>
  <rect x="184" y="110" width="166" height="276" fill="none" stroke="url(#gd)" stroke-width="2"/>
  <path d="M175 101h34l-34 34zM359 101h-34l34 34zM175 395h34l-34-34zM359 395h-34l34-34z" fill="url(#gd)"/>
  <path d="M267 113l7 7-7 7-7-7z" fill="url(#gd)"/>
  <g transform="translate(267 346)">
    <path d="M0-27l27 27-27 27-27-27z" fill="url(#gd)"/>
    <path d="M0-18l18 18-18 18-18-18z" fill="#671b1b"/>
    <path d="M-3-12h6v8h7v6h-7v10h-6v-10h-7v-6h7z" fill="#ecc874"/>
  </g>
  <path fill="#3a0e0e" opacity=".55" transform="translate(2.5 3.5) H_T" d="H_D"/>
  <path fill="#f6ead0" transform="H_T" d="H_D"/>
</g>
""".replace("H_T", H_T).replace("H_D", H_D)

BG = '<rect x="-128" y="-128" width="768" height="768" fill="url(#bg)"/>'
# Launchers draw the background across the whole 108 dp canvas; the gradient
# is defined on the visible 72 dp (0..512), so pin it there for the simulation.
BG_DEFS = DEFS.replace('<radialGradient id="bg" cx="50%" cy="45%" r="70%">',
                       '<radialGradient id="bg" gradientUnits="userSpaceOnUse" cx="256" cy="230" r="358">')


def svg(view, px, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" width="%d" height="%d">%s%s</svg>'
            % (view, px, px, BG_DEFS, body))


FULL = "0 0 512 512"          # what a launcher shows: the visible 72 dp
ADAPT = "-128 -128 768 768"   # the whole 108 dp adaptive canvas


def render(browser, tmp, name, markup, px):
    src = os.path.join(tmp, name + ".svg")
    out = os.path.join(tmp, name + ".png")
    with open(src, "w", encoding="utf-8", newline="\n") as f:
        f.write(markup)
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--default-background-color=00000000",
           "--user-data-dir=" + os.path.join(tmp, "profile"),
           "--window-size=%d,%d" % (px, px), "--screenshot=" + out,
           "file:///" + src.replace("\\", "/")]
    rc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120).returncode
    for _ in range(40):
        if os.path.exists(out) and os.path.getsize(out) > 0:
            break
        time.sleep(0.25)
    else:
        raise SystemExit("render failed: %s (browser rc %s, no screenshot)" % (name, rc))
    img = Image.open(out).convert("RGBA")
    if img.size != (px, px):
        raise SystemExit("render failed: %s is %s, wanted %dx%d" % (name, img.size, px, px))
    return img


def masked(img, shape):
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    w = img.size[0]
    if shape == "circle":
        d.ellipse((0, 0, w - 1, w - 1), fill=255)
    else:
        d.rounded_rectangle((0, 0, w - 1, w - 1), radius=int(w * 0.22), fill=255)
    out = img.copy()
    out.putalpha(m)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the icon files (default: dry run)")
    args = ap.parse_args()

    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not browser:
        raise SystemExit("no Edge/Chrome found to render the SVG")

    # The browser can still hold its profile cache when the renders are done.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        full = render(browser, tmp, "full", svg(FULL, 1024, BG + BOOK), 1024)
        fg = render(browser, tmp, "fg", svg(ADAPT, 864, BOOK), 864)
        bg = render(browser, tmp, "bg", svg(ADAPT, 864, BG), 864)

    if fg.getpixel((4, 4))[3] != 0:
        raise SystemExit("foreground is not transparent at its corner - the browser ignored the background flag")
    if full.getpixel((4, 4))[3] != 255:
        raise SystemExit("full icon is not opaque at its corner")

    # The launcher's view: background + foreground, the central 72 of 108 dp.
    adaptive = Image.alpha_composite(bg, fg).crop((144, 144, 720, 720))
    sheet = Image.new("RGB", (1260, 500), (233, 230, 223))
    ImageDraw.Draw(sheet).rectangle((0, 250, 1260, 500), fill=(28, 27, 31))
    for row in (0, 1):
        x = 24
        for px, shape in ((192, "sq"), (96, "sq"), (48, "sq"), (32, "sq"), (192, "circle"), (96, "circle"), (48, "circle")):
            tile = masked(adaptive.resize((px, px), Image.LANCZOS), shape)
            sheet.paste(tile, (x, row * 250 + 125 - px // 2), tile)
            x += px + 28
        store = full.resize((192, 192), Image.LANCZOS)
        sheet.paste(store, (x, row * 250 + 29), store)
    sheet_path = os.path.join(STORE, "icon-candidates", "final_sheet.png")
    os.makedirs(os.path.dirname(sheet_path), exist_ok=True)
    sheet.save(sheet_path)
    print("sheet:", sheet_path)

    outputs = []
    for dpi, legacy_px, fg_px in (("mdpi", 48, 108), ("hdpi", 72, 162), ("xhdpi", 96, 216),
                                  ("xxhdpi", 144, 324), ("xxxhdpi", 192, 432)):
        d = os.path.join(RES, "mipmap-" + dpi)
        outputs.append((os.path.join(d, "ic_launcher_foreground.png"), fg.resize((fg_px, fg_px), Image.LANCZOS)))
        outputs.append((os.path.join(d, "ic_launcher.png"), masked(full.resize((legacy_px, legacy_px), Image.LANCZOS), "sq")))
    outputs.append((os.path.join(STORE, "icon_1024.png"), full.convert("RGB")))
    outputs.append((os.path.join(STORE, "icon_512_store.png"), full.resize((512, 512), Image.LANCZOS).convert("RGB")))
    outputs.append((os.path.join(STORE, "icon_preview_96.png"), masked(full.resize((96, 96), Image.LANCZOS), "sq")))
    master = os.path.join(STORE, "icon_master.svg")

    for path, img in outputs:
        state = "overwrite" if os.path.exists(path) else "create"
        print("%s %-9s %4dx%-4d %s" % ("WRITE" if args.apply else "would", state, img.size[0], img.size[1],
                                       os.path.relpath(path, ROOT)))
        if args.apply:
            img.save(path)
    print("%s %-9s           %s" % ("WRITE" if args.apply else "would",
                                    "overwrite" if os.path.exists(master) else "create", os.path.relpath(master, ROOT)))
    if args.apply:
        with open(master, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg(FULL, 1024, BG + BOOK))
    else:
        print("dry run - nothing but the sheet was written; re-run with --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
