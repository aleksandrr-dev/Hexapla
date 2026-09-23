# -*- coding: utf-8 -*-
"""Cut every diacritic site to ONE IDENTICAL pixel box, centred on the mark.

    python tools/kxii_fixed_sheet.py --sites sites.json --out sheet.png
    python tools/kxii_fixed_sheet.py --sites sites.json --out sheet.png \
        --box 150x105 --tile-h 1000

## WHY THIS EXISTS — kxii_marks.py AUTO-SIZES, AND THAT INVALIDATES A SHEET

`kxii_marks.py` finds marks by measurement, which is exactly right, but it
emits a box sized to EACH MARK. `contact_sheet.py` then normalises tiles to a
common HEIGHT, so a 108 px source box and a 94 px source box end up at
DIFFERENT MAGNIFICATIONS on the same sheet. The brief's §4-0b says every tile,
site and control alike, must be cut to the same pixel box — and the Sirach
sessions had to RETRACT a reading made on an auto-sized sheet.

So this takes the mark's measured CENTRE from kxii_marks and re-cuts a fixed
WxH window around it. Same box for every site, same box for every control,
therefore one magnification across the whole sheet.

▶ ALSO: it centres the MARK, not the word. A control whose mark sits at the
tile edge is unusable, and that has voided whole sheets before.

## THE RULES THIS TOOL DOES NOT ENFORCE, AND YOU MUST

  · Every sheet carries a RING control and an ‹e› control FROM THE SAME STRIP,
    and you look at the controls FIRST. If a control's mark is not in frame,
    the sheet is void — throw it away, do not squint.
  · Never use a contested lexeme as its own control.
  · A control with NO diacritic at all is not a control (§4-0 direction 3).
  · Body type and Argument type are different sizes — never mix them on one
    sheet. Argument type is about half body size, so it needs its own smaller
    source box (~115x82) to reach the same magnification.
  · If a tile is ambiguous, WIDEN to the whole word (--box 260x150); do not
    zoom further in. The discriminator is the ‹e›'s terminal sweeping down INTO
    the letter versus the ring sitting detached, and that is invisible once the
    letter is cropped away.

⚠ A site whose mark cannot be located is REPORTED, never silently dropped.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kxii_marks as km  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:/Projects/Hexapla-releases")


def resolve(site):
    """-> [(image, (cx, cy), label), ...] one per mark found."""
    img = site["image"]
    path = img if Path(img).is_absolute() else str(ROOT / img)
    if "box" in site:
        x0, y0, x1, y1 = site["box"]
        word = (x0, y0, x1, y1)
        hits = [word]
    else:
        found = km.find_word(path, site["find"])
        if not found:
            return [], "NO TSV MATCH for %r" % site["find"]
        hits = [t[1:5] for t in found]
        if site.get("nth") is not None:
            n = site["nth"]
            if n >= len(hits):
                return [], "nth=%d but only %d match(es)" % (n, len(hits))
            hits = [hits[n]]
    out = []
    for wi, wordbox in enumerate(hits):
        marks, err = km.find_marks(path, wordbox)
        if not marks:
            out.append((path, None, site["label"], err or "no mark found"))
            continue
        for mi, mb in enumerate(marks):
            cx = (mb[0] + mb[2]) // 2
            cy = (mb[1] + mb[3]) // 2
            tag = site["label"]
            if len(hits) > 1:
                tag += "@%d" % (wi + 1)
            if len(marks) > 1:
                tag += "#%d" % (mi + 1)
            out.append((path, (cx, cy), tag, None))
    return out, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--box", default="150x105",
                    help="FIXED source window WxH (body type 150x105, "
                         "argument type 115x82, whole-word 260x150)")
    ap.add_argument("--tile-h", type=int, default=1000)
    ap.add_argument("--cols", type=int, default=4)
    args = ap.parse_args()

    bw, bh = (int(v) for v in args.box.lower().split("x"))
    sites = json.loads(Path(args.sites).read_text(encoding="utf-8"))

    tiles, problems = [], []
    for s in sites:
        got, err = resolve(s)
        if err:
            problems.append("%s: %s" % (s["label"], err))
            continue
        for path, centre, label, perr in got:
            if centre is None:
                problems.append("%s: %s" % (label, perr))
                continue
            im = Image.open(path).convert("L")
            W, H = im.size
            cx, cy = centre
            x0 = max(0, min(W - bw, cx - bw // 2))
            y0 = max(0, min(H - bh, cy - bh // 2))
            tiles.append((im.crop((x0, y0, x0 + bw, y0 + bh)), label))

    if problems:
        print("⚠ %d SITE(S) NOT PLACED - reported, never silently skipped:"
              % len(problems))
        for p in problems:
            print("   " + p)
    if not tiles:
        raise SystemExit("no tiles produced")

    scale = args.tile_h / float(bh)
    tw, th = int(bw * scale), args.tile_h
    label_h = 34
    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    pad = 8
    sheet = Image.new("L", (cols * (tw + pad) + pad,
                            rows * (th + label_h + pad) + pad), 255)
    dr = ImageDraw.Draw(sheet)
    for i, (crop, label) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + label_h + pad)
        sheet.paste(crop.resize((tw, th), Image.LANCZOS), (x, y))
        dr.rectangle([x, y, x + tw, y + th], outline=0)
        dr.text((x + 4, y + th + 8), label, fill=0)
    sheet.save(args.out)
    print("wrote %s  %d tile(s), source box %dx%d, magnification %.1fx"
          % (args.out, len(tiles), bw, bh, scale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
