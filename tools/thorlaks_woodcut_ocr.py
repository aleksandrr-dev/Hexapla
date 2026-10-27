#!/usr/bin/env python
"""
thorlaks_woodcut_ocr.py - give each SMALL (paragraph) woodcut found by
thorlaks_woodcuts.py a verse address, 0 model-token cost: the Þorláksbiblía
Kraken model (h64_trim_gho) reads the text line beside the woodcut, and the
reading is matched against the merged book's verse openings.

    tools/.kraken_venv/Scripts/python.exe tools/thorlaks_woodcut_ocr.py            # OCR + match, writes ocr.json
    tools/.kraken_venv/Scripts/python.exe tools/thorlaks_woodcut_ocr.py --rematch  # match only, from ocr.json
    python tools/thorlaks_woodcut_ocr.py --selftest

MATCH
    Each verse of the book (v >= 2; v1 belongs to the chapter woodcut) gives
    its opening with tags stripped and the FIRST letter dropped (the woodcut
    is that letter). The OCR line (digits dropped) is compared to each opening
    of the same length with difflib; best score S1, runner-up S2.
    ADDRESSED when S1 >= MIN_S and S1 - S2 >= MARGIN. In a book whose chapter
    woodcuts passed the count gate the small one also carries its chapter
    from geometry: a match in a DIFFERENT chapter is CONFLICT, never shipped.
    Everything else is UNMATCHED. Never guessed.

CONTROL
    --selftest: a line taken from a verse opening matches that verse; a
    shuffled line is UNMATCHED. HEXAPLA_OCR_NOMARGIN=1 drops the margin and
    floor, so the shuffled line matches and the selftest must fail.
"""
import argparse
import bisect
import difflib
import io
import json
import os
import random
import re
import sys

DATA = r"C:/Projects/Hexapla-releases"
RES = os.path.join(DATA, "research")
OUT = os.path.join(DATA, "_work", "_scratch", "thor_woodcuts")
MODEL = os.path.join(DATA, "_work", "kraken", "runs", "h64_trim_gho", "best.mlmodel")
PDF = os.path.join(RES, "thorlaks_v3.pdf")
ZOOM_OCR = 8.3
MIN_S, MARGIN = 0.55, 0.12
MIN2, MARGIN2 = 0.62, 0.12    # second test (locate)
BIG_V1_SPAN = 160             # a big block's line may be verse 1's 2nd/3rd line
L1 = 30                       # line-1 prefix used to place the line inside its verse
OPEN_TOL = int(os.environ.get("HEXAPLA_OCR_OPEN_TOL", "12"))   # calibrated on the control rows

CH = re.compile(r"^##\s+(.+?)\s+(\d{1,3})\s*$")
VS = re.compile(r"^(\d{1,3})\s+(.*)$")


def norm(s):
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"[0-9]", "", s.lower())
    return re.sub(r"[^\w]+", " ", s).strip()


def openings(key, first=False):
    """Verse openings, first letter dropped: v >= 2 (paragraph woodcuts), or
    with first=True verse 1 only (chapter woodcuts)."""
    out = []
    ch = None
    for ln in io.open(os.path.join(RES, "thorlaks_%s.md" % key), encoding="utf-8"):
        s = ln.strip()
        if s.startswith("# Appendix"):
            break
        m = CH.match(s)
        if m:
            ch = int(m.group(2))
            continue
        m = VS.match(s)
        if m and ch and (int(m.group(1)) == 1) == first:
            t = norm(m.group(2))
            out.append((ch, int(m.group(1)), t[1:].lstrip() if t else t))
    return out


def match(text, ops):
    t = norm(text)
    if len(t) < 8:
        return None, 0.0, 0.0
    sc = []
    for ch, v, o in ops:
        sc.append((difflib.SequenceMatcher(None, t, o[:len(t) + 4]).ratio(), ch, v))
    sc.sort(reverse=True)
    s1, s2 = sc[0][0], (sc[1][0] if len(sc) > 1 else 0.0)
    if os.environ.get("HEXAPLA_OCR_NOMARGIN") == "1" or (s1 >= MIN_S and s1 - s2 >= MARGIN):
        return (sc[0][1], sc[0][2]), s1, s2
    return None, s1, s2


