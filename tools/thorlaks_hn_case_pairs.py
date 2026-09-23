#!/usr/bin/env python
"""List capital-`N` sites whose OWN word is attested with lowercase `h` nearby.

    python tools/thorlaks_hn_case_pairs.py              # candidate sites
    python tools/thorlaks_hn_case_pairs.py --selftest
    python tools/thorlaks_hn_case_pairs.py --word uors  # one word, with lines

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## ⛔⛔ WHAT THIS IS NOT

**IT RULES ON NOTHING, IT CORRECTS NOTHING, AND IT MUST NEVER LEARN TO.**
H/N resolution is `NOT BY REGEX, NOT BY DICTIONARY` — closed in
`research/THORLAKS_CONVENTIONS.md` and in
`research/_evidence/thorlaks_hn_second_adjudication_2026-09-13.md`. This script
emits a **WITNESS LIST for the owner**, nothing else. ⛔ Do not pipe it into a
patcher. ⛔ Do not treat a candidate as a correction.

## Why the evidence here is NOT the closed dictionary argument

The closed argument is «`Nuors` is not an Icelandic word, therefore it is
`Huors`». That reasons from a LEXICON to a letter, and the project forbids it.

This script reasons from **the corpus's own readers**. Measured 2026-09-14,
`research/_parts/mark_p32-40.md`:

    v22  ...Bid af mier huors þu villt...        <- lowercase h, committed
    v23  ...ad huors þu beidest af mier...       <- lowercase h, committed
    v24  ...til Modur sinnar/Nuors skal eg...    <- CAPITAL, read N

★★ **Same word, same reader, same page, three verses apart — and the `N`
appears ONLY where the letter is CAPITAL.** Lowercase `h` and `n` are not a
confusable pair in this hand; the capital sorts are. So a word attested
lowercase-`h` and capital-`N` in the same corpus is a site where the reader
behaved differently *as a function of case*, which is the signature of the H/N
confusion and is a fact about the READING, not about the dictionary.

⚠ It is still only a WITNESS. It says a site deserves the owner's eye. It does
not say which way he will rule, and ⛔ a site NOT listed here is not thereby
cleared — a word with no lowercase twin in the corpus simply has no witness.

## The owner's discriminator (2026-09-14, `_work/hn_p37_controlled_2026-09-13.png`)

▶ **N's tail goes DOWN; H's tail goes UP.** His verdict on the five panels:
`Nafn` = N (tail down), `Herodes` = H (tail up, smudged), and all three probes
(`Nuors`, `Hun`, `Høfud`) = **H**. ▶ Full record:
`research/_evidence/thorlaks_hn_owner_verdict_2026-09-14.md`.

## The control, and it must fire BOTH ways

- ▶ `Nuors` MUST be listed  — lowercase `huors` is attested (a real candidate).
- ▶ `Nafn`  MUST NOT be listed — 29:0 N across the corpus, lowercase twin
  `hafn` unattested. ★ A run that flags `Nafn` is INERT and proves nothing;
  it would be flagging the whole alphabet.

Exit 0 = the control fired both ways and the list printed.
Exit 3 = the control did NOT fire both ways (⛔ never a usable list).
"""
import argparse
import glob
import io
import os
import re
import sys
from collections import Counter, defaultdict

WORD = re.compile(r"[A-Za-zÀ-ÿæøþðöũñ]+", re.UNICODE)

# The control. ⛔ Do not widen these to make a run pass.
MUST_LIST = "uors"    # capital Nuors, lowercase huors attested
MUST_NOT_LIST = "afn"  # capital Nafn, 29:0 N, no lowercase hafn


def part_files():
    out = []
    for p in glob.glob("research/_parts/*.md"):
        base = os.path.basename(p)
        if ".bak" in base or base.isupper():
            continue
        out.append(p)
    return sorted(out)


