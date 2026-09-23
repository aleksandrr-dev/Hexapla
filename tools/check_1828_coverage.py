"""How much of the KJV/Webster-Bible vocabulary resolves to a Webster 1828
headword through the lookup chain? Mirrors Webster1828Repo.candidates in
the app — keep the two in sync. Prints coverage and the most frequent
unresolved words so the rules can be tuned.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")

# KJV-frequent forms 1828 lacks as headwords (or spells differently).
IRREGULAR = {
    "HATH": "HAVE", "DOTH": "DO", "DOST": "DO", "DIDST": "DO",
    "SAITH": "SAY", "SAIDST": "SAY", "SHALT": "SHALL", "WILT": "WILL",
    "CANST": "CAN", "COULDEST": "COULD", "WOULDEST": "WOULD",
    "SHOULDEST": "SHOULD", "MIGHTEST": "MIGHT", "MAYEST": "MAY",
    "MUSTEST": "MUST", "SHEW": "SHOW", "SHEWED": "SHOW", "SHEWETH": "SHOW",
    "SHEWN": "SHOW", "SHEWING": "SHOW", "SHEWBREAD": "SHOW-BREAD",
    "BEGAT": "BEGET", "BEGOTTEN": "BEGET", "SLEW": "SLAY", "SLAIN": "SLAY",
    "SMOTE": "SMITE", "SMITTEN": "SMITE", "TRODDEN": "TREAD", "TROD": "TREAD",
    "BADE": "BID", "FORBADE": "FORBID", "GAVEST": "GIVE", "GAVE": "GIVE",
    "TOOK": "TAKE", "TOOKEST": "TAKE", "TAKEN": "TAKE", "WENT": "GO",
    "WENTEST": "GO", "CAME": "COME", "CAMEST": "COME", "SAW": "SEE",
    "SAWEST": "SEE", "SEEN": "SEE", "STOOD": "STAND", "STOODEST": "STAND",
    "BROUGHT": "BRING", "BROUGHTEST": "BRING", "SOUGHT": "SEEK",
    "FOUGHT": "FIGHT", "BOUGHT": "BUY", "TAUGHT": "TEACH", "CAUGHT": "CATCH",
    "KEPT": "KEEP", "SLEPT": "SLEEP", "WEPT": "WEEP", "SWEPT": "SWEEP",
    "FLED": "FLEE", "FED": "FEED", "LED": "LEAD", "LEDDEST": "LEAD",
    "MET": "MEET", "HELD": "HOLD", "HELDEST": "HOLD", "TOLD": "TELL",
    "TOLDEST": "TELL", "SOLD": "SELL", "SENT": "SEND", "SENTEST": "SEND",
    "SPENT": "SPEND", "BENT": "BEND", "LENT": "LEND", "RENT": "REND",
    "BUILT": "BUILD", "SAT": "SIT", "SATEST": "SIT", "LAY": "LIE",
    "LAIN": "LIE", "MADE": "MAKE", "MADEST": "MAKE", "SPOKEN": "SPEAK",
    "CHOSE": "CHOOSE", "CHOSEN": "CHOOSE", "DROVE": "DRIVE",
    "DRIVEN": "DRIVE", "RODE": "RIDE", "RIDDEN": "RIDE", "ROSE": "RISE",
    "RISEN": "RISE", "AROSE": "ARISE", "ARISEN": "ARISE", "WROTE": "WRITE",
    "WRITTEN": "WRITE", "SWORE": "SWEAR", "SWORN": "SWEAR", "TORE": "TEAR",
    "TORN": "TEAR", "WORE": "WEAR", "WORN": "WEAR", "BORE": "BEAR",
    "BORNE": "BEAR", "BORN": "BEAR", "GRAVEN": "GRAVE", "HEWN": "HEW",
    "SOWN": "SOW", "MOWN": "MOW", "KNOWN": "KNOW", "KNEW": "KNOW",
    "KNEWEST": "KNOW", "GREW": "GROW", "GROWN": "GROW", "THREW": "THROW",
    "THROWN": "THROW", "BLEW": "BLOW", "BLOWN": "BLOW", "FLEW": "FLY",
    "FLOWN": "FLY", "DREW": "DRAW", "DRAWN": "DRAW", "DRAWEST": "DRAW",
    "ATE": "EAT", "EATEN": "EAT", "DRANK": "DRINK", "DRUNK": "DRINK",
    "DRUNKEN": "DRINK", "SANG": "SING", "SUNG": "SING", "RANG": "RING",
    "RUNG": "RING", "SANK": "SINK", "SUNK": "SINK", "SUNKEN": "SINK",
    "SWAM": "SWIM", "SWUM": "SWIM", "RAN": "RUN", "RANNEST": "RUN",
    "WON": "WIN", "SHONE": "SHINE", "STRUCK": "STRIKE", "STRICKEN": "STRIKE",
    "STOLE": "STEAL", "STOLEN": "STEAL", "FELL": "FALL", "FELLEST": "FALL",
    "FALLEN": "FALL", "FORGAVE": "FORGIVE", "FORGIVEN": "FORGIVE",
    "FORSOOK": "FORSAKE", "FORSAKEN": "FORSAKE", "FOUND": "FIND",
    "FOUNDEST": "FIND", "GROUND": "GRIND", "BOUND": "BIND", "WOUND": "WIND",
    "HID": "HIDE", "HIDDEN": "HIDE", "BITTEN": "BITE", "BIT": "BITE",
    "SHOT": "SHOOT", "GOT": "GET", "GOTTEN": "GET", "GAT": "GET",
    "BESOUGHT": "BESEECH", "WROUGHT": "WORK", "LEFT": "LEAVE",
    "LOST": "LOSE", "PAID": "PAY", "LAID": "LAY", "LAIDST": "LAY",
    "SAID": "SAY", "HEARD": "HEAR", "HEARDEST": "HEAR", "MEANT": "MEAN",
    "FELT": "FEEL", "DEALT": "DEAL", "KNELT": "KNEEL", "DWELT": "DWELL",
    "SPILT": "SPILL", "SPAT": "SPIT", "CLAD": "CLOTHE", "SHOD": "SHOE",
    "WAS": "BE", "WAST": "BE", "WERT": "BE", "WERE": "BE", "BEEN": "BE",
    "AM": "BE", "IS": "BE", "ARE": "BE", "HAD": "HAVE", "HADST": "HAVE",
    "HAS": "HAVE", "HAST": "HAVE", "HAVING": "HAVE", "DID": "DO",
    "DONE": "DO", "DOES": "DO", "WOT": "WOT", "WIST": "WIST",
    "MEN": "MAN", "WOMEN": "WOMAN", "CHILDREN": "CHILD", "BRETHREN": "BROTHER",
    "KINE": "COW", "OXEN": "OX", "FEET": "FOOT", "TEETH": "TOOTH",
    "GEESE": "GOOSE", "MICE": "MOUSE", "LICE": "LOUSE", "DIED": "DIE",
    "DIETH": "DIE", "DYING": "DIE", "LIETH": "LIE", "LYING": "LIE",
    "SPUE": "SPEW", "SPUED": "SPEW", "MARISHES": "MARSH", "MARISH": "MARSH",
    "AGONE": "AGO", "HOISED": "HOISE", "STRAWED": "STREW",
    "THINE": "THINE", "UNTO": "UNTO", "WOE": "WO", "BEGAN": "BEGIN",
    "BEGUN": "BEGIN", "YOURSELVES": "YOURSELF", "OURSELVES": "OURSELF",
    "SELVES": "SELF", "WOLVES": "WOLF", "CALVES": "CALF", "HALVES": "HALF",
    "LOAVES": "LOAF", "LIVES": "LIFE", "WIVES": "WIFE", "KNIVES": "KNIFE",
    "THIEVES": "THIEF", "SHEAVES": "SHEAF", "LEAVES": "LEAF",
    "STAVES": "STAFF", "HOOVES": "HOOF",
}

VOWELS = set("AEIOU")


def candidates(word):
    """Yield lookup candidates, most specific first."""
    w = word
    yield w
    if w in IRREGULAR:
        yield IRREGULAR[w]
        return
    if w.endswith("'S"):
        yield w[:-2]
        w = w[:-2]
    elif w.endswith("S'"):
        yield w[:-1]
        w = w[:-1]
    for suffix in ("ETH", "EST", "ES", "ED", "ING", "S"):
        if not w.endswith(suffix) or len(w) <= len(suffix) + 1:
            continue
        stem = w[: -len(suffix)]
        if suffix in ("ETH", "EST", "ES", "ED") and stem.endswith("I"):
            yield stem[:-1] + "Y"          # carrieth/carried/carries -> carry
        yield stem                          # walketh -> walk
        yield stem + "E"                    # loveth -> love
        if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in VOWELS:
            yield stem[:-1]                 # sitteth/sinned -> sit/sin
    if w.endswith("LY") and len(w) > 4:
        yield w[:-2]


def resolve(word, dic):
    for c in candidates(word):
        if c in dic:
            return c
    return None


def main():
    dic = json.load(open(sys.argv[1], encoding="utf-8"))
    freq = collections.Counter()
    token = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
    margin = re.compile(r"\s*\{[^{}]*:[^{}]*\}")  # as BibleRepo.parseAsset
    for asset in ("en_kjv.json", "en_webster.json"):
        books = json.load(open(os.path.join(ASSETS, asset), encoding="utf-8"))
        for b in books[:66]:
            for ch in b["chapters"]:
                for v in ch:
                    v = margin.sub("", v).replace("{", "").replace("}", "")
                    for m in token.findall(v):
                        freq[m.upper().replace("’", "'")] += 1
    total = sum(freq.values())
    missed = collections.Counter()
    for w, n in freq.items():
        if resolve(w, dic) is None:
            missed[w] += n
    hit = total - sum(missed.values())
    print(f"tokens: {total}, resolved: {hit} ({100*hit/total:.2f}%), "
          f"distinct missed: {len(missed)}")
    print("top missed:")
    for w, n in missed.most_common(40):
        print(f"  {w}: {n}")


if __name__ == "__main__":
    main()
