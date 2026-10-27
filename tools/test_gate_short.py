# -*- coding: utf-8 -*-
"""Control for qa_gate's SHORT-TAKE screen (added 2026-09-25).

    python tools/test_gate_short.py                    # 0 = the screen fires
    HEXAPLA_NO_SHORT=1 python tools/test_gate_short.py # must exit 1

Known-bad: the take installed as «clean» on ylt Matthew 23:8 at 2026-09-25
11:56 - 6926 -> 1405 ms, the ASR heard «and yay». Its transcript is in that
chapter's qa.json repair record, so this control needs no audio and no GPU.
Known-good: the same verse heard in full, and heard with a few words
mis-transcribed, must NOT fire. The false-positive rate on real audio is
measured by `qa_gate.py --validate`, which now counts «short» as a firing.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from qa_gate import gate_reasons, norm_ref  # noqa: E402

WANT = ("And ye, ye may not be called Rabbeye, for one is your director - the "
        "Christ, and all ye are brethren;")


def shorts(heard):
    return [r for r in gate_reasons(heard, norm_ref(heard), WANT, "ylt")
            if r.startswith("short")]


def main():
    bad = shorts("and yay")
    full = shorts(" ".join(norm_ref(WANT)))
    misheard = shorts("and ye ye may not be called rabbi for one is your "
                      "detector the christ and all ye are brother")
    print(f"known-bad «and yay»: {bad or 'SILENT'}")
    print(f"full take:           {full or 'silent'}")
    print(f"misheard full take:  {misheard or 'silent'}")
    ok = bool(bad) and not full and not misheard
    print("PASS - the short-take screen fires on the known-bad take only"
          if ok else "FAIL - the screen did not separate the controls")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
