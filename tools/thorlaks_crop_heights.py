# -*- coding: utf-8 -*-
"""Flag prep crops that hold MORE THAN ONE text line, before anyone reads them.

    python tools/thorlaks_crop_heights.py --chunk luke_kit2 --page p66
    python tools/thorlaks_crop_heights.py --chunk luke_kit2          # every page
    python tools/thorlaks_crop_heights.py --all                      # every chunk

⚠⚠ **A `lineNN` THAT HOLDS FOUR TEXT LINES IS NOT A LINE, AND EVERY ADDRESS
WRITTEN AGAINST IT IS MEANINGLESS.** A ø record reads
`p<NN> line<NN> <L|R>`; if that crop is a BAND of stacked lines, the `L|R` half
does not name a place a second reader can return to. This is how Luke idx 66
was found unreadable (13 crops where its neighbours have 54-56), and it is why
idx 54's `line40` — which holds FOUR text lines — could not supply a control
crop containing the word its own merged record cites.

⛔ **THIS IS A DIFFERENT DEFECT FROM `thorlaks_crop_widths.py`, AND THE WIDTH
FLAG HIDES IT.** Widths catch a crop whose right edge is in the wrong place;
heights catch a crop that is several lines tall. A page can pass widths and be
unreadable. Run BOTH before reading a kit.

▶ Cure per page: `prep_chunk.py --robust-block` or `--full-width`, then rebuild
  the sheets. ⚠ Neither fixed idx 66 — when they do not, the page is a TOOL
  QUESTION for the owner and ⛔ must not be read, recorded truncated, OR
  recorded fine.

The measurement is the crop's height against the MEDIAN crop height of its own
page — a self-contained control, so a page prepped at a different zoom, or a
print with different leading, does not need a hand-set threshold.

⚠⚠ **THIS PRINTS *SUSPECT*, NOT A VERDICT — LIKE `thorlaks_crop_widths.py`.**
Measured false-positive classes, found by running it against pages already
known good:
  · **`line00`** is the RUNNING HEAD and is legitimately tall (it carries the
    whitespace above the text block): Luke p57 line00 is 1.7x its page median,
    p59 line00 is 2.6x, and both pages read fine. It is reported SEPARATELY and
    does NOT set the exit code.
  · **a centred CHAPTER HEADING** is legitimately tall too (Luke p59 `line26`,
    the «Cap. VIII» numeral, 2.7x). It is NOT exempted — there is no way to tell
    it from a merged band by height alone, so it is flagged and a reader clears
    it by looking ONCE at that one crop.
⛔ So a flag is a QUESTION about one crop. What it is not is a page verdict:
   5 bands out of 13 crops (idx 66) is a broken line finder; 1 band out of 58
   is a heading.

★ **POSITION, ADDED 2026-09-15 — IT DISCRIMINATES WHERE THE FRACTION DOES
NOT, AND IT IS FREE.** A band's HEIGHT says a crop is multi-line; WHERE it sits
says whether that is expected:

  · `line00`          → the RUNNING HEAD. Legitimately tall on every page.
  · the LAST crop     → the printer's FOOT (catchword, signature mark, the
                        whitespace below the block). Legitimately tall too.
  · anything BETWEEN  → ⛔ **THE MERGED-ROW DEFECT.** Nothing is legitimately
                        tall in the middle of a body of set text.

⚠⚠ **READ THE MID-PAGE COUNT, NOT THE BAND FRACTION.** 172 of 276 pages carry
a band and most are just a heading, so the fraction drowns the signal. Measured
on luke_kit2: p66 is the ONLY page with mid-page bands and the ONLY one whose
read came back garbled. The fraction alone ranked it beside five innocent pages.

⚠ A centred CHAPTER HEADING is mid-page and legitimately tall, so a mid-page
band stays a QUESTION about one crop — but it is a far smaller and better-aimed
question than the fraction asks. ⛔ It is still not a page verdict.

▶ Control: `--selftest` builds synthetic pages of known geometry and asserts
BOTH directions — a head+foot page must NOT flag, a mid-band page MUST. The
known-bad `HEXAPLA_NO_POSITION=1` disables the classification and the selftest
must then FAIL, so a screen that has stopped discriminating cannot pass quietly.

Exit codes:  0 = no band found · 1 = band(s) found · 2 = COULD NOT RUN.
⛔ 2 is never «clean». A check that cannot run did not pass.
"""
import argparse
import os
import re
import statistics
import sys

try:
    from PIL import Image
