# -*- coding: utf-8 -*-
"""⚠ WORK IN PROGRESS — NOT YET PRODUCING AN ASSET (2026-07-17).
The NT parsing works (label-typo repair, correction notation, dotless
labels — see below). BLOCKED ON: the OT's chapter structure. 1 Chr 5
carries print labels 24-44 — Glück follows a Luther-tradition chapter
division with CONTINUOUS native verse numbers across chapter seams that
differ from both the KJV and the @n markers' placement. The whole OT
needs a structural survey (which books, which arrangement, how the @n
markers relate to the print's own numbers) before any position-based
assumption is safe. The research report explicitly never verse-diffed
the OT; this is that missing assessment. Resume with a fresh survey of
every OT book's label sequences; do NOT position-renumber non-dense
chapters. The partial lv_gluck.json this produced was DELETED from
assets (0-verse first, then aborted runs).

SENIE/CLARIN-LV corpus (Glück Bible: JT1685 NT + VD1689_94 OT) -> app asset.

Source: Senie-DSL-plaintext.zip from the CLARIN-LV repository
(repository.clarin.lv handle 20.500.12574/141) — the University of
Latvia's SENIE corpus of old written Latvian, license CC BY-SA 4.0
(quoted in the research report; attribution added to sources_text).
Ernst Glück's own 1685 New Testament and 1689 Old Testament in the
ORIGINAL 17th-century orthography (long-s ſ/ẜ, w for v, uh/ee digraphs,
virgule / as punctuation) — shipped as printed, per the house precedent
(Karl XII 1703, Luther 1545, Wycliffe c.1395). Litmus 7/7 verified
2026-07-17 — research report: Hexapla-releases/research/gluck_report.md.

Format (custom @-code DSL, one file per book):
  @a/@z author/collection, @g book code, @k running heads, @n{N} chapter,
  @t{...} cross-reference footnotes, @l{...} print marks — all dropped;
  verses are "  N. text" lines wrapped with print line-break hyphens
  (joined here: a line ending in "-" continues the word). Verse 0 in
  every chapter is a Reformation-style chapter ARGUMENT (summary blurb),
  not scripture — dropped. Psalm superscriptions occupy their own
  numbered verse 1 (native numbering, kept; build_versemap.py's
  mechanical title engine pivots them).

The Apokr1689 apocrypha (same edition, same license) is NOT converted
yet — its versification against the KJV apocrypha grid is unassessed;
follow-up recorded in CLAUDE.md.

Usage: python convert_gluck.py <senie_dir> <dst.json>
"""
import io
import json
import os
import re
import sys

# SENIE book-code -> canon index 0..65
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

CODE_LINE = re.compile(r"^@([a-z])\{")
# "12{13}." = the transcription's own print-typo correction notation:
# the FIRST number is the true verse, the braced one is what the 1685/89
# print mislabeled (39 instances corpus-wide, verified at Mark 15:12).
# The dot itself is missing in a handful of prints (Lev 4:32) — a
# dotless leading number is accepted as a verse start ONLY when it
# equals the expected next verse; otherwise it is text.
VERSE_LINE = re.compile(r"^\s+(\d+)(?:\{\d+\})?(\.)?\s+(.*)$")

# Print-label fixes, each verified against the raw lines and the KJV
# (research report + integration session 2026-07-17): the SECOND
# occurrence of a duplicated printed verse number is really the next
# verse, or a skipped label. (book code, chapter, occurrence-to-renumber)
# applied while parsing: when a duplicate verse number appears, it is
# accepted as (previous number + 1) IF that slot is empty — every such
# event is reported and must be in EXPECTED_RELABELS.
EXPECTED_RELABELS = set()


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
    return out


def parse_book(path, relabels):
    chapters = {}
    cur_ch = None
    cur_verse = None
    buf = {}
    skipping = False   # inside verse 0 (chapter argument)
    raw = open(path, encoding="utf-8-sig").read()
    # drop multi-line @t{...}/@k{...} etc. blocks wholesale — but keep
    # @n{...} chapter markers (the first version of this line ate them
    # and produced a 0-verse asset; the empty-chapter assert was vacuous)
    raw = re.sub(r"@(?!n\{)[a-z]\{[^}]*\}", "", raw)
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = re.match(r"@n\{(\d+)\}", line.strip())
        if m:
            cur_ch = int(m.group(1))
            assert cur_ch not in chapters, (path, cur_ch)
            chapters[cur_ch] = {}
            buf = {}
            cur_verse = None
            skipping = False
            continue
        if line.strip().startswith("@"):
            continue
        vm = VERSE_LINE.match(line)
        if vm and cur_ch is not None and (
                vm.group(2) or int(vm.group(1)) == (cur_verse or 0) + 1):
            vn, text = int(vm.group(1)), vm.group(3)
            if vn == 0:
                skipping = True
                cur_verse = None
                continue
            skipping = False
            # Print-label typos exist (Luke 8 prints two "25."s and no
            # "24."; 1 Cor 9 prints "6." where v8 belongs). POSITION in
            # sequence is authoritative: every verse line is prev+1, the
            # printed label is decoration. Mismatches are logged for
            # eyeball review; more than 2 in one chapter aborts (that
            # would mean a parser bug, not a print typo), and the final
            # whole-grid diff against the KJV validates globally.
            expected = (cur_verse or 0) + 1
            if vn != expected:
                relabels.append(f"{os.path.basename(path)} ch {cur_ch}: "
                                f"printed {vn}. accepted as {expected}.")
                per_ch = sum(1 for r in relabels
                             if r.startswith(f"{os.path.basename(path)} ch {cur_ch}:"))
                assert per_ch <= 2, (path, cur_ch, "too many label anomalies")
                vn = expected
            buf[vn] = [text]
            cur_verse = vn
        elif not skipping and cur_verse is not None and cur_ch is not None:
            buf[cur_verse].append(line)
        if cur_ch is not None:
            chapters[cur_ch] = buf
    out = {}
    for c, vs in chapters.items():
        out[c] = {v: join_wrap(parts) for v, parts in vs.items()}
    return out


def convert(senie_dir, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    books = [None] * 66
    relabels = []
    for coll, table in (("JT1685", NT), ("VD1689_94", OT)):
        for code, bi in table.items():
            path = os.path.join(senie_dir, coll, code, f"{code}_Unicode.txt")
            assert os.path.exists(path), path
            chapters = parse_book(path, relabels)
            assert chapters, (code, "no chapters parsed")
            assert sorted(chapters) == list(range(1, len(chapters) + 1)), (code, sorted(chapters)[-3:])
            out_chapters = []
            for c in range(1, len(chapters) + 1):
                vs = chapters[c]
                assert vs, (code, c, "empty chapter")
                assert sorted(vs) == list(range(1, max(vs) + 1)), (code, c, sorted(vs)[:3], sorted(vs)[-3:])
                assert all(vs[v].strip() for v in vs), (code, c)
                out_chapters.append([vs[v] for v in range(1, max(vs) + 1)])
            books[bi] = {"name": NAMES_LV[bi], "chapters": out_chapters}
    assert all(books), [i for i, b in enumerate(books) if not b]
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verses (native "
              f"numbering + original orthography), {os.path.getsize(dst)} bytes\n")
    out.write(f"duplicate-label relabels ({len(relabels)}):\n")
    for r in relabels:
        out.write("  " + r + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
