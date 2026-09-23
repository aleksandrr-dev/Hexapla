# -*- coding: utf-8 -*-
"""Controls for prep_chunk.py's 2026-09-10 fixes. Known-bad FIRST, always.

Two defects, found when a single-page re-prep unblocked Luke v3 idx 54:
  1. a re-prep into an EXISTING kit replaced the kit-wide MANIFEST.md with a
     one-page one, and asserted this run's flags over every page in it;
  2. a re-prep emitting FEWER lines left the extra crops behind at the OLD
     geometry, with nothing to distinguish them downstream.

Every control below is run against BOTH the pre-fix tool (the A/B baseline in
the scratchpad) and the patched one. A control that does not FIRE on the
baseline is broken, not quiet, and this harness says so rather than passing.

    python tools/prep_chunk_controls.py --baseline <path to pre-fix prep_chunk.py>

Run from C:\\Projects\\Hexapla-releases. Writes only under _prep/_ctl_*.
"""
import argparse
import io
import os
import shutil
import subprocess
import sys

DATA = r"C:\Projects\Hexapla-releases"
PREP = os.path.join(DATA, "research", "_prep")
TOOL = r"C:\Projects\Hexapla\tools\prep_chunk.py"
KIT = "_ctl_kit"
fails = []


def run(tool, args, expect=None):
    r = subprocess.run([sys.executable, tool] + args, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=DATA)
    if expect is not None and r.returncode != expect:
        return r, False
    return r, True


def manifest(kit=KIT):
    p = os.path.join(PREP, kit, "MANIFEST.md")
    if not os.path.exists(p):
        return ""
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def rows(text):
    """{idx: cells} of the manifest's page table."""
    out = {}
    for ln in text.split("\n"):
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            out[int(cells[0])] = cells
    return out


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("  | " + detail if detail else ""))
    if not ok:
        fails.append(label)
    return ok


def fresh():
    d = os.path.join(PREP, KIT)
    if os.path.isdir(d):
        shutil.rmtree(d)


def merge_control(tool, tag, expect_survives):
    """Build a two-page kit, re-prep ONE page into it, look for the other row."""
    print("\n== MERGE control  [%s]" % tag)
    fresh()
    r, _ = run(tool, ["--vol", "3", "--pages", "50-51", "--out", KIT])
    before = rows(manifest())
    if not check("%s: two-page kit builds (rows 50,51)" % tag,
                 sorted(before) == [50, 51], "rows=%s" % sorted(before)):
        return
    # The pre-fix tool has NEITHER --full-width NOR --clean-stale. Passing
    # either to it makes argparse exit before the re-prep runs, so the
    # known-bad control would measure nothing and merely look like a failure.
    extra = ["--full-width", "--clean-stale"] if tool == TOOL else []
    r, _ = run(tool, ["--vol", "3", "--pages", "50", "--out", KIT] + extra)
    if not check("%s: the re-prep actually ran" % tag, r.returncode == 0,
                 "exit=%s %s" % (r.returncode,
                                 (r.stderr or "").strip().split("\n")[-1][:60])):
        return
    after = rows(manifest())
    survived = 51 in after
    check("%s: idx 51's row survives a re-prep of idx 50" % tag,
          survived == expect_survives,
          "rows now %s (expected survival=%s)" % (sorted(after), expect_survives))
    if not expect_survives:
        return
    # flags must be recorded PER PAGE
    f50 = after.get(50, [""] * 5)[-1]
    f51 = after.get(51, [""] * 5)[-1]
    check("%s: idx 50 records --full-width" % tag, "full-width" in f50, "flags=%r" % f50)
    check("%s: idx 51 does NOT claim --full-width" % tag,
          "full-width" not in f51, "flags=%r" % f51)
    txt = manifest()
    check("%s: header spans both pages, not just the re-prepped one" % tag,
          "idx 50-51" in txt, txt.split("\n")[0][:70])
    check("%s: mixed kit does not assert one apparatus story for all" % tag,
          "PER PAGE" in txt or "DIFFERENT FLAGS" in txt)


