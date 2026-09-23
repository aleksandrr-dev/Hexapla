# -*- coding: utf-8 -*-
"""List every `append:` flag the RENDER GATE raised, per book. 0 model tokens.

    python tools/qa_gate_appends.py --lang en --books 6
    python tools/qa_gate_appends.py --lang en --books 0-79 --compound-split
    python tools/qa_gate_appends.py --lang en --books 0-79 --compound-split --queue-only
    python tools/qa_gate_appends.py --selftest        # HEXAPLA_NO_COMPOUND=1 = known-bad

## Why this exists

⚠⚠ **THE GATE'S APPEND SET AND THE ASR'S ARE DISJOINT.** Measured on books 1-3
(zero overlap), on book 6 (2026-09-13) and most sharply on book 11
(2026-09-14): the ASR sweep reported **0 APPEND over all 719 verses of 2 Kings**
while the gate flagged **12** on the same audio — and the ear then confirmed one
of them, 2 Kings 15:2, as a real doubling. ⛔ Neither instrument alone is «the
append screen», and a book screened by only one of them is NOT screened.

⚠ **THE GATE HAS FALSE NEGATIVES TOO.** Leviticus 22:17's ear-confirmed
doubling is NOT among book 2's gate flags. Disjoint runs both ways.

`qa_asr_sweep.py` reports the ASR side. Nothing reported the gate side, so it
was being read by hand out of the `.qa.json` files, one `python -c` at a time.
This is that read, done properly.

## ⛔ WHAT AN `append:<token>` MEANS, AND THE ONE QUESTION TO ASK

The gate heard a token past the end of the verse. The ONLY question is:
**is that token part of what the print sets at this point?**

  · «append:judah» on Judges 19:1 — the print reads «Bethlehemjudah», ONE word.
    The token is inside the printed word. ARTIFACT.
  · «append:high» on Judges 15:17 — the print reads «Ramathlehi»; spoken, its
    tail tokenises as «high». ARTIFACT.
  · «append:'» — one character. A tokeniser artifact by the standing rule.
  · «append:of jerusalem» on 2 Kings 15:2 — the print sets the phrase ONCE and
    the audio speaks it TWICE. A DEFECT, ear-confirmed by the owner 2026-09-14
    («Of Jerusalem repeats»). ▶ `_work/en_append_ear_VERDICTS_2026-09-14.md`

⛔ **A DEFECT-SHAPED FLAG IS NOT A DEFECT.** Of book 11's four doubling-shaped
flags the ear confirmed exactly ONE; of books 8-10's sixteen appends, ZERO were
real. ★ **A repeated phrase in the ASR tail is not a repeat in the audio.**
⚠ Judges 9:47 («append:were gathered together») read exactly like the 2 Kings
15:2 case and this docstring cited it as a defect for a day — **the owner
CLEARED it at the ear** on 2026-09-13. ⛔ Do not re-open it; it is the reason
this file now names only an EAR-CONFIRMED verse as its worked example.

⛔⛔ **DO NOT TRIAGE AN APPEND WITH `qa_text_explained.py` ALONE.** That tool is
a TAIL-REPEAT check. Handed an `append:` flag it hunts for a doubling, finds an
unrelated one, and prints TEXT-EXPLAINED over a finding it never examined — it
did exactly that for three of Judges' four, and its own controls pass 8/8 both
ways, so it does not look wrong. ★ TEXT-EXPLAINED CLEARS A DOUBLING, NOT A
VERSE. That is how Numbers 5:22 nearly got cleared with a real truncation in it.
⛔ `--unexplained` is WITHDRAWN and does nothing — it filtered on «is the token
a substring of the print», which DROPS doublings. The tool prints why.

## ★ `--compound-split` — the one rule the ear has warranted (2026-09-20)

The owner ruled FIVE closed compounds at the ear on 2026-09-20 and the class
came back an INSTRUMENT ARTIFACT: `kneadingtroughs`, `Pharaohnechoh`,
`thereinto`, `brokenhanded`, `fellowlabourer`. So the rule asks exactly one
question — **is the appended token the TAIL of a single printed word?** — and it
retires **55 of the 305 en flags** with no ear and no GPU. The reasoning, the
three guards and the closed orthographic fold sit above `parse_books()`.
▶ controls: `--selftest` (0) and `HEXAPLA_NO_COMPOUND=1 --selftest` (1).
⚠ Both of the screen's worked defects — 2 Kings 15:2 and Psalms 35:1 — have
since been repaired or reverted, so NEITHER still appears in the live corpus
run. They survive only as selftest rows, and that is the only place the guard
against explaining away a doubling can now be exercised. ⛔ Do not delete them.

⚠ `--compound-split` NARROWS a queue, it never clears a verse. Only an ear does.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = r"C:/Projects/Hexapla-releases"
_BOOKS = None


def kjv_text(book, chapter, verse):
    """The printed verse, or None. Reuses qa_text_explained's own loader so
    there is ONE definition of «the print» in this toolchain."""
    global _BOOKS
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import qa_text_explained as qte
        if _BOOKS is None:
            _BOOKS = qte.load("kjv")
        return qte.vtext(_BOOKS, book, chapter, verse)
    except Exception:
        return None      # ⛔ None means UNAVAILABLE and prints as such —
                         # never a plausible empty string that would read as
                         # «the token is not in the print».


# ---------------------------------------------------------------------------
# THE COMPOUND-SPLIT RULE (2026-09-20)
# ---------------------------------------------------------------------------
# ★ WARRANT: the owner ruled FIVE of these at the ear on 2026-09-20 and the
#   class came back an INSTRUMENT ARTIFACT, four cleared outright —
#   `kneadingtroughs` (append:troes), `Pharaohnechoh` (append:nesho),
#   `thereinto` (append:into), `brokenhanded` (append:handed),
#   `fellowlabourer` (append:labourer/laborer).
#   ▶ `_work/en_append_ear_VERDICTS_2026-09-20.md`. The fifth (Pharaohnechoh)
#   he preferred the other take of — on VOICE QUALITY. ⛔ He did not hear an
#   appended word in any of the five.
#
# The shape: the print sets ONE CLOSED COMPOUND. The voice speaks it as one
# word; the tokeniser cuts it in two and reports the tail as an append. So the
# question this rule asks is exactly: **is the appended token the TAIL of a
# closed compound in the printed verse?**
#
# ⛔⛔ THE DANGEROUS DIRECTION IS EXPLAINING AWAY A REAL DOUBLING, so the rule
# carries three hard guards, and each one is the reason a known case survives:
#   1. A MULTI-WORD token is NEVER a compound split — a compound cuts into one
#      tail. This alone is what keeps 2 Kings 15:2 («of jerusalem», EAR-
#      CONFIRMED doubling) and Psalms 35:1 («a vite against me») in the queue.
#   2. If the token stands as its OWN WORD in the printed verse, a doubling is
#      at least as good an explanation and only an ear settles it.
#   3. The compound's prefix must be a real chunk (>= 3 folded letters) and the
#      token itself >= 3 folded letters, so a one- or two-letter tail can never
#      retire anything.
#
# `fold()` is a small, CLOSED orthographic equivalence — every rule in it is
# here because a ruled case needed it, and nothing is here speculatively:
#   gh -> ''        troughs ~ troes      (kneadingtroughs)
#   ch, sh -> S     nechoh  ~ nesho      (Pharaohnechoh)
#   ph -> F, th -> T   so those h's are not eaten by the next rule
#   remaining h -> ''  nechoh  ~ nesho
#   vowel run -> its first vowel   labourer ~ laborer, troughs ~ troes
# ⛔ Do not widen it to make a new case pass without an EAR verdict behind it.
# ⚠ This rule NARROWS a queue. It does not clear a verse — only an ear does.

_VOWELS = "aeiouy"


def fold(word):
    """The closed orthographic fold. See the block above; ⛔ not a phonetiser."""
    w = re.sub(r"[^a-z]", "", (word or "").lower())
    w = w.replace("gh", "")
    w = w.replace("ch", "S").replace("sh", "S")
    w = w.replace("ph", "F").replace("th", "T")
    w = w.replace("h", "")
    out = []
    for c in w:
        if c in _VOWELS and out and out[-1] in _VOWELS:
            continue          # collapse a vowel run to the vowel that opened it
        out.append(c)
    return "".join(out)


def compound_split(tok, printed):
    """The printed closed compound whose TAIL is `tok`, or None.

    ⛔ None is also what an UNAVAILABLE print returns — the caller must not
    read that as «not a compound», and main() prints it as unavailable.
    """
    if printed is None:
        return None
    if os.environ.get("HEXAPLA_NO_COMPOUND") == "1":
        return None          # known-bad control: the rule explains nothing
    tok_raw = (tok or "").strip()
    if not tok_raw or re.search(r"\s", tok_raw):
        return None                      # guard 1: multi-word is never a split
    ft = fold(tok_raw)
    if len(ft) < 3:
        return None                      # guard 3a
    words = re.findall(r"[A-Za-z']+", printed)
    if any(fold(w) == ft for w in words):
        return None                      # guard 2: it stands as its own word
    # ⚠ Fold the SUFFIX, never the joined word. Folding «thereinto» whole
    # collapses the vowel run «ei» and eats the i, so the tail «into» stops
    # matching — and that is a ruled case. The tokeniser cuts the spoken word
    # and spells each piece on its own, so the rule must compare the same way.
    for w in words:
        for i in range(1, len(w)):
            if fold(w[i:]) != ft:
                continue
            if len(fold(w[:i])) < 3:
                continue                 # guard 3b: prefix must be a real chunk
            return w
    return None


# ⛔ Known-bad BOTH WAYS. The first five must be EXPLAINED (the ear ruled them);
# the last three must SURVIVE — two are ear-confirmed or unruled defects and the
# third is an artifact this rule is not entitled to claim.
_SELFTEST = [
    ("troes", "and the river shall bring forth frogs abundantly, which shall "
              "go up and come into thine house, and into thy bedchamber, and "
              "upon thy bed, and into the house of thy servants, and upon thy "
              "people, and into thine ovens, and into thy kneadingtroughs",
     "kneadingtroughs"),
    ("nesho", "and Pharaohnechoh put him in bands at Riblah in the land of "
              "Hamath", "Pharaohnechoh"),
    ("necho", "and Pharaohnechoh put him in bands at Riblah in the land of "
              "Hamath", "Pharaohnechoh"),
    ("into", "and let not them that are in the countries enter thereinto",
     "thereinto"),
    ("handed", "or a man that is brokenfooted, or brokenhanded", "brokenhanded"),
    ("labourer", "unto Philemon our dearly beloved, and fellowlabourer",
     "fellowlabourer"),
    ("laborer", "unto Philemon our dearly beloved, and fellowlabourer",
     "fellowlabourer"),
    # ⛔ MUST NOT be explained — ear-confirmed doubling, owner 2026-09-14.
    ("of jerusalem", "and his mother's name was Jephunneh of Jerusalem", None),
    # ⛔ MUST NOT be explained — the genuine append the owner reverted.
    ("a vite against me", "Plead my cause, O LORD, with them that strive with "
                          "me: fight against them that fight against me", None),
    # ⛔ MUST NOT be explained — the token stands as its own word (guard 2),
    #    so a doubling is at least as good an explanation.
    ("judah", "and there was a certain Levite sojourning on the side of mount "
              "Ephraim, who took to him a wife out of Bethlehemjudah, and she "
              "went unto Judah", None),
]


def selftest():
    bad = 0
    off = os.environ.get("HEXAPLA_NO_COMPOUND") == "1"
    for tok, printed, want in _SELFTEST:
        got = compound_split(tok, printed)
        ok = (got == want)
        if not ok:
            bad += 1
        print("  %s append:%-18s -> %-16s (want %s)"
              % ("ok " if ok else "⛔ ", tok, got, want))
    if off:
        print("\nHEXAPLA_NO_COMPOUND=1: the rule is disabled, so the five ruled "
              "compounds go UNEXPLAINED. %d row(s) disagree — a non-zero here "
              "is the KNOWN-BAD control passing." % bad)
        return 1 if bad else 0
    print("\n%s %d/%d" % ("⛔ SELFTEST FAILED" if bad else "✅ selftest",
                          len(_SELFTEST) - bad, len(_SELFTEST)))
    return 1 if bad else 0


def parse_books(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--books", help="e.g. 6 or 0-7 or 1,4,6")
    ap.add_argument("--unexplained", action="store_true",
                    help="⛔ WITHDRAWN — it under-reported. See the docstring.")
    ap.add_argument("--compound-split", action="store_true", dest="compound",
                    help="annotate each flag with the closed compound in the "
                         "print whose tail it is, and report how many that "
                         "retires. Ear-warranted 2026-09-20; see the block "
                         "above parse_books().")
    ap.add_argument("--queue-only", action="store_true",
                    help="with --compound-split: print ONLY the flags the rule "
                         "does NOT explain — the queue that still wants an ear.")
    ap.add_argument("--selftest", action="store_true",
                    help="the compound-split rule against its ruled cases; "
                         "HEXAPLA_NO_COMPOUND=1 is the known-bad control.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.lang or not a.books:
        ap.error("--lang and --books are required (except with --selftest)")
    if a.queue_only and not a.compound:
        ap.error("--queue-only means nothing without --compound-split")
    if a.unexplained:
        sys.stderr.write(
            "⛔ --unexplained is WITHDRAWN and does nothing.\n\n"
            "It filtered on «is the appended token a substring of the printed "
            "verse», and that test is WRONG IN THE DANGEROUS DIRECTION — it "
            "drops doublings, which are the whole defect class.\n"
            "  · 2 Kings 15:2 append:«of jerusalem» — the print DOES contain "
            "that phrase (once); the defect is that the audio says it TWICE. "
            "The filter would have DROPPED it. This one is EAR-CONFIRMED "
            "(owner, 2026-09-14), so the loss is measured, not hypothetical.\n"
            "  · Judges 15:17 append:«high» — NOT a substring of «Ramathlehi», "
            "yet a pure tokeniser artifact. The filter would have KEPT it.\n"
            "Wrong in both directions, and wrong the way that loses defects.\n\n"
            "▶ The real test is whether the token is spoken MORE TIMES "
            "than the print sets it — count, not substring. Unbuilt; screen it "
            "against 2 Kings 15:2 as a KNOWN-BAD case before trusting it.\n"
            "⚠ This block once cited Judges 9:47 as its measured loss. The "
            "owner CLEARED 9:47 at the ear on 2026-09-13; the withdrawal "
            "stands on its other grounds, the example was replaced.\n")
        return 2

    root = os.path.join(DATA, "narration", a.lang)
    total = shown = 0
    retired = unavailable = 0
    missing = []
    for b in parse_books(a.books):
        d = os.path.join(root, str(b))
        if not os.path.isdir(d):
            missing.append(b)
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.qa.json")),
                        key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0)):
            ch = os.path.basename(f).split(".")[0]
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except Exception as e:
                print("  ⚠ UNREADABLE %s: %s" % (f, e))
                continue
            seen = set()
            for v, info in (doc.get("gate") or {}).items():
                for att in info.get("attempts", []):
                    for r in att.get("reasons", []):
                        if not r.startswith("append:"):
                            continue
                        tok = r.split(":", 1)[1]
                        key = (v, tok)
                        if key in seen:
                            continue
                        seen.add(key)
                        total += 1
                        printed = kjv_text(b, int(ch), int(v))
                        comp = compound_split(tok, printed) if a.compound else None
                        if a.compound:
                            if printed is None:
                                unavailable += 1
                            elif comp:
                                retired += 1
                        if a.queue_only and comp:
                            continue
                        shown += 1
                        print("%s %s v%-4s append:%-26s kept=%s%s"
                              % (b, ch, v, tok, info.get("kept"),
                                 "  ★ COMPOUND-SPLIT of «%s»" % comp if comp else ""))
                        print("        tail:  %r" % (att.get("tail", "")[:70],))
                        print("        print: %s"
                              % (printed[:110] if printed
                                 else "⚠ PRINTED TEXT UNAVAILABLE — judge nothing"))

    if missing:
        print("\n⚠ NOT RENDERED (no directory), so NOT screened: books %s"
              % ", ".join(str(m) for m in missing))
    print("\n%d append flag(s) found%s."
          % (total, ", %d shown" % shown if a.queue_only else ""))
    if a.compound:
        print("★ COMPOUND-SPLIT: %d of %d explained as the tail of a closed "
              "compound in the print — %d still want an ear."
              % (retired, total, total - retired - unavailable))
        if unavailable:
            print("⚠ %d flag(s) had NO PRINTED TEXT, so the rule could not "
                  "run on them. A rule that could not run did not pass: they "
                  "are counted in NEITHER column above." % unavailable)
        print("⛔ «Explained» means the flag has a printed cause, NOT that the "
              "audio was listened to. The ear ruled the five compounds this "
              "rule generalises from; it has not ruled these.")
    if total == 0 and not missing:
        print("⛔ A zero here is only as wide as --books. It says nothing "
              "about any book you did not name, and nothing about the ASR "
              "side — run qa_asr_sweep.py too; the two sets are DISJOINT.")
    print("⛔ Nothing above is cleared. An append is cleared by an EAR, or by "
          "the token being part of the printed word — never by this tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
