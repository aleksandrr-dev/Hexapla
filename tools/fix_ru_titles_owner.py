# -*- coding: utf-8 -*-
"""Owner-directed Synodal psalm title additions (2026-07-16 feedback).

Two titles the automated restoration could not decide, now resolved by the
owner (native speaker) reviewing the shipped result:

  Пс 133 — «Песнь восхождения.»  A GAP THE OWNER CAUGHT: the automated pass
      restored the ascent titles for Пс 119-132 but silently skipped 133 (the
      15th and last ascent psalm — «до 118, везде ПЕСНЬ ВОСХОЖДЕНИЯ»).
  Пс 151 — applied per owner dictation, then REVERTED the same day: the
      owner re-delegated («I might be mistaken on my corrections. Go with
      what you think is right for the text»), and the evidence-based
      resolution stands — azbyka's Synodal prints NO superscription at
      Ps 151 (editorial footnote only) and neither PD digitization carries
      one. The Slavonic asset KEEPS its long Пс 151 title because the
      Elizabeth Bible genuinely prints it: the asymmetry is per-edition
      fidelity, not an inconsistency. TITLES below therefore contains only
      Пс 133 as the durable record; do not re-add 151.

Same safety pattern as fix_ru_psalm_titles.py: body-gated, prefix-only,
verse counts asserted, backup outside app/src/main/assets.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")
PSALMS = 18

TITLES = {
    133: ("Песнь восхождения.",
          "Благословите ныне Господа"),          # v1 must start with this
}


def main():
    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[PSALMS]["chapters"]
    counts = [len(c) for c in ps]

    for p, (title, v1_prefix) in TITLES.items():
        v1 = ps[p - 1][0]
        if v1.startswith(title):
            print(f"Пс {p}: already titled — skip")
            continue
        assert v1.startswith(v1_prefix), \
            f"Пс {p} v1 does not start with the expected body — refusing: {v1[:60]!r}"
        ps[p - 1][0] = f"{title} {v1}"
        print(f"Пс {p} + «{title}»")

    assert [len(c) for c in ps] == counts, "verse counts changed — refusing"
    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".owner-titles.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name} (verse counts unchanged)")


if __name__ == "__main__":
    main()
