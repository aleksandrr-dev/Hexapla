"""Diff a Þorláksbiblía 1644 text against the Guðbrandsbiblía 1584 WITNESS
(biblian.is, modernised spelling). 0 model tokens.

⛔ WITNESS ONLY: never a correction source, never shipped. Every flag is
settled by the page image. The 1644 is a revision of the 1584 (Resen), so a
disagreement is often a real edition difference, and the witness spells
modern Icelandic, so it can say which WORD is printed, never which sort
(ø, long-s, nasal bars are out of its reach by construction).

Both sides are folded to a consonant skeleton (abbreviations expanded,
accents/ð/y/j/v folded, vowels dropped after the first letter, doubles
collapsed), aligned per chapter, and each of our tokens is classed:
  MATCH  skeleton equal to its aligned witness token
  NEAR   1:1 substitution at skeleton edit distance 1 - a plausible misread
         (þar/far) OR a spelling revision; the class worth an image look
  OTHER  no aligned counterpart (revision, abbreviation, lost/added word)
Per verse it prints the MATCH rate; a verse far below the chapter's rate is
a question (garbled read, row shift, or a revised verse).

Input: any of the three formats - merged part / corpus (`## John 10`, `N
text`), stitched read (`## Cap. 10`, `N text — lineNN`), merge candidate.
Usage:
  thorlaks_witness_diff.py --book John --file research/_parts/john_p90.md [--near] [--low 0.5]
  thorlaks_witness_diff.py --selftest
"""
import difflib, glob, html, json, os, re, sys, unicodedata

WIT = "C:/Projects/Hexapla-releases/research/_witness/gudbrandsbiblia"
SLUG = {
    "Genesis": "fyrsta-mosebok", "Exodus": "onnur-mosebok", "Leviticus": "thridja-mosebok",
    "Numbers": "fjorda-mosebok", "Deuteronomy": "fimmta-mosebok", "Joshua": "josuabok",
    "Judges": "domarabokin", "Ruth": "rutarbok", "1 Samuel": "fyrri-samuelsbok",
    "2 Samuel": "sidari-samuelsbok", "1 Kings": "fyrri-konungabok", "2 Kings": "sidari-konungabok",
    "1 Chronicles": "fyrri-kronikubok", "2 Chronicles": "sidari-kronikubok", "Ezra": "esrabok",
    "Nehemiah": "nehemiabok", "Esther": "esterarbok", "Job": "jobsbok", "Psalms": "salmarnir",
    "Proverbs": "ordskvidirnir", "Ecclesiastes": "predikarinn", "Song of Solomon": "ljodaljodin",
    "Isaiah": "jesaja", "Jeremiah": "jeremia", "Lamentations": "harmljodin", "Ezekiel": "esekiel",
    "Daniel": "daniel", "Hosea": "hosea", "Joel": "joel", "Amos": "amos", "Obadiah": "obadia",
    "Jonah": "jonas", "Micah": "mika", "Nahum": "nahum", "Habakkuk": "habakkuk",
    "Zephaniah": "sefania", "Haggai": "haggai", "Zechariah": "sakaria", "Malachi": "malaki",
    "Judith": "juditarbok", "Tobit": "tobitsbok", "Wisdom": "speki-salomons", "Sirach": "siraksbok",
    "Baruch": "baruksbok", "1 Maccabees": "fyrsta-makkabeabok", "2 Maccabees": "onnur-makkabeabok",
    "Prayer of Manasseh": "baen-manasse",
    "Matthew": "matteusargudspjall", "Mark": "markusargudspjall", "Luke": "lukasargudspjall",
    "John": "johannesargudspjall", "Acts": "postulasagan", "Romans": "romverjabrefid",
    "1 Corinthians": "fyrra-korintubref", "2 Corinthians": "sidara-korintubref",
    "Galatians": "galatabrefid", "Ephesians": "efesusbrefid", "Philippians": "filippibrefid",
    "Colossians": "kolossubrefid", "1 Thessalonians": "fyrra-thessalonikubref",
    "2 Thessalonians": "sidara-thessalonikubref", "1 Timothy": "fyrra-timoteusarbref",
    "2 Timothy": "sidara-timoteusarbref", "Titus": "titusarbrefid", "Philemon": "filemonsbrefid",
    "Hebrews": "hebreabrefid", "James": "jakobsbrefid", "1 Peter": "fyrra-petursbref",
    "2 Peter": "sidara-petursbref", "1 John": "fyrsta-johannesarbref",
    "2 John": "annad-johannesarbref", "3 John": "thridja-johannesarbref", "Jude": "judasarbrefid",
    "Revelation": "opinberunarbok-johannesar",
}
# 1644 abbreviations spelled out before folding; standalone forms only
ABBR = {"z": "og", "s": "sem", "sm": "sem", "mz": "med", "hñ": "hann", "hn": "hann",
        "þr": "þeir", "þm": "þeim", "þra": "þeirra", "þt": "því að", "ß": "af",
        "β": "fyrir", "ꝑ": "fyrir", "hns": "hans", "hñs": "hans", "þß": "þess"}
