# -*- coding: utf-8 -*-
"""Screen for the SUBSTITUTION defect: the render SPOKE THE WRONG WORD.

    tools\\.kokoro_venv\\Scripts\\python.exe tools/qa_substitution.py --validate
    tools\\.kokoro_venv\\Scripts\\python.exe tools/qa_substitution.py --lang ylt
    ...                                       --lang ylt --books 0 --every 1

## Why this exists — the defect that had NO screen

ylt Genesis 12:14 (book 0, chapter 12, verse 14). Young's reads

    ... northward, and southward, and EASTWARD, and westward;

and the rendered audio says **westward TWICE**. The owner confirmed it BY EAR
on 2026-09-03. The ASR did not mishear; the RENDER is wrong.

Nothing in the existing screens is aimed at this:
  * `qa_selfrepeat` caught it ONLY BY LUCK - the substituted word happened to
    duplicate its neighbour, so it looked like a repeated tail.
  * `qa_asr_sweep`'s APPEND test never saw it at all: nothing was APPENDED, a
    word was REPLACED. The completed full-set sweep log has no `0/12` line.
  * A substitution into a word that does NOT duplicate a neighbour produces no
    signal in either. That class is still unscreened and this tool does not
    close it.

## The discriminator, and why a naive version is useless

`qa_asr_sweep` already computes every `replace` opcode and deliberately does
NOT report the mid-verse ones, because on archaic English they are dominated by
the ASR mis-hearing the text - "mourning"/"morning", "gehenna"/"guyhenna",
Hebrew names - at ~3 per chapter with essentially no true positives. A screen
that printed all of them would be noise, and a screen that produces noise does
not get run, which is the same as not having one.

So this tool reports only the sub-class it can argue for:

  **NEIGHBOUR-COPY** - the heard word does not match the text at this position,
  but it EXACTLY matches a word that appears ELSEWHERE in the same verse's own
  text. That is the signature of the render re-using a nearby word instead of
  synthesising the right one, and it is what Genesis 12:14 looks like:
  want `eastward`, heard `westward`, and `westward` is a real word of the verse.

  An ASR mis-hearing lands on a phonetically similar token that is usually NOT
  another word of the same verse, so this test excludes most of that noise by
  construction rather than by a tuned threshold.

Everything else is counted as OTHER-SUB and printed only under `--all-subs`.

## ⚠⚠ WHAT THIS SCREEN IS NOT

**IT IS NOT VALIDATED FOR RECALL, AND IT CANNOT BE.** Exactly ONE ground-truth
positive exists in this project (Genesis 12:14, ear-confirmed). `--validate`
proves the tool FIRES on that one; it proves nothing about how many real
substitutions it MISSES, and a screen that produces false negatives is worse
than no screen because it licenses discarding real defects. The project rule is
that a screen is validated against ground truth before it is trusted; this one
cannot meet that bar until more positives exist.

▶ So: **every hit needs an ear**, and a clean run means "no NEIGHBOUR-COPY
substitution was detected", never "this set has no substitutions". Report ylt
as "clean on what can be detected". The honest gap - a substitution into a word
that duplicates nothing - has no instrument at all.
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


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / fn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


qav = _load("qav", "qa_asr_verify.py")

# ⚠⚠ THESE TRANSCRIPTION SETTINGS ARE LOAD-BEARING AND ARE COPIED VERBATIM
# from qa_asr_sweep.py, which took them from qa_asr_verify.py. Dropping
# hallucination_silence_threshold took the flag rate from 10 % to 62.5 % on one
# book - the model starts volunteering text it was given no audio for, and every
# one of those is a false flag. Do not tune them here; if they change, they
# change in qa_asr_verify first and every screen follows.
ASR_KWARGS = dict(beam_size=5, vad_filter=False,
                  condition_on_previous_text=False,
                  hallucination_silence_threshold=0.5)

# The one ear-confirmed substitution in the project. Owner, 2026-09-03.
GROUND_TRUTH = ("ylt", 0, 12, 14, "eastward", "westward")


def substitutions(ww, hw):
    """-> (neighbour_copies, other_subs) for one verse.

    neighbour_copies: [(i1, wanted_tokens, heard_tokens)] where a heard token is
    a real word of THIS verse's text taken from somewhere other than the span it
    replaced. other_subs: every remaining mid-verse `replace`.
    """
    sm = difflib.SequenceMatcher(None, ww, hw)
    near, other = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace":
            continue
        # The END of the verse is qa_asr_sweep's END-SUB class, already measured
        # as ~all ASR noise (100 flags on Genesis 1-34, ~0 real). Leave it there.
        if i2 >= len(ww) - 1:
            continue
        want, heard = ww[i1:i2], hw[j1:j2]
        # words of the verse OUTSIDE the replaced span
        elsewhere = set(ww[:i1]) | set(ww[i2:])
        copied = [h for h in heard if h in elsewhere and h not in want]
        (near if copied else other).append((i1, want, heard))
    return near, other


def validate():
    """Require the screen to FIRE on the one ear-confirmed positive."""
    lang, b, ch, v, want_word, heard_word = GROUND_TRUTH
    narrate = _load("narrate", "narrate.py")
    cfg = narrate.LANG_CONFIG[lang]
    ww = qav.norm(qav.verse_text(cfg["asset"], b, ch)[v - 1])
    if want_word not in ww:
        print(f"⛔ BROKEN CHECK, not a pass: {want_word!r} is not in "
              f"{lang} {b}/{ch} v{v}. The asset text changed under this test.")
        return 2
    # Synthesise the transcript the owner's ear confirmed: the render says the
    # NEIGHBOUR word where the text has want_word. This tests the DISCRIMINATOR,
    # not the ASR - the ASR path is exercised by a real --lang run.
    hw = [heard_word if w == want_word else w for w in ww]
    near, other = substitutions(ww, hw)
    print(f"ground truth: {lang} {b}/{ch} v{v}  "
          f"want {want_word!r} -> heard {heard_word!r}")
    print(f"  NEIGHBOUR-COPY hits: {len(near)}   other mid-verse subs: {len(other)}")
    for i1, want, heard in near:
        print(f"    at token {i1}: want {want} heard {heard}")
    # Negative control: the untouched verse must produce nothing.
    n2, _ = substitutions(ww, list(ww))
    print(f"  negative control (identical transcript): {len(n2)} hit(s)")
    ok = len(near) >= 1 and len(n2) == 0
    print("PASS" if ok else "⛔ FAIL")
    print("\n⚠ A PASS HERE IS NOT VALIDATION. It shows the discriminator fires "
          "on the ONE\n  ear-confirmed positive and stays silent on an identical "
          "transcript. It says\n  NOTHING about recall - see this file's "
          "docstring. Every hit still needs an ear.")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--books", type=int, nargs="*")
    ap.add_argument("--chapters", type=int, nargs="*",
                    help="chapter indices within --books; default every chapter")
    ap.add_argument("--every", type=int, default=1,
                    help="sample every Nth chapter (default: all)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--all-subs", action="store_true",
                    help="also print the OTHER-SUB class (mostly ASR noise)")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()

    if a.validate:
        sys.exit(validate())
    if not a.lang:
        print("give --lang, or --validate")
        sys.exit(2)

    from faster_whisper import WhisperModel
    narrate = _load("narrate", "narrate.py")
    cfg = narrate.LANG_CONFIG[a.lang]
    en = a.lang in ("en", "ylt", "tyn", "wbt", "gnv", "wyc")
    name = a.model or ("small.en" if en else "small")
    asr_lang = "en" if en else cfg.get("asr_lang", "en")
    # ⚠ CPU int8 on purpose: CUDA constructs fine on this box and then raises
    # `Library cublas64_12.dll is not found` on the first encode(). A load-time
    # check is not a capability check.
    model = WhisperModel(name, device="cpu", compute_type="int8")
    print(f"model {name}, asr language {asr_lang}", flush=True)

    root = qav.OUTPUT / a.lang
    books = a.books or sorted(int(p.name) for p in root.iterdir()
                              if p.is_dir() and p.name.isdigit())
    tot_v = tot_near = tot_other = 0
    refused = []
    t0 = time.time()
    for b in books:
        bdir = root / str(b)
        chs = sorted(int(p.stem) for p in bdir.glob("*.ogg"))
        if a.chapters:
            want = set(a.chapters)
            missing = want - set(chs)
            if missing:
                # A named chapter that is not on disk is a BROKEN CHECK, not an
                # empty result. Never let it pass as "nothing found".
                print(f"⛔ book {b}: chapter(s) {sorted(missing)} not on disk")
                sys.exit(2)
            chs = [c for c in chs if c in want]
        for ch in chs[::a.every]:
            ogg, side = bdir / f"{ch}.ogg", bdir / f"{ch}.json"
            if not ogg.exists() or not side.exists():
                continue
            offsets = json.loads(side.read_text())["offsets"]
            texts = qav.verse_text(cfg["asset"], b, ch)
            if len(offsets) != len(texts):
                # A mismatch means every diff below would be against the WRONG
                # verse. Refuse the chapter; never score it silently.
                refused.append(f"{b}/{ch} offsets {len(offsets)} != verses {len(texts)}")
                continue
            with tempfile.TemporaryDirectory() as td:
                for i, start in enumerate(offsets):
                    end = offsets[i + 1] if i + 1 < len(offsets) else None
                    wav = Path(td) / f"v{i}.wav"
                    qav.cut(ogg, start, end, wav)
                    segs, _ = model.transcribe(str(wav), language=asr_lang,
                                               **ASR_KWARGS)
                    hw = qav.norm(" ".join(s.text for s in segs))
                    ww = qav.norm(texts[i])
                    if not ww:
                        continue
                    tot_v += 1
                    near, other = substitutions(ww, hw)
                    tot_other += len(other)
                    for i1, want, heard in near:
                        tot_near += 1
                        print(f"  SUBST [{b}/{ch}] v{i + 1}  "
                              f"want {' '.join(want)!r} -> heard "
                              f"{' '.join(heard)!r}", flush=True)
                        lo, hi = max(0, i1 - 6), min(len(ww), i1 + 6)
                        print(f"        text : {' '.join(ww[lo:hi])}", flush=True)
                    if a.all_subs:
                        for i1, want, heard in other:
                            print(f"  other [{b}/{ch}] v{i + 1}  "
                                  f"{' '.join(want)!r} -> {' '.join(heard)!r}",
                                  flush=True)
        print(f"[book {b} done] verses {tot_v}, NEIGHBOUR-COPY {tot_near}, "
              f"other-sub {tot_other}, {(time.time() - t0) / 60:.1f} min",
              flush=True)

    print(f"\n{tot_v} verses scored, {tot_near} NEIGHBOUR-COPY substitution(s), "
          f"{tot_other} other mid-verse substitution(s)")
    if refused:
        print(f"{len(refused)} chapter(s) REFUSED (offsets/verses mismatch):")
        for r in refused[:20]:
            print("  " + r)
    print("\n⚠⚠ EVERY HIT NEEDS AN EAR, AND A CLEAN RUN IS NOT A CLEAN SET.")
    print("  This screen has ONE ground-truth positive and NO recall measurement.")
    print("  A substitution into a word that duplicates nothing in its verse has")
    print("  no instrument at all. Say 'clean on what can be detected'.")


if __name__ == "__main__":
    main()
