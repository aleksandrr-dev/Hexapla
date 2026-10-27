"""Resolve the `[HN]` (H-or-N capital) sites of the Þorláksbiblía 1644 NT
transcription against the Guðbrandsbiblía 1584 WITNESS. 0 model tokens.

Owner ruling 2026-10-07: «Use a witness to determine the H/N». The 1584 text
(biblian.is, modernised spelling; research/_witness/gudbrandsbiblia, fetched
by fetch_gudbrandsbiblia_witness.py) is authorised as the decider for H/N
ONLY - no other letter is ever taken from it.

Read-only over research/; writes only the output table.

Verse addressing: the witness has NO verse numbers (one HTML page per
chapter). Each of our chapters is aligned to its witness chapter on the
consonant skeleton of thorlaks_witness_diff.py (difflib), with every [HN]
token given a unique never-matching skeleton so the alignment cannot lean to
either letter. A verse's witness span = min..max witness index of its aligned
tokens (+-2 tokens pad); a verse with no aligned token takes the gap between
its neighbours. Alignment is positional, so a misprinted or shifted verse
numeral (2 Cor 1/2, Heb 4/5) does not move the span.

Decision per site `prefix[HN]rest` ([?] in rest = one wildcard letter):
  1. witness words in the verse's span matching prefix+H+rest or
     prefix+N+rest (normalised: lowercase, accents off, ð->d, æ->ae, ø/ö->o,
     ſ->s, ij/y/j->i, v/w->u, z->s after the first letter, doubles collapsed;
     a nasal bar or macron on a vowel/n = that letter, +m or +n; 1644
     abbreviations hñ/hn/hns/hñs expanded); edit distance <= 1 when rest has
     >= 4 letters, else 0; the initial letter must agree exactly.
     If none in the verse, the spans of the verses -1 and +1 are searched.
     (E1, a verse +-2 fallback, was DROPPED 2026-10-07 by Fable ruling: its control failed,
     --control-shift 5 WITNESS 202 -> 264.)
     E2 (ON by default 2026-10-08; off switch HEXAPLA_NO_E2=1): 1644 ie ~ modern
     e-acute (hier = her), folded in norm(wit=True) ONLY for the witness comparison in
     matches() (1584 words, and the 1644 head/candidates compared with them), never in the
     CORPUS counts (Fable ruling 2026-10-07 fix b).
     All matches one letter -> WITNESS; both letters -> UNRESOLVED.
  2. no witness match -> CORPUS when exactly one of the two readings is an
     attested word elsewhere in our 27 books with a plain (unbracketed)
     letter; the other not.
  3. otherwise UNRESOLVED.
  4. PINNED (F2, Fable ruling s44 2026-10-20, _work/_scratch/s44_fable/ADVISOR_RULING.md):
     research/_evidence/thorlaks_hn_pins.tsv (same 8 columns, basis PINNED) is applied
     AFTER decide(). A pin applies ONLY to a row that is UNRESOLVED with the identical
     token; a pin whose site/token is absent, or whose row the instrument now decides
     itself, DIES (exit 3, nothing written) - never silently. Pins record in-word-look
     fills of our own `[?]` whose WITNESS word identification predates the fill; a
     CORPUS-basis fill is never pinned. Not applied under --control-shift.

Usage:
  thorlaks_hn_witness.py                    # writes the TSV + summary
  thorlaks_hn_witness.py --control-shift 5  # known-bad: span of verse v+5; writes nothing
  thorlaks_hn_witness.py --selftest
"""
import difflib, os, random, re, sys, unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_witness_diff as twd  # noqa: E402

