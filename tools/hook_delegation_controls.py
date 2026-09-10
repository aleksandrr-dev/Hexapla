"""Control harness for the 2026-09-10 subagent-misattribution fix.

Known-bad case (the defect): a SUBAGENT's hook call - agent_id present -
carrying the PARENT's transcript_path. Before the fix both guards judged it by
the parent's size and refused, blocking delegation at exactly the moment
delegation is prescribed. After the fix both must ALLOW it.

Known-good cases that must NOT be weakened:
  * the same payload WITHOUT agent_id (a real parent call) still blocks;
  * a subagent whose transcript really is its own (path under subagents/) is
    still judged on that transcript.

Writes only inside this scratchpad; deletes nothing.
"""
import json
import os
import subprocess
import sys

H = os.path.expanduser("~/.claude/hooks")
TR = os.path.expanduser("~/.claude/projects/C--Projects-Hexapla")
BIG = os.path.join(TR, "2b5ae1c2-b8de-44d1-8a9c-4d360e606cf5.jsonl")  # 519k ctx, 115 PNG reads
import tempfile
FIX = os.path.join(tempfile.gettempdir(), "hexapla_hook_fixtures")
SUB_BIG = os.path.join(FIX, "fakeproj", "subagents", "sub.jsonl")
fails = 0


def make_fat_transcript(path, n_images=40, ctx=400000):
    """A synthetic transcript that is over BOTH limits, in a few kB."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(n_images):
            fh.write(json.dumps({
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 10, "cache_read_input_tokens": ctx,
                              "cache_creation_input_tokens": 3000},
                    "content": [{"type": "tool_use", "name": "Read",
                                 "input": {"file_path": "C:/x/p%02d_o01.png" % i}}],
                },
            }) + "\n")


def run(script, payload, expect, label):
    global fails
    r = subprocess.run([sys.executable, os.path.join(H, script)],
                       input=json.dumps(payload), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    ok = r.returncode == expect
    fails += (not ok)
    first = (r.stderr or "").strip().splitlines()[:1]
    print(("PASS" if ok else "FAIL"), "exit=%s expect=%s" % (r.returncode, expect),
          "|", label, "|", first[0][:80] if first else "")


def pre(tool, inp, tp, sub=False):
    d = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp,
         "transcript_path": tp, "session_id": "ctl"}
    if sub:
        d["agent_id"] = "abcf132b52ef9ecbb"
        d["agent_type"] = "general-purpose"
    return d


make_fat_transcript(SUB_BIG)

work = {"command": "python C:/Projects/Hexapla/tools/thorlaks_o_sheets.py --chunk luke_kit 55"}
png = {"file_path": "C:/x/p55_o02.png"}

print("== sanity: the synthetic fat transcript trips both guards as a PARENT")
run("guard_context_budget.py", pre("Bash", work, SUB_BIG), 2, "synthetic is over the budget limit")
run("guard_context_images.py", pre("Read", png, SUB_BIG), 2, "synthetic is over the image limit")

print("== KNOWN-BAD (the defect): subagent call carrying the PARENT's transcript")
run("guard_context_budget.py", pre("Bash", work, BIG, sub=True), 0, "budget allows subagent")
run("guard_context_budget.py", pre("Read", png, BIG, sub=True), 0, "budget allows subagent Read")
run("guard_context_images.py", pre("Read", png, BIG, sub=True), 0, "image guard allows subagent")

print("== KNOWN-GOOD (must still block): same payload, no agent_id = parent")
run("guard_context_budget.py", pre("Bash", work, BIG), 2, "budget blocks parent")
run("guard_context_images.py", pre("Read", png, BIG), 2, "image guard blocks parent")

print("== a subagent judged on ITS OWN transcript is still judged")
run("guard_context_budget.py", pre("Bash", work, SUB_BIG, sub=True), 2, "budget blocks fat subagent")
run("guard_context_images.py", pre("Read", png, SUB_BIG, sub=True), 2, "image guard blocks fat subagent")

print("== robustness")
run("guard_context_budget.py", pre("Bash", work, BIG, sub=True), 0, "repeat is stable")
r = subprocess.run([sys.executable, os.path.join(H, "guard_context_budget.py")],
                   input="garbage", capture_output=True, text=True)
print("PASS" if r.returncode == 0 else "FAIL", "garbage stdin exit", r.returncode)
fails += r.returncode != 0

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
