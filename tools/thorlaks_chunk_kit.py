# -*- coding: utf-8 -*-
"""Build a COMPLETE, deterministic reading kit for one Þorláksbiblía book. 0 model tokens.

    python tools/thorlaks_chunk_kit.py --book Colossians --vol 3 --pages 184-190
    python tools/thorlaks_chunk_kit.py --book Colossians --vol 3 --pages 184-190 --chunk colossians_v3

## Why

A chunk agent's tokens should go to READING LINES and WRITING VERSES. Measured
across six books, they went instead to: re-rendering pages (fixed by
prep_chunk), reading 46 crops per page (fixed by thorlaks_linesheet), hunting
the right prep dir (`_v2` vs `_v3`), re-deriving glyph conventions (six chunks,
six `ꝑ` rates), and typing the verse grid by hand (the corpus audit exists
because a report once claimed 572 verses over two on disk).

This runs the whole model-free chain and hands the agent ONE file:

    research/_prep/<chunk>/READ_ME_FIRST.md
      1. the conventions, pasted from research/THORLAKS_CONVENTIONS.md
         (⛔ refuses to build while any convention there is OPEN)
      2. the ordered list of sheets to read, one read each
      3. the coverage report — every strip of ink no crop covers
      4. the KJV verse grid per chapter, so the report is a fill-in
      5. the report skeleton, chapter by chapter, verse numerals pre-typed

Existing tools are called, never re-implemented: prep_chunk.py (skipped when
the chunk dir exists), thorlaks_prep_coverage.py, thorlaks_linesheet.py.

## What it does NOT do

It does not read anything. It does not choose the pages — the folio formula
and the book index live in research/THORLAKS_CAMPAIGN.md; confirm the first
page's printed folio and content before transcribing (the brief's step 1).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
DATA = Path("C:/Projects/Hexapla-releases")
PREP = DATA / "research" / "_prep"
CONV = DATA / "research" / "THORLAKS_CONVENTIONS.md"
KJV = HERE.parent / "app" / "src" / "main" / "assets" / "bibles" / "en_kjv.json"
PY = sys.executable


def run(args, label):
    print(f"  > {label}: {' '.join(str(a) for a in args[1:])[:110]}", flush=True)
    r = subprocess.run([PY] + [str(a) for a in args[1:]], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stdout or "")[-800:]); print((r.stderr or "")[-800:], file=sys.stderr)
        sys.exit(f"{label} failed (exit {r.returncode})")
    return r.stdout or ""


def parse_pages(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", required=True, help="KJV book name, e.g. Colossians")
    ap.add_argument("--vol", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--pages", required=True, help="PDF idx range, e.g. 184-190")
    ap.add_argument("--chunk", help="prep dir name (default <book>_kit)")
    ap.add_argument("--per", type=int, default=23, help="lines per sheet")
    a = ap.parse_args()

    # 1. conventions — refuse while anything is OPEN
    conv = CONV.read_text(encoding="utf-8")
    open_items = [ln for ln in conv.splitlines() if "| OPEN |" in ln]
    if open_items:
        sys.exit("⛔ THORLAKS_CONVENTIONS.md has an OPEN decision — the owner settles it "
                 "there first, or this book invents its own rule like the last six:\n  "
                 + "\n  ".join(ln[:120] for ln in open_items))

    # 2. KJV grid — book names from the asset itself (no narrate import: the
    #    system python has no soundfile, and this tool must run anywhere)
    kjv = json.loads(KJV.read_text(encoding="utf-8"))
    kjv = kjv["books"] if isinstance(kjv, dict) else kjv
    names = [str(b.get("name", "")).lower() for b in kjv]
    if a.book.lower() not in names:
        sys.exit(f"unknown book {a.book!r}; asset names: {', '.join(n for n in names if n)}")
    bi = names.index(a.book.lower())
    grid = [sum(1 for v in ch if v and v.strip()) for ch in kjv[bi]["chapters"]]

    chunk = a.chunk or f"{a.book.lower().replace(' ', '')}_kit"
    cdir = PREP / chunk
    pages = parse_pages(a.pages)

    # 3. prep (skip if present), coverage, sheets
    if not cdir.exists():
        run([PY, HERE / "prep_chunk.py", "--vol", a.vol, "--pages", a.pages, "--out", chunk],
            "prep_chunk")
    else:
        print(f"  prep dir exists: {cdir} (not re-cut)")
    coverage = run([PY, HERE / "thorlaks_prep_coverage.py", "--chunk", chunk], "coverage")
    sheets_dir = DATA / "_work" / "sheets" / chunk
    sheets_dir.mkdir(parents=True, exist_ok=True)
    sheets = []
    for p in pages:
        pdir = cdir / f"p{p}"
        if not pdir.exists():
            print(f"  ⚠ no prep dir for page {p}: {pdir}")
            continue
        run([PY, HERE / "thorlaks_linesheet.py", "--dir", pdir, "--per", a.per,
             "--out", sheets_dir], f"linesheet p{p}")
        sheets += sorted(sheets_dir.glob(f"p{p}_sheet*.png"),
                         key=lambda f: int(re.search(r"sheet(\d+)", f.name).group(1)))

    # 4. READ_ME_FIRST.md
    out = cdir / "READ_ME_FIRST.md"
    L = [f"# {a.book} — reading kit (vol {a.vol}, idx {a.pages}, chunk `{chunk}`)", "",
         "Built by `tools/thorlaks_chunk_kit.py`. **Pixels only; nothing here was read by a machine.**",
         "Read the sheets IN ORDER, one read each. Do not re-render pages. Do not open",
         "`lineNN.png` except for a disputed letter (half-width crop at native 8.3x —",
         "the sheets are ~6.3x and the ø stroke is not reliable there).", "",
         "## 1. Conventions (pasted from THORLAKS_CONVENTIONS.md — not negotiable per chunk)", "",
         conv.split("\n", 1)[1].strip(), "",
         f"## 2. Sheets to read — {len(sheets)} reads for {len(pages)} pages", ""]
    L += [f"{i + 1}. `{s}`" for i, s in enumerate(sheets)]
    L += ["", "Before the first sheet of each page, glance at that page's `page.png`",
          "ONCE for headings, «Cap. N» marginalia and where the text block starts.", "",
          "## 3. Coverage — ink that NO crop covers (read these off page.png)", "",
          "```", coverage.strip()[-3000:], "```", "",
          f"## 4. KJV verse grid — {a.book}, {len(grid)} chapters, {sum(grid)} verses", "",
          "| chapter | KJV verses | printed (fill in) | divergence |", "|---|---|---|---|"]
    L += [f"| {i + 1} | {n} |  |  |" for i, n in enumerate(grid)]
    L += ["", "⚠ The grid is a CHECKSUM, never an authority: transcribe what is printed,",
          "record every divergence (merged verse, printer's numeral error, unnumbered",
          "verse under the next heading), correct nothing toward the KJV.", "",
          "## 5. Report skeleton — copy into research/thorlaks_<book>.md", "",
          f"# Þorláksbiblía 1644 — {a.book.upper()} (chunk report)", "",
          "**STATUS: IN PROGRESS — 0/%d chapters.** Resume: chapter 1." % len(grid), "",
          f"Source: `research/thorlaks_v{a.vol}.pdf`, idx {a.pages}. Read from the",
          f"sheets under `_work/sheets/{chunk}/` (built from `research/_prep/{chunk}/`).",
          "**The PDF text layer was never consulted.**", "",
          "## Pages actually read", "", "| PDF idx | printed folio | side | content |", "|---|---|---|---|"]
    L += [f"| {p} |  |  |  |" for p in pages]
    L += ["", "## Marginal «Cap. N» sightings", "", "(idx, position, numeral)", ""]
    # ⛔⛔ THE HEADING MUST BE `## <Book> <N>` AND NOTHING ELSE.
    # This skeleton used to emit «## Chapter N — KJV NN verses». A chunk agent
    # copied it (correctly — it is the skeleton it was told to fill in) while a
    # sibling followed the campaign format, so Matthew came back in two
    # incompatible shapes and one half had to be reparsed by hand, 2026-09-06.
    # ▶ The KJV verse count is a fill-in AID, not part of the heading: it now
    # sits on its own comment line, where it helps the transcriber and cannot be
    # mistaken for the heading itself. Anything after the number in an `## `
    # line breaks `thorlaks_corpus_audit.py` and `thorlaks_merge_parts.py`.
    for c, n in enumerate(grid, 1):
        L += [f"## {a.book} {c}", f"<!-- KJV has {n} verses -->", ""]
        L += [f"{v} " for v in range(1, n + 1)]
        L += [""]
    L += ["## Divergences from the KJV grid", "", "## Open sites (letters needing a half-width re-read)", ""]
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"\n✅ kit ready: {out}")
    print(f"   {len(sheets)} sheet reads, {sum(grid)} verses in {len(grid)} chapters")
    print("▶ after the book: python tools/thorlaks_corpus_audit.py && "
          "python tools/thorlaks_variants.py   (both 0 tokens; run BEFORE calling it done)")


if __name__ == "__main__":
    main()
