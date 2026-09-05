# -*- coding: utf-8 -*-
"""Detect a re-spoken verse tail from ASR SELF-REPETITION. Needs no reference text.

    tools\\.kokoro_venv\\Scripts\\python.exe tools/qa_selfrepeat.py --validate
    ... --lang sv --every 8 --out _work/sv_repeats.txt

## Why this one is different

Three detectors for this defect have been built and deleted: a duration
cross-check (disproved by ear on 4/4 controls), audio self-similarity (confirmed
1.000 vs random 0.999) and a forced-alignment hypothesis test (random verses
scored HIGHER than real defects). Each tried to compare audio against the
KNOWN TEXT, which is also why `qa_asr_sweep` cannot screen sv: whisper cannot
read Karl XII's 1703 Swedish, so 97.5 % of verses mismatch the reference.

**But the reference is not needed.** Look at what the ASR actually heard on the
ylt verses the owner confirmed by ear:

    "...servant to him TO HIM"
    "...face of jehovah JEHOVAH"
    "...and humbleth her AND HUMBLED HER"

The repetition is IN THE TRANSCRIPT. Whether whisper spelled the words correctly
is irrelevant - if the audio says a phrase twice, a deterministic ASR emits it
twice. So the test is: **does the tail of the transcript repeat the tokens
immediately before it?** That is language-independent and works on a set whose
text the ASR cannot read at all.

    score = longest k such that tokens[-k:] == tokens[-2k:-k]  (fuzzy)

⚠⚠ **VALIDATE FIRST — `--validate`.** It scores the ten ear-confirmed ylt verses
against random verses from the same books and refuses to endorse itself unless
they separate. Three predecessors looked reasonable and failed on real data.
⚠ It cannot see a NOVEL hallucination («saying suik») - that is not a repeat.
`qa_asr_sweep`'s APPEND covers those where the reference text is readable.
"""
import argparse
import difflib
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
NAR = Path("C:/Projects/Hexapla-releases/narration")
SR = 16000
MAX_K = 6
FUZZ = 0.85
# Per-token fallback thresholds (see tail_repeat). Chosen so the measured
# false negative fires, then CHECKED against the 40 controls — not tuned until
# something passed.
STRONG_TOKEN = 0.80        # a pair counts as "the same word" at/above this
MIN_STRONG_LEN = 4         # ...but only if one side is a substantial word
PAIR_JOINED_FLOOR = 0.70   # the span must still look broadly alike overall
# ⚠ MEASURED COST OF THE PER-TOKEN FALLBACK, 2026-09-04. It buys back two
# ear-confirmed FALSE NEGATIVES (ylt 19/30 v21 and, via qa_gate.append_tail,
# 12/3 v24 — both re-drawn, both PASSED by the old gate, both still wrong to the
# owner's ear). It costs ONE extra control flag in qa_gate --validate:
# 0/35 v29, «chief Lotan, chief Shobal, chief Zibeon, chief Anah», which repeats
# "chief" IN THE PRINTED TEXT. So the cost falls in the already-known
# TEXT-REPEAT class, and 10/10 + 1/40 still meets this gate's own criterion.
# ⛔ DO NOT RAISE THIS FLOOR TO 0.75 TO MAKE THAT CONTROL GO AWAY. The true
# positive scores 0.762 and that false positive 0.700; choosing a number
# between them is fitting the threshold to the validation set, which is how a
# detector is made to look good rather than made to work (see the failed
# acoustic-clustering attempt on `Jehovah`).
# ▶ The asymmetry is the point: a false POSITIVE costs someone a few seconds of
#   listening, a false NEGATIVE ships a defect and licenses calling a set clean.

ASR_LANG = {"ylt": "en", "tyn": "en", "wbt": "en", "gnv": "en", "wyc": "en",
            "en": "en", "sv": "sv", "ru": "ru",
            # cu = Church Slavonic 1757, screened with the RUSSIAN model.
            # whisper has no Church Slavonic, and it does not need one: this
            # screen asks only whether the transcript's tail repeats the
            # tokens before it, so the ASR must be DETERMINISTIC, not correct.
            # ⚠ Validated by the synthetic splice control, not by faith:
            #     qa_gate.py --validate-splice cu
            # If that control does not separate, cu has NO screen and must be
            # reported as unscreened, never as clean.
            "cu": "ru"}
