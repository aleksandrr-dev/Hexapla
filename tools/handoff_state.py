#!/usr/bin/env python
"""
handoff_state.py - the session-start / session-end orientation in ONE call.

Prints, from live state:
  * every SESSION_HANDOFF_*.md in the data dir (ONE is correct; 0 or 2+ is a
    finding and the exit code says so),
  * the guard override files that exist (WRAPUP_OFF, IMAGE_GUARD_OFF),
  * the head of NEXT_SESSION_PROMPT.md and its age,
  * git: short status, unpushed commits, current branch,
  * the three newest archived handoffs.

    python C:/Projects/Hexapla/tools/handoff_state.py             # orient
    python C:/Projects/Hexapla/tools/handoff_state.py --archive   # DRY RUN: which
                                                                  #   handoffs would move
    python C:/Projects/Hexapla/tools/handoff_state.py --archive --apply

--archive keeps the newest handoff (by the date-time in its name, not mtime)
and moves every older one into handoff-archive/. Dry run by default (global
CLAUDE.md, script safety gate). Refuses when there is nothing older.

Measured reason (2026-09-10, 8 sessions): 45 hand-typed calls / 19k chars
doing exactly these ls/head/mv/git combinations.
Exit codes: 0 = one handoff and nothing surprising; 3 = handoff count != 1;
1 = a query FAILED (never reported as 'none').
"""
import argparse
import datetime as dt
import glob
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

DATA = r"C:\Projects\Hexapla-releases"
REPO = r"C:\Projects\Hexapla"
ARCHIVE = os.path.join(DATA, "handoff-archive")
WORK = os.path.join(DATA, "_work")
PROMPT = os.path.join(DATA, "NEXT_SESSION_PROMPT.md")
OVERRIDES = ("WRAPUP_OFF", "IMAGE_GUARD_OFF")
STAMP = re.compile(r"SESSION_HANDOFF_(\d{4}-\d{2}-\d{2})(?:_(\d{4}))?\.md$")


def age_min(path):
    return int((dt.datetime.now().timestamp() - os.path.getmtime(path)) // 60)


def handoffs():
    files = glob.glob(os.path.join(DATA, "SESSION_HANDOFF_*.md"))
    keyed = []
    for f in files:
        m = STAMP.search(os.path.basename(f))
        key = (m.group(1), m.group(2) or "0000") if m else ("0000-00-00", "0000")
        keyed.append((key, f))
    keyed.sort()
    return [f for _, f in keyed]


def git(args):
    r = subprocess.run(["git", "-C", REPO] + args, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("git %s rc=%d: %s" % (" ".join(args), r.returncode, r.stderr.strip()[:200]))
    return r.stdout.rstrip("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--archive", action="store_true", help="move all but the newest handoff to handoff-archive/")
    ap.add_argument("--apply", action="store_true", help="with --archive: really move (default dry run)")
    ap.add_argument("--head", type=int, default=8, help="lines of NEXT_SESSION_PROMPT.md to show (default 8)")
    a = ap.parse_args()
    if not os.path.isdir(DATA):
        print("FAILED: data dir missing: " + DATA)
        return 1
    rc = 0

    hs = handoffs()
    print("=== handoffs in %s: %d ===" % (DATA, len(hs)))
    for f in hs:
        print("  %s  (%d min old, %d B)%s" % (os.path.basename(f), age_min(f), os.path.getsize(f),
                                             "  <- CURRENT" if f == hs[-1] else "  <- STALE, archive it"))
    if len(hs) != 1:
        print("  !! expected exactly ONE current handoff")
        rc = 3

    if a.archive:
        older = hs[:-1]
        if not older:
            print("=== archive: nothing older than the current handoff; refusing ===")
        else:
            os.makedirs(ARCHIVE, exist_ok=True)
            for f in older:
                dest = os.path.join(ARCHIVE, os.path.basename(f))
                if os.path.exists(dest):
                    print("  !! %s already exists in archive; not moving %s" % (os.path.basename(dest), f))
                    rc = rc or 1
                    continue
                if a.apply:
                    shutil.move(f, dest)
                    print("  moved   %s -> handoff-archive/" % os.path.basename(f))
                else:
                    print("  DRY RUN would move %s -> handoff-archive/   (add --apply)" % os.path.basename(f))
            if a.apply:
                left = handoffs()
                print("  after: %d handoff(s) current" % len(left))
                rc = 0 if len(left) == 1 else 3

    present = [o for o in OVERRIDES if os.path.exists(os.path.join(WORK, o))]
    print("=== guard overrides: %s ===" % (", ".join(present) if present else "none"))

    if os.path.isfile(PROMPT):
        print("=== NEXT_SESSION_PROMPT.md (%d min old) ===" % age_min(PROMPT))
        with open(PROMPT, encoding="utf-8", errors="replace") as fh:
            for i, ln in enumerate(fh):
                if i >= a.head:
                    print("      ...")
                    break
                print("      | " + ln.rstrip()[:160])
    else:
        print("=== NEXT_SESSION_PROMPT.md: MISSING ===")

    try:
        branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
        status = git(["status", "--short"])
        unpushed = git(["log", "--oneline", "@{u}..HEAD"]) if branch != "HEAD" else ""
        print("=== git %s: %d changed path(s), %d unpushed commit(s) ===" % (
            branch, len(status.splitlines()), len(unpushed.splitlines())))
        for ln in status.splitlines()[:20]:
            print("      " + ln)
        for ln in unpushed.splitlines()[:10]:
            print("      ^ " + ln)
    except Exception as e:  # noqa
        print("=== git: FAILED (%s) ===" % e)
        rc = rc or 1

    arch = sorted(glob.glob(os.path.join(ARCHIVE, "SESSION_HANDOFF_*.md")))[-3:]
    print("=== newest archived: %s ===" % (", ".join(os.path.basename(x) for x in arch) or "none"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
