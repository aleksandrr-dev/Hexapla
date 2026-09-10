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
with open(good, encoding="utf-8") as f, open(bad, "w", encoding="utf-8") as g:
    for line in f:
        if not line.startswith("40 "): g.write(line)
try:
    run("guard_research_writes.py", wr(good), 0, "clean part file")
    run("guard_research_writes.py", wr(bad), 2, "part file with v40 dropped")
finally:
    os.remove(bad)
run("guard_research_writes.py", wr(r"C:\Projects\Hexapla-releases\SESSION_HANDOFF_2026-09-10_0015.md"), 0, "one handoff")
run("guard_research_writes.py", wr(r"C:\Projects\Hexapla\docs\SETTLED.md"), 0, "unrelated md")

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
