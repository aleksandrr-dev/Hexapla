# -*- coding: utf-8 -*-
"""Widen the TITUS credit from Armenian-only to Armenian AND Georgian.

    python tools/widen_titus_credit.py [--dry-run]

Prof. Gippert's grant covers BOTH the Zohrab Armenian and the Bakar Georgian,
and it carries a credit condition — so this is a REQUIRED credit, not a
courtesy (the Tweedale/Ponomar class, explicitly outside the "public domain
needs no credit" trim). CLAUDE.md's standing instruction is to WIDEN the
existing clause when Georgian ships rather than add a second line.

Three phrasings exist across the 25 locales: English (most of them), Russian,
and Georgian. Each is replaced by its widened form, and the script asserts it
found and changed exactly one clause per locale — a locale that silently kept
the Armenian-only wording would under-credit the grant.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RES = Path(__file__).parent.parent / "app" / "src" / "main" / "res"

SUBS = [
    ("Classical Armenian text via TITUS",
     "Classical Armenian and Georgian texts via TITUS"),
    ("Древнеармянский текст — проект TITUS",
     "Древнеармянский и грузинский тексты — проект TITUS"),
    ("კლასიკური სომხური ტექსტი — TITUS",
     "კლასიკური სომხური და ქართული ტექსტები — TITUS"),
]


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(RES.glob("values*/strings.xml"))
    changed, already, missing = [], [], []
    for f in files:
        s = f.read_text(encoding="utf-8")
        if "sources_text" not in s:
            continue
        if "TITUS" not in s:
            missing.append(f.parent.name)
            continue
        if any(new in s for _, new in SUBS):
            already.append(f.parent.name)
            continue
        hits = [(old, new) for old, new in SUBS if old in s]
        if len(hits) != 1:
            missing.append("%s (matched %d phrasings)" % (f.parent.name, len(hits)))
            continue
        old, new = hits[0]
        s2 = s.replace(old, new)
        assert s2 != s
        if not dry:
            f.write_text(s2, encoding="utf-8")
        changed.append(f.parent.name)

    print("widened   : %d locales" % len(changed))
    print("already   : %d" % len(already))
    if missing:
        print("⚠ NOT WIDENED (check these — the grant requires the credit):")
        for m in missing:
            print("    " + m)
    if dry:
        print("\n[dry-run] nothing written")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
