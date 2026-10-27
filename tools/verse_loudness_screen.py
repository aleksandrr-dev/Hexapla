"""Screen repaired verses for a level defect: speech more than QUIET_DB under
the chapter's own speech level (repair_verses.quiet_verses).

Why: 2026-10-06 repair_verses levelled two clean kjv draws to the silent take
they replaced (en 9/19 v22, 42/5 v22). Every other screen passed them.

  python tools/verse_loudness_screen.py --dir en                 # every chapter with repairs
  python tools/verse_loudness_screen.py --dir en --chapter 9/19  # one chapter
  python tools/verse_loudness_screen.py --dir en --chapter 9/19 --all-verses

Scope by default = every verse listed in a chapter's qa.json `repairs` (the
verses this tool can have broken). rc 0 clean, 1 quiet verse(s) found,
2 a chapter could not be read (a check that cannot run did not pass).
Known-bad control: en 9/19 and en 42/5 before their re-repair -> rc 1.
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repair_verses import quiet_verses, SR  # noqa: E402

NARR = Path("C:/Projects/Hexapla-releases/narration")


def decode(ogg):
    fd, t = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ogg), "-ac", "1",
                        "-ar", str(SR), t], check=True)
        a, _ = sf.read(t, dtype="float32")
        return a
    finally:
        os.remove(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="narration dir key, e.g. en, ru, ylt")
    ap.add_argument("--chapter", help="b/c, 0-based as on disk")
    ap.add_argument("--all-verses", action="store_true")
    a = ap.parse_args()
    root = NARR / a.dir
    if a.chapter:
        b, c = a.chapter.split("/")
        chapters = [root / b / f"{c}.ogg"]
    else:
        chapters = sorted(root.glob("*/*.ogg"))
    n_ch = n_v = 0
    hits, errors = [], []
    for ogg in chapters:
        side = ogg.with_suffix(".json")
        qa = ogg.with_suffix(".qa.json")
        try:
            offs = json.loads(side.read_text(encoding="utf-8"))["offsets"]
            if a.all_verses:
                vs = list(range(1, len(offs) + 1))
            else:
                if not qa.exists():
                    continue
                vs = sorted({r["verse"] for r in json.loads(qa.read_text(encoding="utf-8"))
                             .get("repairs") or [] if not r.get("kept_existing_take")})
                if not vs:
                    continue
            audio = decode(ogg)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{ogg}: {e}")
            continue
        n_ch += 1
        n_v += len(vs)
        for v, under in quiet_verses(audio, offs, [v for v in vs if v <= len(offs)]):
            hits.append(f"{a.dir} {ogg.parent.name}/{ogg.stem} v{v}: {under} dB under the chapter")
    for h in hits:
        print("QUIET", h)
    for e in errors:
        print("ERROR", e)
    print(f"screened {n_v} verse(s) in {n_ch} chapter(s): {len(hits)} quiet, {len(errors)} unreadable")
    sys.exit(2 if errors else 1 if hits else 0)


if __name__ == "__main__":
    main()
