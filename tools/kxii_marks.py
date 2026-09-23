#!/usr/bin/env python
"""
kxii_marks.py - find the DIACRITIC MARKS in a word automatically, and emit
tight crop boxes for a contact sheet. Zero model tokens.

## WHY THIS EXISTS

The ae/ring adjudication loop was:
    TSV word box -> ESTIMATE which character carries the mark -> guess its
    pixel offset -> crop -> read the sheet -> discover the box missed -> recrop

On 2026-08-19 (Wisdom 12) **six of twelve first-pass crops missed the mark**,
and every one of them rendered a clean, plausible-looking tile - letter bodies
with the diacritic just out of frame. Two earlier failures the same day were
the same class: one crop CLIPPED a mark at the tile edge and still looked
decidable, and one sheet framed a `g` instead of the vowel. Each miss costs a
full image read, which is the single most expensive thing in this campaign.

The estimate was never necessary. The mark is the ink that FLOATS above the
letter bodies with a white gap under it, and that is a measurement, not a
judgement call. This tool makes it.

## WHAT IT DOES

Given a strip and a word box (or a diacritic-blind regex resolved against the
cached TSV), it:
  1. binarises the word region (Otsu),
  2. finds the BODY BAND - the dense x-height rows where the letter bodies sit,
  3. segments the ink ABOVE that band into column runs,
  4. keeps only runs separated from the body by an all-white row - that gap is
     what distinguishes a floating mark from an ascender (l, h, b, k, t),
  5. emits one tight box per mark, padded, extended DOWN to include the letter
     underneath so the tile still shows the same-word context the method wants.

## USAGE

    # explicit word box
    python tools/kxii_marks.py strip.png --word 1221,1162,1498,1261 --label wardig

    # or let it find the word first, diacritic-blind, via the cached TSV
    python tools/kxii_marks.py strip.png --find "w[a]rdig" --label wardig

    # many sites, possibly across strips, straight into one sheet
    python tools/kxii_marks.py --sites sites.json --json boxes.json
    python tools/contact_sheet.py --boxes boxes.json out.png --tile-h 880

`sites.json` is [{"image": "...", "find": "l[a]t", "label": "lat_v10"}, ...];
"box" may be given instead of "find".

## WHAT IT DOES NOT DO

It LOCATES. It never decides ring vs <e>. The crop it emits still has to be
read at 9x or better, beside a ring control and an <e> control, by the rules in
the scan-transcription skill. It does remove the failure mode where the thing
you are reading is not in the picture.

⚠ A word whose mark it cannot find is REPORTED, not silently skipped - a
missing site must never look like a site with nothing wrong.
"""
import argparse
import csv
import io
import json
import os
import re
import sys

import numpy as np
from PIL import Image

TSV_DIR = r"C:\Projects\Hexapla-releases\research\_ocr_kxii\tsv"
FOLD = {
    "\u00e0": "a", "\u00e2": "a", "\u00e4": "a", "\u00e5": "a", "\u00e1": "a",
    "\u00f4": "o", "\u00f6": "o", "\u00f3": "o", "\u00f2": "o",
    "\u00e8": "e", "\u00e9": "e", "\u00ea": "e", "\u00eb": "e",
    "\u00ec": "i", "\u00ed": "i", "\u00ee": "i", "\u00ef": "i",
    "\u017f": "s",
}


def fold(s):
    return "".join(FOLD.get(c, c) for c in s.lower())


def tsv_rows(image_path):
    """Word boxes AND line boxes from the cached Tesseract TSV.

    ⚠ THE LINE BOX IS THE WHOLE POINT. Two earlier versions of this tool tried
    to infer a word's vertical extent from the ink profile, and both walked
    straight into the neighbouring line: the interline "gap" is NOT white -
    descenders from the line above reach down into it (ink 4-8 px per row where
    the body runs 60-140). No single threshold separates them. Tesseract has
    already segmented the lines, so ask it instead of re-deriving it badly.
    """
    stem = os.path.splitext(os.path.basename(image_path))[0]
    path = os.path.join(TSV_DIR, stem + ".tsv")
    if not os.path.exists(path):
        return None, None
    words, lines = [], {}
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh, delimiter="	", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for row in rd:
            if len(row) < 12:
                continue
            try:
                lvl = int(row[0])
                x, y, w, h = (int(row[i]) for i in (6, 7, 8, 9))
            except ValueError:
                continue
            key = (row[2], row[3], row[4])
            if lvl == 4:
                lines[key] = (x, y, x + w, y + h)
            elif lvl == 5:
                txt = row[11].strip()
                if txt:
                    words.append({"text": txt, "box": (x, y, x + w, y + h),
                                  "key": key})
    return words, lines


