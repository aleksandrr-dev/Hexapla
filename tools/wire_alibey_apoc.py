# -*- coding: utf-8 -*-
"""Wire the 1665 Ali Bey apocrypha (Kadir Akın's transliteration) into the
Turkish column. 0 tokens. DRY RUN BY DEFAULT.

    python tools/wire_alibey_apoc.py            # plan: prints every change, writes nothing
    python tools/wire_alibey_apoc.py --apply    # writes, then re-reads and verifies

Owner 2026-09-28 (docs/SETTLED.md): «go ahead and include the ali bey,
permission fine»; «Credit is enough» - Akın's credit in `sources_text` only,
no column note, no relabel of the 1827 Kieffer column.

What it does (input: _work/alibey_apoc/tr_alibey_apoc.json, built by
tools/build_tr_alibey_apoc.py --write):
  1. bibles/tr_kieffer.json: 66 books -> 83, slots 66-82 appended the way
     sv_karlxii.json holds them (same English slot names; a slot the print
     lacks - 73 Epistle of Jeremiah = Baruch 6, 82 Laodiceans - is an empty
     chapter list). The 66 canonical books are left byte-for-byte as they were
     (checked: their re-serialisation must equal the original's).
  2. rubrics_kie.json: the two Sirach prologues as rubrics on 71:1:1
     (Rubrics.kt keyed format). Refuses to overwrite an existing file.
  3. sources_text in every values*/strings.xml: one sentence crediting Akın,
     inserted after the SENIE/CLARIN-LV (Glück) sentence. A locale without
     that anchor is a FAILURE, not a skip.
The Rubrics.kt "kie" row is a Kotlin edit, done by hand.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "app/src/main/assets"
KIE = ASSETS / "bibles/tr_kieffer.json"
SV = ASSETS / "bibles/sv_karlxii.json"
RUB = ASSETS / "rubrics_kie.json"
SRC = Path("C:/Projects/Hexapla-releases/_work/alibey_apoc/tr_alibey_apoc.json")
RES = REPO / "app/src/main/res"
CREDIT = ("Ali Bey Bobowski's 1665 Turkish Apocrypha: Latin-script transliteration "
          "\u00a9 Kadir Ak\u0131n, used by permission.")
# end of the Glück sentence: «... SENIE/CLARIN-LV corpus, CC BY-SA 4.0.» in every locale's own words
ANCHOR = re.compile(r"CLARIN-LV[^.<]*?CC BY-SA 4\.0\.")


def fail(msg):
    sys.exit("FAIL: " + msg)


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main():
    apply = "--apply" in sys.argv
    raw = KIE.read_text(encoding="utf-8")
    kie = json.loads(raw)
    sv = json.loads(SV.read_text(encoding="utf-8"))
    src = json.loads(SRC.read_text(encoding="utf-8"))
    if len(kie) != 66:
        fail(f"tr_kieffer.json has {len(kie)} books, expected 66 (already wired?)")
    if len(sv) != 83:
        fail("sv_karlxii.json is not 83 books - the slot template moved")
    if dump(kie) != raw.strip():
        print("note: tr_kieffer.json is not in compact form; canonical books will be re-serialised")
    by_slot = {b["slot"]: b for b in src["books"]}
    new = list(kie)
    total = 0
    for slot in range(66, 83):
        name = sv[slot]["name"]
        b = by_slot.get(slot)
        if b and b["name"] != name:
            fail(f"slot {slot}: source says {b['name']!r}, grid says {name!r}")
        chs = b["chapters"] if b else []
        n = sum(1 for ch in chs for v in ch if (v or "").strip())
        total += n
        print(f"  slot {slot:2} {name:22} {len(chs):3} chapters {n:5} verses")
        new.append({"name": name, "chapters": chs})
    print(f"  TOTAL {total} verses into slots 66-82")
    # the 66 canonical books must be untouched
    if dump(new[:66]) != dump(kie):
        fail("canonical books changed")

    rub = src.get("rubrics") or {}
    if list(rub) != ["71:1:1"] or len(rub["71:1:1"]) != 2:
        fail(f"rubrics unexpected: {list(rub)}")
    if RUB.exists():
        fail(f"{RUB.name} exists - move it aside first")
    print(f"  {RUB.name}: 71:1:1 x{len(rub['71:1:1'])} rows "
          f"({', '.join(str(len(r[1])) for r in rub['71:1:1'])} chars)")

    edits = {}
    for f in sorted(RES.glob("values*/strings.xml")):
        with open(f, encoding="utf-8", newline="") as fh:   # keep CRLF as it is
            t = fh.read()
        m = re.search(r'<string name="sources_text">(.*?)</string>', t, re.S)
        if not m:
            continue
        body = m.group(1)
        if "Kadir Ak" in body:
            fail(f"{f.parent.name}: credit already present")
        a = ANCHOR.search(body)
        if not a:
            fail(f"{f.parent.name}: no Glück/CLARIN-LV anchor in sources_text")
        cred = CREDIT.replace("'", "\\'")
        nb = body[:a.end()] + " " + cred + body[a.end():]
        edits[f] = t[:m.start(1)] + nb + t[m.end(1):]
    print(f"  sources_text: {len(edits)} locale files get «{CREDIT}»")
    for f in list(edits)[:3]:
        t = edits[f]
        i = t.index("Kadir")
        print(f"    {f.parent.name}: ...{t[i-120:i+40]}...")

    if not apply:
        print("DRY RUN - nothing written. --apply to write.")
        return 0

    KIE.write_text(dump(new), encoding="utf-8")
    RUB.write_text(dump(rub), encoding="utf-8")
    for f, t in edits.items():
        f.write_text(t, encoding="utf-8", newline="")
    # verify on re-read
    back = json.loads(KIE.read_text(encoding="utf-8"))
    got = sum(1 for b in back[66:] for ch in b["chapters"] for v in ch if (v or "").strip())
    if len(back) != 83 or got != total or dump(back[:66]) != dump(kie):
        fail(f"re-read: {len(back)} books, {got} apocrypha verses (want 83 / {total})")
    if json.loads(RUB.read_text(encoding="utf-8")) != rub:
        fail("rubrics re-read differs")
    bad = [f.parent.name for f in edits if "Kadir Ak\u0131n" not in f.read_text(encoding="utf-8")]
    if bad:
        fail(f"credit missing on re-read: {bad}")
    print(f"VERIFIED ON RE-READ: 83 books, {got} apocrypha verses, rubrics, {len(edits)} credits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