def tally(paths):
    """-> (counts, lines) keyed by the word's case-folded TAIL after H/N."""
    counts = defaultdict(Counter)
    lines = defaultdict(list)
    for p in paths:
        try:
            with io.open(p, encoding="utf-8") as fh:
                text = fh.read()
        except Exception as exc:                              # noqa: BLE001
            sys.stderr.write("FAILED to read %s: %s\n" % (p, exc))
            return None, None
        for lineno, line in enumerate(text.splitlines(), 1):
            for w in WORD.findall(line):
                if len(w) < 2 or w[0] not in "HNhn":
                    continue
                tail = w[1:]
                key = tail
                counts[key][w[0]] += 1
                if w[0] == "N":
                    lines[key].append((p, lineno, w, line.strip()[:110]))
    return counts, lines


def candidates(counts):
    """Capital-N words whose own tail is attested with LOWERCASE h."""
    out = []
    for tail, c in counts.items():
        n_cap, h_cap = c.get("N", 0), c.get("H", 0)
        h_low, n_low = c.get("h", 0), c.get("n", 0)
        if n_cap and h_low and not n_low:
            out.append((tail, n_cap, h_cap, h_low, n_low))
    out.sort(key=lambda r: (-r[1], r[0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--word", help="show the lines for one tail, e.g. uors")
    a = ap.parse_args()

    paths = part_files()
    if not paths:
        sys.stderr.write("NOTHING TO EXAMINE - that is not a pass.\n")
        return 3
    counts, lines = tally(paths)
    if counts is None:
        return 3
    cands = candidates(counts)
    tails = set(t for t, _, _, _, _ in cands)

    fired_pos = MUST_LIST in tails
    fired_neg = MUST_NOT_LIST not in tails
    if a.selftest:
        print("  control + : capital N'%s' listed          = %s (want True)"
              % (MUST_LIST, fired_pos))
        print("  control - : capital N'%s' NOT listed       = %s (want True)"
              % (MUST_NOT_LIST, fired_neg))
        c = counts.get(MUST_NOT_LIST, Counter())
        print("              N%s=%d  h%s=%d  n%s=%d"
              % (MUST_NOT_LIST, c.get("N", 0), MUST_NOT_LIST, c.get("h", 0),
                 MUST_NOT_LIST, c.get("n", 0)))
        if fired_pos and fired_neg:
            print("SELFTEST PASSED - fires both ways, so it cannot be tuned away.")
            return 0
        print("SELFTEST FAILED - the control is inert; the list proves nothing.")
        return 3

    if a.word:
        for p, lineno, w, snippet in lines.get(a.word, []):
            print("%s:%d  %s\n    %s" % (p, lineno, w, snippet))
        low = counts.get(a.word, Counter())
        print("\ncorpus: N%s=%d  H%s=%d  h%s=%d  n%s=%d"
              % (a.word, low.get("N", 0), a.word, low.get("H", 0),
                 a.word, low.get("h", 0), a.word, low.get("n", 0)))
        return 0

    if not (fired_pos and fired_neg):
        sys.stderr.write("CONTROL DID NOT FIRE BOTH WAYS "
                         "(+%s=%s  -%s=%s) - not a usable list.\n"
                         % (MUST_LIST, fired_pos, MUST_NOT_LIST, fired_neg))
        return 3

    total_n = sum(c.get("N", 0) for c in counts.values())
    listed = sum(r[1] for r in cands)
    print("%-16s %7s %7s %7s   %s"
          % ("word (tail)", "N-cap", "H-cap", "h-low", "witness"))
    print("-" * 74)
    for tail, n_cap, h_cap, h_low, _ in cands:
        print("%-16s %7d %7d %7d   N%s vs h%s in the same corpus"
              % ("N" + tail, n_cap, h_cap, h_low, tail, tail))
    print()
    print("%d capital-N site(s) across %d word form(s) have a lowercase-h twin."
          % (listed, len(cands)))
    print("Corpus capital-N sites in merged parts: %d." % total_n)
    print("WITNESS LIST ONLY - it rules on nothing and corrects nothing.")
    print("Every row needs the owner's eye at the pixel, or it stays as read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
