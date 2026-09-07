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
PREP = Path(r"C:\Projects\Hexapla-releases\research\_prep")

# A sheet covers 4 line crops, so a page's sheet count is derivable from the
# prep kit. ⛔ Without a real denominator this report could only print the
# min-max of the sheets it HAS, and «8 sheet(s) 0-10» reads as complete while
# three sheets are missing from the middle — the same «a contiguous range is
# not evidence of completeness» trap that hid 122 verses in an appendix.
LINES_PER_SHEET = 4


def expected_sheets(chunk, page):
    """-> int, or None if it cannot be derived. NEVER a plausible guess."""
    d = PREP / chunk / f"p{page}"
    if not d.is_dir():
        return None
    n = len(list(d.glob("line*.png")))
    if not n:
        return None
    return -(-n // LINES_PER_SHEET)      # ceil


def crop_widths(chunk):
    """page -> line-crop width. Pure geometry, no model tokens.

    ⛔ SHEET COMPLETENESS IS NOT VALIDITY. Matthew p12 had all 14 of its
    sheets read and every one of those reads was worthless, because the prep
    captured only the left 58 % of the page. Without this check the coverage
    report prints «✅ complete» over exactly that.
    """
    try:
        from PIL import Image
    except ImportError:
        return {}
    root = PREP / chunk
    if not root.is_dir():
        return {}
    out = {}
    for d in root.iterdir():
        if not (d.is_dir() and d.name.startswith("p")):
            continue
        pngs = sorted(d.glob("line*.png"))
        if not pngs:
            continue
        try:
            with Image.open(pngs[0]) as im:
                out[int(d.name[1:])] = im.size[0]
        except Exception:
            continue
    return out

# «p16 line19 L  Kicrøllð  | prev: z  -- …»
REC = re.compile(r'^p(\d+)\s+line(\d+)\s+([LR])\s+(.*?)\s*(?:\|\s*prev:\s*(.*?))?\s*$')
# «# p16 sheet04 (lines16-19): …»
SHEET_HDR = re.compile(r'^#\s*p(\d+)\s+sheet(\d+)')
# ⛔⛔ 2026-09-07: COVERAGE MUST NOT BE DERIVED FROM A PROSE HEADER.
# `o_retrofit_p17b-p18a` adjudicated p18 lines 12-15 in full — two ø entries
# and per-line notes for all four — but wrote them under «# p18 line12: …»
# notes instead of a «# p18 sheet03 …» header. This tool counted headers only,
# so it reported «p18: 10/11 — missing o03» over work that HAD been done, and
# a session acted on that and called the page unfinished.
# ▶ A line that was adjudicated is EVIDENCE; a comment naming a sheet is a
#   convention. Derive from the evidence and use the header only to cross-check.
# «# p18 line12: L blank/faint …»  — a per-line note is also proof of a read.
LINE_NOTE = re.compile(r'^#\s*p(\d+)\s+line(\d+)')


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
    hdr_sheets = defaultdict(set)     # page -> {sheet numbers a HEADER claims}
    crop_lines = defaultdict(set)     # page -> {line numbers actually adjudicated}
    per_file = []

    for f in files:
        m = method_of(f)
        n = 0
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            hs = SHEET_HDR.match(line)
            if hs and m == "CROP":
                hdr_sheets[int(hs.group(1))].add(int(hs.group(2)))
                continue
            hl = LINE_NOTE.match(line)
            if hl and m == "CROP":
                crop_lines[int(hl.group(1))].add(int(hl.group(2)))
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
            if m == "CROP":
                crop_lines[page].add(ln)
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

    # ── coverage, derived from the LINES actually adjudicated ──────────────
    # A sheet counts as read when every line crop it covers is attested — by a
    # ø entry or by a per-line note recording that the line was examined and
    # carried nothing. ⛔ Not by a header comment; see the LINE_NOTE note above.
    # ⚠⚠ THE RULE IS A UNION, AND THE FIRST ATTEMPT AT THIS GOT IT WRONG.
    # Requiring EVERY line of a sheet to be attested looks rigorous and is
    # false: an adjudicator writes a per-line note only where there is
    # something to say, so a sheet read clean leaves few notes. That version
    # reported p18 as 1/11 — worse than the bug it replaced.
    # ▶ Both a header and an attested line are EVIDENCE OF A READ. Neither is
    #   complete on its own, so take the union and say which is which.
    line_sheets = defaultdict(set)
    for p, lns in crop_lines.items():
        for ln in lns:
            line_sheets[p].add(ln // LINES_PER_SHEET)

    crop_pages = defaultdict(set)
    for p in set(hdr_sheets) | set(line_sheets):
        crop_pages[p] = hdr_sheets.get(p, set()) | line_sheets.get(p, set())

    for p in sorted(crop_pages):
        only_lines = line_sheets.get(p, set()) - hdr_sheets.get(p, set())
        if only_lines:
            print(f"\n⚠ p{p}: sheet(s) {sorted(only_lines)} are attested by "
                  f"line-level records with no «# p{p} sheetNN» header. "
                  f"Counted as READ — the work is there. This is exactly what "
                  f"made this tool report p18 o03 missing on 2026-09-07 when "
                  f"it had in fact been adjudicated.")

    print(f"\n▶ PAGES RE-ADJUDICATED BY THE CROP METHOD")
    if not crop_pages:
        print("   (none)")
    widths = crop_widths(a.chunk)
    med_w = None
    if widths:
        import statistics
        med_w = statistics.median(widths.values())

    incomplete, truncated = [], []
    for p in sorted(crop_pages):
        sheets = sorted(crop_pages[p])
        exp = expected_sheets(a.chunk, p)
        if med_w and p in widths and widths[p] < 0.80 * med_w:
            truncated.append(p)
            print(f"   p{p}: {len(sheets)} sheet(s) read  ⛔⛔ PREP TRUNCATED "
                  f"({widths[p]} px vs {med_w:.0f} px median) — EVERY ø read "
                  f"on this page is INVALID regardless of sheet coverage")
            continue
        if exp is None:
            print(f"   p{p}: {len(sheets)} sheet(s) present  "
                  f"⛔ CANNOT DERIVE THE DENOMINATOR (no prep dir) — "
                  f"completeness UNKNOWN, not assumed")
            incomplete.append(p)
            continue
        missing = [s for s in range(exp) if s not in crop_pages[p]]
        extra = [s for s in sheets if s >= exp]
        if missing:
            incomplete.append(p)
            print(f"   p{p}: {len(sheets)}/{exp} sheet(s)  "
                  f"⛔ INCOMPLETE — missing "
                  f"{', '.join(f'o{s:02d}' for s in missing)}")
        else:
            print(f"   p{p}: {len(sheets)}/{exp} sheet(s)  ✅ complete")
        if extra:
            print(f"        ⚠ sheet(s) beyond the expected count: "
                  f"{', '.join(f'o{s:02d}' for s in extra)} — check the "
                  f"line/sheet mapping")
    if truncated:
        print(f"\n   ⛔⛔ {len(truncated)} page(s) READ FROM TRUNCATED PREP: "
              f"{', '.join('p%d' % p for p in truncated)}")
        print("      Re-prep at full width and DISCARD every ø record for "
              "them; sheet completeness says nothing about validity here.")
    if incomplete:
        print(f"\n   ⛔ {len(incomplete)} page(s) have PARTIAL crop coverage: "
              f"{', '.join('p%d' % p for p in incomplete)}")
        print("      A partial page is not a low ø rate — the unread sheets "
              "are unmeasured, exactly like a page with no data at all.")
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
