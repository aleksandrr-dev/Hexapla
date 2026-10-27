# -*- coding: utf-8 -*-
"""Build the Thai King James Version asset from Dr Philip Pope's 2026 text.

    python tools/build_th_kjv.py                 # census + grid report, writes nothing
    python tools/build_th_kjv.py --out <file>    # also write the asset

Source: «Thai KJV Bible 2026 Version.txt», extracted with 7-Zip from the
self-extracting «Thai KJV Bible 2026 Version.exe» that Dr Pope e-mailed the
owner on 2026-10-21 with permission to use it in Hexapla (credit line in
SOURCES below). The .exe was never run.

## The source format (census, 2026-10-21)
- cp874 (Windows Thai), CR line ends, one verse per line, 31,102 lines.
- `<abbr> <ch>.<v>\\t<text>`, books in KJV order under Pope's own Thai
  abbreviations (`ปฐก` .. `วว`).
- No markup. `[...]` occurs 14 times: the KJV's Pauline subscriptions at the
  end of the epistles (Rom 16:27 ...). Kept verbatim: Pope's terms are «do not
  change any of the words or punctuation», and BibleRepo only strips `{...}`.
- 0 U+200B (the eBible 2003 copy had 627 inside syllables; this one is clean).

## Book names
The 2026 .txt carries abbreviations only. Display names are the `\\h` headers
of the eBible `thaKJV` USFM (the same translation, 2003 files), with every
U+200B removed and the «หนังสือ» («the book of») prefix dropped, which that
file applies to 9 books and not to the other 57.

⛔ Any line that does not parse, a grid cell that differs from the KJV asset,
an empty verse, or any character outside the census is a hard failure.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SRC = Path("C:/Projects/Hexapla-releases/research/_thai_src/x/Thai KJV Bible 2026 Version.txt")
KJV = Path("C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json")

ABBR = ("ปฐก อพย ลนต กดว พบญ ยชว วนฉ นรธ 1ซมอ 2ซมอ 1พกษ 2พกษ 1พศด 2พศด อสร นหม "
        "อสธ โยบ สดด สภษ ปญจ พซม อสย ยรม พคค อสค ดนล ฮชย ยอล อมส อบด ยนา มคา นฮม "
        "ฮบก ศฟย ฮกก ศคย มลค มธ มก ลก ยน กจ รม 1คร 2คร กท อฟ ฟป คส 1ธส 2ธส 1ทธ "
        "2ทธ ทต ฟม ฮบ ยก 1ปต 2ปต 1ยน 2ยน 3ยน ยด วว").split()

NAMES = [
    "ปฐมกาล", "อพยพ", "เลวีนิติ", "กันดารวิถี", "พระราชบัญญัติ", "โยชูวา",
    "ผู้วินิจฉัย", "นางรูธ", "1 ซามูเอล", "2 ซามูเอล", "1 พงศ์กษัตริย์",
    "2 พงศ์กษัตริย์", "1 พงศาวดาร", "2 พงศาวดาร", "เอสรา", "เนหะมีย์",
    "เอสเธอร์", "โยบ", "เพลงสดุดี", "สุภาษิต", "ปัญญาจารย์", "เพลงซาโลมอน",
    "อิสยาห์", "เยเรมีย์", "เพลงคร่ำครวญ", "เอเสเคียล", "ดาเนียล", "โฮเชยา",
    "โยเอล", "อาโมส", "โอบาดีห์", "โยนาห์", "มีคาห์", "นาฮูม", "ฮาบากุก",
    "เศฟันยาห์", "ฮักกัย", "เศคาริยา", "มาลาคี",
    "มัทธิว", "มาระโก", "ลูกา", "ยอห์น", "กิจการ", "โรม", "1 โครินธ์",
    "2 โครินธ์", "กาลาเทีย", "เอเฟซัส", "ฟีลิปปี", "โคโลสี", "1 เธสะโลนิกา",
    "2 เธสะโลนิกา", "1 ทิโมธี", "2 ทิโมธี", "ทิตัส", "ฟีเลโมน", "ฮีบรู",
    "ยากอบ", "1 เปโตร", "2 เปโตร", "1 ยอห์น", "2 ยอห์น", "3 ยอห์น", "ยูดาส",
    "วิวรณ์",
]

LINE = re.compile(r"^(\S+) (\d+)\.(\d+)\t(.+)$")
# Thai block + what the census found outside it.
ALLOWED = re.compile(r"[\u0e00-\u0e7f 0-9“”‘’()\-\[\].]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    assert len(ABBR) == len(NAMES) == 66

    raw = Path(a.src).read_bytes().decode("cp874")
    lines = raw.split("\r")
    if lines and lines[-1] == "":
        lines.pop()
    books = {ab: [] for ab in ABBR}
    errors = []
    census = Counter()
    for n, ln in enumerate(lines, 1):
        m = LINE.match(ln)
        if not m:
            errors.append(f"line {n}: unparsed {ln[:60]!r}")
            continue
        ab, c, v, text = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip()
        if ab not in books:
            errors.append(f"line {n}: unknown book {ab!r}")
            continue
        chs = books[ab]
        while len(chs) < c:
            chs.append([])
        if v != len(chs[c - 1]) + 1:
            errors.append(f"line {n}: {ab} {c}.{v} out of sequence")
        if not text:
            errors.append(f"line {n}: {ab} {c}.{v} empty")
        for ch in text:
            if not ALLOWED.match(ch):
                census[ch] += 1
        chs[c - 1].append(text)
    if census:
        errors.append(f"characters outside the census: {dict(census)}")

    kjv = json.loads(KJV.read_text(encoding="utf-8"))[:66]
    for i, ab in enumerate(ABBR):
        mine = [len(c) for c in books[ab]]
        ref = [len(c) for c in kjv[i]["chapters"]]
        if mine != ref:
            errors.append(f"grid {ab} ({kjv[i]['name']}): {mine} vs KJV {ref}")

    total = sum(len(c) for b in books.values() for c in b)
    subs = sum(1 for b in books.values() for c in b for t in c if "[" in t)
    print(f"verses {total}  books {sum(1 for b in books.values() if b)}  "
          f"bracketed subscriptions {subs}  U+200B {raw.count(chr(0x200b))}")
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors[:40]:
            print("  " + e)
        return 1
    print("grid matches en_kjv (66 books, every chapter's verse count)")
    if a.out:
        asset = [{"name": NAMES[i], "chapters": books[ab]} for i, ab in enumerate(ABBR)]
        Path(a.out).write_text(json.dumps(asset, ensure_ascii=False, separators=(",", ":")),
                               encoding="utf-8", newline="\n")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
