# -*- coding: utf-8 -*-
"""Find UNACCOUNTED SPEECH in finished narration - audio the text cannot explain.

    python tools/verse_tail_scan.py ylt --book 0                 # sample a book
    python tools/verse_tail_scan.py ylt --book 0 --chapter 3      # one chapter
    python tools/verse_tail_scan.py ylt --all                     # whole set

WHY THIS EXISTS (2026-08-22). The owner found two defects BY EAR in the first
four ylt chapters: a "dad did" after "Genesis, chapter one", and "present to
Jehovah" spoken twice at the end of Genesis 4:3. Both are the same class -
Chatterbox appends speech the text does not contain - and in BOTH cases
replaying narrate.py's `_cut_spoken_tail` over the shipped audio removes the
defect cleanly. So the defect is detectable; it simply was not detected at
render time.

⚠ THE POINT: nobody can listen to 1189 chapters. A render that relies on the
owner's ear to find defects does not scale, and every defect he finds by ear is
one the machinery should have found first. This turns his ear into a
measurement.

HOW IT WORKS - and why it costs ZERO model tokens. MMS_FA forced alignment maps
each word of the verse TEXT onto the audio. Speech that sits outside that map is
audio the text cannot account for:

  * TAIL      - loud speech after the last aligned word, separated from it by a
                real pause. This is the hallucination/repeat class.
  * INTERNAL  - loud speech inside a gap between two consecutive aligned words
                that is far longer than a normal inter-word pause. This is the
                mid-verse repeat class, which the tail cutter cannot see because
                it only ever looks after the LAST word.

⚠ WHISPER/ASR CANNOT DO THIS JOB. Handed famous scripture it recites the next
verse from memory and "hears" it in the recording. Forced alignment is
constrained to the text we actually rendered, so it cannot hallucinate agreement.

⚠ A DETECTION IS NOT A VERDICT. Verse-final punctuation, breaths and a
dramatised pause all produce small unaccounted spans. The threshold below is set
from measurement, not taste: the two owner-confirmed defects run 860 ms and
60 ms, while clean verses across the same chapters sit at 0. Report the number
and let a human judge anything marginal.

⚠ RUNS ON CPU BY DEFAULT and must stay that way - the GPU belongs to the render.
Two chatterbox-sized jobs on the 8 GB card took sampling from 1.7 s/step to
1190 s/step (measured), so never move this to cuda while a render is live.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NARRATION = r"C:\Projects\Hexapla-releases\narration"

# A hallucinated tail always sits after a real pause; contiguous speech is the
# word still finishing.
GAP_MS = 200
# ⚠⚠ DURATION IS THE WRONG LEVER FOR THE TAIL CASE — calibrated against the
# owner's ear 2026-08-22. He heard blips of 60 ms (Genesis 1:1 "uh") AND 20 ms
# (Genesis 3:13, after "and I do eat"). A 20 ms run is ONE frame, so no
# duration floor that suppresses breath noise can also catch it.
# What separates an artifact from speech is not how long it is, it is HOW LONG
# THE SILENCE BEFORE IT WAS. Real speech does not resume for 20 ms after 1.26 s
# of silence — that verse had ended. So the tail test uses a LONG gap and
# essentially no duration floor, while the internal/leading tests keep a
# duration floor because there the gaps are short and breath is common.
MIN_RUN_MS = 60          # internal + leading tests only
TAIL_GAP_MS = 400        # an end-of-utterance pause, not an inter-word one
TAIL_MIN_RUN_MS = 20     # one frame: anything voiced after that pause counts
# Loudness floor relative to the verse's own 90th-percentile level, matching
# narrate.py so this screen and the cutter agree about what "speech" is.
REL_DB = -28


def speech_frames(audio, sr, hop_ms=20):
    ref = np.percentile(np.abs(audio), 90) + 1e-9
    h = max(1, int(hop_ms / 1000.0 * sr))
    n = len(audio) // h
    if n == 0:
        return np.zeros(0, dtype=bool), h
    db = 20 * np.log10(
        np.sqrt((audio[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    return db > (20 * np.log10(ref) + REL_DB), h


def _runs(mask, hop_ms=20):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        if not v and s is not None:
            out.append((s * hop_ms, i * hop_ms))
            s = None
    if s is not None:
        out.append((s * hop_ms, len(mask) * hop_ms))
    return out


def scan_verse(audio, sr, text, aligner, align_key, WORD, int_words):
    """Return (tail_ms, internal_ms, lead_ms, detail) for one verse."""
    import re
    import torch
    import torchaudio.functional as AF

    # Digits are spoken but not alignable - expand them or the spoken number
    # itself reads as unaccounted audio. (Same trap narrate.py documents.)
    if any(c.isdigit() for c in text):
        text = re.sub(r"\d+",
                      lambda m: int_words(int(m.group(0)))
                      if 0 < int(m.group(0)) < 1000 else m.group(0), text)
        if any(c.isdigit() for c in text):
            return None                      # cannot expand -> no verdict

    keys = [k for k in (align_key(w, "latin", "en") for w in WORD.findall(text))
            if k]
    if not keys:
        return None
    w = torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32))
    if sr != aligner.sample_rate:
        w = AF.resample(w, sr, aligner.sample_rate)
    spans = aligner.align(w, keys)
    if spans is None or spans[-1] is None or spans[0] is None:
        return None

    mask, hop = speech_frames(audio, sr)
    if not len(mask):
        return None
    runs = _runs(mask)

    # ---- LEADING: loud speech BEFORE the first aligned word ----
    # ⚠⚠ THIS IS THE CASE THE TAIL CUTTER CANNOT SEE, AND IT IS THE ONE THAT
    # PRODUCES THE AUDIBLE REPEATS. Forced alignment maps the text onto ONE
    # occurrence of a repeated phrase. When Chatterbox says "present to Jehovah"
    # twice, the aligner is free to map the whole verse onto the SECOND copy —
    # and then the unaccounted audio lies BEFORE the first word, where
    # narrate.py's `_cut_spoken_tail` never looks, because it only ever walks
    # forward from the LAST word. That is why Genesis 4:3 shipped with an
    # audible repeat while the cutter reported nothing: not a threshold
    # failure, a blind spot in the geometry.
    # ⚠ CALIBRATION: at MIN_RUN_MS this test fired on 6 verses across Genesis
    # 5-6 with a near-constant 60-81 ms at 0.3 s — that is the LEAD_MS=305 edge
    # pad, not a repeat. Every one was a false positive. A real repeat leaves
    # a whole clause unaccounted (Genesis 4:3 is 880 ms), so the floor is set
    # far above the pad artifact. ⚠ UNVALIDATED against a confirmed leading
    # repeat — no such case has been caught yet; treat a hit as "go listen",
    # not as a verdict.
    LEAD_MIN_MS = 300
    first_start_ms = spans[0][0] * 1000.0
    lead_ms, lead_at = 0, None
    for a, b in runs:
        ov = min(b, first_start_ms) - a
        if ov >= LEAD_MIN_MS:
            lead_ms += ov
            if lead_at is None:
                lead_at = a

    # ---- TAIL: loud speech after a >=GAP_MS pause following the last word ----
    # Walk from the last word's START, not its end. MMS_FA must assign every
    # frame to some token, so a hallucination that follows the final word gets
    # ABSORBED INTO THAT WORD'S SPAN and the word's END lands past the defect.
    last_start_ms = spans[-1][0] * 1000.0
    tail_ms, tail_at = 0, None
    prev_end = None
    for a, b in runs:
        if b <= last_start_ms:
            prev_end = b
            continue
        if prev_end is not None and a - prev_end >= TAIL_GAP_MS and a > last_start_ms:
            if (b - a) >= TAIL_MIN_RUN_MS:
                tail_ms += (b - a)
                if tail_at is None:
                    tail_at = a
        prev_end = b

    # ---- INTERNAL: loud speech in an over-long gap between two words ----
    internal_ms, internal_at = 0, None
    for (s1, e1), (s2, _) in zip(spans, spans[1:]):
        if e1 is None or s2 is None:
            continue
        g0, g1 = e1 * 1000.0, s2 * 1000.0
        if g1 - g0 < GAP_MS * 2:            # a normal inter-word pause
            continue
        for a, b in runs:
            ov = min(b, g1) - max(a, g0)
            if ov >= MIN_RUN_MS:
                internal_ms += ov
                if internal_at is None:
                    internal_at = max(a, g0)
    return tail_ms, internal_ms, lead_ms, (tail_at, internal_at, lead_at)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="find speech the verse text cannot account for")
    ap.add_argument("set")
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--device", default="cpu",
                    help="LEAVE AS cpu while a render is running")
    args = ap.parse_args(argv)

    import soundfile as sf
    import narrate
    from align_words import Aligner, align_key, WORD

    cfg = narrate.LANG_CONFIG[args.set]
    books = narrate.load_bible(args.set)
    books = books if isinstance(books, list) else books["books"]
    aligner = Aligner(device=args.device)

    root = os.path.join(NARRATION, args.set)
    if not os.path.isdir(root):
        print("no such set directory: %s" % root, file=sys.stderr)
        return 2

    targets = []
    for bi in sorted(int(d) for d in os.listdir(root) if d.isdigit()):
        if args.book is not None and bi != args.book:
            continue
        bd = os.path.join(root, str(bi))
        for f in sorted(os.listdir(bd)):
            if not f.endswith(".ogg"):
                continue
            ci = int(f[:-4])
            if args.chapter is not None and ci != args.chapter:
                continue
            targets.append((bi, ci, os.path.join(bd, f)))
    if not targets:
        print("no chapters matched", file=sys.stderr)
        return 2

    flagged = checked = skipped = 0
    for bi, ci, path in targets:
        try:
            off = json.load(open(path.replace(".ogg", ".json")))["offsets"]
        except Exception as e:
            print("  %d/%d: NO SIDECAR (%s)" % (bi, ci, e))
            skipped += 1
            continue
        x, sr = sf.read(path)
        if x.ndim > 1:
            x = x.mean(1)
        raw = books[bi]["chapters"][ci]
        verses = []
        for v in raw:
            if cfg["strip_notes"]:
                v = narrate.strip_kjv_notes(v)
            if cfg["normalizer"]:
                v = narrate.normalize_text(v, cfg["normalizer"])
            verses.append(v)
        if len(off) != len(verses):
            print("  %d/%d: %d offsets for %d verses - UNCHECKABLE"
                  % (bi, ci, len(off), len(verses)))
            skipped += 1
            continue
        hits = []
        for i, t in enumerate(verses):
            a = off[i]
            b = off[i + 1] if i + 1 < len(off) else int(len(x) / sr * 1000)
            seg = np.ascontiguousarray(x[int(a / 1000 * sr):int(b / 1000 * sr)],
                                       dtype=np.float32)
            if len(seg) < sr * 0.3:
                continue
            r = scan_verse(seg, sr, t, aligner, align_key, WORD,
                           narrate._int_words)
            if r is None:
                continue
            tail, internal, lead, (t_at, i_at, l_at) = r
            if tail >= TAIL_MIN_RUN_MS or internal >= MIN_RUN_MS                     or lead >= 300:
                hits.append((i + 1, tail, internal, lead, t_at, i_at, l_at))
        checked += 1
        if hits:
            flagged += 1
            print("  %d/%d: %d verse(s) with unaccounted speech" % (bi, ci, len(hits)))
            for v, tail, internal, lead, t_at, i_at, l_at in hits:
                bits = []
                if tail:
                    bits.append("tail %d ms @ %.1fs into verse" % (tail, t_at / 1000.0))
                if internal:
                    bits.append("internal %d ms @ %.1fs into verse"
                                % (internal, i_at / 1000.0))
                if lead:
                    bits.append("LEADING %d ms before the first aligned word "
                                "@ %.1fs (repeat signature)"
                                % (lead, l_at / 1000.0))
                print("      v%-3d %s" % (v, "; ".join(bits)))

    print()
    print("  %d chapter(s) checked, %d with unaccounted speech, %d skipped"
          % (checked, flagged, skipped))
    # ⚠ A failed read must never look like a clean result.
    return 1 if skipped and not checked else 0


if __name__ == "__main__":
    sys.exit(main())
