# -*- coding: utf-8 -*-
"""⛔⛔ INVALIDATED 2026-09-02 BY AN EAR TEST. DO NOT USE IT TO TRIAGE. ⛔⛔

The owner listened to `_work/ylt_earcheck.ogg` - ten flagged verses, of which
FOUR were included as controls precisely because this tool rated them WEAKENED
("no room for the extra audio, likely ASR"). **All ten repeat audibly**,
controls included:

    1/5 v11  "out of his land"   scored +0.17  -> REALLY DOUBLED
    1/34 v11 "and its socket"    scored +0.17  -> REALLY DOUBLED
    1/38 v33 "and its sockets"   scored +0.06  -> REALLY DOUBLED
    1/39 v30 "putteth washing"   scored +0.01  -> REALLY DOUBLED

So the premise is wrong: **a repeated tail does not reliably lengthen the verse.**
`putteth washing` is spoken twice inside a verse carrying 0.01 s of excess. Why
is not established - the likeliest explanations are that narrate.py's trim/fade
cuts the overrun, or that the offsets were derived from pre-trim durations, so
the doubled audio sits inside the recorded span rather than extending it.

▶ **THE LESSON, WHICH IS THE POINT OF KEEPING THIS FILE:** a screen that
produces FALSE NEGATIVES on the defect class is worse than no screen, because it
licenses discarding real defects. This one would have thrown away 8 of 19 known
defects. It was built on a plausible physical argument and was never validated
against ground truth until the ear test - which took two minutes and should have
come FIRST.

▶ **WHAT TO DO INSTEAD: treat every APPEND flag from `qa_asr_sweep.py` as a
real defect candidate.** That detector is validated 10/10 by the same ear test.
Use `qa_asr_clips.py` to hand an ear a batch; do not pre-filter by duration.

The code below is left runnable ONLY so the measurement can be re-examined if
someone works out why duration does not track the repetition. Its verdicts
(CONFIRMED / WEAKENED) mean nothing.

--- original docstring follows ---

Cross-check qa_asr_sweep's APPEND flags against VERSE DURATION. 0 model tokens.

    python tools/qa_asr_confirm.py _work/qa_asr_ylt_full.log --lang ylt

## The idea

`qa_asr_sweep` says the ASR heard words after the last real word. That is a
screen: it cannot tell a render that genuinely repeated itself from an ASR that
stuttered while transcribing a clean render.

**Duration can tell them apart, and it is already on disk.** If the audio really
re-says «and humbleth her», the verse must contain roughly the extra seconds
those three words take to speak. If the render is clean and only the ASR
stuttered, that time is not there.

So for every flagged verse:

    med       = MEDIAN seconds-per-word of the same chapter (same voice, same
                session - the tightest control available)
    predicted = med * (words in the verse)
    excess    = actual duration - predicted
    needed    = med * (words the ASR appended)
    score     = excess / needed

`score` is "how much of the appended words' speaking time is actually present".

    score >= 0.60   the verse carries most of the time the appended words
                    would need -> consistent with repeated audio. CONFIRMS.
    score <= 0.25   there is no room in the audio for them -> the extra words
                    are almost certainly the ASR's. WEAKENS the flag.

⚠ The score is `excess / needed`, NOT a flat sec-per-word ratio. A flat ratio
was tried first and is blind to the target: 3 appended words in a 20-word verse
move a flat ratio by only ~0.15, which reads as 'normal'.

⚠⚠ **NEITHER VERDICT IS PROOF.** A short verse with a long pause, a proper-noun
list read slowly, or a verse ending a paragraph can all inflate the ratio
honestly. This RANKS; an ear decides. Its value is that it is independent
evidence from a different measurement, which is exactly what the
`evidence-discipline` skill asks for before believing a single screen.

⚠ The LAST verse of a chapter has no following offset, so its duration comes
from the file length and includes trailing padding. Those are marked `(last)`
and their ratio is not trustworthy.
"""
import argparse
import io
import json
import re
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"
NOTE = re.compile(r"\s*\{[^{}]*:[^{}]*\}")
HEAD = re.compile(r"^\s*APPEND \[(\d+)/(\d+)\] v(\d+) \+(.*)  ratio ([0-9.]+)\s*$")

ASSET = {"ylt": "en_ylt.json", "kjv": "en_kjv.json", "wbt": "en_webster.json",
         "gnv": "en_geneva.json", "tyn": "en_tyndale.json"}


