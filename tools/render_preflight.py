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


def cmd_report(a):
    root = NARRATION / a.lang
    rows = []
    no_qa = 0
    for bdir in sorted((p for p in root.iterdir() if p.is_dir() and p.name.isdigit()),
                       key=lambda p: int(p.name)):
        for ogg in sorted(bdir.glob("*.ogg"), key=lambda p: int(p.stem)):
            qa = ogg.with_suffix(".qa.json")
            if not qa.exists():
                no_qa += 1
                continue
            q = json.loads(qa.read_text(encoding="utf-8"))
            rows.append((int(bdir.name), int(ogg.stem), q.get("judged", 0),
                         len(q.get("redrawn", [])), q.get("failing", {}),
                         q.get("unjudged", []), qa.stat().st_mtime))
    if a.since:
        rows = sorted(rows, key=lambda r: r[6])[-a.since:]
    if not rows:
        print(f"no .qa.json under narration/{a.lang} — gate never ran here "
              f"({no_qa} chapter(s) without a record). Screen the slow way.")
        return 1
    per_book = {}
    for b, c, j, rd, fail, unj, _ in rows:
        e = per_book.setdefault(b, [0, 0, 0, 0, 0])
        e[0] += 1; e[1] += j; e[2] += rd; e[3] += len(fail); e[4] += len(unj)
    print(f"{'book':>4} {'ch':>4} {'judged':>7} {'redrawn':>8} {'failing':>8} {'unjudged':>9}")
    for b in sorted(per_book):
        n, j, rd, f, u = per_book[b]
        print(f"{b:>4} {n:>4} {j:>7} {rd:>8} {f:>8} {u:>9}")
    J = sum(r[2] for r in rows); RD = sum(r[3] for r in rows)
    F = sum(len(r[4]) for r in rows); U = sum(len(r[5]) for r in rows)
    print(f"\n{len(rows)} chapter(s) with a gate record, {no_qa} without; "
          f"judged {J}, re-drawn {RD} ({100*RD/max(J,1):.1f} %), still failing {F} "
          f"({100*F/max(J,1):.2f} % of verses), UNJUDGED {U}")
    fails = [(b, c, v, r) for b, c, _, _, fail, _, _ in rows for v, r in fail.items()]
    for b, c, v, r in fails[:40]:
        print(f"   still failing  {b}/{c} v{v}  {'|'.join(r)}")
    if len(fails) > 40:
        print(f"   ... {len(fails) - 40} more")
    bad = U > 0 or (J and F / J > 0.02)
    print("\nVERDICT: " + ("⛔ STOP AND LOOK — unjudged verses or > 2 % still failing"
                         if bad else "✅ within expectation — the render may continue; "
                         "the still-failing verses go to repair_verses.py, not to a re-render"))
    return 1 if bad else 0


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
    a = ap.parse_args()
    return {"check": cmd_check, "launch": cmd_launch, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
