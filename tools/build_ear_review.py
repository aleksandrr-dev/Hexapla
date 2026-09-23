# -*- coding: utf-8 -*-
"""Cut the verses that want an EAR out of the live audio, into one review file.

    python tools/build_ear_review.py --set ylt --out <dir>

0 model tokens, 0 GPU. Two sources, unioned:

  1. verses a repair run left `still failing after 3 draws` (from its tee'd log)
  2. verses `qa_discarded_draws.py` says the gate could not separate, so the
     kept take was chosen arbitrarily

⚠⚠ **IT CUTS FROM THE LIVE TREE, NOT FROM THE DRAWS.** The question an ear is
being asked is «is what will SHIP correct?», and that is `narration/<set>/b/c.ogg`
as it stands now. A clip taken from a draw or from `<set>_qa_fail_originals/`
answers a different question and would be worse than no clip, because it sounds
like an answer.

⚠ Verse n starts at `offsets[n-1]` and ends at `offsets[n]` — the sidecar holds
STARTS only, so the last verse runs to end of file. An off-by-one here clips the
wrong verse and the ear rules on the wrong audio; the printed index carries the
verse TEXT so a mismatch is audible immediately.

⛔ A verse absent from the output is not a verse that passed — it is a verse
neither source named. Silence is not a clean bill (see qa_discarded_draws).
"""
import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
GAP = 0.9          # seconds of silence between verses in the joined file


def resolve_set(set_key, asset_arg):
    """-> (narration dir, text asset) for a SET KEY or a bare directory name.

    ⚠ This tool used to take `--set` as a DIRECTORY while every sibling tool
    (`qa_repair_outcomes.py`, `build_audio_index_gen.py`) takes a SET KEY, and
    the two disagree for exactly the set that matters: `kjv` renders into
    `narration/en`. `--set kjv` therefore produced "⛔ NO AUDIO ON DISK" on
    every row — 2026-09-14, and again 2026-09-21 out of the handoff.
    ⛔ And `--set en` alone was NOT the fix: the asset default is `en_ylt.json`,
    so the kit printed YLT text against KJV audio and every clip would have read
    as a mismatch. The set key must carry BOTH halves, from one table.

    Derived from `build_audio_index_gen.SETS` (the shipping truth), never a
    fourth hand-kept copy. A bare directory name still works, but then the
    asset is whatever `--asset` says.
    """
    try:
        from build_audio_index_gen import SETS
    except Exception:
        return DATA / "narration" / set_key, asset_arg
    by_tid = {s["tid"]: s for s in SETS if s.get("tid")}
    if set_key in by_tid:
        s = by_tid[set_key]
        return (DATA / "narration" / s["dir"],
                asset_arg or s.get("asset"))
    for s in SETS:
        if s.get("dir") == set_key:
            return DATA / "narration" / set_key, asset_arg or s.get("asset")
    return DATA / "narration" / set_key, asset_arg


def still_failing(log):
    """-> {(b, c, v)} from a repair run's tee'd log."""
    out, ch = set(), None
    for line in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^=== (\d+)/(\d+)\b", line)
        if m:
            ch = (int(m.group(1)), int(m.group(2)))
        if ch and "still failing after 3 draws" in line:
            g = re.search(r"v\[([0-9, ]+)\]", line)
            if g:
                for v in g.group(1).split(","):
                    out.add((ch[0], ch[1], int(v.strip())))
    return out