except ImportError:                                       # pragma: no cover
    sys.stderr.write("2: pillow is not importable - this check DID NOT RUN\n")
    sys.exit(2)

DATA = r"C:\Projects\Hexapla-releases"
PREP = os.path.join(DATA, "research", "_prep")
LINE_RE = re.compile(r"^line(\d+)\.png$")

# a crop taller than this many times its page's median holds another text line
BAND = 1.6
# below this many crops a median is not a control, it is an average of noise
MIN_CROPS = 8
# the running head: legitimately tall on every page, reported but not counted
HEAD = "line00.png"
# ★ POSITION. A band at the head or the foot is expected; one BETWEEN them is
# the merged-row defect. See the docstring - this is the discriminating signal.
HEAD_POS, FOOT_POS, MID_POS = "head", "foot", "mid"


def die(msg):
    """⛔ Exit 2 and SAY SO. `sys.exit("2: ...")` exits 1 - it prints the string
    and returns 1, so a caller gating on the code reads «found bands» when the
    check never ran. Caught by this tool's own could-not-run control."""
    sys.stderr.write("2: %s\n" % msg)
    sys.exit(2)


def page_report(d):
    """-> (n_crops, median_h, max_h, bands, head) or raise.

    Each band is (name, height, ratio, position) with position one of
    HEAD_POS / FOOT_POS / MID_POS. ★ MID_POS is the one that means something:
    nothing is legitimately tall in the middle of a body of set text except a
    centred heading.

    ⛔ Never returns a plausible number on failure: a page it cannot measure
    raises, so 'no bands' can never mean 'could not look'.
    """
    names = sorted(n for n in os.listdir(d) if LINE_RE.match(n))
    if not names:
        raise RuntimeError("no line*.png in %s" % d)
    hs = []
    for n in names:
        try:
            hs.append((n, Image.open(os.path.join(d, n)).size[1]))
        except Exception as e:                            # unreadable crop
            raise RuntimeError("cannot read %s: %s" % (n, e))
    med = statistics.median(h for _, h in hs)
    if med <= 0:
        raise RuntimeError("median crop height is %r in %s" % (med, d))
    tall = [(n, h, h / float(med)) for n, h in hs if h > med * BAND]
    head = [t for t in tall if t[0] == HEAD]
    # ⚠ The foot is the LAST crop by name, which is the last line on the page
    # because names are zero-padded and sorted. A one-crop page has no middle.
    last = names[-1]
    no_pos = os.environ.get("HEXAPLA_NO_POSITION")   # known-bad control
    bands = []
    for n, h, r in tall:
        if n == HEAD:
            continue
        if no_pos:
            pos = MID_POS          # ⛔ the screen stops discriminating
        elif n == last:
            pos = FOOT_POS
        else:
            pos = MID_POS
        bands.append((n, h, r, pos))
    return len(hs), med, max(h for _, h in hs), bands, head


# ───── THE CROP-COUNT SCREEN ─────
#
# ★ ADDED 2026-09-12, AND IT IS STRONGER THAN THE BAND FRACTION.
#
# The band fraction answers «is some crop multi-line». It does NOT cleanly
# separate a page with two centred headings from a page whose line finder has
# collapsed, because both can sit near 20 %. luke_kit2 p61 (7 bands of 31) and
# p62 (6 of 29) looked like ordinary heading pages by that measure. They are
# not: p61/line17 holds SEVEN text lines and p62/line15 holds NINE, verified
# by eye against a control crop from p63, which held exactly one.
#
# What separates them is the pair below, and it needs no vision at all:
#
#   1. the page yields FAR FEWER crops than its own kit's healthy pages, and
#   2. its median crop height is correspondingly INFLATED.
#
# Both must hold. (1) alone is a genuinely short page — a book ending, a
# half-page of text — and those have NORMAL crop heights. (2) alone is a page
# with a few headings. Together they mean lines are being MERGED.
#
# luke_kit2, measured: healthy pages 54-61 crops at median h 65-69;
#   p61  31 crops, median  94   → 7 text lines in one crop
#   p62  29 crops, median  90   → 9 text lines in one crop
#   p66  13 crops, median 235   → 11 text lines in one crop
#
# ⚠ The kit is its OWN control: the comparison is against the median crop
# count of the other pages in the same chunk, never a fixed number, because
# page geometry differs per kit and per volume.
# ⛔ Needs >= 3 measured pages in the chunk to have a denominator at all. With
# fewer it prints that it could not screen, and does NOT return a verdict —
# a check that cannot see its denominator did not pass, it did not look.
COUNT_FRAC = 0.75        # crops below this share of the kit median = suspicious
HEIGHT_FRAC = 1.25       # AND median height above this multiple = merged lines
MIN_PAGES_TO_SCREEN = 3


