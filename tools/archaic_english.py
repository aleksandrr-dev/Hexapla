# -*- coding: utf-8 -*-
"""Archaic English spelling normalization for TTS.

Converts Geneva (1599), Tyndale (1525), and Wycliffe (~1395) spellings
to modern-English phonetic equivalents so Kokoro TTS reads them correctly.
The app displays the original text; only TTS input is normalized.

Usage:
    from archaic_english import normalize
    text = normalize("And the worde was made flesshe", "tyndale")
"""
import re

# ── Geneva 1599 ──────────────────────────────────────────────────────
# Light touch: mostly Early Modern English u/v swaps + trailing -e

_GENEVA_DICT = {
    "giue": "give", "giuen": "given", "giueth": "giveth",
    "giuing": "giving",
    "liue": "live", "liued": "lived", "liueth": "liveth",
    "liuing": "living", "liues": "lives",
    "loue": "love", "loued": "loved", "loueth": "loveth",
    "louing": "loving",
    "moue": "move", "moued": "moved", "moueth": "moveth",
    "aboue": "above", "remoue": "remove", "remoueth": "removeth",
    "proue": "prove", "proued": "proved", "proueth": "proveth",
    "haue": "have", "behooue": "behoove",
    "euery": "every", "euen": "even", "euening": "evening",
    "euer": "ever", "euerlasting": "everlasting",
    "euill": "evil", "neuer": "never", "seuen": "seven",
    "eleuen": "eleven", "reuerence": "reverence",
    "deliuer": "deliver", "deliuered": "delivered",
    "deliuerance": "deliverance",
    "riuer": "river", "riuers": "rivers",
    "ouer": "over", "couer": "cover", "couered": "covered",
    "discouer": "discover", "discouered": "discovered",
    "receiue": "receive", "receiued": "received",
    "perceiue": "perceive", "perceiued": "perceived",
    "deceiue": "deceive", "deceiued": "deceived",
    "conceiue": "conceive", "conceiued": "conceived",
    "beleeue": "believe", "beleeued": "believed",
    "grieue": "grieve", "grieued": "grieved",
    "vnto": "unto", "vpon": "upon", "vp": "up",
    "vnder": "under", "vnderstand": "understand",
    "vs": "us", "vnlesse": "unless",
    "vre": "ure",
    "trueth": "truth", "truthe": "truth",
    "sayde": "said", "layde": "laid", "payed": "paid",
    "prayde": "prayed", "prayed": "prayed",
    "hundreth": "hundred",
    "moneth": "month", "moneths": "months",
    "sonnes": "sons", "sinnes": "sins",
    "crowne": "crown", "crownes": "crowns",
    "downe": "down", "towne": "town", "knowne": "known",
    "showne": "shown", "growne": "grown", "blowne": "blown",
    "throwne": "thrown", "sowne": "sown", "ouerthrowne": "overthrown",
    "houre": "hour", "houres": "hours",
    "foure": "four",
    "floure": "flower", "floures": "flowers",
    "fauoure": "favour", "fauour": "favour",
    "honoure": "honour", "honour": "honour",
    "laboure": "labour", "labour": "labour",
    "coloure": "colour", "colour": "colour",
    "deuoure": "devour", "deuoured": "devoured",
    "neighbour": "neighbor", "neighbours": "neighbors",
    "sauour": "savour", "sauoure": "savour",
    "onely": "only",
    "iudge": "judge", "iudged": "judged", "iudgement": "judgement",
    "ioy": "joy", "ioyful": "joyful",
    "iesus": "Jesus", "ierusalem": "Jerusalem",
    "iewes": "Jews", "iohn": "John",
    "iacob": "Jacob", "ioseph": "Joseph",
    "sawe": "saw",
    "glorie": "glory",
}

_GENEVA_RULES = [
    (re.compile(r'\bvn(\w)', re.I), r'un\1'),
]

# ── Tyndale 1525/1531 ───────────────────────────────────────────────

