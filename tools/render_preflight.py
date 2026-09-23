# -*- coding: utf-8 -*-
"""Pre-launch checks for a narration render, and the free post-launch screen.

    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\render_preflight.py check  --lang sv --books 66-82
    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\render_preflight.py launch --lang sv --books 66-82
    python tools\\render_preflight.py report --lang sv [--since 50]

## Why

Every chatterbox set rendered before 2026-09-03 shipped (or nearly shipped)
with a tail defect in ~13 % of chapters, found days to weeks later by a 16-hour
sweep, and repaired by re-rendering whole chapters. Each of the things that let
that happen is a check here, run BEFORE the GPU is committed:

  1. the verse gate's own validation stamp is present and newer than the gate
     code (`qa_gate.py --validate`) — a check that was never validated is not
     a check (two heuristics for this defect looked fine and were wrong);
  2. the ASR worker actually starts and answers for THIS set's language — a
     gate that cannot run must not look like a gate that passed;
  3. no HEXAPLA_NO_GATE in the environment, and the other switches are shown;
  4. the GPU is not held by another render/repair (one card);
  5. the voice reference and the asset exist, the alignment set KEY is known
     (kxii for sv, syn for ru, csl for cu, gen1599 for gnv);
  6. the log target is FRESH — PowerShell's -RedirectStandardOutput truncates
     an existing file, which destroyed flag history once;
  7. the uploader excludes *.qa.json (or the QA record goes public);
  8. the book spec parses and the skip-existing count is printed, so nobody
     expects a plain re-run to regenerate a condemned chapter;
  9. disk headroom.

`check` writes `_work/preflight_<lang>.ok` on success; the Claude Code hook
(`~/.claude/hooks/guard_hexapla_bash.py`) refuses to launch narrate.py without
a stamp younger than 6 h. `launch` prints the exact detached command with a
fresh log name — it does NOT run it; starting a GPU job is the owner's call.

`report` reads the `.qa.json` the gate writes per chapter and prints judged /
re-drawn / still-failing / UNJUDGED per book. It is the "screen the first 50
chapters" gate from CLAUDE.md, at zero model cost, because the screening
already happened in-line. Exit 1 if anything is unjudged or the failing rate
is above 2 % of verses — stop the render and look before it does 1,189 more.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

DATA = Path("C:/Projects/Hexapla-releases")
NARRATION = DATA / "narration"
WORK = DATA / "_work"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# ⚠⚠ SELFTEST-ONLY KNOWN-BAD CONTROL. True only while selftest() runs, so it can
# never blind a real report. See ignore_unjudged().
_IN_SELFTEST = False


def ignore_unjudged():
    """Known-bad control: treat an unjudged chapter as judged-and-clean.

    Reinstates precisely the pre-2026-09-03 condition in which a render was
    believed on the strength of nothing. Under it a corpus that was never
    screened reports UNJUDGED 0 and rc 0.

    ⛔ Gated on _IN_SELFTEST so it can never change a real run's verdict.
    ⚠ Distinct from the tool's own HEXAPLA_NO_GATE, which is a check within
    cmd_check; this control touches only cmd_report.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_IGNORE_UNJUDGED") == "1"

_results = []


def item(name, ok, detail="", warn=False):
    tag = "PASS" if ok else ("WARN" if warn else "FAIL")
    _results.append((tag, name, detail))
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    return ok


def parse_books(spec, n_books):
    if not spec:
        return None
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return [b for b in out if 0 <= b < n_books]


def gpu_holders():
    if os.name != "nt":
        return []
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "
         "'narrate\\.py|repair_verses\\.py' -and $_.CommandLine -notmatch 'render_preflight' "
         "} | ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    return [l for l in (r.stdout or "").splitlines() if "python" in l.lower()]


def gpu_free_mib():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total",
                            "--format=csv,noheader,nounits"], capture_output=True,
                           text=True, creationflags=NO_WINDOW)
        used, total = (int(x) for x in r.stdout.strip().split(","))
        return total - used, total
    except Exception:
        return None, None


