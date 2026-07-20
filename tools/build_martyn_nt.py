# -*- coding: utf-8 -*-
"""Build fa_martyn.json from the 16 Martyn-Persian transcription reports.

THE SOURCE IS THE PROJECT'S OWN MULTIMODAL TRANSCRIPTION (2026-07-20) of the
1876 BFBS sixth-edition reprint of Henry Martyn's Persian NT (translator
†1812; PD beyond dispute), read page-by-page from the archive.org scan —
reports in C:/Projects/Hexapla-releases/research/martyn_*.md, one file per
chunk, every chapter verified against the KJV grid and litmus-perfect
(all seven standard verses TR, incl. 1 Tim 3:16 «خدا در جسم آشکارا شد» and
the Comma at 1 Jn 5:7-8 — both verified twice, feasibility + in-context).

PARSER CONTRACT: verses appear as «(۱) text...» runs with Persian-Indic
markers inside otherwise-markdown reports. Because every chapter matches
KJV counts exactly (three curated exceptions below), the parser is a STRICT
STATE MACHINE: it walks the marker stream expecting precisely books'
chapters' 1..N in canonical order and hard-fails on any deviation. English
prose can't derail it: markers are only accepted when followed by
majority-Arabic text, code spans/fences are stripped first (method sections
quote marker examples in backticks), and each verse segment stops at the
first clearly-non-Persian line.

CURATED EXCEPTIONS:
1. Acts 21:21-32 — folio 295 of the 1876 scan is a master-scan duplicate of
   folio 285; the 12 verses are supplied from the 1837 FIRST PRINTING of the
   same translation (martyn_acts21_recovery.md; calibration proved the two
   printings word-for-word identical, both edge fragments validated). Each
   supplied verse carries a {یادداشت: ...} translator's note naming the
   witness (the app's on-demand note mechanism).
2. Romans 15:32/33 — the print's heading promises 33 verses but one marker
   serves both (content complete; re-verified twice at 8x zoom = print
   defect, the Luke-23:17-missing-numeral class). Split at the printed
   text's own boundary (v33 = the closing peace-benediction sentence).
3. WITNESS_OVERRIDES — readings arbitrated against the 1837 first printing
   (martyn_1837_witness_checks.md): filled in once that pass reports.

    python tools/build_martyn_nt.py --dry-run   # parse + verify, no write
    python tools/build_martyn_nt.py             # write the asset
"""
import argparse
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path("C:/Projects/Hexapla-releases/research")
OUT = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
       / "bibles" / "fa_martyn.json")

# KJV verse counts, NT books 39-65.
KJV = {
    39: [25,23,17,25,48,34,29,34,38,42,30,50,58,36,39,28,27,35,30,34,46,46,39,51,46,75,66,20],
    40: [45,28,35,41,43,56,37,38,50,52,33,44,37,72,47,20],
    41: [80,52,38,44,39,49,50,56,62,42,54,59,35,35,32,31,37,43,48,47,38,71,56,53],
    42: [51,25,36,54,47,71,53,59,41,42,57,50,38,31,27,33,26,40,42,31,25],
    43: [26,47,26,37,42,15,60,40,43,48,30,25,52,28,41,40,34,28,41,38,40,30,35,27,27,32,44,31],
    44: [32,29,31,25,21,23,25,39,33,21,36,21,14,23,33,27],
    45: [31,16,23,21,13,20,40,13,27,33,34,31,13,40,58,24],
    46: [24,17,18,18,21,18,16,24,15,18,33,21,14],
    47: [24,21,29,31,26,18],
    48: [23,22,21,32,33,24],
    49: [30,30,21,23],
    50: [29,23,25,18],
    51: [10,20,13,18,28],
    52: [12,17,18],
    53: [20,15,16,16,25,21],
    54: [18,26,17,22],
    55: [16,15,15],
    56: [25],
    57: [14,18,19,16,14,20,28,13,28,39,40,29,25],
    58: [27,26,18,17,20],
    59: [25,25,22,19,14],
    60: [21,22,18],
    61: [10,29,24,21,21],
    62: [13],
    63: [14],
    64: [25],
    65: [20,29,22,11,14,17,17,13,21,11,19,17,18,20,8,21,18,24,21,15,27,21],
}

