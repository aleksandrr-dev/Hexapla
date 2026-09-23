# -*- coding: utf-8 -*-
"""Recover 3 Ездры (II Esdras) and 3 Маккавейская (III Maccabees) for
cu_elizabeth.json, both currently empty stubs (chapters: []).

ROOT CAUSE (verified 2026-07-19 via raw pysword queries against the cached
CrossWire CSlElizabeth module): the module cu_elizabeth.json was converted
from never digitized these two books at all — every verse query returns "".
Every OTHER apocryphal book (Tobit, Judith, 1-2 Maccabees, 1-2 Esdras, etc.)
is present and correct. This is a source-completeness gap, not a converter
bug — nothing in the existing pipeline can recover it.

SOURCE: the Ponomar Project (github.com/typiconman/ponomar,
Ponomar/languages/cu/bible/elis/{III_Esdra,III_Macc}.text) has full Church
Slavonic text for both books — the same 1751 Elizabeth-Bible edition this
asset's OTHER 81 books were transliterated from (see fix_cu_psalm_titles.py,
whose corpus-learning approach this script generalizes).

THE TRANSLITERATION PROBLEM is identical to the psalm-titles case: Ponomar
is full Church Slavonic orthography (titlos, ѣ ѡ ѧ ligatures, accents); the
asset is civil-script. fix_cu_psalm_titles.py solved this for ~2,400 psalm
verse pairs by LEARNING the civil rendering of each CS word from a parallel
corpus instead of hand-writing conversion rules (the ru_stress failure mode:
invented word forms, 1,029 corrupt verses). This script extends that same
method to the WHOLE BIBLE: every one of cu_elizabeth's 81 already-filled
books has a Ponomar counterpart in elis/, giving a corpus roughly an order
of magnitude larger than the psalm-only one, before ever touching the two
missing books. Esdras/Maccabees narrative-prose vocabulary is well covered
by the already-shipped Ezra/1-2 Maccabees/Nehemiah texts in that corpus.

ALIGNMENT SAFETY: pairing is done per CHAPTER, not per book — a chapter is
only used for corpus-building if Ponomar's and the asset's verse counts for
that chapter match exactly (mirrors fix_cu_psalm_titles.py's per-psalm body
gate: a numbering mismatch can only cause a SKIP, never a misalignment).
Most books match exactly chapter-for-chapter; ~15 books have isolated
chapters with a native ±1 verse-split unrelated to the two target books —
those individual chapters are skipped, not the whole book.

APPLYING TO THE TARGET BOOKS: word-by-word, per verse. A verse is only
"fully resolved" if EVERY token is corpus-reliable; if even one word isn't,
the WHOLE VERSE goes to the review file with the unresolved word(s)
⟨bracketed⟩ — never a partial silent guess (same all-or-nothing per-title
rule as fix_cu_psalm_titles.py, at verse instead of title granularity).

VERSIFICATION: neither target book has any prior cu_elizabeth verse
numbering to match, so this script adopts ru_synodal.json's structure (same
Synodal-tradition family, itself matching the standard synodal canon from
pysword's canons.py). Ponomar's own numbering matches that structure exactly
except two tail-of-chapter native splits (confirmed by direct inspection,
not assumed):
  - 3 Ездры 16: Ponomar has 79 verses where the canon has 78. v78+v79 read
    as one continuous clause ("Го́ре и҆̀же стиснѧ́ютсѧ..." / "и҆́мже
    ѡ҆́бразомъ..."); ru_synodal's existing v78 is exactly their concatenation.
    Verses 1-77 align 1:1 (spot-checked).
  - 3 Маккавейская 2: Ponomar has 25 verses where the canon has 24. v24+v25
    likewise concatenate to ru_synodal's existing v24. Verses 1-23 align 1:1
    (spot-checked).
  Both are therefore merged (Ponomar's two verses -> one target verse) when
  building the output, matching the choice ru_synodal's own converter
  already made for the same edition family. This is a design decision, not
  a silent default — it is asserted and printed, and the owner can revisit.

LICENSING — OPEN QUESTION, not resolved by this script: the owner's prior
2026-07-16 decision to skip a Ponomar permission email was reasoned
specifically around SHORT FORMULAIC psalm titles (135 short phrases).
Recovering two entire books (23 chapters, ~950 verses of running prose) is a
different scale of use of Ponomar's transcription work. See CLAUDE.md and
store-assets/ponomar_email_draft.txt. Do not extend the psalm-titles PD
reasoning to this use without an explicit owner decision.

USAGE:
    python tools/convert_cu_apocrypha.py              # dry run (default)
    python tools/convert_cu_apocrypha.py --dry-run     # same, explicit
    python tools/convert_cu_apocrypha.py --apply-review FILE   # apply

Writes NOTHING to app/src/main/assets/bibles/cu_elizabeth.json unless
--apply-review is passed with a fully-resolved, owner-approved annotated
review file (and even then only after a backup + verse-count assertions on
every OTHER book). The default (no flags) and --dry-run both only print the
report and write the review file.

--apply-review FILE expects the ANNOTATED review file format produced by
the owner-delegated review pass (cu_apocrypha_review_annotated.txt): a
"PER-VERSE DETAIL" section with one block per held-back verse of the shape

    3 Ездры 1:1   [verse verdict: LOW-CONFIDENCE]
      raw      : ...
      SUGGESTED: ...
      FINAL    : <verified full verse text, no ⟨⟩ remaining>
        <word> -> <replacement>   RESOLVED[source] | LOW-CONFIDENCE
            <note>
      (blank line)

It re-runs the SAME corpus-build + transliteration pipeline as the dry run
(so the ~85% of verses that never needed review are taken verbatim from
that pipeline output, unchanged), then overlays the FINAL text from the
annotated file onto exactly the verses that pipeline flagged as needing
review — asserting the coordinate sets match exactly in both directions
before writing anything.
"""
import argparse
import json
import random
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "cu_elizabeth.json")
RU_ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
            / "bibles" / "ru_synodal.json")