def cmd_check(a):
    import narrate
    from align_words import SETS
    lang = a.lang
    cfg = narrate.LANG_CONFIG[lang]
    print(f"preflight for a `narrate.py --lang {lang}` render (engine {cfg['engine']})")

    # 1. gate validation stamp
    stamp = WORK / "gate_validation.json"
    if stamp.exists():
        s = json.loads(stamp.read_text(encoding="utf-8"))
        stale = [n for n, m in s.get("code_mtimes", {}).items()
                 if (HERE / n).exists() and int((HERE / n).stat().st_mtime) > m]
        item("gate validated", bool(s.get("ok")) and not stale,
             f"{s.get('ts')} confirmed {s.get('confirmed')}/10 controls "
             f"{s.get('controls_flagged')}/40" + (f"; CODE CHANGED SINCE: {stale}" if stale else ""))
    else:
        item("gate validated", False, "no _work/gate_validation.json — run "
             "tools\\.chatterbox_venv\\Scripts\\python.exe tools\\qa_gate.py --validate")

    # 2. ASR worker answers for this language
    asr_lang = narrate.ASR_LANG.get(lang)
    if asr_lang is None:
        item("ASR language known", False, f"narrate.ASR_LANG has no entry for {lang}")
    else:
        with tempfile.TemporaryDirectory() as td:
            import numpy as np
            import soundfile as sf
            t = np.linspace(0, 1.0, 16000, dtype="float32")
            w = Path(td) / "tone.wav"
            sf.write(str(w), 0.1 * np.sin(2 * np.pi * 220 * t), 16000)
            t0 = time.time()
            r = narrate.asr_transcribe(str(w), asr_lang)
        item("ASR worker answers", r is not None,
             f"lang {asr_lang}, model {r.get('model') if r else '-'}, "
             f"{time.time() - t0:.1f}s incl. load" if r else "worker did not answer — "
             "check tools/.kokoro_venv has faster-whisper")

    # 3. environment switches
    env = {k: v for k, v in os.environ.items() if k.startswith("HEXAPLA_")}
    item("HEXAPLA_NO_GATE unset", "HEXAPLA_NO_GATE" not in env,
         f"env: {env or 'none'}")
    if "HEXAPLA_NARRATION_OUT" in env:
        item("output redirected", True, env["HEXAPLA_NARRATION_OUT"], warn=True)

    # 4. GPU
    holders = gpu_holders()
    item("GPU not held by another render/repair", not holders,
         "; ".join(h[:90] for h in holders) if holders else "no narrate/repair process")
    free, total = gpu_free_mib()
    if free is not None:
        need = 5000 if cfg["engine"] in ("chatterbox", "cosyvoice3") else 0
        item("VRAM headroom", free >= need, f"{free} MiB free of {total}")

    # 5. voice, asset, alignment key
    voice = cfg.get("voice", "")
    if cfg["engine"] in ("chatterbox", "cosyvoice3"):
        item("voice reference exists", Path(voice).exists(), voice)
    asset = narrate.ASSETS / cfg["asset"]
    item("asset exists", asset.exists(), str(asset))
    keys = [k for k, v in SETS.items() if v["dir"] == lang]
    item("alignment set key known", bool(keys),
         f"align_words.py --set {keys[0]}" if keys else f"no SETS entry with dir={lang}")

    # 6. fresh log name
    ts = time.strftime("%Y%m%d_%H%M")
    log = NARRATION / "logs" / f"{lang}_render_{ts}.log"
    item("log target is fresh", not log.exists(), str(log))

    # 7. uploader excludes .qa.json
    up = (HERE / "upload_narration.py").read_text(encoding="utf-8", errors="replace")
    item("uploader excludes *.qa.json", ".qa.json" in up)

    # 8. books spec and skip-existing
    books = narrate.load_bible(lang)
    sel = parse_books(a.books, len(books))
    if sel is None:
        sel = cfg.get("default_books") or list(range(len(books)))
    todo = done = 0
    for b in sel:
        for c, ch in enumerate(books[b]["chapters"]):
            if not any(v.strip() for v in ch):
                continue
            if (NARRATION / lang / str(b) / f"{c}.ogg").exists():
                done += 1
            else:
                todo += 1
    item("book spec", todo > 0, f"{len(sel)} book(s): {todo} chapter(s) to render, "
         f"{done} already on disk and WILL BE SKIPPED (a condemned chapter needs "
         f"repair_verses.py, not a re-run)", warn=todo == 0)

    # 9. disk
    free_gb = shutil.disk_usage(str(NARRATION)).free / 2**30
    item("disk headroom", free_gb >= 10, f"{free_gb:.0f} GB free")

    fails = [r for r in _results if r[0] == "FAIL"]
    print()
    if fails:
        print(f"⛔ {len(fails)} check(s) FAILED — do not launch:")
        for _, n, d in fails:
            print(f"   - {n}: {d}")
        return 1
    WORK.mkdir(parents=True, exist_ok=True)
    ok = WORK / f"preflight_{lang}.ok"
    ok.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "lang": lang,
                              "books": a.books, "log": str(log)}), encoding="utf-8")
    print(f"✅ all checks passed — stamp {ok} (valid 6 h for the launch hook)")
    print("▶ next: `render_preflight.py launch` prints the command; after ~50 "
          "chapters run `render_preflight.py report` BEFORE letting it continue.")
    return 0


