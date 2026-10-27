# -*- coding: utf-8 -*-
"""Control, BOTH WAYS, for F2 (read-B `[HN]` default drops read A's bracket).

    python tools/test_hn_rebracket.py                        # rc 0 = rule works
    HEXAPLA_NO_HNREBRACKET=1 python tools/test_hn_rebracket.py  # rc 0 = known-bad fires

Advisor ruling 2026-10-09 (`gen_p22_rule/ADVISOR_RULING.md` §2 F2): A «[HN]ott»
vs B «Nott» (Gen 8:22) must write the bracket; A «[HN]anda» vs B lowercase
«handa» (8:19) is a case dispute and must NOT. Checked on the real p22 reads
(the non-adjudicable sites' default) and on literal pairs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_adjudicate_merge as am

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

OFF = os.environ.get("HEXAPLA_NO_HNREBRACKET") == "1"
W = "C:/Projects/Hexapla-releases/_work"
fails = 0


def check(label, got, want):
    global fails
    ok = got == want
    fails += not ok
    print("%s %s: got %r want %r" % ("ok  " if ok else "FAIL", label, got, want))


# literal pairs: (A, B) -> expected with fix / with switch off (None = fallback)
for a, b, want in (("[HN]ott.", "Nott.", "[HN]ott."),
                   ("[HN]er", "Her", "[HN]er"),
                   ("[HN]anda", "handa", None),
                   ("[HN]ott", "Pott", None),
                   ("Nott", "[HN]ott", None),
                   ("[HN]ott sa", "Nott sa", "[HN]ott sa")):
    check("pair %s/%s" % (a, b), am.hn_rebracket(a, b), None if OFF else want)

# real p22 reads: which one-word non-adjudicable sites does the rule rebracket?
a, _ = am.verses_with_addr("%s/genesis_p22_readA_2026-10-09.md" % W, 8)
b, _ = am.verses_with_addr("%s/genesis_p22_readB_2026-10-09.md" % W, 8)
got = {}
for s in am.sites(a, b):
    if s["tag"] != "equal" and not am.adjudicable(s):
        r = am.hn_rebracket(s["a"] or "", s["b"] or "")
        if r:
            got[(s["chapter"], s["verse"])] = r
print("p22 ch8 rebracketed:", got)
check("p22 8:22 rebracketed", (8, 22) in got, not OFF)
check("p22 8:19 not rebracketed", (8, 19) in got, False)
print("%s (%s)" % ("PASS" if not fails else "FAIL",
                   "off switch: nothing rebracketed" if OFF else "fixed"))
sys.exit(1 if fails else 0)
