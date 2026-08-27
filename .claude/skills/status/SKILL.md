---
name: status
description: Verify every long-running Hexapla job (renders, alignment, archive.org uploads and derives) against LIVE state rather than logs or the handoff. Use at the start of a session, when the user asks what is running, or before claiming any pipeline is healthy, stalled or finished.
---

# Hexapla job status - live evidence only

**Do not trust logs, the handoff, or a previous status report.** A render once
sat dead for 11 days behind a healthy-looking log; an upload wrapper printed
`=== COMPLETE ===` over three non-zero exit codes. Every line of the report
below must come from a command run just now.

Working dirs: repo `C:\Projects\Hexapla`, artifacts and logs
`C:\Projects\Hexapla-releases` (narration/, logs/, research/, handoff).

## The supervisor already exists - do not build a second one

Jobs are parented to Task Scheduler via `HexaplaRenderKeepalive` ->
`render_keepalive_hidden.vbs` -> `render_bootstrap.ps1`. The bootstrap is NOT a
resident process; do not look for one, and do not conclude a job is dead
because no supervisor is running.

Bootstrap sections are gated on **counts, not process handles** - a count
survives a reboot. Pause switches are files named `PAUSE_<job>`.

**Never start a long job with `Start-Process` from a session.** A reboot killed
exactly that twice. Add the job to the bootstrap instead.

## Checks to run

1. **Renders** - count artifacts, then count RECENT artifacts. A total alone
   cannot distinguish progress from a freeze:
   `find narration/<set> -name '*.ogg' | wc -l`
   `find narration/<set> -name '*.ogg' -newermt '-60 minutes' | wc -l`
   Zero new files in 60 min on an active set = STALLED, regardless of the log.
2. **GPU** - `nvidia-smi` plus
   `nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv`.
   Confirm a `python.exe` holds VRAM as a compute (`C`) client. A live process
   with an idle GPU is a stall. Note the temperature: this card throttles near
   80 C and that sets the real chapters/hour.
3. **Pollers and chain jobs** - check the LOG MTIME, not the pid. The keepalive
   re-arms these under a new pid, so a dead pid with a ticking log is healthy.
4. **archive.org** - never infer from a summary count:
   `internetarchive.get_session().get_my_catalog()`, then group by
   `(color, cmd, identifier)`. Tasks on one item are worked IN ORDER, and 150
   is the per-access-key ration, so one slow derive can block every other item.
   Being queued behind our own derive is EXPECTED - waiting is correct, do not
   cancel tasks, re-upload, or contact support.
5. **Derive progress** - count formats in `https://archive.org/metadata/<item>`
   (`Ogg Vorbis`, `VBR MP3`, `PNG`, `Spectrogram`, `JSON`). Stages run in that
   order; Spectrogram is last. Compare against a previous count to get a rate
   before quoting an ETA.
6. **What is owed** - before calling a set shipped, confirm on the LIVE item
   that oggs, per-verse offset JSON and word-level `.w.json` sidecars all
   exist. A set has been uploaded without its sidecars before.

## Reporting

Emit a table: **job | live evidence | verdict (RUNNING / STALLED / BLOCKED-
EXTERNAL / DONE)**. Every verdict cites the evidence that produced it. Flag
anything with no output in 30+ min as STALLED rather than assuming it is slow.

Distinguish **BLOCKED-EXTERNAL** (waiting correctly on archive.org) from
**STALLED** (needs a human). Conflating them causes needless intervention.

If a check itself fails, report the failure. **A count function that cannot read
its path must return -1, never 0** - a broken read that looks like "not done
yet" silently blocked two chain steps for a day with nothing in any log.
