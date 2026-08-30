# -*- coding: utf-8 -*-
"""Load the transcribed Karl XII 1703 apocrypha into sv_karlxii.json.

    python tools/build_apocrypha_sv.py                 # DRY RUN (the default)
    python tools/build_apocrypha_sv.py --write         # actually modify the asset
    python tools/build_apocrypha_sv.py --book Sirach   # one book, verbose

Reads the chunk reports in `C:/Projects/Hexapla-releases/research/karlxii_*.md`
— the same files, parsed by the same rules, as `karlxii_apoc_corpus_audit.py` —
and fills grid slots 66-82 of the app asset. Canonical books 0-65 are NEVER
touched, and the script proves that rather than promising it.

## ⚠⚠ THIS EMITS THE PRINT'S NATIVE VERSIFICATION, NOT THE KJV GRID

That is a deliberate choice and it needs to be a conscious one, because
`CLAUDE.md` and the audit's own docstring both say the apocrypha would be
"integrated the same way" as `fix_sv_karlxii.py` did the canon — re-flowed into
the KJV grid with curated splits.

▶ WHY NATIVE, MEASURED (2026-08-30) — four translations already ship apocrypha
that does NOT conform to the grid, so the grid is not a precondition:

    asset             chapters LONGER than grid   SHORTER
    la_vulgata                 77                   13
    enm_wycliffe               81                   13
    ru_synodal                 50                   10
    lv_gluck                   19                   20

  and the reader tolerates it by construction: `ReaderScreen.kt` pads a short
  parallel column with `secondaryAligned.getOrNull(i) ?: ""` and skips/greys
  empty books, so a mismatched verse count degrades to a blank cell.

▶ WHAT IT COSTS: in the 94 chapters that diverge from the grid, the parallel
column will not line up with the other translations — exactly as Vulgate and
Wycliffe already do not. Grid mapping remains desirable LATER work; only 9
chapters (all Sirach) currently carry a derived map, so doing it now would
block shipping on ~85 undone derivations.

⛔ Do NOT "fix" a divergence by editing a research .md toward the grid. The
research files are the transcription record; this script is the only thing that
reshapes anything, and it reshapes nothing but numbering offsets declared below.

## VERSE PLACEMENT

A verse printed «12.» goes to index 11, so the app displays the PRINT's own
numeral. 144 of the corpus's 147 chapters number from 1 with no gaps and no
duplicates, so this is the whole story for almost everything.

RENUMBER holds the only exception where the print's numbering is a declared
constant offset from the grid. Two further chapters are left positional ON
PURPOSE and are listed in KNOWN_HOLES below — read that before "fixing" them.

## ⚠ ORTHOGRAPHY — THE ASSET BECOMES TWO-REGISTER, AND THAT IS NOT THIS SCRIPT'S
## CALL TO MAKE

The shipped canon of `sv_karlxii.json` is the CrossWire SweKarlXII **1873**
text: modernised spelling, commas, zero `/` characters in all 66 books
("I begynnelsen skapade Gud Himmel och Jord"). Our apocrypha is transcribed
from the **1703** print: «hafwer», «oß», «wij», «thet», `/` for comma.

So after this runs, Genesis reads 1873 Swedish and Tobit reads 1703 Swedish.
That is a real editorial inconsistency and the owner should see it. This script
does the ONE typographic normalisation that is not a textual change — the
print's `/` is its comma glyph, so it is rendered as a comma — and otherwise
ships the words exactly as transcribed. ⛔ It does NOT modernise spelling, and
nothing here ever should: that would be rewriting the source.
Use --keep-slash to see the untouched form.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
BIBLES = Path(__file__).resolve().parent.parent / "app/src/main/assets/bibles"
SV = BIBLES / "sv_karlxii.json"
BACKUPS = Path(r"C:/Projects/Hexapla-releases/asset-backups")
KJV = BIBLES / "en_kjv.json"

APOC = range(66, 83)
EXCLUDE = ("campaign", "precampaign", "scanhunt", "report", "prompts",
           "navigation")

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+(\S.*)$")

# (book, chapter) -> offset, where index = numeral - 1 - offset.
# An entry belongs here ONLY when the print DECLARES the offset on the page.
RENUMBER = {
    # «Asarie Böön» sub-title: «Efter Daniels 3 cap. 23 v.» — the print sets the
    # Vulgate's Daniel 3 numbering, so its 24-91 is the grid's 1-68 exactly.
    ("Prayer of Azariah", 1): 23,
}

# Chapters deliberately left positional even though it leaves empty slots.
# Listed so the holes are recognised as intended, not as a converter bug.
KNOWN_HOLES = {
    ("Additions to Esther", 10):
        "print numbers this piece 4-13, which IS the KJV numbering, so indices "
        "0-2 stay empty exactly as en_kjv's own ch10 placeholder slots do",
    ("Additions to Esther", 15):
        "print numbers 4-20 (Vulgate) and SKIPS the numeral 14 (verified by "
        "zoom on p741_L5 - a numbering skip, no lost text). A full derived "
        "grid map exists in karlxii_esther_additions.md 'Notes on ch15' "
        "(print 15 merges KJV 15:11+12; print 20 is KJV 11:1). It is NOT "
        "applied here because this build is native-numbering; apply it when "
        "the corpus is grid-mapped.",
}


def die(msg):
    raise SystemExit("FATAL: " + msg)


def chunk_files():
    out = []
    for p in sorted(glob.glob(str(RESEARCH / "karlxii_*.md"))):
        b = os.path.basename(p).lower()
        if b.endswith(".bak") or any(x in b for x in EXCLUDE):
            continue
        out.append(p)
    if not out:
        die("no chunk reports found under %s" % RESEARCH)
    return out


def parse_chunks(names):
    """-> {(bookname, chapter): {numeral: text}}. Raises on a duplicate."""
    data, src = {}, {}
    for path in chunk_files():
        key = None
        for lineno, line in enumerate(
                Path(path).read_text(encoding="utf-8").splitlines(), 1):
            m = CHAPTER_RE.match(line)
            if m:
                book, ch = m.group(1).strip(), int(m.group(2))
                key = (book, ch) if book in names else None
                if key is not None:
                    data.setdefault(key, {})
                    src[key] = os.path.basename(path)
                continue
            if line.startswith("#"):
                key = None
                continue
            if key is None:
                continue
            v = VERSE_RE.match(line)
            if v:
                n = int(v.group(1))
                if n in data[key]:
                    die("duplicate verse numeral %d in %s %d (%s:%d)"
                        % (n, key[0], key[1], os.path.basename(path), lineno))
                data[key][n] = v.group(2).strip()
    if not data:
        die("parsed 0 chapters - the chunk format or the book names changed")
    return data, src


DOUBLED_INITIAL = re.compile(r"^([A-ZÄÅÖ])([A-ZÄÅÖ])(?=[a-zäåöß])")


def fold_initial(text):
    """«OCh» -> «Och». ⛔⛔ OFF BY DEFAULT, AND IT SHOULD STAY OFF.

    ⚠ THE DOUBLED CAPITAL IS NOT A TRANSCRIPTION ARTEFACT — IT IS WHAT THE PAGE
    SETS. This fount opens a decorated initial with the ornament AND a second
    capital letter: p742_L5 is ornament-E then a capital N («EN man war i
    Babylon»), p744_R4 is ornament-T then a capital H («THer war ock en stoor
    drake»). That is brief §F1, observed directly on the strips, 479 times in
    this corpus. Folding it DELETES a real feature of the print.

    This function exists only so the owner can choose otherwise; nothing should
    turn it on by default, and a future session must not "tidy" these away.
    ⛔ And it NEVER folds the divine name regardless: the corpus sets
    «HErre/HErran/HErrans» 31 times at a verse head and that small-capital form
    carries meaning (it is the LORD), not ornament."""
    w = text.split(" ", 1)[0]
    if w.upper().startswith("HERR"):
        return text
    return DOUBLED_INITIAL.sub(lambda m: m.group(1) + m.group(2).lower(), text, count=1)


def clean(text, keep_slash=False, keep_markers=False, fold=False):
    if not keep_markers:
        text = re.sub(r"\s*\*", "", text)          # apparatus asterisk
        text = re.sub(r"\s*\([a-z]\)", "", text)   # lettered apparatus marker
    if not keep_slash:
        text = text.replace("/", ",")
    if fold:
        text = fold_initial(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,;:.?!])", r"\1", text)
    text = re.sub(r",{2,}", ",", text)
    return text.strip()


def build(data, names, grid, keep_slash, keep_markers, fold):
    """-> {book index: [[verse,...], ...]} plus a per-chapter report."""
    out, report = {}, []
    for (book, ch), verses in sorted(data.items()):
        bi = names[book]
        if bi not in APOC:
            die("%s is book index %d, outside the apocrypha slots" % (book, bi))
        off = RENUMBER.get((book, ch), 0)
        placed = {}
        for n, txt in verses.items():
            idx = n - 1 - off
            if idx < 0:
                die("%s %d verse %d renumbers to a negative index (offset %d)"
                    % (book, ch, n, off))
            placed[idx] = clean(txt, keep_slash, keep_markers, fold)
        size = max(placed) + 1
        chapter = [placed.get(i, "") for i in range(size)]
        holes = sum(1 for v in chapter if not v)
        nch = len(grid[book])
        out.setdefault(bi, [[] for _ in range(nch)])
        if ch - 1 >= nch:
            die("%s ch%d lies beyond the grid's %d chapters" % (book, ch, nch))
        out[bi][ch - 1] = chapter
        report.append((book, ch, len(verses), size, holes,
                       grid[book][ch - 1] if ch - 1 < len(grid[book]) else 0,
                       off))
    return out, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="apply the change (default is a dry run)")
    ap.add_argument("--book", help="show every chapter of one book")
    ap.add_argument("--keep-slash", action="store_true",
                    help="leave the print's / instead of rendering it a comma")
    ap.add_argument("--keep-markers", action="store_true",
                    help="leave the inline * and (a) apparatus markers")
    ap.add_argument("--fold-initials", action="store_true",
                    help="OCh -> Och; folds the decorated-initial doubled "
                         "capital (never the HErr- divine name)")
    args = ap.parse_args()

    kjv = json.loads(KJV.read_text(encoding="utf-8"))
    names = {b["name"]: i for i, b in enumerate(kjv)}
    grid = {b["name"]: [len(c) for c in b["chapters"]] for b in kjv}

    data, src = parse_chunks(names)
    built, report = build(data, names, grid, args.keep_slash,
                          args.keep_markers, args.fold_initials)

    sv = json.loads(SV.read_text(encoding="utf-8"))
    if len(sv) != len(kjv):
        die("sv_karlxii has %d books, en_kjv has %d" % (len(sv), len(kjv)))

    print("%-22s %5s %6s %6s %6s %6s %s"
          % ("book", "chs", "verses", "slots", "holes", "grid", "note"))
    print("-" * 78)
    per = {}
    for book, ch, nv, size, holes, g, off in report:
        per.setdefault(book, [0, 0, 0])
        per[book][0] += 1
        per[book][1] += nv
        per[book][2] += holes
    total_v = total_h = 0
    for book in sorted(per):
        chs, nv, holes = per[book]
        gv = sum(grid[book])
        note = ""
        if any((book, c) in RENUMBER for c in range(1, 60)):
            note = "renumbered"
        if any((book, c) in KNOWN_HOLES for c in range(1, 60)):
            note = (note + " known-holes").strip()
        print("%-22s %5d %6d %6s %6d %6d %s"
              % (book, chs, nv, "-", holes, gv, note))
        total_v += nv
        total_h += holes
    print("-" * 78)
    print("%-22s %5s %6d %6s %6d" % ("TOTAL", "", total_v, "-", total_h))

    if args.book:
        print("\nper-chapter for %s:" % args.book)
        for book, ch, nv, size, holes, g, off in report:
            if book == args.book:
                print("   ch%-3d verses=%-4d slots=%-4d holes=%-3d grid=%-4d "
                      "offset=%d" % (ch, nv, size, holes, g, off))

    if total_h:
        print("\nEMPTY SLOTS (%d) - each must be a KNOWN_HOLES entry:" % total_h)
        for book, ch, nv, size, holes, g, off in report:
            if holes:
                k = (book, ch)
                tag = "OK - documented" if k in KNOWN_HOLES else "*** UNEXPECTED ***"
                print("   %s %d: %d empty of %d slots  [%s]"
                      % (book, ch, holes, size, tag))
                if k not in KNOWN_HOLES:
                    die("undocumented empty verse slots in %s %d" % (book, ch))

    print("\nsample of the text transform (slash->comma=%s, markers=%s):"
          % (not args.keep_slash, "kept" if args.keep_markers else "stripped"))
    for probe in (("Susanna", 1, 9), ("Bel and the Dragon", 1, 4),
                  ("Sirach", 18, 1)):
        b, c, n = probe
        raw = data.get((b, c), {}).get(n)
        if raw:
            print("   %s %d:%d" % (b, c, n))
            print("     raw : %s" % raw[:96])
            print("     out : %s" % clean(raw, args.keep_slash,
                                          args.keep_markers,
                                          args.fold_initials)[:96])

    if not args.write:
        print("\nDRY RUN - nothing written. Re-run with --write to apply.")
        return 0

    # ⚠⚠ THE BACKUP MUST NOT LIVE UNDER app/src/main/assets/ — EVERYTHING THERE
    # IS PACKAGED. A first version of this script wrote the backup beside the
    # asset and shipped a 1.56 MB compressed duplicate of the whole Swedish
    # Bible inside the APK. The build was green and the asset was correct; only
    # listing the APK's own entries caught it. Backups go to the sibling
    # working directory, matching asset-backups/cu_elizabeth.json.preapocrypha.bak
    if BACKUPS.is_dir():
        backup = BACKUPS / (SV.name + ".preapocrypha.bak")
    else:
        backup = SV.parent.parent.parent.parent.parent / (SV.name + ".preapocrypha.bak")
        print("⚠ %s missing; backup goes to %s" % (BACKUPS, backup))
    if backup.resolve().is_relative_to(SV.parent.parent.resolve()):
        die("refusing to write a backup inside the packaged assets tree: %s"
            % backup)
    if not backup.exists():
        shutil.copy2(SV, backup)
        print("\nbackup -> %s" % backup)
    else:
        print("\nbackup already exists, kept: %s" % backup)

    canon_before = json.dumps([sv[i] for i in range(66)], ensure_ascii=False)
    for bi, chapters in built.items():
        sv[bi]["chapters"] = chapters
    canon_after = json.dumps([sv[i] for i in range(66)], ensure_ascii=False)
    if canon_before != canon_after:
        die("canonical books 0-65 changed - refusing to write")

    SV.write_text(json.dumps(sv, ensure_ascii=False), encoding="utf-8")

    # Re-read from disk and prove the write, rather than trusting it.
    check = json.loads(SV.read_text(encoding="utf-8"))
    got = 0
    for bi in APOC:
        for c in check[bi]["chapters"]:
            got += sum(1 for v in c if v)
    if got != total_v:
        die("wrote %d verses but the file holds %d" % (total_v, got))
    if json.dumps([check[i] for i in range(66)], ensure_ascii=False) != canon_before:
        die("canonical books differ on re-read")
    print("VERIFIED ON RE-READ: %d apocrypha verses in %s, canon unchanged."
          % (got, SV.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
