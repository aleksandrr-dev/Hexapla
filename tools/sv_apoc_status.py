# -*- coding: utf-8 -*-
"""Derive the sv (Karl XII) APOCRYPHA narration state. 0 model tokens.

    python tools/sv_apoc_status.py

Answers, from live disk and the app asset -- never from a log or a handoff:

  * how many apocrypha chapters are RENDERABLE (a chapter with zero verses in
    sv_karlxii.json cannot be spoken and is not a gap);
  * how many are rendered, how many carry a word-alignment sidecar;
  * how many carry a gate record (.qa.json) and what it says;
  * whether the set is in audio_index_gen.json yet.

WHY THIS EXISTS. The render straddled the 2026-09-03 gate change, so the
apocrypha is TWO populations: chapters rendered under the validated gate (which
wrote .qa.json) and chapters rendered on the old token_repetition retry (which
only wrote flags into a tee'd log). Those logs are TRUNCATED -- they carry
hundreds of "tail cut" markers -- so any count taken from them is a FLOOR, not
a measurement. This reads the artifacts instead.

⛔ A count that CANNOT be taken raises. It never returns 0 or a plausible
number: a failed read must not be indistinguishable from a clean corpus.

## --selftest, and its known-bad control

    python tools/sv_apoc_status.py --selftest

It asserts the defect this tool was actually bitten by: live_chapters() must
return the LIVE CHAPTER NUMBERS, not a count. Additions to Esther's live
chapters are 9,10,12,13,14,15 -- assuming range(n) there looked for
0.qa.json..5.qa.json and reported SIX FALSE ABSENT.

⛔ A control that passes on broken code is not a control. `HEXAPLA_LIVE_BY_COUNT=1`
reinstates that exact bug (indices become range(n)). Both directions must hold:

    python tools/sv_apoc_status.py --selftest                        # exit 0
    HEXAPLA_LIVE_BY_COUNT=1 python tools/sv_apoc_status.py --selftest # exit 1
"""
import glob
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = "C:/Projects/Hexapla/app/src/main/assets/bibles/sv_karlxii.json"
INDEX = "C:/Projects/Hexapla/app/src/main/assets/audio_index_gen.json"
NAR = "C:/Projects/Hexapla-releases/narration/sv"
FIRST_APOC = 66          # books 0-65 are the protestant canon
INDEX_KEY = "kxii"       # ⚠ the index/align key for Swedish is kxii, NOT sv


def live_chapters(chapters):
    """-> the LIVE CHAPTER NUMBERS in `chapters` (indices, not a count).

    A chapter with no verses, or whose every verse is empty or a placeholder,
    cannot be spoken and is NOT a gap.

    ⛔ Returns INDICES on purpose. Additions to Esther's live chapters are
    9,10,12,13,14,15; assuming range(n) here looked for 0.qa.json..5.qa.json
    and reported six false ABSENT.
    """
    live = [c for c, ch in enumerate(chapters)
            if ch and not all(str(v).strip() in ("", "…", "...") for v in ch)]
    if os.environ.get("HEXAPLA_LIVE_BY_COUNT") == "1":
        # ⛔ Known-bad control for --selftest ONLY: reinstates the range(n) bug.
        return list(range(len(live)))
    return live


def load_books(path=None):
    path = path or ASSET
    if not os.path.exists(path):
        raise SystemExit("FAIL: asset not found: %s" % path)
    d = json.load(open(path, encoding="utf-8"))
    books = d["books"] if isinstance(d, dict) and "books" in d else d
    if not isinstance(books, list) or not books:
        raise SystemExit("FAIL: could not read a book list out of the asset")
    return books