WORD = re.compile(r"[^\W\d_]+", re.U)
# The 1584 witness cuts two OT books into a different number of chapters than
# the KJV. KJV chapter -> witness chapters, joined (2026-10-07, read off the
# chapter openings): 1 Chr w5 opens «Synir Símeon» = KJV 4:24, so w4+w5 = K4
# and w(n+1) = Kn after it; Hab w3 opens «En vínið prettar» = KJV 2:5, so
# w2+w3 = K2 and w4 = K3. Every other book: KJV n = witness n (word-count
# screen vs the KJV, shifted-Genesis control flags 10/49). Single chapters
# whose boundary differs by a few verses (Isa 15, 63/64, Ezek 2, Dan 12,
# Hos 6) are NOT remapped: diff those at verse level.
CHAPTER_MAP = {
    "1 Chronicles": {k: ([4, 5] if k == 4 else [k] if k < 4 else [k + 1]) for k in range(1, 30)},
    "Habakkuk": {1: [1], 2: [2, 3], 3: [4]},
}


def witness(book):
    raw = _witness_raw(book)
    cmap = CHAPTER_MAP.get(book)
    if not cmap:
        return raw
    return {k: " ".join(raw[w] for w in ws) for k, ws in cmap.items()}


def _witness_raw(book):
    slug = SLUG[book]
    out = {}
    for f in sorted(glob.glob(os.path.join(WIT, "pages_*.json"))):
        for r in json.load(open(f, encoding="utf-8")):
            m = re.match(re.escape(slug) + r"-(\d+)-kafli$", r["slug"])
            if not m:
                continue
            h = r["content"]["rendered"]
            h = re.sub(r"<span[^>]*>.*?</span>", " ", h, flags=re.S)  # note keys
            h = re.sub(r"<p>\s*[IVXLC]+\.\s*</p>", " ", h)  # roman chapter head
            t = html.unescape(re.sub(r"<[^>]+>", " ", h))
            out[int(m.group(1))] = t
    if not out:
        raise SystemExit("no witness chapters for %s (slug %s) - fetched?" % (book, slug))
    return out


def ours(path):
    """{chapter: [(verse, text)]} from a part, corpus, stitched read or candidate."""
    ch, out = None, {}
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\n")
        m = re.match(r"^## (?:Cap\.|[1-3]?\s?[A-Za-z ]+?) (\d+)\s*$", ln)
        if m:
            ch = int(m.group(1))
            out.setdefault(ch, [])
            continue
        m = re.match(r"^(\d+) (.*)$", ln)
        if m and ch is not None:
            t = re.sub(r"\s+—\s+line\S+\s*$", "", m.group(2))
            out[ch].append((int(m.group(1)), t))
    return out


def toks(text):
    """Our tokens with their display form; bracket tags reduced to their letter."""
    text = re.sub(r"\[ornate initial: ?([^\]]*)\]", r"\1", text)
    text = text.replace("[HN]", "H").replace("[?]", "")
    text = re.sub(r"\[[^\]]*\]", " ", text)
    return [w for w in re.split(r"[\s/]+", text) if WORD.search(w)]


def skel(w, old):
    w = w.lower().strip(".,:;?!()'\"„“”‘’")
    if old:
        if w in ABBR:
            w = ABBR[w]
        w = (w.replace("ñ", "nn").replace("ū", "um").replace("ü", "um").replace("ā", "am").replace("ō", "om")
             .replace("ē", "em").replace("ʳ", "r").replace("'", "er"))
    w = w.replace("ð", "d").replace("æ", "ae").replace("ø", "o").replace("ö", "o")
    w = w.replace("ß", "s").replace("ſ", "s")
    w = "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))
    w = w.replace("ij", "i").replace("ck", "k").replace("c", "k").replace("pt", "ft")
    w = re.sub(r"(?<=.)z", "s", w)
    w = w.translate(str.maketrans("wvjyq", "uuiik"))
    w = "".join(c for c in w if c.isalpha())
    if not w:
        return ""
    s = w[0] + re.sub(r"[aeiou]", "", w[1:])
    return re.sub(r"(.)\1+", r"\1", s)


