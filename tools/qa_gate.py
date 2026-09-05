# -*- coding: utf-8 -*-
"""The verse gate: every EAR-VALIDATED tail-defect screen, as one function.

    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\qa_gate.py --validate
    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\qa_gate.py --validate-sv

`narrate.py` calls `gate_reasons()` on every verse WHILE IT IS STILL A WAV IN
HAND and re-draws the verse if anything fires; `repair_verses.py` does the same
for a verse being spliced into a shipped chapter. Both used to happen days
later, per chapter, with a 16-hour sweep in between (RENDER_GATE_BRIEF
2026-09-03 in Hexapla-releases has the numbers).

## What is in here, and where each piece was validated

- `tail_repeat`  — imported from `qa_selfrepeat`, NOT copied. The transcript's
  tail repeats the tokens before it. Needs no reference text, so it works on a
  language whisper cannot read. 9/10 on the ear-confirmed ylt verses, 0/40 on
  controls; fires 6/6 on a synthetic Swedish positive control.
- `append_tail`  — the APPEND opcode test from `qa_asr_sweep`, byte-for-byte:
  a pure `insert` past every wanted word, consuming nothing. 10/10 by ear.
  English-reference sets only — on a text whisper cannot read (sv, wyc, cu)
  every verse would flag, which is noise, not a screen.
- `tail_peak`    — RECORD-ONLY unless a limit is passed. The peak after the
  last aligned word is the metric that separated the owner's "garbled tail"
  verdicts (peak ≥ ~0.75) once rms was shown to track nothing, but that was
  measured on loudnormed chapter audio and the render-time WAV is not
  loudnormed. Calibrate against `_work/*_tail_loudness_all.csv` before turning
  it on (`HEXAPLA_GATE_TAIL_PEAK`).

## ⚠⚠ VALIDATE BEFORE TRUSTING — `--validate` (CLAUDE.md render-gate rule)

Two heuristics built for this defect looked reasonable and were wrong (a
duration cross-check, an audio self-similarity score). `--validate` runs the
whole render-time path — the persistent whisper worker in `.kokoro_venv`, the
token normalisation, this module — over the ten ear-confirmed ylt verses and
40 random controls, and refuses to endorse itself below 9/10 or above 1/40.
If it differs from `qa_selfrepeat.py --validate`, the WORKER's transcription
settings have drifted; fix that, do not retune FUZZ.

`--validate-sv` builds the synthetic Swedish positive control (six clean canon
verses with their own last ~1.4 s of SPEECH re-appended — trimmed to the last
loud sample first, or the splice appends silence and proves nothing) and
requires 6/6.
"""
import argparse
import difflib
import json
import random
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from qa_selfrepeat import tail_repeat, EAR_CONFIRMED_YLT, verse_wav  # noqa: E402

NAR = Path("C:/Projects/Hexapla-releases/narration")

# Sets whose TEXT whisper can read well enough for the APPEND test. wyc is
# Middle English and cu is Church Slavonic: no model reads them, and sv is
# 1703 Swedish (97.5 % of verses mismatch the reference — measured).
ENGLISH_TEXT_SETS = {"en", "ylt", "tyn", "wbt", "gnv"}


def norm_ref(s):
    """`qa_asr_verify.norm`, identical — the APPEND test was validated on it."""
    s = s.lower().replace("\u2014", " ").replace("\u2019", "'").replace("`", "")
    s = re.sub(r"[^a-z' ]+", " ", s)
    return [w for w in s.split() if w]


