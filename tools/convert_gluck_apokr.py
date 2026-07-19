# -*- coding: utf-8 -*-
"""SENIE/CLARIN-LV corpus (Glück's 1685/1689 Apokr1689 apocrypha) -> app
asset. Follow-up to convert_gluck.py (same source, same CC BY-SA 4.0
license already credited in sources_text ×13 for the main 66-book
lv_gluck.json text — no new attribution needed).

Source: Senie-DSL-plaintext.zip, Apokr1689/ directory (14 files: 13 real
translated books + Prolog front matter). Research pass:
Hexapla-releases/research/latvian_apokr1689_report.md.

This reuses convert_gluck.py's strip_codes()/join_wrap()/verse-line
machinery UNMODIFIED (verified against all 13 files in the research
pass and again here) with three book-specific additions, all found by
direct inspection of the raw source, not assumed:

  1. GabpEst (Additions to Esther) ch.2 v.1 is printed "..1." (leading
     dots) instead of the corpus's usual "  1." — a one-off transcription
     quirk (grep-verified: the ONLY "^.." verse line in all 13 files).
     A lenient fallback regex (leading dots optional) recovers it;
     without it, v1's text is silently dropped and the whole chapter's
     base numbering shifts wrong.
  2. Baruch ch.3 has a genuine print omission at v.8 (labels jump 7->9;
     KJV 3:8 "Behold, we are yet this day..." has no Latvian counterpart
     between v7 and v9, confirmed by direct comparison against
     en_kjv.json) -- registered as an OMISSION_SKIPS-style shift so the
     rest of the chapter's printed labels (9..37) realign to their true
     position (8..36) instead of tripping the per-chapter typo cap.
  3. Baruch ch.6 (Epistle of Jeremiah, inline) opens with a labeled
     "0." verse that is REAL content (KJV Ep. Jer. v1, "A copy of an
     epistle which Jeremy sent...") -- not the usual Reformation
     chapter-argument that v0 means everywhere else in this corpus. Kept
     as true v1; the rest of the chapter shifts down by one (the
     printed "1." becomes v2, matching KJV Ep. Jer. v2).
  4. Prayer of Azariah + Song of the Three (Asar) ch.2 has a genuine
     print label skip at 52->54 (no v53 printed, content continuous) --
     same OMISSION_SKIPS-style shift as Baruch 3:8, registered
     separately since it is a different (code, chapter).

VERIFIED FINDING on Asar's total (64 native verses vs. the commonly
cited 68 in KJV/Vulgate editions): resolved by direct verse-by-verse
comparison against en_kjv.json's Prayer of Azariah, not assumed. Native
ch1 merges KJV vv.1-2 ("they walked in the fire... Azarias stood and
prayed") into one opening verse (-1); native ch2 (the Song) omits three
of the KJV's "cosmic praise" refrain verses present in that tradition
(ice&cold, frost&snow, seas&rivers -- -3) and reorders one quartet
(winter/summer, dew/snow, nights/days, light/darkness print in the
order night/day, light/dark, winter/summer, dew/snow -- a genuine
textual variant, not a parse artifact). 68 - 1 - 3 = 64, exactly. This
is Glück's own edition, not a defect; shipped as native 64, unmapped
(see NOTE on versemap below).

P_Sir (Prologue to Ecclesiasticus): real, CC-BY-SA translated text, but
has zero @n{} chapter markers (unstructured prose, one embedded "1."
and nothing else) and does not fit any of the app's 17 named apocrypha
slots. DROPPED, matching the house pattern for front-matter/paratext
(the main text's own Prolog/Prolog_Iev/Prolog_Tit/Prolog_Sat are
already dropped the same way) and matching how this app's other two
apocrypha-bearing assets (en_kjv.json, la_vulgata.json) already ship
Sirach without its prologue. This discards real content reversibly --
the source file is untouched in the corpus cache if a future version
adds a slot for it.

Sirach: parses with ZERO label anomalies (no v0s, no skips, no
TRUE{PRINTED} corrections) across all 51 native chapters -- the print's
own numbering is internally consistent throughout. Its chapter/verse
COUNTS diverge from en_kjv.json's (and from la_vulgata.json's and
ru_synodal.json's -- confirmed, this app already ships THREE mutually
different Sirach versification traditions) but that is ordinary
native-vs-KJV versification drift, not corruption -- kept as native
51-chapter numbering, same treatment as 1 Chronicles' 30 native
chapters in the main text.

NOTE on versemap.json: NOT extended for any of these 13 books.
build_versemap.py's engine hard-limits its per-translation loop to
`for bi in range(66)` -- apocrypha books (indices 66-82) are out of
scope for EVERY translation currently in the app, including the
apocrypha already shipped in en_kjv.json/la_vulgata.json/ru_synodal.json
(whose own mutually-divergent Sirach/Baruch/Daniel-appendix
versifications are, today, not cross-mapped to each other either).
Adding lv_gluck-only apocrypha versemap entries would be new scope
with no existing cross-reference feature to serve, and no established
convention to follow -- left undone deliberately, not overlooked.

Usage: python convert_gluck_apokr.py <apokr1689_dir> <lv_gluck.json to update>
"""
import io
import json
import os
import re
import sys

