"""Build the Tesseract TSV word-box cache for strips that lack one.

Mirrors tools/kxii_locate.py exactly: same binary, same tessdata, same
-l Fraktur --psm 4 tsv invocation, same flat cache keyed on strip basename.

(!) MUST be run in the BACKGROUND. Running tesseract inline over many strips
    takes minutes and times out the session - a documented landmine.
(!) Skips strips that already have a cache entry, so re-running is free and a
    killed run resumes.
(!) A strip whose OCR FAILS is reported and left with NO cache file, never an
    empty one - an empty .tsv would read as "cached, no words" forever.
(!) Safe to run CONCURRENTLY with another instance: targets are enumerated at
    startup, already-cached strips are skipped, and the temp file is PID-keyed.
    But two instances will still OCR the same pending strip twice and waste the
    CPU, so prefer scoping a catch-up run to the pages that actually need it.
"""
import os, subprocess, sys, time

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Projects\Hexapla-releases\tessdata"
CACHE = r"C:\Projects\Hexapla-releases\research\_ocr_kxii\tsv"
BASE = r"C:\Projects\Hexapla-releases\research\_strips_kxii"

targets = []
for book in sys.argv[1:]:
    d = os.path.join(BASE, book)
    for f in sorted(os.listdir(d)):
        if f.endswith(".png"):
            targets.append((book, os.path.join(d, f), os.path.splitext(f)[0]))

os.makedirs(CACHE, exist_ok=True)
todo = [t for t in targets if not os.path.exists(os.path.join(CACHE, t[2] + ".tsv"))]
print("targets %d, already cached %d, to build %d"
      % (len(targets), len(targets) - len(todo), len(todo)), flush=True)

env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
ok = fail = 0
failures = []
t0 = time.time()
for i, (book, path, stem) in enumerate(todo, 1):
    try:
        out = subprocess.run([TESS, path, "stdout", "-l", "Fraktur", "--psm", "4", "tsv"],
                             capture_output=True, env=env, timeout=300)
        if out.returncode != 0 or not out.stdout.strip():
            raise RuntimeError("rc=%s stderr=%s" % (out.returncode, out.stderr.decode("utf-8", "replace")[-200:]))
        # Write to a temp name and rename, so a killed run can never leave a
        # truncated .tsv that would then be treated as a valid cache hit.
        # (!) The .part name carries the PID. Two instances CAN legitimately run
        # at once (a bulk background sweep plus a scoped catch-up for pages cut
        # after that sweep enumerated its targets), and a shared .part name
        # would let two writers interleave and then rename a CORRUPT file into
        # the cache, where it would read as a valid hit forever.
        tmp = os.path.join(CACHE, "%s.tsv.part.%d" % (stem, os.getpid()))
        with open(tmp, "wb") as fh:
            fh.write(out.stdout)
        os.replace(tmp, os.path.join(CACHE, stem + ".tsv"))
        ok += 1
    except Exception as e:
        fail += 1
        failures.append((stem, str(e)[:160]))
        print("  FAIL %s: %s" % (stem, str(e)[:160]), flush=True)
    if i % 25 == 0:
        el = time.time() - t0
        print("  %d/%d  ok=%d fail=%d  %.1fs elapsed  %.2fs/strip"
              % (i, len(todo), ok, fail, el, el / i), flush=True)

print("DONE ok=%d fail=%d of %d in %.1fs" % (ok, fail, len(todo), time.time() - t0), flush=True)
if failures:
    print("FAILURES (no cache file written for these):", flush=True)
    for s, e in failures:
        print("  %s  %s" % (s, e), flush=True)
# Non-zero exit on any failure so a wrapper cannot print success over it.
sys.exit(1 if failures else 0)
