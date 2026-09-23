"""Census every shipped Bible asset for EMPTY verse slots.

A blank slot renders as an empty line in the reader and is invisible to
audit_asset_markup.py (there is no markup to match).  0 tokens, so it runs
over the FULL corpus, never a sample.

Some empties are legitimate: an asset whose versification splits a verse the
KJV keeps whole can carry a deliberate empty tail slot (see the de_luther
alignment entry in docs/ASSET_DEFECTS.md).  This tool reports; it does not
judge.  A count is not a verdict - read the addresses.

    python tools/audit_empty_verses.py            # every asset
    python tools/audit_empty_verses.py zh_cuv_s   # one asset
    python tools/audit_empty_verses.py --selftest # exercise the census itself

Exit 0 = no empties anywhere, 1 = empties found, 2 = an asset failed to read
(NEVER 0 on a failed read).

================================================================================
SELF-TEST  (--selftest)

  python tools/audit_empty_verses.py --selftest                            # exit 0
  HEXAPLA_NO_PLACEHOLDER=1 python tools/audit_empty_verses.py --selftest   # exit 1

Builds its own synthetic fixture in a temp dir - it never touches the real
corpus and never reads app/src/main/assets/bibles/.  One line per assertion:
`ok   - <what>` or `FAIL - <what>`; exit 0 iff every assertion passed.

HEXAPLA_NO_PLACEHOLDER=1 makes is_placeholder() always return False, which
disables exactly the detection this tool was found to be MISSING on
2026-09-20 (book 78 of en_kjv carries twelve `…` slots and was reported
clean).  The selftest MUST fail in that mode.  A test that passes in both
directions proves nothing; the failing direction is the only proof the
passing direction means anything.
================================================================================
"""
import glob
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ASSETS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "app", "src", "main", "assets", "bibles"))


# ⛔ A SLOT THAT IS NOT EMPTY BUT CARRIES NO SCRIPTURE.  `v.strip()` calls
# these clean, and that is the whole defect this tool was found to have
# (2026-09-20): book 78 of en_kjv carries twelve `…` slots and they were
# reported as a clean asset.  ru_synodal carries 357 slots that are a bare
# full stop.  A placeholder renders in the reader exactly like scripture and
# is INVISIBLE to an emptiness test - which is worse than an empty slot, not
# better.
# ⚠ The set is deliberately TINY and literal: ellipsis, runs of full stops,
# dashes, and the lone bullet.  It is NOT a heuristic about short verses - a
# real verse can be two words long ("Jesus wept.") and must never be flagged.
PLACEHOLDER = set(list(u"….-–—_*•") )


def is_placeholder(v):
    """True when every character of the slot is punctuation from PLACEHOLDER.

    ⛔ Never call an ordinary short verse a placeholder: a slot qualifies only
    if it carries NO letter and NO digit at all.

    HEXAPLA_NO_PLACEHOLDER=1 forces False unconditionally.  That is the
    known-bad control the selftest is built around - it removes exactly the
    detection the tool was found to lack, so any suite that still passes
    under it is not testing anything.  Read the flag at CALL time, not at
    import time, so the environment can be flipped inside one process.
    """
    if os.environ.get("HEXAPLA_NO_PLACEHOLDER") == "1":
        return False
    s = v.strip()
    return bool(s) and all(c in PLACEHOLDER or c.isspace() for c in s)


