# -*- coding: utf-8 -*-
"""Which verses SPEAK a pronunciation the lexicon has since corrected?

    python tools/lexicon_render_debt.py --set ylt
    python tools/lexicon_render_debt.py --set ylt --queue _work/ylt_lexicon_queue.txt

0 model tokens, 0 GPU. Answers the only question that matters before shipping a
set: **is the audio actually saying what the tables now say it should?**

## Why a wired-in lexicon row is not a rendered one

`pronounce_lexicon.py --scope` counts verses the lexicon WOULD change. That is a
scope, not a debt: a row wired in today does nothing to audio rendered last week.
The respelling reaches a listener only when the verse is re-synthesised.

## How «current» is decided — and why it is per VERSE, not per chapter

A verse is CURRENT when it was synthesised at or after the date of every lexicon
row that touches it. Two ways that can be true:

  * the chapter was rendered after the row landed; or
  * the verse carries a repair record (`<chapter>.qa.json` -> repairs[].ts) at
    or after that date.

⚠⚠ A CHAPTER'S FILE MTIME IS NOT EVIDENCE FOR ITS VERSES. `repair_verses.py`
rewrites the whole `.ogg` while re-synthesising only the NAMED verses, so a
chapter touched five minutes ago can be full of month-old takes. Reading mtime
per chapter would report this debt as paid. The per-verse repair records are the
only honest signal, and where they are absent the answer is «not current», not
«probably fine».

⛔ It reports a DEBT, never a defect: a stale verse is not wrong, it simply
still speaks the old pronunciation the owner asked to change.
"""
import argparse
import glob
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")



# ── engine -> venv, derived; a launcher must never hardcode one ────────────
ENGINE_VENV = {
    "kokoro":     "/c/Projects/Hexapla/tools/.kokoro_venv/Scripts/python.exe",
    "chatterbox": "/c/Projects/Hexapla/tools/.chatterbox_venv/Scripts/python.exe",
    "cosyvoice3": "/c/Projects/Hexapla/tools/.cosyvoice_venv/Scripts/python.exe",
}


def engine_of(set_key):
    """The set's engine, read from narrate.py's LANG_CONFIG by AST.

    Parsed rather than imported for the same reason the rest of this module
    parses it: importing narrate.py pulls in soundfile and an engine venv.
    ⛔ Raises rather than defaulting - a wrong engine silently renders a set in
    the wrong voice, which is unrecoverable without a re-render.
    """
    import ast
    src = (Path(__file__).parent / "narrate.py").read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if not (isinstance(t, ast.Name) and t.id == "LANG_CONFIG"):
                continue
            for k, v in zip(node.value.keys, node.value.values):
                if getattr(k, "value", None) != set_key or not isinstance(v, ast.Dict):
                    continue
                for kk, vv in zip(v.keys, v.values):
                    if getattr(kk, "value", None) == "engine":
                        eng = getattr(vv, "value", None)
                        if eng not in ENGINE_VENV:
                            raise SystemExit(
                                f"unknown engine {eng!r} for set {set_key!r} - "
                                f"add it to ENGINE_VENV before generating a launcher")
                        return eng
    raise SystemExit(f"no engine found for set {set_key!r} in narrate.py LANG_CONFIG")

