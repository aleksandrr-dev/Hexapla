# -*- coding: utf-8 -*-
"""Fold the SETTLED sorts out of a crop-read chunk, so no reader ever sees them.

    python tools/thorlaks_normalize_chunk.py --book Luke --page p64            # DRY RUN
    python tools/thorlaks_normalize_chunk.py --book Luke --page p64 --apply
    python tools/thorlaks_normalize_chunk.py --selftest

## WHY THIS EXISTS

`thorlaks_chunk_check.py` refuses a read that carries a forbidden sort, and it
is right to: the conventions SETTLE those sorts, so a chunk carrying one has
not been written to the convention. But the remedy it names - "this is a
re-read, not an edit" - is wrong for this class, and that wrongness is
expensive. Measured 2026-09-19 on Luke idx 64:

    read B: 15 HARD findings. 14 of them are `N x U+017F long-s` on a line.

⛔ A reader that wrote `ſ` DID NOT MISREAD THE GLYPH. It identified the long-s
correctly and then wrote it in the sort the conventions forbid. There is
nothing on the page left to look at. Re-reading idx 64 to turn `ſ` into `s`
buys a different wrong answer at full price - and row 55 of the conventions
already rules the opposite way:

    "Build the kit from the diff itself, normalising away first everything the
     conventions already settle (long-s, the oe/ae sort, the virgule's
     spacing, [HN] bracketing, the nasal bar) so that nothing which is merely
     spelling ever reaches a reader."

▶ This tool is that normalisation, applied one stage earlier: at the chunk,
before the stitch, so the gate sees a convention-clean read.

## ⛔⛔ THE GUARD THAT MATTERS - ø IS NOT A FORMATTING SORT

`ſ -> s` is lossless: the convention says long-s IS written plain `s`, so the
mapping throws away nothing that any downstream tool wants.

**`ø -> o` IS NOT LOSSLESS AND IS CATASTROPHIC IN THE WRONG BOOK.** In Mark,
Matthew and the rest of the campaign the stroke is REAL DATA - it carries a ø
rate, a retrofit, and per-site records, and a script that quietly folded it
away would destroy the campaign's most expensive evidence with no trace.

It is admissible in Luke ONLY because the owner ruled (convention row 48, in
every brief as convention 2) that **Luke gets NO ø rate and every o stands
plain**. So:

  * `--strip-o-marks` is REQUIRED before any ø/ö is touched, and
  * it is REFUSED for any book not in `NO_O_RATE`, by name, with a non-zero
    exit. ⛔ Do not add a book to that set to get a run through: the owner
    rules a book's ø status, not this file.

## WHAT IT WILL NOT TOUCH

  * `## NOTES` and `## HN` - a reader DISCUSSING a sort must be able to name
    it. Folding the apparatus would erase the reader's own reasoning about the
    very glyph in question.
  * Anything but the sorts listed in `SETTLED`. It is not a spelling pass.
  * The file, without `--apply`. Default is a dry run that prints every change.

Every changed line is printed as a before/after pair, and `--apply` writes a
`.pre_normalize` backup next to each file it rewrites.

## CONTROLS

  `--selftest`                     fixtures, both directions
  `HEXAPLA_NO_NORMALIZE=1`         known-bad: maps nothing, so the gate still
                                   refuses the chunk and the difference is
                                   visible rather than assumed
"""
import argparse
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

DATA = r"C:\Projects\Hexapla-releases"

# ⚠ Books the OWNER has ruled carry no ø rate. Luke: convention row 48.
# ⛔ This is a record of a ruling, not a switch to flip.
NO_O_RATE = {"luke"}

# The sorts the conventions settle, and what they settle to.
LONG_S = {u"\u017f": u"s"}                      # ſ  -> s   (always safe)
O_MARKS = {u"\u00f8": u"o", u"\u00d8": u"O",    # ø Ø -> o O (Luke only)
           u"\u00f6": u"o", u"\u00d6": u"O"}    # ö Ö -> o O (Luke only)

ROW_RE = re.compile(r"^\s*line(\d{2})\s*\|")
SEC_RE = re.compile(r"^##\s*(LINES|NUMERALS|HN|NOTES)\b", re.I)
# ⛔ Only these two sections hold returned TEXT. HN and NOTES are apparatus.
TEXT_SECTIONS = ("LINES", "NUMERALS")


def die(msg, code=2):
    print("⛔ %s" % msg)
    sys.exit(code)


def build_map(strip_o):
    m = dict(LONG_S)
    if strip_o:
        m.update(O_MARKS)
    if os.environ.get("HEXAPLA_NO_NORMALIZE"):
        return {}          # known-bad control: change nothing
    return m


def normalize_text(text, mapping):
    """Return (new_text, [(lineno, before, after)]) for TEXT sections only."""
    out, changes, sec = [], [], None
    for raw in text.splitlines():
        m = SEC_RE.match(raw.strip())
        if m:
            sec = m.group(1).upper()
            out.append(raw)
            continue
        if sec in TEXT_SECTIONS and ROW_RE.match(raw):
            new = raw
            for a, b in mapping.items():
                new = new.replace(a, b)
            if new != raw:
                changes.append((int(ROW_RE.match(raw).group(1)), raw, new))
            out.append(new)
        else:
            out.append(raw)
    tail = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + tail, changes


