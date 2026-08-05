# -*- coding: utf-8 -*-
"""Remove the space the Bakar converter inserted before closing punctuation.

THE DEFECT. 33,439 of 36,849 verses (90.7%) in ka_bakar.json read «სიტყუაჲ ,
და» — a space before the comma. 86,090 sites: 67,654 «,», 10,512 «:», 6,760
«.», 958 «;», 206 «?».

IT IS OURS, NOT THE PRINT'S. In the raw TITUS HTML only 27 of 239,693
punctuation marks are preceded by a space. The cause is one character in
tools/extract_bakar.py:

    txt = TAG_RE.sub(' ', raw_html)

TITUS wraps every WORD in its own <a> element —

    <a id=mxag16 href="javascript:ci(38405,'…')">იესო</a>, <a …>რომელსა</a>

— so «</a>,» becomes « ,». Replacing tags with '' instead would fuse words
across element boundaries, which is why the space is there and must stay; the
squeeze belongs at the end of clean_text, and extract_bakar.py is fixed to do
it so a rebuild cannot reintroduce this.

WHAT IS SQUEEZED, and what deliberately is not. Census of every non-Georgian,
non-word character preceded by a space in the asset:

    ,  67654  squeeze      [   92  KEEP — opening bracket, the LXX-supplied
    :  10512  squeeze                     and variant-passage convention
    .   6760  squeeze      -   69  KEEP — a dash between words is punctuation
    ;    958  squeeze      "   19  KEEP — ambiguous open/close
    ?    206  squeeze      {    3  KEEP — the app's own margin-note markup
    ]     10  squeeze      (    2  KEEP — opening
    ̃      4  squeeze      <    1  KEEP — see the NOTE below
                           '    1  KEEP — ambiguous

«!» never occurs preceded by a space, but is included in the pattern for
completeness. U+0300-U+036F combining marks are squeezed because a combining
mark separated from its base letter renders as a diacritic floating over the
space — it belongs on the preceding letter by definition.

⚠ NOTE, NOT FIXED HERE (needs an editorial decision, reported separately):
Genesis 40:22 carries «მთავარმან პყრობილთ <პყრობილთ> მცველმან» — TITUS's
angle-bracket editorial mark around a repeated word, leaked into the asset.
tools/audit_asset_markup.py reports the whole tree CLEAN because its tag regex
expects an ASCII tag name and this one is Georgian. Both are real; neither is
a spacing defect, so neither is touched by this script.

NO COORDINATE IMPACT. Verse counts do not change, so versemap.json, bookmarks,
notes and highlights are all untouched. rubrics_bak.json stores text only —
no character offsets, unlike rubrics_vul.json — so its 841 rows are squeezed
the same way and nothing has to be re-derived.

THE GATE. Every rewritten string must be identical to the original once ALL
whitespace is removed from both. That proves only whitespace changed: no
letter, no mark and no punctuation can be added, dropped or reordered without
the assertion firing. Backups go OUTSIDE app/src/main/assets (Android bundles
that whole tree into the APK).

Owner approved 2026-08-04.

    python tools/fix_bakar_punct_spacing.py --dry-run
    python tools/fix_bakar_punct_spacing.py
"""
import argparse
import collections
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
BIBLE = ASSETS / "bibles" / "ka_bakar.json"
RUBRICS = ASSETS / "rubrics_bak.json"
BACKUPS = Path("C:/Projects/Hexapla-releases/asset-backups")

# Closing punctuation only. See the docstring for what is deliberately absent.
SQUEEZE = re.compile(r"\s+([,.:;?!\]\u0300-\u036f])")

# Expected sites, from the census. A mismatch means the asset is not the one
# this script was written against — stop rather than "fix" something else.
EXPECTED = {",": 67654, ":": 10512, ".": 6760, ";": 958, "?": 206,
            "]": 10, "\u0303": 4}


def squeeze(s):
    return SQUEEZE.sub(r"\1", s)


def bare(s):
    """The string with every whitespace character removed."""
    return "".join(s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.loads(BIBLE.read_text(encoding="utf-8"))
    rubrics = json.loads(RUBRICS.read_text(encoding="utf-8"))

    found = collections.Counter()       # verse sites — checked against EXPECTED
    found_rub = collections.Counter()   # rubric sites — additional
    changed_verses = 0
    total_verses = 0
    empty_before = 0

    for bk in books:
        for ch in bk.get("chapters", []):
            for i, v in enumerate(ch):
                if not v:
                    empty_before += 1
                    continue
                total_verses += 1
                new = squeeze(v)
                if new == v:
                    continue
                # THE GATE — only whitespace may differ.
                assert bare(new) == bare(v), (bk["name"], i, repr(v[:120]))
                assert new.strip(), ("verse emptied", bk["name"], i)
                for m in SQUEEZE.finditer(v):
                    found[m.group(1)] += 1
                ch[i] = new
                changed_verses += 1

    changed_rubrics = 0
    for row in rubrics:
        t = row.get("text")
        if not t:
            continue
        new = squeeze(t)
        if new == t:
            continue
        assert bare(new) == bare(t), (row, repr(t[:120]))
        for m in SQUEEZE.finditer(t):
            found_rub[m.group(1)] += 1
        row["text"] = new
        changed_rubrics += 1

    print(f"verses: {total_verses} non-empty ({empty_before} empty slots)")
    print(f"changed: {changed_verses} verses "
          f"({100 * changed_verses / total_verses:.1f}%), "
          f"{changed_rubrics} of {len(rubrics)} rubric rows")
    print("sites squeezed (verses | rubrics):")
    for k in sorted(set(found) | set(found_rub) | set(EXPECTED)):
        print(f"   {k!r:12} {found[k]:>6} | {found_rub[k]:<4} "
              f" census expected {EXPECTED.get(k, 0)}")

    # The verse-side census must match EXACTLY. A mismatch means this is not
    # the asset the script was written against — stop rather than rewrite
    # something whose shape nobody has looked at.
    assert dict(found) == EXPECTED, \
        f"verse census mismatch: found {dict(found)}, expected {EXPECTED}"

    # Nothing targeted may survive.
    for bk in books:
        for ch in bk.get("chapters", []):
            for v in ch:
                assert not (v and SQUEEZE.search(v)), repr(v[:120])
    for row in rubrics:
        assert not SQUEEZE.search(row.get("text") or "")
    print("verified: no targeted space-before-punctuation remains")

    if args.dry_run:
        print("\ndry run — nothing written")
        return

    BACKUPS.mkdir(parents=True, exist_ok=True)
    for src, tag in ((BIBLE, "prepunct"), (RUBRICS, "prepunct")):
        dst = BACKUPS / f"{src.name}.{tag}.bak"
        shutil.copy2(src, dst)
        print("backed up ->", dst)

    BIBLE.write_text(json.dumps(books, ensure_ascii=False), encoding="utf-8")
    RUBRICS.write_text(json.dumps(rubrics, ensure_ascii=False),
                       encoding="utf-8")
    print("wrote", BIBLE)
    print("wrote", RUBRICS)


if __name__ == "__main__":
    main()
