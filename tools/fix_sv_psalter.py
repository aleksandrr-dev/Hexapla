# -*- coding: utf-8 -*-
"""Un-squeeze the Karl XII psalter to its native numbering (2026-09-25).

    python tools/fix_sv_psalter.py            # dry run (default): prints every split
    python tools/fix_sv_psalter.py --apply    # writes, with backups

The shipped sv_karlxii Psalms keep the print's title verses (v1 = title) but
were squeezed into the KJV's verse COUNTS by merging each titled psalm's last
KJV verses into its last slot (Ps 89:52 held KJV 51+52; Ps 51:19 held 17-19).
fix_sv_karlxii.py re-versified every other book in 2026-07 and never touched
the Psalms. Found by verse_embed_screen.py (shift control 67 %, every top run
in Psalms at v2..).

This splits each merged last slot back into its verses, so every titled psalm
has the native count (Luther's, which the 1703 psalter shares - checked by
reading 31 psalms where title/body could be confused). build_versemap.py then
maps it through psalm_title_runs like every other title-numbered psalter.

SPLITS: text from each marker onward starts the next verse. Proposed by
embedding each candidate cut against the KJV AND Luther's native verses, then
EVERY split read against the KJV; the seven marked «by hand» were wrong in
the proposal (the KJV boundary falls mid-sentence there).

The Swedish narration covers all 150 psalms, so the same split is applied to
  * audio_index_gen.json kxii book 18 offsets (a new offset 120 ms - the
    corpus median - before the new verse's first word, never before the
    previous word's end), and
  * the local narration/sv/18/<c>.json offsets and <c>.w.json word sidecars
    (the verse's word list split at the cut, char ranges rebased).
The archive.org copies of those sidecars are NOT touched here - upload them
separately. A phone with a cached OLD sidecar keeps word highlighting on every
verse but the new last one(s), which fall back to verse-level (bounds-guarded
in ReaderScreen; nothing can crash).

Refuses to run on an asset that is not in the squeezed state (idempotent), and
refuses to write a JSON file whose unchanged re-serialisation does not
reproduce the original bytes (so formatting can never drift).
"""
import argparse
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets")
SV = os.path.join(ASSETS, "bibles", "sv_karlxii.json")
KJV = os.path.join(ASSETS, "bibles", "en_kjv.json")
LUT = os.path.join(ASSETS, "bibles", "de_luther.json")
GEN = os.path.join(ASSETS, "audio_index_gen.json")
DATA = os.path.join(HERE, "..", "..", "Hexapla-releases")
NARR = os.path.join(DATA, "narration", "sv", "18")
BACKUP = os.path.join(DATA, "asset-backups")
TAG = "pre-psalter-2026-09-25"
LEAD_MS = 120

SPLITS = {
    3: ['När Herranom finner man'],
    4: ['Jag ligger och sofver'],
    5: ['Ty du, Herre, välsignar'],
    6: ['Alle mine fiender komme'],
    7: ['Jag tackar Herranom för'],
    8: ['Herre, vår Herre, huru'],
    9: ['Gif dem, Herre, en'],
    12: ['Ty det varder allestäds'],
    13: ['Jag vill sjunga Herranom,'],
    18: ['Den sinom Konung stor'],
    19: ['Låt dig täckas mins'],
    20: ['Hjelp, Herre; Konungen höre'],
    21: ['Herre, upphöj dig i'],
    22: ['De skola, komma och'],
    30: ['På det min ära'],
    31: ['Varer tröste och oförfärade,'],
    34: ['Herren förlöser sina tjenares'],
    36: ['Utan låt de ogerningsmän'],
    38: ['Skynda dig till att'],
    39: ['Håll upp af mig,'],
    40: ['Ty jag är fattig'],
    41: ['Lofvad vare Herren, Israels'],
    42: ['Hvad bedröfvar du dig,'],
    44: ['Statt upp, hjelp oss,'],
    45: ['Jag skall tänka uppå'],
    46: ['Herren Zebaoth är med'],
    47: ['Förstarne ibland folken äro'],
    48: ['Ty denne Guden är'],
    49: ['Korteliga: När en menniska'],
    51: ['Gör väl vid Zion,', 'Då skola dig behaga'],
    52: ['Men jag skall blifva', 'Jag tackar dig'],  # by hand
    53: ['Ack, att den hjelp'],
    54: ['Så vill jag göra', 'Ty du hjelper mig'],
    55: ['Men Gud, du skall'],
    56: ['Ty du hafver frälst'],
    57: ['Upphöj dig, Gud, öfver'],
    58: ['Att man skall säga:'],
    59: ['Jag vill lofsjunga dig,'],
    60: ['Skaffa oss bistånd', 'Med Gudi vilje'],  # by hand
    61: ['Så vill jag lofsjunga'],
    62: ['Och du, Herre, äst'],
    63: ['Men Konungen fröjdar'],  # by hand
    64: ['De rättfärdige skola fröjda'],
    65: ['Hjordmarken är full med'],
    67: ['Gud välsigne oss, och'],
    68: ['Gud är underlig i sinom'],  # by hand
    69: ['Och hans tjenares säd'],  # by hand
    70: ['Men jag är eländig'],
    75: ['Och vill sönderbryta allt'],
    76: ['Den der Förstomen borttager'],
    77: ['Du förde ditt folk,'],
    80: ['Herre Gud Zebaoth, tröst'],
    81: ['Och jag skulle spisa'],
    83: ['Så skola de förnimma,'],
    84: ['Herre Zebaoth, säll är'],
    85: ['Att rättfärdighet må ändå'],
    88: ['Du gör, att mina'],
    89: ['Lofvad vare Herren evinnerliga'],  # by hand
    92: ['Att de förkunna skola'],  # by hand
    102: ['Dina tjenares barn varda'],
    108: ['I Gudi vilje vi'],
    140: ['Och skola de rättfärdige'],
    142: ['För mina själ utu'],
}


