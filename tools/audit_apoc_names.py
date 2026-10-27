"""Audit: apocrypha book names left in ENGLISH in a non-English Bible asset.

For every translation registered in Bible.kt (`Translation("id", "bibles/x.json", ...)`),
every book in slots 66-82 that carries text and whose `name` equals en_kjv.json's
name for the same slot is reported. English assets (file name starting `en_`) are
skipped. A name that is legitimately identical in the target language (e.g. Latin
«Tobit») is listed in ALLOWED below, per asset and slot, with the reason.

    python tools/audit_apoc_names.py            # rc 0 = none, rc 1 = findings, rc 2 = could not run
    python tools/audit_apoc_names.py --selftest # known-bad control: must report a planted English name

0 tokens. Read-only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIBLE_KT = ROOT / "app/src/main/java/com/aleks/hexapla/Bible.kt"
ASSETS = ROOT / "app/src/main/assets"

# (asset id, slot) -> reason the English-identical name is the target language's own
ALLOWED = {
    ("vul", 69): "Judith - the Clementine Vulgate's own Latin title",
    ("vul", 72): "Baruch - the Latin title",
    ("kxii", 68): "Tobit - the Swedish name (sv.wikipedia «Apokryferna», Wikidata sv label)",
    ("kxii", 80): "Susanna - the Swedish name (Wikidata sv label; sv.wikipedia «Susanna i badet»)",
    ("kie", 68): "Tobit - Kadir Akın's Turkish running head (commit acd9dc5)",
}


def registered():
    src = BIBLE_KT.read_text(encoding="utf-8")
    return re.findall(r'Translation\("([a-z0-9_]+)",\s*"(bibles/[^"]+\.json)"', src)


def has_text(book):
    for ch in book.get("chapters", []):
        for v in ch:
            if isinstance(v, str) and v.strip():
                return True
    return False


def findings(assets, kjv_names):
    out = []
    for tid, rel in assets:
        if Path(rel).name.split("_")[0] in ("en", "enm"):  # English incl. Middle English (wyc)
            continue
        books = json.loads((ASSETS / rel).read_text(encoding="utf-8"))
        for slot in range(66, min(len(books), len(kjv_names))):
            b = books[slot]
            if b.get("name") == kjv_names[slot] and has_text(b) and (tid, slot) not in ALLOWED:
                out.append((tid, rel, slot, b["name"]))
    return out


def main():
    try:
        kjv = json.loads((ASSETS / "bibles/en_kjv.json").read_text(encoding="utf-8"))
        kjv_names = [b["name"] for b in kjv]
        assets = registered()
    except Exception as e:  # a check that cannot run did not pass
        print(f"ERROR: could not run: {e}")
        return 2
    if not assets:
        print("ERROR: no translations parsed from Bible.kt")
        return 2
    if "--selftest" in sys.argv:
        planted = [("t", "x", 70, "Wisdom of Solomon")]
        fake = [{"name": n, "chapters": [["x"]]} for n in kjv_names]
        tmp = ASSETS / "bibles/_selftest_apoc_names.json"
        try:
            tmp.write_text(json.dumps(fake), encoding="utf-8")
            got = findings([("selftest", "bibles/_selftest_apoc_names.json")], kjv_names)
        finally:
            tmp.unlink(missing_ok=True)
        ok = any(s == planted[0][2] for _, _, s, _ in got)
        print(f"selftest: planted English name {'REPORTED' if ok else 'MISSED'} ({len(got)} findings)")
        return 0 if ok else 1
    got = findings(assets, kjv_names)
    print(f"{len(assets)} registered translations checked, slots 66-82")
    for tid, rel, slot, name in got:
        print(f"  {tid:8s} {rel:34s} slot {slot:2d}  «{name}»")
    for (tid, slot), why in sorted(ALLOWED.items()):
        print(f"  allowed: {tid} slot {slot}: {why}")
    print(f"{len(got)} English apocrypha name(s) in non-English assets")
    return 1 if got else 0


if __name__ == "__main__":
    sys.exit(main())
