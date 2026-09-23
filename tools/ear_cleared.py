# -*- coding: utf-8 -*-
"""Has this verse been ruled BY EAR? The ledger, read by machine. 0 tokens.

    python tools/ear_cleared.py --list
    python tools/ear_cleared.py --check 3 6 16          # book/chapter/verse, 0-indexed
    python tools/ear_cleared.py --screen still-failing.txt
    python tools/ear_cleared.py --selftest             # HEXAPLA_NO_EARLEDGER=1 = known-bad

## Why this exists

⛔⛔ **NOTHING IN `tools/` RECORDED AN EAR VERDICT UNTIL NOW.** The owner's
rulings lived only in `_work/en_append_ear_VERDICTS_*.md`, as prose. So the
next corpus sweep could — and, on the evidence of how these queues are built,
WOULD — re-condemn a verse he has already listened to and re-roll the dice on
audio he approved. That is not a hypothetical: `repair_verses.py` silently
skips a verse that already has a repair record, so the re-roll needs `--force`,
and `--force` is exactly what a sweep-driven repair pass reaches for.

★ **An ear verdict is the ONLY thing that clears audio in this pipeline.** The
gate's `still_failing=-` is not a pass — it false-negatived TWICE in one day
(Numbers 7:16, Nehemiah 10:26), on takes the owner then condemned by ear. So
this ledger outranks every screen, and a verse listed CLEAR here must not be
re-queued by any of them.

## ⛔ WHY IT PARSES A BLOCK AND NOT THE PROSE

The verdict files are written for the owner to read, and their prose does not
survive a parser. Numbers 7:16 is the proof: its TABLE row says «⛔ REDRAW —
defect in both takes», and a later section of the same file records the redraw
and his clearance of it («Offering no longer doubled. It sounds good.»). A tool
that read the table would report a CLEARED verse as a defect.

So every ledger file must carry a `## MACHINE-READABLE LEDGER` block holding
one `EAR` line per verse, and this tool reads ONLY that block. A ledger file
without one is reported LOUDLY and is NOT silently treated as empty — see
`load()`.

Line format, tab- or multi-space separated, `#` starts a comment:

    EAR <book> <chapter> <verse> <state> <date> <flag> | <owner's words>

`<book> <chapter>` are the 0-INDEXED indices as they appear in
`narration/<lang>/<book>/<chapter>.ogg` — the same addressing
`qa_repair_outcomes.py` prints. `<verse>` is 1-based, as printed.

States, and what each one forbids:

  CLEAR           he listened and heard no defect. ⛔ Do not re-queue, do not
                  repair, do not revert.
  REDRAWN-CLEAR   he condemned a take, it was redrawn, he cleared the NEW one.
                  ⛔ Do not re-queue. ⚠ The screens never cleared this audio and
                  one of them false-negatived on it.
  REVERTED        he preferred the pristine take; the revert is APPLIED and
                  verified byte-identical. ⛔ Do not re-repair.
  DEFECT          he condemned it and it is NOT yet fixed. ★ This is the only
                  state that is a work item.

⚠ This tool answers «was it ruled», never «is it good». A verse absent from the
ledger is UNRULED — which is not the same as clean, and not the same as broken.
"""
import argparse
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = r"C:/Projects/Hexapla-releases"
LEDGER_GLOB = os.path.join(DATA, "_work", "en_append_ear_VERDICTS_*.md")
BLOCK = "## MACHINE-READABLE LEDGER"

STATES = ("CLEAR", "REDRAWN-CLEAR", "REVERTED", "DEFECT")
RULED = ("CLEAR", "REDRAWN-CLEAR", "REVERTED")      # ⛔ do not re-queue these


class LedgerError(Exception):
    """⛔ Raised, never swallowed into a plausible empty result. A ledger that
    could not be read must NEVER be indistinguishable from «nothing is ruled»:
    that is the failure shape that re-rolls approved audio."""


def _parse_block(text, src):
    rows, bad = [], []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        # ⚠ `EAR` + WHITESPACE, not merely a line starting with those letters:
        # the 2026-09-20 backfill tripped on an ordinary prose line beginning
        # «earlier)» and the prose got reworded to suit the parser. ⛔ The
        # owner's record is not edited to satisfy a tool; the tool is fixed.
        if not re.match(r"^EAR\s", line, flags=re.I):
            # Prose inside the block is documentation and is skipped in
            # silence — but a line SHAPED like a row that lost its keyword is
            # a typo, and a typo that reads as «unruled» is the whole danger.
            if re.match(r"^\d+\s+\d+\s+\d+\b", line):
                bad.append((src, raw.strip()))
            continue
        head, _, words = line.partition("|")
        parts = head.split()
        if len(parts) < 6:
            bad.append((src, raw.strip()))
            continue
        _, book, chapter, verse, state, date = parts[:6]
        flag = " ".join(parts[6:])
        if state not in STATES:
            bad.append((src, raw.strip()))
            continue
        try:
            key = (int(book), int(chapter), int(verse))
        except ValueError:
            bad.append((src, raw.strip()))
            continue
        rows.append({"key": key, "state": state, "date": date, "flag": flag,
                     "words": words.strip(), "src": os.path.basename(src)})
    return rows, bad


