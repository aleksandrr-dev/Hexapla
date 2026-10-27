# -*- coding: utf-8 -*-
"""Line-image + ground-truth pairs for training a Kraken recogniser on Þorláksbiblía v3.

    python tools/kraken_gt_build.py --ocr            # cache anchor OCR (slow, detach it)
    python tools/kraken_gt_build.py                  # align + write pairs (dry run: report only)
    python tools/kraken_gt_build.py --apply          # write research/_prep/kraken_gt/{train,eval}/
    python tools/kraken_gt_build.py --selftest       # known-bad control: shuffled GT must be refused
    <kraken_venv>/python tools/kraken_gt_build.py --kraken-ocr cpu|cuda:0   # h64 read + per-char x
    python tools/kraken_gt_build.py --anchor h64 --trim [--check-reads|--selftest|--apply]

--trim (2026-09-27, the recommended mode): every anchor OCR drops edge words,
so no rule can say which of two lines owns a word at the break (page_labels()
was still ~7 % wrong per edge). --trim labels only the whole words from the
first to the last one the h64 read matched at their edge letter, and crops
the image at the clear ink gap just outside them. Measured on the 34 pages
with crop reads: 294/300 crop starts and 291/300 ends re-read to the label
(6 residuals image-checked: all reader errors on correct crops); check-reads
1/705 neighbour, itself a misaddressed read.

Generalises tools/tesstrain_prep.py (one book, cursor from the book's first
verse) to EVERY merged NT book at once: each page is first LOCATED in the
concatenated merged text by 8-gram shingle voting over its whole OCR, and only
then aligned line by line with a monotonic cursor. A page whose vote is weak
(not merged yet — Acts, most of John — or a page the OCR cannot see) is
dropped whole, never guessed.

The anchor OCR is the local Tesseract `isfrak` model (CER ~0.135): wrong about
characters, right about order and length. Its text never reaches a label; the
label is always the MERGED text's own characters for the aligned span.

⚠⚠ A MISALIGNED PAIR IS WORSE THAN NO PAIR — it teaches the recogniser to
hallucinate. Every pair is gated on alignment confidence; any label holding an
editorial bracket ([HN], [?], [ornate initial...]) is dropped rather than
cleaned, because the bracket's position in the line is unknown.
⚠ The merged text carries known adjudication errors (witness calib 2026-09-26);
the recogniser inherits them at their base rate. It is a WITNESS read, never a
correction source.

Held-out pages (every 10th located page, by idx) go to eval/ WHOLE, so no
eval line has a neighbour in train.
"""
import argparse
import bisect
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from local_screen import parse_chunk  # noqa: E402
from tesstrain_prep import skeleton, snap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
PREP = RESEARCH / "_prep"
OUT = PREP / "kraken_gt"
CACHE = Path(r"C:/Projects/Hexapla-releases/_work/kraken/ocr_cache_isfrak.json")
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:/Projects/Hexapla-releases/tessdata"

NT = ["matthew", "mark", "luke", "john", "acts", "romans", "1corinthians", "2cor",
      "galatians", "ephesians", "philippians", "colossians", "1thessalonians",
      "2thessalonians", "1timothy", "2timothy", "titus", "philemon", "hebrews",
      "james", "1peter", "2peter", "1john", "2john", "3john", "jude"]
SKIP_KIT = re.compile(r"^(_|gt$|kraken_gt|eph_test$|ot_)")
BRACKET = re.compile(r"[\[\]{}«»]")
K = 8
WHY = Counter()
EDGE_DIFF = []   # (pidx, line, snap() label, page_labels() label) where they differ
EDGE_ALL = []    # the same for every labelled line (absolute edge accuracy)
# a line break whose best cut wins by less than this many letters drops both lines
# Measured 2026-09-27 on the isfrak anchor: margin 1 kept 543 of 6321 pairs (the
# OCR-count costs tie at most breaks) - so OFF until h64 ink geometry is scored.
DROP_MARGIN = float(os.environ.get("KGT_MARGIN", "0"))
TRIM = False     # --trim: label only matched whole words and crop the image to them
# a cut column may hold this fraction of dark pixels; 0.05/0.1 bought 2-6 % more
# pairs but lost 5-8 of 300 ends (measured 2026-09-27) - so a truly clear column
GAP_INK = float(os.environ.get("KGT_GAPINK", "0"))
TRIM_AGREE = float(os.environ.get("KGT_AGREE", "0.8"))
CHAR_L, CHAR_R = (float(x) for x in os.environ.get("KGT_CHAR", "0.7,1.7").split(","))


