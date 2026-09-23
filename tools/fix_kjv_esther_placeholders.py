"""One-shot repair: en_kjv «Additions to Esther» (slot 78) carries 12 `…` slots.

The KJV prints the Greek additions as «The rest of the chapters of the book of
Esther», starting at 10:4 - chapters 1-9 and 10:1-3 are the canonical Hebrew
book and are NOT in the Apocrypha section. The asset kept those addresses as
one-verse chapters holding a bare `…`, so the reader shows an ellipsis where
there is nothing to show, and `audit_empty_verses.py` (kind PLACE, 2026-09-20)
reports them as placeholders rendering like text.

The corpus already has the right shape for this book: `sv_karlxii` and
`hy_zohrab` carry slot 78 with chapters 1-9 as EMPTY chapters and 10:1-3 as
empty verses - ReaderScreen skips a blank verse (unless the split-view partner
has text) and steps over an empty chapter, so nothing is displayed and nothing
is mis-addressed. This makes en_kjv match that shape:

    chapters 1-9 :  ["…"]  ->  []
    10:1-3       :  "…"    ->  ""

No scripture is added, removed or moved; every other verse is byte-identical.
Refuses unless the book is in exactly the expected shape, so a re-run on an
already-repaired asset is a no-op rather than a second edit. Dry run by
default; `--apply` writes atomically with the asset's own serialisation
(compact separators, ensure_ascii=False, LF).

    python tools/fix_kjv_esther_placeholders.py            # dry run
    python tools/fix_kjv_esther_placeholders.py --apply

## --selftest, and its known-bad control

`--selftest` builds its OWN asset fixture in `tempfile.mkdtemp()` and points the
tool at it. ⛔ It NEVER touches `app/src/main/assets/bibles/en_kjv.json`. Because
this tool WRITES, the assertion that matters most is #1: a dry run must leave
the file BYTE-IDENTICAL.

⛔ A control that passes on broken code is not a control. `HEXAPLA_NO_DRYRUN_GATE=1`
makes a fixture run write as if `--apply` had been passed - it removes exactly
the dry-run default this docstring promises. Both directions must hold:

    python tools/fix_kjv_esther_placeholders.py --selftest                          # exit 0
    HEXAPLA_NO_DRYRUN_GATE=1 python tools/fix_kjv_esther_placeholders.py --selftest # exit 1

⚠ The variable is honoured ONLY while the selftest drives a fixture; a normal
invocation of this tool still never writes without `--apply`.
"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ASSET = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "app", "src", "main", "assets", "bibles", "en_kjv.json"))
SLOT = 78
NAME = "Additions to Esther"
PLACEHOLDER = "…"

#: Set by selftest() while it drives a fixture; ⛔ never true in a normal run.
_IN_SELFTEST = False


def _no_dryrun_gate():
    """⚠ The known-bad control: a fixture run behaves as if `--apply` was given."""
    return _IN_SELFTEST and os.environ.get("HEXAPLA_NO_DRYRUN_GATE") == "1"


def _serialise(data):
    """The asset's own serialisation: compact separators, ensure_ascii=False, LF."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def main(argv=None, asset=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    asset = asset or ASSET
    apply = "--apply" in argv or _no_dryrun_gate()
    with open(asset, encoding="utf-8") as fh:
        data = json.load(fh)
    book = data[SLOT]
    if book.get("name") != NAME:
        print("⛔ slot %d is «%s», not «%s» - nothing done" % (SLOT, book.get("name"), NAME))
        return 2
    ch = book["chapters"]
    if len(ch) != 16:
        print("⛔ expected 16 chapters, found %d - nothing done" % len(ch))
        return 2
    head_ok = all(c == [PLACEHOLDER] for c in ch[:9])
    ten_ok = len(ch[9]) == 13 and ch[9][:3] == [PLACEHOLDER] * 3 and all(
        any(x.isalpha() for x in v) for v in ch[9][3:])
    rest_ok = all(any(x.isalpha() for x in v) for c in ch[10:] for v in c)
    already = all(c == [] for c in ch[:9]) and ch[9][:3] == [""] * 3
    if already:
        print("✅ already repaired: chapters 1-9 empty, 10:1-3 empty - nothing to do")
        return 0
    if not (head_ok and ten_ok and rest_ok):
        print("⛔ unexpected shape (1-9 placeholders: %s, 10:1-3 placeholders: %s, rest scripture: %s)"
              " - nothing done" % (head_ok, ten_ok, rest_ok))
        return 2
    plan = ["  ch %d: [\"…\"] -> []" % (i + 1) for i in range(9)]
    plan += ["  10:%d: \"…\" -> \"\"" % (i + 1) for i in range(3)]
    print("%s slot %d «%s»: 12 placeholder slots" % ("APPLY" if apply else "DRY RUN", SLOT, NAME))
    print("\n".join(plan))
    if not apply:
        print("dry run - nothing written; re-run with --apply")
        return 0
    for i in range(9):
        ch[i] = []
    for i in range(3):
        ch[9][i] = ""
    tmp = asset + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_serialise(data))
    os.replace(tmp, asset)
    with open(asset, encoding="utf-8") as fh:
        back = json.load(fh)[SLOT]["chapters"]
    ok = all(c == [] for c in back[:9]) and back[9][:3] == [""] * 3 and len(back[9]) == 13
    print("✅ written and re-read: %s" % ("shape confirmed" if ok else "⛔ SHAPE WRONG AFTER WRITE"))
    return 0 if ok else 1