def append_tail(want, heard):
    """Words the ASR heard AFTER every wanted word, consuming nothing from
    `want`. ⚠ IDENTICAL to qa_asr_sweep — a prefix test was tried there and
    is WEAKER (misses a tail whenever an earlier word also differs)."""
    if not want or not heard:
        return []
    sm = difflib.SequenceMatcher(None, want, heard)
    ops = sm.get_opcodes()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "insert" and i1 >= len(want) and j2 == len(heard):
            return heard[j1:j2]
    # ⚠⚠ A TRAILING `replace` HIDES AN APPEND — measured false negative,
    # 2026-09-04. ylt 12/3 v24 was re-drawn, the gate PASSED it, and the owner
    # still heard the stray "sh". The transcripts:
    #     attempt 1  «...zerah shaul SHOP»  -> pure insert, flagged correctly
    #     attempt 2  «...zera  shawl SHRI»  -> PASSED
    # In attempt 2 the ASR also mistranscribed the LAST WANTED WORD
    # (shaul -> shawl), so difflib emitted one `replace` of ['shaul'] into
    # ['shawl','shri'] instead of a match plus a trailing insert. The extra word
    # was swallowed inside the replace and the pure-insert test never ran.
    # The docstring above already warns that a prefix test misses a tail when an
    # EARLIER word differs; this is the same blind spot from the other end.
    # ▶ So also read the excess out of a FINAL replace, but only when the words
    #   that DO line up actually resemble their counterparts — otherwise a
    #   wholly misheard ending would be reported as appended speech.
    if ops:
        tag, i1, i2, j1, j2 = ops[-1]
        if tag == "replace" and i2 == len(want) and j2 == len(heard):
            n_want, n_heard = i2 - i1, j2 - j1
            if n_heard > n_want:
                aligned_ok = all(
                    difflib.SequenceMatcher(None, want[i1 + n], heard[j1 + n]
                                            ).ratio() >= 0.55
                    for n in range(n_want))
                if aligned_ok:
                    return heard[j1 + n_want:j2]
    return []


def gate_reasons(heard_text, tokens, want_text, lang,
                 tail_peak=None, tail_peak_limit=None):
    """-> list of reasons the verse FAILS. Empty list = passed every screen
    that can run on this set. `tokens` is the worker's normalised token list;
    `heard_text` its raw transcript; `want_text` what the engine was fed."""
    reasons = []
    if tokens is None:
        return ["asr-unavailable"]      # visible, never a silent pass
    k = tail_repeat(tokens)
    if k >= 1:
        reasons.append(f"repeat:k{k}")
    if lang in ENGLISH_TEXT_SETS and want_text:
        extra = append_tail(norm_ref(want_text), norm_ref(heard_text or ""))
        if extra:
            reasons.append("append:" + " ".join(extra))
    if tail_peak is not None and tail_peak_limit is not None \
            and tail_peak >= tail_peak_limit:
        reasons.append(f"tailpeak:{tail_peak:.2f}")
    return reasons


def _spoken(lang, b, ch, v):
    import narrate
    books = narrate.load_bible(lang)
    raw = books[b]["chapters"][ch][v - 1]
    cfg = narrate.LANG_CONFIG[lang]
    if cfg["strip_notes"]:
        raw = narrate.strip_kjv_notes(raw)
    if cfg["normalizer"]:
        raw = narrate.normalize_text(raw, cfg["normalizer"])
    return raw


def _judge(lang, items, td, show, prefer_originals=False):
    """Run the RENDER-TIME path (worker + gate) over chapter-cut verses."""
    import narrate
    hits = 0
    for b, ch, v in items:
        w = verse_wav(lang, b, ch, v, td, prefer_originals)
        if w is None:
            print(f"  {b}/{ch} v{v}: cannot cut (missing or < 1.5 s)")
            continue
        asr = narrate.asr_transcribe(str(w), narrate.ASR_LANG[lang])
        if asr is None:
            print(f"  {b}/{ch} v{v}: ASR UNAVAILABLE")
            continue
        reasons = gate_reasons(asr["text"], asr["tokens"], _spoken(lang, b, ch, v), lang)
        fired = any(r.startswith(("repeat", "append")) for r in reasons)
        hits += fired
        if show or fired:
            print(f"  {b}/{ch} v{v:<3} {'FAIL' if fired else 'pass'} "
                  f"{reasons}  ...{' '.join(asr['tokens'][-8:])}")
    return hits