def selftest():
    ops = [(1, 2, "ar var eirn madur af gude sendr sa hiet johanes"),
           (1, 3, "an kom til vitnisburdar ad hann vitnade vm liosed"),
           (2, 5, "g hans moder sagde til þenara huad hann segir ydur")]
    a, _, _ = match("Ar var eirn Madur af Gude sendr", ops)
    w = list("ar var eirn madur af gude sendr")
    random.Random(1).shuffle(w)
    b, _, _ = match("".join(w), ops)
    ok = a == (1, 2) and b is None
    # second test: an opening (first letter dropped) is OPEN, a mid-verse
    # paragraph is MID in its verse, a phrase two verses share and a shuffle
    # are refused
    bk = index_verses([
        (5, 18, "þar fyrer leitudu gydingar enn meir ad lijflata hann"),
        (5, 19, "jesus suarade og sagde til þeirra sannlega sannlega seige eg ydur sonurenn kann ecke af sialfum sier"),
        (5, 24, "sannlega sannlega seige eg ydur huor sem heyrer mitt ord og truer þeim sem mig sende"),
        (9, 19, "og hann tok fædu og styrktest saul var þa nockra daga hia lærisueinunum j damasco")])
    c = locate("esus suarade og sagde til þeirra sannlega", bk)
    d = locate("aul var þa nockra daga hia lærisueinunum", bk)
    e = locate("annlega sannlega seige eg ydur", bk)
    w = list("esus suarade og sagde til þeirra sannlega")
    random.Random(2).shuffle(w)
    f = locate("".join(w), bk)
    ok2 = c[:2] == (1, "OPEN") and d[:2] == (3, "MID") and e[0] is None and f[0] is None
    print("selftest first", "OK" if ok else "FAIL", "| second", "OK" if ok2 else "FAIL",
          c[:2], d[:2], e[:2], f[:2])
    return 0 if ok and ok2 else 1


def first_line(pg, x0, x1, d, z, nth=0):
    """The text line the woodcut opens, in zoom-z page rows: the ink band
    beside the block whose start is nearest the block's top. Measured
    2026-10-05: line pitch ~1.8 lh, a small woodcut spans ~3 lines and its
    top sits a few rows BELOW the first line's top - a window cut from the
    block top straddles two lines and Kraken returns noise.
    nth=1: the band after that one (the second test's second line)."""
    import fitz
    import numpy as np
    pitch = 1.8 * d["lh"]
    top = d["y"] - pitch
    r = fitz.Rect(x0, top / z, x1, (d["y"] + d["h"]) / z)
    pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), clip=r, colorspace=fitz.csGRAY)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
    prof = (g < 110).mean(axis=1)
    on = prof > 0.02
    bands, s = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and s is None:
            s = i
        elif not v and s is not None:
            bands.append([s, i])
            s = None
    out = []
    for a, b in bands:          # a band over 1.4 pitch is two lines touching: cut at its minimum
        while b - a > 1.4 * pitch:
            lo = a + int(0.6 * pitch)
            hi = min(b, a + int(1.4 * pitch))
            m = lo + int(np.argmin(prof[lo:hi]))
            out.append([a, m])
            a = m + 1
        if b - a >= 0.5 * d["lh"]:
            out.append([a, b])
    want = d["y"] - top
    near = [bd for bd in out if abs(bd[0] - want) <= 0.6 * pitch]
    if not near:
        return None
    i = out.index(min(near, key=lambda bd: abs(bd[0] - want))) + nth
    if i >= len(out):
        return None
    a, b = out[i]
    return top + a - 2, top + b + 2


def book_text(key):
    """Every verse of the merged book as one normalised string, with each
    verse's start offset and a trigram index for locate()."""
    vs, ch = [], None
    for ln in io.open(os.path.join(RES, "thorlaks_%s.md" % key), encoding="utf-8"):
        s = ln.strip()
        if s.startswith("# Appendix"):
            break
        m = CH.match(s)
        if m:
            ch = int(m.group(2))
            continue
        m = VS.match(s)
        if m and ch:
            vs.append((ch, int(m.group(1)), norm(m.group(2))))
    return index_verses(vs)


def index_verses(vs):
    starts, parts, n = [], [], 0
    for _, _, t in vs:
        starts.append(n)
        parts.append(t + " ")
        n += len(t) + 1
    T = "".join(parts)
    tri = {}
    for p in range(len(T) - 2):
        tri.setdefault(T[p:p + 3], []).append(p)
    return vs, starts, T, tri


