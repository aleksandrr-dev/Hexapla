#!/usr/bin/env python
"""
kxii_initials_crop.py - cut each assigned Karl XII 1703 initial out of its page
scan by INK, not by the detector's box (0 model cost), and build the contact
sheets for the ONE look that checks the cuts.

    python tools/kxii_initials_crop.py --rows assign_ruled.json --out DIR          # dry run: stats only
    python tools/kxii_initials_crop.py --rows assign_ruled.json --out DIR --apply  # write crops + sheets
    python tools/kxii_initials_crop.py --selftest

Rows come from `kxii_initials_assign.py --ruled ... --out` (slot, ch, 0-based v,
page, col, x, y, w, h, kind, status, grow_left).

METHOD
    Ink = grey < INK at full resolution inside the box grown by PAD x its
    height. Connected components (the detector's own union-find). The initial
    = every component that overlaps the detector box, plus every component
    lying wholly inside that union (the loose dots of a woodcut's ground).
    ⛔ A union that grows past GROW x the box in either dimension has swallowed
    text or a rule: the box itself is cut and the row is flagged GREW - never
    silently shipped at the wider size. GREW-OK (grew_ok()): the detector boxed
    PART of the block - drop thin rules, regrow the window until nothing is
    clipped, keep the union if roughly square and <= GROW_MAX x the box
    (selftest «grew-ok», control HEXAPLA_NO_GREWOK=1). 2026-09-29: 6 of the 10
    GREW rows recover; 4 keep growing into neighbours and stay GREW (box cut).
    Both flags go to the contact-sheet look.
    grow_left rows (RULED-V1FRAG: the box is a flourish at the FOOT of the v1
    woodcut, which sits left of and above it): the search window extends left
    to the column edge and up by 3 box heights, and the initial is the TALLEST
    component there whose bottom is level with the box.

OUTPUT (--apply)
    DIR/<slot>_<ch>_<v1-based>.png   grey+alpha: black ink, alpha = ink darkness
                                     (so it sits on any page colour; the dark
                                     theme inverts it in CSS/Compose)
    DIR/crops.json                   row + crop box + flags
    DIR/sheet_NN.png, DIR/sheet_key.tsv   cells labelled C1..Cn only
                                     (never book/verse on a look's sheet), each
                                     sheet <= 1.15 MP
"""
import argparse
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kxii_initials_detect import PAGES, components  # noqa: E402

INK = 135
PAD = 0.35
GROW = 1.6
GROW_MAX = 2.0          # GREW-OK ceiling per dimension
ASPECT = (0.55, 1.45)   # GREW-OK: union width / height
RULE_THIN, RULE_RATIO = 12, 8   # GREW-OK: a component this thin and long is a rule
MAX_PX = 1150000
CELL, PER_ROW = 112, 9


