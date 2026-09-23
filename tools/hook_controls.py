"""Control harness: every guard hook fed a known-bad and a known-good stdin.
A hook whose known-bad case does not exit 2 is BROKEN, not quiet."""
import json, os, subprocess, sys
H = os.path.expanduser("~/.claude/hooks")
TR = os.path.expanduser("~/.claude/projects/C--Projects-Hexapla")
BAD_TP = os.path.join(TR, "2b5ae1c2-b8de-44d1-8a9c-4d360e606cf5.jsonl")   # 115 PNG reads
GOOD_TP = os.path.join(TR, "566cee3f-7335-418f-b985-10189b0f4e0c.jsonl")  # this session, 0
fails = 0

def run(script, payload, expect, label):
    global fails
    r = subprocess.run([sys.executable, os.path.join(H, script)], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    ok = r.returncode == expect
    fails += (not ok)
    first = (r.stderr or "").strip().splitlines()[:1]
    print(("PASS" if ok else "FAIL"), f"exit={r.returncode} expect={expect}", "|", label, "|", first[0][:90] if first else "")

def bash(cmd, cwd=r"C:\Projects\Hexapla"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}

print("== guard_hexapla_bash.py (new rules 8/9 + regression)")
run("guard_hexapla_bash.py", bash("git push origin main"), 2, "git push")
run("guard_hexapla_bash.py", bash("git -C C:/Projects/Hexapla push"), 2, "git -C push")
run("guard_hexapla_bash.py", bash('git commit -m "fix\n\nCo-Authored-By: Claude <noreply>"'), 2, "commit w/ trailer")
run("guard_hexapla_bash.py", bash("git push --dry-run"), 0, "push --dry-run")
run("guard_hexapla_bash.py", bash("git push  # owner-approved"), 0, "push owner-approved")
run("guard_hexapla_bash.py", bash('git commit -m "Track the batched uploader"'), 0, "plain commit")
run("guard_hexapla_bash.py", bash("git log --oneline origin/main..main"), 0, "git log")
run("guard_hexapla_bash.py", bash("python tools/thorlaks_corpus_audit.py", cwd=r"C:\Projects\Hexapla-releases"), 2, "regression: rule 5 relative tools/")
run("guard_hexapla_bash.py", bash("ls tools"), 0, "ls")

print("== guard_context_images.py")
rd = lambda fp, tp: {"tool_name": "Read", "tool_input": {"file_path": fp}, "transcript_path": tp}
run("guard_context_images.py", rd("C:/x/p36_o02.png", BAD_TP), 2, "png, 115-image transcript")
run("guard_context_images.py", rd("C:/x/p36_o02.png", GOOD_TP), 0, "png, 0-image transcript")
run("guard_context_images.py", rd("C:/x/notes.md", BAD_TP), 0, "md, bad transcript")
run("guard_context_images.py", rd("C:/x/p.png", "C:/does/not/exist.jsonl"), 0, "missing transcript")

print("== guard_agent_launch.py")
ag = lambda m, p: {"tool_name": "Agent", "tool_input": {"model": m, "prompt": p}}
run("guard_agent_launch.py", ag("haiku", "read research/_prep/luke_kit/READ_ME_FIRST.md and transcribe"), 2, "haiku transcription")
run("guard_agent_launch.py", ag("sonnet", "transcribe Thorlaks pages"), 0, "sonnet transcription")
run("guard_agent_launch.py", ag("haiku", "grep gradle for minSdk"), 0, "haiku unrelated")

print("== guard_research_writes.py")
wr = lambda fp: {"tool_name": "Write", "tool_input": {"file_path": fp}}
good = r"C:\Projects\Hexapla-releases\research\_parts\luke_p50-58.md"
bad = r"C:\Projects\Hexapla-releases\research\_parts\_hooktest_luke.md"
# ⚠ The FAIL-OPEN controls below are the point of this group. A guard hook that
# cannot reach its check must BLOCK, not allow: "a failed read must never be
# indistinguishable from a real «nothing wrong»". Rows 3 and 4 FAIL against the
# pre-2026-09-22 hook (which returned 0 when the tool was missing or the
# subprocess raised) and PASS against the fixed one.
MISSING_TOOL = r"C:\Projects\Hexapla\tools\_no_such_part_check_control_.py"
# A DIRECTORY: os.path.isfile() is False, so this exercises the missing-tool
# branch. For the subprocess-RAISES branch we need a path that IS a file but
# cannot be run as a program — a `.md` passed to `[sys.executable, <md>]` is
# still runnable by python, so the real seam is a file whose read raises. Use
# the harness's own directory: isfile False -> missing branch. So instead the
# raiser shim is a python file that itself blows up BEFORE printing anything,
# which lands on the could-not-run (no «N problem(s)») branch; and for a true
# subprocess RAISE we point at a path whose parent makes CreateProcess fail is
# not portable. Both could-not-run branches are therefore covered by rows 3
# (missing) and 4 (ran-but-unusable). ⚠ If a genuine OSError/TimeoutExpired
# branch is ever wanted, add a seam that monkeypatches subprocess.run in a
# wrapper; do NOT fake it with a shim, which would test something else.
raise_shim = os.path.join(H, "_control_raising_part_check.py")
with open(good, encoding="utf-8") as f, open(bad, "w", encoding="utf-8") as g:
    for line in f:
        if not line.startswith("40 "): g.write(line)
# Fixture for the «subprocess raises» control: a part-check stand-in that dies.
# It is pointed at by the hook's own seam (PART_CHECK), which the hook reads at
# call time — the same seam row 3 uses.
with open(raise_shim, "w", encoding="utf-8") as f:
    f.write("raise RuntimeError('control: part_check could not start')\n")
try:
    run("guard_research_writes.py", wr(good), 0, "1. FALSE-POSITIVE ctl: clean part file ALLOWED")
    run("guard_research_writes.py", wr(bad), 2, "2. part file with v40 dropped BLOCKED")
    # 3. tool unreachable -> must BLOCK (fail-open defect: returned 0 before)
    _pc = os.environ.get("HEXAPLA_PART_CHECK_PATH")
    os.environ["HEXAPLA_PART_CHECK_PATH"] = MISSING_TOOL
    try:
        run("guard_research_writes.py", wr(good), 2, "3. part_check tool MISSING -> BLOCK (missing path named)")
    finally:
        if _pc is None: os.environ.pop("HEXAPLA_PART_CHECK_PATH", None)
        else: os.environ["HEXAPLA_PART_CHECK_PATH"] = _pc
    # 4. subprocess RAISES -> must BLOCK. Seam: a bogus interpreter, so
    #    subprocess.run raises FileNotFoundError inside part_check.
    #    The pre-fix hook swallowed that with `except Exception: return 0`.
    _py = os.environ.get("HEXAPLA_PYTHON_EXE")
    os.environ["HEXAPLA_PYTHON_EXE"] = r"C:\no\such\python-control.exe"
    try:
        run("guard_research_writes.py", wr(good), 2, "4. subprocess RAISES -> BLOCK (exception class+msg named)")
    finally:
        if _py is None: os.environ.pop("HEXAPLA_PYTHON_EXE", None)
        else: os.environ["HEXAPLA_PYTHON_EXE"] = _py
    # 4b. tool RAN but produced no parsable «N problem(s)» line -> must BLOCK
    #     (an unparsable report is not a clean report)
    _pc = os.environ.get("HEXAPLA_PART_CHECK_PATH")
    os.environ["HEXAPLA_PART_CHECK_PATH"] = raise_shim
    try:
        run("guard_research_writes.py", wr(good), 2, "4b. part_check ran, no «N problem(s)» line -> BLOCK")
    finally:
        if _pc is None: os.environ.pop("HEXAPLA_PART_CHECK_PATH", None)
        else: os.environ["HEXAPLA_PART_CHECK_PATH"] = _pc
finally:
    os.remove(bad)
    os.remove(raise_shim)
run("guard_research_writes.py", wr(r"C:\Projects\Hexapla-releases\SESSION_HANDOFF_2026-09-10_0015.md"), 0, "one handoff")
run("guard_research_writes.py", wr(r"C:\Projects\Hexapla\docs\SETTLED.md"), 0, "unrelated md")
run("guard_research_writes.py", wr(r"C:\Projects\Hexapla-releases\research\notes.md"), 0, "5. uncovered research/notes.md ALLOWED (scope not widened)")

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
