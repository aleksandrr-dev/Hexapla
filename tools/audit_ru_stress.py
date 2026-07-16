# -*- coding: utf-8 -*-
"""Audit tools/ru_stress.py: does it only ADD STRESS, or does it CHANGE WORDS?

THE INVARIANT: a stress table must be invisible once the combining acute
(U+0301) is stripped. strip_acute(apply_stress(v)) == v, for every verse.
Anything surviving that strip is a real edit to the Bible text.

Run this before ever enabling the "ru_stress" normalizer in narrate.py:
    python tools/audit_ru_stress.py

FIRST RUN, 2026-07-15 — the table FAILED, hard. Of 197 entries, 30 rewrote the
word instead of accenting it, corrupting 1,029 of 37,098 verses:
    Вирсавия -> Виргавия   (Beersheba -> a non-word; Gen 21:31,32,33, 22:19...)
    Христа   -> Христоса   (invented non-word for Christ)
    Ирод     -> Ириод      Михей -> Михай     Иосиф -> Иосифа (wrong case)
    Нерон    -> НерО́н      (Latin capital O)
    8 entries inject 'і' U+0456 (Ukrainian/pre-reform, not Russian)
The normalizer is disabled in narrate.py as a result. The table was drafted but
the plan's "⚠ GATE (quality): owner/native spot-check" never happened — which
is exactly the failure this script exists to catch. Do not re-enable ru_stress
until every section below reports zero.
"""
import json, re, sys, io, unicodedata
sys.path.insert(0, "C:/Projects/Hexapla/tools")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import ru_stress

ACUTE = "́"
def strip_acute(s):
    return s.replace(ACUTE, "")

print("=== 1. Audit the table itself ===")
bad, noop, ok = [], [], []
for bare, stressed in ru_stress.STRESS_DICT.items():
    if strip_acute(stressed) == bare:
        (ok if ACUTE in stressed else noop).append((bare, stressed))
    else:
        bad.append((bare, stressed, strip_acute(stressed)))

print(f"  entries          : {len(ru_stress.STRESS_DICT)}")
print(f"  OK (stress only) : {len(ok)}")
print(f"  no-ops           : {len(noop)}")
print(f"  CHANGE THE WORD  : {len(bad)}")
print()
for bare, stressed, plain in bad:
    print(f"    {bare!r:>22} -> {stressed!r:<22} (reads as {plain!r})")

print("\n=== 2. Non-Russian letters introduced ===")
for bare, stressed in ru_stress.STRESS_DICT.items():
    for ch in strip_acute(stressed):
        if ch.isalpha() and not ("Ѐ" <= ch <= "ӿ"):
            print(f"    {bare!r} -> {stressed!r}: {ch!r} U+{ord(ch):04X} "
                  f"{unicodedata.name(ch, '?')}")
            break
    else:
        # і U+0456 is Cyrillic-block but not modern Russian
        if "і" in stressed:
            print(f"    {bare!r} -> {stressed!r}: 'і' U+0456 (Ukrainian/pre-reform, not Russian)")

print("\n=== 3. Duplicate keys silently lost ===")
src = open("C:/Projects/Hexapla/tools/ru_stress.py", encoding="utf-8").read()
keys = re.findall(r'^\s*"([^"]+)":\s*"', src, re.M)
from collections import Counter
for k, n in Counter(keys).items():
    if n > 1:
        print(f"    {k!r} appears {n}x")

print("\n=== 4. Damage to the actual Bible text ===")
b = json.load(open("C:/Projects/Hexapla/app/src/main/assets/bibles/ru_synodal.json",
                   encoding="utf-8"))
changed = corrupted = total = 0
examples = []
for bi, bk in enumerate(b):
    for ci, ch in enumerate(bk["chapters"]):
        for vi, v in enumerate(ch):
            if not v:
                continue
            total += 1
            out = ru_stress.apply_stress(v)
            if out == v:
                continue
            changed += 1
            if strip_acute(out) != v:
                corrupted += 1
                if len(examples) < 8:
                    examples.append((bk["name"], ci + 1, vi + 1, v, out))

print(f"  verses total     : {total:,}")
print(f"  verses touched   : {changed:,}")
print(f"  verses CORRUPTED : {corrupted:,}  (text changed, not just accented)")
print()
for name, c, v, before, after in examples:
    print(f"  {name} {c}:{v}")
    print(f"    before: {before[:95]}")
    print(f"    after : {strip_acute(after)[:95]}")
    print()
