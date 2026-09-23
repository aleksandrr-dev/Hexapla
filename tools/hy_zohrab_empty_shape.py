# -*- coding: utf-8 -*-
"""The SHAPE of hy_zohrab's 135 empty verses — grouped, before any master is sought.

    PYTHONIOENCODING=utf-8 python tools/hy_zohrab_empty_shape.py
    python tools/hy_zohrab_empty_shape.py --selftest

⛔ WRITES NOTHING AND CORRECTS NOTHING. It answers one question: are the empties
scattered, or are they CONTIGUOUS RUNS inside name-list chapters? A contiguous
run inside Nehemiah 11-12 is consistent with the LXX-based long-name-run
hypothesis AND with a scrape that dropped them; ⛔ this tool cannot separate
those two and does not try. ⛔ Only an upstream master separates them
(docs/ASSET_DEFECTS.md, owner 2026-09-15).

⚠ A count/status failure raises or returns -1; it never returns a plausible 0.
For THIS asset an empty result means the loader did not understand the asset
shape — a FAILED READ, not a clean result — so main() returns 1, never 0.

## --selftest, and its known-bad control

`--selftest` builds its own fixtures in a temp dir; it never reads the real
asset. It asserts run lengths and boundaries in runs(), the 1-based addressing
and both verse shapes in empties(), the false-positive control (a populated
verse is never flagged), and the failure path above.

⛔ A control that passes on broken code is not a control. `HEXAPLA_SOFT_FAIL=1`
makes the failure path return 0 instead of 1 — the exact defect this project
has been bitten by, a status function that fails but returns a plausible
number. Both directions must hold, or the test means nothing:

    python tools/hy_zohrab_empty_shape.py --selftest                     # exit 0
    HEXAPLA_SOFT_FAIL=1 python tools/hy_zohrab_empty_shape.py --selftest # exit 1
"""
import collections
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "app", "src", "main", "assets", "bibles",
                     "hy_zohrab.json")


def load(path=None):
    with open(path or ASSET, encoding="utf-8") as fh:
        return json.load(fh)


def empties(data):
    """-> [(book, chapter, verse)] for every empty/whitespace verse.

    ⚠ Raises ValueError on a shape this loader cannot read, rather than
    silently returning [] — see the failure contract below: for THIS asset an
    empty result means a FAILED READ, so a malformed shape must not be able to
    masquerade as one.
    """
    out = []
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    if not isinstance(books, list):
        raise ValueError("books is %s, not a list" % type(books).__name__)
    for b in books:
        if not isinstance(b, dict):
            raise ValueError("book entry is %s, not an object" % type(b).__name__)
        name = b.get("name") or b.get("n") or "?"
        chapters = b.get("chapters") or b.get("c") or []
        if not isinstance(chapters, list):
            raise ValueError("%s: chapters is %s, not a list"
                             % (name, type(chapters).__name__))
        for ci, ch in enumerate(chapters, 1):
            if isinstance(ch, list):
                verses = ch
            elif isinstance(ch, dict):
                verses = ch.get("verses") or []
            else:
                raise ValueError("%s %d: chapter is %s, not a list or object"
                                 % (name, ci, type(ch).__name__))
            if not isinstance(verses, list):
                raise ValueError("%s %d: verses is %s, not a list"
                                 % (name, ci, type(verses).__name__))
            for vi, v in enumerate(verses, 1):
                if isinstance(v, str):
                    text = v
                elif isinstance(v, dict):
                    text = v.get("t") or v.get("text") or ""
                else:
                    raise ValueError("%s %d:%d: verse is %s, not a string or "
                                     "object" % (name, ci, vi, type(v).__name__))
                if not text or not text.strip():
                    out.append((name, ci, vi))
    return out


def runs(nums):
    """Contiguous runs in a sorted list of ints -> [(start, end)]."""
    out = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [(a, b) for a, b in out]


def _fail(msg):
    """The ONE failure path: say so on stderr, never return a plausible 0.

    ⚠ A failed read must never be indistinguishable from a clean result.
    HEXAPLA_SOFT_FAIL is the known-bad control for exactly this line; it exists
    so --selftest can prove the hard failure is real.
    """
    sys.stderr.write(msg)
    return 0 if (os.environ.get("HEXAPLA_SOFT_FAIL") == "1" and _IN_SELFTEST) else 1


#: Set by selftest() while it drives a fixture; ⛔ never true in a normal run.
_IN_SELFTEST = False


def main(path=None):
    data = load(path)
    try:
        emp = empties(data)
    except ValueError as exc:
        # A shape the loader cannot read. ⛔ NOT an empty asset and NOT a pass.
        return _fail("CANNOT READ THE ASSET SHAPE (%s) — that is a FAILURE, "
                     "not a clean result.\n" % exc)
    if not emp:
        return _fail("NO EMPTIES FOUND — the loader did not understand the "
                     "asset shape. That is a FAILURE, not a clean result.\n")
    print("hy_zohrab: %d empty verse(s)" % len(emp))
    print()
    by_ch = collections.OrderedDict()
    for name, c, v in emp:
        by_ch.setdefault((name, c), []).append(v)
    print("%-28s %5s %6s  %s" % ("book", "chap", "empty", "runs (verse numbers)"))
    for (name, c), vs in by_ch.items():
        rr = runs(vs)
        txt = ", ".join("%d" % a if a == b else "%d-%d" % (a, b) for a, b in rr)
        print("%-28s %5d %6d  %s" % (name, c, len(vs), txt))
    print()
    by_book = collections.Counter(name for name, _, _ in emp)
    print("by book:")
    for name, n in by_book.most_common():
        print("   %-28s %4d" % (name, n))
    print()
    longest = max((len(vs) for vs in by_ch.values()))
    multi = sum(1 for vs in by_ch.values() if len(runs(vs)) == 1 and len(vs) > 1)
    print("%d chapter(s) affected; longest single chapter has %d empties; "
          "%d chapter(s) are ONE contiguous run of >1." % (len(by_ch), longest, multi))
    print("⛔ A contiguous run is consistent with BOTH an LXX name-list gap and a "
          "dropped scrape. This tool does not separate them; only an upstream "
          "master does.")
    return 0