RES = "C:/Projects/Hexapla-releases/research"
OUT = RES + "/_evidence/thorlaks_hn_witness_2026-10-07.tsv"
PINS = RES + "/_evidence/thorlaks_hn_pins.tsv"
HEADER = "book\tchapter\tverse\toccurrence_index_in_verse\ttoken\tletter\tbasis\twitness_word_or_count"
BOOKS = [("Matthew", "matthew"), ("Mark", "mark"), ("Luke", "luke"), ("John", "john"),
         ("Acts", "acts"), ("Romans", "romans"), ("1 Corinthians", "1corinthians"),
         ("2 Corinthians", "2cor"), ("Galatians", "galatians"), ("Ephesians", "ephesians"),
         ("Philippians", "philippians"), ("Colossians", "colossians"),
         ("1 Thessalonians", "1thessalonians"), ("2 Thessalonians", "2thessalonians"),
         ("1 Timothy", "1timothy"), ("2 Timothy", "2timothy"), ("Titus", "titus"),
         ("Philemon", "philemon"), ("Hebrews", "hebrews"), ("James", "james"),
         ("1 Peter", "1peter"), ("2 Peter", "2peter"), ("1 John", "1john"), ("2 John", "2john"),
         ("3 John", "3john"), ("Jude", "jude"), ("Revelation", "revelation")]
# OT books join when their thorlaks_<slug>.md exists (Genesis from p16, 2026-10-07); the witness diff's CHAPTER_MAP
# covers the 1584 chapter cuts. A missing file is skipped, never an error.
# F5 (Fable ruling s44, 2026-10-20): Exodus joins the same way (exists-guarded).
BOOKS += [(b, s) for b, s in [("Genesis", "genesis"), ("Exodus", "exodus")]
          if os.path.exists(os.path.join(RES, "thorlaks_%s.md" % s))]
L = r"[^\W\d_]"
SITE = re.compile(r"((?:%s|\[\?\])*)\[HN\]((?:%s|\[\?\])*)" % (L, L), re.U)
# E1 (verse +-2 fallback) was DROPPED 2026-10-07 by Fable ruling (control failed: shift 5 WITNESS 202 -> 264).
# E2 (ie ~ e-acute) is ON by default since 2026-10-08 (owner-delegated Fable ruling, _work/_scratch/owner_queue_ruling/
# ADVISOR_RULING.md X1): the 2026-10-07 'unchanged' bar was unmeetable by any extension that adds a matchable class;
# the amended control is 0 flips of existing WITNESS rows AND the new class's chance rate under --control-shift 5 <=
# the baseline chance rate. Off switch: bare `HEXAPLA_NO_E2=1 python ...`. Fable fix (b): the fold runs only for the
# witness comparison (norm(w, wit=True) in matches()), never in the CORPUS keys, where 1644 ie and e are different sorts
# (it had merged hier/her, nie/ne, hiellu/hellum). Evidence: _work/_scratch/e1e2/.
NO_E2 = os.environ.get("HEXAPLA_NO_E2") == "1"
ABBR = {"hñ": "hann", "hn": "hann", "hns": "hans", "hñs": "hans"}
WILD = "?"
NASAL = {"ñ": "n", "ū": "u", "ā": "a", "ē": "e", "ō": "o", "ī": "i", "ũ": "u", "õ": "o", "ẽ": "e", "ã": "a"}


def ornate(text):
    # an unread woodcut (`?`) is a WILDCARD prefix letter, never nothing: a bare `?` fell out of SITE and
    # `[ornate initial: ?][HN]n` scored as the abbreviation hn=hann (Acts 22:22, 24:1, 24:10 shipped «·Hn»)
    return re.sub(r"\[ornate initial: ?([^\]]*)\]", lambda m: "[?]" if m.group(1) == "?" else m.group(1), text)


def norm(w, wit=False):
    """One normalised string; `?` (wildcard) survives. wit=True: witness comparison (E2 fold allowed)."""
    w = w.lower()
    w = w.replace("ð", "d").replace("æ", "ae").replace("ø", "o").replace("ö", "o")
    # F1 (Fable ruling s44, 2026-10-20): in this corpus ß is the tailed f-position sort (conventions rows 13/19),
    # so it folds to f, never s: «[HN]oßdingia» must meet 1584 «höfðingja». Folding to s lost 5 NT sites.
    w = w.replace("ſ", "s").replace("ß", "f")
    w = "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))
    w = w.replace("ij", "i")
    if wit and not NO_E2:  # E2: 1644 ie ~ modern e-acute (hier/thier/mier = her/ther/mer); witness comparison only
        w = w.replace("ie", "e")
    w = w.translate(str.maketrans("yjvw", "iiuu"))
    w = w[:1] + w[1:].replace("z", "s")
    w = "".join(c for c in w if c.isalpha() or c == WILD)
    w = re.sub(r"([^?])\1+", r"\1", w)
    return w.replace("uo", "ue")  # 1644 huor/huort ~ modern hver/hvert (both sides)


