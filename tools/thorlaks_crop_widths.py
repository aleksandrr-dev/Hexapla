# -*- coding: utf-8 -*-
"""Crop-width outlier audit over a prep kit — pure geometry, 0 model tokens.

    python tools/thorlaks_crop_widths.py                 # every kit
    python tools/thorlaks_crop_widths.py mark_kit        # one kit

## Why this exists

Matthew **p12** was prepped at 1308 px while every peer page was 1968-2342.
The prep captured roughly the LEFT 58 % of the page, so ~41 characters of
Mt 10:8 were simply not in any image — and **both agents' ø passes over that
page, 92 o-positions examined and 14 sheets "complete", were worthless.**

`thorlaks_prep_coverage.py` reported p12 as «0 uncovered runs», because it
had classified the lost right-hand region as apparatus. That is a clean
result meaning "I did not look there".

▶ This check is what would have caught it on day one, and it costs nothing.
Run it on a kit BEFORE reading a single page of it.

## ★ THE PRIMARY TEST IS THE RIGHT MARGIN, NOT THE WIDTH

Width alone is a weak instrument: it needs a kit median, and Matthew's widths
are bimodal so the threshold has to be set loose enough to miss real damage.
It missed **mark_kit/p49**.

The reliable signature is measured PER PAGE and needs no peers: on a correctly
prepped page the crop ends in white margin, so the median distance from the
last ink to the right edge is ~12-16 px. On a truncated page the box cuts
through the text block and that median is **0**.

    page                 ink touching right edge   median right margin
    matthew p12 (bad)              44/56                  0 px
    mark    p49 (bad)              22/39                  0 px
    mark    p48 (good)              0/56                 16 px
    matthew p13 (good)             15/57                 12 px

⚠ «Ends mid-word» is NOT evidence on its own — this typography breaks words
across lines routinely, so healthy pages also touch the edge sometimes.
It is the MEDIAN over the whole page that separates them.

## ⛔⛔ THIS SCREEN HAS A KNOWN FALSE POSITIVE — IT IS A SCREEN, NOT A VERDICT

Some crops include a narrow vertical SLIVER of the adjacent marginal apparatus
column at the far right. That sliver's ink touches the edge, so the page scores
a 0 median margin while the scripture block ends in a perfectly clean margin
and nothing is lost.

**matthew_kit/p18 is exactly this and is NOT truncated** — confirmed by eye on
2026-09-07, while a worker was mid-read on it. Had this tool been believed, a
sound page would have been thrown away and re-prepped.

▶ So a SUSPECT page must be adjudicated BY EYE before anything is discarded:
crop the rightmost ~320 px of ~6 lines, stack, upscale, and look for
  * glyphs SLICED MID-STROKE with no margin      -> truly truncated
  * a clean margin followed by a strip of OTHER text -> apparatus sliver, fine
Verified truncated so far: matthew_kit/p12, mark_kit/p49.
Verified false positive: matthew_kit/p18.

## ⚠ Read the distribution, not just the flag

Matthew's widths are BIMODAL — a ~1968-2031 cluster and a ~2313-2342 cluster
(pages that do and do not exclude an apparatus column). A naive "below 92 %
of median" rule flags the entire lower cluster as suspect. Only p12 falls
below BOTH clusters, and that is the real signal. The percentage is printed
for every page so the clustering is visible; the ⛔ threshold is deliberately
set low (80 %) so it fires on genuine truncation, not on a second cluster.

⛔ A page that cannot be measured is reported as ERROR — never as 0, never
silently skipped.
"""
import io
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PREP = Path(r"C:\Projects\Hexapla-releases\research\_prep")
TRUNCATED = 0.80      # below this share of the kit median = prep truncation
NARROW = 0.92         # below this = worth a look (often a legitimate cluster)


INK = 160          # below this grey level counts as ink
MARGIN_OK = 4      # median right margin at/below this = SUSPECT (not a verdict)

