# -*- coding: utf-8 -*-
"""Render ONE verse N times from the IDENTICAL synthesis string, for an ear.

    tools\.chatterbox_venv\Scripts\python.exe tools\redraw_test.py \
        --set tyn --book 0 --chapter 43 --verse 31 --draws 4 --word seeth --apply

## Why this exists — it answers a question `synthesis_variant_test.py` CANNOT

The variant test renders one take per DIFFERENT string, so when a variant
sounds right it cannot tell you WHY. In a stochastic engine there are two
explanations and they demand opposite actions:

  * the input change fixed it        -> record the change, it helps every verse
  * that draw happened to come out   -> record nothing, there is no fix here

Measured 2026-09-08, tyn: the owner picked the «trailing space + stop» take for
`seeth` in Genesis 44:31. But `seeth` is **word 6 of 34** in that verse and the
only difference in that take is a full stop appended after word 34. A change 28
words downstream cannot be what altered word 6, so the take is far more likely
a good DRAW than a good INPUT.

▶ This tool renders the SAME string repeatedly. If some plain draws already say
the word correctly, the variant proved nothing and there is nothing to wire.
If every plain draw is wrong, the input change is worth believing.

⛔ It never writes into `narration/`. Output is a clip in `_work/` plus a
manifest, exactly like the variant test.

⚠ ONLY AN EAR DECIDES. The ASR line is printed because it is free, but it
cannot separate «seethe» from «see-eth» — both transcribe as `seeth`. Treat a
transcript hit as «the word is present», never as «the word is right». The
ONE thing ASR does catch is a WORD change (ylt's `fliyeth` -> «flyeth»), and
that is why the target word is checked in every draw.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"C:\Projects\Hexapla-releases\_work")
SR = 24000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="tyn")
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--verse", type=int, required=True)
    ap.add_argument("--draws", type=int, default=4)
    ap.add_argument("--word", default=None,
                    help="target word; each draw reports whether ASR heard it")
    ap.add_argument("--text", default=None,
                    help="override the SYNTHESIS string (e.g. a punctuation "
                         "variant). ⛔ Must speak the SAME WORDS as the asset "
                         "verse - checked, not trusted.")
    ap.add_argument("--respell", default=None, metavar="OLD=NEW",
                    help="respell ONE word for synthesis, e.g. seeth=seeith. "
                         "This is the sanctioned exception to the same-words "
                         "rule (it is what pronounce_lexicon does); exactly one "
                         "word may differ, and that is CHECKED.")
    ap.add_argument("--apply", action="store_true", help="synthesize (uses the GPU)")
    a = ap.parse_args()

    import narrate
    books = narrate.load_bible(a.set_key)
    text = books[a.book]["chapters"][a.chapter][a.verse - 1]
    ref = f"{books[a.book]['name']} {a.chapter+1}:{a.verse}"
    if a.respell:
        # ⚠ A RESPELLING IS THE ONE SANCTIONED WORD CHANGE — it is exactly what
        # pronounce_lexicon does, and --text's same-words guard would (rightly)
        # refuse it. So it gets its own door, and that door still CHECKS: the
        # substitution must actually occur, and it must change nothing else.
        if a.text:
            print("[STOP] pass --respell OR --text, not both.")
            sys.exit(1)
        if "=" not in a.respell:
            print("[STOP] --respell wants OLD=NEW, e.g. seeth=seeith")
            sys.exit(1)
        oldw, neww = a.respell.split("=", 1)
        if oldw.lower() not in text.lower():
            print(f"[STOP] «{oldw}» does not occur in this verse.")
            sys.exit(1)
        cand = text.replace(oldw, neww)
        diff = [(x, y) for x, y in zip(text.split(), cand.split()) if x != y]
        if not diff:
            print("[STOP] --respell changed nothing.")
            sys.exit(1)
        changed = {x for x, _ in diff}
        if len(changed) > 1:
            print(f"[STOP] --respell changed more than one distinct word: {changed}")
            sys.exit(1)
        print(f"⚠ RESPELLED FOR SYNTHESIS ONLY: «{oldw}» -> «{neww}» "
              f"({len(diff)} occurrence(s)); every other word unchanged.")
        text = cand
        # ⚠ TWO DIFFERENT WORDS ARE NEEDED HERE AND CONFLATING THEM BROKE THIS
        # TOOL TWICE ON 2026-09-08:
        #   LOCATION  — must be the RESPELLING, because that is what is in the
        #               synthesis string now; looking for the original raises
        #               «does not occur in this verse».
        #   ASR TARGET— must be the ORIGINAL, because ASR transcribes what it
        #               HEARS: a correct rendering of `seeith` returns «seeth».
        asr_word = oldw
        if a.word is None:
            # ⛔⛔ THE ASR TARGET IS THE **ORIGINAL** WORD, NEVER THE RESPELLING.
            # A respelling is an INPUT spelling; ASR transcribes what it HEARS,
            # so a correct rendering of `seeith` still comes back as «seeth».
            # Targeting the respelling therefore scores 0/N no matter what
            # happens - a screen that cannot fire. (Measured 2026-09-08: all
            # three candidates reported 0/3 and the number meant nothing.)
            # ▶ Targeting the ORIGINAL makes the check meaningful again: a MISS
            #   is what a word change looks like - ylt's `fliyeth` -> «flyeth».
            a.word = neww
    if a.text:
        # ⛔⛔ NEVER CHANGE WHICH WORDS ARE SPOKEN. Punctuation and spacing are
        # allowed levers; a different word is a different verse, and the audio
        # must still match the displayed text and align_words' reference.
        import re as _re
        norm = lambda t: [w for w in _re.sub(r"[^\w\s]", " ", t.lower()).split()]
        if norm(a.text) != norm(text):
            print("[STOP] --text does not speak the same words as the asset verse.")
            print(f"   asset: {norm(text)}")
            print(f"   given: {norm(a.text)}")
            sys.exit(1)
        print(f"⚠ SYNTHESIS STRING OVERRIDDEN (same words, different punctuation)")
        text = a.text
    words = text.split()
    print(f"{ref}  [{a.book}/{a.chapter} v{a.verse}]  {len(words)} words")
    print(f"  {text}")
    if a.word:
        pos = [i for i, w in enumerate(words) if a.word.lower() in w.lower()]
        for i in pos:
            print(f"  ▶ «{a.word}» is word {i+1} of {len(words)} "
                  f"({len(words)-i-1} words after it)")
        if not pos:
            sys.exit(f"⛔ «{a.word}» does not occur in this verse — wrong carrier?")
    print(f"\n{a.draws} draw(s) of the IDENTICAL string. "
          f"⚠ The string does not change; only the draw does.")
    if not a.apply:
        print("\nDRY RUN — nothing rendered. Add --apply to use the GPU.")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="redraw_"))
    sil = tmp / "sil.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "1.5",
                    "-i", f"anullsrc=r={SR}:cl=mono", str(sil)], check=True)
    asr_word = locals().get("asr_word") or a.word
    parts, manifest, heard_word = [], [], []
    for i in range(a.draws):
        wav, dur = narrate.synthesize_verse(text, a.set_key, str(tmp), 7100 + i,
                                            book_idx=a.book)
        if not wav or not dur:
            print(f"  draw {i+1}: synthesis returned nothing")
            manifest.append(f"{i+1}. SYNTHESIS RETURNED NOTHING")
            continue
        asr = narrate.asr_transcribe(str(wav), narrate.ASR_LANG[a.set_key])
        toks = asr["tokens"] if asr else []
        hit = None
        if asr_word and toks:
            hit = any(asr_word.lower() in t.lower() for t in toks)
            heard_word.append(hit)
        near = ""
        if asr_word and toks:
            for n, t in enumerate(toks):
                if asr_word.lower() in t.lower():
                    near = " ".join(toks[max(0, n-3):n+4])
                    break
        print(f"  draw {i+1}: {dur} ms"
              + (f"  ASR heard «{asr_word}»: {hit}" if asr_word else "")
              + (f"\n      ...{near}..." if near else ""), flush=True)
        if dur < 2000:
            print(f"      ⛔ DRAW {i+1} IS {dur} ms — a truncated/failed synthesis, "
                  f"not a take. It is still included so the clip and the log "
                  f"agree, but it is NOT one of the draws you are judging.",
                  flush=True)
            manifest.append(f"   ⛔ draw {i+1} is {dur} ms — FAILED SYNTHESIS, not a take")
        norm = tmp / f"{i:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav,
                        "-ar", str(SR), "-ac", "1", str(norm)], check=True)
        parts += [norm, sil]
        manifest.append(f"{i+1}. draw {i+1}  {dur} ms"
                        + (f"  [ASR heard the word: {hit}]" if a.word else ""))
    if not parts:
        sys.exit("nothing rendered")
    lst = tmp / "l.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
                   encoding="utf-8")
    # ⛔ THE VARIANT MUST BE IN THE FILENAME. Without it a --text run overwrote
    # the plain run's clip at the same path, so the two halves of the very
    # comparison this tool exists to make could not sit side by side.
    # (Happened 2026-09-08 on the first --text run.)
    tag = "asprinted"
    if a.respell:
        tag = "respell_" + a.respell.split("=", 1)[1]
    if a.text:
        import hashlib
        tag = "alt" + hashlib.sha1(a.text.encode("utf-8")).hexdigest()[:6]
    out = OUT / f"EAR_redraw_{a.set_key}_{a.book}_{a.chapter}_v{a.verse}_{tag}.ogg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-ar", str(SR), "-ac", "1", "-c:a", "libopus",
                    "-b:a", "16k", "-vbr", "on", "-application", "voip", str(out)],
                   check=True)
    out.with_suffix(".txt").write_text(
        f"{ref} — {a.draws} draws of the IDENTICAL synthesis string, 1.5 s apart.\n"
        "⚠ THE INPUT IS THE SAME EVERY TIME. Any difference you hear is the\n"
        "  model drawing differently, not the text.\n"
        f"Question: does «{a.word}» come out RIGHT in any of these plain draws?\n"
        "  If yes -> the variant that sounded good proved nothing; wire nothing.\n"
        "  If no  -> the input change is real and worth recording.\n\n"
        + "\n".join(manifest) + "\n", encoding="utf-8")
    print(f"\n-> {out}  {out.stat().st_size/1024:.1f} KB")
    if asr_word and heard_word:
        print(f"⚠ ASR heard «{asr_word}» in {sum(heard_word)}/{len(heard_word)} draw(s) "
              f"— presence only, NOT correctness. The clip is the deliverable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