def validate():
    random.seed(7)
    pool = []
    for b in (0, 1):
        for js in sorted((NAR / "ylt" / str(b)).glob("*.json")):
            if js.name.endswith((".w.json", ".eos.json", ".qa.json")):
                continue
            n = len(json.loads(js.read_text())["offsets"])
            pool += [(b, int(js.stem), v) for v in range(1, n + 1)
                     if (b, int(js.stem), v) not in EAR_CONFIRMED_YLT]
    controls = random.sample(pool, 40)
    with tempfile.TemporaryDirectory() as td:
        print("EAR-CONFIRMED ylt verses (want >= 9/10 FAIL):")
        # ⚠⚠ THE CONFIRMED VERSES MUST BE READ FROM THE PRE-REPAIR BACKUPS.
        # repair_verses.py overwrites narration/ylt, so after a repair the live
        # tree no longer holds the defect. Measured 2026-09-04: reading the live
        # tree scored these 0/10, which would have written an "ok": false stamp
        # -- condemning a working gate and blocking every future render.
        pos = _judge("ylt", EAR_CONFIRMED_YLT, td, show=True,
                     prefer_originals=True)
        print("\nrandom ylt controls (want <= 1/40 FAIL):")
        neg = _judge("ylt", controls, td, show=False)
    print(f"\nSUMMARY  confirmed {pos}/10   controls {neg}/40")
    ok = pos >= 9 and neg <= 1
    print("VERDICT: " + ("VALIDATED — the render-time gate reproduces the "
                         "ear-confirmed screen" if ok else
                         "NOT VALIDATED — do not render or repair on this gate"))
    # The stamp render_preflight.py checks. It carries the mtimes of the code
    # it validated, so editing the gate or the worker invalidates it.
    import time
    stamp = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "confirmed": pos,
             "controls_flagged": neg, "ok": ok,
             "code_mtimes": {n: int((HERE / n).stat().st_mtime)
                             for n in ("qa_gate.py", "_asr_worker.py", "qa_selfrepeat.py")}}
    out = NAR.parent / "_work" / "gate_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stamp, indent=1), encoding="utf-8")
    print(f"stamp -> {out}")
    return 0 if ok else 1


# Which whisper model reads which set for the SELF-REPEAT screen.
# ⚠ THE ASR DOES NOT HAVE TO UNDERSTAND THE LANGUAGE. The self-repeat screen
# asks only whether the transcript's tail repeats the tokens before it, so the
# model needs to be DETERMINISTIC, not correct. That is why `cu` (Church
# Slavonic 1757) is screened with the RUSSIAN model: whisper has no Church
# Slavonic, but it transcribes cu audio phonetically and will emit the same
# wrong tokens twice when the audio says the same thing twice.
# ⚠ THAT IS A CLAIM, NOT A FACT, until the splice control below separates on
# the set itself. Do not screen a set whose control has not run.
SPLICE_ASR = {"sv": "sv", "ru": "ru", "cu": "ru"}
SPLICE_LABEL = {"sv": "Swedish", "ru": "Russian", "cu": "Church Slavonic"}


def validate_sv():
    return validate_splice("sv")


