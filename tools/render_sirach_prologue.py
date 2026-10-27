# -*- coding: utf-8 -*-
"""Voice the KJV's two Sirach prologues into the Sirach 1 chapter audio.

    # plan (DEFAULT - nothing synthesized, nothing written)
    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\render_sirach_prologue.py
    # do it
    ... --apply

WHY: the reader shows both prologues above Sir 1:1 (rubrics_kjv.json, owner
2026-09-26) and the owner asked for them to be heard as well. The chapter is
ONE ogg with per-verse offsets, so the prologue is spliced IN: the chapter's
announcement, then the prologue, then verse 1 onward exactly as rendered.

    [header][gap][PROLOGUE][original gap][v1] ... [v30]

Every offset (and so every .w.json word time, via align_words --force) moves
by the prologue's length. Nothing before offsets[0] is ever highlighted, so
the reader follows verses exactly as before.

- Text: rubrics_kjv.json (same text the reader shows - one source).
- Voice/engine: narrate.LANG_CONFIG["en"] (the kjv set's chatterbox config);
  each segment goes through narrate.synthesize_verse_gated, i.e. the same ASR
  gate and re-draws as every verse. A segment still failing after its draws
  REFUSES the splice (no arbitrary take installed; owner rule 2026-09-07).
- Level: the prologue is scaled to the chapter's own speech RMS.
- Originals: copied ONCE to narration/en_prologue_originals/71/ and every run
  splices from there, so a re-run never stacks two prologues. Deliberately NOT
  en_qa_fail_originals/: repair_verses reads verses from that backup and takes
  its header from LIVE when offsets[0] moved, which keeps this prologue.
- Idempotence: the sidecar gets "front_matter_ms": [start, end].
- apply_announcements / announce_splice_proof cover books 0-65 only; Sirach
  (71) is never re-headed by them.

After --apply: listen, then upload_narration.py en (the item file
kjv_71_0.ogg + sidecars) and rebuild audio_index_gen.json.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import repair_verses as rv
narrate = rv.narrate
np, sf = rv.np, rv.sf

REPO = Path(__file__).resolve().parent.parent
RUBRICS = REPO / "app" / "src" / "main" / "assets" / "rubrics_kjv.json"
BOOK, CHAP = 71, 0
LIVE = rv.NARRATION / "en" / str(BOOK)
ORIG = rv.NARRATION / "en_prologue_originals" / str(BOOK)
SR = rv.SR
IN_PARA_MS = 450          # between segments of one paragraph
BLOCK_MS = 900            # after a heading / between the two prologues
MAX_SEG = 280             # chars per synthesis take


def segments():
    """[(kind, text)] in reading order; long sentences split at ; or :"""
    rows = json.loads(RUBRICS.read_text(encoding="utf-8"))[f"{BOOK}:1:1"]
    out = []
    for _, t in rows:
        if len(t) <= 120:
            out.append(("h", t.rstrip(".")))
            continue
        for s in re.split(r"(?<=[.?!])\s+", t):
            while len(s) > MAX_SEG:
                cut = max(s.rfind(p, 0, MAX_SEG) for p in (";", ":"))
                if cut < 60:
                    cut = s.rfind(",", 0, MAX_SEG)
                if cut < 60:
                    break
                out.append(("p", s[:cut + 1].strip()))
                s = s[cut + 1:].strip()
            out.append(("p", s.strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    segs = segments()
    joined = " ".join(t for _, t in segs)
    want = " ".join(t for _, t in json.loads(RUBRICS.read_text(encoding="utf-8"))[f"{BOOK}:1:1"])
    if re.sub(r"\W", "", joined) != re.sub(r"\W", "", want):
        sys.exit("FAIL: segmentation lost or added text")
    for k, t in segs:
        print(f"  {k} {len(t):4d}  {t[:80]}")
    print(f"{len(segs)} segments, {sum(len(t) for _, t in segs)} chars; longest "
          f"{max(len(t) for _, t in segs)}")

    src_dir = ORIG if (ORIG / f"{CHAP}.ogg").exists() else LIVE
    side = json.loads((src_dir / f"{CHAP}.json").read_text(encoding="utf-8"))
    if "front_matter_ms" in side:
        sys.exit(f"FAIL: {src_dir} already carries a prologue - the originals are gone?")
    live_side = json.loads((LIVE / f"{CHAP}.json").read_text(encoding="utf-8"))
    print(f"source: {src_dir}  offsets[0]={side['offsets'][0]}  "
          f"live has prologue: {'front_matter_ms' in live_side}")
    if not a.apply:
        print("DRY RUN - nothing synthesized or written (--apply)")
        return 0

    for p in (rv.gpu_busy(),):
        if p:
            sys.exit(f"FAIL: GPU busy ({p}) - pause the render first")
    ORIG.mkdir(parents=True, exist_ok=True)
    for ext in ("ogg", "json", "w.json", "eos.json", "qa.json"):
        f = LIVE / f"{CHAP}.{ext}"
        if f.exists() and not (ORIG / f.name).exists():
            shutil.copy2(f, ORIG / f.name)
    side = json.loads((ORIG / f"{CHAP}.json").read_text(encoding="utf-8"))
    offsets = side["offsets"]

    tmp = rv.NARRATION.parent / "_work" / "sirach_prologue"
    tmp.mkdir(parents=True, exist_ok=True)
    audio = rv.decode(ORIG / f"{CHAP}.ogg", tmp / "src.wav")
    ref_rms = rv.speech_rms(audio[int(offsets[0] / 1000 * SR):], SR)

    takes, record, failing = [], [], []
    for i, (k, t) in enumerate(segs):
        t0 = time.time()
        wav, dur, info = narrate.synthesize_verse_gated(t, "en", str(tmp), 1000 + i, BOOK)
        if not wav or dur <= 0:
            sys.exit(f"FAIL: segment {i} synthesis failed")
        x, sr = sf.read(str(wav), dtype="float32")
        x = rv.resample(x.mean(1) if x.ndim > 1 else x, sr, SR)
        reasons = (info or {}).get("reasons") or []
        print(f"  seg {i:2d} {len(x)/SR:6.1f}s  attempts {len((info or {}).get('attempts') or [])}  "
              f"{'FAILING ' + '|'.join(reasons) if reasons else 'clean'}  ({time.time()-t0:.0f}s)",
              flush=True)
        if reasons:
            failing.append(i)
        takes.append((k, x))
        record.append({"seg": i, "text": t, "info": info})
    (tmp / "gate_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    if failing:
        sys.exit(f"REFUSED: segments {failing} still failing the gate - nothing spliced "
                 f"(record: {tmp / 'gate_record.json'})")

    parts = []
    for i, (k, x) in enumerate(takes):
        parts.append(x)
        if i < len(takes) - 1:
            nxt = takes[i + 1][0]
            ms = BLOCK_MS if (k == "h" or nxt == "h") else IN_PARA_MS
            parts.append(np.zeros(int(SR * ms / 1000), dtype="float32"))
    pro = np.concatenate(parts)
    cur = rv.speech_rms(pro, SR)
    if cur > 1e-6:
        pro = np.clip(pro * (ref_rms / cur), -1.0, 1.0)
    sf.write(str(tmp / "prologue.wav"), (pro * 32767).astype(np.int16), SR, subtype="PCM_16")

    split = int(max(0, offsets[0] - rv.GAP_MS) / 1000 * SR)      # end of header
    gap = np.zeros(int(SR * rv.GAP_MS / 1000), dtype="float32")
    merged = np.concatenate([audio[:split], gap, pro, audio[split:]])
    shift = round((len(gap) + len(pro)) / SR * 1000)
    fm_start = round((split + len(gap)) / SR * 1000)

    wav = tmp / "chapter.wav"
    sf.write(str(wav), (merged * 32767).astype(np.int16), SR, subtype="PCM_16")
    new_ogg = tmp / "chapter.ogg"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", rv.BITRATE,
                        "-c:a", "libopus", "-ac", "1", str(new_ogg)],
                       capture_output=True, creationflags=rv.NO_WINDOW)
    if r.returncode != 0:
        sys.exit("FAIL: encode " + r.stderr.decode(errors="replace")[-200:])
    chk = rv.decode(new_ogg, tmp / "chk.wav")
    if len(chk) < len(merged) * 0.95:
        sys.exit("FAIL: truncated after encode")

    shutil.copy2(new_ogg, LIVE / f"{CHAP}.ogg")
    side["offsets"] = [o + shift for o in offsets]
    side["front_matter_ms"] = [fm_start, fm_start + round(len(pro) / SR * 1000)]
    (LIVE / f"{CHAP}.json").write_text(json.dumps(side, separators=(",", ":")), encoding="utf-8")
    ok, msg = rv.align("kjv", BOOK, CHAP)
    qa_p = LIVE / f"{CHAP}.qa.json"
    qa = json.loads(qa_p.read_text(encoding="utf-8")) if qa_p.exists() else {}
    qa["front_matter"] = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "shift_ms": shift,
                          "segments": len(segs), "align": msg}
    qa_p.write_text(json.dumps(qa, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"{'ok' if ok else 'AUDIO WRITTEN BUT ALIGNMENT FAILED'}: prologue "
          f"{len(pro)/SR:.1f}s at {fm_start} ms, offsets +{shift} ms, align {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