EAR_CONFIRMED_YLT = [(0, 8, 26), (0, 18, 27), (0, 33, 2), (0, 35, 11),
                     (1, 4, 20), (1, 5, 11), (1, 33, 23), (1, 34, 11),
                     (1, 38, 33), (1, 39, 30)]


def verse_wav(lang, b, ch, v, td, prefer_originals=False):
    """Cut verse v to a 16 kHz mono wav. -> path or None.

    ⚠⚠ `prefer_originals` EXISTS BECAUSE THE REPAIR OVERWRITES THE GROUND TRUTH.
    `repair_verses.py` splices a fresh take into narration/<lang>/, so once a
    verse has been repaired the live tree no longer contains the defect the
    screen was validated on. Measured 2026-09-04: after the 280-verse ylt
    repair, `--validate` scored the ten ear-confirmed verses 0/10 and declared
    the detector unusable — it was reading REPAIRED audio. The pre-repair takes
    survive in narration/<lang>_qa_fail_originals/, and that is what validation
    must read.
    """
    root = NAR / lang
    if prefer_originals:
        orig = NAR / f"{lang}_qa_fail_originals" / str(b) / f"{ch}.ogg"
        if orig.exists() and orig.with_suffix(".json").exists():
            root = NAR / f"{lang}_qa_fail_originals"
    side, ogg = root / str(b) / f"{ch}.json", root / str(b) / f"{ch}.ogg"
    if not side.exists() or not ogg.exists():
        return None
    off = json.loads(side.read_text())["offsets"]
    i = v - 1
    if i >= len(off):
        return None
    s = off[i] / 1000
    if i + 1 < len(off):
        e = off[i + 1] / 1000
    else:
        import soundfile as sf
        e = sf.info(str(ogg)).duration
    if e - s < 1.5:
        return None
    w = Path(td) / f"{b}_{ch}_{v}.wav"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-to",
                        str(e), "-i", str(ogg), "-ac", "1", "-ar", str(SR),
                        str(w)], capture_output=True)
    return w if r.returncode == 0 else None


def tail_repeat(tokens):
    """Longest k where the last k tokens repeat the k before them (fuzzy)."""
    best = 0
    for k in range(1, MAX_K + 1):
        if len(tokens) < 2 * k:
            break
        a, b = tokens[-k:], tokens[-2 * k:-k]
        # ⚠⚠ COMPARE CHARACTERS, NOT TOKEN LISTS. The TTS often clips the
        # last word of the repeat, so the transcript reads
        # «its sockets ... its socket» or «kenaz ... kena». A token-list
        # comparison scores those 0.67 and 0.00 and MISSES them; measured, it
        # cost 2 of 3 misses in validation. Joined characters score ~0.96.
        joined = difflib.SequenceMatcher(None, "".join(a), "".join(b)).ratio()
        if joined >= FUZZ:
            best = k
            continue
        # ⚠⚠ PER-TOKEN FALLBACK — added 2026-09-04 after a MEASURED FALSE
        # NEGATIVE, the failure mode this project calls worse than no screen.
        # ylt 19/30 v21 (Proverbs 31:21) was re-drawn, the gate PASSED it, and
        # the owner's ear then heard "with scarlet" spoken twice. The gate's own
        # recorded transcript was «...clothed WAS scarlet WITH scarlet»: a real
        # doubling in which the ASR merely heard the first copy differently.
        # Joined-character scoring dilutes one wrong word across the whole span
        # (k=2 scored 0.762 against FUZZ 0.85) and the verse passed.
        # ▶ So ALSO accept a span whose tokens each match their counterpart
        #   individually. A single mistranscribed word can no longer hide a
        #   repeat, while every token still has to line up one-for-one.
        # ⚠ FIRST ATTEMPT AT THIS TEST REQUIRED EVERY TOKEN TO MATCH AND STILL
        #   MISSED THE CASE IT WAS BUILT FOR. Measured: «was» vs «with» scores
        #   0.286 — short words score badly however similar they sound — so an
        #   all-tokens rule needed a threshold so low it would fire on anything.
        # ▶ The real signal is that the LONG, distinctive token repeats exactly
        #   («scarlet» == «scarlet») while a short function word differs. So
        #   require a MAJORITY of the span's pairs to match strongly, and only
        #   count a pair as strong if at least one side is a substantial word —
        #   otherwise «and»/«the» pairs could carry the whole decision.
        # ⚠ k >= 2 only: at k=1 there is no majority to take and nothing to
        #   corroborate a single short word against.
        strong = sum(1 for x, y in zip(b, a)
                     if max(len(x), len(y)) >= MIN_STRONG_LEN
                     and difflib.SequenceMatcher(None, x, y).ratio() >= STRONG_TOKEN)
        if k >= 2 and joined >= PAIR_JOINED_FLOOR and strong >= (k + 1) // 2:
            best = k
    return best


