# -*- coding: utf-8 -*-
"""Restore the ~58 missing psalm superscriptions in ru_synodal.json.

THE DEFECT (found 2026-07-15, owner-approved repair 2026-07-16): the converter
that produced ru_synodal.json from the CrossWire RusSynodal SWORD module
stripped every real <title> element, deleting the psalm superscriptions that
sit INLINE at the head of verse 1 — roughly half the psalter. Titles occupying
their own verse (Пс 3:1 etc.) survived. Full evidence in CLAUDE.md.

SOURCES (same Fedosov PD digitization lineage as the shipped asset — zero new
licensing exposure; licenses quoted in CLAUDE.md):
  1. The CrossWire RusSynodal module itself (read via pysword): psalms whose
     v1 raw markup carries <title canonical="true" type="psalm">…</title>.
     Titles come back lowercase («псалом Давида.») — first letter is
     normalized to match the asset's surviving titles.
  2. gratis-bible ru/rst.xml: Hebrew-numbered osisIDs, but every verse text
     opens with an explicit «(S:V)» SYNODAL coordinate — the mapping is in the
     data, no LXX/Hebrew arithmetic. Titles are inline and capitalized; this
     source covers the ascent/hallelujah superscriptions the module lacks
     («Песнь восхождения.», «Аллилуия.»).

SAFETY MODEL — title-prefix-only, body-gated:
  * A psalm is edited ONLY if a source title is found AND the source's v1 body
    matches the asset's v1 (folded skeleton: dashes unified, whitespace
    collapsed, lowercase). Same digitization -> the match is essentially
    exact; anything below MIN_RATIO is skipped and reported, so a numbering
    mix-up can only ever cause a SKIP, never a wrong-title prepend.
  * new_v1 = title + " " + old_v1 — asserted verbatim. Bodies are never
    touched; no verse is created, moved, or removed (title was inline in v1,
    so versemap/bookmarks/notes/highlights are unaffected — the same safe
    class fix_psalm144_title.py established).
  * Psalms whose v1 already starts with the title are skipped (e.g. Пс 144,
    restored earlier).

    python tools/fix_ru_psalm_titles.py --dry-run
    python tools/fix_ru_psalm_titles.py
"""
import argparse
import difflib
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")
SCRATCH = Path("C:/Users/infer/AppData/Local/Temp/claude/C--Projects-Hexapla/"
               "3f23918e-d4f5-4a45-a47c-fcc99c282210/scratchpad")
MODULE_DIR = SCRATCH / "rsmod"
RST_XML = SCRATCH / "rst.xml"
PSALMS = 18
MIN_RATIO = 0.90   # same digitization — near-exact is the expectation

TITLE_RE = re.compile(r'<title[^>]*type="psalm"[^>]*>(.*?)</title>', re.S)
TAG_RE = re.compile(r"<[^>]*>")
RST_VERSE_RE = re.compile(r"<verse osisID='Ps\.\d+\.\d+'>(.*?)</verse>", re.S)
DUAL_RE = re.compile(r"^\((\d+):(\d+)\)\s*(.*)$", re.S)


def fold(s):
    """Comparison skeleton: dash variants unified, whitespace collapsed, lowercase."""
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def cap_first(s):
    return s[0].upper() + s[1:] if s else s


# A v1 that is ITSELF a superscription (own-verse title, e.g. Пс 139:1
# «Начальнику хора. Псалом Давида.»). Prepending anything to these is always
# wrong: rst carries a stray extra «Псалом.» before Пс 139's title, and the
# suffix gate alone would have doubled it (caught in the 2026-07-16 spot-check).
TITLE_SHAPED = re.compile(
    r"^(Начальнику хора|Псалом|Песнь|Хвала|Аллилуия|Молитва|Учение|Давида|"
    r"О Соломоне|Славословие)\b")

# Пс 151: PERMANENTLY EXCLUDED — resolved 2026-07-16, stays UNTITLED.
# The module's title «Псалом Давида на единоборстов с Голиафом» carries a
# typo («единоборстов» is not a Russian word form), rst has no Ps 151 to
# corroborate, and a second witness (azbyka.ru's Synodal) prints NO
# superscription there at all — only the traditional footnote «У Евреев этого
# псалма нет: он переведен с греческого». Verdict: the module's line is its
# own editorial paraphrase of the LXX heading, not a Synodal superscription.
# One typo'd witness contradicted by a second witness = do not add.
OWNER_GATED = {151}


def normalize_title(s):
    s = cap_first(s.strip())
    if s and s[-1] not in ".]":
        s += "."          # rst's Пс 112 «Аллилуия» lacks its period; the
    return s              # asset's surviving titles are period-terminated


