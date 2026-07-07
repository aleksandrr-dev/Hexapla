"""Build audio_index.json v2 — section-based LibriVox KJV audio index.

Output: {"<bookIdx>": [[firstChapter, lastChapter, url], ...], ...}
Only books whose sections cover every chapter contiguously are included.
"""
import json
import re
import time
import urllib.parse
import urllib.request

APP_KJV = r"C:\Projects\Hexapla\app\src\main\assets\bibles\en_kjv.json"
OUT = r"C:\Projects\Hexapla\app\src\main\assets\audio_index.json"

NAMES = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
    "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
    "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah",
    "Malachi","Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians",
    "2 Corinthians","Galatians","Ephesians","Philippians","Colossians",
    "1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon",
    "Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation",
]
ALIASES = {
    "Song of Solomon": ["song of solomon", "song of songs", "canticles"],
    "Psalms": ["psalms", "psalm"],
    "1 Kings": ["1 kings", "1 king", "1kings", "1king"],
    "2 Kings": ["2 kings", "2 king", "2kings", "2king"],
}

def norm(s):
    return re.sub(r"\s+", " ", s.lower().replace("&", "and")).strip()

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hexapla-audio-index"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def search_items(book):
    q = f'collection:librivoxaudio AND title:({book})'
    url = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
           "&fl%5B%5D=identifier&fl%5B%5D=title&rows=25&output=json")
    try:
        docs = fetch_json(url)["response"]["docs"]
    except Exception:
        return []
    return [d["identifier"] for d in docs]

META_CACHE = {}
def metadata(item):
    if item not in META_CACHE:
        try:
            META_CACHE[item] = fetch_json(f"https://archive.org/metadata/{item}")
        except Exception:
            META_CACHE[item] = {}
        time.sleep(0.3)
    return META_CACHE[item]

def is_kjv(meta):
    md = meta.get("metadata", {})
    blob = norm(str(md.get("title", "")) + " " + str(md.get("description", "")))
    return "kjv" in blob or "king james" in blob

RANGE = re.compile(r"(\d{1,3})(?:\s*(?:[-–—]|&|and)\s*(\d{1,3}))?\s*$")

def sections_for(meta, book, expected):
    """Parse (first, last, url) sections for `book` from an item's files."""
    item = meta.get("metadata", {}).get("identifier", "")
    keys = ALIASES.get(book, [norm(book)])
    out = []
    for f in meta.get("files", []):
        name = f.get("name", "")
        if not name.endswith("64kb.mp3"):
            continue
        title = norm(f.get("title", "") or "")
        matched_key = next((k for k in keys if k in title), None)
        if matched_key:
            tail = title.split(matched_key, 1)[1]
        elif "chapter" in title and any(
            k.replace(" ", "") in norm(name).replace("_", "") for k in keys
        ):
            tail = title.split("chapter", 1)[1]
        else:
            continue
        m = RANGE.search(tail.strip())
        if not m:
            # Single-chapter books: a file titled just with the book name.
            if expected == 1 and not tail.strip():
                out.append((1, 1, f"https://archive.org/download/{item}/{name}"))
            continue
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if 1 <= a <= b <= expected:
            out.append((a, b, f"https://archive.org/download/{item}/{name}"))
    return out

def covers(sections, expected):
    """True if sections tile 1..expected contiguously without overlap."""
    if not sections:
        return False
    s = sorted(sections)
    if s[0][0] != 1 or s[-1][1] != expected:
        return False
    for (a1, b1, _), (a2, b2, _) in zip(s, s[1:]):
        if a2 != b1 + 1:
            return False
    return True

def main():
    kjv = json.load(open(APP_KJV, encoding="utf-8"))
    expected = {i: len(kjv[i]["chapters"]) for i in range(66)}
    index = {}
    for i, book in enumerate(NAMES):
        want = expected[i]
        found = None
        for item in search_items(book):
            meta = metadata(item)
            if not meta or not is_kjv(meta):
                continue
            secs = sections_for(meta, book, want)
            if covers(secs, want):
                found = sorted(secs)
                break
        if found:
            index[str(i)] = [[a, b, u] for a, b, u in found]
            print(f"OK  {book}: {len(found)} sections")
        else:
            print(f"--  {book}: no complete item")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"))
    print(f"\nindexed: {len(index)}/66 books")

if __name__ == "__main__":
    main()
