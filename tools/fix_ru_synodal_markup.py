# -*- coding: utf-8 -*-
"""Convert escaped OSIS remnants in ru_synodal.json into {x: y} margin notes.

THE DEFECT: three verses carry HTML-escaped OSIS that survived conversion. The
owner CONFIRMED (2026-07-15) that the app renders this markup to readers — Job
2:9 shows a wall of "&lt;note&gt;Этот стих по переводу 70-ти: ..." mid-chapter.
Bible.kt's parseAsset strips {x: y} margin notes and knows nothing about
escaped tags, so they pass straight through to the screen.

WHY CONVERT RATHER THAN STRIP: the notes are real content. Job 2:9's is a ~600-
char Septuagint variant of the whole verse; Job 9:9's identifies the
constellations. Bible.kt already has the mechanism we want:

    private val marginNote = Regex(\"\"\"\\s*\\{([^{}]*:[^{}]*)\\}\"\"\")
    // strips from display, RETAINS for the "Translator's notes" verse action

That is the feature built for KJV's ~7.8k margin notes. Reusing it fixes the
display AND keeps the text, at zero UI cost. Note the regex requires a colon and
forbids braces in the body — both hold for these three.

⚠ Псалтирь 143:15 IS NOT A NOTE. It trails «<title type="psalm">Хвала
Давида.</title>» — that is PSALM 144'S TITLE, detached and stranded on the end
of 143. Псалом 144:1 begins "Буду превозносить Тебя" with no title, so the text
really is misplaced. It is NOT moved here: other psalms carry their titles as
VERSE 1 (Псалом 4:1 = "Начальнику хора. На струнных орудиях. Псалом Давида."),
so restoring it properly is a VERSIFICATION change, and those ripple into
versemap.json, bookmarks, notes and highlights. Filed as a note for now; the
owner should decide whether Psalm 144 gets its title verse back.

    python tools/fix_ru_synodal_markup.py --dry-run
    python tools/fix_ru_synodal_markup.py
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")

NOTE = re.compile(r"\s*&lt;note&gt;(.*?)&lt;/note&gt;", re.S)
TITLE = re.compile(r"\s*&lt;title[^&]*&gt;(.*?)&lt;/title&gt;", re.S)
ANY_ESCAPED = re.compile(r"&lt;|&gt;|&amp;|&#\d+;")


def convert(text):
    """Escaped OSIS -> {x: y} margin notes parseAsset already understands."""
    text = NOTE.sub(lambda m: " {Примечание: " + m.group(1).strip() + "}", text)
    text = TITLE.sub(lambda m: " {Заголовок следующего псалма: "
                               + m.group(1).strip() + "}", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    changed, examples, leftovers = 0, [], []

    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk["chapters"]):
            for vi, v in enumerate(ch):
                if not v or "&lt;" not in v:
                    continue
                new = convert(v)

                # SAFETY 1: nothing escaped may survive.
                if ANY_ESCAPED.search(new):
                    leftovers.append((bk["name"], ci + 1, vi + 1, new[:120]))
                    continue
                # SAFETY 2: the result must parse the way Bible.kt will read
                # it — a note body with no braces and at least one colon.
                for body in re.findall(r"\{([^{}]*)\}", new):
                    if ":" not in body:
                        leftovers.append((bk["name"], ci + 1, vi + 1,
                                          f"brace group without a colon: {body[:60]}"))
                        break
                else:
                    changed += 1
                    examples.append((bk["name"], ci + 1, vi + 1, v, new))
                    if not args.dry_run:
                        ch[vi] = new

    print(f"verses converted: {changed}")
    for name, c, v, before, after in examples:
        print(f"\n  {name} {c}:{v}")
        print(f"    before: {before[:150]}")
        print(f"    after : {after[:150]}")
        # What the reader will actually see, per Bible.kt's regex.
        display = re.sub(r"\s*\{[^{}]*:[^{}]*\}", "", after)
        display = re.sub(r"[{}]", "", display)
        print(f"    SHOWN : {re.sub(r'\\s+', ' ', display).strip()[:110]}")

    if leftovers:
        print(f"\n⚠ {len(leftovers)} verse(s) NOT converted — left untouched:")
        for name, c, v, why in leftovers:
            print(f"    {name} {c}:{v}  {why}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"\nbackup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}")


if __name__ == "__main__":
    main()
