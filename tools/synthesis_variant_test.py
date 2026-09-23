# -*- coding: utf-8 -*-
"""Render ONE verse several times with DIFFERENT SYNTHESIS INPUT, for an ear.

    tools\.chatterbox_venv\Scripts\python.exe tools\synthesis_variant_test.py \
        --set ylt --book 12 --chapter 23 --verse 25 --apply

## Why this exists

Some verses fail every draw. ylt `12/23 v25` doubled its final name in 12 of 12
draws across three sessions — that is not stochastic bad luck, so drawing again
is not a plan. The remaining lever is the STRING HANDED TO THE SYNTHESISER,
which is the same lever `pronounce_lexicon.py` pulls for mispronunciation.

This renders the verse once per candidate string and cuts them into one clip,
so an ear can say which input the model reads correctly.

## ⛔ WHAT IT MAY NEVER DO

It never writes into `narration/`, and the DISPLAYED text is never changed —
only the synthesis input. A variant that wins here has to be recorded somewhere
that feeds synthesis alone, exactly like the lexicon.

## ⚠ Only an ear decides

The gate's verdict is printed for each variant because it is free, but a gate
PASS is not a fix: the gate fires on printed-text repeats and misses mid-verse
ones. The clip is the deliverable.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"C:\Projects\Hexapla-releases\_work")
SR = 24000


def variants(text, also=()):
    """Candidate synthesis strings.

    ⛔ NEVER CHANGE WHICH WORDS ARE SPOKEN. The audio must still match the
    displayed verse and align_words' reference text. Two levers are allowed:
      * PUNCTUATION AND SPACING — generated below;
      * RESPELLING a word for the synthesiser only, which is exactly what
        `pronounce_lexicon.py` does. Pass those with --also.
    ⚠ A respelling that wins here must be RECORDED somewhere that feeds
    synthesis alone, or it is lost the moment the verse is re-rendered.
    """
    t = text.rstrip()
    out = [("as printed", t)]
    if t.endswith(";"):
        out.append(("semicolon -> full stop", t[:-1] + "."))
        out.append(("semicolon dropped", t[:-1]))
    if ":" in t:
        out.append(("colon -> comma", t.replace(":", ",")))
    out.append(("trailing space + stop", t.rstrip(";:. ") + " ."))
    out += [(f"custom {i+1}", c) for i, c in enumerate(also)]
    seen, uniq = set(), []
    for label, s in out:
        if s not in seen:
            seen.add(s); uniq.append((label, s))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--verse", type=int, required=True)
    ap.add_argument("--apply", action="store_true", help="synthesize (uses the GPU)")
    ap.add_argument("--also", action="append",
                    help="extra synthesis string (repeatable). Respellings go here.")
    a = ap.parse_args()

    import narrate
    books = narrate.load_bible(a.set_key)
    text = books[a.book]["chapters"][a.chapter][a.verse - 1]
    ref = f"{books[a.book]['name']} {a.chapter+1}:{a.verse}"
    vs = variants(text, a.also or [])
    print(f"{ref}  [{a.book}/{a.chapter} v{a.verse}]")
    for i, (label, s) in enumerate(vs, 1):
        print(f"  {i}. {label}\n     {s}")
    if not a.apply:
        print("\nDRY RUN — nothing rendered. Add --apply to use the GPU.")
        return 0

    import qa_gate
    tmp = Path(tempfile.mkdtemp(prefix="variant_"))
    sil = tmp / "sil.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "1.5",
                    "-i", f"anullsrc=r={SR}:cl=mono", str(sil)], check=True)
    parts, manifest = [], []
    for i, (label, s) in enumerate(vs):
        wav, dur = narrate.synthesize_verse(s, a.set_key, str(tmp), 7000 + i,
                                            book_idx=a.book)
        if not wav or not dur:
            print(f"  {label}: synthesis returned nothing"); continue
        asr = narrate.asr_transcribe(str(wav), narrate.ASR_LANG[a.set_key])
        reasons = (qa_gate.gate_reasons(asr["text"], asr["tokens"], text, a.set_key)
                   if asr else ["ASR UNAVAILABLE"])
        heard = " ".join(asr["tokens"][-8:]) if asr else "?"
        print(f"  {i+1}. {label}: {dur} ms  gate={reasons or 'clean'}\n     ...{heard}",
              flush=True)
        norm = tmp / f"{i:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav,
                        "-ar", str(SR), "-ac", "1", str(norm)], check=True)
        parts += [norm, sil]
        manifest.append(f"{i+1}. {label}  [gate: {reasons or 'clean'}]\n   {s}")
    if not parts:
        sys.exit("nothing rendered")
    # ⚠ one rate for every part; a mixed-rate concat re-encodes at the wrong speed
    lst = tmp / "l.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
                   encoding="utf-8")
    out = OUT / f"EAR_variants_{a.set_key}_{a.book}_{a.chapter}_v{a.verse}.ogg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-ar", str(SR), "-ac", "1", "-c:a", "libopus",
                    "-b:a", "16k", "-vbr", "on", "-application", "voip", str(out)],
                   check=True)
    out.with_suffix(".txt").write_text(
        f"{ref} — synthesis-input variants, 1.5 s apart, in this order.\n"
        "The WORDS are identical in every take; only punctuation differs.\n"
        "Which one says the final name ONCE?\n\n" + "\n\n".join(manifest) + "\n",
        encoding="utf-8")
    print(f"\n-> {out}  {out.stat().st_size/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
