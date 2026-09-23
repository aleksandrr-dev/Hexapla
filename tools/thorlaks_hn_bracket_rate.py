#!/usr/bin/env python
"""Flag a Þorláksbiblía read that bracketed NO `[HN]` sites.

    python tools/thorlaks_hn_bracket_rate.py                 # held reads + parts
    python tools/thorlaks_hn_bracket_rate.py _work/luke_p64_read_2026-09-14.md
    python tools/thorlaks_hn_bracket_rate.py --selftest

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## Why this exists

★ The campaign's standing rule is «**a reader that brackets SOME `[HN]` sites
may silently COMMIT to others**». It was written about a reader that bracketed
*some*. Measured 2026-09-14 across the four held Luke reads, the worse case is
a reader that brackets **none**:

    idx 61 → 5 brackets   idx 62 → 0   idx 63 → 10   idx 64 → 0

A zero-bracket read looks CLEAN and is not: it defaulted every H/N decision on
the page instead of adjudicating them. ⛔ That is indistinguishable from a
careful read by reading the file, which is exactly the class this project
refuses to leave to a human eye.

## What it measures — and what it deliberately does NOT

It reports brackets against a **DENOMINATOR**: every word-initial `H`/`N` site
on the page, which is where the H/N confusion lives in this hand. A bare count
is not interpretable (a page with two capitals and no brackets is fine).

⚠⚠ **THE DENOMINATOR IS `brackets + remaining capitals`, NEVER THE CAPITALS
ALONE.** A bracketed site no longer matches `SITE` — `[HN]oggorm` has no
capital followed by a lowercase letter — so counting only the capitals means
**bracketing a site DELETES it from its own denominator**. Measured 2026-09-14:
`luke_p65`, a well-bracketed page, printed «**28 of 2 bracketed**». The flag
direction was never affected (with zero brackets the two formulas coincide), so
the tool was sound where it was used and nonsense where it was not — ★ **a
diagnostic can be correct in the direction it was built for and still print
gibberish in the other; the untested direction is where it rots.**

⛔ **THIS TOOL DOES NOT RULE ON ANY SITE, AND MUST NOT LEARN TO.** H/N is with
the owner and delegated pixel adjudication is MEASURED-UNFIT. ⛔ NOT BY REGEX,
NOT BY DICTIONARY — a tool that guessed H or N here would be re-committing the
closed error. It only asks whether the READER did its job.

⚠ A nonzero rate is NOT a pass either. Bracketing 5 of 40 sites still leaves 35
committed silently. The rate is a smoke alarm, not a screen.

Exit 0 = every file examined bracketed at least one site.
Exit 1 = at least one file has a nonzero H/N denominator and ZERO brackets.
Exit 2 = nothing to examine (⛔ never a plausible pass).
"""
import argparse
import glob
import io
import os
import re
import sys

BRACKET = re.compile(r"\[HN\]")
# Word-initial capital H or N. The blackletter H and N are the confusable pair;
# this is the population a reader had to decide on.
SITE = re.compile(r"(?<![A-Za-zÀ-ÿ])[HN][a-zà-ÿæøþðöũñ̃]", re.UNICODE)

DEFAULT_GLOBS = ["_work/*_read_*.md", "research/_parts/*.md"]

SELFTEST = [
    # (text, expect_brackets, expect_denominator)
    # brackets present -> OK.  denom = 1 bracket + 3 capitals (Huor/Nær/Hier)
    ("Huor er [HN]oggorm/Nær Hier", 1, 4),
    # capitals, no brackets -> FLAG.  denom == capitals when b == 0
    ("Huor er Noggorm/Nær Hier Holl", 0, 5),
    # no denominator at all -> not judged
    ("engin hofud lowercase only", 0, 0),
    # ★ THE DENOMINATOR CONTROL (added 2026-09-14 with the p65 fix):
    # a FULLY bracketed page must score 100 %, not «2 of 0» and not >100 %.
    # Under the old capitals-only denominator this case read as «no H/N
    # sites, not judged» — a perfectly adjudicated page scored as empty.
    ("[HN]un og [HN]afn", 2, 2),
]


def scan(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("FAILED to read %s: %s\n" % (path, exc))
        return None
    # Do not count the prose ABOVE the verse text: a record's own commentary
    # says "[HN]" while discussing the rule and would mask a zero.
    body = text
    for marker in ("## Verse text", "## ø sites", "## ø candidate"):
        idx = text.find(marker)
        if idx >= 0:
            body = text[idx:]
            break
    return count(body)


def count(text):
    """-> (brackets, denominator).

    ⚠ The denominator is brackets + REMAINING capitals. A bracketed site does
    not match SITE, so the capitals alone shrink as the page is adjudicated.
    """
    b = len(BRACKET.findall(text))
    return b, b + len(SITE.findall(text))


def selftest():
    ok = True
    for i, (text, want_b, want_denom) in enumerate(SELFTEST, 1):
        b, denom = count(text)
        got_flag = (denom > 0 and b == 0)
        want_flag = (want_denom > 0 and want_b == 0)
        bad = (b != want_b or denom != want_denom or got_flag != want_flag
               or b > denom)
        if bad:
            ok = False
        print("  case %d: brackets=%d denom=%d (want %d/%d) flag=%s  %s"
              % (i, b, denom, want_b, want_denom, got_flag,
                 "FAIL" if bad else "ok"))
    if ok:
        print("✅ SELFTEST PASSED — it flags a zero-bracket page WITH capitals,")
        print("   does NOT flag a page that has no H/N sites at all, and scores")
        print("   a FULLY bracketed page at 100 %, never above it.")
        print("   It fails in both directions, so it cannot be tuned away.")
        return 0
    print("⛔ SELFTEST FAILED")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    paths = list(a.files)
    if not paths:
        for g in DEFAULT_GLOBS:
            # ⚠ Windows glob is CASE-INSENSITIVE — skip the shouty campaign
            # docs and every .bak-* that a bare pattern also matches.
            for p in glob.glob(g):
                base = os.path.basename(p)
                if ".bak" in base or base.isupper() or base[0].isupper():
                    continue
                paths.append(p)
    paths = sorted(set(paths))
    if not paths:
        sys.stderr.write("⛔ NOTHING TO EXAMINE — that is not a pass.\n")
        return 2

    print("%-52s %8s %8s  %s" % ("file", "[HN]", "H/N total", "verdict"))
    print("-" * 88)
    flagged = []
    for p in paths:
        got = scan(p)
        if got is None:
            print("%-52s %8s %8s  ⛔ UNREADABLE" % (p[-52:], "?", "?"))
            flagged.append(p)
            continue
        b, denom = got
        if denom == 0:
            verdict = "— no H/N sites, not judged"
        elif b == 0:
            verdict = "⛔ ZERO BRACKETS — every site committed silently"
            flagged.append(p)
        else:
            verdict = "⚠ %d of %d bracketed (%.0f %%; the rest are committed)" \
                % (b, denom, 100.0 * b / denom)
        print("%-52s %8d %8d  %s" % (p[-52:], b, denom, verdict))

    print()
    if flagged:
        print("⛔ %d file(s) bracketed NOTHING while carrying H/N sites."
              % len(flagged))
        print("   Those reads DEFAULTED every H/N decision. They are not")
        print("   clean pages; they are unadjudicated ones.")
        print("   ▶ When the owner rules H/N, these need a pass of their own.")
        print("   ⛔ Do not resolve them by regex or dictionary — closed.")
        return 1
    print("✅ every file examined bracketed at least one site.")
    print("⚠ NOT a clearance — bracketing 5 of 40 still leaves 35 committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
