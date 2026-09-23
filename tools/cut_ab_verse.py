# -*- coding: utf-8 -*-
"""Cut ONE verse out of two different renders of the same chapter, for an A/B ear check.

    python tools/cut_ab_verse.py --book 3 --chapter 4 --verse 22 \
        --a narration/en --b narration/en_qa_fail_originals --out _work/ab_num5_22

Why this exists: a verse condemned by ear cannot be cleared by any screen, so
the owner has to hear the repaired take against the one it replaced. Making him
seek to 2m40s inside two 5-minute chapters twice is the slow part.

⚠⚠ **EACH TREE'S OFFSETS COME FROM ITS OWN `<c>.json`.** The two renders do not
share a timeline; using one tree's offsets on the other tree's ogg clips the
wrong audio and the ear then rules on the wrong thing. This script reads each
side's own offsets and refuses if either is missing.

⚠ Verse n starts at offsets[n-1] and ends at offsets[n]; the last verse runs to
end of file. Offsets are MILLISECONDS.

⛔ Writes NOTHING unless every anchor asserts. Exit 1 on any failure - a missing
clip must never be indistinguishable from a clip that came out silent.

## --selftest, and its known-bad control

    python tools/cut_ab_verse.py --selftest

It tests OFFSET RESOLUTION, not the audio cut: fixtures give the two trees
deliberately DIFFERENT offsets, and the test asserts each side resolved from
its OWN `<c>.json`. No ffmpeg, no real corpus, no audio is cut.

⛔ A control that passes on broken code is not a control. `HEXAPLA_XTREE_OFFSETS=1`
makes side B resolve its offsets from side A's tree - exactly the defect the
warning above exists to prevent, and one that is INAUDIBLE as a bug: the clip
plays, it is simply the wrong audio, and the owner then rules on it. Both
directions must hold:

    python tools/cut_ab_verse.py --selftest                        # exit 0
    HEXAPLA_XTREE_OFFSETS=1 python tools/cut_ab_verse.py --selftest # exit 1
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def side(tree, book, chapter, verse, root=None, off_tree=None):
    """Return (ogg_path, start_s, end_s_or_None) for one tree, asserting as it goes.

    ⚠ `off_tree` exists ONLY so --selftest can inject the cross-tree defect.
    In every real run it is None and the offsets come from `tree` itself.
    """
    base = root or DATA
    d = base / tree / str(book) / str(chapter)
    ogg = d.with_suffix(".ogg")
    off = (base / (off_tree or tree) / str(book) / str(chapter)).with_suffix(".json")
    if not ogg.is_file():
        fail("no ogg: %s" % ogg)
    if not off.is_file():
        fail("no offsets file: %s" % off)
    offs = json.loads(off.read_text(encoding="utf-8")).get("offsets")
    if not offs:
        fail("no 'offsets' key in %s" % off)
    if verse > len(offs):
        fail("verse %d beyond %d offsets in %s" % (verse, len(offs), off))
    start = offs[verse - 1] / 1000.0
    end = offs[verse] / 1000.0 if verse < len(offs) else None
    if end is not None and end <= start:
        fail("non-advancing offsets in %s: %s -> %s" % (off, start, end))
    return ogg, start, end, len(offs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, required=True, help="0-based book index")
    ap.add_argument("--chapter", type=int, required=True, help="0-based chapter index")
    ap.add_argument("--verse", type=int, required=True, help="1-based verse number")
    ap.add_argument("--a", required=True, help="tree for side A (relative to the data dir)")
    ap.add_argument("--b", required=True, help="tree for side B")
    ap.add_argument("--out", required=True, help="output directory (relative to the data dir)")
    a = ap.parse_args()

    outdir = DATA / a.out
    outdir.mkdir(parents=True, exist_ok=True)

    plan = []
    for label, tree in (("A", a.a), ("B", a.b)):
        # ⚠ off_tree stays None in a real run: each tree's offsets come from its
        # own <c>.json. HEXAPLA_XTREE_OFFSETS is the known-bad control for that
        # invariant and must never be set outside --selftest.
        xtree = (a.a if (label == "B"
                         and os.environ.get("HEXAPLA_XTREE_OFFSETS") == "1")
                 else None)
        ogg, start, end, n = side(tree, a.book, a.chapter, a.verse, off_tree=xtree)
        plan.append((label, tree, ogg, start, end, n))

    if plan[0][5] != plan[1][5]:
        fail("the two trees disagree on verse count (%d vs %d) - they are not the "
             "same chapter and an A/B between them is meaningless"
             % (plan[0][5], plan[1][5]))

    written = []
    for label, tree, ogg, start, end, n in plan:
        dest = outdir / ("%s.ogg" % label)
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % start]
        if end is not None:
            cmd += ["-to", "%.3f" % end]
        cmd += ["-i", str(ogg), "-c:a", "libvorbis", str(dest)]
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            fail("ffmpeg rc=%d cutting %s from %s" % (rc, label, ogg))
        if not dest.is_file() or dest.stat().st_size < 2000:
            fail("%s came out missing or tiny (%s) - refusing to hand over a clip "
                 "that would sound like an answer"
                 % (dest, dest.stat().st_size if dest.is_file() else "absent"))
        dur = end - start if end is not None else None
        written.append((label, tree, dest, start, end, dur))
        print("%s  %-34s  %7.2fs -> %s  (%d B)"
              % (label, tree, start, ("%.2fs" % end) if end else "EOF",
                 dest.stat().st_size))

    da, db = written[0][5], written[1][5]
    if da and db and abs(da - db) > max(da, db) * 0.75:
        print("NOTE: the two clips differ in length by more than 75%% "
              "(%.2fs vs %.2fs) - check the offsets before trusting the A/B" % (da, db))

    print("OK: wrote %d clips to %s" % (len(written), outdir))


# ---------------------------------------------------------------- selftest ---

def _tree(root, tree, book, chapter, offsets, ogg=True, key="offsets"):
    """Plant one tree's chapter: a stub ogg plus its own offsets json."""
    d = root / tree / str(book)
    d.mkdir(parents=True, exist_ok=True)
    if ogg:
        (d / ("%d.ogg" % chapter)).write_bytes(b"\0" * 4096)
    if offsets is not None:
        body = {key: offsets} if key else {}
        (d / ("%d.json" % chapter)).write_text(json.dumps(body), encoding="utf-8")
    return d


