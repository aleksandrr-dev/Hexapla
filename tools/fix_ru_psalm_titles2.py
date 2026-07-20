# -*- coding: utf-8 -*-
"""Second (completion) pass on the Synodal psalter's dropped superscriptions.

The 2026-07-16 pass (fix_ru_psalm_titles.py) restored 56 titles from the two
PD digitization witnesses (CrossWire RusSynodal + gratis rst.xml). The
residual set — titles absent from BOTH digitizations — was recovered
2026-07-20 by reading a genuine 1904 Синодальная типография print scan
(archive.org B-001-026-985-ALL / bibliiailiknigis00sankuoft, 7-е изд.,
600ppi page images, pre-reform orthography) page by page:
research/ru_psalm_titles_completion.md documents every psalm with its page
index and as-printed text. 24 titles recovered; Пс 42/70/104 confirmed
genuinely untitled in the print (asset already correct; Пс 104 notably
diverges from the Vulgate's "Alleluja" — per-edition fidelity keeps it
bare); Пс 7 was a census false positive.

CONVENTION (mirrors both the print and the asset's own existing style):
the print parenthesizes superscriptions supplied from the Greek/LXX
tradition (its own Пс 151 footnote states the principle: «переведенъ съ
Греческаго») and prints Hebrew-attested ones bare. The asset marks
LXX-supplied material with [square brackets] (Пс 98 «[Псалом Давида.]»,
Пс 23's «[В первый день недели]») and Hebrew-attested titles bare
(Аллилуия at Пс 110-112/134 = MT 111-113/135's own hallelujah openings).
So: print parens -> asset brackets; print bare -> asset bare. The one
bare title here, Пс 137 «Давида.», is exactly the one whose Hebrew
counterpart (MT 138) carries לדוד — the print's distinction is precise,
not a typesetting slip. Period-outside-parens (Пс 90/94/95) is kept
faithfully as period-outside-brackets. Пс 96's archaic «устроялась» is the
edition's own wording — kept.

Orthography: mechanically modernized (і->и, ѣ->е, ъ dropped) per the
report's proposed renderings — the same civil-spelling register as the
asset's existing titles.

Gates (mirror the first pass): TITLE-PREFIX-ONLY prepend to verse 1;
idempotent (skips a psalm already carrying its title); verse counts
asserted unchanged; backup outside assets/.

    python tools/fix_ru_psalm_titles2.py --dry-run
    python tools/fix_ru_psalm_titles2.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")
BACKUP = Path("C:/Projects/Hexapla-releases/asset-backups/ru_synodal.json.pretitles2.bak")

# psalm (LXX numbering, = the asset's own) -> exact title to prepend
TITLES = {
    32: "[Псалом Давида.]",
    90: "[Хвалебная песнь Давида].",
    92: "[Хвалебная песнь Давида. В день предсубботний, когда населена земля.]",
    93: "[Псалом Давида в четвертый день недели.]",
    94: "[Хвалебная песнь Давида].",
    95: "[Хвалебная песнь Давида. На построение дома].",
    96: "[Псалом Давида, когда устроялась земля его.]",
    103: "[Псалом Давида о сотворении мира.]",
    106: "[Аллилуия.]",
    113: "[Аллилуия.]",
    114: "[Аллилуия.]",
    115: "[Аллилуия.]",
    116: "[Аллилуия.]",
    117: "[Аллилуия.]",
    118: "[Аллилуия.]",
    135: "[Аллилуия.]",
    136: "[Давида.]",
    137: "Давида.",
    145: "[Аллилуия.]",
    146: "[Аллилуия.]",
    147: "[Аллилуия.]",
    148: "[Аллилуия.]",
    149: "[Аллилуия.]",
    150: "[Аллилуия.]",
}

# Expected opening words of each psalm's CURRENT verse 1 (from the asset,
# cross-checked against the print by the research pass) — a wrong-psalm or
# already-shifted asset fails loudly instead of being silently titled.
BODY_STARTS = {
    32: "Радуйтесь, праведные",
    90: "Живущий под кровом",
    92: "Господь царствует; Он облечен",
    93: "Боже отмщений",
    94: "Приидите, воспоем",
    95: "Воспойте Господу песнь новую",
    96: "Господь царствует: да радуется земля",
    103: "Благослови, душа моя",
    106: "Славьте Господа, ибо Он благ",
    113: "Когда вышел Израиль",
    114: "Я радуюсь",
    115: "Я веровал",
    116: "Хвалите Господа, все народы",
    117: "Славьте Господа, ибо Он благ",
    118: "Блаженны непорочные",
    135: "Славьте Господа, ибо Он благ",
    136: "При реках Вавилона",
    137: "Славлю Тебя всем сердцем",
    145: "Хвали, душа моя, Господа",
    146: "Хвалите Господа, ибо благо",
    147: "Хвали, Иерусалим, Господа",
    148: "Хвалите Господа с небес",
    149: "Пойте Господу песнь новую",
    150: "Хвалите Бога во святыне",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[18]["chapters"]
    counts_before = [len(c) for c in ps]

    applied, skipped = [], []
    for n, title in sorted(TITLES.items()):
        v1 = ps[n - 1][0]
        if v1.startswith(title):
            skipped.append(n)
            continue
        assert v1.startswith(BODY_STARTS[n]), \
            f"Пс {n}: v1 starts {v1[:50]!r}, expected {BODY_STARTS[n]!r} — aborting"
        new = f"{title} {v1}"
        assert new[len(title) + 1:] == v1  # title-prefix-only, body untouched
        if not args.dry_run:
            ps[n - 1][0] = new
        applied.append((n, title))

    assert [len(c) for c in ps] == counts_before, "verse counts changed?!"

    print(f"applied {len(applied)}, skipped (already titled) {len(skipped)}")
    for n, t in applied:
        print(f"  Пс {n}: {t}")
    if args.dry_run:
        print("dry run — nothing written")
        return

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(ASSET, BACKUP)
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET}\nbackup at {BACKUP}")


if __name__ == "__main__":
    main()