def tsv_tokens(image_path):
    words, _ = tsv_rows(image_path)
    if words is None:
        return None
    return [(w["text"],) + w["box"] for w in words]


def line_for(image_path, box):
    """The Tesseract line box that best contains `box`."""
    _, lines = tsv_rows(image_path)
    if not lines:
        return None
    x0, y0, x1, y1 = box
    best, best_ov = None, 0
    for lb in lines.values():
        lx0, ly0, lx1, ly1 = lb
        if x1 <= lx0 or x0 >= lx1:
            continue
        ov = min(y1, ly1) - max(y0, ly0)
        if ov > best_ov:
            best, best_ov = lb, ov
    return best


def find_word(image_path, pattern):
    toks = tsv_tokens(image_path)
    if toks is None:
        raise SystemExit("no cached TSV for %s" % image_path)
    rx = re.compile(fold(pattern))
    return [t for t in toks if rx.search(fold(t[0]))]


def otsu(gray):
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    total = hist.sum()
    if total == 0:
        return 128
    omega = np.cumsum(hist)
    mu = np.cumsum(hist * np.arange(256))
    mu_t = mu[-1]
    denom = omega * (total - omega)
    denom[denom == 0] = 1e-9
    sigma_b = (mu_t * omega - total * mu) ** 2 / denom
    return int(np.argmax(sigma_b))