def discarded(set_key):
    """-> {(b, c, v)} that qa_discarded_draws flags as an arbitrary choice."""
    r = subprocess.run(
        [sys.executable, str(HERE / "qa_discarded_draws.py"), "--set", set_key],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = set()
    for line in (r.stdout or "").splitlines():
        m = re.match(r"^\s+(\d+)/(\d+) v(\d+)\s*$", line)
        if m:
            out.add(tuple(int(x) for x in m.groups()))
    if not out:
        # ⛔ An empty parse and a genuinely clean set look identical. Refuse.
        print("⛔ parsed 0 verses out of qa_discarded_draws — treat as a "
              "BROKEN parse, not a clean set, and fix this before trusting "
              "the bundle.", file=sys.stderr)
    return out


NOTE_RE = re.compile(r"\{[^{}]*:[^{}]*\}")


def strip_notes(text):
    """Drop `{...:...}` note markup, keep `{...}` supplied words.

    ⚠ An ear kit prints the verse so the listener can say whether the audio
    matches the PRINT. Note markup is not printed scripture and is not spoken,
    so leaving it in makes the text disagree with correct audio — which is
    exactly the disagreement the kit is asking him to report. Mirrors
    `BibleRepo.parseAsset`: colon = note, drop; no colon = supplied, keep.
    """
    t = NOTE_RE.sub("", text)
    # Supplied words ARE spoken, so they stay — but the braces are not, and a
    # listener comparing audio to text should not have to mentally delete
    # punctuation that the voice never says. Drop the brackets, keep the words.
    t = t.replace("{", "").replace("}", "")
    return re.sub(r"\s{2,}", " ", t).strip()


ROLES = {"suspect", "ctl+", "ctl-"}


def from_queue(path):
    """-> ({(b, c, v): role}, {(b, c, v): tree}) from `B C vV [role] [@tree]` lines.

    Role defaults to `suspect`. `ctl+` is a verse KNOWN to carry the defect,
    `ctl-` one known to be clean.

    ⚠⚠ `@tree` NAMES A DIFFERENT SOURCE TREE under `narration/` for that ONE row,
    and it exists for exactly one reason: **a ctl+ whose verse has since been
    repaired no longer carries its defect in the live tree.** Both confirmed
    positives (2 Kings 15:2, repaired 2026-09-14; Num 5:22, repaired three times
    by 2026-09-17) are in that state, so cutting them from `narration/en` would
    hand the owner a CLEAN clip labelled as the positive control — a kit that
    cannot fire and whose silence is indistinguishable from an ear that missed it.
    ▶ `11 14 v2 ctl+ @en_qa_fail_originals` cuts from the pristine backup, which
    is never deleted (owner's ruling, 2026-09-16).

    ⛔ `@tree` IS FOR CONTROLS ONLY. A SUSPECT must always come from the live
    tree: the question a suspect asks is «is what will SHIP correct?», and a clip
    from a backup answers a different question while looking like an answer.
    Enforced below.

    ⛔ An empty or unparsable queue returns ({}, {}) and the caller REFUSES — a
    kit built from nothing must never look like a kit that found nothing.
    """
    out, srcs = {}, {}
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        m = re.match(r"^(\d+)\s+(\d+)\s+v?(\d+)\s*([^@\s]+)?\s*(?:@(\S+))?\s*$", ln)
        if not m:
            print(f"⛔ unparsable queue line, refusing: {ln!r}", file=sys.stderr)
            return {}, {}
        role = (m.group(4) or "suspect").lower()
        if role not in ROLES:
            print(f"⛔ unknown role {role!r} (want one of {sorted(ROLES)}): "
                  f"{ln!r}", file=sys.stderr)
            return {}, {}
        tree = m.group(5)
        if tree and role == "suspect":
            print(f"⛔ @{tree} on a SUSPECT row, refusing: a suspect must be cut "
                  f"from the LIVE tree or the kit answers the wrong question: "
                  f"{ln!r}", file=sys.stderr)
            return {}, {}
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        out[key] = role
        if tree:
            srcs[key] = tree
    return out, srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt",
                    help="SET KEY (kjv, ylt, wyc, ...) — resolved to its "
                         "narration dir AND its text asset. A bare dir name "
                         "still works but then --asset is on you.")
    ap.add_argument("--asset", default=None,
                    help="override the set's text asset (default: the set's "
                         "own, from build_audio_index_gen.SETS)")
    ap.add_argument("--log", action="append", default=[],
                    help="repair log(s) to read `still failing` out of")
    ap.add_argument("--queue",
                    help="verse list `B C vV [suspect|ctl+|ctl-]`, one per "
                         "line. Sole source when given — the log/discarded "
                         "sources answer a different question.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    nar, asset = resolve_set(a.set_key, a.asset)
    if not asset:
        print(f"⛔ no text asset for --set {a.set_key} — pass --asset. A kit "
              f"whose printed text is the WRONG translation reads as six "
              f"mismatches and is worse than no kit.", file=sys.stderr)
        return 2
    if not nar.is_dir():
        print(f"⛔ {nar} is not a directory — check --set (it is a SET KEY; "
              f"the kjv render lives in narration/en).", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    books = json.loads((ASSETS / asset).read_text(encoding="utf-8"))

    want, role_of, src_of = {}, {}, {}
    if a.queue:
        role_of, src_of = from_queue(a.queue)
        for k, role in role_of.items():
            want.setdefault(k, set()).add({
                "suspect": "suspect — flagged, not yet heard",
                "ctl+": "POSITIVE CONTROL — known to carry the defect",
                "ctl-": "negative control — known clean",
            }[role])
        if not want:
            print("⛔ queue named no verses (or failed to parse) — that is a "
                  "broken run, not a clean set.")
            return 2
    else:
        for lg in a.log:
            for k in still_failing(lg):
                want.setdefault(k, set()).add("gate-failed after 3 draws")
        for k in discarded(a.set_key):
            want.setdefault(k, set()).add("arbitrary choice between draws")
        if not want:
            print("⛔ no verses named by either source — that is a broken run, "
                  "not a clean set.")
            return 2

    rows, clips = [], []
    # ⚠⚠ CLIP ORDER IS PART OF THE INSTRUMENT, NOT PRESENTATION.
    # Ordering by (book, chapter, verse) put the controls at positions 1, 2, 3
    # of EVERY kit built 2026-09-12 → 2026-09-14: the controls are drawn from
    # Leviticus and Ruth, the suspects from later books, so the sort front-loaded
    # them automatically. Five consecutive kits opened with the same three clips
    # in the same three slots, and the owner said so (2026-09-14).
    # ⛔ A control whose SLOT is predictable is not a control — the positive
    # control can be named by position without listening, which is exactly the
    # "a control that cannot fail proves nothing" failure this toolchain keeps
    # rediscovering. Its three "firings" on the 13c/13d/13e kits cannot be
    # distinguished from recognition and must not be quoted as evidence.
    # Seeded on the output directory: a given kit is reproducible, but the slot
    # a control lands in is not guessable from the book numbers.
    order = sorted(want)
    random.Random(out.name).shuffle(order)
    for (b, c, v) in order:
        # ⚠ A row may name its own source tree (`@en_qa_fail_originals`) so a
        # ctl+ whose verse has since been repaired is still cut from audio that
        # CARRIES the defect. Offsets come from that same tree — the two renders
        # do not share a timeline, and borrowing the live sidecar would clip the
        # wrong span while looking entirely normal.
        src = DATA / "narration" / src_of[(b, c, v)] if (b, c, v) in src_of else nar
        ogg = src / str(b) / f"{c}.ogg"
        sc = src / str(b) / f"{c}.json"
        if not ogg.exists() or not sc.exists():
            rows.append((b, c, v, None, None, "⛔ NO AUDIO ON DISK", want[(b, c, v)]))
            continue
        offs = json.loads(sc.read_text(encoding="utf-8"))["offsets"]
        if v > len(offs):
            rows.append((b, c, v, None, None,
                         f"⛔ verse {v} beyond {len(offs)} offsets", want[(b, c, v)]))
            continue
        start = offs[v - 1] / 1000.0
        end = offs[v] / 1000.0 if v < len(offs) else None
        try:
            bk = books[b]
            text = strip_notes(bk["chapters"][c][v - 1])
            name = bk.get("name") or bk.get("n") or f"book{b}"
        except (IndexError, KeyError, TypeError):
            text, name = "", f"book{b}"
        clip = out / f"{b:02d}_{c:03d}_v{v:03d}.mp3"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ogg),
               "-ss", f"{start:.3f}"]
        if end is not None:
            cmd += ["-to", f"{end:.3f}"]
        cmd += ["-c:a", "libmp3lame", "-q:a", "4", str(clip)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not clip.exists():
            rows.append((b, c, v, name, text, "⛔ ffmpeg failed", want[(b, c, v)]))
            continue
        clips.append(clip)
        span = (f"{start:.1f}-{end:.1f}s" if end is not None
                else f"{start:.1f}s-EOF (last verse)")
        rows.append((b, c, v, name, text, span, want[(b, c, v)]))

    joined, joined_failed = None, False
    if clips:
        sil = out / "_gap.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"anullsrc=r=44100:cl=mono", "-t", str(GAP),
                        "-c:a", "libmp3lame", "-q:a", "4", str(sil)],
                       capture_output=True)
        lst = out / "_concat.txt"
        parts = []
        for c_ in clips:
            # ⚠ ABSOLUTE paths, always. The concat demuxer resolves `file`
            # entries relative to the LIST FILE's own directory, not the cwd,
            # so a relative --out silently doubles the path
            # (_work/kit/_work/kit/clip.mp3) and ffmpeg cannot open it. An
            # absolute --out hides this bug completely — which is why it
            # survived two hand-built kits.
            parts.append(f"file '{c_.resolve().as_posix()}'")
            parts.append(f"file '{sil.resolve().as_posix()}'")
        lst.write_text("\n".join(parts) + "\n", encoding="utf-8")
        joined = out / f"{a.set_key}_ear_review.mp3"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f",
                            "concat", "-safe", "0", "-i", str(lst), "-c:a",
                            "libmp3lame", "-q:a", "4", str(joined)],
                           capture_output=True, text=True)
        # ⛔ Gate the banner on the child's return code AND on the artifact
        # actually existing. Printing "▶ joined review file: ..." for a file
        # ffmpeg never wrote is a green banner over a missing artifact, and it
        # is what this tool did before 2026-09-13.
        if r.returncode != 0 or not joined.exists():
            print(f"⛔ ffmpeg concat FAILED (rc={r.returncode}) — no joined "
                  f"review file was written.\n{(r.stderr or '').strip()}",
                  file=sys.stderr)
            joined = None
            joined_failed = True

    # ⚠ ONE file, task in two lines at the top, caveats BELOW the key
    # (owner, 2026-09-12: the scattered brief was confusing, and he answered by
    # simply listing what he heard). ⛔ Do not split a kit across the audio, a
    # tool's stdout and a separate key.
    joined_name = joined.name if joined else "(no audio built)"
    md = [f"# Ear test — {a.set_key}, your voice",
          "",
          f"**Play `{joined_name}` ({len(clips)} clips, a pause between each). "
          "Tell me which clips repeat something or say extra words, and what "
          "you hear.**",
          "",
          "That is the whole task. Where a clip's text is printed below, the "
          "audio should say exactly that; if it matches, the clip is fine.",
          ""]
    for i, (b, c, v, name, text, span, why) in enumerate(rows, 1):
        md.append(f"**{i}.**")
        if role_of.get((b, c, v), "").startswith("ctl"):
            # ⛔ Withholding the text is the POINT. A positive control only
            # fires if the printed text and the audio CAN disagree; printing
            # text that already contains the doubling makes silence the honest
            # answer, and the control proves nothing (measured 2026-09-13).
            # ⚠ Withheld for BOTH control kinds on purpose: if only the ctl+
            # were textless, "the clip with no text" would BE the answer, and
            # the control would give itself away.
            md.append("_(no text for this one — just say what you hear.)_")
        elif text:
            md.append(text)
        md.append("")
    md += ["---", "",
           "## Key — read AFTER you have listened",
           ""]
    for i, (b, c, v, name, text, span, why) in enumerate(rows, 1):
        md.append(f"- **{i}.** {name} {c + 1}:{v} `{b} {c} v{v}` — "
                  f"{'; '.join(sorted(why))} — clip "
                  f"`{b:02d}_{c:03d}_v{v:03d}.mp3` ({span})")
    md += ["",
           "## Caveats",
           "",
           f"- Every SUSPECT is cut from the LIVE tree (`narration/{a.set_key}/`) "
           "— this is what will ship, not a draw."
           + ("" if not src_of else
              "  ⚠ Some CONTROL clips are cut from a pre-repair backup tree, "
              "because the verse has since been repaired and the live audio no "
              "longer carries the defect the control exists to prove. Which "
              "slots those are is deliberately not stated here."),
           "- ⛔ A verse not listed here is one no source named, NOT one that "
           "passed.",
           "- ⛔ Two cleared verses are not a clearance rate; nothing here "
           "projects onto unheard appends.",
           "- Note markup `{...:...}` is stripped from the printed text above; "
           "it is not spoken and is not printed scripture.",
           ]
    (out / "INDEX.md").write_text("\n".join(md), encoding="utf-8")

    # ⚠⚠ SEND `LISTEN.md`, NEVER `INDEX.md`. INDEX.md carries the key, and the
    # key names which slots are the controls. It sits under "read AFTER you have
    # listened", which is a SOCIAL barrier, not a technical one - one scroll and
    # the instrument is void, and a control that was recognised cannot be
    # distinguished from a control that fired (2026-09-14, Leviticus 22:17).
    # So the listener's half is written out as its own file with the key CUT.
    try:
        cut = md.index("## Key — read AFTER you have listened")
    except ValueError:
        print("⛔ could not find the key heading — refusing to write LISTEN.md "
              "rather than write one that might still contain the key",
              file=sys.stderr)
    else:
        listen = "\n".join(md[:cut]).rstrip().rstrip("-").rstrip() + "\n"
        low = listen.lower()
        # A belt-and-braces check: the listener's file must not contain the
        # words that give a control away, whatever the template later becomes.
        leak = [w for w in ("ctl+", "ctl-", "control") if w in low]
        if leak:
            print("⛔ LISTEN.md would leak %s — not written" % ", ".join(leak),
                  file=sys.stderr)
        else:
            (out / "LISTEN.md").write_text(listen, encoding="utf-8")
            print(f"▶ send THIS to the owner: {out / 'LISTEN.md'} "
                  f"(+ the audio). ⛔ Not INDEX.md — it holds the key.")

    # ⚠ Count the clips actually CUT, never the rows REQUESTED. A row whose
    # audio was missing is still a row, so `len(rows)` reports a full kit for a
    # kit with nothing in it — which is what `--set kjv` did on 2026-09-14:
    # `narration/kjv` does not exist (the set key is `en`), every verse came
    # back "⛔ NO AUDIO ON DISK", and this tool printed "11 verse(s) written"
    # and exited 0. A green banner is not an artifact.
    print(f"{len(clips)} of {len(rows)} verse(s) cut into {out}")
    for (b, c, v, name, _t, span, why) in rows:
        print(f"  {name} {c + 1}:{v:<4} [{b}/{c} v{v}]  {span}   "
              f"{'; '.join(sorted(why))}")
    if joined:
        print(f"\n▶ joined review file: {joined}")
    print(f"▶ index: {out / 'INDEX.md'}")

    # ⛔ A verse the queue named but the kit could not cut makes the kit's
    # denominator wrong, and a MISSING CONTROL makes it void in both
    # directions: a ctl+ that was never cut cannot fire, and its silence is
    # indistinguishable from an ear that missed it. Refuse rather than hand
    # over a kit whose key promises clips it does not contain.
    missing = [r for r in rows if str(r[5]).startswith("⛔")]
    if missing:
        print(f"⛔ KIT INCOMPLETE — {len(missing)} of {len(rows)} queued "
              f"verse(s) produced NO CLIP:", file=sys.stderr)
        for (b, c, v, _n, _t, span, why) in missing:
            print(f"     {b}/{c} v{v}  [{'; '.join(sorted(why))}]  {span}",
                  file=sys.stderr)
        if any("CONTROL" in "; ".join(r[6]) for r in missing):
            print("  ⛔⛔ A CONTROL is among them — this kit proves nothing "
                  "in either direction.", file=sys.stderr)
        print("  ▶ Check --set (it names narration/<set>, and the kjv render "
              "lives in narration/en). Do not send this kit.", file=sys.stderr)
        return 2
    if joined_failed:
        # ⛔ The per-verse clips exist, but the kit he actually plays does not.
        # A kit with no audio is not a kit; fail loudly rather than hand over
        # a brief pointing at a file that was never written.
        print("⛔ KIT INCOMPLETE — clips were cut but the joined audio was "
              "not written. Do not send this kit.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
