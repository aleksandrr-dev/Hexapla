"""Print the context curve of a transcript: turn 1, 5, 10, 25, 50 and last.

Answers "what does a session COST just to start, and how fast does it grow?"
with this box's own billed numbers rather than an estimate.
"""
import glob
import json
import os
import sys

TR = os.path.expanduser("~/.claude/projects/C--Projects-Hexapla")


def curve(path):
    ctxs = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"assistant"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "assistant":
                    continue
                u = (d.get("message") or {}).get("usage") or {}
                if not u:
                    continue
                ctxs.append(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                            + u.get("cache_creation_input_tokens", 0))
    except Exception:
        return []
    return ctxs


targets = sys.argv[1:]
if not targets:
    targets = sorted(glob.glob(os.path.join(TR, "*.jsonl")),
                     key=os.path.getmtime, reverse=True)[:6]

print("%-14s %6s %8s %8s %8s %8s %8s %8s" %
      ("session", "turns", "t1", "t5", "t10", "t25", "t50", "last"))
for p in targets:
    c = curve(p)
    if len(c) < 2:
        continue
    def at(i):
        return "%dk" % (c[i - 1] // 1000) if len(c) >= i else "-"
    print("%-14s %6d %8s %8s %8s %8s %8s %8s" %
          (os.path.basename(p)[:12], len(c), at(1), at(5), at(10), at(25), at(50),
           "%dk" % (c[-1] // 1000)))
