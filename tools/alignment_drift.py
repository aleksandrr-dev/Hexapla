# -*- coding: utf-8 -*-
"""Find chapters whose WORD TIMINGS have drifted away from their audio.

    python tools/alignment_drift.py                     # every set
    python tools/alignment_drift.py --set ru            # one set
    python tools/alignment_drift.py --set ru --queue _work/ru_realign_queue.txt

WHY THIS EXISTS (2026-09-03)
----------------------------
`tail_hallucinations` flagged 39 of the 73 verses in wyc 66/4 with tails up to
2.3 s, and the owner heard "repetitions" in the ear clips. BOTH signals were
misleading and a chapter re-render was nearly authorised on them:

  . `qa_selfrepeat` -- validated, and needs NO sidecar -- scored all 450 verses
    of wyc book 66 and found ZERO repeated tails. The AUDIO was never wrong.
  . the clips overlapped: `--clips` cuts from `last_word_end - 2500 ms`, and the
    flagged verses were ADJACENT, so consecutive clips replayed the same words.
    That is what sounded like repetition.

The real fault was that ONE chapter's `.w.json`: median
(verse_end - last_word_end) was 16,032 ms against a healthy 1,322 ms, drifting
to 33,210 ms, with 2 null-timing verses. One re-alignment took the median to
1,341 ms, nulls to 0, and `tail_hallucinations` over the whole book from
"39 flagged, 2 unjudgeable" to "450 judged, 0 flagged, 0 unjudgeable".

▶ THE GAP IS A FREE DETERMINISTIC CHECK. No ASR, no ear, no GPU, no model.
A healthy chapter's median gap is just the set's trailing pad and it is TIGHT:
measured 2026-09-03, gnv / wyc / sv / tyn / en sit at ~1,322 ms with a p99
within ~20 ms of the median, and ru / cu at ~800 ms. A chapter whose median gap
is SECONDS has broken timings -- which means word-level highlighting is wrong
in the app for that chapter, silently, with nothing in any log.

⚠⚠ THIS DIAGNOSES TIMINGS, NOT AUDIO, and the difference decides the repair.
Bad audio needs a re-render (or better, a verse repair). Good audio with bad
timings needs re-alignment, which costs no GPU. To tell them apart, run
`qa_selfrepeat` -- it needs no sidecar, so a broken sidecar cannot fool it.
Re-rendering a chapter whose only fault is alignment burns GPU and fixes
nothing.

⚠ A FAILED READ RETURNS None AND IS COUNTED SEPARATELY, never as 0 ms and
never as healthy. A chapter that cannot be measured is not a chapter that
passed -- see the `evidence-discipline` skill.

⚠⚠ THE align_words `--set` KEY IS NOT THE DIRECTORY NAME: `syn` for ru, `csl`
for cu, `kxii` for sv, `gen1599` for gnv. Passing the directory name is an
argparse error that exits looking like a clean run. This tool prints the right
key for you.

⚠⚠ RE-ALIGN WITH `.kokoro_venv`, NOT `.chatterbox_venv`. The Cyrillic sets
romanize through `uroman`, which is installed only in the kokoro venv. Under
chatterbox every Cyrillic chapter dies on `ModuleNotFoundError: No module
named 'uroman'` -- measured 2026-09-03, when all 38 queued ru chapters
"completed" that way and changed nothing. Latin-script sets never reach
romanize(), so they work under either venv, which is why this is easy to miss.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

NAR = Path(r"C:\Projects\Hexapla-releases\narration")
# narration dir -> the align_words.py --set key that writes it.
ALIGN_KEY = {"ru": "syn", "cu": "csl", "sv": "kxii", "gnv": "gen1599",
             "wyc": "wyc", "tyn": "tyn", "ylt": "ylt", "en": "en", "wbt": "wbt"}
DRIFT_MS = 3000

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def median_gap(d, b, c):
    """Median (verse_end - last_word_end) in ms. None if it cannot be read."""
    try:
        side = json.loads((NAR / d / str(b) / f"{c}.json").read_text())["offsets"]
        w = json.loads((NAR / d / str(b) / f"{c}.w.json").read_text())["v"]
    except Exception:
        return None, None
    nulls = sum(1 for ws in w if not ws)
    g = [side[i + 1] - max(x[1] for x in ws)
         for i, ws in enumerate(w) if ws and i + 1 < len(side)]
    return (statistics.median(g) if g else None), nulls


def scan(d):
    rows, unreadable = [], 0
    for wj in sorted((NAR / d).glob("*/*.w.json")):
        b, c = wj.parent.name, wj.name.split(".")[0]
        if not b.isdigit() or not c.isdigit():
            continue
        m, nulls = median_gap(d, int(b), int(c))
        if m is None:
            unreadable += 1
            continue
        rows.append((m, int(b), int(c), nulls))
    return rows, unreadable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="dirs", action="append",
                    help="narration directory name (ru, cu, wyc, ...); "
                         "repeatable. Default: all present")
    ap.add_argument("--queue", help="write '<book> <chapter>' lines for the "
                                    "drifted chapters, worst first")
    ap.add_argument("--threshold", type=int, default=DRIFT_MS,
                    help=f"median gap in ms above which a chapter is drifted "
                         f"(default {DRIFT_MS})")
    a = ap.parse_args()

    # ⚠ ONLY THE LIVE SETS BY DEFAULT. narration/ also holds backups and
    # quarantines (`ru_pre_announce`, `gnv_quarantine_archaic_spelling`, ...).
    # Auto-discovery reported those as if they were shipping sets on
    # 2026-09-03, complete with a repair suggestion — 36 "drifted" chapters in
    # a directory nothing reads. Anything not in ALIGN_KEY must be asked for
    # by name.
    if a.dirs:
        dirs = a.dirs
    else:
        dirs = [d for d in ALIGN_KEY if (NAR / d).is_dir()
                and any((NAR / d).glob("*/*.w.json"))]
        skipped = [p.name for p in sorted(NAR.iterdir())
                   if p.is_dir() and p.name not in ALIGN_KEY
                   and any(p.glob("*/*.w.json"))]
        if skipped:
            print(f"  (not a live set, skipped: {', '.join(skipped)} — "
                  f"pass --set <name> to scan one anyway)")
    if a.queue and len(dirs) != 1:
        sys.exit("--queue needs exactly one --set")

    any_bad = False
    for d in dirs:
        rows, unreadable = scan(d)
        if not rows:
            print(f"  {d:4s} NO CHAPTERS MEASURED — broken read, not a clean set")
            any_bad = True
            continue
        rows.sort(reverse=True)
        meds = sorted(r[0] for r in rows)
        n = len(meds)
        bad = [r for r in rows if r[0] > a.threshold]
        any_bad |= bool(bad) or bool(unreadable)
        print(f"  {d:4s} measured={n:5d}  median-of-medians={meds[n // 2]:6.0f}ms"
              f"  p99={meds[int(n * .99)]:7.0f}ms"
              f"  drifted(>{a.threshold}ms)={len(bad)}"
              f"  unreadable={unreadable}")
        for m, b, c, nulls in bad[:10]:
            print(f"         {d} {b}/{c}  median gap {m:7.0f} ms  nulls {nulls}")
        if len(bad) > 10:
            print(f"         ... and {len(bad) - 10} more")
        if bad:
            key = ALIGN_KEY.get(d)
            if key is None:
                print(f"         ▶ {d} has no align_words --set key — it is "
                      f"not a live set; nothing to repair here")
            else:
                warn = f"  (⚠ --set {key}, NOT {d})" if key != d else ""
                print(f"         ▶ repair: python _work/realign_drifted.py "
                      f"--set {key} --queue <queue> --apply{warn}"
                      f"   — runs in .kokoro_venv, not .chatterbox_venv")
        if a.queue:
            Path(a.queue).write_text(
                "".join(f"{b} {c}\n" for _, b, c, _ in bad), encoding="utf-8")
            print(f"         queue -> {a.queue} ({len(bad)} chapters)")

    # Non-zero when anything is drifted or unmeasurable, so a chain step that
    # gates on this cannot mistake "could not read" for "nothing to do".
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