def census(path):
    """-> (total, [(address, kind)]).

    kind PLACE = the slot is not empty, but carries no scripture: `…`, `.`,
                 a dash.  See PLACEHOLDER above - this is the class the tool
                 used to report as clean.
    kind TAIL  = the empty slot is the LAST verse of its chapter.  That is the
                 signature of a versification merge: this edition folded the
                 verse into its predecessor and the KJV-shaped slot is left
                 over.  Benign, and the documented de_luther class.
    kind MID   = an empty slot with populated verses AFTER it in the same
                 chapter.  A merge cannot produce that.  Either the edition
                 genuinely lacks the verse (LXX-based texts lack many) or the
                 scrape dropped it.  ⚠ Only a REFERENCE TEXT can tell those
                 apart - this tool must not guess, and neither may you.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    total, empties = 0, []
    for b in data:
        for ci, ch in enumerate(b["chapters"]):
            for vi, v in enumerate(ch):
                total += 1
                addr = "%s %d:%d" % (b["name"], ci + 1, vi + 1)
                if not v.strip():
                    rest = [w for w in ch[vi + 1:] if w.strip()]
                    kind = "TAIL" if not rest else "MID "
                    empties.append((addr, kind))
                elif is_placeholder(v):
                    empties.append((addr + "  <%s>" % v.strip()[:8], "PLACE"))
    return total, empties


def _selftest_fixture():
    """One synthetic asset covering every class census() claims to see.

    chapter 1, by 1-based verse number:
      1  "In the beginning God created the heaven and the earth."  normal
      2  "Jesus wept."            ⛔ false-positive CONTROL: two words, real
                                  scripture, punctuation inside it.  Must never
                                  be flagged.
      3  "…"                      PLACE (bare ellipsis)
      4  "."                      PLACE (bare full stop)
      5  "—"                      PLACE (em dash)
      6  ""                       MID   (populated verse 7 follows it)
      7  "And God said, Let there be light."  normal, counted
    chapter 2:
      1  "Thus the heavens and the earth were finished."  normal
      2  ""                       TAIL  (last verse of the chapter - the
                                  versification-merge signature)
    """
    asset = [{
        "name": "Fixture",
        "chapters": [
            [
                "In the beginning God created the heaven and the earth.",
                "Jesus wept.",
                u"…",
                ".",
                u"—",
                "",
                "And God said, Let there be light.",
            ],
            [
                "Thus the heavens and the earth were finished.",
                "",
            ],
        ],
    }]
    # Counted by hand from the literal above - an independent number so a
    # census() that silently drops slots cannot agree with it by accident.
    return asset, 9


def _selftest():
    """Exercise census() against a self-built fixture.  -> 0 all ok, 1 any FAIL.

    Does NOT read app/src/main/assets/bibles/ and does not need the real
    corpus.  Prints `ok   - <what>` / `FAIL - <what>` per assertion.
    """
    failures = 0

    def check(what, cond):
        nonlocal failures
        if cond:
            print("ok   - %s" % what)
        else:
            failures += 1
            print("FAIL - %s" % what)

    asset, expect_total = _selftest_fixture()
    tmp = tempfile.mkdtemp(prefix="audit_empty_verses_selftest_")
    try:
        path = os.path.join(tmp, "fixture.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asset, fh, ensure_ascii=False)

        total, empties = census(path)
        by_addr = {addr: kind for addr, kind in empties}
        flagged = set(by_addr)

        # Addresses census() builds for the fixture.  Spelled out as literals
        # rather than recomputed by the same expression under test.
        A_NORM1 = "Fixture 1:1"
        A_WEPT = "Fixture 1:2"
        A_TAIL = "Fixture 2:2"
        A_MID = "Fixture 1:6"
        A_NORM7 = "Fixture 1:7"
        A_ELLIPSIS = u"Fixture 1:3  <…>"
        A_DOT = u"Fixture 1:4  <\u002e>"
        A_DASH = u"Fixture 1:5  <—>"

        # --- the total and the flagged-set size -----------------------------
        check("total verse count == 9 (every slot counted, incl. empty + tails)",
              total == expect_total)
        check("census flags exactly the 5 planted defects, no more",
              len(empties) == 5 and flagged == {
                  A_ELLIPSIS, A_DOT, A_DASH, A_MID, A_TAIL})

        # --- 1. the false-positive control, stated first ---------------------
        # If any assertion in this file is worth keeping, it is this one.
        check(u'"Jesus wept." is NOT flagged  (short real verse, control)',
              A_WEPT not in flagged)
        check(u'"Jesus wept." is not misclassified as PLACE',
              by_addr.get(A_WEPT) != "PLACE")

        # --- 2. empty last verse of its chapter -> TAIL ----------------------
        check("empty final slot of chapter 2 -> TAIL   (Fixture 2:2)",
              by_addr.get(A_TAIL) == "TAIL")

        # --- 3. empty slot with populated verses after it -> MID -------------
        check("empty slot with a populated verse after it -> MID   (Fixture 1:6)",
              by_addr.get(A_MID) == "MID ")

        # --- 4,5,6. bare punctuation-only slots -> PLACE ---------------------
        check(u"slot that is only U+2026 '…' -> PLACE   (Fixture 1:3)",
              by_addr.get(A_ELLIPSIS) == "PLACE")
        check(u"slot that is only '.' -> PLACE   (Fixture 1:4)",
              by_addr.get(A_DOT) == "PLACE")
        check(u"slot that is only U+2014 '—' -> PLACE   (Fixture 1:5)",
              by_addr.get(A_DASH) == "PLACE")
        check("the three bare-punctuation slots are the ONLY PLACE findings",
              sorted(a for a, k in empties if k == "PLACE") ==
              sorted([A_ELLIPSIS, A_DOT, A_DASH]))

        # --- 7. ordinary multi-word verses: unflagged, but still counted -----
        check(u'"In the beginning God created the heaven and the earth." is NOT flagged',
              A_NORM1 not in flagged)
        check(u'"And God said, Let there be light." is NOT flagged and IS counted',
              A_NORM7 not in flagged and total == expect_total)

        # --- the suite must key off PLACE, or it proves nothing -------------
        # Under HEXAPLA_NO_PLACEHOLDER=1 the three PLACE rows above go blind
        # and the run must FAIL.  This last assertion states that dependency
        # outright, so a future edit that quietly stops testing PLACE is
        # caught here rather than passing green forever.
        check("the suite depends on PLACE detection (known-bad control armed)",
              len([1 for _, k in empties if k == "PLACE"]) == 3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return 1 if failures else 0


def main(argv):
    if "--selftest" in argv[1:]:
        return _selftest()
    wanted = [a for a in argv[1:] if not a.startswith("-")]
    verbose = "--all" in argv[1:]
    grand_mid, grand_place = [], []
    paths = sorted(glob.glob(os.path.join(ASSETS, "*.json")))
    if wanted:
        paths = [p for p in paths
                 if os.path.basename(p)[:-5] in wanted or
                 os.path.basename(p) in wanted]
        if not paths:
            print("no asset matched %r" % (wanted,))
            return 2
    rc, dirty, grand = 0, 0, 0
    for p in paths:
        name = os.path.basename(p)
        try:
            total, empties = census(p)
        except Exception as exc:                      # a failed read is not a pass
            print("READ FAILED  %-22s %s" % (name, exc))
            rc = 2
            continue
        grand += total
        if empties:
            dirty += 1
            if rc == 0:
                rc = 1
            mid = [a for a, k in empties if k == "MID "]
            place = [a for a, k in empties if k == "PLACE"]
            print("%-22s %6d verses  %3d EMPTY  (%d mid-chapter, %d placeholder)"
                  % (name, total, len(empties) - len(place), len(mid), len(place)))
            # ⛔ Placeholders are listed WITHOUT --all. A slot that renders as
            # scripture and is not scripture is the finding this tool exists
            # to surface; hiding it behind a flag is how it went unseen.
            shown = empties if verbose else \
                [(a, "PLACE") for a in place] + [(a, "MID ") for a in mid]
            for a, k in shown[:25]:
                print("      %s %s" % (k, a))
            if len(shown) > 25:
                print("      ... +%d more" % (len(shown) - 25))
            grand_mid.append((name, len(mid), len(empties)))
            if place:
                grand_place.append((name, len(place)))
        else:
            print("%-22s %6d verses  clean" % (name, total))
    print("\n%d assets, %d verses, %d asset(s) with empty or placeholder slots"
          % (len(paths), grand, dirty))
    if grand_place:
        print("PLACEHOLDER slots (NOT empty, and NOT scripture - these render")
        print("in the reader as if they were text, so no emptiness test sees them):")
        for name, p in sorted(grand_place, key=lambda r: -r[1]):
            print("   %-22s %4d" % (name, p))
        print(u"⚠ Every one is a QUESTION for the owner, not a repair to make")
        print(u"  here: whether a slot should hold scripture, an empty line or")
        print(u"  its placeholder is a TEXT decision. ⛔ Do not edit an asset.")
    if grand_mid:
        print("MID-CHAPTER empties (a merge cannot make these):")
        for name, m, t in sorted(grand_mid, key=lambda r: -r[1]):
            print("   %-22s %3d of %3d" % (name, m, t))
        print("⚠ mid-chapter is a QUESTION, not a verdict - an LXX-based text")
        print("  legitimately lacks verses the KJV has. Needs a reference text.")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
