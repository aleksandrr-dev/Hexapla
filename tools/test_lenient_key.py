#!/usr/bin/env python
u"""Control for the LENIENT verdict key in `thorlaks_adjudicate_merge`.

THE DEFECT (Luke idx 70 and 72, 2026-09-23)
-------------------------------------------
Batch 2 refused p70 (3 sites) and p72 (1) with every verdict written: the
adjudicator COPIED the site's A=/B= text with a combining mark rewritten
(`hn̄` as `hñ`), `[?]` dropped or trailing punctuation lost, so the exact key
missed. `lenient_pass()` now gives such a site the ONE unused verdict of the
same verse whose A=/B= match once those are folded.

WHAT THIS ASSERTS - THREE WAYS
------------------------------
  * FIXED: a verdict whose A= copy carries a TILDE where the site has a
    MACRON is matched, and the site takes the verdict's side (`kende`, B).
  * KNOWN-BAD: `HEXAPLA_NO_LENIENT_KEY=1` -> the same run REFUSES with the
    site unanswered. A control that cannot fail is not a control.
  * NOT TOO LOOSE: a verdict that differs from its site in CONTENT on both
    sides (not only by what `lenient()` folds) still refuses, lenient key on.

Exit 0 = all held. Exit 1 = they did not, and the reason is printed.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MERGE = os.path.join(HERE, "thorlaks_adjudicate_merge.py")

# The reads differ ONLY at 13:10 (`kēndi` with U+0304 vs `kende`).
READ_A = u"""# Luke p99 - read A

## VERSES

## Cap. 13

10 Og hann kēndi — line10
11 Enn sia thad — line11
"""

READ_B = u"""# Luke p99 - read B

## VERSES

## Cap. 13

10 Og hann kende — line10
11 Enn sia thad — line11
"""

# The copy writes a precomposed TILDE (U+1EBD) - folds to the same `kendi`.
V_FOLD = u"line10 | v10 | A=kẽndi | B=kende | VERDICT: B\n"
# Both sides differ in content - must NOT be taken.
V_CONTENT = u"line10 | v10 | A=kalladi | B=sagde | VERDICT: B\n"


def run(tmp, verdicts, env_extra, tag):
    vpath = os.path.join(tmp, "v_%s.md" % tag)
    io.open(vpath, "w", encoding="utf-8", newline="\n").write(verdicts)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("HEXAPLA_NO_LENIENT_KEY", None)
    env.update(env_extra)
    out = os.path.join(tmp, "out_%s.md" % tag)
    p = subprocess.Popen(
        [sys.executable, MERGE,
         "--a", os.path.join(tmp, "a.md"), "--b", os.path.join(tmp, "b.md"),
         "--verdicts", vpath,
         "--book", "Luke", "--chapter", "13", "--page", "p99",
         "--out", out, "--apply"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    text = p.communicate()[0].decode("utf-8", "replace")
    body = io.open(out, encoding="utf-8").read() if os.path.exists(out) else u""
    return p.returncode, text, body


def main():
    tmp = tempfile.mkdtemp(prefix="lenkey_")
    for name, body in (("a.md", READ_A), ("b.md", READ_B)):
        io.open(os.path.join(tmp, name), "w", encoding="utf-8",
                newline="\n").write(body)

    fails = []

    rc, log, body = run(tmp, V_FOLD, {}, "fixed")
    if rc != 0:
        fails.append("FIXED direction: rc %d, expected 0\n%s" % (rc, log[-1200:]))
    elif u"10 Og hann kende" not in body:
        fails.append(u"FIXED direction: 13:10 did not take verdict B (kende)."
                     u"\n--- body ---\n%s" % body)
    elif "lenient key" not in log:
        fails.append("FIXED direction: merged, but not through the lenient key "
                     "- the fixture no longer exercises it:\n%s" % log[-1200:])

    rc, log, body = run(tmp, V_FOLD, {"HEXAPLA_NO_LENIENT_KEY": "1"}, "bad")
    if rc == 0:
        fails.append("KNOWN-BAD direction: HEXAPLA_NO_LENIENT_KEY=1 still merged "
                     "(rc 0). The control does not fail.\n--- body ---\n" + body)
    elif "NO verdict" not in log:
        fails.append("KNOWN-BAD direction: refused, but not for the unanswered "
                     "site:\n%s" % log[-1200:])

    rc, log, body = run(tmp, V_CONTENT, {}, "content")
    if rc == 0:
        fails.append("NOT-TOO-LOOSE: a verdict differing in CONTENT on both "
                     "sides was taken.\n--- body ---\n" + body)

    for f in fails:
        print(u"[X] %s" % f)
    if fails:
        print("\n%d FAILURE(S)." % len(fails))
        return 1
    print("PASS  fixed: a tilde-for-macron copy is matched; 13:10 took B (kende)")
    print("PASS  known-bad: HEXAPLA_NO_LENIENT_KEY=1 refuses with the site unanswered")
    print("PASS  not too loose: a content-different verdict still refuses")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa
        pass
    sys.exit(main())
