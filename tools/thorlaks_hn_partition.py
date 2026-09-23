#!/usr/bin/env python
"""Partition the H/N witness list into CONFIDENT and AMBIGUOUS. Rules on nothing.

    python tools/thorlaks_hn_partition.py            # the two buckets
    python tools/thorlaks_hn_partition.py --selftest # two-way control
    python tools/thorlaks_hn_partition.py --sites    # one line per SITE

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## What this is, and what it is NOT

The owner ruled (2026-09-14): **"rule a default, flag the rest."** That ruling
needs a partition of `thorlaks_hn_case_pairs.py`'s 243 sites into the ones a
default may cover and the ones that must be flagged for his eye.

✅ He supplied the letter on **2026-09-16: `H`, over the STRICT cut ONLY.** ⛔ This
script still does not guess and still does not write — it prints the partition
and nothing else. The ruling is EXECUTED by `thorlaks_hn_apply_default.py`,
which derives its site list from `build()` here on every run.

⛔ It introduces **NO new evidence**. Every number below is one of the three
columns `case_pairs` already prints, re-read from the same `research/_parts/`
files through the same tally. It is a SORTING AID over a witness list, so it
inherits every limitation of that list: agreement with it proves nothing, and a
site it calls CONFIDENT is confident about the CORPUS'S READERS, not about the
ink. ▶ `research/_evidence/thorlaks_hn_owner_verdict_2026-09-14.md`.

## The statistic, and why these two numbers

For a word tail T, `case_pairs` guarantees `n<T>` (lowercase n) is **unattested**
— that is a precondition of being listed at all. So the corpus's own readers
have written T with only three initials:

    S  = h<T> + H<T>    every reading that took the initial as an h-sort
    A  = N<T>           every reading that took it as N

- **R = S / A** — how lopsided the readers were on this exact word form.
- **S** — how much evidence that ratio rests on.

A site is CONFIDENT when **R >= 10 and S >= 10**: the h-sort readings outnumber
the N readings by an order of magnitude AND there are at least ten of them, so
the ratio is not built on one or two tokens. Everything else is AMBIGUOUS.
⚠ The two thresholds are a declared cut, not a fitted one — ⛔ if a future run
disagrees with the owner at the pixel, that is a FINDING about the witness list,
⛔ never a licence to move 10 to 8.

## The control, and it must fire BOTH ways

- ▶ `Nid` MUST land CONFIDENT     — 1 N against 80 lowercase `hid`, 0 capital H.
- ▶ `Nofud` MUST land AMBIGUOUS   — 10 N against 6 H + 3 h; the readers split.
  ★ A cut that calls `Nofud` confident is calling a coin toss confident.

### ★★ Why the control had to be FROZEN (2026-09-16, and it is a finding)

Both controls were read LIVE from the corpus until
`thorlaks_hn_apply_default.py` executed the owner's ruling and rewrote all 27
CONFIDENT sites to `H`. `candidates()` requires a live capital-`N` reading, so
**the patched tails left the witness list entirely and the CONFIDENT bucket
went to zero — taking the live positive control with it.**

★★ **A patcher that resolves a bucket destroys any control drawn from that
bucket.** The bucket is empty *because the tool worked*, so an empty bucket can
never again be distinguished from a broken cut by a live reading.

⛔ This is NOT the «redefine the feature until the control passes» failure. The
instrument — `classify()` — is byte-unchanged, and the fixture carries the
SAME TWO WITNESSES at their real pre-patch counts. What moved is only where the
numbers are read from: the phenomenon was removed from the corpus by an
authorised action, so the control had to stop depending on the corpus still
containing it. The live half is still run and still printed, and a live row
that DISAGREES with the fixture fails the selftest.
⚠ `HEXAPLA_NO_HNPART=1` must still break it — the fixture's `Nofud` row is what
the known-bad path misclassifies.

Exit 0 = both controls fired and the partition printed.
Exit 3 = a control did not fire (⛔ never a usable partition), or the upstream
         witness list refused. Set `HEXAPLA_NO_HNPART=1` to force the known-bad
         path and confirm the control is alive.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_hn_case_pairs as cp   # noqa: E402  the witness list itself

MIN_RATIO = 10.0
MIN_SUPPORT = 10

CONTROL_CONFIDENT = "id"      # Nid   : 1 N vs 80 h
CONTROL_AMBIGUOUS = "ofud"    # Nofud : 10 N vs 6 H + 3 h

# ★ The control is a FIXTURE, and these are the REAL counts, frozen from the
# live corpus at 2026-09-16 17:17 — the moment BEFORE
# `thorlaks_hn_apply_default.py` resolved the CONFIDENT bucket. ⛔ They are not
# invented numbers and ⛔ they must never be tuned; they are the same two
# witnesses the cut was always pinned to. See «Why the control had to be
# frozen» in the docstring.
#                tail,               N, H,  h,  want
FIXTURE = [(CONTROL_CONFIDENT, 1, 0, 80, "CONFIDENT"),
           (CONTROL_AMBIGUOUS, 10, 6, 3, "AMBIGUOUS")]


def classify(n_cap, h_cap, h_low):
    """-> ('CONFIDENT'|'AMBIGUOUS', support, ratio). Never raises on A == 0."""
    support = h_cap + h_low
    if n_cap <= 0:
        return "AMBIGUOUS", support, -1.0   # cannot happen from case_pairs
    ratio = float(support) / float(n_cap)
    if os.environ.get("HEXAPLA_NO_HNPART"):
        return "CONFIDENT", support, ratio  # known-bad: everything confident
    if ratio >= MIN_RATIO and support >= MIN_SUPPORT:
        return "CONFIDENT", support, ratio
    return "AMBIGUOUS", support, ratio


def build():
    """-> (rows, counts) or (None, None) if the witness list refused."""
    paths = cp.part_files()
    if not paths:
        sys.stderr.write("NOTHING TO EXAMINE - that is not a pass.\n")
        return None, None
    counts, lines = cp.tally(paths)
    if counts is None:
        return None, None
    cands = cp.candidates(counts)
    tails = set(t for t, _, _, _, _ in cands)
    if cp.MUST_LIST not in tails or cp.MUST_NOT_LIST in tails:
        sys.stderr.write("UPSTREAM WITNESS CONTROL DID NOT FIRE - no partition.\n")
        return None, None
    rows = []
    for tail, n_cap, h_cap, h_low, _ in cands:
        bucket, support, ratio = classify(n_cap, h_cap, h_low)
        rows.append((bucket, tail, n_cap, h_cap, h_low, support, ratio))
    rows.sort(key=lambda r: (r[0] != "CONFIDENT", -r[2], r[1]))
    return rows, (counts, lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sites", action="store_true",
                    help="one line per SITE (file:line), not per word form")
    a = ap.parse_args()

    rows, extra = build()
    if rows is None:
        return 3

    if a.selftest:
        ok = True

        # -- the control proper: classify() itself, on the frozen real counts.
        print("  -- fixture half (the two real witnesses, frozen 2026-09-16) --")
        for tail, n_cap, h_cap, h_low, want in FIXTURE:
            bucket, support, ratio = classify(n_cap, h_cap, h_low)
            print("  %s control : N%-8s N=%d H=%d h=%d  S=%d  R=%.2f  -> %-9s "
                  "(want %s)"
                  % ("+" if want == "CONFIDENT" else "-", tail, n_cap, h_cap,
                     h_low, support, ratio, bucket, want))
            if bucket != want:
                ok = False

        # -- the live half. ⚠ It is a REPORT, not a pass condition: once the
        # CONFIDENT bucket has been applied, it is EMPTY BY CONSTRUCTION and a
        # live positive control is no longer obtainable. A live row that
        # DISAGREES with the fixture is still a failure.
        got = dict((r[1], r[0]) for r in rows)
        print("  -- live half (a report; the corpus may legitimately hold 0 "
              "CONFIDENT rows) --")
        for tail, _n, _h, _l, want in FIXTURE:
            live = got.get(tail)
            print("     N%-8s live -> %s" % (tail, live or "not a candidate"))
            if live is not None and live != want:
                print("     ⛔ LIVE DISAGREES WITH THE FIXTURE - that is a "
                      "FINDING about the corpus, not a licence to move the cut.")
                ok = False

        if ok:
            print("SELFTEST PASSED - fires both ways, so the cut cannot be "
                  "tuned away without breaking it.")
            return 0
        print("SELFTEST FAILED - the cut is inert; the partition proves nothing.")
        return 3

    counts, lines = extra
    conf = [r for r in rows if r[0] == "CONFIDENT"]
    amb = [r for r in rows if r[0] == "AMBIGUOUS"]

    if a.sites:
        for bucket, tail, n_cap, h_cap, h_low, support, ratio in rows:
            for p, lineno, w, snippet in lines.get(tail, []):
                print("%-9s %-14s %s:%d  R=%.2f S=%d\n    %s"
                      % (bucket, w, p, lineno, ratio, support, snippet))
        print()
    else:
        for label, group in (("CONFIDENT", conf), ("AMBIGUOUS", amb)):
            print("== %s: %d word form(s), %d site(s) =="
                  % (label, len(group), sum(r[2] for r in group)))
            print("%-16s %7s %7s %7s %7s %8s"
                  % ("word (tail)", "N-cap", "H-cap", "h-low", "S", "R"))
            print("-" * 58)
            for bucket, tail, n_cap, h_cap, h_low, support, ratio in group:
                print("%-16s %7d %7d %7d %7d %8.2f"
                      % ("N" + tail, n_cap, h_cap, h_low, support, ratio))
            print()

    total_sites = sum(r[2] for r in rows)
    print("%d site(s) across %d word form(s): %d CONFIDENT, %d AMBIGUOUS."
          % (total_sites, len(rows), sum(r[2] for r in conf),
             sum(r[2] for r in amb)))
    print("Cut: R >= %.0f and S >= %d, over the case_pairs columns only."
          % (MIN_RATIO, MIN_SUPPORT))
    lex = sum(r[2] for r in rows if r[4] >= MIN_SUPPORT)
    print("⚠ A LOOSER, PURELY LEXICAL cut - 'the word is attested lowercase-h "
          "at least %d times' (h-low >= %d; lowercase n is unattested for every "
          "row by construction) - would cover %d of the %d sites instead of %d."
          % (MIN_SUPPORT, MIN_SUPPORT, lex, total_sites,
             sum(r[2] for r in conf)))
    print("  The two cuts answer DIFFERENT questions: the lexical one asks "
          "whether the WORD is an h-word; the cut above also asks whether the "
          "readers agreed on the CAPITAL, which is the sort actually confused.")
    print("✅ RULED BY THE OWNER 2026-09-16: the default letter is H, and it")
    print("   covers the STRICT cut ONLY - the CONFIDENT rows above. He was shown")
    print("   both cuts and declined the lexical one, because it asks only whether")
    print("   the WORD is an h-word and never whether the readers agreed on the")
    print("   CAPITAL, which is the sort actually confused.")
    print("   ⛔ The AMBIGUOUS rows STAY BRACKETED and are adjudicated one at a time.")
    print("PARTITION ONLY - it still writes nothing and patches nothing. No tool")
    print("applies the default yet; a patcher must be --dry-run BY DEFAULT, show")
    print("~3 items first, and it touches already-merged records.")
    print("⛔ The READING rule is unchanged: a reader brackets [HN] whenever the")
    print("tail is not legible. A retroactive default is not a licence to resolve")
    print("a site at the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
