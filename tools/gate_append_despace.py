# -*- coding: utf-8 -*-
"""Clear the two FALSE-POSITIVE classes of the gate's `append:` detector by the
PRINTED-WORD route, for any book. 0 model tokens, 0 ears.

    python tools/gate_append_despace.py --lang en --books 11
    python tools/gate_append_despace.py --selftest

## The clearing rule

An append is cleared by an EAR, **or** by the flagged token being PART OF THE
PRINTED WORD. This script tests only the second route, so its verdict is
reproducible and needs no human judgement:

  CLASS A (compound split): the ASR split a printed compound ("armourbearer"
    -> "armour bearer", "Ramothgilead" -> "ramoth galad"). Test: strip ALL
    spaces and non-letters from both the ASR tail and the printed verse; if the
    print then ENDS WITH the ASR tail, no audio was added -- the detector
    merely tokenised a printed word into two.

  CLASS B (spurious apostrophe): the flagged token is "'", one character, and
    the de-spaced tails already agree. Same test, same conclusion.

⛔ A flag that does NOT de-space-match is NOT cleared here. It still needs an
ear. This tool NARROWS a queue; it never clears a verse on its own.

⚠ A near-miss is a finding, not a pass: "armorbearer" vs the print's
"armourbearer" does NOT clear, and must not be made to by loosening the match.
⛔ Do not add fuzzy matching, a Levenshtein threshold, or a spelling-variant
table -- the whole value of this test is that it cannot be tuned after seeing
the cases.

## Provenance

Generalised 2026-09-14 from `_work/gate_append_despace_check.py`, which carried
its flags and tails HARDCODED from the 2026-09-13 books 8-10 run and silently
ignored `--books`. This version reads the same `.qa.json` files the gate reads,
via the gate's own extraction logic, so the two instruments cannot drift apart.

`--selftest` replays those 11 legacy flags and asserts the exact split measured
on 2026-09-13: 4 CLEARED, 7 NOT. It is a control in BOTH directions -- it
contains compound-splits that MUST clear and real mismatches that MUST NOT.
⛔ A selftest that only ever passes proves nothing; if you change the matching
rule, this is what must fail.

Exit 0 = every flag tested cleared (or selftest reproduced).
Exit 1 = at least one flag not cleared (or selftest disagreed).
Exit 2 = a verse could not be read. ⛔ A failed read must never look like a pass.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = r"C:/Projects/Hexapla-releases"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_gate_appends as gate          # ONE definition of "the print"


# ---- the 2026-09-13 books 8-10 run, verbatim: the selftest's fixture ---------
LEGACY_FLAGS = [
    (8, 0, 8, "'", "not i better to thee than ten sons"),
    (8, 6, 6, "pee", "judged the children of israel in mice pee"),
    (8, 6, 6, "p", "judged the children of israel in mice p"),
    (8, 15, 21, "bearer", "him greatly and he became his armor bearer"),
    (8, 22, 1, "floors", "against keela and they rob the threshing floors"),
    (8, 24, 25, "'", "men of my lord whom thou didst send"),
    (9, 1, 20, "'", "as a whole and he answered i am"),
    (9, 2, 23, "'", "him away and he is gone in peace"),
    (9, 6, 10, "time", "wickedness afflict them any more as before time"),
    (9, 23, 18, "site", "the threshing floor of arana the jebi site"),
    (10, 21, 9, "'", "said haysin hither micaiah the son of imla"),
]
# measured 2026-09-13 -- the ONLY four that cleared by the printed-word route
LEGACY_CLEARED = {
    (8, 0, 8, "'"),
    (8, 24, 25, "'"),
    (9, 2, 23, "'"),
    (9, 6, 10, "time"),
}


def parse_books(spec):
    return gate.parse_books(spec)


def strip_notes(t):
    """BibleRepo.parseAsset rule: {x:y} is a note -> drop; {x} is supplied -> keep."""
    t = re.sub(r"\{[^{}]*:[^{}]*\}", " ", t)
    return t.replace("{", " ").replace("}", " ")


def despace(t):
    return re.sub(r"[^a-z]", "", t.lower())


def collect(lang, books):
    """Every append flag, as (book, chapter, verse, token, tail).

    Mirrors qa_gate_appends.main()'s walk exactly, including its (verse, token)
    dedup. Returns (flags, missing_books).
    """
    root = os.path.join(DATA, "narration", lang)
    flags = []
    missing = []
    for b in books:
        d = os.path.join(root, str(b))
        if not os.path.isdir(d):
            missing.append(b)
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.qa.json")),
                        key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0)):
            ch = os.path.basename(f).split(".")[0]
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except Exception as e:
                print("  ⚠ UNREADABLE %s: %s" % (f, e))
                continue
            seen = set()
            for v, info in (doc.get("gate") or {}).items():
                for att in info.get("attempts", []):
                    for r in att.get("reasons", []):
                        if not r.startswith("append:"):
                            continue
                        tok = r.split(":", 1)[1]
                        key = (v, tok)
                        if key in seen:
                            continue
                        seen.add(key)
                        flags.append((b, int(ch), int(v), tok,
                                      att.get("tail", "")))
    return flags, missing


def verdict(book, chapter, verse, tok, tail):
    """(cleared, asr_despaced, print_despaced) or raises on an unreadable verse."""
    printed = gate.kjv_text(book, chapter, verse)
    if not printed or not str(printed).strip():
        raise IOError("printed text UNAVAILABLE for %d/%d v%d"
                      % (book, chapter, verse))
    a = despace(tail)
    p = despace(strip_notes(printed))
    return p.endswith(a) and bool(a), a, p


def report(flags, label):
    """Print each verdict. Returns (n_cleared, failures) or exits 2 on a bad read."""
    print("%-14s %-12s %s" % ("ref", "token", "verdict"))
    print("-" * 78)
    failures = []
    cleared = []
    for (b, c, v, tok, tail) in flags:
        ref = "%d/%d v%d" % (b, c, v)
        try:
            ok, a, p = verdict(b, c, v, tok, tail)
        except Exception as e:
            print("READ FAILED for %s: %s" % (ref, e))
            sys.exit(2)
        if ok:
            cls = "B spurious-apostrophe" if tok == "'" else "A compound-split"
            print("%-14s %-12s CLEARED (%s)" % (ref, tok[:12], cls))
            cleared.append((b, c, v, tok))
        else:
            print("%-14s %-12s NOT CLEARED - needs an EAR" % (ref, tok[:12]))
            print("      asr  : ...%s" % a[-60:])
            print("      print: ...%s" % p[-60:])
            failures.append((ref, tok))
    print("-" * 78)
    return cleared, failures


def selftest():
    print("SELFTEST: replaying the 2026-09-13 books 8-10 flags.")
    print("Expected: 4 CLEARED, 7 NOT CLEARED. Both directions are asserted.\n")
    cleared, failures = report(LEGACY_FLAGS, "selftest")
    got = set(cleared)
    if got != LEGACY_CLEARED:
        print("⛔ SELFTEST FAILED - the clearing rule has CHANGED.")
        for k in sorted(LEGACY_CLEARED - got):
            print("   no longer clears (was CLEARED): %s" % (k,))
        for k in sorted(got - LEGACY_CLEARED):
            print("   now clears (was NOT cleared):   %s" % (k,))
        return 1
    print("✅ SELFTEST PASSED: %d cleared / %d not, exactly as measured "
          "2026-09-13." % (len(cleared), len(failures)))
    print("   It contains compound-splits that MUST clear and real mismatches "
          "that MUST NOT, so it can fail in both directions.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--books", help="e.g. 11 or 8-10 or 1,4,6")
    ap.add_argument("--selftest", action="store_true",
                    help="replay the 2026-09-13 fixture and assert its split")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.lang or not a.books:
        ap.error("--lang and --books are required (or use --selftest)")

    books = parse_books(a.books)
    flags, missing = collect(a.lang, books)
    if missing:
        print("⚠ NOT RENDERED (no directory), so NOT screened: books %s"
              % ", ".join(str(m) for m in missing))
    if not flags:
        print("0 append flag(s) in books %s." % a.books)
        print("⛔ A zero here is only as wide as --books, and says NOTHING "
              "about the ASR side -- the two instruments are DISJOINT.")
        return 0

    cleared, failures = report(flags, a.books)
    if failures:
        print("%d of %d flag(s) NOT cleared; each needs an ear:"
              % (len(failures), len(flags)))
        for ref, tok in failures:
            print("   %s  %s" % (ref, tok))
        print("⛔ NOT CLEARED means UNJUDGED, not defective. Only an ear "
              "decides, and the printed text is withheld from the ear kit.")
        return 1
    print("all %d flag(s) CLEARED as detector artifacts by the PRINTED-WORD "
          "route" % len(flags))
    print("⛔ This is not an ear, and it says nothing about the ASR side.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