# report file -> ordered list of book indexes it contains (chapters implied
# by KJV[book]; multi-chunk books list their chapter RANGE).
FILES = [
    ("martyn_matthew_1-9.md",   [(39, 0, 9)]),
    ("martyn_matthew_10-18.md", [(39, 9, 18)]),
    ("martyn_matthew_19-28.md", [(39, 18, 28)]),
    ("martyn_mark_1-6.md",      [(40, 0, 6)]),
    ("martyn_mark_7-11.md",     [(40, 6, 11)]),
    ("martyn_mark_12-16.md",    [(40, 11, 16)]),
    ("martyn_luke_1-8.md",      [(41, 0, 8)]),
    ("martyn_luke_9-16.md",     [(41, 8, 16)]),
    ("martyn_luke_17-24.md",    [(41, 16, 24)]),
    ("martyn_john_1-7.md",      [(42, 0, 7)]),
    ("martyn_john_8-13.md",     [(42, 7, 13)]),
    ("martyn_john_14-21.md",    [(42, 13, 21)]),
    ("martyn_acts_1-9.md",      [(43, 0, 9)]),
    ("martyn_acts_10-19.md",    [(43, 9, 19)]),
    ("martyn_acts_20-28.md",    [(43, 19, 28)]),
    ("martyn_romans.md",        [(44, 0, 16)]),
    ("martyn_1corinthians.md",  [(45, 0, 16)]),
    ("martyn_2corinthians.md",  [(46, 0, 13)]),
    ("martyn_gal_col.md",       [(47, 0, 6), (48, 0, 6), (49, 0, 4), (50, 0, 4)]),
    ("martyn_thess_phlm.md",    [(51, 0, 5), (52, 0, 3), (53, 0, 6), (54, 0, 4), (55, 0, 3), (56, 0, 1)]),
    ("martyn_heb_2pet.md",      [(57, 0, 13), (58, 0, 5), (59, 0, 5), (60, 0, 3)]),
    ("martyn_1jn_rev.md",       [(61, 0, 5), (62, 0, 1), (63, 0, 1), (64, 0, 1), (65, 0, 22)]),
]

# Display names. Register follows the print's own conventions (attested:
# «کتاب انجیلِ متّی», «کتابِ اعمالِ حواریان», «نامهء پولسِ حواری به
# گَلَتِیانْ», «نامه دویم به تسلنیقیان», «نامه اول پولس حواری به
# تیموتیوس») — the harvest step prints every title/colophon line found in
# the reports so this table can be re-curated against the print.
FA_NAMES = {
    39: "انجیل متّی", 40: "انجیل مَرقُس", 41: "انجیل لوقا", 42: "انجیل یوحنّا",
    43: "اعمال حواریان",
    44: "نامهٔ پولس حواری به رومیان",
    45: "نامهٔ اول پولس حواری به قرنتیان",
    46: "نامهٔ دویم پولس حواری به قرنتیان",
    47: "نامهٔ پولس حواری به گلتیان",
    48: "نامهٔ پولس حواری به افسسیان",
    49: "نامهٔ پولس حواری به فیلپیان",
    50: "نامهٔ پولس حواری به کولسیان",
    51: "نامهٔ اول پولس حواری به تسلنیقیان",
    52: "نامهٔ دویم پولس حواری به تسلنیقیان",
    53: "نامهٔ اول پولس حواری به تیموتیوس",
    54: "نامهٔ دویم پولس حواری به تیموتیوس",
    55: "نامهٔ پولس حواری به تیطوس",
    56: "نامهٔ پولس حواری به فلیمون",
    57: "نامه به عبرانیان",
    58: "نامهٔ یعقوب",
    59: "نامهٔ اول پطرس",
    60: "نامهٔ دویم پطرس",
    61: "نامهٔ اول یوحنّا",
    62: "نامهٔ دویم یوحنّا",
    63: "نامهٔ سیوم یوحنّا",
    64: "نامهٔ یهودا",
    65: "مکاشفهٔ یوحنّا",
}

