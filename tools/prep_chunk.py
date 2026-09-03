# -*- coding: utf-8 -*-
"""Pre-cut a chunk's working set so a transcriber spends tokens READING, not HUNTING.

Model-free: pure geometry (PyMuPDF + Pillow). Needs no GPU, so it runs while a
narration render holds the card.

    python tools/prep_chunk.py --vol 3 --pages 173-177 --out gal
    python tools/prep_chunk.py --vol 3 --pages 202 --out philemon --split

## The problem it solves

Chunk agents in this campaign spend most of their tool calls RENDERING, not
reading: full page at 2.6x to orient, bands at 8.3x to transcribe, word crops
at 40x for a disputed glyph, then re-rendering because the crop was in the
wrong place. Measured on the first wave: 79-200 tool calls and ~230k tokens per
book, and a large share of that was hunting for the right rectangle.

Everything in that hunt is deterministic. This tool does it once, up front:

  · finds the TEXT BLOCK and excludes the marginal apparatus column, so no
    tokens are spent on pixels that are not scripture — and so nobody
    transcribes a cross-reference as a verse (a mistake the brief warns about);
  · finds the text LINES by ink profile and emits each one pre-cropped at
    transcription zoom;
  · emits a per-page orientation image at navigation zoom;
  · writes MANIFEST.md with the folio arithmetic already done.

The agent then opens a directory of correctly-framed lines instead of
discovering the layout for itself, and can re-read ONE line at higher zoom
instead of re-rendering a whole band.

## ⚠ WHAT THIS DOES NOT DO — and must not

It does not read anything. No OCR, no model, no draft text. The campaign's
standing lesson is that plausible text is the failure mode (Glen's 18
fabricated chapters; ru_stress.py's 30 corrupt entries), and a machine-made
draft would anchor a reviewer into rubber-stamping it. This tool hands over
pixels, correctly framed, and nothing else. Reading stays with the transcriber.

⚠ Line detection is a HEURISTIC. It can merge two lines that touch, split a
line with a tall initial, and it treats a decorated drop-cap block as its own
run. The manifest reports the count so an implausible page announces itself;
the agent must still confirm against the page image. Never assume line N of
the crops is verse N of anything.
"""
import argparse
import io
import sys
from pathlib import Path

import fitz
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
OUTROOT = Path(r"C:/Projects/Hexapla-releases/research/_prep")

# idx = 2*folio + C  (verified at both extremes of every volume, 2026-08-10)
FOLIO_C = {1: 14, 2: 6, 3: 0}

READ_ZOOM = 8.3       # native ceiling of these scans; letter-level decisions
PAGE_ZOOM = 2.2       # orientation only — never transcribe at this
PROFILE_ZOOM = 2.0
LINE_FRAC = 0.65      # tuned: 40 lines on v3:202, 51 on v3:178 (0.85 -> 7)

# short_line_rects() — recovering one-word lines the mean threshold drops.
SHORT_INK_CUT = 0.55    # ink cutoff inside the block's own grey range
SHORT_MIN_ROWS = 6      # a real line is at least this tall in profile space
SHORT_MAX_SPAN = 0.60   # ink must occupy under this fraction of block width
SHORT_MIN_FILL = 0.35   # ...and fill that span this solidly (words, not scatter)
SHORT_CLUSTER_GAP = 12  # columns further apart than this are separate clusters
SHORT_MIN_SPAN = 8      # a cluster narrower than this is a speck, not a word

COL_FRAC = 0.72
PAD_Y = 1.6
PAD_X = 2.0


def _gray(page, zoom):
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")


