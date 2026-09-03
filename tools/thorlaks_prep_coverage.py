# -*- coding: utf-8 -*-
"""Find ink on a prepped page that NO line crop covers. Pure geometry, 0 model tokens.

    python tools/thorlaks_prep_coverage.py --chunk philippians_v2
    python tools/thorlaks_prep_coverage.py --all
    python tools/thorlaks_prep_coverage.py --chunk philippians_v2 --dump _work/cov

## Why this exists

`prep_chunk.py` hands the transcriber a directory of line crops and says nothing
about what it failed to cut. **A line-crop set is silent about its own gaps**,
and the gap is sometimes scripture:

  - v3:208 (2 Peter 2:9) - «sins.» alone on a line, NO crop. Found 2026-08-13,
    fixed additively by `short_line_rects()`.
  - v3:182 (Philippians 2:13) - the page's LAST text line, «er sijne þocknan.»,
    NO crop, **after** that fix. Cause: `short_line_rects()` scanned only the
    gaps BETWEEN detected lines, so the strip below the LAST line was never
    examined. Fixed 2026-09-01 (head and foot strips added); this tool is what
    found it and is the regression check for it.

▶ No downstream check sees this class - `thorlaks_corpus_audit.py` counts verse
NUMERALS, and a dropped clause mid-verse changes no count. The verse still
parses. Same class as Karl XII's Sirach 22:33: an omission leaves no evidence
behind. That is why coverage has to be checked against the PAGE, not the crops.

## How it works - and why it does NOT match pixels

The first version of this tool tried to locate each `lineNN.png` back onto a
full-page render by matching row profiles. **That cannot work**, and the failure
is worth recording: `page.get_pixmap(clip=rect)` RE-RASTERIZES the clipped
region, it does not slice the full-page bitmap. Origin rounding differs, so the
crop is never pixel-identical to the corresponding page rows and every match is
rejected. The symptom was a clean-looking report in which *every* run was "0%
covered" - i.e. a broken check that looks like a catastrophic finding.

So this re-derives the rectangles instead, by calling `prep_chunk`'s own
`text_block()` / `line_rects()` / `short_line_rects()`, and compares them with an
independently computed ink profile. It then CHECKS that the derivation actually
reproduces the crops on disk (count and per-crop height); if it does not, the
prep was cut with different parameters and the report is flagged as such rather
than quietly believed.

## What it does NOT do

It does not read. It reports y-ranges in PDF points. **An uncovered run is not
automatically scripture** - most are running heads, chapter numerals, colophons,
signatures and catchwords. A chunk must still record those, but they are not
verses. The transcriber renders the flagged band and decides.
"""
import argparse
import importlib.util
import io
import re
import sys
from pathlib import Path

import fitz
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
PREP = RESEARCH / "_prep"
HERE = Path(__file__).parent

_spec = importlib.util.spec_from_file_location("prep_chunk", HERE / "prep_chunk.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

MIN_RUN_ROWS = 4          # at PROFILE_ZOOM=2, a text line is ~12-17 profile rows
COVER_OK = 0.50


def ink_profile(page, block):
    """Per-row ink COUNT inside the block. Deliberately not line_rects' mean.

    `line_rects()` averages each row to one pixel and thresholds the mean, which
    is exactly what makes it blind to short lines. Counting binarised ink is
    sensitive to a one-word line; it is a poor LINE SEGMENTER (descender ink in
    an inter-line gap can exceed a short line's ink - measured, see
    `line_rects`' docstring) but a perfectly good "is there ink in this row"
    detector, which is all this tool asks.
    """
    im = pc._gray(page, pc.PROFILE_ZOOM)
    hist, tot, acc, cut = im.histogram(), 0, 0, 128
    tot = sum(hist)
    for i, c in enumerate(hist):
        acc += c
        if acc > tot * 0.12:
            cut = i
            break
    x0 = int((block.x0 - page.rect.x0) * pc.PROFILE_ZOOM)
    x1 = int((block.x1 - page.rect.x0) * pc.PROFILE_ZOOM)
    band = im.crop((max(x0, 0), 0, min(x1, im.width), im.height))
    binary = band.point(lambda v, t=cut: 1 if v <= t else 0)
    px = binary.load()
    w, h = binary.size
    prof = [sum(px[x, y] for x in range(w)) for y in range(h)]
    # Per-row ink split into left/centre/right thirds of the block. This is the
    # 0-token discriminator that decides whether a flagged run needs a READ:
    # scripture is set FROM THE LEFT MARGIN, a catchword sits at the right, and
    # a signature ("D ij") sits centred. Without it, triaging the page-foot runs
    # means reading ~30 strips to learn that most are catchwords.
    t = w // 3
    thirds = [(sum(px[x, y] for x in range(0, t)),
               sum(px[x, y] for x in range(t, 2 * t)),
               sum(px[x, y] for x in range(2 * t, w))) for y in range(h)]
    return prof, w, thirds


def runs(mask, min_len):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    if s is not None and len(mask) - s >= min_len:
        out.append((s, len(mask)))
    return out


def check_page(pdf, idx, d):
    page = pdf[idx]
    block, note = pc.text_block(page)
    lines = pc.line_rects(page, block)
    rec = pc.short_line_rects(page, block, lines)
    if rec:
        lines = sorted(lines + rec, key=lambda r: r.y0)

    crops = sorted(d.glob("line*.png"),
                   key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))
    # Does the derivation reproduce what is on disk? If not, say so loudly -
    # a coverage report against rectangles the prep never used is worthless.
    repro = len(crops) == len(lines)
    if repro:
        for f, r in zip(crops, lines):
            ph = Image.open(f).height
            if abs(ph - r.height * pc.READ_ZOOM) > 4:
                repro = False
                break

    prof, bw, thirds = ink_profile(page, block)
    inked = [v >= max(2, int(0.010 * bw)) for v in prof]

    covered = [False] * len(prof)
    for r in lines:
        a = int((r.y0 - page.rect.y0) * pc.PROFILE_ZOOM)
        b = int((r.y1 - page.rect.y0) * pc.PROFILE_ZOOM)
        for y in range(max(a, 0), min(b, len(covered))):
            covered[y] = True

    # ⚠⚠ TEST THE UNCOVERED INK DIRECTLY, NOT "runs that are <50% covered".
    # The first version did the latter and MISSED its own positive control:
    # p182's dropped «er sijne þocknan.» sits close enough to the line above
    # that the two merge into ONE ink run, which is then >50% covered by the
    # line above's rect and never reported. A dropped line is by definition
    # adjacent to a kept one, so that formulation is blind to exactly the
    # defect it exists to find. Intersect first, then look for runs.
    naked = [ink and not cov for ink, cov in zip(inked, covered)]
    gaps = []
    for s, e in runs(naked, MIN_RUN_ROWS):
        y0 = page.rect.y0 + s / pc.PROFILE_ZOOM
        y1 = page.rect.y0 + e / pc.PROFILE_ZOOM
        L = max(t[0] for t in thirds[s:e])
        C = max(t[1] for t in thirds[s:e])
        R = max(t[2] for t in thirds[s:e])
        gaps.append((y0, y1, (L, C, R), max(prof[s:e]),
                     s > 0.80 * len(prof)))
    return {"idx": idx, "note": note, "n_lines": len(lines),
            "n_crops": len(crops), "repro": repro, "gaps": gaps,
            "block": block, "page_h": page.rect.height}