# English placeholder names for the empty OT slots (grc/arm precedent).
CANON_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
]

# Both Extended-Persian (۰-۹, U+06F0) and Arabic-Indic (٠-٩, U+0660) digit
# sets — the Acts 10-19 report mixes them mid-chapter.
MARKER = re.compile(r"\(([۰-۹٠-٩]+)\)")
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
FLAG = re.compile(r"⟨[^⟩]*⟩")
# ⟨uncertain: READING — explanation⟩ keeps its READING (the transcriber's
# best-supported text); every other ⟨...⟩ flag is dropped.
UNCERTAIN = re.compile(r"⟨uncertain:\s*([^—⟩]+?)\s*(?:—[^⟩]*)?⟩", re.S)


def resolve_flags(s):
    return FLAG.sub(" ", UNCERTAIN.sub(r"\1", s))

# Acts 21 witness note, one per supplied verse (colon note -> shown on
# demand via the app's translator's-notes mechanism, stripped from display).
ACTS21_NOTE = ("{یادداشت: متن این آیه از چاپ نخست ۱۸۳۷ همین ترجمه تکمیل شده است؛ "
               "برگ ۲۹۵ در اسکن چاپ ۱۸۷۶ مفقود است.}")

# Readings arbitrated against the 1837 first printing
# (martyn_1837_witness_checks.md, 2026-07-20). Keyed (book, ch, v),
# value = (find, replace, rationale).
WITNESS_OVERRIDES = {
    # Heb 6:14: the 1876 prints «منتشر» THREE times; the 1837 first printing
    # reads the standard doubled Hebraism («منتشر میکنم منتشر کردنی», KJV
    # "multiplying I will multiply") — the third repetition is a reprint-
    # specific typesetting defect, corrected per the Acts-21 earlier-witness
    # precedent. The transcriber's inline Persian explanation bracket is
    # removed with it (agent annotation, not print text).
    (57, 6, 14): [
        ("منتشر منتشر میکنم", "منتشر میکنم",
         "1837 witness reads doubled, 1876 triple is a reprint defect"),
        ("[یعنی، بمعنیِ تکرارِ ادات تأکید عبرانی — نک. یادداشتِ ذیل]", "",
         "transcriber's Persian annotation removed"),
    ],
}

# Spot re-verification overrides (martyn_spot_reverify.md, 2026-07-20): a
# page-level re-read of every length-audit suspect proved the 1876 print
# innocent at all of them — the flags were transcription slips in the chunk
# passes (incl. Mark 10's supposed one-off numbering, which was the chunk
# agent's own misread of the 35/36 boundary). These sites are REPLACED with
# the re-verify pass's fresh transcriptions.
REVERIFY = [  # (section-header prefix, book, chapter, v_lo, v_hi)
    ("## 1. Mark 10", 40, 10, 34, 52),
    ("## 2. 1 Corinthians 10", 45, 10, 15, 18),
    ("## 3. John 2:14", 42, 2, 14, 14),
    ("## 4. Philippians 3", 49, 3, 5, 6),
    ("## 6. 1 Peter 1:8", 59, 1, 8, 8),
]

# John 21:11: BOTH witnesses (1837 first printing AND the 1876 reprint) read
# «دویست و پنجاه و سه» (253) fish where the Greek reads 153 — the reading is
# the translation's own, kept as printed with an on-demand note.
JN21_NOTE = ("{یادداشت: در هر دو چاپ ۱۸۳۷ و ۱۸۷۶ «دویست و پنجاه و سه» چاپ "
             "شده است؛ متن یونانی «صد و پنجاه و سه» دارد.}")

