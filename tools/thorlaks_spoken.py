# -*- coding: utf-8 -*-
"""Spoken form of a Thorlaksbiblia 1644 verse, for narration. 0 tokens.

    python tools/thorlaks_spoken.py --residue          # NT: what is left unexpanded
    python tools/thorlaks_spoken.py --verse 42 0 0     # book chapter verse, 0-indexed
    python tools/thorlaks_spoken.py --selftest

The asset is a DIPLOMATIC transcription: it keeps the printer's abbreviations
(z/⁊ = og, ñ = nn, hñ = hann, s̄ = sem, ū = um, ꝑ/ß = f ...). A TTS reads
those as letters or skips them, so narration needs the expanded word. This
module is the ONE place that expansion lives; the displayed text is never
touched (align_words maps spoken tokens back to the displayed ones).

⚠ v0, 2026-10-21. The word table is derived from the NT's own word counts
and verse contexts (John 1:3 «ß þ giorder» = fyrir það gjörðir; «so ē» =
svo sem; «þ̄ sig» = fyrir sig). Spelling is NOT modernised (Ord stays Ord,
Gude stays Gude): only abbreviations and type sorts are resolved. Whether
the 1644 spelling read as written is acceptable is an EAR question.
⛔ `--residue` is the gate: a word still carrying a mark after `spoken()` is
a word the TTS will mangle. Its count is the instrument, never a sample.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "is_thorlaks.json")

# Whole-word abbreviations (compared after NFC, case-folded on the first
# letter only; trailing punctuation is kept by the caller).
WORDS = {
    "z": "og", "⁊": "og", "j": "í",
    "ꝥ": "það", "þ": "það", "ꝥt": "það", "þt": "það", "ꝥta": "þetta",
    "ꝥr": "þeir", "þr": "þeir", "ꝥra": "þeirra", "þra": "þeirra",
    "ꝥre": "þeirre", "ꝥss": "þess", "ꝥsser": "þessir", "ꝥssu": "þessu",
    "ꝥssare": "þessare",
    "s̄": "sem", "sm̄": "sem", "sm̃": "sem", "s̃": "sem", "ʒ̄": "sem",
    "ē": "sem", "ẽ": "sem", "ā": "sem", "ã": "sem", "ō": "sem",
    "ꝑ": "fyrir", "þ̄": "fyrir", "ß": "fyrir",
    "hñ": "hann", "hn̄": "hann", "hn": "hann", "hñs": "hans", "hn̄s": "hans",
    "hns": "hans", "hm̄": "honum", "hm̃": "honum", "hm": "honum",
    "þm̄": "þeim", "þm̃": "þeim", "þm": "þeim",
    "mz": "með", "mʒ": "með",
    "v'": "var", "vʳ": "var", "v°": "var", "v^r": "var", "vʼr": "var",
    "þi'": "þier", "þi°": "þier", "þʼ": "það", "þ'": "það", "þ°": "það",
    "ept'": "epter", "ept°": "epter", "eptʳ": "epter", "ept^r": "epter",
    "fyr'": "fyrer", "fyr°": "fyrer",
    "vi'": "við", "vi°": "við", "mi'": "mig", "mi°": "mig",
    "yp'": "yfer", "ypʼ": "yfer", "yf'": "yfer", "all'": "aller",
    # the last five residue words, one each (2026-10-21, by verse context):
    # Rom 8:32 «gaf hñ ⁊t þ oss» (út), 1 Tim 6:20 «vardueit ꝥ·», Heb 9:11
    # «þ́ hñ sle», 2 Pet 1:18 «ꝥssa Raust», 1 John 2:18 «Antachristur kiem⁊»
    "⁊t": "út", "ꝥ·": "það", "þ́": "það", "ꝥssa": "þessa", "kiem⁊": "kiemur",
    # ★ VOWEL-LESS forms whose bar the transcription did not carry (2026-10-21).
    # The residue gate could not see them: no mark survives, yet the TTS
    # spells them out. Ruled by verse context, one line each:
    # s/sm Gen 1:7 «Votnum sm voru», 1:26 «Skridkuikendū s hrærast»; fm =
    # sm on the f-for-ſ pages (2 Cor 8:19 «fm þ off verdur»); þñ Gen 2:3
    # «blezade þñ, siounda Dag»; sk Gen 13:9 «þa sk eg ßara»; þv Matt 8:30
    # «Eñ þv v° langt burt», Mark 6:5; hr Matt 4:16 «z hr s satu», Luke 4:29,
    # John 1:19 «þa hr Judar sendu». Left as printed (ambiguous): ð, t, Mn, þ·.
    "s": "sem", "sm": "sem", "fm": "sem",
    "jñ": "inn", "jnn": "inn", "jn": "inn",
    "hñm": "honum", "hnm": "honum", "hnn": "hann",
    "þñ": "þann", "þss": "þess", "mñ": "menn", "kñ": "kann",
    "sk": "skal", "þv": "þar", "hr": "þeir",
    "va'": "var", "þr'": "þeir", "þeg'": "þegar",
    # a lone b / c is a marginal-reference sigil (Gen 21:31 «Stadur b
    # Bersaba», 32:2 «stad c Mahanaim»): not spoken
    "b": "", "c": "",
}

DATIVE = {"í", "i", "af", "frá", "fra", "hjá", "hia", "með", "med", "að", "ad", "mót", "mot", "úr", "vr", "ur"}

# Type sorts and marks inside a word.
SORTS = [
    ("ñ", "nn"), ("Ñ", "Nn"), ("ꝑ", "f"), ("ß", "f"), ("ſ", "s"),
    ("ꝛ", "ur"), ("ꝰ", "ur"), ("ʳ", "er"), ("œ", "æ"), ("Œ", "Æ"),
    ("ø", "ö"), ("Ø", "Ö"), ("ij", "í"), ("ꜳ", "á"), ("ʒ", "z"),
    # w is the 1644 sort for ú (Hws = hús, wt = út, Tialldbwd = tjaldbúð);
    # Piper reads a bare w as «v».
    ("w", "ú"), ("W", "Ú"),
]
# Vowel + nasal bar: final = vowel+m (ollū = ollum, kō = kom), medial before
# a vowel or b/p = +m, else +n (Gydingalāds = Gydingalands).
NASAL = {"ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u", "ũ": "u",
         "ã": "a", "ẽ": "e", "õ": "o", "ỹ": "y", "ȳ": "y"}
DROP = set("·•¶°^'ʼ()ªº…~+") | set("ᵃᵇᶜᵈᵉᵍᵛᶠⁿˢ")
MARK = re.compile(r"[ñÑꝑßſꝛꝰʳꝥ⁊ʒ·•°^'ʼªºᵃᵇᶜᵈᵉᵍᵛⁿˢ̀-ͯ"
                  + "".join(NASAL) + "]")


def _word(w):
    lead = re.match(r"^[(\[]*", w).group(0)
    m = re.match(r"^(.*?)([,.;:?!)\]•…]*)$", w[len(lead):])
    core, tail = m.group(1), m.group(2)
    key = core[:1].lower() + core[1:]
    key = key.replace("ʼ", "'")   # vaʼ / eptʼ are the v' / ept' keys
    if key in WORDS:
        rep = WORDS[key]
        if core[:1].isupper():
            rep = rep[:1].upper() + rep[1:]
        return rep + tail.replace("•", "")
    out = core
    for a, b in SORTS:
        out = out.replace(a, b)
    # combining macron/tilde on a consonant (hm̄, ßram̄) = doubled letter
    out = re.sub(r"([^\W\d_])[̄̃]",
                 lambda g: g.group(1) * 2 if g.group(1).lower() not in "aeiouy"
                 else g.group(1) + "n", out)
    chars = list(out)
    res = []
    for i, ch in enumerate(chars):
        if ch.lower() in NASAL or ch in NASAL:
            base = NASAL.get(ch.lower(), ch)
            base = base.upper() if ch.isupper() else base
            nxt = chars[i + 1].lower() if i + 1 < len(chars) else ""
            if not nxt or nxt in "aeiouyáéíóúæöbpm":
                res.append(base + "m")
            else:
                res.append(base + "n")
        else:
            res.append(ch)
    out = "".join(c for c in "".join(res) if c not in DROP)
    # u/v are one letter in 1644: initial V before a consonant is U (Vpphafe,
    # vtan, vm); Piper otherwise says «vaf-pavi» (Whisper, 2026-10-21).
    out = re.sub(r"^([Vv])(?=[^aeiouyáéíóúýæöAEIOUY\W])",
                 lambda g: "U" if g.group(1) == "V" else "u", out)
    # i/j likewise: initial j before a consonant is i (jllt = illt, jnn = inn)
    out = re.sub(r"^([Jj])(?=[^aeiouyáéíóúýæöAEIOUY\W])",
                 lambda g: "I" if g.group(1) == "J" else "i", out)
    out = unicodedata.normalize("NFC", re.sub(r"[̀-ͯ]", "", out)) \
        if re.search(r"[̄̃̆̇̌]", out) else out
    return out + tail.replace("•", "")


def spoken(verse):
    v = unicodedata.normalize("NFC", verse)
    v = re.sub(r"\s+", " ", v).strip()
    words = [_word(w) for w in v.split(" ")]
    # hñ after a dative preposition is «honum» (John 1:4 «J hñ var Lifid» =
    # Í honum var lífið). A heuristic: an ear question, not a ruling.
    for i in range(1, len(words)):
        if words[i] in ("hann", "Hann") and words[i - 1].lower() in DATIVE:
            words[i] = "honum"
    return re.sub(r"\s+", " ", " ".join(w for w in words if w)).strip()


def _nt():
    b = json.loads(ASSET.read_text(encoding="utf-8"))
    # Every book that holds verses (Genesis ships since s46), not just the NT.
    return b, [i for i, bk in enumerate(b)
               if any(v.strip() for ch in bk["chapters"] for v in ch)]


VOWEL = set("aeiouyáéíóúýæöAEIOUYÁÉÍÓÚÝÆÖ")


def residue():
    """⚠ Two classes, both counted: a surviving MARK, and a VOWEL-LESS word
    (sm, hñm, jñ - a bar the transcription lost leaves no mark at all, so
    the mark test alone passed 2,406 of them on 2026-10-21)."""
    b, nt = _nt()
    from collections import Counter
    left, nwords, nverses = Counter(), 0, 0
    for bi in nt:
        for ch in b[bi]["chapters"]:
            for v in ch:
                if not v.strip():
                    continue
                nverses += 1
                for w in spoken(v).split():
                    nwords += 1
                    core = re.sub(r"[^\w]", "", w)
                    if MARK.search(w) or (core and not set(core) & VOWEL):
                        left[w] += 1
    tot = sum(left.values())
    print(f"{len(nt)} books: {nverses} verses, {nwords} spoken words; {tot} words "
          f"({len(left)} distinct) carry a mark or no vowel "
          f"({100 * tot / max(nwords, 1):.2f} %)")
    for w, n in left.most_common(60):
        print(f"  {n:5d}  {w}")
    return 0 if nverses else 2


def selftest():
    cases = [
        ("I Vpphafe var Ord, og þad Ord var hia Gude, z Orded var Gud.",
         "I Upphafe var Ord, og þad Ord var hia Gude, og Orded var Gud."),
        ("Aller Hluter eru. ß þ giorder", "Aller Hluter eru. fyrir það giorder"),
        ("hñ gaf þm̄ Magt", "hann gaf þeim Magt"),
        ("ollū Bornū", "ollum Bornum"),
        ("so ē Saude", "so sem Saude"),
        ("Gydingalāds", "Gydingalands"),
        ("I Vpphafe vtan vm Vin", "I Upphafe utan um Vin"),
    ]
    bad = 0
    for src, want in cases:
        got = spoken(src)
        ok = got == want
        bad += not ok
        print(("ok  " if ok else "BAD ") + repr(got) + ("" if ok else f" != {want!r}"))
    # known-bad control: a raw verse must FAIL the residue mark test
    raw_marked = bool(MARK.search("hñ gaf þm̄"))
    print(("ok  " if raw_marked else "BAD ") + "control: raw abbreviations are seen by MARK")
    bad += not raw_marked
    return 1 if bad else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--residue", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verse", nargs=3, type=int)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.verse:
        b, _ = _nt()
        bi, ci, vi = a.verse
        v = b[bi]["chapters"][ci][vi]
        print(v)
        print(spoken(v))
        return 0
    return residue()


if __name__ == "__main__":
    sys.exit(main())
