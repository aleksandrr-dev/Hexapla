# -*- coding: utf-8 -*-
"""Adjudicate a single o/ø site by cropping it out of the NATIVE per-line image.

    python tools/thorlaks_o_zoom.py --chunk matthew_kit p16 49 R
    python tools/thorlaks_o_zoom.py --chunk matthew_kit p16 49 R --x 0 --w 150
    python tools/thorlaks_o_zoom.py --chunk matthew_kit \
        --stack p14:12:L:1060:96 p16:49:R:0:150 p16:52:L:150:150

✅ **THE CONTROL, WITH ITS WINDOW — put it FIRST in every batch:**

        p14:12:L:1060:96        «hin ø» — Matt 12:13, the confirmed ø site

⚠ The window matters and is not obvious. The retrofit SHEET shows this site as
«p14 line12 L/R», which reads as though the ø were at the START of the R half;
it is not — it is the LAST glyph of the L half, and `p14:12:R:0:150` frames
«ñur.» with the stroke already cut off. A batch whose "control" shows no ø is
worse than no control: it teaches the reader that the control is unresolvable.

Batch about FOUR sites per call (control + three candidates). One call per word
is what made a full-page retrofit cost ~12 reads a sheet, and two agents stopped
partway through Matthew because of it.

⚠⚠ **DO NOT ESTIMATE `X` FROM THE PACKED SHEET — IT DOES NOT TRANSFER.** Reported
by the p6-p7 reader, 2026-09-06, after chasing blank crops on seven lines. The
packed retrofit sheet's L/R rows are built by its own layout; `line_half()` here
splits the native crop at exactly `width // 2`, and a word's visual proportion
across the sheet row does not map onto the same fraction of that half.
▶ What works: crop a WIDE region of the native line with PIL first to locate the
word, then call this tool with a tight window for the actual reading —

    python -c "from PIL import Image; im=Image.open('research/_prep/matthew_kit/p7/line04.png').convert('L'); w,h=im.size; c=im.crop((w//2,0,w,h)); c.resize((c.width*3,c.height*3)).save('_work/find.png')"

The locating crop is throwaway and its magnification does not matter; only the
final windowed read is evidence.

⚠⚠ WHY THIS EXISTS — MEASURED 2026-09-06, THE RETROFIT'S NEGATIVES WERE WRONG.
The ø retrofit reads packed 4-line sheets (`_work/sheets/<chunk>_o_retrofit/
p<N>_o<NN>.png`, 1200 px wide, four line-halves stacked). An agent read p16 and
p17 that way and reported «ſogdu» as PLAIN o at p16 line49 R and p16 line52 L.
Both words plainly carry the ø stroke — proved by cropping them out of
`research/_prep/<chunk>/p16/line49.png` and viewing them at 5x beside the p14
control. Evidence: `research/_evidence/o_retrofit_false_negatives_2026-09-06.png`.

▶ So a packed sheet is fine for SPOTTING candidates and is NOT sufficient for
  adjudicating one. Crop the word and look at it.
▶ The 5x NEAREST resize adds NO information. It is not upscaling-as-evidence:
  it exists solely to stop the reader downscaling a 1200 px image before a model
  ever sees it, which is the same reasoning that caps the retrofit sheets at
  1200 px wide (thorlaks_o_sheets.py).
⛔ Never read above the prep crops' 8.3x — that IS the scan's native ceiling
  (thorlaks_sorts.py). This tool never re-renders the PDF; it only crops what
  prep already produced.

WHAT THE STROKE LOOKS LIKE at 5x: the bowl's white counter is BISECTED by a dark
diagonal running lower-left to upper-right. A plain o has one clean open counter.
⚠ A horizontal bar ABOVE the o is a nasal abbreviation, NOT ø.
⚠⚠ ø IS NOT PREDICTABLE FROM THE WORD. «giorde» (modern gjörði, an ö-sound)
   prints a PLAIN o. Read the stroke or do not mark it.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# ⚠ BOTH streams. Windows defaults to cp1252 and the ⛔/⚠/▶ in the refusal path
# go to STDERR via sys.exit — reconfiguring stdout alone leaves the one message
# that matters unreadable.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("C:/Projects/Hexapla-releases")
SCALE = 5
LABEL_H = 15
# ⛔ THE WHOLE POINT IS THAT THE READER MUST NOT DOWNSCALE THIS IMAGE.
# A full line-half is ~984 px; at 5x that is 4920 px, which is downscaled to
# BELOW the packed sheet it was meant to improve on — i.e. the tool would
# silently reproduce the very false-negative it exists to prevent. So the
# output is CAPPED and the tool REFUSES rather than emitting useless evidence.
MAX_W = 1200
# The reader fits the LONG edge, so height needs the same cap as width.
MAX_EDGE = 1568

ap = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--chunk", default="matthew_kit", help="prep chunk dir under research/_prep/")
ap.add_argument("site", nargs="*", help="PAGE LINE HALF, e.g. p16 49 R")
ap.add_argument("--stack", nargs="+", metavar="P:LINE:HALF[:X[:W]]",
                help="several sites in ONE image — the cheap way to compare, and "
                     "the only way to compare against a control. Give each site "
                     "its OWN window as :X or :X:W, e.g. p6:14:L:300 — one shared "
                     "--x cannot frame words that sit at different places on "
                     "their lines, which forced one call per word")
ap.add_argument("--x", type=int, default=None, help="left edge within the half, px")
ap.add_argument("--w", type=int, default=150, help="window width with --x, px")
ap.add_argument("--out", default=None, help="output png (default: _work/o_zoom.png)")
a = ap.parse_args()


def line_half(page, line, half):
    """-> the LEFT or RIGHT half of a native per-line crop.

    ⚠ The retrofit sheets label rows `p16 line49 L` / `... R`; those halves are
    exactly this split, so a site reported off a sheet maps here unchanged.
    """
    page = page if str(page).startswith("p") else f"p{page}"
    f = ROOT / "research/_prep" / a.chunk / page / f"line{int(line):02d}.png"
    if not f.exists():
        sys.exit(f"no such line crop: {f}\n"
                 f"⚠ a page whose prep produced few crops (a tall-block page) may not "
                 f"number its lines the way a sheet label does — check "
                 f"research/_prep/{a.chunk}/{page}/ before assuming a miss.")
    im = Image.open(f).convert("L")
    w, h = im.size
    return im.crop((0, 0, w // 2, h)) if half.upper() == "L" else im.crop((w // 2, 0, w, h))


def window(c):
    if a.x is None:
        return c
    return c.crop((a.x, 0, min(a.x + a.w, c.width), c.height))


sites = []
if a.stack:
    for s in a.stack:
        parts = s.split(":")
        if not 3 <= len(parts) <= 5:
            sys.exit(f"--stack takes PAGE:LINE:HALF[:X[:W]], got {s!r}")
        p, ln, hf = parts[0], parts[1], parts[2]
        c = line_half(p, ln, hf)
        lab = f"{p} line{int(ln):02d} {hf.upper()}"
        if len(parts) >= 4:            # per-site window — see the batching note
            x0 = int(parts[3])
            w = int(parts[4]) if len(parts) >= 5 else a.w
            c = c.crop((x0, 0, min(x0 + w, c.width), c.height))
            lab += f" x{x0}"
        else:
            c = window(c)
        sites.append((c, lab))
elif len(a.site) == 3:
    p, ln, hf = a.site
    sites.append((window(line_half(p, ln, hf)), f"{p} line{int(ln):02d} {hf.upper()}"))
else:
    sys.exit("give PAGE LINE HALF (e.g. p16 49 R), or --stack p15:44:L p16:49:R")

W = max(c.width for c, _ in sites) * SCALE
if W > MAX_W:
    widest = max(c.width for c, _ in sites)
    sys.exit(
        f"⛔ REFUSING: the composite would be {W} px wide (widest crop {widest} px "
        f"x {SCALE}). The reader downscales anything past ~{MAX_W} px, so this image "
        f"would show the stroke SMALLER than the packed sheet does — the exact false "
        f"negative this tool exists to prevent.\n"
        f"▶ Narrow to the word: add --x <left edge in the half> --w {MAX_W // SCALE} "
        f"(or smaller). Find the left edge by first viewing the packed sheet "
        f"_work/sheets/{a.chunk.replace('_kit', '')}_o_retrofit/, or step --x in "
        f"~150 px increments across the half.")
H = sum(c.height * SCALE + LABEL_H + 8 for c, _ in sites)
# ⛔ HEIGHT IS AS LOAD-BEARING AS WIDTH. The reader fits the LONG edge, so a tall
# stack is downscaled exactly like a wide one. A batch of ten sites builds a
# ~3400 px column that comes back at ~0.45x — smaller than the packed sheet, and
# the tool would silently defeat itself while printing a success line. At 5x each
# site is ~340 px tall, so about four fit; batch four, not ten.
if H > MAX_EDGE:
    sys.exit(
        f"⛔ REFUSING: the composite would be {H} px tall ({len(sites)} sites x "
        f"~{sites[0][0].height * SCALE + LABEL_H + 8} px). The reader downscales "
        f"anything past ~{MAX_EDGE} px on its long edge, so every stroke in this "
        f"image would be shown SMALLER than the packed sheet shows it.\n"
        f"▶ Split into batches of about {max(1, MAX_EDGE // (sites[0][0].height * SCALE + LABEL_H + 8))} "
        f"sites, each still including the control as the first entry.")
out = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(out)
y = 0
for c, lab in sites:
    d.text((2, y + 2), lab, fill=0)
    y += LABEL_H
    out.paste(c.resize((c.width * SCALE, c.height * SCALE), Image.NEAREST), (0, y))
    y += c.height * SCALE + 8

dest = Path(a.out) if a.out else ROOT / "_work/o_zoom.png"
dest.parent.mkdir(parents=True, exist_ok=True)
out.save(dest)
print(f"{dest}  ({out.size[0]}x{out.size[1]}, {len(sites)} site(s), {SCALE}x NEAREST)")
print("⚠ Read the stroke through the bowl. Do NOT infer ø from the word or from "
      "modern Icelandic spelling.")