PONOMAR_DIR = Path(
    "C:/Users/infer/AppData/Local/Temp/claude/C--Projects-Hexapla/"
    "f9e5cf18-a888-4bf7-a230-2cd4fad9d6ae/scratchpad/ponomar_elis")

REVIEW_PATH = Path("C:/Projects/Hexapla-releases/cu_apocrypha_review.txt")
ANNOTATED_REVIEW_PATH = Path(
    "C:/Projects/Hexapla-releases/cu_apocrypha_review_annotated.txt")
BACKUP_DIR = Path("C:/Projects/Hexapla-releases/asset-backups")

# cu_elizabeth.json book index -> Ponomar elis/ filename (without .text),
# for every already-filled book. Verified 2026-07-19: chapter counts match
# exactly for every book except the ~15 listed with isolated-chapter native
# splits (handled by the per-chapter equal-length gate below, not curated
# here — those chapters are simply skipped from the corpus).
BOOK_MAP = {
    0: "Gen", 1: "Ex", 2: "Lev", 3: "Num", 4: "Deut", 5: "Josh", 6: "Judg",
    7: "Ruth", 8: "I_Kings", 9: "II_Kings", 10: "III_Kings", 11: "IV_Kings",
    12: "I_Paral", 13: "II_Paral", 14: "I_Esdra", 15: "Nehem", 16: "Esther",
    17: "Job", 18: "Psalm", 19: "Prov", 20: "Eccles", 21: "Song",
    22: "Isa", 23: "Jerem", 24: "Lamen", 25: "Ezek", 26: "Dan",
    27: "Hos", 28: "Joel", 29: "Amos", 30: "Obad", 31: "Jona", 32: "Mica",
    33: "Nahum", 34: "Habak", 35: "Zeph", 36: "Hagg", 37: "Zech", 38: "Mal",
    39: "Mt", 40: "Mk", 41: "Lk", 42: "Jn", 43: "Acts", 44: "Rom",
    45: "I_Cor", 46: "II_Cor", 47: "Gal", 48: "Eph", 49: "Philip", 50: "Col",
    51: "I_Thess", 52: "II_Thess", 53: "I_Tim", 54: "II_Tim", 55: "Tit",
    56: "Philemon", 57: "Heb", 58: "Jas", 59: "I_Pet", 60: "II_Pet",
    61: "I_Jn", 62: "II_Jn", 63: "III_Jn", 64: "Jude", 65: "Apoc",
    66: "II_Esdra",   # "2 Ездры" (apocryphal, = English "1 Esdras")
    # 67 = "3 Ездры" is a TARGET, not corpus
    68: "Tobit", 69: "Judith", 70: "Wisd", 71: "Sirach", 72: "Baruch",
    73: "Epistle",   # "Послание Иеремии" = Epistle of Jeremiah
    75: "I_Macc", 76: "II_Macc",
    # 77 = "3 Маккавейская" is a TARGET, not corpus
}

# index -> (ponomar filename, target verse counts per chapter, tail-merge map)
TARGETS = {
    67: dict(
        name="3 Ездры", ponomar="III_Esdra",
        counts=[40, 48, 36, 52, 56, 59, 70, 63, 47, 60, 46, 51, 58, 48, 63, 78],
        merge_tail={16: 78},   # Ponomar ch16 v78+v79 -> target v78
    ),
    77: dict(
        name="3 Маккавейская", ponomar="III_Macc",
        counts=[25, 24, 22, 16, 36, 37, 20],
        merge_tail={2: 24},    # Ponomar ch2 v24+v25 -> target v24
    ),
}

WORD = re.compile(r"[^\s]+")
STRIP_PUNCT = ".,:;!?()[]{}«»\"'"

REL_MIN_COUNT = 2
REL_MIN_SHARE = 0.90

HOLDOUT_SAMPLE = 4000     # cap for the hold-one-out end-to-end test
HOLDOUT_SEED = 20260719


# --------------------------------------------------------------------------
# Ponomar parsing (generalization of fix_cu_psalm_titles.py's parse_ponomar)
# --------------------------------------------------------------------------

