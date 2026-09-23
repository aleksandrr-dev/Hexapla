#!/usr/bin/env python
"""wb_run.py - run a delegation BRIEF headlessly on WorkBuddy's DeepSeek, then GRADE it by running.

The WorkBuddy desktop app bundles a Claude-Code-style CLI (`codebuddy`) that
accepts `--model deepseek-v4.1-flash` in print mode and uses the app's own
login (verified 2026-09-22: `PONG. I am deepseek-v4.1-flash.`, cost 0, three
concurrent calls fine). This script is the paste-a-brief loop with the human
taken out of the middle:

    python tools/wb_run.py _work/BRIEF_x.md [_work/BRIEF_y.md ...]
        [--cwd C:\\Projects\\Hexapla] [--add-dir C:\\Projects\\Hexapla-releases]
        [--mode edit|plan] [--parallel N] [--max-turns N] [--timeout SEC]
        [--dry-run] [--no-grade]

Per brief it
  1. snapshots `git status --porcelain` in --cwd and stamps a marker file;
  2. sends PREAMBLE + brief to `codebuddy -p --model deepseek-v4.1-flash`
     (--mode plan = read-only permission mode, for DIAG briefs);
  3. saves the raw JSON transcript and the model's final text under
     <runs>/<stamp>_<brief>/;
  4. GRADES by running, never by reading the returned text:
       - git status after vs before (unbriefed edits are a finding);
       - every changed .py is `ast.parse`d on THIS interpreter (the PEP 701
         f-string class that killed two files in batch 2);
       - every `python tools/X.py ... selftest` line found in the brief is
         run as written; a line carrying `HEXAPLA_*=1` must exit 1, a clean
         one must exit 0; 0/0 = control does not fire = FAIL;
       - files under --add-dir newer than the stamp are listed
         (narration/, logs/ excluded);
  5. appends one row to <runs>/WB_LEDGER.md.

Exit: 0 every brief graded PASS · 1 at least one FAIL · 2 could not run
(CLI missing, model refused, timeout) - never 0 on a run that did not happen.

--dry-run prints the exact command and the assembled prompt head, runs nothing.
--parallel N runs N briefs at once (measured OK at 3); grading is always serial
because it runs selftests in the shared tree.

The CLI does NOT load ~/.claude/hooks - every guard that matters is re-run
here in step 4. Keep it that way: add a check, not a hook.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

EXE = Path(r"C:\Program Files\WorkBuddyAI\WorkBuddyAI.exe")
CLI = Path(r"C:\Program Files\WorkBuddyAI\resources\app.asar.unpacked\cli\bin\codebuddy")
MODEL = "deepseek-v4.1-flash"
# Other model ids this account is served, found 2026-09-22 by probing: the
# server answers an unknown id with "service info not found" and lists only
# the four tier ALIASES, so a plain id that ANSWERS is a real one. Verified:
#   deepseek-v4.1-flash  the measured default; rate-limited PER MODEL (HTTP 429)
#   hy4-preview          free to 2026-10-10 (owner); answered while deepseek 429'd
#   hy3                  free to 2026-09-30 (owner)
#   gpt-5.6-sol          seen in the desktop app's telemetry; not graded here
# The aliases fast-model / balanced-model / primary-model / deep-model also
# work, but they HIDE which model ran - never use one for a graded brief, the
# ledger has to name the model that produced the result.
MODELS_KNOWN_GOOD = ("deepseek-v4.1-flash", "hy4-preview", "hy3", "gpt-5.6-sol")
# Reasoning effort. The CLI takes --effort minimal|low|medium|high|xhigh|max;
# this script passed NOTHING until 2026-09-22, so every brief before that ran
# at the server default - an invisible quality setting on 30+ graded briefs.
# Default to high here, and put the value in the ledger: a run's effort must
# never have to be guessed afterwards. --autocompact 1m (below) separately
# forces the model's full window instead of the app's 300k default.
EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")
EFFORT_DEFAULT = "high"
DEFAULT_CWD = Path(r"C:\Projects\Hexapla")
DEFAULT_ADD = Path(r"C:\Projects\Hexapla-releases")
DEFAULT_RUNS = DEFAULT_ADD / "_work" / "wb_runs"

PREAMBLE = """\
You are a delegated engineer working unattended on the Hexapla repository
(C:\\Projects\\Hexapla, Kotlin/Android app + Python tools; data and research
live in C:\\Projects\\Hexapla-releases which is NOT a git repo). The brief
below is the whole task. Standing rules, all non-negotiable:

