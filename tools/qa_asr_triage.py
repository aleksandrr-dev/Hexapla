# -*- coding: utf-8 -*-
"""Sort qa_asr_sweep's APPEND flags into REPEAT / NOVEL / NOISE, from the log.

    python tools/qa_asr_triage.py _work/qa_asr_ylt_full.log

Runs on the LOG, not the audio, so it costs nothing and needs no re-sweep.

## Why the split matters

`qa_asr_sweep` reports APPEND = audio after the last real word. On ylt Genesis
that is a genuine signal, but it is not ONE defect:

  NOISE   the appended text has no letters ("'", "-"). An artifact of the ASR's
          punctuation, never a render defect. Drop it.
  REPEAT  the appended words re-say the end of the verse - «servant to him TO
          HIM», «face of jehovah JEHOVAH», «and humbleth her AND HUMBLED HER».
          This is Chatterbox's known repetition mode; `narrate.py` already
          carries a repetition retry and an `alignment_repetition` flag, so
          these are the cases where the retry did not save it.
  NOVEL   the appended words correspond to nothing in the verse - «saying SUIK».
          This is the class the owner's ear caught on the pilot («POLE»,
          «NASS», «ACCORD») and it is the most likely to be audible as garbage.

⚠ ALL THREE ARE SCREENS. A REPEAT can be the ASR stuttering rather than the
render; a NOVEL can be the ASR inventing a word for a proper noun it cannot
place. **Nothing here is a defect until someone listens.** The point is to hand
an ear a ranked list of tens instead of an unranked list of hundreds.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEAD = re.compile(r"^\s*APPEND \[(\d+)/(\d+)\] v(\d+) \+(.*)  ratio ([0-9.]+)\s*$")


def classify(added, want_tail):
    if not re.search(r"[a-z]", added):
        return "NOISE"
    aw = added.split()
    ww = want_tail.split()
    # A repeat re-says words that are already at the end of the verse.
    if aw and ww:
        n = len(aw)
        if aw == ww[-n:]:
            return "REPEAT"
        # allow a near match - the ASR rarely repeats a phrase verbatim
        if n <= len(ww) and difflib.SequenceMatcher(None, aw, ww[-n:]).ratio() >= 0.6:
            return "REPEAT"
        if len(aw) == 1 and aw[0] in ww:
            return "REPEAT"
    return "NOVEL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--show", default="NOVEL,REPEAT",
                    help="comma-separated classes to print in full")
    a = ap.parse_args()

    lines = Path(a.log).read_text(encoding="utf-8", errors="replace").split("\n")
    show = set(s.strip().upper() for s in a.show.split(","))
    buckets = {"NOVEL": [], "REPEAT": [], "NOISE": []}

    for i, ln in enumerate(lines):
        m = HEAD.match(ln)
        if not m:
            continue
        b, ch, v, added, ratio = m.groups()
        added = added.strip().strip("'\"")
        want = heard = ""
        for j in (i + 1, i + 2):
            if j < len(lines):
                t = lines[j].strip()
                if t.startswith("want :"):
                    want = t[6:].strip()
                elif t.startswith("heard:"):
                    heard = t[6:].strip()
        kind = classify(added, want)
        buckets[kind].append((f"{b}/{ch} v{v}", added, float(ratio), want, heard))

    tot = sum(len(v) for v in buckets.values())
    print(f"{tot} APPEND flag(s): "
          f"{len(buckets['NOVEL'])} NOVEL, {len(buckets['REPEAT'])} REPEAT, "
          f"{len(buckets['NOISE'])} NOISE\n")
    for kind in ("NOVEL", "REPEAT", "NOISE"):
        rows = buckets[kind]
        if not rows:
            continue
        print(f"--- {kind} ({len(rows)}) ---")
        if kind not in show:
            print("   " + ", ".join(r[0] for r in rows) + "\n")
            continue
        for ref, added, ratio, want, heard in sorted(rows, key=lambda r: r[2]):
            print(f"  {ref:<12} +{added!r}  ratio {ratio:.2f}")
            print(f"      want : {want}")
            print(f"      heard: {heard}")
        print()
    print("⚠ A screen, not a verdict. NOVEL first, then REPEAT; NOISE is the "
          "ASR's punctuation\n  and can be ignored. Nothing is a defect until "
          "someone listens to it.")


if __name__ == "__main__":
    main()
