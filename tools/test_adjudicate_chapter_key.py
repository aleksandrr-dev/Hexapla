#!/usr/bin/env python
u"""Control for the (chapter, verse) verdict key in `thorlaks_adjudicate_merge`.

THE DEFECT (Luke idx 67, 2026-09-20)
------------------------------------
A page can print the same verse number in two chapters - idx 67 carries
Luke 13:10 and Luke 14:10 - and a verdict line keys its site by `v10` alone,
because the brief writes no chapter. The merge tool refused the whole page
rather than mis-file a verdict, and nothing was written for a page whose four
adjudication chunks were complete.

The fix keys a site by (chapter, verse) and reads the chapter off the
verdict's own `lineNN`, which both reads already carry.

WHAT THIS ASSERTS - BOTH DIRECTIONS
-----------------------------------
  * FIXED: a fixture page with v10 in two chapters merges, and each v10 gets
    ITS OWN chapter's verdict - `kendi` in 13:10, `fæti` in 14:10. Taking the
    other chapter's verdict would produce the other word, so the assertion
    distinguishes the fix from a coincidence.
  * KNOWN-BAD: with `HEXAPLA_NO_CHAPKEY=1` the old verse-only key is restored,
    both verdicts collapse onto chapter 13, and the run REFUSES with the
    chapter-14 site unanswered. A control that cannot fail is not a control.

Exit 0 = both directions held. Exit 1 = they did not, and the reason is printed.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MERGE = os.path.join(HERE, "thorlaks_adjudicate_merge.py")

# ⚠ The two reads must differ ONLY at the two v10 sites: any other disputed
# site would need a verdict of its own and the refusal would be about that.
READ_A = u"""# Luke p99 - read A

## VERSES

## Cap. 13

10 Og hann kendi — line10
11 Enn sia thad — line11

## Cap. 14

10 Enn tha sæti — line50
"""

READ_B = u"""# Luke p99 - read B

## VERSES

## Cap. 13

10 Og hann kende — line10
11 Enn sia thad — line11

## Cap. 14

10 Enn tha fæti — line50
"""

# Two verdicts, the SAME `v10`, different chapters - told apart only by lineNN.
VERDICTS = u"""line10 | v10 | A=kendi | B=kende | VERDICT: A
line50 | v10 | A=sæti | B=fæti | VERDICT: B
"""


def run(tmp, env_extra):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra)
    out = os.path.join(tmp, "out_%s.md" % ("bad" if env_extra else "fixed"))
    p = subprocess.Popen(
        [sys.executable, MERGE,
         "--a", os.path.join(tmp, "a.md"), "--b", os.path.join(tmp, "b.md"),
         "--verdicts", os.path.join(tmp, "v.md"),
         "--book", "Luke", "--chapter", "13", "--page", "p99",
         "--out", out, "--apply"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    text = p.communicate()[0].decode("utf-8", "replace")
    body = io.open(out, encoding="utf-8").read() if os.path.exists(out) else u""
    return p.returncode, text, body


def main():
    tmp = tempfile.mkdtemp(prefix="chapkey_")
    for name, body in (("a.md", READ_A), ("b.md", READ_B), ("v.md", VERDICTS)):
        io.open(os.path.join(tmp, name), "w", encoding="utf-8",
                newline="\n").write(body)

    fails = []

    rc, log, body = run(tmp, {})
    if rc != 0:
        fails.append("FIXED direction: rc %d, expected 0\n%s" % (rc, log[-1200:]))
    else:
        want = [(u"## Luke 13", u"10 Og hann kendi"),
                (u"## Luke 14", u"10 Enn tha fæti")]
        for head, verse in want:
            seg = body.split(head, 1)[-1] if head in body else u""
            if verse not in seg.split(u"## ", 1)[0]:
                fails.append(u"FIXED direction: %r not under %r.\n--- body ---\n%s"
                             % (verse, head, body))

    rc, log, body = run(tmp, {"HEXAPLA_NO_CHAPKEY": "1"})
    if rc == 0:
        fails.append("KNOWN-BAD direction: HEXAPLA_NO_CHAPKEY=1 still merged "
                     "(rc 0). The control does not fail, so it is not a "
                     "control.\n--- body ---\n" + body)
    elif "NO verdict" not in log:
        fails.append("KNOWN-BAD direction: refused, but not for the unanswered "
                     "chapter-14 site:\n%s" % log[-1200:])

    for f in fails:
        print(u"[X] %s" % f)
    if fails:
        print("\n%d FAILURE(S)." % len(fails))
        return 1
    print("PASS  fixed: each v10 took its own chapter's verdict "
          "(13:10 kendi, 14:10 fæti)")
    print("PASS  known-bad: HEXAPLA_NO_CHAPKEY=1 collapses both onto chapter "
          "13 and the run refuses")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa
        pass
    sys.exit(main())
