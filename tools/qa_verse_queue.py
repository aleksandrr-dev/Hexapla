# -*- coding: utf-8 -*-
"""Build a VERSE-level repair queue by merging every screen's output.

    python tools/qa_verse_queue.py --set ylt \\
        --rerender _work/ylt_rerender.txt \\
        --selfrepeat "_work/ylt_repeats_b*.log" \\
        --substitution _work/ylt_substitution.log \\
        --out _work/ylt_verse_queue.txt

## Why this exists

`_work/ylt_rerender.txt` is written as a list of

    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\narrate.py --lang ylt
        --book 0 --chapter 8 --force    # v26

⚠⚠ **CHAPTER `--force` IS FORBIDDEN FOR THIS DEFECT CLASS.** A whole-chapter
re-render is another draw at the same ~0.54 %/verse rate, so it brings a NEW
defect into a different verse of the same chapter ~13 % of the time, and it
throws away 25 good verses to fix one. `repair_verses.py` does in fact parse the
`# v26` comments out of that file, so passing it as a `--queue` works today —
but the file still LOOKS like a runnable script, and running it is a one-line
mistake that costs 22 h of GPU and re-damages the set. This tool emits a plain
`book chapter verses` queue that cannot be executed.

## The second reason: ONE FILE IS NOT THE SCOPE

`ylt_rerender.txt` holds only the APPEND sweep's findings. The self-repeat
screen ran later, over every verse of every book, and its hits live in 66
separate per-book logs that nothing had ever merged. Measured 2026-09-04:

    APPEND sweep        152 chapters, 169 verses
    self-repeat screen  190 chapters, 214 verses
    UNION               233 chapters, 280 verses   (103 verses in both)

⚠ So a queue built from `ylt_rerender.txt` alone is **60 % of the real scope**,
and it would have looked complete. Merge every screen that has run, and say
which ones those were.

## ⚠ WHAT THIS TOOL DOES NOT DECIDE

It does not triage. A self-repeat hit is queued whether or not someone judged it
a false positive from the text, because **text evidence alone cannot clear a
hit**: it cannot distinguish "the ASR misheard A as B" from "the TTS SPOKE B
where the text has A". That was established by ear on ylt 0/12 v14, where the
render really does say "westward" for "eastward". Only an ear clears a hit.
Use `--exclude` to drop verses an ear HAS cleared, and record whose ear.

Repairing a verse that was fine costs ~1 minute of GPU and re-draws one verse
behind the render gate; leaving a real defect ships it. The asymmetry says
queue it.
"""
import argparse
import glob
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# `--book 0 --chapter 8 --force    # v26`  /  `# v2,8,20`
RERENDER_RE = re.compile(r"--book (\d+) --chapter (\d+).*#\s*v([\d,\s]+)")
# `  REPEAT 22/1 v1  k=2  ...`
SELFREPEAT_RE = re.compile(r"^\s*REPEAT (\d+)/(\d+) v(\d+)\b")
# `  SUBST [0/12] v14  want ... -> heard ...`
SUBST_RE = re.compile(r"^\s*SUBST \[(\d+)/(\d+)\] v(\d+)\b")
# `B C 3,7` — this tool's own output, so a queue can be re-merged
PLAIN_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d,]+)\s*$")


def add(q, b, c, v):
    q.setdefault((int(b), int(c)), set()).add(int(v))