def score_set(model, lang, items, asr_lang, show=False, progress=False,
              prefer_originals=False):
    out = []
    with tempfile.TemporaryDirectory() as td:
        for b, ch, v in items:
            w = verse_wav(lang, b, ch, v, td, prefer_originals)
            if w is None:
                continue
            segs, _ = model.transcribe(str(w), language=asr_lang, beam_size=5,
                                       vad_filter=False,
                                       condition_on_previous_text=False,
                                       hallucination_silence_threshold=0.5)
            txt = " ".join(s.text for s in segs).lower()
            toks = [t for t in "".join(c if c.isalnum() or c.isspace() else " "
                                       for c in txt).split() if t]
            k = tail_repeat(toks)
            out.append((k, b, ch, v, " ".join(toks[-10:])))
            if show:
                print(f"  {b}/{ch} v{v:<3} k={k}   ...{' '.join(toks[-9:])}",
                      flush=True)
            elif progress:
                # WARNING EMIT AS YOU GO. This used to accumulate silently and print
                # only at the end, so a 3-hour run produced an EMPTY log and any
                # progress check on it read "0 repeats found" - which is not a
                # clean result, it is no result. A long-running check must be
                # able to say how far it has got.
                n = len(out)
                if k >= 1:
                    print(f"  REPEAT {b}/{ch} v{v}  k={k}  ...{' '.join(toks[-8:])}",
                          flush=True)
                if n % 100 == 0:
                    print(f"[progress] {n} verses scored, "
                          f"{sum(1 for r in out if r[0] >= 1)} repeat(s)", flush=True)
    return out


