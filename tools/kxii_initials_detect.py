#!/usr/bin/env python
"""
kxii_initials_detect.py - find the woodcut INITIALS on the Karl XII 1703 page
scans by geometry (0 model cost), so they can be cut out and shown in place of
the plain-letter drop cap.

    python tools/kxii_initials_detect.py --pages 770-880            # table
    python tools/kxii_initials_detect.py --pages 770 --debug         # every big component
    python tools/kxii_initials_detect.py --pages 770-880 --json out.json

Source scans: research/kxii_pages/pNNNN.jpg = Litteraturbanken lb2431561
faksimil (GUB F 430), licence field «pd» (verified live 2026-09-29).

METHOD
    Ink = grey < threshold on a 2x-downsampled page. Connected components by
    row runs + union-find (no scipy here). A woodcut initial is a COMPACT,
    DENSE component much taller than a text line: its framed block prints as
    one connected mass. Text letters, rules and ornament bars fail on height
    or aspect. Everything is reported in FULL-RESOLUTION pixels.

    This tool LOCATES. The assignment of a detection to a verse address and
    the crop it produces are checked on a contact sheet before anything ships.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep_kxii  # noqa: E402  find_frame / trim_column / text_band: the prep's own geometry

PAGES = r"C:\Projects\Hexapla-releases\research\kxii_pages"
DS = 2          # downsample factor for detection
INK = 120       # grey threshold (0-255) on the downsampled page


def components(mask):
    """Connected components (8-way) of a boolean mask -> list of
    (x0, y0, x1, y1, pixels). Row runs + union-find."""
    h, w = mask.shape
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    prev = []           # runs of previous row: (x0, x1, label)
    runs_all = []       # (y, x0, x1, label)
    for y in range(h):
        row = mask[y]
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        cur = []
        j = 0
        for x0, x1 in zip(starts.tolist(), ends.tolist()):
            lab = -1
            # runs are [x0, x1); 8-way touch = prev.p1 >= x0 and prev.p0 <= x1
            while j < len(prev) and prev[j][1] < x0:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] <= x1:
                pl = find(prev[k][2])
                if lab < 0:
                    lab = pl
                elif pl != lab:
                    parent[pl] = lab
                k += 1
            if lab < 0:
                lab = len(parent)
                parent.append(lab)
            cur.append((x0, x1, lab))
            runs_all.append((y, x0, x1, lab))
        prev = cur
    boxes = {}
    for y, x0, x1, lab in runs_all:
        r = find(lab)
        b = boxes.get(r)
        n = x1 - x0
        if b is None:
            boxes[r] = [x0, y, x1, y + 1, n]
        else:
            b[0] = min(b[0], x0); b[1] = min(b[1], y)
            b[2] = max(b[2], x1); b[3] = max(b[3], y + 1); b[4] += n
    return list(boxes.values())


def detect(path, debug=False):
    im = Image.open(path).convert("L")
    W, H = im.size
    small = im.resize((W // DS, H // DS), Image.BILINEAR)
    a = np.asarray(small)
    mask = a < INK
    comps = components(mask)
    # text line scale: median height of letter-sized components
    hs = sorted(b[3] - b[1] for b in comps if 4 <= b[3] - b[1] <= 40 and b[4] > 8)
    line = hs[len(hs) // 2] if hs else 10
    # A frame RULE touching a woodcut joins it to every text line along the
    # rule (p0874: one 256x866 component). Erase vertical ink runs longer than
    # any initial (14 lines; a woodcut is ~11) and re-label.
    if os.environ.get("HEXAPLA_OLD_COLS") != "1":
        mask = erase_vrules(mask, 14 * line)
        comps = components(mask)
    out = []
    for x0, y0, x1, y1, n in comps:
        w, h = x1 - x0, y1 - y0
        if 11.5 * line < h <= 40 * line and 1.6 * line <= w <= 16 * line \
                and os.environ.get("HEXAPLA_OLD_COLS") != "1":
            # a woodcut touching the text line under it (p0874: 256x404, the
            # block is the top 240): keep the longest run of DENSE rows
            prof = mask[y0:y1, x0:x1].mean(axis=1)
            prof = np.convolve(prof, np.ones(3) / 3, "same")
            best, s = (0, 0), None
            for i, v in enumerate(list(prof) + [0]):
                if v >= 0.2 and s is None:
                    s = i
                elif v < 0.2 and s is not None:
                    best = max(best, (i - s, s))
                    s = None
            if best[0] >= 2.2 * line:
                y0, y1 = y0 + best[1], y0 + best[1] + best[0]
                h = y1 - y0
                n = int(mask[y0:y1, x0:x1].sum())
        if h < 2.2 * line or w < 1.6 * line:
            continue
        dens = n / float(w * h)
        asp = w / float(h)
        keep = 0.45 <= asp <= 2.2 and dens >= 0.18 and h <= 14 * line
        if debug or keep:
            out.append({"x": x0 * DS, "y": y0 * DS, "w": w * DS, "h": h * DS,
                        "dens": round(dens, 3), "asp": round(asp, 2),
                        "hl": round(h / float(line), 1), "keep": keep})
    # A woodcut initial opens a text line: its left edge sits ON the column's
    # TEXT left edge. 2026-09-29: the edge is measured from the text lines
    # themselves (per row, the leftmost letter; median over rows). The prep's
    # frame/trim_column geometry left the edge on the frame RULE (p0791 t0=214,
    # text at ~340) and finds no frame at all on p0799/p0874, which silently
    # dropped 5 of 8 book-opening woodcuts. HEXAPLA_OLD_COLS=1 = that old path
    # (the known-bad control: tools/kxii_initials_detect.py --selftest must fail).
    fr = prep_kxii.find_frame(im)
    if os.environ.get("HEXAPLA_OLD_COLS") == "1":
        cols = old_cols(im, fr)
    else:
        cols = text_cols(comps, line, W // DS)
    for b in out:
        b["col"] = None
        for i, (t0, t1, c0, c1) in enumerate(cols):
            # on the edge, or after the verse NUMERAL a mid-chapter initial
            # keeps (1 Macc: «5 TÅ» puts the T at +84..+104 px)
            if t0 - 50 <= b["x"] <= t0 + 140 and c0 <= b["y"] <= c1 and b["x"] + b["w"] < t1:
                b["col"] = "LR"[i]
        # a letter of a display TITLE also sits on the column edge: it has
        # neighbours of its OWN height to its right (a title is a row of them);
        # an initial has text lines there instead, or one enlarged 2nd capital
        b["title"] = False
        if b["col"]:
            x0, y0, x1, y1 = b["x"] // DS, b["y"] // DS, (b["x"] + b["w"]) // DS, (b["y"] + b["h"]) // DS
            h0, same = y1 - y0, 0
            for c in comps:
                ch = c[3] - c[1]
                if (x1 - 2 <= c[0] <= x1 + 3 * (x1 - x0) and 0.75 * h0 <= ch <= 1.33 * h0
                        and 0.2 * h0 <= c[2] - c[0] <= 2.5 * h0     # not a rule fragment (p0830)
                        and c[1] < y1 and c[3] > y0):
                    same += 1
            b["title"] = same >= 2
        b["keep"] = bool(b["keep"] and b["col"] and not b["title"])
        # 1 Macc 6 (p0842-0844, 10 recorded initials): every real one has
        # dens 0.39-0.57; the extras there were 0.22-0.26 (headings, specks)
        # ... but that sample was MID initials (~66 px). A chapter's big verse-1
        # woodcut on the column EDGE is open scrollwork, dens 0.18-0.33 (about
        # 35 in p0770-0880); both initials of 1 Macc 9 fell below it and the
        # chapter vanished (gap look 2026-09-29). Those keep the base 0.18
        # floor. HEXAPLA_DENS_ALL=1 = the old rule (selftest must then fail).
        big_edge = b["col"] and b["h"] >= 90 and b["x"] - cols["LR".index(b["col"])][0] < 45 \
            and os.environ.get("HEXAPLA_DENS_ALL") != "1"
        if b["keep"] and b["dens"] < 0.33 and not big_edge and os.environ.get("HEXAPLA_OLD_COLS") != "1":
            b["keep"] = False
    # A chapter-numeral ORNAMENT row («Cap.» + fleurons) prints solid ink to the
    # right of its first glyph. Measured on the 2026-09-29 sheet01 look (72
    # Judith cells, 67 Y / 5 N): ink fraction in the 400 px strip right of the
    # box is 0.37-0.49 for all 5 ornaments and <= 0.30 for all 67 initials.
    ga = np.asarray(im)
    for b in out:
        b["right_ink"] = None
        if b["keep"] and b["h"] < 200:
            x1 = b["x"] + b["w"] + 6
            strip = ga[b["y"]:b["y"] + b["h"], x1:x1 + 400] < INK
            b["right_ink"] = round(float(strip.mean()), 3) if strip.size else 0.0
            if b["right_ink"] >= 0.34 and os.environ.get("HEXAPLA_OLD_COLS") != "1":
                b["keep"] = False
                b["ornament"] = True     # a chapter heading: kxii_initials_assign.py splits on it
    # one initial = one box: drop a kept box that overlaps a bigger kept one
    kept = sorted((b for b in out if b["keep"]), key=lambda b: -b["w"] * b["h"])
    for i, b in enumerate(kept):
        for g in kept[:i]:
            if g["keep"] and b["x"] < g["x"] + g["w"] and g["x"] < b["x"] + b["w"] \
                    and b["y"] < g["y"] + g["h"] and g["y"] < b["y"] + b["h"]:
                b["keep"] = False
                break
    out.sort(key=lambda b: ((b["col"] or "Z"), b["y"]))   # left column, then right
    return {"page": os.path.basename(path), "W": W, "H": H, "line": line * DS,
            "frame": fr, "cols": cols, "boxes": out}


def erase_vrules(mask, minlen):
    """Copy of mask with every vertical run of ink >= minlen rows cleared."""
    m = mask.copy()
    pad = np.zeros((1, m.shape[1]), dtype=np.int8)
    d = np.diff(np.vstack([pad, m.view(np.int8), pad]), axis=0)
    for x in np.flatnonzero((m.sum(axis=0) >= minlen)):
        st = np.flatnonzero(d[:, x] == 1)
        en = np.flatnonzero(d[:, x] == -1)
        for s, e in zip(st, en):
            if e - s >= minlen:
                m[s:e, x] = False
    return m


def old_cols(im, fr):
    """The prep's frame geometry (pre 2026-09-29) - kept only as the control."""
    cols = []
    if fr:
        L, C, R = fr
        y0, y1, _ = prep_kxii.text_band(im, L, C, R)
        for a0, a1 in ((L, C), (C, R)):
            t0, t1 = prep_kxii.trim_column(im, a0, a1, y0, y1)
            cols.append((t0, t1, y0, y1))
    return cols