- Target **Python 3.11**. No expression may span a line break inside an
  f-string (PEP 701 is 3.12+). Before you finish, run
  `python tools/_wb_astcheck.py <file>` (or `python -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" <file>`)
  on every .py you changed and paste the result.
- No commits, no pushes, no git config changes, no AI-attribution trailers.
- No GPU, no renders, no uploads, no network calls, no package installs.
  A render may be running on this machine; never kill a process.
- Never read, print or copy keystore.properties, *.jks, *.keystore, or any
  token/credential file.
- Touch ONLY the files the brief names. If you believe another file must
  change, say so in the report and stop - do not change it.
- ⛔ **NEVER INVOKE A SCRIPT UNDER `tools/`, NOT EVEN WITH `--help`.**
  Measured 2026-09-22: several tools here do not use argparse and take the
  first argument as a POSITIONAL. Probing them with `--help` ran their real
  job: one rewrote `app/src/main/assets/bibles/he_wlc.json` (scripture,
  -23,505 bytes), an icon optimiser re-compressed 11 launcher PNGs, and a
  chapter tool created a directory literally named `--help` full of output.
  Nothing announced it. To learn a tool's flags, READ them - `ast` over its
  `add_argument` calls, or grep - never by running it.
  The ONLY executions permitted are: (a) a script YOU wrote under a scratch
  directory the brief names, and (b) `python tools/X.py --selftest` when the
  brief lists that exact line. Anything else is a blocker: say so and stop.
- No `python -c` and no heredoc Python for EDITS - write edit scripts to a
  file first. Set PYTHONIOENCODING=utf-8 on anything printing non-ASCII.
- Free deterministic checks run on the FULL denominator, never a sample.
- Grade your own work by RUNNING it both ways (clean run exits 0, the
  known-bad env var run exits 1 with a `FAIL - ...` line, not a traceback).
  Do not report a count you did not measure.
- A check you could not run is a GAP, reported as such, never a pass.
- ⛔ **C:\\Projects\\Hexapla-releases IS READ-ONLY TO YOU** (owner, 2026-09-22:
  «no write access»). It is not under git, so nothing written there can be
  undone. Read it freely; write NOTHING there - not a report, not scratch, not
  a redirect (`> file`, `tee`, `cp`, `>>`). Your scratch directory is
  `C:\\Projects\\Hexapla\\_wb_scratch\\<brief name>\\`; your report goes to the
  path below. The grader lists every file under that tree newer than your
  start, and ANY such file FAILS the run.

DELIVERABLE: besides the edits, write a report file
`{report_path}`
with sections: WHAT CHANGED (file list), HOW GRADED (exact commands + rc +
key output lines), FINDINGS (anything the brief did not anticipate),
GAPS (checks you could not run and why). Finish your final message with a
line `CHANGED FILES:` followed by one path per line (or `CHANGED FILES: none`).

