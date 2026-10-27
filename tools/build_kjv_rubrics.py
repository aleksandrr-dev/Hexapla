"""Build app/src/main/assets/rubrics_kjv.json: the two Sirach prologues.

The KJV 1611 prints two unnumbered prologues before Ecclesiasticus 1:1
("A Prologue made by an uncertain Author" and the grandson's "The Prologue
of the Wisdom of Jesus the Son of Sirach"). Owner decision 2026-09-26: ship
both as front matter above Sir 1:1, in the rubric channel (not scripture).

Source: eBible eng-kjv USFM (public domain),
https://ebible.org/Scriptures/eng-kjv_usfm.zip -> 46-SIReng-kjv.usfm.
The prologue paragraphs sit between `\\c 1` and `\\v 1` as `\\s1` heading +
`\\p` body pairs. eBible leaks one footnote letter into the first body
("called home a again"; 1611: "called home againe"); it is removed by an
exact-match fix that FAILS if the source text changes.

Output is the rubrics_vul.json shape: {"<slot>:1:1": [[0, heading],
[0, body], [0, heading], [0, body]]}. Offsets are 0 (above the verse).

Usage:  python tools/build_kjv_rubrics.py --usfm <46-SIReng-kjv.usfm>          (dry run)
        python tools/build_kjv_rubrics.py --usfm <...> --apply
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSET = REPO / "app" / "src" / "main" / "assets" / "bibles" / "en_kjv.json"
OUT = REPO / "app" / "src" / "main" / "assets" / "rubrics_kjv.json"

FIXES = [("called home a again", "called home again")]
HEADINGS = ["A Prologue made by an uncertain Author",
            "The Prologue of the Wisdom of Jesus the Son of Sirach."]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usfm", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    src = Path(a.usfm).read_text(encoding="utf-8")
    m = re.search(r"\\c 1\s*\n(.*?)\n\\v 1 (.*?)\n", src, re.S)
    if not m:
        sys.exit("FAIL: no \\c 1 .. \\v 1 block")
    front, v1 = m.group(1), m.group(2).strip()

    rows = []
    for line in front.splitlines():
        line = line.strip()
        if line.startswith("\\s1 "):
            rows.append(["h", line[4:].strip()])
        elif line.startswith("\\p "):
            rows.append(["p", line[3:].strip()])
        elif line in ("", "\\p"):
            continue
        else:
            sys.exit(f"FAIL: unexpected front-matter line {line[:60]!r}")
    if [k for k, _ in rows] != ["h", "p", "h", "p"]:
        sys.exit(f"FAIL: expected heading/body x2, got {[k for k, _ in rows]}")
    if [t for k, t in rows if k == "h"] != HEADINGS:
        sys.exit(f"FAIL: headings differ: {[t for k, t in rows if k == 'h']}")
    body = "\n".join(t for _, t in rows)
    if "\\" in body:
        sys.exit("FAIL: USFM marker left in prologue text")
    for bad, good in FIXES:
        if body.count(bad) != 1:
            sys.exit(f"FAIL: fix {bad!r} matched {body.count(bad)}x (want 1)")
        rows = [[k, t.replace(bad, good)] for k, t in rows]

    bible = json.loads(ASSET.read_text(encoding="utf-8"))
    slot = next((i for i, b in enumerate(bible) if b["name"] == "Sirach"), None)
    if slot is None:
        sys.exit("FAIL: no Sirach in en_kjv.json")
    shipped = bible[slot]["chapters"][0][0]
    if shipped.strip() != v1:
        sys.exit(f"FAIL: shipped Sir 1:1 {shipped!r} != USFM v1 {v1!r} (wrong slot?)")

    out = {f"{slot}:1:1": [[0, t] for _, t in rows]}
    text = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    for k, t in rows:
        print(f"  {k} {len(t):5d} chars  {t[:70]}")
    print(f"slot {slot} (Sirach), Sir 1:1 matches USFM v1; {len(text.encode())} bytes")
    if a.apply:
        OUT.write_bytes(text.encode("utf-8"))
        print(f"wrote {OUT}")
    else:
        print("DRY RUN - nothing written (--apply to write)")


if __name__ == "__main__":
    main()