def load(pattern=None):
    """Every EAR row in every ledger file. ⛔ Raises rather than returning an
    empty list when a ledger exists but cannot be read."""
    if os.environ.get("HEXAPLA_NO_EARLEDGER") == "1":
        return [], [], []        # known-bad control: the ledger is invisible
    files = sorted(glob.glob(pattern or LEDGER_GLOB))
    if not files:
        raise LedgerError(
            "no ledger file matched %s — ⛔ that is NOT «nothing is ruled», it "
            "is a broken path. The owner's verdicts are the authority here and "
            "a tool that cannot find them must stop." % (pattern or LEDGER_GLOB))
    rows, bad, blockless = [], [], []
    for f in files:
        try:
            text = open(f, encoding="utf-8").read()
        except Exception as e:
            raise LedgerError("cannot read %s: %s" % (f, e))
        if BLOCK not in text:
            blockless.append(f)
            continue
        body = text.split(BLOCK, 1)[1]
        body = re.split(r"^## ", body, maxsplit=1, flags=re.M)[0]
        r, b = _parse_block(body, f)
        rows.extend(r)
        bad.extend(b)
    return rows, bad, blockless


def index(rows):
    """The FINAL verdict per verse. A later RULING supersedes an earlier one.

    ⚠ Ordered by the row's own date first and file order only as the
    tie-break — ⛔ not by filename alone. Filename order happens to agree today
    (`…-09-14` sorts before `…-09-14b12`), and relying on that is how a ledger
    named out of order would silently resurrect a superseded DEFECT.
    """
    out = {}
    for i, r in enumerate(rows):
        prev = out.get(r["key"])
        if prev is None or (r["date"], i) >= (prev["date"], prev["_i"]):
            r = dict(r, _i=i)
            out[r["key"]] = r
    return out


def _report_gaps(bad, blockless):
    for f in blockless:
        print("⛔ %s has NO %s block — its verdicts are INVISIBLE to every tool."
              % (os.path.basename(f), BLOCK))
        print("   ⚠ Not counted as «nothing ruled». Add the block.")
    for src, line in bad:
        print("⛔ UNPARSED in %s: %r" % (os.path.basename(src), line))
    if bad or blockless:
        print("⛔ %d unparsed line(s), %d ledger file(s) with no block. A row "
              "this tool could not read is NOT a row that says «unruled»."
              % (len(bad), len(blockless)))


def cmd_list(a):
    """⛔ FINAL state PER VERSE, never raw rows. The same verse is ruled more
    than once on purpose — a known defect gets reused as a positive control to
    prove the instrument still fires — so the raw rows hold superseded
    verdicts. Listing them was actively misleading: Numbers 7:16 carries two
    2026-09-12/14 DEFECT rows and a 2026-09-20 REDRAWN-CLEAR that supersedes
    them, and the first version of this function printed it as a defect."""
    rows, bad, blockless = load(a.ledger)
    idx = index(rows)
    shown = rows if a.all_rows else sorted(idx.values(), key=lambda r: r["key"])
    for r in sorted(shown, key=lambda r: (r["key"], r["date"])):
        b, c, v = r["key"]
        print("%3d %3d v%-4s %-14s %s  %-24s %s"
              % (b, c, v, r["state"], r["date"], r["flag"], r["words"][:60]))
    _report_gaps(bad, blockless)
    n = len(idx)
    ruled = sum(1 for r in idx.values() if r["state"] in RULED)
    print("\n%d VERSE(S) ruled by ear, from %d ruling(s) on record: %d must NOT "
          "be re-queued, %d still a work item (DEFECT)."
          % (n, len(rows), ruled, n - ruled))
    if not a.all_rows and len(rows) != n:
        print("⚠ %d superseded ruling(s) folded away — `--all-rows` shows the "
              "history. ⛔ A superseded DEFECT is NOT an open work item."
              % (len(rows) - n))
    print("⛔ A verse ABSENT from this list is UNRULED — which is not «clean».")
    return 1 if (bad or blockless) else 0


