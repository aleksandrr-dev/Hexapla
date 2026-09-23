# -*- coding: utf-8 -*-
"""Is every rendered narration set UPLOADED and WIRED INTO THE APP?

    PYTHONIOENCODING=utf-8 python tools/audit_narration_shipped.py
    ... --offline          # skip the network; live columns report UNKNOWN
    ... --set ylt          # one set
    ... --selftest         # controls, must exit 0

WHY THIS EXISTS
---------------
On 2026-09-20 the owner reported hearing the wrong voice for the English NT.
Three things were true at once and no single check would have shown any of
them:

  · ylt was rendered (1189) AND uploaded (1189 live) AND its index entry was
    still COMMENTED OUT, so the app shipped no ylt at all;
  · wyc was rendered (1345) AND uploaded (1345 live) with NO index entry at
    all, not even a commented one;
  · the RELEASED 1.6.4 APK carried only wbt/kxii/syn/csl, so even a corrected
    source tree would not change what is on a phone until a rebuild.

An index entry that is missing does not fail. An item that does not exist does
not fail either - the app falls back to LibriVox or TTS SILENTLY. So the only
way to know is to derive all three layers at once and print them together.

THE THREE LAYERS, and they are independent
------------------------------------------
  RENDERED   narration/<dir>/<book>/<chapter>.ogg on disk
  UPLOADED   the same names present on the live archive.org item
  WIRED      a SETS entry here AND the tid present in the built asset
  SHIPPED    the tid present in the RELEASED apk/aab - a rebuild is a
             separate act and this column is the one that answers
             "why am I still hearing the old voice?"

⛔ A COUNT THAT COULD NOT BE TAKEN RETURNS -1 AND PRINTS WHY.
It never returns 0, because 0 is a real and different answer ("nothing there")
and the two must never be confused. Every network failure is loud.

⚠ This audit reports COVERAGE OF WHAT WAS RENDERED. It is not a claim that the
rendered set is the whole canon: tyn is 451 chapters because Tyndale never
translated the rest, and that is correct. The `expect` column is the set's own
non-empty-book denominator, taken from the same asset the builder uses.
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_audio_index_gen as B

try:
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
except ImportError:                                    # pragma: no cover
    from urllib2 import urlopen, URLError, HTTPError   # noqa

UNKNOWN = -1
META = "https://archive.org/metadata/%s"
DL = "https://archive.org/download/%s/%s"

# Every narration folder that holds a render. Derived from disk, NOT typed, so
# a set rendered tomorrow shows up here without editing this file.
def rendered_dirs():
    if not B.NARRATION.is_dir():
        return None
    out = []
    for p in sorted(B.NARRATION.iterdir()):
        if not p.is_dir():
            continue
        n = p.name
        # quarantines, originals and scratch are not sets
        if ("quarantine" in n or n.startswith("_") or "_qa_fail" in n
                or n in ("logs",) or "_originals" in n or "_announce" in n
                or "_pre" in n or "_test" in n or "_predates" in n):
            continue
        if any(p.glob("*/*.ogg")):
            out.append(n)
    return out


def local_oggs(d):
    """-> set of '<book>/<chapter>.ogg' relative names, or None if unreadable."""
    src = B.NARRATION / d
    if not src.is_dir():
        return None
    got = set()
    for b in src.iterdir():
        if not b.is_dir() or not b.name.isdigit():
            continue
        for f in b.glob("*.ogg"):
            got.add("%s/%s" % (b.name, f.name))
    return got


def live_oggs(item, flat=None):
    """-> set of relative ogg names on the LIVE item.

    ⛔ Returns None on ANY failure. archive.org answers 200 with a stub for an
    item that does not exist, so the discriminator is the FILE LIST, never the
    status code - probing the status alone reported four non-existent items as
    present during this audit."""
    try:
        raw = urlopen(META % item, timeout=60).read().decode("utf-8", "replace")
    except (URLError, HTTPError, OSError):
        return None
    try:
        meta = json.loads(raw)
    except ValueError:
        return None
    if not meta.get("files"):
        return set()            # a real answer: the item holds nothing
    return {f["name"] for f in meta["files"]
            if f.get("name", "").endswith(".ogg")}


def probe(item, rel):
    """Fetch ONE real chapter. ⚠ A listing is not a file - HEAD/listing said
    ylt was fine while `ylt/40/1.ogg` 404'd, because the path was wrong."""
    try:
        r = urlopen(DL % (item, rel), timeout=60)
        n = len(r.read(65536))
        return n if n > 0 else 0
    except (URLError, HTTPError, OSError):
        return UNKNOWN