def main():
    books = load_books()
    if not os.path.isdir(NAR):
        raise SystemExit("FAIL: narration dir missing: %s" % NAR)

    rows = []
    renderable = rendered = sidecars = 0
    for i, b in enumerate(books):
        if i < FIRST_APOC:
            continue
        chapters = b.get("chapters", []) or []
        # a chapter with no verses cannot be spoken -- not a gap
        live = live_chapters(chapters)
        if not live:
            continue
        d = os.path.join(NAR, str(i))
        ogg = {int(os.path.basename(p)[:-4]) for p in glob.glob(d + "/*.ogg")}
        wj = {int(os.path.basename(p)[:-7]) for p in glob.glob(d + "/*.w.json")}
        renderable += len(live)
        rendered += len(ogg & set(live))
        sidecars += len(wj & set(live))
        # keep the LIVE CHAPTER NUMBERS, not just how many: Additions to
        # Esther's live chapters are 9,10,12,13,14,15 -- assuming range(n)
        # here looked for 0.qa.json..5.qa.json and reported six false ABSENT.
        rows.append((i, str(b.get("name"))[:24], live,
                     len(ogg & set(live)), len(wj & set(live))))

    if renderable == 0:
        raise SystemExit("FAIL: no renderable apocrypha chapters found -- "
                         "the asset shape changed; refusing to report 0")

    print("sv (kxii) APOCRYPHA — derived from live disk + the app asset")
    print("=" * 64)
    print("%-4s %-25s %8s %8s %9s" % ("idx", "book", "render", "ogg", "sidecar"))
    for i, name, live, o, w in rows:
        n = len(live)
        mark = "" if (o == n and w == n) else "   <--"
        print("%-4d %-25s %8d %8d %9d%s" % (i, name, n, o, w, mark))
    print("-" * 64)
    print("%-30s %8d %8d %9d" % ("TOTAL renderable", renderable, rendered, sidecars))
    print()
    print("rendered : %d / %d" % (rendered, renderable))
    print("sidecars : %d / %d" % (sidecars, renderable))

    # gate records
    have = miss = 0
    ver = Counter()
    failing = unjudged = redrawn = 0
    for i, _, live, _, _ in rows:
        for c in live:
            qa = os.path.join(NAR, str(i), "%d.qa.json" % c)
            if not os.path.exists(qa):
                miss += 1
                continue
            have += 1
            q = json.load(open(qa, encoding="utf-8"))
            ver[q.get("gate_version", "none")] += 1
            failing += len(q.get("failing") or {})
            unjudged += len(q.get("unjudged") or [])
            redrawn += len(q.get("redrawn") or [])
    print()
    print("gate records (.qa.json): %d present, %d ABSENT" % (have, miss))
    print("  gate_version spread  : %s" % dict(ver))
    print("  failing / unjudged / redrawn: %d / %d / %d" % (failing, unjudged, redrawn))
    if miss:
        print("  ⚠ the %d chapters with NO gate record predate the 2026-09-03 gate."
              % miss)
        print("    They were screened only by the OLD token_repetition retry, whose")
        print("    record is a TRUNCATED log. Screen them with qa_selfrepeat.")

    # index
    if os.path.exists(INDEX):
        idx = json.load(open(INDEX, encoding="utf-8"))
        k = idx.get(INDEX_KEY, {})
        bk = sorted(int(x) for x in k if str(x).isdigit())
        apoc = [b for b in bk if b >= FIRST_APOC]
        print()
        print("audio_index_gen['%s']: %d book(s), %d apocrypha book(s) indexed"
              % (INDEX_KEY, len(bk), len(apoc)))
        if not apoc:
            print("  ⛔ NO apocrypha in the index — the app cannot play any of it,")
            print("     however many .ogg sit on disk.")
    else:
        print("\n⚠ index not found: %s" % INDEX)

    print()
    print("⛔ Not a completeness claim on its own: sidecars present says nothing")
    print("   about DEFECTS. Repairing a verse changes its audio, so a repaired")
    print("   chapter needs its sidecar rebuilt (align_words --force).")


# ---------------------------------------------------------------- selftest ---

