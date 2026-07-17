"""Generate assets/versemap.json — verse-level alignment of every
translation's native versification to the KJV backbone (2026-07-11).

The app's pairing features (split view, Compare, cross-references, red
letters, Topics) are KJV-indexed. Translations that keep their authentic
native numbering (Luther, Synodal, the Hebrew WLC, Martin, Wycliffe,
Elizabeth, Meiji, Byzantine NT, and the 3 John / Rev 12:18 tails in
Geneva/Almeida/CUV) need an explicit map; rewriting their text would
break how their readers cite scripture (Пс 50:3 must stay Пс 50:3).

Map model, per translation per book: a list of runs
    [kjv_ch, kjv_v0, kjv_v1, trans_ch, trans_v0, trans_v1]   (1-based)
Equal-length runs pair verse-for-verse; unequal runs are blocks whose
verses concatenate on display (psalm titles, merges); trans_v0 > trans_v1
encodes an omission (Meiji Luke 17:36). Multiple runs may share a KJV
verse (Rev 13:1 <- trans 12:18 + 13:1). Anything not listed is identity.

Derivation:
  1. LXX psalter (Synodal/Elizabeth, 151 psalms): seam-accurate chapter
     map (9=9+10, 113=114+115, 114/115=116, 146/147=147) + per-psalm
     title offsets, all verified by count arithmetic.
  2. Same-book repartition: where a book's total verse count equals the
     KJV's and only chapter boundaries differ (the Hebrew-tradition
     shifts: Gen 31/32, Lev 5/6, Num, Job 38-41, Jonah, Joel 2/3 ...),
     runs derive from cumulative pairing.
  3. Psalm titles outside the LXX psalter: +1/+2 leading title verses
     merge into KJV v1 as a block.
  4. Curated exceptions (each verified against the actual verse text —
     see the EXTRA table): continental merges/splits, the Byzantine
     Romans doxology (KJV 16:25-27 = Byz 14:24-26), Meiji's documented
     committee omissions, bracketed LXX additions in Synodal Proverbs,
     end-of-book LXX extras (Josh 24:34-36, Ps 151, Dan 13-14).

Usage: python build_versemap.py
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLES = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")
OUT = os.path.join(HERE, "..", "app", "src", "main", "assets", "versemap.json")

IDS = {
    "syn": "ru_synodal", "csl": "cu_elizabeth", "lut": "de_luther",
    "wlc": "he_wlc", "mar": "fr_martin", "wyc": "enm_wycliffe",
    "mei": "ja_meiji", "grc": "grc_byz", "gen1599": "en_geneva",
    "alm": "pt_almeida", "cus": "zh_cuv_s", "cuv": "zh_cuv_t",
    "san": "sa_nt",
    "ta": "ta_irv",
    "vul": "la_vulgata",
    "vd": "ar_vandyck",
    "fi76": "fi_biblia1776",
    "gda": "pl_gdanska",
    "srb": "sr_karadzic",
    "kar": "hu_karoli",
    "bkr": "cs_kralicka",
    "arm": "hy_west1853",
}

# Curated non-mechanical alignments, verified against verse text.
# (id-list, book, [(kc,kv0,kv1, tc,tv0,tv1), ...]) — these PRE-EMPT the
# mechanical engines for that (translation, book).
STD_TAIL = [  # continental 3 John split + Rev 12:18
    (63, [(1, 14, 14, 1, 14, 15)]),
    (65, [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)]),
]
EXTRA = {
    # Byzantine/Slavonic Romans doxology at 14:24-26
    ("grc", "syn", "csl"): {
        44: [(16, 25, 27, 14, 24, 26)],
    },
    ("syn", "csl"): {
        2: [(14, 55, 56, 14, 55, 55), (14, 57, 57, 14, 56, 56)],   # Lev 55+56 merged
        5: [(6, 1, 1, 5, 16, 16), (6, 2, 27, 6, 1, 26)],           # Josh 6:1 = ru 5:16
        8: [(20, 42, 42, 20, 42, 43),                              # ru splits 20:42
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],       # 23:29 = ru 24:1
        22: [(3, 19, 20, 3, 19, 19), (3, 21, 26, 3, 20, 25)],      # Isa 3 ornament merge
        19: [(13, 14, 25, 13, 15, 26), (18, 8, 24, 18, 9, 25)],    # Prov: [13:14]/[18:8] LXX insertions
        21: [(1, 1, 1, 1, 1, 0), (1, 2, 17, 1, 1, 16),             # Song: no title verse
             (6, 13, 13, 7, 1, 1), (7, 1, 13, 7, 2, 14)],          # 6:13 = ru 7:1
        46: [(11, 32, 33, 11, 32, 32), (13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],
        43: [(19, 40, 41, 19, 40, 40)],                            # Acts 19:40+41
        63: [(1, 14, 14, 1, 14, 15)],
    },
    ("mar",): {
        8: [(20, 42, 42, 20, 42, 43),                               # Martin splits 20:42
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],        # 23:29 = fr 24:1
        10: [(22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],   # Martin splits 22:43
        40: [(9, 50, 50, 9, 50, 51), (10, 52, 52, 10, 52, 53)],    # Mark splits
        44: [(3, 22, 23, 3, 22, 22), (3, 24, 31, 3, 23, 30),       # Rom 3:22+23 merged
             (8, 20, 21, 8, 20, 20), (8, 22, 39, 8, 21, 38)],      # Rom 8:20+21 merged
        45: [(3, 22, 23, 3, 22, 22)],                               # 1 Cor 3 merge
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],   # 2 Cor 13 merge
        43: [(24, 18, 18, 24, 18, 19), (24, 19, 27, 24, 20, 28),   # Martin splits 24:18
             (19, 40, 41, 19, 40, 40)],                             # Acts 19 merge
        63: [(1, 14, 14, 1, 14, 15)],
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
    },
    # Wycliffe follows the Vulgate: mostly single-verse merges (two KJV
    # verses in one), plus the Vulgate Daniel arrangement (Song of the
    # Three at 3:24-90, so KJV 3:24-30 sit at 3:91-97; Susanna/Bel in
    # ch13-14 stay unmapped, as do Esther's additions 10:4-16:24).
    # Each run verified by reading the Middle English against the KJV;
    # shared with the Clementine Vulgate itself ("vul", added 1.4.3 —
    # every shared run re-verified against the Latin, see the eyeball
    # report; vul's Daniel comes from the LXX special-case below and
    # its Rev 12:18 tail from the ("vul",) entry).
    # Wycliffe-only: its digitization holds Gen 5:32 in wyc 6:1; the
    # Clementine instead merges it into 5:31 (see the ("vul",) entry).
    ("wyc",): {
        0: [(5, 32, 32, 6, 1, 1), (6, 1, 1, 6, 1, 1),               # Gen 5:32 merged into wyc 6:1
            (49, 31, 32, 49, 31, 31), (49, 33, 33, 49, 32, 32),     # Vulgate has no separate 49:32
            (50, 22, 23, 50, 22, 22), (50, 24, 26, 50, 23, 25)],    # 50:22+23 merged
    },
    ("wyc", "vul"): {
        1: [(40, 13, 15, 40, 13, 13), (40, 16, 38, 40, 14, 36)],    # Exod 40:13-15 condensed to one
        2: [(26, 45, 46, 26, 45, 45)],                              # Lev 26:46 colophon merged into 45
        8: [(23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],        # 23:29 = wyc 24:1 (wyc 20:43 is an empty slot)
        12: [(11, 46, 47, 11, 46, 46), (20, 7, 8, 20, 7, 7)],       # 1 Chr name-list merges
        15: [(3, 30, 31, 3, 30, 30), (3, 32, 32, 3, 31, 31),        # Neh 3:30+31 merged
             (12, 33, 34, 12, 33, 33), (12, 35, 47, 12, 34, 46)],   # Neh 12:33+34 merged
        21: [(1, 1, 1, 1, 1, 0), (1, 2, 17, 1, 1, 16),              # Song: no title verse
             (6, 1, 1, 5, 17, 17), (6, 2, 13, 6, 1, 12)],           # KJV 6:1 = wyc 5:17
        23: [(37, 4, 5, 37, 4, 4), (37, 6, 21, 37, 5, 20)],         # Jer 37:4+5 merged
        25: [(2, 9, 10, 2, 9, 9)],                                  # Ezek 2:9+10 merged
        26: [(3, 24, 30, 3, 91, 97), (4, 1, 3, 3, 98, 100),
             (4, 4, 37, 4, 1, 34)],
        27: [(2, 23, 23, 2, 23, 24),                                # Hos 2:23 split into 23+24
             (13, 16, 16, 14, 1, 1), (14, 1, 9, 14, 2, 10)],        # 13:16 = wyc 14:1
        32: [(5, 11, 12, 5, 11, 11), (5, 13, 15, 5, 12, 14)],       # Mic 5:11+12 merged
        39: [(17, 14, 15, 17, 14, 14), (17, 16, 27, 17, 15, 26)],   # Matt 17:14+15 merged
        40: [(4, 40, 41, 4, 40, 40),                                # Mark 4:40+41 merged
             (9, 1, 1, 8, 39, 39), (9, 2, 50, 9, 1, 49)],           # KJV 9:1 = wyc 8:39
        43: [(7, 55, 56, 7, 55, 55), (7, 57, 60, 7, 56, 59),        # Acts 7:55+56 merged
             (14, 6, 7, 14, 6, 6), (14, 8, 28, 14, 7, 27),          # Acts 14:6+7 merged
             (19, 40, 41, 19, 40, 40)],                             # Acts 19:40+41 merged
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],   # 2 Cor 13 continental merge
    },
    ("mei",): {
        41: [(17, 36, 36, 17, 1, 0), (17, 37, 37, 17, 36, 36)],    # Luke 17:36 omitted
        43: [(15, 34, 34, 15, 1, 0), (15, 35, 41, 15, 34, 40),     # Acts 15:34 omitted
             (20, 37, 38, 20, 37, 37)],                             # Acts 20:37+38 merged
    },
    ("gen1599", "alm", "cus", "cuv"): {b: runs for b, runs in STD_TAIL},
    # Sanskrit 1851 NT: continental 3 John split only. The source's
    # Rev 12:18 is a bare "[]" placeholder (content sits in 13:1,
    # KJV-style) — dropped by convert_sanskrit_nt.py, so Revelation
    # needs no map.
    ("san",): {
        63: [(1, 14, 14, 1, 14, 15)],
    },
    # Tamil IRV 2019: continental 3 John split only — everything else
    # sits on the KJV grid (convert_tamil_irv.py: zero empty slots,
    # zero other extras; the source's Rev 12:17-18 bridge prints the
    # KJV arrangement, its vacuous 18 dropped at conversion).
    # Van Dyck Arabic: exact KJV grid except two text-verified native
    # splits — 1 Tim 6:21 -> 21+22 (the grace-benediction «اَلنِّعْمَةُ
    # مَعَكَ. آمِينَ» numbered as its own v22) and the continental
    # 3 John 14/15. Rev 12/13 is KJV-shaped (no Rev entry needed).
    ("vd",): {
        53: [(6, 21, 21, 6, 21, 22)],
        63: [(1, 14, 14, 1, 14, 15)],
    },
    # Biblia 1776: exact KJV grid except the two standard continental
    # tails — 3 Jn 14/15 and a real Rev 12:18 («Ja minä seisoin meren
    # sannalla») pairing with KJV 13:1. Both text-verified 2026-07-16.
    ("fi76",): {
        63: [(1, 14, 14, 1, 14, 15)],
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
    },
    # Western Armenian NT 1853: every seam read against the KJV
    # 2026-07-17 (session scripts arm_*.py; convert_armwestern.py's
    # docstring has the full map). Native merges incl. the classical
    # Acts 7/8 and Mark 8/9 chapter boundaries (KJV 9:1 = arm 8:39,
    # restored from the module's squeeze by a verified split); Luke
    # splits KJV 4:38, John splits KJV 6:51; KJV Jn 10:41 spans arm
    # 41-42.
    ("arm",): {
        39: [(17, 14, 15, 17, 14, 14), (17, 16, 27, 17, 15, 26)],
        40: [(9, 1, 1, 8, 39, 39), (9, 2, 50, 9, 1, 49)],
        41: [(4, 38, 38, 4, 38, 39), (4, 39, 42, 4, 40, 43),
             (4, 43, 44, 4, 44, 44)],
        42: [(6, 51, 51, 6, 51, 52), (6, 52, 69, 6, 53, 70),
             (6, 70, 71, 6, 71, 71), (10, 41, 41, 10, 41, 42)],
        43: [(7, 55, 56, 7, 55, 55), (7, 57, 60, 7, 56, 59),
             (8, 1, 1, 7, 59, 59), (8, 1, 1, 8, 1, 1),
             (14, 6, 7, 14, 6, 6), (14, 8, 28, 14, 7, 27),
             (19, 40, 41, 19, 40, 40)],
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],
        51: [(4, 11, 12, 4, 11, 11), (4, 13, 18, 4, 12, 17)],
        57: [(13, 24, 25, 13, 24, 24)],
    },
    # Bible kralická 1613: 29 non-psalm native chapters, every seam
    # text-verified 2026-07-17 (62 title-psalms are mechanical). Notable
    # vs its cousins: the lion verses STAY in Job 38 (KJV 40:1-5 = bkr
    # 39:31-35); Eccl straddles KJV 8:1 across bkr 7:30 + 8:1; Haggai
    # has the Hebrew 1:15=2:1 seam; Exod 2:11+12 merge.
    ("bkr",): {
        1: [(2, 11, 12, 2, 11, 11), (2, 13, 25, 2, 12, 24)],
        3: [(12, 16, 16, 13, 1, 1), (13, 1, 33, 13, 2, 34),
            (29, 40, 40, 30, 1, 1), (30, 1, 16, 30, 2, 17)],
        8: [(20, 42, 42, 20, 42, 43),
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],
        10: [(22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],
        17: [(31, 40, 40, 31, 40, 41),
             (37, 1, 1, 36, 34, 34), (37, 2, 24, 37, 1, 23),
             (40, 1, 5, 39, 31, 35), (40, 6, 24, 40, 1, 19),
             (41, 1, 9, 40, 20, 28), (41, 10, 34, 41, 1, 25)],
        20: [(8, 1, 1, 7, 30, 30), (8, 1, 1, 8, 1, 1)],
        21: [(6, 1, 1, 5, 17, 17), (6, 2, 13, 6, 1, 12)],
        26: [(4, 1, 3, 3, 31, 33), (4, 4, 37, 4, 1, 34)],
        31: [(1, 17, 17, 2, 1, 1), (2, 1, 10, 2, 2, 11)],
        36: [(1, 15, 15, 2, 1, 1), (2, 1, 23, 2, 2, 24)],
        42: [(1, 38, 38, 1, 38, 39), (1, 39, 51, 1, 40, 52)],
        43: [(19, 40, 41, 19, 40, 40)],
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],
        63: [(1, 14, 14, 1, 14, 15)],
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
    },
    # Károli 1908 (Calvin/continental numbering): seams text-verified
    # 2026-07-17. Job is the Luther arrangement except ch 41 returns to
    # identity (kar 40 = KJV 40:6-24 only). Psalms are fully mechanical
    # (62 title psalms, +1/+2). Remaining total-matching books go to the
    # repartition engine; its pair report was eyeballed before trusting.
    ("kar",): {
        1: [(36, 1, 1, 35, 36, 36), (36, 2, 38, 36, 1, 37)],
        3: [(12, 16, 16, 13, 1, 1), (13, 1, 33, 13, 2, 34)],
        8: [(20, 42, 42, 20, 42, 43),
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],
        10: [(22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],
        17: [(17, 1, 1, 16, 23, 23), (17, 2, 16, 17, 1, 15),
             (37, 1, 1, 36, 34, 34), (37, 2, 24, 37, 1, 23),
             (38, 39, 41, 39, 1, 3), (39, 1, 30, 39, 4, 33),
             (40, 1, 5, 39, 34, 38), (40, 6, 24, 40, 1, 19)],
        19: [(12, 1, 1, 11, 32, 32), (12, 2, 28, 12, 1, 27)],
        20: [(1, 18, 18, 2, 1, 1), (2, 1, 26, 2, 2, 27),
             (8, 16, 17, 9, 1, 2), (9, 1, 18, 9, 3, 20),
             (10, 1, 3, 9, 21, 23), (10, 4, 20, 10, 1, 17),
             (11, 9, 10, 12, 1, 2), (12, 1, 14, 12, 3, 16)],
        21: [(6, 1, 3, 5, 17, 19), (6, 4, 13, 6, 1, 10)],
        22: [(2, 22, 22, 3, 1, 1), (3, 1, 26, 3, 2, 27),
             (4, 1, 1, 3, 28, 28), (4, 2, 6, 4, 1, 5),
             (64, 1, 2, 64, 1, 1), (64, 3, 12, 64, 2, 11)],
        26: [(4, 1, 3, 3, 31, 33), (4, 4, 37, 4, 1, 34)],
        27: [(2, 1, 1, 1, 12, 12), (2, 2, 23, 2, 1, 22),
             (13, 16, 16, 14, 1, 1), (14, 1, 9, 14, 2, 10)],
        31: [(1, 17, 17, 2, 1, 1), (2, 1, 10, 2, 2, 11)],
        41: [(23, 56, 56, 23, 56, 57)],
        42: [(1, 38, 38, 1, 38, 39), (1, 39, 51, 1, 40, 52)],
        43: [(19, 40, 41, 19, 40, 40)],
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],
        63: [(1, 14, 14, 1, 14, 15)],
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
    },
    # Karadžić/Daničić Serbian (eBible srp1865): 17 native-divergent
    # chapters, every seam text-verified 2026-07-17 (research report +
    # session notes). Mostly Hebrew/German chapter boundaries; the Job
    # reflow is Luther's arrangement, verified at every boundary (srp
    # 39:1 = KJV 38:39 lion-hunt, srp 39:38 = KJV 40:5 "once have I
    # spoken", srp 40:28 = KJV 41:9, srp 41:25 = KJV 41:34).
    ("srb",): {
        3: [(12, 16, 16, 13, 1, 1), (13, 1, 33, 13, 2, 34),
            (29, 40, 40, 30, 1, 1), (30, 1, 16, 30, 2, 17)],
        8: [(20, 42, 42, 20, 42, 43),
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],
        10: [(22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],
        17: [(38, 39, 41, 39, 1, 3), (39, 1, 30, 39, 4, 33),
             (40, 1, 5, 39, 34, 38), (40, 6, 24, 40, 1, 19),
             (41, 1, 9, 40, 20, 28), (41, 10, 34, 41, 1, 25)],
        21: [(6, 1, 1, 5, 17, 17), (6, 2, 13, 6, 1, 12)],
        25: [(20, 45, 49, 21, 1, 5), (21, 1, 32, 21, 6, 37)],
        27: [(11, 12, 12, 12, 1, 1), (12, 1, 14, 12, 2, 15)],
        31: [(1, 17, 17, 2, 1, 1), (2, 1, 10, 2, 2, 11)],
        63: [(1, 14, 14, 1, 14, 15)],
    },
    # Biblia Gdańska: every run below text-verified 2026-07-16 against the
    # CrossWire module (same wording, KJV-shaped) via SequenceMatcher
    # alignment — the 1.0-ratio merges are the source's own native
    # numbering, NOT drops (the four proven drops were repaired at
    # conversion instead; see convert_gdanska.py). 3 Jn 14/15 and
    # Rev 12:18 arrive pre-merged to the KJV grid — no runs needed.
    ("gda",): {
        2: [(24, 23, 23, 24, 23, 24)],                              # Lev 24:23 split
        3: [(29, 40, 40, 30, 1, 1), (30, 1, 16, 30, 2, 17)],        # Num 29:40 = gda 30:1
        8: [(20, 42, 42, 20, 42, 43)],                              # 1 Sam 20:42 split
        18: [(51, 1, 1, 51, 1, 2), (51, 2, 19, 51, 3, 20),          # double superscriptions
             (52, 1, 1, 52, 1, 2), (52, 2, 9, 52, 3, 10),           # as their own verse 1
             (54, 1, 1, 54, 1, 2), (54, 2, 7, 54, 3, 8),            # (like the Synodal)
             (60, 1, 1, 60, 1, 2), (60, 2, 12, 60, 3, 13),
             (146, 1, 2, 146, 1, 1), (146, 3, 10, 146, 2, 9)],      # Ps 146:1-2 merged
        23: [(29, 31, 32, 29, 31, 31)],                             # Jer 29 tail merge
        43: [(19, 40, 41, 19, 40, 40)],                             # Acts 19:40+41 (as syn/mar)
        46: [(11, 32, 33, 11, 32, 32), (13, 13, 14, 13, 13, 13)],   # 2 Cor merges
        47: [(1, 23, 24, 1, 23, 23)],                               # Gal 1 tail merge
    },
    ("ta",): {
        63: [(1, 14, 14, 1, 14, 15)],
    },
    # Clementine Vulgate: Rev 12:18 is a real verse ("Et stetit supra
    # arenam maris") = KJV 13:1a, like Luther/Karl XII. Psalter (LXX),
    # Daniel and same-total OT reflows come from the engines; the runs
    # below are vul-specific splits ABSENT from the Wycliffe digitization
    # (found by the count audit, each verified against the Latin):
    # 1 Sam 20:42 "And he arose and departed" = vul 20:43 "Et surrexit
    # David"; 1 Kgs 22:43 "Nevertheless the high places" = vul 22:44
    # "Verumtamen excelsa"; Amos 6:10 "Hold thy tongue" tail = vul 6:11
    # "Tace, et non recorderis"; John 6:51 "if any man eat" = vul 6:52
    # "Si quis manducaverit".
    # The OT books below PRE-EMPT the repartition engine: their count
    # differences are LOCAL intra-chapter splits/merges, which flat
    # cumulative pairing would smear across every later chapter (found
    # by eyeballing the pair report; each run text-verified 2026-07-13).
    ("vul",): {
        0: [(5, 31, 32, 5, 31, 31),                                 # Gen 5:31 holds 5:32 ("Noë vero...")
            (49, 31, 32, 49, 31, 31), (49, 33, 33, 49, 32, 32),
            (50, 22, 23, 50, 22, 22), (50, 24, 26, 50, 23, 25)],
        3: [(11, 34, 35, 11, 34, 34),                               # Num 11:35 tail inside vul 11:34
            (12, 16, 16, 13, 1, 1), (13, 1, 33, 13, 2, 34),         # KJV 12:16 = vul 13:1
            (20, 28, 28, 20, 28, 29), (20, 29, 29, 20, 30, 30),     # Aaron's death split
            (29, 40, 40, 30, 1, 1), (30, 1, 16, 30, 2, 17)],        # KJV 29:40 = vul 30:1
        5: [(4, 23, 23, 4, 23, 24), (4, 24, 24, 4, 25, 25),         # Josh 4:23 split ("sicut... mari Rubro")
            (5, 14, 14, 5, 14, 15), (5, 15, 15, 5, 16, 16),         # 5:14 split ("Cecidit Josue...")
            (21, 36, 37, 21, 36, 36), (21, 38, 39, 21, 37, 37),     # Levite city pairs merged
            (21, 40, 45, 21, 38, 43)],
        6: [(5, 31, 31, 5, 31, 32),                                 # "land had rest" = vul 5:32
            (21, 24, 25, 21, 24, 24)],                              # "no king in Israel" inside 21:24
        8: [(20, 42, 42, 20, 42, 43)],
        10: [(22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],
        17: [(16, 4, 4, 16, 4, 5), (16, 5, 22, 16, 6, 23),          # Job 16:4 split
             (40, 1, 5, 39, 31, 35), (40, 6, 24, 40, 1, 19),        # the Vulgate Job 39-41 reflow
             (41, 1, 9, 40, 20, 28), (41, 10, 34, 41, 1, 25),
             (42, 16, 17, 42, 16, 16)],                             # "So Job died" inside 42:16
        29: [(6, 10, 10, 6, 10, 11), (6, 11, 14, 6, 12, 15)],
        42: [(6, 51, 51, 6, 51, 52), (6, 52, 71, 6, 53, 72)],
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
    },
    ("lut", "wlc"): {
        63: [(1, 14, 14, 1, 14, 15)],                               # (lut only; wlc lacks NT)
        65: [(13, 1, 1, 12, 18, 18), (13, 1, 1, 13, 1, 1)],
        3: [(16, 36, 50, 17, 1, 15), (17, 1, 13, 17, 16, 28),       # Num 16/17 boundary
            (26, 1, 1, 25, 19, 19), (26, 1, 1, 26, 1, 1),           # Heb 25:19 = KJV 26:1a
            (29, 40, 40, 30, 1, 1), (30, 1, 16, 30, 2, 17)],
        8: [(20, 42, 42, 20, 42, 42), (20, 42, 42, 21, 1, 1),       # KJV 20:42 = Heb 20:42+21:1
            (21, 1, 15, 21, 2, 16),
            (23, 29, 29, 24, 1, 1), (24, 1, 22, 24, 2, 23)],        # 23:29 = Heb 24:1
        10: [(4, 21, 34, 5, 1, 14), (5, 1, 18, 5, 15, 32),          # 1 Kgs 4/5 boundary
             (22, 43, 43, 22, 43, 44), (22, 44, 53, 22, 45, 54)],   # Heb splits 22:43
        11: [(11, 21, 21, 12, 1, 1), (12, 1, 21, 12, 2, 22)],       # 2 Kgs 11/12 boundary
             # (lut 15:39 is an empty trailing slot in the asset — unmapped)
        12: [(6, 1, 15, 5, 27, 41), (6, 16, 81, 6, 1, 66),          # 1 Chr 5/6 boundary
             (12, 4, 4, 12, 4, 5), (12, 5, 40, 12, 6, 41)],         # Heb splits 12:4
        15: [(4, 1, 6, 3, 33, 38), (4, 7, 23, 4, 1, 17),            # Neh 3/4 boundary
             (7, 72, 73, 7, 72, 72),                                 # KJV 7:73 ~ Heb 7:72
             (9, 38, 38, 10, 1, 1), (10, 1, 39, 10, 2, 40)],
        22: [(9, 1, 1, 8, 23, 23), (9, 2, 21, 9, 1, 20),            # Isa 8/9 boundary
             (64, 1, 1, 63, 19, 19), (64, 2, 12, 64, 1, 11)],       # KJV 64:1 = Heb 63:19b
        28: [(2, 28, 32, 3, 1, 5), (3, 1, 21, 4, 1, 21)],           # Joel: Heb has 4 chapters
        38: [(4, 1, 6, 3, 19, 24)],                                 # Malachi: Heb has 3 chapters
        46: [(13, 12, 13, 13, 12, 12), (13, 14, 14, 13, 13, 13)],   # (lut only)
        43: [(19, 40, 41, 19, 40, 40)],                              # (lut only)
    },
}

# Vulgate psalms whose count deviation is not a leading title — each
# verified against the Latin 2026-07-13:
#   Ps 2: KJV 2:12 ("Kiss the Son... Blessed are all") = vul 2:12-13
#     ("Apprehendite disciplinam..." + "Cum exarserit... beati omnes").
#   Ps 4: v1 title; KJV 1-4 = vul 2-5; KJV 5-8 reflowed across vul 6-10
#     (vul 6 = KJV 5 + 6a "Multi dicunt", vul 8 = KJV 7b "A fructu
#     frumenti", vul 9-10 split KJV 8) — kept as one block.
#   Ps 16: title inside vul 15:1; KJV 16:10-11 merged in vul 15:10
#     ("...videre corruptionem. Notas mihi fecisti vias vitæ...").
VUL_PSALTER = {
    2: [(2, 12, 12, 2, 12, 13)],
    4: [(4, 1, 1, 4, 1, 2), (4, 2, 4, 4, 3, 5), (4, 5, 8, 4, 6, 10)],
    16: [(16, 10, 11, 15, 10, 10)],
}


def load(n):
    return json.load(open(os.path.join(BIBLES, n + ".json"), encoding="utf-8"))


def counts(bible, bi):
    return [len(c) for c in bible[bi]["chapters"]]


def repartition_runs(tc_counts, kc_counts):
    """Cumulative pairing of two partitions of the same verse sequence."""
    runs = []
    ci_t, v_t = 0, 1
    for kc, kn in enumerate(kc_counts, start=1):
        kv = 1
        while kv <= kn:
            room_t = tc_counts[ci_t] - v_t + 1
            take = min(kn - kv + 1, room_t)
            if not (kc == ci_t + 1 and kv == v_t):
                runs.append((kc, kv, kv + take - 1, ci_t + 1, v_t, v_t + take - 1))
            kv += take
            v_t += take
            if v_t > tc_counts[ci_t] and ci_t + 1 < len(tc_counts):
                ci_t += 1
                v_t = 1
    return runs


def psalm_title_runs(ci, tn, kn):
    """Non-LXX psalter: leading title verse(s) merge into KJV v1."""
    extra = tn - kn
    assert extra in (1, 2), (ci + 1, tn, kn)
    return [(ci + 1, 1, 1, ci + 1, 1, 1 + extra),
            (ci + 1, 2, kn, ci + 1, 2 + extra, tn)]


def lxx_psalter_runs(trans, kjv, overrides=None):
    """151-psalm LXX psalter -> KJV 150, with seams + per-psalm titles.
    overrides: {kjv psalm: [runs]} for psalms whose surplus/deficit is
    NOT a leading title (Vulgate Ps 2/4/16) — text-verified curation."""
    t = [len(c) for c in trans[18]["chapters"]]
    k = [len(c) for c in kjv[18]["chapters"]]
    runs = []

    def straight(kc, tc):
        """One KJV psalm onto one LXX psalm (title offset 0/+1/+2)."""
        if overrides and kc in overrides:
            runs.extend(overrides[kc])
            return
        extra = t[tc - 1] - k[kc - 1]
        assert extra in (0, 1, 2), ("psalm", kc, tc, extra)
        if extra == 0 and kc == tc:
            return
        if extra:
            runs.append((kc, 1, 1, tc, 1, 1 + extra))
            runs.append((kc, 2, k[kc - 1], tc, 2 + extra, t[tc - 1]))
        else:
            runs.append((kc, 1, k[kc - 1], tc, 1, t[tc - 1]))

    def seam_two_into_one(kc1, kc2, tc):
        """KJV psalms kc1+kc2 both live in LXX psalm tc."""
        extra = t[tc - 1] - k[kc1 - 1] - k[kc2 - 1]
        assert extra in (0, 1, 2), ("seam", kc1, kc2, tc, extra)
        off = 1 + extra
        runs.append((kc1, 1, 1, tc, 1, off))
        runs.append((kc1, 2, k[kc1 - 1], tc, off + 1, off + k[kc1 - 1] - 1))
        base = off + k[kc1 - 1] - 1
        runs.append((kc2, 1, k[kc2 - 1], tc, base + 1, base + k[kc2 - 1]))

    def seam_one_into_two(kc, tc1, tc2):
        """KJV psalm kc split across LXX psalms tc1+tc2."""
        extra = t[tc1 - 1] + t[tc2 - 1] - k[kc - 1]
        assert extra in (0, 1, 2), ("split", kc, tc1, tc2, extra)
        n1 = t[tc1 - 1] - extra          # KJV verses inside tc1 after title
        if extra:
            runs.append((kc, 1, 1, tc1, 1, 1 + extra))
            runs.append((kc, 2, n1 + 1, tc1, 2 + extra, t[tc1 - 1]))
        else:
            runs.append((kc, 1, n1, tc1, 1, t[tc1 - 1]))
        runs.append((kc, n1 + 2 if extra else n1 + 1, k[kc - 1], tc2, 1, t[tc2 - 1]))

    seam_two_into_one(9, 10, 9)
    for kc in range(11, 114):
        straight(kc, kc - 1)
    seam_two_into_one(114, 115, 113)
    seam_one_into_two(116, 114, 115)
    for kc in range(117, 147):
        straight(kc, kc - 1)
    seam_one_into_two(147, 146, 147)
    for kc in range(148, 151):
        straight(kc, kc)
    for kc in range(1, 9):
        straight(kc, kc)
    return runs


def main():
    kjv = load("en_kjv")
    out = {}
    for tid, fname in IDS.items():
        trans = load(fname)
        books = {}
        curated = {}
        for ids, table in EXTRA.items():
            if tid in ids:
                for b, runs in table.items():
                    curated.setdefault(b, []).extend(runs)
        for bi in range(66):
            tcounts = counts(trans, bi)
            kcounts = counts(kjv, bi)
            if not any(tcounts):
                continue
            if tid in ("syn", "csl", "vul") and bi == 26:
                continue  # LXX Daniel handled below
            if bi in curated:
                runs = list(curated[bi])
                # complete the book: chapters not covered by curated runs
                # that still mismatch get repartitioned only if trivially
                # shifted — otherwise identity (verified below).
                books[bi] = runs
                continue
            if tcounts == kcounts:
                continue
            if bi == 18 and tcounts[8] >= kcounts[8] + kcounts[9]:
                # LXX/Vulgate psalter arrangement (Ps 9 = MT 9+10 ...)
                try:
                    books[bi] = lxx_psalter_runs(
                        trans, kjv, VUL_PSALTER if tid == "vul" else None)
                except AssertionError as e:
                    if tid != "wyc":
                        raise
                    print(f"  note: wyc psalter left identity ({e})")
                continue
            if bi == 18:
                runs = []
                for ci, (tn, kn) in enumerate(zip(tcounts, kcounts)):
                    if tn != kn:
                        runs.extend(psalm_title_runs(ci, tn, kn))
                books[bi] = runs
                continue
            # end-of-book/end-of-chapter extras: trans may have MORE chapters
            # (ru Dan 13-14, wyc Esther 11-16) or extra trailing verses.
            nch = min(len(tcounts), len(kcounts))
            if sum(tcounts[:nch]) == sum(kcounts[:nch]):
                books[bi] = repartition_runs(tcounts[:nch], kcounts[:nch])
                continue
            # remaining: chapters with equal counts stay identity; extra
            # TRAILING trans verses (LXX additions) stay unmapped; any
            # other shape must be curated — fail loudly, except for the
            # rough Middle-English Wycliffe where identity is accepted.
            deficits = [ci + 1 for ci in range(nch) if tcounts[ci] < kcounts[ci]]
            if deficits and tid != "wyc":
                raise SystemExit(f"{tid} book {bi}: unhandled shape (short chapters {deficits})")
            if deficits:
                print(f"  note: wyc book {bi} left identity (chapters {deficits} differ)")
        # LXX Daniel: ch13-14 (Susanna, Bel) are additions with no KJV
        # counterpart; ch3 carries the Song of the Three (3:24-90) so
        # KJV 3:24-30 sit at 3:91-97 and KJV 4:1-3 at 3:98-100, with
        # ch4 holding KJV 4:4-37 as 4:1-34.
        if tid in ("syn", "csl", "vul"):
            tdan, kdan = counts(trans, 26), counts(kjv, 26)
            for ci in range(12):
                if ci in (2, 3):
                    continue
                assert tdan[ci] == kdan[ci], (tid, "Dan", ci + 1, tdan[ci], kdan[ci])
            assert tdan[2] == kdan[2] + 70 and tdan[3] == kdan[3] - 3, \
                (tid, "Dan 3/4", tdan[2:4], kdan[2:4])
            books[26] = [(3, 24, 30, 3, 91, 97),
                         (4, 1, 3, 3, 98, 100),
                         (4, 4, 37, 4, 1, 34)]
        out[tid] = {str(b): [list(r) for r in rs] for b, rs in sorted(books.items()) if rs}

    # ---- validation ----
    for tid, fname in IDS.items():
        trans = load(fname)
        for b, runs in out[tid].items():
            bi = int(b)
            for kc, kv0, kv1, tc, tv0, tv1 in runs:
                assert 1 <= kc <= len(kjv[bi]["chapters"]), (tid, b, kc)
                assert kv1 <= len(kjv[bi]["chapters"][kc - 1]), (tid, b, kc, kv1)
                if tv0 <= tv1:  # not an omission
                    assert tc <= len(trans[bi]["chapters"]), (tid, b, tc)
                    assert tv1 <= len(trans[bi]["chapters"][tc - 1]), \
                        (tid, b, tc, tv1, len(trans[bi]["chapters"][tc - 1]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    n = sum(len(rs) for t in out.values() for rs in t.values())
    print(f"versemap.json: {len(out)} translations, {n} runs, {os.path.getsize(OUT)} bytes")

    # ---- eyeball report: first verse of every curated/seam run ----
    print("\n--- sample pairings for review ---")
    for tid in ("syn", "lut", "wlc", "mar", "mei", "grc"):
        trans = load(IDS[tid])
        shown = 0
        for b, runs in out[tid].items():
            bi = int(b)
            for kc, kv0, kv1, tc, tv0, tv1 in runs:
                if shown >= 8:
                    break
                kt = kjv[bi]["chapters"][kc - 1][kv0 - 1][:52]
                tt = ("<omitted>" if tv0 > tv1
                      else trans[bi]["chapters"][tc - 1][tv0 - 1][:52])
                print(f"{tid} b{bi} KJV {kc}:{kv0} '{kt}' <-> {tc}:{tv0} '{tt}'")
                shown += 1
            if shown >= 8:
                break


if __name__ == "__main__":
    main()
