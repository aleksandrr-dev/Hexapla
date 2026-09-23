# -*- coding: utf-8 -*-
"""Pre-cut Karl XII 1703 apocrypha pages into per-column line crops.

    python tools/prep_kxii.py --pages 636-640 --out judith
    python tools/prep_kxii.py --pages 637 --out probe --debug

Sibling of tools/prep_chunk.py (Þorláksbiblía). Same idea — hand the
transcriber correctly-framed pixels so tokens go on READING, not hunting — but
the geometry is entirely different and none of prep_chunk's assumptions hold.

## ⚠ WHY THIS IS A SEPARATE TOOL, not a flag on prep_chunk

Four things differ, each found the hard way on 2026-08-11:

 1. **The source is a photograph of an OPENING, not a page.** litteraturbanken
    serves a JPEG showing the target page plus part of its neighbour, the book
    edges, the binding and the dark table behind it. The target page is the one
    fully enclosed by its printed frame; which SIDE it sits on alternates.
 2. **The text is TWO COLUMNS split by a printed vertical rule**, with narrow
    marginal-note columns outside the frame on both sides. prep_chunk takes the
    span from first to last inked column, which here swallows both columns and
    both margins and then merges lines across the gutter.
 3. **Fixed-percentile binarisation does not transfer.** prep_chunk's 12th
    percentile is tuned to the Þorláks PDF renders; on these scans the dark
    background dominates it and the column profile collapses to noise. Otsu is
    used here instead.
 4. **The scans are SKEWED by a fraction of a degree.** That is enough to smear
    a 3 px vertical rule across ~10 columns over 2000 px of height, so a
    full-height projection finds nothing — which is exactly what happened for
    several attempts before the cause was spotted. Rules are therefore detected
    by VOTING over short y-bands, where drift is under 2 px.

## How the page is located

Vote for near-solid dark columns in 250 px bands, then look for a triple
(left frame, centre rule, right frame) where the centre sits at the midpoint
within tolerance and the width is plausible for this book. Verified on printed
637 (rules at x≈320 / 1028 / 1732) and printed 680 (≈805 / 1535 / 2269).

⚠ If no triple is found the page is SKIPPED and reported, never guessed. A
mis-located frame yields crops that silently omit a column of scripture.

## ⚠ Fetching

Images come from litteraturbanken; **image number = printed page + 134**
(verified 636->0770, 637->0771, 658->0792, 659->0793, 680->0814, 743->0877).
Re-verify at both ends of a range before bulk fetching.
⚠⚠ **A browser User-Agent is REQUIRED** — a default script UA gets 403, which
in July was misread as "their images are broken" and cost an apology to their
editor. Fetch politely: sequential, cached to disk, no hammering.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
CACHE = RESEARCH / "kxii_pages"
OUT = RESEARCH / "_prep_kxii"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
URL = ("https://litteraturbanken.se/txt/lb2431561/lb2431561_5/"
       "lb2431561_5_{n:04d}.jpeg")
PAGE_OFFSET = 134

INK = 140              # grey level counted as ink on these scans
BAND = 250             # y-band height for skew-tolerant rule voting
MIN_W, MAX_W = 1300, 1750   # plausible frame width in px
MID_TOL = 60           # how far the centre rule may sit off the midpoint
READ_ZOOM = 2.0        # crops are already ~2500px wide; modest upscale is enough

# recover_lines() — the additive second pass. See its docstring for why the
# span/fill constants are applied at a FIXED resampled width (they are
# prep_chunk.py's measured values, valid only at the ~512 px block they were
# tuned at) while the height constants are relative to the page's OWN measured
# line box, which varies with the scan.
SHORT_W = 512
SHORT_MAX_SPAN = 0.60   # ink must occupy under this fraction of column width
SHORT_MIN_FILL = 0.35   # ...and fill that span this solidly (words, not scatter)
SHORT_CLUSTER_GAP = 12  # columns further apart than this are separate clusters
SHORT_MIN_SPAN = 8      # a cluster narrower than this is a speck, not a word
FULL_H_FRAC = 0.55      # a gap run this tall (x median line box) IS a line
SHORT_H_FRAC = 0.25     # ...below this it is not even a candidate
SPLIT_H_FRAC = 1.40     # a run taller than this covers >1 missed line — split it


def fetch(printed):
    CACHE.mkdir(parents=True, exist_ok=True)
    n = printed + PAGE_OFFSET
    p = CACHE / f"p{n:04d}.jpg"
    if not p.exists():
        req = urllib.request.Request(URL.format(n=n), headers={"User-Agent": UA})
        p.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        print(f"  fetched image {n} ({p.stat().st_size/1e6:.1f} MB)")
    return p


def rule_candidates(im):
    W, H = im.size
    votes = {}
    for y0 in range(int(H * 0.18), int(H * 0.78), BAND):
        b = im.crop((0, y0, W, y0 + BAND)).point(lambda v: 255 if v <= INK else 0)
        cov = [c / 255.0 for c in b.resize((W, 1)).tobytes()]
        for x, c in enumerate(cov):
            if c > 0.90 and 60 < x < W - 60:
                votes[x] = votes.get(x, 0) + 1
    groups, s, p = [], None, None
    for x in sorted(votes):
        if s is None:
            s = x
        elif x > p + 6:
            groups.append((s + p) // 2)
            s = x
        p = x
    if s is not None:
        groups.append((s + p) // 2)
    return groups


def find_frame(im):
    """-> (left, centre, right) or None. Never guesses.

    ⚠⚠ GEOMETRY ALONE CANNOT PICK THE FRAME — this took three attempts.
    The marginal-note columns are ruled too and are ALSO symmetric about the
    same centre rule, so a midpoint test selects the outer pair (on printed
    637: 158/1017/1874 instead of the true 334/1030/1746, putting blank margin
    in the left crop and clipping the right column). Preferring the narrowest
    triple then overshoots onto a spurious pair straddling the facing page
    (1043/1733/2370).

    What actually identifies the frame is a PROPERTY OF THE RESULT, not of the
    rules: the correct triple is the one whose two columns each yield a similar,
    large number of text lines — because they are two columns of one page.
    So every candidate triple is scored by running line detection on both
    columns and comparing. Wrong triples give lopsided counts (41/50, 54/15);
    the right one gives ~50/50.
    """
    c = rule_candidates(im)
    H = im.size[1]
    # ⚠ Provisional band only. The real one (text_band) is derived FROM the
    # frame, so it cannot be used to find it; scoring only compares candidates
    # against each other, for which a rough band is sufficient.
    y0, y1 = int(H * SCORE_BAND[0]), int(H * SCORE_BAND[1])
    best = None
    for i, L in enumerate(c):
        for R in c[i + 1:]:
            w = R - L
            if not (MIN_W <= w <= MAX_W):
                continue
            mid = (L + R) / 2
            for C in c:
                if not (L < C < R and abs(C - mid) <= MID_TOL):
                    continue
                if min(C - L, R - C) < 550:
                    continue
                nl = len(line_rects(im, L + 6, C - 6, y0, y1))
                nr = len(line_rects(im, C + 6, R - 6, y0, y1))
                if min(nl, nr) < 20:
                    continue
                # symmetry first, then total coverage
                score = (abs(nl - nr), -(nl + nr))
                if best is None or score < best[0]:
                    best = (score, L, C, R)
    return best[1:] if best else None


XBAND = 150            # x-band width for skew-tolerant horizontal-rule voting
SCORE_BAND = (0.115, 0.86)   # provisional band, used ONLY to score frames


def hrules(im, x0, x1):
    """Horizontal rule groups between x0..x1, as (top, bottom) row pairs.

    Same skew-tolerant voting as rule_candidates() and for the same reason: a
    fraction of a degree of skew smears a 3 px rule across ~10 rows over the
    frame's width, so a full-width row projection finds nothing.
    """
    H = im.size[1]
    votes, nb = {}, 0
    for bx in range(x0, x1 - XBAND, XBAND):
        nb += 1
        b = im.crop((bx, 0, bx + XBAND, H)).point(
            lambda v: 255 if v <= INK else 0)
        cov = [c / 255.0 for c in b.resize((1, H)).tobytes()]
        for y in range(int(H * 0.03), int(H * 0.97)):
            if cov[y] > 0.85:
                votes[y] = votes.get(y, 0) + 1
    groups, cur = [], []
    for y in sorted(votes):
        if cur and y - cur[-1] > 20:
            groups.append(cur)
            cur = []
        cur.append(y)
    if cur:
        groups.append(cur)
    return [(g[0], g[-1]) for g in groups
            if sum(votes[y] for y in g) >= max(nb, 1) * 0.6]


def text_band(im, L, C, R):
    """(y0, y1, note) — the vertical extent to cut lines from.

    ⚠⚠ THE FIXED 0.115H..0.86H BAND THIS REPLACED WAS LOSING SCRIPTURE ON EVERY
    PAGE. Measured 2026-08-14 on printed 637/700/746: the printed frame's head
    separator sits at 0.073-0.096H and its foot rule at 0.883-0.895H, so a band
    starting at 0.115H cut through the third line of each column and dropped the
    two above it outright, while 0.86H dropped about two more at the foot. On
    printed 746 the lost pair is «wat och prisat ware titt härliga och helga
    namn;» / «och warde prisat och vphögt ewinnerliga.» — read off the scan by
    eye, plainly scripture. Four lines per column, two columns, ~111 pages: of
    the order of 800 lines that no crop would ever have shown a transcriber.
    ▶ **No downstream check could have caught it.** The verse numerals went with
    the lines, so a chunk simply never sees them; the corpus audit can only
    count what was transcribed, and the crops themselves look perfect.

    So the band is DERIVED per page from the frame's own horizontal rules:
    from the top frame rule (the running head is deliberately INCLUDED — it is
    free navigation evidence and cannot displace scripture) down to the last
    foot rule (which keeps end-of-book colophons such as «Ände på Gamla
    Testamentets Böcker»).

    ⚠ The fallback fractions are deliberately WIDER than any measured page
    rather than average: over-cutting costs a few blank crops, under-cutting
    costs text, and only one of those is recoverable.
    """
    H = im.size[1]
    rules = hrules(im, L + 12, C - 12) or hrules(im, C + 12, R - 12)
    top = [g for g in rules if 0.04 * H <= g[0] <= 0.20 * H]
    bot = [g for g in rules if 0.75 * H <= g[0] <= 0.95 * H]
    note = []
    if top:
        y0 = top[0][1] + 2
    else:
        y0, _ = int(H * 0.070), note.append("top rule not found — fallback")
    if bot:
        y1 = bot[-1][0] - 2
    else:
        y1, _ = int(H * 0.900), note.append("foot rule not found — fallback")
    return y0, y1, "; ".join(note) or "frame-derived"


def trim_column(im, x0, x1, y0, y1):
    """Shrink a column to its actual inked extent.

    ⚠ The chosen frame triple can sit on a MARGINAL rule rather than the true
    frame rule (printed 637 selects R=1865, the right margin rule, not 1746),
    which would drag the note column into the crop — the exact thing this tool
    exists to prevent. Trimming to real ink makes the crop independent of which
    rule was matched.
    """
    band = im.crop((x0, y0, x1, y1)).point(lambda v: 255 if v <= INK else 0)
    cov = [c / 255.0 for c in band.resize((x1 - x0, 1)).tobytes()]
    if not cov:
        return x0, x1
    mx = max(cov)
    hits = [i for i, c in enumerate(cov) if c > mx * 0.35]
    if len(hits) < 20:
        return x0, x1
    return x0 + hits[0] - 6, x0 + hits[-1] + 6


def line_rects(im, x0, x1, y0, y1, frac=0.62):
    """Line rectangles from the row-mean ink profile.

    ⚠⚠ IT AVERAGES EACH ROW TO ONE PIXEL (`b.resize((1, h))`) AND THRESHOLDS THE
    MEAN. That silently DROPS SHORT LINES — a one-word line leaves ~95% of the
    row as blank paper, so its mean never crosses any 'ink' cutoff. Proven on
    the Þorláks scans, where two real lines of scripture (2 Peter 2:9 «sins.»
    and 2:22 «aptur j Saurnum.») got NO CROP AT ALL from the identical code.

    ▶ **No verse-count audit can catch it.** The verse numeral survives on the
    neighbouring line; only words vanish, mid-verse, and the sentence often
    still parses.
    ▶ ⚠ A TWO-COLUMN LAYOUT MAKES IT WORSE: every column end is another place a
    sentence can spill one short word onto a line of its own — and this page has
    twice as many column ends as a single-column one.

    ✅ **COMPENSATED SINCE 2026-08-14 by short_line_rects(), which main() merges
    in.** This function is deliberately left as-is: it is reliable for normal
    lines, and the recovery runs as an ADDITIVE second pass, so it can only add
    lines, never lose one.

    ⚠ Do NOT "fix" it by re-thresholding rows. Tried and reverted on the sibling
    tool: measured, an inter-line gap carries MORE ink (0.081 of block width)
    than a whole short line (0.054), because descenders hang into it. No global
    row threshold separates them; the attempt collapsed a 52-line page to 14.
    """
    col = im.crop((x0, y0, x1, y1))
    sm = col.resize((max(col.width // 4, 1), col.height))
    b = sm.point(lambda v: 255 if v <= INK else 0)
    rows = [c / 255.0 for c in b.resize((1, sm.height)).tobytes()]
    s = sorted(rows)
    lo, hi = s[len(s) // 100], s[-max(len(s) // 50, 1)]
    if hi - lo < 0.02:
        return []
    thr = lo + (hi - lo) * frac
    out, st = [], None
    for i, v in enumerate(rows):
        if v > thr and st is None:      # rows list is INK coverage: high = text
            st = i
        elif v <= thr and st is not None:
            if i - st >= 12:
                out.append((y0 + st - 9, y0 + i + 9))
            st = None
    if st is not None and len(rows) - st >= 12:
        out.append((y0 + st - 4, y1))
    return out


def expected_lines(lines, y0, y1):
    """How many lines the column SHOULD hold, derived from its own type pitch.

    The honest guard against silent under-detection: band height / type pitch,
    which does not trust the detector's own tally. Measured on printed
    637/700/746, pitch is 36-38 px in every column of every page, so a 2550 px
    band holds ≈ 69 lines.

    ⚠ THE PITCH ESTIMATOR IS A LOW PERCENTILE, NOT THE MEDIAN. Using the median
    made the guard self-defeating and it passed a column it should have caught
    (printed 641 L, 64 lines against a true ~79): **a missed line can only ever
    INFLATE a top-to-top gap, never shrink one**, so on a badly-detected column
    the median pitch drifts up, the expected count drifts down to meet the
    detector, and the check congratulates itself. The 25th percentile is close
    to the true single-line pitch as long as most lines are found, and it
    degrades in the safe direction — it over-estimates how many lines there
    should be, which raises a question instead of hiding one.
    """
    tops = [a for a, b in lines]
    p = sorted(b - a for a, b in zip(tops, tops[1:]))
    if not p:
        return 0, 0
    pitch = p[max(len(p) // 4, 0)]
    return (y1 - y0) // pitch if pitch else 0, pitch


def recover_lines(im, x0, x1, y0, y1, lines):
    """Recover lines that line_rects() drops. ADDITIVE — never edits.

    ⚠⚠ THIS IS NOT A SHORT-LINE PASS. It began as a port of prep_chunk's
    `short_line_rects`, and measuring it on printed 637 proved the Karl XII
    scans have a LARGER problem than the Þorláks ones: at frac 0.62 the row-mean
    detector finds 40-54 lines in a column that holds ~69 (2550 px band, 37 px
    pitch — see expected_lines). The gaps it leaves are 33-44 rows tall, and a
    LINE here is 37 rows: these are whole missed lines, not one-word spills.
    Verified by eye — the run at y1174 in column L of printed 637 is
    «tolftusend skyttor til häst.», a full line of Judith with no crop at all.

    ▶ So the run in a gap is classified by HEIGHT first, against the page's own
    median line box:
      - **>= FULL_H_FRAC of a line box → a missed line**, accepted at any width.
        Descender scatter cannot reach that height; a line can be any width.
      - shorter, but narrow-and-densely-filled → a **short line** (the original
        prep_chunk case: ink contiguous near the margin, not spread scatter).
      - anything else → rejected as scatter.
    A run over SPLIT_H_FRAC covers more than one missed line and is divided
    evenly, so the transcriber still gets one crop per line.

    ⚠ WHY NOT JUST LOWER `frac`. Swept on three pages: dropping it to 0.30-0.40
    does raise the count, but on printed 637-R and 746-R the tallest detected
    box goes 37 -> 103-116 px, i.e. it starts WELDING lines together. Under-
    detection is recoverable (this function); merging is not, because the
    evidence that two lines existed is gone. So the primary detector keeps its
    proven conservative threshold and this pass adds what it missed — the same
    can-only-add discipline that makes prep_chunk's version safe.

    ⚠ MIN-MAX SPAN IS NOT ROBUST for the short-line branch — it was the first
    version on the sibling tool and failed on the very line it existed for: a
    few specks of page-edge ink stretched min-max to 97% of the width and pushed
    fill to 0.09. **Cluster the ink columns and judge the LARGEST cluster**, so
    stray marks (and on THESE scans, bleed from the printed rules and from the
    facing page) cannot veto a real line.

    ⚠ DIFFERENCE FROM prep_chunk: the head and tail of the column are searched
    too, not only the gaps BETWEEN detected lines. On a two-column page the
    likeliest place for a spilled short line is the FOOT OF A COLUMN — a tail
    region, which prep_chunk's between-lines-only loop cannot see.
    """
    if len(lines) < 2:
        return []
    _, pitch = expected_lines(lines, y0, y1)
    box = sorted(b - a for a, b in lines)[len(lines) // 2]
    full_h = max(int(box * FULL_H_FRAC), 6)
    min_h = max(int(box * SHORT_H_FRAC), 5)

    col = im.crop((x0, y0, x1, y1))
    b = col.resize((SHORT_W, col.height)).point(lambda v: 255 if v <= INK else 0)
    px = b.load()
    w, h = b.size

    # Regions to search: head, the gaps between detected lines, and the tail.
    # Rects carry ±9 px of padding, so consecutive ones can overlap; a negative
    # or tiny span is simply skipped by the length test.
    bounds = [(0, lines[0][0] - y0)]
    for a, c in zip(lines, lines[1:]):
        bounds.append((a[1] - y0, c[0] - y0))
    bounds.append((lines[-1][1] - y0, h))

    out = []
    for g0, g1 in bounds:
        g0, g1 = max(0, g0), min(h, g1)
        if g1 - g0 < min_h:
            continue
        rows = [(y, [x for x in range(w) if px[x, y] == 255])
                for y in range(g0, g1)]
        run, start, last = [], None, None
        for y, cols in rows + [(None, [])]:
            if cols and start is None:
                start, run, last = y, [cols], y
            elif cols and start is not None:
                run.append(cols)
                last = y
            elif not cols and start is not None:
                end = last + 1                      # sentinel carries y=None
                n = len(run)
                if n >= min_h:
                    allc = sorted({c for r in run for c in r})
                    clusters, cur = [], [allc[0]]
                    for c in allc[1:]:
                        if c - cur[-1] <= SHORT_CLUSTER_GAP:
                            cur.append(c)
                        else:
                            clusters.append(cur)
                            cur = [c]
                    clusters.append(cur)
                    big = max(clusters, key=len)
                    span = big[-1] - big[0] + 1
                    fill = len(big) / span
                    shortline = (SHORT_MIN_SPAN <= span <= w * SHORT_MAX_SPAN
                                 and fill >= SHORT_MIN_FILL)
                    if n >= full_h or shortline:
                        parts = max(round(n / pitch), 1) if n > box * SPLIT_H_FRAC else 1
                        step = n / parts
                        for k in range(parts):
                            out.append((y0 + start + int(k * step) - 9,
                                        y0 + start + int((k + 1) * step) + 9))
                start, run = None, []
    return out


def gap_report(lines):
    """Flag pitch anomalies — a line the detector may still have missed.

    A dropped line shows as ~2x the median top-to-top pitch. Legitimate 2x+
    gaps exist (a running head, a chapter heading, the foot of a short column),
    so this REPORTS and never edits: it says where to look at `page.png`.
    """
    tops = [r[0] for r in lines]
    pitch = [b - a for a, b in zip(tops, tops[1:])]
    if not pitch:
        return []
    med = sorted(pitch)[len(pitch) // 2]
    return [(i, p, p / med) for i, p in enumerate(pitch) if p > med * 1.6]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="PRINTED page(s), e.g. 637 or 636-646")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom", type=float, default=READ_ZOOM)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--gaps", action="store_true",
                    help="report pitch anomalies — where a short line may STILL "
                         "have been dropped (see line_rects docstring)")
    a = ap.parse_args()

    lo, _, hi = a.pages.partition("-")
    pages = list(range(int(lo), int(hi or lo) + 1))
    outdir = OUT / a.out
    outdir.mkdir(parents=True, exist_ok=True)
    man = ["# Karl XII 1703 — prep manifest", "",
           "Pre-cut by `tools/prep_kxii.py`. **Pixels only — nothing here was "
           "read by a machine.**", "",
           "⚠ Line segmentation is a heuristic; line N is not verse N. Confirm "
           "against `page.png`. The marginal note columns are OUTSIDE the frame "
           "and are deliberately not cut — they are apparatus, not scripture.",
           "", "⚠ `recovered` counts SHORT LINES added by the second-pass "
           "detector (`short_line_rects`). They are real scripture the row-mean "
           "detector drops — most often at the FOOT of a column, where a "
           "sentence spills one word. A page showing `-` is not necessarily "
           "clean; it may simply have had no short lines.",
           "", "⚠ The `band` column is DERIVED from the page's own printed "
           "frame rules. A row reading `fallback` means the rules were not "
           "found on that page and a conservative fixed band was used — check "
           "`page.png` there especially, at BOTH the head and the foot.",
           "", "| printed | image | frame x | band y | lines L | lines R | "
           "recovered |", "|---|---|---|---|---|---|---|"]
    skipped, short_cols = [], []
    for printed in pages:
        src = fetch(printed)
        im = Image.open(src).convert("L")
        fr = find_frame(im)
        if not fr:
            skipped.append(printed)
            print(f"  p{printed}: NO FRAME FOUND — skipped")
            continue
        L, C, R = fr
        H = im.size[1]
        y0, y1, bnote = text_band(im, L, C, R)
        d = outdir / f"p{printed}"
        d.mkdir(exist_ok=True)
        # page.png must show at least the whole cut band, or it cannot serve as
        # the check on the crops that the manifest tells the transcriber it is.
        Image.open(src).crop((L - 40, max(y0 - 60, 0), R + 40,
                              min(y1 + 60, H))).save(d / "page.png")
        counts, rec = [], []
        for tag, (bx0, bx1) in (("L", (L + 6, C - 6)), ("R", (C + 6, R - 6))):
            cx0, cx1 = trim_column(im, bx0, bx1, y0, y1)
            rects = line_rects(im, cx0, cx1, y0, y1)
            # Recover one-word lines the mean-threshold detector drops, and
            # merge them into reading order. See short_line_rects(): on the
            # sibling print this is the difference between having two real
            # lines of scripture and silently losing both, invisibly to every
            # verse-count audit.
            extra = recover_lines(im, cx0, cx1, y0, y1, rects)
            exp, _ = expected_lines(rects, y0, y1)
            if extra:
                rects = sorted(rects + extra)
                rec.append(f"{tag}+{len(extra)}")
            counts.append(len(rects))
            # ⚠ The honest completeness check for line DETECTION: a column of
            # this type pitch holds ~exp lines. Falling well short means text is
            # still uncut and therefore untranscribable — it is not a cosmetic
            # warning. (Legitimately short columns exist: a book ends, a chapter
            # heading eats space. Look at page.png before dismissing it.)
            if exp and len(rects) < exp * 0.90:
                short_cols.append(f"p{printed}{tag} {len(rects)}/{exp}")
                print(f"  ⚠ p{printed} {tag}: {len(rects)} lines but pitch "
                      f"implies ~{exp} — CHECK page.png, text may be uncut")
            if a.gaps:
                flags = gap_report(rects)
                print(f"  p{printed} {tag}: {len(rects)} lines, {len(flags)} "
                      f"pitch anomal{'y' if len(flags) == 1 else 'ies'}")
                for i, p, mult in flags:
                    print(f"    after {tag}{i:02d}.png: {p}px = {mult:.2f}x "
                          f"pitch — check page.png for a dropped short line")
            full = Image.open(src)
            for i, (ry0, ry1) in enumerate(rects):
                full.crop((cx0, ry0, cx1, ry1)).resize(
                    (int((cx1 - cx0) * a.zoom), int((ry1 - ry0) * a.zoom))
                ).save(d / f"{tag}{i:02d}.png")
        man.append(f"| {printed} | {printed+PAGE_OFFSET} | {L}/{C}/{R} | "
                   f"{y0}-{y1} ({bnote}) | {counts[0]} | {counts[1]} | "
                   f"{' '.join(rec) or '-'} |")
        print(f"  p{printed}: frame {L}/{C}/{R}, band {y0}-{y1} [{bnote}], "
              f"lines L={counts[0]} R={counts[1]}"
              + (f", recovered {' '.join(rec)}" if rec else ""))
    if skipped:
        man += ["", f"⚠ **SKIPPED (no frame found): {skipped}** — these pages "
                "must be located by hand before they can be transcribed."]
    if short_cols:
        man += ["", "⚠⚠ **COLUMNS UNDER 90% OF THEIR EXPECTED LINE COUNT** "
                "(count/expected, expected = band height / median type pitch): "
                + ", ".join(short_cols) + ". Text is probably still uncut in "
                "these columns — check `page.png` against the crops before "
                "transcribing them, and do not report the chunk complete on the "
                "crops alone."]
    (outdir / "MANIFEST.md").write_text("\n".join(man), encoding="utf-8")
    print(f"\nmanifest: {outdir/'MANIFEST.md'}")


if __name__ == "__main__":
    main()