def row_dates(lex):
    """word -> ISO timestamp the row became live, best evidence available.

    ⚠⚠ THE `validated_by` STAMP IS A DATE, AND A DATE IS NOT ENOUGH.
    Repairs carry a full timestamp; rows carry «owner ear 2026-09-07». Comparing
    at day granularity got this wrong in BOTH directions on 2026-09-07:
      * II Kings 5 vv8-25 were repaired at 03:49 for the `Eelighsha` wire-in,
        hours BEFORE the `naaman` row landed the same morning — reported CURRENT
        when they still speak the old name;
      * treating every same-day repair as unproven then condemned 224 `abraham`
        verses the owner confirmed BY EAR are correct.
    ▶ So take the time from GIT: the commit that introduced the respelling.
    ⚠ That is the COMMIT time, not the moment the row was first written, so a
      row wired in and rendered before it was committed is reported as debt it
      does not owe. That direction is deliberate — re-rendering a sound verse
      costs a GPU minute; shipping a wrong reading costs a wrong reading.
    ⛔ A row git cannot date is treated as INFINITELY NEW, never as paid.
    """
    import subprocess
    out = {}
    # ⚠ Rows carry an OPTIONAL 4th element (the sets they are cleared for).
    # Unpacking exactly 3 crashed the moment the first 4-element row landed.
    for w, entry in lex.items():
        sp, _why, by = entry[0], entry[1], entry[2]
        ts = ""
        try:
            r = subprocess.run(
                ["git", "log", "-S", sp, "--format=%aI", "--reverse",
                 "--", "tools/pronounce_lexicon.py"],
                cwd=str(HERE.parent), capture_output=True, text=True, timeout=60)
            ts = (r.stdout or "").strip().splitlines()[0] if r.stdout.strip() else ""
        except Exception:
            ts = ""
        if not ts:
            # ⛔⛔ FIXED 2026-09-07: this used to fall back to the stamp's DAY
            # START, which CONTRADICTED the contract three lines up and
            # UNDER-REPORTED — the one direction that licenses shipping a
            # wrong reading. An uncommitted row (`seeth -> seeith`, wired in
            # 15:5x) was dated 2026-09-07T00:00:00, so the 68 chapters
            # repaired earlier the SAME DAY, hours before the row existed,
            # counted as CURRENT. It hid 3 verses that still say «seethe».
            # ▶ A row git cannot date has no evidence of ever being rendered,
            #   so it is INFINITELY NEW. Commit the row and the real date
            #   takes over; until then every verse it touches is debt.
            ts = "9999-99-99T00:00:00"
        out[w] = ts[:19]
    return out


