"""Russian Strong's glosses -> assets/strongs_lexicon_ru.json

Source: the BibleQuote module `modules/Strong.zip` from
github.com/BibleQuote/BibleQuote-Modules, staged at
C:/Projects/Hexapla-releases/strongs_ru/Strong.zip (611,637 bytes).

Two traps this script exists to avoid repeating (see
research/russian_strongs_status.md):

  * the member path is `Strong/greek.htm` and `Strong/hebrew.htm` inside the
    zip -- NOT the repo root, as an older note claimed;
  * the .htm files are UTF-16 LE with a BOM. cp1251 and utf-8 raise, but
    koi8-r and cp866 decode them WITHOUT ERROR into convincing mojibake. This
    script decodes with 'utf-16' and asserts the BOM, so a wrong codec can
    never slip through silently.

Output shape mirrors assets/strongs_lexicon.json exactly -- same H<n>/G<n>
keys, same {"w","t","p","d"} fields -- so the app can swap lexicons by locale
with a per-id English fallback. Fields the Russian source does not carry
("t" transliteration, "p" part of speech) are emitted empty; the app keeps
the English ones for those.

The Dvoretsky gate (this must NOT be Dvoretsky's 1958 dictionary, (c) until
2049) is re-run here on every build rather than trusted from the July
research, on both lines of evidence: keyword absence AND the gloss-length
distribution. A build that trips it aborts.
"""

import argparse
import collections
import html
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

ZIP = Path("C:/Projects/Hexapla-releases/strongs_ru/Strong.zip")
OUT = Path("app/src/main/assets/strongs_lexicon_ru.json")
ENGLISH = Path("app/src/main/assets/strongs_lexicon.json")

MEMBERS = {"G": "Strong/greek.htm", "H": "Strong/hebrew.htm"}
# What the vetted artifact holds. A change here means a different file.
EXPECTED_ZIP_BYTES = 611_637
EXPECTED_ENTRIES = {"G": 5520, "H": 8674}

ENTRY_RE = re.compile(
    r"<h4>(\d+)</h4>\s*<b>(.*?)</b>\s*<p>(.*?)</p>", re.DOTALL
)

# --- Dvoretsky gate ---------------------------------------------------------
# His name in Russian and Latin, his co-editors, the dictionary's own title,
# and the classical-citation markers that pepper every page of it.
DVORETSKY_MARKERS = [
    "Дворецк", "Dvoretsky", "древнегреческо-русский",
    "Журомск", "Цыганков",
    "Hom.", "Plat.", "Aesch.", "Thuc.", "Xen.", "Arst.",
]
# Measured on the vetted artifact: Greek median 83, Hebrew median 59.
# Dvoretsky's entries are dense classical essays running to thousands of
# characters. A median anywhere near his is structurally incompatible.
MAX_PLAUSIBLE_MEDIAN = 200


def decode(raw: bytes, name: str) -> str:
    if not raw.startswith(b"\xff\xfe"):
        sys.exit(f"{name}: expected a UTF-16 LE BOM, got {raw[:4]!r}. "
                 "Do NOT guess a cyrillic codec -- koi8-r and cp866 will "
                 "'succeed' and give you mojibake.")
    return raw.decode("utf-16")


