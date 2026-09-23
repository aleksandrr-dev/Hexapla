# -*- coding: utf-8 -*-
"""Verify every locale carries the same string keys as the English base, with
identical format placeholders.

    python tools/check_strings.py [key ...]

With no arguments it checks EVERY key in values/strings.xml. With arguments it
checks only those keys (used when a batch of new strings is being localized).

The two failure modes that actually reach users are a mistranslated placeholder
(`%1$d` dropped or renumbered -> the app formats wrong or crashes) and invalid
XML (build failure), so both are checked mechanically rather than by eye.
`app_name` is exempt: it deliberately falls back to "Hexapla" everywhere except
Russian.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.abspath(__file__)) + "/.."
BASE = REPO + "/app/src/main/res/values/strings.xml"
EXEMPT = {"app_name"}
PH = re.compile(r"%\d\$[sd]|%[sd]")


def strings(path):
    src = open(path, encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in
            re.finditer(r'<string name="([^"]+)"[^>]*>(.*?)</string>', src, re.S)}


def main():
    only = set(sys.argv[1:])
    base = strings(BASE)
    keys = [k for k in base if k not in EXEMPT and (not only or k in only)]
    problems, missing, ok = [], [], []
    for d in sorted(glob.glob(REPO + "/app/src/main/res/values-*/")):
        loc = os.path.basename(os.path.dirname(d))
        if loc == "values-night":
            continue
        p = d + "strings.xml"
        if not os.path.exists(p):
            continue
        try:
            ET.parse(p)
        except Exception as e:
            problems.append("%s: XML PARSE FAILURE — %s" % (loc, e))
            continue
        loc_s = strings(p)
        miss = [k for k in keys if k not in loc_s]
        if miss:
            missing.append("%s: missing %d (%s)" % (loc, len(miss), ", ".join(miss[:4])))
        for k in keys:
            if k not in loc_s:
                continue
            a, b = sorted(PH.findall(base[k])), sorted(PH.findall(loc_s[k]))
            if a != b:
                problems.append("%s / %s: placeholders %s, English has %s"
                                % (loc, k, b, a))
        if not miss:
            ok.append(loc)
    print("checked %d keys across %d locales" % (len(keys), len(ok) + len(missing)))
    print("complete locales : %d" % len(ok))
    if missing:
        print("INCOMPLETE:")
        for m in missing:
            print("   " + m)
    print("placeholder / XML problems: %s" % ("NONE" if not problems else ""))
    for x in problems:
        print("   " + x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