def validate_splice(set_key, asr_lang=None, books=(0, 18, 39)):
    """Synthetic positive control for the SELF-REPEAT screen, on any set.

    Splices a word-boundary repeat into verses that are presumed clean and
    checks the gate fires on the splice and stays silent on the original.
    That manufactures ground truth, which is the only way to validate a
    screen on a set with no ear-confirmed defects (ru, cu) or whose text the
    ASR cannot read (cu, sv).

    See handoff §3c: trim to the last loud sample BEFORE splicing, or the
    appended audio is concat padding and the control proves nothing."""
    asr_lang = asr_lang or SPLICE_ASR.get(set_key)
    label = SPLICE_LABEL.get(set_key, set_key)
    if not asr_lang:
        print(f"no ASR language mapped for set {set_key!r}")
        return 1
    import numpy as np
    import soundfile as sf
    import narrate
    random.seed(11)
    cands = []
    for b in books:
        for js in sorted((NAR / set_key / str(b)).glob("*.json")):
            if js.name.endswith((".w.json", ".eos.json", ".qa.json")):
                continue
            n = len(json.loads(js.read_text())["offsets"])
            cands += [(b, int(js.stem), v) for v in range(1, n + 1)]
    picks = random.sample(cands, 24)
    fired_clean = fired_spliced = n_done = 0
    with tempfile.TemporaryDirectory() as td:
        for b, ch, v in picks:
            if n_done == 6:
                break
            # ⚠ CONTROL-CONSTRUCTION TRAP (handoff §3c, and re-measured
            # 2026-09-03): a naive "last 1.4 s" splice scored 2/6 — it cuts
            # MID-WORD with no gap, so the ASR hears one garbled run, not a
            # phrase said twice. A real defect re-says WHOLE words after a
            # short gap. So the repeat is cut at WORD boundaries from the
            # chapter's own .w.json and joined with a 150 ms gap.
            wjs = NAR / set_key / str(b) / f"{ch}.w.json"
            side = NAR / set_key / str(b) / f"{ch}.json"
            if not wjs.exists():
                continue
            words = json.loads(wjs.read_text(encoding="utf-8"))["v"][v - 1]
            off = json.loads(side.read_text(encoding="utf-8"))["offsets"][v - 1]
            if not words or len(words) < 5:
                continue
            w = verse_wav(set_key, b, ch, v, td)
            if w is None:
                continue
            a, sr = sf.read(str(w), dtype="float32")
            a = a.mean(1) if a.ndim > 1 else a
            loud = np.nonzero(np.abs(a) > 0.02 * np.abs(a).max())[0]
            if not len(loud) or loud[-1] < sr * 2:
                continue
            a = a[:loud[-1] + 1]
            k = 3 if len(words) >= 6 else 2
            start = int((words[-k][0] - off) / 1000 * sr)
            if start <= 0 or start >= len(a) - sr // 4:
                continue
            tail = a[start:]
            gap = np.zeros(int(0.15 * sr), dtype="float32")
            spl = Path(td) / f"spl_{b}_{ch}_{v}.wav"
            sf.write(str(spl), np.concatenate([a, gap, tail]), sr)
            r0 = narrate.asr_transcribe(str(w), asr_lang)
            r1 = narrate.asr_transcribe(str(spl), asr_lang)
            if r0 is None or r1 is None:
                print(f"  {b}/{ch} v{v}: ASR UNAVAILABLE")
                continue
            g0 = [r for r in gate_reasons(r0["text"], r0["tokens"], "", set_key) if r.startswith("repeat")]
            g1 = [r for r in gate_reasons(r1["text"], r1["tokens"], "", set_key) if r.startswith("repeat")]
            n_done += 1
            fired_clean += bool(g0)
            fired_spliced += bool(g1)
            print(f"  {b}/{ch} v{v:<3} clean {g0 or 'pass':<14} spliced {g1 or 'MISS'}"
                  f"   ...{' '.join(r1['tokens'][-8:])}")
    print(f"\nSUMMARY  spliced {fired_spliced}/{n_done} fired   clean {fired_clean}/{n_done} fired")
    # ≥ 5/6, not 6/6: measured 2026-09-03, whisper occasionally REWRITES the
    # repeated words into different ones («…samma stunds högstadsbarn») and
    # then there is no repeat in the transcript to find. That is the same
    # recall limit the English validation shows at 9/10. 0 on the clean side
    # is required — a false positive costs a needless re-draw on every verse.
    ok = n_done == 6 and fired_spliced >= 5 and fired_clean == 0
    # ⚠ PRINT THE MEASURED RECALL, NEVER A LITERAL. This line said
    # "recall ≈ 5/6" unconditionally until 2026-09-03, which under-reported
    # cu's actual 6/6 — and anyone reading only the VERDICT line would have
    # carried the wrong figure into a handoff.
    print("VERDICT: " + (f"VALIDATED on {label} (recall {fired_spliced}/{n_done} "
                         "by this control; "
                         "a miss is a defect that survives — the post-render "
                         "screens still run)" if ok
                         else f"NOT VALIDATED on {label} — this set has NO "
                              "self-repeat screen. Report it as unscreened, "
                              "never as clean."))
    return 0 if ok else 1
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--validate-sv", action="store_true")
    ap.add_argument("--validate-splice", metavar="SET",
                    help="run the synthetic splice control on any set "
                         "(sv, ru, cu) — the only way to validate the "
                         "self-repeat screen without ear-confirmed defects")
    ap.add_argument("--asr-lang", help="override the whisper model language "
                                       "for --validate-splice")
    a = ap.parse_args()
    if a.validate:
        return validate()
    if a.validate_sv:
        return validate_sv()
    if a.validate_splice:
        return validate_splice(a.validate_splice, a.asr_lang)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
