# -*- coding: utf-8 -*-
"""Replace el_vamvas.json's English book names with Greek ones.

convert_scrollmapper.py passes through the source's book names, and the
scrollmapper GreVamvas export carries ENGLISH names — the same
books[i].name defect class fixed for de_luther/es_rv/fr_martin/pt_almeida
in 1.4.1 (tools/localize_book_names.py). Curated list below: standard
Greek Protestant (Vamvas-tradition) names, MONOTONIC to match the
translation's own orthography — the deliberate counterpart of the
polytonic names in grc_byz («Κατὰ Ματθαῖον» there, «Κατά Ματθαίον» here).

Names-only edit: chapters are asserted byte-identical. Re-run after any
regeneration of el_vamvas.json from the scrollmapper source.

Usage: python fix_vamvas_book_names.py
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "el_vamvas.json")

NAMES = [
    "Γένεσις", "Έξοδος", "Λευιτικόν", "Αριθμοί", "Δευτερονόμιον",
    "Ιησούς του Ναυή", "Κριταί", "Ρουθ", "Σαμουήλ Α΄", "Σαμουήλ Β΄",
    "Βασιλέων Α΄", "Βασιλέων Β΄", "Χρονικών Α΄", "Χρονικών Β΄", "Έσδρας",
    "Νεεμίας", "Εσθήρ", "Ιώβ", "Ψαλμοί", "Παροιμίαι",
    "Εκκλησιαστής", "Άσμα Ασμάτων", "Ησαΐας", "Ιερεμίας", "Θρήνοι",
    "Ιεζεκιήλ", "Δανιήλ", "Ωσηέ", "Ιωήλ", "Αμώς",
    "Αβδιού", "Ιωνάς", "Μιχαίας", "Ναούμ", "Αββακούμ",
    "Σοφονίας", "Αγγαίος", "Ζαχαρίας", "Μαλαχίας",
    "Κατά Ματθαίον", "Κατά Μάρκον", "Κατά Λουκάν", "Κατά Ιωάννην",
    "Πράξεις των Αποστόλων", "Προς Ρωμαίους", "Προς Κορινθίους Α΄",
    "Προς Κορινθίους Β΄", "Προς Γαλάτας", "Προς Εφεσίους",
    "Προς Φιλιππησίους", "Προς Κολοσσαείς", "Προς Θεσσαλονικείς Α΄",
    "Προς Θεσσαλονικείς Β΄", "Προς Τιμόθεον Α΄", "Προς Τιμόθεον Β΄",
    "Προς Τίτον", "Προς Φιλήμονα", "Προς Εβραίους", "Ιακώβου",
    "Πέτρου Α΄", "Πέτρου Β΄", "Ιωάννου Α΄", "Ιωάννου Β΄", "Ιωάννου Γ΄",
    "Ιούδα", "Αποκάλυψις Ιωάννου",
]

assert len(NAMES) == 66

books = json.load(open(ASSET, encoding="utf-8"))
assert len(books) == 66, len(books)
before = json.dumps([b["chapters"] for b in books], ensure_ascii=False)
for b, name in zip(books, NAMES):
    print(f"{b['name']:24} -> {name}")
    b["name"] = name
after = json.dumps([b["chapters"] for b in books], ensure_ascii=False)
assert before == after, "verse text changed — refusing to write"
with open(ASSET, "w", encoding="utf-8") as f:
    json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
print(f"\n{ASSET}: 66 names replaced, text untouched")
