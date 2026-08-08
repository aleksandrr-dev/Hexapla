# -*- coding: utf-8 -*-
"""Re-render the ru chapters whose audio predates a text fix, then re-splice.

⚠⚠ THE ORDERING TRAP THIS SCRIPT EXISTS TO PREVENT. narrate.py generates its
OWN chapter announcement, so re-rendering a chapter REINTRODUCES the truncated/
mispronounced announcement that the 2026-08-06/07 component work removed. Every
re-render must therefore be followed by apply_announcements.py for the same
chapter, which swaps in the verified component audio. Doing it in one script
means the two cannot drift apart.

⚠ apply_announcements re-splices FROM ITS BACKUP, so the backup of a re-rendered
chapter must be refreshed first — otherwise it would splice the OLD verse audio
straight back over the new render. Handled below by deleting the stale backup.

Chapters come from check_ru_titles_rendered.py, which measures rather than
trusts: CLAUDE.md's queue claimed ~25 psalms plus Job 2/9, and measurement found
19 psalms already correct and both Job chapters clean.

    python tools/rerender_ru_stale.py --dry-run
    python tools/rerender_ru_stale.py
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
COSY = HERE / ".cosyvoice_venv/Scripts/python.exe"
KOKORO = HERE / ".kokoro_venv/Scripts/python.exe"
BACKUP = Path("C:/Projects/Hexapla-releases/narration/ru_pre_announce")

# (book, chapter) 0-BASED.
# ⚠ FIRST PASS 2026-08-07 re-rendered Psalms 113, 114, 135, 146, 148, 149. Only
# 113/114 came back speaking their «Аллилуия» superscription; 135/146/148 were
# rendered WITHOUT it even though the asset text plainly carries it, and
# sampling 1.5 s before the verse offset found nothing there either.
#
# ⚠⚠ SO CosyVoice ALSO DROPS A SHORT LEADING WORD, not just a trailing one.
# «Аллилуия.» is one word followed by a pause at the very start of a chapter's
# first verse — exactly the position most likely to be swallowed. The render
# has no guard for this, and no count- or duration-based check can see it: the
# chapter is one word shorter and nothing else changes.
# Hence the verify-and-retry loop below: render, then LISTEN (ASR) for the
# title, and redraw if it is missing.
TARGETS = [(18, 22), (18, 90), (18, 134), (18, 145), (18, 147)]
MAX_TRIES = 3


def title_spoken(b, c):
    """Does the rendered chapter actually SAY its superscription? (ASR)

    ⚠ Compare fuzzily. Whisper mangles «Аллилуия» into «Алилуя», «Алилуи»,
    «Олелуя», «Олеллое» and «Псалом» into «Салон» — a strict or prefix-based
    match calls perfectly good audio stale. The question is only whether the
    word is THERE.
    """
    import difflib
    import json as _json
    import re as _re
    sys.path.insert(0, str(HERE))
    import build_announcements as ba
    import check_ru_titles_rendered as chk

    bible = _json.loads((HERE.parent /
                         "app/src/main/assets/bibles/ru_synodal.json")
                        .read_text(encoding="utf-8"))
    verse = bible[b]["chapters"][c][0]
    title = chk.title_of(verse)
    if not title:
        return True, "(no title in asset)"
    js = Path("C:/Projects/Hexapla-releases/narration/ru") / str(b) / f"{c}.json"
    t0 = _json.loads(js.read_text())["offsets"][0] / 1000.0
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "v1.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.2f}",
                        "-t", "7", "-i",
                        str(Path("C:/Projects/Hexapla-releases/narration/ru") /
                            str(b) / f"{c}.ogg"), str(w)], check=True)
        heard = ba.asr(w)
    tw = chk.words(title)
    hw = set(chk.words(heard))
    hits = sum(1 for x in tw
               if any(difflib.SequenceMatcher(None, x, y).ratio() >= 0.55
                      for y in hw))
    return bool(tw and hits >= max(1, len(tw) // 2)), heard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"{len(TARGETS)} chapters to re-render then re-splice")
    for b, c in TARGETS:
        print(f"\n=== book {b} chapter {c} (Psalm {c + 1}) ===", flush=True)
        if args.dry_run:
            continue

        for attempt in range(1, MAX_TRIES + 1):
            r = subprocess.run([str(COSY), "-u", str(HERE / "narrate.py"),
                                "--lang", "ru", "--book", str(b),
                                "--chapter", str(c), "--force"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=str(HERE.parent))
            if r.returncode != 0:
                print(f"  attempt {attempt}: RENDER FAILED")
                print((r.stderr or "")[-300:])
                continue

            # The backup holds pre-re-render audio; drop it so the splice takes
            # the FRESH render as its source rather than restoring the old one.
            for ext in ("ogg", "json", "w.json"):
                f = BACKUP / str(b) / f"{c}.{ext}"
                if f.exists():
                    f.unlink()

            r2 = subprocess.run([str(KOKORO), "-u",
                                 str(HERE / "apply_announcements.py"),
                                 "--book", str(b), "--chapter", str(c)],
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", cwd=str(HERE.parent))
            spliced = any("chapters, 0 errors" in l
                          for l in (r2.stdout or "").splitlines())

            ok, heard = title_spoken(b, c)
            print(f"  attempt {attempt}: spliced={spliced} title={'YES' if ok else 'NO'}"
                  f"  heard={heard[:60]!r}", flush=True)
            if ok and spliced:
                break
        else:
            print("  ⚠ GAVE UP — title still not spoken after "
                  f"{MAX_TRIES} draws; needs a human ear", flush=True)

    print("\nDone. Re-run tools/check_ru_titles_rendered.py to confirm the "
          "titles are now spoken, then let the upload watcher pick them up.")


if __name__ == "__main__":
    main()
