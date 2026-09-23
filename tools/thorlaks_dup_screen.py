#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Flag text DUPLICATED inside a verse by the stitcher -- the additive twin of
the silent losses fixed in f9aa584.

WHY THIS EXISTS
    `thorlaks_adjudicate_merge.py` rebuilds a verse by appending one piece per
    adjudicated site, in order. Two ADJACENT sites can carry verdict TEXTS that
    overlap (Luke 14:1, 2026-09-21: a delete-site whose NEITHER verdict supplied
    `þ° framme`, beside a replace-site whose B verdict supplied `framme þ hm̄.`).
    Both pieces were appended, so `framme þ` was written twice. Nothing checked.

⛔ THE ONLY EXISTING SCREEN CANNOT SEE THIS CLASS -- BY CONSTRUCTION, NOT BY A
   NARROW MARGIN. `thorlaks_verse_length_witness.py` flags `ratio < med * FLOOR`
   and has NO UPPER BOUND; it is a witness for LOST text and says so. A
   duplicated verse is LONGER, so its ratio rises and it can never be flagged,
   however large the duplication.

THE CHECK
    Within a verse (bracketed apparatus stripped, `/` treated as a separator),
    flag any contiguous repeated bigram `w1 w2 w1 w2` where len(w1)+len(w2) >= 4.

⚠ LIMIT, STATED: exact-token repetition only. A verdict overlap that duplicates
  with DIFFERENT spelling (`framc þ` beside `framme þ`) is NOT caught here. That
  variant belongs at merge time, comparing a NEITHER verdict's tokens against the
  adjacent site's chosen text after folding.

⛔ This screen NAMES a verse and stops. It never rewrites a verse, a verdict line
  or a read. Genuine scripture repeats -- `Gud miñ Gud miñ` (Mark 15:34, Matthew
  27:46) is the real text -- so a hit is a QUESTION, never a correction.

Exit codes
    0  no duplication found
    1  at least one verse flagged -- look at each; some are genuine
    2  bad usage

Controls (a screen with no failing control is not a screen)
    --selftest                 known-good and known-bad, both directions
    HEXAPLA_NO_DUPCHK=1        disables the check, so the known-bad PASSES;
                               this is how you prove the check is what catches it
    Live positive control on disk, a record, ⛔ NEVER to be edited:
        _work/luke_p67_MERGE_CANDIDATE.md   carries `þ° framme þ framme þ hm̄.`
"""

import argparse
import glob
import os
import re
import sys

RELEASES = r"C:\Projects\Hexapla-releases"
VERSE_RE = re.compile(r"^(\d+)\s+(.*)$")
BRACKET_RE = re.compile(r"\[[^\]]*\]")


def enabled():
    return os.environ.get("HEXAPLA_NO_DUPCHK") != "1"


def words(text):
    """Apparatus out, virgule as a separator, then plain tokens."""
    t = BRACKET_RE.sub(" ", text)
    t = t.replace("/", " ")
    return [w for w in t.split() if w]


def dup_bigrams(text, minlen=4):
    """Every contiguous repeated bigram w1 w2 w1 w2 in the verse."""
    ws = words(text)
    out = []
    for i in range(len(ws) - 3):
        w1, w2 = ws[i], ws[i + 1]
        if ws[i + 2] == w1 and ws[i + 3] == w2 and len(w1) + len(w2) >= minlen:
            out.append("%s %s %s %s" % (w1, w2, w1, w2))
    return out


def scan_file(path, minlen=4):
    """[(lineno, verse_no, snippet)] for one file."""
    hits = []
    if not enabled():
        return hits
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            m = VERSE_RE.match(raw.rstrip("\n"))
            if not m:
                continue
            for snip in dup_bigrams(m.group(2), minlen):
                hits.append((n, m.group(1), snip))
    return hits


def corpus_files(root):
    """Every MERGED book. The free-check rule: full denominator, never a sample."""
    out = []
    for p in sorted(glob.glob(os.path.join(root, "research", "thorlaks_*.md"))):
        b = os.path.basename(p)
        if ".bak" in b or "CAMPAIGN" in b or "CONVENTIONS" in b:
            continue
        out.append(p)
    return out


def report(paths, minlen=4):
    total = 0
    scanned = 0
    for p in paths:
        if not os.path.exists(p):
            print("  MISSING: %s" % p)
            continue
        scanned += 1
        hits = scan_file(p, minlen)
        if hits:
            print("=== %s ===" % os.path.basename(p))
            for n, verse, snip in hits:
                print("  line %-5d v%-4s  «%s»" % (n, verse, snip))
            total += len(hits)
    print("")
    print("%d file(s) scanned, %d duplicated span(s) flagged." % (scanned, total))
    if total:
        print("⚠ A hit is a QUESTION, not a defect: scripture does repeat "
              "(«Gud miñ Gud miñ» = Mark 15:34 / Matthew 27:46 is the real text).")
        print("⛔ Confirm against the CROP before changing anything, and never "
              "edit a record to satisfy this screen.")
        return 1
    if not enabled():
        print("⚠ HEXAPLA_NO_DUPCHK=1 — THE CHECK DID NOT RUN. This 0 means nothing.")
    return 0


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="dupchk_")

    good = os.path.join(tmp, "thorlaks_good.md")
    with open(good, "w", encoding="utf-8") as fh:
        fh.write("# good\n")
        fh.write("1 Og þ skiede ad hann kom a Sabbathsdeige j hws nockurs.\n")
        fh.write("2 [unnumbered — no printed numeral] Og sia ad madr nockur.\n")

    bad = os.path.join(tmp, "thorlaks_bad.md")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("# bad\n")
        fh.write("1 hafde var þ° framme þ framme þ hm̄.\n")

    print("--- known-good ---")
    rc_good = report([good])
    print("--- known-bad ---")
    rc_bad = report([bad])

    # The live positive control: the real merge candidate, still on disk.
    live = os.path.join(RELEASES, "_work", "luke_p67_MERGE_CANDIDATE.md")
    rc_live = None
    if os.path.exists(live):
        print("--- live positive control (%s) ---" % os.path.basename(live))
        rc_live = report([live])

    print("--- selftest ---")
    print("known-good  rc=%d (want 0)" % rc_good)
    print("known-bad   rc=%d (want 1; want 0 under HEXAPLA_NO_DUPCHK=1)" % rc_bad)
    if rc_live is not None:
        print("live ctrl   rc=%d (want 1; want 0 under HEXAPLA_NO_DUPCHK=1)" % rc_live)
    else:
        print("live ctrl   ABSENT — %s is gone. That fixture is a RECORD; "
              "find out who removed it." % live)

    if not enabled():
        ok = rc_good == 0 and rc_bad == 0 and (rc_live in (0, None))
        print("HEXAPLA_NO_DUPCHK=1: the check is disabled, so the known-bad PASSES.")
        print("selftest %s" % ("PASS (check confirmed to be what catches it)"
                               if ok else "FAIL"))
        return 0 if ok else 1

    ok = rc_good == 0 and rc_bad == 1 and (rc_live in (1, None))
    print("selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", action="append", help="scan one file (repeatable)")
    ap.add_argument("--corpus", action="store_true",
                    help="scan every merged book (the full denominator)")
    ap.add_argument("--root", default=RELEASES)
    ap.add_argument("--minlen", type=int, default=4,
                    help="minimum len(w1)+len(w2) of a flagged bigram")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.corpus:
        return report(corpus_files(args.root), args.minlen)
    if args.file:
        return report(args.file, args.minlen)
    ap.error("one of --corpus, --file or --selftest is required")


if __name__ == "__main__":
    sys.exit(main())
