# -*- coding: utf-8 -*-
"""Control, BOTH WAYS, for the multi-word span sites in the adjudication brief.

    python tools/test_span_brief.py                     # rc 0 = the rule works
    HEXAPLA_NO_SPANBRIEF=1 python tools/test_span_brief.py   # rc 0 = the
                                                        # known-bad control fires

## What is under test

`adjudicable()` drops a whole `replace` span because of ONE token in it (an
`[HN]` capital, a drop-cap, notation). `SequenceMatcher` emits ONE opcode when
two ADJACENT words both differ, so a content dispute rides out of adjudication
attached to a settled token and the merge hands the entire span to read B -
with no verdict, no vote, and no line in the merge's `[X] N site(s) with NO
verdict` gate, because a site never briefed has no verdict to be missing.

`thorlaks_adjudicate_brief.brief_sites()` now ALSO briefs those spans. This
file asserts:

  1. the span IS briefed, and the single-word `[HN]` site beside it is NOT
     (that one really is settled by the conventions);
  2. `need` - what the merge DEMANDS a verdict for - is UNCHANGED by the fix,
     so site derivation did not move and every existing verdict file still
     keys against the same sites;
  3. with `HEXAPLA_NO_SPANBRIEF=1` the span goes unbriefed again, i.e. the
     control can actually distinguish the fixed tool from the broken one.

⛔ A screen that cannot be shown to fail has not been shown to pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_adjudicate_merge as am
import thorlaks_adjudicate_brief as ab

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

OFF = os.environ.get("HEXAPLA_NO_SPANBRIEF") == "1"

# The Luke idx 63 shape, from the evidence file: two adjacent words differ, one
# of them carries [HN], so the pair leaves adjudication as a single span.
A = {
    (9, 18): u"[HN]ã sagde vid hana",        # long-s/f dispute, riding on [HN]
    (9, 19): u"og Herrann suarade",          # a plain one-word dispute
    (9, 20): u"[HN]ofn yðar",                # [HN] ALONE - settled by rule 3
    (9, 21): u"[under decorative initial «[O]»]",   # apparatus, no printed word
}
B = {
    (9, 18): u"[HN]nñ fagde vid hana",
    (9, 19): u"og Herrann suaradi",
    (9, 20): u"[HN]ofn yðar",
    (9, 21): u"[OG]",
}
# v20's two reads agree, so it produces no site at all; v18 is the span, v19 is
# an ordinary adjudicable site.


def main():
    all_s = am.sites(A, B)
    need, spans, brief = ab.brief_sites(all_s)

    def has(sites, verse):
        return any(s["verse"] == verse for s in sites)

    fail = 0

    # (2) derivation is untouched - the merge's demand set is the same either way
    if not (has(need, 19) and not has(need, 18)):
        print(u"⛔ `need` moved: v19 in need=%s, v18 in need=%s (want True/False)"
              % (has(need, 19), has(need, 18)))
        fail += 1
    else:
        print(u"ok  merge's demand set unchanged: v19 adjudicable, v18 not")

    # (1)/(3) the span itself
    briefed = has(brief, 18)
    if OFF:
        if briefed or spans:
            print(u"⛔ HEXAPLA_NO_SPANBRIEF=1 but the v18 span was still "
                  u"briefed (%d span(s)) - the control cannot tell the fixed "
                  u"tool from the broken one." % len(spans))
            fail += 1
        else:
            print(u"ok  KNOWN-BAD control fires: the v18 span goes unbriefed "
                  u"and would take read B's `fagde` unexamined")
    else:
        if not briefed:
            print(u"⛔ the v18 multi-word span was NOT briefed - the merge "
                  u"would settle `[HN]ã sagde` / `[HN]nñ fagde` by the read-B "
                  u"default, unexamined.")
            fail += 1
        else:
            print(u"ok  the v18 multi-word span IS briefed (%d span(s) total)"
                  % len(spans))
        # the ONE exclusion: a span that is all apparatus is not a reader's job
        if has(brief, 21):
            print(u"⛔ the v21 drop-cap span was briefed - that site carries no "
                  u"printed word and the conventions settle it.")
            fail += 1
        else:
            print(u"ok  the all-apparatus drop-cap span is NOT briefed")
        if ab.apparatus_only({"a": u"[HN][?]", "b": u"G hñ"}):
            print(u"⛔ `[HN][?]` / `G hñ` read as apparatus-only - B carries words")
            fail += 1
        else:
            print(u"ok  a span with words outside the brackets is not apparatus")
        # and the brief must be a SUPERSET of what the merge demands
        if not set(id(s) for s in need) <= set(id(s) for s in brief):
            print(u"⛔ the brief does not cover every site the merge demands")
            fail += 1
        else:
            print(u"ok  the brief covers every site the merge demands")

    if fail:
        print(u"\n⛔ SPAN-BRIEF CONTROL FAILED (%d)" % fail)
        return 1
    print(u"\n✅ span-brief control passes (%s)"
          % ("known-bad direction" if OFF else "the rule"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