_TYNDALE_DICT = {
    **_GENEVA_DICT,
    "yf": "if", "ytt": "it",
    "ye": "the", "yt": "it",
    "youre": "your", "oure": "our",
    "lyfe": "life", "wyfe": "wife", "knyfe": "knife",
    "stryfe": "strife",
    "synne": "sin", "synnes": "sins", "synned": "sinned",
    "thynge": "thing", "thynges": "things",
    "kynge": "king", "kynges": "kings",
    "kyngdome": "kingdom", "kyngdomes": "kingdoms",
    "brynge": "bring", "brynges": "brings",
    "saynge": "saying", "saynges": "sayings",
    "doynge": "doing", "goynge": "going",
    "beynge": "being", "seynge": "seeing",
    "comynge": "coming", "makynge": "making",
    "offerynge": "offering", "offerynges": "offerings",
    "burntofferynge": "burnt offering",
    "mornynge": "morning", "evenynge": "evening",
    "begynnynge": "beginning", "beginnynge": "beginning",
    "accordynge": "according", "acordynge": "according",
    "nothynge": "nothing", "every thynge": "everything",
    "flesshe": "flesh", "fleshe": "flesh",
    "erthe": "earth",
    "herte": "heart", "hertes": "hearts",
    "deeth": "death", "deth": "death",
    "breth": "breath",
    "worde": "word", "wordes": "words",
    "lorde": "lord", "lordes": "lords",
    "worlde": "world",
    "amonge": "among", "amongest": "amongst",
    "verite": "verity",
    "syde": "side", "wyde": "wide",
    "skynne": "skin", "skynnes": "skins",
    "mayde": "maid", "maydes": "maids",
    "myddes": "midst", "myddest": "midst",
    "geueth": "giveth", "geue": "give", "geuen": "given",
    "lyfte": "lift", "lyft": "lift",
    "housse": "house", "hous": "house",
    "multytude": "multitude",
    "baptyme": "baptism",
    "beleue": "believe", "beleued": "believed",
    "receaue": "receive", "receaued": "received",
    "deceaue": "deceive",
    "greate": "great",
    "tyme": "time", "tymes": "times",
    "myne": "mine", "thyne": "thine",
    "fyre": "fire",
    "desyre": "desire", "desyred": "desired",
    "hyer": "higher",
    "awaye": "away",
    "praye": "pray", "prayed": "prayed", "prayer": "prayer",
    "obeye": "obey",
    "iourney": "journey",
    "hedde": "head",
    "bredde": "bread",
    "agayne": "again", "agaynst": "against",
    "faythfull": "faithful", "fayth": "faith",
    "daye": "day", "dayes": "days",
    "waye": "way", "wayes": "ways",
    "saye": "say",
    "laye": "lay",
    "heven": "heaven", "heuen": "heaven",
    "even": "even",
    "rightwesnes": "righteousness",
    "rightewesnes": "righteousness",
    "righteous": "righteous",
    "blessinge": "blessing", "blessynge": "blessing",
    "dwellynge": "dwelling",
    "willynge": "willing",
    "knowlege": "knowledge",
    "iudge": "judge", "iudgement": "judgement",
}

_TYNDALE_RULES = [
    (re.compile(r'\byf\b', re.I), 'if'),
    (re.compile(r'(\w)ynne\b', re.I), r'\1in'),
    (re.compile(r'(\w)ynge\b', re.I), r'\1ing'),
    (re.compile(r'(\w)ynge\b', re.I), r'\1ing'),
    (re.compile(r'(\w)yng\b', re.I), r'\1ing'),
    (re.compile(r'\bvn(\w)', re.I), r'un\1'),
]

# ── Wycliffe ~1395 ───────────────────────────────────────────────────