# code -> app apocrypha slot index (Bible.kt / asset schema, 17 slots at
# 66-82). P_Sir has no slot (dropped, see docstring). Prolog is not a
# real book (front matter, zero @n{} markers, already excluded by
# simply never appearing in this table).
APOC = {
    "Tob": 68,       # Tobit
    "Jd": 69,        # Judith
    "Sal": 70,       # Wisdom of Solomon
    "Sir": 71,       # Sirach
    "Bar": 72,       # Baruch (ch 6 = Epistle of Jeremiah, inline)
    "Man": 74,       # Prayer of Manasses
    "1Mak": 75,      # 1 Maccabees
    "2Mak": 76,      # 2 Maccabees
    "GabpEst": 78,   # Additions to Esther
    "Asar": 79,      # Prayer of Azariah (+ Song of the Three)
    "Sus": 80,       # Susanna
    "Bel": 81,       # Bel and the Dragon
}
# Slots left empty (no source text exists in the SENIE corpus, verified
# exhaustively against the Apokr1689 directory listing): 1 Esdras (66),
# 2 Esdras (67), Epistle of Jeremiah (73, folded into Baruch 6 instead),
# 3 Maccabees (77), Laodiceans (82).

# Primary verse-line pattern (identical to convert_gluck.py).
VERSE_LINE = re.compile(r"^\s+(\d+)(?:\{\d+\})?(\.)?\s+(.*)$")
# Lenient fallback: same, but REQUIRES one or more leading literal dots
# before the number (GabpEst ch.2 v.1 prints "..1." -- grep-verified the
# ONLY occurrence of this pattern across all 13 files). Deliberately
# narrow -- an earlier draft made the leading dots optional (`\.*`) and
# it silently mis-matched ordinary zero-indent continuation lines that
# happen to start with a bare "N." (found in Sal: chapter-argument
# wrap lines "4. prett teem..." / "11. Deews taupa...", which are NOT
# verse starts). Requiring `\.+` targets exactly the one known case.
VERSE_LINE_LOOSE = re.compile(r"^\.+\s*(\d+)(?:\{\d+\})?(\.)?\s+(.*)$")

# (code, chapter): labels legitimately skip this position -- a genuine
# print-side gap (Baruch 3:8, content confirmed absent vs. en_kjv.json)
# or a genuine label-only skip with no content lost (Asar 2:53, the
# surrounding refrain verses are continuous). Mechanically identical
# handling either way -- see convert_gluck.py's own OMISSION_SKIPS.
OMISSION_SKIPS = {("Bar", 3): {8}, ("Asar", 2): {53}}

# (code, chapter): v0 is REAL content here, not the corpus-wide
# droppable Reformation chapter-argument convention. Kept as true v1;
# everything else in the chapter shifts down by one.
KEEP_V0_AS_V1 = {("Bar", 6)}


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
    out = re.sub(r"\{[^}]*\}", "", out)
    out = out.replace("*", " ").replace("|", " ")
    out = re.sub(r"\s*/\s*", ", ", out)
    out = re.sub(r",\s+([.:;!?,])", r"\1", out)
    return re.sub(r"\s+", " ", out).strip()


def strip_codes(raw):
    """Remove @x{...} blocks (all except @n) with a depth counter -- see
    convert_gluck.py's identical function for why the depth counter is
    needed (nested {corrections} inside footnote blocks)."""
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
    cur_verse = None
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
        vm = VERSE_LINE.match(line) or VERSE_LINE_LOOSE.match(line)
        is_verse = vm is not None and cur is not None and (
            vm.group(2) or (base_label is not None and
                            int(vm.group(1)) == base_label + len(buf)))
        if is_verse:
            vn, text = int(vm.group(1)), vm.group(3)
            if vn == 0 and (code, cur) in KEEP_V0_AS_V1:
                relabels.append(f"{code} ch {cur}: v0 kept as true v1 (real content, not a chapter argument)")
                base_label = 0
                buf[1] = [text]
                cur_verse = 1
                skipping = False
                continue
            if vn == 0:
                skipping = True
                cur_verse = None
                continue
            skipping = False
            if base_label is None:
                base_label = vn
                if vn != 1:
                    relabels.append(f"{code} ch {cur}: labels start at {vn} (native)")
            expected = base_label + len(buf)
            if vn != expected:
                if vn == expected + 1 and expected in OMISSION_SKIPS.get((code, cur), ()):
                    base_label += 1
                    relabels.append(f"{code} ch {cur}: label {expected} skipped by the print")
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
        assert all(verses), (code, c, "empty verse produced")
        out[c] = verses
    assert out, (code, "no chapters parsed")
    assert sorted(out) == list(range(1, len(out) + 1)), (code, sorted(out))
    return out


def convert(apokr_dir, dst):
    log = io.open(1, "w", encoding="utf-8", closefd=False)
    books = json.load(open(dst, encoding="utf-8"))
    assert len(books) == 83, ("unexpected slot count", len(books))
    relabels = []
    total_verses = 0
    for code, bi in sorted(APOC.items(), key=lambda kv: kv[1]):
        chapters = parse_book(apokr_dir, code, relabels)
        out_chapters = [chapters[c] for c in range(1, len(chapters) + 1)]
        n_verses = sum(len(c) for c in out_chapters)
        total_verses += n_verses
        books[bi]["chapters"] = out_chapters
        log.write(f"{code} -> slot {bi} ({books[bi]['name']}): "
                  f"{len(out_chapters)} chapters, {n_verses} verses -- "
                  f"{[len(c) for c in out_chapters]}\n")

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    log.write(f"\n{dst}: {len(APOC)} apocrypha books converted, "
              f"{total_verses} verses, {os.path.getsize(dst)} bytes\n")
    log.write(f"label events ({len(relabels)}):\n")
    for r in relabels:
        log.write("  " + r + "\n")
    empty_slots = [i for i in range(66, 83) if not books[i]["chapters"]]
    log.write(f"apocrypha slots left empty ({len(empty_slots)}): "
              f"{[books[i]['name'] for i in empty_slots]}\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