def cmd_launch(a):
    ok = WORK / f"preflight_{a.lang}.ok"
    if not ok.exists() or time.time() - ok.stat().st_mtime > 6 * 3600:
        print("⛔ no fresh preflight stamp — run `render_preflight.py check` first")
        return 1
    s = json.loads(ok.read_text(encoding="utf-8"))
    log = s["log"]
    err = log[:-4] + ".err"
    py = "C:/Projects/Hexapla/tools/.chatterbox_venv/Scripts/python.exe"
    books = f" --books {a.books}" if a.books else ""
    print("Detached launch (Git Bash), from the DATA directory, fresh log — copy exactly:\n")
    print(f"  cd /c/Projects/Hexapla-releases && nohup \"{py}\" -u "
          f"C:/Projects/Hexapla/tools/narrate.py --lang {a.lang}{books} "
          f"> \"{log}\" 2> \"{err}\" &\n")
    print("⚠ This tool does not start it. Starting a GPU job is the owner's decision.")
    print("⚠ Never point a redirect at an existing log. Never start it while "
          "another narrate.py runs.")
    print(f"▶ after ~50 chapters:  python tools/render_preflight.py report --lang {a.lang}")
    return 0


def _read_qa(q):
    """Return (judged, redrawn, failing, unjudged) from EITHER QA schema, or
    None if the file is neither.

    ⚠ TWO tools write `<c>.qa.json` and they do NOT share a schema:
      * narrate.py's render gate  -> {"judged", "redrawn", "failing", "unjudged"}
      * repair_verses.py          -> {"repairs": [ {verse, attempts, kept,
                                      still_failing} ], "realigned": {...}}
    This function used to be four `q.get(key, 0)` calls, which meant every
    repair-written record read as "judged 0, failing 0" and the whole command
    printed a ✅ VERDICT over 234 files it had not understood a byte of
    (measured on ylt, 2026-09-04, while the repair log held 68 still-failing
    verses). A defaulted read is indistinguishable from a real zero, so this
    returns None instead and the caller REFUSES rather than reporting clean.
    """
    if "judged" in q or "unjudged" in q:            # narrate.py's gate
        return (q.get("judged", 0), q.get("redrawn", []),
                q.get("failing", {}), q.get("unjudged", []))
    if "repairs" in q:                              # repair_verses.py
        reps = q["repairs"]
        judged, redrawn, failing, unjudged = 0, [], {}, []
        for r in reps:
            v = r.get("verse")
            atts = r.get("attempts") or []
            # an attempt whose reasons is null means the ASR worker was down:
            # that verse was NOT judged, and must never read as a pass.
            if not atts or any(a.get("reasons") is None for a in atts):
                unjudged.append(v)
                continue
            judged += 1
            if len(atts) > 1:
                redrawn.append(v)
            if r.get("still_failing"):
                failing[str(v)] = r["still_failing"]
        return (judged, redrawn, failing, unjudged)
    return None


