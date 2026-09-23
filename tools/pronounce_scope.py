#!/usr/bin/env python
"""Scope the ELEVEN open pronunciation items, and score the ASR against them.

    python tools/pronounce_scope.py                 # all items
    python tools/pronounce_scope.py --item baal     # one
    python tools/pronounce_scope.py --control       # score the ASR only

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## Why this exists

Eleven proper nouns are open on the render, and **eight have never been shown
to the owner**. The handoff's standing instruction is «the next step is
EVIDENCE, not an edit»: this tool produces the evidence — for each item, how
many verses of the asset carry the token, how many are ALREADY RENDERED, and
what the gate's stored ASR tail says where it can see the token at all.

⛔ **IT PROPOSES NOTHING.** The pronunciation lexicon is owner-gated. A
respelling may not be added on the strength of a count, and this tool prints no
candidate respelling on purpose.

## ⛔⛔ THE ASR IS MEASURED UNFIT FOR THIS ENTIRE CLASS

`baal` carries the only ear ground truth in the set: the owner ruled **2 Kings
10:28 a DEFECT** («Ball instead of Baal», 2026-09-14). The gate's stored ASR
tail for that exact verse reads `...thus jehu destroyed baal out of israel` —
**the ASR spelled it CORRECTLY on the one verse the owner heard wrong.**

Whisper restores the expected spelling of a proper noun from its language
prior. Every one of the eleven items IS a proper noun, so the ASR manufactures
agreement with the print across the whole class. It can CONFIRM a defect
(when it breaks down anyway) and it can NEVER CLEAR one.

▶ `--control` prints exactly that, and the tool exits **3** if the control
verse is not in view — a witness that cannot be scored must report nothing
rather than a plausible zero. ⛔ Do not widen `heard` until the control passes:
**don't tune a threshold after seeing the cases.**

⚠ A carrier-phrase clearance is NOT a clearance — `Aybraham` passed a carrier
and then failed a real verse. Validate any candidate in a REAL VERSE.
⚠ Repair is per VERSE (`repair_verses.py`), never a chapter `--force`.

Exit 0 = derivation printed · 2 = asset/narration unreadable · 3 = the ASR
control was not in view (⛔ never a plausible zero).

## --selftest, and its known-bad control

    python tools/pronounce_scope.py --selftest      # run from the DATA dir

It asserts the two things that would silently corrupt this evidence: the
COMPOUND NON-FOLDING in the patterns (`\\bbaal\\b` must not match Baalzebub -
a respelling that fixes one may break the other), and the exit-3 contract
above, checked end-to-end by re-running this tool as a subprocess.

⛔ A control that passes on broken code is not a control. `HEXAPLA_SOFT_CONTROL=1`
makes the control-not-in-view path return 0 instead of 3 - the exact «plausible
zero» this project keeps getting bitten by, and here it would make every
`spelled-correct` figure read as a clearance. Both directions must hold:

    python tools/pronounce_scope.py --selftest                       # exit 0
    HEXAPLA_SOFT_CONTROL=1 python tools/pronounce_scope.py --selftest # exit 1
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(HERE, os.pardir, "app", "src", "main", "assets",
                     "bibles", "en_kjv.json")
NARRATION = os.path.join("narration", "en")
TAIL_WORDS = 12

# The eleven open items. `heard` is what the OWNER or the gate's ASR actually
# reported — ⛔ never a proposed correction, and ⛔ never widened to make a
# result look cleaner. `source` records who raised it, because a QUESTION and a
# VERDICT are not the same thing and must not be merged.
#
# ⚠ `pattern` matches the PRINTED form. Compounds are deliberately NOT folded
# into their base token: `Baalzebub` is a separate question from `Baal`, and a
# respelling that fixes one may break the other.
ITEMS = [
    dict(key="baal", pattern=r"\bbaal\b", label="Baal",
         heard=["ball", "balls", "bal", "bell", "bowl"],
         source="OWNER — VERDICT: a defect (2 Kings 10:28, 2026-09-14)",
         note="The only item with ear ground truth. Its compounds "
              "(Baalzebub, Jerubbaal, Baalim, Baalpeor ...) are SEPARATE "
              "questions and are not counted here — see baal_scope.py."),
    dict(key="mizpeh", pattern=r"\bmizpeh\b", label="Mizpeh",
         heard=["mice pea", "mice pee", "mispee", "mice"],
         source="OWNER — VERDICT: clearly wrong («mice pea»)",
         note="He was unambiguous that this one is wrong."),
    dict(key="keilah", pattern=r"\bkeilah\b", label="Keilah",
         heard=["keelah", "kayla", "kyla", "kee lah"],
         source="OWNER — QUESTION, not a verdict",
         note="⛔ He raised it as a question. Do not record it as a defect."),
    dict(key="jebusite", pattern=r"\bjebusites?\b", label="Jebusite(s)",
         heard=["jebbusite", "jeb you site", "jebusight"],
         source="OWNER — QUESTION, not a verdict",
         note="⛔ He raised it as a question. Do not record it as a defect."),
    dict(key="ramothgilead", pattern=r"\bramoth-?gilead\b",
         label="Ramothgilead",
         heard=["ramath galad", "ramoth galad", "galad", "ramath"],
         source="GATE (book 11, 2 flags: 2 Kings 9:1 and 9:4)",
         note="⚠ HE HAS HEARD BOTH AND DID NOT FLAG THEM (clips 2 and 6 of "
              "the 14b kit came back CLEAN). ⛔ Present as evidence, not as a "
              "defect — silence on a clip is not a clearance, but it is "
              "certainly not a confirmation."),
    dict(key="gathhepher", pattern=r"\bgath-?hepher\b", label="Gathhepher",
         heard=["gath heper", "gath hippur", "heper", "hippur"],
         source="GATE (book 11)",
         note="⚠ Heard on the 14b kit, not flagged."),
    dict(key="pharaohnechoh", pattern=r"\bpharaoh-?nechoh?\b",
         label="Pharaohnechoh",
         heard=["necho", "on ocho", "nachos", "nacho"],
         source="GATE (book 11, 3 variants)",
         note="⚠ Three DIFFERENT readings of one printed word — the render is "
              "not even self-consistent here. ⚠ Heard, not flagged."),
    dict(key="jecholiah", pattern=r"\bjecholiah\b", label="Jecholiah",
         heard=["jekylliah", "jekyliah", "jekyll"],
         source="GATE (book 11)",
         note="⚠ Heard on the 14b kit, not flagged."),
]

# Ground truth: 2 Kings 10:28 — book 11, chapter index 9, verse index 27
# (zero-based). Owner ruled it a DEFECT by ear, 2026-09-14.
CTL = (11, 9, 27, "baal")


def load_asset():
    try:
        with io.open(ASSET, encoding="utf-8") as fh:
            books = json.load(fh)
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("FAILED to read %s: %s\n" % (ASSET, exc))
        raise SystemExit(2)
    if not isinstance(books, list) or len(books) < 66:
        sys.stderr.write("asset shape unexpected\n")
        raise SystemExit(2)
    return books


def heard_re(item):
    return re.compile(r"\b(" + "|".join(re.escape(h) for h in item["heard"])
                      + r")\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", help="only this key (e.g. baal)")
    ap.add_argument("--control", action="store_true",
                    help="print only the ASR control and exit")
    a = ap.parse_args()

    books = load_asset()
    if not os.path.isdir(NARRATION):
        sys.stderr.write("FAILED: %s not found — run from the DATA dir "
                         "(C:\\Projects\\Hexapla-releases)\n" % NARRATION)
        raise SystemExit(2)

    items = [i for i in ITEMS if not a.item or i["key"] == a.item]
    if not items:
        sys.exit("no such item: %s (have: %s)"
                 % (a.item, ", ".join(i["key"] for i in ITEMS)))

    qa_cache = {}

    def gate_tail(bi, ci, vi):
        key = (bi, ci)
        if key not in qa_cache:
            path = os.path.join(NARRATION, str(bi), "%d.qa.json" % ci)
            try:
                with io.open(path, encoding="utf-8") as fh:
                    qa_cache[key] = json.load(fh).get("gate") or {}
            except Exception:                                 # noqa: BLE001
                qa_cache[key] = {}
        entry = qa_cache[key].get(str(vi + 1)) or qa_cache[key].get(str(vi))
        if not entry:
            return None
        att = entry.get("attempts") or []
        return (att[-1].get("tail") or "") if att else None

    ctl_row = None
    print("=" * 78)
    print("OPEN PRONUNCIATION ITEMS — scope derived from en_kjv.json")
    print("=" * 78)
    print("⛔ SCOPE IS EXPOSURE, NOT A DEFECT COUNT. Only an ear rules.")
    print()

    grand = Counter()
    for item in items:
        pat = re.compile(item["pattern"], re.I)
        hre = heard_re(item)
        hits = []
        for bi, book in enumerate(books):
            for ci, chapter in enumerate(book.get("chapters") or []):
                for vi, verse in enumerate(chapter):
                    if pat.search(verse or ""):
                        hits.append((bi, ci, vi, book.get("name", "?"), verse))

        rendered = [h for h in hits
                    if os.path.exists(os.path.join(NARRATION, str(h[0]),
                                                   "%d.ogg" % h[1]))]
        by_book = Counter((h[3]) for h in hits)

        # tail witness, three ways
        seen = agree = correct = neither = 0
        agree_rows = []
        for bi, ci, vi, name, text in rendered:
            tail = gate_tail(bi, ci, vi)
            if not tail:
                continue
            print_tail = " ".join((text or "").split()[-TAIL_WORDS:])
            if not pat.search(print_tail):
                continue
            seen += 1
            if pat.search(tail):
                correct += 1
            elif hre.search(tail):
                agree += 1
                agree_rows.append((name, ci + 1, vi + 1, tail))
            else:
                neither += 1
            if (bi, ci, vi, item["key"]) == CTL:
                ctl_row = (item, tail, "correct" if pat.search(tail)
                           else ("agree" if hre.search(tail) else "neither"))

        grand["verses"] += len(hits)
        grand["rendered"] += len(rendered)

        print("-" * 78)
        print("%-16s %s" % (item["label"].upper(), item["source"]))
        print("-" * 78)
        print("  heard as        : %s" % ", ".join('"%s"' % h
                                                   for h in item["heard"]))
        print("  verses in asset : %-5d  ALREADY RENDERED: %d"
              % (len(hits), len(rendered)))
        if by_book:
            top = ", ".join("%s %d" % (n, c) for n, c in by_book.most_common(6))
            print("  books           : %s%s"
                  % (top, " ..." if len(by_book) > 6 else ""))
        print("  ASR tails in view: %-4d  spelled-correct %-4d  heard-wrong %-3d"
              "  neither %d" % (seen, correct, agree, neither))
        if seen == 0:
            print("     ⚠ NOTHING IN VIEW — an empty denominator, not a pass.")
        for name, c, v, tail in agree_rows[:6]:
            print("     ⚠ %s %d:%d  asr: ...%s" % (name, c, v, tail[-50:]))
        if len(agree_rows) > 6:
            print("     ... and %d more" % (len(agree_rows) - 6))
        print("  note: %s" % item["note"])
        print()

    print("=" * 78)
    print("TOTAL EXPOSURE across the items shown: %d verses, %d already "
          "rendered" % (grand["verses"], grand["rendered"]))
    print("  ^ a per-VERSE repair ceiling. ⛔ NOT a defect count.")

    # ---- the control ----------------------------------------------------
    print()
    print("=" * 78)
    print("CONTROL — 2 Kings 10:28, the ONLY ear ground truth in the set")
    print("=" * 78)
    if ctl_row is None:
        print("⛔ CONTROL NOT IN VIEW — the ASR witness cannot be scored, so")
        print("   every 'spelled-correct' figure above means NOTHING.")
        print("   (Run without --item, or with --item baal, to see it.)")
        # ⚠ A witness that cannot be scored reports NOTHING, never a plausible
        # zero. HEXAPLA_SOFT_CONTROL is the known-bad control for exactly this
        # line and must never be set outside --selftest.
        return 0 if os.environ.get("HEXAPLA_SOFT_CONTROL") == "1" else 3
    item, tail, verdict = ctl_row
    print("  print : Baal")
    print("  asr   : ...%s" % tail[-60:])
    print("  ear   : 'Ball' — the owner, 2026-09-14 (a DEFECT)")
    print()
    if verdict == "agree":
        print("  ✅ The ASR agreed with the ear here. Its other rows carry")
        print("     some weight — still never a verdict.")
    else:
        print("  ⛔⛔ THE ASR FAILS ITS OWN CONTROL (it said '%s')." % verdict)
        print("      On the one verse the owner ruled a DEFECT, the ASR tail")
        print("      spells the token CORRECTLY. Whisper restores a proper")
        print("      noun's expected spelling from its language prior.")
        print()
        print("      ▶ EVERY 'spelled-correct' COUNT ABOVE CLEARS NOTHING.")
        print("      ▶ Every item here is a proper noun, so this unfitness")
        print("        applies to ALL ELEVEN, not just Baal.")
        print("      ▶ ONLY THE EAR CAN RULE THIS CLASS.")
    print()
    print("⛔ Nothing goes in the lexicon without the owner.")
    print("⚠ Three of these are HIS (Mizpeh a verdict; Keilah and Jebusite")
    print("  QUESTIONS). Baal is his verdict. The remaining four are GATE")
    print("  findings he has heard WITHOUT flagging — evidence, not defects.")
    return 0


# ---------------------------------------------------------------- selftest ---

def selftest():
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    by_key = {i["key"]: i for i in ITEMS}

    # -- COMPOUND NON-FOLDING: the documented invariant -------------------
    baal = re.compile(by_key["baal"]["pattern"], re.I)
    check(bool(baal.search("and served Baal")), "baal: matches the bare token")
    check(bool(baal.search("altar of baal.")),
          "baal: matches with trailing punctuation")
    check(not baal.search("Baalzebub the god of Ekron"),
          "baal: does NOT match Baalzebub - compounds are SEPARATE questions")
    check(not baal.search("the prophets of Baalim"),
          "baal: does NOT match Baalim")
    check(not baal.search("Jerubbaal his father"),
          "baal: does NOT match Jerubbaal")
    check(not baal.search("Baalpeor"), "baal: does NOT match Baalpeor")

    # -- the other patterns behave as documented --------------------------
    jeb = re.compile(by_key["jebusite"]["pattern"], re.I)
    check(bool(jeb.search("the Jebusite")) and bool(jeb.search("the Jebusites")),
          "jebusite: matches singular AND plural")
    rg = re.compile(by_key["ramothgilead"]["pattern"], re.I)
    check(bool(rg.search("Ramothgilead")) and bool(rg.search("Ramoth-gilead")),
          "ramothgilead: matches the hyphenated and unhyphenated print")
    pn = re.compile(by_key["pharaohnechoh"]["pattern"], re.I)
    check(bool(pn.search("Pharaohnechoh")) and bool(pn.search("Pharaoh-necho")),
          "pharaohnechoh: matches all three printed forms")

    # -- heard_re(): a word-boundary alternation, never a substring --------
    hre = heard_re(by_key["baal"])
    check(bool(hre.search("destroyed ball out of israel")),
          "heard_re: matches a listed mis-hearing")
    check(bool(hre.search("destroyed BALL")), "heard_re: is case-insensitive")
    check(not hre.search("football stadium"),
          "heard_re: does NOT match inside another word (word boundary)")
    check(not hre.search("baal out of israel"),
          "heard_re: the CORRECT spelling is not a mis-hearing")

    # -- the CTL anchor must resolve to 2 Kings 10:28 ---------------------
    # ⚠ Asserted against the REAL asset: if the book order or the zero-based
    # address ever shifts, every control verdict below would be scored on the
    # wrong verse.
    try:
        books = load_asset()
    except SystemExit:
        books = None
    if books is None:
        check(False, "CTL anchor: the asset could not be read - THIS CHECK "
                     "DID NOT RUN, which is not a pass")
    else:
        bi, ci, vi, key = CTL
        name = (books[bi].get("name") or "").lower()
        text = books[bi]["chapters"][ci][vi]
        check("kings" in name, "CTL anchor: book index 11 is Kings (got %r)" % name)
        check(key == "baal" and "baal" in (text or "").lower(),
              "CTL anchor: 11/9/27 is a verse containing 'baal' (2 Kings 10:28)")

    # -- THE EXIT CONTRACT, end to end against the ARTIFACT ---------------
    # ⛔ Asserted by RUNNING the tool, not by re-deriving the right answer.
    data = r"C:\Projects\Hexapla-releases"
    if not os.path.isdir(os.path.join(data, NARRATION)):
        check(False, "exit contract: %s not found - THESE CHECKS DID NOT RUN, "
                     "which is not a pass" % NARRATION)
    else:
        def run(*args):
            p = subprocess.run([sys.executable, os.path.abspath(__file__)] + list(args),
                               cwd=data, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            return p.returncode

        rc_no_ctl = run("--item", "mizpeh")
        check(rc_no_ctl == 3,
              "exit contract: --item mizpeh puts the control OUT of view, so "
              "the tool exits 3 - NEVER a plausible 0 (got %d)" % rc_no_ctl)
        rc_ctl = run("--item", "baal")
        check(rc_ctl == 0,
              "exit contract: --item baal has the control in view and exits 0 "
              "(got %d)" % rc_ctl)

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
