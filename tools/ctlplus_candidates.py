# -*- coding: utf-8 -*-
"""Find candidate `ctl+` verses: gate-flagged appends whose PRINT does not repeat.

    python tools/ctlplus_candidates.py --lang en
    python tools/ctlplus_candidates.py --lang en --queue _work/ctlplus_queue.txt

0 model tokens, 0 GPU. Runs over the WHOLE corpus, never a sample.

## Why the "print does not repeat" filter is the whole point

A positive control must be a doubling a LISTENER hears as one, AND it must be a
doubling the PRINT does not already contain - otherwise the honest answer is
silence and the control proves nothing (the rule of 2026-09-13).

▶ Num 5:22 is the worked example of the trap in the other direction: the print
genuinely ends "And the woman shall say, **Amen, amen.**", so the gate flagged
`repeat:k1` on nine consecutive draws and could not discriminate any of them.
A candidate whose print already repeats the flagged token is NOT a candidate.

## ⚠⚠ THE GATE RECORD IS STALE FOR ANY REPAIRED VERSE

`qa_gate_appends.py` reads `<c>.qa.json`'s `gate` key, which is the ORIGINAL
render's record and is never rewritten by a repair. A verse repaired since is
still listed there, with the flag and ASR tail of audio no longer on disk.
▶ So this tool EXCLUDES every verse carrying a `repairs` entry, and says how
many it dropped. A candidate whose audio has changed would put the owner's ear
on a defect that is not there.

## ⛔ It also excludes verses an ear has already ruled on

`_work/en_append_ear_VERDICTS_*.md` is every question already put to him. Asking
one twice spends trust, not just minutes (2026-09-14: "I have already reviewed
it 5 times").

Exit 0 = candidates printed. Exit 1 = it could not run, and says why. A tool
that cannot run has not passed - it must never print an empty list that reads
like "no candidates".
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"C:\Projects\Hexapla-releases"
ASSETS = os.path.join(os.path.dirname(HERE), "app", "src", "main", "assets", "bibles")

WORD = re.compile(r"[a-z']+")


def die(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def norm(s):
    """Lowercase word list, note markup stripped - the voice never says a brace."""
    s = re.sub(r"\{[^{}]*:[^{}]*\}", " ", s)
    s = s.replace("{", " ").replace("}", " ")
    return WORD.findall(s.lower())


def load_print(asset):
    p = os.path.join(ASSETS, asset)
    if not os.path.isfile(p):
        die("no asset %s" % p)
    return json.load(open(p, encoding="utf-8"))


def print_repeats(words, atoks):
    """Does the PRINT already repeat, so a control here would prove nothing?

    ⚠ Extracted verbatim from main()'s inline filter so --selftest can assert
    it; the behaviour is unchanged. Two rules, and the FIRST is deliberately
    broad:

    1. ANY adjacent duplicate anywhere in the printed verse -> True, whatever
       the appended token was. Num 5:22 ends "Amen, amen.", so it is caught
       here and must NEVER become a candidate.
    2. otherwise, if the appended token is simply the verse's LAST word -> True.

    ⚠ Rule 1 is broader than "the flagged token repeats": a verse repeating
    some OTHER word adjacently is also dropped. That is the behaviour as it
    stands and it errs toward silence, which is the safe direction for an
    owner-ear queue. Not tuned here.
    """
    if os.environ.get("HEXAPLA_NO_PRINTREPEAT") == "1":
        # ⛔ Known-bad control for --selftest ONLY. This is the filter that is
        # the whole point of the tool; switching it off makes Num 5:22 a
        # candidate and spends the owner's ear on a non-defect.
        return False
    repeats = False
    for i in range(len(words) - 1):
        if words[i] == words[i + 1]:
            repeats = True
            break
    if atoks and not repeats:
        # also reject when the appended token is simply the verse's last word
        if words and atoks[-1] == words[-1]:
            repeats = True
    return repeats


def verse_text(bible, b, c, v):
    """The asset is a FLAT LIST of books, each {name, chapters}; chapters is a
    list of chapters, each a list of verse strings. ⚠ Not {"books": …} - getting
    this wrong makes every lookup return None and the whole screen reports a
    clean-looking 0 candidates (measured 2026-09-17: 223 of 254 silently dropped)."""
    try:
        return bible[b]["chapters"][c][v - 1]
    except Exception:
        return None


def assert_indexing(bible):
    """Known anchor: book 3 chapter 4 verse 22 is Numbers 5:22, which ends
    'Amen, amen.' If this does not hold, the asset's shape has changed and every
    print lookup below would be wrong - refuse rather than report 0."""
    if len(bible) < 4 or not isinstance(bible[3], dict):
        die("asset is not a flat list of book objects - indexing assumption broken")
    if "numbers" not in (bible[3].get("name") or "").lower():
        die("book index 3 is %r, expected Numbers - the book order has changed"
            % bible[3].get("name"))
    t = verse_text(bible, 3, 4, 22)
    if not t or "amen" not in t.lower():
        die("anchor Num 5:22 did not resolve to text containing 'amen' (got %r) - "
            "refusing to run with a broken print lookup" % (t or "")[:60])


def already_asked():
    """Every (book, chapter, verse) an ear has already ruled on."""
    seen = set()
    files = sorted(glob.glob(os.path.join(DATA, "_work", "en_append_ear_VERDICTS_*.md")))
    if not files:
        die("no en_append_ear_VERDICTS_*.md found - refusing to build a kit that "
            "might re-ask a question already answered")
    pat = re.compile(r"\b(\d+)\s+(\d+)\s+v(\d+)\b")
    for f in files:
        for line in open(f, encoding="utf-8", errors="replace"):
            m = pat.search(line)
            if m:
                seen.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return seen, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--asset", default="en_kjv.json")
    ap.add_argument("--queue", help="write a build_ear_review --queue file here")
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()

    root = os.path.join(DATA, "narration", a.lang)
    if not os.path.isdir(root):
        die("no narration dir %s" % root)
    bible = load_print(a.asset)
    assert_indexing(bible)
    asked, verdict_files = already_asked()

    n_files = 0
    flagged = 0
    drop_repaired = 0
    drop_printrepeats = 0
    drop_asked = 0
    drop_notext = 0
    drop_asrsplit = 0
    cands = []

    for qa in glob.glob(os.path.join(root, "*", "*.qa.json")):
        n_files += 1
        try:
            doc = json.load(open(qa, encoding="utf-8"))
        except Exception:
            continue
        b = int(os.path.basename(os.path.dirname(qa)))
        c = int(os.path.basename(qa).split(".")[0])
        repaired = {int(r["verse"]) for r in (doc.get("repairs") or [])
                    if "verse" in r}
        for vs, info in (doc.get("gate") or {}).items():
            try:
                v = int(vs)
            except ValueError:
                continue
            atts = info.get("attempts") or []
            app = None
            tail = ""
            for at in atts:
                for r in (at.get("reasons") or []):
                    if str(r).startswith("append:"):
                        app = str(r).split(":", 1)[1].strip()
                        tail = at.get("tail") or ""
            if not app:
                continue
            flagged += 1
            if v in repaired:
                drop_repaired += 1
                continue
            if (b, c, v) in asked:
                drop_asked += 1
                continue
            txt = verse_text(bible, b, c, v)
            if not txt:
                drop_notext += 1
                continue
            words = norm(txt)
            atoks = norm(app)
            # Does the PRINT already repeat the appended token(s)?
            if print_repeats(words, atoks):
                drop_printrepeats += 1
                continue
            # ⚠ THE ASR SPLITS COMPOUND WORDS, and the gate reads that as an
            # append. "lovingkindness" comes back "loving kindness" and the
            # trailing "kindness" is flagged; so is "Magormissabib" -> "magor
            # misabeeb". Nothing is wrong with the audio. A kit row like this
            # spends a real listen to confirm a spelling artifact.
            joined = "".join(atoks)
            if joined and joined in "".join(words[-6:]):
                drop_asrsplit += 1
                continue
            cands.append((b, c, v, app, tail, txt))

    if n_files == 0:
        die("read 0 qa.json files under %s - the check could not run" % root)

    cands.sort(key=lambda t: (-len(t[3]), t[0], t[1], t[2]))

    print("qa.json files read            : %d" % n_files)
    print("verses with an append flag    : %d" % flagged)
    print("  dropped, already repaired   : %d  (stale gate record)" % drop_repaired)
    print("  dropped, print repeats      : %d  (control would prove nothing)"
          % drop_printrepeats)
    print("  dropped, ear already ruled  : %d  (across %d verdict files)"
          % (drop_asked, len(verdict_files)))
    print("  dropped, no printed text    : %d" % drop_notext)
    print("  dropped, ASR split a compound: %d  (spelling artifact, not audio)"
          % drop_asrsplit)
    print("CANDIDATES                    : %d" % len(cands))
    print("")
    for b, c, v, app, tail, txt in cands[:a.max]:
        print("%d %d v%-4d append:%-22s" % (b, c, v, app))
        print("    tail : %s" % tail[:100])
        print("    print: %s" % txt[:100])

    if a.queue:
        qp = a.queue if os.path.isabs(a.queue) else os.path.join(DATA, a.queue)
        os.makedirs(os.path.dirname(qp), exist_ok=True)
        with open(qp, "w", encoding="utf-8", newline="\n") as fh:
            for b, c, v, app, tail, txt in cands[:a.max]:
                fh.write("%d %d v%d suspect\n" % (b, c, v))
        print("\nwrote queue: %s (%d suspects; add ctl+/ctl- rows before building)"
              % (qp, min(len(cands), a.max)))

    if not cands:
        print("\nNOTE: 0 candidates is a real result ONLY if the counts above are "
              "non-zero. All-zero means the check did not run.")


# ---------------------------------------------------------------- selftest ---

NUM_5_22 = "And the woman shall say, Amen, amen."


def _refuses(fn):
    """-> True if fn() refused via die() (SystemExit 1), with its output eaten."""
    import contextlib
    import io
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn()
    except SystemExit as e:
        return e.code == 1
    return False


def selftest():
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # -- THE WORKED TRAP: Num 5:22's print genuinely repeats ----------------
    w = norm(NUM_5_22)
    check(w[-2:] == ["amen", "amen"],
          "Num 5:22 normalises to a print ending 'amen amen'")
    check(print_repeats(w, norm("amen")) is True,
          "Num 5:22 + append:amen is DROPPED - the print repeats, so a control "
          "there would prove nothing (the worked trap)")
    check(print_repeats(w, norm("amen amen")) is True,
          "Num 5:22 is dropped for a two-token append too")
    check(print_repeats(w, []) is True,
          "Num 5:22 is dropped on the adjacent-duplicate rule alone")

    # -- the false-positive control: a REAL append must survive -------------
    plain = norm("In the beginning God created the heaven and the earth.")
    check(print_repeats(plain, norm("selah")) is False,
          "a genuine append (token absent from the print) IS a candidate "
          "(false-positive control - the tool must still find real defects)")
    check(print_repeats(plain, norm("earth")) is True,
          "an append equal to the print's LAST word is dropped (rule 2)")
    check(print_repeats(plain, norm("heaven")) is False,
          "an append matching a NON-final print word is NOT dropped by rule 2")
    check(print_repeats([], norm("x")) is False,
          "an empty print does not crash and is not dropped")
    check(print_repeats(plain, []) is False,
          "no appended token and no adjacent duplicate -> not dropped")
    check(print_repeats(norm("he said said unto them"), norm("selah")) is True,
          "rule 1 is BROAD: an adjacent duplicate of some OTHER word also "
          "drops the verse (actual behaviour, erring toward silence)")

    # -- norm(): note markup is stripped the way the voice hears it ---------
    check(norm("the LORD {Selah: a note} spake") == ["the", "lord", "spake"],
          "norm: a {x:y} note is DROPPED (colon = note)")
    check(norm("there {was} light") == ["there", "was", "light"],
          "norm: {supplied} words are KEPT without their braces (no colon)")
    check(norm("Amen, amen.") == ["amen", "amen"],
          "norm: punctuation is not a word and case is folded")

    # -- verse_text(): flat list of books, 1-BASED verse -------------------
    bible = [{"name": "Genesis", "chapters": [["g1v1", "g1v2"]]},
             {"name": "Exodus", "chapters": [["e1v1"]]},
             {"name": "Leviticus", "chapters": [["l1v1"]]},
             {"name": "Numbers", "chapters": [[], [], [], [],
                                              ["x"] * 21 + [NUM_5_22]]}]
    check(verse_text(bible, 0, 0, 1) == "g1v1",
          "verse_text: verse is 1-BASED (verse 1 is index 0)")
    check(verse_text(bible, 0, 0, 2) == "g1v2", "verse_text: verse 2 resolves")
    check(verse_text(bible, 3, 4, 22) == NUM_5_22,
          "verse_text: the Num 5:22 anchor resolves at book 3, chapter 4, v22")
    check(verse_text(bible, 0, 0, 99) is None,
          "verse_text: an out-of-range verse returns None, never a wrong verse")

    # -- assert_indexing(): refuse rather than report a clean-looking 0 ----
    check(assert_indexing(bible) is None,
          "assert_indexing: a well-shaped asset passes")
    check(_refuses(lambda: assert_indexing({"books": bible})),
          "assert_indexing: a {'books': ...} asset REFUSES (not a flat list)")
    check(_refuses(lambda: assert_indexing(bible[:2])),
          "assert_indexing: too few books refuses")
    reordered = list(bible)
    reordered[3] = {"name": "Joshua", "chapters": [[NUM_5_22]]}
    check(_refuses(lambda: assert_indexing(reordered)),
          "assert_indexing: a changed book order refuses")
    noanchor = list(bible)
    noanchor[3] = {"name": "Numbers", "chapters": [[], [], [], [], ["x"] * 22]}
    check(_refuses(lambda: assert_indexing(noanchor)),
          "assert_indexing: a broken print lookup refuses (no 'amen' anchor) - "
          "it never reports 0 candidates instead")

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
    main()
