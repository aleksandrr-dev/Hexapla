# -*- coding: utf-8 -*-
"""Cache the raw HTML of the 1827 J.D. Kieffer Turkish Bible (OT + NT) from
osmbibletextreader.com - the reader embedded by osmanlicakelam.net.

    python tools/fetch_osm_kieffer.py            # plan: list books, fetch nothing
    python tools/fetch_osm_kieffer.py --apply    # fetch every book not cached yet

Permission: OsmKelam, 2026-09-25 (web AND app), on condition their link is
shown at the top of the column - research/_evidence/osmkelam_permission_2026-09-25.md.
They recommend a yearly re-download: re-run into a new --cache dir and diff.

## How the reader works (probed 2026-09-25)
- The form is state-in-COOKIES: a POST sets `bibleTitle` / `bookName` cookies,
  and a one-shot POST without that session state returns an empty page (the
  1125 handoff's «no verse_p ids»). So: one Session, POST the title, then POST
  title+book.
- ONE book POST returns the WHOLE BOOK (Matthew: 1071 verse ids, 1:1-28:20);
  the `chapter` field only scrolls. ~70 requests for the whole Bible, not 1,189.
- No charset header: force UTF-8 or the Turkish letters come back as mojibake.

⚠ Never overwrites a cached file; a book whose page has 0 verse ids is NOT
written (it is reported and the run exits 1), so a failed fetch can never be
mistaken for a cached book.
"""
import argparse
import html
import re
import sys
import time
from pathlib import Path

import requests

URL = "https://osmbibletextreader.com/view.php?iso=tur&st=tur"
UA = "Hexapla-offline-bible/1.0 (hexaplabible.com; permission from OsmKelam 2026-09-25)"
TITLES = {
    "ot": "1827 ESKİ AHİT, haz. J.D. Kieffer",
    "nt": "1827 YENİ AHİT (İncil), haz. J.D. Kieffer",
}
DELAY = 2.5
VERSE_ID = re.compile(r'id="verse_p([A-Z0-9]+)\.(\d+)\.(\d+)"')


def options(page, name):
    m = re.search(r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % name, page, re.S)
    if not m:
        return []
    return [html.unescape(v) for v in re.findall(r'<option value="([^"]+)"', m.group(1))]


def post(s, data):
    r = s.post(URL, data=data, timeout=(30, 180))
    r.raise_for_status()
    r.encoding = "utf-8"
    time.sleep(DELAY)
    return r.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="fetch (default: plan only)")
    ap.add_argument("--cache", default="C:/Projects/Hexapla-releases/_work/osm_cache/kieffer1827")
    ap.add_argument("--limit", type=int, default=0, help="stop after N fetched books")
    a = ap.parse_args()

    cache = Path(a.cache)
    fetched = failed = 0
    for key, title in TITLES.items():
        s = requests.Session()
        s.headers["User-Agent"] = UA
        books = options(post(s, {"bibleTitle": title}), "bookName")
        print(f"{key}: {len(books)} book entries under «{title}»")
        if not books:
            print("  ⛔ no bookName options - the form changed; nothing fetched")
            return 2
        for i, book in enumerate(books, 1):
            out = cache / key / f"{i:02d}.html"
            if out.exists():
                print(f"  {i:02d} {book}: cached")
                continue
            if not a.apply:
                print(f"  {i:02d} {book}: would fetch")
                continue
            if a.limit and fetched >= a.limit:
                break
            page = post(s, {"bibleTitle": title, "bookName": book})
            ids = VERSE_ID.findall(page)
            if not ids:
                print(f"  ⛔ {i:02d} {book}: 0 verse ids ({len(page)} B) - NOT written")
                failed += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(page, encoding="utf-8", newline="\n")
            (cache / key / f"{i:02d}.name").write_text(book, encoding="utf-8", newline="\n")
            fetched += 1
            print(f"  {i:02d} {book}: {len(ids)} verses {ids[0][0]} "
                  f"{int(ids[0][1])}:{int(ids[0][2])}-{int(ids[-1][1])}:{int(ids[-1][2])}",
                  flush=True)
    print(f"\nfetched {fetched}, failed {failed}" + ("" if a.apply else "  (PLAN ONLY)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
