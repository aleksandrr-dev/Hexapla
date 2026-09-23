"""Beblia Holy-Bible-XML-Format -> app asset format.

Structure: <bible><testament><book number><chapter number><verse number>.
Verse gaps are filled with "". Book names are supplied per translation
below (the XML carries none).

WARNING (2026-07-11): Beblia squeezes continentally-versified texts
into a KJV-shaped grid, leaving empty slots at chapter-boundary
divergences, shifting neighbors, and merging overflow verses — and
some corpora carry literal "*** POSSIBLE ERROR ***" placeholders.
That defect shipped in 1.4.0 (sv_karlxii, da_1819; repaired by
fix_sv_karlxii.py / replaced via convert_emg_danish.py). Before
shipping ANY Beblia-derived text: compare per-chapter verse counts
against en_kjv.json and inspect every empty slot.

Usage: python convert_beblia.py <src.xml> <names-key> <dst.json>
"""
import json
import sys
import xml.etree.ElementTree as ET

NAMES = {
    # Diodati tradition Italian names.
    "it": [
        "Genesi", "Esodo", "Levitico", "Numeri", "Deuteronomio", "Giosuè",
        "Giudici", "Rut", "1 Samuele", "2 Samuele", "1 Re", "2 Re",
        "1 Cronache", "2 Cronache", "Esdra", "Neemia", "Ester", "Giobbe",
        "Salmi", "Proverbi", "Ecclesiaste", "Cantico de' Cantici", "Isaia",
        "Geremia", "Lamentazioni", "Ezechiele", "Daniele", "Osea", "Gioele",
        "Amos", "Abdia", "Giona", "Michea", "Nahum", "Abacuc", "Sofonia",
        "Aggeo", "Zaccaria", "Malachia",
        "Matteo", "Marco", "Luca", "Giovanni", "Atti", "Romani",
        "1 Corinzi", "2 Corinzi", "Galati", "Efesini", "Filippesi",
        "Colossesi", "1 Tessalonicesi", "2 Tessalonicesi", "1 Timoteo",
        "2 Timoteo", "Tito", "Filemone", "Ebrei", "Giacomo", "1 Pietro",
        "2 Pietro", "1 Giovanni", "2 Giovanni", "3 Giovanni", "Giuda",
        "Apocalisse",
    ],
    # Danish 1819-era names.
    "da": [
        "1 Mosebog", "2 Mosebog", "3 Mosebog", "4 Mosebog", "5 Mosebog",
        "Josva", "Dommerne", "Ruth", "1 Samuelsbog", "2 Samuelsbog",
        "1 Kongebog", "2 Kongebog", "1 Krønikebog", "2 Krønikebog", "Esra",
        "Nehemias", "Esther", "Job", "Psalmerne", "Ordsprogene",
        "Prædikeren", "Højsangen", "Esajas", "Jeremias", "Klagesangene",
        "Ezekiel", "Daniel", "Hoseas", "Joel", "Amos", "Obadias", "Jonas",
        "Mika", "Nahum", "Habakkuk", "Zefanias", "Haggaj", "Zakarias",
        "Malakias",
        "Matthæus", "Markus", "Lukas", "Johannes", "Apostlenes Gerninger",
        "Romerbrevet", "1 Korinther", "2 Korinther", "Galaterne",
        "Efeserne", "Filipperne", "Kolossenserne", "1 Thessaloniker",
        "2 Thessaloniker", "1 Timotheus", "2 Timotheus", "Titus",
        "Filemon", "Hebræerne", "Jakob", "1 Peter", "2 Peter",
        "1 Johannes", "2 Johannes", "3 Johannes", "Judas",
        "Johannes' Aabenbaring",
    ],
}


def main(src, names_key, dst):
    names = NAMES[names_key]
    tree = ET.parse(src)
    raw_books = [b for t in tree.getroot() for b in t]
    assert len(raw_books) == 66, len(raw_books)
    books = []
    for i, b in enumerate(raw_books):
        chapters = []
        for ch in sorted(b, key=lambda x: int(x.get("number"))):
            vmax = max(int(v.get("number")) for v in ch)
            verses = [""] * vmax
            for v in ch:
                text = (v.text or "").strip()
                assert "POSSIBLE ERROR" not in text, \
                    f"placeholder verse in source: book {i + 1} ch {ch.get('number')} v {v.get('number')}"
                verses[int(v.get("number")) - 1] = text
            chapters.append(verses)
        books.append({"name": names[i], "chapters": chapters})
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    print(f"{dst}: 66 books, {total} verses")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
