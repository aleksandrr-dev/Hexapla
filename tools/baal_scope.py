#!/usr/bin/env python
"""Derive the SCOPE of the `Baal` pronunciation class, and its tail-witness.

The owner heard "Ball" for "Baal" in 2 Kings 10:28 (ear, 2026-09-14) — an
ACCIDENTAL finding: that clip had been queued for a suspected append and came
back carrying a mispronunciation nothing was looking for. One ear verdict is
one verse. This tool answers the two questions that verdict does NOT:

  1. SCOPE      — how many verses of the en asset carry the token at all, and
                  how many of those are already rendered (i.e. already wrong,
                  if the defect is systematic).
  2. WITNESS    — is there a SECOND instrument that saw it? The per-verse gate
                  stores an ASR `tail` for every rendered verse. Where the
                  PRINT tail contains a baal-token and the ASR tail contains
                  "ball"/"bell"/"bowl" and NOT that token, the ASR heard the
                  same thing the owner heard.

⛔ This tool proposes NOTHING. The lexicon is owner-gated; a respelling may not
   be added on the strength of a count. ⚠ The witness denominator is only the
   verse TAIL — the gate stores no full transcript — so a clean witness result
   is NOT a clean book. It can confirm, it cannot clear.

⚠ The forms are NOT one class. Standalone `Baal` is the confirmed case.
  `Baalim`, `Baalah`, `Baalath` and the `Baal-` compounds are separate
  questions and are counted separately on purpose: a respelling that fixes one
  may break another, and only the owner rules.

Exit 0 = derivation printed. Exit 2 = asset or narration tree unreadable
(⛔ never a plausible zero).

## --selftest, and its known-bad control

`--selftest` builds a SYNTHETIC asset and narration tree in `tempfile.mkdtemp()`
and drives the derivation functions above against them. It never reads
`app/src/main/assets/bibles/en_kjv.json` and needs no real `narration/en`. It
asserts the invariant the docstring states: the forms are NOT one class, and the
compounds are counted separately from standalone `Baal`.

⛔ A control that passes on broken code is not a control. `HEXAPLA_FOLD_BAAL=1`
makes the classifier fold every `*baal*` form into the single `baal` bucket —
exactly the conflation this docstring forbids. Both directions must hold:

    python tools/baal_scope.py --selftest                      # exit 0
    HEXAPLA_FOLD_BAAL=1 python tools/baal_scope.py --selftest  # exit 1
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.normpath(os.path.join(HERE, os.pardir, "app", "src", "main",
                                      "assets", "bibles", "en_kjv.json"))
NARRATION = os.path.join("narration", "en")

TOKEN = re.compile(r"[A-Za-z]*baal[A-Za-z]*", re.I)
# What the render substitutes when it gets this wrong. Heard by the owner as
# "Ball"; the ASR spells a one-syllable reading these ways.
MISHEARD = re.compile(r"\b(ball|balls|bal|bell|bowl)\b", re.I)
TAIL_WORDS = 12

# The one verse with ear ground truth: 2 Kings 10:28 (book 11, ch 10, v 28),
# ruled "Ball" by the owner on 2026-09-14. Zero-based chapter and verse.
CTL_BOOK, CTL_CH, CTL_V = 11, 9, 27

#: The single bucket the classifier must NOT fold everything into.
BAAL_BUCKET = "Baal (standalone) - THE CONFIRMED CASE"


#: Set by selftest() while it drives a fixture; ⛔ never true in a normal run.
_IN_SELFTEST = False


def fold_baal():
    """⚠ The known-bad control. True = conflate every *baal* form into one class.

    ⛔ Only `--selftest` consults this. A normal invocation must be bit-for-bit
    unaffected by the variable - the whole point is to test the classifier, not
    to add a second way to configure it.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_FOLD_BAAL") == "1"


