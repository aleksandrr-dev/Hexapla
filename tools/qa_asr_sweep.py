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


def parse_only(text):
    """`book chapter [verses]` -> {(b, ch): set(verses) or None}, + bad lines.

    Accepts the exact shape `qa_verse_queue.py` emits and `repair_verses.py`
    consumes, so a re-screen is driven by the SAME file the repair was:
    `#` comments and blank lines ignored; verses are `3` or `15,16` or absent
    (absent = the whole chapter).

    ⛔ A line it cannot parse is RETURNED, never dropped. A queue row silently
    skipped is a verse the screen cannot speak for, and this project treats
    that as unscreened rather than as passed.
    """
    want, bad = {}, []
    for ln in text.splitlines():
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        f = ln.split()
        if len(f) not in (2, 3) or not (f[0].isdigit() and f[1].isdigit()):
            bad.append(ln)
            continue
        key = (int(f[0]), int(f[1]))
        if len(f) == 2:
            want[key] = None          # whole chapter
            continue
        try:
            vs = {int(v) for v in f[2].split(",") if v != ""}
        except ValueError:
            bad.append(ln)
            continue
        if not vs:
            bad.append(ln)
            continue
        if key in want and want[key] is not None:
            want[key] |= vs
        elif key not in want:
            want[key] = vs
    return want, bad