# ---------------------------------------------------------------- selftest ---

def _fixture(damaged=True):
    """-> a synthetic 79-slot asset in the damaged (or repaired) shape."""
    books = [{"name": "Book %d" % i, "chapters": [["verse one of %d" % i]]}
             for i in range(79)]
    ch = [["genuine %d" % i] for i in range(9)]
    if damaged:
        ch = [[PLACEHOLDER] for _ in range(9)]
    ten = ["real text %d" % i for i in range(13)]
    if damaged:
        ten = [PLACEHOLDER] * 3 + ["real text %d" % i for i in range(3, 13)]
    ch.append(ten)
    ch += [["rest of the book %d" % i] for i in range(6)]
    books[SLOT] = {"name": NAME, "chapters": ch}
    return books


def _digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def selftest():
    global _IN_SELFTEST
    _IN_SELFTEST = True
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    fd, tmpdir = tempfile.mkstemp(prefix="kjv_esther_selftest_")
    os.close(fd)
    os.unlink(tmpdir)
    os.makedirs(tmpdir)
    out = io.StringIO()
    real_stdout = sys.stdout
    try:
        damaged = os.path.join(tmpdir, "damaged.json")
        with open(damaged, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_serialise(_fixture(True)))

        # -- 1. THE DRY-RUN GATE (the assertion that matters most) ---------
        before = _digest(damaged)
        sys.stdout = out
        rc = main([], damaged)
        sys.stdout = real_stdout
        after = _digest(damaged)
        check(before == after,
              "dry run leaves the file BYTE-IDENTICAL (the dry-run gate)")
        check(rc == 0, "the dry run reports success without writing")
        if _no_dryrun_gate():
            check(before != after,
                  "HEXAPLA_NO_DRYRUN_GATE=1 is active: the fixture run wrote "
                  "without --apply (this run is SUPPOSED to fail overall)")
        else:
            check(before == after,
                  "a fixture run does NOT write unless the gate is removed")

        # -- 2. --apply does exactly 12 slots -----------------------------
        sys.stdout = out
        rc = main(["--apply"], damaged)
        sys.stdout = real_stdout
        with open(damaged, encoding="utf-8") as fh:
            fixed = json.load(fh)
        ch = fixed[SLOT]["chapters"]
        check(rc == 0 and all(c == [] for c in ch[:9]) and ch[9][:3] == [""] * 3,
              "--apply makes chapters 1-9 [] and 10:1-3 '' (exactly 12 slots)")
        check(len(ch) == 16 and len(ch[9]) == 13,
              "--apply changes no chapter or verse count")

        # -- 3. idempotence ----------------------------------------------
        run1 = _digest(damaged)
        sys.stdout = out
        rc = main(["--apply"], damaged)
        sys.stdout = real_stdout
        check(_digest(damaged) == run1,
              "a second --apply is a no-op: the file is byte-identical to run 1")

        # -- 4. refusal on an unexpected shape ---------------------------
        odd = os.path.join(tmpdir, "odd.json")
        books = _fixture(True)
        books[SLOT]["chapters"][9][0] = "10:1 already holds real text"
        with open(odd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_serialise(books))
        before = _digest(odd)
        sys.stdout = out
        rc = main(["--apply"], odd)
        sys.stdout = real_stdout
        check(rc == 2, "a slot 78 not in the expected shape is REFUSED (rc 2)")
        check(_digest(odd) == before, "a refused run writes nothing")

        # -- 5. no collateral damage -------------------------------------
        orig = _fixture(False)
        with open(damaged, encoding="utf-8") as fh:
            done = json.load(fh)
        others_ok = all(done[i] == orig[i] for i in range(len(orig)) if i != SLOT)
        check(others_ok, "every book other than slot 78 is unchanged")
        tail_ok = done[SLOT]["chapters"][9][3:] == orig[SLOT]["chapters"][9][3:]
        check(tail_ok, "every verse in 78 from 10:4 onward is unchanged")

        # -- 6. round-trip, LF only --------------------------------------
        with open(damaged, "rb") as fh:
            raw = fh.read()
        check(b"\r\n" not in raw, "the written file contains no CRLF")
        check(json.loads(raw.decode("utf-8"))[SLOT]["name"] == NAME,
              "the written file re-parses with slot 78 intact")
    finally:
        sys.stdout = real_stdout
        shutil.rmtree(tmpdir, ignore_errors=True)

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
