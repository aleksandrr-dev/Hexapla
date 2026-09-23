# -*- coding: utf-8 -*-
"""Find verses where a repair DISCARDED a draw that looked better than the one it kept.

    python tools/qa_discarded_draws.py --set ylt
    python tools/qa_discarded_draws.py --set ylt --validate

0 model tokens, 0 GPU. It reads `<chapter>.qa.json` records that are already on
disk — every repair attempt's ASR tail was recorded at the time.

## Why this exists — ylt Genesis 13:14, found 2026-09-07

`repair_verses.py` redraws a failing verse up to 3x and keeps the first draw
that passes the gate. When NO draw passes, it keeps attempt 1. That is fine
when the gate can see the defect. It is NOT fine when the gate is blind to it:

    Genesis 13:14, 2026-09-05T20:20 — three attempts, ALL gated `repeat:k2`
      attempt 1  …and southward and westward and westward   <- KEPT
      attempt 2  …and southward and westward and westward
      attempt 3  …and southward and eastward and westward   <- CORRECT, discarded

«eastward» and «westward» are equally good repeats of the «-ward» pattern, so
the gate scored all three alike, the tie fell to attempt 1, and the shipped
audio says «westward» twice. The run BEFORE it had already produced a correct
take and this one overwrote it.

▶ So a redraw of a gate-blind verse is not merely futile — **it can replace a
good take with a bad one, and nothing reports it.**

## What this screen actually claims

It flags a verse when every attempt tied on the gate AND the discarded attempts'
tails DISAGREE with the kept one. That is a claim about **arbitrary selection**,
not about which take is right:

  ⛔ It CANNOT tell you the kept take is wrong. Only an ear can — the same rule
     that governs the substitution and mispronunciation classes.
  ⛔ Silence is NOT a clean bill. A verse where all draws were identically
     defective ties and agrees, so it is not flagged.

▶ Read a hit as: "the tool had no basis for the choice it made here, and the
alternatives were audibly different. Worth an ear."
"""
import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATA = Path(r"C:\Projects\Hexapla-releases")


def norm(t):
    return " ".join((t or "").lower().split())


def scan_record(rec):
    """-> (flagged, kept_tail, other_tails) for one repair record."""
    atts = rec.get("attempts") or []
    if len(atts) < 2:
        return False, None, []
    kept_i = rec.get("kept")
    if not isinstance(kept_i, int) or not (1 <= kept_i <= len(atts)):
        return False, None, []
    # Only interesting when the gate could not separate them: every attempt
    # carries the SAME reason set. If one passed, the choice was justified.
    sigs = {tuple(sorted(a.get("reasons") or [])) for a in atts}
    if len(sigs) != 1:
        return False, None, []
    if not next(iter(sigs)):          # all clean -> nothing was failing
        return False, None, []
    kept = norm(atts[kept_i - 1].get("tail"))
    others = [norm(a.get("tail")) for i, a in enumerate(atts, 1) if i != kept_i]
    differing = [t for t in others if t and t != kept]
    return bool(differing), kept, differing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--validate", action="store_true",
                    help="run the controls and exit non-zero if one fails")
    a = ap.parse_args()

    if a.validate:
        # ⚠ A NEW SCREEN IS BROKEN UNTIL A CONTROL FIRES. Two positives and
        # two negatives, so neither over- nor under-reporting passes silently.
        cases = [
            ("POSITIVE the real Genesis 13:14 shape", True, {
                "kept": 1, "attempts": [
                    {"reasons": ["repeat:k2"], "tail": "and southward and westward and westward"},
                    {"reasons": ["repeat:k2"], "tail": "and southward and westward and westward"},
                    {"reasons": ["repeat:k2"], "tail": "and southward and eastward and westward"}]}),
            ("POSITIVE kept take differs from a later one", True, {
                "kept": 1, "attempts": [
                    {"reasons": ["repeat:k1"], "tail": "alpha beta"},
                    {"reasons": ["repeat:k1"], "tail": "alpha gamma"}]}),
            ("NEGATIVE all draws identical -> no arbitrary choice", False, {
                "kept": 1, "attempts": [
                    {"reasons": ["repeat:k2"], "tail": "same tail here"},
                    {"reasons": ["repeat:k2"], "tail": "same tail here"}]}),
            ("NEGATIVE a draw actually PASSED -> choice was justified", False, {
                "kept": 2, "attempts": [
                    {"reasons": ["repeat:k2"], "tail": "bad tail"},
                    {"reasons": [], "tail": "good tail"}]}),
        ]
        ok = True
        for name, want, rec in cases:
            got = scan_record(rec)[0]
            print(f"  {'✅' if got == want else '⛔'} {name}: "
                  f"expected {want}, got {got}")
            ok &= (got == want)
        print("\n✅ controls pass" if ok else "\n⛔ CONTROLS FAILED — do not use it")
        return 0 if ok else 1

    root = DATA / "narration" / a.set_key
    files = sorted(glob.glob(str(root / "*" / "*.qa.json")))
    if not files:
        print(f"⛔ no .qa.json under {root} — REFUSING to report a clean result "
              f"over a denominator of zero")
        return 2

    hits, recs, skipped = [], 0, Counter()
    for f in files:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            skipped[type(e).__name__] += 1
            continue
        if "repairs" not in d:            # narrate.py's gate schema — no attempts
            skipped["not-a-repair-record"] += 1
            continue
        book, chap = Path(f).parent.name, Path(f).name.split(".")[0]
        for rec in d["repairs"]:
            recs += 1
            flagged, kept, others = scan_record(rec)
            if flagged:
                hits.append((book, chap, rec.get("verse"), kept, others))

    print(f"{a.set_key}: {len(files)} qa file(s), {recs} repair record(s) read")
    for k, v in skipped.items():
        print(f"   skipped {v} ({k})")
    print(f"\n{len(hits)} verse(s) where the gate could not separate the draws "
          f"and a DISCARDED draw differed from the kept one:\n")
    for book, chap, v, kept, others in hits:
        print(f"  {book}/{chap} v{v}")
        print(f"     kept      : …{kept}")
        for o in others:
            print(f"     discarded : …{o}")
    print("\n⚠ A hit says the CHOICE WAS ARBITRARY, not that the kept take is "
          "wrong — only an ear can say that.")
    print("⛔ And silence is not a clean bill: a verse whose draws were all "
          "identically defective ties AND agrees, so it is never flagged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