# ---------------------------------------------------------------- selftest ---

def _write(tmp, name, obj):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)
    return p


def _quiet_main(path):
    """main() with its report and its stderr captured -> (rc, out, err)."""
    so, se = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        rc = main(path)
    return rc, so.getvalue(), se.getvalue()


def selftest():
    global _IN_SELFTEST
    _IN_SELFTEST = True          # arm the known-bad control for this process
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # -- runs(): lengths and BOUNDARIES ------------------------------------
    check(runs([5]) == [(5, 5)], "runs: a singleton is a run of length 1")
    check(runs([1, 2, 3]) == [(1, 3)],
          "runs: a run starting at verse 1 (lower boundary)")
    check(runs([7, 8, 9]) == [(7, 9)], "runs: one interior run")
    check(runs([1, 2, 5, 6, 7, 20]) == [(1, 2), (5, 7), (20, 20)],
          "runs: several runs in order, trailing singleton at the last verse")
    check(runs([3, 1, 2]) == [(1, 3)], "runs: input order does not matter")
    check(runs([]) == [], "runs: empty input gives no runs")
    check(runs([4, 6]) == [(4, 4), (6, 6)],
          "runs: a gap of one gives TWO runs, never one (adjacency is +1)")

    # -- empties(): detection, addressing, verse shapes --------------------
    data = {"books": [{"name": "Fixture", "chapters": [
        ["", "a populated first-chapter verse", "   "],
        ["another populated verse", {"t": ""}, {"text": "populated via text"}],
    ]}]}
    emp = empties(data)
    check(("Fixture", 1, 1) in emp, "empties: an empty string is reported")
    check(("Fixture", 1, 3) in emp, "empties: a whitespace-only verse is reported")
    check(("Fixture", 1, 2) not in emp,
          "empties: a populated verse is NOT reported (false-positive control)")
    check(("Fixture", 2, 1) not in emp,
          "empties: a populated bare-string verse is NOT reported")
    check(("Fixture", 2, 2) in emp, "empties: a dict verse with empty 't' is reported")
    check(("Fixture", 2, 3) not in emp,
          "empties: a dict verse populated via 'text' is NOT reported")
    check(emp[0] == ("Fixture", 1, 1),
          "empties: addresses are 1-based in both chapter and verse")
    check(len(emp) == 3, "empties: exactly the three planted empties are found")

    # -- a normal run still reports, and is unaffected by the control ------
    tmp = tempfile.mkdtemp(prefix="hyz_selftest_")
    try:
        good = _write(tmp, "good.json", data)
        rc, out, _ = _quiet_main(good)
        check(rc == 0, "main: an asset WITH empties returns 0")
        check("3 empty verse(s)" in out, "main: the report states the empty count")
        check("1-1, 3-3" not in out,
              "main: a singleton prints as '1', not as a degenerate range")

        # -- the failure path: invariant B --------------------------------
        allfull = {"books": [{"name": "Full", "chapters": [["x", "y", "z"]]}]}
        full = _write(tmp, "full.json", allfull)
        rc, out, err = _quiet_main(full)
        check(rc != 0, "main: an asset with NO empties FAILS (never a plausible 0)")
        check("NO EMPTIES FOUND" in err, "main: the failed read says so on stderr")
        check(out == "", "main: a failed read prints NO clean-looking report")

        malformed = _write(tmp, "malformed.json", {"books": []})
        rc, out, err = _quiet_main(malformed)
        check(rc != 0, "main: a malformed asset FAILS, and never returns 0")
        check(out == "", "main: a malformed asset prints no report")

        # A shape the loader cannot read must fail the SAME clean way - a
        # status, never a traceback (a crash is not a status, and a reader
        # cannot tell it from a broken tool).
        unreadable = _write(tmp, "unreadable.json",
                            {"books": [{"name": "X", "chapters": "nope"}]})
        try:
            rc, out, err = _quiet_main(unreadable)
        except Exception as exc:                              # noqa: BLE001
            check(False, "main: an unreadable shape returns a status, not a "
                         "traceback (%s: %s)" % (type(exc).__name__, exc))
        else:
            check(rc != 0 and out == "",
                  "main: an unreadable shape fails cleanly, never a traceback")
            check(err.strip() != "", "main: an unreadable shape says so on stderr")

        # -- the known-bad control, asserted against the ARTIFACT ---------
        soft = os.environ.get("HEXAPLA_SOFT_FAIL") == "1"
        rc, _, _ = _quiet_main(full)
        if soft:
            check(rc == 0,
                  "HEXAPLA_SOFT_FAIL=1 is active: the failure path returns a "
                  "plausible 0 (this run is SUPPOSED to fail overall)")
        else:
            check(rc == 1, "the failure path returns exactly 1 when not softened")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [w for ok, w in results if not ok]
    print()
    print("%d assertion(s), %d failed" % (len(results), len(bad)))
    if bad:
        print("⛔ SELFTEST FAILED")
        return 1
    print("✅ selftest passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main())
