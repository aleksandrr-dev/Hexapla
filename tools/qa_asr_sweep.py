# -*- coding: utf-8 -*-
"""Run qa_asr_verify's diff over a WHOLE set with ONE model load.

    tools\\.kokoro_venv\\Scripts\\python.exe tools/qa_asr_sweep.py --lang ylt
    ... --books 39 40 41 --device cuda --model small.en

## Why this exists

`qa_asr_verify.py` takes `--book` and constructs a `WhisperModel` per run on
**CPU int8**. Measured on ylt 2026-09-02: 1 m 48 s for one 48-verse chapter,
which is ~36 hours for a 1,189-chapter set - long enough that the audit simply
does not get run, which is the same as not having one.

Loading the model ONCE and sweeping the whole set is the difference between an
audit that happens and an audit that is described in a handoff.

⚠⚠ CUDA DOES NOT WORK ON THIS BOX AND THE FAILURE IS SILENT AT LOAD TIME.
`WhisperModel(..., device="cuda")` CONSTRUCTS FINE in 1.6 s; the first
`encode()` then raises `RuntimeError: Library cublas64_12.dll is not found`.
So a load-time check is not a capability check - run one real transcription
before believing the GPU is available. Default here is therefore CPU int8.

## What it reports, and the distinction that matters

It separates **TAIL** flags from mid-verse ones, because they are not equally
strong evidence and `qa_asr_verify`'s own docstring says so:

  - a **TAIL** insertion - audio after the last real word - is the hallucination
    class the owner's ear caught on the ylt pilot («POLE», «NASS», «ACCORD»).
    No duration heuristic can see it: one syllable moves a 5 s verse ~0.3 s,
    inside the natural spread of a read.
  - a **mid-verse** substitution is usually faster-whisper mis-hearing archaic
    English - "mourning"/"morning", "neighbour"/"neighbor", "fulfil"/"fulfill",
    "gehenna"/"guyhenna" were all flagged on a chapter that is FINE.

⚠⚠ **THIS IS A SCREEN, NOT AN ORACLE.** It ranks and shows; a human ear decides.
A high mid-verse rate on an archaic translation is expected and is not a defect.
"""
import argparse
import difflib
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_spec = importlib.util.spec_from_file_location("qav", HERE / "qa_asr_verify.py")
qav = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--books", type=int, nargs="*",
                    help="book indices; default every book present")
    ap.add_argument("--model", default=None,
                    help="default: small.en for English sets, small otherwise")
    ap.add_argument("--asr-lang", default=None,
                    help="ISO code for the ASR; default from the set")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute", default="int8")
    ap.add_argument("--every", type=int, default=1,
                    help="sample every Nth chapter (1 = all)")
    a = ap.parse_args()

    sys.path.insert(0, str(HERE))
    import narrate
    cfg = narrate.LANG_CONFIG[a.lang]

    # ⚠⚠ THE ASR LANGUAGE IS NOT ALWAYS ENGLISH AND THE FAILURE IS SILENT.
    # This defaulted to `small.en` with a hardcoded language="en". Pointed at
    # sv (Karl XII, Swedish) that transcribes Swedish through an ENGLISH-ONLY
    # model: every verse mismatches, the tool reports ~100 % flagged, and it
    # looks like a catastrophic defect rather than a misconfigured check.
    # `.en` models cannot do other languages at all - they must be swapped, not
    # merely told a different language code.
    ASR_LANG = {"ylt": "en", "en": "en", "wbt": "en", "gnv": "en", "wyc": "en",
                "tyn": "en", "sv": "sv", "ru": "ru", "cu": "ru"}
    asr_lang = a.asr_lang or ASR_LANG.get(a.lang)
    if asr_lang is None:
        sys.exit(f"no ASR language known for set {a.lang!r} - pass --asr-lang")
    model_name = a.model or ("small.en" if asr_lang == "en" else "small")
    if asr_lang != "en" and model_name.endswith(".en"):
        sys.exit(f"model {model_name} is English-only but the set is "
                 f"{asr_lang!r} - use a multilingual model")
    # ⚠ cu is Church Slavonic; whisper has no such code. 'ru' is the closest
    # and is a POOR fit - expect a high flag rate that means nothing. Do not
    # read a cu run as evidence without checking a few by ear first.
    print(f"set {a.lang}: ASR language {asr_lang}, model {model_name}", flush=True)

    from faster_whisper import WhisperModel
    t0 = time.time()
    model = WhisperModel(model_name, device=a.device, compute_type=a.compute)
    print(f"model {model_name} on {a.device} loaded in {time.time() - t0:.1f}s",
          flush=True)

    root = qav.OUTPUT / a.lang
    books = a.books or sorted(int(p.name) for p in root.iterdir()
                              if p.is_dir() and p.name.isdigit())

    tot_v = tot_flag = tot_tail = tot_endsub = 0
    refused = []
    skipped_empty = []
    t0 = time.time()
    for b in books:
        bdir = root / str(b)
        chapters = sorted(int(p.stem) for p in bdir.glob("*.ogg"))[::a.every]
        for ch in chapters:
            ogg, side = bdir / f"{ch}.ogg", bdir / f"{ch}.json"
            if not ogg.exists() or not side.exists():
                continue
            offsets = json.loads(side.read_text())["offsets"]
            texts = qav.verse_text(cfg["asset"], b, ch)
            if len(offsets) != len(texts):
                # Same refusal as qa_asr_verify: a mismatch means every diff
                # below would be against the wrong verse.
                refused.append(f"{b}/{ch} offsets {len(offsets)} != verses {len(texts)}")
                continue
            with tempfile.TemporaryDirectory() as td:
                for i, start in enumerate(offsets):
                    end = offsets[i + 1] if i + 1 < len(offsets) else None
                    # ⚠⚠ AN EMPTY VERSE HAS A ZERO-LENGTH SPAN AND KILLED THE
                    # WHOLE BOOK. Measured 2026-09-05: tyn book 44 (Romans) has
                    # an EMPTY verse 22 in the asset, so offsets[21]==offsets[22]
                    # and ffmpeg was handed `-ss 171.898 -to 171.898`. It aborts
                    # with "-to value smaller than -ss", qav.cut raises
                    # CalledProcessError, and the sweep DIES for the entire book.
                    # Romans was therefore never APPEND-screened, and the chain
                    # retried and re-failed it on every pass.
                    # ▶ Skip it, but SAY SO and count it — a verse silently
                    #   dropped from a screen is a verse the screen cannot speak
                    #   for, and this project treats that as unscreened, never
                    #   as passed.
                    if not texts[i].strip() or (end is not None and end <= start):
                        skipped_empty.append(f"{b}/{ch} v{i + 1}")
                        continue
                    wav = Path(td) / f"v{i}.wav"
                    qav.cut(ogg, start, end, wav)
                    segs, _ = model.transcribe(
                        str(wav), language=asr_lang, beam_size=5,
                        vad_filter=False,
                        # ⚠⚠ BOTH ARE LOad-BEARING and both come from
                        # qa_asr_verify. Dropping the hallucination threshold
                        # took the flag rate from 10 % to 62.5 % on one book -
                        # the model starts volunteering text it was given no
                        # audio for, and every one of those is a false flag.
                        condition_on_previous_text=False,
                        hallucination_silence_threshold=0.5)
                    # ⚠ qav.norm() returns a LIST of word tokens, not a string.
                    hw = qav.norm(" ".join(s.text for s in segs))
                    ww = qav.norm(texts[i])
                    if not ww:
                        continue
                    tot_v += 1
                    sm = difflib.SequenceMatcher(None, ww, hw)
                    r = sm.ratio()
                    # ⚠⚠ IDENTICAL to qa_asr_verify - do not "improve" it here.
                    # A prefix test (hw[:len(ww)] == ww) was tried and is WEAKER:
                    # it misses a tail whenever an earlier word also differs, so
                    # it reports "0 TAIL" on audio that has one. A sweep must
                    # never be more permissive than the tool it scales up.
                    # ⚠⚠ TWO DIFFERENT THINGS, DELIBERATELY SEPARATED.
                    # APPEND  = pure `insert` past every wanted word, consuming
                    #           nothing from want. This is the hallucination the
                    #           owner heard on the pilot («POLE», «NASS»).
                    # END-SUB = the final word REPLACED 1:1, which is almost
                    #           always the ASR mis-hearing archaic English or a
                    #           Hebrew name (dieth->dife, cush->kush). Measured
                    #           on Genesis 1-34: 100 such flags, ~0 real.
                    # qa_asr_verify scores both as "TAIL"; that is fine for one
                    # chapter read by a human and useless over 31,102 verses.
                    append = []
                    endsub = []
                    for tag, i1, i2, j1, j2 in sm.get_opcodes():
                        if tag == "insert" and i1 >= len(ww) and j2 == len(hw):
                            append = hw[j1:j2]
                        elif tag == "replace" and i2 >= len(ww) - 1:
                            endsub = hw[j1:j2]
                    if not (append or endsub or r < 0.90):
                        continue
                    tot_flag += 1
                    if endsub and not append:
                        tot_endsub += 1
                    if append:
                        tot_tail += 1
                        print(f"  APPEND [{b}/{ch}] v{i+1} "
                              f"+{' '.join(append)!r}  ratio {r:.2f}", flush=True)
                        print(f"        want : {' '.join(ww[-12:])}", flush=True)
                        print(f"        heard: {' '.join(hw[-12:])}", flush=True)
        el = time.time() - t0
        print(f"[book {b} done] verses {tot_v}, flagged {tot_flag}, "
              f"APPEND {tot_tail}, end-sub {tot_endsub}, {el/60:.1f} min",
              flush=True)

    print(f"\n{tot_v} verses checked | {tot_flag} flagged "
          f"({100*tot_flag/max(tot_v,1):.1f}%) | {tot_tail} APPEND "
          f"| {tot_endsub} end-substitutions (ASR noise)")
    if refused:
        print(f"{len(refused)} chapter(s) REFUSED (offsets/verses mismatch):")
        for r in refused[:20]:
            print("  " + r)
    if skipped_empty:
        # Visible on purpose: these verses were NOT screened. An empty verse in
        # the asset is a legitimate skip, but the count must be stated so nobody
        # reads "N verses checked" as "the whole book".
        print(f"{len(skipped_empty)} verse(s) SKIPPED as empty/zero-span "
              f"(not screened, not passed):")
        for r in skipped_empty[:20]:
            print("  " + r)
        if len(skipped_empty) > 20:
            print(f"  ... {len(skipped_empty) - 20} more")
    print("\n⚠ APPEND is the real defect class and every one needs an ear. "
          "end-substitutions\n  and mid-verse flags are mostly ASR "
          "mis-hearings of archaic English - on ylt\n  Genesis they ran ~3 per "
          "chapter with essentially no true positives.")


if __name__ == "__main__":
    main()
