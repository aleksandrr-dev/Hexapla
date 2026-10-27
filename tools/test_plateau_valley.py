"""Control for the PLATEAU branch of prep_chunk.split_tall_runs() - both ways, real scans.

Genesis v1 idx 48 is a plateau page (frac 0.65, 44 runs) whose six tall runs hold
nine printed lines welded in pairs and threes; the valleys inside them are deep
(0.08-0.139) where the cliff class is shallow (<= 0.058). The depth-gated plateau
cut must recover exactly those nine rows and must move NOTHING on plateau
neighbours idx 18 and idx 49 (measured 2026-10-19, evidence in
research/_evidence/thorlaks_p48_plateau_valley_2026-10-19.md).

    python tools/test_plateau_valley.py                              -> 0 when the rule holds
    HEXAPLA_NO_PLATEAU_VALLEY=1 python tools/test_plateau_valley.py  -> 1 (known-bad)

The cliff page's own control stays tools/test_valley_split.py (idx 66 = 49 either way).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prep_chunk as pc  # noqa: E402
import fitz  # noqa: E402

VOL = 1
PAGE, RUNS_BEFORE, RUNS_AFTER = 48, 44, 53
PLATEAU = {18: 51, 49: 55}   # measured 2026-10-19 before the edit


def runs_for(doc, idx):
    page = doc[idx]
    block, _ = pc.text_block(page)
    return len(pc.line_rects(page, block))


def main():
    doc = fitz.open(pc.RESEARCH / f"thorlaks_v{VOL}.pdf")
    fails = []
    got = runs_for(doc, PAGE)
    print(f"v{VOL} idx {PAGE}: {got} runs (want {RUNS_AFTER}; {RUNS_BEFORE} is the unsplit plateau)")
    if got != RUNS_AFTER:
        fails.append(f"idx {PAGE} = {got}, not {RUNS_AFTER}")
    for idx, want in PLATEAU.items():
        got = runs_for(doc, idx)
        print(f"v{VOL} idx {idx}: {got} runs (want {want}, plateau neighbour, untouched)")
        if got != want:
            fails.append(f"idx {idx} moved to {got} from {want}")
    if fails:
        print("FAIL: " + "; ".join(fails))
        return 1
    print("ok: plateau valley recovers idx 48 and leaves idx 18 / 49 untouched"
          + (" [HEXAPLA_NO_PLATEAU_VALLEY set - this line must NOT print]"
             if os.environ.get("HEXAPLA_NO_PLATEAU_VALLEY") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
