# -*- coding: utf-8 -*-
"""Normalize YLT's ASCII double-hyphens to em dashes.

Young's Literal Translation uses dashes as a signature punctuation
("In the beginning of God's preparing the heavens and the earth--"),
and the digitization renders them as ASCII "--", which reads as an
artifact on device (owner report, 2026-07-17: "in Psalms 1 and 3 I see
--"). They are authentic Young punctuation — 7,116 across the asset —
normalized here to "—". Only that substitution is performed; every
verse is asserted to differ by nothing else.

Usage: python fix_ylt_dashes.py
"""
import json
import os

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "app", "src", "main", "assets", "bibles", "en_ylt.json")

books = json.load(open(ASSET, encoding="utf-8"))
changed = 0
for bk in books:
    for ch in bk["chapters"]:
        for i, v in enumerate(ch):
            if "--" in v:
                new = v.replace("--", "—")
                assert new.replace("—", "--") == v
                ch[i] = new
                changed += 1
with open(ASSET, "w", encoding="utf-8") as f:
    json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
print(f"{ASSET}: {changed} verses normalized")
