# -*- coding: utf-8 -*-
"""Re-derive the ja_meiji NT from Wikisource with the fixed parser, and repair the asset.

    python tools/fix_meiji_ranges.py --selftest
    python tools/fix_meiji_ranges.py                 # DRY RUN (the default)
    python tools/fix_meiji_ranges.py --limit 3       # dry run, first 3 changed chapters
    python tools/fix_meiji_ranges.py --apply         # write assets/bibles/ja_meiji.json

WHY THIS EXISTS, AND WHY IT IS NOT A FULL REBUILD. `build_meiji_nt.py` builds
the whole 66-book asset, and its OT half comes from a scrollmapper JapBungo
file that is NO LONGER ON THIS MACHINE. Re-running it would rebuild the NT
correctly and destroy the OT. So this script re-derives ONLY the 27 NT books,
from the same Wikisource pages and the same (now fixed) `parse_chapter`, and
splices them into the existing asset. The OT is not read, not parsed and not
written.

WHAT IT REPAIRS — two defects in the shipped asset, both fixed at source in
`build_meiji_nt.parse_chapter` on 2026-09-20:

  1. 32 verse slots holding a bare `-`. Wikisource prints a verse group the
     committee translated as one unit under a RANGE heading («43-44 イエス…»);
     the old splitter gave slot 43 the hyphen and slot 44 the text of both.
     ⛔ The text was never missing and NONE of the 32 is a TR omission.
  2. Rom 3:25-26 and Rom 6:10 shipped with the verse printed TWICE, in two
     spellings — the old parser skipped a `※` footnote HEADING but then read
     the numbered 1881-edition variant lines under it as scripture.

⛔ DRY RUN IS THE DEFAULT and prints every chapter it would change, with the
before/after of each differing verse. Run it, read it, and only then `--apply`.
A backup of the existing asset is written next to it before any write.

⚠ THIS CHANGES VERSE ADDRESSING, so `versemap.json` must follow: the ranges
this script prints under «VERSEMAP RUNS» pair the KJV verses with the single
Japanese block. Feed them to `build_versemap.py` — do not hand-edit the map.

▶ Control after applying: `audit_empty_verses.py ja_meiji` must report ZERO
placeholder slots. Its MID/empty count rises by exactly the number of covered
tail verses, which is the repair working, not a new defect.

Controls: `--selftest` parses three fixtures — a range heading, a footnote
block with numbered 1881 lines, and an ordinary chapter that must come back
byte-identical — and must flag exactly the first two;
`HEXAPLA_NO_MEIJIFIX=1` restores the OLD parsing and the selftest must then
FAIL (exit 1).
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_meiji_nt as B                                    # noqa: E402

ASSET = os.path.join(HERE, "..", "app", "src", "main", "assets",
                     "bibles", "ja_meiji.json")
OT_BOOKS = 39


def old_parse_chapter(wikitext):
    """The parser AS IT SHIPPED, kept only as the known-bad control."""
    kept = []
    for raw in wikitext.split("\n"):
        raw = raw.strip()
        if raw.startswith("※") or raw.startswith("=") or raw.startswith("[[カテゴリ"):
            continue
        kept.append(raw)
    text = B.clean_line(" ".join(kept))
    parts = re.split(r"(?<![0-9])(\d{1,3})[  \t]?", text)
    verses = {}
    for i in range(1, len(parts) - 1, 2):
        n = int(parts[i])
        t = parts[i + 1].strip()
        if t and 1 <= n <= 200:
            verses[n] = (verses[n] + " " + t) if n in verses else t
    if not verses:
        return []
    out = [""] * max(verses)
    for n, t in verses.items():
        out[n - 1] = t
    return out


def parser():
    if os.environ.get("HEXAPLA_NO_MEIJIFIX") == "1":
        return old_parse_chapter                              # known-bad control
    return B.parse_chapter


def page_title(book, n_ch, c):
    if n_ch == 1:
        return "%s(明治元訳)" % book
    return "%s(明治元訳) 第%s章" % (book, B.kanji_num(c))


def fetch_nt(kjv):
    titles = []
    for bi, book in enumerate(B.NT_BOOKS):
        n_ch = len(kjv[OT_BOOKS + bi]["chapters"])
        for c in range(1, n_ch + 1):
            titles.append((bi, c, page_title(book, n_ch, c)))
    fetched = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        fetched.update(B.api_fetch([t[2] for t in batch]))
        print("  fetched %d/%d pages" % (min(i + 20, len(titles)), len(titles)))
        time.sleep(1)
    return titles, fetched


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true",
                    help="write the asset (default is a dry run)")
    ap.add_argument("--limit", type=int, default=0,
                    help="dry run: show only the first N changed chapters")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())

    books = json.load(io.open(ASSET, encoding="utf-8"))
    kjv = json.load(io.open(os.path.join(os.path.dirname(ASSET), "en_kjv.json"),
                            encoding="utf-8"))
    pc = parser()

    print("fetching the 27 NT books from ja.wikisource.org …")
    titles, fetched = fetch_nt(kjv)
    missing = [t for _, _, t in titles if t not in fetched]
    # ⛔ A failed fetch must never look like a chapter with no changes.
    if missing:
        print("⛔ %d chapter page(s) did NOT fetch — REFUSING to touch the "
              "asset. A missing page would silently keep its defective "
              "verses while the run reported success." % len(missing))
        for m in missing[:10]:
            print("   ", m)
        return 2

    changed, ranges, dup_fixed = [], [], []
    for bi, c, title in titles:
        old = books[OT_BOOKS + bi]["chapters"][c - 1]
        rng = []
        new = pc(fetched[title], rng) if pc is B.parse_chapter else pc(fetched[title])
        for first, tail in rng:
            ranges.append((OT_BOOKS + bi, c, first, tail))
        if new != old:
            diffs = []
            for v in range(max(len(old), len(new))):
                o = old[v] if v < len(old) else "<no slot>"
                n = new[v] if v < len(new) else "<no slot>"
                if o != n:
                    diffs.append((v + 1, o, n))
                    if o.strip() and n.strip() and len(o) > len(n) + 20:
                        dup_fixed.append((books[OT_BOOKS + bi]["name"], c, v + 1))
            changed.append((OT_BOOKS + bi, c, diffs))
            books[OT_BOOKS + bi]["chapters"][c - 1] = new

    placeholders = sum(1 for b in books[OT_BOOKS:] for ch in b["chapters"]
                       for v in ch if v.strip() == "-")
    print("\n%d chapter(s) differ · %d range heading(s) found · "
          "%d verse(s) shortened (duplicated text removed) · "
          "%d `-` placeholder(s) left after the fix"
          % (len(changed), len(ranges), len(dup_fixed), placeholders))

    shown = changed[:a.limit] if a.limit else changed
    for bi, c, diffs in shown:
        print("\n--- %s %d  (%d verse slot(s) differ)" % (books[bi]["name"], c, len(diffs)))
        for v, o, n in diffs[:8]:
            print("   v%-3d OLD %s" % (v, (o[:70] + "…") if len(o) > 70 else o))
            print("        NEW %s" % ((n[:70] + "…") if len(n) > 70 else n))
    if a.limit and len(changed) > a.limit:
        print("\n… %d more changed chapter(s) not shown (--limit %d)"
              % (len(changed) - a.limit, a.limit))

    print("\n=== VERSEMAP RUNS (%d) — KJV range -> the one Japanese block ===" % len(ranges))
    for bi, c, first, tail in ranges:
        print("  %-22s %d:%d-%d  ->  block at %d:%d"
              % (books[bi]["name"], c, first, tail[-1], c, first))

    if placeholders:
        print("\n⛔ %d `-` slot(s) SURVIVE the fix — they are NOT range tails "
              "and need their own explanation before this ships." % placeholders)

    if not a.apply:
        print("\n▶ DRY RUN — nothing written. Re-run with --apply once the "
              "diffs above read correctly.")
        return 0

    bak = ASSET + ".bak-2026-09-20-meijiranges"
    if not os.path.exists(bak):
        shutil.copy2(ASSET, bak)
        print("\nbackup: %s" % bak)
    with io.open(ASSET, "w", encoding="utf-8") as fh:
        json.dump(books, fh, ensure_ascii=False, separators=(",", ":"))
    print("✅ wrote %s" % ASSET)
    print("▶ NOW: feed the VERSEMAP RUNS above to build_versemap.py, then run "
          "`audit_empty_verses.py ja_meiji` — it must report ZERO placeholders.")
    return 0


RANGE_FIXTURE = """43-44 {{ruby|嚴|きびし}}く{{ruby|戒|いまし}}めて
45 {{ruby|然|され}}ど{{ruby|彼|かれ}}{{ruby|出|いで}}て
"""

FOOTNOTE_FIXTURE = """25-26 {{ruby|神|かみ}}はその{{ruby|血|ち}}によりて
27 {{ruby|然|され}}ば{{ruby|誇|ほこ}}るところ{{ruby|何|いづく}}にかある
※4 明治14(1881)年版では以下のとおり<br />
25 {{ruby|神|かみ}}は{{ruby|忍|しのび}}て{{ruby|已往|すぎこしかた}}の{{ruby|罪|つみ}}を
26 {{ruby|神|かみ}}はイエスを{{ruby|信|しん}}ずる{{ruby|者|もの}}を
{{DEFAULTSORT:ろーましよ}}
"""

PLAIN_FIXTURE = """1 {{ruby|太初|はじめ}}に{{ruby|道|ことば}}あり
2 この{{ruby|道|ことば}}は{{ruby|太初|はじめ}}に{{ruby|神|かみ}}と{{ruby|偕|とも}}にあり
"""


def selftest():
    pc = parser()

    def run(text):
        rng = []
        return (pc(text, rng) if pc is B.parse_chapter else pc(text)), rng

    # 1. a range heading: text in the FIRST slot, the tail slot empty
    out, rng = run(RANGE_FIXTURE)
    ok1 = (len(out) >= 45 and out[42].startswith("嚴") and out[43] == ""
           and out[44].startswith("然") and rng == [(43, [44])])
    print("  %s range «43-44» -> v43 text, v44 empty, range recorded %s"
          % ("✅" if ok1 else "⛔", rng))

    # 2. a footnote block: the 1881 variant lines must NOT reach the text
    out2, _ = run(FOOTNOTE_FIXTURE)
    v25 = out2[24] if len(out2) > 24 else ""
    v26 = out2[25] if len(out2) > 25 else ""
    ok2 = ("忍" not in v25 and "忍" not in v26
           and "-" not in (v25.strip(), v26.strip()) and v25.startswith("神はその血"))
    print("  %s footnote block dropped -> v25 %r" % ("✅" if ok2 else "⛔", v25[:24]))

    # 3. ⛔ an ordinary chapter must be UNCHANGED by all of this
    out3, rng3 = run(PLAIN_FIXTURE)
    ok3 = (out3 == ["太初に道あり", "この道は太初に神と偕にあり"] and not rng3)
    print("  %s ordinary chapter untouched -> %s" % ("✅" if ok3 else "⛔", out3))

    ok = ok1 and ok2 and ok3
    print("selftest: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
