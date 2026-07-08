"""Chronological 1-year reading plan: curated (book, chapter) ordering.

Own curation (not copied from any published plan), anchored to internal
biblical evidence, cross-checked against Blue Letter Bible's chronological
plan as a helper. Events order, KJV/TR-tradition dating conventions:

- Job between Gen 11 and 12 (patriarchal setting; Job 42:16).
- Psa 90-91 before Deu 33-34 (Psa 90 title: "A Prayer of Moses").
- Davidic psalms threaded through Samuel by superscription anchors
  (Psa 59 = 1Sa 19; 56/34 = 1Sa 21; 142/52 = 1Sa 22; 54/63 = 1Sa 23;
  57 = 1Sa 24; 51/32 = 2Sa 12; 3 = 2Sa 15; 18 = 2Sa 22; 30 = 1Ch 21-22).
  Psa 96/105/106 at the ark (quoted in 1Ch 16). Undated Davidic psalms
  grouped thematically within David's reign; Psa 2 is David's per Acts
  4:25, Psa 95 per Heb 4:7.
- Psa 132 & 135-136 at the temple dedication (2Ch 6:41-42 quotes 132:8-10;
  the refrain of 136 is sung in 2Ch 5:13; 7:3). Psa 72/127 = Solomon.
- Psa 89 after the kingdom splits (Ethan the Ezrahite, 1Ki 4:31, laments
  the humbled crown). Psa 46-48/83 after 2Ch 20 (sons of Korah and of
  Asaph at Jehoshaphat's deliverance, 2Ch 20:14,19; the enemy list of
  Psa 83 matches). Psa 80 at the fall of Samaria; 75-76 at Sennacherib's
  rout (Asaph school, 2Ch 29:30); 74/79/137 with Lamentations; 102 with
  Dan 9 ("the set time to favour Zion"); 107/85/87/126 at the return;
  119 with Ezra the scribe (Ezr 7:10); remaining Songs of Ascents with
  Nehemiah's walls; 146-150 as the post-exile hallelujah finale.
- Prophets at their date formulas: Joel at Joash (traditional early date);
  Jonah/Amos under Jeroboam II (2Ki 14:25; Amo 1:1); Hosea before Samaria
  falls; Isaiah interleaved at 6:1/7:1/36-39, chs 40-66 kept with Isaiah
  in Hezekiah's days (one Isaiah); Obadiah after Jerusalem falls (Oba
  11-14; cf. Psa 137:7). Jeremiah re-ordered by its own reign headings;
  Ezekiel split at the fall (1-24 dated 593-588; 33:21 the news arrives);
  Daniel by its date lines (7:1 and 8:1 under Belshazzar precede ch 5;
  9:1/6 under Darius; 10:1 third year of Cyrus, after the return begins).
- 1Ch 1-9 (Adam to the returned exiles) as the post-exilic bridge before
  Ezra. Esther between Ezr 6 and Ezr 7 (Ahasuerus, 483-473 BC).
- Gospels harmonized at chapter level (events, not composition dates);
  epistles threaded through Acts at their writing points (Jas after Act
  12; Gal after the council; 1-2Th from Corinth, Act 18; 1Co from
  Ephesus, 1Co 16:8; 2Co from Macedonia; Rom from Greece, Act 20:2-3;
  prison epistles after Act 28; then 1Ti/Tit/1Pe/Heb/2Ti/2Pe/Jde;
  John's epistles and Revelation last.

Outputs the compact order string for ChronoOrder.kt and verifies that
every canon chapter appears exactly once against en_kjv.json, and that
the anchor verses actually say what the placements assume.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

BOOKS = ("Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh "
         "Est Job Psa Pro Ecc Sng Isa Jer Lam Eze Dan Hos Joe Amo Oba Jon "
         "Mic Nah Hab Zep Hag Zec Mal Mat Mar Luk Jhn Act Rom 1Co 2Co Gal "
         "Eph Phl Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jo 2Jo 3Jo "
         "Jde Rev").split()

# One token per line-part: "Abbr n", "Abbr a-b", or "Abbr a,b,c" (mixable).
ORDER = """
Gen 1-11
Job 1-42
Gen 12-50
Exo 1-40
Lev 1-27
Num 1-36
Deu 1-32
Psa 90,91
Deu 33-34
Jos 1-24
Jdg 1-21
Rut 1-4
1Sa 1-18
Psa 59
1Sa 19-20
1Sa 21
Psa 56,34
1Sa 22
Psa 142,52
1Sa 23
Psa 54,63
1Sa 24
Psa 57
1Sa 25-26
Psa 7
Psa 5,11,12,13,14,17,22,25,26,27,28,31,35,64,69,86,109,140,141,143
1Sa 27-31
1Ch 10
2Sa 1-4
2Sa 5
1Ch 11-12
Psa 2,101,110
2Sa 6
1Ch 13-16
Psa 96,105,106
Psa 8,15,19,24,29,33,65,66,67,68,93,95,97,98,99,100,104
2Sa 7
1Ch 17
Psa 16,23,36,39,62,84
2Sa 8-9
1Ch 18
Psa 60,108
2Sa 10
1Ch 19
Psa 9,10,20,21,44
2Sa 11-12
1Ch 20
Psa 51,32,38,6
2Sa 13-15
Psa 3,4,55
2Sa 16-18
Psa 41,61,70
2Sa 19-21
Psa 40,58
2Sa 22
Psa 18
2Sa 23-24
1Ch 21
Psa 30
1Ch 22-25
Psa 1,42,43,45,49,50,53,73,77,78,81,82,88,92,94,103,111,112,113,114,115,116,117,118,122,124,131,133,138,139,144,145
1Ch 26-29
1Ki 1-2
Psa 37,71
1Ki 3
2Ch 1
Psa 72
1Ki 4
Sng 1-8
1Ki 5-6
2Ch 2-3
1Ki 7
2Ch 4
1Ki 8
2Ch 5
Psa 132
2Ch 6-7
Psa 135,136
1Ki 9
2Ch 8
Psa 127
Pro 1-31
1Ki 10
2Ch 9
Ecc 1-12
1Ki 11
1Ki 12-14
2Ch 10-12
Psa 89
1Ki 15
2Ch 13-16
1Ki 16
2Ch 17
1Ki 17-19
1Ki 20-21
1Ki 22
2Ch 18
2Ch 19-20
Psa 46,47,48,83
2Ki 1-2
2Ki 3-4
2Ki 5-7
2Ki 8
2Ch 21
2Ki 9-10
2Ch 22
2Ki 11-12
2Ch 23-24
Joe 1-3
2Ki 13
2Ki 14
2Ch 25
Jon 1-4
Amo 1-9
2Ki 15
2Ch 26
Isa 1-6
2Ch 27
Mic 1-7
2Ki 16
2Ch 28
Isa 7-12
Hos 1-14
2Ki 17
Psa 80
2Ch 29-31
Isa 13-27
Isa 28-35
2Ki 18-19
2Ch 32
Isa 36-37
Psa 75,76
2Ki 20
Isa 38-39
Isa 40-66
2Ki 21
2Ch 33
Nah 1-3
2Ki 22
2Ch 34
Zep 1-3
Jer 1-6
2Ki 23
2Ch 35
Hab 1-3
Jer 26
Jer 7-10
Jer 11-20
Jer 22-23
Jer 25
Jer 46-47
Dan 1
Jer 36
Jer 45
Dan 2
Jer 35
Jer 48-49
Dan 3
2Ki 24
Jer 24
Jer 29
Jer 27-28
Jer 50-51
Eze 1-24
Jer 21
Jer 34
Jer 30-31
Jer 32-33
Jer 37-38
2Ki 25
2Ch 36
Jer 39
Jer 52
Lam 1-5
Oba 1
Psa 74,79,137
Jer 40-44
Eze 25-32
Eze 33-39
Eze 40-48
Dan 4
Dan 7-8
Dan 5
Dan 9
Psa 102
Dan 6
1Ch 1-9
Ezr 1-3
Psa 107,85,87,126
Dan 10-12
Ezr 4
Hag 1-2
Zec 1-8
Ezr 5-6
Zec 9-14
Est 1-10
Ezr 7-10
Psa 119
Neh 1-7
Psa 120,121,123,125,128,129,130,134
Neh 8-10
Neh 11-13
Psa 146-150
Mal 1-4
Luk 1
Mat 1
Luk 2
Mat 2
Mat 3
Mar 1
Luk 3
Jhn 1
Mat 4
Luk 4-5
Jhn 2-4
Jhn 5
Mar 2
Mat 12
Mar 3
Luk 6
Mat 5-7
Mat 8
Luk 7
Mat 11
Luk 8
Mar 4-5
Mat 13
Mat 9
Mat 10
Mat 14
Mar 6
Luk 9
Jhn 6
Mat 15
Mar 7
Mat 16
Mar 8
Mat 17
Mar 9
Mat 18
Jhn 7-8
Jhn 9-10
Luk 10-11
Luk 12-13
Luk 14-15
Luk 16-17
Jhn 11
Luk 18
Mat 19
Mar 10
Mat 20
Luk 19
Jhn 12
Mat 21
Mar 11
Mat 22
Mar 12
Luk 20
Mat 23
Mat 24
Mar 13
Luk 21
Mat 25
Mat 26
Mar 14
Luk 22
Jhn 13
Jhn 14-17
Mat 27
Mar 15
Luk 23
Jhn 18-19
Mat 28
Mar 16
Luk 24
Jhn 20-21
Act 1-8
Act 9-12
Jas 1-5
Act 13-15
Gal 1-6
Act 16-18
1Th 1-5
2Th 1-3
Act 19
1Co 1-16
2Co 1-13
Rom 1-16
Act 20-28
Eph 1-6
Col 1-4
Phm 1
Phl 1-4
1Ti 1-6
Tit 1-3
1Pe 1-5
Heb 1-13
2Ti 1-4
2Pe 1-3
Jde 1
1Jo 1-5
2Jo 1
3Jo 1
Rev 1-22
"""

# (abbr, chapter, must-contain regex) — placements rest on these verses.
ANCHORS = [
    ("Psa", 90, r"Prayer of Moses"),
    ("Psa", 59, r"Saul sent, and they watched the house"),
    ("Psa", 56, r"Philistines took him in Gath"),
    ("Psa", 34, r"behaviour before Abimelech"),
    ("Psa", 142, r"in the cave"),
    ("Psa", 52, r"Doeg the Edomite"),
    ("Psa", 54, r"Ziphims"),
    ("Psa", 63, r"wilderness of Judah"),
    ("Psa", 57, r"in the cave"),
    ("Psa", 51, r"Nathan the prophet came unto him"),
    ("Psa", 3, r"fled from Absalom"),
    ("Psa", 18, r"from the hand of Saul"),
    ("Psa", 30, r"dedication of the house of David"),
    ("Psa", 60, r"Aramnaharaim"),
    ("Psa", 72, r"for Solomon"),
    ("Psa", 127, r"for Solomon"),
    ("Psa", 137, r"rivers of Babylon"),
    ("Psa", 126, r"turned again the captivity of Zion"),
    ("Psa", 102, r"set time,? is come"),
    ("1Ki", 4, r"Ethan the Ezrahite"),
    ("2Ki", 14, r"Jonah"),
    ("2Ch", 20, r"sons? of Asaph"),
    ("2Ch", 29, r"words of David, and of Asaph the seer"),
    ("2Ch", 6, r"arise, O LORD God, into thy resting place"),
    ("Jer", 25, r"fourth year of Jehoiakim"),
    ("Jer", 51, r"fourth year of his reign"),
    ("Eze", 33, r"The city is smitten"),
    ("Eze", 40, r"five and twentieth year of our captivity"),
    ("Dan", 7, r"first year of Belshazzar"),
    ("Dan", 8, r"third year of the reign of king Belshazzar"),
    ("Dan", 9, r"first year of Darius"),
    ("Dan", 10, r"third year of Cyrus"),
    ("Ezr", 7, r"seek the law of the LORD"),
    ("1Co", 16, r"tarry at Ephesus"),
]


def parse_order():
    seq = []
    for line in ORDER.strip().splitlines():
        abbr, spec = line.split()
        b = BOOKS.index(abbr)
        for part in spec.split(","):
            if "-" in part:
                lo, hi = part.split("-")
                seq += [(b, c) for c in range(int(lo), int(hi) + 1)]
            else:
                seq.append((b, int(part)))
    return seq


def main():
    kjv = json.load(open(KJV, encoding="utf-8"))
    counts = [len(b["chapters"]) for b in kjv[:66]]
    seq = parse_order()

    seen = set()
    for b, c in seq:
        assert 1 <= c <= counts[b], f"{BOOKS[b]} {c} out of range (max {counts[b]})"
        assert (b, c) not in seen, f"duplicate: {BOOKS[b]} {c}"
        seen.add((b, c))
    missing = [(BOOKS[b], c) for b in range(66)
               for c in range(1, counts[b] + 1) if (b, c) not in seen]
    assert not missing, f"missing chapters: {missing[:20]}"
    assert len(seq) == sum(counts) == 1189, len(seq)

    for abbr, ch, pat in ANCHORS:
        text = " ".join(kjv[BOOKS.index(abbr)]["chapters"][ch - 1])
        assert re.search(pat, text), f"anchor failed: {abbr} {ch} ~ /{pat}/"
    print(f"OK: {len(seq)} chapters, each exactly once; "
          f"{len(ANCHORS)} anchor verses verified against the KJV text.")

    # Compact Kotlin string: "book:ch" / "book:lo-hi" tokens (0-based book,
    # 1-based chapters), runs merged across input lines where contiguous.
    tokens = []
    i = 0
    while i < len(seq):
        b, c = seq[i]
        j = i
        while j + 1 < len(seq) and seq[j + 1] == (b, seq[j][1] + 1):
            j += 1
        tokens.append(f"{b}:{c}" if i == j else f"{b}:{c}-{seq[j][1]}")
        i = j + 1
    out = " ".join(tokens)
    print(f"{len(tokens)} tokens, {len(out)} chars")
    dst = os.path.join(HERE, "chrono_order.txt")
    with open(dst, "w") as f:
        f.write(out + "\n")
    print("wrote", dst)


if __name__ == "__main__":
    main()
