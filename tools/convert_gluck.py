# -*- coding: utf-8 -*-
"""SENIE/CLARIN-LV corpus (Glück Bible: JT1685 NT + VD1689_94 OT) -> app asset.

Source: Senie-DSL-plaintext.zip from the CLARIN-LV repository
(repository.clarin.lv handle 20.500.12574/141) — the University of
Latvia's SENIE corpus of old written Latvian, CC BY-SA 4.0 (attribution
in sources_text ×13). Ernst Glück's own 1685 New Testament and 1689 Old
Testament in the ORIGINAL 17th-century orthography (ſ/ẜ, w for v,
virgule /) — shipped as printed, per the house precedent (Karl XII,
Luther 1545, Wycliffe). Litmus 7/7 (research report:
Hexapla-releases/research/gluck_report.md; re-verified on the asset).

STRUCTURE (full survey + seam-reading, 2026-07-17 session; scripts
lv_*.py in the session scratchpad):
  * DSL: @a/@z/@g/@k/@t/@l codes dropped (keep @n{N} chapters!); verse
    lines "  N. text" with print line-wrap hyphens joined; verse 0 =
    Reformation chapter ARGUMENT, dropped (Jes 37's argument spills
    into a second paragraph mislabeled "1." — special-cased).
  * "12{13}." = the transcription's TRUE{PRINTED} typo-correction
    notation; dotless labels accepted only at the expected position;
    remaining print-label typos repaired by POSITION (each logged,
    ≤2/chapter, e.g. Ezek 40's "9." where v2 belongs).
  * NATIVE CHAPTER DIVISIONS kept and versemap-curated: 1 Chr has 30
    chapters (KJV 4 split at the Simeonites, 4:23/24, print numbering
    continuing 24-44 across the seam; chapters 6-30 = KJV 5-29);
    Habakkuk has 4 (KJV 2 split at 2:4/5, labels continuing 5-20);
    1 Sam 3:22 = KJV 4:1a; Eccl uses Hebrew boundaries at 4/5 AND 6/7;
    Hos 13:16=14:1, Jonah 1:17=2:1, Hag 1:15=2:1, Dan 3/4 Hebrew seam;
    Job = the Luther arrangement (identical to the Serbian runs);
    the usual Num 12/13+29/30, 1 Sam 20/23-24, 1 Kgs 22:43 seams;
    Isa 53:2 split; Ezek 19:10+11 merged; Lev 15:22+23 and Num 6:22+23
    merged; Ezra 6:22 split; John 1:38 split; Acts 19:40+41 and
    2 Cor 13:12+13 merged; 3 Jn 15; Rev 12:18. Every seam text-read
    against the KJV before curation.
  * INLINE-MARKER MERGES SPLIT (the print merged two verses but kept
    the second number inline — exact anchors): 1 Chr 6:25 («26,»),
    1 Chr 12:3 («..4.») and 12:6 («..7.»), 2 Chr 32:19 («20.»).
  * ONE GENUINE OMISSION: Ezek 5:9 is absent from the print (its
    ch 5 labels skip 9; the surrounding verses are complete). Kept as
    a versemap omission, not padded.
  * Psalm superscriptions occupy their own numbered verse(s) — native,
    handled by build_versemap.py's mechanical title engine (62+ psalms,
    +1/+2 incl. the double-title 51/52/54/60).
The Apokr1689 apocrypha (same edition/license) is NOT converted yet —
versification unassessed; follow-up in CLAUDE.md.

Usage: python convert_gluck.py <senie_dir> <dst.json>
"""
import io
import json
import os
import re
import sys

NT = {"Mt": 39, "Mk": 40, "Lk": 41, "Jn": 42, "Apd": 43, "Rm": 44,
      "1Kor": 45, "2Kor": 46, "Gal": 47, "Ef": 48, "Fil": 49, "Kol": 50,
      "1Tes": 51, "2Tes": 52, "1Tim": 53, "2Tim": 54, "Tit": 55,
      "Flm": 56, "Ebr": 57, "Jk": 58, "1P": 59, "2P": 60, "1J": 61,
      "2J": 62, "3J": 63, "Jud": 64, "Atk": 65}
OT = {"1Moz": 0, "2Moz": 1, "3Moz": 2, "4Moz": 3, "5Moz": 4, "Joz": 5,
      "Sog": 6, "Rut": 7, "1Sam": 8, "2Sam": 9, "1Ken": 10, "2Ken": 11,
      "1L": 12, "2L": 13, "Ezr": 14, "Neh": 15, "Est": 16, "Ij": 17,
      "Ps": 18, "Sak": 19, "Mac": 20, "Dz": 21, "Jes": 22, "Jer": 23,
      "Rdz": 24, "Ech": 25, "Dan": 26, "Hoz": 27, "Jl": 28, "Am": 29,
      "Ob": 30, "Jon": 31, "Mih": 32, "Nah": 33, "Hab": 34, "Cef": 35,
      "Hag": 36, "Zah": 37, "Mal": 38}