def parse_ponomar(path):
    """chapter -> {verse_num: text}. Verse 0 (titles) kept but excluded from
    normal alignment; {variant readings} stripped."""
    out = {}
    cur = None
    for line in open(path, encoding="utf-8").read().splitlines():
        line = line.strip()
        m = re.match(r"^#(\d+)$", line)
        if m:
            cur = int(m.group(1))
            out[cur] = {}
            continue
        m = re.match(r"^(\d+)\|\s*(.*)$", line)
        if m and cur is not None:
            n, text = int(m.group(1)), m.group(2).strip()
            text = re.sub(r"\{[^{}]*\}", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            out[cur][n] = text
    return out


def tokens(s):
    return [t.strip(STRIP_PUNCT) for t in WORD.findall(s)
            if t.strip(STRIP_PUNCT)]


def key_acc(w):
    return unicodedata.normalize("NFC", w).lower()


def key_cs(w):
    w = unicodedata.normalize("NFD", w)
    w = "".join(c for c in w if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", w).lower()


# --------------------------------------------------------------------------
# Corpus: every already-filled book, aligned per CHAPTER
# --------------------------------------------------------------------------

def build_corpus(books):
    """Yield (cs_verse, civil_verse, coord) for every chapter whose verse
    count matches exactly between Ponomar and the asset. coord is a
    'BookName N:M' style label used only for diagnostics."""
    stats = Counter()
    pairs = []
    for idx, fn in BOOK_MAP.items():
        path = PONOMAR_DIR / f"{fn}.text"
        if not path.exists():
            stats["missing_files"] += 1
            print(f"  WARNING: {fn}.text not cached — book idx{idx} "
                  f"({books[idx]['name']}) excluded from corpus")
            continue
        pon = parse_ponomar(path)
        app_chapters = books[idx]["chapters"]
        name = books[idx]["name"]
        for ch_num in sorted(pon):
            if ch_num < 1 or ch_num > len(app_chapters):
                continue
            verse_dict = {v: t for v, t in pon[ch_num].items() if v >= 1}
            app_ch = app_chapters[ch_num - 1]
            n = len(app_ch)
            if not verse_dict or not app_ch:
                continue
            if set(verse_dict) != set(range(1, n + 1)):
                stats["chapters_skipped_gap_or_len"] += 1
                continue
            stats["chapters_used"] += 1
            for v in range(1, n + 1):
                pairs.append((verse_dict[v], app_ch[v - 1],
                              f"{name} {ch_num}:{v}"))
    stats["pairs"] = len(pairs)
    return pairs, stats


def build_dictionary(pairs):
    acc = defaultdict(Counter)
    strip = defaultdict(Counter)
    used = 0
    for cs_v, civ_v, _coord in pairs:
        ct, vt = tokens(cs_v), tokens(civ_v)
        if len(ct) != len(vt) or not ct:
            continue
        used += 1
        for c, v in zip(ct, vt):
            acc[key_acc(c)][v] += 1
            strip[key_cs(c)][v] += 1
    return (acc, strip), used


def _pick(counter, min_count, min_share):
    total = sum(counter.values())
    if total <= 0:
        return None
    folded = Counter()
    for form, n in counter.items():
        folded[form.lower()] += n
    form, n = folded.most_common(1)[0]
    if not (total >= min_count and n / total >= min_share):
        return None
    caps = sum(v for f, v in counter.items()
               if f.lower() == form and f[:1].isupper())
    return form.capitalize() if caps / n > 0.8 else form


def reliable_form(vocab, word):
    acc, strip = vocab
    c = acc.get(key_acc(word))
    if c:
        f = _pick(c, 1, 0.95)
        if f:
            return f
    c = strip.get(key_cs(word))
    if c:
        return _pick(c, REL_MIN_COUNT, REL_MIN_SHARE)
    return None


def reliable_form_diag(vocab, word):
    """Like reliable_form, but also returns (total, share) for whichever
    tier's counter produced the answer — used only for holdout diagnostics,
    to distinguish a thin-margin call from a landslide one."""
    acc, strip = vocab
    c = acc.get(key_acc(word))
    if c:
        f = _pick(c, 1, 0.95)
        if f:
            total = sum(c.values())
            share = sum(v for k, v in c.items() if k.lower() == f.lower()) / total
            return f, total, share
    c = strip.get(key_cs(word))
    if c:
        f = _pick(c, REL_MIN_COUNT, REL_MIN_SHARE)
        if f:
            total = sum(c.values())
            share = sum(v for k, v in c.items() if k.lower() == f.lower()) / total
            return f, total, share
    return None, 0, 0.0


# A holdout mismatch is a LANDSLIDE override — the corpus (recomputed WITH
# the held-out instance removed) still clears the SAME reliability bar the
# pipeline itself uses at build time (share >= REL_MIN_SHARE), with at
# least LANDSLIDE_MIN_TOTAL independent attestations — when the single
# asset spelling being tested against is almost certainly itself the
# outlier (a typo/OCR artifact or a rare archaic-spelling variant already
# present in the shipped asset), not a dictionary error.
#
# First run of this script (2026-07-19) found 34 holdout mismatches, EVERY
# ONE with share >= 91.7% for the dictionary's answer (many at 100%) — so
# share alone barely discriminates here (by construction, every mismatch
# passed reliable_form's own >=90% bar to be produced at all). The real
# signal is sample size: with total >= 3 independent corpus attestations,
# hand review of every case (aще/аше, по/но, missing-letter OCR typos like
# "свидетелство"/"свидетельство" x50, "отвсти"/"отвести", "снов"/"сынов",
# "вкпе"/"вкупе") confirmed the dictionary's answer, never the asset's
# held-out spelling. Only at total < 3 (a single surviving corpus vote
# after holdout) does genuine ambiguity show up — e.g. "рыданий" vs
# "рыдании" at Откровение 18:7, exactly the accent-collapse risk the
# two-tier dictionary design exists to guard against (a near-singleton
# accented form shadowed by a barely-over-threshold stripped-tier
# fallback). The hard stop is scoped to THIN-MARGIN (total < 3) cases
# only; landslide cases are reported in full, never hidden, but do not
# block the pipeline.
LANDSLIDE_MIN_TOTAL = 3
LANDSLIDE_MIN_SHARE = 0.90


def validate(pairs, vocab):
    ok = wrong = 0
    for cs_v, civ_v, _coord in pairs:
        ct, vt = tokens(cs_v), tokens(civ_v)
        if len(ct) != len(vt) or not ct:
            continue
        for c, v in zip(ct, vt):
            form = reliable_form(vocab, c)
            if form is None:
                continue
            if form.lower() == v.lower():
                ok += 1
            else:
                wrong += 1
    return ok, wrong


# --------------------------------------------------------------------------
# Hold-one-out end-to-end test — the gate that matters: SILENT-WRONG
# --------------------------------------------------------------------------

def holdout_test(pairs, vocab, sample_n=HOLDOUT_SAMPLE, seed=HOLDOUT_SEED):
    acc, strip = vocab
    usable = [(c, v, coord) for c, v, coord in pairs
              if len(tokens(c)) == len(tokens(v)) and tokens(c)]
    rng = random.Random(seed)
    sample = usable if len(usable) <= sample_n else rng.sample(usable, sample_n)

    results = []
    for cs_v, civ_v, coord in sample:
        ct, vt = tokens(cs_v), tokens(civ_v)
        held = list(zip(ct, vt))
        for c, v in held:
            acc[key_acc(c)][v] -= 1
            strip[key_cs(c)][v] -= 1

        got_words, missing = [], []
        for c in ct:
            f = reliable_form(vocab, c)
            if f is None:
                missing.append(c)
                got_words.append(None)
            else:
                got_words.append(f.lower())

        for c, v in held:
            acc[key_acc(c)][v] += 1
            strip[key_cs(c)][v] += 1

        want_words = [w.lower() for w in vt]
        if missing:
            results.append(("flagged", coord, got_words, want_words, missing, None))
        elif got_words == want_words:
            results.append(("exact", coord, got_words, want_words, missing, None))
        else:
            # classify severity: landslide (corpus overwhelmingly backs the
            # dictionary's answer over this one held-out instance) vs
            # thin-margin (a genuine low-confidence call — the real risk).
            diag = []
            for i, (g, w) in enumerate(zip(got_words, want_words)):
                if g != w:
                    for c, v in held:
                        acc[key_acc(c)][v] -= 1
                        strip[key_cs(c)][v] -= 1
                    _f, total, share = reliable_form_diag(vocab, ct[i])
                    for c, v in held:
                        acc[key_acc(c)][v] += 1
                        strip[key_cs(c)][v] += 1
                    diag.append((ct[i], g, w, total, share))
            thin = any(total < LANDSLIDE_MIN_TOTAL or share < LANDSLIDE_MIN_SHARE
                       for _s, _g, _w, total, share in diag)
            kind = "silent_thin" if thin else "silent_landslide"
            results.append((kind, coord, got_words, want_words, missing, diag))
    return results


# --------------------------------------------------------------------------
# Transliteration of the target books
# --------------------------------------------------------------------------

def transliterate_verse(text, vocab):
    """Word-by-word via reliable corpus forms, punctuation preserved
    verbatim from the source. Returns (text, missing_words)."""
    out, missing = [], []
    for raw in WORD.findall(text):
        core = raw.strip(STRIP_PUNCT)
        if not core:
            out.append(raw)   # standalone punctuation token — pass through
            continue
        lead = raw[:len(raw) - len(raw.lstrip(STRIP_PUNCT))]
        trail = raw[len(raw.rstrip(STRIP_PUNCT)):]
        form = reliable_form(vocab, core)
        if form is None:
            missing.append(core)
            out.append(f"{lead}⟨{core}⟩{trail}")
        else:
            out.append(lead + form + trail)
    joined = " ".join(out)
    return (joined[0].upper() + joined[1:] if joined else joined), missing


CHAR = str.maketrans({"ѣ": "е", "Ѣ": "Е", "ѡ": "о", "Ѡ": "О",
                       "ѧ": "я", "Ѧ": "Я", "ꙗ": "я", "Ꙗ": "Я",
                       "ї": "и", "Ї": "И", "і": "и", "І": "И",
                       "ꙋ": "у", "Ꙋ": "У", "є": "е", "Є": "Е",
                       "ѕ": "з", "Ѕ": "З", "ѳ": "ф", "Ѳ": "Ф",
                       "ѻ": "о", "Ѻ": "О", "ѵ": "и", "Ѵ": "И"})


def charmap(w):
    s = unicodedata.normalize("NFD", w)
    s = "".join(c for c in s if not unicodedata.combining(c) or c == "̆")
    s = unicodedata.normalize("NFC", s).translate(CHAR)
    s = s.replace("ᲂу", "у").replace("ᲂ", "")
    s = re.sub(r"ъ$", "", s)
    has_titlo = any("ⷠ" <= ch <= "ⷿ" or ch == "҃"
                    for ch in unicodedata.normalize("NFD", w))
    return f"⟨{w}⟩" if has_titlo else s


def build_target_verses(target, vocab):
    """Returns list-of-chapters of (text, missing_words, coord)."""
    pon = parse_ponomar(PONOMAR_DIR / f"{target['ponomar']}.text")
    counts = target["counts"]
    merge_tail = target["merge_tail"]
    out_chapters = []
    for ch_num in range(1, len(counts) + 1):
        n_target = counts[ch_num - 1]
        ch = pon.get(ch_num, {})
        n_pon = max(ch) if ch else 0
        merged_at = merge_tail.get(ch_num)
        if merged_at is not None:
            assert n_pon == n_target + 1, (
                f"ch{ch_num}: expected Ponomar to have exactly one more "
                f"verse than target for a tail-merge (pon={n_pon}, "
                f"target={n_target})")
        else:
            assert n_pon == n_target, (
                f"ch{ch_num}: Ponomar has {n_pon} verses, target wants "
                f"{n_target}, and no merge is curated for this chapter — "
                f"UNEXPECTED, refusing")
        chapter_out = []
        for v in range(1, n_target + 1):
            if merged_at is not None and v == merged_at:
                src = ch[v] + " " + ch[v + 1]
            else:
                src = ch[v]
            text, missing = transliterate_verse(src, vocab)
            chapter_out.append((text, missing, f"{target['name']} {ch_num}:{v}"))
        out_chapters.append(chapter_out)
    return out_chapters


# --------------------------------------------------------------------------
# --apply-review: parse the ANNOTATED review file and apply
# --------------------------------------------------------------------------

VERSE_BLOCK_RE = re.compile(
    r"^(3 Ездры|3 Маккавейская) (\d+):(\d+)   \[verse verdict: "
    r"(RESOLVED|LOW-CONFIDENCE|STILL-UNRESOLVED)\]\n"
    r"  raw      : (.*)\n"
    r"  SUGGESTED: (.*)\n"
    r"  FINAL    : (.*)\n",
    re.MULTILINE,
)

FOCUS_COORD_RE = re.compile(
    r"^\s*(3 Ездры|3 Маккавейская)\s+(\d+):(\d+)\s+(\S+)\s*->\s*(\S+)\s*$")
FOCUS_PLAIN_RE = re.compile(r"^\s*(\S+)\s*->\s*(\S+)\s*$")


def parse_annotated_review(path):
    """Returns (verse_map, focus_words).

    verse_map: {(book_name, ch, v): (verdict, final_text)} for every
    per-verse block in the PER-VERSE DETAIL section.
    focus_words: set of raw Church-Slavonic source-word strings listed in
    the FOCUS LIST FOR A NATIVE READER section (the genuine judgment
    calls — everything else in verse_map is mechanical RESOLVED/
    LOW-CONFIDENCE application).
    """
    text = open(path, encoding="utf-8").read()

    if "PER-VERSE DETAIL" not in text:
        sys.exit(f"{path}: 'PER-VERSE DETAIL' section header not found — "
                  f"unexpected file format, refusing to guess")
    detail = text[text.index("PER-VERSE DETAIL"):]

    verse_map = {}
    for m in VERSE_BLOCK_RE.finditer(detail):
        book, ch, v, verdict, _raw, _sug, final = m.groups()
        key = (book, int(ch), int(v))
        if key in verse_map:
            sys.exit(f"duplicate verse block for {book} {ch}:{v} in "
                      f"{path} — refusing to guess which is authoritative")
        if "⟨" in final or "⟩" in final:
            sys.exit(f"{book} {ch}:{v}: FINAL line still contains an "
                      f"unresolved ⟨bracket⟩ — refusing to apply")
        verse_map[key] = (verdict, final)

    if "FOCUS LIST FOR A NATIVE READER" not in text:
        sys.exit(f"{path}: 'FOCUS LIST FOR A NATIVE READER' section not "
                  f"found — refusing to guess which words were judgment "
                  f"calls")
    focus_section = text[
        text.index("FOCUS LIST FOR A NATIVE READER"):text.index("PER-VERSE DETAIL")]
    focus_words = set()
    for line in focus_section.splitlines():
        m = FOCUS_COORD_RE.match(line)
        if m:
            focus_words.add(m.group(4))
            continue
        m = FOCUS_PLAIN_RE.match(line)
        if m and "->" in line:
            focus_words.add(m.group(1))

    return verse_map, focus_words


def apply_review(review_path):
    review_path = Path(review_path)
    if not review_path.exists():
        sys.exit(f"review file not found: {review_path}")

    verse_map, focus_words = parse_annotated_review(review_path)
    print(f"parsed {len(verse_map)} reviewed verses, "
          f"{len(focus_words)} FOCUS LIST judgment-call source words "
          f"from {review_path.name}")

    books = json.load(open(ASSET, encoding="utf-8"))
    counts_before = [len(b["chapters"]) for b in books]
    other_books_before = [b for i, b in enumerate(books) if i not in TARGETS]
    other_books_before_json = json.dumps(other_books_before,
                                          ensure_ascii=False, sort_keys=True)

    for idx in TARGETS:
        if books[idx]["chapters"]:
            sys.exit(f"idx{idx} ({books[idx]['name']}) already has "
                      f"{len(books[idx]['chapters'])} chapters — expected "
                      f"an empty stub, refusing (state inconsistent with "
                      f"the documented starting point)")

    print("rebuilding the corpus + auto-transliteration pipeline (same as "
          "the dry run) so the ~85% of verses that never needed review are "
          "taken from it verbatim...")
    pairs, stats = build_corpus(books)
    vocab, used = build_dictionary(pairs)
    ok, wrong = validate(pairs, vocab)
    acc_rate = ok / max(ok + wrong, 1)
    print(f"  reliable-word accuracy: {acc_rate:.2%} "
          f"({stats['pairs']} corpus pairs, {len(vocab[1])} word forms)")
    if acc_rate < 0.98:
        sys.exit("reliable-word accuracy below 98% — refusing to proceed")

    review_coords_seen = set()
    judgment_call_verses = []
    mechanical_review_verses = 0
    final_books = {}
    for idx, target in TARGETS.items():
        chapters = build_target_verses(target, vocab)
        final_chapters = []
        for c in chapters:
            row = []
            for text, missing, coord in c:
                book_name, rest = coord.rsplit(" ", 1)
                ch_s, v_s = rest.split(":")
                key = (book_name, int(ch_s), int(v_s))
                if missing:
                    if key not in verse_map:
                        sys.exit(f"{coord}: pipeline flagged this verse as "
                                  f"needing review but it has no block in "
                                  f"{review_path.name} — refusing")
                    review_coords_seen.add(key)
                    verdict, final_text = verse_map[key]
                    row.append(final_text)
                    mechanical_review_verses += 1
                    if any(w in focus_words for w in missing):
                        judgment_call_verses.append(
                            (coord, [w for w in missing if w in focus_words]))
                else:
                    row.append(text)
            final_chapters.append(row)
        final_books[idx] = final_chapters

    # Every reviewed coordinate must have been consumed exactly once, and
    # every consumed coordinate must have come from the review file — no
    # silent leftovers in either direction.
    unused = set(verse_map) - review_coords_seen
    if unused:
        sys.exit(f"{len(unused)} verse block(s) in {review_path.name} were "
                  f"never matched to a pipeline-flagged verse (e.g. "
                  f"{sorted(unused)[:5]}) — refusing, coordinates may have "
                  f"drifted between the dry run and this review file")
    print(f"applied {len(review_coords_seen)} reviewed verses "
          f"(pipeline-flagged == review-file-covered, exact match)")
    print(f"  of those, {len(judgment_call_verses)} verse(s) contain a "
          f"FOCUS LIST judgment-call word (tracked below, not just "
          f"mechanical RESOLVED/LOW-CONFIDENCE application)")
    if judgment_call_verses:
        print("  FOCUS LIST judgment-call verses:")
        for coord, words in judgment_call_verses:
            print(f"    {coord}: {', '.join(words)}")

    for idx, target in TARGETS.items():
        final_chapters = final_books[idx]
        actual_counts = [len(c) for c in final_chapters]
        if actual_counts != target["counts"]:
            sys.exit(f"idx{idx} {target['name']}: final chapter/verse "
                      f"counts {actual_counts} != expected "
                      f"{target['counts']} — refusing to write")
        if any("⟨" in v or "⟩" in v for c in final_chapters for v in c):
            sys.exit(f"idx{idx} {target['name']}: leftover ⟨bracket⟩ found "
                      f"in the final verse array — refusing to write")

    for idx, target in TARGETS.items():
        books[idx]["chapters"] = final_books[idx]

    other_books_after = [b for i, b in enumerate(books) if i not in TARGETS]
    other_books_after_json = json.dumps(other_books_after,
                                         ensure_ascii=False, sort_keys=True)
    assert other_books_before_json == other_books_after_json, (
        "a book other than the two apocrypha targets changed — refusing")
    assert [len(b["chapters"]) for i, b in enumerate(books) if i not in TARGETS] == \
           [c for i, c in enumerate(counts_before) if i not in TARGETS]

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / (ASSET.name + ".preapocrypha.bak")
    if backup.exists():
        sys.exit(f"backup already exists: {backup} — refusing to overwrite "
                  f"(this should not happen; investigate before proceeding)")
    shutil.copy2(ASSET, backup)
    print(f"backup written: {backup}")

    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))

    for idx, target in TARGETS.items():
        total = sum(len(c) for c in final_books[idx])
        print(f"wrote {target['name']} (idx{idx}): "
              f"{len(final_books[idx])} chapters, {total} verses")
    print(f"\nwrote {ASSET.name}. All other books byte-identical "
          f"(assertion passed).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="explicit alias for the default (no write)")
    ap.add_argument("--apply-review", metavar="FILE",
                     help="apply an owner-reviewed ANNOTATED review file "
                          "(cu_apocrypha_review_annotated.txt format) to "
                          "the asset")
    args = ap.parse_args()

    if args.apply_review:
        apply_review(args.apply_review)
        return

    books = json.load(open(ASSET, encoding="utf-8"))
    counts_before = [len(b["chapters"]) for b in books]

    print("=" * 70)
    print("STEP 1 — building the parallel corpus from all already-filled")
    print("cu_elizabeth books (Ponomar CS vs asset civil), chapter-gated")
    print("=" * 70)
    pairs, stats = build_corpus(books)
    print(f"books mapped: {len(BOOK_MAP)}   "
          f"chapters used: {stats['chapters_used']}   "
          f"chapters skipped (len/gap mismatch): "
          f"{stats['chapters_skipped_gap_or_len']}")
    print(f"verse pairs in corpus: {stats['pairs']}")

    vocab, used = build_dictionary(pairs)
    n_forms = len(vocab[1])
    print(f"verse pairs with matching token counts (usable for the "
          f"dictionary): {used}/{stats['pairs']}")
    print(f"distinct Church Slavonic word forms learned: {n_forms}")
    print(f"  (compare: fix_cu_psalm_titles.py's Psalm-only corpus was "
          f"~2,400 verse pairs)")

    print()
    print("=" * 70)
    print("STEP 2 — reliable-word accuracy over the corpus")
    print("=" * 70)
    ok, wrong = validate(pairs, vocab)
    acc_rate = ok / max(ok + wrong, 1)
    print(f"reliable-word accuracy (case-folded): {ok}/{ok + wrong} "
          f"({acc_rate:.2%})")
    if acc_rate < 0.98:
        sys.exit("reliable-word accuracy below 98% — refusing to proceed")

    print()
    print("=" * 70)
    print("STEP 3 — hold-one-out end-to-end test (the gate that matters)")
    print("=" * 70)
    ho = holdout_test(pairs, vocab)
    n_exact = sum(1 for r in ho if r[0] == "exact")
    n_flagged = sum(1 for r in ho if r[0] == "flagged")
    n_landslide = sum(1 for r in ho if r[0] == "silent_landslide")
    n_thin = sum(1 for r in ho if r[0] == "silent_thin")
    print(f"sampled {len(ho)} verse pairs (cap {HOLDOUT_SAMPLE}, "
          f"seed {HOLDOUT_SEED})")
    print(f"  exact                        : {n_exact}")
    print(f"  flagged-unknown              : {n_flagged}  (safe — word "
          f"correctly deferred, not guessed)")
    print(f"  silent-wrong, LANDSLIDE      : {n_landslide}  (reported in "
          f"full below, does NOT block — see rationale in the script's "
          f"LANDSLIDE_MIN_TOTAL comment)")
    print(f"  silent-wrong, THIN-MARGIN    : {n_thin}  <-- hard stop if "
          f"nonzero, this is the real risk")

    if n_landslide:
        print(f"\nlandslide overrides ({n_landslide}) — dictionary's "
              f"answer beats the held-out asset instance by "
              f">={LANDSLIDE_MIN_SHARE:.0%} share on >={LANDSLIDE_MIN_TOTAL} "
              f"corpus attestations; almost certainly the ASSET's held-out "
              f"spelling is the outlier (typo/OCR noise or a rare archaic "
              f"variant already in cu_elizabeth.json), not a dictionary "
              f"error. Shown in full, not hidden:")
        for kind, coord, got, want, _missing, diag in ho:
            if kind == "silent_landslide":
                for src, g, w, total, share in diag:
                    print(f"  {coord}: src={src!r}  got={g!r}  want={w!r}  "
                          f"(corpus: {total} attestations, {share:.1%} "
                          f"agree with 'got')")

    if n_thin:
        print(f"\nTHIN-MARGIN silent-wrong cases ({n_thin}) — genuine risk, "
              f"the ru_stress failure mode:")
        thin_srcs = set()
        for kind, coord, got, want, _missing, diag in ho:
            if kind == "silent_thin":
                print(f"  {coord}")
                print(f"    got : {got}")
                print(f"    want: {want}")
                for src, g, w, total, share in diag:
                    print(f"    src={src!r}  got={g!r}  want={w!r}  "
                          f"(corpus: {total} attestations, {share:.1%} "
                          f"agree with 'got')")
                    thin_srcs.add(key_acc(src))
                    thin_srcs.add(key_cs(src))

        # RELEVANCE CHECK: a thin-margin risk elsewhere in the whole-Bible
        # corpus only matters to THIS deliverable if the target books
        # actually need that word. If neither target book's own vocabulary
        # contains any thin-margin word, the risk is real (reported above,
        # not hidden) but doesn't touch what we're about to build — so the
        # dry-run REPORT may proceed. This does NOT relax the write gate:
        # nothing is written to the asset in this script yet regardless.
        target_vocab = set()
        for target in TARGETS.values():
            pon = parse_ponomar(PONOMAR_DIR / f"{target['ponomar']}.text")
            for ch in pon.values():
                for text in ch.values():
                    for t in tokens(text):
                        target_vocab.add(key_acc(t))
                        target_vocab.add(key_cs(t))
        overlap = thin_srcs & target_vocab
        if overlap:
            sys.exit(f"\nthin-margin word(s) {overlap} appear in the "
                     f"target books' own vocabulary — refusing to "
                     f"transliterate anything")
        print(f"\n  RELEVANCE CHECK: none of the {n_thin} thin-margin "
              f"word(s) above appear anywhere in III Ездры / III "
              f"Маккавейская's own text — this whole-Bible-corpus risk is "
              f"real and reported, but does not touch the two target "
              f"books. Proceeding to build the coverage report (still "
              f"WRITES NOTHING — see Step 6).")

    print()
    print("=" * 70)
    print("STEP 4 — chapter/verse-count validation against the Synodal canon")
    print("=" * 70)
    ru = json.load(open(RU_ASSET, encoding="utf-8"))
    for idx, target in TARGETS.items():
        ru_counts = [len(c) for c in ru[idx]["chapters"]]
        match = ru_counts == target["counts"]
        print(f"idx{idx} {target['name']}: target counts vs ru_synodal.json "
              f"— {'MATCH' if match else 'MISMATCH'}")
        if not match:
            sys.exit(f"target counts for idx{idx} do not match ru_synodal "
                      f"— refusing (this should never happen; the counts "
                      f"table was built FROM ru_synodal)")
        pon = parse_ponomar(PONOMAR_DIR / f"{target['ponomar']}.text")
        pon_counts = [max(pon[c]) for c in sorted(pon)]
        for ch_num, (pc, tc) in enumerate(zip(pon_counts, target["counts"]), 1):
            merged = target["merge_tail"].get(ch_num)
            if merged is not None:
                status = "native tail-split, MERGED to match canon" if pc == tc + 1 else "UNEXPECTED"
            else:
                status = "exact" if pc == tc else "UNEXPECTED MISMATCH"
            if merged is not None or pc != tc:
                print(f"  ch{ch_num}: Ponomar={pc}  canon={tc}  [{status}]")

    print()
    print("=" * 70)
    print("STEP 5 — transliterating the two target books")
    print("=" * 70)
    review_entries = []
    book_reports = {}
    for idx, target in TARGETS.items():
        chapters = build_target_verses(target, vocab)
        total_verses = sum(len(c) for c in chapters)
        fully_resolved = sum(1 for c in chapters for (_t, m, _co) in c if not m)
        needs_review = total_verses - fully_resolved
        book_reports[idx] = (target["name"], total_verses, fully_resolved,
                              needs_review)
        print(f"\n{target['name']} (idx{idx}): {len(chapters)} chapters, "
              f"{total_verses} verses")
        print(f"  fully auto-resolved: {fully_resolved} "
              f"({fully_resolved / total_verses:.1%})")
        print(f"  needs review       : {needs_review} "
              f"({needs_review / total_verses:.1%})")
        for c in chapters:
            for text, missing, coord in c:
                if missing:
                    review_entries.append((coord, text, missing))

    print()
    print("=" * 70)
    print("STEP 6 — review file")
    print("=" * 70)
    if review_entries:
        REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REVIEW_PATH, "w", encoding="utf-8") as rf:
            rf.write("Church Slavonic apocrypha (3 Ездры / 3 Маккавейская) "
                     "— OWNER REVIEW\n")
            rf.write("=" * 60 + "\n")
            rf.write(
                "Corpus-attested words are rendered from the whole-Bible "
                "parallel\ncorpus (validated above). ⟨Bracketed⟩ words "
                "were never seen in the\ncorpus; a SUGGESTED line renders "
                "them by a mechanical letter map\n(accents stripped, ѣ→е "
                "etc.) — titlo abbreviations cannot be\nchar-mapped and "
                "remain bracketed. A verse with ANY bracketed word\nis "
                "held back in full — nothing here has been written to "
                "the asset.\n\n"
                "LICENSING NOTE: this recovers two ENTIRE BOOKS (running "
                "prose,\nnot short titles) from Ponomar's transcription — "
                "a different scale\nof use than the psalm-titles case. "
                "See CLAUDE.md / this script's\ndocstring. Not resolved "
                "by this script.\n\n")
            for coord, text, missing in review_entries:
                sug = re.sub(r"⟨([^⟨⟩]*)⟩", lambda m: charmap(m.group(1)),
                             text)
                rf.write(f"{coord}\n  raw      : {text}\n"
                         f"  SUGGESTED: {sug}\n"
                         f"  unresolved words: {', '.join(missing)}\n\n")
        print(f"{len(review_entries)} verses need review — written to "
              f"{REVIEW_PATH}")
    else:
        print("no verses needed review (unexpected for a corpus this size "
              "— double check)")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for idx, (name, total, resolved, review) in book_reports.items():
        print(f"  {name}: {resolved}/{total} verses fully auto-resolved "
              f"({resolved/total:.1%}), {review} need review")
    print(f"\n  corpus: {stats['pairs']} verse pairs, {n_forms} word forms, "
          f"{acc_rate:.2%} reliable-word accuracy")
    print(f"  holdout: {n_exact} exact / {n_flagged} flagged-unknown / "
          f"{n_landslide} silent-landslide (non-blocking) / "
          f"{n_thin} silent-THIN-MARGIN (of {len(ho)} sampled)")
    print(f"\n  asset counts before: unchanged (dry run — nothing written)")
    assert [len(b["chapters"]) for b in books] == counts_before
    print(f"\n  (dry run — {ASSET.name} was not modified)")


if __name__ == "__main__":
    main()
