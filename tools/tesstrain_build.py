# -*- coding: utf-8 -*-
"""Rebuild and retrain `isfrak` — the Þorláksbiblía OCR screener model.

    python tools/tesstrain_build.py                 # full rebuild + train + eval
    python tools/tesstrain_build.py --iterations 6000
    python tools/tesstrain_build.py --eval-only

Run this whenever a book completes, or whenever a completed book's text is
CORRECTED — the second case matters more. Galatians 1-2 was retrofitted on
2026-08-11 with ~49 `ꝑ` sites changed, which meant the model had been trained
on labels we now know were wrong. Stale ground truth is worse than less of it:
it teaches the model the errors we just spent an agent removing.

⚠ The model this produces is a SCREENER (page-level fabrication detection) and
nothing else. See tools/local_screen.py for what it can and cannot see, and
why lowering its error rate does NOT make it a verse-level checker: its ground
truth is our own transcription, so it is a compression of us, never an
independent witness.

## ⚠ THE MODEL HAS PLATEAUED — MORE ITERATIONS DO NOT HELP. MORE DATA MIGHT.

Measured 2026-08-11, all three scored on the SAME 60 held-out lines (re-scoring
the old model rather than quoting its old number, because the split changed):

    Fraktur (stock)                          mean CER 0.303
    isfrak_v1  3000 iters, pre-retrofit GT   mean CER 0.137
    isfrak     6000 iters, corrected GT      mean CER 0.135

Doubling the iterations AND removing ~49 known-wrong `ꝑ` labels bought
**0.002** — noise on 60 lines. Meanwhile training BCER fell 13.97 -> 10.89.
That gap is the signature of **overfitting**: with 481 lines the model is
memorising the training set, not learning the fount.

▶ Do NOT raise --iterations again hoping for a better model. The next real
gain comes from more BOOKS (add rows to BOOKS below and rerun), not more
epochs. Re-measure when the corpus roughly doubles.
▶ The retrain was still worth running: it removed labels we had proven wrong,
so the model is no longer being taught the `ꝑ` error the campaign just fixed.
"No measurable gain" and "no point doing it" are different statements.

⚠ Screener performance is unchanged and remains fine for its job: Philemon vs
its own page 0.813, wrong-book control 0.068. The detector was never the
bottleneck.

## ⚠ BOX FILES MUST NOT CARRY CRLF

`Path.write_text("...\n")` on Windows emits `\r\n`, and batch `.lstmf`
generation then fails with `Deserialize header failed` on a scattered subset —
which surfaces much later as `Load of images failed!!` and no checkpoint, with
nothing in stdout explaining why (lstmtraining reports it on stderr). If a
training run produces no checkpoint, regenerate the `.lstmf` files first and
check the box line endings before suspecting anything else.

## Pipeline

    prep_chunk.py      pages -> line crops (must already have been run)
    tesstrain_prep.py  verse text -> per-line .gt.txt via OCR-anchored alignment
    (here)             .box -> .lstmf -> lstmtraining -> .traineddata -> CER eval

Requires Tesseract with training tools (UB-Mannheim build) and
`Hexapla-releases/tessdata/` holding Fraktur.traineddata + radical-stroke.txt.
"""
import argparse
import difflib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BIN = Path(r"C:/Program Files/Tesseract-OCR")
TD = Path(r"C:/Projects/Hexapla-releases/tessdata")
PREP = Path(r"C:/Projects/Hexapla-releases/research/_prep")
GT = PREP / "gt"
TOOLS = Path(__file__).parent

# book prep-dir, chunk report, volume, page range. Add a row when a book lands.
BOOKS = [
    ("philemon",  "thorlaks_philemon.md",  3, "202"),
    ("galatians", "thorlaks_galatians.md", 3, "173-177"),
    ("ephesians", "thorlaks_ephesians.md", 3, "177-181"),
    ("james",     "thorlaks_james.md",     3, "223-227"),
]


def run(cmd, **kw):
    env = dict(os.environ, TESSDATA_PREFIX=str(TD))
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, **kw)


def regenerate_gt():
    if GT.exists():
        shutil.rmtree(GT)
    GT.mkdir(parents=True)
    for book, chunk, vol, pages in BOOKS:
        if not (PREP / book).exists():
            print(f"  prep missing for {book}, running prep_chunk")
            run([sys.executable, str(TOOLS / "prep_chunk.py"), "--vol", str(vol),
                 "--pages", pages, "--out", book])
        r = run([sys.executable, str(TOOLS / "tesstrain_prep.py"),
                 "--book", book, "--chunk", chunk, "--vol", str(vol),
                 "--pages", pages, "--out", "gt"])
        line = [l for l in r.stdout.splitlines() if "coverage" in l]
        print("  " + (line[0].strip() if line else r.stderr.strip()[:120]))


def make_boxes():
    n = 0
    for gt in GT.glob("*.gt.txt"):
        png = gt.with_name(gt.name[:-7] + ".png")
        if not png.exists():
            continue
        text = gt.read_text(encoding="utf-8").strip()
        if not text:
            continue
        w, h = Image.open(png).size
        gt.with_name(gt.name[:-7] + ".box").write_text(
            f"WordStr 0 0 {w} {h} 0 #{text}\n\t 0 0 {w} {h} 0\n", encoding="utf-8")
        n += 1
    return n


