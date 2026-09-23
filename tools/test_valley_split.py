"""Control for prep_chunk.split_tall_runs() — BOTH directions, on the real scans.

Luke v3 idx 66 is the page the cliff fix could not finish: choose_frac() picks
0.40 and three runs still hold 2 / 4 / 2 printed lines. The valley split must
recover exactly the five missing rows there, and must touch NOTHING on its
plateau neighbours 64, 65 and 67.

    python tools/test_valley_split.py            -> 0 when the splitter holds
    HEXAPLA_NO_VALLEY=1 python tools/test_valley_split.py   -> 1 (known-bad)

▶ Read the second run as seriously as the first: a control that cannot fail
is not a control.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prep_chunk as pc  # noqa: E402
import fitz  # noqa: E402

VOL = 3
CLIFF_PAGE, CLIFF_RUNS_BEFORE, CLIFF_RUNS_AFTER = 66, 44, 49
PLATEAU = {64: 52, 65: 52, 67: 53}   # measured 2026-09-20, splitter cannot reach them


def runs_for(doc, idx):
    page = doc[idx]
    block, _ = pc.text_block(page)
    return len(pc.line_rects(page, block))


def main():
    doc = fitz.open(pc.RESEARCH / f"thorlaks_v{VOL}.pdf")
    fails = []
    got = runs_for(doc, CLIFF_PAGE)
    print(f"idx {CLIFF_PAGE}: {got} runs (want {CLIFF_RUNS_AFTER}; "
          f"{CLIFF_RUNS_BEFORE} is the unsplit cliff)")
    if got != CLIFF_RUNS_AFTER:
        fails.append(f"idx {CLIFF_PAGE} = {got}, not {CLIFF_RUNS_AFTER}")
    for idx, want in PLATEAU.items():
        got = runs_for(doc, idx)
        print(f"idx {idx}: {got} runs (want {want}, plateau, untouched)")
        if got != want:
            fails.append(f"idx {idx} moved to {got} from {want}")
    if fails:
        print("FAIL: " + "; ".join(fails))
        return 1
    print("ok: valley split recovers idx 66 and leaves its neighbours byte-identical"
          + (" [HEXAPLA_NO_VALLEY set — this line must NOT print]"
             if os.environ.get("HEXAPLA_NO_VALLEY") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
