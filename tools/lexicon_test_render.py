# -*- coding: utf-8 -*-
"""Render ONE verse per pronunciation-lexicon entry so an ear can judge it.

    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\lexicon_test_render.py \
        --lang ylt --out _work\\EAR_ylt_lexicon_test.ogg            # dry run
    ... --apply                                                     # uses the GPU

## What this is for

`tools/pronounce_lexicon.py` holds respellings that are fed to the SYNTHESISER
so it says a word correctly. Every entry there is a **hypothesis about how this
model reads these letters** — not knowledge — and the file says so on every run.
This tool produces the only thing that can settle one: a BEFORE/AFTER pair for
each entry, cut back to back, for a human to listen to.

  BEFORE = the SHIPPED audio for that verse, sliced out of narration/<set>/<b>/<c>.ogg
           using the chapter's own offsets. It is not re-rendered, so it is
           exactly what the owner would hear in the app today.
  AFTER  = a fresh synthesis of the SAME verse with the respelling applied.

## ⛔ Why BEFORE is the shipped audio and not a fresh render of the original

A fresh render of the original spelling would be a different draw, and
chatterbox is stochastic: any difference the ear noticed could then be the draw
rather than the respelling. Slicing the shipped take removes that confound —
the only deliberate difference between the two clips is the spelling.

## ⛔ WHAT THIS TOOL CANNOT TELL YOU

Nothing here decides whether an entry is good. The gate is not consulted and no
screen is run, because **no screen can adjudicate pronunciation** — the ASR
emits a different token either way, which is exactly why this defect class has
no instrument (CLAUDE.md, «MISPRONUNCIATION IS A FIFTH DEFECT CLASS»). This
tool only cuts the evidence. A human marks `validated:` in the lexicon.

## ⚠ It never writes into narration/

Output is a single .ogg plus a .txt manifest under _work/. The shipped audio is
read-only here, and the lexicon is NOT wired into narrate.py by this tool.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DATA = Path(r"C:\Projects\Hexapla-releases")
NARRATION = DATA / "narration"

# One rate for every clip in the output. See slice_shipped().
SR = 24000

ASSETS = {"ylt": REPO / "app/src/main/assets/bibles/en_ylt.json"}


def load_books(lang):
    path = ASSETS.get(lang)
    if path is None or not path.exists():
        sys.exit(f"no asset mapped for --lang {lang}")
    return json.loads(path.read_text(encoding="utf-8"))


def pick_verse(books, word, used):
    """Shortest verse containing `word` as a whole word, not already used.

    Shortest on purpose: the clip is for a human ear and a 4-second verse makes
    the word easy to locate. Ties go to the earliest reference so the run is
    deterministic and a re-run produces the same evidence.
    """
    pat = re.compile(r"\b" + re.escape(word) + r"\b", re.I)
    best = None
    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk["chapters"]):
            verses = ch if isinstance(ch, list) else [ch[k] for k in sorted(ch, key=int)]
            for vi, text in enumerate(verses, start=1):
                if not text or not pat.search(text):
                    continue
                if (bi, ci, vi) in used:
                    continue
                key = (len(text), bi, ci, vi)
                if best is None or key < best[0]:
                    best = (key, bi, ci, vi, text)
    return None if best is None else (best[1], best[2], best[3], best[4])


def slice_shipped(lang, b, c, v, out_wav):
    """Cut verse v out of the shipped chapter ogg. -> True on success.

    ⚠ Returns False rather than a silent zero-length file when anything is
    missing; the caller drops the entry and SAYS SO. A missing BEFORE clip that
    reads as silence would look like a catastrophic render defect.
    """
    ogg = NARRATION / lang / str(b) / f"{c}.ogg"
    off_p = NARRATION / lang / str(b) / f"{c}.json"
    if not ogg.exists() or not off_p.exists():
        return False
    off = json.loads(off_p.read_text(encoding="utf-8"))["offsets"]
    if v - 1 >= len(off):
        return False
    start = off[v - 1] / 1000.0
    dur = (off[v] / 1000.0 - start) if v < len(off) else 20.0
    if dur <= 0.1:
        return False
    # ⚠ -ar/-ac ARE NOT OPTIONAL. The shipped chapters are Opus, which decodes
    # at 48 kHz, while chatterbox synthesises at 24 kHz. The concat demuxer takes
    # its parameters from the FIRST input and does not resample, so an unforced
    # rate here encodes every B clip at 2x speed, an octave up — the whole
    # 18-entry file was unlistenable on 2026-09-04 for exactly this reason.
    rc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}",
                         "-t", f"{dur}", "-i", str(ogg),
                         "-ar", str(SR), "-ac", "1", str(out_wav)]).returncode
    return rc == 0 and Path(out_wav).exists() and Path(out_wav).stat().st_size > 1000


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--out", default=r"_work\EAR_ylt_lexicon_test.ogg")
    ap.add_argument("--apply", action="store_true",
                    help="actually synthesize (uses the GPU). Default is a dry run.")
    ap.add_argument("--only", help="comma-separated lexicon keys to test")
    a = ap.parse_args()

    import pronounce_lexicon as pl
    lex = pl.LEXICON
    if a.only:
        want = {w.strip().lower() for w in a.only.split(",") if w.strip()}
        missing = want - set(lex)
        if missing:
            sys.exit(f"not in the lexicon: {', '.join(sorted(missing))}")
        lex = {k: v for k, v in lex.items() if k in want}

    books = load_books(a.lang)
    plan, used, skipped = [], set(), []
    for word, (respell, why, validated) in lex.items():
        got = pick_verse(books, word, used)
        if got is None:
            skipped.append((word, "no verse contains it"))
            continue
        b, c, v, text = got
        used.add((b, c, v))
        # apply() -> (synthesis_text, [words replaced]); unpack it. A bare
        # assignment silently yields a TUPLE that stringifies plausibly and
        # would have been fed to the synthesiser verbatim.
        new_text, changed = pl.apply(text)
        if new_text == text or not changed:
            skipped.append((word, "apply() changed nothing — entry is inert here"))
            continue
        plan.append(dict(word=word, respell=respell, why=why, validated=validated,
                         b=b, c=c, v=v, text=text, new_text=new_text,
                         ref=f"{books[b]['name']} {c+1}:{v}"))

    print(f"{len(plan)} entry/entries to test"
          + (f", {len(skipped)} skipped" if skipped else ""))
    for w, why in skipped:
        print(f"  SKIP {w}: {why}")
    for p in plan:
        print(f"  {p['word']:12s} -> {p['respell']:14s} {p['b']}/{p['c']} v{p['v']}"
              f"  {p['ref']}")
        print(f"       {p['new_text'][:110]}")
    if not plan:
        sys.exit("nothing to test")
    if not a.apply:
        print("\nDRY RUN — nothing rendered. Add --apply to use the GPU.")
        return 0

    import narrate
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="lexrender_"))
    parts, manifest, failed = [], [], []
    sil = tmp / "sil.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-t", "1",
                    "-i", f"anullsrc=r={SR}:cl=mono", str(sil)], check=True)

    for i, p in enumerate(plan):
        before = tmp / f"{i:02d}_before.wav"
        if not slice_shipped(a.lang, p["b"], p["c"], p["v"], before):
            failed.append((p["word"], "shipped audio missing — BEFORE could not be cut"))
            continue
        wav, dur = narrate.synthesize_verse(p["new_text"], a.lang, str(tmp), 9000 + i,
                                            book_idx=p["b"])
        if not wav or not dur:
            failed.append((p["word"], "synthesis returned nothing"))
            continue
        parts += [before, sil, Path(wav), sil, sil]
        manifest.append(p)
        print(f"  rendered {p['word']} ({dur} ms)")

    if not parts:
        sys.exit("nothing rendered — refusing to write an empty clip file")

    # Refuse rather than emit a file whose B clips play at the wrong pitch.
    # A mixed-rate concat produces a plausible-looking .ogg of about the right
    # length; nothing downstream catches it except an ear.
    rates = set()
    for q in parts:
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "stream=sample_rate", "-of", "csv=p=0", str(q)],
                            capture_output=True, text=True)
        if pr.returncode != 0 or not pr.stdout.strip():
            sys.exit(f"ffprobe failed on {q} — refusing to concat blind")
        rates.add(int(pr.stdout.strip().splitlines()[0]))
    if rates != {SR}:
        sys.exit(f"REFUSING to concat: sample rates {sorted(rates)}, expected {SR}. "
                 "The concat demuxer does not resample; B would play at the "
                 "wrong speed and pitch.")

    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{q.as_posix()}'\n" for q in parts), encoding="utf-8")
    rc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                         "-safe", "0", "-i", str(lst), "-ar", str(SR), "-ac", "1",
                         "-c:a", "libopus", "-b:a", "16k", "-vbr", "on",
                         "-application", "voip", str(out)]).returncode
    if rc != 0 or not out.exists():
        sys.exit(f"ffmpeg concat failed rc={rc}")

    txt = out.with_suffix(".txt")
    lines = [
        f"{a.lang} — PRONUNCIATION LEXICON TEST, {len(manifest)} entry/entries.",
        "",
        "Each entry is TWO clips, 1 s apart, then a 2 s gap before the next entry:",
        "   clip A = the SHIPPED audio (what the app plays today)",
        "   clip B = the SAME verse re-synthesised with the respelling",
        "",
        "⚠ The ONLY deliberate difference is the spelling fed to the synthesiser.",
        "  The displayed text is never changed by any of this.",
        "⚠ Chatterbox is stochastic, so B is also a different DRAW. If B sounds",
        "  better in some way unrelated to the word, that is the draw, not the",
        "  respelling — judge the WORD only.",
        "",
        "For each: is the word RIGHT in B? (and did anything else get worse?)",
        "",
    ]
    for i, p in enumerate(manifest, start=1):
        lines += [f"{i}. {p['ref']}   [{p['b']}/{p['c']} v{p['v']}]",
                  f"   word: {p['word']}  ->  respelled '{p['respell']}'",
                  f"   why:  {p['why']}",
                  f"   text: {p['text'][:150]}",
                  ""]
    if failed:
        lines += ["", "⛔ NOT IN THIS FILE (no clip was produced):"]
        lines += [f"   {w}: {why}" for w, why in failed]
    txt.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n-> {out}")
    print(f"-> {txt}")
    for w, why in failed:
        print(f"  FAILED {w}: {why}")
    # Non-zero if any planned entry produced no clip: a short file that looks
    # complete is the failure mode this project keeps hitting.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
