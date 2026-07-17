# -*- coding: utf-8 -*-
"""krisek/HunKar raw OSIS (revideált Károli Biblia, 1590/1908) -> app asset.

Source: https://raw.githubusercontent.com/krisek/HunKar/master/
hunkaroli_rev.osis.xml — the CANONICAL upstream of the CrossWire HunKar
module; PD per hunkar.conf (DistributionLicense=Public Domain; 1908 text,
PD by age). Litmus 7/7 verified 2026-07-16 — research report:
Hexapla-releases/research/karoli_report.md.

⚠ NEVER build from the compiled SWORD module or scrollmapper's JSON: the
module's Versification=Calvin force-fit silently pads 44 fake empty
verses across 25 chapters and fuses 10 real verses of Job 41 into one
blob. The raw OSIS has none of that (verified in the research pass).

Handled here:
  * Container-style OSIS verses; <note>...</note> apparatus and section
    <title>s stripped; every residual tag asserted away.
  * Native Calvin/continental numbering KEPT (62 title-psalms, Joel 4
    chapters, Hebrew seams...) — build_versemap.py's mechanical engines
    (psalm_title_runs, repartition, seam maps) pivot it; curated runs
    added there where the engines need pre-empting.
  * THREE genuine content gaps in the raw OSIS — John 21:1, Acts 12:6,
    Acts 15:18, real narrative text absent entirely — PATCHED from the
    gratis-bible hu/hun.xml witness (same 1908 wording, verified by
    cross-matching John 21:2 across both witnesses), with its degraded
    Latin-1 Hungarian orthography normalized (õ->ő, û->ű) to match this
    source. The 1908 text is PD; three verses carry no transcription
    right. Each patch asserts the slot is still a gap first.
  * Book names: curated Hungarian (Károli tradition).

Usage: python convert_karoli.py <hunkaroli_rev.osis.xml> <hun.xml> <dst.json>
"""
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))

OSIS_ORDER = [
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam",
    "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov",
    "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos",
    "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
    "Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor", "Gal", "Eph",
    "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim", "Titus", "Phlm", "Heb",
    "Jas", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Rev",
]

NAMES_HU = [
    "1 Mózes", "2 Mózes", "3 Mózes", "4 Mózes", "5 Mózes",
    "Józsué", "Bírák", "Ruth", "1 Sámuel", "2 Sámuel",
    "1 Királyok", "2 Királyok", "1 Krónika", "2 Krónika", "Ezsdrás",
    "Nehémiás", "Eszter", "Jób", "Zsoltárok", "Példabeszédek",
    "Prédikátor", "Énekek éneke", "Ésaiás", "Jeremiás", "Jeremiás siralmai",
    "Ezékiel", "Dániel", "Hóseás", "Jóel", "Ámós",
    "Abdiás", "Jónás", "Mikeás", "Náhum", "Habakuk",
    "Sofóniás", "Aggeus", "Zakariás", "Malakiás",
    "Máté", "Márk", "Lukács", "János", "Apostolok cselekedetei",
    "Róma", "1 Korinthus", "2 Korinthus", "Galátzia", "Efézus",
    "Filippi", "Kolossé", "1 Thessalonika", "2 Thessalonika",
    "1 Timótheus", "2 Timótheus", "Titus", "Filemon", "Zsidók",
    "Jakab", "1 Péter", "2 Péter", "1 János", "2 János", "3 János",
    "Júdás", "Jelenések",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

GAPS = [("John", 21, 1), ("Acts", 12, 6), ("Acts", 15, 18)]
DEGRADED = str.maketrans({"õ": "ő", "û": "ű", "Õ": "Ő", "Û": "Ű"})


def clean(text):
    text = re.sub(r"<note\b.*?</note>", "", text, flags=re.S)
    text = re.sub(r"<title\b.*?</title>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&apos;", "'")
    text = re.sub(r"\s+", " ", text).strip()
    assert "<" not in text and ">" not in text, text[:80]
    return text


def parse_osis(raw):
    books = {}
    for m in re.finditer(r'<verse osisID="([^".]+)\.(\d+)\.(\d+)"[^>]*>(.*?)</verse>', raw, re.S):
        b, c, v = m.group(1), int(m.group(2)), int(m.group(3))
        books.setdefault(b, {}).setdefault(c, {})[v] = clean(m.group(4))
    return books


def convert(osis_path, witness_path, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    main = parse_osis(open(osis_path, encoding="utf-8").read())
    assert sorted(main) == sorted(OSIS_ORDER), sorted(main)[:5]

    wraw = open(witness_path, encoding="utf-8", errors="replace").read()

    def witness(vid):
        pat = vid.replace(".", r"\.")
        m = (re.search(r'<verse osisID="%s"[^>]*>(.*?)</verse>' % pat, wraw, re.S)
             or re.search(r"<verse osisID='%s'[^>]*>(.*?)</verse>" % pat, wraw, re.S))
        assert m, vid
        return clean(m.group(1)).translate(DEGRADED)

    # cross-witness sanity: John 21:2 must match across both sources
    j212 = witness("John.21.2")
    r = SequenceMatcher(None, j212, main["John"][21][2], autojunk=False).ratio()
    assert r > 0.93, ("witness lineage check failed", r)
    out.write(f"witness lineage check (John 21:2): ratio {r:.3f}\n")

    patched = 0
    for b, c, v in GAPS:
        assert v not in main[b][c], (b, c, v, "gap filled upstream — re-check")
        main[b][c][v] = witness(f"{b}.{c}.{v}")
        out.write(f"patched {b} {c}:{v}: {main[b][c][v][:70]}\n")
        patched += 1
    assert patched == 3

    books = []
    for bi, code in enumerate(OSIS_ORDER):
        chapters = main[code]
        assert sorted(chapters) == list(range(1, len(chapters) + 1)), code
        out_chapters = []
        for c in range(1, len(chapters) + 1):
            vs = chapters[c]
            assert sorted(vs) == list(range(1, max(vs) + 1)), (code, c, sorted(vs)[-3:])
            assert all(vs[v] for v in vs), (code, c, "empty verse")
            out_chapters.append([vs[v] for v in range(1, max(vs) + 1)])
        books.append({"name": NAMES_HU[bi], "chapters": out_chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verses (native "
              f"Calvin numbering, versemap pivots), {os.path.getsize(dst)} bytes\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2], sys.argv[3])
