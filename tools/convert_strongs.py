"""Convert kaiserlik/kjv (KJV with Strong's tags) + lexicon into app assets.

Output 1: en_kjv_strongs.json — app book format, verse text with [H1234]/[G1234] tags.
Output 2: lexicon.json — {"H1": {"w": word, "t": translit, "p": part_of_speech, "d": def}, ...}
"""
import html
import json
import os
import re
import sys

ORDER = [
    "Gen","Exo","Lev","Num","Deu","Jos","Jdg","Rth","1Sa","2Sa","1Ki","2Ki",
    "1Ch","2Ch","Ezr","Neh","Est","Job","Psa","Pro","Ecc","Sng","Isa","Jer",
    "Lam","Eze","Dan","Hos","Joe","Amo","Oba","Jon","Mic","Nah","Hab","Zep",
    "Hag","Zec","Mal",
    "Mat","Mar","Luk","Jhn","Act","Rom","1Co","2Co","Gal","Eph","Phl","Col",
    "1Th","2Th","1Ti","2Ti","Tit","Phm","Heb","Jas","1Pe","2Pe","1Jo","2Jo",
    "3Jo","Jde","Rev",
]

TAG = re.compile(r"\[([HG]\d+)\]")

def clean(text):
    text = html.unescape(text)
    # <em> marks KJV supplied words: keep the words, drop the markup.
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
    # Drop any non-Strong's bracketed leftovers, keep the tags.
    text = re.sub(r"\[(?![HG]\d+\])[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip()

VERSE_RE = re.compile(
    r'"([A-Za-z0-9]+)\|(\d+)\|(\d+)":\s*\{\s*"en":\s*"(.*?)",\s*"(?:bg|ch|sp)"',
    re.DOTALL,
)

def extract_verses(path, abbr):
    """Pull (chapter, verse) -> en text straight from the raw file. The non-
    English fields in some source files contain raw quotes that break JSON,
    so we never parse the whole document."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    name = raw.split('"', 2)[1]
    verses = {}
    for k, c, v, text in VERSE_RE.findall(raw):
        if k != abbr:  # Phm.json has a stray copy of Philippians appended
            continue
        if chr(92) in text:  # decode JSON escapes only when present
            try:
                text = json.loads('"' + text + '"')
            except json.JSONDecodeError:
                pass
        verses[(int(c), int(v))] = text
    return name, verses

def convert_text(src_dir, dst):
    books = []
    total = 0
    for abbr in ORDER:
        name, flat = extract_verses(os.path.join(src_dir, abbr + ".json"), abbr)
        assert flat, f"{abbr}: no verses extracted"
        chapters = []
        for c in range(1, max(k[0] for k in flat) + 1):
            vmax = max((k[1] for k in flat if k[0] == c), default=0)
            chapters.append([clean(flat.get((c, v), "")) for v in range(1, vmax + 1)])
        total += sum(len(ch) for ch in chapters)
        books.append({"name": name, "chapters": chapters})
    # The source uses a slightly different versification in a handful of
    # chapters; a mid-chapter split would shift every following verse against
    # the app's KJV. For those chapters, fall back to untagged KJV text.
    kjv_path = os.path.join(os.path.dirname(dst), "en_kjv.json")
    with open(kjv_path, encoding="utf-8") as f:
        kjv = json.load(f)
    fallbacks = 0
    for i in range(66):
        for c in range(len(kjv[i]["chapters"])):
            if len(books[i]["chapters"][c]) != len(kjv[i]["chapters"][c]):
                books[i]["chapters"][c] = kjv[i]["chapters"][c]
                fallbacks += 1
    print(f"chapters reverted to plain KJV (versification mismatch): {fallbacks}")
    assert len(books) == 66
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{dst}: 66 books, {total} verses, {os.path.getsize(dst)} bytes")

def convert_lexicon(src, dst):
    with open(src, encoding="utf-8") as f:
        lex = json.load(f)
    out = {}
    for sid, e in lex.items():
        word = e.get("Hb_word") or e.get("Gk_word") or ""
        out[sid] = {
            "w": word,
            "t": e.get("transliteration", ""),
            "p": e.get("part_of_speech", ""),
            "d": clean(e.get("strongs_def", "")),
        }
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{dst}: {len(out)} entries, {os.path.getsize(dst)} bytes")

if __name__ == "__main__":
    src_dir, assets = sys.argv[1], sys.argv[2]
    convert_text(src_dir, os.path.join(assets, "bibles", "en_kjv_strongs.json"))
    convert_lexicon(os.path.join(src_dir, "lexicon.json"), os.path.join(assets, "strongs_lexicon.json"))
