# -*- coding: utf-8 -*-
"""Turn QA findings into the exact re-render commands, and verify them after.

    python tools/qa_rerender_queue.py --lang ylt \\
        --sweep _work/qa_asr_ylt_full.log --selfrepeat _work/ylt_repeats.txt
    python tools/qa_rerender_queue.py --lang ylt --sweep ... --verify

## ⚠ SINCE 2026-09-03 THE UNIT OF REPAIR IS THE VERSE, NOT THE CHAPTER

Feed this tool's output file straight to `tools/repair_verses.py --set <KEY>
--queue <file>` — it parses the `# v3,7` comments and re-synthesises ONLY those
verses (gated, spliced, re-aligned). The `narrate.py --force` lines below are
kept for the truncation class only (zero_duration hits); the Bash hook blocks
them otherwise, and the "~N h of GPU at 7 chapters/hour" figure printed below
is the OLD price — verse repair costs ~1 min per verse.

## Why a tool and not a note

The unit of repair WAS a CHAPTER (`narrate.py --force` re-renders a whole
chapter), while every screen reports VERSES. Converting one to the other by
hand across ~180 chapters is exactly the kind of transcription that goes wrong
quietly, and the handoff rule is that a fiddly derivation becomes a script.

It merges both validated screens, because they see different defects:

  - `qa_asr_sweep.py` APPEND - words appended that the text does not account
    for. Catches REPEATS and NOVEL hallucinations. Needs a readable reference,
    so English sets only. Validated 10/10 by ear 2026-09-02.
  - `qa_selfrepeat.py` - the ASR transcript repeats its own tail. Catches
    REPEATS only, in ANY language. Validated 9/10 with 0/40 false positives.

## ⚠ AFTER RE-RENDERING, RE-CHECK. A RE-RENDER CAN INTRODUCE A FRESH DEFECT.

`--verify` re-runs the cheap deterministic check over the chapters you just
re-rendered and prints what to do next. ylt 1 Samuel 28 rendered TRUNCATED on
the first pass - 12 verses silent inside a file that passed a 1189/1189 count -
so "it was re-rendered" is not evidence that it is now correct.

## ⚠ THE UPLOAD IS RESUMABLE, SO FIX FIRST AND RE-UPLOAD AFTER

`upload_narration.py` runs with `checksum=True`: files already on the item with
a matching MD5 are skipped. So re-running the SAME upload command after a
re-render sends only the changed chapters. Do NOT pause a running upload to
wait for repairs - it costs days of archive.org throughput and saves nothing.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
NAR = Path("C:/Projects/Hexapla-releases/narration")

APPEND = re.compile(r"^\s*APPEND \[(\d+)/(\d+)\] v(\d+) ")
SELFREP = re.compile(r"^k=(\d+) (\d+)/(\d+) v(\d+)")
SELFREP2 = re.compile(r"^\s*REPEAT (\d+)/(\d+) v(\d+)\s+k=(\d+)")


def collect(sweep, selfrepeat):
    """-> {(book, chapter): {verse: [reasons]}}"""
    out = defaultdict(lambda: defaultdict(list))
    if sweep and Path(sweep).exists():
        for ln in Path(sweep).read_text(encoding="utf-8", errors="replace").split("\n"):
            m = APPEND.match(ln)
            if m:
                b, c, v = int(m.group(1)), int(m.group(2)), int(m.group(3))
                out[(b, c)][v].append("APPEND")
    if selfrepeat and Path(selfrepeat).exists():
        for ln in Path(selfrepeat).read_text(encoding="utf-8", errors="replace").split("\n"):
            m = SELFREP.match(ln) or SELFREP2.match(ln)
            if not m:
                continue
            g = m.groups()
            if ln.startswith("k="):
                b, c, v = int(g[1]), int(g[2]), int(g[3])
            else:
                b, c, v = int(g[0]), int(g[1]), int(g[2])
            out[(b, c)][v].append("SELFREPEAT")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--sweep")
    ap.add_argument("--selfrepeat")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not a.sweep and not a.selfrepeat:
        sys.exit("pass --sweep and/or --selfrepeat")

    found = collect(a.sweep, a.selfrepeat)
    if not found:
        print("no findings in the given log(s) - nothing to re-render")
        return
    chapters = sorted(found)
    n_v = sum(len(v) for v in found.values())
    both = sum(1 for ch in found for v in found[ch]
               if len(set(found[ch][v])) > 1)

    print(f"{n_v} flagged verse(s) in {len(chapters)} chapter(s)"
          + (f"; {both} verse(s) flagged by BOTH screens" if both else ""))
    print(f"\n\u26a0 The unit of repair is the CHAPTER: {len(chapters)} re-renders, "
          f"~{len(chapters)/7:.0f} h of GPU at 7 chapters/hour.\n")

    venv = r"tools\.chatterbox_venv\Scripts\python.exe"
    lines = [f"{venv} tools\\narrate.py --lang {a.lang} "
             f"--book {b} --chapter {c} --force"
             f"    # v{','.join(str(x) for x in sorted(found[(b, c)]))}"
             for b, c in chapters]
    if a.out:
        Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"commands written to {a.out}")
    else:
        for ln in lines[:40]:
            print("  " + ln)
        if len(lines) > 40:
            print(f"  ... {len(lines) - 40} more (use --out)")

    if a.verify:
        print("\n--- verifying the flagged chapters on disk ---")
        missing = [f"{b}/{c}" for b, c in chapters
                   if not (NAR / a.lang / str(b) / f"{c}.ogg").exists()]
        if missing:
            print(f"  \u26d4 {len(missing)} chapter(s) have no audio at all: "
                  f"{', '.join(missing[:8])}")
        r = subprocess.run([sys.executable,
                            str(HERE / "zero_duration_verses.py"), a.lang],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-2:]
        print("  zero-duration check: " + " | ".join(tail))
        print("\n\u26a0 A clean zero-duration result does NOT mean the repeats are "
              "gone - that\n  check is blind to them. Re-run the screen that "
              "flagged them, then LISTEN:\n"
              f"    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\qa_asr_clips.py "
              f"<log> --lang {a.lang} --out _work/{a.lang}_recheck.ogg")


if __name__ == "__main__":
    main()
