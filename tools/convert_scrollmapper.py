"""Convert scrollmapper bible JSON to the app's asset format:
[{"name": ..., "chapters": [[verse, ...], ...]}, ...]
"""
import json
import sys

def convert(src, dst):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    books = []
    for b in data["books"]:
        chapters = []
        for ch in b["chapters"]:
            # Verses are 1-based and should be dense; fill gaps with "".
            vmax = max(v["verse"] for v in ch["verses"])
            verses = [""] * vmax
            for v in ch["verses"]:
                # Scrollmapper marks supplied (italicized) words with [...];
                # keep the words, drop the brackets (matches how the app
                # renders the KJV's {...} supplied words).
                text = v["text"].replace("[", "").replace("]", "")
                verses[v["verse"] - 1] = text.strip()
            chapters.append(verses)
        books.append({"name": b["name"], "chapters": chapters})
    assert len(books) == 66, f"{src}: expected 66 books, got {len(books)}"
    assert books[0]["name"].lower().startswith("gen"), books[0]["name"]
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    print(f"{dst}: 66 books, {total} verses")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
