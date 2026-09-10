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
    transcribes a cross-reference as a verse (a mistake the brief warns about).
    ⚠ That exclusion is a COVERAGE rule and it CUTS SPARSE SCRIPTURE: a
    second text column of short lines (a genealogy) reads as apparatus and is
    sliced off. Use --full-width on such a page; see text_block's docstring;
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


def text_block(page, robust=False, full_width=False):
    """(rect, note) — the main text column, marginal apparatus excluded.

    ⛔⛔ THE EXCLUSION IS A COVERAGE RULE, AND SPARSE SCRIPTURE LOOKS
    EXACTLY LIKE APPARATUS TO IT. The block is the span of columns carrying
    >=45 % of peak ink coverage, on the reasoning that the text block has ink
    on most rows while the margin has ink on only a few. A SECOND TEXT COLUMN
    OF SHORT LINES BREAKS THAT ASSUMPTION. Measured 2026-09-09 on v3 idx 54,
    Luke 3:24-38: the genealogy is set in two columns of «Sa ed var sonur X»,
    the right column is mostly white space, its coverage falls under the
    threshold, and it is excluded AS IF IT WERE APPARATUS — every line crop
    came out 1797 px against a kit median of 2005 and the right column read
    «Mathat» where the page prints «Mathathan».
    ⚠ `--robust-block` IS NOT THE CURE FOR THIS and reaching for it wastes a
    session: it lowers `peak` to the 90th percentile, which widens the block
    only incidentally — measured on that same page it went 1797 -> 1840 px and
    the column still read «Mathath», still cut.
    ⚠⚠ AND THE WIDTH CHECK DOES NOT CATCH IT. thorlaks_crop_widths.py passes
    idx 54 («narrow, but margin is intact»), because it measures the right
    margin of the crop it is handed and cannot see that the crop's edge is in
    the wrong place. ▶ research/_evidence/luke_p54_apparatus_exclusion_cuts_text_2026-09-09.md

    `full_width=True` bypasses detection completely and returns the whole
    page. The apparatus then lands in the crops too — which is the correct
    trade: a cross-reference in view is a nuisance the conventions already
    cover («margin apparatus — not scripture, not transcribed»), while a
    sliced verse is unrecoverable and invisible to every verse-count audit.

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
    if full_width:
        return page.rect, "FULL WIDTH — block detection bypassed"
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
    # ⛔⛔ `peak = max(cov)` IS A SINGLE-COLUMN STATISTIC AND A DARK SCAN EDGE
    # BEATS THE TEXT. Measured 2026-09-06 on v3 idx 12: max coverage 0.553 at
    # x=11 — 2 % across the page, a binding/edge artefact — against a 0.271 peak
    # on idx 11 and 13. The 45 %-of-peak threshold then sits above the real
    # text's coverage, the block comes out 47 % of the page instead of ~85 %,
    # and EVERY line crop is cut off mid-word («4 Simon af Cana…»). Three
    # transcription agents produced nothing on that page before anyone looked at
    # the crops. Full write-up: research/THORLAKS_CAMPAIGN.md.
    #
    # ⚠⚠ `--robust-block` USES THE 90th PERCENTILE INSTEAD, AND IS OPT-IN ON
    # PURPOSE. It is NOT validated as a global default: swept over all of v3 it
    # moves 120 pages by >3pp, and 28 of those were already healthy. Changing the
    # default would silently re-cut finished books. Use it per page, look at the
    # crops afterwards, and record which pages were prepped with it.
    peak = max(cov) if cov else 0
    if robust and cov:
        srt = sorted(cov)
        peak = srt[int(len(srt) * 0.90)]
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


MAN_HEADER = "# Prep manifest"


def _flag_tokens(a):
    """The per-page `flags` cell: which opt-in geometry flags built these crops.

    `--full-width` and `--robust-block` are per-page opt-ins whose own help text
    tells the operator to «record which pages used it». Until 2026-09-10 the
    tool then overwrote the record. The flags now live in the manifest table,
    per page, so a later reader can see which pages were prepped how.
    """
    t = []
    if getattr(a, "full_width", False):
        t.append("`--full-width`")
    if getattr(a, "robust_block", False):
        t.append("`--robust-block`")
    if getattr(a, "split", False):
        t.append("`--split`")
    return " ".join(t) if t else "\u2014"


def _read_existing_manifest(path):
    """(preamble, {idx: row_cells}) of an existing manifest.

    preamble is everything BEFORE the `# Prep manifest` heading, preserved
    verbatim: a hand-written scope banner or warning must survive a merge, or
    the merge becomes the next version of the bug it is fixing.

    A pre-2026-09-10 row has four cells and no flags; it is carried forward
    with the flags cell saying so, never with a guess.
    """
    if not path.exists():
        return [], {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return [], {}
    lines = text.split("\n")
    pre = []
    for i, ln in enumerate(lines):
        if ln.startswith(MAN_HEADER):
            pre = lines[:i]
            break
    rows = {}
    for ln in lines:
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [x.strip() for x in s.strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        if len(cells) == 4:
            cells = cells + ["(unrecorded \u2014 prepped before flags were tracked)"]
        rows[int(cells[0])] = cells[:5]
    return pre, rows


def _idx_span(keys):
    """'50-58' when contiguous, else an explicit list. Never a lying range."""
    if not keys:
        return "(none)"
    if keys == list(range(keys[0], keys[-1] + 1)):
        return "%d-%d" % (keys[0], keys[-1]) if len(keys) > 1 else str(keys[0])
    return ",".join(str(k) for k in keys)


def _claim_for(uniform_flags, zoom):
    """The headline sentence about what the crops contain.

    \u26a0 IT MUST NOT ASSERT THE APPARATUS WAS CUT WHEN --full-width LEFT IT IN,
    and \u2014 the 2026-09-10 lesson \u2014 it must not speak for the whole kit when
    the pages were prepped differently. A manifest that misdescribes its own
    crops is the same defect class as a part-file note asserting «no numeral
    appears» on a line that prints one (Mark 3:34).
    """
    head = ("Pre-cut by `tools/prep_chunk.py`. **Pixels only \u2014 nothing here was "
            "read by a machine.** Transcribe from these crops; they are already "
            "at %.1fx (the scan's native ceiling), " % zoom)
    if uniform_flags is None:
        return head + ("and **what each page's crops contain is recorded PER PAGE "
                       "in the `flags` column below** \u2014 the pages in this kit "
                       "were NOT all prepped the same way, so a single sentence "
                       "here would misdescribe some of them.")
    if "--full-width" in uniform_flags:
        return head + ("with the FULL PAGE WIDTH kept: the marginal apparatus is "
                       "PRESENT in these crops and was not cut away.")
    return head + "with the marginal apparatus column cut away."


def _note_for(uniform_flags):
    if uniform_flags is None:
        return ("\u26a0\u26a0 **THE PAGES IN THIS KIT WERE PREPPED WITH DIFFERENT FLAGS "
                "\u2014 READ THE `flags` COLUMN BEFORE TRUSTING ANY PAGE.** A page "
                "marked `--full-width` has the marginal apparatus IN its crops "
                "(cross-references and gloss text sit beside the scripture and "
                "are NOT scripture). A page with no flag had that column cut "
                "away. Assuming either one for the whole kit is how idx 54's "
                "manifest came to misdescribe eight pages.")
    if "--full-width" in uniform_flags:
        return ("\u26a0\u26a0 **THESE PAGES WERE PREPPED `--full-width`, SO THE MARGINAL "
                "APPARATUS IS IN THE CROPS.** Cross-references and gloss text sit "
                "beside the scripture on these lines and are NOT scripture \u2014 do "
                "not transcribe them as verses. The flag was used because block "
                "detection cut real text; see text_block's docstring in "
                "tools/prep_chunk.py.")
    return ("\u26a0 The excluded side column holds cross-references and gloss text \u2014 "
            "not scripture. If you need to check a gloss key, re-render that "
            "page yourself; it is deliberately not here.")


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
    ap.add_argument("--robust-block", action="store_true",
                    help="use the 90th-percentile column instead of the MAX "
                         "when finding the text block. For a page whose crops "
                         "come out cut off mid-word because a dark scan edge "
                         "beat the text (v3 idx 12). OPT-IN: not validated as "
                         "a default, it moves 28 healthy v3 pages too.")
    ap.add_argument("--full-width", action="store_true",
                    help="skip text-block detection and crop the FULL page "
                         "width. For a page whose own scripture is sparse "
                         "enough to be mistaken for the marginal apparatus "
                         "and cut off — a two-column genealogy (v3 idx 54). "
                         "The apparatus lands in the crops too; that is the "
                         "intended trade. NOT --robust-block, which does not "
                         "fix this. OPT-IN, per page, and record which pages "
                         "used it.")
    ap.add_argument("--clean-stale", action="store_true",
                    help="delete crops already in a page directory that THIS "
                         "run will not rewrite. Without it, such crops make "
                         "the run REFUSE. A re-prep that emits fewer lines "
                         "than the last one strands the extra crops at the OLD "
                         "geometry, where nothing distinguishes them (v3 idx "
                         "54: a 1797px line55.png beside 55 new 2739px crops).")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be written, deleted and merged, and "
                         "write nothing.")
    a = ap.parse_args()

    lo, _, hi = a.pages.partition("-")
    idxs = list(range(int(lo), int(hi or lo) + 1))
    out = OUTROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(RESEARCH / f"thorlaks_v{a.vol}.pdf")
    c = FOLIO_C[a.vol]
    flags_cell = _flag_tokens(a)
    man_path = out / "MANIFEST.md"

    # ---- pass 1: detect every page, and see what is already on disk -------
    # Detection runs for ALL pages before ANY pixel is written, so a stale-crop
    # refusal cannot leave a half-rewritten page directory behind.
    plan = []
    stale = []
    for idx in idxs:
        page = doc[idx]
        block, note = text_block(page, robust=a.robust_block,
                                 full_width=a.full_width)
        lines = line_rects(page, block)
        # Recover one-word lines the mean-threshold detector drops, and merge
        # them into reading order. See short_line_rects: on v3:208 this is the
        # difference between having «sins.» and «aptur j Saurnum.» and silently
        # losing both — real scripture, invisible to every verse-count audit.
        recovered = short_line_rects(page, block, lines)
        if recovered:
            lines = sorted(lines + recovered, key=lambda r: r.y0)
        d = out / f"p{idx}"
        will_write = set()
        for i, rect in enumerate(lines):
            will_write.add(f"line{i:02d}.png")
            if a.split and rect.width > 120:
                will_write.add(f"line{i:02d}a.png")
                will_write.add(f"line{i:02d}b.png")
        found = sorted(p.name for p in d.glob("line*.png")) if d.is_dir() else []
        orphans = [n for n in found if n not in will_write]
        if orphans:
            stale.append((idx, d, orphans))
        plan.append((idx, page, lines, note))

    if stale and not (a.clean_stale or a.dry_run):
        doc.close()
        sys.stderr.write(
            "\n\u26d4 REFUSING: %d page director%s already hold%s crop(s) that "
            "THIS run will not rewrite.\n" %
            (len(stale), "y" if len(stale) == 1 else "ies",
             "s" if len(stale) == 1 else ""))
        sys.stderr.write(
            "A re-prep emitting FEWER lines than the previous one strands the "
            "extra crops at the OLD geometry. Nothing downstream can tell them "
            "apart: on Luke v3 idx 54 a 1797px line55.png survived beside 55 "
            "new 2739px crops and would have gone into the packed sheets as one "
            "line of cut-off text.\n\n")
        for idx, d, orphans in stale:
            sys.stderr.write("  p%d  (%s)\n" % (idx, d))
            for n in orphans:
                sys.stderr.write("        %s\n" % n)
        sys.stderr.write(
            "\n\u25b6 Look at them before deleting anything. If they are the "
            "previous prep's leftovers, re-run with --clean-stale to remove "
            "exactly the files listed above. --dry-run shows the whole plan and "
            "writes nothing.\n")
        return 2

    if a.dry_run:
        doc.close()
        pre, rows = _read_existing_manifest(man_path)
        print("DRY RUN \u2014 nothing written, nothing deleted.")
        for idx, _pg, lines, note in plan:
            print("  p%d: would write page.png + %d line crop(s)  [flags %s]  %s"
                  % (idx, len(lines), flags_cell, note))
        for idx, d, orphans in stale:
            print("  p%d: would DELETE %d stale crop(s) (only with --clean-stale): %s"
                  % (idx, len(orphans), ", ".join(orphans)))
        if rows:
            keep = [k for k in sorted(rows) if k not in idxs]
            print("  manifest: would MERGE %d row(s) into %d existing row(s); "
                  "rows kept untouched: %s"
                  % (len(plan), len(rows),
                     ",".join(str(k) for k in keep) if keep else "(none)"))
        else:
            print("  manifest: would CREATE %s" % man_path)
        return 0

    if stale and a.clean_stale:
        for idx, d, orphans in stale:
            for n in orphans:
                (d / n).unlink()
            print("p%d: removed %d stale crop(s) left by an earlier prep: %s"
                  % (idx, len(orphans), ", ".join(orphans)), flush=True)

    # ---- pass 2: write ---------------------------------------------------
    new_rows = {}
    total = 0
    for idx, page, lines, note in plan:
        if a.gaps:
            anomalies = gap_report(lines)
            print(f"  idx {idx}: {len(lines)} lines, {len(anomalies)} pitch "
                  f"anomal{'y' if len(anomalies) == 1 else 'ies'}")
            for i, p, mult in anomalies:
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
        new_rows[idx] = [str(idx), f"{folio} {side}", str(len(lines)), note,
                         flags_cell]
        total += len(lines)
        print(f"idx {idx}: folio {folio} {side}, {len(lines)} lines, {note}",
              flush=True)

    doc.close()

    # ---- manifest: MERGE, never replace ----------------------------------
    # Until 2026-09-10 this rebuilt the file from this invocation alone, so a
    # single-page re-prep into a live kit destroyed the other pages' rows AND
    # asserted this run's flags over all of them.
    pre, rows = _read_existing_manifest(man_path)
    merged = dict(rows)
    merged.update(new_rows)
    keys = sorted(merged)
    kept = [k for k in rows if k not in new_rows]
    uniform = set(r[4] for r in merged.values())
    uniform_flags = uniform.pop() if len(uniform) == 1 else None

    man = list(pre)
    man += ["# Prep manifest — Þorláksbiblía v%d, idx %s"
            % (a.vol, _idx_span(keys)), "",
            _claim_for(uniform_flags, a.zoom), "",
            "⚠ Line segmentation is a heuristic: it can merge touching lines, "
            "split a line carrying a tall initial, and it treats a decorated "
            "drop-cap as its own run. **Line N is not verse N.** Confirm "
            "against `page.png` before trusting any sequence.", "",
            _note_for(uniform_flags), "",
            "| idx | folio | lines | columns | flags |",
            "|---|---|---|---|---|"]
    man += ["| " + " | ".join(merged[k]) + " |" for k in keys]
    grand = sum(int(merged[k][2]) for k in keys if merged[k][2].isdigit())
    man += ["", "**%d line crops** across %d page(s) in this kit."
            % (grand, len(keys)), ""]
    if kept:
        man += ["⚠ This run prepped idx %s. The row(s) for idx %s were already "
                "here and were carried forward unchanged — their crops were "
                "NOT re-rendered and their `flags` are the flags they were "
                "built with." % (_idx_span(sorted(new_rows)),
                                 _idx_span(sorted(kept))), ""]
    man += ["## Suggested order of work", "",
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
    man_path.write_text("\n".join(man), encoding="utf-8")
    print(f"\n{total} line crops written -> {out}")
    if kept:
        print(f"manifest MERGED (kept idx {_idx_span(sorted(kept))}): {man_path}")
    else:
        print(f"manifest: {man_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
