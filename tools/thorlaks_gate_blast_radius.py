# -*- coding: utf-8 -*-
"""Measure the blast radius of promoting ONE chunk_check rule from SOFT to HARD.

THE RULE (tools/thorlaks_chunk_check.py, NUMERAL SYNC, second loop):

    "NUMERAL SYNC: lineNN's text carries a bare N that the NUMERALS table
     does not list"

Today it is `[.]` SOFT, so a chunk carrying it still prints "[ok] no HARD
finding". That is how BOTH Luke idx 64 reads passed while a real verse
(11:48) sat under the wrong address: its numeral was transcribed inline but
never tabled, and nothing hard fired.

The owner's ruling (2026-09-19): MEASURE the blast radius BEFORE changing it.
How many chunks/pages that pass today would start failing, and on which books.

⛔ This script CHANGES NOTHING. It only classifies what is already on disk.

Output columns per chunk:
    hard   - HARD findings TODAY (a chunk already failing cannot "flip")
    bare   - findings of the class under consideration
    verdict:
        PASS->HARD   0 hard today, >=1 bare  <- THE BLAST RADIUS
        pass         0 hard today, 0 bare    <- unaffected
        already HARD >=1 hard today          <- unaffected (already blocked)
        REFUSED      chunk_check refused the file (missing section etc.)

USAGE
    python tools/thorlaks_gate_blast_radius.py                 # live chunks
    python tools/thorlaks_gate_blast_radius.py --include-stash # + _stash_* copies
    python tools/thorlaks_gate_blast_radius.py --selftest      # the control

CONTROL (--selftest): the class matcher is proved in BOTH directions on two
fixtures - one carrying an untabled bare numeral over text, one clean. A
matcher that cannot fire has measured nothing, and a blast radius of 0 from a
dead matcher is the exact "plausible number" failure this repo keeps hitting.

Run from C:\\Projects\\Hexapla-releases (the data directory); the tool is
addressed by absolute path.
"""

from __future__ import print_function

import io
import os
import re
import sys
import glob
import argparse
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_chunk_check as cc            # noqa: E402

# The exact tail of the SOFT message this ruling is about. Matching on the
# message text is deliberate: it breaks loudly if the wording changes, rather
# than silently measuring nothing.
BARE_RE = re.compile(r"NUMERAL SYNC: line\d+'s text carries a bare \d+ "
                     r"that the NUMERALS table does not list")

# The gate's real input is a crop read, not an adjudication brief or a stitched
# read. Only these files are ever handed to chunk_check.
CHUNK_GLOBS = ["_work/*_CROP_READ_CHUNK*.md", "_work/*_CROP_READB_CHUNK*.md"]
STASH_GLOBS = ["_work/_stash_*/*_CROP_READ_CHUNK*.md",
               "_work/_stash_*/*_CROP_READB_CHUNK*.md"]

PAGE_RE = re.compile(r"^([a-z0-9]+)_p(\d+)_CROP_READ(B?)_CHUNK(\d+)\.md$")

# Which prep kit holds each book's crops. A chunk whose kit is unknown is
# still measured, but its HARD baseline omits the COVERAGE check, so it is
# reported as such rather than counted as a clean pass.
KIT_FOR_BOOK = {"luke": "research/_prep/luke_kit2"}


def kit_dir_for(book, page):
    root = KIT_FOR_BOOK.get(book)
    if not root:
        return None
    d = os.path.join(root, "p%d" % page)
    return d if os.path.isdir(d) else None


def measure(path, kit_dir):
    """(hard_n, bare_n, refused_reason_or_None)."""
    out = sys.stdout
    sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else out
    try:
        hard, soft = cc.check(path, kit_dir=kit_dir, quiet=True)
    except SystemExit as e:
        return (0, 0, "chunk_check refused (exit %s)" % e.code)
    except Exception as e:                    # noqa: BLE001
        return (0, 0, "%s: %s" % (type(e).__name__, e))
    finally:
        sys.stdout = out
    return (len(hard), len([s for s in soft if BARE_RE.search(s)]), None)


# ---------------------------------------------------------------------------
# CONTROL
# ---------------------------------------------------------------------------
_HEAD = u"# Luke idx 99 - CROP READ chunk 1 (line01-line03)\n\n## LINES\n"
_TAIL = u"\n## HN\n- none\n\n## NOTES\n- none\n"

_DIRTY = (_HEAD +
          u"line01 | 3 Og hann sagde\n"
          u"line02 | vid thu 4 Enn hann svarade\n"
          u"line03 | 5 Thad er skrifad\n"
          u"\n## NUMERALS\nline01 | 3 | Og\nline03 | 5 | Thad\n" + _TAIL)

