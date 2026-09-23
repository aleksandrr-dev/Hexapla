"""One-shot repair: zh_cuv_s/zh_cuv_t John 7:53 is empty.

The CUV joins 7:53 onto 8:1 with a semicolon, so the verse slot for 7:53
exists but is blank while its text rides at the head of 8:1.  A reader who
taps 7:53 in the app gets an empty line.  This splits the clause back to its
own address.  No text is added or removed; only the joining semicolon becomes
a full stop, matching the printed CUV, and the verse COUNT is unchanged.

Refuses unless the file is in exactly the expected shape, so a re-run on an
already-repaired asset is a no-op rather than a second split.

    python tools/fix_zh_john753.py            # dry run (default)
    python tools/fix_zh_john753.py --apply

## --selftest, and its known-bad control

`--selftest` builds its own `zh_cuv_s` and `zh_cuv_t` fixtures in
`tempfile.mkdtemp()` and points the tool at them. ⛔ It NEVER touches
`app/src/main/assets/bibles/zh_cuv_*.json`. Because this tool WRITES, the
assertion that matters most is #1: a dry run must leave both files
BYTE-IDENTICAL.

⛔ A control that passes on broken code is not a control. `HEXAPLA_NO_SHAPE_GUARD=1`
makes a fixture run skip the expected-shape check and split unconditionally -
exactly the "a re-run splits a second time" defect this docstring promises it
prevents. Both directions must hold:

    python tools/fix_zh_john753.py --selftest                          # exit 0
    HEXAPLA_NO_SHAPE_GUARD=1 python tools/fix_zh_john753.py --selftest # exit 1

⚠ The variable is honoured ONLY while the selftest drives a fixture.
"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ASSETS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "app", "src", "main", "assets", "bibles"))

JOHN = 42          # 0-based position of John in the 66-book canon
CH7, CH8 = 6, 7

# file -> (text that belongs to 7:53, the separator it is joined with)
EXPECT = {
    "zh_cuv_s.json": ("于是各人都回家去了", "；"),
    "zh_cuv_t.json": ("於是各人都回家去了", "；"),
}
FULL_STOP = "。"

#: Set by selftest() while it drives a fixture; ⛔ never true in a normal run.
_IN_SELFTEST = False


def _no_shape_guard():
    """⚠ The known-bad control: skip the expected-shape check and split anyway."""
    return _IN_SELFTEST and os.environ.get("HEXAPLA_NO_SHAPE_GUARD") == "1"


def _serialise(data):
    """The asset's own serialisation: compact separators, ensure_ascii=False, LF."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def main(argv=None, assets=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    assets = assets or ASSETS
    apply = "--apply" in argv
    rc = 0
    for name, (head, sep) in EXPECT.items():
        path = os.path.normpath(os.path.join(assets, name))
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        book = data[JOHN]
        ch7, ch8 = book["chapters"][CH7], book["chapters"][CH8]
        before = sum(len(c) for c in book["chapters"])

        if ch7[52].strip():
            print("SKIP  %s  7:53 is already populated: %r" % (name, ch7[52]))
            continue
        if not ch8[0].startswith(head + sep) and not _no_shape_guard():
            print("REFUSE %s  8:1 does not start with the expected clause:\n"
                  "        %r" % (name, ch8[0]))
            rc = 1
            continue

        new753 = head + FULL_STOP
        new81 = ch8[0][len(head + sep):] if ch8[0].startswith(head + sep) \
            else ch8[0]
        print("%s  %s" % ("APPLY " if apply else "DRYRUN", name))
        print("   7:53  %r -> %r" % (ch7[52], new753))
        print("   8:1   %r" % ch8[0])
        print("      -> %r" % new81)

        ch7[52] = new753
        ch8[0] = new81
        after = sum(len(c) for c in book["chapters"])
        if before != after:
            print("REFUSE %s  verse count changed %d -> %d" % (name, before, after))
            return 1
        print("   verse count unchanged: %d" % after)

        if apply:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_serialise(data))
            os.replace(tmp, path)
            print("   written")
    if not apply and rc == 0:
        print("\ndry run only - re-run with --apply")
    return rc


# ---------------------------------------------------------------- selftest ---

BODY = "众百姓都上山去了"
_TAIL_TAIL = "众人都跟着他"


