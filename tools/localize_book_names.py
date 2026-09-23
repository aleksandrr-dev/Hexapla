"""Localize the display book names inside translation assets.

The app shows books[i].name from the current translation's asset
(Bible.kt parseAsset), but the scrollmapper-derived assets for Luther,
Reina-Valera, Martin, Almeida and the WLC kept English book names —
so a German reader saw "Revelation" instead of "Offenbarung".

Names are curated per translation tradition (Luther 1545, RV 1909,
Martin 1744, Almeida/Bíblia Livre, Hebrew Tanakh) in KJV canonical
order. Only the canon (or, for the WLC, the 39 OT books that carry
text) is renamed; apocrypha slots and empty books are left untouched.

Idempotent: re-running just rewrites the same names.

Usage: python localize_book_names.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")

DE_LUTHER = [
    "1. Mose", "2. Mose", "3. Mose", "4. Mose", "5. Mose",
    "Josua", "Richter", "Ruth", "1. Samuel", "2. Samuel",
    "1. Könige", "2. Könige", "1. Chronik", "2. Chronik", "Esra",
    "Nehemia", "Esther", "Hiob", "Psalmen", "Sprüche",
    "Prediger", "Hoheslied", "Jesaja", "Jeremia", "Klagelieder",
    "Hesekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadja", "Jona", "Micha", "Nahum", "Habakuk",
    "Zephanja", "Haggai", "Sacharja", "Maleachi",
    "Matthäus", "Markus", "Lukas", "Johannes", "Apostelgeschichte",
    "Römer", "1. Korinther", "2. Korinther", "Galater", "Epheser",
    "Philipper", "Kolosser", "1. Thessalonicher", "2. Thessalonicher",
    "1. Timotheus", "2. Timotheus", "Titus", "Philemon", "Hebräer",
    "Jakobus", "1. Petrus", "2. Petrus", "1. Johannes", "2. Johannes",
    "3. Johannes", "Judas", "Offenbarung",
]

ES_RV = [
    "Génesis", "Éxodo", "Levítico", "Números", "Deuteronomio",
    "Josué", "Jueces", "Rut", "1 Samuel", "2 Samuel",
    "1 Reyes", "2 Reyes", "1 Crónicas", "2 Crónicas", "Esdras",
    "Nehemías", "Ester", "Job", "Salmos", "Proverbios",
    "Eclesiastés", "Cantares", "Isaías", "Jeremías", "Lamentaciones",
    "Ezequiel", "Daniel", "Oseas", "Joel", "Amós",
    "Abdías", "Jonás", "Miqueas", "Nahúm", "Habacuc",
    "Sofonías", "Hageo", "Zacarías", "Malaquías",
    "Mateo", "Marcos", "Lucas", "Juan", "Hechos",
    "Romanos", "1 Corintios", "2 Corintios", "Gálatas", "Efesios",
    "Filipenses", "Colosenses", "1 Tesalonicenses", "2 Tesalonicenses",
    "1 Timoteo", "2 Timoteo", "Tito", "Filemón", "Hebreos",
    "Santiago", "1 Pedro", "2 Pedro", "1 Juan", "2 Juan",
    "3 Juan", "Judas", "Apocalipsis",
]

FR_MARTIN = [
    "Genèse", "Exode", "Lévitique", "Nombres", "Deutéronome",
    "Josué", "Juges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Rois", "2 Rois", "1 Chroniques", "2 Chroniques", "Esdras",
    "Néhémie", "Esther", "Job", "Psaumes", "Proverbes",
    "Ecclésiaste", "Cantique des cantiques", "Ésaïe", "Jérémie",
    "Lamentations", "Ézéchiel", "Daniel", "Osée", "Joël", "Amos",
    "Abdias", "Jonas", "Michée", "Nahum", "Habacuc",
    "Sophonie", "Aggée", "Zacharie", "Malachie",
    "Matthieu", "Marc", "Luc", "Jean", "Actes",
    "Romains", "1 Corinthiens", "2 Corinthiens", "Galates", "Éphésiens",
    "Philippiens", "Colossiens", "1 Thessaloniciens", "2 Thessaloniciens",
    "1 Timothée", "2 Timothée", "Tite", "Philémon", "Hébreux",
    "Jacques", "1 Pierre", "2 Pierre", "1 Jean", "2 Jean",
    "3 Jean", "Jude", "Apocalypse",
]

PT_ALMEIDA = [
    "Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio",
    "Josué", "Juízes", "Rute", "1 Samuel", "2 Samuel",
    "1 Reis", "2 Reis", "1 Crônicas", "2 Crônicas", "Esdras",
    "Neemias", "Ester", "Jó", "Salmos", "Provérbios",
    "Eclesiastes", "Cantares", "Isaías", "Jeremias", "Lamentações",
    "Ezequiel", "Daniel", "Oseias", "Joel", "Amós",
    "Obadias", "Jonas", "Miqueias", "Naum", "Habacuque",
    "Sofonias", "Ageu", "Zacarias", "Malaquias",
    "Mateus", "Marcos", "Lucas", "João", "Atos",
    "Romanos", "1 Coríntios", "2 Coríntios", "Gálatas", "Efésios",
    "Filipenses", "Colossenses", "1 Tessalonicenses", "2 Tessalonicenses",
    "1 Timóteo", "2 Timóteo", "Tito", "Filemom", "Hebreus",
    "Tiago", "1 Pedro", "2 Pedro", "1 João", "2 João",
    "3 João", "Judas", "Apocalipse",
]

# Hebrew Tanakh names in KJV canonical order — only the 39 OT books;
# the WLC asset's NT slots are empty and never shown.
HE_WLC = [
    "בראשית", "שמות", "ויקרא", "במדבר", "דברים",
    "יהושע", "שופטים", "רות", "שמואל א", "שמואל ב",
    "מלכים א", "מלכים ב", "דברי הימים א", "דברי הימים ב", "עזרא",
    "נחמיה", "אסתר", "איוב", "תהלים", "משלי",
    "קהלת", "שיר השירים", "ישעיהו", "ירמיהו", "איכה",
    "יחזקאל", "דניאל", "הושע", "יואל", "עמוס",
    "עובדיה", "יונה", "מיכה", "נחום", "חבקוק",
    "צפניה", "חגי", "זכריה", "מלאכי",
]

JOBS = [
    ("de_luther.json", DE_LUTHER),
    ("es_rv.json", ES_RV),
    ("fr_martin.json", FR_MARTIN),
    ("pt_almeida.json", PT_ALMEIDA),
    ("he_wlc.json", HE_WLC),
]


def main():
    for asset, names in JOBS:
        path = os.path.join(ASSETS, asset)
        books = json.load(open(path, encoding="utf-8"))
        assert len(books) >= len(names), f"{asset}: {len(books)} books < {len(names)} names"
        changed = 0
        for i, name in enumerate(names):
            if books[i]["name"] != name:
                books[i]["name"] = name
                changed += 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
        print(f"{asset}: renamed {changed}/{len(names)} books")


if __name__ == "__main__":
    main()
