# -*- coding: utf-8 -*-
"""Restore missing psalm superscriptions (надписания) in cu_elizabeth.json.

SOURCE: the Ponomar Project's Elizabeth psalter (typiconman/ponomar,
Ponomar/languages/cu/bible/elis/Psalm.text) — the same 1751 edition our asset
was transliterated from (proven: its verses reduce to our asset's text under
the asset's own convention). Titles sit as verse `0|` lines; 135 of 151
psalms carry one. License: owner decision 2026-07-16 to proceed on the PD
reasoning without a permission email (see CLAUDE.md; the draft email is kept
at store-assets/ponomar_email_draft.txt should feedback ever arrive).
Ponomar must be credited in sources_text before this ships (TODO).

THE TRANSLITERATION PROBLEM — and why this is not ru_stress again:
Ponomar is full Church Slavonic orthography (titlos, ѣ ѡ ѧ, accents); the
asset is civil spelling. Hand-writing the conversion is the ru_stress failure
mode (invented word forms, 1,029 corrupt verses). Instead the convention is
LEARNED from the texts themselves: both are the same edition, so their
~2,400 aligned verse pairs form a parallel corpus. Every Church Slavonic
word in a title is rendered ONLY by its civil form as attested in that
corpus (majority vote across occurrences). A title containing ANY word never
attested in the corpus is NOT applied — it goes to a review bucket for the
owner (a native reader). The dictionary itself is validated by round-trip:
reconstructing verse bodies from it must reproduce the asset's text at a
high exact-match rate, reported at every run.

SAFETY (same pattern as fix_ru_psalm_titles.py):
  * psalm alignment gated by body match: the transliterated Ponomar v1 must
    match the asset's v1 (folded skeleton, autojunk=False) or the psalm is
    skipped — a numbering mismatch can only cause a SKIP;
  * title-shaped v1 guard: psalms whose v1 already IS a superscription
    (the Slavonic numbers some titles as verses, e.g. Пс 3) are never touched;
  * title-prefix-only edits, verse counts asserted unchanged, backup outside
    app/src/main/assets (Android bundles that tree into the APK).

    python tools/fix_cu_psalm_titles.py --dry-run
    python tools/fix_cu_psalm_titles.py
"""
import argparse
import difflib
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "cu_elizabeth.json")
PONOMAR = Path("C:/Users/infer/AppData/Local/Temp/claude/C--Projects-Hexapla/"
               "3f23918e-d4f5-4a45-a47c-fcc99c282210/scratchpad/ponomar_psalm.text")
PSALMS = 18
MIN_RATIO = 0.85
MIN_ATTEST = 1          # a word must be corpus-attested at least this often

# The asset's own titles (e.g. Пс 3:1 «Псалом Давиду, внегда отбегаше…») must
# never receive a second title on top.
TITLE_SHAPED = re.compile(
    r"^(Псалом|Песнь|Хвала|Аллилуия|Молитва|Разума|В конец|Давиду|"
    r"О |Не растли|Столпописание|Учение)")

WORD = re.compile(r"[^\s]+")
STRIP_PUNCT = ".,:;!?()[]{}«»\"'"


def parse_ponomar():
    """psalm -> {'title': str|None, 'verses': [str, ...]}"""
    out = {}
    cur = None
    for line in open(PONOMAR, encoding="utf-8").read().splitlines():
        line = line.strip()
        m = re.match(r"^#(\d+)$", line)
        if m:
            cur = int(m.group(1))
            out[cur] = {"title": None, "verses": []}
            continue
        m = re.match(r"^(\d+)\|\s*(.*)$", line)
        if m and cur is not None:
            n, text = int(m.group(1)), m.group(2).strip()
            text = re.sub(r"\{[^{}]*\}", "", text)      # drop variant readings
            text = re.sub(r"\s+", " ", text).strip()
            if n == 0:
                out[cur]["title"] = text
            else:
                out[cur]["verses"].append(text)
    return out


def tokens(s):
    return [t.strip(STRIP_PUNCT) for t in WORD.findall(s)
            if t.strip(STRIP_PUNCT)]