def clean(fragment: str) -> str:
    """<p> body -> plain text. <br> is the only inline tag the source uses."""
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    text = html.unescape(text)
    # Directional marks travel with the Hebrew lemmas and only confuse layout.
    text = text.replace("\u200e", "").replace("\u200f", "")
    lines = [re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


def parse(text: str, prefix: str) -> dict:
    out = {}
    for num, bold, body in ENTRY_RE.findall(text):
        sid = int(num)
        bold = clean(bold)
        # "<b>25, ἀγαπάω</b>" -- the leading number restates the id, so it is
        # a free integrity check rather than something to parse around.
        m = re.match(r"^(\d+)\s*,\s*(.*)$", bold, re.DOTALL)
        if not m:
            sys.exit(f"{prefix}{sid}: <b> does not start with its own number: {bold!r}")
        if int(m.group(1)) != sid:
            sys.exit(f"{prefix}{sid}: <b> claims number {m.group(1)}")
        key = f"{prefix}{sid}"
        if key in out:
            sys.exit(f"{key}: duplicate entry")
        out[key] = {"w": m.group(2).strip(), "t": "", "p": "", "d": clean(body)}
    return out


def dvoretsky_gate(raw_text: dict, entries: dict) -> None:
    """Abort unless BOTH independent lines of evidence clear the source."""
    hits = {}
    for prefix, text in raw_text.items():
        for marker in DVORETSKY_MARKERS:
            n = text.count(marker)
            if n:
                hits[f"{prefix}:{marker}"] = n
    if hits:
        sys.exit("DVORETSKY GATE FAILED -- markers present: "
                 + json.dumps(hits, ensure_ascii=False)
                 + "\nThis may be a Dvoretsky-merged build. (c) until 2049; "
                   "do not ship. See research/russian_strongs_status.md.")

    for prefix in ("G", "H"):
        lengths = [len(v["d"]) for k, v in entries.items() if k[0] == prefix]
        med = statistics.median(lengths)
        p95 = statistics.quantiles(lengths, n=20)[-1]
        print(f"  {prefix}: gloss length median {med:.0f}, p95 {p95:.0f}, "
              f"max {max(lengths)}")
        if med > MAX_PLAUSIBLE_MEDIAN:
            sys.exit(f"DVORETSKY GATE FAILED -- {prefix} median gloss is "
                     f"{med:.0f} chars, far above the {MAX_PLAUSIBLE_MEDIAN} "
                     "ceiling. Keyword absence alone is not enough; a long-gloss "
                     "distribution is what a merged classical dictionary looks "
                     "like.")
    print("  Dvoretsky gate PASSES on both keyword absence and gloss length.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=ZIP)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    size = args.zip.stat().st_size
    print(f"{args.zip} -- {size:,} bytes")
    if size != EXPECTED_ZIP_BYTES:
        sys.exit(f"expected {EXPECTED_ZIP_BYTES:,} bytes (the vetted artifact); "
                 "a different file has NOT been through the licensing review.")

    zf = zipfile.ZipFile(args.zip)
    raw_text, entries = {}, {}
    for prefix, member in MEMBERS.items():
        text = decode(zf.read(member), member)
        raw_text[prefix] = text
        got = parse(text, prefix)
        want = EXPECTED_ENTRIES[prefix]
        print(f"{member}: {len(got):,} entries (expected {want:,})")
        if len(got) != want:
            sys.exit(f"{member}: entry count changed -- re-vet before shipping.")
        entries.update(got)

    print("Dvoretsky gate:")
    dvoretsky_gate(raw_text, entries)

    empty = [k for k, v in entries.items() if not v["d"]]
    if empty:
        sys.exit(f"{len(empty)} entries have an empty gloss, e.g. {empty[:10]}")

    # Key compatibility with the English lexicon is the whole point of the
    # per-locale swap: an id the app can look up in one and not the other
    # silently degrades to no definition at all.
    if ENGLISH.exists():
        en = json.loads(ENGLISH.read_text(encoding="utf-8"))
        shared = set(en) & set(entries)
        only_ru = sorted(set(entries) - set(en))
        only_en = sorted(set(en) - set(entries))
        print(f"vs English lexicon: {len(shared):,} shared ids, "
              f"{len(only_ru):,} Russian-only, {len(only_en):,} English-only "
              f"(these fall back to English)")
        if len(shared) < 0.98 * len(en):
            sys.exit("key overlap below 98% -- the id formats have diverged.")
        if only_ru[:5]:
            print(f"  Russian-only sample: {only_ru[:5]}")
        if only_en[:5]:
            print(f"  English-only sample: {only_en[:5]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {args.out} -- {len(entries):,} entries, "
          f"{args.out.stat().st_size:,} bytes")
    if ENGLISH.exists():
        print(f"  (English lexicon for comparison: "
              f"{ENGLISH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