def cut(im, r):
    """-> (x0, y0, x1, y1), flags"""
    W, H = im.size
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    p = int(PAD * h)
    if r.get("grow_left"):
        rx0, ry0 = max(0, x - 4 * w), max(0, y - 3 * h)
    else:
        rx0, ry0 = max(0, x - p), max(0, y - p)
    rx1, ry1 = min(W, x + w + p), min(H, y + h + p)
    a = np.asarray(im.crop((rx0, ry0, rx1, ry1))) < INK
    comps = [(c[0] + rx0, c[1] + ry0, c[2] + rx0, c[3] + ry0, c[4]) for c in components(a)]
    flags = []
    if r.get("grow_left"):
        level = [c for c in comps if abs(c[3] - (y + h)) <= h // 2 and c[3] - c[1] >= 1.5 * h and c[0] < x]
        if not level:
            return (x, y, x + w, y + h), ["NOBIG"]
        big = max(level, key=lambda c: c[3] - c[1])
        core = (big[0], big[1], max(big[2], x + w), max(big[3], y + h))
        w, h = core[2] - core[0], core[3] - core[1]
        x, y = core[0], core[1]
    hit = [c for c in comps if c[0] < x + w and c[2] > x and c[1] < y + h and c[3] > y]
    if not hit:
        return (x, y, x + w, y + h), ["NOINK"]
    if os.environ.get("HEXAPLA_CROP_BAD") == "1":
        hit, flags = comps, ["BAD"]     # control: every component in the window, no GREW guard
    u = [min(c[0] for c in hit), min(c[1] for c in hit), max(c[2] for c in hit), max(c[3] for c in hit)]
    uw, uh = u[2] - u[0], u[3] - u[1]
    if not flags and (uw > GROW * w or uh > GROW * h):
        tag = "%dx%d>%dx%d" % (uw, uh, w, h)
        if os.environ.get("HEXAPLA_NO_GREWOK") != "1":
            v = grew_ok(im, (x, y, w, h))
            if v:
                return v, ["GREW-OK %dx%d>%dx%d" % (v[2] - v[0], v[3] - v[1], w, h)]
        return (x, y, x + w, y + h), ["GREW " + tag]
    return tuple(u), flags


def is_rule(c):
    """a column/section rule: thin and long (never part of a woodcut's block)."""
    cw, ch = c[2] - c[0], c[3] - c[1]
    return min(cw, ch) <= RULE_THIN and max(cw, ch) >= RULE_RATIO * min(cw, ch)


def grew_ok(im, box):
    """GREW-OK: the detector often boxes PART of a woodcut (70_4_7: 32x66 of a
    wider letter), and a column rule touching the block drags the union along.
    Only for a row that GREW (healthy rows stay byte-identical): drop thin
    rules, then re-cut with the window regrown around the union until no
    component overlapping the ORIGINAL box is clipped by the window edge. The
    union is kept only when it is roughly square and grew <= GROW_MAX in each
    dimension - a text line joined to the letter fails both. Flagged GREW-OK
    either way: the contact-sheet look must see every one. -> box or None"""
    W, H = im.size
    x, y, w, h = box
    u = [x, y, x + w, y + h]
    for _ in range(4):
        p = int(PAD * max(u[3] - u[1], h))
        rx0, ry0 = max(0, u[0] - p), max(0, u[1] - p)
        rx1, ry1 = min(W, u[2] + p), min(H, u[3] + p)
        a = np.asarray(im.crop((rx0, ry0, rx1, ry1))) < INK
        comps = [(c[0] + rx0, c[1] + ry0, c[2] + rx0, c[3] + ry0) for c in components(a)]
        hit = [c for c in comps if c[0] < x + w and c[2] > x and c[1] < y + h and c[3] > y and not is_rule(c)]
        if not hit:
            return None
        u = [min(c[0] for c in hit), min(c[1] for c in hit), max(c[2] for c in hit), max(c[3] for c in hit)]
        uw, uh = u[2] - u[0], u[3] - u[1]
        if uw > GROW_MAX * w or uh > GROW_MAX * h:
            return None
        clipped = (u[0] <= rx0 and rx0 > 0) or (u[1] <= ry0 and ry0 > 0) or \
                  (u[2] >= rx1 and rx1 < W) or (u[3] >= ry1 and ry1 < H)
        if not clipped:
            return tuple(u) if ASPECT[0] <= uw / float(uh) <= ASPECT[1] else None
    return None


def to_alpha(g):
    """grey crop -> LA image: black, alpha from darkness (paper -> 0)."""
    a = np.asarray(g).astype(np.float32)
    paper = np.percentile(a, 90)
    alpha = np.clip((paper - a) / max(1.0, paper - a.min()) * 255.0 * 1.15, 0, 255).astype(np.uint8)
    return Image.merge("LA", (Image.new("L", g.size, 0), Image.fromarray(alpha)))


def sheets(items, out):
    font = ImageFont.load_default()
    rows_per = MAX_PX // (CELL * PER_ROW) // CELL
    per = rows_per * PER_ROW
    key = io.open(os.path.join(out, "sheet_key.tsv"), "w", encoding="utf-8", newline="\n")
    key.write("cell\tsheet\tfile\n")
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        nr = (len(chunk) + PER_ROW - 1) // PER_ROW
        sh = Image.new("L", (CELL * PER_ROW, CELL * nr), 255)
        d = ImageDraw.Draw(sh)
        for k, (fn, g) in enumerate(chunk):
            n = si + k + 1
            t = g.copy()
            t.thumbnail((CELL - 6, CELL - 16))
            cx, cy = (k % PER_ROW) * CELL, (k // PER_ROW) * CELL
            sh.paste(t, (cx + 3, cy + 13))
            d.text((cx + 2, cy + 1), "C%d" % n, fill=0, font=font)
            d.rectangle((cx, cy, cx + CELL - 1, cy + CELL - 1), outline=170)
            key.write("C%d\t%d\t%s\n" % (n, si // per + 1, fn))
        assert sh.size[0] * sh.size[1] <= MAX_PX
        sh.save(os.path.join(out, "sheet_%02d.png" % (si // per + 1)))
    key.close()
    return (len(items) + per - 1) // per


def selftest():
    """Synthetic page: a 60x60 initial (two parts: a letter and a detached
    frame dot touching the box) next to a text line starting 20 px right.
    The cut must hold the initial and NOT the text. Control: HEXAPLA_CROP_BAD=1
    takes every component in the search window (the text too) with no GREW
    guard, so the test must fail."""
    a = np.full((400, 600), 255, np.uint8)
    a[100:160, 100:160] = 0            # initial block
    a[98:102, 150:156] = 0             # a dot poking out of the top
    a[110:120, 172:190] = 0            # text glyph, separate component
    a[125:135, 175:560] = 0            # a text line running right
    im = Image.fromarray(a)
    box, flags = cut(im, {"x": 100, "y": 100, "w": 60, "h": 60})
    ok = box == (100, 98, 160, 160) and not flags
    print("SELFTEST crop %s %s %s" % ("PASS" if ok else "FAIL", box, flags))
    # GREW-OK: the detector boxed a column rule plus the LEFT PART of a 56x60
    # woodcut (one component, clipped by the first window), and a text line
    # starts 30 px on. The whole letter must come
    # back (GREW-OK) without the rule or the text.
    # Control: HEXAPLA_NO_GREWOK=1 falls back to the part box -> FAIL.
    b = np.full((400, 600), 255, np.uint8)
    b[100:160, 100:156] = 0            # the woodcut
    b[20:380, 94:97] = 0               # column rule, 3 px off it, inside the box
    b[110:120, 192:560] = 0            # text line
    box2, flags2 = cut(Image.fromarray(b), {"x": 94, "y": 100, "w": 30, "h": 60})
    ok2 = box2 == (100, 100, 156, 160) and flags2 and flags2[0].startswith("GREW-OK")
    print("SELFTEST grew-ok %s %s %s" % ("PASS" if ok2 else "FAIL", box2, flags2))
    # and a part box whose letter is joined to a text line stays a plain GREW
    c = b.copy()
    c[130:140, 156:560] = 0            # text line touching the letter
    box3, flags3 = cut(Image.fromarray(c), {"x": 94, "y": 100, "w": 30, "h": 60})
    ok3 = box3 == (94, 100, 124, 160) and flags3 and flags3[0].startswith("GREW ")
    print("SELFTEST grew-text %s %s %s" % ("PASS" if ok3 else "FAIL", box3, flags3))
    return 0 if ok and ok2 and ok3 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows")
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    g = ap.parse_args()
    if g.selftest:
        return selftest()
    if not (g.rows and g.out):
        ap.error("--rows and --out are required")
    rows = json.load(io.open(g.rows, encoding="utf-8"))
    # a chapter-SUMMARY initial is no verse initial: never cut, never shipped
    rows = [r for r in rows if r["kind"] in ("opening", "mid")]
    # an opening still LONE-SMALL is (so far always) the summary's initial with
    # the v1 woodcut unfound; an ESTIMATE row has no ruled verse
    open_q = [r for r in rows if r["status"] in ("LONE-SMALL", "ESTIMATE") or r["status"].startswith("COUNT")]
    for r in open_q:
        print("   UNRESOLVED %-10s slot %d ch%d p%04d %s y=%d" % (r["status"], r["slot"], r["ch"], r["page"], r["col"], r["y"]))
    cache, res, items, nflag = {}, [], [], {}
    for r in sorted(rows, key=lambda r: (r["page"], r["col"], r["y"])):
        if r["page"] not in cache:
            cache = {r["page"]: Image.open(os.path.join(PAGES, "p%04d.jpg" % r["page"])).convert("L")}
        im = cache[r["page"]]
        box, flags = cut(im, r)
        fn = "%d_%d_%d.png" % (r["slot"], r["ch"], r["v"] + 1)
        res.append(dict(r, crop=list(box), flags=flags, file=fn))
        for f in flags:
            nflag[f.split()[0]] = nflag.get(f.split()[0], 0) + 1
        items.append((fn, im.crop(box)))
    dup = len(items) - len({fn for fn, _ in items})
    print("rows %d  flagged %s  duplicate addresses %d" % (len(res), nflag or "none", dup))
    for x in res:
        if x["flags"]:
            print("   %-12s p%04d %s y=%d %s" % (x["file"], x["page"], x["col"], x["y"], " ".join(x["flags"])))
    if not g.apply:
        print("DRY RUN - nothing written; --apply writes %d crops + sheets to %s (unresolved %d)" % (
            len(res), g.out, len(open_q)))
        return 1 if dup or open_q else 0
    if dup or open_q:
        print("[X] %d duplicate addresses, %d unresolved rows - refusing to write" % (dup, len(open_q)))
        return 1
    os.makedirs(g.out, exist_ok=True)
    for fn, c in items:
        to_alpha(c).save(os.path.join(g.out, fn), optimize=True)
    with io.open(os.path.join(g.out, "crops.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=0)
    n = sheets(items, g.out)
    print("wrote %d crops, %d sheets to %s" % (len(items), n, g.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