def _fixture(head, damaged=True):
    """-> a 66-book asset whose John has 7:53 blank and 8:1 holding the clause."""
    books = [{"name": "Book %d" % i, "chapters": [["text of book %d" % i]]}
             for i in range(66)]
    ch7 = ["verse %d" % i for i in range(53)]
    if damaged:
        ch7[52] = ""
    else:
        ch7[52] = head + FULL_STOP
    ch8 = [("" if not damaged else head + "；") + BODY, "second verse of 8"]
    ch8 += ["verse %d of 8" % i for i in range(3, 20)]
    chapters = [["c1"], ["c2"], ["c3"], ["c4"], ["c5"], ["c6"], ch7, ch8]
    chapters += [["ch %d" % i] for i in range(9, 22)]
    books[JOHN] = {"name": "John", "chapters": chapters}
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

    tmpdir = tempfile.mkdtemp(prefix="zh_john753_selftest_")
    out = io.StringIO()
    real_stdout = sys.stdout
    try:
        damaged = os.path.join(tmpdir, "damaged")
        os.makedirs(damaged)
        created = {}
        for name, (head, _sep) in EXPECT.items():
            p = os.path.join(damaged, name)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_serialise(_fixture(head, True)))
            created[name] = p

        # -- 1. THE DRY-RUN GATE (the assertion that matters most) ---------
        before = {n: _digest(p) for n, p in created.items()}
        sys.stdout = out
        rc = main([], damaged)
        sys.stdout = real_stdout
        after = {n: _digest(p) for n, p in created.items()}
        check(before == after,
              "dry run leaves BOTH files byte-identical (the dry-run gate)")
        check(rc == 0, "the dry run reports success without writing")

        # -- 2. --apply splits correctly in BOTH files --------------------
        sys.stdout = out
        rc = main(["--apply"], damaged)
        sys.stdout = real_stdout
        ok_split = True
        for name, (head, _sep) in EXPECT.items():
            with open(created[name], encoding="utf-8") as fh:
                book = json.load(fh)[JOHN]
            ch7, ch8 = book["chapters"][CH7], book["chapters"][CH8]
            if ch7[52] != head + FULL_STOP or ch8[0] != BODY:
                ok_split = False
        check(rc == 0 and ok_split,
              "--apply moves the head clause to 7:53 and leaves 8:1 the "
              "remainder, in BOTH files with the correct head text")

        # -- 3. verse count unchanged, book-wide --------------------------
        counts_ok = True
        for name, (head, _sep) in EXPECT.items():
            want = sum(len(c) for c in _fixture(head, True)[JOHN]["chapters"])
            with open(created[name], encoding="utf-8") as fh:
                got = sum(len(c) for c in json.load(fh)[JOHN]["chapters"])
            if got != want:
                counts_ok = False
        check(counts_ok, "the John verse count is unchanged after --apply")

        # -- 4. character conservation ------------------------------------
        cons_ok = True
        for name, (head, sep) in EXPECT.items():
            with open(created[name], encoding="utf-8") as fh:
                book = json.load(fh)[JOHN]
            joined = book["chapters"][CH7][52] + book["chapters"][CH8][0]
            rebuilt = (head + sep + BODY).replace(sep, FULL_STOP)
            if joined != rebuilt:
                cons_ok = False
        check(cons_ok,
              "7:53 + 8:1 equals the original 8:1 with ； replaced by 。 - no "
              "character lost or invented")

        # -- 5. idempotence ----------------------------------------------
        run1 = {n: _digest(p) for n, p in created.items()}
        sys.stdout = out
        rc = main(["--apply"], damaged)
        sys.stdout = real_stdout
        check({n: _digest(p) for n, p in created.items()} == run1,
              "a second --apply is a no-op: both files byte-identical to run 1")

        # -- 6. refusal ---------------------------------------------------
        odd = os.path.join(tmpdir, "odd")
        os.makedirs(odd)
        for name, (head, _sep) in EXPECT.items():
            p = os.path.join(odd, name)
            books = _fixture(head, True)
            books[JOHN]["chapters"][CH8][0] = "完全不同的开头" + BODY
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_serialise(books))
        before = {n: _digest(os.path.join(odd, n)) for n in EXPECT}
        sys.stdout = out
        rc = main(["--apply"], odd)
        sys.stdout = real_stdout
        check(rc != 0, "a fixture whose 8:1 lacks the head clause is REFUSED")
        check({n: _digest(os.path.join(odd, n)) for n in EXPECT} == before,
              "a refused run writes nothing")

        # -- 7. no collateral damage -------------------------------------
        other_ok = True
        for name, (head, _sep) in EXPECT.items():
            with open(created[name], encoding="utf-8") as fh:
                done = json.load(fh)
            want = _fixture(head, False)
            for i in range(66):
                if i != JOHN and done[i] != want[i]:
                    other_ok = False
        check(other_ok, "every book other than John is unchanged after --apply")

        # -- the known-bad control, asserted against the ARTIFACT ---------
        if _no_shape_guard():
            check(rc != 0,
                  "HEXAPLA_NO_SHAPE_GUARD=1 is active: the shape check is "
                  "skipped (this run is SUPPOSED to fail overall)")
        else:
            check(rc != 0, "the shape guard is real when not skipped")
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