def variants(w, wit=False):
    """Our 1644 form -> set of normalised readings (nasal bars expanded)."""
    w = unicodedata.normalize("NFC", w.replace("[?]", WILD))
    parts = [""]
    chars = unicodedata.normalize("NFD", w)
    i = 0
    while i < len(chars):
        c = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        pre = unicodedata.normalize("NFC", c + nxt) if nxt in ("\u0303", "\u0304") else None
        if pre is not None:
            base = NASAL.get(pre, c)
            alts = [base, base + "m", base + "n"] if base != "n" else ["n", "nn"]
            i += 2
        else:
            alts = [c]
            i += 1
        parts = [p + a for p in parts for a in alts][:64]
    out = {norm(p, wit) for p in parts}
    lw = w.lower()
    if lw in ABBR:
        out.add(norm(ABBR[lw], wit))
    return out


def dist(a, b, cap=2):
    """Levenshtein with `?` in a matching any letter; returns min(d, cap)."""
    if abs(len(a) - len(b)) >= cap:
        return cap
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if ca == cb or ca == WILD else 1))
        prev = cur
    return min(prev[-1], cap)


def cons_eq(a, b):
    """Consonant skeletons equal (`?` matches any letter)."""
    a, b = re.sub(r"[aeiou]", "", a), re.sub(r"[aeiou]", "", b)
    return len(a) == len(b) and all(x == y or x == WILD for x, y in zip(a, b))


def nletters(rest):
    return len(re.findall(L + r"|\[\?\]", rest))


def matches(prefix, rest, words):
    """-> {letter: [witness words]} over `words` (raw witness tokens)."""
    # Edit distance 1 only for rest >= 4 letters, and (tightened after the
    # --control-shift run, where [HN]erra ~ nema and [HN]afns ~ hans got
    # through) only when the consonant skeletons agree: the 1644 -> modern
    # drift is in vowels (himen/himin), never a consonant.
    thr = 1 if nletters(rest) >= 4 else 0
    got = defaultdict(list)
    for letter in "HN":
        cands = variants(prefix + letter.lower() + rest, True)
        head = norm(prefix + letter.lower(), True)
        for w in words:
            nw = norm(w, True)
            if len(nw) < len(head) or any(h != c and h != WILD for h, c in zip(head, nw)):
                continue  # wildcard-aware startswith (an unread woodcut prefix is `?`)
            if any(dist(c, nw) == 0 or (thr and dist(c, nw) <= 1 and cons_eq(c, nw)) for c in cands):
                got[letter].append(w.strip(".,:;?!()'\"„“”‘’"))
    return got


def corpus_count(prefix, rest, letter, corpus):
    cands = variants(prefix + letter.lower() + rest)
    n = 0
    for c in cands:
        if WILD in c:
            rx = re.compile("^" + re.escape(c).replace(re.escape(WILD), ".") + "$")
            n += sum(v for k, v in corpus.items() if len(k) == len(c) and rx.match(k))
        else:
            n += corpus.get(c, 0)
    return n


def decide(prefix, rest, verse_words, adj_words, corpus):
    """-> (letter, basis, evidence)."""
    for words in (verse_words, adj_words):
        m = matches(prefix, rest, words)
        if m:
            if len(m) == 1:
                letter = next(iter(m))
                return letter, "WITNESS", ",".join(sorted(set(m[letter])))
            return "", "UNRESOLVED", "conflict H:%s N:%s" % (",".join(sorted(set(m["H"]))),
                                                            ",".join(sorted(set(m["N"]))))
    h, n = corpus_count(prefix, rest, "H", corpus), corpus_count(prefix, rest, "N", corpus)
    if (h > 0) != (n > 0):
        return ("H" if h else "N"), "CORPUS", "H=%d N=%d" % (h, n)
    return "", "UNRESOLVED", "no witness match; corpus H=%d N=%d" % (h, n)