def chunk_files(data, book, page, series):
    lower = book.lower()
    suffix = "CROP_READ_CHUNK" if series.upper() == "A" else "CROP_READB_CHUNK"
    pat = os.path.join(data, "_work", "%s_%s_%s*.md" % (lower, page, suffix))
    return sorted(glob.glob(pat))


def run(data, book, page, series, strip_o, apply_it):
    if strip_o and book.lower() not in NO_O_RATE:
        die("REFUSING --strip-o-marks for %s. The stroke is REAL DATA in every "
            "book the owner has not ruled otherwise - it carries a ø rate, a "
            "retrofit and per-site records. Only %s is ruled to have no ø "
            "rate. ⛔ Do not widen this set to get a run through."
            % (book, ", ".join(sorted(NO_O_RATE))))
    files = chunk_files(data, book, page, series)
    if not files:
        die("no chunk files for %s %s read %s" % (book, page, series))
    mapping = build_map(strip_o)
    if not mapping:
        print("⚠ HEXAPLA_NO_NORMALIZE=1 - mapping is EMPTY, nothing will change")
    print("=" * 68)
    print("NORMALIZE %s %s read %s - %d chunk(s)%s"
          % (book, page, series.upper(), len(files),
             "" if apply_it else "   ⚠ DRY RUN"))
    print("sorts folded: %s"
          % (", ".join("%s->%s" % (a, b) for a, b in sorted(mapping.items()))
             or "(none)"))
    print("=" * 68)
    total = 0
    for f in files:
        with io.open(f, encoding="utf-8") as fh:
            text = fh.read()
        new, changes = normalize_text(text, mapping)
        print("\n%s : %d line(s) changed" % (os.path.basename(f), len(changes)))
        for n, before, after in changes:
            print("  line%02d" % n)
            print("    -  %s" % before.strip())
            print("    +  %s" % after.strip())
        total += len(changes)
        if apply_it and changes:
            bak = f + ".pre_normalize"
            if not os.path.exists(bak):
                with io.open(bak, "w", encoding="utf-8") as fh:
                    fh.write(text)
            with io.open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
    print("\n" + "=" * 68)
    print("TOTAL %d line(s) across %d chunk(s)%s"
          % (total, len(files),
             "" if apply_it else "   ⚠ NOTHING WRITTEN - re-run with --apply"))
    return total


def selftest():
    ok = True

    def case(label, text, mapping, want_changes, want_in=None, want_not_in=None):
        nonlocal ok
        new, ch = normalize_text(text, mapping)
        good = len(ch) == want_changes
        if want_in is not None:
            good = good and want_in in new
        if want_not_in is not None:
            good = good and want_not_in not in new
        print("  %-52s changes=%d want=%d %s"
              % (label, len(ch), want_changes, "ok" if good else "FAIL"))
        ok = good and ok

    s_map = dict(LONG_S)
    o_map = dict(LONG_S); o_map.update(O_MARKS)

    body = (u"## LINES\n"
            u"line05 | 3 \u017fkulu \u017fegia Born\n"
            u"line06 | 4 plain text here\n"
            u"\n## NUMERALS\nline05 | 3 | \u017fkulu\n"
            u"\n## NOTES\n- the long-s \u017f is discussed here on purpose\n")

    case("long-s is folded in LINES", body, s_map, 2, want_in=u"skulu segia")
    case("  ...and in the NUMERALS word column", body, s_map, 2,
         want_in=u"line05 | 3 | skulu")
    case("  ...but NOT in NOTES (a reader may name the sort)",
         body, s_map, 2, want_in=u"the long-s \u017f is discussed")
    case("empty mapping (HEXAPLA_NO_NORMALIZE) changes nothing",
         body, {}, 0, want_in=u"\u017fkulu")

    obody = u"## LINES\nline15 | 25 nockur L\u00f8guitringur sto\u00f0 upp\n"
    case("ø is left ALONE without --strip-o-marks", obody, s_map, 0,
         want_in=u"L\u00f8guitringur")
    case("ø folds WITH it", obody, o_map, 1, want_in=u"Loguitringur")
    case("  ...and eth (\u00f0) is NEVER touched - it is a real letter",
         obody, o_map, 1, want_in=u"sto\u00f0")

    # ⛔ the guard is the point: a ø book must be refused, not normalised
    guarded = [b for b in ("mark", "matthew", "john") if b not in NO_O_RATE]
    good = len(guarded) == 3 and "luke" in NO_O_RATE
    print("  %-52s %s" % ("only Luke is ruled ø-rate-free",
                          "ok" if good else "FAIL"))
    ok = good and ok

    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--page", help="pNN")
    ap.add_argument("--series", default="A", choices=["A", "B", "a", "b"])
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--strip-o-marks", action="store_true",
                    help="also fold ø/ö to o - REFUSED unless the owner has "
                         "ruled the book carries no ø rate")
    ap.add_argument("--apply", action="store_true",
                    help="write the files (default is a dry run)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.book and a.page):
        die("--book and --page are required (or --selftest)")
    run(a.data, a.book, a.page, a.series, a.strip_o_marks, a.apply)


if __name__ == "__main__":
    main()
