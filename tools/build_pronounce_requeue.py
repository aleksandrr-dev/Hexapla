# -*- coding: utf-8 -*-
"""Build a per-VERSE re-render queue for verses whose audio predates a
pronunciation-lexicon row, for `repair_verses.py --queue`.

    python tools\\build_pronounce_requeue.py --lang en                  # plan
    python tools\\build_pronounce_requeue.py --lang en --out _work\\q.txt
    python tools\\build_pronounce_requeue.py --lang en --words esau,mizpeh,baal

## What it does

Walks the set's TEXT asset, applies the lexicon exactly the way `narrate.py`
does (`pronounce_lexicon.apply(t, set_key=<lang>)`, same call, same set key),
and emits one `B C v1,v2` line per chapter holding a changed verse.

## ⛔ WHY THIS IS OVER-INCLUSIVE, AND WHY IT IS NOT TUNED DOWN

A chapter got whatever rows were scoped to its set **on the day it was
rendered**, and NOTHING ON DISK RECORDS THAT. The chapter sidecars store
offsets, gate attempts and ASR tails - never the synthesis text and never a
hash of it - so there is no artifact that answers "does this audio already
carry Kaynen?". The only instrument for a pronunciation is an ear, and the
project has no screen for this class by construction.

▶ So this tool queues every verse the lexicon would change TODAY, not every
  verse that is known-wrong. A verse already carrying the respelling will be
  re-synthesised needlessly.
⚠ That costs a FRESH DRAW at the usual per-verse defect rate, so the gate does
  real work here - an over-inclusive queue is not free, it trades GPU and a
  small new-defect risk for not shipping a known-wrong pronunciation.
⛔ Do not "optimise" this by guessing render dates from ogg mtimes: a repair
  re-encodes the chapter, so an mtime is the last SPLICE, not the render.

## Narrowing it HONESTLY

`--words` restricts to named rows - use it when an ear has actually placed the
defect (he heard Canaan wrong on 2026-09-21, Abraham on 2026-09-13), so those
rows are known-owed rather than assumed-owed. That is a narrowing by evidence,
not by inference from a timestamp.

⚠ Addresses are 0-INDEXED IN BOOK AND CHAPTER (the narration/ convention);
verse numbers are 1-BASED, which is what `repair_verses.py --verses` wants.
The plan prints sample verse TEXT back so the address can be checked against
the spoken words before anything is rendered.

## --selftest, and its known-bad control

    python tools\\build_pronounce_requeue.py --selftest

It asserts the two things that would silently render the WRONG audio: the
1-BASED verse conversion above (an off-by-one here re-renders the neighbouring
verse and the owner then rules on it), and the PLAN-ONLY default - this tool
must write nothing without `--out`. The queue it emits is checked as an
ARTIFACT, by running the tool and reading the file back.

⛔ A control that passes on broken code is not a control.
`HEXAPLA_ZERO_BASED_VERSES=1` emits `vi` instead of `vi + 1`, reinstating
exactly the 0-vs-1 address trap. Both directions must hold:

    python tools\\build_pronounce_requeue.py --selftest                          # exit 0
    HEXAPLA_ZERO_BASED_VERSES=1 python tools\\build_pronounce_requeue.py --selftest # exit 1
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets" / "bibles"
DATA = Path(r"C:\Projects\Hexapla-releases")

# set key -> (text asset, narration directory). The KEY IS NOT THE DIRECTORY.
SETS = {
    "en":  ("en_kjv.json", "en"),
    "ylt": ("en_ylt.json", "ylt"),
}


def verse_no(vi):
    """Asset verse INDEX -> the 1-BASED verse number repair_verses.py wants.

    ⚠ narration/ is 0-indexed in book and chapter; verse numbers are NOT.
    An off-by-one here re-renders the neighbouring verse, and the owner then
    rules by ear on audio that was never the question.
    """
    if os.environ.get("HEXAPLA_ZERO_BASED_VERSES") == "1":
        # ⛔ Known-bad control for --selftest ONLY: the 0-vs-1 address trap.
        return vi
    return vi + 1


def queue_line(b, c, verses):
    """One `repair_verses.py --queue` line: `B C v1,v2` (0-based B and C)."""
    return "%d %d %s" % (b, c, ",".join(str(v) for v in verses))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en", choices=sorted(SETS))
    ap.add_argument("--words", help="comma list of lexicon keys to restrict to")
    ap.add_argument("--out", help="write the queue file (default: plan only)")
    ap.add_argument("--samples", type=int, default=4,
                    help="verse texts to print back for address checking")
    a = ap.parse_args()

    import pronounce_lexicon as pl

    asset, narr_dir = SETS[a.lang]
    only = {w.strip().lower() for w in a.words.split(",")} if a.words else None
    if only:
        known = set(pl.rows_for(a.lang, include_unvalidated=True))
        bad = only - known
        if bad:
            sys.exit("--words names rows that are not scoped to %s: %s"
                     % (a.lang, ", ".join(sorted(bad))))

    data = json.loads((ASSETS / asset).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data

    per_word, rows, samples = {}, [], []
    verses_total = 0
    for bi, b in enumerate(books):
        chapters = b["chapters"] if isinstance(b, dict) else b
        for ci, ch in enumerate(chapters):
            hit_verses = []
            for vi, v in enumerate(ch):
                if not isinstance(v, str):
                    continue
                out, hits = pl.apply(v, set_key=a.lang)
                if not hits:
                    continue
                words = {h.lower() for h in hits}
                if only is not None and not (words & only):
                    continue
                hit_verses.append(verse_no(vi))    # repair_verses wants 1-based
                for w in words:
                    if only is None or w in only:
                        per_word[w] = per_word.get(w, 0) + 1
                if len(samples) < a.samples:
                    samples.append((bi, ci, vi + 1, v, out))
            if hit_verses:
                rows.append((bi, ci, hit_verses))
                verses_total += len(hit_verses)

    missing = [f"{b}/{c}" for b, c, _ in rows
               if not (DATA / "narration" / narr_dir / str(b) / f"{c}.ogg").exists()]

    print(f"set {a.lang}  (asset {asset}, narration/{narr_dir})")
    if only:
        print(f"restricted to: {', '.join(sorted(only))}")
    print(f"\n{'entry':<12}{'verses':>8}")
    for w in sorted(per_word, key=lambda x: -per_word[x]):
        print(f"{w:<12}{per_word[w]:>8}")
    print(f"\nverses queued   : {verses_total}")
    print(f"chapters touched: {len(rows)}")
    # ⚠ A queued chapter with no ogg is an ADDRESS BUG, not a render job.
    if missing:
        print(f"\n⛔ {len(missing)} queued chapter(s) have NO ogg on disk: "
              + ", ".join(missing[:8]))
        print("   That is an addressing fault - fix it before rendering.")

    print("\nsample verses (check the address against the spoken words):")
    for bi, ci, vn, src, out in samples:
        print(f"  {narr_dir}/{bi}/{ci}.ogg  v{vn}")
        print(f"     text : {src[:88]}")
        print(f"     synth: {out[:88]}")

    if not a.out:
        print("\nPLAN ONLY - nothing written. Add --out to write the queue.")
        return 0 if not missing else 1

    lines = [queue_line(b, c, vs) for b, c, vs in rows]
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\n-> {a.out}  ({len(lines)} chapter line(s), {verses_total} verse(s))")
    return 0 if not missing else 1


# ---------------------------------------------------------------- selftest ---

def selftest():
    import re
    import shutil
    import subprocess
    import tempfile
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # -- the 1-BASED verse conversion -------------------------------------
    check(verse_no(0) == 1,
          "verse_no: asset index 0 is verse 1 (got %d) - the 0-vs-1 trap"
          % verse_no(0))
    check(verse_no(29) == 30, "verse_no: asset index 29 is verse 30")
    check(verse_no(0) != 0,
          "verse_no: NEVER emits verse 0 - repair_verses --verses is 1-based")

    # -- the queue line format repair_verses.py --queue parses ------------
    check(queue_line(0, 0, [1]) == "0 0 1",
          "queue_line: 'B C v' with 0-based book and chapter")
    check(queue_line(3, 4, [22, 23]) == "3 4 22,23",
          "queue_line: verses are comma-joined with NO spaces")
    ln = queue_line(11, 9, [18, 19, 20])
    check(bool(re.match(r"^\d+ \d+ \d+(,\d+)*$", ln)),
          "queue_line: matches the queue grammar (%r)" % ln)
    b, c, vs = ln.split()
    check(int(b) == 11 and int(c) == 9
          and [int(x) for x in vs.split(",")] == [18, 19, 20],
          "queue_line: round-trips back to its address and verses")

    # -- PLAN-ONLY by default, and the queue checked as an ARTIFACT -------
    tmp = tempfile.mkdtemp(prefix="bpr_selftest_")
    try:
        def run(*args, **kw):
            p = subprocess.run([sys.executable, os.path.abspath(__file__)]
                               + list(args), cwd=kw.get("cwd", tmp),
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        rc, out = run("--lang", "en", "--words", "canaan", "--samples", "0")
        check("PLAN ONLY - nothing written" in out,
              "a run with no --out says PLAN ONLY")
        check(os.listdir(tmp) == [],
              "PLAN-ONLY default WROTE NOTHING (temp cwd still empty)")

        rc, out = run("--lang", "en", "--words", "no_such_row_here")
        check(rc != 0 and "not scoped to en" in out,
              "--words naming an unknown row REFUSES (never a silent empty queue)")

        qp = os.path.join(tmp, "q.txt")
        rc, out = run("--lang", "en", "--words", "canaan", "--samples", "0",
                      "--out", qp)
        check(os.path.isfile(qp), "--out writes the queue file")
        if os.path.isfile(qp):
            lines = [l for l in open(qp, encoding="utf-8").read().splitlines() if l]
            check(bool(lines), "the emitted queue is not empty")
            grammar = all(re.match(r"^\d+ \d+ \d+(,\d+)*$", l) for l in lines)
            check(grammar, "EVERY emitted line matches the queue grammar")
            verses = [int(v) for l in lines for v in l.split()[2].split(",")]
            check(verses and min(verses) >= 1,
                  "EVERY emitted verse number is >= 1 (min %s) - a verse 0 "
                  "would render the wrong verse" % (min(verses) if verses else "n/a"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- the set KEY is not the directory --------------------------------
    check("en" in SETS and SETS["en"][0] == "en_kjv.json",
          "SETS maps the key 'en' to its TEXT asset (the key is not the dir)")

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