def locate(text, book, chapter=None):
    """SECOND TEST: find the OCR text anywhere in the book (or in `chapter`),
    not only at verse openings - a paragraph woodcut can open mid-verse, two
    verses can open alike, and the first test's opening-sized window is short.
    -> (k, pos, s1, s2): k = verse index into book[0], pos OPEN|MID, s2 = the
    best score at a start more than half the query away (a different place),
    or None when below MIN2 / inside MARGIN2."""
    vs, starts, T, tri = book
    q = norm(text)
    L = len(q)
    if L < 16:
        return None, None, 0.0, 0.0
    votes = {}
    for i in range(L - 2):
        for p in tri.get(q[i:i + 3], ()):
            b = (p - i) // 4
            votes[b] = votes.get(b, 0) + 1
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(q)
    cand = []
    for b, _ in sorted(votes.items(), key=lambda kv: -kv[1])[:40]:
        for s in range(max(0, b * 4 - 6), b * 4 + 10):
            k = bisect.bisect_right(starts, s) - 1
            if k + 1 < len(starts) and starts[k + 1] - s <= 3:
                k += 1            # a window opening just short of a verse belongs to it
            if chapter and vs[k][0] != chapter:
                continue
            sm.set_seq1(T[s:s + L])
            cand.append((sm.ratio(), s, k))
    if not cand:
        return None, None, 0.0, 0.0
    s1, at, k = max(cand)
    s2 = max([c[0] for c in cand if abs(c[1] - at) > L // 2] or [0.0])
    pos = "OPEN" if abs(at - starts[k]) <= 3 else "MID"
    if os.environ.get("HEXAPLA_OCR_NOMARGIN") == "1" or (s1 >= MIN2 and s1 - s2 >= MARGIN2):
        return k, pos, s1, s2
    return None, None, s1, s2


def ocr_all(plan, prev=None, nth=0, only=None, width=0.55):
    import warnings
    warnings.filterwarnings("ignore")
    import fitz
    from PIL import Image
    from kraken import rpred
    from kraken.containers import BBoxLine, Segmentation
    from kraken.lib import models
    net = models.load_any(MODEL, device="cpu")
    doc = fitz.open(PDF)
    res = dict(prev or {})
    for key, p in plan.items():
        for d in p["dets"]:
            if d["file"] in res or (only is not None and d["file"] not in only):
                continue
            z = 3.0
            pg = doc[d["idx"]]
            x0 = (d["x"] + d["w"] * 1.05) / z
            x1 = min(pg.rect.x1, x0 + pg.rect.width * width)
            band = first_line(pg, x0, x1, d, z, nth)
            if band is None:
                print(d["file"], "| [no line band]", flush=True)
                continue
            r = fitz.Rect(x0, band[0] / z, x1, band[1] / z)
            pix = pg.get_pixmap(matrix=fitz.Matrix(ZOOM_OCR, ZOOM_OCR), clip=r, colorspace=fitz.csGRAY)
            im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            seg = Segmentation(type="bbox", imagename="x", text_direction="horizontal-lr",
                               script_detection=False,
                               lines=[BBoxLine(id="l", bbox=(0, 0, im.width, im.height))])
            rec = next(iter(rpred.rpred(net, im, seg)))
            res[d["file"]] = rec.prediction
            print(d["file"], "|", rec.prediction, flush=True)
    return res


def look_bad():
    """files the crop-check look called anything but OK (LOOK_RESULT + sheet_key)."""
    key = {}
    for ln in io.open(os.path.join(OUT, "sheet_key.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 3:
            key[p[0]] = p[2]
    bad = {}
    for ln in io.open(os.path.join(OUT, "LOOK_RESULT.txt"), encoding="utf-8"):
        p = ln.split()
        if len(p) >= 2 and p[0] in key:
            bad[key[p[0]]] = p[1]
    return bad


def second(rematch, wide=None):
    """SECOND TEST on the first test's UNMATCHED rows: OCR the line below the
    first one too, locate line1+line2 anywhere in the book (the small one's
    geometry chapter when it has one). CONTROL in the same run: every row the
    first test ADDRESSED goes through the same locate, and the agreement rate
    is printed - the second test's error rate on rows whose answer is known.
    Writes addr2.json (every row) and ship2.json (new shippable rows only).
    wide=FRAC: the WIDER-WINDOW variant - only rows the second test left
    unaddressed are re-OCRed (both lines) at FRAC of the page width; outputs
    go to *_wide.json so the normal-width results stay untouched."""
    plan = json.load(io.open(os.path.join(OUT, "plan.json"), encoding="utf-8"))
    rows = json.load(io.open(os.path.join(OUT, "addr.json"), encoding="utf-8"))
    o2 = os.path.join(OUT, "ocr2.json")
    ocr2 = json.load(io.open(o2, encoding="utf-8")) if os.path.exists(o2) else {}
    sfx = ""
    if wide:
        sfx = "_wide"
        prev = json.load(io.open(os.path.join(OUT, "addr2.json"), encoding="utf-8"))
        tgt = {r["file"] for r in prev if "UNMATCHED" in r["status"] and not r.get("addr2")}
        ow = os.path.join(OUT, "ocr_wide.json")
        w = json.load(io.open(ow, encoding="utf-8")) if os.path.exists(ow) else {"1": {}, "2": {}}
        if not rematch:
            w["1"] = ocr_all(plan, w["1"], nth=0, only=tgt, width=wide)
            w["2"] = ocr_all(plan, w["2"], nth=1, only=tgt, width=wide)
            io.open(ow, "w", encoding="utf-8", newline="\n").write(json.dumps(w, ensure_ascii=False, indent=1))
        for r in rows:
            if r["file"] in w["1"]:
                r["ocr_narrow"] = r["ocr"]
                r["ocr"] = w["1"][r["file"]]
        ocr2 = dict(ocr2, **w["2"])
    elif not rematch:
        ocr2 = ocr_all(plan, ocr2, nth=1, only={r["file"] for r in rows})
        io.open(o2, "w", encoding="utf-8", newline="\n").write(json.dumps(ocr2, ensure_ascii=False, indent=1))
    geo = {d["file"]: (d["idx"], d["x"], d["y"]) for p in plan.values() for d in p["dets"]}
    books = {}
    ctl = {"agree": 0, "disagree": 0, "none": 0}
    ctl_bad = []
    for r in rows:
        if r["book"] not in books:
            books[r["book"]] = book_text(r["book"])
        bk = books[r["book"]]
        q = (r["ocr"] + " " + ocr2.get(r["file"], "")).strip()
        k, pos, s1, s2 = locate(q, bk, r["geo_chapter"] if r["size"] == "small" else None)
        got, off = None, None
        if k is not None:
            ch, v = bk[0][k][:2]
            # where LINE 1 starts inside the located verse decides OPEN/MID:
            # the two-line query's own offset blurs it (John 19:16b read 13)
            q1 = norm(r["ocr"])[:L1]
            off = locate_offset(q1, bk, k) if len(q1) >= 12 else None
            pos = "MID" if off is None or off > OPEN_TOL else "OPEN"
            if r["size"] == "small" and pos == "OPEN":
                got = "%d:%d" % (ch, v)
            elif r["size"] == "big" and v == 1 and off is not None and off <= BIG_V1_SPAN:
                # a big block's band may be verse 1's second line
                got = "%d:1" % ch
        r.update({"addr2": got, "pos2": pos, "off2": off, "loc2": "%d:%d" % bk[0][k][:2] if k is not None else None,
                  "s1b": round(s1, 3), "s2b": round(s2, 3), "ocr2": ocr2.get(r["file"])})
        first_ok = r["addr"] and "UNMATCHED" not in r["status"] and "ORDER" not in r["status"]
        if first_ok:
            if got == r["addr"]:
                ctl["agree"] += 1
            elif got is None:
                ctl["none"] += 1
            else:
                ctl["disagree"] += 1
                ctl_bad.append((r["file"], r["addr"], got))
    # ORDER over the union of both tests' addresses, as the first test does
    for key in plan:
        seq = [r for r in rows if r["book"] == key and (
            (r["addr"] and "UNMATCHED" not in r["status"]) or r.get("addr2"))]
        cv = [tuple(int(x) for x in (r["addr"] if r["addr"] and "UNMATCHED" not in r["status"]
                                     else r["addr2"]).split(":")) for r in seq]
        for i, r in enumerate(seq):
            lo = i > 0 and cv[i - 1] >= cv[i]
            hi = i + 1 < len(seq) and cv[i + 1] <= cv[i]
            r["order2"] = bool(lo and hi or (lo and i + 1 == len(seq)) or (hi and i == 0))
    bad = look_bad()
    new, why = [], {}
    for r in rows:
        if "UNMATCHED" not in r["status"]:
            continue
        if not r.get("addr2"):
            w = "located mid-verse (no verse opening)" if r["loc2"] and r["size"] == "small" else \
                "big, not verse 1" if r["loc2"] else "still unmatched"
        elif r["file"] in bad:
            w = "look " + bad[r["file"]]
        elif r["order2"]:
            w = "ORDER"
        else:
            new.append(r)
            continue
        why[w] = why.get(w, 0) + 1
    # one physical block filed under two books (shared pages) ships under neither
    seen = {}
    for r in new:
        seen.setdefault(geo.get(r["file"]), []).append(r)
    dup = {id(r) for g in seen.values() if len(g) > 1 for r in g}
    if dup:
        why["shared-page block in two books"] = len(dup)
    new = [r for r in new if id(r) not in dup]
    io.open(os.path.join(OUT, "addr2%s.json" % sfx), "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    io.open(os.path.join(OUT, "ship2%s.json" % sfx), "w", encoding="utf-8", newline="\n").write(json.dumps(
        [{"book": r["book"], "addr": r["addr2"], "size": r["size"], "file": r["file"], "test": "second"}
         for r in new], ensure_ascii=False, indent=1))
    n = sum(ctl.values())
    print("CONTROL (first-test addresses re-found by the second test): %d rows - agree %d, "
          "disagree %d, no answer %d" % (n, ctl["agree"], ctl["disagree"], ctl["none"]))
    for b in ctl_bad:
        print("   disagree %-40s first %-7s second %s" % b)
    unm = sum("UNMATCHED" in r["status"] for r in rows)
    print("UNMATCHED by the first test: %d -> second test ships %d (small %d, big %d); not shipped: %s" % (
        unm, len(new), sum(r["size"] == "small" for r in new), sum(r["size"] == "big" for r in new), why))
    return 0


def locate_offset(q, bk, k):
    """chars from verse k's start to where q sits inside it (MID big rows)."""
    vs, starts, T, _ = bk
    q = norm(q)
    end = starts[k + 1] if k + 1 < len(starts) else len(T)
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(q)
    best = (0.0, 0)
    for s in range(starts[k], max(starts[k] + 1, end - len(q) // 2)):
        sm.set_seq1(T[s:s + len(q)])
        best = max(best, (sm.ratio(), s - starts[k]))
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rematch", action="store_true")
    ap.add_argument("--second", action="store_true", help="second test on the UNMATCHED rows")
    ap.add_argument("--wide", type=float, help="with --second: re-OCR the still-unaddressed rows at this page-width fraction")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.second:
        return second(a.rematch, a.wide)
    plan = json.load(io.open(os.path.join(OUT, "plan.json"), encoding="utf-8"))
    oj = os.path.join(OUT, "ocr.json")
    if a.rematch:
        ocr = json.load(io.open(oj, encoding="utf-8"))
    else:
        prev = json.load(io.open(oj, encoding="utf-8")) if os.path.exists(oj) else {}
        ocr = ocr_all(plan, prev)
        io.open(oj, "w", encoding="utf-8", newline="\n").write(json.dumps(ocr, ensure_ascii=False, indent=1))
    rows = []
    tally = {}
    for key, p in plan.items():
        ops = {"small": openings(key), "big": openings(key, first=True)}
        for d in p["dets"]:
            if d["file"] not in ocr:
                continue
            m, s1, s2 = match(ocr[d["file"]], ops[d["size"]])
            geo = d.get("addr") if d["size"] == "big" else d.get("chapter")
            got = None if m is None else ("%d:%d" % m if d["size"] == "big" else m[0])
            if m is None:
                st = "UNMATCHED"
            elif geo and geo != got:
                st = "GEO-DISAGREES"     # 2026-10-05: on every such row the OCR was right
            elif geo:
                st = "ADDRESSED+GEO"
            else:
                st = "ADDRESSED"
            st = d["size"] + " " + st
            tally.setdefault(key, {}).setdefault(st, 0)
            tally[key][st] += 1
            rows.append({"book": key, "file": d["file"], "idx": d["idx"], "geo_chapter": d.get("chapter"),
                         "addr": "%d:%d" % m if m else None, "s1": round(s1, 3), "s2": round(s2, 3),
                         "size": d["size"], "status": st, "ocr": ocr[d["file"]]})
    # ORDER: in reading order a book's addresses must rise. An address lower
    # than its predecessor's or higher than its successor's is flagged, never
    # shipped (a free second check the OCR match cannot give itself).
    for key in plan:
        seq = [r for r in rows if r["book"] == key and r["addr"]]
        cv = [tuple(int(x) for x in r["addr"].split(":")) for r in seq]
        for i, r in enumerate(seq):
            lo = i > 0 and cv[i - 1] >= cv[i]
            hi = i + 1 < len(seq) and cv[i + 1] <= cv[i]
            if lo and hi or (lo and i + 1 == len(seq)) or (hi and i == 0):
                r["status"] += " ORDER"
    io.open(os.path.join(OUT, "addr.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    for k in sorted(tally):
        print("%-15s %s" % (k, tally[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
