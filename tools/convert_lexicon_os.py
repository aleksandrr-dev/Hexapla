"""Build strongs_lexicon.json from the Open Scriptures dictionaries (CC-BY-SA).
Format: {"H1": {"w": lemma, "t": translit, "p": "", "d": definition}, ...}
"""
import json
import re
import sys

def load_js(path):
    raw = open(path, encoding="utf-8").read()
    start = raw.index("{", raw.index("="))
    end = raw.rindex("}")
    return json.loads(raw[start:end + 1])

def build(entries, out):
    for sid, e in entries.items():
        d = e.get("strongs_def", "").strip().rstrip(";,")
        kjv = e.get("kjv_def", "").strip().rstrip(";,.")
        if kjv:
            d = f"{d}. KJV: {kjv}." if d else f"KJV: {kjv}."
        out[sid] = {
            "w": e.get("lemma", ""),
            "t": e.get("xlit") or e.get("translit", ""),
            "p": "",
            "d": re.sub(r"\s+", " ", d),
        }

if __name__ == "__main__":
    heb, grk, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    out = {}
    build(load_js(heb), out)
    build(load_js(grk), out)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{dst}: {len(out)} entries")
