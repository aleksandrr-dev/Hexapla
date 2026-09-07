# -*- coding: utf-8 -*-
"""Merge the Þorláksbiblía ø-retrofit adjudication files into ONE list, labelled
by the METHOD each record came from.

    python tools/thorlaks_o_merge.py --chunk matthew_kit
    python tools/thorlaks_o_merge.py --chunk matthew_kit --out _work/o_matthew_MERGED.txt

## ⛔ WHY METHOD LABELLING IS THE WHOLE POINT

Two incompatible methods produced these files and they are NOT interchangeable:

  CROP    — the word cropped out of the native `line<NN>.png` and read beside the
            p14:12:L:1060:96 control (`thorlaks_o_zoom.py`). Validated.
  SHEET   — read off a packed 4-line retrofit sheet at ~6.3x. **DISPROVED
            2026-09-06.** p16 line49 R and p16 line52 L were both called plain
            and both plainly carry the stroke.

⚠⚠ AND THE SHEET METHOD ERRED IN BOTH DIRECTIONS, so its POSITIVES are no more
usable than its negatives. Measured 2026-09-07: `p17 line02 høpdu` was recorded
as ø by the sheet pass; re-read from the native crop against the control, the
bowl is a clean open counter — a FALSE POSITIVE. It had been the only reason to
think that site carried a stroke.

▶ So this tool never silently blends them. A SHEET record is carried through as
evidence of what was once claimed, marked, and excluded from the usable set
unless a CROP record confirms the same site.

A file is CROP if its name contains `READJUDICATED`; otherwise SHEET. That is the
naming convention the campaign actually used, and it is asserted here rather than
guessed per-record.

## What it reports

- the usable (CROP) records, de-duplicated by (page, line, half, word);
- SHEET-only records, listed separately as UNCONFIRMED;
- CONFLICTS, where a CROP record and a SHEET record disagree about the same site;
- PAGE COVERAGE: which pages have been re-adjudicated by the crop method at all.
  ⚠ A page absent from that list has NO trustworthy ø data in either direction.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORK = Path(r"C:\Projects\Hexapla-releases\_work")

# «p16 line19 L  Kicrøllð  | prev: z  -- …»
REC = re.compile(r'^p(\d+)\s+line(\d+)\s+([LR])\s+(.*?)\s*(?:\|\s*prev:\s*(.*?))?\s*$')
# «# p16 sheet04 (lines16-19): …»
SHEET_HDR = re.compile(r'^#\s*p(\d+)\s+sheet(\d+)')


def method_of(path):
    return "CROP" if "READJUDICATED" in path.name.upper() else "SHEET"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", default="matthew_kit",
                    help="only used for the report header")
    ap.add_argument("--glob", default="o_retrofit_*.txt")
    ap.add_argument("--out")
    a = ap.parse_args()

    files = sorted(WORK.glob(a.glob))
    if not files:
        print(f"⛔ no files matched {a.glob} in {WORK} — nothing to merge")
        return 1

    recs = defaultdict(list)          # (page,line,half) -> [(method, word, prev, src)]
    crop_pages = defaultdict(set)     # page -> {sheet numbers re-adjudicated}
    per_file = []

    for f in files:
        m = method_of(f)
        n = 0
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            hs = SHEET_HDR.match(line)
            if hs and m == "CROP":
                crop_pages[int(hs.group(1))].add(int(hs.group(2)))
                continue
            if not line or line.startswith("#"):
                continue
            r = REC.match(line)
            if not r:
                continue
            page, ln, half = int(r.group(1)), int(r.group(2)), r.group(3)
            word = r.group(4).split("  ")[0].strip()
            # drop a trailing «-- reasoning -- CONFIRMED ø» tail if present
            word = re.split(r'\s+--\s+', word)[0].strip()
            recs[(page, ln, half)].append((m, word, (r.group(5) or "").strip(), f.name))
            n += 1
        per_file.append((f.name, m, n))

    print(f"ø retrofit merge — {a.chunk}")
    print(f"{'file':<58}{'method':<8}{'records':>8}")
    for name, m, n in per_file:
        print(f"{name:<58}{m:<8}{n:>8}")

    usable, unconfirmed, conflicts = [], [], []
    for key in sorted(recs):
        entries = recs[key]
        crop = [e for e in entries if e[0] == "CROP"]
        sheet = [e for e in entries if e[0] == "SHEET"]
        if crop:
            usable.append((key, crop[0]))
            if sheet and sheet[0][1] != crop[0][1]:
                conflicts.append((key, crop[0], sheet[0]))
        else:
            unconfirmed.append((key, sheet[0]))

    print(f"\n✅ USABLE (crop-method, validated): {len(usable)} site(s)")
    for (p, ln, h), (_, w, prev, src) in usable:
        print(f"   p{p} line{ln:02d} {h}  {w}" + (f"   | prev: {prev}" if prev else ""))

    print(f"\n⚠ SHEET-ONLY, NOT USABLE: {len(unconfirmed)} site(s)")
    print("   The disproved method claimed these and no crop read has confirmed")
    print("   them. It produced false POSITIVES as well as false negatives, so")
    print("   these are claims, not findings.")
    for (p, ln, h), (_, w, prev, src) in unconfirmed:
        print(f"   p{p} line{ln:02d} {h}  {w}   [{src}]")

    if conflicts:
        print(f"\n⛔ CONFLICTS: {len(conflicts)}")
        for (p, ln, h), c, s in conflicts:
            print(f"   p{p} line{ln:02d} {h}: crop «{c[1]}» vs sheet «{s[1]}»")

    print(f"\n▶ PAGES RE-ADJUDICATED BY THE CROP METHOD")
    if not crop_pages:
        print("   (none)")
    for p in sorted(crop_pages):
        sheets = sorted(crop_pages[p])
        print(f"   p{p}: {len(sheets)} sheet(s)  {sheets[0]}-{sheets[-1]}")
    print("   ⚠ ANY PAGE NOT LISTED HERE HAS NO TRUSTWORTHY ø DATA — not a low")
    print("     rate, not a clean bill: no measurement at all.")

    if a.out:
        out = Path(a.out)
        lines = ["# ø retrofit — MERGED usable (crop-method) sites only.",
                 "# Generated by tools/thorlaks_o_merge.py. Do not hand-edit.",
                 "# format: p<page> line<NN> <L|R>  <word>  | prev: <word before>",
                 ""]
        for (p, ln, h), (_, w, prev, src) in usable:
            lines.append(f"p{p} line{ln:02d} {h}  {w}" + (f"  | prev: {prev}" if prev else ""))
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwrote {out}  ({len(usable)} usable sites)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
