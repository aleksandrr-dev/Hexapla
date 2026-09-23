#!/usr/bin/env python
"""
kxii_sites.py - resolve DISPUTED diff sites to exact diacritic crop boxes.

    python tools/kxii_sites.py --report research/kxii_witness_wisdom.md \
        --chunk research/karlxii_wisdom.md --name "Wisdom of Solomon" \
        --strips research/_strips_kxii/wisdom --out _kxii_cache/marks.json

## WHY THIS EXISTS, AND WHAT IT FIXES

A first attempt located sites by matching the disputed WORD against the OCR of
every strip. That is wrong: a lexeme like `låter` occurs in many verses, most of
them never disputed, so the boxes it produced were a mix of real sites and
irrelevant correct ones - and a blind adjudication over them is meaningless.

**A disputed site is a (chapter, verse, word) triple, not a word.** So this
anchors on the VERSE: it folds our verse text, slides it over each strip's OCR
token stream to find the best-matching window, and then picks the token at the
disputed word's position within that window. Tesseract is wrong about the
characters and right about the order, which is all the anchor needs - the same
"wrong text, right geometry" trick tesstrain_prep.py uses for line alignment.

⚠ Every box is emitted with the match score that produced it. A low score means
the anchor is not trustworthy and the site must be found by hand; it does NOT
mean "crop it anyway". Silent mislocation is the failure mode that makes a
blind adjudication worse than no adjudication.
"""
import argparse
import difflib
import glob
import io
import json
import os
import re
import sys

import numpy as np
from PIL import Image

FOLD = {"à": "a", "â": "a", "ä": "a", "å": "a", "á": "a", "ô": "o", "ö": "o",
        "ó": "o", "ſ": "s", "ß": "ss", "é": "e", "è": "e", "ê": "e"}


def fold(s):
    s = s.lower()
    s = "".join(FOLD.get(c, c) for c in s)
    return re.sub(r"[^a-z0-9]", "", s)


def load_tsv(path):
    rows = []
    for line in io.open(path, encoding="utf-8", errors="replace").read().splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        try:
            rows.append({"text": f[11].strip(), "left": int(f[6]), "top": int(f[7]),
                         "width": int(f[8]), "height": int(f[9])})
        except ValueError:
            continue
    return rows


def parse_report(path):
    """-> [(ch, verse, ours, theirs)] for the a-ring/a-umlaut class only."""
    out = []
    ch = v = None
    for line in io.open(path, encoding="utf-8"):
        m = re.match(r"^- \*\*(\d+):(\d+)\*\*", line)
        if m:
            ch, v = int(m.group(1)), int(m.group(2))
            continue
        m2 = re.search(r"ours='(.*?)' theirs='(.*?)'", line)
        if m2 and ch:
            a, b = m2.group(1), m2.group(2)
            if a and b and len(a) == len(b):
                d = [(x, y) for x, y in zip(a, b) if x != y]
                if d and all({x, y} <= {"å", "ä"} for x, y in d):
                    out.append((ch, v, a, b))
    return out


def parse_chunk(path, name):
    out, cur, vn = {}, None, None
    head = re.compile(r"^##\s+%s\s+(\d+)\s*$" % re.escape(name))
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = head.match(line)
        if m:
            cur, vn = int(m.group(1)), None
            out.setdefault(cur, {})
            continue
        if line.startswith("#"):
            cur = vn = None
            continue
        if cur is None:
            continue
        vm = re.match(r"^(\d+)\s+(.*)$", line)
        if vm:
            vn = int(vm.group(1))
            out[cur][vn] = vm.group(2).strip()
        elif vn is not None and line.strip() and line.strip()[0] not in "·⚠✅★▶⛔|-":
            out[cur][vn] += " " + line.strip()
    return out


def anchor(verse_words, strip_tokens):
    """Best window of strip tokens matching the verse. -> (score, start)."""
    n = len(verse_words)
    if n == 0 or len(strip_tokens) < 2:
        return 0.0, -1
    best = (0.0, -1)
    folded = [t["f"] for t in strip_tokens]
    for i in range(0, max(1, len(folded) - n + 1)):
        win = folded[i:i + n]
        r = difflib.SequenceMatcher(a=verse_words, b=win, autojunk=False).ratio()
        if r > best[0]:
            best = (r, i)
    return best