# Print-side marker merges: verse V's numeral is missing in the print but
# its text is complete, riding either at the END of verse V-1's segment
# ("prev") or at the HEAD of verse V+1's segment ("next") — each site
# DISCLOSED in its chunk report, and each chapter's printed heading count
# still promises the KJV total, making these print defects (the missing-
# numeral class), not native versification. Keyed (book, ch, v) ->
# (direction, regex matching the start of the LATER verse of the pair).
# The state machine detects sites mechanically; a site without an entry
# fails the build with the carrier text printed for curation.
CURATED_SPLITS = {
    # Mark 6:15 «Others said, That it is Elias...» rides in v14's segment.
    (40, 6, 15): ("prev", r"و دیگران گفتند که اِ?یلیا"),
    # Luke 23:17 «for of necessity he must release one...» heads v18's
    # segment; v18 proper starts at «they cried out all at once».
    (41, 23, 17): ("next", r"همه به یک بار فریاد"),
    # Rom 15:33 the peace benediction rides in v32's segment — Martyn's
    # wording is «خدائي که اصلِ آرام است» ("the God who is the source of
    # peace"), NOT the modern «خدای سلامتی».
    (44, 15, 33): ("prev", r"خدائ?[یي] که اصلِ آرام"),
    # Rev 22:9 «Then saith he unto me, See thou do it not...» rides in
    # v8's segment.
    (65, 22, 9): ("prev", r"مرا گفت زینهار نکنی"),
}


