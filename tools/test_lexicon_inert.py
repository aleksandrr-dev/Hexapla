#!/usr/bin/env python
"""Control, BOTH WAYS, for «an unvalidated lexicon row is INERT» (2026-09-21).

    python tools/test_lexicon_inert.py             -> exit 0
    HEXAPLA_NO_INERT=1 python tools/...            -> exit 1 (known-bad fires)

THE BUG THIS PINS
-----------------
`narrate.py` (~2151) documents "Both tables are INERT while a row is
unvalidated" and `synthesis_overrides.py` (~117) implements it. THIS table did
not: `rows_for()` filtered on scope alone, so a candidate respelling written
down for an ear test was LIVE - the next render or repair touching a verse with
that word would have spoken an unheard guess into shipped audio.

It had never bitten only because `unvalidated()` was empty. The workflow this
table exists for - propose a spelling, render it, ask the owner - creates
exactly the condition that triggers it.

WHAT IS ASSERTED
----------------
1. INERT:      an unvalidated row does NOT change synthesis text.
2. NO-REGRESS: a validated row in scope still DOES.
3. TESTABLE:   `include_unvalidated=True` still applies it, or
               `lexicon_test_render.py` could never validate anything.
4. SCOPE KEPT: a validated row out of scope still does nothing.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pronounce_lexicon as pl  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BROKEN = os.environ.get("HEXAPLA_NO_INERT") == "1"

if BROKEN:
    # Restore the pre-2026-09-21 behaviour exactly: scope only, no validated test.
    pl.rows_for = lambda set_key, include_unvalidated=False: {
        w: e for w, e in pl.LEXICON.items() if set_key in pl.row_sets(e)
    }


def main():
    fails = []
    pl.LEXICON["zzunvalidated"] = ("Zzcandidate", "probe", None, ("en",))
    pl.LEXICON["zzvalidated"] = ("Zzcleared", "probe", "probe ear", ("en",))
    pl.LEXICON["zzoutofscope"] = ("Zzelsewhere", "probe", "probe ear", ("ylt",))

    # 1. INERT
    out, hits = pl.apply("a zzunvalidated word", set_key="en")
    if hits:
        fails.append("INERT: an UNVALIDATED row was applied -> %r" % out)
    else:
        print("  ✅ INERT        unvalidated row did not fire")

    # 2. NO-REGRESS
    out, hits = pl.apply("a zzvalidated word", set_key="en")
    if not hits:
        fails.append("NO-REGRESS: a VALIDATED in-scope row stopped firing -> %r" % out)
    else:
        print("  ✅ NO-REGRESS   validated row still fires (%r)" % out)

    # 3. TESTABLE
    out, hits = pl.apply("a zzunvalidated word", set_key="en",
                         include_unvalidated=True)
    if not hits:
        fails.append("TESTABLE: include_unvalidated=True did NOT apply the row - "
                     "lexicon_test_render could never validate a proposal")
    else:
        print("  ✅ TESTABLE     opt-in still applies it (%r)" % out)

    # 4. SCOPE KEPT
    out, hits = pl.apply("a zzoutofscope word", set_key="en")
    if hits:
        fails.append("SCOPE KEPT: an out-of-scope row fired -> %r" % out)
    else:
        print("  ✅ SCOPE KEPT   out-of-scope row did not fire")

    if BROKEN:
        if fails:
            print("\nknown-bad control (HEXAPLA_NO_INERT=1): reproduced, as it must")
            for f in fails:
                print("    " + f)
            return 1
        print("\n⛔ known-bad control did NOT reproduce - the control is broken")
        return 1

    if fails:
        print("\n⛔ FAIL")
        for f in fails:
            print("    " + f)
        return 1
    print("\nlexicon inert: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
