# -*- coding: utf-8 -*-
"""Audit every Bible asset for markup that leaked through conversion.

WHY: ru_synodal.json Иов 2:9 ships HTML-escaped OSIS — &lt;note&gt; wrapping a
~600-char Septuagint variant — and the owner confirmed 2026-07-15 that the app
RENDERS IT to readers. BibleRepo.parseAsset strips {x:y} margin notes and knows
nothing about escaped tags. If one converter leaked, others may have.

This is display-affecting, not just narration: whatever is in the asset is what
the reader sees.

    python tools/audit_asset_markup.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"

PATTERNS = {
    "escaped-tag":      re.compile(r"&lt;\s*/?\s*[a-zA-Z]"),   # &lt;note&gt;
    "raw-tag":          re.compile(r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*[\s>/]"),
    "named-entity":     re.compile(r"&(?:amp|lt|gt|quot|apos|nbsp|mdash|ndash);"),
    "numeric-entity":   re.compile(r"&#\d+;|&#x[0-9a-fA-F]+;"),
    "double-escaped":   re.compile(r"&amp;[a-z]+;"),
    "osis-ref":         re.compile(r"\bosisRef\b|\bsID\b|\beID\b"),
    "usfm-marker":      re.compile(r"\\[a-z]{1,3}\d?\s"),        # \v \c \q1
    "replacement-char": re.compile("�"),
    "control-char":     re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"),
}

def main():
    files = sorted(ASSETS.glob("*.json"))
    print(f"scanning {len(files)} assets in {ASSETS}\n")

    grand = Counter()
    dirty = []

    for path in files:
        try:
            books = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"{path.name}: UNREADABLE — {e}")
            continue
        if not isinstance(books, list) or not books or "chapters" not in books[0]:
            continue  # not a bible asset (lexicon, versemap, etc.)

        hits = Counter()
        examples = {}
        verses = 0
        for bk in books:
            name = bk.get("name", "?")
            for ci, ch in enumerate(bk.get("chapters", [])):
                for vi, v in enumerate(ch):
                    if not v:
                        continue
                    verses += 1
                    for label, pat in PATTERNS.items():
                        if pat.search(v):
                            hits[label] += 1
                            examples.setdefault(label, (name, ci + 1, vi + 1, v))

        if hits:
            dirty.append(path.name)
            total = sum(hits.values())
            print(f"=== {path.name}  ({verses:,} verses) — {total} hit(s)")
            for label, n in hits.most_common():
                bn, c, v, text = examples[label]
                snippet = text[:120].replace("\n", " ")
                print(f"    {label:<16} x{n:<5} e.g. {bn} {c}:{v}")
                print(f"        {snippet}")
            print()
            grand.update(hits)

    print("=" * 70)
    if not dirty:
        print("CLEAN — no markup leakage in any asset.")
    else:
        print(f"assets with markup: {len(dirty)} of {len(files)}")
        for name in dirty:
            print(f"    {name}")
        print("\ntotals by pattern:")
        for label, n in grand.most_common():
            print(f"    {label:<16} {n}")

if __name__ == "__main__":
    main()