def cmd_check(a):
    rows, bad, blockless = load(a.ledger)
    _report_gaps(bad, blockless)
    key = (a.check[0], a.check[1], a.check[2])
    r = index(rows).get(key)
    if not r:
        print("%d/%d v%d — UNRULED. No ear verdict on record." % key)
        print("⚠ Unruled is not clean and not broken. Only an ear settles it.")
        return 1
    print("%d/%d v%d — %s (%s, %s)" % (key + (r["state"], r["date"], r["src"])))
    if r["words"]:
        print("   owner: %s" % r["words"])
    if r["state"] in RULED:
        print("⛔ DO NOT re-queue, re-repair or revert this verse.")
        return 0
    print("★ DEFECT and not yet fixed — this one IS a work item.")
    return 2


def cmd_screen(a):
    """Read `qa_repair_outcomes.py --class still-failing` output (or any text
    carrying `<book> <chapter> v<verse>` rows) and say which rows are unruled.
    ⛔ An unruled row must not ship."""
    rows, bad, blockless = load(a.ledger)
    _report_gaps(bad, blockless)
    idx = index(rows)
    seen, unruled = 0, []
    for line in open(a.screen, encoding="utf-8"):
        m = re.match(r"\s*(\d+)\s+(\d+)\s+v(\d+)\b", line)
        if not m:
            continue
        seen += 1
        key = tuple(int(g) for g in m.groups())
        r = idx.get(key)
        state = r["state"] if r else "UNRULED"
        print("  %3d %3d v%-4s %s" % (key + (state,)))
        if not r or r["state"] not in RULED:
            unruled.append(key)
    print("\n%d row(s) read, %d NOT ear-ruled." % (seen, len(unruled)))
    if seen == 0:
        print("⛔ ZERO rows matched the `<book> <chapter> v<verse>` shape. That "
              "is a PARSE FAILURE, not a clean screen — check the input.")
        return 1
    if unruled:
        print("⛔ Those rows are unruled and MUST NOT SHIP.")
        return 1
    print("✅ every row is ear-ruled and must not be re-queued.")
    return 1 if (bad or blockless) else 0


# ⛔ Known-bad both ways. These are the 2026-09-20 rulings; if the ledger block
#    is ever edited so one of them stops resolving, this fails loudly.
_SELFTEST = [
    ((3, 6, 16), "REDRAWN-CLEAR"),   # Numbers 7:16 — condemned, redrawn, cleared
    ((15, 9, 26), "REVERTED"),       # Nehemiah 10:26 — reverted to the pristine take
    ((11, 22, 35), "REVERTED"),      # 2 Kings 23:35
    ((0, 12, 14), "CLEAR"),          # Genesis 13:14
    ((56, 0, 1), "CLEAR"),           # Philemon 1:1
    ((99, 99, 99), None),            # ⛔ must come back UNRULED, never a guess
]


def selftest(a):
    off = os.environ.get("HEXAPLA_NO_EARLEDGER") == "1"
    try:
        rows, bad, blockless = load(a.ledger)
    except LedgerError as e:
        print("⛔ %s" % e)
        return 1
    idx = index(rows)
    failures = 0
    for key, want in _SELFTEST:
        got = idx.get(key, {}).get("state")
        ok = (got == want)
        failures += 0 if ok else 1
        print("  %s %s -> %-14s (want %s)"
              % ("ok " if ok else "⛔ ", key, got, want))
    if off:
        print("\nHEXAPLA_NO_EARLEDGER=1: the ledger is invisible, so every "
              "ruled verse reads UNRULED. %d row(s) disagree — a non-zero "
              "here is the KNOWN-BAD control passing." % failures)
        return 1 if failures else 0
    _report_gaps(bad, blockless)
    if failures or bad:
        print("\n⛔ SELFTEST FAILED")
        return 1
    if blockless:
        # ⚠ Deliberately NOT a selftest failure: the rule works, and these are
        # OUTSTANDING BACKFILL, reported every run so they cannot go quiet.
        print("\n⚠ the rule passes, but %d older ledger file(s) still carry no "
              "block, so those rulings remain invisible. Backfill them."
              % len(blockless))
    print("\n✅ selftest %d/%d" % (len(_SELFTEST), len(_SELFTEST)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", help="glob; default is every en verdicts file")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all-rows", action="store_true", dest="all_rows",
                    help="every ruling including superseded ones (history)")
    ap.add_argument("--check", nargs=3, type=int, metavar=("BOOK", "CH", "VERSE"))
    ap.add_argument("--screen", metavar="FILE")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        if a.selftest:
            return selftest(a)
        if a.check:
            return cmd_check(a)
        if a.screen:
            return cmd_screen(a)
        return cmd_list(a)
    except LedgerError as e:
        print("⛔ %s" % e)
        return 3          # ⛔ never 0, and never an empty «nothing ruled»


if __name__ == "__main__":
    sys.exit(main())