def key_acc(w):
    """Primary key: the accented form itself, lowercased. Most specific —
    accents disambiguate inflections that collapse when stripped."""
    return unicodedata.normalize("NFC", w).lower()


def key_cs(w):
    """Fallback key: accents stripped, lowercased. Collapses accent variants —
    broader coverage, but homographs can collide (hence the reliability bar)."""
    w = unicodedata.normalize("NFD", w)
    w = "".join(c for c in w if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", w).lower()


def aligned_pairs(pon, app_ps):
    """Yield (cs_verse, civil_verse) pairs, offset-aware.

    Where the asset numbers the superscription as verse 1 (Пс 3 etc.), the
    asset has one MORE verse than Ponomar's body — align body against
    app[1:]. First draft skipped those psalms entirely and lost ~1,000 pairs.
    """
    for p, entry in pon.items():
        if not (1 <= p <= len(app_ps)) or not app_ps[p - 1]:
            continue
        body, app = entry["verses"], app_ps[p - 1]
        if len(body) == len(app):
            yield from zip(body, app)
        elif len(body) + 1 == len(app) and TITLE_SHAPED.match(app[0]):
            # Numbered-title psalm: the asset's v1 IS the superscription the
            # civil digitization kept. Pair it with Ponomar's title — these
            # ~40 pairs teach exactly the title vocabulary («Ѱало́мъ дв҃дꙋ» ↔
            # «Псалом Давиду») that verse bodies rarely contain.
            if entry["title"]:
                yield (entry["title"], app[0])
            yield from zip(body, app[1:])
        elif len(body) == len(app) + 1:
            yield from zip(body[1:], app)


def build_dictionary(pon, app_ps):
    """Two-tier dictionaries: accented key (specific) + stripped key (broad)."""
    acc = defaultdict(Counter)
    strip = defaultdict(Counter)
    pairs = used = 0
    for cs_v, civ_v in aligned_pairs(pon, app_ps):
        civ_v = re.sub(r"\[[^\[\]]*\]", " ", civ_v)     # supplied words
        ct, vt = tokens(cs_v), tokens(civ_v)
        pairs += 1
        if len(ct) != len(vt) or not ct:
            continue
        used += 1
        for c, v in zip(ct, vt):
            acc[key_acc(c)][v] += 1
            strip[key_cs(c)][v] += 1
    return (acc, strip), pairs, used


# A word is RELIABLE only when the corpus is near-unanimous about its civil
# form. Accent-stripping can collapse two different inflections onto one key;
# naive majority vote then silently renders the minority form wrongly — the
# first draft scored only ~94% per word that way. Titles may only be built
# from reliable words; everything else goes to the owner's review bucket.
REL_MIN_COUNT = 2
REL_MIN_SHARE = 0.90


def _pick(counter, min_count, min_share):
    """Reliability on CASE-FOLDED identity; casing decided separately.

    Raw case-sensitive share testing silently disqualified the commonest
    words: «его»/«Его» (reverential capitalization, contextual) splits the
    counter below any share bar even though the word identity is unanimous.
    So: fold to lowercase for the reliability test, then capitalize only
    when the corpus capitalizes near-always (proper names, divine names).
    """
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
    """Accented tier first (specific), stripped tier as fallback (broad)."""
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


def validate(pon, app_ps, vocab):
    """Per-word accuracy of RELIABLE words over the aligned corpus."""
    ok = wrong = 0
    for cs_v, civ_v in aligned_pairs(pon, app_ps):
        civ_clean = re.sub(r"\[[^\[\]]*\]", " ", civ_v)
        ct, vt = tokens(cs_v), tokens(civ_clean)
        if len(ct) != len(vt) or not ct:
            continue
        for c, v in zip(ct, vt):
            form = reliable_form(vocab, c)
            if form is None:
                continue
            # Case-folded: diagnosis showed the residual mismatches are almost
            # entirely CONTEXTUAL CAPITALIZATION (sentence-initial «И» vs «и»,
            # reverential «Твоя» vs «твоя») — word identity, not word choice.
            # First-word casing is applied explicitly at title build time.
            if form.lower() == v.lower():
                ok += 1
            else:
                wrong += 1
    return ok, wrong


def holdout_title_test(pon, app_ps, vocab):
    """END-TO-END gate: rebuild each KNOWN title with its own pair held out.

    The ~40 numbered-title psalms give (Ponomar title, asset civil title)
    pairs. For each, subtract that pair's contribution from the dictionary,
    transliterate the Ponomar title, and compare against the asset's actual
    text. This tests exactly the transformation being shipped, on ground
    truth, without self-training leakage.
    """
    acc, strip = vocab
    results = []
    for p, entry in pon.items():
        if not entry["title"] or not (1 <= p <= len(app_ps)) or not app_ps[p - 1]:
            continue
        app = app_ps[p - 1]
        if not (len(entry["verses"]) + 1 == len(app) and TITLE_SHAPED.match(app[0])):
            continue
        ct, vt = tokens(entry["title"]), tokens(app[0])
        held = list(zip(ct, vt)) if len(ct) == len(vt) else []
        for c, v in held:                      # hold out
            acc[key_acc(c)][v] -= 1
            strip[key_cs(c)][v] -= 1
        rebuilt, missing = transliterate_title(entry["title"], vocab)
        for c, v in held:                      # restore
            acc[key_acc(c)][v] += 1
            strip[key_cs(c)][v] += 1
        want = re.sub(r"\s+", " ", app[0]).strip()
        got = rebuilt
        exact = (not missing and got.rstrip(".").lower() == want.rstrip(".").lower())
        results.append((p, exact, got, want, missing))
    return results


def transliterate_title(title, vocab):
    """Word-by-word via RELIABLE corpus forms, punctuation preserved.

    Returns (text, unresolved). Any unresolved word disqualifies the title
    from automatic application.
    """
    out, missing = [], []
    for raw in WORD.findall(title):
        core = raw.strip(STRIP_PUNCT)
        if not core:
            continue
        # Keep punctuation on BOTH sides: Ponomar parenthesizes the Alleluia
        # titles «(А҆ллилꙋ́їа.)»; dropping the lead paren produced «...⟩.).».
        lead = raw[:len(raw) - len(raw.lstrip(STRIP_PUNCT))]
        trail = raw[len(raw.rstrip(STRIP_PUNCT)):]
        form = reliable_form(vocab, core)
        if form is None:
            missing.append(core)
            out.append(f"{lead}⟨{core}⟩{trail}")
        else:
            out.append(lead + form + trail)
    text = " ".join(out)
    text = text[0].upper() + text[1:] if text else text
    # Ponomar titles trail a comma (they flow into v1 in print); the asset's
    # own surviving titles are period-terminated.
    text = text.rstrip(",")
    if text and text[-1] not in ".:]":   # ':' — Пс 17-style titles end mid-flow
        text += "."
    return text, missing


def fold(s):
    s = re.sub(r"\[[^\[\]]*\]", " ", s)
    s = re.sub(r"[^\w]", "", s, flags=re.U)
    return s.lower()


def apply_review(review_path):
    """Apply owner-reviewed titles from the review file's SUGGESTED lines.

    The owner (native reader) edits the SUGGESTED lines in place and approves;
    this reads them back and applies with the same safety rules. Any line
    still containing ⟨⟩ (unresolved titlo etc.) is skipped and reported.
    """
    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[PSALMS]["chapters"]
    counts = [len(c) for c in ps]

    text = open(review_path, encoding="utf-8").read()
    entries = re.findall(r"Пс (\d+)\n  raw      : .*\n  SUGGESTED: (.*)\n", text)
    applied, skipped = [], []
    for p_str, title in entries:
        p, title = int(p_str), title.strip()
        if "⟨" in title or not title:
            skipped.append((p, "unresolved ⟨⟩ or empty"))
            continue
        if not (1 <= p <= len(ps)) or not ps[p - 1]:
            skipped.append((p, "no such psalm"))
            continue
        v1 = ps[p - 1][0]
        if TITLE_SHAPED.match(v1) or fold_simple(v1).startswith(fold_simple(title)):
            skipped.append((p, "already titled"))
            continue
        ps[p - 1][0] = f"{title} {v1}"
        applied.append((p, title))

    print(f"apply-review: {len(applied)} applied, {len(skipped)} skipped")
    for p, t in applied:
        print(f"  Пс {p:>3} + «{t}»")
    for p, why in skipped:
        print(f"  Пс {p:>3} skipped ({why})")
    if not applied:
        return
    assert [len(c) for c in ps] == counts, "verse counts changed — refusing"
    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".prereview.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name} (backup: {backup.name})")