def _selftest():
    ok = True

    def chk(name, got, exp):
        nonlocal ok
        good = got == exp
        ok = ok and good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: {got!r}")

    print("parse_only — known-GOOD input:")
    want, bad = parse_only("# header\n1 7 3\n16 8 4\n1 16 15,16\n22 32\n\n")
    chk("rows", want, {(1, 7): {3}, (16, 8): {4}, (1, 16): {15, 16},
                       (22, 32): None})
    chk("no bad lines", bad, [])
    print("parse_only — known-BAD input (must be REPORTED, not dropped):")
    want2, bad2 = parse_only("1 7 3\nnonsense\n2\n3 x 4\n7 8 a,b\n1 9 \n")
    # ⚠ `1 9 ` (trailing space) is NOT bad — it is two fields, i.e. the whole
    #   chapter, exactly as the documented rule says. Asserted here so nobody
    #   "fixes" it into a refusal later.
    chk("good rows still parsed", want2, {(1, 7): {3}, (1, 9): None})
    chk("four bad lines reported", len(bad2), 4)
    chk("bad lines named verbatim", sorted(bad2),
        sorted(["nonsense", "2", "3 x 4", "7 8 a,b"]))
    print("parse_only — whole-chapter row wins in EITHER order:")
    want5, _ = parse_only("1 7 3\n1 7\n")
    chk("verse row then whole chapter", want5, {(1, 7): None})
    print("parse_only — two rows for one chapter UNION, never replace:")
    want3, _ = parse_only("1 7 3\n1 7 9\n")
    chk("union", want3, {(1, 7): {3, 9}})
    print("parse_only — whole-chapter row WINS over a verse row:")
    want4, _ = parse_only("1 7\n1 7 3\n")
    chk("whole chapter kept", want4, {(1, 7): None})
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


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
    # ⚠⚠ RE-SCREEN MODE. `repair_verses.py` rewrites ONE verse inside a
    # chapter and its own last line says its OK is not evidence about the
    # audio. The screen that condemned the verse therefore has to run again on
    # the NEW audio — but sweeping the whole book to re-check one verse is
    # hours of Whisper for a question about 42 of them.
    # ⛔ This is NOT a sample: for the question «did the repair hold?» the 42
    #    repaired verses ARE the whole denominator. --every is a sample and
    #    prints as one; --only is a restriction and prints its COVERAGE.
    ap.add_argument("--only",
                    help="file of `book chapter [verses]` lines (the "
                         "repair queue's own format): screen ONLY these. "
                         "Reports coverage — a requested verse the screen "
                         "could not reach is NAMED, never counted as passed")
    ap.add_argument("--selftest", action="store_true",
                    help="parse controls for --only, both ways; no model load")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())

    # ⚠ Parsed BEFORE the model load on purpose: a queue this tool cannot read
    #   is a refusal, and a refusal should not cost a Whisper load first.
    only, only_bad = (None, [])
    if a.only:
        only, only_bad = parse_only(Path(a.only).read_text(encoding="utf-8"))
        if only_bad:
            # ⛔ Refuse. An unparseable row in a re-screen queue means the run
            #    would report on fewer verses than it was asked about while
            #    printing a clean total — the exact shape this project bans.
            print(f"⛔ {len(only_bad)} unparseable line(s) in {a.only}:")
            for r in only_bad[:20]:
                print("  " + r)
            sys.exit(2)
        if not only:
            sys.exit(f"⛔ {a.only} names no chapters — nothing to screen")
        if a.every != 1:
            sys.exit("⛔ --only is a restriction and --every is a sample; "
                     "combining them screens some of the verses you asked "
                     "about and reports a total for all of them")
        print(f"--only {a.only}: {len(only)} chapter(s), "
              f"{sum(1 if v is None else len(v) for v in only.values())} "
              f"requested target(s)", flush=True)

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
    books = a.books or (sorted({b for b, _ in only}) if only else
                        sorted(int(p.name) for p in root.iterdir()
                               if p.is_dir() and p.name.isdigit()))
    screened = set()   # (b, ch, verse) actually put through the model

    tot_v = tot_flag = tot_tail = tot_endsub = 0
    refused = []
    skipped_empty = []
    t0 = time.time()
    for b in books:
        # ⚠⚠ THE PER-BOOK LINE BELOW USED TO PRINT THE RUNNING TOTAL UNDER A
        # SINGLE BOOK'S NAME. tot_* are cumulative and are never reset, so
        # «[book 3 done] verses 3360, APPEND 5» was books 1+2+3, not book 3 —
        # a status line stating a plausible, wrong number, which is the one
        # thing this project forbids a status function to do. The 2026-09-12
        # handoff duly added the three lines together and reported «7 APPEND in
        # 6645 verses»; the run had screened 3360 verses and found 5.
        # ▶ Snapshot before the book, print the DELTA after it, and label the
        #   cumulative figure as cumulative.
        b_v0, b_flag0, b_tail0, b_endsub0 = tot_v, tot_flag, tot_tail, tot_endsub
        bdir = root / str(b)
        chapters = sorted(int(p.stem) for p in bdir.glob("*.ogg"))[::a.every]
        if only is not None:
            chapters = [c for c in chapters if (b, c) in only]
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
                    if only is not None:
                        vs = only[(b, ch)]
                        if vs is not None and (i + 1) not in vs:
                            continue
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
                    screened.add((b, ch, i + 1))
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
        print(f"[book {b} done] THIS BOOK: verses {tot_v - b_v0}, "
              f"flagged {tot_flag - b_flag0}, APPEND {tot_tail - b_tail0}, "
              f"end-sub {tot_endsub - b_endsub0}"
              f"  |  RUN SO FAR: verses {tot_v}, flagged {tot_flag}, "
              f"APPEND {tot_tail}, end-sub {tot_endsub}, {el/60:.1f} min",
              flush=True)

    print(f"\nRUN TOTAL over books {', '.join(str(x) for x in books)}: "
          f"{tot_v} verses checked | {tot_flag} flagged "
          f"({100*tot_flag/max(tot_v,1):.1f}%) | {tot_tail} APPEND "
          f"| {tot_endsub} end-substitutions (ASR noise)")
    # ⛔ The books screened are named above on purpose: this total speaks for
    #    those books and nothing else. «ASR-screened» is never a property of
    #    the render, only of the books listed here.
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
    if only is not None:
        # ★ THE COVERAGE LINE IS THE POINT OF --only. «0 APPEND» over a
        #   restricted queue means nothing until the run says it actually
        #   reached every verse it was asked about. A missing verse is named.
        missed = []
        for (b, ch), vs in sorted(only.items()):
            if vs is None:
                if not any(k[0] == b and k[1] == ch for k in screened):
                    missed.append(f"{b}/{ch} (whole chapter — nothing screened)")
                continue
            for v in sorted(vs):
                if (b, ch, v) not in screened:
                    missed.append(f"{b}/{ch} v{v}")
        asked = sum(1 if v is None else len(v) for v in only.values())
        print(f"\nCOVERAGE: {asked - len(missed)} of {asked} requested "
              f"target(s) reached ({len(missed)} NOT screened)")
        if missed:
            print("⛔ NOT SCREENED — these were asked about and not reached. "
                  "They did not pass; they were not checked:")
            for m in missed[:40]:
                print("  " + m)
            if len(missed) > 40:
                print(f"  ... {len(missed) - 40} more")
    print("\n⚠ APPEND is the real defect class and every one needs an ear. "
          "end-substitutions\n  and mid-verse flags are mostly ASR "
          "mis-hearings of archaic English - on ylt\n  Genesis they ran ~3 per "
          "chapter with essentially no true positives.")

    if only is not None and missed:
        # rc 1 = the run is INCOMPLETE against what it was asked. A caller
        # must not read a clean flag count off a screen that did not finish.
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