def text_cols(comps, line, w):
    """Two text columns measured from letter-sized components (downsampled
    coords in, FULL-RES out): gutter = emptiest x in the middle of the page;
    per text row the leftmost/rightmost letter; edge = median over rows with
    enough letters (indented and initial-bearing rows are the minority)."""
    let = [c for c in comps if 0.6 * line <= c[3] - c[1] <= 1.8 * line and c[2] - c[0] <= 2 * line]
    if len(let) < 50:
        return []
    hist = np.zeros(w + 1)
    for c in let:
        hist[c[0]:c[2]] += 1
    lo, hi = int(w * 0.35), int(w * 0.65)
    # the middle of the TEXT BLOCK, not of the image: on p0794/p0806 the block
    # sits ~570 px right of centre, the gutter fell outside 35-65 % of the
    # width and the page came back as ONE column, so its right column's
    # initials (Tobit 6's opening) were dropped with col=None (2026-09-29).
    # HEXAPLA_PAGE_GUTTER=1 = the old image-width window (selftest must fail).
    if os.environ.get("HEXAPLA_PAGE_GUTTER") != "1":
        xs = np.array([c[0] for c in let] + [c[2] for c in let])
        a, z = np.percentile(xs, 2), np.percentile(xs, 98)
        lo, hi = int(a + 0.35 * (z - a)), int(a + 0.65 * (z - a))
    sm = np.convolve(hist, np.ones(9) / 9, "same")
    gut = lo + int(np.argmin(sm[lo:hi]))
    cols = []
    for side in (0, 1):
        rows = {}
        for c in let:
            cx = (c[0] + c[2]) / 2
            if (cx < gut) != (side == 0):
                continue
            rows.setdefault(((c[1] + c[3]) // 2) // max(1, int(1.5 * line)), []).append(c)
        mins, maxs, ys = [], [], []
        for r in rows.values():
            # the row's text = its longest run of letters with word-sized
            # gaps; margin dust, rule fragments and marginal notes fall outside
            r.sort(key=lambda c: c[0])
            best, cur = [], [r[0]]
            for c in r[1:]:
                if c[0] - max(k[2] for k in cur) <= 3 * line:
                    cur.append(c)
                else:
                    best = max(best, cur, key=len)
                    cur = [c]
            best = max(best, cur, key=len)
            if len(best) >= 8:
                mins.append(best[0][0])
                maxs.append(max(c[2] for c in best))
                ys += [c[1] for c in best] + [c[3] for c in best]
        if len(mins) < 5:
            continue
        t0 = int(np.median(mins)) * DS
        t1 = int(np.median(maxs)) * DS + 4 * line * DS
        cols.append((t0, t1, (min(ys) - 3 * line) * DS, max(ys) * DS))
    return cols


# 2026-09-29: book-opening woodcuts (tall, ~240 px full-res) that the detector
# MUST find. p0770/0780/0858 were found before the fix; the other five were not.
OPENINGS = {770: "Judith", 780: "Wisdom", 791: "Tobit", 799: "Sirach", 830: "Baruch",
            835: "1 Macc", 858: "2 Macc", 874: "Esther-add"}


# 2026-09-29 sheet01 look (Sonnet, one image): chapter-numeral ornaments (must
# NOT be kept) and a sample of confirmed initials (must be kept). (page, x, y).
ORNAMENTS = [(770, 1594, 2618), (774, 890, 1294), (775, 438, 336), (777, 1154, 2356), (778, 882, 2130)]
CONFIRMED = [(770, 768, 1596), (771, 1044, 1480), (772, 1606, 774), (774, 774, 1576),
             (776, 858, 1090), (777, 430, 2784), (778, 1610, 1042),
             # 2026-09-29 gap look (heading + first words = the asset's verse 1):
             # 1 Macc 9 summary + v1 woodcut, 1 Macc 10 v1 woodcut - all three
             # lost to the dens < 0.33 rule (0.328 / 0.307 / 0.289)
             (846, 1554, 640), (846, 1558, 910), (848, 848, 2236),
             # Tobit 6's summary + v1 woodcut in p0794's right column (the page
             # came back as ONE column; control HEXAPLA_PAGE_GUTTER=1)
             (794, 1622, 1016), (794, 1628, 1198)]


def selftest():
    bad = []
    by = {}
    for p, x, y in ORNAMENTS + CONFIRMED:
        if p not in by:
            by[p] = detect(os.path.join(PAGES, "p%04d.jpg" % p))["boxes"]
    for want, lst in ((False, ORNAMENTS), (True, CONFIRMED)):
        for p, x, y in lst:
            hit = any(b["keep"] and abs(b["x"] - x) <= 8 and abs(b["y"] - y) <= 8 for b in by[p])
            if hit != want:
                bad.append((p, x, y))
                print("p%04d (%d,%d) %s but kept=%s" % (p, x, y, "ornament" if not want else "initial", hit))
    for p, name in sorted(OPENINGS.items()):
        r = detect(os.path.join(PAGES, "p%04d.jpg" % p))
        tall = [b for b in r["boxes"] if b["keep"] and b["h"] >= 200]
        print("p%04d %-10s tall kept=%d %s" % (p, name, len(tall),
              " ".join("%s(%d,%d %dx%d)" % (b["col"], b["x"], b["y"], b["w"], b["h"]) for b in tall)))
        if len(tall) != 1:
            bad.append(p)
    print("SELFTEST %s (%d/%d openings)" % ("PASS" if not bad else "FAIL " + str(bad),
                                           len(OPENINGS) - len(bad), len(OPENINGS)))
    return 1 if bad else 0


def page_range(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="image numbers, e.g. 770-880")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.pages:
        ap.error("--pages is required")
    res = []
    for p in page_range(a.pages):
        path = os.path.join(PAGES, "p%04d.jpg" % p)
        if not os.path.exists(path):
            print("MISSING", path)
            continue
        r = detect(path, a.debug)
        res.append(r)
        kept = [b for b in r["boxes"] if b["keep"]]
        print("p%04d frame=%s line=%d kept=%d %s" % (p, r["frame"], r["line"], len(kept), " ".join(
            "%s(%d,%d %dx%d d%.2f)" % (b["col"] or "-", b["x"], b["y"], b["w"], b["h"], b["dens"])
            for b in r["boxes"] if b["keep"] or a.debug)))
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