def iter_verses(lang, every):
    root = NAR / lang
    for bd in sorted((d for d in root.iterdir() if d.is_dir() and d.name.isdigit()),
                     key=lambda d: int(d.name)):
        for ch in sorted(int(p.stem) for p in bd.glob("*.ogg"))[::every]:
            side = bd / f"{ch}.json"
            if side.exists():
                n = len(json.loads(side.read_text())["offsets"])
                for v in range(1, n + 1):
                    yield int(bd.name), ch, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--every", type=int, default=8)
    # Resume handle. A whole-Bible run at --every 1 is ~22 h of CPU and has no
    # checkpoint of its own; a restart without this re-scores everything.
    # Accepts "12", "0-38" or "12-" (open-ended).
    ap.add_argument("--books")
    ap.add_argument("--model")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    asr_lang = ASR_LANG.get(a.lang)
    if not asr_lang:
        sys.exit(f"no ASR language for {a.lang}")
    name = a.model or ("small.en" if asr_lang == "en" else "small")

    from faster_whisper import WhisperModel
    model = WhisperModel(name, device="cpu", compute_type="int8")
    print(f"model {name}, asr language {asr_lang}\n", flush=True)

    if a.validate:
        # ⚠⚠ READ THE GROUND TRUTH FROM THE PRE-REPAIR BACKUPS.
        # repair_verses.py splices fresh takes into narration/<lang>/, so once a
        # verse is repaired the live tree NO LONGER CONTAINS the defect this
        # detector was validated on. Measured 2026-09-04: after the 280-verse
        # ylt repair this block scored the ten ear-confirmed verses 0/10 and
        # printed "do not use it" -- it was reading REPAIRED audio. See verse_wav.
        n_orig = sum(1 for b, ch, _ in EAR_CONFIRMED_YLT
                     if (NAR / "ylt_qa_fail_originals" / str(b) / f"{ch}.ogg").exists())
        print(f"ten ear-CONFIRMED ylt verses "
              f"({n_orig}/10 read from the PRE-REPAIR originals):")
        if n_orig < len(EAR_CONFIRMED_YLT):
            print(f"  ⚠ {len(EAR_CONFIRMED_YLT) - n_orig} verse(s) have NO "
                  f"pre-repair backup; if those were repaired, the recall figure "
                  f"below is not a measurement of the detector.")
        pos = score_set(model, "ylt", EAR_CONFIRMED_YLT, "en", show=True,
                        prefer_originals=True)
        random.seed(7)
        pool = [t for t in iter_verses("ylt", 1)
                if t[0] in (0, 1) and t not in EAR_CONFIRMED_YLT]
        print("\n40 random verses from the same books:", flush=True)
        neg = score_set(model, "ylt", random.sample(pool, 40), "en")
        pk = np.array([r[0] for r in pos])
        nk = np.array([r[0] for r in neg])
        print(f"\n  CONFIRMED (n={len(pk)}): k>=1 on {(pk >= 1).sum()}/{len(pk)}"
              f"   mean k {pk.mean():.2f}")
        print(f"  RANDOM    (n={len(nk)}): k>=1 on {(nk >= 1).sum()}/{len(nk)}"
              f"   mean k {nk.mean():.2f}")
        tp, fp = int((pk >= 1).sum()), int((nk >= 1).sum())
        print(f"\n  at threshold k>=1 : catches {tp}/{len(pk)} confirmed, "
              f"false-positives {fp}/{len(nk)} random")
        # A detector with ZERO false positives is usable well below
        # perfect recall: it can only ever ADD confirmed work.
        if tp >= 0.7 * len(pk) and fp <= 0.05 * len(nk):
            print("  \u2705 SEPARATED — usable. Note it finds REPEATS only, not "
                  "novel hallucinations.")
        else:
            print("  \u26d4 NOT SEPARATED — do not use it.")
        # ⚠ EXIT NON-ZERO WHEN IT DOES NOT SEPARATE. This used to plain
        # `return`, so the process exited 0 and "do not use it" was
        # INDISTINGUISHABLE from "usable" to anything gating on the exit
        # code -- including the preflight stamp that licenses a render.
        return 0 if (tp >= 0.7 * len(pk) and fp <= 0.05 * len(nk)) else 1

    lo, hi = 0, 10**6
    if a.books:
        parts = a.books.split("-")
        lo = int(parts[0])
        hi = int(parts[1]) if len(parts) > 1 and parts[1] else (
            lo if len(parts) == 1 else 10**6)
    hits, n = [], 0
    items = [t for t in iter_verses(a.lang, a.every) if lo <= t[0] <= hi]
    print(f"{len(items)} verses to score"
          + (f" (books {lo}-{hi})" if a.books else ""), flush=True)
    res = score_set(model, a.lang, items, asr_lang, progress=True)
    for k, b, ch, v, tail in res:
        n += 1
        if k >= 1:
            hits.append((k, b, ch, v, tail))
    print(f"\n{n} verses scored, {len(hits)} with a repeated tail")
    if a.out:
        Path(a.out).write_text("\n".join(f"k={k} {b}/{c} v{v}  {t}"
                                         for k, b, c, v, t in hits),
                               encoding="utf-8")
        print(f"written to {a.out}")


if __name__ == "__main__":
    sys.exit(main() or 0)
