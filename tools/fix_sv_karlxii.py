"""Re-versify sv_karlxii.json to true KJV numbering (2026-07-11).

The shipped asset (Beblia = the CrossWire SweKarlXII1873 text, verified
byte-identical) squeezes the Karl XII Bible's continental numbering into
a KJV-shaped grid: at every continental chapter-boundary divergence it
leaves an EMPTY slot (27 of them) while the displaced verses sit one
slot off in the next chapter and the overflow is MERGED into a nearby
verse (e.g. Jonah 2:10 held both "Men jag vill offra…" [KJV 2:9] and
"…han utsputade Jona in uppå landet" [KJV 2:10]; Job 39:30 held NINE
KJV verses). No text is actually missing — it only needs redistributing.

Method: split the 15 merged donor verses at curated boundaries (each
verified against the KJV meaning), then re-flow each affected book's
verse sequence — which is in exact KJV order once split — into the KJV
chapter/verse grid, eliminating the empty slots.

Epistle colophons ("Den andra Epistel till de Corinthier, sänd af…")
are authentic Karl XII edition content and are kept, as in the other
five epistles that already carry them.

Usage: python fix_sv_karlxii.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLES = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")
SV = os.path.join(BIBLES, "sv_karlxii.json")
KJV = os.path.join(BIBLES, "en_kjv.json")

# (book, chapter, verse) -> markers; text from each marker onward
# becomes the next verse. Verified against the shipped text.
SPLITS = {
    (3, 13, 33): ["Vi såge der ock tyranner"],                       # KJV Num 13:33
    (3, 30, 16): ["Desse äro de stadgar"],                           # Num 30:16
    (8, 24, 22): ["Och David svor Saul;"],                           # 1 Sam 24:22
    (17, 39, 30): [                                                  # KJV Job 39:28-30 + 40:1-5
        "I bergklippon bor han",
        "Dädan af skådar han efter mat",
        "Hans ungar supa blod",
        "Och Herren svarade Job, och sade:",
        "Den som vill träta med den Allsmägtiga",
        "Job svarade Herranom, och sade:",
        "Si, jag hafver bannats",
        "Jag hafver en gång talat",
    ],
    (17, 40, 24): [                                                  # KJV Job 41:6-9
        "Menar du, att sällskapet",
        "Kan du fylla ena not",
        "När du kommer dina hand vid honom",
        "Si, hans hopp skall fela honom",
    ],
    (20, 4, 16): ["Bevara din fot"],                                 # Eccl 5:1
    (20, 7, 29): ["Allena skåda härtill:"],                          # Eccl 7:29
    (21, 5, 16): ["Hvart är då din vän gången"],                     # Song 6:1
    (26, 3, 30): [                                                   # Dan 4:1-3
        "Konung NebucadNezar, allom landom",
        "Mig synes godt vara",
        "Ty hans tecken äro stor",
    ],
    (27, 14, 9): ["Ho är vis,"],                                     # Hos 14:9
    (31, 2, 10): ["Och Herren sade till fisken"],                    # Jonah 2:10
    (36, 2, 23): ["På den samma tiden, säger Herren Zebaoth, skall jag taga dig"],  # Hag 2:23
    (43, 13, 51): ["Och Lärjungarna vordo uppfyllde"],               # Acts 13:52
    (43, 19, 40): ["Och då han det sagt hade"],                      # Acts 19:41
    (46, 13, 12): ["helsa eder all helgon"],                         # 2 Cor 13:13
}

# First words expected at repaired positions (book, ch, verse, prefix).
CHECKS = [
    (3, 12, 16, "Sedan drog folket ifrå Hazeroth"),
    (3, 13, 33, "Vi såge der ock tyranner"),
    (8, 23, 29, "Och David drog med dädan"),
    (17, 38, 39, "Kan du gifva lejinnone hennes rof"),
    (17, 40, 1, "Och Herren svarade Job, och sade:"),
    (17, 40, 6, "Och Herren svarade Job utur ett väder"),
    (17, 41, 1, "Kan du draga Leviathan med en krok"),
    (17, 41, 10, "Ingen är så dristig"),
    (20, 5, 1, "Bevara din fot"),
    (21, 6, 1, "Hvart är då din vän gången"),
    (21, 6, 13, "Vänd om, vänd om, o Sulamith"),
    (26, 4, 1, "Konung NebucadNezar, allom landom"),
    (26, 4, 4, "Jag NebucadNezar, då jag god ro hade"),
    (27, 13, 16, "Samarien skall öde varda"),
    (31, 1, 17, "Och Herren förskaffade en stor fisk"),
    (31, 2, 10, "Och Herren sade till fisken"),
    (36, 1, 15, "På fjerde och tjugonde dagen i sjette månadenom"),
    (43, 13, 52, "Och Lärjungarna vordo uppfyllde"),
    (43, 19, 41, "Och då han det sagt hade"),
    (46, 13, 14, "Vårs Herras Jesu Christi nåd"),
]


def main():
    sv = json.load(open(SV, encoding="utf-8"))
    kjv = json.load(open(KJV, encoding="utf-8"))

    for (bi, c, v), markers in SPLITS.items():
        ch = sv[bi]["chapters"][c - 1]
        t = ch[v - 1]
        parts, rest = [], t
        for m in reversed(markers):
            i = rest.index(m)  # raises if the shipped text changed
            parts.insert(0, rest[i:])
            rest = rest[:i].rstrip()
        ch[v - 1: v] = [rest] + parts

    affected = sorted({bi for bi, _, _ in SPLITS})
    for bi in affected:
        want = [len(c) for c in kjv[bi]["chapters"]]
        flat = [v for ch in sv[bi]["chapters"] for v in ch if v.strip()]
        assert len(flat) == sum(want), (bi, len(flat), sum(want))
        out, i = [], 0
        for n in want:
            out.append(flat[i:i + n])
            i += n
        sv[bi]["chapters"] = out

    # gates
    for bi in range(66):
        assert [len(c) for c in sv[bi]["chapters"]] == \
               [len(c) for c in kjv[bi]["chapters"]], sv[bi]["name"]
        for ch in sv[bi]["chapters"]:
            for v in ch:
                assert v.strip(), (sv[bi]["name"], "empty verse")
    for bi, c, v, prefix in CHECKS:
        got = sv[bi]["chapters"][c - 1][v - 1]
        assert got.startswith(prefix), (sv[bi]["name"], c, v, got[:60])
    total = sum(len(c) for b in sv for c in b["chapters"])
    assert total == 31102, total

    with open(SV, "w", encoding="utf-8") as f:
        json.dump(sv, f, ensure_ascii=False, separators=(",", ":"))
    print(f"sv_karlxii.json re-versified: {total} verses, KJV grid, no empty slots")


if __name__ == "__main__":
    main()
