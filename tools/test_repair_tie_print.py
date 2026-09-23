# -*- coding: utf-8 -*-
"""CONTROL: does the repair tie-rule consult the PRINT before calling a tie?

    python tools/test_repair_tie_print.py            # must exit 0
    HEXAPLA_NO_TIEPRINT=1 python tools/test_repair_tie_print.py   # must exit 1

## What this guards

`repair_verses.py` refuses to install a draw when every draw carries the SAME
gate reason set — the gate cannot choose, and a coin toss against shipped audio
is a one-way bet (ylt Genesis 13:14, 2026-09-05).

That rule computed the tie AMONG THE DRAWS ONLY. When the reason they share is
the gate firing on SCRIPTURE, the draws are clean and there is no tie — but the
rule still kept the incumbent, even when the incumbent's own record was worse.

▶ MEASURED: kjv Numbers 5:22 (3/4 v22), 2026-09-15. The verse ends «Amen,
  amen.», so all three draws were gated `repeat:k1`. The incumbent's gate record
  said `append:a`, tail «…amen amen a». The defective take was kept.
  ★ THE OWNER CONFIRMED THE STRAY «a» BY EAR, 2026-09-15 — this is not a model's
  reading of a JSON field. That ear ruling is what makes v22 a POSITIVE CONTROL.

## ⛔ CHECK THE CHECKER — IT MUST FAIL IN BOTH DIRECTIONS

Both controls are real verses with real measured gate records:

  ctl+  kjv Numbers 5:22   print repeats («Amen, amen.»)     -> draws are CLEAN,
        so the tie must NOT fire and the new take must be installed.
  ctl-  ylt Genesis 13:14  print does NOT repeat              -> the tie MUST
        still fire and the shipped take MUST stay protected.

⚠⚠ The ctl- is the one with teeth. It is the case the tie-rule was WRITTEN for.
A change that makes the ctl+ pass by disabling the tie-rule outright would move
the ctl- too — so if the ctl- number is unchanged, the change could not have
been a blanket disable. ⛔ Never remove the ctl- to make a run pass.

⚠ This tests the DECISION, not the audio. It asserts nothing about whether any
particular draw sounds correct; only an ear does that.
"""
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import qa_text_explained
import repair_verses

BROKEN = os.environ.get("HEXAPLA_NO_TIEPRINT") == "1"

# The two verses, read from the SHIPPED assets — not pasted here, so a change to
# the text is a change to the control.
CASES = [
    # (label, set_key, book, chapter, verse, draw_reasons, expect_tie_fires)
    ("ctl+ kjv Numbers 5:22", "kjv", 3, 4, 22, ["repeat:k1"], False),
    ("ctl- ylt Genesis 13:14", "ylt", 0, 12, 14, ["repeat:k2"], True),
]


def tie_fires(text, draw_reasons):
    """Replay repair_verses' blindness decision for 3 identical draws."""
    if BROKEN:
        # The pre-2026-09-15 behaviour: the print is never consulted.
        explained = False
    else:
        explained = repair_verses.text_explained_repeats(text)
    reasons = repair_verses.effective_reasons(draw_reasons, explained)
    atts = [{"reasons": list(draw_reasons)} for _ in range(3)]
    sigs = {tuple(sorted(repair_verses.effective_reasons(a["reasons"], explained)))
            for a in atts}
    return bool(len(atts) >= 2 and len(sigs) == 1
                and next(iter(sigs), ()) and bool(reasons))


def main():
    if BROKEN:
        print("⚠ HEXAPLA_NO_TIEPRINT=1 — replaying the PRE-FIX behaviour; "
              "this run MUST fail.\n")
    bad = 0
    for label, set_key, b, c, v, draws, expect in CASES:
        books = qa_text_explained.load(set_key)
        text = qa_text_explained.vtext(books, b, c, v)
        if not text:
            print(f"⛔ {label}: verse text not found — a control that cannot "
                  f"run has NOT passed")
            return -1
        got = tie_fires(text, draws)
        ok = (got == expect)
        bad += (not ok)
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
        print(f"        draws={'|'.join(draws)}  print-repeats="
              f"{repair_verses.text_explained_repeats(text)}")
        print(f"        tie fires: {got}   expected: {expect}"
              f"   -> {'KEEP incumbent' if got else 'INSTALL new take'}")
        print(f"        text: {text[:88]}...")
    print()
    if bad:
        print(f"⛔ {bad} of {len(CASES)} control(s) wrong — the tie-rule's "
              f"verdicts must not be used.")
        return 1
    print("✅ controls pass: the print clears a scripture-repeat and does NOT "
          "clear an ordinary one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