def selftest():
    import shutil
    import tempfile
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # -- THE ESTHER TRAP: live chapter NUMBERS, not a count ---------------
    # 16 chapters, live only at 9,10,12,13,14,15 (Additions to Esther's shape).
    esther = [[] for _ in range(16)]
    for c in (9, 10, 12, 13, 14, 15):
        esther[c] = ["a real verse of chapter %d" % c]
    got = live_chapters(esther)
    check(got == [9, 10, 12, 13, 14, 15],
          "live_chapters returns the live chapter NUMBERS 9,10,12,13,14,15 "
          "(got %r) - range(6) here reported six false ABSENT" % (got,))
    check(got != list(range(6)),
          "live_chapters is NOT range(n) - the historical bug")
    check(len(got) == 6, "live_chapters finds exactly the six live chapters")

    # -- placeholder and empty chapters are NOT gaps ----------------------
    check(live_chapters([[]]) == [],
          "an empty chapter is not renderable (not a gap)")
    check(live_chapters([[""]]) == [],
          "a chapter of empty-string verses is not renderable")
    check(live_chapters([["   "]]) == [],
          "a chapter of whitespace-only verses is not renderable")
    check(live_chapters([["…"]]) == [],
          "a chapter of '…' placeholders is not renderable")
    check(live_chapters([["..."]]) == [],
          "a chapter of '...' placeholders is not renderable")
    check(live_chapters([["…", "..."]]) == [],
          "both placeholder spellings together are not renderable")

    # -- the false-positive control: real text must COUNT -----------------
    check(live_chapters([["…", "but this verse is real"]]) == [0],
          "ONE real verse among placeholders IS renderable (false-positive "
          "control - the tool must still see real chapters)")
    check(live_chapters([["real"], ["…"], ["real"]]) == [0, 2],
          "a placeholder chapter between two live ones is skipped, and the "
          "indices stay TRUE (0 and 2, never 0 and 1)")

    # -- a count that cannot be taken RAISES, never returns 0 -------------
    tmp = tempfile.mkdtemp(prefix="svapoc_selftest_")
    try:
        missing = os.path.join(tmp, "nope.json")
        try:
            load_books(missing)
            check(False, "load_books on a missing asset must RAISE")
        except SystemExit:
            check(True, "load_books RAISES on a missing asset (never a "
                        "plausible empty list)")
        bad = os.path.join(tmp, "bad.json")
        with open(bad, "w", encoding="utf-8") as fh:
            json.dump({"not_books": 1}, fh)
        try:
            load_books(bad)
            check(False, "load_books on an unreadable shape must RAISE")
        except SystemExit:
            check(True, "load_books RAISES when it cannot find a book list")
        ok = os.path.join(tmp, "ok.json")
        with open(ok, "w", encoding="utf-8") as fh:
            json.dump([{"name": "X", "chapters": [["v"]]}], fh)
        check(len(load_books(ok)) == 1,
              "load_books reads a well-shaped asset (both list and {'books':})")
        wrapped = os.path.join(tmp, "wrapped.json")
        with open(wrapped, "w", encoding="utf-8") as fh:
            json.dump({"books": [{"name": "X", "chapters": [["v"]]}]}, fh)
        check(len(load_books(wrapped)) == 1,
              "load_books also reads the {'books': [...]} shape")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- the constants that silently mis-address the whole report ---------
    check(FIRST_APOC == 66,
          "FIRST_APOC is 66 (books 0-65 are the protestant canon)")
    check(INDEX_KEY == "kxii",
          "INDEX_KEY is 'kxii', NOT 'sv' - the index key for Swedish")

    bad_rows = [w for ok, w in results if not ok]
    print()
    print("%d assertion(s), %d failed" % (len(results), len(bad_rows)))
    if bad_rows:
        print("⛔ SELFTEST FAILED")
        return 1
    print("✅ selftest passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
