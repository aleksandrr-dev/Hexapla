# -*- coding: utf-8 -*-
"""Assemble the Glen Persian OT (1856) from the campaign's chunk reports.

Fills books 0-38 of `assets/bibles/fa_martyn.json`, whose OT slots are empty
(verified: they hold NO chapters at all, so this FILLS rather than overwrites).
The NT (books 39-65, Martyn 1876) is untouched.

    python tools/build_glen_ot.py --dry-run      # report only, write nothing
    python tools/build_glen_ot.py --out fa_glen_martyn.json

## Design decisions, each with its reason

**Verses are addressed by POSITION in the marker run, never by marker value.**
Owner ruling 2026-08-08: defective numerals are recorded AS PRINTED, so the
glyph «۱» can appear at position 9. Keying on the glyph merges verse 9 into
verse 1 — which is exactly what happened in an earlier tool and hid every site
of interest. Position is the addressing; the printed glyph is evidence.

**The print's own verse divisions are kept.** Where the marker count differs
from the KJV, this is NOT silently reconciled — the asset keeps what the print
does and the divergence is reported for versemap curation, the same model used
for Károli, Kralická and Glück. Reconciling here would invent a text.

**A strict state machine that hard-fails.** Every exception is curated
explicitly with its evidence rather than by loosening the parser (campaign
rule, learned across three earlier converters).
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import glen_defect_inventory as inv  # noqa: E402
sys.path.insert(0, str(inv.RESEARCH))
_argv = sys.argv[:]
sys.argv = ["scan_markers"]
import scan_markers as sm  # noqa: E402
sys.argv = _argv

RESEARCH = inv.RESEARCH
ASSET = HERE.parent / "app/src/main/assets/bibles/fa_martyn.json"
KJV = inv.KJV

# ── Normalisation ───────────────────────────────────────────────────────────
# Corpus-wide, deferred to conversion by the campaign brief. Transcribers' IMEs
# emitted Arabic forms; the asset must be uniformly Persian.
YEH_KAF = {0x064A: "ی", 0x0643: "ک"}          # ي→ی  ك→ک
ARABIC_INDIC = {0x0660 + i: chr(0x06F0 + i) for i in range(10)}   # ٠-٩ → ۰-۹
TRANS = {**YEH_KAF, **ARABIC_INDIC}

# The print's own paragraph separator. Standalone it is punctuation and is
# dropped; ATTACHED to a word it is one of three things (spurious-after-name,
# izafa هٔ, lost space) and the campaign deferred that classification — so
# attached instances are counted and reported, never silently altered.
STAR = "٭"

# ── Book names, from the print's OWN فهرست (PDF idx 11-12) ──────────────────
# The empty OT slots in fa_martyn.json carry ENGLISH placeholders ("Genesis"),
# which the app would display verbatim — the v1 de_luther / Vamvas defect
# class. These are the 1856's own names, with the «کتابِ»/«سفرِ» prefix and the
# descriptive tails dropped for picker width, following the shortened-book-name
# pass the owner asked for on the Armenian.
#   full TOC forms, for the record: «سفر تکوین المخلوقات», «کتاب قضاة بنی
#   اسرائیل», «کتاب یوشع بن نون», «کتاب مزامیر معروف بزبور داود»,
#   «کتاب امثال سلیمان», «کتاب واعظ سلیمان».
# Read twice independently — off the TOC page here, and in the campaign brief's
# own table — and the two agree.
BOOK_NAMES = [
    "تکوین", "خروج", "لویان", "اعداد", "توریة مثنی",
    "یوشع", "قضاة", "روث", "اول شموئیل", "دویمین شموئیل",
    "اول ملوک", "دویمین ملوک", "اول تواریخ ایام", "دویمین تواریخ ایام",
    "عزرا", "نحمیاه", "استیر", "ایوب", "مزامیر", "امثال",
    "واعظ", "سرود سلیمان", "اشعیاه", "یرمیاه", "نیاحات یرمیاه",
    "حزقیل", "دانیال", "هوشیع", "یوئیل", "عاموص", "عوبدیاه",
    "یوناه", "میکاه", "ناحوم", "حبقوق", "صفنیاه", "حگّي",
    "زکریاه", "ملاکي",
]
assert len(BOOK_NAMES) == 39


# ── Curated line exclusions ─────────────────────────────────────────────────
# Prose lines that quote a verse marker and slip past the commentary filter
# because they carry little or no Latin. Three of the four quote the NEXT
# BOOK's opening verse in a boundary note — «(۱) اینهایَند امثالِ سُلَیْمانِ»
# is Proverbs 1:1 sitting at the end of Psalms; «(۱) در سالِ اوّلِ سلطنتِ
# کُوٗرِش» is Ezra 1:1 at the end of 2 Chronicles. Each added a phantom verse
# and put its chapter on the versemap-curation list.
# ⚠ Curated explicitly rather than by widening the regex: a rule broad enough
# to catch these also catches real scripture (a Latin-count rule dropped
# Ecclesiastes 9:11, whose verse text ends "...(continues next page)").
# Verified against the print by the versemap pass: all four chapters are clean
# against the KJV grid once these lines are excluded.
DROP_LINES = {
    (18, 150): ["اینهایَند امثالِ"],          # Proverbs 1:1 quoted at book seam
    (13, 36): ["در سالِ اوّلِ سلطنتِ کُوٗرِش"],  # Ezra 1:1 quoted at book seam
    (3, 35): ['"(۹)" line'],                   # prose quoting its own marker
    (6, 14): ["پدرَش برآمد"],                   # verse 20 written twice
}


def normalise(t):
    """⚠⚠ THE ٭ CLASSIFICATION IS STILL OPEN — DO NOT 'SIMPLIFY' THIS.

    An earlier version of this function replaced EVERY ٭ with a space. That
    silently destroyed **841 sites where ٭ follows ه**, and reading them shows
    many are IZAFA, not punctuation:
        «بالاي بِرکه٭ حِبرون»  = "upon the pool OF Hebron"   (برکهٔ حبرون)
        «بقیّه٭ قوم‌را»        = "the rest OF the people"     (بقیّهٔ قوم)
        «از مقابله٭ او»        = "from before him"           (مقابلهٔ او)
    Dropping the mark there turns correct Persian into ungrammatical Persian.

    It cannot be resolved by rule: the corpus ALREADY uses real izafa forms
    (هٔ ×2418, هٴ ×135, ۀ ×119), so ٭ is not simply the transcribers' stand-in
    for a mark they could not type — both appear, and only the PRINT can say
    which is which at a given site.

    Until that classification is done against the page images:
      · a STANDALONE ٭ (whitespace both sides) is the print's paragraph
        separator — dropped, which is safe and uncontested;
      · an ATTACHED ٭ is PRESERVED VERBATIM, so no information is lost and the
        sites remain findable.
    """
    t = t.translate(TRANS)
    t = re.sub(r"(?<=\s)%s(?=\s)|^%s\s|\s%s$" % (STAR, STAR, STAR), " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def verse_runs(path, bidx):
    """{chapter: [verse text, ...]} for one book out of one report file.

    Ordered by POSITION. Chapter headings are recognised through the scanner's
    own patterns so this and scan_markers can never disagree about where a
    chapter starts.
    """
    text = io_read(path)
    base = os.path.basename(path)
    if base in inv.MULTI:
        marks = []
        for idx, pat in inv.MULTI[base]:
            s = 0 if pat is None else re.search(pat, text).start()
            marks.append((s, idx))
        marks.sort()
        for i, (s, idx) in enumerate(marks):
            if idx == bidx:
                e = marks[i + 1][0] if i + 1 < len(marks) else len(text)
                text = text[s:e]
                break
        else:
            return {}
    out, cur, pre = {}, None, {}
    for raw in text.splitlines():
        m = sm.CH_RE.match(raw)
        if not m and raw.startswith("#"):
            m2 = sm.CH_RE_PAREN.match(raw.rstrip())
            if m2:
                cur = int(m2.group(2))
                out.setdefault(cur, [])
                continue
        if m:
            cur = int(m.group(1))
            out.setdefault(cur, [])
            continue
        if cur is None or sm.is_commentary(raw):
            continue
        if any(sig in raw for sig in DROP_LINES.get((bidx, cur), ())):
            continue
        # ⚠ VERSES SPAN LINES. An earlier version captured only the text on the
        # marker's own line, which silently truncated every verse that wrapped
        # and produced ~30 EMPTY verses in Deuteronomy alone. Stream instead:
        # a marker opens a verse, and everything after it — across as many
        # lines as follow — belongs to that verse until the next marker.
        parts = re.split(r"\(([۰-۹٠-٩]+)\)", raw)
        # parts = [before, marker, text, marker, text, ...]
        # ⚠ TEXT BEFORE THE CHAPTER'S FIRST MARKER IS SCRIPTURE, NOT NOISE.
        # An earlier version discarded it when no verse was open yet, which
        # silently DELETED all of Psalms 17:1: this print leaves some first
        # verses unmarked — the psalm title «[دعايِ داۇد]» is followed by verse
        # 1's text and only then by «(۲)». Dropping it lost a whole verse and
        # made the chapter look like a versemap divergence instead of a bug.
        # Open an implicit verse 1 for such text.
        if parts[0].strip():
            if out[cur]:
                out[cur][-1] += " " + parts[0]
            else:
                pre.setdefault(cur, []).append(parts[0])
        for i in range(1, len(parts), 2):
            val = int(parts[i].translate(str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")))
            txt = parts[i + 1] if i + 1 < len(parts) else ""
            # ⚠ FIRST MARKER OF A CHAPTER: what precedes it is NOT always
            # verse 1. Two different things live there and they need opposite
            # treatment:
            #   · a psalm SUPERSCRIPTION («[دعايِ داۇد]»), when the first
            #     marker is «۱» — belongs PREPENDED to verse 1, the same
            #     convention used for the ru/cu/ta psalters. Making it its own
            #     verse invented a spurious verse in ~30 psalms.
            #   · a genuinely UNMARKED verse 1, when the first marker is «۲» —
            #     this print sometimes omits the opening numeral (Psalms 17).
            #     Discarding it deleted real scripture.
            # The first marker's own value discriminates them.
            if not out[cur] and cur in pre:
                lead = " ".join(pre.pop(cur))
                # ⚠ STRIP THE PRINT'S OWN CHAPTER HEADING. The reports quote
                # it inline — «(فصلِ دویم مشتمل بر سی و هفت آیه)» — on the same
                # line as the chapter's opening words. It is not scripture, and
                # retaining it prepended a heading to 208 verse-1 texts.
                lead = re.sub(r"«?\((?:فصل|مزمور)[^)]*آیه\)\s*", "", lead)
                if not lead.strip():
                    pass
                elif val == 1:
                    txt = lead + " " + txt
                else:
                    out[cur].append(lead)
            out[cur].append(txt)
    return {c: v for c, v in out.items() if v}


def io_read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    kjv = json.load(open(KJV, encoding="utf-8"))
    counts = [[len(c) for c in b["chapters"]] for b in kjv]
    names = [b["name"] for b in kjv]

    # ── gather, preferring the copy that matches the reference ──────────────
    best = {}
    for path in sorted(RESEARCH.glob("glen_*.md")):
        if ".bak" in path.name or any(x in path.name for x in inv.EXCLUDE):
            continue
        for bidx, _ in inv.sections(str(path), None):
            if bidx is None:
                continue
            for c, vs in verse_runs(str(path), bidx).items():
                exp = counts[bidx][c - 1] if c - 1 < len(counts[bidx]) else None
                prev = best.get((bidx, c))
                if prev is None or (len(vs) == exp and len(prev[0]) != exp) \
                        or (len(prev[0]) != exp and len(vs) > len(prev[0])):
                    best[(bidx, c)] = (vs, path.name)

    problems, divergent, attached_star = [], [], 0
    books = []
    total = 0
    for b in range(39):
        exp = counts[b]
        chapters = []
        for c in range(1, len(exp) + 1):
            entry = best.get((b, c))
            if entry is None:
                problems.append(f"{names[b]} {c}: MISSING")
                chapters.append([])
                continue
            vs, src = entry
            clean = []
            for v in vs:
                attached_star += len(re.findall(r"\S%s|%s\S" % (STAR, STAR), v))
                clean.append(normalise(v))
            if any(not x for x in clean):
                problems.append(f"{names[b]} {c}: {sum(1 for x in clean if not x)}"
                                f" EMPTY verse(s) [{src}]")
            if len(clean) != exp[c - 1]:
                divergent.append((names[b], b, c, len(clean), exp[c - 1], src))
            chapters.append(clean)
            total += len(clean)
        books.append({"name": names[b], "chapters": chapters})

    # ── assertions the asset must satisfy ───────────────────────────────────
    leaks = 0
    for bk in books:
        for ch in bk["chapters"]:
            for v in ch:
                leaks += sum(1 for ch_ in v if ord(ch_) in TRANS)
    print(f"books assembled      : {len(books)}")
    print(f"verses               : {total}")
    print(f"Arabic yeh/kaf left  : {leaks}   (must be 0)")
    print(f"attached ٭ instances : {attached_star}   (deferred class, reported)")
    print(f"structural problems  : {len(problems)}")
    for p in problems[:20]:
        print("   ", p)
    print(f"\nchapters whose verse count differs from the KJV: {len(divergent)}")
    print("  → these need VERSEMAP curation, each seam text-verified.")
    print("  → the asset keeps the PRINT's divisions; nothing is reconciled here.")
    for n, b, c, got, e, src in divergent:
        print(f"   {n:<14} {c:>3}: {got:>3} vs KJV {e:<3}  [{src}]")

    assert leaks == 0, "Arabic yeh/kaf survived normalisation"
    if args.dry_run or not args.out:
        print("\n(dry run — nothing written)")
        return

    asset = json.load(open(ASSET, encoding="utf-8"))
    assert len(asset) == 66, f"expected 66 book slots, found {len(asset)}"
    for b in range(39):
        assert not asset[b]["chapters"], \
            f"slot {b} ({asset[b]['name']}) is NOT empty — refusing to overwrite"
        asset[b]["chapters"] = books[b]["chapters"]
        asset[b]["name"] = BOOK_NAMES[b]        # replace English placeholder
    out = HERE.parent / "app/src/main/assets/bibles" / args.out
    json.dump(asset, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