# Pages already adjudicated BY EYE. The screen cannot distinguish these two
# outcomes on its own, so the human/vision verdict is recorded here rather
# than being re-litigated (or silently forgotten) every run.
KNOWN = {
    # --- truly truncated: glyphs sliced mid-stroke, no margin, no sliver ---
    ("matthew_kit", "p12"): "TRUNCATED",   # proven 3 ways; use matthew_p12fix
    # ✅ mark_kit p32 and p49 were TRUNCATED and are now FIXED (2026-09-07):
    # re-prepped with `prep_chunk.py --robust-block`, verified by eye, and the
    # corrected crops were installed over them. The originals are preserved at
    # mark_kit/_TRUNCATED_DO_NOT_USE_p32 / _p49 (that name deliberately does
    # not match the p* glob, so this screen ignores them).
    #   p32  1968 -> 2035 px, right margin 0 -> 7
    #   p49  1624 -> 1981 px, right margin 0 -> 15, edge-touch 22/39 -> 0/39
    # ⛔ Do NOT re-add them as TRUNCATED — that would condemn good crops.
    ("mark_p32fix", "p32"): "CLEAN",
    ("mark_p49fix", "p49"): "CLEAN",
    # --- screened SUSPECT, verified CLEAN: apparatus sliver at the crop edge ---
    ("matthew_kit", "p18"): "CLEAN",
    ("matthew_kit", "p4"): "CLEAN",
    ("matthew_kit", "p6"): "CLEAN",
    ("matthew_kit", "p8"): "CLEAN",
    ("matthew_kit", "p28"): "CLEAN",
    ("mark_kit", "p38"): "CLEAN",
    ("mark_kit", "p44"): "CLEAN",
    ("mark_kit", "p46"): "CLEAN",
}
# All eleven adjudicated by eye 2026-09-07. The screen flagged 11 pages;
# only 3 were real. ▶ That is a ~73 % false-positive rate, which is why this
# file says SUSPECT and refuses to say TRUNCATED on its own authority.


def _right_margin(im):
    """-> px from the last ink to the right edge, or None if the line is blank."""
    g = im.convert("L").point(lambda v: 255 if v < INK else 0)
    bb = g.getbbox()                      # C-speed; None when there is no ink
    if bb is None:
        return None
    return im.size[0] - bb[2]


def measure(kit):
    """-> (error, rows).

    rows: (page, n_lines, minW, medW, maxW, med_margin, n_touching, note)
    """
    try:
        from PIL import Image
    except ImportError:
        return "PIL not available in this interpreter", None
    root = PREP / kit
    if not root.is_dir():
        return f"no kit at {root}", None
    # A dir whose name does not start with "p" is not a page: it is an
    # archived/quarantined set (e.g. mark_kit/_TRUNCATED_DO_NOT_USE_p32).
    # Scanning those re-reports damage that has already been fixed and
    # superseded, which reads as an open problem when it is a closed one.
    pages = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("p")]
    pages.sort(key=lambda d: (len(d.name), d.name))
    rows = []
    for d in pages:
        pngs = sorted(d.glob("line*.png"))
        if not pngs:
            rows.append((d.name, 0, None, None, None, None, None,
                         "NO line*.png"))
            continue
        widths, margins, touching, bad = [], [], 0, 0
        for p in pngs:
            try:
                with Image.open(p) as im:
                    widths.append(im.size[0])
                    m = _right_margin(im)
                    if m is not None:
                        margins.append(m)
                        if m <= 2:
                            touching += 1
            except Exception:
                bad += 1
        if not widths:
            rows.append((d.name, len(pngs), None, None, None, None, None,
                         f"ALL {len(pngs)} UNREADABLE"))
            continue
        med_m = int(statistics.median(margins)) if margins else None
        rows.append((d.name, len(pngs), min(widths),
                     int(statistics.median(widths)), max(widths),
                     med_m, touching,
                     f"{bad} unreadable" if bad else ""))
    return None, rows