def _refuses(fn):
    """-> True if fn() refused via fail() (SystemExit 1), with its output eaten."""
    import contextlib
    import io
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn()
    except SystemExit as e:
        return e.code == 1
    return False


def selftest():
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    root = Path(tempfile.mkdtemp(prefix="cutab_selftest_"))
    try:
        # The two renders do NOT share a timeline - that is the whole point.
        _tree(root, "tA", 3, 4, [0, 1000, 2500, 4000])
        _tree(root, "tB", 3, 4, [0, 1500, 3000, 5000])

        ra = side("tA", 3, 4, 2, root=root)
        soft = os.environ.get("HEXAPLA_XTREE_OFFSETS") == "1"
        rb = side("tB", 3, 4, 2, root=root, off_tree=("tA" if soft else None))

        # -- offset RESOLUTION: each tree reads its own <c>.json --------------
        check(abs(ra[1] - 1.0) < 1e-9 and abs(ra[2] - 2.5) < 1e-9,
              "side A resolves verse 2 from A's own offsets (1.000 -> 2.500)")
        check(abs(rb[1] - 1.5) < 1e-9 and abs(rb[2] - 3.0) < 1e-9,
              "side B resolves verse 2 from B's OWN offsets (1.500 -> 3.000)")
        check(ra[1] != rb[1],
              "the two sides do NOT share a timeline (cross-tree offsets would "
              "clip the wrong audio)")
        check(str(ra[0]).endswith(os.path.join("tA", "3", "4.ogg")),
              "side A's ogg comes from the tree it was asked for")
        check(str(rb[0]).endswith(os.path.join("tB", "3", "4.ogg")),
              "side B's ogg comes from the tree it was asked for")

        # -- verse n = offsets[n-1] .. offsets[n] -----------------------------
        r1 = side("tA", 3, 4, 1, root=root)
        check(abs(r1[1] - 0.0) < 1e-9 and abs(r1[2] - 1.0) < 1e-9,
              "verse n spans offsets[n-1] -> offsets[n] (verse 1 = 0.000 -> 1.000)")
        r4 = side("tA", 3, 4, 4, root=root)
        check(abs(r4[1] - 4.0) < 1e-9 and r4[2] is None,
              "the LAST verse runs to end of file (end is None, not 0)")
        check(ra[3] == 4, "the verse count returned is len(offsets)")

        # -- a missing/!unusable offsets file must REFUSE, never fall back ----
        _tree(root, "noff", 3, 4, None)          # ogg only, no json
        check(_refuses(lambda: side("noff", 3, 4, 2, root=root)),
              "a MISSING offsets file refuses (never falls back to the other tree)")
        _tree(root, "nogg", 3, 4, [0, 1000], ogg=False)
        check(_refuses(lambda: side("nogg", 3, 4, 2, root=root)),
              "a missing ogg refuses")
        _tree(root, "nokey", 3, 4, [0, 1000], key=None)
        check(_refuses(lambda: side("nokey", 3, 4, 2, root=root)),
              "an offsets json with no 'offsets' key refuses")
        check(_refuses(lambda: side("tA", 3, 4, 9, root=root)),
              "a verse beyond the offsets refuses (no silent clamp)")
        _tree(root, "flat", 3, 4, [0, 1000, 1000, 2000])
        check(_refuses(lambda: side("flat", 3, 4, 2, root=root)),
              "non-advancing offsets refuse (a zero-length clip proves nothing)")

        # -- the known-bad control, asserted against the ARTIFACT -------------
        xr = side("tB", 3, 4, 2, root=root, off_tree="tA")
        check(abs(xr[1] - 1.0) < 1e-9,
              "cross-tree resolution IS detectable by these assertions "
              "(B + A's offsets gives A's 1.000, so the control can fire)")
    finally:
        shutil.rmtree(root, ignore_errors=True)

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
    main()