def tighten(img, box):
    """Shrink a word box onto its diacritic. -> box or None."""
    x0, y0, x1, y1 = [max(0, int(v)) for v in box]
    sub = np.array(img.convert("L"))[y0:y1, x0:x1] < 140
    if sub.size == 0 or not sub.any():
        return None
    h, w = sub.shape
    lab = np.zeros((h, w), np.int32)
    cur, comps = 0, []
    for yy in range(h):
        for xx in range(w):
            if sub[yy, xx] and lab[yy, xx] == 0:
                cur += 1
                st, pix = [(yy, xx)], []
                lab[yy, xx] = cur
                while st:
                    cy, cx = st.pop()
                    pix.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and sub[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            st.append((ny, nx))
                comps.append(pix)
    best = None
    for pix in comps:
        ys = [p[0] for p in pix]
        xs = [p[1] for p in pix]
        cw, chh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        if len(pix) < 30 or cw > 0.45 * w or chh > 0.6 * h:
            continue
        if min(xs) <= 1 or max(xs) >= w - 2:      # touches edge: column rule
            continue
        if not (0.45 <= chh / float(cw) <= 2.6):  # stem or bar, not a mark
            continue
        if min(ys) > 0.5 * h:                     # must sit in the upper half
            continue
        if best is None or min(ys) < best[0]:
            best = (min(ys), min(xs), min(ys), max(xs), max(ys))
    if not best:
        return None
    _, mx0, my0, mx1, my1 = best
    p = 7
    return [x0 + mx0 - p, y0 + my0 - p, x0 + mx1 + p + 1, y0 + my1 + p + 1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True)
    ap.add_argument("--chunk", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--strips", required=True)
    ap.add_argument("--tsv", default=r"C:\Projects\Hexapla-releases\research\_ocr_kxii\tsv")
    ap.add_argument("--min-score", type=float, default=0.45)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    sites = parse_report(args.report)
    ours = parse_chunk(args.chunk, args.name)
    strips = sorted(glob.glob(os.path.join(args.strips, "*.png")))
    cache = {}
    for s in strips:
        p = os.path.join(args.tsv, os.path.splitext(os.path.basename(s))[0] + ".tsv")
        if os.path.isfile(p):
            toks = load_tsv(p)
            for t in toks:
                t["f"] = fold(t["text"])
            cache[s] = [t for t in toks if t["f"]]

    out, weak = [], []
    for ch, v, a, b in sites:
        text = ours.get(ch, {}).get(v)
        if not text:
            continue
        vw = [fold(w) for w in text.split() if fold(w)]
        target = fold(a)
        try:
            pos = vw.index(target)
        except ValueError:
            pos = next((i for i, w in enumerate(vw) if w == target), None)
            if pos is None:
                weak.append((ch, v, a, "word not in verse after folding"))
                continue
        best = (0.0, None, -1)
        for s, toks in cache.items():
            r, i = anchor(vw, toks)
            if r > best[0]:
                best = (r, s, i)
        score, strip, start = best
        if score < args.min_score or strip is None or start < 0:
            weak.append((ch, v, a, "anchor score %.2f" % score))
            continue
        toks = cache[strip]
        idx = start + pos
        if idx >= len(toks):
            weak.append((ch, v, a, "index past strip"))
            continue
        t = toks[idx]
        wbox = [t["left"], t["top"], t["left"] + t["width"],
                t["top"] + int(t["height"] * 0.62)]
        mark = tighten(Image.open(strip), wbox)
        if not mark:
            weak.append((ch, v, a, "no mark component isolated"))
            continue
        out.append({"ch": ch, "v": v, "ours": a, "theirs": b,
                    "strip": os.path.basename(strip), "box": mark,
                    "score": round(score, 3), "ocr": t["text"]})

    json.dump(out, io.open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("resolved %d/%d sites -> %s" % (len(out), len(sites), args.out))
    for r in out:
        print("  %d:%-3d %-12s %-14s score=%.2f box=%s" %
              (r["ch"], r["v"], r["ours"], r["strip"], r["score"], r["box"]))
    if weak:
        print("\nUNRESOLVED (find by hand, do NOT guess):")
        for ch, v, a, why in weak:
            print("  %d:%-3d %-12s %s" % (ch, v, a, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
