# -*- coding: utf-8 -*-
"""Russian biblical stress dictionary for Piper TTS.

Piper mispronounces biblical proper names. This script builds a curated
name→accented-form lookup table (using combining acute U+0301 after the
stressed vowel, which is what Piper expects) and applies it as text
preprocessing.

Usage:
  python ru_stress.py --build          # frequency-count capitalized words
  python ru_stress.py --apply < input  # apply stress marks to stdin

When imported: apply_stress(text: str) -> str
"""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"

# Stress marks: combining acute U+0301 after vowel.
# Each stem maps to the stress position (0-indexed from the start of the stem).
# All declined forms are listed explicitly.

STRESS_DICT = {
    # Common OT names (patriarchs, prophets, kings)
    "Авраам": "Авраа́м",          # Abraham (stem 0: А)
    "Авраама": "Авраа́ма",
    "Аврааму": "Авраа́му",
    "Авраамом": "Авраа́мом",
    "Аврааме": "Авраа́ме",

    "Моисей": "Моисе́й",           # Moses
    "Моисея": "Моисе́я",
    "Моисею": "Моисе́ю",
    "Моисеем": "Моисе́ем",

    "Иосиф": "Иосифа",             # Joseph (common: unstressed)

    "Иаков": "Иа́ков",             # Jacob
    "Иакова": "Иа́кова",
    "Иакову": "Иа́кову",

    "Исаак": "Исаа́к",             # Isaac
    "Исаака": "Исаа́ка",

    "Ной": "Но́й",                  # Noah
    "Ноя": "Но́я",

    "Лот": "Ло́т",                  # Lot
    "Лота": "Ло́та",

    "Давид": "Дави́д",             # David
    "Давида": "Дави́да",
    "Давиду": "Дави́ду",
    "Давидом": "Дави́дом",

    "Соломон": "Соломо́н",         # Solomon
    "Соломона": "Соломо́на",

    "Исаия": "Иса́ия",             # Isaiah
    "Исаии": "Иса́ии",
    "Исаиею": "Иса́иею",

    "Иеремия": "Иеремі́я",         # Jeremiah (archaic і for і after e)
    "Иеремии": "Иеремі́и",

    "Иезекииль": "Иезекии́ль",     # Ezekiel
    "Иезекииля": "Иезекии́ля",

    "Даниил": "Дании́л",            # Daniel
    "Даниила": "Дании́ла",
    "Даниилу": "Дании́лу",

    "Иов": "Ио́в",                  # Job
    "Иова": "Ио́ва",

    "Авватум": "Аввату́м",         # Habakkuk (genitive/accusative form found in text)

    "Наум": "Нау́м",                # Nahum
    "Наума": "Нау́ма",

    "Софония": "Софони́я",         # Zephaniah
    "Софонии": "Софони́и",

    "Иоиль": "Иои́ль",             # Joel
    "Иоиля": "Иои́ля",

    "Амос": "А́мос",               # Amos
    "Амоса": "А́моса",

    "Авдий": "Авди́й",             # Obadiah

    "Иона": "Ио́на",               # Jonah
    "Ионы": "Ио́ны",
    "Ионе": "Ио́не",

    "Михей": "Миха́й",             # Micah
    "Михея": "Миха́я",

    "Аггей": "Аггей",              # Haggai

    "Захария": "Захари́я",         # Zechariah
    "Захарии": "Захари́и",
    "Захариею": "Захари́ею",

    "Малахия": "Малахі́я",         # Malachi
    "Малахии": "Малахі́и",

    "Елизавета": "Елиза́вета",     # Elizabeth
    "Елизаветы": "Елиза́веты",
    "Елизаветой": "Елиза́ветой",

    "Вирсавия": "Виргави́я",       # Bathsheba (various transliterations)
    "Вирсавии": "Виргави́и",

    "Вакхук": "Вакху́к",           # alternative Habakkuk

    # NT common names (apostles, disciples)
    "Иисус": "Иису́с",             # Jesus
    "Иисуса": "Иису́са",
    "Иисусе": "Иису́се",
    "Иисусом": "Иису́сом",
    "Иисусу": "Иису́су",

    "Христос": "Христо́с",         # Christ
    "Христа": "Христо́са",
    "Христе": "Христо́се",
    "Христом": "Христо́сом",

    "Петр": "Петр",                # Peter (unstressed usually)
    "Петра": "Петра",
    "Петре": "Петре",
    "Петром": "Петром",

    "Иоанн": "Иоа́нн",             # John
    "Иоанна": "Иоа́нна",
    "Иоаннова": "Иоа́ннова",

    "Иаков": "Иа́ков",             # James
    "Иакова": "Иа́кова",

    "Андрей": "Андре́й",           # Andrew
    "Андрея": "Андре́я",

    "Филипп": "Филипп",            # Philip
    "Филиппа": "Филиппа",

    "Варфоломей": "Варфоломе́й",  # Bartholomew
    "Варфоломея": "Варфоломе́я",

    "Матфей": "Матфе́й",           # Matthew
    "Матфея": "Матфе́я",

    "Фома": "Фома́",               # Thomas
    "Фомы": "Фома́",
    "Фоме": "Фома́е",

    "Нафанаил": "Нафанаи́л",       # Nathanael
    "Нафанаила": "Нафанаи́ла",

    "Симон": "Симо́н",             # Simon
    "Симона": "Симо́на",

    "Иуда": "Иу́да",               # Judas
    "Иуды": "Иу́ды",
    "Иуде": "Иу́де",

    "Максимин": "Максими́н",       # Maximinus (apostolic age)

    "Павел": "Па́вел",             # Paul
    "Павла": "Па́вла",
    "Павле": "Па́вле",
    "Павлом": "Па́влом",

    "Варнава": "Варнава́",         # Barnabas
    "Варнавы": "Варнава́",

    "Марк": "Марк",                # Mark
    "Марка": "Марка",

    "Лука": "Лука́",               # Luke
    "Луки": "Лука́",

    "Тимофей": "Тимофе́й",         # Timothy
    "Тимофея": "Тимофе́я",

    "Титу": "Ти́ту",               # Titus
    "Тита": "Ти́та",

    "Филимон": "Филимо́н",         # Philemon
    "Филимона": "Филимо́на",

    "Онисим": "Онисі́м",           # Onesimus
    "Онисима": "Онисі́ма",

    # NT women
    "Мария": "Мари́я",             # Mary
    "Марии": "Мари́и",
    "Маринов": "Мари́нов",
    "Мариею": "Мари́ею",

    "Магдалина": "Магдали́на",     # Magdalene
    "Магдалины": "Магдали́ны",

    "Салома": "Салома́",           # Salome
    "Салому": "Салома́",

    # Places (major cities, regions)
    "Иерусалим": "Иерусали́м",     # Jerusalem
    "Иерусалима": "Иерусали́ма",
    "Иерусалиме": "Иерусали́ме",
    "Иерусалимом": "Иерусали́мом",

    "Вифлеем": "Вифлее́м",         # Bethlehem
    "Вифлеема": "Вифлее́ма",
    "Вифлееме": "Вифлее́ме",

    "Назарет": "Назаре́т",         # Nazareth
    "Назарета": "Назаре́та",
    "Назарете": "Назаре́те",

    "Египет": "Еги́пет",           # Egypt
    "Египта": "Еги́пта",
    "Египте": "Еги́пте",

    "Вавилон": "Вавило́н",         # Babylon
    "Вавилона": "Вавило́на",
    "Вавилоне": "Вавило́не",

    "Галилея": "Галилея́",         # Galilee
    "Галилеи": "Галилея́",

    "Иудея": "Иудея́",             # Judea
    "Иудеи": "Иудея́",

    "Самария": "Самари́я",         # Samaria
    "Самарии": "Самари́и",
    "Самариею": "Самари́ею",

    "Голгофа": "Голго́фа",         # Golgotha
    "Голгофе": "Голго́фе",
    "Голгофу": "Голго́фу",

    "Гефсимания": "Гефсима́ния",   # Gethsemane
    "Гефсимании": "Гефсима́ни",

    "Синай": "Сина́й",             # Sinai
    "Синая": "Сина́я",
    "Синае": "Сина́е",

    "Сион": "Сио́н",               # Zion
    "Сиона": "Сио́на",
    "Сионе": "Сио́не",

    "Кедрон": "Кедро́н",           # Cedron
    "Кедрона": "Кедро́на",

    "Иордан": "Иорда́н",           # Jordan
    "Иордана": "Иорда́на",
    "Иордане": "Иорда́не",

    "Мертвое": "Мёртвое",          # Dead Sea (usually unstressed)

    "Тивериада": "Тивериа́да",     # Tiberias
    "Тивериаде": "Тивериа́де",

    "Каперсаум": "Капернау́м",     # Capernaum
    "Капернаума": "Капернау́ма",
    "Капернауме": "Капернау́ме",

    "Вифсаида": "Вифсаи́да",       # Bethsaida
    "Вифсаиде": "Вифсаи́де",

    "Никодим": "Никоди́м",         # Nicodemus
    "Никодима": "Никоди́ма",

    "Гавриил": "Гавриил",          # Gabriel
    "Гавриила": "Гавриила",

    "Мелхиседек": "Мелхиседе́к",   # Melchizedek
    "Мелхиседека": "Мелхиседе́ка",

    "Навуходоносор": "Навухадоносо́р",  # Nebuchadnezzar
    "Навуходоносора": "Навухадоносо́ра",

    "Артаксеркс": "Артаксе́ркс",   # Artaxerxes
    "Артаксеркса": "Артаксе́ркса",

    "Ирод": "Ирі́од",              # Herod
    "Ирода": "Ирі́ода",

    "Филипп": "Филипп",            # Philip (tetrarch)

    "Клавдий": "Кла́вдий",         # Claudius
    "Клавдия": "Кла́вдия",

    "Нерон": "НерО́н",             # Nero
    "Нерона": "НерО́на",

    # Common divine/religious terms
    "Бог": "Бог",                  # God (typically unstressed)
    "Боге": "Боге",
    "Богом": "Богом",

    "Господь": "Го́спо́дь",        # Lord (double stress in some dialects, kept as single for TTS)
    "Господа": "Го́спода",
    "Господе": "Го́споде",

    "Святой": "Свято́й",           # Holy
    "Святого": "Свято́го",
    "Святым": "Святы́м",

    # Add more as needed - frequency list will guide additional entries
}


