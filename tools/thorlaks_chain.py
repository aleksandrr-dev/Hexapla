#!/usr/bin/env python
"""
thorlaks_chain.py - the part-file -> book-file chain as ONE gated call.

Steps, each gated on the previous one's return code (a failed step stops the
chain and is the exit code; nothing downstream runs on a failed check):

  1. thorlaks_part_check.py --file <part>        (skipped without --file)
  2. thorlaks_merge_parts.py --book <B>          DRY RUN unless --apply
  3. thorlaks_part_check.py --book <B>           (only after a real merge)
  4. thorlaks_corpus_audit.py --book <B>

    python C:/Projects/Hexapla/tools/thorlaks_chain.py --book Luke --file research/_parts/luke_p50-58.md
    python C:/Projects/Hexapla/tools/thorlaks_chain.py --book Luke --file ... --apply
    python C:/Projects/Hexapla/tools/thorlaks_chain.py --book Luke            # audit-only view

Each step prints its last N lines (--tail, default 8) under a header with its
rc, so one screen replaces the three or four commands sessions typed by hand
(measured 2026-09-10: 74 calls / 37k chars in 8 sessions). --full prints
everything. Extra --prefix values are passed through to merge_parts (a book
that straddles two part prefixes needs them; see that tool's help).

Runs from the data dir regardless of cwd. A tool that cannot be found or
times out is FAILED, never 'clean'.
"""
import argparse
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

DATA = r"C:\Projects\Hexapla-releases"
TOOLS = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def step(title, args, tail, full, timeout=240, keep=None):
    exe = os.path.join(TOOLS, args[0])
    if not os.path.isfile(exe):
        print("=== %s: FAILED - tool missing: %s ===" % (title, exe))
        return 127
    try:
        r = subprocess.run([sys.executable, exe] + args[1:], cwd=DATA, env=ENV,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        print("=== %s: FAILED - timeout after %ds ===" % (title, timeout))
        return 124
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "")
    lines = out.rstrip().splitlines()
    print("=== %s: rc=%d (%d lines%s) ===" % (title, r.returncode, len(lines),
                                             "" if full or len(lines) <= tail else ", last %d" % tail))
    shown = lines if full else lines[-tail:]
    if keep and not full:
        # lines naming the book come first (the audit's row + its findings), then the tail
        named = [ln for ln in lines if keep in ln and ln not in shown][:15]
        shown = named + (["    ..."] if named else []) + shown
    for ln in shown:
        print("    " + ln[:200])
    return r.returncode


def book_index(name):
    """Index of `name` in the KJV asset, via corpus_audit's own loader (never a hand-kept table)."""
    try:
        sys.path.insert(0, TOOLS)
        import thorlaks_corpus_audit as tca
        names, _counts, _booknames = tca.load_kjv()
        return names.get(name)
    except Exception as e:  # noqa
        print("book_index: FAILED to load KJV names: %s" % e)
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--book", required=True, help="book name as in the '## <Book> <N>' headings")
    ap.add_argument("--file", help="part file to check first (relative to the data dir)")
    ap.add_argument("--prefix", action="append", help="passed through to merge_parts (repeatable)")
    ap.add_argument("--apply", action="store_true", help="really merge (default: merge dry run)")
    ap.add_argument("--tail", type=int, default=8)
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(DATA):
        print("FAILED: data dir missing: " + DATA)
        return 1

    if a.file:
        if not os.path.isfile(os.path.join(DATA, a.file)):
            print("FAILED: part file not found: " + os.path.join(DATA, a.file))
            return 1
        rc = step("1 part_check --file " + a.file, ["thorlaks_part_check.py", "--file", a.file], a.tail, a.full)
        if rc:
            print("STOP: the part file does not pass; nothing merged.")
            return rc
    else:
        print("=== 1 part_check --file: skipped (no --file) ===")

    margs = ["thorlaks_merge_parts.py", "--book", a.book]
    for p in a.prefix or []:
        margs += ["--prefix", p]
    if a.apply:
        margs.append("--apply")
    rc = step("2 merge_parts --book %s%s" % (a.book, " --apply" if a.apply else " (DRY RUN)"), margs, a.tail, a.full)
    if rc:
        print("STOP: merge reported rc=%d." % rc)
        return rc

    if a.apply:
        rc = step("3 part_check --book " + a.book, ["thorlaks_part_check.py", "--book", a.book], a.tail, a.full)
        if rc:
            print("STOP: the merged book file does not pass; look before merging again.")
            return rc
    else:
        print("=== 3 part_check --book: skipped (dry run; add --apply) ===")

    # corpus_audit takes the KJV book INDEX, not the name; resolve it the way the audit does.
    idx = book_index(a.book)
    if idx is None:
        print("=== 4 corpus_audit: FAILED - book '%s' is not a KJV book name ===" % a.book)
        return 1
    rc = step("4 corpus_audit --book %s (index %d)" % (a.book, idx),
              ["thorlaks_corpus_audit.py", "--book", str(idx)], a.tail, a.full, keep=a.book)
    print("=== chain %s: %s ===" % (a.book, "OK" if rc == 0 else "audit rc=%d" % rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