_CLEAN = (_HEAD +
          u"line01 | 3 Og hann sagde\n"
          u"line02 | 4 Enn hann svarade\n"
          u"line03 | 5 Thad er skrifad\n"
          u"\n## NUMERALS\nline01 | 3 | Og\nline02 | 4 | Enn\n"
          u"line03 | 5 | Thad\n" + _TAIL)


def selftest():
    ok = True
    tmp = tempfile.mkdtemp(prefix="gate_blast_")
    for name, body, want in (("dirty", _DIRTY, True), ("clean", _CLEAN, False)):
        p = os.path.join(tmp, name + ".md")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        _h, bare, refused = measure(p, None)
        got = bare > 0
        good = (got == want) and not refused
        ok &= good
        print("  %-52s %s" % (
            "an untabled bare numeral is MATCHED" if want
            else "a fully tabled chunk matches NOTHING",
            "ok" if good else "FAIL (bare=%d refused=%s)" % (bare, refused)))
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-stash", action="store_true",
                    help="also measure superseded copies under _work/_stash_*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    paths = []
    for g in CHUNK_GLOBS + (STASH_GLOBS if a.include_stash else []):
        paths.extend(glob.glob(g))
    paths = sorted(set(paths))
    if not paths:
        sys.stderr.write("no crop-read chunks found - run from "
                         "C:\\Projects\\Hexapla-releases\n")
        return 2

    rows = []
    for p in paths:
        m = PAGE_RE.match(os.path.basename(p))
        book, page = (m.group(1), int(m.group(2))) if m else ("?", -1)
        kit = kit_dir_for(book, page) if m else None
        hard, bare, refused = measure(p, kit)
        rows.append({"path": p, "book": book, "page": page, "kit": kit,
                     "hard": hard, "bare": bare, "refused": refused})

    print("%-46s %5s %5s  %s" % ("chunk", "hard", "bare", "verdict"))
    print("-" * 78)
    for r in rows:
        if r["refused"]:
            v = "REFUSED - %s" % r["refused"]
        elif r["hard"]:
            v = "already HARD"
        elif r["bare"]:
            v = "PASS->HARD"
        else:
            v = "pass"
        if r["kit"] is None and not r["refused"]:
            v += "  (no kit: COVERAGE not checked)"
        print("%-46s %5d %5d  %s"
              % (os.path.relpath(r["path"], "_work")[:46],
                 r["hard"], r["bare"], v))

    flips = [r for r in rows if not r["refused"] and not r["hard"] and r["bare"]]
    live = [r for r in rows if not r["refused"]]
    print("")
    print("chunks measured        : %d (%d refused)"
          % (len(rows), len(rows) - len(live)))
    print("already HARD today     : %d" % len([r for r in live if r["hard"]]))
    print("pass today             : %d" % len([r for r in live if not r["hard"]]))
    print("  of those, WOULD FLIP : %d   <- THE BLAST RADIUS" % len(flips))

    pages = {}
    for r in live:
        k = (r["book"], r["page"])
        pages.setdefault(k, {"n": 0, "flip": 0, "hard": 0})
        pages[k]["n"] += 1
        if r["hard"]:
            pages[k]["hard"] += 1
        elif r["bare"]:
            pages[k]["flip"] += 1
    print("")
    print("%-14s %7s %7s %7s  %s" % ("page", "chunks", "hard", "flip", "page verdict"))
    for (book, page) in sorted(pages):
        d = pages[(book, page)]
        # ⚠ A page can hold BOTH. "already blocked" must not hide a flip: the
        # blocked chunk may be a superseded copy while the flipping one is the
        # live read. Report the flip whenever there is one.
        if d["flip"] and d["hard"]:
            pv = "PAGE FLIPS pass->HARD (and holds %d already-HARD chunk(s))" % d["hard"]
        elif d["flip"]:
            pv = "PAGE FLIPS pass->HARD"
        elif d["hard"]:
            pv = "already blocked"
        else:
            pv = "unaffected"
        print("%-14s %7d %7d %7d  %s"
              % ("%s p%d" % (book, page), d["n"], d["hard"], d["flip"], pv))

    books = sorted({b for (b, _p) in pages})
    print("")
    print("books represented on disk: %s" % (", ".join(books) or "none"))
    print("⚠ This is the blast radius over the chunks THAT EXIST ON DISK, which "
          "is not\n  the corpus. Books merged before the crop-read method have "
          "no chunks to measure;\n  for them the radius is UNKNOWN, not zero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
