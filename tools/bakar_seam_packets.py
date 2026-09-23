# -*- coding: utf-8 -*-
"""Emit one evidence packet per unresolved Bakar seam site.

    python tools/bakar_seam_packets.py <outdir>

Each packet is self-contained: the chapter's label stream in DOCUMENT order,
every unit's full text, and the KJV chapter beside it as a reference grid. It
exists so the seam decisions are made from evidence rather than from arithmetic
— see research/BAKAR_BUILD_LOG.md for why counting does not settle these.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets" / "bibles"
RAW = Path("C:/Projects/Hexapla-releases/titus_bakar/extracted/bakar_raw.json")

# (part, chapter) -> (KJV slot, KJV chapter) for the reference grid.
# Daniel 14 is Bel and the Dragon, which the KJV grid carries in its own slot.
SITES = {
    (8, "41"): (0, 41), (9, "8"): (1, 8), (9, "30"): (1, 30),
    (9, "31"): (1, 31), (12, "32"): (4, 32), (13, "17"): (5, 17),
    (16, "23"): (8, 23), (18, "4"): (10, 4), (18, "10"): (10, 10),
    (18, "12"): (10, 12), (18, "21"): (10, 21), (21, "29"): (13, 29),
    (33, "17"): (19, 17), (39, "51"): (23, 51), (44, "33"): (25, 33),
    (45, "6"): (26, 6), (45, "14"): (81, 1), (58, "4"): (75, 4),
    (63, "1"): (41, 1), (37, "37"): (71, 37), (37, "41"): (71, 41),
}
LABEL = {8: "Genesis", 9: "Exodus", 12: "Deuteronomy", 13: "Joshua",
         16: "1 Samuel", 18: "3 Kingdoms (=1 Kings)", 21: "2 Chronicles",
         33: "Proverbs", 37: "Sirach", 39: "Jeremiah", 44: "Ezekiel",
         45: "Daniel", 58: "1 Maccabees", 63: "Luke"}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    kjv = json.loads((ASSETS / "en_kjv.json").read_text(encoding="utf-8"))

    for (part, ck), (kb, kc) in sorted(SITES.items()):
        book = raw["books"]["part%03d" % part]
        ch = book["chapters"][ck]
        name = LABEL.get(part, book["book_label"])
        lines = []
        lines.append("# SEAM SITE: %s chapter %s   (TITUS part%03d)" % (name, ck, part))
        lines.append("")
        lines.append("## Label stream, in the order the print carries them")
        lines.append("")
        lines.append(" ".join(repr(k) for k in ch["verses"]))
        lines.append("")
        lines.append("## Every unit, in document order")
        lines.append("")
        for vk, t in ch["verses"].items():
            t = re.sub(r"\s+", " ", t.replace("*", "").replace("//", "")).strip()
            lines.append("[%s] %s" % (vk, t))
            lines.append("")
        lines.append("## KJV %s %d — the reference grid (English)" % (kjv[kb]["name"], kc))
        lines.append("")
        try:
            ref = kjv[kb]["chapters"][kc - 1]
        except IndexError:
            ref = []
        for i, t in enumerate(ref, 1):
            lines.append("(%d) %s" % (i, t))
        (out / ("%s_%s.md" % (name.split()[0].replace("(", ""), ck))).write_text(
            "\n".join(lines), encoding="utf-8")
    print("wrote %d packets to %s" % (len(SITES), out))


if __name__ == "__main__":
    main()
