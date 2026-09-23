#!/usr/bin/env python
"""Apply the owner's H default to the CONFIDENT H/N sites only. Dry run by default.

    python tools/thorlaks_hn_apply_default.py            # DRY RUN (the default)
    python tools/thorlaks_hn_apply_default.py --selftest # two-way control
    python tools/thorlaks_hn_apply_default.py --apply    # writes, then re-reads

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).
⚠ Prefix with `PYTHONIOENCODING=utf-8`; the tails carry ñ / þ / ø.

## What this does, and the exact licence it runs under

The owner ruled 2026-09-16: **the default letter is `H`, and it covers the
STRICT cut ONLY** — the rows `thorlaks_hn_partition.py` calls CONFIDENT
(`R >= 10 AND S >= 10`). He was shown the looser lexical cut and DECLINED it,
because it asks only whether the WORD is an h-word and never whether the
corpus's readers agreed on the CAPITAL, which is the sort actually confused.
▶ `research/_evidence/thorlaks_hn_owner_verdict_2026-09-14.md`

⛔ **The AMBIGUOUS rows stay bracketed** and are adjudicated one at a time.
⛔ **`case_pairs` still rules on nothing** — it is a witness list. This script
does not extend the witness; it executes a ruling already given on a partition
derived from it, and it derives that partition LIVE on every run. ⛔ There is no
hardcoded site list here, because a stale hardcoded answer looks exactly like a
fresh one.

⛔ **The READING rule is UNCHANGED.** A reader still brackets `[HN]` whenever
the tail is not legible. A retroactive default is NOT a licence to resolve a
site at the page, and this tool never touches a bracketed site — `[HN]id`
tokenises to `HN` + `id`, neither of which begins with a capital `N`.

## ⚠ It touches ALREADY-MERGED records

Every site lives in `research/_parts/*.md`. That is why it is `--dry-run` by
default, shows the first three sites in full before anything else, backs every
file up to `<name>.md.bak-hnH` (which `part_files()` skips, so a backup can
never re-enter the tally), and re-reads the live files after writing.

## Why a token rewrite and not a string replace

`cp.WORD` is the same tokeniser the witness list is built from, so the sites
this patcher edits are exactly the sites the partition counted. A substring
replace of `Nid` -> `Hid` would also corrupt **`Nidur`**, a different word that
merely starts with the same letters. That is the known-bad path, and the
selftest fires on precisely it.

## The control, and it must fire BOTH ways

Fixture half (no corpus needed), with the confident set forced to `{id}`:

- ▶ `Nid`   MUST become `Hid`               — the default applies;
- ▶ `Nidur` MUST stay `Nidur`               — ★ the substring trap;
- ▶ `Nofud` MUST stay (AMBIGUOUS bucket), `Nafn` MUST stay (never a candidate),
  `[HN]id` MUST stay (bracketed), lowercase `nid` MUST stay.

Live half:

- ▶ `thorlaks_hn_partition.py --selftest` MUST exit 0, run through its REAL
  entry point (⛔ never a re-implementation of its cut here — a
  re-implementation would agree with itself while the shipped tool drifted);
- ▶ `Nofud` MUST NOT be in the covered set. ★ A cut that calls `Nofud`
  confident is calling a coin toss confident, and a patcher running on it
  would write a coin toss to disk.

⚠⚠ **A covered set of 0 is the EXPECTED STEADY STATE after a successful
`--apply`, not a failure.** `candidates()` requires a live capital-`N` reading,
so resolving every CONFIDENT site removes those tails from the witness list
entirely. ★★ **A patcher that resolves a bucket destroys any control drawn from
that bucket** — which is exactly what happened at 17:17 on 2026-09-16, and why
the partition's positive control is now a frozen fixture of the same two real
witnesses. ▶ `research/_evidence/thorlaks_hn_default_applied_2026-09-16.md`

Exit 0 = the controls fired and the plan printed (or the write verified).
Exit 1 = an ANCHOR FAILED or the post-write re-read disagreed. ⛔ Nothing is
         written when an anchor fails; a partial patch is worse than none.
Exit 3 = the upstream partition or witness list refused, so there is no plan.
         ⛔ A refusal is not a pass.

Set `HEXAPLA_NO_HNPATCH=1` to force the known-bad substring path and confirm
the control is alive (`--selftest` must then FAIL with exit 1).
"""
import argparse
import datetime
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_hn_case_pairs as cp       # noqa: E402  the tokeniser + witness
import thorlaks_hn_partition as hp        # noqa: E402  the ruled partition