=== BRIEF ===
"""

SELFTEST_RE = re.compile(
    r"^\s*((?:[A-Z_][A-Z0-9_]*=\S+\s+)*)python\s+(tools/\S+\.py)\s+(.*?(?:--selftest|\bselftest\b).*?)(?:\s*;.*)?$"
)
KNOWN_BAD_RE = re.compile(r"\b(HEXAPLA_[A-Z0-9_]+)=1\b")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def sh(cmd: str, cwd: Path, env: dict | None = None, timeout: int = 900) -> tuple[int, str]:
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    if env:
        e.update(env)
    try:
        p = subprocess.run(
            ["bash", "-lc", cmd], cwd=str(cwd), env=e, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out


PROTECTED_GLOBS = [
    # (relative to an --add-dir) - a file that vanishes from any of these fails the run.
    "research/**/*.md", "research/**/*.json", "_work/**/*.md", "docs/**/*",
    "narration/*_qa_fail_originals/**/*", "narration/**/*.qa.json",
    "SESSION_HANDOFF_*.md", "NEXT_SESSION_PROMPT.md", "PLAY_*.md",
]


def protected_inventory(roots: list[Path]) -> set[str]:
    inv: set[str] = set()
    for r in roots:
        for g in PROTECTED_GLOBS:
            for p in r.glob(g):
                if p.is_file():
                    inv.add(str(p))
    return inv


def git_status(cwd: Path) -> set[str]:
    rc, out = sh("git status --porcelain", cwd)
    if rc != 0:
        return {"<git status failed>"}
    return {ln.rstrip() for ln in out.splitlines() if ln.strip()}


def build_cmd(prompt_file: Path, args, mode: str) -> list[str]:
    cmd = [
        str(EXE), str(CLI), "-p", "--model", args.model,
        "--output-format", "json", "--no-session-persistence",
        "--autocompact", "1m",  # the app's default window is 300k; force the model's full 1M
        "--effort", args.effort,  # never leave reasoning effort to the server default
        "--max-turns", str(args.max_turns),
        # plan mode denies Bash and any Read outside the repo in non-interactive
        # runs (measured 2026-09-22: both DIAG briefs stopped on a blocker), so
        # read-only briefs get the same mode with no edit tools; the git delta
        # and the newer-files scan in grade() are the fence.
        "--permission-mode", "bypassPermissions",
        "--disallowedTools",
        "Bash(git commit:*)", "Bash(git push:*)", "Bash(git config:*)",
        "Bash(git reset:*)", "Bash(git checkout:*)", "Bash(git stash:*)",
        "Bash(pip install:*)", "Bash(gh:*)", "Bash(curl:*)", "Bash(wget:*)",
        "Bash(taskkill:*)", "Bash(kill:*)", "Bash(Stop-Process:*)",
        "Bash(rm:*)", "Bash(rmdir:*)", "Bash(del:*)", "Bash(Remove-Item:*)",
        "Bash(git clean:*)", "Bash(git rm:*)", "Bash(mv:*)", "Bash(shred:*)",
        "Read(**/keystore.properties)", "Read(**/*.jks)", "Read(**/*.keystore)",
        "WebFetch", "WebSearch",
    ]
    # ⛔ The --add-dir trees are READ-ONLY to a delegate (owner, 2026-09-22).
    # ⚠ This cannot stop a Bash redirect; the newer-files scan in grade() is
    # the rail that holds, because it FAILS the run.
    for d in args.add_dir:
        cmd += [f"Write({d}\\**)", f"Edit({d}\\**)", f"MultiEdit({d}\\**)",
                f"NotebookEdit({d}\\**)"]
    if mode == "plan":
        cmd += ["Edit", "MultiEdit", "NotebookEdit"]
    for d in args.add_dir:
        cmd += ["--add-dir", str(d)]
    return cmd


def run_model(brief: Path, args, run_dir: Path, mode: str) -> dict:
    """Send the brief. Returns dict(rc, result_text, usage, num_turns, is_error, error)."""
    # Inside the repo, NOT the releases tree: a delegate never needs to write
    # outside git's reach. ⛔ Not gitignored on purpose - an untracked report is
    # visible in `git status`, which is the point.
    report_dir = Path(args.cwd) / "_wb_reports"
    report_dir.mkdir(exist_ok=True)
    (Path(args.cwd) / "_wb_scratch" / brief.stem).mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"REPORT_{brief.stem}.md"
    prompt = PREAMBLE.format(report_path=str(report_path)) + brief.read_text(encoding="utf-8")
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    cmd = build_cmd(prompt_file, args, mode)
    (run_dir / "cmd.txt").write_text(" ".join(shlex.quote(c) for c in cmd) + "\n", encoding="utf-8")
    if args.dry_run:
        print(f"[dry-run] {brief.name}: mode={mode}\n  " + " ".join(cmd[:12]) + " ...")
        print("  prompt head:\n    " + "\n    ".join(prompt.splitlines()[:6]))
        return {"rc": 0, "dry": True}
    env = dict(os.environ, ELECTRON_RUN_AS_NODE="1", PYTHONIOENCODING="utf-8")
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=str(args.cwd), env=env, input=prompt.encode("utf-8"),
                           capture_output=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return {"rc": 2, "error": f"model run TIMEOUT after {args.timeout}s"}
    raw = (p.stdout or b"").decode("utf-8", "replace")
    (run_dir / "stdout.json").write_text(raw, encoding="utf-8")
    (run_dir / "stderr.txt").write_text((p.stderr or b"").decode("utf-8", "replace"), encoding="utf-8")
    # stdout carries app log lines before the JSON array; find the array.
    start = raw.find("[\n")
    if start < 0:
        start = raw.find("[")
    try:
        msgs = json.loads(raw[start:]) if start >= 0 else []
    except json.JSONDecodeError as e:
        return {"rc": 2, "error": f"could not parse CLI JSON: {e}; cli rc={p.returncode}"}
    result = next((m for m in reversed(msgs) if m.get("type") == "result"), None)
    if result is None:
        return {"rc": 2, "error": f"no result message; cli rc={p.returncode}"}
    text = result.get("result") or ""
    (run_dir / "result.md").write_text(text, encoding="utf-8")
    return {
        "rc": 1 if result.get("is_error") else 0,
        "result_text": text,
        "usage": result.get("usage", {}),
        "num_turns": result.get("num_turns"),
        "is_error": result.get("is_error"),
        "seconds": round(time.time() - t0),
        "denials": result.get("permission_denials", []),
        "report_path": report_path,
    }


def grade(brief: Path, args, run_dir: Path, before: set[str], stamp_file: Path, model: dict) -> tuple[str, list[str]]:
    """Returns (verdict, lines). Verdict PASS / FAIL / NORUN."""
    lines: list[str] = []
    verdict = "PASS"
    if model.get("rc") == 2:
        return "NORUN", [f"model: {model.get('error')}"]
    if model.get("is_error"):
        verdict = "FAIL"
        lines.append(f"model reported is_error: {model.get('result_text','')[:300]}")

    if model.get("denials"):
        lines.append(f"PERMISSION DENIALS: {len(model['denials'])} - the delegate could not do what the brief asked; see stdout.json")
        verdict = "FAIL"
    txt = model.get("result_text", "")
    if re.search(r"\b(BLOCKER|cannot (?:run|execute)|could not run|permission(?:s)? (?:is|are|was|were) denied)\b", txt, re.I):
        lines.append("delegate reports a blocker in its final answer - read result.md before trusting anything")
        verdict = "FAIL"

    after = git_status(args.cwd)
    new = sorted(after - before)
    lines.append(f"git status delta ({len(new)} new entries): " + (", ".join(new) if new else "none"))
    deleted = [e for e in new if e.startswith(" D") or e.startswith("D ")]
    if deleted:
        lines.append("DELETED tracked files: " + ", ".join(deleted))
        verdict = "FAIL"
    gone = sorted(model.get("inv_before", set()) - protected_inventory(list(args.add_dir)))
    if gone:
        lines.append(f"PROTECTED FILES VANISHED ({len(gone)}): " + ", ".join(gone[:20]))
        verdict = "FAIL"

    # Unbriefed edits: anything changed whose basename is not mentioned in the brief.
    brief_text = brief.read_text(encoding="utf-8")
    unbriefed = [e for e in new if Path(e.split()[-1]).name not in brief_text
                 and not e.split()[-1].startswith(("_wb_reports", "_wb_scratch"))]
    if unbriefed:
        lines.append("UNBRIEFED edits (not named in the brief): " + ", ".join(unbriefed))
        verdict = "FAIL"

    # ast.parse every changed .py on this interpreter.
    for e in new:
        path = e.split()[-1]
        if path.endswith(".py"):
            fp = args.cwd / path
            if fp.exists():
                try:
                    ast.parse(fp.read_text(encoding="utf-8"))
                    lines.append(f"ast.parse OK  {path}")
                except SyntaxError as ex:
                    lines.append(f"ast.parse FAIL {path}: {ex}")
                    verdict = "FAIL"

    # Selftest lines from the brief, run as written.
    ran_any = False
    for ln in brief_text.splitlines():
        m = SELFTEST_RE.match(ln)
        if not m:
            continue
        envs, tool, rest = m.group(1).strip(), m.group(2), m.group(3).strip()
        env = dict(kv.split("=", 1) for kv in envs.split()) if envs else {}
        known_bad = KNOWN_BAD_RE.search(envs) is not None
        cmd = f"python {tool} {rest}"
        rc, out = sh(cmd, args.cwd, env=env, timeout=600)
        ran_any = True
        want = 1 if known_bad else 0
        ok = rc == want
        tail = " | ".join([l for l in out.splitlines() if l.strip()][-3:])[:300]
        lines.append(f"selftest {'OK ' if ok else 'BAD'} rc={rc} want={want}  {envs} {cmd}  :: {tail}")
        if not ok:
            verdict = "FAIL"
        if known_bad and rc == 1 and "Traceback" in out:
            lines.append("  ^ rc 1 came from a TRACEBACK, not a FAIL line -> not a passing control")
            verdict = "FAIL"
    if not ran_any:
        lines.append("no selftest lines found in brief (nothing to run both ways)")

    # Files touched under add-dirs since the stamp.
    for d in args.add_dir:
        if not Path(d).is_dir():
            lines.append(f"{d}: NEWER-FILES SCAN COULD NOT RUN (not a directory) - not a pass")
            verdict = "FAIL"
            continue
        rc, out = sh(
            f"set -o pipefail; find . -type f -newer {shlex.quote(str(stamp_file))} "
            f"-not -path './narration/*' -not -path './logs/*' -not -path './_work/wb_runs/*' | head -50",
            Path(d), timeout=120)
        touched = [l for l in out.splitlines() if l.strip()]
        # ⛔ A FAIL, not a listing (owner, 2026-09-22: «no write access»). The
        # tree has no git, so this scan is the only rail a Bash redirect cannot
        # get round. ⚠ A main-session job writing the same tree at the same
        # time lands here too - a false FAIL is the safe direction; read the
        # names. ⚠ A scan that could not run is not a clean scan.
        if rc != 0:
            lines.append(f"{d}: NEWER-FILES SCAN COULD NOT RUN (rc={rc}) - not a pass")
            verdict = "FAIL"
        elif touched:
            lines.append(f"WRITE INTO READ-ONLY TREE {d}: {len(touched)} file(s) newer than start: "
                         + ", ".join(touched[:20]))
            verdict = "FAIL"
        else:
            lines.append(f"{d}: 0 file(s) newer than start")

    rp = model.get("report_path")
    if rp and not Path(rp).exists() and model.get("mode") == "plan" and model.get("result_text"):
        # plan mode is read-only for the model; its final answer IS the report.
        Path(rp).write_text(
            f"# {brief.stem} — DeepSeek report (plan mode, saved by wb_run.py from the final answer)\n\n"
            + model["result_text"], encoding="utf-8")
        lines.append(f"report written from final answer (plan mode): {rp}")
    if rp and not Path(rp).exists():
        lines.append(f"REPORT MISSING: {rp}")
        verdict = "FAIL" if verdict == "PASS" else verdict
    return verdict, lines


def one_brief(brief: Path, args, runs: Path) -> dict:
    mode = args.mode
    if mode == "auto":
        mode = "plan" if ("READ-ONLY" in brief.read_text(encoding="utf-8")[:400] or "_DIAG_" in brief.name) else "edit"
    stamp = now_stamp()
    run_dir = runs / f"{stamp}_{brief.stem}"
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp_file = run_dir / "START"
    stamp_file.write_text(stamp, encoding="utf-8")
    before = git_status(args.cwd)
    (run_dir / "git_before.txt").write_text("\n".join(sorted(before)), encoding="utf-8")
    inv_before = protected_inventory(list(args.add_dir))
    model = run_model(brief, args, run_dir, mode)
    model["mode"] = mode
    model["inv_before"] = inv_before
    return {"brief": brief, "run_dir": run_dir, "before": before, "stamp_file": stamp_file, "model": model, "mode": mode}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("briefs", nargs="*", type=Path)
    ap.add_argument("--queue", type=Path, default=None,
                    help="text file, one brief path per line (# comments ok); briefs with a PASS row in the ledger are skipped")
    ap.add_argument("--cwd", type=Path, default=DEFAULT_CWD)
    ap.add_argument("--add-dir", type=Path, action="append", default=None)
    ap.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--mode", choices=["auto", "edit", "plan"], default="auto")
    ap.add_argument("--effort", choices=EFFORTS, default=EFFORT_DEFAULT,
                    help="reasoning effort (default: %(default)s). The CLI default is the server's, which is not documented and is not necessarily high.")
    ap.add_argument("--model", default=MODEL,
                    help="model id to send the brief to (default: %(default)s). Known good: "
                         + ", ".join(MODELS_KNOWN_GOOD)
                         + ". An unknown id is REFUSED by the server, never silently substituted.")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--max-turns", type=int, default=80)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-grade", action="store_true")
    args = ap.parse_args()
    if args.add_dir is None:
        args.add_dir = [DEFAULT_ADD]
    if args.queue:
        if not args.queue.exists():
            print(f"could not run: queue file missing {args.queue}")
            return 2
        ledger_txt = (args.runs / "WB_LEDGER.md").read_text(encoding="utf-8") if (args.runs / "WB_LEDGER.md").exists() else ""
        passed = set(re.findall(r"\| (\S+\.md) \| \S+ \| \S+ \| \S+ \| \S+ \| \*\*PASS\*\* \|", ledger_txt))
        for ln in args.queue.read_text(encoding="utf-8").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            p = Path(ln) if Path(ln).is_absolute() else args.queue.parent / ln
            if p.name in passed:
                print(f"[queue] skip (PASS in ledger): {p.name}")
                continue
            args.briefs.append(p)
        if not args.briefs:
            print("[queue] nothing left to run - every brief has a PASS row")
            return 0
    if not args.briefs:
        print("could not run: no briefs given (pass paths or --queue FILE)")
        return 2
    if not EXE.exists() or not CLI.exists():
        print(f"could not run: WorkBuddy CLI not found at {CLI}")
        return 2
    for b in args.briefs:
        if not b.exists():
            print(f"could not run: brief missing {b}")
            return 2
    args.runs.mkdir(parents=True, exist_ok=True)

    if args.parallel > 1 and not args.dry_run:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            results = list(ex.map(lambda b: one_brief(b, args, args.runs), args.briefs))
    else:
        results = [one_brief(b, args, args.runs) for b in args.briefs]

    worst = 0
    ledger = args.runs / "WB_LEDGER.md"
    if not ledger.exists():
        ledger.write_text("# WorkBuddy/DeepSeek run ledger (written by tools/wb_run.py)\n\n| when | brief | model | effort | mode | turns | tokens in/out | secs | verdict | run dir |\n|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    for r in results:
        m = r["model"]
        if m.get("dry"):
            continue
        if args.no_grade:
            verdict, lines = ("UNGRADED", [])
        else:
            verdict, lines = grade(r["brief"], args, r["run_dir"], r["before"], r["stamp_file"], m)
        (r["run_dir"] / "grade.md").write_text(f"# {verdict}\n\n" + "\n".join(f"- {l}" for l in lines) + "\n", encoding="utf-8")
        u = m.get("usage") or {}
        tok = f"{u.get('input_tokens','?')}/{u.get('output_tokens','?')}"
        row = f"| {r['run_dir'].name[:17]} | {r['brief'].name} | {args.model} | {args.effort} | {r['mode']} | {m.get('num_turns','?')} | {tok} | {m.get('seconds','?')} | **{verdict}** | {r['run_dir'].name} |\n"
        with ledger.open("a", encoding="utf-8") as f:
            f.write(row)
        print(f"\n=== {r['brief'].name}  mode={r['mode']}  turns={m.get('num_turns')}  tokens={tok}  {m.get('seconds')}s  -> {verdict}")
        for l in lines:
            print("  - " + l)
        if m.get("denials"):
            print(f"  - permission denials: {len(m['denials'])} (see stdout.json)")
        print(f"  run dir: {r['run_dir']}")
        worst = max(worst, {"PASS": 0, "UNGRADED": 0, "FAIL": 1, "NORUN": 2}[verdict])
    return worst


if __name__ == "__main__":
    sys.exit(main())
