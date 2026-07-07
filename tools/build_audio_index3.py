"""Audio index v3: one bulk archive.org search + known KJV items, validated
per book. Output identical to v2."""
import json
import re
import time
import urllib.parse
import urllib.request

from build_audio_index2 import (
    APP_KJV, OUT, NAMES, ALIASES, norm, fetch_json, metadata, is_kjv,
    sections_for, covers,
)

KNOWN = [
    "bible_kjv_01_02_03_0908_librivox",   # Genesis, Exodus, Leviticus
    "bible_kjv_nt_03_luke_0812_librivox",
    "acts_kjv_v2_1401_librivox",
    "bible_4epistles_kjv_1104_librivox",  # Gal, Eph, Php, Col
    "bible_epistlesjohn_rt_librivox",     # 1-3 John
    "bible_kjv_17_esther_dr_1502_librivox",
    "job_kjv_1012_librivox",
    "psalms_kjv_1202_librivox",
    "1corinthians_kjv_1103_librivox",
    "hebrews_kjv_1111_librivox",
    "isaiah_kjv_1107_librivox",
    "jeremiah_kjv_1201_librivox",
    "daniel_kjv_1112_librivox",
    "ezra_kjv_sw_librivox",
    "nehemiah_kjv_1110_librivox",
    "numbers_kjv_1108_librivox",
    "songofsolomon_kjv_1009_librivox",
    "joel_kjv_ss_librivox",
    "mark_kjv_sw_librivox",
    "matthew_kjv_mp_librivox",
    "bible_ruth_tg_librivox",
    "jude_kjv",
    "bible_kjvnt_27_revelation_1401_librivox",
]

def bulk_docs():
    docs = []
    for q in ['collection:librivoxaudio AND (title:bible OR subject:bible)',
              'collection:librivoxaudio AND subject:(old testament)',
              'collection:librivoxaudio AND subject:(new testament)']:
        url = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
               "&fl%5B%5D=identifier&fl%5B%5D=title&rows=800&output=json")
        try:
            docs += fetch_json(url)["response"]["docs"]
        except Exception as e:
            print("search failed:", e)
        time.sleep(1)
    seen, out = set(), []
    for d in docs:
        if d["identifier"] not in seen:
            seen.add(d["identifier"])
            out.append(d)
    return out

def main():
    kjv = json.load(open(APP_KJV, encoding="utf-8"))
    expected = {i: len(kjv[i]["chapters"]) for i in range(66)}
    docs = bulk_docs()
    print("bulk candidates:", len(docs))
    index = {}
    for i, book in enumerate(NAMES):
        want = expected[i]
        keys = ALIASES.get(book, [norm(book)])
        cands = list(KNOWN)
        for d in docs:
            t = norm(d.get("title", ""))
            if any(k in t for k in keys):
                cands.append(d["identifier"])
        found = None
        for item in cands:
            meta = metadata(item)
            if not meta or not is_kjv(meta):
                continue
            secs = sections_for(meta, book, want)
            if covers(secs, want):
                found = sorted(secs)
                break
        if found:
            index[str(i)] = [[a, b, u] for a, b, u in found]
            print(f"OK  {book}: {len(found)} sections", flush=True)
        else:
            print(f"--  {book}", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"))
    print(f"\nindexed: {len(index)}/66 books")

if __name__ == "__main__":
    main()
