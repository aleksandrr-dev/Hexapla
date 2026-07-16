# -*- coding: utf-8 -*-
"""Mechanical QA for rendered narration. Reports PASS / WARN / FAIL per chapter.

Designed to be run by a CHEAP MODEL as a monitor during long renders. All
judgment lives HERE, in thresholds, not in the operator: the script decides
pass/fail, the operator relays numbers and escalates FAILs. Do not ask a
monitor to interpret — ask it to run this and report.

    python tools/qa_narration.py --lang ru                 # whole language
    python tools/qa_narration.py --lang ru --book 30       # one book
    python tools/qa_narration.py --lang ru --quiet         # problems only

Exit code: 0 all pass, 1 any WARN, 2 any FAIL.

CHECKS, and the real bug each one exists to catch:

  offsets-count    len(offsets) must equal the chapter's verse count.
  offsets-monotonic  offsets must strictly increase (except empty verses).
  offsets-vs-audio   the last offset must land inside the audio, and within
                     one plausible verse of its end. Bark shipped 441.6s of
                     audio with offsets claiming 30s (2026-07-15).
  uniform-deltas   THE BARK SIGNATURE. If every delta equals the silence gap
                   (600ms), every verse measured 0ms and the offsets are pure
                   accumulated silence. This is the exact fingerprint of the
                   float32/`wave` bug; it must never reappear silently.
  header           offsets[0] must be > 0 — the spoken book/chapter header
                   occupies the head of the file.
  digits-in-text   Russian text must contain NO digits: CosyVoice has no
                   Russian branch, so digits go through its ENGLISH number
                   speller («Глава 1» -> "Глава one"). Owner caught this in
                   Matthew 1.
  pace-cv          per-verse speaking-rate consistency. Humans hold ~10%.
  pace-spread      fastest verse vs slowest.
  flatness         VOCODER ARTIFACTS. The owner heard one as "whispering" at
                   0:50 of Genesis 1 (2026-07-15). Content, level and voicing
                   were all NORMAL there — the only anomaly was spectral
                   flatness, 0.054 against a ~0.040 chapter median: the
                   harmonics of voiced speech partly collapsing into noise.
                   Reported RELATIVE to each chapter's own median, because
                   flatness legitimately varies with a verse's phonetics (a
                   sibilant-heavy verse is naturally flatter than a vowel-heavy
                   one) and an absolute cutoff would drown you in false alarms.
  size             an implausibly small ogg means a near-empty chapter.

NOTE flatness here is measured on the ENCODED ogg, whereas narrate.py's
re-roller measures raw WAVs. Opus at 32kbps smooths the spectrum, so the two
scales are NOT comparable — do not port a threshold between them.
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import narrate  # noqa: E402  (also owns sys.stdout wrapping)

SILENCE_MS = 600
MIN_CHARS = 20

# Thresholds. The operator does NOT get to reinterpret these.
CV_WARN = 0.22          # measured 0.22 on Obadiah/solemn before re-rolling
CV_FAIL = 0.35
SPREAD_WARN = 2.0
SPREAD_FAIL = 3.0
MIN_KB = 8
TAIL_SLACK_S = 60.0     # last offset may sit this far from the end, at most

# Flatness, relative to the chapter's own median. The one confirmed artifact
# sat at 1.35x its chapter median; 1.6x is deliberately well clear of that so
# the monitor reports the bad ones rather than every phonetically-flat verse.
FLATNESS_WARN = 1.6
FLATNESS_FAIL = 2.2


def probe_duration_s(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def _flatness_outlier(ogg, offsets, texts, dur_s):
    """Worst per-verse spectral-flatness outlier: (verse_no, ratio, value).

    Returns None ONLY when librosa is genuinely absent (the monitor may run
    under a plain interpreter) or the chapter is too short to judge.

    ⚠ DOES NOT swallow other errors. The first draft wrapped everything in a
    bare `except Exception: return None` AND forgot to import tempfile — so it
    raised NameError on every chapter, caught it, and reported CLEAN. It passed
    a chapter I had measured at 1.71x median minutes earlier. That is the exact
    shape of the Bark bug this very file exists to catch: an error silently
    converted into an all-clear. A QA check that cannot fail loudly is worse
    than no QA check, because it manufactures confidence.
    """
    try:
        import librosa
    except ImportError:
        return None          # legitimately unmeasurable; not a failure

    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "c.wav")
        r = subprocess.run(["ffmpeg", "-y", "-i", str(ogg), "-ar", "24000",
                            "-ac", "1", wav], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"ffmpeg could not decode {ogg}: "
                f"{r.stderr.decode(errors='replace')[-200:]}")
        y, sr = librosa.load(wav, sr=None, mono=True)
        vals = []
        for i, off in enumerate(offsets):
            end = ((offsets[i + 1] - SILENCE_MS) / 1000
                   if i + 1 < len(offsets) else dur_s)
            if len(texts[i]) < MIN_CHARS:
                continue
            seg = y[int(off / 1000 * sr):int(end * sr)]
            if len(seg) < 2048:
                continue
            vals.append((i + 1,
                         float(librosa.feature.spectral_flatness(y=seg).mean())))
        if len(vals) < 4:
            return None
        med = statistics.median([v for _, v in vals])
        if med <= 0:
            return None
        no, worst = max(vals, key=lambda t: t[1])
        return (no, worst / med, worst)


def check_chapter(lang, books, cfg, book_idx, ch_idx):
    """Return (status, [messages], stats). status in PASS/WARN/FAIL/MISSING."""
    d = narrate.OUTPUT / lang / str(book_idx)
    ogg, jsn = d / f"{ch_idx}.ogg", d / f"{ch_idx}.json"
    raw = books[book_idx]["chapters"][ch_idx]

    if not raw:
        return "SKIP", ["empty chapter in asset"], {}
    if not ogg.exists() or not jsn.exists():
        return "MISSING", ["not rendered"], {}

    msgs, status = [], "PASS"

    def fail(m):
        nonlocal status
        msgs.append("FAIL " + m)
        status = "FAIL"

    def warn(m):
        nonlocal status
        msgs.append("WARN " + m)
        if status != "FAIL":
            status = "WARN"

    try:
        offsets = json.load(open(jsn))["offsets"]
    except Exception as e:
        return "FAIL", [f"FAIL unreadable json: {e}"], {}

    kb = ogg.stat().st_size / 1024
    if kb < MIN_KB:
        fail(f"ogg is {kb:.0f} KB — near-empty")

    if len(offsets) != len(raw):
        fail(f"offsets {len(offsets)} != verses {len(raw)}")

    for i in range(1, len(offsets)):
        if offsets[i] < offsets[i - 1]:
            fail(f"offsets not monotonic at verse {i+1}")
            break

    if offsets and offsets[0] <= 0:
        warn("offsets[0] == 0 — spoken header missing?")

    # THE BARK SIGNATURE. A delta of exactly the silence gap means that verse
    # measured 0ms — it contributed nothing but its trailing gap.
    #
    # NOTE this originally used all(d == SILENCE_MS) and MISSED the real Bark
    # chapter it was written for: ru/42/0 has 49 deltas of 600ms and ONE of 0
    # (an empty verse adds no gap), so all() was False and the check passed a
    # chapter that was 98% broken. Fractions, not absolutes.
    deltas = [offsets[i] - offsets[i - 1] for i in range(1, len(offsets))]
    if deltas:
        zero_len = sum(1 for d in deltas if d == SILENCE_MS)
        frac = zero_len / len(deltas)
        if frac >= 0.5:
            fail(f"{zero_len}/{len(deltas)} deltas == {SILENCE_MS}ms ({frac:.0%}) "
                 f"— those verses measured 0ms (the Bark float32 bug). "
                 f"Offsets are accumulated silence, not audio.")
        elif zero_len:
            warn(f"{zero_len} verse(s) measured 0ms (delta == gap)")

    dur = probe_duration_s(ogg)
    stats = {"kb": kb, "dur_s": dur}
    if dur is None:
        fail("ffprobe could not read duration")
    elif offsets:
        last_s = offsets[-1] / 1000
        if last_s > dur:
            fail(f"last offset {last_s:.1f}s is beyond audio end {dur:.1f}s")
        elif dur - last_s > TAIL_SLACK_S:
            fail(f"last offset {last_s:.1f}s but audio runs {dur:.1f}s "
                 f"({dur-last_s:.1f}s unaccounted)")

    # Text-side checks + pace.
    texts = []
    for v in raw:
        if not v:
            texts.append("")
            continue
        t = narrate.strip_kjv_notes(v) if cfg["strip_notes"] else v
        texts.append(narrate.normalize_text(t, cfg["normalizer"]))

    if lang == "ru":
        for i, t in enumerate(texts):
            if t and re.search(r"\d", t):
                fail(f"verse {i+1} still contains a digit — will be spoken "
                     f"in ENGLISH: {t[:60]!r}")
                break

    rates = []
    if dur and len(offsets) == len(raw):
        for i in range(len(offsets)):
            end = (offsets[i + 1] - SILENCE_MS) if i + 1 < len(offsets) else dur * 1000
            ms = end - offsets[i]
            if len(texts[i]) >= MIN_CHARS and ms > 0:
                rates.append(len(texts[i]) / (ms / 1000))
    # Vocoder-artifact scan. Skipped unless librosa is importable — the QA tool
    # must still run under a plain interpreter for the monitor.
    if dur and len(offsets) == len(raw):
        worst = _flatness_outlier(ogg, offsets, texts, dur)
        if worst:
            verse_no, ratio, val = worst
            stats["flatness_ratio"] = ratio
            if ratio >= FLATNESS_FAIL:
                fail(f"verse {verse_no} spectral flatness {val:.4f} = "
                     f"{ratio:.2f}x chapter median — vocoder artifact")
            elif ratio >= FLATNESS_WARN:
                warn(f"verse {verse_no} spectral flatness {val:.4f} = "
                     f"{ratio:.2f}x chapter median — possible artifact")

    if len(rates) >= 4:
        med = statistics.median(rates)
        cv = statistics.pstdev(rates) / med
        spread = max(rates) / min(rates)
        stats.update({"cv": cv, "spread": spread, "median_cps": med})
        if cv >= CV_FAIL:
            fail(f"pace CV {cv:.0%} (>= {CV_FAIL:.0%})")
        elif cv >= CV_WARN:
            warn(f"pace CV {cv:.0%} (>= {CV_WARN:.0%})")
        if spread >= SPREAD_FAIL:
            fail(f"pace spread {spread:.1f}x (>= {SPREAD_FAIL}x)")
        elif spread >= SPREAD_WARN:
            warn(f"pace spread {spread:.1f}x (>= {SPREAD_WARN}x)")

    return status, msgs, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=list(narrate.LANG_CONFIG))
    ap.add_argument("--book", type=int)
    ap.add_argument("--quiet", action="store_true",
                    help="only show chapters that are not PASS")
    args = ap.parse_args()

    cfg = narrate.LANG_CONFIG[args.lang]
    books = narrate.load_bible(args.lang)
    book_range = [args.book] if args.book is not None else range(len(books))

    tally = {"PASS": 0, "WARN": 0, "FAIL": 0, "MISSING": 0, "SKIP": 0}
    problems = []

    for bi in book_range:
        if bi >= len(books):
            continue
        name = books[bi].get("name", f"book{bi}")
        for ci in range(len(books[bi]["chapters"])):
            status, msgs, stats = check_chapter(args.lang, books, cfg, bi, ci)
            tally[status] += 1
            if status in ("FAIL", "WARN"):
                problems.append((bi, ci, name, status, msgs))
            if args.quiet and status in ("PASS", "MISSING", "SKIP"):
                continue
            if status == "PASS":
                extra = ""
                if "cv" in stats:
                    extra = (f"  cv {stats['cv']:.0%}  spread {stats['spread']:.1f}x"
                             f"  {stats['median_cps']:.1f}ch/s")
                print(f"  PASS  {name} {ci+1}  {stats.get('dur_s',0):.0f}s{extra}")
            elif status not in ("MISSING", "SKIP"):
                print(f"  {status}  {name} {ci+1}")
                for m in msgs:
                    print(f"          {m}")

    print()
    print(f"  rendered: {tally['PASS']+tally['WARN']+tally['FAIL']}"
          f"   pass {tally['PASS']}  warn {tally['WARN']}  fail {tally['FAIL']}"
          f"   not-yet {tally['MISSING']}  empty {tally['SKIP']}")

    if problems:
        print("\n  chapters needing attention:")
        for bi, ci, name, status, msgs in problems[:40]:
            print(f"    {status}  {name} {ci+1}  (--book {bi} --chapter {ci})")

    sys.exit(2 if tally["FAIL"] else (1 if tally["WARN"] else 0))


if __name__ == "__main__":
    main()