def set_asset_map():
    """set key -> (asset, ASR language), parsed out of narrate.py.

    ⚠⚠ THE SET DOES NOT IMPLY THE ASSET UNLESS SOMETHING MAKES IT SO. Until
    2026-09-07 `--asset` defaulted to `en_ylt.json` regardless of `--set`, so
    every set read YOUNG'S text: `--set sv` printed ylt's 1327 verses under a
    Swedish label, and `--set en` scored the KJV's audio against ylt's wording.
    ylt's own reading was right only by the accident of the default matching.
    ▶ narrate.py's LANG_CONFIG is the ONE map from a set to its text; this
    parses it rather than keeping a second copy that can drift.
    ⚠ Parsed, not imported: narrate.py pulls in soundfile and the engine venvs,
    and this tool must stay runnable on plain python at 0 tokens and 0 GPU.
    """
    src = (HERE / "narrate.py").read_text(encoding="utf-8")
    m = re.search(r"ASR_LANG = \{(.*?)\}", src, re.S)
    langs = dict(re.findall(r'"([a-z0-9_]+)":\s*"([a-z]+)"', m.group(1))) if m else {}
    out, cur = {}, None
    for line in src[src.index("LANG_CONFIG = {"):].splitlines():
        k = re.match(r'^    "([a-z0-9_]+)": \{', line)
        if k:
            cur = k.group(1)
        av = re.match(r'^        "asset": "([^"]+)"', line)
        if av and cur:
            out[cur] = (av.group(1), langs.get(cur))
    if not out:
        raise SystemExit("⛔ could not parse LANG_CONFIG out of narrate.py — "
                         "refusing to fall back to a guessed asset")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--asset", help="override the set's own asset; almost "
                    "always wrong — the set decides the text")
    ap.add_argument("--queue", help="write a repair_verses queue of the debt")
    ap.add_argument("--script", help="write a per-chapter repair_verses "
                    "launcher (.sh) for the debt")
    a = ap.parse_args()

    import pronounce_lexicon as pl
    dates = row_dates(pl.LEXICON)

    sets = set_asset_map()
    if a.set_key not in sets:
        print(f"⛔ unknown set '{a.set_key}' — narrate.py knows: "
              + ", ".join(sorted(sets)))
        return 2
    asset, asr = sets[a.set_key]
    if a.asset and a.asset != asset:
        print(f"⚠ --asset overrides {a.set_key}'s own text {asset}")
        asset = a.asset
    elif asr != "en":
        # The lexicon holds ENGLISH respellings (`prophesy -> prophesigh`).
        # Matching them against a Swedish or Slavonic text yields a debt that
        # cannot exist, and a 0 there would be equally meaningless.
        print(f"⛔ {a.set_key} is a '{asr}' set and the pronunciation "
              "lexicon is ENGLISH respellings; any figure here would be "
              "noise, in either direction. Refusing.")
        return 2

    # ⚠⚠ THE ROWS ARE SCOPED PER SET — see pronounce_lexicon.row_sets.
    # Scoring a set against rows it is not cleared for invents a debt that
    # cannot be paid by any render.
    live_rows = pl.rows_for(a.set_key)

    books = json.loads((ASSETS / asset).read_text(encoding="utf-8"))
    nar = DATA / "narration" / a.set_key

    # verse -> the newest lexicon-row date that applies to it
    need = {}
    for bi, b in enumerate(books):
        for ci, ch in enumerate(b["chapters"]):
            for vi, text in enumerate(ch, 1):
                _, hits = pl.apply(text, a.set_key)
                if hits:
                    d = max(dates.get(h.lower(), "9999-99-99") for h in hits)
                    need[(bi, ci, vi)] = (d, sorted(set(hits)))
    if not live_rows:
        # ⛔⛔ NOT A CLEAN RESULT, AND NOT A DEBT OF ZERO. Until 2026-09-08 this
        # tool called `pl.apply(text)` with no set, so EVERY set was scored
        # with ylt's rows: `--set wbt` printed «28 falleth stale» for a set
        # narrate.py applies no row to at all. That debt was UNPAYABLE — a
        # re-render would have produced byte-identical audio, because
        # `rows_for("wbt")` is empty.
        # ▶ A set with no cleared rows has NO lexicon debt and NO lexicon
        #   coverage. Those are different facts and this must never print the
        #   first while meaning the second.
        print(f"⛔ NO LEXICON ROW IS CLEARED FOR '{a.set_key}' — "
              f"rows_for('{a.set_key}') is empty.")
        print("   This is NOT «0 stale / clean». A re-render would change "
              "nothing, because narrate.py applies no respelling to this set.")
        print("   Every row was ear-validated on ylt's voice. A row reaches "
              "another set only by naming that set in its 4th element, "
              "and only after an ear test ON THAT SET's voice/engine.")
        return 2
    if not need:
        print(f"⛔ no verse matched any of the {len(live_rows)} row(s) cleared "
              f"for '{a.set_key}' — that is not a clean result, it means the "
              "matcher or the asset is wrong")
        return 2

    # ── EXACT EVIDENCE: the recorded synthesis input ───────────────────────
    # ⚠⚠ A DATE IS A PROXY; THE `synth_sha` IS THE THING ITSELF. repair_verses
    # records sha1 of the exact string it handed the synthesiser. If that
    # equals the string today's lexicon produces, the verse WAS rendered with
    # today's respelling — no date reasoning can improve on that, and none can
    # overrule it.
    # ⛔⛔ WITHOUT THIS THE TOOL DEADLOCKS ON ITS OWN WORKFLOW. Row dates come
    # from the GIT COMMIT, and the real sequence is wire in -> render ->
    # commit, so a freshly committed row is always NEWER than the render that
    # already paid it. On 2026-09-07 that reported 229 verses as owing a
    # re-render they had just had; obeying it would have cost 2+ hours of GPU
    # to produce byte-identical audio.
    # ⚠ Falls back to dates when the synthesis path cannot be imported (it
    #   needs the engine venv). The fallback OVER-reports and says so — it is
    #   never silently trusted as a clean result.
    sha_ok, spoken = set(), None
    try:
        sys.path.insert(0, str(HERE))
        import repair_verses as _rv
        import narrate as _nar
        spoken = (_rv.spoken_verses, _nar.load_bible(a.set_key))
    except Exception as e:                       # noqa: BLE001
        print(f"⚠ synthesis path unavailable ({type(e).__name__}) — falling "
              f"back to ROW DATES, which OVER-report a row committed after "
              f"the render that paid it. Re-run with the engine venv python "
              f"for an exact answer.")

    if spoken:
        import hashlib
        fn, sbooks = spoken
        by_chapter = defaultdict(list)
        for (bi, ci, vi) in need:
            by_chapter[(bi, ci)].append(vi)
        for (bi, ci), vlist in by_chapter.items():
            qa = nar / str(bi) / f"{ci}.qa.json"
            if not qa.exists():
                continue
            try:
                recs = json.loads(qa.read_text(encoding="utf-8"))
                vs = fn(a.set_key, sbooks, bi, ci)
            except Exception:                    # noqa: BLE001
                continue
            latest = {}
            for r in recs.get("repairs") or []:
                v = r.get("verse")
                if v is None or not r.get("synth_sha"):
                    continue
                latest[int(v)] = r["synth_sha"]
            for vi in vlist:
                if vi > len(vs):
                    continue
                want_sha = hashlib.sha1(
                    vs[vi - 1].encode("utf-8")).hexdigest()[:12]
                if latest.get(vi) == want_sha:
                    sha_ok.add((bi, ci, vi))

    # verse -> latest synthesis we can PROVE, from per-verse repair records
    proved = {}
    for f in glob.glob(str(nar / "*" / "*.qa.json")):
        p = Path(f)
        bi, ci = int(p.parent.name), int(p.name.split(".")[0])
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in d.get("repairs") or []:
            ts = (r.get("ts") or "")[:19]      # full timestamp, not the day
            v = r.get("verse")
            if ts and v:
                k = (bi, ci, v)
                if ts > proved.get(k, ""):
                    proved[k] = ts

    # ⛔⛔ STRICTLY LATER, NOT «>=» — a same-day repair proves NOTHING.
    # A lexicon row records only a DATE («owner ear 2026-09-07»), while repairs
    # carry a full timestamp. Comparing them with «>=» silently assumes the
    # repair came after the row, and on 2026-09-07 that was false: II Kings 5
    # vv8-25 were repaired at 03:49 for the `Eelighsha` wire-in, hours BEFORE
    # the `naaman` row was added the same morning. Those verses still speak the
    # old name and the first version of this tool reported them CURRENT.
    # ▶ Intra-day ordering is unknowable from the row, so a same-day repair is
    #   UNPROVEN and counts as debt. Re-rendering a verse that was already fine
    #   costs a minute; shipping one that is not costs a wrong reading.
    stale, current, by_sha = [], 0, 0
    for k, (d, hits) in sorted(need.items()):
        if k in sha_ok:                    # ★ proof, not a proxy — see above
            current += 1
            by_sha += 1
        elif proved.get(k, "") > d:        # strictly later than the row's commit
            current += 1
        else:
            stale.append((k, d, hits))

    per_word = defaultdict(int)
    for _k, _d, hits in stale:
        for h in hits:
            per_word[h.lower()] += 1
    chapters = {(b, c) for (b, c, _v), _d, _h in stale}

    print(f"{a.set_key} ({asset}): {len(need)} verse(s) carry a "
          "lexicon respelling")
    print(f"   {current} verified re-synthesised after their row landed"
          + (f"  ({by_sha} of them proved by synth_sha, the rest by date)"
             if by_sha else ""))
    print(f"   {len(stale)} STILL SPEAK THE OLD PRONUNCIATION "
          f"across {len(chapters)} chapter(s)\n")
    for w in sorted(per_word, key=lambda x: -per_word[x]):
        print(f"   {w:<14} {per_word[w]:>5} stale verse(s)   "
              f"(row {dates.get(w)})")

    if a.queue or a.script:
        # ⛔ UNION RULE: a repair rebuilds the chapter from the originals and
        # splices only the NAMED verses, so every verse in a chapter that
        # carries a prior repair must be named too or it REVERTS.
        by_ch = defaultdict(set)
        for (b, c, v), _d, _h in stale:
            by_ch[(b, c)].add(v)
        for f in glob.glob(str(nar / "*" / "*.qa.json")):
            p = Path(f)
            b, c = int(p.parent.name), int(p.name.split(".")[0])
            if (b, c) not in by_ch:
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for r in d.get("repairs") or []:
                if r.get("verse"):
                    by_ch[(b, c)].add(r["verse"])
        total = sum(len(v) for v in by_ch.values())
        if a.queue:
            lines = [f"{b} {c} v{','.join(str(x) for x in sorted(vs))}"
                     for (b, c), vs in sorted(by_ch.items())]
            Path(a.queue).write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"\n▶ queue written: {a.queue}")
            print(f"   {len(by_ch)} chapter(s), {total} verse(s) named "
                  f"({total - len(stale)} of them added ONLY to satisfy the "
                  f"union rule — they carry prior repairs and would revert if "
                  f"omitted)")

        if a.script:
            # ⚠⚠ THE TWO LISTS ARE NOT THE SAME LIST, and conflating them is
            # how a correct take gets discarded:
            #   --verses      = the UNION (stale + every prior-repair verse in
            #                   the chapter), or the omitted ones REVERT;
            #   --install-tied = ONLY the stale ones, whose synthesis input
            #                   actually changed. A verse named here may
            #                   install a tied take; every other verse keeps
            #                   its existing take on a tie (the 2026-09-07 fix).
            # ⛔ ONE INVOCATION PER CHAPTER: --install-tied takes bare verse
            #   NUMBERS, so a multi-chapter run would let a number install a
            #   tied take in the WRONG chapter.
            # ⛔ NO `set -e`: a verse still failing its gate is a NORMAL
            #   outcome, and aborting would leave the rest unrendered while
            #   looking finished.
            stale_by_ch = defaultdict(set)
            for (b, c, v), _d, _h in stale:
                stale_by_ch[(b, c)].add(v)
            out_l = [
                "#!/bin/sh",
                "# Re-render every verse that still speaks a pre-lexicon "
                "pronunciation.",
                "# GENERATED by tools/lexicon_render_debt.py --script — "
                "DERIVED, never hand-listed.",
                "#   sh <this> apply    # writes (GPU)",
                "cd /c/Projects/Hexapla-releases",
                # ⛔⛔ THE VENV IS DERIVED FROM THE SET'S ENGINE, NEVER
                # HARDCODED. This literal used to read `.chatterbox_venv`
                # because ylt was the only set that had ever used this tool.
                # The first launcher generated for `wbt` — a KOKORO set —
                # therefore named the chatterbox venv, which would have driven
                # a kokoro set's repair through the wrong engine. Same
                # set-blindness class as the scoring bug fixed 2026-09-08.
                f"PY={ENGINE_VENV[engine_of(a.set_key)]}",
                "TOOL=/c/Projects/Hexapla/tools/repair_verses.py",
                'if [ "$1" = "apply" ]; then A="--apply"; else A=""; fi',
                "",
            ]
            for (b, c), vs in sorted(by_ch.items()):
                st = sorted(stale_by_ch[(b, c)])
                out_l.append(f'echo "=== {b}/{c}  stale {len(st)} of '
                             f'{len(vs)} named ==="')
                out_l.append(
                    f'"$PY" "$TOOL" --set {a.set_key} --book {b} '
                    f'--chapter {c} '
                    f'--verses {",".join(str(x) for x in sorted(vs))} '
                    f'--install-tied {",".join(str(x) for x in st)} $A')
            Path(a.script).write_text("\n".join(out_l) + "\n",
                                      encoding="utf-8", newline="\n")
            print(f"\n▶ launcher written: {a.script}")
            print(f"   {len(by_ch)} chapter(s), {len(stale)} stale verse(s), "
                  f"{total} named in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