def make_lstmf():
    n = 0
    for png in sorted(GT.glob("*.png")):
        base = png.with_suffix("")
        if not base.with_suffix(".box").exists():
            continue
        r = run([str(BIN / "tesseract.exe"), str(png), str(base),
                 "--psm", "7", "-l", "Fraktur", "lstm.train"])
        if base.with_suffix(".lstmf").exists():
            n += 1
        elif n == 0:
            print("   ", r.stderr.strip()[:160])
    return n


def split_lists(every=8):
    files = sorted(str(p) for p in GT.glob("*.lstmf"))
    (TD / "train.txt").write_text(
        "\n".join(f for i, f in enumerate(files) if i % every), encoding="utf-8")
    (TD / "eval.txt").write_text(
        "\n".join(f for i, f in enumerate(files) if not i % every), encoding="utf-8")
    return len(files)


def build_unicharset():
    allgt = TD / "all_gt.txt"
    allgt.write_text(
        "\n".join(p.read_text(encoding="utf-8").strip()
                  for p in GT.glob("*.gt.txt")), encoding="utf-8")
    run([str(BIN / "unicharset_extractor.exe"), "--output_unicharset",
         str(TD / "our.unicharset"), "--norm_mode", "2", str(allgt)])
    if (TD / "isfrak").exists():
        shutil.rmtree(TD / "isfrak")
    run([str(BIN / "combine_lang_model.exe"), "--input_unicharset",
         str(TD / "our.unicharset"), "--script_dir", str(TD),
         "--output_dir", str(TD), "--lang", "isfrak"])
    return (TD / "isfrak" / "isfrak.traineddata").exists()


def cer(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    d = sum(max(i2 - i1, j2 - j1)
            for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return d / max(len(a), 1)


def evaluate(langs):
    files = [l.strip() for l in (TD / "eval.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    pngs = [f.replace(".lstmf", ".png") for f in files]
    print(f"\nheld-out lines: {len(pngs)}")
    for lang in langs:
        if not (TD / f"{lang}.traineddata").exists():
            print(f"  {lang:<12} (not present, skipped)")
            continue
        vals = []
        for p in pngs:
            gt = Path(p.replace(".png", ".gt.txt")).read_text(encoding="utf-8").strip()
            if not gt:
                continue
            out = run([str(BIN / "tesseract.exe"), p, "stdout",
                       "-l", lang, "--psm", "7"]).stdout.strip()
            vals.append(cer(gt, out))
        vals.sort()
        print(f"  {lang:<12} mean CER={sum(vals)/len(vals):.3f}  "
              f"median={vals[len(vals)//2]:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=6000)
    ap.add_argument("--eval-only", action="store_true")
    a = ap.parse_args()

    if a.eval_only:
        evaluate(["Fraktur", "isfrak_v1", "isfrak"])
        return

    print("1. regenerating ground truth from chunk reports")
    regenerate_gt()
    print(f"2. box files: {make_boxes()}")
    print(f"3. lstmf files: {make_lstmf()}")
    print(f"4. train/eval split over {split_lists()} lines")
    print(f"5. unicharset + starter traineddata: {build_unicharset()}")

    # keep the previous model for comparison rather than overwriting it
    cur = TD / "isfrak.traineddata"
    if cur.exists() and not (TD / "isfrak_v1.traineddata").exists():
        shutil.copyfile(cur, TD / "isfrak_v1.traineddata")

    out = TD / "out"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    run([str(BIN / "combine_tessdata.exe"), "-e",
         str(TD / "Fraktur.traineddata"), str(TD / "Fraktur.lstm")])
    print(f"6. training {a.iterations} iterations …")
    r = run([str(BIN / "lstmtraining.exe"),
             "--model_output", str(out / "isfrak"),
             "--continue_from", str(TD / "Fraktur.lstm"),
             "--old_traineddata", str(TD / "Fraktur.traineddata"),
             "--traineddata", str(TD / "isfrak" / "isfrak.traineddata"),
             "--train_listfile", str(TD / "train.txt"),
             "--eval_listfile", str(TD / "eval.txt"),
             "--max_iterations", str(a.iterations)])
    for line in r.stdout.splitlines()[-3:]:
        print("   " + line.strip())

    best = sorted(out.glob("isfrak_*.checkpoint"),
                  key=lambda p: float(p.stem.split("_")[1]))
    if not best:
        sys.exit("no checkpoint produced — see training output above")
    print(f"7. finalising from {best[0].name}")
    run([str(BIN / "lstmtraining.exe"), "--stop_training",
         "--continue_from", str(best[0]),
         "--traineddata", str(TD / "isfrak" / "isfrak.traineddata"),
         "--model_output", str(TD / "isfrak.traineddata")])
    evaluate(["Fraktur", "isfrak_v1", "isfrak"])


if __name__ == "__main__":
    main()
