#!/usr/bin/env python
"""
thorlaks_woodcuts.py - find the Þorláksbiblía 1644 woodcut initials on the
v3 scans of the MERGED books, address the chapter-opening ones by structure,
and cut them out as grey+alpha PNGs (0 model cost). The Karl XII twin is
kxii_initials_detect/assign/crop; this is the same idea for the print whose
books we have already read (owner 2026-10-05: «get these woodcuts in the
already-done chapters for free with a tool»).

    python tools/thorlaks_woodcuts.py                         # dry run: per-book table
    python tools/thorlaks_woodcuts.py --book john -v          # every detection
    python tools/thorlaks_woodcuts.py --apply                 # write crops + sheets
    python tools/thorlaks_woodcuts.py --selftest

TWO SIZES (measured 2026-10-05 at ZOOM 3, text line ~11-12 px)
    BIG   ~115-125 x 125-140 px (~10-11 lines): opens a chapter = verse 1.
    SMALL ~40-50 x 50-60 px (~4-5 lines tall as one inked block, a 2-line
          drop cap at the text block's LEFT EDGE): opens a paragraph inside a
          chapter (Rev p234, the owner). Its VERSE is not derivable from
          geometry: the merged text records almost none of them (Matthew 1,
          Mark 0, Romans 0 tags). They are detected, placed in their chapter
          (between the big anchors) and written to the plan UNADDRESSED.

ADDRESSING (big only)
    Pages of a book = the idx ranges of the parts its merged file names in
    its appendix (`###### from <book>_pA[-B].md`). The k-th big block in
    reading order (page idx, then y) is chapter k, verse 1 - ONLY when the
    book's big count equals its chapter count. Any other book is COUNT and
    nothing in it is addressed (a preface woodcut or a shared first/last page
    shifts every address after it; never guessed).

OUTPUT (--apply) into --out (default _work/_scratch/thor_woodcuts):
    plan.json         every detection, its book/page/box/size class/address
    big/<book>_<c>_1.png, small/<book>_p<idx>_<n>.png   grey+alpha, ZOOM_CUT
    sheet_NN.png + sheet_key.tsv   cells C1..Cn only (<= 1.15 MP) for ONE
                                   crop-check look before anything ships.
    Nothing here touches app assets; build_woodcut_assets.py does that, and
    the Þorláksbiblía is not a shipped translation yet.

CONTROL
    --selftest: a count-mismatched book addresses nothing, a matched one
    addresses k -> chapter k. HEXAPLA_WOODCUT_NOGATE=1 drops the count gate,
    so the selftest must fail.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kxii_initials_detect import components  # noqa: E402
from kxii_initials_crop import sheets, to_alpha  # noqa: E402

DATA = r"C:/Projects/Hexapla-releases"
RES = os.path.join(DATA, "research")
PDF = os.path.join(RES, "thorlaks_v3.pdf")
ZOOM = 3.0
ZOOM_CUT = 6.0
INK = 110
BIG_LH = 8.0               # big: height >= this many text-line heights
SMALL_LH = (3.4, 6.0)        # small: in this band AND at the left edge
EDGE_LH = 2.5                # small: x0 within this many lh of the text left
PAD = 0.06

BOOK_IDX = {  # 0-based KJV order, as initials.json / woodcuts.json
    "matthew": 39, "mark": 40, "luke": 41, "john": 42, "acts": 43, "romans": 44,
    "1corinthians": 45, "2cor": 46, "galatians": 47, "ephesians": 48,
    "philippians": 49, "colossians": 50, "1thessalonians": 51,
    "2thessalonians": 52, "1timothy": 53, "2timothy": 54, "titus": 55,
    "philemon": 56, "hebrews": 57, "james": 58, "1peter": 59, "2peter": 60,
    "1john": 61, "2john": 62, "3john": 63, "jude": 64, "revelation": 65}

CH = re.compile(r"^##\s+(.+?)\s+(\d{1,3})\s*$")
FROM = re.compile(r"^######\s+from\s+\S+?_p(\d+)(?:-(\d+))?\.md")


def book_info(key):
    """-> (chapter count, sorted page idxs) from the merged book file."""
    chs, pages = set(), set()
    body = True
    for ln in io.open(os.path.join(RES, "thorlaks_%s.md" % key), encoding="utf-8"):
        s = ln.strip()
        if s.startswith("# Appendix"):
            body = False
        if body:
            m = CH.match(s)
            if m:
                chs.add(int(m.group(2)))
        else:
            m = FROM.match(s)
            if m:
                a = int(m.group(1))
                pages.update(range(a, int(m.group(2) or a) + 1))
    return len(chs), sorted(pages)


def detect(doc, idx):
    pix = doc[idx].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), colorspace=fitz.csGRAY)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
    comps = components(g < INK)
    small = [c for c in comps if 6 <= c[3] - c[1] <= 80 and c[4] > 20]
    if not small:
        return 0, []
    lh = float(np.median([c[3] - c[1] for c in small]))
    # text left = median over text rows of the row's leftmost letter
    rows = {}
    for c in small:
        r = int(c[1] // max(lh, 1))
        rows[r] = min(rows.get(r, 1e9), c[0])
    left = float(np.median(list(rows.values())))
    out = []
    for (x0, y0, x1, y1, n) in comps:
        w, h = x1 - x0, y1 - y0
        if h < SMALL_LH[0] * lh or not (0.5 <= w / h <= 2.0) or n / (w * h) < 0.2 \
                or h > pix.height * 0.6:
            continue
        if h >= BIG_LH * lh:
            if w / h > 1.6:      # tailpiece ornament (Mark p49, Luke p79: ~375 x 199)
                continue
            out.append({"size": "big", "x": x0, "y": y0, "w": w, "h": h})
        elif h <= SMALL_LH[1] * lh and abs(x0 - left) <= EDGE_LH * lh:
            out.append({"size": "small", "x": x0, "y": y0, "w": w, "h": h})
    out.sort(key=lambda d: (d["y"], d["x"]))
    return lh, out


def address(dets, nch):
    """Big detections in reading order -> chapter k verse 1, gated on count.
    Smalls get the chapter of the last big above them (or None)."""
    big = [d for d in dets if d["size"] == "big"]
    gate = len(big) == nch or os.environ.get("HEXAPLA_WOODCUT_NOGATE") == "1"
    k = 0
    for d in dets:
        if d["size"] == "big":
            k += 1
            d["addr"] = "%d:1" % k if gate and k <= nch else None
        else:
            d["chapter"] = k if gate and k else None
    return gate, len(big)


def selftest():
    def mk(seq):
        return [{"size": s} for s in seq]
    a = mk(["big", "small", "big", "small", "small"])
    g1, _ = address(a, 2)
    b = mk(["big", "big", "big"])
    g2, _ = address(b, 2)
    ok = g1 and [d.get("addr") for d in a if d["size"] == "big"] == ["1:1", "2:1"] \
        and a[3]["chapter"] == 2 and not g2 and all(d["addr"] is None for d in b)
    print("selftest", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="merged-file key, e.g. john, 2cor")
    ap.add_argument("--out", default=os.path.join(DATA, "_work", "_scratch", "thor_woodcuts"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    keys = [a.book] if a.book else sorted(
        k for k in (os.path.basename(p)[9:-3] for p in glob.glob(os.path.join(RES, "thorlaks_*.md")))
        if k in BOOK_IDX)
    doc = fitz.open(PDF)
    cache = {}
    plan = {}
    for key in keys:
        nch, pages = book_info(key)
        if not pages:
            print("%-15s no page list in its appendix - skipped" % key)
            continue
        dets = []
        for i in pages:
            if i not in cache:
                cache[i] = detect(doc, i)
            lh, ds = cache[i]
            for d in ds:
                dets.append(dict(d, idx=i, lh=lh))
        gate, nbig = address(dets, nch)
        nsmall = sum(d["size"] == "small" for d in dets)
        shared = [i for i in pages if any(i in plan[k2]["pages"] for k2 in plan)]
        print("%-15s idx %3d-%3d  chapters %3d  big %3d  small %3d  %s%s" % (
            key, pages[0], pages[-1], nch, nbig, nsmall, "AGREE" if gate else "COUNT",
            "  shared pages %s" % shared if shared else ""))
        if a.v or not gate:
            for i in pages:
                bs = [(d["y"], d["w"], d["h"]) for d in dets if d["idx"] == i and d["size"] == "big"]
                if bs or a.v:
                    print("      p%-4d big %s  small %d" % (i, bs, sum(
                        1 for d in dets if d["idx"] == i and d["size"] == "small")))
        plan[key] = {"book": BOOK_IDX[key], "chapters": nch, "pages": pages,
                     "status": "AGREE" if gate else "COUNT", "dets": dets}
    if not a.apply:
        print("dry run - nothing written (--apply writes crops, sheets, plan.json to %s)" % a.out)
        return 0
    os.makedirs(os.path.join(a.out, "big"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "small"), exist_ok=True)
    items = []
    for key, p in plan.items():
        n_on = {}
        for d in p["dets"]:
            s = ZOOM_CUT / ZOOM
            pad = PAD * d["h"]
            r = fitz.Rect((d["x"] - pad) / ZOOM, (d["y"] - pad) / ZOOM,
                          (d["x"] + d["w"] + pad) / ZOOM, (d["y"] + d["h"] + pad) / ZOOM)
            pix = doc[d["idx"]].get_pixmap(matrix=fitz.Matrix(ZOOM_CUT, ZOOM_CUT), clip=r,
                                           colorspace=fitz.csGRAY)
            g = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            if d["size"] == "big" and d.get("addr"):
                fn = "big/%s_%s.png" % (key, d["addr"].replace(":", "_"))
            else:
                n_on[d["idx"]] = n_on.get(d["idx"], 0) + 1
                fn = "%s/%s_p%d_%d.png" % (d["size"], key, d["idx"], n_on[d["idx"]])
            to_alpha(g).save(os.path.join(a.out, fn))
            d["file"] = fn
            d["scale"] = s
            items.append((fn, g))
    n = sheets(items, a.out)
    io.open(os.path.join(a.out, "plan.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(plan, ensure_ascii=False, indent=1))
    print("wrote %d crops, %d sheet(s), plan.json -> %s" % (len(items), n, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
