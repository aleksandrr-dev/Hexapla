# -*- coding: utf-8 -*-
"""Control, BOTH WAYS, for F2: one-word `[HN]` sites that differ in other letters.

    python tools/test_hn_brief.py                       # rc 0 = the rule works
    HEXAPLA_NO_HNBRIEF=1 python tools/test_hn_brief.py  # rc 0 = the known-bad
                                                        # control fires

Advisor ruling 2026-10-09 (`_work/_scratch/gen_p20_21_rule/ADVISOR_RULING.md`
§2 F2): `adjudicable()` drops any site with `[HN]` in it and `silent_defaults()`
only named MULTI-word spans, so five one-word disputes on Genesis p20/p21 went
to read B unasked. Fixed, `silent_defaults()` lists p20 6:4 and 6:9 and p21
7:11, 8:2 and 8:7; with the off switch it lists none of them. A pure H/N
disagreement (`[HN]u` vs `Nu`) is NOT listed either way - that is the 1584
witness tool's.

Runs from the data directory's real reads (C:/Projects/Hexapla-releases/_work).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_adjudicate_merge as am

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

OFF = os.environ.get("HEXAPLA_NO_HNBRIEF") == "1"
W = "C:/Projects/Hexapla-releases/_work"
PAGES = [("p20", 5, {(6, 4), (6, 9)}), ("p21", 7, {(7, 11), (8, 2), (8, 7)})]

fails = 0
for page, ch, want in PAGES:
    a, _ = am.verses_with_addr("%s/genesis_%s_readA_2026-10-08.md" % (W, page), ch)
    b, _ = am.verses_with_addr("%s/genesis_%s_readB_2026-10-08.md" % (W, page), ch)
    one_word = set()
    for s in am.silent_defaults(am.sites(a, b)):
        if len(s["a"].split()) <= 1 and len(s["b"].split()) <= 1:
            one_word.add((s["chapter"], s["verse"]))
            print("  %s %d:%d  A=%s  B=%s" % (page, s["chapter"], s["verse"],
                                             s["a"], s["b"]))
    if OFF:
        ok = not (want & one_word)
    else:
        ok = want <= one_word
    print("%s %s: want %s, listed %s"
          % ("ok  " if ok else "FAIL", page, sorted(want), sorted(one_word)))
    fails += not ok

# A pure H/N disagreement is never a content dispute.
pure = {"tag": "replace", "notation": False, "a": "[HN]u", "b": "Nu"}
if am.hn_content_dispute(pure):
    print("FAIL pure H/N site listed")
    fails += 1
print("%s (%s)" % ("PASS" if not fails else "FAIL",
                   "off switch: none listed" if OFF else "fixed: all listed"))
sys.exit(1 if fails else 0)