def report(kit):
    err, rows = measure(kit)
    print(f"\n{'=' * 76}\n{kit}\n{'=' * 76}")
    # ⛔ Both failures below return a MEASURED-PAGE COUNT OF 0, and main() is
    # required to treat that as a failure rather than a clean result. Until
    # 2026-09-19 they returned a bare [], indistinguishable from "measured
    # everything, found nothing wrong", and the tool printed
    #     ⛔ no kit at .../luke_kit2/p63
    #     ✅ no suspect or unmeasurable pages in the kits checked.
    # and exited 0. A mistyped kit name therefore PASSED this screen.
    # ▶ global CLAUDE.md: a count/status function that FAILS must never return
    #   0 or a plausible number.
    if err:
        print(f"  ⛔ {err}")
        return [], 0
    meds = [r[3] for r in rows if r[3] is not None]
    if not meds:
        print("  ⛔ no measurable pages")
        return [], 0
    med = statistics.median(meds)
    print(f"kit median line width = {med:.0f} px  "
          f"(over {len(meds)} measurable page(s) of {len(rows)})")
    print(f"\n{'page':<8}{'lines':>6}{'medW':>8}{'% med':>8}"
          f"{'Rmargin':>9}{'touch':>8}  flag")
    hits = []
    for name, n, mn, md, mx, med_m, touch, note in rows:
        if md is None:
            print(f"{name:<8}{n:>6}{'-':>8}{'-':>8}{'-':>9}{'-':>8}  ⛔ {note}")
            hits.append((kit, name, "UNMEASURABLE"))
            continue
        pct = md / med * 100
        flag = ""
        # ★ PRIMARY SCREEN: no right margin. ⚠ NOT a verdict — an apparatus
        # sliver at the crop edge scores the same (matthew p18).
        known = KNOWN.get((kit, name))
        if known == "CLEAN":
            flag = "✅ screened SUSPECT but VERIFIED CLEAN by eye (apparatus sliver)"
        elif med_m is not None and med_m <= MARGIN_OK:
            if known == "TRUNCATED":
                flag = "⛔⛔ TRUNCATED — VERIFIED by eye; re-prep, discard reads"
                hits.append((kit, name, "TRUNCATED (verified)"))
            else:
                flag = "⚠⚠ SUSPECT (no right margin) — ADJUDICATE BY EYE, do not discard yet"
                hits.append((kit, name, "SUSPECT — needs an eye"))
        elif pct < TRUNCATED * 100:
            flag = "⚠⚠ SUSPECT (width outlier) — ADJUDICATE BY EYE"
            hits.append((kit, name, "SUSPECT — needs an eye"))
        elif pct < NARROW * 100:
            flag = "⚠ narrow, but margin is intact — likely a second cluster"
        if mn != mx:
            flag = (flag + f"  ⚠ widths vary within page ({mn}-{mx})").strip()
        if note:
            flag = (flag + "  " + note).strip()
        tt = f"{touch}/{n}" if touch is not None else "-"
        mm = med_m if med_m is not None else "-"
        print(f"{name:<8}{n:>6}{md:>8}{pct:>7.1f}%{mm:>9}{tt:>8}  {flag}")
    return hits, len(meds)


