# -*- coding: utf-8 -*-
"""Assemble values-ka/strings.xml from the per-part translation fragments.

    python tools/assemble_ka_locale.py <fragment-dir>

The Georgian UI was translated in three parts by separate translators working
from a shared glossary. This merges them back into one resource file IN THE
ENGLISH FILE'S OWN KEY ORDER — not in fragment order — so the result is
diffable against any other locale, and asserts that every expected key arrived
exactly once.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).parent.parent
RES = REPO / "app" / "src" / "main" / "res"
BASE = RES / "values" / "strings.xml"
OUT = RES / "values-ka" / "strings.xml"
# app_name deliberately falls back to the product name, as in every locale but ru
SKIP = {"app_name"}
LINE = re.compile(r'<string name="([^"]+)"[^>]*>(.*?)</string>', re.S)


def main():
    frag_dir = Path(sys.argv[1])
    base_src = BASE.read_text(encoding="utf-8")
    order = [m.group(1) for m in LINE.finditer(base_src)]
    base = {m.group(1): m.group(2) for m in LINE.finditer(base_src)}

    got, dupes = {}, []
    for f in sorted(frag_dir.glob("ka_part*.xml")):
        for m in LINE.finditer(f.read_text(encoding="utf-8")):
            k, v = m.group(1), m.group(2)
            if k in got:
                dupes.append(k)
            got[k] = v

    want = [k for k in order if k not in SKIP]
    missing = [k for k in want if k not in got]
    extra = [k for k in got if k not in base]
    print("fragments      : %d files" % len(list(frag_dir.glob("ka_part*.xml"))))
    print("keys expected  : %d" % len(want))
    print("keys received  : %d" % len(got))
    if dupes:
        print("⚠ DUPLICATE keys across fragments: %s" % sorted(set(dupes)))
    if extra:
        print("⚠ keys not in the English base: %s" % extra)
    if missing:
        print("⚠ MISSING (%d): %s" % (len(missing), missing[:20]))

    ph = re.compile(r"%\d\$[sd]|%[sd]")
    bad = []
    for k in want:
        if k in got and sorted(ph.findall(base[k])) != sorted(ph.findall(got[k])):
            bad.append((k, ph.findall(got[k]), ph.findall(base[k])))
    if bad:
        print("⚠ PLACEHOLDER MISMATCH:")
        for k, a, b in bad:
            print("    %s: got %s, English has %s" % (k, a, b))

    if missing or bad or extra or dupes:
        print("\nNOT WRITTEN — fix the above first.")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join('    <string name="%s">%s</string>' % (k, got[k]) for k in want)
    OUT.write_text('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n\n'
                   + body + "\n</resources>\n", encoding="utf-8")
    print("\nwrote %s (%d strings)" % (OUT, len(want)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