def find_marks(image_path, box, pad=10, min_run=3, min_ink=4, body_frac=0.55):
    """Return [(x0,y0,x1,y1), ...] for each floating diacritic in `box`.

    The vertical slab is the TESSERACT LINE BOX, not a guess - see tsv_rows.
    Within it: zero out full-width rules, find the first row where ink reaches
    body level and STAYS there (a mark's own crossbar can spike one row), treat
    everything above that as the mark zone, and keep only column runs separated
    from the body by an all-white row. That gap is what tells a floating mark
    from an ascender (l, h, b, k, t).
    """
    src = Image.open(image_path).convert("L")
    W, H = src.size
    x0, y0, x1, y1 = (int(v) for v in box)
    line = line_for(image_path, (x0, y0, x1, y1))
    if line is None:
        return [], "no Tesseract line box covers this word"
    ly0, ly1 = max(0, line[1] - 2), min(H, line[3] + 2)
    rx0, rx1 = max(0, x0 - 6), min(W, x1 + 6)
    slab = np.asarray(src.crop((rx0, ly0, rx1, ly1)))
    if slab.size == 0:
        return [], "empty region"

    thr = otsu(slab)
    ink = slab < thr
    width = ink.shape[1]
    prof = ink.sum(axis=1)
    prof = np.where(prof >= width * 0.95, 0, prof)  # rules/borders are not text
    if prof.max() == 0:
        return [], "no ink in line slab"
    cut = prof.max() * body_frac

    body_rel = None
    for i in range(len(prof) - 3):
        if prof[i] >= cut and prof[i + 1] >= cut and prof[i + 2] >= cut:
            body_rel = i
            break
    if body_rel is None or body_rel < 3:
        return [], "no separable zone above the body band"

    # PER-COLUMN float test. Testing whole column-runs was too strict: a mark
    # whose terminal touches its letter, or one sitting next to an ascender in
    # the same run, made min(gap)>0 and the site was rejected with a
    # confident-sounding reason. A column is "floating" if its upper ink stops
    # before the body band with white underneath; contiguous floating columns
    # ARE the mark, which also gives a tighter box than run-then-test did.
    floating = np.zeros(ink.shape[1], dtype=bool)
    for j in range(ink.shape[1]):
        u = ink[:body_rel, j]
        idx = np.where(u)[0]
        if idx.size == 0:
            continue
        last = int(idx[-1])
        if last >= body_rel - 1:
            continue                      # ink runs into the body -> ascender
        if not ink[last + 1:body_rel, j].any():
            floating[j] = True

    # MERGE nearby floating columns before calling them separate marks. A ring
    # at this resolution is ~30 px wide and the binarisation breaks it into two
    # or three column runs, which first showed up as 54 "marks" for 8 sites.
    span = max(4, int((ly1 - ly0) * 0.10))
    idx = np.where(floating)[0]
    for k in range(len(idx) - 1):
        if 1 < idx[k + 1] - idx[k] <= span:
            floating[idx[k]:idx[k + 1]] = True

    marks = []
    st = None
    for j in range(len(floating) + 1):
        on = j < len(floating) and floating[j]
        if on and st is None:
            st = j
        elif not on and st is not None:
            a, b = st, j - 1
            st = None
            if (b - a + 1) < min_run:
                continue
            up = ink[:body_rel, a:b + 1]
            if up.sum() < min_ink or (b - a + 1) < span * 0.6:
                continue
            rr = np.where(up.sum(axis=1) > 0)[0]
            if rr.size == 0:
                continue
            m_top = int(rr[0])
            by1 = ly0 + body_rel + int((len(prof) - body_rel) * 0.85)
            marks.append((max(0, rx0 + a - pad), max(0, ly0 + m_top - pad),
                          min(W, rx0 + b + 1 + pad), min(H, by1)))

    if not marks:
        return [], "no floating mark found (all upper ink connects to the body)"
    return marks, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="locate diacritic marks; emit crop boxes")
    ap.add_argument("image", nargs="?", help="strip png (omit when using --sites)")
    ap.add_argument("--word", help="explicit Tesseract word box x0,y0,x1,y1")
    ap.add_argument("--find", help="diacritic-blind regex resolved against the cached TSV")
    ap.add_argument("--label", default="site")
    ap.add_argument("--sites", help="JSON list of {image, find|box, label}")
    ap.add_argument("--json", help="write contact_sheet-ready boxes here")
    ap.add_argument("--pad", type=int, default=10)
    ap.add_argument("--nth", type=int, default=None,
                    help="keep only the Nth mark found in the word (1-based)")
    a = ap.parse_args(argv)

    if a.sites:
        sites = json.load(io.open(a.sites, encoding="utf-8"))
    else:
        if not a.image or not (a.word or a.find):
            ap.error("give an image plus --word or --find, or use --sites")
        sites = [{"image": a.image,
                  "box": a.word, "find": a.find, "label": a.label}]

    out, problems = [], []
    for s in sites:
        img = s["image"]
        label = s.get("label", "site")
        if s.get("box"):
            boxes = [tuple(int(v) for v in str(s["box"]).split(",")[:4])]
            words = [("(given)",) + boxes[0]]
        else:
            words = find_word(img, s["find"])
            if not words:
                problems.append("%s: NO TSV MATCH for %r" % (label, s["find"]))
                continue
        for wi, w in enumerate(words):
            wbox = w[1:5]
            marks, err = find_marks(img, wbox, pad=a.pad)
            if err:
                problems.append("%s [%s]: %s" % (label, w[0], err))
                continue
            keep = marks
            if a.nth is not None and 1 <= a.nth <= len(marks):
                keep = [marks[a.nth - 1]]
            for mi, m in enumerate(keep):
                tag = label
                if len(words) > 1:
                    tag += "@%d" % (wi + 1)
                if len(keep) > 1:
                    tag += "#%d" % (mi + 1)
                out.append({"image": img, "box": list(m), "label": tag})
                print("  %-26s %s  %d,%d,%d,%d" % (tag, os.path.basename(img), *m))

    if problems:
        print("\n⚠ %d SITE(S) NOT RESOLVED - these are reported, never skipped:"
              % len(problems), file=sys.stderr)
        for p in problems:
            print("   " + p, file=sys.stderr)

    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1))
        print("\nwrote %d box(es) -> %s" % (len(out), a.json))
    return 0 if out else 1


if __name__ == "__main__":
    sys.exit(main())