def selftest():
    """The control, both ways: a kit that cannot be measured must NOT pass,
    and a kit that can must still be able to.

    ⛔ The known-bad half is the point. Before 2026-09-19 an absent kit printed
    ✅ and exited 0, so this tool's clean bill of health meant nothing when the
    kit name was wrong - and `--kit-dir luke_kit2/p63`, which is how a caller
    naturally writes it, was exactly that case.
    """
    ok = True

    def run(label, argv, want_rc_nonzero):
        saved = sys.argv
        sys.argv = ["thorlaks_crop_widths.py"] + argv
        buf, out = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = main()
        except SystemExit as e:
            rc = e.code or 0
        finally:
            sys.stdout = out
            sys.argv = saved
        # want_rc_nonzero is None = "this case's rc is not the assertion";
        # printing a verdict for it would be an instrument reporting FAIL on a
        # test it is not running, which is its own kind of lie.
        if want_rc_nonzero is None:
            return True, buf.getvalue()
        good = bool(rc) == want_rc_nonzero
        print("  %-52s %s" % (label, "ok" if good
                              else "FAIL (rc=%s, wanted %s)"
                              % (rc, "nonzero" if want_rc_nonzero else "0")))
        return good, buf.getvalue()

    g, txt = run("an absent kit FAILS, it does not pass", ["_no_such_kit_"], True)
    ok &= g
    if "✅" in txt:
        print("  %-52s FAIL" % "...and it does NOT print the clean banner")
        ok = False
    else:
        print("  %-52s ok" % "...and it does NOT print the clean banner")

    g, _ = run("a flag-shaped argument is a usage error",
               ["--kit-dir", "luke_kit2/p63"], True)
    ok &= g

    real = sorted(d.name for d in PREP.iterdir() if d.is_dir()) if PREP.is_dir() else []
    if real:
        # ⚠ rc may legitimately be 1 here (a real kit really does hold a SUSPECT
        # page), so this half asserts on the BANNER, not the code: what must not
        # happen is "nothing measured". The rc expectation is therefore ignored.
        _g, txt = run("a real kit runs", [real[0]], None)
        if "NOTHING WAS MEASURED" in txt:
            print("  %-52s FAIL" % "a real kit measures something")
            ok = False
        else:
            print("  %-52s ok" % "a real kit measures something")
    else:
        print("  %-52s SKIP (no kits on this box)" % "a real kit measures something")

    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    kits = sys.argv[1:]
    if kits == ["--selftest"]:
        return selftest()
    # ⛔ This tool takes KIT NAMES positionally and has no flags. A token that
    # looks like one is a typo, and a typo used to be swallowed as a kit name
    # that did not exist - which then passed. Refuse instead.
    bad = [k for k in kits if k.startswith("-")]
    if bad:
        sys.stderr.write("thorlaks_crop_widths: no such option %s - this tool "
                         "takes KIT NAMES positionally, e.g.\n"
                         "    python tools/thorlaks_crop_widths.py luke_kit2\n"
                         % ", ".join(repr(b) for b in bad))
        return 2
    if not kits:
        kits = sorted(d.name for d in PREP.iterdir() if d.is_dir())
    hits = []
    measured = 0
    unmeasured = []
    for k in kits:
        h, m = report(k)
        hits += h
        measured += m
        if not m:
            unmeasured.append(k)
    print(f"\n{'=' * 76}")
    # ⛔ FIRST: a screen that measured nothing did not pass. This must outrank
    # the ✅ below, and it must outrank it even when some other kit was fine.
    if unmeasured:
        print("⛔ NOTHING WAS MEASURED in %d of %d kit(s): %s"
              % (len(unmeasured), len(kits), ", ".join(unmeasured)))
        print("   A check that could not run did NOT pass. Fix the kit name or "
              "the prep, then re-run.")
        if measured:
            print("   (%d page(s) in the other kit(s) WERE measured; their "
                  "result above stands on its own.)" % measured)
        return 2
    if hits:
        print(f"⛔ {len(hits)} page(s) need action before any vision read:")
        for kit, page, why in hits:
            print(f"   {kit}/{page}: {why}")
        print("\n▶ VERIFIED TRUNCATED: re-prep at full width and discard every "
              "judgement made on that page.")
        print("▶ SUSPECT: adjudicate BY EYE first — crop the rightmost ~320 px "
              "of ~6 lines, stack, upscale, and look. Sliced glyphs with no "
              "margin = truncated; a clean margin followed by a strip of OTHER "
              "text = an apparatus sliver and the page is FINE (matthew p18).")
        print("⛔ Do not discard a page on this screen's word alone.")
        return 1
    print("✅ no suspect or unmeasurable pages in the kits checked.")
    print("⚠ This checks the RIGHT EDGE only. It cannot see a page cropped at "
          "the bottom or LEFT, a wrong page, or a page at the wrong zoom.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