def _runs(vals, frac, min_len):
    """Dark runs, threshold placed adaptively within this page's own range.

    ⚠ ADAPTIVE IS NOT OPTIONAL. These are aged-paper scans: row means on
    v3:202 span 0.51 (text) to 0.79 (blank). A fixed 'dark' cutoff calls the
    whole page one run — which is exactly what a hardcoded threshold did on the
    first attempt here.
    """
    s = sorted(vals)
    lo, hi = s[len(s) // 100], s[-max(len(s) // 50, 1)]
    if hi - lo < 0.02:                       # blank or near-blank page
        return []
    thr = lo + (hi - lo) * frac
    out, start = [], None
    for i, v in enumerate(vals):
        if v < thr and start is None:
            start = i
        elif v >= thr and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(vals) - start >= min_len:
        out.append((start, len(vals)))
    return out


def text_block(page):
    """(rect, note) — the main text column, marginal apparatus excluded.

    ⚠ MEAN DARKNESS DOES NOT SEPARATE THE MARGIN. Tried first and it failed:
    the marginal apparatus is dark enough that no threshold on a grey column
    profile splits it from the text block, and searching for the whitest
    vertical stripe just finds the page edge.

    What works is COVERAGE, not darkness. Binarise the page first, then take
    the per-column ink fraction: the main text block has ink on most rows,
    the marginal column has ink on only a few (it is sparse notes, not
    continuous setting), and the gutter has none. The block is then the span
    between the first and last column carrying at least 45% of peak coverage.
    Measured on v3: text runs to ~0.85 of page width, apparatus sits beyond it.
    """
    im = _gray(page, PROFILE_ZOOM)
    hist, tot, acc, ink = im.histogram(), 0, 0, 128
    tot = sum(hist)
    for i, c in enumerate(hist):
        acc += c
        if acc > tot * 0.12:
            ink = i
            break
    binary = im.point(lambda v, t=ink: 255 if v <= t else 0)
    cov = [c / 255.0 for c in binary.resize((im.width, 1)).tobytes()]
    r = page.rect
    peak = max(cov) if cov else 0
    if peak <= 0:
        return r, "blank page"
    hits = [x for x, c in enumerate(cov) if c > peak * 0.45]
    if not hits:
        return r, "no column structure — using full page"
    a, b = hits[0], hits[-1] + 1
    tail = sum(1 for c in cov[b:] if c > peak * 0.10)
    x0 = r.x0 + a / PROFILE_ZOOM - PAD_X
    x1 = r.x0 + b / PROFILE_ZOOM + PAD_X
    note = ("apparatus column excluded" if tail > im.width * 0.02
            else "single column")
    return fitz.Rect(max(x0, r.x0), r.y0, min(x1, r.x1), r.y1), note


def line_rects(page, block):
    """Line rectangles from the row-mean darkness profile.

    ⚠⚠ IT AVERAGES EACH ROW TO ONE PIXEL (`band.resize((1, h))`) AND THRESHOLDS
    THE MEAN. That silently DROPS SHORT LINES, and short lines are
    where a sentence spills one word onto its own line — so the dropped text was
    real scripture, not decoration. Proven on v3 idx 208 (2 Peter 2:9): the page
    prints «...a Dag Dom» / «sins.» / «10 Eñ eirna mest...», and «sins.» had NO
    crop at all. A one-word line leaves ~95% of the row as blank paper, so its
    MEAN never crosses a 'dark' cutoff no matter how the cutoff is placed.

    ▶ **No verse-count audit can catch this.** The verse numeral lives on the
    neighbouring line and survives; only words vanish, mid-verse. It passes
    `thorlaks_corpus_audit.py`, it passes a re-read of the crops (the evidence
    is not there to re-read), and the sentence often still parses. Every chunk
    prepped before 2026-08-14 was cut WITHOUT the recovery pass and may be
    missing words — re-prep them and diff, do not assume they are clean.

    ✅ **COMPENSATED SINCE 2026-08-14 by short_line_rects(), which main() now
    merges in.** This function is deliberately left as-is: it is reliable for
    normal lines, and replacing it wholesale risked the whole page. The
    recovery runs as an additive second pass, so it can only add lines.

    ⚠ Counting ink per row instead of averaging it was tried first and
    REVERTED, because it is not a fix — measured on v3:208, block width 516px:

        «sins.» short line   peak ink 0.054 of width
        inter-line gap       peak ink 0.081   <-- MORE than the short line
        full line            peak ink 0.519

    Descenders hanging into the gap put MORE ink there than a one-word line
    contains, so NO global row threshold separates them; the attempt merged
    the page into 14 runs instead of 52. The discriminator has to be
    horizontal CLUSTERING — a short line's ink is contiguous near the left
    margin, descender ink is scattered across the full width — which is a
    real change, not a constant tweak. Do not retry it with a different
    number.

    ▶ UNTIL IT IS FIXED: run with `--gaps` and eyeball `page.png` wherever a
    pitch anomaly is reported. That is the only defence, and it is manual.
    """
    im = _gray(page, PROFILE_ZOOM)
    x0 = int((block.x0 - page.rect.x0) * PROFILE_ZOOM)
    x1 = int((block.x1 - page.rect.x0) * PROFILE_ZOOM)
    band = im.crop((max(x0, 0), 0, min(x1, im.width), im.height))
    col = band.resize((1, band.height))
    rows = [col.getpixel((0, y)) / 255.0 for y in range(band.height)]
    out = []
    for a, b in _runs(rows, LINE_FRAC, min_len=6):
        y0 = page.rect.y0 + a / PROFILE_ZOOM - PAD_Y
        y1 = page.rect.y0 + b / PROFILE_ZOOM + PAD_Y
        out.append(fitz.Rect(block.x0, y0, block.x1, y1))
    return out


def short_line_rects(page, block, lines):
    """Recover one-word lines that line_rects() drops. ADDITIVE — never edits.

    ⚠ WHY A SECOND PASS AND NOT A BETTER THRESHOLD. Measured on v3:208
    (block 516px): a «sins.» line peaks at 0.054 of the width in ink, while the
    inter-line GAP peaks at 0.081 — descenders hanging off the line above carry
    MORE ink than a whole short line contains. Any global row threshold that
    admits the short line also welds every line to its neighbour (tried: 52
    lines collapsed to 14). Ink VOLUME cannot separate them.

    Ink SHAPE can. A short line is a few words sitting together near the left
    margin: its ink columns are CONTIGUOUS and densely filled over a narrow
    span. Descender scatter is the opposite — a dozen isolated stems spread
    right across the block. So measure the span the ink occupies and how
    solidly it fills it.

    Running as a second pass over the GAPS between already-detected lines keeps
    the working detector untouched, so this can only add lines, never lose one.
    """
    im = _gray(page, PROFILE_ZOOM)
    bx0 = int((block.x0 - page.rect.x0) * PROFILE_ZOOM)
    bx1 = int((block.x1 - page.rect.x0) * PROFILE_ZOOM)
    band = im.crop((max(bx0, 0), 0, min(bx1, im.width), im.height))
    w, h = band.size
    px = band.load()
    vals = sorted(px[x, y] for y in range(h) for x in range(w))
    lo = vals[len(vals) // 100]
    hi = vals[-max(len(vals) // 50, 1)]
    if hi - lo < 6:
        return []
    cut = lo + (hi - lo) * SHORT_INK_CUT

    def prof_row(pt):
        return int((pt - page.rect.y0) * PROFILE_ZOOM)

    # Regions to search, in profile rows.
    #
    # ⚠⚠ THIS USED TO BE ONLY `zip(lines, lines[1:])` — the gaps BETWEEN
    # detected lines — which left the strip above the first line and the strip
    # below the last line NEVER EXAMINED. That is a coverage hole, not a
    # threshold problem: the cluster test below was never even reached for a
    # line in those strips.
    #
    # It cost real scripture. On v3:182 the page's last text line is
    # «er sijne þocknan.» — the tail of Philippians 2:13, which otherwise ends
    # on a dangling preposition («...giorningeñ/ept» / «er sijne þocknan.»).
    # It sits BELOW the last line_rects() line, so no gap contained it and no
    # crop was ever cut. Found 2026-09-01, by reading the sentence.
    #
    # ▶ The foot strip is the dangerous one and it is dangerous on EVERY page,
    # because that row is also where the signature («D ij») and the catchword
    # sit — so a page always has ink there, and a reader scanning crops has no
    # way to notice that scripture was sharing the row with them.
    #
    # ⚠ Over-recovery here is CHEAP and under-recovery is not: an extra crop of
    # a catchword or a running head costs one small PNG, and the manifest
    # already warns that line N is not verse N. A missing crop costs a verse.
    gaps = []
    if lines:
        head = prof_row(lines[0].y0)
        if head >= 6:
            gaps.append((0, head))
    for a, b in zip(lines, lines[1:]):
        r0, r1 = prof_row(a.y1), prof_row(b.y0)
        if r1 - r0 >= 6:
            gaps.append((r0, r1))
    if lines:
        foot = prof_row(lines[-1].y1)
        if h - foot >= 6:
            gaps.append((foot, h))

    out = []
    for g0, g1 in gaps:
        rows = []
        for y in range(max(0, g0), min(h, g1)):
            cols = [x for x in range(w) if px[x, y] <= cut]
            rows.append((y, cols))
        # contiguous runs of rows carrying any ink at all
        run, start, last = [], None, None
        for y, cols in rows + [(None, [])]:
            if cols and start is None:
                start, run, last = y, [cols], y
            elif cols and start is not None:
                run.append(cols)
                last = y
            elif not cols and start is not None:
                y = last + 1                      # sentinel carries y=None
                if len(run) >= SHORT_MIN_ROWS:
                    allc = sorted({c for r in run for c in r})
                    if allc:
                        # ⚠ MIN-MAX SPAN IS NOT ROBUST — it was the first
                        # version and it failed on the very line this function
                        # exists for. «sins.» sits at x 13-33, but a few specks
                        # of page-edge ink at x~504-514 stretched min-max to
                        # 97% of the width and pushed fill to 0.09. Cluster the
                        # columns and judge the LARGEST cluster instead, so
                        # stray marks cannot veto a real line.
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
                        if (span >= SHORT_MIN_SPAN
                                and span <= w * SHORT_MAX_SPAN
                                and fill >= SHORT_MIN_FILL):
                            y0 = page.rect.y0 + start / PROFILE_ZOOM - PAD_Y
                            y1 = page.rect.y0 + y / PROFILE_ZOOM + PAD_Y
                            out.append(fitz.Rect(block.x0, y0, block.x1, y1))
                start, run = None, []
    return out


def gap_report(lines):
    """Flag pitch anomalies — a line the detector may still have missed.

    A dropped line shows as ~2x the median top-to-top pitch. Legitimate 2x+
    gaps exist (running head to body, a chapter heading), so this REPORTS and
    never edits: it tells a human where to look at `page.png`.
    """
    tops = [r.y0 for r in lines]
    pitch = [b - a for a, b in zip(tops, tops[1:])]
    if not pitch:
        return []
    med = sorted(pitch)[len(pitch) // 2]
    return [(i, p, p / med) for i, p in enumerate(pitch) if p > med * 1.6]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vol", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--pages", required=True, help="PDF index, e.g. 202 or 173-177")
    ap.add_argument("--out", required=True, help="subdirectory name under _prep/")
    ap.add_argument("--zoom", type=float, default=READ_ZOOM)
    ap.add_argument("--split", action="store_true",
                    help="also emit left/right half-line crops with overlap, "
                         "for very wide lines")
    ap.add_argument("--overlap", type=float, default=26.0, help="pt, for --split")
    ap.add_argument("--gaps", action="store_true",
                    help="report pitch anomalies — where a short line may have "
                         "been dropped (see line_rects docstring)")
    a = ap.parse_args()

    lo, _, hi = a.pages.partition("-")
    idxs = list(range(int(lo), int(hi or lo) + 1))
    out = OUTROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(RESEARCH / f"thorlaks_v{a.vol}.pdf")
    c = FOLIO_C[a.vol]

    man = ["# Prep manifest — Þorláksbiblía v%d, idx %s" % (a.vol, a.pages), "",
           "Pre-cut by `tools/prep_chunk.py`. **Pixels only — nothing here was "
           "read by a machine.** Transcribe from these crops; they are already "
           "at %.1fx (the scan's native ceiling), with the marginal apparatus "
           "column cut away." % a.zoom, "",
           "⚠ Line segmentation is a heuristic: it can merge touching lines, "
           "split a line carrying a tall initial, and it treats a decorated "
           "drop-cap as its own run. **Line N is not verse N.** Confirm "
           "against `page.png` before trusting any sequence.", "",
           "⚠ The excluded side column holds cross-references and gloss text — "
           "not scripture. If you need to check a gloss key, re-render that "
           "page yourself; it is deliberately not here.", "",
           "| idx | folio | lines | columns |", "|---|---|---|---|"]

    total = 0
    n_recovered = {}
    for idx in idxs:
        page = doc[idx]
        block, note = text_block(page)
        lines = line_rects(page, block)
        # Recover one-word lines the mean-threshold detector drops, and merge
        # them into reading order. See short_line_rects: on v3:208 this is the
        # difference between having «sins.» and «aptur j Saurnum.» and silently
        # losing both — real scripture, invisible to every verse-count audit.
        recovered = short_line_rects(page, block, lines)
        if recovered:
            lines = sorted(lines + recovered, key=lambda r: r.y0)
            n_recovered[idx] = len(recovered)
        if a.gaps:
            flags = gap_report(lines)
            print(f"  idx {idx}: {len(lines)} lines, {len(flags)} pitch "
                  f"anomal{'y' if len(flags) == 1 else 'ies'}")
            for i, p, mult in flags:
                print(f"    after line{i:02d}.png: {p:.1f}pt = {mult:.2f}x "
                      f"pitch — check page.png for a dropped short line")
        d = out / f"p{idx}"
        d.mkdir(exist_ok=True)
        page.get_pixmap(matrix=fitz.Matrix(PAGE_ZOOM, PAGE_ZOOM)).save(d / "page.png")
        for i, rect in enumerate(lines):
            page.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom),
                            clip=rect).save(d / f"line{i:02d}.png")
            if a.split and rect.width > 120:
                mid = (rect.x0 + rect.x1) / 2
                page.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom),
                                clip=fitz.Rect(rect.x0, rect.y0,
                                               mid + a.overlap / 2, rect.y1)
                                ).save(d / f"line{i:02d}a.png")
                page.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom),
                                clip=fitz.Rect(mid - a.overlap / 2, rect.y0,
                                               rect.x1, rect.y1)
                                ).save(d / f"line{i:02d}b.png")
        folio = (idx - c) // 2
        side = "recto" if (idx - c) % 2 == 0 else "verso"
        man.append(f"| {idx} | {folio} {side} | {len(lines)} | {note} |")
        total += len(lines)
        print(f"idx {idx}: folio {folio} {side}, {len(lines)} lines, {note}",
              flush=True)

    doc.close()
    man += ["", f"**{total} line crops** across {len(idxs)} pages.", "",
            "## Suggested order of work", "",
            "1. Read `page.png` for each page first — orientation, chapter "
            "headings, where the text block starts and ends.",
            "2. Transcribe from `lineNN.png` in order.",
            "3. ⚠ **DO NOT re-render a disputed line at higher zoom.** These "
            f"crops are already at {READ_ZOOM}x, the native ceiling of the "
            "scans. Anything above it interpolates: more pixels, zero new "
            "evidence, and it FEELS like progress. (This manifest advised "
            "20-40x until 2026-08-13; it was wrong from the first chunk.)",
            "4. For a disputed p-family sort (`þ ꝑ ꝥ p`) MEASURE it, do not "
            "judge it:",
            "       python tools/thorlaks_sorts.py --dir <this page dir> "
            "--line NN",
            "   The map shows which stems rise above the body band (þ/ꝥ) and "
            "which fall below it (ꝑ/p); `--at <x>` gives the number at one "
            "stem. The bar is NOT measurable at this resolution — the tool "
            "says so rather than guessing.",
            "5. Compare a disputed letter against an unambiguous same-page "
            "instance of BOTH candidates before deciding. Never judge a glyph "
            "in isolation.",
            "",
            "⚠ The failure this guards against is not misreading — it is "
            "supplying the letter the WORD wants. «fyrer» entered two books "
            "that way, each with genuine same-page corroboration."]
    (out / "MANIFEST.md").write_text("\n".join(man), encoding="utf-8")
    print(f"\n{total} line crops -> {out}\nmanifest: {out / 'MANIFEST.md'}")


if __name__ == "__main__":
    main()
