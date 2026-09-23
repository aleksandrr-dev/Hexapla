"""Control for the 2026-09-12 repace fix, run against narrate.py AS IT EXISTS.

Four cases, each with a KNOWN expected outcome. The one that matters is case 2:
a re-roll that is BETTER ON PACE but DIRTY must be refused. That is the defect
the owner heard on Genesis 19:18 and 30:21.
"""
import sys, types, tempfile, os
from pathlib import Path

sys.path.insert(0, r"C:\Projects\Hexapla\tools")
import narrate

TMP = tempfile.mkdtemp()
LANG = "en"
narrate.LANG_CONFIG[LANG] = dict(narrate.LANG_CONFIG.get(LANG, {}),
                                 engine="chatterbox", voice="_ref.wav")

# Chapter of 6 verses. Verse 0 is the outlier; the rest fix the median at ~10.0
VERSES = ["x" * 100] + ["y" * 100] * 5
NORMAL_DUR = 10000            # 100 chars / 10.0s = 10.0 ch/s  -> the median
OUTLIER_DUR = 25000           # 100 / 25.0 = 4.0 ch/s          -> far below band


def _mk(path):
    Path(path).write_bytes(b"\0" * 64)
    return True


def run(name, alt_plan, expect_swapped, expect_reasons):
    """alt_plan: list of (duration_ms, reasons|None) served to successive re-rolls."""
    state = {"n": 0}

    def fake_resynth(text, cfg, path):
        _mk(path)
        return True

    def fake_dur(path):
        p = str(path)
        if "_r" in p:
            return alt_plan[min(state["n"], len(alt_plan) - 1)][0]
        return OUTLIER_DUR

    def fake_judge(wav, text, lang, i):
        r = alt_plan[min(state["n"], len(alt_plan) - 1)][1]
        state["n"] += 1
        return r

    narrate.synthesize_chatterbox = fake_resynth
    narrate.get_wav_duration_ms = fake_dur
    narrate._judge_take = fake_judge
    narrate.EDGE_PAD_MS = 0

    pairs = [("verse_0000.wav", OUTLIER_DUR)] + [
        (f"verse_{i:04d}.wav", NORMAL_DUR) for i in range(1, 6)]
    gate_log = {i + 1: {"attempts": [{"attempt": 1, "reasons": []}], "kept": 1,
                        "reasons": []} for i in range(6)}

    out = narrate.repace_outliers(VERSES, pairs, LANG, TMP, None, gate_log)
    swapped = out[0][0] != "verse_0000.wav"
    reasons = gate_log[1].get("reasons")
    ok = (swapped == expect_swapped) and (reasons == expect_reasons)
    print(f"  {'PASS' if ok else '** FAIL **'}  {name}")
    print(f"        swapped={swapped} (expected {expect_swapped})  "
          f"reasons={reasons} (expected {expect_reasons})")
    print(f"        record: repaced={'repaced' in gate_log[1]} "
          f"declined={gate_log[1].get('repace_declined')}")
    return ok


print("CONTROLS for repace_outliers gate judging\n")
results = []

# 1. KNOWN POSITIVE - a clean alt with good pace must be ACCEPTED.
results.append(run("clean alt, pace in band -> ACCEPT",
                   [(10000, [])], True, []))

# 2. ★ KNOWN NEGATIVE - the actual bug. Alt has PERFECT pace but is DIRTY.
#    Pre-fix code accepted this purely on pace. It must now be refused.
results.append(run("dirty alt, PERFECT pace -> REJECT (the bug)",
                   [(10000, ["append:lord"]), (10000, ["append:lord"])],
                   False, []))

# 3. ASR unavailable -> cannot judge -> must keep the judged incumbent.
results.append(run("ASR down (None) -> keep incumbent",
                   [(10000, None)], False, []))

# 4. Alt clean but pace no better than incumbent -> tie/worse keeps incumbent.
results.append(run("clean alt, WORSE pace -> keep incumbent",
                   [(26000, [])], False, []))

print()
print("ALL CONTROLS PASSED" if all(results) else "** A CONTROL FAILED **")
sys.exit(0 if all(results) else 1)
