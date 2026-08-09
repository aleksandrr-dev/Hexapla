# -*- coding: utf-8 -*-
"""Derive the official translation/language counts from Bible.kt.

THE CONVENTION (owner decision 2026-08-09 — do not re-litigate per release):
  · TRANSLATIONS = distinct texts. Two scripts of ONE translation count once
    (zh_cuv_s + zh_cuv_t = the same 和合本). Original-language texts (grc,
    wlc) COUNT — "translation" in user-facing copy means "Bible text", and
    excluding them understates the app.
  · LANGUAGES = languages a READER would name. Middle English (enm) folds
    into English; ancient languages (cu, grc, la, sa) count as their own —
    a Greek speaker cannot read the Byzantine text as modern Greek.

Run this before editing the tagline, the store listing, or the landing page,
and make ALL THREE agree with its output. The three drifted apart for a month
(37/35/33 and 31/30/28 coexisting) because each was hand-counted under a
different unstated convention.

    python tools/count_translations.py
"""
import io
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KT = Path(__file__).parent.parent / "app/src/main/java/com/aleks/hexapla/Bible.kt"

# id-level dedupe: entries that are the SAME text in another script
SAME_TEXT = {"cuv": "cus"}          # zh Traditional -> counts with Simplified
# language folds: asset prefix -> counted language
FOLD = {"enm": "en"}                # Middle English reads as English


def main():
    t = io.open(KT, encoding="utf-8").read()
    blk = t[t.index("val translations"):t.index("fun translation(")]
    rows = re.findall(r'Translation\(\s*"([a-z0-9]+)",\s*"bibles/([a-z0-9_]+)\.json"', blk)
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate translation ids"

    texts = [i for i in ids if i not in SAME_TEXT]
    prefixes = {FOLD.get(a.split("_")[0], a.split("_")[0]) for _, a in rows}

    print(f"entries in Bible.kt : {len(ids)}")
    print(f"TRANSLATIONS (texts): {len(texts)}   (script-duplicates deduped: "
          f"{sorted(SAME_TEXT)})")
    print(f"LANGUAGES (reader)  : {len(prefixes)}   (folds: {FOLD})")
    print()
    print(f'==> user-facing copy: «{len(texts)} translations in '
          f'{len(prefixes)} languages»')
    print()
    print("Update TOGETHER whenever this changes:")
    print("  · welcome_tagline ×26 locales (res/values*/strings.xml)")
    print("  · store-assets/STORE_LISTING.md")
    print("  · index.html (landing page)")


if __name__ == "__main__":
    main()