_WYCLIFFE_DICT = {
    **_TYNDALE_DICT,
    "sche": "she", "hir": "her", "hem": "them",
    "thei": "they", "thai": "they",
    "hise": "his", "youre": "your",
    "schulen": "shall", "schulde": "should",
    "schal": "shall", "schalt": "shalt",
    "shal": "shall", "shulde": "should",
    "wolde": "would", "coude": "could",
    "seith": "saith", "seide": "said", "seid": "said",
    "seye": "say", "seiynge": "saying",
    "schewe": "show", "schewid": "showed", "schewide": "showed",
    "schewith": "showeth", "schewing": "showing",
    "scheep": "sheep",
    "schen": "shine", "schyne": "shine",
    "schryne": "shrine",
    "kyng": "king", "kyngis": "kings",
    "bigynnyng": "beginning",
    "bigetun": "begotten",
    "bifore": "before",
    "bitwixe": "betwixt", "bitwene": "between",
    "bicause": "because", "bicam": "became",
    "biside": "beside",
    "perische": "perish", "perischide": "perished",
    "perauenture": "peradventure",
    "doith": "doeth", "makith": "maketh",
    "dwellith": "dwelleth", "goith": "goeth",
    "cometh": "cometh", "comynge": "coming",
    "witnessyng": "witnessing",
    "euerlastynge": "everlasting",
    "lyuynge": "living", "lyueth": "liveth",
    "hauynge": "having",
    "kunnyng": "cunning",
    "mesure": "measure",
    "myddis": "midst", "myddil": "middle",
    "heuene": "heaven", "heuenes": "heavens",
    "heuenly": "heavenly",
    "erthe": "earth", "ertheli": "earthly",
    "nouyt": "naught", "nought": "naught",
    "ayen": "again", "ayens": "against", "agen": "again",
    "togidere": "together", "togidre": "together",
    "abrood": "abroad",
    "treuthe": "truth", "treuth": "truth",
    "feith": "faith", "feithful": "faithful",
    "preest": "priest", "preestis": "priests",
    "sones": "sons", "sone": "son",
    "stoon": "stone", "stoones": "stones", "stoonys": "stones",
    "moone": "moon", "sonne": "sun",
    "wijf": "wife", "wyues": "wives",
    "synne": "sin", "synnes": "sins",
    "chirche": "church",
    "citee": "city", "citees": "cities",
    "peple": "people",
    "prophetis": "prophets", "prophete": "prophet",
    "disciplis": "disciples",
    "apostlis": "apostles",
    "holi": "holy", "hooli": "holy",
    "entride": "entered", "entring": "entering",
    "turne": "turn", "turnede": "turned",
    "axe": "ask", "axide": "asked", "axynge": "asking",
    "clepe": "call", "clepid": "called", "clepith": "calleth",
    "wondride": "wondered", "wondriden": "wondered",
    "knewe": "knew",
    "tyme": "time", "tymes": "times",
    "fier": "fire", "fyre": "fire",
    "watir": "water", "watris": "waters",
    "knyfe": "knife",
    "derknessis": "darknesses", "derknesse": "darkness",
    "derknesis": "darkness",
    "liyt": "light", "liytis": "lights",
    "riytful": "rightful", "riytfulnesse": "righteousness",
    "riytwisnesse": "righteousness",
    "wickidnesse": "wickedness",
    "priuyli": "privily",
    "forsothe": "forsooth",
    "sotheli": "soothly",
    "therfor": "therefore", "therfore": "therefore",
    "whanne": "when", "whan": "when",
    "wher": "where", "wherfore": "wherefore",
    "whiche": "which",
    "aftir": "after", "aftirward": "afterward",
    "silf": "self", "himsilf": "himself",
    "also": "also",
    "thousynde": "thousand", "thousyndes": "thousands",
    "hundrid": "hundred", "hundridis": "hundreds",
    "dwellide": "dwelled", "dwelte": "dwelt",
    "answeride": "answered",
    "commaundide": "commanded", "comaundide": "commanded",
    "resseyuede": "received", "resseyued": "received",
    "vndirstonde": "understand", "vndirstood": "understood",
    "iuge": "judge", "iugement": "judgement",
    "iugide": "judged",
    "ioie": "joy", "ioye": "joy",
    "schuld": "should",
    "wolden": "would",
    "weren": "were", "hadden": "had",
    "camen": "came",
    "diden": "did",
    "seiden": "said",
    "kyngdom": "kingdom",
    "ynne": "inn",
    "cros": "cross",
    "oonli": "only",
    "oon": "one", "ech": "each",
    "maad": "made", "maade": "made",
    "han": "have", "hath": "hath",
    "seyn": "seen", "sien": "seen",
    "hym": "him", "hir": "her", "hem": "them",
    "fadir": "father", "fadris": "fathers",
    "modir": "mother", "modris": "mothers",
    "brothir": "brother", "bretheren": "brethren",
    "sistir": "sister",
    "ful": "full",
    "aungel": "angel", "aungelis": "angels",
    "dai": "day", "daies": "days",
    "weie": "way", "weies": "ways",
    "place": "place", "plas": "place",
    "dwellide": "dwelled", "dwellyde": "dwelled",
    "answerid": "answered",
    "wordis": "words",
    "werkis": "works", "werk": "work",
    "wolde": "would", "wolden": "would",
    "schulden": "should",
    "myche": "much", "mych": "much",
    "suche": "such",
    "yche": "each",
    "eiythe": "eighth",
    "writen": "written", "writun": "written",
    "tokene": "token",
    "schulde": "should",
    "abhomynacioun": "abomination",
    "tabernacle": "tabernacle",
    "wickid": "wicked", "wickidly": "wickedly",
    "graue": "grave",
    "auter": "altar", "auteris": "altars",
    "sacrid": "sacred",
    "encense": "incense",
    "tribulacioun": "tribulation",
    "resurreccioun": "resurrection",
    "temptacioun": "temptation",
    "generacioun": "generation",
    "nacioun": "nation", "naciouns": "nations",
    "condicioun": "condition",
    "multitude": "multitude",
    "greet": "great",
    "twei": "two", "tweyne": "twain",
    "thre": "three",
    "fyue": "five", "fiue": "five",
    "sixe": "six",
    "seuene": "seven",
    "eiyte": "eight",
    "nyne": "nine",
    "ten": "ten",
    "twelue": "twelve",
    "thritti": "thirty", "fourti": "forty", "fifti": "fifty",
}

