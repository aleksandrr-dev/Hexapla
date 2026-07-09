"""Webster's American Dictionary of the English Language (1828) ->
compact app asset.

Source: the mshaffer/1828.mshaffer.com volunteer digitization, via the
DataWar/1828-dictionary repo (v2015 MySQL dump; the 1828 text itself is
public domain). Parses the INSERT tuples, strips the HTML markup, and
writes assets/webster1828.json as {"HEADWORD": "definition", ...} with
senses separated by newlines.

Usage: python convert_webster1828.py <dictionary_webster1828.sql> <out.json>
"""
import html
import json
import re
import sys


def parse_tuples(s):
    """Parse (a,'b',...) value tuples honoring MySQL quoting."""
    rows = []
    i, n = 0, len(s)
    while True:
        i = s.find("(", i)
        if i < 0:
            break
        row, cur, i = [], [], i + 1
        in_str = False
        while i < n:
            ch = s[i]
            if in_str:
                if ch == "\\":
                    cur.append(s[i + 1])
                    i += 2
                    continue
                if ch == "'":
                    if i + 1 < n and s[i + 1] == "'":
                        cur.append("'")
                        i += 2
                        continue
                    in_str = False
                    i += 1
                    continue
                cur.append(ch)
                i += 1
                continue
            if ch == "'":
                in_str = True
                i += 1
                continue
            if ch == ",":
                row.append("".join(cur))
                cur = []
                i += 1
                continue
            if ch == ")":
                row.append("".join(cur))
                rows.append(row)
                i += 1
                break
            cur.append(ch)
            i += 1
    return rows


TAG = re.compile(r"<p>|</p>", re.I)
OTHER_TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"[ \t]+")


def clean(html_text):
    t = TAG.sub("\n", html_text)
    t = OTHER_TAG.sub("", t)
    t = html.unescape(t)
    lines = [WS.sub(" ", ln).strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def main(src, dst):
    text = open(src, encoding="utf-8", errors="replace").read()
    rows = parse_tuples(text[text.find("VALUES"):])
    out = {}
    for r in rows:
        if len(r) != 7:
            continue
        word = r[1].strip().upper()
        if not word:
            continue
        definition = clean(r[3])
        if not definition:
            continue
        # A handful of words have split entries; append as extra senses.
        if word in out:
            out[word] += "\n" + definition
        else:
            out[word] = definition
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(v) for v in out.values())
    print(f"{dst}: {len(out)} headwords, {total/1e6:.1f} MB of text")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
