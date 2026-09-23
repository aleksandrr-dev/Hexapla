# -*- coding: utf-8 -*-
"""Which ru psalm chapters still lack their restored title in the AUDIO?

WHY (2026-08-07). CLAUDE.md carries a re-render queue of 24-25 psalms said to
predate the 2026-07-20 title restoration, plus Job 2/9 for a note leak. Spot
checks showed the list is STALE IN BOTH DIRECTIONS: Job 2/9 are clean, and
Ps 32/90/95/137/151 already speak their titles — but Ps 106 and 113 do not.
Re-rendering the whole list would waste GPU on chapters that are already right;
skipping it would ship psalms missing their superscription.

So: measure. Transcribe the first seconds of each chapter's verse 1 and check
whether the title's own words are actually spoken.

    python tools/check_ru_titles_rendered.py

⚠ Compare against the TITLE ONLY, not the whole verse. And compare loosely —
whisper mangles these words routinely («Псалом» came back as «Салон», «Давида»
as «Дарита»), so this asks whether the title is PRESENT, never whether it was
transcribed prettily.

⚠ Run under the kokoro venv (faster-whisper lives there).
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

ASSET = Path(__file__).parent.parent / "app/src/main/assets/bibles/ru_synodal.json"
NARR = Path("C:/Projects/Hexapla-releases/narration/ru")

# ⚠ SCAN THE WHOLE PSALTER, not CLAUDE.md's old re-render queue. That queue
# was wrong in both directions — it listed 19 psalms that were already correct
# and both Job chapters, which were clean — and it could not have listed the
# real problem, because the cause was not staleness at all: CosyVoice drops a
# short leading sentence (see narrate.join_short_lead). Any psalm with a
# superscription can be affected, so every one gets checked.
QUEUE = list(range(1, 152))


def title_of(verse):
    """The superscription: a leading [bracketed] span, or a short bare one."""
    m = re.match(r"\s*\[([^\]]+)\]", verse)
    if m:
        return m.group(1)
    m = re.match(r"\s*([А-ЯЁ][^.]{2,40}\.)\s", verse)   # e.g. «Давида. »
    return m.group(1) if m else None


def words(s):
    s = s.lower().replace("ё", "е")
    return [w for w in re.sub(r"[^а-я ]+", " ", s).split() if len(w) > 3]


def main():
    import build_announcements as ba
    bible = json.loads(ASSET.read_text(encoding="utf-8"))
    stale, ok, notitle = [], [], []

    for ps in QUEUE:
        ci = ps - 1
        ogg = NARR / "18" / f"{ci}.ogg"
        js = NARR / "18" / f"{ci}.json"
        if not ogg.exists():
            continue
        verse = bible[18]["chapters"][ci][0]
        title = title_of(verse)
        if not title:
            notitle.append(ps)
            continue
        # ⚠ START ~0.8 s BEFORE offsets[0], NEVER EXACTLY AT IT. The offset can
        # land a few tens of ms INSIDE the first word, and a clipped onset is
        # enough for whisper to miss it entirely. Psalm 135 was reported
        # "title not spoken" NINE consecutive times this way while the audio
        # plainly said «Аллилуия» — word timestamps put it at 3.48-4.44 s
        # against an offsets[0] of 3.542 s. The verdicts, not the audio, were
        # wrong. The preceding 0.8 s is silence (the 600 ms gap), so this
        # cannot pick up announcement words.
        t0 = max(0.0, json.loads(js.read_text())["offsets"][0] / 1000.0 - 0.8)
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp) / "v1.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.2f}",
                            "-t", "8", "-i", str(ogg), str(w)], check=True)
            heard = ba.asr(w)
        tw = words(title)
        hw = set(words(heard))
        # ⚠ FUZZY, NOT PREFIX. A 4-character prefix test called Ps 106/115/117/
        # 118/145/150 stale when every one of them audibly says the title:
        # whisper renders «Аллилуия» as «Алилуя», «Алилуи», «Алилуия» and
        # «Давида» as «Довида», so the first four characters routinely differ.
        # The question is whether the word is THERE, so compare it as a whole.
        import difflib
        hits = sum(1 for x in tw
                   if any(difflib.SequenceMatcher(None, x, y).ratio() >= 0.5
                          for y in hw))
        verdict = "OK" if tw and hits >= max(1, len(tw) // 2) else "STALE"
        (ok if verdict == "OK" else stale).append(ps)
        print(f"  Ps {ps:<4} title={title[:34]!r:38} heard={heard[:46]!r:50} {verdict}")

    print(f"\nalready rendered with title : {len(ok)}  {ok}")
    print(f"STALE, need re-render        : {len(stale)}  {stale}")
    if notitle:
        print(f"no title in asset (skipped)  : {notitle}")
    if stale:
        print("\n0-based --chapter args for narrate.py:",
              ",".join(str(p - 1) for p in stale))


if __name__ == "__main__":
    main()
