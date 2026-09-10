import atexit, json, os, subprocess, sys, glob
H = os.path.expanduser("~/.claude/hooks/guard_context_budget.py")
TR = os.path.expanduser("~/.claude/projects/C--Projects-Hexapla")
BIG = os.path.join(TR, "2b5ae1c2-b8de-44d1-8a9c-4d360e606cf5.jsonl")   # last turn ~519k
# SMALL must stay small. It used to point at a live session, which grew past
# the hard limit within a day and turned this control into a false FAIL
# (2026-09-10). A synthetic transcript cannot drift.
import tempfile
FIX = os.path.join(tempfile.gettempdir(), "hexapla_hook_fixtures")
os.makedirs(FIX, exist_ok=True)
SMALL = os.path.join(FIX, "small_ctx.jsonl")
with open(SMALL, "w", encoding="utf-8") as _fh:
    for _i in range(6):
        _fh.write(json.dumps({"type": "assistant", "message": {
            "usage": {"input_tokens": 10, "cache_read_input_tokens": 90000,
                      "cache_creation_input_tokens": 500}, "content": []}}) + "\n")
fails = 0

# ⛔⛔ PARK THE OWNER OVERRIDE FOR THE DURATION OF THIS HARNESS.
# `_work/WRAPUP_OFF` makes the guard return 0 for EVERYTHING. With it in place
# every known-bad case here "passes" while measuring nothing — which is exactly
# what happened on 2026-09-10, when a session placed the override to get past
# the hard stop and then ran this harness: five real block cases reported PASS.
# A check that cannot run did not pass. So the harness moves the override aside
# itself and puts it back, rather than trusting the environment it inherits.
_OFF = r"C:\Projects\Hexapla-releases\_work\WRAPUP_OFF"
_PARKED = _OFF + ".parked-by-controls"
_was_parked = False
if os.path.exists(_OFF):
    os.replace(_OFF, _PARKED)
    _was_parked = True
    print("NOTE: _work/WRAPUP_OFF was in place; parked for the duration of this "
          "harness and restored at the end.\n")


def _restore_override():
    if _was_parked and os.path.exists(_PARKED):
        os.replace(_PARKED, _OFF)


atexit.register(_restore_override)
for p in glob.glob(r"C:\Projects\Hexapla-releases\_work\ctx_nudge_*.txt"): os.remove(p)

def run(payload, expect, label, env=None):
    global fails
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run([sys.executable, H], input=json.dumps(payload), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60, env=e)
    ok = r.returncode == expect; fails += (not ok)
    first = (r.stderr or "").strip().splitlines()[:1]
    print("PASS" if ok else "FAIL", f"exit={r.returncode} expect={expect} |", label, "|", first[0][:100] if first else "")

def pre(tool, inp, tp): return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp, "transcript_path": tp, "session_id": "ctl"}
def post(tool, inp, tp): return {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": inp, "transcript_path": tp, "session_id": "ctl"}

print("== HARD (519k transcript)")
run(pre("Bash", {"command": "python C:/Projects/Hexapla/tools/thorlaks_o_sheets.py --chunk luke_kit 55"}, BIG), 2, "work command blocked")
run(pre("Agent", {"prompt": "read page 55"}, BIG), 2, "agent blocked")
run(pre("Write", {"file_path": r"C:\Projects\Hexapla-releases\research\_parts\luke_p50-58.md"}, BIG), 2, "part-file write blocked")
run(pre("Bash", {"command": "python C:/Projects/Hexapla/tools/thorlaks_corpus_audit.py"}, BIG), 0, "audit allowed")
run(pre("Bash", {"command": "git -C C:/Projects/Hexapla status --short"}, BIG), 0, "git status allowed")
run(pre("Write", {"file_path": r"C:\Projects\Hexapla-releases\SESSION_HANDOFF_2026-09-10_0200.md"}, BIG), 0, "handoff write allowed")
# The handoff skill's documented LAST STEP is rewriting NEXT_SESSION_PROMPT.md.
# Until 2026-09-10 the guard blocked exactly that, so a hard-stopped session
# left the file describing the PREVIOUS session - which is the one bug that
# file exists to prevent. A guard that refuses the wrap-up it demands is worse
# than no guard: it produces a stale prompt AND a clean conscience.
run(pre("Write", {"file_path": r"C:\Projects\Hexapla-releases\NEXT_SESSION_PROMPT.md"}, BIG), 0, "next-session prompt write allowed")
run(pre("Edit", {"file_path": r"C:\Projects\Hexapla-releases\NEXT_SESSION_PROMPT.md"}, BIG), 0, "next-session prompt edit allowed")
run(pre("Write", {"file_path": r"C:\Projects\Hexapla-releases\research\_parts\next_session_notes.md"}, BIG), 2, "a look-alike under research/ is still blocked")
run(pre("Skill", {"skill": "handoff"}, BIG), 0, "skill allowed")
run(pre("Read", {"file_path": "C:/x/p.png"}, BIG), 0, "read allowed")
print("== below limits (this session)")
run(pre("Bash", {"command": "python anything.py"}, SMALL), 0, "small ctx, work allowed")
run(post("Bash", {"command": "ls"}, SMALL), 0, "small ctx, no nudge")
print("== SOFT nudge, thresholds lowered by env")
env = {"HEXAPLA_SOFT_K": "50", "HEXAPLA_HARD_K": "900"}
run(post("Bash", {"command": "ls"}, SMALL), 2, "first nudge fires", env)
run(post("Bash", {"command": "ls"}, SMALL), 0, "second within 12 turns is silent", env)
run(pre("Bash", {"command": "python anything.py"}, SMALL), 0, "soft zone does not block", env)
print("== robustness")
run(pre("Bash", {"command": "python x.py"}, "C:/nope.jsonl"), 0, "missing transcript")
r = subprocess.run([sys.executable, H], input="garbage", capture_output=True, text=True); print("PASS" if r.returncode == 0 else "FAIL", "garbage stdin exit", r.returncode)
fails += r.returncode != 0
open(r"C:\Projects\Hexapla-releases\_work\WRAPUP_OFF", "w").close()
try: run(pre("Bash", {"command": "python x.py"}, BIG), 0, "OFF file honoured")
finally: os.remove(r"C:\Projects\Hexapla-releases\_work\WRAPUP_OFF")
for p in glob.glob(r"C:\Projects\Hexapla-releases\_work\ctx_nudge_*.txt"): os.remove(p)
print("\nFAILURES:", fails); sys.exit(1 if fails else 0)
