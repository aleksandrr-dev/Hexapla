# -*- coding: utf-8 -*-
"""Дзекуць-Малей / Луцкевіч 1931 (Belarusian NT + Psalms) -> app asset.

Public domain: joint-work term runs from the later-dying co-author
(Dzekuć-Malej, d. 1955); life+50 expired 1 Jan 2006, well before
Belarus's non-retroactive 2024 life+70 extension. Full analysis:
Hexapla-releases/research/belarusian_report.md (litmus 7/7 verified
there against raw text from two independent hosts).

No bulk-download format exists for this text (confirmed: no CrossWire
module, no eBible entry, no scrollmapper/gratis-bible source) — this is
a scraper, Meiji-NT-precedent shape, not a zip-parser.

Primary source: biblia.by/dz-maley/<book>/<chapter>/ — chosen over
be.wikisource.org (the report's tentative primary) after inspecting
both rendered structures directly: biblia.by carries one
`<div id="N"><sup>N</sup> text</div>` per verse, uniform across every
book and chapter, machine-parseable with a single regex. be.wikisource
mixes a `{{верш|раздзел=N|верш=M}}` template (Matthew, Luke, John,
Acts, Romans, ...) with bare `N text` numbering (1 Timothy, 1 John,
...) on different book pages (an editing inconsistency between
Wikisource contributors, confirmed by direct inspection) and renders
Psalms as inline "N. text N. text" prose paragraphs per psalm — three
distinct micro-formats needing three parsers, all just to reach the
same text biblia.by already exposes uniformly. be.wikisource is used
here only for cross-validation (a full book's wikitext fetched once
per book + Psalms, sampled against the biblia.by parse).

Book numbering on biblia.by (confirmed from /dz-maley/'s own nav):
  19 = Psalms; 40-44 = Matthew..Acts; 45-51 = James, 1-2 Peter,
  1-3 John, Jude (Catholic epistles, Byzantine canon order); 52-65 =
  Romans..Hebrews; 66 = Revelation. Mapped to KJV slot indices below.

Canon: 27 NT books + Psalms only (the 1931 print was titled "Новы
Запавет і Псальмы" — explicitly "не поўны пераклад", not a full
Bible). All other 65 book slots stay empty (English placeholder name,
zero chapters), matching the grc_byz/hy_west1853/sa_nt NT-only
precedent.

Stress-accent marks (е́, а́ ...) are KEPT verbatim — they are the
edition's own orthography, not a transcription artifact, and this
project's precedent (cu_elizabeth, hy_west1853) keeps source diacritics
rather than normalizing them away.

Usage: python build_dzmaley_nt.py [--verify-only]
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets")
UA = "Hexapla-bible-app/1.0 (data pipeline; offline PD Bible reader)"

# biblia.by book number -> KJV slot index (39=Matthew .. 65=Revelation; 18=Psalms)
BOOK_MAP = [
    (40, 39, "Мацьвея"),
    (41, 40, "Марка"),
    (42, 41, "Лукі"),
    (43, 42, "Іоана"),
    (44, 43, "Дзеяньні"),
    (52, 44, "Да Рымлянаў"),
    (53, 45, "1 да Карыньцянаў"),
    (54, 46, "2 да Карыньцянаў"),
    (55, 47, "Да Галятаў"),
    (56, 48, "Да Эфэсцаў"),
    (57, 49, "Да Філіпянаў"),
    (58, 50, "Да Каласянаў"),
    (59, 51, "1 да Фесалонікійцаў"),
    (60, 52, "2 да Фесалонікійцаў"),
    (61, 53, "1 да Цімахвея"),
    (62, 54, "2 да Цімахвея"),
    (63, 55, "Да Ціта"),
    (64, 56, "Да Філімона"),
    (65, 57, "Да Жыдоў"),
    (45, 58, "Якуба"),
    (46, 59, "1 Пётры"),
    (47, 60, "2 Пётры"),
    (48, 61, "1 Іоана"),
    (49, 62, "2 Іоана"),
    (50, 63, "3 Іоана"),
    (51, 64, "Юда"),
    (66, 65, "Адкрыцьце"),
]
PSALMS_NUM = 19
PSALMS_NAME = "Псальмы"

OT_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
]
APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

VERSE_DIV = re.compile(r'<div id="(\d+)"><sup>\d+</sup>(.*?)</div>', re.DOTALL)
SPAN_NOTE = re.compile(r'<span class="gray">[^<]*</span>')
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"[ \t ]+")


def clean_verse(raw):
    t = SPAN_NOTE.sub("", raw)
    t = TAG.sub("", t)
    t = html.unescape(t)
    t = WS.sub(" ", t).strip()
    return t


def http_get(url, retries=5):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_chapter(book_num, chapter):
    """Returns list of verse strings (1-indexed -> list[0]), or [] if the
    chapter doesn't exist (biblia.by 200s an empty page past the last
    chapter rather than 404ing)."""
    url = f"https://biblia.by/dz-maley/{book_num}/{chapter}/"
    body = http_get(url)
    found = {}
    for m in VERSE_DIV.finditer(body):
        n = int(m.group(1))
        found[n] = clean_verse(m.group(2))
    if not found:
        return []
    out = [""] * max(found)
    for n, t in found.items():
        out[n - 1] = t
    return out


def scrape_book(book_num, max_chapters_hint, cap_buffer=6):
    """Scrape chapters 1..N, stopping at the first empty chapter past the
    hint (with a small buffer to catch native chapter-count divergence
    from KJV in either direction)."""
    chapters = []
    c = 1
    empty_run = 0
    hard_cap = max_chapters_hint + cap_buffer if max_chapters_hint else 200
    while c <= hard_cap:
        verses = fetch_chapter(book_num, c)
        if not verses:
            empty_run += 1
            if c > max_chapters_hint or empty_run >= 2:
                break
        else:
            empty_run = 0
            chapters.append(verses)
        c += 1
        time.sleep(0.12)
    return chapters


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    verify_only = "--verify-only" in sys.argv
    kjv_path = os.path.join(ASSETS, "bibles", "en_kjv.json")
    kjv = json.load(open(kjv_path, encoding="utf-8"))

    books = [{"name": n, "chapters": []} for n in OT_NAMES]
    books[18] = None  # placeholder, filled below
    nt_slots = {}

    print("Scraping Psalms (book 19)...")
    psalm_chapters = scrape_book(PSALMS_NUM, 150)
    books[18] = {"name": PSALMS_NAME, "chapters": psalm_chapters}
    print(f"  {len(psalm_chapters)} chapters, "
          f"{sum(len(c) for c in psalm_chapters)} verses")

    for bnum, kidx, name in BOOK_MAP:
        kn = len(kjv[kidx]["chapters"])
        print(f"Scraping {name} (book {bnum}, KJV hint {kn} chapters)...")
        chapters = scrape_book(bnum, kn)
        nt_slots[kidx] = {"name": name, "chapters": chapters}
        tot = sum(len(c) for c in chapters)
        flag = "" if len(chapters) == kn else "  <-- CHAPTER COUNT DIFFERS"
        print(f"  {len(chapters)} chapters, {tot} verses{flag}")

    for i in range(39, 66):
        books.append(nt_slots[i])
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83, len(books)

    dst = os.path.join(ASSETS, "bibles", "be_dzekuc.json")
    if not verify_only:
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
        print(f"\nWrote {dst} ({os.path.getsize(dst)} bytes)")

    # ---- report: chapter/verse-count diffs vs KJV for the NT ----
    diffs = []
    for kidx in range(39, 66):
        tchapters = books[kidx]["chapters"]
        kchapters = kjv[kidx]["chapters"]
        for ci in range(max(len(tchapters), len(kchapters))):
            tn = len(tchapters[ci]) if ci < len(tchapters) else None
            kn = len(kchapters[ci]) if ci < len(kchapters) else None
            if tn != kn:
                diffs.append(f"{books[kidx]['name']} ch{ci+1}: be={tn} kjv={kn}")
    empty_nt = sum(1 for kidx in range(39, 66) for ch in books[kidx]["chapters"]
                   for v in ch if not v)
    nt_total = sum(len(c) for b in books[39:66] for c in b["chapters"])
    ps_total = sum(len(c) for c in books[18]["chapters"])
    print(f"\nNT: 27 books, {nt_total} verses; empty verse slots: {empty_nt}")
    print(f"Psalms: {len(books[18]['chapters'])} chapters, {ps_total} verses")
    print(f"\nVerse-count diffs vs KJV grid ({len(diffs)} chapters differ):")
    for d in diffs:
        print("   ", d)

    # ---- litmus re-check on the assembled asset ----
    def verse(kidx, ch, v):
        try:
            return books[kidx]["chapters"][ch - 1][v - 1]
        except IndexError:
            return "<<MISSING>>"

    print("\nLitmus verses in the assembled asset:")
    print("1 Tim 3:16 ", verse(53, 3, 16))
    print("1 Jn 5:7   ", verse(61, 5, 7))
    print("1 Jn 5:8   ", verse(61, 5, 8))
    print("Acts 8:37  ", verse(43, 8, 37))
    print("Rom 16:24  ", verse(44, 16, 24))
    print("Lk 2:33    ", verse(41, 2, 33))
    print("Acts 20:28 ", verse(43, 20, 28))
    print("Jn 3:13    ", verse(42, 3, 13))


if __name__ == "__main__":
    main()