def scan(paths, regex, q):
    """-> (files_read, verses_added). Verses are added to q in place."""
    files = 0
    before = sum(len(v) for v in q.values())
    for p in paths:
        f = Path(p)
        if not f.exists():
            continue
        files += 1
        for line in f.read_text(encoding="utf-8", errors="replace").split("\n"):
            # ⚠ search(), NOT match(). RERENDER_RE has no `^` anchor because its
            # line STARTS with `tools\.chatterbox_venv\Scripts\python.exe …` and
            # the interesting part is in the middle. MEASURED 2026-09-04: with
            # match() this function read the 152-line rerender file, reported
            # "1 file", and contributed +0 verses — and the run still printed a
            # perfectly plausible 214-verse total. 66 verses would have gone
            # unrepaired with nothing anywhere saying so. The other three
            # patterns are `^`-anchored, so search() is identical for them.
            m = regex.search(line)
            if not m:
                continue
            b, c, v = m.group(1), m.group(2), m.group(3)
            for one in str(v).replace(" ", "").split(","):
                if one:
                    add(q, b, c, one)
    return files, sum(len(v) for v in q.values()) - before


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--rerender", help="qa_rerender_queue output (chapter cmds + # vN)")
    ap.add_argument("--selfrepeat", help="glob of qa_selfrepeat per-book logs")
    ap.add_argument("--substitution", help="qa_substitution log")
    ap.add_argument("--merge", action="append", default=[],
                    help="another plain `B C v,v` queue to fold in. REPEATABLE.")
    ap.add_argument("--exclude", help="plain `B C v,v` file of verses an EAR has "
                                     "cleared. Text evidence is not an ear.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    q, report = {}, []
    if a.rerender:
        n = scan([a.rerender], RERENDER_RE, q)
        report.append(f"APPEND sweep        {n[0]} file,  +{n[1]} verses")
    if a.selfrepeat:
        logs = sorted(glob.glob(a.selfrepeat))
        # ⛔⛔ A LOG THAT IS STILL BEING WRITTEN HOLDS ONLY PART OF ITS BOOK'S
        # HITS, AND NOTHING ABOUT IT LOOKS WRONG.
        # Measured 2026-09-04: the Task Scheduler keepalive started a SECOND
        # qa_cpu_chain instance, which went back to the ylt job because most
        # books had no sentinel, and began RE-RUNNING books that were already
        # complete — truncating each log back to in-progress as it went. A
        # queue rebuilt in that window would have silently dropped every hit of
        # the book then in flight (book 18: 19 verses) and printed a total that
        # looked entirely reasonable. Only the completion line proves a book
        # was scored to the end; anchor it, because an unanchored
        # `verses scored` also matches the `[progress]` lines.
        done_re = re.compile(r"^\d+ verses scored,", re.M)
        partial = [Path(f).name for f in logs
                   if not done_re.search(Path(f).read_text(encoding="utf-8",
                                                           errors="replace"))]
        if partial:
            print("⛔⛔ SELF-REPEAT LOG(S) HAVE NO COMPLETION LINE — that book is "
                  "STILL RUNNING or\n   DIED, so its log holds only part of its "
                  "hits. Building a queue now would\n   drop them silently. Wait "
                  "for it, or pass a narrower glob:")
            for name in partial:
                print(f"      {name}")
            sys.exit(5)
        n = scan(logs, SELFREPEAT_RE, q)
        report.append(f"self-repeat screen  {n[0]} files, +{n[1]} verses")
    if a.substitution:
        n = scan([a.substitution], SUBST_RE, q)
        report.append(f"substitution screen {n[0]} file,  +{n[1]} verses")
    for m in a.merge:
        n = scan([m], PLAIN_RE, q)
        report.append(f"merged {m}  {n[0]} file, +{n[1]} verses")

    # ⛔ A SOURCE THAT WAS NAMED, WAS READ, AND YIELDED NOTHING IS A BROKEN
    # PARSE — not a screen with no findings. It has to be impossible to miss:
    # the +0 above was invisible in a report whose bottom line looked right.
    # Distinguish the two ways a source yields nothing — they need opposite
    # fixes, and a message that names the wrong one sends the next reader after
    # a regex when the path was simply wrong.
    dead = [r for r in report if "+0 verses" in r and " 0 file" not in r]
    absent = [r for r in report if " 0 file" in r]
    if absent:
        print("⛔ A NAMED SOURCE MATCHED NO FILE AT ALL — check the path/glob, "
              "not the pattern:")
        for r in absent:
            print("      " + r)
        sys.exit(4)
    if dead:
        print("⛔⛔ A NAMED SOURCE CONTRIBUTED NOTHING. Its file WAS found and "
              "read, so this is\n   a PARSE failure, not an empty screen. Fix "
              "the pattern before trusting any\n   total below:")
        for r in dead:
            print("      " + r)
        sys.exit(3)

    if not q:
        # ⛔ An empty queue from a run that named input files is a BROKEN READ,
        # not a clean set. Never let it write a zero-line queue and exit 0.
        print("⛔ NOTHING PARSED. That is a broken read, not an empty queue — "
              "check the input paths and their line formats.")
        sys.exit(2)

    excluded = 0
    if a.exclude:
        ex = {}
        scan([a.exclude], PLAIN_RE, ex)
        for k, vs in ex.items():
            if k in q:
                excluded += len(q[k] & vs)
                q[k] -= vs
                if not q[k]:
                    del q[k]

    keys = sorted(q)
    total = sum(len(q[k]) for k in keys)
    out = Path(a.out)
    body = [f"# {a.set} verse-level repair queue — built by tools/qa_verse_queue.py",
            "# `book chapter verses`. Feed to:",
            f"#   repair_verses.py --set {a.set} --queue {out.as_posix()} --apply",
            "# ⛔ NOT a script. Chapter --force is forbidden for this defect class.",
            "# Sources merged:"]
    body += [f"#   {r}" for r in report]
    if a.exclude:
        body.append(f"#   excluded by ear ({a.exclude}): {excluded} verses")
    body.append(f"# TOTAL {len(keys)} chapters, {total} verses")
    body += [f"{b} {c} {','.join(str(v) for v in sorted(q[(b, c)]))}"
             for b, c in keys]
    out.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")

    for r in report:
        print("  " + r)
    if a.exclude:
        print(f"  excluded by ear    {excluded} verses")
    print(f"\nUNION: {len(keys)} chapters, {total} verses -> {out}")
    print("\n▶ Verify before repairing, and do not trust this count alone:")
    print(f"     python C:/Projects/Hexapla/tools/repair_verses.py --set {a.set} "
          f"--queue {out.as_posix()}          # dry run")
    print("⚠ A hit is queued whether or not the text 'explains' it. Text evidence "
          "cannot\n  clear a hit — only an ear can. See this file's docstring.")


if __name__ == "__main__":
    main()