try:                                       # the tails carry ñ / þ / ø
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                          # noqa: BLE001  py2-style stdout
    pass

DEFAULT_LETTER = "H"
BACKUP_SUFFIX = ".bak-hnH"
SHOW_FIRST = 3

# The fixture control. ⛔ Do not edit these to make a run pass.
FIX_TAILS = set(["id"])
FIX_IN = [
    "og Nid var þar, en Nidur stod hia",
    "hann Nofud sagdi vid þa",
    "med Nafn sitt i hende",
    "þat [HN]id er ecki leseligt",
    "lowercase nid stendur obreytt",
]
FIX_WANT = [
    "og Hid var þar, en Nidur stod hia",
    "hann Nofud sagdi vid þa",
    "med Nafn sitt i hende",
    "þat [HN]id er ecki leseligt",
    "lowercase nid stendur obreytt",
]


def rewrite_line(line, tails):
    """-> (new_line, [(old_word, new_word, col)]).

    Token-exact: a word is rewritten only when it is a WHOLE token whose first
    character is a capital `N` and whose tail is in `tails`.
    """
    if os.environ.get("HEXAPLA_NO_HNPATCH"):
        # KNOWN-BAD: substring replace. Corrupts `Nidur` when `id` is confident.
        hits = []
        out = line
        for t in sorted(tails):
            old, new = "N" + t, DEFAULT_LETTER + t
            if old in out:
                hits.append((old, new, out.index(old)))
                out = out.replace(old, new)
        return out, hits

    hits = []
    pieces = []
    last = 0
    for m in cp.WORD.finditer(line):
        w = m.group(0)
        if len(w) < 2 or w[0] != "N" or w[1:] not in tails:
            continue
        new = DEFAULT_LETTER + w[1:]
        pieces.append(line[last:m.start()])
        pieces.append(new)
        last = m.end()
        hits.append((w, new, m.start()))
    if not hits:
        return line, []
    pieces.append(line[last:])
    return "".join(pieces), hits


def confident_set():
    """-> (tails, expected_sites, rows) or (None, None, None) if upstream refused."""
    rows, extra = hp.build()
    if rows is None:
        return None, None, None
    tails = set(r[1] for r in rows if r[0] == "CONFIDENT")
    expected = sum(r[2] for r in rows if r[0] == "CONFIDENT")
    return tails, expected, rows


def build_plan(tails):
    """-> (plan, total) or (None, None) on a read failure. Reads, writes nothing."""
    paths = cp.part_files()
    if not paths:
        sys.stderr.write("NOTHING TO EXAMINE - that is not a pass.\n")
        return None, None
    plan = []
    total = 0
    for p in paths:
        try:
            with io.open(p, encoding="utf-8") as fh:
                text = fh.read()
        except Exception as exc:                              # noqa: BLE001
            sys.stderr.write("FAILED to read %s: %s\n" % (p, exc))
            return None, None
        newline_at_end = text.endswith("\n")
        lines = text.splitlines()
        edits = []
        for i, line in enumerate(lines):
            new, hits = rewrite_line(line, tails)
            if hits:
                edits.append((i + 1, line, new, hits))
                total += len(hits)
        if edits:
            plan.append((p, lines, edits, newline_at_end))
    return plan, total


def _upstream_selftest():
    """Run the partition's OWN two-way selftest, through its real entry point.

    ⛔ Not a re-implementation of its cut: a re-implementation would agree with
    itself while the shipped tool drifted. -1 on a launch failure, never 0.
    """
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(here, "thorlaks_hn_partition.py"),
             "--selftest"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("COULD NOT LAUNCH the partition selftest: %s\n" % exc)
        return -1