def expected(s):
    """The set's own denominator, DERIVED THE WAY THE BUILDER DERIVES IT.

    ⚠ It must be `bible_live_chapters` (verse-holding chapters only), not
    `bible_chapter_counts`. Using the latter reported kxii as "short
    1336/1346" on the first run of this audit while the builder itself said
    1336/1336 and passed its own partial:False guard - the 10 are placeholder
    chapter slots that hold no verses and must never be rendered. A second
    reimplementation of a denominator is how an instrument invents a defect.
    """
    try:
        live = B.bible_live_chapters(s["asset"])
    except Exception:
        return UNKNOWN, UNKNOWN
    last = len(live) if s.get("apocrypha") else B.CANON_BOOKS
    live = live[:last]
    return sum(len(ch) for ch in live), sum(1 for ch in live if ch)


def shipped_tids(path):
    """tids present in a built/released index asset, or None if unreadable."""
    try:
        if str(path).endswith((".apk", ".aab")):
            import zipfile
            with zipfile.ZipFile(str(path)) as z:
                name = [n for n in z.namelist()
                        if n.endswith("assets/audio_index_gen.json")
                        or n == "assets/audio_index_gen.json"]
                if not name:
                    return set()
                raw = z.read(name[0]).decode("utf-8", "replace")
        else:
            with io.open(str(path), encoding="utf-8") as fh:
                raw = fh.read()
    except Exception:
        return None
    return set(re.findall(r'"([A-Za-z0-9_]+)":\{"0":\{"base"', raw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--set", dest="only")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    by_dir = {s["dir"]: s for s in B.SETS}
    disk = rendered_dirs()
    if disk is None:
        sys.stderr.write("CANNOT RUN: %s is not a directory. A check that "
                         "cannot run did not pass.\n" % B.NARRATION)
        return 2

    built = shipped_tids(B.OUT)
    rel = sorted(B.NARRATION.parent.glob("Hexapla-*-rustore.apk"))
    released = shipped_tids(rel[-1]) if rel else None

    print("RENDERED -> UPLOADED -> WIRED -> SHIPPED, all four derived.\n")
    print("%-6s %-5s %7s %7s %7s  %-5s %-6s %s"
          % ("dir", "tid", "local", "live", "expect", "wired", "shippd", "verdict"))
    print("-" * 86)

    problems = []
    # ⚠ The UNION, not the disk scan. A SETS entry may point at a directory the
    # scan filters out (a quarantine), and that entry is precisely the one most
    # worth printing - gen1599 does exactly this and was invisible until the
    # audit iterated both sides.
    for d in sorted(set(disk) | set(by_dir)):
        if a.only and d != a.only and by_dir.get(d, {}).get("tid") != a.only:
            continue
        s = by_dir.get(d)
        loc = local_oggs(d)
        nloc = UNKNOWN if loc is None else len(loc)
        if s is None:
            # It may still be served THROUGH a quarantine entry - that is the
            # Geneva arrangement, and it is not the same thing as unwired.
            via = [q for q in by_dir if q.startswith(d + "_quarantine")]
            if via:
                print("%-6s %-5s %7d %7s %7s  %-5s %-6s %s"
                      % (d, by_dir[via[0]]["tid"], nloc, "-", "-",
                         "via", "-", "indexed via %s - see that row" % via[0]))
            else:
                print("%-6s %-5s %7d %7s %7s  %-5s %-6s %s"
                      % (d, "-", nloc, "-", "-", "NO", "NO",
                         "NOT WIRED AT ALL - no SETS entry"))
                problems.append("%s: rendered (%d) but has NO entry in "
                                "build_audio_index_gen.SETS - it is uploaded "
                                "or not, but the app can never reach it"
                                % (d, nloc))
            continue

        tid, item = s["tid"], s["item"]
        exp, nbooks = expected(s)
        if a.offline:
            nlive, live = UNKNOWN, None
        else:
            live = live_oggs(item)
            nlive = UNKNOWN if live is None else len(live)

        wired = built is not None and tid in built
        shipd = released is not None and tid in released

        verdict = []
        if nlive == UNKNOWN and not a.offline:
            verdict.append("LIVE UNREADABLE")
            problems.append("%s: could not read the live item %s - NOT a 0"
                            % (tid, item))
        elif live is not None and loc is not None:
            flat = s.get("flat")
            if flat:
                want = {flat.format(b=r.split("/")[0],
                                    c=r.split("/")[1].split(".")[0])
                        for r in loc}
            else:
                want = loc
            missing = want - live
            if missing:
                verdict.append("%d NOT UPLOADED" % len(missing))
                problems.append("%s: %d rendered chapter(s) are not on %s, "
                                "e.g. %s" % (tid, len(missing), item,
                                             ", ".join(sorted(missing)[:3])))
        if exp != UNKNOWN and nloc != UNKNOWN and nloc < exp:
            verdict.append("render short %d/%d" % (nloc, exp))
        if not wired:
            verdict.append("NOT WIRED")
            problems.append("%s: uploaded but absent from the built index"
                            % tid)
        if not shipd:
            verdict.append("not in released apk")
        if s.get("partial"):
            verdict.append("partial:True")
        # ★ THE GENEVA TRAP. An entry may point `dir` at a QUARANTINE on
        # purpose: the index embeds the verse offsets of the audio that is
        # actually STREAMED, so while archive.org still serves the old render
        # it must be built from the old render. That is correct - and it
        # silently stops being correct the moment the re-render is uploaded,
        # because then the app ships offsets that drift against the audio.
        # Nothing else notices, so this does.
        if "quarantine" in d:
            fresh = d.split("_quarantine")[0]
            nfresh = local_oggs(fresh)
            if nfresh:
                verdict.append("dir is the QUARANTINE; %s holds %d"
                               % (fresh, len(nfresh)))
                problems.append(
                    "%s: `dir` points at %s, but a re-render sits in %s (%d "
                    "chapter(s)). The index is built from the OLD audio. That "
                    "is right ONLY while the item still serves the old audio - "
                    "upload the re-render, then point dir at %s and REBUILD, "
                    "or the app ships offsets that drift against what plays."
                    % (tid, d, fresh, len(nfresh), fresh))

        print("%-6s %-5s %7d %7s %7s  %-5s %-6s %s"
              % (d, tid, nloc,
                 "?" if nlive == UNKNOWN else nlive,
                 "?" if exp == UNKNOWN else exp,
                 "yes" if wired else "NO",
                 "yes" if shipd else "NO",
                 "; ".join(verdict) if verdict else "ok"))

    print("-" * 86)
    if released is None:
        print("⚠ no Hexapla-*-rustore.apk found - the SHIPPED column is "
              "UNKNOWN, not 'no'.")
    else:
        print("shipped column read from: %s" % rel[-1].name)
    print("\n⚠ WIRED is the source tree. SHIPPED is the phone. A set that is "
          "wired but\n  not shipped needs a REBUILD - that is why the owner "
          "still hears the old voice.")
    if problems:
        print("\n%d PROBLEM(S):" % len(problems))
        for p in problems:
            print("  · %s" % p)
        return 1
    print("\n[ok] every rendered set is uploaded and wired.")
    return 0


def selftest():
    ok = True

    def chk(label, got, want):
        good = got == want
        print("  %-52s got=%-8s want=%-8s %s"
              % (label, got, want, "ok" if good else "FAIL"))
        return good

    # ★ THE CONTROL THAT MATTERS. archive.org returns HTTP 200 with a stub for
    # an item that does not exist, so a status-code probe reports a missing
    # item as present. Four invented names did exactly that during this audit.
    # live_oggs must distinguish them by the FILE LIST.
    print("audit_narration_shipped selftest")
    # ★ THE ONE THAT ACTUALLY BITES, and it needs the network to mean anything.
    # An invented item must come back EMPTY, and a known-good item NON-EMPTY.
    # ⛔ Do not weaken this to a status-code check: that is the bug it exists
    # to catch. If the network is down this says so and FAILS, because a
    # control that cannot run did not pass.
    if os.environ.get("HEXAPLA_AUDIT_OFFLINE"):
        print("  %-52s SKIPPED (HEXAPLA_AUDIT_OFFLINE)" % "live item discrimination")
    else:
        bogus = live_oggs("hexapla-audio-no-such-item-2026")
        real = live_oggs("hexapla-audio-ylt-1898")
        ok &= chk("an item that does not exist lists 0 oggs",
                  UNKNOWN if bogus is None else len(bogus), 0)
        ok &= chk("a real item lists >0 oggs (proves it is not always 0)",
                  bool(real), True)

    # a failed read is -1 / None, never a plausible number
    ok &= chk("local_oggs on a missing dir is None (never 0)",
              local_oggs("__no_such_set__"), None)
    ok &= chk("shipped_tids on a missing file is None (never empty set)",
              shipped_tids("__no_such_file__.json"), None)
    # and on the real built asset it finds the sets
    got = shipped_tids(B.OUT)
    ok &= chk("shipped_tids reads the built asset",
              isinstance(got, set) and len(got) > 0, True)
    ok &= chk("every SETS dir is unique",
              len({s["dir"] for s in B.SETS}), len(B.SETS))
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