def dump_gap(pdf, idx, block, y0, y1, out):
    out.mkdir(parents=True, exist_ok=True)
    page = pdf[idx]
    pad = 3
    clip = fitz.Rect(block.x0, max(y0 - pad, page.rect.y0),
                     block.x1, min(y1 + pad, page.rect.y1))
    page.get_pixmap(matrix=fitz.Matrix(pc.READ_ZOOM, pc.READ_ZOOM),
                    clip=clip).save(out / f"p{idx}_y{int(y0)}-{int(y1)}.png")


def manifest_vol(chunk):
    m = PREP / chunk / "MANIFEST.md"
    if not m.exists():
        return None
    g = re.search(r"Þorláksbiblía v(\d)", io.open(m, encoding="utf-8").read())
    return int(g.group(1)) if g else None


def run_chunk(chunk, dump_root=None):
    d = PREP / chunk
    vol = manifest_vol(chunk)
    if vol is None:
        print(f"\n=== {chunk} ===\n  no readable MANIFEST.md - SKIPPED")
        return
    pdf = fitz.open(str(RESEARCH / f"thorlaks_v{vol}.pdf"))
    pages = sorted((p for p in d.iterdir()
                    if p.is_dir() and re.fullmatch(r"p\d+", p.name)),
                   key=lambda p: int(p.name[1:]))
    print(f"\n=== {chunk}  (v{vol}, {len(pages)} pages) ===")
    total, tail_hits, bad_repro = 0, 0, []
    for pd in pages:
        idx = int(pd.name[1:])
        r = check_page(pdf, idx, pd)
        tag = "" if r["repro"] else "  ** derivation does NOT reproduce crops **"
        if not r["repro"]:
            bad_repro.append(idx)
        print(f"  p{idx}: {r['n_crops']} crops / {r['n_lines']} derived, "
              f"{r['note']}, {len(r['gaps'])} uncovered run(s){tag}")
        for y0, y1, lcr, mx, tail in r["gaps"]:
            L, C, R = lcr
            # Left-margin ink in an uncovered run is the shape of dropped
            # SCRIPTURE. Right-only is a catchword, centre-only a signature -
            # both must be recorded by the chunk, neither is a verse.
            if L >= max(4, mx * 0.25):
                kind = "LEFT-SET  <-- may be DROPPED SCRIPTURE, read it"
            elif R > L and R >= C:
                kind = "right     (catchword)"
            elif C > L:
                kind = "centre    (signature)"
            else:
                kind = "faint"
            mark = " [page foot]" if tail else ""
            print(f"      y {y0:.0f}-{y1:.0f} pt  ink L{L}/C{C}/R{R}  "
                  f"{kind}{mark}")
            if tail:
                tail_hits += 1
            if dump_root:
                dump_gap(pdf, idx, r["block"], y0, y1,
                         Path(dump_root) / chunk)
        total += len(r["gaps"])
    print(f"  TOTAL uncovered runs: {total}   (at the page foot: {tail_hits})")
    if bad_repro:
        print(f"  WARNING pages whose derivation does not match the crops on "
              f"disk: {bad_repro} - re-prep them before trusting this report")
    pdf.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dump", default=None,
                    help="render every flagged run here, for ONE adjudicating read")
    a = ap.parse_args()
    if a.all:
        for d in sorted(PREP.iterdir()):
            if d.is_dir():
                run_chunk(d.name, a.dump)
    elif a.chunk:
        run_chunk(a.chunk, a.dump)
    else:
        sys.exit("pass --chunk <name> or --all")


if __name__ == "__main__":
    main()