def titles_from_module():
    """psalm number (Synodal, 1-based) -> (title, source_body_text)."""
    from pysword.modules import SwordModules
    mods = SwordModules(str(MODULE_DIR))
    found = mods.parse_modules()
    bible = mods.get_bible_from_module(list(found.keys())[0])
    out = {}
    for p in range(1, 152):
        try:
            raw = bible.get(books=["Psalms"], chapters=[p], verses=[1], clean=False)
        except Exception:
            continue
        m = TITLE_RE.search(raw)
        if not m:
            continue
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        body = TAG_RE.sub(" ", raw[m.end():])
        body = re.sub(r"\s+", " ", body).strip()
        if title and body:
            out[p] = (title, body)
    return out


def titles_from_rst(app_ps):
    """psalm number -> (title, source_body) derived by suffix-matching app v1.

    rst.xml verse text = "(S:V) [title ]body". The (S:V) prefix is the SYNODAL
    coordinate. The title is whatever prefix remains once the app's own v1 is
    located as the suffix of the source text — derived from the asset itself,
    so a title can never contain scripture the app lacks.
    """
    xml = open(RST_XML, encoding="utf-8").read()
    out = {}
    for m in RST_VERSE_RE.finditer(xml):
        dm = DUAL_RE.match(m.group(1).strip())
        if not dm:
            continue
        s_ps, s_vs = int(dm.group(1)), int(dm.group(2))
        if s_vs != 1 or not (1 <= s_ps <= 151):
            continue
        text = re.sub(r"\s+", " ", dm.group(3)).strip()
        app_v1 = app_ps[s_ps - 1][0] if app_ps[s_ps - 1] else ""
        if not app_v1:
            continue
        f_text, f_app = fold(text), fold(app_v1)
        if f_text == f_app:
            continue                      # no inline title here
        idx = f_text.find(f_app)
        if idx <= 0 or abs(len(f_text) - idx - len(f_app)) > 2:
            continue                      # app v1 is not a clean suffix — skip
        # Map the fold-index back: folding only collapses whitespace/dashes,
        # so align by consuming idx folded chars from the unfolded text.
        title = text[:idx].strip()
        if title:
            out[s_ps] = (title, text[idx:].strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[PSALMS]["chapters"]
    n_psalms = len(ps)
    counts = [len(c) for c in ps]

    mod = titles_from_module()
    rst = titles_from_rst(ps)
    print(f"module titles: {len(mod)}   rst-derived titles: {len(rst)}")

    edits, skipped_mismatch, already = [], [], []
    for p in range(1, n_psalms + 1):
        if not ps[p - 1]:
            continue
        v1 = ps[p - 1][0]
        title, body, src = None, None, None
        if p in mod:
            title, body, src = normalize_title(mod[p][0]), mod[p][1], "module"
        elif p in rst:
            title, body, src = normalize_title(rst[p][0]), rst[p][1], "rst"
        if not title:
            continue
        if p in OWNER_GATED:
            skipped_mismatch.append((p, src, f"OWNER DECISION — proposed "
                                             f"{title!r} (see script header)"))
            continue
        if TITLE_SHAPED.match(v1) and len(v1) < 130:
            skipped_mismatch.append((p, src, f"v1 is already an own-verse "
                                             f"title: {v1[:60]!r}"))
            continue
        if re.search(r"[<>&\d]", title) or len(title) > 120:
            skipped_mismatch.append((p, src, f"suspicious title {title!r}"))
            continue
        if fold(v1).startswith(fold(title)):
            already.append(p)
            continue
        ratio = difflib.SequenceMatcher(None, fold(v1), fold(body),
                                        autojunk=False).ratio()
        if ratio < MIN_RATIO:
            skipped_mismatch.append((p, src, f"body match {ratio:.2f}"))
            continue
        edits.append((p, title, src, ratio))

    print(f"\nproposed edits: {len(edits)}   already titled: {len(already)}   "
          f"skipped: {len(skipped_mismatch)}\n")
    for p, title, src, ratio in edits:
        print(f"  Пс {p:>3} [{src:<6} r={ratio:.2f}] + «{title}»")
    if skipped_mismatch:
        print("\nskipped (reported, untouched):")
        for p, src, why in skipped_mismatch:
            print(f"  Пс {p:>3} [{src}] {why}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    if not edits:
        print("nothing to do")
        return

    for p, title, src, _ in edits:
        old = ps[p - 1][0]
        new = f"{title} {old}"
        assert new.endswith(old) and new[:len(title)] == title
        ps[p - 1][0] = new

    assert len(ps) == n_psalms and [len(c) for c in ps] == counts, \
        "verse counts changed — refusing to write"

    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".pretitles.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"\nbackup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}: {len(edits)} titles restored, "
          f"verse counts unchanged ({sum(counts)} verses)")


if __name__ == "__main__":
    main()
