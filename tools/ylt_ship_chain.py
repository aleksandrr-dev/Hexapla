# -*- coding: utf-8 -*-
"""Advance the ylt set toward a shippable build, ONE gated step at a time.

    python tools/ylt_ship_chain.py            # report where it is, change nothing
    python tools/ylt_ship_chain.py --advance  # do the next step, if its gate passes

## Why this exists

The ylt build gate was two commented-out lines guarded by PROSE ("do not
uncomment before the upload has landed"). Prose cannot be checked, so every
session re-litigated it from memory and asked the owner. This turns each
precondition into a MEASUREMENT and refuses to advance while any is unmet.

## ⛔ THE RULES IT ENFORCES, each one a bug that already happened

1. An index entry whose archive.org item is not current points chapters at a
   404 and the app SILENTLY FALLS BACK TO TTS - no error, nothing to debug.
   So the upload must be verified COMPLETE against the live item first.
2. The lexicon re-render rewrites 422 chapters. Uploading before it finishes
   means uploading them twice and paying an expensive full re-derive twice.
3. `partial: False` in the index builder checks .ogg and offsets ONLY. It does
   NOT check word alignment, so alignment is gated here instead.
4. A count is not a check. Every gate below states its denominator.

## ⚠ WHAT IT WILL NOT DO

It never judges audio QUALITY. `qa_rescreen_repairs` reports repeat/append
only; substitution has one ground-truth positive and mispronunciation has no
screen at all. This chain can say "clean on what can be detected" and nothing
stronger - and it prints that caveat rather than implying more.
It also never starts a GPU render and never force-pushes anything.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(r"C:\Projects\Hexapla")
DATA = Path(r"C:\Projects\Hexapla-releases")
NAR = DATA / "narration" / "ylt"
BUILDER = REPO / "tools" / "build_audio_index_gen.py"
INDEX = REPO / "app" / "src" / "main" / "assets" / "audio_index_gen.json"
VENV = REPO / "tools" / ".chatterbox_venv" / "Scripts" / "python.exe"
CANON = 1189


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


# ── gates ──────────────────────────────────────────────────────────────────
def gate_render():
    """No GPU re-render still in flight."""
    if os.name != "nt":
        return None, "not windows"
    r = _run(["powershell", "-NoProfile", "-Command",
              "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "
              "'repair_verses\\.py|narrate\\.py' -and $_.CommandLine -notmatch "
              "'CimInstance|ylt_ship_chain' } | Measure-Object).Count"])
    n = (r.stdout or "").strip()
    if not n.isdigit():
        return None, f"could not count render processes ({n!r}) - REFUSING to guess"
    return int(n) == 0, f"{n} render process(es) running"


def gate_audio():
    n = len(glob.glob(str(NAR / "*" / "*.ogg")))
    return n >= CANON, f"{n}/{CANON} chapters have audio"


def gate_aligned():
    n = len(glob.glob(str(NAR / "*" / "*.w.json")))
    return n >= CANON, f"{n}/{CANON} chapters aligned (.w.json)"


# ── append-class flags a HUMAN EAR has already ruled on ────────────────────
# ⛔⛔ THIS IS NOT A WAY TO RELAX THE GATE, AND IT MUST NEVER BECOME ONE.
# The gate's job is «no append-class flag ships unexamined». It had no memory,
# so four verses the owner had ALREADY HEARD blocked it forever and no amount
# of re-running could change that — three 79-minute passes on 2026-09-07 proved
# the point. The fix is to record the rulings, not to lower the bar:
#
#   * an entry means A PERSON LISTENED and said this take is acceptable;
#   * ANY append flag NOT in this table still fails the gate, loudly;
#   * removing a verse from the queue is NOT the same as ruling on it. Every
#     entry names who ruled and when, because "someone decided this once" with
#     no name attached is exactly how a false clean bill gets inherited.
#
# (book, chapter, verse) -> (verdict, who/when)
ADJUDICATED_APPENDS = {
    (3, 9, 22): ("heard by the owner — it is «Ammihud» read as «ami hood», a "
                 "MISPRONUNCIATION being reported as an append; the appended "
                 "word is an ASR artefact, not spoken audio",
                 "owner ear, 2026-09-06 ear queue"),
    (4, 32, 8): ("heard by the owner in the 2026-09-06 clip set; «the other 21 "
                 "were fine» (owner, 2026-09-07)",
                 "owner ear, 2026-09-06 ear queue"),
    (19, 17, 6): ("heard by the owner in the 2026-09-06 clip set; «the other 21 "
                  "were fine» (owner, 2026-09-07)",
                  "owner ear, 2026-09-06 ear queue"),
    (11, 2, 16): ("TEXT-EXPLAINED — YLT prints «make this valley ditches "
                  "ditches»; the doubling is scripture. qa_text_explained.py "
                  "classifies it, controls 8/8 including two negatives",
                  "tool + text, 2026-09-06"),
    # Surfaced by the FIRST gate run after the double-e re-render (the screen
    # re-judged 2927 verses, up from 2317, because 144 chapters were rewritten).
    # ⚠ qa_text_explained.py did NOT clear it — the flag is `append:'` and the
    # verse genuinely ends `six sons;'` where Leah's speech closes, but the
    # tool cannot tell a printed quote mark from a spoken one, so this needed
    # an ear and got one. ⛔ Never read «the punctuation explains it» as a
    # ruling; that reasoning was available before the ear and was not enough.
    (0, 29, 20): ("Genesis 30:20 — owner heard the shipped clip and ruled it "
                  "«sounds fine». The `append:'` flag is the closing quote of "
                  "Leah's speech, an ASR artefact, not spoken audio",
                  "owner ear, 2026-09-07 gate run"),
}

# «  3/9 v22  FAIL ['append:hood']  …»
FLAG_LINE = re.compile(r"^\s*(\d+)/(\d+)\s+v(\d+)\s+FAIL\s+\[(.*?)\]")


def _append_flags(out):
    """-> (adjudicated, unruled) lists of (book, chapter, verse, flags).

    ⚠ Parses the VERSE off each flag line rather than counting «append:»
    occurrences. The old count could not tell a new defect from a known one,
    so it treated every ruling as if it had never happened.
    """
    adjudicated, unruled = [], []
    for ln in out.splitlines():
        m = FLAG_LINE.match(ln)
        if not m or "append:" not in m.group(4):
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        (adjudicated if key in ADJUDICATED_APPENDS else unruled).append(
            (key, m.group(4)))
    # de-duplicate: a verse is re-judged once per repair record
    seen, uniq = set(), []
    for key, flags in unruled:
        if key not in seen:
            seen.add(key)
            uniq.append((key, flags))
    return sorted({k for k, _ in adjudicated}), uniq


def gate_screens():
    """No UNRULED append-class flag across the repaired set.

    ⚠ Repeat-class flags the PRINTED TEXT explains are expected and are not a
    defect. Append-class flags a person has already heard are listed in
    ADJUDICATED_APPENDS above — read that comment before touching this.
    """
    if not VENV.exists():
        return None, "chatterbox venv missing"
    # ⛔⛔ DO NOT REINSTATE A BARE `if r.returncode != 0: return None`.
    # `qa_rescreen_repairs.py` ends with `return 1 if hits else 0`, so exit 1
    # is its DOCUMENTED "I ran correctly and found still-failing verses" —
    # not a crash. Treating it as ERROR threw away the result of a 79-minute
    # ASR pass three times on 2026-09-07 and reported «no information» over a
    # screen that had in fact completed.
    # ▶ The SUMMARY line is the evidence that the tool ran. Parse first, and
    #   judge the exit code only when the summary is absent.
    log = DATA / "narration" / "logs" / "ylt_screens_last.log"
    r = _run([str(VENV), str(REPO / "tools" / "qa_rescreen_repairs.py"),
              "--set", "ylt"], cwd=str(DATA))
    out = (r.stdout or "") + (r.stderr or "")
    try:                       # persist it — an hour-long pass must survive
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(out, encoding="utf-8", errors="replace")
    except OSError:
        pass
    m = re.search(r"SUMMARY\s+(\d+) repaired verse\(s\) re-judged, "
                  r"(\d+) STILL FAILING", out)
    if not m:
        return None, (f"qa_rescreen_repairs exited {r.returncode} and printed "
                      f"no parseable SUMMARY - REFUSING to guess (see {log})")
    if r.returncode not in (0, 1):
        return None, (f"qa_rescreen_repairs exited {r.returncode}, which is "
                      f"neither of its documented codes - REFUSING to guess")
    ruled, unruled = _append_flags(out)
    detail = (f"{m.group(1)} verses re-judged, {m.group(2)} flagged; "
              f"append-class: {len(ruled)} already ruled on, "
              f"{len(unruled)} UNRULED  [log: {log.name}]")
    if unruled:
        detail += "\n" + "\n".join(
            f"           ⛔ UNRULED {b}/{c} v{v}  {flags} — an ear must hear "
            f"this before ylt ships" for (b, c, v), flags in unruled)
    return not unruled, detail


def gate_upload():
    """The live archive.org item carries every local file."""
    r = _run([sys.executable, str(REPO / "tools" / "upload_narration.py"),
              "ylt", "--dry-run"], cwd=str(DATA))
    if r.returncode != 0:
        return None, f"upload dry-run exited {r.returncode} - cannot read the live item"
    m = re.search(r"outstanding:\s*(\d+) of (\d+) to send", r.stdout or "")
    if not m:
        return None, "could not parse the outstanding line - REFUSING to guess"
    out, tot = int(m.group(1)), int(m.group(2))
    return out == 0, f"{out} of {tot} files still to send to the live item"


# (name, fn, cheap) — an EXPENSIVE gate is skipped once an earlier one has
# already failed. Two reasons, both measured 2026-09-05:
#   * cost: gate_screens re-judges every repaired verse with ASR (~8 min) and
#     gate_upload reads the live archive.org item. Running them on every cycle
#     of a scheduled chain, only to be blocked by a render that is obviously
#     still going, is pure waste.
#   * CORRECTNESS: while a re-render is writing <chapter>.qa.json, the screen
#     can read one mid-write and refuse it — a real ERROR that means nothing
#     except "you asked at a bad moment". Skipping it while the render gate is
#     still WAITing removes that false alarm at the source.
# ⚠ A skipped gate is reported as SKIP, never as PASS. It is not evidence.
GATES = [("re-render finished", gate_render, True),
         ("audio complete", gate_audio, True),
         ("word alignment complete", gate_aligned, True),
         ("screens: no append-class flags", gate_screens, False),
         ("archive.org item current", gate_upload, False)]


def index_has_ylt():
    try:
        return "ylt" in json.loads(INDEX.read_text(encoding="utf-8"))
    except Exception:
        return False


def uncomment_entry():
    """Uncomment the ylt SETS row in build_audio_index_gen.py."""
    s = BUILDER.read_text(encoding="utf-8")
    old = ('    # {"tid": "ylt", "dir": "ylt", "asset": "en_ylt.json",\n'
           '    #  "item": "hexapla-audio-ylt-1898", "partial": False},\n')
    new = ('    {"tid": "ylt", "dir": "ylt", "asset": "en_ylt.json",\n'
           '     "item": "hexapla-audio-ylt-1898", "partial": False},\n')
    if new in s:
        return True, "already uncommented"
    if s.count(old) != 1:
        return False, "the commented ylt row is not where expected - REFUSING to edit blindly"
    BUILDER.write_text(s.replace(old, new), encoding="utf-8")
    return True, "uncommented the ylt row"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--advance", action="store_true",
                    help="perform the next step when every gate passes")
    a = ap.parse_args()

    print("ylt ship chain - every line below is measured, not remembered\n")
    blocked = []
    for name, fn, cheap in GATES:
        if blocked and not cheap:
            print(f"  [SKIP ] {name:<32} not evaluated — an earlier gate is unmet")
            blocked.append((name, "SKIP"))
            continue
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = None, f"{type(e).__name__}: {e}"
        mark = {True: "PASS", False: "WAIT", None: "ERROR"}[ok]
        print(f"  [{mark:5}] {name:<32} {detail}")
        if ok is not True:
            blocked.append((name, mark))

    print(f"\n  index currently ships ylt: {index_has_ylt()}")

    if blocked:
        print(f"\n⛔ {len(blocked)} gate(s) not passed - not advancing.")
        if any(m == "ERROR" for _, m in blocked):
            print("⚠ An ERROR is a check that COULD NOT RUN. That is not a pass, and it is "
                  "not a fail - it is no information. Fix the check before trusting anything.")
        return 1

    print("\n✅ every gate passes.")
    if not a.advance:
        print("   report only; re-run with --advance to open the gate and build.")
        return 0

    ok, msg = uncomment_entry()
    print(f"   index entry: {msg}")
    if not ok:
        return 2
    r = _run([sys.executable, str(BUILDER)], cwd=str(REPO))
    print(f"   rebuild index: exit {r.returncode}")
    if r.returncode != 0 or not index_has_ylt():
        print("⛔ the index does not contain ylt after rebuilding - stopping before the build.")
        return 3
    print("   ✅ audio_index_gen.json now ships ylt")

    # ── build both artifacts ───────────────────────────────────────────────
    gradlew = str(REPO / "gradlew.bat")
    env = dict(os.environ)
    env.setdefault("JAVA_HOME", r"C:\Program Files\Android\Android Studio\jbr")
    for task, what in [("bundlePlayRelease", "Play AAB"),
                       ("assembleRustoreRelease", "RuStore APK")]:
        print(f"   building {what} ({task}) ...", flush=True)
        r = _run([gradlew, task], cwd=str(REPO), env=env)
        if r.returncode != 0:
            tail = (r.stdout or "")[-1500:] + (r.stderr or "")[-1500:]
            print(f"⛔ {task} FAILED (exit {r.returncode}):\n{tail}")
            return 4
        print(f"   ✅ {what} built")

    # ── the donation grep, WITH ITS POSITIVE CONTROL ───────────────────────
    # ⚠⚠ 0 on the Play artifact means NOTHING on its own. The same grep must
    #    return 1+ on the RuStore artifact, or the grep itself is broken - the
    #    play path silently regressed for five releases (1.4.0-1.5.1) exactly
    #    this way. A 0/0 result is a BROKEN GREP, not a clean build.
    aab = sorted(REPO.glob("app/build/outputs/bundle/playRelease/*.aab"))
    apk = sorted(REPO.glob("app/build/outputs/apk/rustore/release/*.apk"))
    if not aab or not apk:
        print(f"⛔ cannot find both artifacts (aab={len(aab)}, apk={len(apk)}) - "
              "the donation grep cannot run, so this build is NOT cleared.")
        return 5

    def yoo(path, member):
        p1 = subprocess.Popen(["unzip", "-p", str(path), member], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["grep", "-ac", "yoomoney"], stdin=p1.stdout,
                              stdout=subprocess.PIPE)
        p1.stdout.close()
        out, _ = p2.communicate()
        try:
            return int((out or b"0").decode().strip() or 0)
        except ValueError:
            return -1

    play = yoo(aab[-1], "base/dex/classes*.dex")
    rust = yoo(apk[-1], "classes*.dex")
    print(f"\n   donation grep: play={play} (must be 0)   rustore={rust} (must be 1+)")
    if rust < 1:
        print("⛔ THE POSITIVE CONTROL FAILED. The RuStore artifact should contain "
              "yoomoney. The grep is broken, so play=0 proves NOTHING. NOT cleared.")
        return 6
    if play != 0:
        print("⛔ the Play artifact contains the donation path. NOT cleared.")
        return 7
    print("   ✅ donation grep passes WITH its positive control")
    print(f"\n✅ built and cleared:\n     {aab[-1]}\n     {apk[-1]}")
    print("⚠ 'clean on what can be detected': these screens cover repeat/append only. "
          "Substitution has one ground-truth positive; mispronunciation has no screen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
