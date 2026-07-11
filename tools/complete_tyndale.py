"""Complete en_tyndale.json: fill the books Tyndale published that the
shipped asset lacks.

The shipped asset (from scrollmapper's "Tyndale" = CrossWire SWORD module,
text by Sergej Fedosov / Slavic Bible, public domain) contains only
Genesis + 9 NT books.  William Tyndale actually published the complete
27-book New Testament (1526, rev. 1534), the Pentateuch (1530) and Jonah
(1531).  This script fetches the missing 23 books from two web mirrors of
the same public-domain digitization lineage (verified byte-identical to
the shipped text for the overlapping books, KJV versification):

  primary : https://studybible.info/Tyndale/<Book>%20<ch>       ("SB")
  secondary: https://www.biblestudytools.com/tyn/<book>/<ch>.html ("BST")

Each mirror has a handful of holes the other fills; the merge below is
per-verse (SB preferred).  Four verse slots are empty in BOTH mirrors
because Tyndale's own text merges/omits them (verified against the
neighbours' content, and for Exodus against the independent Gutenberg
#10553 transcription of the 1530 Pentateuch):

  Exodus    40:14  (Tyndale 1530 lacks "bring his sons, clothe them...";
                    jumps from 40:13 to the everlasting-priesthood clause)
  Leviticus 27:18  (content inside 27:17)
  Numbers    7:22  (repetitive offering list)
  Galatians  5:21  (content inside 5:20: "envyinge murther dronkenes...")

Those stay "" — same convention as the 8 empty slots already shipped
(Gen 9:29, Mt 5:47, Mk 11:26, Lk 17:37, Rom 1:22, 1 Cor 3:21, Heb 11:40,
Rev 21:27).

The 10 shipped books are preserved byte-identically: the asset was written
with json.dumps(..., ensure_ascii=False) default separators, which this
script reuses, and every originally non-empty book is asserted unchanged.

Verification performed on every added chapter: verse count == en_kjv.json,
verse numbers contiguous from 1, no unexpected empty verses.  Litmus:
1 Tim 3:16 must read "God was shewed in the flesshe" (deity gate),
Acts 8:37 present, 1 John 5:7 Comma reported.

Usage:  python tools/complete_tyndale.py
        (run from the repo root; caches pages in tools/.tyndale_cache/)
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "app/src/main/assets/bibles/en_tyndale.json")
KJV = os.path.join(ROOT, "app/src/main/assets/bibles/en_kjv.json")
CACHE = os.path.join(ROOT, "tools/.tyndale_cache")

# The 23 books Tyndale published that the shipped asset lacks.
MISSING = [
    "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Jonah",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
    "Titus", "Philemon", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude",
]

# (book, chapter, verse) slots empty in both mirrors -- genuine merges in
# Tyndale's text (see module docstring).  Anything else empty is an error.
EXPECTED_EMPTY = {
    ("Exodus", 40, 14),
    ("Leviticus", 27, 18),
    ("Numbers", 7, 22),
    ("Galatians", 5, 21),
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, cache_name):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, cache_name)
    if os.path.exists(fn) and os.path.getsize(fn) > 1000:
        with open(fn, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    with open(fn, "w", encoding="utf-8") as f:
        f.write(h)
    time.sleep(0.3)  # politeness
    return h


def clean(txt):
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def is_junk(txt):
    """Placeholder markers used by the mirrors for missing verses."""
    return not txt or not re.search(r"[A-Za-z]", txt)  # "", "...", etc.


def parse_sb(book, ch):
    """studybible.info chapter -> {verse_num: text}."""
    url = "https://studybible.info/Tyndale/%s%%20%d" % (
        urllib.parse.quote(book), ch)
    h = fetch(url, "sb_%s_%d.html" % (book.replace(" ", "_"), ch))
    m = re.search(r'class="passage row Tyndale"(.*?)</div>', h, re.S)
    if not m:
        return {}
    parts = re.split(
        r'<sup><a class="verse_ref[^"]*"[^>]*>(\d+)</a></sup>', m.group(1))
    out = {}
    for i in range(1, len(parts), 2):
        t = clean(parts[i + 1])
        if "(OMITTED TEXT)" in t:
            t = ""
        out[int(parts[i])] = t
    return out


BST_VERSE = re.compile(
    r'data-verse-id="(\d+)".*?<span class="bible-text">(.*?)</span>', re.S)


def parse_bst(book, ch):
    """biblestudytools.com chapter -> {verse_num: text}."""
    slug = book.lower().replace(" ", "-")
    url = "https://www.biblestudytools.com/tyn/%s/%d.html" % (slug, ch)
    h = fetch(url, "bst_%s_%d.html" % (slug, ch))
    out = {}
    for num, txt in BST_VERSE.findall(h):
        t = clean(txt)
        if "(OMITTED TEXT)" in t:
            t = ""
        out[int(num)] = t
    return out


def main():
    with open(ASSET, "rb") as f:
        raw = f.read()
    asset = json.loads(raw.decode("utf-8"))
    # Byte-fidelity precondition: default-separator dump reproduces the file.
    if json.dumps(asset, ensure_ascii=False).encode("utf-8") != raw:
        sys.exit("ABORT: asset does not round-trip byte-identically; "
                 "serialization convention changed?")
    with open(KJV, encoding="utf-8") as f:
        kjv = json.load(f)
    kjv_by_name = {b["name"]: b["chapters"] for b in kjv}
    names = [b["name"] for b in asset]

    # Snapshot of every already-populated book, for the preservation check.
    shipped = {b["name"]: json.dumps(b, ensure_ascii=False)
               for b in asset if b["chapters"]}
    print("Shipped books preserved as-is: %s" % ", ".join(sorted(shipped)))

    problems = []
    warnings = []
    filled_empty = []
    for book in MISSING:
        tgt = asset[names.index(book)]
        if tgt["chapters"]:
            print("%s already populated -- skipping" % book)
            continue
        kch = kjv_by_name[book]
        chapters = []
        for ci, kverses in enumerate(kch):
            ch = ci + 1
            want = len(kverses)
            sb = parse_sb(book, ch)
            bst = parse_bst(book, ch)
            # A mirror whose verse numbers exceed the KJV chapter length is
            # misassembled there (e.g. BST 2 Thess 1 carries 2:13-17 as
            # 1:13-17) -- drop it for this chapter rather than truncate.
            if sb and max(sb) > want:
                warnings.append("%s %d: SB has %d verses vs KJV %d -- "
                                "SB ignored for this chapter"
                                % (book, ch, max(sb), want))
                sb = {}
            if bst and max(bst) > want:
                warnings.append("%s %d: BST has %d verses vs KJV %d -- "
                                "BST ignored for this chapter"
                                % (book, ch, max(bst), want))
                bst = {}
            if not sb and not bst:
                sys.exit("ABORT: %s %d unavailable from both mirrors" %
                         (book, ch))
            verses = []
            for n in range(1, want + 1):
                t = sb.get(n, "")
                if is_junk(t):
                    t = bst.get(n, "")
                if is_junk(t):
                    t = ""
                    if (book, ch, n) in EXPECTED_EMPTY:
                        filled_empty.append("%s %d:%d" % (book, ch, n))
                    else:
                        problems.append("%s %d:%d EMPTY in both mirrors"
                                        % (book, ch, n))
                if "{" in t or "}" in t:
                    # Braces would be eaten by the app's margin-note
                    # stripper; the Tyndale text has none.
                    problems.append("%s %d:%d contains braces" % (book, ch, n))
                verses.append(t)
            chapters.append(verses)
        tgt["chapters"] = chapters
        nv = sum(len(c) for c in chapters)
        print("%s: %d chapters, %d verses" % (book, len(chapters), nv))

    # ---- verification -------------------------------------------------
    # Litmus: deity gate (1 Tim 3:16), Acts 8:37, Comma (report only).
    def verse(book, ch, v):
        return asset[names.index(book)]["chapters"][ch - 1][v - 1]

    t316 = verse("1 Timothy", 3, 16)
    if "God was shewed in the fles" not in t316:
        problems.append("LITMUS FAIL 1 Tim 3:16: %r" % t316)
    if not verse("Acts", 8, 37).strip():
        problems.append("LITMUS FAIL Acts 8:37 empty")
    print("1 Tim 3:16: %s" % t316)
    print("1 John 5:7: %s" % verse("1 John", 5, 7))

    # Shipped books byte-identical.
    for name, snap in shipped.items():
        if json.dumps(asset[names.index(name)], ensure_ascii=False) != snap:
            problems.append("SHIPPED BOOK MUTATED: %s" % name)

    if len(asset) != 83:
        problems.append("book count %d != 83" % len(asset))

    if filled_empty:
        print("Expected empty slots (Tyndale merges, see docstring): %s"
              % ", ".join(filled_empty))
    for w in warnings:
        print("WARNING: " + w)
    if problems:
        print("\n".join("PROBLEM: " + p for p in problems))
        sys.exit("ABORT: %d problem(s); asset NOT written." % len(problems))

    out = json.dumps(asset, ensure_ascii=False).encode("utf-8")
    with open(ASSET, "wb") as f:
        f.write(out)
    populated = sum(1 for b in asset if b["chapters"])
    print("Wrote %s: %d books populated of %d, %d bytes"
          % (ASSET, populated, len(asset), len(out)))


if __name__ == "__main__":
    main()
