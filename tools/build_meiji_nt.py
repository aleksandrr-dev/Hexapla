"""Meiji Motoyaku (明治元訳) Japanese Bible -> app asset.

The first complete Japanese Bible: NT 1880, OT 1887, by the missionary
translation committee (Hepburn et al.) — translated from the Textus
Receptus tradition BEFORE Westcott-Hort (1881), hence TR readings
(e.g. 1 Tim 3:16 神肉體となりて顯れ, "GOD manifested in the flesh").
Public domain.

Sources:
- OT: scrollmapper JapBungo (the 文語 OT is the Meiji OT, 1953 printing;
  only the NT was ever replaced by the 1917 Taisho revision there).
- NT: ja.wikisource.org 明治元訳新約聖書 (明治37年), digitized from the
  National Diet Library scans, one page per chapter, {{ruby|漢字|かな}}
  furigana markup (stripped to base text here).

Verifies chapter counts against the app KJV and prints verse-count
diffs (TR versification). Output: assets/bibles/ja_meiji.json.

Usage: python build_meiji_nt.py <scrollmapper-JapBungo.json>
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets")
API = "https://ja.wikisource.org/w/api.php"

# 1904 Wikisource page names, in canonical NT order.
NT_BOOKS = [
    "馬太傳福音書", "馬可傳福音書", "路加傳福音書", "約翰傳福音書",
    "使徒行傳", "羅馬書", "哥林多前書", "哥林多後書", "加拉太書",
    "以弗所書", "腓立比書", "哥羅西書", "帖撒羅尼迦前書", "帖撒羅尼迦後書",
    "提摩太前書", "提摩太後書", "提多書", "腓利門書", "希伯來書",
    "雅各書", "彼得前書", "彼得後書", "約翰第一書", "約翰第二書",
    "約翰第三書", "猶太書", "約翰默示録",
]

# 文語 OT names as in the 1953-printing lineage the OT text descends from.
OT_NAMES = [
    "創世記", "出エジプト記", "レビ記", "民數紀略", "申命記", "ヨシュア記",
    "士師記", "ルツ記", "サムエル前書", "サムエル後書", "列王紀略上",
    "列王紀略下", "歷代志略上", "歷代志略下", "エズラ書", "ネヘミヤ記",
    "エステル書", "ヨブ記", "詩篇", "箴言", "傳道之書", "雅歌",
    "イザヤ書", "ヱレミヤ記", "哀歌", "エゼキエル書", "ダニエル書",
    "ホセア書", "ヨエル書", "アモス書", "オバデヤ書", "ヨナ書", "ミカ書",
    "ナホム書", "ハバクク書", "ゼパニヤ書", "ハガイ書", "ゼカリヤ書",
    "マラキ書",
]


def kanji_num(n):
    d = "一二三四五六七八九"
    if n <= 9:
        return d[n - 1]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + d[n - 11]
    tens, ones = divmod(n, 10)
    return d[tens - 1] + "十" + (d[ones - 1] if ones else "")


def api_fetch(titles):
    """Batch-fetch wikitext for up to 50 titles; returns {title: text}."""
    q = urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "format": "json", "titles": "|".join(titles),
    })
    req = urllib.request.Request(
        f"{API}?{q}", headers={"User-Agent": "Hexapla-bible-app/1.0 (data pipeline)"}
    )
    data = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req) as r:
                data = json.load(r)
            break
        except Exception as e:
            if attempt == 4:
                raise
            print(f"  retry {attempt+1} after {e.__class__.__name__}")
            time.sleep(3 * (attempt + 1))
    out = {}
    for p in data["query"]["pages"].values():
        if "revisions" in p:
            out[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
    return out


RUBY = re.compile(r"\{\{ruby\|([^|{}]*)\|[^{}]*\}\}")
LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")
TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
NOTE_MARK = re.compile(r"[(（]※\d+[)）]")
TAGS = re.compile(r"<[^>]+>")


def clean_line(s):
    prev = None
    while prev != s:
        prev = s
        s = RUBY.sub(r"\1", s)
    s = LINK.sub(r"\1", s)
    s = TEMPLATE.sub("", s)
    s = NOTE_MARK.sub("", s)
    s = TAGS.sub("", s)
    return s.strip()


# A range heading — «43-44 イエス…» — is how these pages print a verse group
# the committee translated as ONE unit. Wikisource writes the numbers joined by
# a hyphen; both ASCII and the CJK dashes occur, so accept them all.
RANGE_SEP = "[-－–—ー]"
VERSE_NUM_RE = re.compile(r"(?<![0-9])(\d{1,3}(?:%s\d{1,3})*)[  \t]?" % RANGE_SEP)

# Filled by parse_chapter, read by the caller: (first, [covered tail verses]).
# ▶ These become the versemap runs that pair a KJV verse range with the one
#   Japanese block, so the builder EMITS them rather than anyone hand-listing.
RANGES = []


def parse_chapter(wikitext, ranges_out=None):
    """-> [verse text, ...] for one Wikisource chapter page.

    ⛔⛔ TWO DEFECTS WERE FIXED HERE ON 2026-09-20. Both shipped in
    `ja_meiji.json` from 2026-07-11 until then. Do not undo either without
    reading `docs/ASSET_DEFECTS.md`.

    1. **Range headings.** «43-44 text» was split on EVERY Arabic numeral, so
       43 got the bare hyphen left between the numbers and 44 got the text of
       both. That is where the asset's 32 `-` verses came from — the text was
       never missing, only mis-addressed. ⛔ NONE of the 32 is a verse the
       Textus Receptus omits, so this was never an editorial absence.
       The text now goes in the FIRST slot of the range and the rest stay
       empty, which is the shape the reader already skips and the shape the
       corpus already uses for Meiji's Acts 20:37+38.

    2. **Footnote blocks.** A `※N 明治14(1881)年版では以下のとおり` heading is
       followed by NUMBERED lines quoting the 1881 edition's variant of that
       verse. The old code skipped the heading only, so the splitter read those
       numbered lines as scripture and spliced the 1881 variant onto the 1904
       verse — Rom 3:25-26 and Rom 6:10 shipped printed TWICE, in two
       spellings. Everything from the first `※` to the end of the page is now
       dropped. ✅ Verified over the FULL denominator, not a sample: all 260
       chapter pages were scanned, and every line following a `※` heading is a
       note, an 1881 variant line (exactly 3, all in Romans) or a DEFAULTSORT —
       never scripture.
    """
    kept = []
    in_footnote = False
    for raw in wikitext.split("\n"):
        raw = raw.strip()
        if raw.startswith("※"):
            in_footnote = True      # ⛔ and so is everything after it
            continue
        if in_footnote or raw.startswith("=") or raw.startswith("[[カテゴリ"):
            continue
        kept.append(raw)
    text = clean_line(" ".join(kept))
    # Verse numbers are the only Arabic digits on these pages (the scripture
    # body uses kanji numerals), so split the whole chapter on them — this
    # also catches verses that share a physical line.
    parts = VERSE_NUM_RE.split(text)
    verses, covered = {}, set()
    for i in range(1, len(parts) - 1, 2):
        nums = [int(x) for x in re.split(RANGE_SEP, parts[i])]
        t = parts[i + 1].strip()
        if not t or not all(1 <= n <= 200 for n in nums):
            continue
        n = nums[0]
        verses[n] = (verses[n] + " " + t) if n in verses else t
        if len(nums) > 1:
            covered.update(nums[1:])
            rec = (n, nums[1:])
            RANGES.append(rec)
            if ranges_out is not None:
                ranges_out.append(rec)
    if not verses:
        return []
    out = [""] * max(list(verses) + list(covered))
    for n, t in verses.items():
        out[n - 1] = t
    return out


def main(japbungo_path):
    sys.stdout.reconfigure(encoding="utf-8")
    kjv = json.load(open(os.path.join(ASSETS, "bibles", "en_kjv.json"),
                         encoding="utf-8"))
    bungo = json.load(open(japbungo_path, encoding="utf-8"))["books"]

    # OT straight from scrollmapper (Meiji text), names replaced.
    books = []
    for i in range(39):
        chapters = []
        for ch in bungo[i]["chapters"]:
            vmax = max(v["verse"] for v in ch["verses"])
            verses = [""] * vmax
            for v in ch["verses"]:
                verses[v["verse"] - 1] = v["text"].strip()
            chapters.append(verses)
        books.append({"name": OT_NAMES[i], "chapters": chapters})

    # NT scraped from Wikisource.
    titles = []
    for bi, book in enumerate(NT_BOOKS):
        n_ch = len(kjv[39 + bi]["chapters"])
        for c in range(1, n_ch + 1):
            # Single-chapter books have no 第一章 subpage.
            page = f"{book}(明治元訳)" if n_ch == 1 else f"{book}(明治元訳) 第{kanji_num(c)}章"
            titles.append((bi, c, page))

    fetched = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        fetched.update(api_fetch([t[2] for t in batch]))
        time.sleep(1)

    missing = []
    nt = []
    for bi, book in enumerate(NT_BOOKS):
        n_ch = len(kjv[39 + bi]["chapters"])
        chapters = []
        for c in range(1, n_ch + 1):
            title = f"{book}(明治元訳)" if n_ch == 1 else f"{book}(明治元訳) 第{kanji_num(c)}章"
            if title not in fetched:
                missing.append(title)
                chapters.append([])
                continue
            chapters.append(parse_chapter(fetched[title]))
        nt.append({"name": book, "chapters": chapters})
    books.extend(nt)

    # Report: verse-count diffs vs KJV for the scraped NT.
    diffs = []
    for bi in range(39, 66):
        for c, verses in enumerate(books[bi]["chapters"]):
            kn = len(kjv[bi]["chapters"][c])
            if len(verses) != kn:
                diffs.append(f"{books[bi]['name']} {c+1}: {len(verses)} vs KJV {kn}")
    empty = sum(1 for bi in range(39, 66) for ch in books[bi]["chapters"]
                for v in ch if not v)

    dst = os.path.join(ASSETS, "bibles", "ja_meiji.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    nt_verses = sum(len(c) for b in books[39:] for c in b["chapters"])
    print(f"{dst}: 66 books, {total} verses ({nt_verses} NT)")
    print(f"missing chapter pages: {len(missing)}")
    for m_ in missing[:10]:
        print("   ", m_)
    print(f"NT verse-count diffs vs KJV: {len(diffs)}; empty NT verses: {empty}")
    for d_ in diffs[:15]:
        print("   ", d_)


if __name__ == "__main__":
    main(sys.argv[1])
