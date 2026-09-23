# -*- coding: utf-8 -*-
"""Count a spelling's precedent in the Karl XII corpus -- SCRIPTURE LINES ONLY.

## WHY THIS EXISTS (2026-08-25)

The campaign's standard corroboration move is a free grep over
`research/karlxii_*.md`:

    "wärd 74 / wård 8 -- both attested, so this site was worth measuring"

Done with a plain `str.count()` over the whole file, **that grep also counts
the transcriber's own notes**, and those files are now more note prose than
scripture (5,188 note lines against 3,380 scripture lines). Every ⚠ entry that
quotes a rival spelling adds a hit for that rival. The corroboration therefore
reads its own commentary back as evidence.

Measured on 2026-08-25, the damage was not marginal:

    form        whole-file      SCRIPTURE ONLY
    häller           9                0      <- cited as "attested 6 times"
    wård             9                0      <- cited as "attested 8 times"
    owånner          5                0      <- cited as "attested 4 times"
    mänga            2                0
    åhra            12               10      <- cited as 3; the REAL figure is higher

⚠⚠ **NO VERSE TEXT WAS EVER WRONG BECAUSE OF THIS.** Every ae/ring decision in
this campaign is made on a measured contact sheet against controls; the corpus
is corroboration only, and §4b already says precedent CORROBORATES and never
overrides the image. What the flaw corrupted was the CONFIDENCE STATEMENTS
written beside those decisions -- which is still a defect worth killing, because
a future session reads those statements as evidence.

▶ Use this tool for every precedent claim from now on. Never `grep` the raw file.

## USAGE

    python tools/kxii_precedent.py haller haller haller      # any number of forms
    python tools/kxii_precedent.py "w[a]rd" --regex
    python tools/kxii_precedent.py sang saeng --pairs        # print as rival pairs

## WHAT COUNTS AS SCRIPTURE

A line matching `^[0-9]+ ` (a verse) or starting `Argument:`. That is exactly
what `karlxii_apoc_corpus_audit.py` and the standing `grep -c '^[0-9]\\+ '`
cross-check count, so the three agree by construction.

⚠ `\\b` word boundaries SILENTLY FAIL on a/o with diacritics in grep -- they are
not word characters. That is why this counts in Python and why --regex compiles
with re.UNICODE.

## HONESTY CONTRACT (CLAUDE.md)

If no corpus file is found, or a file cannot be read, this exits 2 and prints
why. It never reports a plausible-looking 0.
"""
import argparse
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RELEASES = os.path.join(os.path.dirname(REPO), "Hexapla-releases")
CORPUS = os.path.join(RELEASES, "research", "karlxii_*.md")

VERSE = re.compile(r"^[0-9]+ ")


def load():
    """(scripture_text, note_text, per-file line counts). Raises rather than
    returning an empty corpus that would read as 'no precedent'."""
    files = sorted(glob.glob(CORPUS))
    if not files:
        raise SystemExit("NO CORPUS FILES matched %s -- refusing to report counts"
                         % CORPUS)
    scripture, notes, stats = [], [], []
    for f in files:
        s = n = 0
        for line in io.open(f, encoding="utf-8"):
            if VERSE.match(line) or line.startswith("Argument:"):
                scripture.append(line)
                s += 1
            else:
                notes.append(line)
                n += 1
        stats.append((os.path.basename(f), s, n))
    if not scripture:
        raise SystemExit("CORPUS HELD NO SCRIPTURE LINES -- refusing to report counts")
    return "".join(scripture), "".join(notes), stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("forms", nargs="+", help="spellings to count")
    ap.add_argument("--regex", action="store_true",
                    help="treat each form as a regex instead of a literal")
    ap.add_argument("--pairs", action="store_true",
                    help="read the forms as rival pairs and judge each pair")
    ap.add_argument("--files", action="store_true", help="show per-file line counts")
    args = ap.parse_args()

    try:
        S, N, stats = load()
    except SystemExit:
        raise
    except Exception as e:
        print("CORPUS READ FAILED: %s: %s" % (type(e).__name__, e))
        return 2

    if args.files:
        for name, s, n in stats:
            print("  %-28s scripture %5d   notes %5d" % (name, s, n))
        print()

    def count(form, text):
        if args.regex:
            return len(re.findall(form, text, re.UNICODE))
        return text.count(form)

    print("%-18s %10s %8s" % ("form", "SCRIPTURE", "(notes)"))
    print("%-18s %10s %8s" % ("-" * 18, "-" * 10, "-" * 8))
    got = []
    for form in args.forms:
        s, n = count(form, S), count(form, N)
        got.append((form, s, n))
        flag = ""
        if s == 0 and n > 0:
            flag = "  <- ZERO in scripture; every hit is our own notes"
        print("%-18s %10d %8d%s" % (form, s, n, flag))

    if args.pairs and len(got) % 2 == 0:
        print()
        for i in range(0, len(got), 2):
            (a, sa, _), (b, sb, _) = got[i], got[i + 1]
            if sa and sb:
                verdict = ("BOTH ATTESTED -- a genuine contested lexeme; "
                           "measure it every time")
            elif sa or sb:
                only = a if sa else b
                verdict = ("only %r is attested -- the rival has NO scripture "
                           "precedent, so this is weak corroboration, not a rule"
                           % only)
            else:
                verdict = "NEITHER attested -- no precedent either way; flag it"
            print("  %s / %s : %d / %d -- %s" % (a, b, sa, sb, verdict))

    print("\ncounted over %d scripture lines (verse + Argument) from %d file(s); "
          "note prose excluded by construction."
          % (S.count("\n"), len(stats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