def arabic_ratio(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    ar = sum(1 for c in letters if "؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ")
    return ar / len(letters)


def strip_code(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    # mid-verse page-break annotations — «(idx388, folio 384, running header
    # only — same chapter continues...)» — sit on their own line INSIDE a
    # verse that spans a page; they must vanish BEFORE splitting or the
    # verse's continuation is silently truncated at the English line.
    return re.sub(r"(?m)^\([^)\n]*(?:folio|idx|PDF)[^)\n]*\)\s*$", "", text)


def clean_verse(seg):
    """Trim a raw inter-marker segment down to the verse text."""
    lines = seg.split("\n")
    kept = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue                       # verses may span page-break paragraphs
        if s.startswith(("#", "|", "**", "- ", "---", ">", "(باب", "باب ")):
            break                          # structural/commentary/chapter-header fence
        if arabic_ratio(s) < 0.5 and re.search(r"[A-Za-z]", s):
            break                          # English/mixed commentary line
        kept.append(s)
    t = " ".join(kept)
    # normalize Arabic-form yeh/kaf to Persian — the chunks were transcribed
    # by different agents whose IME choices differed (ي/ك vs ی/ک); the print
    # itself makes no such distinction, and a mixed asset breaks search.
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = t.replace("*", " ")                # report-side separators/emphasis
    # inline English annotations in [brackets] or (parens) — e.g. the Mark
    # 10 "[see note]" tags and the John 21:11 reading-disclosure note.
    # Persian-dominant blocks (the print's own [supplied words]) survive.
    t = re.sub(r"\[[^\]\n]*\]|\([^)\n]*\)",
               lambda mm: " " if arabic_ratio(mm.group(0)) < 0.2 else mm.group(0), t)
    t = re.sub(r"\s+", " ", t).strip(" -–—")
    # a quoted verse can end mid-line with English prose continuing on the
    # SAME line (the 3 John 14 discussion-quote class) — no Latin letter can
    # be verse content, so cut at the first one.
    m = re.search(r"[A-Za-z]", t)
    if m:
        t = t[:m.start()].rstrip(' "«»—–-*')
    return t.strip()


def parse_stream(text):
    """Yield (verse_number, raw_segment) for every accepted marker."""
    text = strip_code(text)
    matches = list(MARKER.finditer(text))
    accepted = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(text), m.end() + 4000)
        # transcriber annotations ride inline as *italic spans* (the Matt
        # 2:6 numeral-glyph note) or {English brace notes} (the John 7:15
        # print-defect note) — strip both BEFORE the language gate or an
        # annotated verse gets rejected as English prose. Only mostly-ASCII
        # brace blocks are dropped; Persian braces would be verse content.
        seg = re.sub(r"\*[^*\n]+\*", " ", text[m.end():end])
        seg = re.sub(r"\{[^}]*\}", lambda mm: " " if arabic_ratio(mm.group(0)) < 0.2 else mm.group(0), seg)
        probe = seg[:80]
        # a marker whose segment opens with a ⟨...⟩ flag is a transcription
        # placeholder (the Acts 21 missing-folio verses) — keep it so the
        # state machine stays in sync; the curated replacement fills it.
        if arabic_ratio(probe) < 0.35 and not FLAG.search(seg[:200]):
            continue                       # marker quoted in English prose
        accepted.append((int(m.group(1).translate(PERSIAN_DIGITS)), seg))
    return accepted


def harvest_titles(text, fname):
    for m in re.finditer(r"(کتاب[^\n«»]{0,80}|نامه[^\n«»]{0,80}|انجیل[^\n«»]{0,60}|مکاشفه[^\n«»]{0,60}|تمام شد[^\n«»]{0,80})", text):
        s = m.group(0).strip()
        if arabic_ratio(s) > 0.5 and len(s) > 8:
            print(f"    title-harvest [{fname}]: {s[:90]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--harvest", action="store_true", help="print title lines")
    args = ap.parse_args()

    recovery = io.open(RESEARCH / "martyn_acts21_recovery.md", encoding="utf-8").read()
    # The recovery report marks verses as **(21)** (ASCII digits, bold) with
    # inline English annotations in *(...)* italics. Split on the markers
    # FIRST — the annotation regex would otherwise eat `*(21)*` inside
    # `**(21)**` — then strip annotations per segment.
    rec_text = strip_code(recovery)
    rec_marker = re.compile(r"\*\*\((\d+)\)\*\*")
    rec_verses = {}
    rms = list(rec_marker.finditer(rec_text))
    for i, m in enumerate(rms):
        end = rms[i + 1].start() if i + 1 < len(rms) else min(len(rec_text), m.end() + 3000)
        seg = resolve_flags(re.sub(r"\*\([^)]*\)\*", " ", rec_text[m.end():end]))
        if arabic_ratio(seg[:80]) < 0.35:
            continue
        v = int(m.group(1))
        if 21 <= v <= 32 and v not in rec_verses:
            t = clean_verse(seg)
            if len(t) > 20:
                rec_verses[v] = t
    assert set(rec_verses) == set(range(21, 33)), \
        f"Acts21 recovery parse: got verses {sorted(rec_verses)}"

    books = {}
    problems = []
    strays = []
    for fname, spec in FILES:
        text = io.open(RESEARCH / fname, encoding="utf-8").read()
        if args.harvest:
            harvest_titles(text, fname)
        stream = parse_stream(text)
        pos = 0
        for (bk, ch0, ch1) in spec:
            books.setdefault(bk, [None] * len(KJV[bk]))
            for ci in range(ch0, ch1):
                n = KJV[bk][ci]
                verses = [None] * n
                merge_sites = []
                want = 1
                while want <= n:
                    if pos >= len(stream):
                        problems.append(f"{fname}: ran out at {bk} ch{ci+1} v{want}")
                        break
                    vnum, seg = stream[pos]
                    if vnum == want:
                        # Summary sections QUOTE verses with their markers
                        # before the transcription proper; a chapter may only
                        # BEGIN where a long consecutive run does (quotes are
                        # short runs), or the Pericope-quote class hijacks
                        # the chapter head.
                        if want == 1:
                            k = min(n, 8)
                            run = [v for v, _ in stream[pos:pos + k]]
                            if run != list(range(1, k + 1)):
                                strays.append(
                                    f"{fname}: {bk} ch{ci+1} rejected short run at ({vnum}): {run}")
                                pos += 1
                                continue
                        t = clean_verse(resolve_flags(seg) if not (bk == 43 and ci == 20) else seg)
                        verses[want - 1] = t
                        pos += 1
                        want += 1
                    elif vnum == want + 1 and want >= 2 and verses[want - 2]:
                        # missing-numeral site: verse `want`'s text rides in a
                        # neighbour's segment (direction resolved by the
                        # curated table; do NOT consume the seen marker)
                        merge_sites.append(want)
                        want += 1
                    elif want == n and vnum == 1 and want >= 2 and verses[want - 2]:
                        # last verse of the chapter merged; next chapter begins
                        merge_sites.append(want)
                        want += 1
                    else:
                        strays.append(
                            f"{fname}: {bk} ch{ci+1} expected v{want}, skipped stray ({vnum}) "
                            f"{clean_verse(seg)[:60]!r}")
                        pos += 1
                for v in merge_sites:
                    ent = CURATED_SPLITS.get((bk, ci + 1, v))
                    if not ent:
                        prev = verses[v - 2] or ""
                        nxt = verses[v] if v < n and verses[v] else ""
                        problems.append(
                            f"MERGE SITE NEEDS CURATED SPLIT: book {bk} ch{ci+1} v{v}; "
                            f"prev tail: …{prev[-120:]!r} | next head: {nxt[:120]!r}…")
                        continue
                    direction, rx = ent
                    if direction == "prev":
                        carrier = verses[v - 2]
                        m = re.search(rx, carrier or "")
                        if not m or m.start() == 0:
                            problems.append(f"split anchor failed ({bk} ch{ci+1} v{v} prev): "
                                            f"…{(carrier or '')[-140:]!r}")
                            continue
                        verses[v - 2] = carrier[:m.start()].strip()
                        verses[v - 1] = carrier[m.start():].strip()
                    else:                  # "next": carrier is the verse AFTER v
                        carrier = verses[v] if v < n else None
                        m = re.search(rx, carrier or "")
                        if not m or m.start() == 0:
                            problems.append(f"split anchor failed ({bk} ch{ci+1} v{v} next): "
                                            f"{(carrier or '')[:140]!r}…")
                            continue
                        verses[v - 1] = carrier[:m.start()].strip()
                        verses[v] = carrier[m.start():].strip()
                # curated: Mark 5 — the print MERGES KJV 5:28+29 under its
                # marker 28 and renumbers the rest of the chapter one low;
                # its promised 43rd numeral is the invisible/fused one, where
                # the report left a Persian bracket note instead of text.
                # (The chunk report's own summary claimed clean counts here —
                # this resegmentation was established by direct comparison of
                # every marker's content against the KJV storyline.)
                if bk == 40 and ci == 4:
                    assert verses[42] and "این متن ذیل" in verses[42], verses[42][:60]
                    m28 = verses[27]
                    m = re.search(r"که در ساعت جریانِ? خونِ? وَ?ی ایستاد", m28)
                    assert m and m.start() > 0, f"Mark 5:28/29 anchor: {m28[:120]!r}"
                    verses = (verses[:27]
                              + [m28[:m.start()].strip(), m28[m.start():].strip()]
                              + verses[28:42])
                    assert len(verses) == 43, len(verses)
                # curated: Acts 21 supplied verses
                if bk == 43 and ci == 20:
                    for v in range(21, 33):
                        verses[v - 1] = rec_verses[v] + " " + ACTS21_NOTE
                    for v, t in enumerate(verses, 1):
                        assert t and "⟨" not in t, (bk, ci + 1, v, t and t[:60])
                for v, t in enumerate(verses, 1):
                    if not t:
                        problems.append(f"{bk} ch{ci+1} v{v}: EMPTY after parse")
                    elif "⟨" in t:
                        problems.append(f"{bk} ch{ci+1} v{v}: unresolved flag: {t[:70]}")
                books[bk][ci] = verses
        if pos != len(stream):
            # trailing quotes in verification/notes sections are harmless as
            # long as every expected verse was captured — the empties check
            # below is the real gate.
            strays.append(f"{fname}: {len(stream)-pos} unconsumed trailing markers")

    reverify = io.open(RESEARCH / "martyn_spot_reverify.md", encoding="utf-8").read()
    for header, bk, ch, v_lo, v_hi in REVERIFY:
        start = reverify.find(header)
        assert start >= 0, header
        nxt = reverify.find("\n## ", start + 1)
        section = reverify[start:nxt if nxt > 0 else len(reverify)]
        got = {}
        for vnum, seg in parse_stream(section):
            if v_lo <= vnum <= v_hi and vnum not in got:
                t = clean_verse(resolve_flags(seg))
                if len(t) > 3:
                    got[vnum] = t
        assert set(got) == set(range(v_lo, v_hi + 1)), (header, sorted(got))
        for vnum, t in got.items():
            books[bk][ch - 1][vnum - 1] = t
        print(f"  reverify override: book {bk} ch{ch} v{v_lo}-{v_hi} ({len(got)} verses)")

    for (bk, ch, v), pairs in WITNESS_OVERRIDES.items():
        for find, repl, why in pairs:
            old = books[bk][ch - 1][v - 1]
            assert find in old, (bk, ch, v, "override find-text absent", old[:90])
            books[bk][ch - 1][v - 1] = re.sub(r"\s+", " ", old.replace(find, repl)).strip()
            print(f"  witness override applied at {bk} {ch}:{v} ({why})")
    jn2111 = books[42][20][10]
    assert "دویست و پنجاه" in jn2111, jn2111[:90]
    books[42][20][10] = jn2111 + " " + JN21_NOTE
    print("  Jn 21:11 kept as printed (253 in both witnesses) + note")

    total = sum(len(c) for chs in books.values() for c in chs if c)
    print(f"\nparsed {len(books)} books, {total} verses; "
          f"fatal problems: {len(problems)}; stray-skips: {len(strays)}")
    for s in strays[:15]:
        print("  · stray:", s)
    for p in problems[:40]:
        print("  ⚠", p)
    if problems:
        raise SystemExit("unresolved problems — not writing")
    assert total == 7957, total

    # charset sanity: no ASCII letters may survive in verse text
    ascii_leak = []
    for bk, chs in books.items():
        for ci, ch in enumerate(chs):
            for vi, t in enumerate(ch):
                core = re.sub(r"\{[^}]*\}", "", t)
                if re.search(r"[A-Za-z]", core):
                    ascii_leak.append((bk, ci + 1, vi + 1, t[:70]))
    for x in ascii_leak[:20]:
        print("  ⚠ ascii leak:", x)
    assert not ascii_leak, f"{len(ascii_leak)} verses contain Latin letters"

    # litmus on the built data
    def verse(bk, c, v):
        return books[bk][c - 1][v - 1]
    LITMUS = [
        (53, 3, 16, "خدا در جسم آشکارا شد", "1 Tim 3:16 God-manifest"),
        (61, 5, 7, "در آسمان", "1 Jn 5:7 Comma heavenly witnesses"),
        (43, 8, 37, "پسرِ خدا", "Acts 8:37 confession"),
        (44, 16, 24, "توفیقِ خداوندِ ما", "Rom 16:24 grace benediction"),
        (41, 2, 33, "یوسف", "Lk 2:33 Joseph"),
        (43, 20, 28, "خدا", "Acts 20:28 church of God"),
        (42, 5, 4, "فرشته", "Jn 5:4 angel"),
    ]
    for bk, c, v, needle, label in LITMUS:
        assert needle in verse(bk, c, v), (label, verse(bk, c, v)[:100])
        print(f"  litmus OK: {label}")

    if args.dry_run:
        print("dry run — nothing written")
        return

    out = []
    for i in range(66):
        if i < 39:
            out.append({"name": CANON_NAMES[i], "chapters": []})
        else:
            out.append({"name": FA_NAMES[i], "chapters": books[i]})
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {total} verses)")


if __name__ == "__main__":
    main()