def read_book(slug, book):
    """{ch: [(verse, text)]} in print order; text before `## <Book> 1` ignored."""
    p = os.path.join(RES, "thorlaks_%s.md" % slug)
    out, ch, started = {}, None, False
    hdr = re.compile(r"^## %s (\d+)\s*$" % re.escape(book))
    for ln in open(p, encoding="utf-8"):
        ln = ln.rstrip("\n")
        m = hdr.match(ln)
        if m:
            if int(m.group(1)) == 1:
                started = True
            if started:
                ch = int(m.group(1))
                out.setdefault(ch, [])
            continue
        if ln.startswith("## "):
            ch = None
        m = re.match(r"^(\d+) (.*)$", ln)
        if m and started and ch is not None:
            out[ch].append((int(m.group(1)), m.group(2)))
    return out


def tokens(text):
    """Alignment tokens; any token with [HN] gets a unique non-matching skeleton."""
    text = ornate(text)
    toks = []
    for w in re.split(r"[\s/]+", text):
        if "[HN]" in w:
            toks.append(None)
            continue
        w2 = re.sub(r"\[[^\]]*\]", "", w)
        if twd.WORD.search(w2):
            toks.append(twd.skel(w2, True))
    return toks


def spans(verses, wit_text):
    wt = [w for w in re.split(r"\s+", wit_text) if twd.WORD.search(w)]
    ws = [twd.skel(w, False) for w in wt]
    flat, owner = [], []
    for k, (v, text) in enumerate(verses):
        for s in tokens(text):
            flat.append(s if s is not None else "\x00%d" % len(flat))
            owner.append(k)
    pos = defaultdict(list)
    sm = difflib.SequenceMatcher(a=flat, b=ws, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for d in range(i2 - i1):
                pos[owner[i1 + d]].append(j1 + d)
    n = len(verses)
    lo, hi = [None] * n, [None] * n
    for k in range(n):
        if pos[k]:
            lo[k], hi[k] = min(pos[k]), max(pos[k])
    for k in range(n):  # fill unaligned verses from neighbours
        if lo[k] is None:
            a = max([hi[x] for x in range(k) if hi[x] is not None] or [-1]) + 1
            b = min([lo[x] for x in range(k + 1, n) if lo[x] is not None] or [len(wt)]) - 1
            lo[k], hi[k] = a, max(a, b)
    return wt, [(max(0, lo[k] - 2), min(len(wt), hi[k] + 3)) for k in range(n)]


def build_corpus(books):
    c = Counter()
    for _, verses in books:
        for vs in verses.values():
            for _, text in vs:
                for w in re.split(r"[\s/·]+", ornate(text)):
                    if "[" in w:
                        continue
                    w = w.strip(".,:;?!()'\"„“”‘’")
                    if w and re.fullmatch(r"%s+" % L, w):
                        for v in variants(w):
                            c[v] += 1
    return c


def run(shift):
    books = [(b, read_book(s, b)) for b, s in BOOKS]
    corpus = build_corpus(books)
    rows, cover = [], []
    for book, verses in books:
        try:
            wit = twd.witness(book)
        except SystemExit:
            wit = {}
        cover.append((book, len(verses), sum(1 for c in verses if c in wit)))
        for ch, vs in sorted(verses.items()):
            if not any("[HN]" in t for _, t in vs):
                continue
            if ch in wit:
                wt, sp = spans(vs, wit[ch])
            else:
                wt, sp = [], [(0, 0)] * len(vs)
            for k, (v, text) in enumerate(vs):
                kk = k + shift
                win = (lambda x: wt[sp[x][0]:sp[x][1]] if 0 <= x < len(sp) else [])
                own = win(kk)
                adj = win(kk - 1) + win(kk + 1)
                for occ, m in enumerate(SITE.finditer(ornate(text))):
                    letter, basis, ev = decide(m.group(1), m.group(2), own, adj, corpus)
                    rows.append((book, ch, v, occ, m.group(0), letter, basis, ev))
    return rows, cover


def load_pins(path):
    """-> {(book, ch, v, occ): (token, letter, evidence)}; {} when the file is absent; dies on a bad row."""
    if not os.path.exists(path):
        return {}
    lines = open(path, encoding="utf-8").read().split("\n")
    if lines[0].rstrip("\r") != HEADER:
        sys.exit("DIE: %s: unexpected header %r" % (path, lines[0]))
    pins = {}
    for i, ln in enumerate(lines[1:], 2):
        if not ln.strip():
            continue
        f = ln.rstrip("\r").split("\t")
        if len(f) != 8 or f[6] != "PINNED" or f[5] not in ("H", "N") or "[HN]" not in f[4]:
            sys.exit("DIE: %s:%d: bad pin row %r" % (path, i, f))
        key = (f[0], int(f[1]), int(f[2]), int(f[3]))
        if key in pins:
            sys.exit("DIE: %s:%d: duplicate pin %s" % (path, i, key))
        pins[key] = (f[4], f[5], f[7])
    return pins


def apply_pins(rows, pins):
    """F2: -> (rows, problems). A pin lands only on an UNRESOLVED row with the identical token;
    an absent site, a stale token, or a row the instrument decides itself is a problem (caller DIES)."""
    idx = {(r[0], r[1], r[2], r[3]): i for i, r in enumerate(rows)}
    rows, problems = list(rows), []
    for key, (tok, letter, ev) in sorted(pins.items()):
        where = "%s %d:%d occ %d" % key
        i = idx.get(key)
        if i is None:
            problems.append("%s: pinned site %r absent from the text" % (where, tok))
            continue
        r = rows[i]
        if r[4] != tok:
            problems.append("%s: stale pin token %r != text %r" % (where, tok, r[4]))
        elif r[6] != "UNRESOLVED":
            problems.append("%s: %r is decided by the instrument itself (%s %s: %s) - the pin is dead"
                            % (where, tok, r[5], r[6], r[7]))
        else:
            rows[i] = r[:5] + (letter, "PINNED", ev)
    return rows, problems


def report(rows, cover, write):
    print("witness coverage (our chapters with a witness chapter):")
    print("  " + "; ".join("%s %d/%d" % (b, w, n) for b, n, w in cover))
    per = defaultdict(Counter)
    for r in rows:
        per[r[0]][r[6]] += 1
    tot = Counter(r[6] for r in rows)
    print("sites %d  WITNESS %d  CORPUS %d  PINNED %d  UNRESOLVED %d" % (
        len(rows), tot["WITNESS"], tot["CORPUS"], tot["PINNED"], tot["UNRESOLVED"]))
    for b, c in per.items():
        print("  %-12s WITNESS %4d  CORPUS %4d  PINNED %2d  UNRESOLVED %4d  (H %d / N %d)" % (
            b, c["WITNESS"], c["CORPUS"], c["PINNED"], c["UNRESOLVED"],
            sum(1 for r in rows if r[0] == b and r[5] == "H"),
            sum(1 for r in rows if r[0] == b and r[5] == "N")))
    if write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(HEADER + "\n")
            for r in rows:
                f.write("\t".join(str(x) for x in r) + "\n")
        print("wrote", OUT, len(rows), "rows")
        rnd = random.Random(7)
        for basis, n in (("WITNESS", 15), ("CORPUS", 10)):
            pool = [r for r in rows if r[6] == basis]
            print("-- %d random %s rows" % (min(n, len(pool)), basis))
            for r in rnd.sample(pool, min(n, len(pool))):
                print("  %s %d:%d #%d  %-14s -> %s  (%s)" % (r[0], r[1], r[2], r[3], r[4], r[5], r[7]))


def selftest():
    corpus = Counter({"hiarta": 9, "hialp": 0})
    for v in variants("Heidinge"):
        corpus[v] += 3
    verse = "Og hann sagði: Náð sé með yður, hvað segir þú; Heilagur, nú".split()
    cases = [
        # (prefix, rest, verse words, adjacent words, want letter, want basis)
        ("", "añ", verse, [], "H", "WITNESS"),           # clear H: hann
        ("", "aad", verse, [], "N", "WITNESS"),          # clear N: Náð
        ("", "u", "nú hú".split(), [], "", "UNRESOLVED"),  # conflicting witness
        ("", "eidinge", ["annað"], [], "H", "CORPUS"),    # corpus fallback
        ("", "xyzq", verse, [], "", "UNRESOLVED"),       # no match anywhere
        ("", "u[?]d", verse, [], "H", "WITNESS"),        # wildcard: hv?d ~ hvað
        ("", "oßdingia", ["höfðingja"], [], "H", "WITNESS"),    # F1: ß = f-sort (failed while ß folded to s)
        ("", "oßdingia", ["hósdingja"], [], "", "UNRESOLVED"),  # F1 negative: an s-word must not meet ß
    ]
    ok = True
    resolved = 0
    for p, r, vw, aw, wl, wb in cases:
        got = decide(p, r, vw, aw, corpus)
        good = got[0] == wl and got[1] == wb
        ok &= good
        resolved += got[1] != "UNRESOLVED"
        print("%-10s -> %-1s %-10s %-30s %s" % (p + "[HN]" + r, got[0], got[1], got[2], "ok" if good else "FAIL"))
    # adjacent-verse fallback and the initial-letter guard
    ok &= decide("", "uad", ["og"], ["hvað"], corpus)[1] == "WITNESS"
    ok &= not matches("", "ann", ["mann"])
    # an unread woodcut before [HN]n is a wildcard letter, not the hn=hann abbreviation (failed before the ornate fix)
    m = SITE.search(ornate("1 [ornate initial: ?][HN]n Paall"))
    ok &= bool(m) and decide(m.group(1), m.group(2), ["En"], [], corpus)[0] == "N"
    ok &= bool(m) and decide(m.group(1), m.group(2), ["hann"], [], corpus)[1] == "UNRESOLVED"
    # E2: [HN]ier ~ Her -> H, vs an "En" span -> UNRESOLVED
    ok &= (decide("", "ier", ["Hér"], [], corpus)[:2] == (("", "UNRESOLVED") if NO_E2 else ("H", "WITNESS")))
    ok &= decide("", "ier", ["En"], [], corpus)[1] == "UNRESOLVED"
    # F2 pins: on an UNRESOLVED row -> letter; on a row the instrument decides -> DIE; stale token -> DIE;
    # absent site -> DIE
    rows = [("Acts", 27, 34, 1, "[HN]opde", "", "UNRESOLVED", "no witness match"),
            ("Acts", 27, 34, 0, "[HN]aar", "N", "WITNESS", "nær")]
    pin_ev = "inword3 WITNESS höfði; [?] filled by in-word look"
    got, pr = apply_pins(rows, {("Acts", 27, 34, 1): ("[HN]opde", "H", pin_ev)})
    good = not pr and got[0][5:7] == ("H", "PINNED") and got[1] == rows[1]
    print("pin on UNRESOLVED -> letter      ", "ok" if good else "FAIL %r %r" % (got[0], pr)); ok &= good
    _, pr = apply_pins(rows, {("Acts", 27, 34, 0): ("[HN]aar", "H", pin_ev)})
    good = len(pr) == 1 and "decided by the instrument" in pr[0]
    print("pin on WITNESS row -> DIE        ", "ok" if good else "FAIL %r" % pr); ok &= good
    _, pr = apply_pins(rows, {("Acts", 27, 34, 1): ("[HN]o[?]de", "H", pin_ev)})
    good = len(pr) == 1 and "stale pin token" in pr[0]
    print("pin with stale token -> DIE      ", "ok" if good else "FAIL %r" % pr); ok &= good
    _, pr = apply_pins(rows, {("Acts", 27, 35, 0): ("[HN]opde", "H", pin_ev)})
    good = len(pr) == 1 and "absent" in pr[0]
    print("pin on absent site -> DIE        ", "ok" if good else "FAIL %r" % pr); ok &= good
    ok &= resolved >= 4
    print("selftest", "PASS" if ok else "FAIL", "(%d of 8 resolved)" % resolved)
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    shift = int(sys.argv[sys.argv.index("--control-shift") + 1]) if "--control-shift" in sys.argv else 0
    rows, cover = run(shift)
    if not rows:
        print("no [HN] sites found - wrong paths?")
        sys.exit(2)
    if shift:
        print("CONTROL shift +%d verses (nothing written; pins not applied)" % shift)
    else:
        rows, probs = apply_pins(rows, load_pins(PINS))
        if probs:
            print("DIE: %d pin(s) in %s do not apply (nothing written):" % (len(probs), PINS))
            for p in probs:
                print("  " + p)
            sys.exit(3)
    report(rows, cover, write=not shift)
