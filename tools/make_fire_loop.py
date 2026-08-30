# -*- coding: utf-8 -*-
"""Synthesize the seamless fireside loop bundled in the APK.

    python tools/make_fire_loop.py                    # write the .ogg + a .wav
    python tools/make_fire_loop.py --seconds 30 --seed 7

Writes `app/src/main/assets/ambience/fire_loop.ogg`, which is the asset
`ReadingService.FIRESIDE_ASSET` looks for.

## WHY SYNTHESIZE RATHER THAN SOURCE A RECORDING

The owner's rule is that every shipped asset is public domain or CC with
attribution, and proving the provenance of a "free" fire recording is exactly
the trap `pd-provenance` warns about — most aggregator uploads are re-uploads
with a licence the uploader never held. Synthesized audio has no such question:
we made it, we own it, there is nothing to attribute and nothing to verify.
It also costs no download.

▶ If a real recording is ever preferred, this file is the thing it replaces,
and the credit for it belongs in `sources_text` (a CC-BY recording is a
PROMISED credit under the owner's 2026-07-16 policy).

## HOW IT LOOPS PERFECTLY — no crossfade, no seam

A crossfaded loop still ticks, because the two ends are different noise.
Instead:

  · the BED and HISS are built in the FREQUENCY domain — a spectral envelope
    with random phase, inverse-FFT'd. The result is mathematically periodic
    over the buffer, so its end already joins its start exactly.
  · the CRACKLES are written into a circular buffer: a transient that starts
    near the end wraps around and finishes at the beginning, so the decay
    continues across the loop point instead of being cut.

There is therefore no fade at either end and no discontinuity to hear.

## ⚠ THE 2026-08-30 RETUNE — READ BEFORE CHANGING ANY LEVEL

The owner rejected the first three candidates: "sounds like fire in the middle
of a raging river." A real fireplace recording was then measured as a
REFERENCE WITNESS (it is NOT shipped and its licence was never established --
it only told us what to aim at). It measures **crest 30.0 dB, flatness 0.096**;
the rejected candidates measured **16.4 dB, 0.017**. Three independent causes,
all fixed here:

  1. `roar_lvl` was **0.62** against `pareto * 0.05` crackles, so the
     continuous bed simply drowned the transients. Now 0.10.
  2. the crackle burst was multiplied by a SINGLE COSINE CARRIER -- ring
     modulation, which moves broadband noise onto a narrow band and yields a
     tuned *ping*. Now a first-difference high-pass, which stays broadband.
  3. the encoder was `-q:a 1`, which by itself collapsed flatness from 0.098
     to 0.030 -- so even a perfect synth was being wrecked on the way out.
     q3 is now a floor.

▶ `main()` re-decodes the finished .ogg and MEASURES IT, and **raises rather
than presenting a candidate that fails**. Judge the encoded file, never the
float buffer: they differ, and the difference is what the owner hears.

## ⚠⚠ "TOO DENSE" IS NOT WHAT CREST FACTOR MEASURES — THE 2026-08-30b FINDING

The owner heard the retune above as "too dense" even though its crest (36.8 dB)
was already SPARSER than the reference's 30.0. Crest is one peak over the whole
buffer, so it says nothing about how the time in between is filled. Measuring
the distribution of 25 ms window energies instead inverted the picture:

    REFERENCE  median -14.7 dB   only  1.7% of windows below -20 dB
    that synth median -23.6 dB       82.1% of windows below -20 dB

**Real fire is a CONTINUOUS texture punctuated by pops. That synth was
countable pops over near-silence** — which is what "dense" was describing: not
too much sound, too many separately audible events.

▶ The fix was therefore NOT simply fewer crackles. It was fewer crackles **plus
a much louder broadband `hiss` bed** (0.05 -> 0.22) to blend them, keeping
`roar` low so the low rumble never returns as the "river". ⚠ `hiss` and `roar`
are NOT interchangeable: roar is 20-420 Hz and is the river knob; hiss is
900-6500 Hz and is the texture knob.

⚠ Thinning has a floor. Below ~15 crackles/sec the bed dominates the spectrum,
flatness falls back under the gate, and the tool refuses the candidate. Raise
`--amp` to buy a little more thinning; past that, the shape stops being fire.

## WHAT A FIRE ACTUALLY SOUNDS LIKE

Three layers, and getting the balance right matters more than any one of them:
  1. a low roar — brown-ish noise under ~400 Hz, slowly swelling;
  2. a broadband hiss — the steam and gas, ~1-5 kHz, quiet;
  3. crackles — short decaying bursts, Poisson-distributed in time, with a
     power-law amplitude spread so most are tiny and a few are sharp. Uniform
     crackles are the thing that makes synthetic fire sound like a machine.

⚠ This is a BED that plays under narration at low volume. It is deliberately
mixed dark and quiet, with the crackle peaks well below full scale, so it never
competes with a voice. Do not "improve" it by making it louder or brighter.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "app/src/main/assets/ambience"
SR = 32000          # 16 kHz Nyquist: everything a fire bed needs, and small


def spectral_noise(n, sr, rng, lo, hi, slope):
    """Periodic noise shaped by a band and a spectral slope.

    Built via rFFT with random phase, so the buffer is exactly periodic —
    this is what makes the loop seamless without a crossfade.
    """
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mag = np.zeros_like(freqs)
    band = (freqs >= lo) & (freqs <= hi)
    f = np.maximum(freqs[band], 1e-6)
    mag[band] = f ** slope
    # soften the band edges so the noise does not sound filtered
    if band.any():
        idx = np.where(band)[0]
        ramp = max(1, len(idx) // 8)
        mag[idx[:ramp]] *= np.linspace(0, 1, ramp)
        mag[idx[-ramp:]] *= np.linspace(1, 0, ramp)
    phase = rng.uniform(0, 2 * np.pi, len(freqs))
    spec = mag * np.exp(1j * phase)
    out = np.fft.irfft(spec, n)
    peak = np.max(np.abs(out))
    return out / peak if peak > 0 else out


def slow_envelope(n, sr, rng, rate, depth):
    """A gentle, periodic swell — the fire breathing. Periodic by construction:
    only integer numbers of cycles over the buffer are used."""
    t = np.arange(n) / sr
    dur = n / sr
    env = np.zeros(n)
    for _ in range(4):
        cycles = max(1, int(round(rng.uniform(0.4, 2.2) * dur * rate)))
        env += rng.uniform(0.5, 1.0) * np.sin(
            2 * np.pi * cycles * t / dur + rng.uniform(0, 2 * np.pi))
    env /= np.max(np.abs(env)) or 1.0
    return 1.0 - depth + depth * (0.5 + 0.5 * env)


def crackles(n, sr, rng, per_sec, amp_scale=0.25, brightness=0.3):
    """Poisson-timed decaying transients written into a CIRCULAR buffer.

    Amplitudes are power-law (rng.pareto): many faint ticks, a few sharp pops.
    Uniform amplitudes are the single thing that makes synthetic fire sound
    mechanical, so this is where the character lives.
    """
    left = np.zeros(n)
    right = np.zeros(n)
    count = int(per_sec * n / sr)
    for _ in range(count):
        start = rng.integers(0, n)
        # 1.5-40 ms, skewed short
        dur_ms = float(np.clip(rng.gamma(2.0, 3.5), 1.5, 40.0))
        ln = max(4, int(sr * dur_ms / 1000.0))
        # a BROADBAND burst, decaying fast.
        # ⚠⚠ DO NOT multiply by a single cosine carrier. That is ring
        # modulation: it moves broadband noise onto a NARROW band, and it is
        # exactly what made the first three candidates a tuned *ping* rather
        # than a snap -- measured spectral flatness 0.017 against a real
        # fire's 0.096. A first difference tilts the noise bright while
        # leaving it broadband.
        k = np.arange(ln)
        raw = rng.standard_normal(ln + 1)
        # ⚠ BRIGHTNESS IS THE STATIC KNOB. 1.0 is a pure first difference
        # (+6 dB/oct) -- that is what pushed the spectral centroid to 4-5 kHz
        # against a real fire's ~2 kHz, and the owner heard it, correctly, as
        # static. 0.0 is raw noise. Keep it low; see the centroid note above.
        burst = raw[1:] + brightness * np.diff(raw)
        burst *= np.exp(-k / (ln / 4.0))
        amp = min(rng.pareto(2.2) * amp_scale, 1.0)
        burst *= amp
        pan = rng.uniform(0.15, 0.85)
        idx = (start + k) % n          # <- the wrap that keeps the loop seamless
        np.add.at(left, idx, burst * (1.0 - pan))
        np.add.at(right, idx, burst * pan)
    return left, right


def build(seconds, seed, per_sec=20.0, hiss_lvl=0.18, roar_lvl=0.10,
          amp_scale=0.25, brightness=0.3):
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)

    def one_channel(r):
        roar = spectral_noise(n, SR, r, 20, 420, -0.9)
        roar *= slow_envelope(n, SR, r, 0.35, 0.45)
        # ⚠ BAND WAS 900-6500 Hz WITH SLOPE -0.7 AND THAT WAS TOO BRIGHT.
        # 300-2800 with a steeper -1.3 puts the bed where a real fire's
        # continuous energy actually sits.
        hiss = spectral_noise(n, SR, r, 300, 2800, -1.3)
        hiss *= slow_envelope(n, SR, r, 0.8, 0.6)
        return roar_lvl * roar + hiss_lvl * hiss

    left = one_channel(rng)
    right = one_channel(rng)          # independent -> a wide, non-mono bed
    cl, cr = crackles(n, SR, rng, per_sec=per_sec, amp_scale=amp_scale,
                      brightness=brightness)
    left += cl
    right += cr

    stereo = np.stack([left, right], axis=1)
    peak = np.max(np.abs(stereo))
    if peak > 0:
        stereo = stereo / peak * 0.72   # headroom: this plays UNDER a voice
    return stereo


# ── THE TWO NUMBERS A CANDIDATE IS JUDGED ON ────────────────────────────────
# Measured from a real fireplace recording used as a REFERENCE WITNESS ONLY
# (2026-08-30). The recording itself is NOT shipped and its licence was never
# established -- it exists to tell us what to aim at, nothing else.
REF_CREST_DB = 30.0     # sparse pops over near-silence
REF_FLATNESS = 0.0964   # broadband snaps, not a tuned carrier
REF_CENTROID = 1976.0   # Hz. ⚠⚠ THE ONE THAT ACTUALLY TRACKED THE OWNER'S EAR
# For contrast, the three candidates the owner rejected as "fire in the middle
# of a raging river" measured 16.4 dB and 0.017.


def crest_db(x):
    rms = float(np.sqrt(np.mean(x ** 2)))
    if rms <= 0:
        return float("nan")
    return 20.0 * np.log10(float(np.max(np.abs(x))) / rms)


def flatness(x, nfft=2048):
    """Geometric/arithmetic mean of the power spectrum, averaged over frames.
    ~1 is broadband, ~0 is a pure tone."""
    hop, vals, win = nfft // 2, [], np.hanning(nfft)
    for i in range(0, len(x) - nfft, hop):
        p = np.abs(np.fft.rfft(x[i:i + nfft] * win)) ** 2
        p = p[1:]
        if np.mean(p) < 1e-12:
            continue
        p = np.maximum(p, 1e-20)
        vals.append(np.exp(np.mean(np.log(p))) / np.mean(p))
    return float(np.mean(vals)) if vals else float("nan")


def centroid(x, sr=None, nfft=2048):
    """Spectral centroid in Hz -- the brightness of the sound.

    ⚠⚠ THIS IS THE MEASUREMENT THAT MATTERED AND IT WAS MISSING FOR THREE
    ROUNDS. Two candidates passed crest AND flatness and the owner rejected
    both as "static"; they measured 4222 Hz and 5139 Hz against a real fire's
    1976 Hz. Neither of the other two numbers can see that.
    """
    sr = sr or SR
    hop, vals, win = nfft // 2, [], np.hanning(nfft)
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)[1:]
    for i in range(0, len(x) - nfft, hop):
        p = np.abs(np.fft.rfft(x[i:i + nfft] * win)) ** 2
        p = p[1:]
        if np.mean(p) < 1e-12:
            continue
        vals.append(float(np.sum(freqs * p) / np.sum(p)))
    return float(np.mean(vals)) if vals else float("nan")


def write_wav(path, data, sr):
    import wave
    pcm = np.clip(data, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=24.0)
    ap.add_argument("--seed", type=int, default=20260830)
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--keep-wav", action="store_true")
    ap.add_argument("--crackles", type=float, default=20.0,
                    help="transients per second. ⚠ BELOW ~15 the bed starts to "
                         "dominate the spectrum again and the flatness gate "
                         "will refuse the result -- raise --amp to compensate")
    ap.add_argument("--hiss", type=float, default=0.18,
                    help="continuous bed (300-2800 Hz). This is what blends "
                         "the crackles into a texture instead of leaving them "
                         "as countable pops; see the density note in the header")
    ap.add_argument("--brightness", type=float, default=0.3,
                    help="crackle spectral tilt, 0 dark .. 1 the old +6 dB/oct. "
                         "⚠ THE STATIC KNOB -- raise it and the centroid gate "
                         "will refuse the result")
    ap.add_argument("--roar", type=float, default=0.10,
                    help="continuous bed level. ⚠ THIS IS THE RIVER KNOB -- "
                         "0.62 is what the owner rejected; above ~0.20 the "
                         "bed swamps the transients again")
    ap.add_argument("--amp", type=float, default=0.25,
                    help="crackle amplitude scale")
    ap.add_argument("--name", default="fire_loop")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    wav = out / (args.name + ".wav")
    ogg = out / (args.name + ".ogg")

    data = build(args.seconds, args.seed, args.crackles, args.hiss, args.roar,
                 args.amp, args.brightness)
    write_wav(wav, data, SR)

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
           # ⚠⚠ q:a 3 IS A FLOOR, NOT A PREFERENCE. Vorbis at q1/q2 smears the
           # broadband snaps: measured on a real fire, flatness fell 0.0976 ->
           # 0.0301 at q1 and 0.0311 at q2, i.e. back into the "tuned ping"
           # range this file exists to avoid. q3 keeps 0.0887. Do not lower it
           # to save bytes.
           "-c:a", "libvorbis", "-q:a", "3", "-ar", str(SR), str(ogg)]
    r = subprocess.run(cmd)
    if r.returncode != 0 or not ogg.exists():
        raise SystemExit("FATAL: ffmpeg failed to encode %s" % ogg)

    # Prove the loop joins: the last frame and the first must be close, and
    # there must be no step at the seam larger than the signal's own texture.
    seam = float(np.max(np.abs(data[0] - data[-1])))
    typical = float(np.mean(np.abs(np.diff(data[:, 0]))))
    print("wrote %s  (%.1f s, %d bytes)" % (ogg.name, args.seconds,
                                            ogg.stat().st_size))
    print("peak %.3f   rms %.4f" % (np.max(np.abs(data)),
                                    float(np.sqrt(np.mean(data ** 2)))))
    print("seam step %.5f vs typical sample step %.5f  -> %s"
          % (seam, typical, "SEAMLESS" if seam < typical * 12 else "CHECK"))

    # ⚠ Measure what was ACTUALLY ENCODED, not the float buffer -- the encoder
    # is one of the two things that can destroy the character (see the q:a
    # note above). Decode the .ogg back and judge that.
    dec = out / (args.name + ".decoded.wav")
    r2 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ogg),
                         "-ac", "1", "-ar", str(SR), str(dec)])
    if r2.returncode != 0 or not dec.exists():
        raise SystemExit("FATAL: could not decode %s back to measure it" % ogg)
    import wave as _wave
    with _wave.open(str(dec), "rb") as w:
        mono = (np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                .astype(np.float64) / 32768.0)
    dec.unlink()

    c, f, ct = crest_db(mono), flatness(mono), centroid(mono)
    ok_c = c >= REF_CREST_DB - 3.0          # ABOVE the reference is fine: sparser
    # ⚠ BOTH of these are TWO-SIDED, and they were not before. A one-sided
    # flatness floor passed the 0.1354 candidate the owner called static:
    # too NOISY is a failure exactly as much as too tonal.
    ok_f = REF_FLATNESS * 0.75 <= f <= REF_FLATNESS * 1.45
    ok_t = REF_CENTROID * 0.70 <= ct <= REF_CENTROID * 1.30
    print("crest    %5.1f dB  (reference %.1f)  %s"
          % (c, REF_CREST_DB, "OK" if ok_c else "TOO CONTINUOUS -- the river"))
    print("flatness %6.4f    (reference %.4f)  %s"
          % (f, REF_FLATNESS,
             "OK" if ok_f else
             ("TOO NARROW -- a tuned ping" if f < REF_FLATNESS
              else "TOO NOISY -- static")))
    print("centroid %5.0f Hz  (reference %.0f)  %s"
          % (ct, REF_CENTROID,
             "OK" if ok_t else
             ("TOO DARK -- muffled" if ct < REF_CENTROID
              else "TOO BRIGHT -- this is what 'static' means")))
    if not (ok_c and ok_f and ok_t):
        raise SystemExit(
            "REFUSING TO PRESENT THIS CANDIDATE: it fails the measurement that "
            "the rejected ones failed. Fix it before the owner hears it.")

    if not args.keep_wav:
        wav.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