def _median(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def _crop_count_verdict(chunk, rows):
    """-> [(chunk, page, n, kit_n, med_h, kit_med_h)] for pages whose line
    finder has collapsed. Prints its own denominator note when it cannot run."""
    if len(rows) < MIN_PAGES_TO_SCREEN:
        print("  %-14s ⚠ crop-count screen DID NOT RUN — %d page(s) is no "
              "denominator (needs %d)" % (chunk, len(rows), MIN_PAGES_TO_SCREEN))
        return []
    kit_n = _median([n for _, n, _ in rows])
    kit_h = _median([h for _, _, h in rows])
    out = []
    for page, n, h in rows:
        if n < kit_n * COUNT_FRAC and h > kit_h * HEIGHT_FRAC:
            out.append((chunk, page, n, kit_n, h, kit_h))
    return out


# ★★ THE CONTROL FOR THE POSITION SCREEN.
#
# ⚠⚠ A check that cannot run returns a clean-looking 0, so this screen must
# be able to FAIL on demand. `--selftest` builds pages of KNOWN geometry and
# asserts BOTH directions:
#
#   page HEADFOOT  tall line00 + tall LAST crop, uniform middle  → 0 mid-page
#   page MIDBAND   uniform, one tall crop in the MIDDLE          → 1 mid-page
#
# ⛔ Asserting only that the mid-band page flags would pass a screen that
# flags everything. Both directions, or it proves nothing.
#
# ▶ HEXAPLA_NO_POSITION=1 makes page_report call every band MID_POS. The
# HEADFOOT page then reports a mid-page band and this selftest FAILS (rc 1),
# which is what makes the rc 0 above mean something.
def _selftest():
    import shutil
    import tempfile

    med_h, tall_h, w = 60, 200, 400
    root = tempfile.mkdtemp(prefix="cropheights_selftest_")
    try:
        def build(name, tall_idx, n=12):
            d = os.path.join(root, name)
            os.makedirs(d)
            for i in range(n):
                h = tall_h if i in tall_idx else med_h
                Image.new("L", (w, h), 255).save(
                    os.path.join(d, "line%02d.png" % i))
            return d

        # line00 = running head, line11 = last crop = printer's foot
        headfoot = build("headfoot", {0, 11})
        # line05 sits in the MIDDLE - the merged-row defect
        midband = build("midband", {5})

        ok = True
        no_pos = os.environ.get("HEXAPLA_NO_POSITION")
        print("  known-bad HEXAPLA_NO_POSITION = %s"
              % ("SET - the screen is disabled" if no_pos else "unset"))

        _, _, _, bands, head = page_report(headfoot)
        mids = [b for b in bands if b[3] == MID_POS]
        feet = [b for b in bands if b[3] == FOOT_POS]
        print("  HEADFOOT page: %d head, %d foot, %d MID-PAGE (want 0 mid)"
              % (len(head), len(feet), len(mids)))
        if len(mids) != 0:
            ok = False
        if len(head) != 1:
            print("       ⛔ the running head was not seen as a head")
            ok = False

        _, _, _, bands, head = page_report(midband)
        mids = [b for b in bands if b[3] == MID_POS]
        print("  MIDBAND  page: %d MID-PAGE (want 1), names %s"
              % (len(mids), [b[0] for b in mids]))
        if len(mids) != 1 or mids[0][0] != "line05.png":
            ok = False

        if ok:
            print("SELFTEST PASSED - position separates a head/foot band from a "
                  "mid-page one, in BOTH directions.")
            return 0
        print("SELFTEST FAILED - the position screen does not discriminate.")
        return 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk")
    ap.add_argument("--page")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="build synthetic pages of known geometry and assert "
                         "the POSITION screen in BOTH directions. The known-bad "
                         "control is HEXAPLA_NO_POSITION=1, which must make it "
                         "fail.")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())

    if not a.all and not a.chunk:
        die("give --chunk <name> [--page pNN] or --all - NOTHING WAS CHECKED")
    if not os.path.isdir(PREP):
        die("no prep dir at %s - this check DID NOT RUN" % PREP)

    chunks = sorted(os.listdir(PREP)) if a.all else [a.chunk]
    checked = flagged = thin = unmeasured = 0
    midpages = []        # (chunk, page, [names]) - the pages POSITION indicts
    broken = []          # (chunk, page, n_crops, kit median crops, med h, kit med h)

    for chunk in chunks:
        # per-chunk tally for the CROP-COUNT screen -- see _crop_count_verdict
        chunk_rows = []
        cd = os.path.join(PREP, chunk)
        if not os.path.isdir(cd):
            die("no such chunk dir: %s" % cd)
        # ⚠ a chunk dir also holds non-page dirs (`_sheets`). Counting one as an
        # unmeasurable PAGE made --all exit 2 over a directory that was never a
        # page - a failed measurement that was not one. Pages are `p<NN>` only.
        pages = [a.page] if a.page else sorted(
            p for p in os.listdir(cd)
            if os.path.isdir(os.path.join(cd, p)) and re.match(r"^p\d", p))
        for page in pages:
            d = os.path.join(cd, page)
            if not os.path.isdir(d):
                die("no such page dir: %s" % d)
            try:
                n, med, mx, bands, head = page_report(d)
            except RuntimeError as e:
                unmeasured += 1
                print("  %-14s %-6s  ⛔ COULD NOT MEASURE: %s" % (chunk, page, e))
                continue
            checked += 1
            chunk_rows.append((page, n, med))
            note = ""
            if n < MIN_CROPS:
                thin += 1
                note = ("  ⚠ only %d crop(s) - the median is NOT a control here; "
                        "compare against a NEIGHBOURING page" % n)
            if bands:
                flagged += 1
            mids = [b for b in bands if b[3] == MID_POS]
            if mids:
                midpages.append((chunk, page, [b[0] for b in mids]))
            print("  %-14s %-6s  %3d crops, median h=%3d, max=%3d, %d band(s), "
                  "%d MID-PAGE%s"
                  % (chunk, page, n, med, mx, len(bands), len(mids), note))
            for nm, h, r, pos in bands:
                if pos == FOOT_POS:
                    print("       ·  %-12s h=%-4d = %.1fx median  → printer's FOOT "
                          "(last crop), EXPECTED" % (nm, h, r))
                else:
                    print("       ⛔ %-12s h=%-4d = %.1fx median  → MID-PAGE SUSPECT: "
                          "~%d text lines, or a centred heading"
                          % (nm, h, r, max(2, int(round(r)))))
            for nm, h, r in head:
                print("       ·  %-12s h=%-4d = %.1fx median  → running head, EXPECTED "
                      "(not counted)" % (nm, h, r))

        broken += _crop_count_verdict(chunk, chunk_rows)

    print("\n%d page(s) measured, %d with band(s), %d with MID-PAGE band(s), "
          "%d too thin to self-control, %d unmeasurable."
          % (checked, flagged, len(midpages), thin, unmeasured))

    if midpages:
        print("")
        print("★ POSITION SCREEN — bands that are NOT the running head or the")
        print("   printer's foot. ⚠ A centred chapter heading lands here too, so")
        print("   this is a QUESTION about those crops, not a page verdict — but")
        print("   it is the signal the band FRACTION drowns.")
        for chunk, page, names in midpages:
            print("   %-14s %-6s  %s" % (chunk, page, ", ".join(names)))

    if broken:
        print("")
        print("⛔⛔ BROKEN LINE FINDER — these pages MUST NOT BE READ AT ALL.")
        print("   A `lineNN` on them is not a line, so every page/line ADDRESS")
        print("   they carry is void — including one already merged.")
        print("   ⛔ --robust-block and --full-width do NOT fix this class.")
        for chunk, page, n, kn, mh, km in broken:
            print("   %-14s %-6s %3d crops vs %d kit median (%.0f%%), "
                  "median h=%d vs %d (%.1fx)"
                  % (chunk, page, n, kn, 100.0 * n / kn, mh, km,
                     float(mh) / km if km else -1))
    if unmeasured:
        die("%d page(s) could not be measured - this run is NOT a pass" % unmeasured)
    if not checked:
        die("nothing was measured - this check DID NOT RUN")
    if broken and not flagged:
        sys.exit(1)
    if flagged:
        print("⛔ A band is SUSPECT, not a verdict - clear it by looking at that ONE crop.")
        print("   But a page where a LARGE FRACTION of crops are bands has a broken line")
        print("   finder, and ⛔ must not be read at all: an address it carries is void.")
        sys.exit(1)
    print("✅ no band found. ⛔ That is «no crop is multi-line», NOT «this page is")
    print("   readable» - run thorlaks_crop_widths.py too; they are different defects.")


if __name__ == "__main__":
    main()