def cmd_report(a):
    root = NARRATION / a.lang
    # ⛔ VALIDATE THE INPUT UP FRONT: an unknown --lang has no narration
    # directory, and `root.iterdir()` raised FileNotFoundError — a traceback,
    # not the documented could-not-run. rc 2 so the caller reading «zero vs
    # non-zero» is unaffected. ⛔ Only the directory's existence is checked: a
    # directory that exists but holds no records is a DIFFERENT result (rc 1,
    # «the gate never ran here»), handled below.
    if not root.is_dir():
        print("⛔ COULD NOT RUN — narration/%s does not exist, so nothing can be "
              "screened. Known rendered sets live under %s; lang must name one "
              "of them (e.g. sv, ru, cu)." % (a.lang, NARRATION))
        return 2
    rows = []
    no_qa = 0
    unjudged_unscreened = 0
    unreadable = []
    for bdir in sorted((p for p in root.iterdir() if p.is_dir() and p.name.isdigit()),
                       key=lambda p: int(p.name)):
        for ogg in sorted(bdir.glob("*.ogg"), key=lambda p: int(p.stem)):
            qa = ogg.with_suffix(".qa.json")
            if not qa.exists():
                # ⛔⛔ A CHAPTER WITH AUDIO AND NO GATE RECORD IS **UNJUDGED**,
                # not absent. It used to be counted in `no_qa` and EXCLUDED from
                # `rows`, so it raised no UNJUDGED and forced no rc 1: the run
                # printed `1 without`, `UNJUDGED 0`, and exited 0 with a ✅
                # VERDICT. A chapter that was never screened was therefore
                # indistinguishable from a screened clean one, inside the tool
                # whose whole purpose is that distinction — the
                # «a check that cannot run did not pass» rule broken in the tool
                # that enforces it. Measured 2026-09-22: sv has 1265 such
                # chapters against 71 with a record, and `report --lang sv`
                # called that corpus ✅.
                # ▶ KEEP `no_qa` AS ITS OWN NUMBER. It and UNJUDGED are
                #   different facts (never screened vs screened-and-undecided)
                #   and the code below says which of the two it is refusing on.
                no_qa += 1
                unjudged_unscreened += 1
                continue
            q = json.loads(qa.read_text(encoding="utf-8"))
            rec = _read_qa(q)
            if rec is None:
                unreadable.append(f"{bdir.name}/{ogg.stem}")
                continue
            judged, redrawn, failing, unjudged = rec
            # ⚠ A gate_version < 2 record PREDATES the repace fix (2026-09-12)
            # and cannot say whether an UNJUDGED re-roll replaced the take it
            # describes: repace_outliers ran AFTER the record was built. That
            # is UNKNOWN, never zero — a defaulted read is indistinguishable
            # from a real zero, which is the trap _read_qa exists to avoid.
            # ▶ research/_evidence/kjv_repace_bypasses_gate_2026-09-12.md
            if "repairs" in q:
                rp, dec, known = 0, 0, True     # repair_verses.py: repace not involved
            elif q.get("gate_version", 1) >= 2:
                rp = len(q.get("repaced", []))
                dec = len(q.get("repace_declined", []))
                known = True
            else:
                rp, dec, known = 0, 0, False
            rows.append((int(bdir.name), int(ogg.stem), judged,
                         len(redrawn), failing, unjudged, qa.stat().st_mtime,
                         rp, dec, known))
    if a.since:
        rows = sorted(rows, key=lambda r: r[6])[-a.since:]
    if unreadable:
        print(f"⛔ {len(unreadable)} .qa.json file(s) under narration/{a.lang} match "
              f"NEITHER known schema — this command cannot measure them and will "
              f"not report a rate over them: {', '.join(unreadable[:8])}"
              + (" ..." if len(unreadable) > 8 else ""))
        return 1
    if not rows:
        # ⚠ `no_qa` here is the whole corpus, so the run is UNJUDGED rather than
        # a clean zero — but it is still rc 1 (not rc 2): the screen DID run,
        # it simply found nothing screened. That distinction is what keeps the
        # «zero vs non-zero» callers (the launch hook reads rc, not this text)
        # working, and matches assertion 12b's existing contract.
        print(f"no .qa.json under narration/{a.lang} — gate never ran here "
              f"({no_qa} chapter(s) without a record). Screen the slow way.")
        return 1
    per_book = {}
    for b, c, j, rd, fail, unj, *_ in rows:
        e = per_book.setdefault(b, [0, 0, 0, 0, 0])
        e[0] += 1; e[1] += j; e[2] += rd; e[3] += len(fail); e[4] += len(unj)
    print(f"{'book':>4} {'ch':>4} {'judged':>7} {'redrawn':>8} {'failing':>8} {'unjudged':>9}")
    for b in sorted(per_book):
        n, j, rd, f, u = per_book[b]
        print(f"{b:>4} {n:>4} {j:>7} {rd:>8} {f:>8} {u:>9}")
    J = sum(r[2] for r in rows); RD = sum(r[3] for r in rows)
    F = sum(len(r[4]) for r in rows); U_judged = sum(len(r[5]) for r in rows)
    # ⚑ A never-screened chapter is the STRONGEST form of unjudged, so it counts
    # into the UNJUDGED total while `no_qa` keeps its own number beside it. The
    # brief's acceptance is literally «UNJUDGED 1265» for sv; the forbidden
    # thing was folding the two FACTS into one, not counting the chapters.
    U = U_judged + unjudged_unscreened
    print(f"\n{len(rows)} chapter(s) with a gate record, {no_qa} without; "
          f"judged {J}, re-drawn {RD} ({100*RD/max(J,1):.1f} %), still failing {F} "
          f"({100*F/max(J,1):.2f} % of verses), UNJUDGED {U}")
    if unjudged_unscreened:
        print(f"⚠ {unjudged_unscreened} of the {no_qa} chapter(s) WITHOUT a record "
              f"hold audio and were NEVER SCREENED — counted into UNJUDGED above, "
              f"not clean. They can only be judged by a screen that can read this "
              f"language (qa_selfrepeat for sv, not whisper).")
    fails = [(b, c, v, r) for b, c, _, _, fail, *_ in rows for v, r in fail.items()]
    for b, c, v, r in fails[:40]:
        print(f"   still failing  {b}/{c} v{v}  {'|'.join(r)}")
    if len(fails) > 40:
        print(f"   ... {len(fails) - 40} more")
    RP = sum(r[7] for r in rows)
    DEC = sum(r[8] for r in rows)
    unknown = [r for r in rows if not r[9]]
    print(f"re-paced {RP} verse(s) (judged), {DEC} re-roll(s) declined by the gate")
    if unknown:
        print(f"⚠ {len(unknown)} of {len(rows)} chapter(s) carry a gate_version<2 "
              f"record. For those, whether an UNJUDGED re-roll replaced the take "
              f"is UNKNOWN — not zero. Only an ASR screen of the AUDIO can tell.\n"
              f"  ▶ research/_evidence/kjv_repace_bypasses_gate_2026-09-12.md")
    # ⚠⚠ KNOWN-BAD CONTROL (selftest only): an UNJUDGED chapter is treated as
    # judged-and-clean, so U collapses to 0 and the verdict goes green over a
    # corpus that was never screened. Gated on _IN_SELFTEST.
    # ⛔ It also removes the NEVER-SCREENED count, because that is the same
    # defect in its larger form: pre-2026-09-22 a chapter with no record at all
    # was already invisible to the total.
    if ignore_unjudged():
        if U:
            print(f"⛔ IGNORE-UNJUDGED CONTROL: {U} unjudged chapter/verse(s) "
                  f"treated as judged-and-clean — the pre-2026-09-03 condition")
        U = 0
    bad = U > 0 or (J and F / J > 0.02)
    # ⚑ The verdict must NAME which fact it is refusing on: a screened-and-
    # undecided verse and a never-screened chapter are different problems with
    # different fixes, and folding them into one line is how the 1265 went
    # unnoticed.
    reason = []
    if unjudged_unscreened and not ignore_unjudged():
        reason.append(f"{unjudged_unscreened} chapter(s) NEVER SCREENED (no gate record)")
    judged_unjudged = U - (0 if ignore_unjudged() else unjudged_unscreened)
    if judged_unjudged:
        reason.append(f"{judged_unjudged} unjudged verse(s)")
    if J and F / J > 0.02:
        reason.append(f"{100*F/J:.2f} % of verses still failing")
    print("\nVERDICT: " + ("⛔ STOP AND LOOK — " + "; ".join(reason)
                         if bad else "✅ within expectation — the render may continue; "
                         "the still-failing verses go to repair_verses.py, not to a re-render"))
    if unknown and not bad:
        # ★ The gate speaks only for what the gate saw. Do not let a green
        # verdict be read as a claim about chapters whose repace status is
        # unknown — that over-claim is exactly the defect of 2026-09-12.
        print(f"         ⚠ THIS VERDICT COVERS THE GATE, NOT THE FILE, for the "
              f"{len(unknown)} chapter(s) above.")
    return 1 if bad else 0


