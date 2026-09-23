#!/usr/bin/env python
"""Control for the 2-of-3 MAJORITY VOTE in `thorlaks_adjudicate_merge.sites()`.

WHY THIS EXISTS
---------------
A screen is broken until a control fires. This one fires BOTH ways:

  * with a third read, a site two reads agree on is settled in code and is
    NOT adjudicable, and the wording it contributes is the majority's;
  * with `HEXAPLA_NO_VOTE=1` the SAME inputs put every one of those sites back
    in front of an adjudicator. If that number does not rise, the vote is not
    doing the thing the pass count claims.

and it pins the other half of the ruling: **without `--c` the two-read site
list is unchanged**, field for field, so the vote cannot have quietly altered
the pipeline that has already merged pages.

    python tools/test_majority_vote.py          # exit 0 = all controls fired

⛔ Exit 1 names the control that did not fire. A test that cannot run has not
passed.
"""
import io
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

# Three synthetic reads of one verse, keyed the way `verses_with_addr` returns.
# ⚠ difflib cuts the two ADJACENT disputed words `þr sagde` / `þeir fagde` into
# ONE site, so the three A/B sites are:
#   site 1  `þr sagde`/`þeir fagde`  - C agrees with B at one position and with
#                                      A at the other -> settled `mixed`
#   site 2  `þr`/`þeir`              - C corroborates B      -> settled `B+C`
#   site 3  `Nafne`/`Napne`          - C differs from BOTH   -> adjudicable
KEY = (10, 17)
A = {KEY: u"Enn þr sagde Herra vm þr i Nafne"}
B = {KEY: u"Enn þeir fagde Herra vm þeir i Napne"}
C = {KEY: u"Enn þeir sagde Herra vm þeir i Nafnne"}

FAIL = []


def check(name, cond, detail=""):
    print(("  [ok] " if cond else "  [X]  ") + name + (("  - " + detail) if detail else ""))
    if not cond:
        FAIL.append(name)


def main():
    import thorlaks_adjudicate_merge as am

    print("1 · the two-read path is UNCHANGED (no --c)")
    two = am.sites(A, B)
    check("every site carries majority=None", all(s["majority"] is None for s in two))
    check("every site carries c=None", all(s["c"] is None for s in two))
    n_adj_two = sum(1 for s in two if am.adjudicable(s))
    check("the two reads disagree at 3 sites", n_adj_two == 3,
          "got %d" % n_adj_two)

    print("2 · WITH a third read, 2-of-3 sites are settled in code")
    three = am.sites(A, B, C)
    settled = [s for s in three if s["majority"] is not None]
    n_adj_three = sum(1 for s in three if am.adjudicable(s))
    votes = sorted(s["vote"] for s in settled)
    check("2 site(s) settled", len(settled) == 2, "got %d" % len(settled))
    check("one B+C and one position-wise `mixed`", votes == ["B+C", "mixed"],
          "got %s" % votes)
    check("the third site is STILL adjudicable", n_adj_three == 1,
          "got %d" % n_adj_three)
    got = sorted(s["majority"] for s in settled)
    check("the majority wording is the corroborated one",
          got == sorted([u"þeir sagde", u"þeir"]), "got %s" % got)
    check("a settled site is never adjudicable",
          not any(am.adjudicable(s) for s in settled))
    check("the unsettled site carries C's own reading",
          [s["c"] for s in three if am.adjudicable(s)] == [u"Nafnne"])

    print("3 · KNOWN-BAD CONTROL: HEXAPLA_NO_VOTE=1 puts them all back")
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_test_novote_probe.py")
    io.open(src, "w", encoding="utf-8", newline="\n").write(
        u"import os, sys\n"
        u"sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
        u"import thorlaks_adjudicate_merge as am\n"
        u"A = {(10, 17): %r}\n" % A[KEY] +
        u"B = {(10, 17): %r}\n" % B[KEY] +
        u"C = {(10, 17): %r}\n" % C[KEY] +
        u"s = am.sites(A, B, C)\n"
        u"print(sum(1 for x in s if am.adjudicable(x)),\n"
        u"      sum(1 for x in s if x['majority'] is not None))\n")
    try:
        env = dict(os.environ, HEXAPLA_NO_VOTE="1", PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([sys.executable, src], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        out = out.decode("utf-8", "replace").strip()
        check("the probe ran", p.returncode == 0,
              err.decode("utf-8", "replace").strip()[:200])
        if p.returncode == 0:
            adj, maj = (int(x) for x in out.split())
            check("adjudicable RISES to the two-read count with the vote off",
                  adj == n_adj_two and adj > n_adj_three,
                  "off=%d on=%d two-read=%d" % (adj, n_adj_three, n_adj_two))
            check("nothing is settled with the vote off", maj == 0,
                  "got %d" % maj)
    finally:
        if os.path.exists(src):
            os.remove(src)

    print("")
    if FAIL:
        print(u"[X] %d control(s) did NOT fire: %s" % (len(FAIL), "; ".join(FAIL)))
        sys.exit(1)
    print(u"★ every control fired - the 2-of-3 vote is doing what it reports.")
    sys.exit(0)


if __name__ == "__main__":
    main()