def banner_control(tool, tag):
    """A hand-written warning above the heading must survive a merge."""
    print("\n== PREAMBLE control  [%s]" % tag)
    fresh()
    run(tool, ["--vol", "3", "--pages", "50-51", "--out", KIT])
    p = os.path.join(PREP, KIT, "MANIFEST.md")
    with io.open(p, encoding="utf-8") as fh:
        body = fh.read()
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write("SCOPE BANNER DO NOT LOSE\n\n" + body)
    run(tool, ["--vol", "3", "--pages", "50", "--out", KIT, "--clean-stale"])
    check("%s: hand-written scope banner survives the merge" % tag,
          "SCOPE BANNER DO NOT LOSE" in manifest())


def stale_control(tool, tag, expect_refusal):
    """A crop this run will not rewrite must stop the run, not ride along."""
    print("\n== STALE-CROP control  [%s]" % tag)
    fresh()
    run(tool, ["--vol", "3", "--pages", "50", "--out", KIT])
    d = os.path.join(PREP, KIT, "p50")
    ghost = os.path.join(d, "line99.png")
    shutil.copyfile(os.path.join(d, "line00.png"), ghost)
    r, _ = run(tool, ["--vol", "3", "--pages", "50", "--out", KIT])
    refused = (r.returncode == 2)
    check("%s: a stale crop makes the re-prep REFUSE" % tag,
          refused == expect_refusal,
          "exit=%s (expected refusal=%s)" % (r.returncode, expect_refusal))
    if not expect_refusal:
        check("%s: pre-fix tool leaves the stale crop in place, silently" % tag,
              os.path.exists(ghost), "line99.png still there")
        return
    check("%s: it names the file" % tag, "line99.png" in (r.stderr or ""))
    check("%s: and it did NOT delete anything on its own" % tag, os.path.exists(ghost))
    r, _ = run(tool, ["--vol", "3", "--pages", "50", "--out", KIT, "--dry-run"])
    check("%s: --dry-run shows the removal and deletes nothing" % tag,
          "line99.png" in (r.stdout or "") and os.path.exists(ghost),
          (r.stdout or "").strip().split("\n")[-1][:70])
    r, _ = run(tool, ["--vol", "3", "--pages", "50", "--out", KIT, "--clean-stale"])
    check("%s: --clean-stale removes exactly it" % tag,
          not os.path.exists(ghost) and os.path.exists(os.path.join(d, "line00.png")))


def additive_control(baseline):
    """The change must be purely additive: identical crops for an untouched page."""
    print("\n== ADDITIVITY control  (baseline vs patched, same page, same flags)")
    a, b = "_ctl_base", "_ctl_new"
    for k in (a, b):
        if os.path.isdir(os.path.join(PREP, k)):
            shutil.rmtree(os.path.join(PREP, k))
    run(baseline, ["--vol", "3", "--pages", "52", "--out", a])
    run(TOOL, ["--vol", "3", "--pages", "52", "--out", b])
    da = os.path.join(PREP, a, "p52")
    db = os.path.join(PREP, b, "p52")
    na = sorted(os.listdir(da))
    nb = sorted(os.listdir(db))
    if not check("same file list", na == nb, "%d vs %d" % (len(na), len(nb))):
        return
    diff = []
    for n in na:
        with open(os.path.join(da, n), "rb") as f1, open(os.path.join(db, n), "rb") as f2:
            if f1.read() != f2.read():
                diff.append(n)
    check("every crop is byte-identical", not diff,
          "%d file(s) differ: %s" % (len(diff), diff[:4]) if diff else "%d files" % len(na))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True,
                    help="the pre-fix prep_chunk.py (A/B baseline)")
    a = ap.parse_args()
    if not os.path.exists(a.baseline):
        sys.stderr.write("no baseline at %s\n" % a.baseline)
        return 1

    print("#" * 72)
    print("# KNOWN-BAD FIRST: the pre-fix tool must FAIL these")
    print("#" * 72)
    merge_control(a.baseline, "pre-fix", expect_survives=False)
    stale_control(a.baseline, "pre-fix", expect_refusal=False)

    print("\n" + "#" * 72)
    print("# the patched tool must PASS them")
    print("#" * 72)
    merge_control(TOOL, "patched", expect_survives=True)
    banner_control(TOOL, "patched")
    stale_control(TOOL, "patched", expect_refusal=True)
    additive_control(a.baseline)

    fresh()
    print("\n" + "=" * 72)
    if fails:
        print("FAILURES (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("ALL CONTROLS PASS \u2014 and the pre-fix tool failed the two it must fail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