def selftest():
    ok = True

    print("  -- fixture half (confident set forced to {id}) --")
    got = [rewrite_line(l, FIX_TAILS)[0] for l in FIX_IN]
    for want, g, src in zip(FIX_WANT, got, FIX_IN):
        mark = "ok " if g == want else "FAIL"
        print("  %s %s" % (mark, src))
        if g != want:
            ok = False
            print("       want: %s" % want)
            print("       got : %s" % g)
    print("     ^ `Nidur` is the substring trap: it MUST survive line 1 intact.")

    print("  -- live half (the real corpus, through the ruled partition) --")
    tails, expected, rows = confident_set()
    if tails is None:
        print("  FAIL upstream partition refused - no plan is possible.")
        return 3
    # ⚠ The upstream cut is controlled by a FIXTURE, not by the live bucket —
    # applying the default EMPTIES the CONFIDENT bucket by construction, so a
    # live positive control is not obtainable after a successful run. Delegate
    # to the partition's own two-way selftest, then assert what stays true
    # live: `Nofud` must NEVER be covered.
    rc = _upstream_selftest()
    print("  partition --selftest exit = %d (want 0)" % rc)
    if rc != 0:
        ok = False
    neg = hp.CONTROL_AMBIGUOUS not in tails
    print("  control - : N%-6s NOT in the covered set = %s (want True)"
          % (hp.CONTROL_AMBIGUOUS, neg))
    if not neg:
        ok = False
    print("  covered right now: %d word form(s), %d site(s)"
          % (len(tails), expected))
    if not tails:
        print("     ^ 0 is the EXPECTED STEADY STATE after a successful "
              "--apply, not a failure. The fixture half above is what proves "
              "the cut is still live.")

    if ok:
        print("SELFTEST PASSED - fires both ways, so the patcher cannot be "
              "loosened without breaking it.")
        return 0
    print("SELFTEST FAILED - the control is inert; ⛔ do not run --apply.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (default is a DRY RUN)")
    ap.add_argument("--all", action="store_true",
                    help="print every planned site, not just the first %d"
                         % SHOW_FIRST)
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    tails, expected, rows = confident_set()
    if tails is None:
        sys.stderr.write("UPSTREAM REFUSED - no partition, so no plan. "
                         "⛔ This is not a pass.\n")
        return 3
    # ⛔ Refuse to plan unless the upstream cut still fires BOTH ways. An empty
    # covered set is fine (it is the steady state after --apply); an upstream
    # whose control is inert is not.
    if _upstream_selftest() != 0:
        sys.stderr.write("PARTITION SELFTEST DID NOT PASS - the cut is inert, "
                         "so refusing to plan anything. ⛔ Not a pass.\n")
        return 3
    if hp.CONTROL_AMBIGUOUS in tails:
        sys.stderr.write("LIVE CONTROL FAILED: N%s is in the covered set. The "
                         "cut is calling a coin toss confident. ⛔ Refusing.\n"
                         % hp.CONTROL_AMBIGUOUS)
        return 3

    plan, total = build_plan(tails)
    if plan is None:
        return 3

    print("Default letter: %s   (owner, 2026-09-16 - STRICT cut only)"
          % DEFAULT_LETTER)
    print("Covered: %d CONFIDENT word form(s); partition expects %d site(s)."
          % (len(tails), expected))
    print("Found in research/_parts/: %d site(s) in %d file(s)."
          % (total, len(plan)))
    print()

    # ---- the anchor. ⛔ Nothing is written if this disagrees. ----
    if total != expected:
        sys.stderr.write(
            "ANCHOR FAILED: planned %d site(s) but the partition counted %d.\n"
            "The tokeniser and the tally disagree, so the plan is not the "
            "witness list. ⛔ NOTHING WRITTEN.\n" % (total, expected))
        return 1
    if total == 0:
        print("Nothing to do - no CONFIDENT capital-N site remains. (After a "
              "successful --apply this is the expected steady state: the "
              "patched tails leave the witness list entirely, because "
              "`candidates()` requires a live capital-N reading.)")
        return 0

    shown = 0
    print("---- first %d site(s), in full ----" % SHOW_FIRST)
    for p, lines, edits, _ in plan:
        for lineno, old, new, hits in edits:
            if shown >= SHOW_FIRST:
                break
            print("%s:%d" % (p, lineno))
            for ow, nw, _col in hits:
                print("    %s  ->  %s" % (ow, nw))
            print("  - %s" % old.strip()[:118])
            print("  + %s" % new.strip()[:118])
            shown += 1
        if shown >= SHOW_FIRST:
            break
    print()

    if a.all:
        print("---- every planned site ----")
        for p, lines, edits, _ in plan:
            for lineno, old, new, hits in edits:
                print("%-46s :%-5d %s" % (p, lineno,
                      "  ".join("%s->%s" % (o, n) for o, n, _ in hits)))
        print()

    if not a.apply:
        print("DRY RUN - nothing written. Re-run with --apply to write.")
        print("⚠ These are ALREADY-MERGED records. Every file is backed up to "
              "<name>.md%s first." % BACKUP_SUFFIX)
        print("▶ `--all` lists every site; `--selftest` proves the cut still "
              "fires both ways.")
        return 0

    # ---- write ----
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    manifest = []
    written = []
    for p, lines, edits, nl in plan:
        bak = p + BACKUP_SUFFIX
        try:
            with io.open(p, encoding="utf-8") as fh:
                current = fh.read()
            if current.splitlines() != lines:
                sys.stderr.write("ANCHOR FAILED: %s changed under us. "
                                 "⛔ STOPPING; %d file(s) already written.\n"
                                 % (p, len(written)))
                return 1
            with io.open(bak, "w", encoding="utf-8", newline="") as fh:
                fh.write(current)
            out = list(lines)
            for lineno, old, new, hits in edits:
                if out[lineno - 1] != old:
                    sys.stderr.write("ANCHOR FAILED at %s:%d. ⛔ STOPPING.\n"
                                     % (p, lineno))
                    return 1
                out[lineno - 1] = new
                for ow, nw, col in hits:
                    manifest.append("%s\t%d\t%d\t%s\t%s"
                                    % (p, lineno, col, ow, nw))
            text = "\n".join(out) + ("\n" if nl else "")
            with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            written.append(p)
        except Exception as exc:                              # noqa: BLE001
            sys.stderr.write("WRITE FAILED on %s: %s ⛔ STOPPING.\n" % (p, exc))
            return 1

    # ---- re-read the LIVE target. An exit code is not an outcome. ----
    counts, _ = cp.tally(cp.part_files())
    if counts is None:
        sys.stderr.write("POST-WRITE RE-READ FAILED - ⛔ the write is "
                         "UNVERIFIED. Backups are at *%s.\n" % BACKUP_SUFFIX)
        return 1
    left = sum(counts.get(t, {}).get("N", 0) for t in tails)
    if left:
        sys.stderr.write("POST-WRITE RE-READ DISAGREES: %d capital-N site(s) "
                         "still carry a CONFIDENT tail. ⛔ NOT CLEAN. Backups "
                         "are at *%s.\n" % (left, BACKUP_SUFFIX))
        return 1

    try:
        os.makedirs("_work", exist_ok=True)
        mpath = os.path.join("_work", "hn_patch_manifest_%s.tsv" % stamp)
        with io.open(mpath, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("path\tline\tcol\told\tnew\n")
            fh.write("\n".join(manifest) + "\n")
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("⚠ manifest not written (%s) - the patch itself is "
                         "verified and the backups stand.\n" % exc)
        mpath = "(not written)"

    print("APPLIED and RE-READ: %d site(s) in %d file(s); 0 CONFIDENT "
          "capital-N site(s) remain." % (len(manifest), len(written)))
    print("manifest: %s" % mpath)
    print("backups : *%s  (part_files() skips them)" % BACKUP_SUFFIX)
    print("▶ NOW RUN, per touched book:")
    print("    python C:/Projects/Hexapla/tools/thorlaks_part_check.py --book <B>")
    print("⛔ «0 findings» there means PASSED THESE CHECKS, never «read "
          "correctly».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