def fold_simple(s):
    return re.sub(r"[^\w]", "", s, flags=re.U).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply-review", metavar="FILE",
                    help="apply owner-edited SUGGESTED titles from the review file")
    args = ap.parse_args()

    if args.apply_review:
        apply_review(args.apply_review)
        return

    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[PSALMS]["chapters"]
    counts = [len(c) for c in ps]

    pon = parse_ponomar()
    n_titles = sum(1 for e in pon.values() if e["title"])
    print(f"Ponomar: {len(pon)} psalms, {n_titles} titles")

    vocab, pairs, used = build_dictionary(pon, ps)
    print(f"parallel corpus: {used}/{pairs} verse pairs aligned, "
          f"{len(vocab[1])} CS word forms learned")

    ok, wrong = validate(pon, ps, vocab)
    acc = ok / max(ok + wrong, 1)
    print(f"validation: reliable-word accuracy (case-folded) "
          f"{ok}/{ok+wrong} ({acc:.2%})")
    if acc < 0.98:
        sys.exit("reliable-word accuracy below 98% — refusing to transliterate")

    # THE GATE THAT MATTERS: silent errors. A hold-one-out miss caused by a
    # flagged singleton word (its ONLY attestation was the held-out pair) is
    # the review mechanism working. A miss with NO flag is the pipeline being
    # confidently wrong — the ru_stress failure mode — and forbids applying.
    ho = holdout_title_test(pon, ps, vocab)
    ho_ok = sum(1 for _, e, _, _, _ in ho if e)
    flagged = [r for r in ho if not r[1] and r[4]]

    def words_only(s):
        return re.sub(r"[^\w\s]", "", s, flags=re.U).lower().split()

    # Punctuation-only differences are WITNESS VARIANCE (Ponomar and the
    # asset punctuate a few titles differently, e.g. Пс 68's comma), not a
    # rendering error — the words are identical. Cosmetic, reported, safe.
    rest = [r for r in ho if not r[1] and not r[4]]
    punct_var = [r for r in rest if words_only(r[2]) == words_only(r[3])]
    silent = [r for r in rest if words_only(r[2]) != words_only(r[3])]
    print(f"hold-one-out TITLE test: {ho_ok}/{len(ho)} exact, "
          f"{len(flagged)} flagged-unknown (safe), "
          f"{len(punct_var)} punctuation-variance (cosmetic), "
          f"{len(silent)} SILENT-WRONG")
    for p, _e, got, want, _m in silent:
        print(f"    Пс {p:>3} SILENT MISS: got  «{got}»")
        print(f"                       want «{want}»")
    if silent:
        sys.exit("silent wrong renderings exist — refusing to apply")

    edits, review, skipped = [], [], []
    for p in sorted(pon):
        entry = pon[p]
        if not entry["title"] or not (1 <= p <= len(ps)) or not ps[p - 1]:
            continue
        v1 = ps[p - 1][0]
        if TITLE_SHAPED.match(v1):
            skipped.append((p, "v1 already an own-verse title"))
            continue
        title, missing = transliterate_title(entry["title"], vocab)
        # psalm-alignment gate: transliterated Ponomar v1 must match asset v1
        if entry["verses"]:
            pv1, _m = transliterate_title(entry["verses"][0], vocab)
            r = difflib.SequenceMatcher(None, fold(pv1), fold(v1),
                                        autojunk=False).ratio()
            if r < MIN_RATIO:
                skipped.append((p, f"v1 body mismatch r={r:.2f} — alignment "
                                   f"not trusted"))
                continue
        if fold(v1).startswith(fold(title)):
            skipped.append((p, "already titled"))
            continue
        if missing:
            review.append((p, title, missing))
            continue
        edits.append((p, title))

    print(f"\napply: {len(edits)}   REVIEW (unattested words): {len(review)}   "
          f"skipped: {len(skipped)}\n")
    for p, title in edits:
        print(f"  Пс {p:>3} + «{title}»")
    if review:
        print("\nREVIEW — held for the owner (words never seen in the corpus "
              "are ⟨bracketed⟩):")
        for p, title, missing in review:
            print(f"  Пс {p:>3}   «{title}»")
        # A review FILE with a char-map fallback rendering per title, so the
        # owner reads-and-blesses instead of transliterating from scratch.
        # The char map is MECHANICAL ONLY (letters + accents); it cannot
        # expand titlo abbreviations — those stay ⟨bracketed⟩ even here.
        CHAR = str.maketrans({"ѣ": "е", "Ѣ": "Е", "ѡ": "о", "Ѡ": "О",
                              "ѧ": "я", "Ѧ": "Я", "ꙗ": "я", "Ꙗ": "Я",
                              "ї": "и", "Ї": "И", "і": "и", "І": "И",
                              "ꙋ": "у", "Ꙋ": "У", "є": "е", "Є": "Е",
                              "ѕ": "з", "Ѕ": "З", "ѳ": "ф", "Ѳ": "Ф",
                              "ѻ": "о", "Ѻ": "О", "ѵ": "и", "Ѵ": "И"})

        def charmap(w):
            s = unicodedata.normalize("NFD", w)
            # Strip accents/breathings/titlos but NEVER U+0306 (breve): й is
            # и + breve under NFD, and stripping it turned «еврей» into
            # «евреи» in the first review file.
            s = "".join(c for c in s
                        if not unicodedata.combining(c) or c == "̆")
            s = unicodedata.normalize("NFC", s).translate(CHAR)
            s = s.replace("ᲂу", "у").replace("ᲂ", "")
            s = re.sub(r"ъ$", "", s)
            has_titlo = any("ⷠ" <= ch <= "ⷿ" or ch == "҃"
                            for ch in unicodedata.normalize("NFD", w))
            return f"⟨{w}⟩" if has_titlo else s

        rev_path = Path("C:/Projects/Hexapla-releases/cu_titles_review.txt")
        with open(rev_path, "w", encoding="utf-8") as rf:
            rf.write("Church Slavonic psalm titles — OWNER REVIEW\n")
            rf.write("=" * 60 + "\n")
            rf.write("Corpus-attested words are rendered from the parallel\n"
                     "corpus (validated 99.9%). ⟨Bracketed⟩ words were never\n"
                     "seen in the corpus; the SUGGESTED line renders them by\n"
                     "a mechanical letter map (accents stripped, ѣ→е etc.) —\n"
                     "titlo abbreviations cannot be char-mapped and remain\n"
                     "bracketed. Edit freely; reply with corrections or\n"
                     "approval, then run fix_cu_psalm_titles.py --apply-review\n"
                     "with the edited file.\n\n")
            for p, title, missing in review:
                sug = re.sub(r"⟨([^⟨⟩]*)⟩",
                             lambda m: charmap(m.group(1)), title)
                rf.write(f"Пс {p}\n  raw      : {title}\n"
                         f"  SUGGESTED: {sug}\n\n")
        print(f"\n  review file with suggestions: {rev_path}")
    if skipped:
        print(f"\nskipped: " + ", ".join(f"Пс {p} ({why})" for p, why in skipped[:12]))

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    if not edits:
        print("nothing to apply")
        return

    for p, title in edits:
        old = ps[p - 1][0]
        new = f"{title} {old}"
        assert new.endswith(old)
        ps[p - 1][0] = new
    assert [len(c) for c in ps] == counts, "verse counts changed — refusing"

    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".pretitles.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"\nbackup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}: {len(edits)} titles restored, "
          f"{len(review)} held for review, verse counts unchanged")


if __name__ == "__main__":
    main()
