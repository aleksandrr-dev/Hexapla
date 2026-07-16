# Narration render monitor — brief for a cheap-model session

You are monitoring a long unattended audio render (days of wall-clock). Your
job is **mechanical**: run commands, report numbers, escalate failures.

## THE ONE RULE

**Run the tools. Report what they print. Do not interpret, do not fix, do not
edit any file.**

The judgment is already encoded in `tools/qa_narration.py` thresholds. You do
not get to decide whether a WARN is "probably fine" or a FAIL is "close
enough". If a check says FAIL, it is a FAIL — report it verbatim and stop.

This matters because of what this project has already learned the hard way:
`tools/ru_stress.py` was drafted in a cheap-model session working from a
detailed plan. It looked completely plausible and shipped 30 corrupt entries
out of 197 — «Вирсавия» became «Виргавия» (a non-word) in Genesis, «Христа»
became «Христоса». It would have put wrong words into 1,029 verses of a Bible.
Nothing in it looked wrong without knowing Russian. The lesson is not "cheap
models are bad" — it is that *plausible-looking output is the failure mode*.
So: when in doubt, report and escalate. An honest "I don't know" is worth far
more here than a confident guess. Never invent a diagnosis.

## Commands

Progress:

    python tools/qa_narration.py --lang ru --quiet

`--quiet` prints only chapters that are not PASS, plus a summary line.
Exit code: `0` = all pass, `1` = some WARN, `2` = some FAIL.

One book:

    python tools/qa_narration.py --lang ru --book 30

Is it still running?

    Get-Process python* | Where-Object { (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like "*narrate.py*" }

## What to report each check-in

Copy the summary line verbatim, e.g.:

    rendered: 412   pass 401  warn 11  fail 0   not-yet 777  empty 5

Plus:
- exit code
- whether the render process is alive
- every FAIL, verbatim, with its `--book N --chapter M`

Nothing else. No prose analysis. No theories about causes.

## ESCALATE IMMEDIATELY — stop and report to the human

- **any FAIL** (exit code 2)
- the render process is **dead** but `not-yet` is still large
- `pass` has not increased since the previous check-in (render is stuck)
- WARN count is climbing steadily check-over-check
- anything you do not understand

Escalating a false alarm is cheap. Missing a real failure costs days of GPU.

## What each FAIL means (report, do not act)

| FAIL | meaning |
|---|---|
| `N/M deltas == 600ms` | **THE BARK BUG IS BACK.** Verse durations measured 0ms; offsets are pure silence. Stop the render and escalate. |
| `last offset ... unaccounted` | Offsets and audio disagree. Verse highlighting broken. |
| `offsets N != verses M` | Chapter/asset mismatch. |
| `verse N still contains a digit` | Russian text leaked a digit — CosyVoice speaks digits in **English**. |
| `pace CV` / `pace spread` | Verses drift in speed. WARN is tolerable; FAIL is not. |
| `ogg is N KB — near-empty` | Chapter effectively failed. |

## Do NOT

- Do not edit `narrate.py`, `qa_narration.py`, or any asset.
- Do not "fix" a FAIL. Report it.
- Do not restart the render.
- Do not adjust thresholds because a warning seems pedantic.
- Do not delete anything. Renders cost days; the artifacts are expensive.
- Do not summarize a FAIL as "minor". You are not the judge of that.

## Context you may need

- Language `ru` renders **83 books** (66 canonical + apocrypha), ~1,486 chapters.
- Engine is CosyVoice3, running **in-process**, so `--lang ru` must be run with
  `tools\.cosyvoice_venv\Scripts\python.exe`. The QA script itself runs under
  any Python that has `soundfile`.
- Some chapters are legitimately empty in the asset (5 apocrypha slots) — those
  report `empty` and are not failures.
- WARN on pace is expected at times: CosyVoice generates prosody per verse and
  drifts. `narrate.py` re-rolls outliers automatically.
