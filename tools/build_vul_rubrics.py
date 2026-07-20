# -*- coding: utf-8 -*-
"""Extract the Clementine Vulgate's editorial rubrics into a sidecar asset.

Reinstates (as STRUCTURE) the information tools/fix_vulgate_markers.py
stripped from la_vulgata.json on 2026-07-15: the <Sponsa>/<Sponsus>/<Chorus>
speaker rubrics of Canticum Canticorum, the <Aleph>..<Thau> acrostic letters
of Ps 118 (=119) and Lamentationes 1-4, and the two <Prologus> rubrics
(Lam 1:1, Sir 1:1). Print Clementine editions carry these as rubrics; the
owner approved surfacing them as structure "in a later version" — this is
that version's data half.

Source: the same clemtext .lat files convert_vulgate.py consumed
(Quasimodo.zip, sourceforge.net/projects/vulsearch, PD with acknowledgment
— already honored in sources_text).

Output: app/src/main/assets/rubrics_vul.json
    { "<book0>:<chapter1>:<verse1>": [[offset, "Label"], ...], ... }
book is the app's 0-based slot; chapter/verse are 1-based (the asset's
native Vulgate numbering, NOT KJV). offset is the character index into the
verse text AS SHIPPED where the rubric points (0 = start of verse); the
current UI renders labels above the verse and ignores offsets, but they are
recorded so a future inline renderer needs no re-extraction.

Every offset is verified by locating the cleaned post-marker snippet in the
shipped verse text (monotonic, must be found) — the script fails loudly on
any verse where the source and the shipped asset disagree.

    python tools/build_vul_rubrics.py <clemtext-source-dir>
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "la_vulgata.json")
OUT = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
       / "rubrics_vul.json")

# Book slots for the files that carry markers (subset of convert_vulgate's).
SLOTS = {"Ps": 18, "Ct": 21, "Lam": 24, "Sir": 71}

MARKERS = [
    "Aleph", "Beth", "Ghimel", "Daleth", "He", "Vau", "Zain", "Heth", "Teth",
    "Jod", "Caph", "Lamed", "Mem", "Nun", "Samech", "Ain", "Phe", "Sade",
    "Coph", "Res", "Sin", "Thau", "Tau",
    "Sponsa", "Sponsus", "Chorus", "Chorus Fratrum", "Chorus Adolescentularum",
    "Prologus",
]
PATTERN = re.compile(r"<(" + "|".join(re.escape(m) for m in sorted(MARKERS, key=len, reverse=True)) + r")>")


def clean(t):
    """convert_vulgate.py's text cleanup."""
    t = t.replace("/", " ").replace("\\", " ").replace("[", "").replace("]", "")
    return re.sub(r"\s+", " ", t).strip()


def parse_book(path):
    chapters = {}
    last = None
    for line in io.open(path, encoding="latin-1"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+):(\d+)\s+(.*)$", line)
        if not m:
            assert last is not None, (path, line)
            chapters[last[0]][last[1]] += " " + line
            continue
        c, v, text = int(m.group(1)), int(m.group(2)), m.group(3)
        chapters.setdefault(c, {})[v] = text
        last = (c, v)
    return chapters


def main():
    src = Path(sys.argv[1])
    asset = json.load(open(ASSET, encoding="utf-8"))

    out = {}
    total = 0
    for abbr, slot in SLOTS.items():
        chapters = parse_book(src / (abbr + ".lat"))
        for c, vs in chapters.items():
            for v, raw in vs.items():
                if "<" not in raw:
                    continue
                labels = PATTERN.findall(raw)
                stray = re.findall(r"<[^>]*>", PATTERN.sub("", raw))
                assert not stray, (abbr, c, v, stray)
                shipped = asset[slot]["chapters"][c - 1][v - 1]
                assert PATTERN.search(shipped) is None, (abbr, c, v, "asset still has markers?")
                # locate each marker: the cleaned text that FOLLOWS it must be
                # findable in the shipped verse, monotonically.
                entries = []
                pos = 0
                parts = PATTERN.split(raw)  # [pre, label1, seg1, label2, ...]
                for j in range(1, len(parts), 2):
                    label = parts[j]
                    after = clean("".join(parts[j + 1::2]))  # rest of the verse, markers gone
                    snippet = after[:30]
                    if snippet:
                        off = shipped.find(snippet, pos)
                        assert off >= 0, (abbr, c, v, label, snippet, shipped[:80])
                        pos = off
                    else:
                        off = len(shipped)  # trailing marker (none expected)
                    entries.append([off, label])
                assert [e[1] for e in entries] == labels, (abbr, c, v)
                assert all(a[0] <= b[0] for a, b in zip(entries, entries[1:])), (abbr, c, v, entries)
                out[f"{slot}:{c}:{v}"] = entries
                total += len(entries)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    dist = Counter(l for es in out.values() for _, l in es)
    print(f"{OUT.name}: {total} rubrics across {len(out)} verses, "
          f"{len(dist)} distinct, {OUT.stat().st_size} bytes")
    for m, n in dist.most_common():
        print(f"    {m}  x{n}")


if __name__ == "__main__":
    main()
