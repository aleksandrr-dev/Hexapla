"""Chinese Union Version (和合本 1919, public domain) -> app assets.

Source: scrollmapper ChiUn (Traditional script, Shen edition). The
Simplified edition is derived from the same public-domain text via
OpenCC t2s character conversion, so both scripts stay textually
identical and license-clean (the Bible societies' 1988 new-punctuation
editions are avoided on purpose).

Cleanup: the source carries tokenization spaces and the Shen-edition
reverence gap (space before 神); all spaces between CJK characters are
collapsed for clean mobile rendering.

Usage: python convert_cuv.py <ChiUn.json>
Writes assets/bibles/zh_cuv_t.json (Traditional) and zh_cuv_s.json
(Simplified). Book names in matching script.
"""
import json
import os
import re
import sys

from opencc import OpenCC

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")

# Traditional-script CUV book names, canonical order.
NAMES_T = [
    "創世記", "出埃及記", "利未記", "民數記", "申命記", "約書亞記",
    "士師記", "路得記", "撒母耳記上", "撒母耳記下", "列王紀上", "列王紀下",
    "歷代志上", "歷代志下", "以斯拉記", "尼希米記", "以斯帖記", "約伯記",
    "詩篇", "箴言", "傳道書", "雅歌", "以賽亞書", "耶利米書", "耶利米哀歌",
    "以西結書", "但以理書", "何西阿書", "約珥書", "阿摩司書", "俄巴底亞書",
    "約拿書", "彌迦書", "那鴻書", "哈巴谷書", "西番雅書", "哈該書",
    "撒迦利亞書", "瑪拉基書",
    "馬太福音", "馬可福音", "路加福音", "約翰福音", "使徒行傳", "羅馬書",
    "哥林多前書", "哥林多後書", "加拉太書", "以弗所書", "腓立比書",
    "歌羅西書", "帖撒羅尼迦前書", "帖撒羅尼迦後書", "提摩太前書",
    "提摩太後書", "提多書", "腓利門書", "希伯來書", "雅各書", "彼得前書",
    "彼得後書", "約翰一書", "約翰二書", "約翰三書", "猶大書", "啟示錄",
]

CJK_SPACE = re.compile(r"(?<=[一-鿿　-〿，。！？；：、「」『』（）])"
                       r"[ 　]+"
                       r"(?=[一-鿿　-〿，。！？；：、「」『』（）])")


def clean(text):
    t = CJK_SPACE.sub("", text.strip())
    return t.strip(" 　")


def main(src):
    data = json.load(open(src, encoding="utf-8"))["books"]
    assert len(data) == 66, len(data)
    t2s = OpenCC("t2s")

    trad = []
    for i, b in enumerate(data):
        chapters = []
        for ch in b["chapters"]:
            vmax = max(v["verse"] for v in ch["verses"])
            verses = [""] * vmax
            for v in ch["verses"]:
                verses[v["verse"] - 1] = clean(v["text"])
            chapters.append(verses)
        trad.append({"name": NAMES_T[i], "chapters": chapters})

    simp = [{"name": t2s.convert(b["name"]),
             "chapters": [[t2s.convert(v) for v in ch] for ch in b["chapters"]]}
            for b in trad]

    for fname, books in (("zh_cuv_t.json", trad), ("zh_cuv_s.json", simp)):
        dst = os.path.join(ASSETS, fname)
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
        total = sum(len(c) for b in books for c in b["chapters"])
        print(f"{fname}: 66 books, {total} verses, "
              f"{os.path.getsize(dst)/1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