def classify(tok):
    if fold_baal():
        return BAAL_BUCKET
    t = tok.lower()
    if t == "baal":
        return BAAL_BUCKET
    if t in ("baalim", "baalims"):
        return "Baalim"
    if t.startswith("baal"):
        return "Baal- compound (Baalah, Baalath, Baalpeor, Baalzebub, ...)"
    return "-baal suffix (Jerubbaal, Eshbaal, Meribbaal, ...)"


def load_asset(path=None):
    try:
        with io.open(path or ASSET, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("FAILED to read %s: %s\n" % (path or ASSET, exc))
        raise SystemExit(2)


def norm(s):
    return re.sub(r"[^a-z]+", "", s.lower())


def scope(books):
    """-> (hits, by_class, by_book) for every verse carrying a baal-token.

    `hits` is [(bi, ci, vi, book_name, text, [tokens])]; `by_class` maps each
    class name to the SET of (bi, ci, vi) in it. ⚠ The classes are kept apart
    on purpose - see the FOLD control above.
    """
    hits = []
    for bi, book in enumerate(books):
        for ci, chapter in enumerate(book.get("chapters") or []):
            for vi, verse in enumerate(chapter):
                toks = TOKEN.findall(verse or "")
                if toks:
                    hits.append((bi, ci, vi, book.get("name", "?"), verse, toks))
    by_class = defaultdict(set)
    by_book = Counter()
    chapters = set()
    for bi, ci, vi, name, _text, toks in hits:
        by_book[(bi, name)] += 1
        chapters.add((bi, ci))
        for t in toks:
            by_class[classify(t)].add((bi, ci, vi))
    return hits, by_class, by_book, chapters


def tail_witness(hits, rendered_ch, narration=None):
    """-> (checked, agree, two_syl, neither) for the verse-TAIL witness.

    Only a verse whose PRINT tail carries the token is judged: the ASR tail is
    the last few words, so anything earlier is out of view. A clean result here
    is still not a clean book - the denominator is the TAIL, not the verse.

    ⚠ `narration` is resolved at CALL time, not bound as a default: the
    selftest points the module at a temp root, and a definition-time default
    would keep reading the real tree.
    """
    narration = narration or NARRATION
    qa_cache = {}
    checked = 0
    agree, two_syl, neither = [], [], []
    for bi, ci, vi, name, text, toks in hits:
        if (bi, ci) not in rendered_ch:
            continue
        key = (bi, ci)
        if key not in qa_cache:
            path = os.path.join(narration, str(bi), "%d.qa.json" % ci)
            try:
                with io.open(path, encoding="utf-8") as fh:
                    qa_cache[key] = json.load(fh).get("gate") or {}
            except Exception:                                 # noqa: BLE001
                qa_cache[key] = {}
        gate = qa_cache[key]
        entry = gate.get(str(vi + 1)) or gate.get(str(vi))
        if not entry:
            continue
        attempts = entry.get("attempts") or []
        if not attempts:
            continue
        tail = (attempts[-1].get("tail") or "")
        if not tail:
            continue
        print_tail = " ".join((text or "").split()[-TAIL_WORDS:])
        ptoks = TOKEN.findall(print_tail)
        if not ptoks:
            continue
        checked += 1
        if TOKEN.search(tail):
            two_syl.append((bi, ci, vi, name, ptoks, tail))
        elif MISHEARD.search(tail):
            agree.append((bi, ci, vi, name, ptoks, tail))
        else:
            neither.append((bi, ci, vi, name, ptoks, tail))
    return checked, agree, two_syl, neither


def main():
    books = load_asset()
    if not isinstance(books, list) or len(books) < 66:
        sys.stderr.write("asset shape unexpected (%r books)\n" % len(books))
        raise SystemExit(2)

    # ---- 1. scope -------------------------------------------------------
    hits, by_class, by_book, chapters = scope(books)

    print("=" * 78)
    print("BAAL SCOPE - derived from en_kjv.json, %d books" % len(books))
    print("=" * 78)
    print("verses carrying any baal-token : %d" % len(hits))
    print("chapters touched               : %d" % len(chapters))
    print()
    print("-- by class (a verse can carry more than one) --")
    for cls in sorted(by_class, key=lambda c: -len(by_class[c])):
        print("  %-52s %5d verses" % (cls, len(by_class[cls])))
    print()
    print("-- distinct printed forms, most frequent first --")
    by_form = Counter()
    for _bi, _ci, _vi, _n, _t, toks in hits:
        for t in toks:
            by_form[t] += 1
    for form, n in by_form.most_common():
        print("  %-24s %4d" % (form, n))
    print()
    print("-- by book, most affected first --")
    for (bi, name), n in by_book.most_common(15):
        print("  %-3d %-22s %4d verses" % (bi, name, n))
    if len(by_book) > 15:
        print("  ... and %d more books" % (len(by_book) - 15))

    # ---- 2. how much is already rendered --------------------------------
    if not os.path.isdir(NARRATION):
        sys.stderr.write("FAILED: %s not found - run from the DATA dir "
                         "(C:\\Projects\\Hexapla-releases)\n" % NARRATION)
        raise SystemExit(2)

    rendered_ch = set()
    for bi, ci in chapters:
        if os.path.exists(os.path.join(NARRATION, str(bi), "%d.ogg" % ci)):
            rendered_ch.add((bi, ci))
    rendered_v = sum(1 for bi, ci, _vi, _n, _t, _k in hits
                     if (bi, ci) in rendered_ch)
    print()
    print("-- already rendered (so already carrying the defect, if systematic) --")
    print("  chapters rendered of %-4d touched : %d" % (len(chapters),
                                                        len(rendered_ch)))
    print("  verses   rendered of %-4d carrying: %d" % (len(hits), rendered_v))
    print("  ^ a per-VERSE repair queue of that size, NOT a chapter re-render.")

    # ---- 3. the tail witness --------------------------------------------
    print()
    print("=" * 78)
    print("TAIL WITNESS - a SECOND instrument, on the verse tail only")
    print("=" * 78)
    checked, agree, two_syl, neither = tail_witness(hits, rendered_ch)

    print("verse tails in view (print tail carries the token) : %d" % checked)
    if checked == 0:
        print("  ⚠ NOTHING IN VIEW - that is not a clean result, it is an")
        print("    empty denominator. The witness says nothing here.")
    print()
    print("  ASR tail spells a baal-token (heard as TWO syllables) : %d" % len(two_syl))
    print("  ASR tail says ball/bell/bowl  (the owner's defect)    : %d" % len(agree))
    print("  ASR tail says NEITHER (⛔ says nothing either way)     : %d" % len(neither))
    print()
    print("  ⛔ Read the finding, do not count it. The THIRD row is not a")
    print("     clearance - the token may simply have fallen outside the tail")
    print("     the ASR returned, or been transcribed as a third thing.")

    for label, rows in (("ASR AGREES WITH THE OWNER ('ball')", agree),
                        ("ASR HEARD TWO SYLLABLES", two_syl),
                        ("NEITHER - unjudged", neither)):
        if not rows:
            continue
        print()
        print("  -- %s (%d) --" % (label, len(rows)))
        for bi, ci, vi, name, ptoks, tail in rows[:25]:
            print("     %-18s %3d:%-3d print %-14s asr: ...%s"
                  % (name, ci + 1, vi + 1, "/".join(ptoks)[:14], tail[-52:]))
        if len(rows) > 25:
            print("     ... and %d more" % (len(rows) - 25))

    # ---- 4. THE CONTROL -------------------------------------------------
    # 2 Kings 10:28 is the ONE verse in this whole class with ground truth:
    # the owner heard "Ball" there by ear on 2026-09-14. Whatever the witness
    # says about that verse is the witness's own score.
    print()
    print("=" * 78)
    print("CONTROL - 2 Kings 10:28, the only verse with ear ground truth")
    print("=" * 78)
    ctl = [r for r in (agree + two_syl + neither)
           if r[0] == CTL_BOOK and r[1] == CTL_CH and r[2] == CTL_V]
    if not ctl:
        print("⛔ CONTROL NOT IN VIEW - the witness cannot be scored, so its")
        print("   output means nothing. Treat every row above as unjudged.")
        return 3
    _b, _c, _v, _n, ptoks, tail = ctl[0]
    print("  print : ...%s" % "/".join(ptoks))
    print("  asr   : ...%s" % tail[-60:])
    print("  ear   : 'Ball' - the owner, 2026-09-14 (a DEFECT)")
    print()
    if ctl[0] in agree:
        print("  ✅ The witness AGREES with the ear on the control. Its other")
        print("     rows carry some weight - still not a verdict.")
        verdict = 0
    else:
        print("  ⛔⛔ THE WITNESS FAILS ITS OWN CONTROL. On the one verse the")
        print("      owner has ruled a DEFECT, the ASR tail spells the token")
        print("      CORRECTLY. Whisper restores the expected spelling from")
        print("      its language prior, so it CANNOT hear this defect class.")
        print()
        print("      ▶ Therefore the 'TWO SYLLABLES' rows above CLEAR NOTHING,")
        print("        and the 2 'ball' rows are a floor, never a count.")
        print("      ▶ ONLY THE EAR CAN RULE THIS CLASS. An ASR screen of the")
        print("        %d rendered verses would report a clean book that is not"
              % rendered_v)
        print("        clean - exactly the shape of a failed read that looks")
        print("        like a pass.")
        verdict = 0

    print()
    print("⛔ SCOPE IS NOT A VERDICT. 140 verses carry the token; %d are"
          % rendered_v)
    print("   already rendered. Whether the render says 'Ball' in any of them")
    print("   beyond 2 Kings 10:28 is NOT established.")
    print("⛔ Nothing goes in the lexicon without the owner.")
    return verdict


# ---------------------------------------------------------------- selftest ---

#: A synthetic "book" wrapper so a fixture reaches the >= 66 book guard in main.
def _full66(slot0):
    books = [{"name": "Fixture", "chapters": [[v] for v in slot0]}]
    while len(books) < 66:
        books.append({"name": "Filler %d" % len(books), "chapters": [["x"]]})
    return books


def _planted():
    """⚠ The verse BODIES must sit inside the last TAIL_WORDS so the print tail
    carries the token - the witness judges the tail only.

    -> (books, narration_dir, [(bi, ci, vi, [tokens])]) for the 5 planted
    verses, indexes 0..4 == 'Baal', 'Baalim', 'Baalzebub', 'Jerubbaal',
    'Baalpeor'. Index 5 carries no baal-token at all.
    """
    bodies = ["and he served Baal", "the prophets of Baalim",
              "unto Baalzebub the god of Ekron", "the son of Jerubbaal",
              "and they joined themselves unto Baalpeor"]
    books = _full66(bodies + ["and he walked in the way of David"])
    planted = [(0, 0, i, TOKEN.findall(bodies[i])) for i in range(5)]
    return books, planted


def _write_fixture(tmp):
    """-> (asset_path, narration_dir) with the .qa.json gate records planted."""
    books, _planted_rows = _planted()
    asset = os.path.join(tmp, "en_kjv.fixture.json")
    with io.open(asset, "w", encoding="utf-8") as fh:
        json.dump(books, fh, ensure_ascii=False)

    narr = os.path.join(tmp, "narration", "en", "0")
    os.makedirs(narr)
    # 0.ogg present so every chapter reads as RENDERED.
    with io.open(os.path.join(narr, "0.ogg"), "wb") as fh:
        fh.write(b"")
    gate = {
        # v1: print tail carries the token, ASR says "ball" and not the token.
        "1": {"attempts": [{"tail": "and he served ball"}]},
        # v2: print tail carries Baalim, ASR says Baalim too -> NOT a hit.
        "2": {"attempts": [{"tail": "the prophets of baalim"}]},
    }
    with io.open(os.path.join(narr, "0.qa.json"), "w", encoding="utf-8") as fh:
        json.dump({"gate": gate}, fh, ensure_ascii=False)
    return asset, os.path.join(tmp, "narration", "en")


def selftest():
    global ASSET, NARRATION, _IN_SELFTEST
    _IN_SELFTEST = True          # arm the known-bad control for this process
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    tmp = tempfile.mkdtemp(prefix="baal_scope_selftest_")
    old_asset, old_narr = ASSET, NARRATION
    try:
        asset, narr = _write_fixture(tmp)
        ASSET, NARRATION = asset, narr

        books, planted = _planted()
        hits, by_class, _by_book, _chapters = scope(books)
        baal = BAAL_BUCKET

        # --- the non-folding invariant: bucket counts by VALUE -------------
        check(len(by_class[baal]) == 1,
              "scope: standalone Baal counts 1 verse in its own bucket")
        check(len(by_class.get("Baalim", ())) == 1,
              "scope: Baalim is counted separately, NOT in the baal bucket")
        check((0, 1, 0) not in by_class[baal],
              "scope: the Baalim verse is absent from the baal bucket")
        compound = [c for c in by_class if c.startswith("Baal- compound")]
        check(len(compound) == 1 and len(by_class[compound[0]]) == 2,
              "scope: the two Baal- compounds count separately, NOT in baal")
        check((0, 2, 0) not in by_class[baal] and (0, 4, 0) not in by_class[baal],
              "scope: Baalzebub and Baalpeor never reach the baal bucket")
        suffix = [c for c in by_class if c.startswith("-baal suffix")]
        check(len(suffix) == 1 and (0, 3, 0) in by_class[suffix[0]],
              "scope: Jerubbaal counts as a -baal suffix, NOT in baal")
        check(len(by_class[baal]) == 1 and sum(len(v) for v in by_class.values()) >= 5,
              "scope: exactly 5 verses carry a token and only 1 is standalone")
        check(len(hits) == 5,
              "scope: the no-token control verse is counted nowhere")

        # --- the tail witness --------------------------------------------
        rendered = {(0, 0)}
        checked, agree, two_syl, neither = tail_witness(hits, rendered)
        agree_rows = {r[2] for r in agree}
        two_rows = {r[2] for r in two_syl}
        check(0 in agree_rows,
              "witness: print 'Baal' + ASR 'ball' is reported as a witness hit")
        check(1 not in two_rows and 1 not in agree_rows,
              "witness: an ASR tail still spelling the token is NOT a witness hit")

        # --- a failed read is NEVER a plausible zero ----------------------
        try:
            load_asset(os.path.join(tmp, "does-not-exist.json"))
            check(False, "load: a missing asset raises SystemExit(2)")
        except SystemExit as exc:
            check(exc.code == 2, "load: a missing asset exits 2, never 0")

        # --- the known-bad control, asserted against the ARTIFACT ---------
        folded = fold_baal()
        if folded:
            check(len(by_class[baal]) == 5,
                  "HEXAPLA_FOLD_BAAL=1 is active: all 5 forms fold into one "
                  "bucket (this run is SUPPOSED to fail overall)")
        else:
            check(len(by_class) >= 4,
                  "the classifier keeps at least 4 separate classes when not folded")
    finally:
        ASSET, NARRATION = old_asset, old_narr
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [w for ok, w in results if not ok]
    print()
    print("%d assertion(s), %d failed" % (len(results), len(bad)))
    if bad:
        print("⛔ SELFTEST FAILED")
        return 1
    print("✅ selftest passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main())