_WYCLIFFE_RULES = [
    (re.compile(r'\bsche\b', re.I), 'she'),
    (re.compile(r'sch(\w)', re.I), r'sh\1'),
    (re.compile(r'(\w)ith\b'), r'\1eth'),
    (re.compile(r'(\w)ide\b'), r'\1ed'),
    (re.compile(r'(\w)iden\b'), r'\1ed'),
    (re.compile(r'(\w)ynge\b', re.I), r'\1ing'),
    (re.compile(r'(\w)ynne\b', re.I), r'\1in'),
    (re.compile(r'(\w)yng\b', re.I), r'\1ing'),
    (re.compile(r'\bvn(\w)', re.I), r'un\1'),
    (re.compile(r'\beu(\w)', re.I), r'ev\1'),
    (re.compile(r'(\w)nes\b'), r'\1ness'),
]

_NORMALIZERS = {
    "geneva":  (_GENEVA_DICT,  _GENEVA_RULES),
    "tyndale": (_TYNDALE_DICT, _TYNDALE_RULES),
    "wycliffe": (_WYCLIFFE_DICT, _WYCLIFFE_RULES),
}


def _apply_dict(text, word_dict):
    """Replace whole words using dictionary (case-preserving)."""
    def _replace(m):
        word = m.group(0)
        key = word.lower()
        if key not in word_dict:
            return word
        replacement = word_dict[key]
        if word[0].isupper() and not replacement[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    return re.sub(r'\b[A-Za-z]+\b', _replace, text)


def _apply_rules(text, rules):
    """Apply regex substitution rules in order."""
    for pattern, repl in rules:
        text = pattern.sub(repl, text)
    return text


def normalize(text, dialect):
    """Normalize archaic English spelling for TTS.

    Args:
        text: original verse text
        dialect: "geneva", "tyndale", or "wycliffe"

    Returns:
        text with spellings normalized for modern TTS pronunciation
    """
    if dialect not in _NORMALIZERS:
        return text
    word_dict, rules = _NORMALIZERS[dialect]
    text = _apply_dict(text, word_dict)
    text = _apply_rules(text, rules)
    return text