def build_frequency():
    """Read ru_synodal.json, count capitalized words, print sorted by frequency."""
    asset_path = ASSETS / "ru_synodal.json"
    if not asset_path.exists():
        print(f"Error: {asset_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(asset_path, encoding="utf-8") as f:
        books = json.load(f)

    words = Counter()
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter:
                # Split on whitespace and punctuation, preserve capitalization
                tokens = re.findall(r"\b[\w]+\b", verse) if verse else []
                for token in tokens:
                    # Count capitalized words (first letter uppercase)
                    if token and token[0].isupper():
                        words[token] += 1

    print("Most frequent capitalized words (candidates for stress marking):\n")
    print("Frequency | Word")
    print("-" * 40)
    for word, count in words.most_common(300):
        print(f"{count:8d} | {word}")


def apply_stress(text):
    """Apply stress marks from STRESS_DICT to text.

    Matches whole words only (case-sensitive). Returns text with stress marks applied.
    """
    result = text
    # Sort by length descending to match longer forms first (e.g., "Авраама" before "Авраам")
    for bare, stressed in sorted(STRESS_DICT.items(), key=lambda x: len(x[0]), reverse=True):
        # Word boundary match: \b at the start, and not followed by \w at end
        # Use a negative lookahead to avoid partial matches
        pattern = r'\b' + re.escape(bare) + r'\b'
        result = re.sub(pattern, stressed, result)

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        build_frequency()
    elif len(sys.argv) > 1 and sys.argv[1] == "--apply":
        # Read stdin, apply stress, write stdout
        text = sys.stdin.read()
        print(apply_stress(text), end="")
    else:
        # Print help
        sys.stdout.write("Usage:\n  python ru_stress.py --build          # frequency-count capitalized words\n")
        sys.stdout.write("  python ru_stress.py --apply < input  # apply stress marks to stdin\n")
        sys.exit(1)