def durations(lang, b, ch):
    """(seconds per verse, using the sidecar; last verse from file length)."""
    side = NARRATION / lang / str(b) / f"{ch}.json"
    ogg = NARRATION / lang / str(b) / f"{ch}.ogg"
    if not side.exists() or not ogg.exists():
        return None
    off = json.loads(side.read_text())["offsets"]
    try:
        import soundfile as sf
        total = sf.info(str(ogg)).duration
    except Exception:
        return None
    out = []
    for i, s in enumerate(off):
        e = off[i + 1] / 1000 if i + 1 < len(off) else total
        out.append(max(e - s / 1000, 0.001))
    return out


def words(lang, b, ch):
    d = json.loads((ASSETS / ASSET[lang]).read_text(encoding="utf-8"))
    bk = d["books"] if isinstance(d, dict) else d
    return [len(NOTE.sub("", v).split()) for v in bk[b]["chapters"][ch]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--confirm-at", type=float, default=0.60)
    ap.add_argument("--weaken-at", type=float, default=0.25)
    a = ap.parse_args()

    flags = []
    for ln in io.open(a.log, encoding="utf-8", errors="replace"):
        m = HEAD.match(ln)
        if m:
            b, ch, v, added, r = m.groups()
            flags.append((int(b), int(ch), int(v), added.strip().strip("'\""),
                          float(r)))
    if not flags:
        print("no APPEND flags in that log")
        return

    cache = {}
    rows = []
    for b, ch, v, added, r in flags:
        key = (b, ch)
        if key not in cache:
            cache[key] = (durations(a.lang, b, ch), words(a.lang, b, ch))
        durs, wc = cache[key]
        if not durs or len(durs) != len(wc):
            rows.append((None, b, ch, v, added, "no duration data"))
            continue
        spw = [d / w for d, w in zip(durs, wc) if w >= 3]
        if len(spw) < 5:
            rows.append((None, b, ch, v, added, "chapter too short to rank"))
            continue
        med = statistics.median(spw)
        i = v - 1
        if i >= len(durs) or wc[i] < 3:
            rows.append((None, b, ch, v, added, "verse too short to rank"))
            continue
        # ⚠⚠ DO NOT USE A FLAT sec/word RATIO. That was the first version and
        # it CANNOT SEE THE DEFECT IT EXISTS FOR: appending 3 words to a
        # 20-word verse lengthens it ~15 %, so a real repetition scores 1.15x
        # and lands in a "normal length, likely ASR" bucket. A test whose
        # threshold is coarser than its target reports a false all-clear.
        # ▶ Compare the verse's EXCESS duration against the predicted duration
        # of the APPENDED WORDS specifically.
        n_add = len([w for w in added.split() if w])
        predicted = wc[i] * med
        excess = durs[i] - predicted
        need = n_add * med
        score = (excess / need) if need > 0 else 0.0
        note = "(last)" if i == len(durs) - 1 else ""
        detail = (f"{added} [{n_add}w, excess {excess:+.2f}s "
                  f"vs {need:.2f}s needed]")
        rows.append((score, b, ch, v, detail, note))

    ranked = sorted([r for r in rows if r[0] is not None],
                    key=lambda x: -x[0])
    conf = [r for r in ranked if r[0] >= a.confirm_at]
    weak = [r for r in ranked if r[0] <= a.weaken_at]
    mid = [r for r in ranked if a.weaken_at < r[0] < a.confirm_at]

    print("\u26d4 THIS TOOL IS INVALIDATED (2026-09-02 ear test): its WEAKENED "
          "bucket\n   contained 4/4 verified defects. The verdicts below mean "
          "NOTHING.\n   Treat every APPEND flag as a real candidate.\n")
    print(f"{len(flags)} APPEND flag(s) cross-checked against verse duration\n")
    print(f"  CONFIRMED (excess >= {a.confirm_at} of the appended words' predicted time): {len(conf)}")
    for ratio, b, ch, v, added, note in conf:
        print(f"    {b}/{ch} v{v}  score {ratio:+.2f}  {added} {note}")
    print(f"\n  INCONCLUSIVE: {len(mid)}")
    for ratio, b, ch, v, added, note in mid:
        print(f"    {b}/{ch} v{v}  score {ratio:+.2f}  {added} {note}")
    print(f"\n  WEAKENED (<= {a.weaken_at} — no room for the extra audio, likely ASR): {len(weak)}")
    for ratio, b, ch, v, added, note in weak:
        print(f"    {b}/{ch} v{v}  score {ratio:+.2f}  {added} {note}")
    bad = [r for r in rows if r[0] is None]
    if bad:
        print(f"\n  NOT RANKED: {len(bad)}")
        for _, b, ch, v, added, why in bad:
            print(f"    {b}/{ch} v{v}  {why}")
    print("\n⚠ Independent evidence, NOT proof. A long pause, a slowly-read "
          "name list or a\n  paragraph-final verse all buy time honestly. "
          "CONFIRMED means LISTEN first,\n  never re-render first.")


if __name__ == "__main__":
    main()