def selftest():
    """Control on the pure report logic. No GPU, no nvidia-smi, no subprocess to
    an ASR worker, no network.

    Covers parse_books(), _read_qa() and the verdict arithmetic in cmd_report().
    Fixtures are built in tempfile.mkdtemp() with NARRATION repointed at them.
    ⛔ NEVER writes _work/preflight_<lang>.ok — writing that stamp would satisfy
    the launch hook and let a render start on a test artifact. Asserted at the
    end: no preflight_*.ok was created.
    """
    global _IN_SELFTEST, DATA, NARRATION, WORK
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    import contextlib
    import io
    import shutil

    saved = (DATA, NARRATION, WORK)
    td = Path(tempfile.mkdtemp(prefix="render_preflight_selftest_"))
    root = Path(td)
    narration = root / "narration"
    work = root / "_work"
    narration.mkdir(parents=True)
    work.mkdir(parents=True)

    class A:
        pass

    def report(lang="sv", since=0):
        a = A()
        a.lang = lang
        a.since = since
        buf = io.StringIO()
        rc = 0
        try:
            with contextlib.redirect_stdout(buf):
                rc = cmd_report(a)
        except Exception as e:  # noqa: BLE001 - surfaced as a FAIL
            rc = f"EXC {type(e).__name__}"
        return rc, buf.getvalue()

    def chapter(lang, b, c, qa):
        d = narration / lang / str(b)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{c}.ogg").write_bytes(b"x")
        if qa is not None:
            (d / f"{c}.qa.json").write_text(
                qa if isinstance(qa, str) else json.dumps(qa), encoding="utf-8")

    gate = lambda j, fail=None, unj=None: {          # narrate.py's gate schema
        "judged": j, "redrawn": [], "failing": fail or {}, "unjudged": unj or []}

    try:
        DATA, NARRATION, WORK = root, narration, work

        # ── parse_books ────────────────────────────────────────────────────
        r = parse_books("66-82", 100)
        ok(r == list(range(66, 83)) and len(r) == 17,
           f"1. parse_books('66-82', 100) -> the inclusive range, length 17 "
           f"(got len={len(r) if r else None})")
        r = parse_books("40", 66)
        ok(r == [40],
           f"2. parse_books('40', 66) -> one book (got {r})")
        r = parse_books("1,3,5-7", 66)
        ok(r == [1, 3, 5, 6, 7],
           f"3. parse_books('1,3,5-7', 66) -> the exact set (mixed list IS "
           f"supported; got {r})")
        r = parse_books("0-999", 66)
        ok(r is not None and r == list(range(0, 66)) and len(r) > 0,
           f"4. FINDING: parse_books('0-999', 66) CLAMPS to 0..65 rather than "
           f"rejecting — it does not produce an empty set (got len="
           f"{len(r) if r is not None else None}, first={r[0] if r else None})")
        rejected = True
        for bad in ("66-", "abc", "1-2-3"):
            try:
                parse_books(bad, 66)
                rejected = False
            except (ValueError, TypeError):
                pass
        ok(rejected,
           "5. FINDING: garbage specs ('66-', 'abc') RAISE (ValueError) rather "
           "than silently passing as an empty set — never a quiet pass")
        # ⚠ Document the one empty-set case that IS quiet: an empty spec -> None.
        ok(parse_books("", 66) is None,
           "5b. an empty spec returns None (the caller then uses the config "
           "default), not a silent empty set")

        # ── cmd_report over fixtures ───────────────────────────────────────
        # 6. the false-positive control: every chapter judged, 0 failing
        shutil.rmtree(narration / "sv", ignore_errors=True)
        chapter("sv", 0, 0, gate(50))
        chapter("sv", 1, 0, gate(60))
        rc, sout = report()
        ok(rc == 0 and "UNJUDGED 0" in sout,
           f"6. all judged, 0 failing -> rc 0 and UNJUDGED 0 (rc={rc})")

        # 7. ONE unjudged chapter among many judged -> rc 1. HEADLINE.
        chapter("sv", 1, 0, gate(60, unj=[7, 8]))
        rc, sout = report()
        ok(rc == 1 and "UNJUDGED 2" in sout,
           f"7. ONE unjudged chapter among judged ones -> rc 1 and UNJUDGED>0 "
           f"(rc={rc}, contains «UNJUDGED 2»: {'UNJUDGED 2' in sout})")

        # 8. a chapter directory with NO .qa.json at all — THE RULE THIS TOOL
        # NOW ENFORCES (was a pinned FINDING until 2026-09-22, when the owner
        # approved the fix). A chapter holding audio and no gate record is
        # UNJUDGED and forces rc 1. ⚠ The fixture is the same one that pinned
        # the OLD behaviour; only what it asserts has been inverted, so the
        # number cannot drift back unnoticed.
        shutil.rmtree(narration / "sv", ignore_errors=True)
        chapter("sv", 0, 0, gate(50))
        chapter("sv", 1, 0, None)                 # ogg, no .qa.json
        rc, sout = report()
        ok("1 without" in sout and "UNJUDGED 1" in sout and rc == 1,
           f"8. a chapter with NO .qa.json is counted as `1 without` AND as "
           f"UNJUDGED, forcing rc 1 — a chapter the gate never screened is NOT "
           f"reported clean (rc={rc}, «1 without»={'1 without' in sout}, "
           f"«UNJUDGED 1»={'UNJUDGED 1' in sout})")
        # 8b. the acceptance shape: `N without` survives as its OWN number.
        ok("1 chapter(s) with a gate record, 1 without" in sout,
           "8b. `N without` is still reported as its own number beside UNJUDGED "
           "(the two facts are not folded into one label)")

        # 9. the 2 % threshold, both sides.
        # failing% = F/J. Build J=100 with F=1 (1 %) -> rc 0; F=3 (3 %) -> rc 1.
        shutil.rmtree(narration / "sv", ignore_errors=True)
        chapter("sv", 0, 0, gate(100, fail={"1": ["x"]}))          # 1/100 = 1 %
        rc_below, s_below = report()
        shutil.rmtree(narration / "sv", ignore_errors=True)
        chapter("sv", 0, 0, gate(100, fail={"1": ["x"], "2": ["x"], "3": ["x"]}))  # 3 %
        rc_above, s_above = report()
        ok(rc_below == 0 and rc_above == 1,
           f"9. the 2 % threshold: 1/100=1.00 % -> rc 0, 3/100=3.00 % -> rc 1 "
           f"(below rc={rc_below}, above rc={rc_above})")

        # 10. malformed / truncated .qa.json.
        # ⚠⚠ FINDING, PINNED: invalid JSON RAISES (JSONDecodeError), i.e. a
        # traceback — it is loud, but it is not the documented contract. It does
        # NOT silently improve the verdict. Assert the measured behaviour.
        shutil.rmtree(narration / "sv", ignore_errors=True)
        chapter("sv", 0, 0, gate(50))
        chapter("sv", 1, 0, "{ this is not json")
        rc, sout = report()
        ok(rc == "EXC JSONDecodeError",
           f"10. FINDING: a malformed/truncated .qa.json RAISES JSONDecodeError "
           f"(a traceback) rather than being counted UNJUDGED — loud, but not "
           f"the documented contract (measured rc={rc})")

        # 11. kept_existing_take.
        # ⚠⚠ FINDING, PINNED: _read_qa IGNORES kept_existing_take entirely, so a
        # chapter whose take the gate condemned, redrew, failed to improve and
        # LEFT AS IT WAS reads as judged-and-clean. Per the standing note that is
        # NOT a cleared verse. Assert the classification; do NOT change it.
        q = gate(50)
        q["kept_existing_take"] = True
        rec = _read_qa(q)
        ok(rec == (50, [], {}, []),
           f"11. FINDING: a record carrying kept_existing_take=True is counted "
           f"as judged-and-clean by _read_qa — the flag is IGNORED (returned "
           f"{rec}). Per the standing note that verse was NOT cleared; "
           f"classification NOT changed")

        # 12. the could-not-run contract for an unknown --lang.
        # ⛔ `report --lang xx` has no narration/xx dir; this used to die with a
        # FileNotFoundError traceback out of root.iterdir(). It must be the
        # documented could-not-run: rc 2 and ONE honest line. ⛔ And a directory
        # that EXISTS but holds no records is a DIFFERENT result (rc 1) — the
        # fix must not collapse the two.
        shutil.rmtree(narration / "xx", ignore_errors=True)
        rc, sout = report(lang="xx")
        ok(rc == 2 and "COULD NOT RUN" in sout,
           f"12. an unknown --lang (no narration dir) is COULD NOT RUN: rc={rc} "
           f"(want 2), «COULD NOT RUN»={'COULD NOT RUN' in sout}")
        # and the distinction is preserved: an EXISTING but empty dir -> rc 1
        (narration / "yy").mkdir(parents=True, exist_ok=True)
        rc2, sout2 = report(lang="yy")
        ok(rc2 == 1 and "COULD NOT RUN" not in sout2,
           f"12b. an existing-but-EMPTY narration dir is a DIFFERENT result: "
           f"rc={rc2} (want 1), NOT reported as could-not-run "
           f"(«COULD NOT RUN»={'COULD NOT RUN' in sout2})")

        # ── MANDATORY: no preflight stamp was written ──────────────────────
        stamps = list(root.rglob("preflight_*.ok"))
        ok(not stamps,
           f"MANDATORY: the selftest created NO preflight_*.ok stamp (found "
           f"{[p.name for p in stamps]}) — a test artifact must never satisfy "
           f"the launch hook")

    finally:
        DATA, NARRATION, WORK = saved
        shutil.rmtree(td, ignore_errors=True)

    print("", flush=True)
    if ignore_unjudged():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_IGNORE_UNJUDGED=1 — an "
              "unjudged chapter is treated as judged-and-clean", flush=True)
    print(f"{len(fails)} failure(s)", flush=True)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "launch"):
        p = sub.add_parser(name)
        p.add_argument("--lang", required=True)
        p.add_argument("--books")
    p = sub.add_parser("report")
    p.add_argument("--lang", required=True)
    p.add_argument("--since", type=int, default=0, help="only the N most recent chapters")
    sub.add_parser("selftest",
                   help="control on parse_books/_read_qa/cmd_report; no GPU, no "
                        "ASR, never writes a preflight stamp")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    return {"check": cmd_check, "launch": cmd_launch, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