def reference():
    """Concatenated merged NT text with verse numerals, plus its skeleton."""
    parts = []
    for b in NT:
        f = RESEARCH / f"thorlaks_{b}.md"
        if f.exists():
            parts += [f"{no} {t}" for _, _, no, t in parse_chunk(f)]
    text = " ".join(parts)
    skel, idx = skeleton(text)
    return text, skel, idx


def pages():
    """(idx) -> newest kit dir holding p<idx>, vol 3 only."""
    best = {}
    for kit in PREP.iterdir():
        if not kit.is_dir() or SKIP_KIT.match(kit.name):
            continue
        man = kit / "MANIFEST.md"
        if man.exists() and "v3" not in man.read_text(encoding="utf-8")[:200]:
            continue
        for p in kit.glob("p*"):
            m = re.fullmatch(r"p(\d+)", p.name)
            if not m or not any(p.glob("line*.png")):
                continue
            i = int(m.group(1))
            if i not in best or p.stat().st_mtime > best[i].stat().st_mtime:
                best[i] = p
    return dict(sorted(best.items()))


def lines_of(pdir):
    return sorted(p for p in pdir.glob("line*.png") if re.fullmatch(r"line\d+\.png", p.name))


def ocr(png):
    env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
    r = subprocess.run([TESS, str(png), "stdout", "-l", "isfrak", "--psm", "7"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if r.returncode != 0:
        raise RuntimeError(f"tesseract rc {r.returncode} on {png}: {r.stderr[:200]}")
    return r.stdout.strip()


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


H64 = Path(r"C:/Projects/Hexapla-releases/_work/kraken/runs/h64_v1/best_16.mlmodel")
KCACHE = Path(r"C:/Projects/Hexapla-releases/_work/kraken/ocr_cache_h64.json")


def load_kcache():
    return json.loads(KCACHE.read_text(encoding="utf-8")) if KCACHE.exists() else {}


def ink_extent(im):
    """x of the first/last ink column in the line's middle band (neighbour
    lines' ascenders/descenders bleed into the top/bottom rows)."""
    import numpy as np
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h = a.shape[0]
    band = a[int(h * .3):int(h * .75)]
    xs = np.nonzero((band < np.percentile(a, 50) - 40).sum(0))[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else (0, im.width - 1)


def run_kraken_ocr(pg, device, limit=None):
    """Kraken read + geometry per line (run with the kraken venv's python).
    Both Tesseract (any psm, padded or not) and this model stop short of a
    line's edge words (luke_kit2 p62 line09: the print ends «Og þa er Jesus»,
    isfrak reads to «þa», h64 to «er»), so a read's TEXT cannot say which of
    two lines owns a word near the break. The unread INK can: x0/x1 = first/
    last recognised char, i0/i1 = ink extent."""
    import warnings
    warnings.filterwarnings("ignore")
    from PIL import Image
    from kraken import rpred
    from kraken.containers import BBoxLine, Segmentation
    from kraken.lib import models
    net = models.load_any(str(H64), device=device)
    kc = load_kcache()
    todo = [l for d in list(pg.values())[:limit] for l in lines_of(d)
            if "c" not in kc.get(str(l), {})]
    print(f"kraken OCR ({device}): {len(todo)} lines to do, {len(kc)} cached", flush=True)
    for n, png in enumerate(todo, 1):
        im = Image.open(png)
        seg = Segmentation(type="bbox", imagename=str(png), text_direction="horizontal-lr",
                           script_detection=False,
                           lines=[BBoxLine(id="l", bbox=(0, 0, im.width, im.height))])
        rec = next(iter(rpred.rpred(net, im, seg)))
        xs = [c[0][0] for c in rec.cuts]
        i0, i1 = ink_extent(im)
        # c = each predicted char's x (CTC peak; kraken's cuts are degenerate boxes)
        kc[str(png)] = {"t": rec.prediction, "x0": min(xs, default=0),
                        "x1": max(xs, default=0), "i0": i0, "i1": i1,
                        "c": [int(x) for x in xs]}
        if n % 500 == 0:
            KCACHE.write_text(json.dumps(kc, ensure_ascii=False), encoding="utf-8")
            print(f"  {n}/{len(todo)}", flush=True)
    KCACHE.write_text(json.dumps(kc, ensure_ascii=False), encoding="utf-8")
    print(f"kraken OCR done: {len(kc)} cached", flush=True)


def unread_letters(k, block=None):
    """Letters' worth of ink left of the first / right of the last recognised
    char, at this line's own pitch -> (left, right). block = the page's text
    block (left, right): ink outside it by more than two letters is a margin
    mark or a neighbour column, not text (matthew p4 line03: ink to x=1942,
    text ends at 1570)."""
    t = k["t"]
    n = len(t.strip())
    if n < 10 or k["x1"] <= k["x0"]:
        return 0, 0
    pitch = (k["x1"] - k["x0"]) / (n - 1)
    i0, i1 = k["i0"], k["i1"]
    if block:
        i0, i1 = max(i0, block[0] - 2 * pitch), min(i1, block[1] + 2 * pitch)
    per = len(skeleton(t)[0]) / len(t)          # letters per char (spaces, marks)
    return (max(k["x0"] - i0, 0) / pitch * per,
            max(i1 - k["x1"], 0) / pitch * per)


def text_block(geoms):
    """Median left / right ink edge of a page's lines = its justified block."""
    if len(geoms) < 5:
        return None
    l, r = sorted(g["i0"] for g in geoms), sorted(g["i1"] for g in geoms)
    return l[len(l) // 2], r[len(r) // 2]


def run_ocr(pg):
    cache = load_cache()
    todo = [str(l) for d in pg.values() for l in lines_of(d) if str(l) not in cache]
    print(f"OCR: {len(todo)} lines to do, {len(cache)} cached", flush=True)
    done = 0
    with ThreadPoolExecutor(6) as ex:
        for path, txt in zip(todo, ex.map(lambda p: ocr(p), todo)):
            cache[path] = txt
            done += 1
            if done % 500 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  {done}/{len(todo)}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"OCR done: {len(cache)} cached", flush=True)


def locate(page_skel, shingles, n_ref):
    """Vote on the reference offset where this page's text starts."""
    votes = Counter()
    for i in range(0, max(len(page_skel) - K, 0), 2):
        for pos in shingles.get(page_skel[i:i + K], ())[:20]:
            votes[(pos - i) // 200] += 1
    if not votes:
        return None, 0
    (bucket, v), = votes.most_common(1)
    return max(bucket * 200 - 400, 0), v


def align(pg, cache, text, skel, idx, min_conf=0.70, min_chars=20, min_votes=25, geom=None):
    shingles = {}
    for i in range(len(skel) - K):
        shingles.setdefault(skel[i:i + K], []).append(i)
    pairs, report = [], []
    for pidx, pdir in pg.items():
        lines = lines_of(pdir)
        if any(str(l) not in cache for l in lines):
            report.append((pidx, "NO-OCR", 0, 0, len(lines)))
            continue
        osks = [skeleton(cache[str(l)])[0] for l in lines]
        start, pvotes = locate("".join(osks), shingles, len(skel))
        if start is None or pvotes < min_votes:
            report.append((pidx, "UNLOCATED", pvotes, 0, len(lines)))
            continue
        cur, kept, got = start, 0, []
        block = text_block([geom[str(l)] for l in lines if str(l) in geom]) if geom else None
        for png, osk in zip(lines, osks):
            if len(osk) < min_chars:
                WHY['short-ocr'] += 1
                continue
            # vote this line's start inside a wide forward window: the page
            # locate is only bucket-accurate, and a fixed narrow window never
            # catches up once it starts behind
            lo, hi = max(cur - 40, 0), cur + 3000
            votes = Counter()
            for i in range(len(osk) - 6):
                j = skel.find(osk[i:i + 6], lo, hi)
                while j != -1:
                    votes[j - i] += 1
                    j = skel.find(osk[i:i + 6], j + 1, hi)
            if not votes:
                WHY['no-anchor'] += 1
                continue
            # the EARLIEST offset whose support is near the best, so a line
            # that repeats a later phrase does not jump ahead
            top = max(votes.values())
            if top < 3:
                WHY['no-anchor'] += 1
                continue
            off = min(o for o, c in votes.items() if c >= top * 0.6)
            base = max(off - 30, 0)
            win = skel[base:off + len(osk) + 30]
            sm = difflib.SequenceMatcher(None, osk, win, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size > 3]
            if not blocks:
                WHY['no-anchor'] += 1
                continue
            s, e = base + blocks[0].b, base + blocks[-1].b + blocks[-1].size
            if e <= s:
                WHY['empty-span'] += 1
                continue
            conf = difflib.SequenceMatcher(None, osk, skel[s:e], autojunk=False).ratio()
            # span length must match the line's own OCR length: a span that
            # swallowed a skipped line is the misalignment we exist to refuse
            if conf < min_conf:
                WHY['low-conf'] += 1
                continue
            if not (0.8 <= (e - s) / len(osk) <= 1.25):
                WHY['span-length'] += 1
                continue
            raw = cache[str(png)]
            ul, ur = (unread_letters(geom[str(png)], block)
                      if geom and str(png) in geom else (0, 0))
            tr = None
            if TRIM:
                k = geom[str(png)]
                tr = trim_span(png, k, skeleton(k["t"])[1], blocks, base, text, idx)
            got.append({"png": png, "n": int(png.stem[4:]), "s": s, "e": e, "conf": conf, "trim": tr,
                        "lead": blocks[0].a + round(ul),
                        "tail": len(osk) - (blocks[-1].a + blocks[-1].size) + round(ur),
                        "dlead": _edge_digits(raw), "dtail": _edge_digits(raw[::-1])})
            cur = e
        labels = ([g["trim"] and g["trim"][0] for g in got] if TRIM
                  else page_labels(got, text, idx))
        for g, gt in zip(got, labels):
            if gt is None:
                WHY['trim-refused' if TRIM else 'uncertain-cut'] += 1
                continue
            old = snap(text, idx[g["s"]], idx[min(g["e"], len(idx) - 1)])
            EDGE_ALL.append((pidx, g["png"].stem, old, gt))
            if old != gt:
                EDGE_DIFF.append((pidx, g["png"].stem, old, gt))
            if len(gt) < min_chars or BRACKET.search(gt):
                WHY['bracket/short-gt'] += 1
                continue
            pairs.append((pidx, g["png"], gt, g["conf"], g["trim"] and g["trim"][1:]))
            kept += 1
        report.append((pidx, "OK", pvotes, kept, len(lines)))
    return pairs, report


def _gap_x(im, lo, hi, prefer):
    """x of the widest ink-free run of columns in [lo, hi] (middle band), the
    run nearest `prefer` on ties; None when no column in the window is clear."""
    import numpy as np
    lo, hi = max(int(lo), 0), min(int(hi), im.width - 1)
    if hi <= lo:
        return None
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h = a.shape[0]
    thr = np.percentile(a, 50) - 40
    ink = (a[int(h * .2):int(h * .8), lo:hi + 1] < thr).sum(0)
    clear = ink <= GAP_INK * (a.shape[0] * .6)   # speckle and hairline serifs, not strokes
    runs, x = [], 0
    while x < len(clear):
        if clear[x]:
            y = x
            while y + 1 < len(clear) and clear[y + 1]:
                y += 1
            runs.append((y - x + 1, -abs(lo + (x + y) / 2 - prefer), lo + (x + y) // 2))
            x = y + 1
        else:
            x += 1
    return max(runs)[2] if runs else None


def trim_span(png, k, osk_idx, blocks, base, text, idx):
    """-> (label, x_left, x_right) or None.

    The label is the run of WHOLE text words from the first word whose first
    letter the anchor read matched to the last word whose last letter it
    matched; the image is cut at the clear gap just outside those two letters
    (the read's per-char x). Edge words the read missed or half-matched are
    left out of BOTH label and image, so no break word is ever assigned by
    guesswork (page_labels() measured ~7 % wrong edges per side)."""
    from PIL import Image
    t, c = k["t"], k.get("c")
    if not c or len(c) != len(t):
        return None
    ref2osk = {}
    for b in blocks:
        for j in range(b.size):
            ref2osk[base + b.b + j] = b.a + j
    s, e = min(ref2osk), max(ref2osk) + 1
    sk_pos = idx
    # whole tokens of text overlapping [idx[s], idx[e-1]]
    lo, hi = idx[s], idx[e - 1]
    while lo > 0 and not text[lo - 1].isspace():
        lo -= 1
    toks, i = [], lo
    while i <= hi:
        j = i
        while j < len(text) and not text[j].isspace():
            j += 1
        a, z = bisect.bisect_left(sk_pos, i), bisect.bisect_left(sk_pos, j)
        if z > a:
            toks.append((i, j, a, z - 1))       # text span, first/last skeleton letter
        i = j + 1
    ok = [x for x in toks if x[2] >= s and x[3] < e]
    first = next((x for x in ok if x[2] in ref2osk), None)
    last = next((x for x in reversed(ok) if x[3] in ref2osk), None)
    if not first or not last or first[0] >= last[1]:
        return None
    tf, tl = osk_idx[ref2osk[first[2]]], osk_idx[ref2osk[last[3]]]
    while tl + 1 < len(t) and not t[tl + 1].isspace() and not t[tl + 1].isalnum():
        tl += 1                                # trailing punctuation the read saw
    # the label must be what the read saw BETWEEN the two cut letters: a label
    # that runs on into the next line's words (p66 line18) disagrees in length
    lab = text[first[0]:last[1]]
    rs, ls = skeleton(t[tf:tl + 1])[0], skeleton(lab)[0]
    if (not 0.9 <= len(ls) / max(len(rs), 1) <= 1.1
            or difflib.SequenceMatcher(None, rs, ls, autojunk=False).ratio() < TRIM_AGREE):
        return None
    n = len(t.strip())
    pitch = (k["x1"] - k["x0"]) / max(n - 1, 1)
    im = Image.open(png)
    # h64's char x is EARLY: a char's ink spans ~[x + 0.7p, x + 1.7p] (measured
    # 2026-09-27 over 1,868 lines: ink starts 0.6-0.8p right of the first peak,
    # ends 1.7-2.0p right of the last). Without this every right cut fell
    # inside the last word («seli|e», «Chriſ|t»).
    lft = lambda i: c[i] + CHAR_L * pitch
    rgt = lambda i: c[i] + CHAR_R * pitch
    prev = next((i for i in range(tf - 1, -1, -1) if not t[i].isspace()), None)
    nxt = next((i for i in range(tl + 1, len(t)) if not t[i].isspace()), None)
    lo = max(lft(tf) - 1.1 * pitch, rgt(prev) if prev is not None else -1)
    hi = min(rgt(tl) + 1.1 * pitch, lft(nxt) if nxt is not None else 1e9)
    xl = _gap_x(im, lo, lft(tf), lft(tf))
    xr = _gap_x(im, rgt(tl), hi, rgt(tl))
    if xl is None or xr is None or xr - xl < 10 * pitch:
        return None
    return lab, xl, xr


def _letters(text, a, b, sk_pos):
    """Skeleton letters inside text[a:b] (sk_pos = sorted idx map)."""
    return bisect.bisect_left(sk_pos, b) - bisect.bisect_left(sk_pos, a)


def _edge_digits(raw):
    """Digits the OCR shows before its first letter (pass raw[::-1] for the end)."""
    n = 0
    for ch in raw:
        if ch.isalpha():
            break
        n += ch.isdigit()
    return n


def page_labels(got, text, idx):
    """Labels for one page's aligned lines, cutting each LINE BREAK once.

    The alignment only fixes the letters it matched in >3-letter blocks; what
    lies between line n's last matched letter (A) and line n+1's first (B) is
    unassigned. snap() widened each line to whole words on its own, which (1)
    labelled a word the print splits over a break (john p80 «Vitnisbu|rd»)
    WHOLE on both lines, (2) let one stray OCR letter pull a neighbour line's
    word in (p80 line14 «uad» -> «Liosinu»), and (3) always swallowed the word
    AFTER a cleanly matched end (it snapped from idx[e], the next letter).

    Here consecutive aligned lines share one cut c in [A, B], at a word
    boundary (space, or just after '/'), chosen so the letters (and numerals,
    which the letters-only skeleton cannot see) on each side best match the
    OCR's unmatched tail of line n and lead of line n+1. No boundary in
    [A, B] means both edges sit in one word: the print split it there, and
    the cut goes mid-word in proportion to tail:lead. A line with no aligned
    neighbour on a side gets its partial word completed plus at most two whole
    words, by the same letter-count evidence from its own OCR alone.
    A break whose best cut beats the runner-up by less than DROP_MARGIN
    letters is not decided by the evidence: both lines come back None.
    Scored against the crop reads of the same line images: --edge-diff."""
    n_text = len(text)

    def boundary(c):
        return (c <= 0 or c >= n_text or text[c - 1].isspace() or text[c - 1] == "/"
                or text[c].isspace())

    def L(a, b):
        return _letters(text, a, b, idx)

    def D(a, b):
        return sum(ch.isdigit() for ch in text[a:b])

    def fit(a, b, letters, digits):
        return abs(L(a, b) - letters) + 0.5 * abs(D(a, b) - digits)

    cuts = [[idx[g["s"]], idx[g["e"] - 1] + 1] for g in got]
    joined, unsure = set(), set()
    for k in range(1, len(got)):
        p, g = got[k - 1], got[k]
        A, B = cuts[k - 1][1], cuts[k][0]
        if g["n"] != p["n"] + 1 or B < A:
            continue
        cands = [c for c in range(A, B + 1) if boundary(c)]
        if cands:
            cost = sorted((fit(A, c, p["tail"], p["dtail"]) + fit(c, B, g["lead"], g["dlead"]), c)
                          for c in cands)
            c = cost[0][1]
            # runner-up = best cut that splits the LETTERS differently (the cut at
            # a space and the one just after it are the same split, always tied)
            rival = [x for x, cc in cost if (L(A, cc), D(A, cc)) != (L(A, c), D(A, c))]
            if rival and rival[0] - cost[0][0] < DROP_MARGIN:
                unsure |= {k - 1, k}
        else:
            t, l = p["tail"], g["lead"]
            c = A + round((B - A) * (t / (t + l) if t + l else 0.5))
        cuts[k - 1][1] = cuts[k][0] = c
        joined |= {(k - 1, "end"), (k, "start")}

    for k, g in enumerate(got):
        a, b = cuts[k]
        if (k, "start") not in joined:
            q = a
            while q > 0 and not boundary(q):
                q -= 1
            cands = [q]
            for _ in range(2):
                while q > 0 and text[q - 1].isspace():
                    q -= 1
                if q <= 0:
                    break
                q -= 1
                while q > 0 and not boundary(q):
                    q -= 1
                cands.append(q)
            a = min(cands, key=lambda c: (fit(c, a, g["lead"], g["dlead"]), -c))
        if (k, "end") not in joined:
            q = b
            while q < n_text and not boundary(q):
                q += 1
            cands = [q]
            for _ in range(2):
                while q < n_text and text[q].isspace():
                    q += 1
                if q >= n_text:
                    break
                q += 1
                while q < n_text and not boundary(q):
                    q += 1
                cands.append(q)
            b = min(cands, key=lambda c: (fit(b, c, g["tail"], g["dtail"]), c))
        cuts[k] = [a, b]
    return [None if k in unsure else text[a:b].strip() for k, (a, b) in enumerate(cuts)]


def selftest(pg, cache, text, skel, idx, geom=None):
    """Known-bad control: the same pages against a reference whose verses are
    shuffled must yield (almost) no pairs; the real reference must yield many."""
    import random
    pg = dict([(i, d) for i, d in pg.items()
               if all(str(l) in cache for l in lines_of(d))][:20])
    good, _ = align(pg, cache, text, skel, idx, geom=geom)
    words = text.split(" ")
    chunks = [" ".join(words[i:i + 3]) for i in range(0, len(words), 3)]
    random.Random(1).shuffle(chunks)
    bad_text = " ".join(chunks)
    bsk, bidx = skeleton(bad_text)
    bad, _ = align(pg, cache, bad_text, bsk, bidx, geom=geom)
    print(f"selftest: real ref {len(good)} pairs, shuffled ref {len(bad)} pairs")
    ok = len(good) > 200 and len(bad) < len(good) * 0.02
    print("selftest", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def load_reads():
    """(idx, 'lineNN') -> a model's crop read of that very line image."""
    work = Path(r"C:/Projects/Hexapla-releases/_work")
    reads = {}
    for f in work.glob("*_p*_CROP_READ_CHUNK*.md"):
        m = re.match(r"(\w+?)_p(\d+)_CROP_READ_CHUNK\d+\.md$", f.name)
        if not m:
            continue
        for ln in f.read_text(encoding="utf-8").splitlines():
            mm = re.match(r"(line\d+)\s*\|\s*(.*)$", ln)
            if mm and "## NUMERALS" not in ln:
                reads.setdefault((int(m.group(2)), mm.group(1)), mm.group(2))
    return reads


def edge_diff():
    """Score snap() vs label_span() labels against the crop reads of the same
    line image, on the labels where the two differ. Edge agreement = the read's
    first/last 10 skeleton letters vs the label's."""
    reads = load_reads()
    def edge(lbl, rd, first):
        a, b = skeleton(lbl)[0], skeleton(rd)[0]
        a, b = (a[:10], b[:10]) if first else (a[-10:], b[-10:])
        return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    score = Counter()
    for pidx, ln, old, new in EDGE_DIFF:
        rd = reads.get((pidx, ln))
        if rd is None:
            continue
        for first in (True, False):
            o, n = edge(old, rd, first), edge(new, rd, first)
            k = "start" if first else "end"
            v = "new" if n > o + 0.05 else "old" if o > n + 0.05 else "tie"
            score[(k, v)] += 1
            if v == os.environ.get("KGT_SHOW") and score[(k, v)] <= 6:
                print(f"  [{k} {v}] p{pidx} {ln}\n    read | {rd}\n    snap | {old}\n    span | {new}")
    # absolute: a label edge is RIGHT when its first/last 10 letters match the
    # read's at >= 0.8 - over every labelled line with a read, not only moved ones
    ok, tot = Counter(), 0
    for pidx, ln, old, new in EDGE_ALL:
        rd = reads.get((pidx, ln))
        if rd is None:
            continue
        tot += 1
        for first in (True, False):
            k = "start" if first else "end"
            ok[("old", k)] += edge(old, rd, first) >= 0.8
            ok[("new", k)] += edge(new, rd, first) >= 0.8
    if tot:
        print(f"absolute edge agreement with the read, {tot} labelled lines: "
              f"snap start {ok[('old', 'start')] / tot:.1%} end {ok[('old', 'end')] / tot:.1%} | "
              f"new start {ok[('new', 'start')] / tot:.1%} end {ok[('new', 'end')] / tot:.1%}")
    n = sum(1 for p, l, _, _ in EDGE_DIFF if (p, l) in reads)
    print(f"edge-diff: {len(EDGE_DIFF)} labels moved; {n} have a crop read")
    for k in ("start", "end"):
        print(f"  {k:5s}: new better {score[(k, 'new')]}, old better {score[(k, 'old')]}, "
              f"tie {score[(k, 'tie')]}")
    return score


def check_reads(pairs):
    """Independent control on the labels: where a line-addressed crop read
    exists (_work/<book>_p<idx>_CROP_READ_CHUNK*.md, a model reading the SAME
    lineNN.png), the label must agree with it. A misaligned label agrees with
    the read of a NEIGHBOURING line instead. Only same-kit reads count."""
    reads = load_reads()
    rs, nb = [], []
    for pidx, png, gt, *_ in pairs:
        r = reads.get((pidx, png.stem))
        if r is None:
            continue
        g = skeleton(gt)[0]
        own = difflib.SequenceMatcher(None, g, skeleton(r)[0], autojunk=False).ratio()
        n = int(png.stem[4:])
        nbr = max((difflib.SequenceMatcher(None, g, skeleton(reads[(pidx, f"line{k:02d}")])[0],
                                           autojunk=False).ratio()
                   for k in (n - 1, n + 1) if (pidx, f"line{k:02d}") in reads), default=0)
        rs.append(own)
        if nbr > own:
            nb.append((pidx, png.stem, own, nbr, gt[:50]))
    if not rs:
        print("check-reads: no overlapping crop reads")
        return 1
    rs.sort()
    print(f"check-reads: {len(rs)} labels vs crop reads; median agreement "
          f"{rs[len(rs) // 2]:.2f}, 5th pct {rs[len(rs) // 20]:.2f}; "
          f"{len(nb)} agree better with a NEIGHBOUR line")
    for x in nb[:15]:
        print(f"  p{x[0]} {x[1]} own {x[2]:.2f} nbr {x[3]:.2f} | {x[4]}")
    return 0 if len(nb) <= len(rs) * 0.01 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--kraken-ocr", metavar="DEVICE", help="cpu or cuda:0 (kraken venv)")
    ap.add_argument("--limit", type=int, help="--kraken-ocr: first N pages only")
    ap.add_argument("--with-reads", action="store_true",
                    help="--kraken-ocr: only pages that have crop reads (--edge-diff's denominator)")
    ap.add_argument("--anchor", choices=["isfrak", "h64"], default="isfrak")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-reads", action="store_true")
    ap.add_argument("--out", help="--apply target dir (default research/_prep/kraken_gt)")
    ap.add_argument("--trim", action="store_true",
                    help="with --anchor h64: label only matched whole words, crop the image to them")
    ap.add_argument("--edge-diff", action="store_true",
                    help="score page_labels() vs snap() edges against the crop reads")
    a = ap.parse_args()
    pg = pages()
    print(f"{len(pg)} vol-3 pages with line crops, idx {min(pg)}-{max(pg)}")
    if a.kraken_ocr:
        if a.with_reads:
            have = {i for i, _ in load_reads()}
            pg = {i: d for i, d in pg.items() if i in have}
            print(f"--with-reads: {len(pg)} pages")
        run_kraken_ocr(pg, a.kraken_ocr, a.limit)
        return 0
    if a.ocr:
        run_ocr(pg)
        return 0
    cache, geom = load_cache(), None
    if a.trim:
        global TRIM
        if a.anchor != "h64":
            ap.error("--trim needs --anchor h64 (per-char x)")
        TRIM = True
    if a.anchor == "h64":
        geom = load_kcache()
        cache = {k: v["t"] for k, v in geom.items()}
    text, skel, idx = reference()
    print(f"reference: {len(text)} chars")
    if a.selftest:
        return selftest(pg, cache, text, skel, idx, geom)
    pairs, report = align(pg, cache, text, skel, idx, geom=geom)
    if a.check_reads:
        return check_reads(pairs)
    if a.edge_diff:
        print(f"of {len(pairs)} pairs")
        edge_diff()
        for x in EDGE_DIFF[:: max(len(EDGE_DIFF) // 12, 1)]:
            print(f"  p{x[0]} {x[1]}\n    snap | {x[2]}\n    span | {x[3]}")
        return 0
    located = [r[0] for r in report if r[1] == "OK"]
    held = set(located[5::10])
    ntr = sum(1 for p in pairs if p[0] not in held)
    print(f"pages: {Counter(r[1] for r in report)}")
    print(f"pairs: {len(pairs)} ({ntr} train, {len(pairs) - ntr} eval on pages {sorted(held)})")
    tot = sum(r[4] for r in report if r[1] == "OK")
    print(f"coverage of located pages' crops: {len(pairs)}/{tot}")
    for r in report:
        if r[1] == "OK" and r[3] < r[4] * 0.5:
            print(f"  low page p{r[0]}: kept {r[3]}/{r[4]} votes {r[2]}")
    print(f"line drops: {dict(WHY)}")
    print("unlocated:", [r[0] for r in report if r[1] == "UNLOCATED"])
    for p in pairs[:: max(len(pairs) // 6, 1)][:6]:
        print(f"  sample p{p[0]} {p[1].name} {p[3]:.2f} | {p[2]}")
    if not a.apply:
        print("dry run - pass --apply to write pairs")
        return 0
    global OUT
    if a.out:
        OUT = Path(a.out)
    if OUT.exists():
        shutil.rmtree(OUT)
    for sub in ("train", "eval"):
        (OUT / sub).mkdir(parents=True)
    from PIL import Image
    for pidx, png, gt, _, box in pairs:
        d = OUT / ("eval" if pidx in held else "train")
        stem = f"p{pidx}_{png.stem}"
        if box:
            im = Image.open(png)
            im.crop((box[0], 0, box[1] + 1, im.height)).save(d / f"{stem}.png")
        else:
            shutil.copyfile(png, d / f"{stem}.png")
        (d / f"{stem}.gt.txt").write_text(gt + "\n", encoding="utf-8")
    print(f"wrote {len(pairs)} pairs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