NAMES_LV = [
    "1. Mozus", "2. Mozus", "3. Mozus", "4. Mozus", "5. Mozus",
    "Jozua", "Soģu grāmata", "Rute", "1. Samuēla", "2. Samuēla",
    "1. Ķēniņu", "2. Ķēniņu", "1. Laiku", "2. Laiku", "Ezra",
    "Nehemija", "Estere", "Ījabs", "Psalmi", "Salamana sakāmvārdi",
    "Mācītājs", "Dziesmu dziesma", "Jesaja", "Jeremija", "Raudu dziesmas",
    "Ecēchiēls", "Daniēls", "Hozeja", "Joēls", "Amos",
    "Obadja", "Jona", "Miha", "Nahums", "Habakuks",
    "Cefanja", "Hagajs", "Zaharja", "Maleachis",
    "Mateja evaņģēlijs", "Marka evaņģēlijs", "Lūkas evaņģēlijs",
    "Jāņa evaņģēlijs", "Apustuļu darbi", "Romiešiem",
    "1. Korintiešiem", "2. Korintiešiem", "Galatiešiem", "Efeziešiem",
    "Filipiešiem", "Kolosiešiem", "1. Tesaloniķiešiem",
    "2. Tesaloniķiešiem", "1. Timotejam", "2. Timotejam", "Titam",
    "Filemonam", "Ebrejiem", "Jēkaba", "1. Pētera", "2. Pētera",
    "1. Jāņa", "2. Jāņa", "3. Jāņa", "Jūdas", "Atklāsmes grāmata",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

VERSE_LINE = re.compile(r"^\s+(\d+)(?:\{\d+\})?(\.)?\s+(.*)$")

# (code, chapter, position-label): split the verse at the inline marker.
INLINE_SPLITS = {
    ("1L", 6, 25): r"\s*26[,.]\s*",
    ("1L", 12, 3): r"\s*\.*\s*4\.\s*",
    ("1L", 12, 6): r"\s*\.*\s*7\.\s*",
    ("2L", 32, 19): r"\s+20\.\s*",
}
# (code, chapter): labels legitimately skip these — either a genuine
# print omission (Ezek 5:9) or the number rides INLINE in the previous
# verse (the 1 Chr 12 merges, split back below).
OMISSION_SKIPS = {("Ech", 5): {9}, ("1L", 12): {4, 7}, ("2L", 32): {20}}
# native chapter-count expectations that differ from KJV
NATIVE_CHAPTERS = {"1L": 30, "Hab": 4}


def join_wrap(parts):
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out.endswith("-"):
            out = out[:-1] + p
        elif out:
            out += " " + p
        else:
            out = p
    # Text-level cleanup (surveyed on a full conversion 2026-07-17):
    #  * 215 word{word} = the transcription's TRUE{PRINTED} correction
    #    notation inside verse text — keep the corrected form, drop the
    #    braced print reading;
    #  * 462 "*" + one "|" = print footnote/reference anchors — drop;
    #  * 88,802 "/" virgules — the 17th-century comma, preserved
    #    diplomatically by SENIE. Every other period asset in the app
    #    (Karl XII, Luther 1545, Geneva, Wycliffe, Biblia 1776) ships
    #    its digitization's modernized commas, so the virgule becomes
    #    a comma here too (owner review of Mt 1, 2026-07-17). The
    #    reverential capitals (JESUS, KUNGS) stay — the de_luther
    #    JEsus/GOtt precedent.
    out = re.sub(r"\{[^}]*\}", "", out)
    out = out.replace("*", " ").replace("|", " ")
    out = re.sub(r"\s*/\s*", ", ", out)
    out = re.sub(r",\s+([.:;!?,])", r"\1", out)
    return re.sub(r"\s+", " ", out).strip()


def strip_codes(raw):
    """Remove @x{...} blocks (all except @n) with a depth counter — the
    footnote blocks can contain NESTED {corrections}, which a regex's
    [^}]* stops at, leaking the tail into verse text (56 instances on
    the first full conversion)."""
    out = []
    i = 0
    n = len(raw)
    while i < n:
        m = re.match(r"@(?!n\{)[a-z]\{", raw[i:])
        if m:
            j = i + m.end()
            depth = 1
            while j < n and depth:
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                j += 1
            i = j
        else:
            out.append(raw[i])
            i += 1
    return "".join(out)


def parse_book(coll_path, code, relabels):
    path = os.path.join(coll_path, code, f"{code}_Unicode.txt")
    raw = open(path, encoding="utf-8-sig").read()
    raw = strip_codes(raw)
    chapters = {}
    cur = None
    cur_verse = None       # position index within chapter (1-based)
    base_label = None
    buf = {}
    skipping = False
    for line in raw.splitlines():
        m = re.match(r"@n\{(\d+)\}", line.strip())
        if m:
            cur = int(m.group(1))
            assert cur not in chapters, (code, cur)
            chapters[cur] = buf = {}
            cur_verse = None
            base_label = None
            skipping = False
            continue
        if line.strip().startswith("@") or not line.strip():
            continue
        vm = VERSE_LINE.match(line)
        is_verse = vm is not None and cur is not None and (
            vm.group(2) or (base_label is not None and
                            int(vm.group(1)) == base_label + len(buf)))
        if is_verse:
            vn, text = int(vm.group(1)), vm.group(3)
            if vn == 0:
                skipping = True
                cur_verse = None
                continue
            # Jes 37: the chapter argument spills into a 2nd paragraph
            # mislabeled "1." — the REAL v1 is the next lbl-1 line.
            if code == "Jes" and cur == 37 and vn == 1 and buf and len(buf) == 1:
                relabels.append(f"{code} ch 37: argument paragraph mislabeled 1. dropped")
                buf.clear()
            skipping = False
            if base_label is None:
                base_label = vn      # 1L 5 starts at 24, Hab 3 at 5
                if vn != 1:
                    relabels.append(f"{code} ch {cur}: labels start at {vn} (native)")
            expected = base_label + len(buf)
            if vn != expected:
                if vn == expected + 1 and expected in OMISSION_SKIPS.get((code, cur), ()):
                    base_label += 1   # genuine print omission — shift window
                    relabels.append(f"{code} ch {cur}: label {expected} omitted by the print")
                else:
                    relabels.append(f"{code} ch {cur}: printed {vn}. accepted as {expected}.")
                    per = sum(1 for r in relabels
                              if r.startswith(f"{code} ch {cur}: printed"))
                    assert per <= 2, (code, cur, "too many label anomalies")
                    vn = expected
            pos = len(buf) + 1
            buf[pos] = [text]
            cur_verse = pos
        elif not skipping and cur_verse is not None and cur is not None:
            buf[cur_verse].append(line)
    out = {}
    for c, vs in chapters.items():
        verses = [join_wrap(vs[p]) for p in sorted(vs)]
        # inline-marker splits
        for (sc, sch, slabel), anchor in INLINE_SPLITS.items():
            if sc == code and sch == c:
                i = slabel - 1 if code != "1L" or c != 6 else slabel - 1
                # position == label here (all four sites are label==position)
                t = verses[i]
                m2 = re.search(anchor, t)
                assert m2, (code, c, slabel, "inline split anchor missing")
                verses[i:i + 1] = [t[:m2.start()].strip(), t[m2.end():].strip()]
        assert all(verses), (code, c)
        out[c] = verses
    return out


def convert(senie_dir, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "app", "src", "main", "assets", "bibles", "en_kjv.json"),
        encoding="utf-8"))
    books = [None] * 66
    relabels = []
    divergent = []
    for coll, table in (("JT1685", NT), ("VD1689_94", OT)):
        cp = os.path.join(senie_dir, coll)
        for code, bi in table.items():
            chapters = parse_book(cp, code, relabels)
            assert chapters, (code, "no chapters")
            assert sorted(chapters) == list(range(1, len(chapters) + 1)), code
            want_ch = NATIVE_CHAPTERS.get(code, len(kjv[bi]["chapters"]))
            assert len(chapters) == want_ch, (code, len(chapters), want_ch)
            out_chapters = [chapters[c] for c in range(1, len(chapters) + 1)]
            for ci, vs in enumerate(out_chapters):
                kch = kjv[bi]["chapters"]
                kn = len(kch[ci]) if ci < len(kch) else -1
                if len(vs) != kn:
                    divergent.append(f"{code} {ci+1}: {len(vs)} vs KJV {kn}")
            books[bi] = {"name": NAMES_LV[bi], "chapters": out_chapters}
    assert all(books)
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verses (native "
              f"numbering + original orthography), {os.path.getsize(dst)} bytes\n")
    out.write(f"label events ({len(relabels)}):\n")
    for r in relabels:
        out.write("  " + r + "\n")
    out.write(f"native-divergent chapters ({len(divergent)}, all versemap-curated "
              f"or mechanical title-psalms):\n")
    for d in divergent:
        out.write("  " + d + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