def lev1(a, b):
    """Levenshtein distance exactly 1."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:k] + l[k + 1:] == s for k in range(len(l)))


def classify(book, path):
    """-> list of (ch, verse, token_index, token, cls, witness_token)."""
    wit, our = witness(book), ours(path)
    rows = []
    for ch, verses in sorted(our.items()):
        if ch not in wit:
            continue
        wt = [w for w in re.split(r"\s+", wit[ch]) if WORD.search(w)]
        ws = [skel(w, False) for w in wt]
        flat = [(v, i, t) for v, text in verses for i, t in enumerate(toks(text))]
        os_ = [skel(t, True) for v, i, t in flat]
        # restrict the witness window to the span our verses cover
        sm = difflib.SequenceMatcher(a=os_, b=ws, autojunk=False)
        ops = sm.get_opcodes()
        start = len(rows)
        for n_op, (op, i1, i2, j1, j2) in enumerate(ops):
            # a SMALL disagreement with matching text on both sides is a
            # misread/loss/dittography suspect; a long one is a 1644 revision
            ctx = (n_op == 0 or ops[n_op - 1][0] == "equal") and \
                  (n_op == len(ops) - 1 or ops[n_op + 1][0] == "equal")
            small = ctx and (i2 - i1) <= 2 and (j2 - j1) <= 2
            if op == "insert" and small and i1 > 0:
                # the witness has 1-2 words we lack: a LOST word, charged to the token before
                c0 = rows[start + i1 - 1] if start + i1 - 1 < len(rows) else None
                if c0 and c0[4] == "MATCH":
                    rows[start + i1 - 1] = c0[:4] + ("GAP", " ".join(wt[j1:j2]))
            for k in range(i1, i2):
                v, i, t = flat[k]
                if op == "equal":
                    rows.append((ch, v, i, t, "MATCH", wt[j1 + k - i1]))
                elif op == "replace" and i2 - i1 == j2 - j1:
                    w = wt[j1 + k - i1]
                    a, b = os_[k], ws[j1 + k - i1]
                    near = len(a) >= 2 and len(b) >= 2 and t.lower() not in ABBR and lev1(a, b)
                    rows.append((ch, v, i, t, "NEAR" if near else ("ISO" if small else "OTHER"), w))
                elif op == "delete" and small:
                    rows.append((ch, v, i, t, "EXTRA", ""))  # ours only: dittography/seam dup suspect
                else:
                    rows.append((ch, v, i, t, "ISO" if small else "OTHER", " ".join(wt[j1:j2])))
        # a token repeating its predecessor is a dittography suspect (genuine doublets exempt)
        for k in range(start + 1, len(rows)):
            a, b = rows[k - 1], rows[k]
            if skel(a[3], True) == skel(b[3], True) and len(skel(b[3], True)) >= 2 and \
                    skel(b[3], True) not in DOUBLETS and b[4] in ("MATCH", "OTHER"):
                rows[k] = b[:4] + ("DUP", b[5])
    return rows


# repeats the print really has (Verily verily, my God my God) - never a DUP flag
DOUBLETS = {"snlg", "gd", "mn"}
FLAG = ("NEAR", "ISO", "GAP", "EXTRA", "DUP")


def selftest():
    ok = True
    for a, b, want in [("Sañlega", "Sannlega", True), ("seige", "segi", True), ("geingur", "gengur", True),
                       ("hñ", "hann", True), ("epter", "eftir", True), ("Dyrnar/", "dyrnar", True),
                       ("þar", "far", False), ("fære", "þære", False)]:
        got = skel(a.strip("/"), True) == skel(b, False)
        ok &= got == want
        print("%-10s %-10s skel %s/%s equal=%s want %s" % (a, b, skel(a, True), skel(b, False), got, want))
    ok &= lev1("þr", "fr") and not lev1("þr", "þr")
    print("selftest", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    book = sys.argv[sys.argv.index("--book") + 1]
    path = sys.argv[sys.argv.index("--file") + 1]
    low = float(sys.argv[sys.argv.index("--low") + 1]) if "--low" in sys.argv else 0.5
    rows = classify(book, path)
    if not rows:
        print("no tokens aligned - wrong book or empty file")
        sys.exit(2)
    per = {}
    for ch, v, i, t, c, w in rows:
        per.setdefault((ch, v), []).append(c)
    n = len(rows)
    m = sum(1 for r in rows if r[4] == "MATCH")
    near = [r for r in rows if r[4] == "NEAR"]
    print("# %s vs Guðbrandsbiblía 1584: %d tokens, MATCH %.1f %%, NEAR %d, OTHER %d" % (
        os.path.basename(path), n, 100.0 * m / n, len(near), n - m - len(near)))
    for (ch, v), cs in sorted(per.items()):
        r = cs.count("MATCH") / float(len(cs))
        if r < low:
            print("LOW   %d:%d  match %.0f %% of %d tokens" % (ch, v, 100 * r, len(cs)))
    if "--near" in sys.argv:
        for ch, v, i, t, c, w in near:
            print("NEAR  %d:%d  #%d  %s  ~ %s" % (ch, v, i, t, w))