def read(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    obj = json.loads(raw.decode("utf-8"))
    for style in ({"separators": (",", ":")}, {}, {"indent": 1}, {"indent": 2}):
        for ea in (False, True):
            if json.dumps(obj, ensure_ascii=ea, **style).encode("utf-8") == raw:
                return obj, dict(style, ensure_ascii=ea)
    raise SystemExit(f"REFUSE: cannot reproduce {path} byte-for-byte; would reformat it")


def write(path, obj, style, apply):
    if not apply:
        return
    os.makedirs(BACKUP, exist_ok=True)
    rel = os.path.relpath(path, os.path.join(HERE, "..", ".."))
    bak = os.path.join(BACKUP, rel.replace(os.sep, "__") + "." + TAG)
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(json.dumps(obj, **style).encode("utf-8"))
    os.replace(tmp, path)


def cuts_for(text, markers):
    cuts = []
    for m in markers:
        assert text.count(m) == 1, ("marker not unique", m)
        cuts.append(text.index(m))
    assert cuts == sorted(cuts) and cuts[0] > 0, cuts
    return cuts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    sv, sv_style = read(SV)
    kjv = json.load(open(KJV, encoding="utf-8"))
    lut = json.load(open(LUT, encoding="utf-8"))
    gen, gen_style = read(GEN)
    P, K, L = (b[18]["chapters"] for b in (sv, kjv, lut))
    G = gen["kxii"]["18"]["chapters"]

    # the squeezed state, exactly: every titled psalm at the KJV count
    for p, ms in SPLITS.items():
        c = p - 1
        if len(P[c]) != len(K[c]):
            raise SystemExit(f"REFUSE: Ps {p} has {len(P[c])} verses, KJV {len(K[c])} - "
                             "already un-squeezed?")
        if len(L[c]) - len(K[c]) != len(ms):
            raise SystemExit(f"Ps {p}: {len(ms)} markers but Luther has "
                             f"{len(L[c]) - len(K[c])} title verses")
    extra = [c + 1 for c in range(150) if len(L[c]) != len(K[c]) and c + 1 not in SPLITS]
    assert not extra, ("titled psalms without a split", extra)

    side_writes = []
    for p, ms in sorted(SPLITS.items()):
        c = p - 1
        text = P[c][-1]
        cuts = cuts_for(text, ms)
        b = [0] + cuts + [len(text)]
        parts = [text[b[i]:b[i + 1]].strip() for i in range(len(b) - 1)]
        starts = [b[i] + (len(text[b[i]:]) - len(text[b[i]:].lstrip())) for i in range(len(b) - 1)]

        side_path = os.path.join(NARR, f"{c}.w.json")
        off_path = os.path.join(NARR, f"{c}.json")
        side, side_style = read(side_path)
        loc, loc_style = read(off_path)
        o = G[str(c)]["o"]
        assert loc["offsets"] == o and len(o) == len(P[c]) == len(side["v"]), (p, "audio out of step")
        words = side["v"][-1]
        assert words, (p, "no word timings for the merged verse")
        groups = [[] for _ in parts]
        for w in words:
            k = max(i for i in range(len(parts)) if w[2] >= starts[i])
            groups[k].append([w[0], w[1], w[2] - starts[k], w[3] - starts[k]])
        new_o = []
        for k in range(1, len(parts)):
            assert groups[k] and groups[k - 1], (p, "empty word group", k)
            new_o.append(max(groups[k][0][0] - LEAD_MS, groups[k - 1][-1][1]))
        for k, g in enumerate(groups):
            for w in g:
                assert parts[k][w[2]:w[3]] == text[w[2] + starts[k]:w[3] + starts[k]], (p, k, w)

        print(f"Ps {p}: {len(P[c])} -> {len(P[c]) + len(ms)} verses")
        for k, part in enumerate(parts):
            at = o[-1] if k == 0 else new_o[k - 1]
            print(f"   v{len(P[c]) + k} @{at}ms  {part[:60]}{' ...' if len(part) > 60 else ''}")

        P[c][-1:] = parts
        o.extend(new_o)
        side["v"][-1:] = groups
        loc["offsets"] = list(o)
        side_writes += [(side_path, side, side_style), (off_path, loc, loc_style)]

    for c in range(150):
        assert len(P[c]) == len(L[c]) or len(L[c]) == len(K[c]), c + 1
    n = sum(len(ms) for ms in SPLITS.values())
    print(f"\n{len(SPLITS)} psalms, {n} verses restored; psalter {sum(map(len, K))} -> "
          f"{sum(map(len, P))} verses")
    if not a.apply:
        print("DRY RUN - nothing written. --apply to write (backups -> asset-backups/*." + TAG + ")")
        return
    write(SV, sv, sv_style, True)
    write(GEN, gen, gen_style, True)
    for path, obj, style in side_writes:
        write(path, obj, style, True)
    print(f"WROTE sv_karlxii.json, audio_index_gen.json, {len(side_writes)} narration files")


if __name__ == "__main__":
    main()
