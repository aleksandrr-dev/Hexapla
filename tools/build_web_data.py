# -*- coding: utf-8 -*-
"""Split the app's Bible assets into per-book JSON for the web app.

WHY: the web reader must never drift from Android. Its data is BUILT from
`app/src/main/assets` on every deploy and never committed — the split tree is
~200 MB. This script is the contract every later web brief codes against, so
it fails loudly rather than shipping a plausible-looking partial build.

    python tools/build_web_data.py --out C:/path/to/data        # real build
    python tools/build_web_data.py --aux --out C:/path/to/data  # aux assets
    python tools/build_web_data.py --selftest                   # fixture checks

What it writes under --out:
    data/<id>/<bookIndex>.json   one book, margin notes stripped
    data/<id>/books.json         per-book chapter verse counts (for navigation)
    data/manifest.json           the translation list + the licence credit

`--aux` writes the auxiliary assets the reader needs, beside that tree, and
may be run on its own:
    data/xrefs/<b>.json                  xrefs.json split by book prefix
    data/interlinear/gr/<b>.json         interlinear_gr.json split by book
    data/interlinear/he/<b>.json         interlinear_he.json split by book
    data/webster/<L>.json                webster1828.json split by first letter
    data/kjv_strongs/<b>.json            en_kjv_strongs.json (tagged KJV) by book,
                                         {"<b>": chapters}; also text-controlled
    data/<name>.json                     versemap, strongs_lexicon*,
                                         audio_index{,_gen} copied byte for byte

Every split is controlled by REASSEMBLY: the written pieces are read back,
merged, and compared for EQUALITY with the source dict — not merely counted,
so a duplicate key spanning two files is a hard failure. Whole copies are
controlled by MD5 against the source asset, so they are copied as BYTES and
never round-tripped through json.load/json.dump.

The translation list is PARSED out of Bible.kt, never globbed: the assets
directory contains `ja_meiji.json.bak-2026-09-20-meijiranges`, which is not a
translation and must not ship.

Exit codes: 0 ok, 1 selftest failure, 2 build failure (control mismatch,
unreadable asset, --out inside the repo).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
BIBLE_KT = REPO / "app/src/main/java/com/aleks/hexapla/Bible.kt"
ASSETS = REPO / "app/src/main/assets"
STRINGS_XML = REPO / "app/src/main/res/values/strings.xml"
COUNT_TOOL = REPO / "tools/count_translations.py"

KJV_ASSET = ASSETS / "bibles/en_kjv.json"
STRONGS_ASSET = ASSETS / "bibles/en_kjv_strongs.json"
STRONGS_TAG = re.compile(r"\[[HG]\d+\]")

# BibleRepo.parseAsset (Bible.kt ~line 166): a brace group CONTAINING a colon
# is a translator's margin note — the whole group goes, leading whitespace
# included. A brace group with NO colon marks supplied (italicised) words:
# the braces go, the words stay. The pattern is non-nesting by construction
# (`[^{}]*`); do not make it greedy or recursive.
MARGIN_NOTE = re.compile(r"\s*\{([^{}]*:[^{}]*)\}")
MULTI_SPACE = re.compile(r"\s+")

# Only honoured under --selftest; the known-bad control for the strip rule.
# A real build must never be able to disable it.
_IN_SELFTEST = False

# The auxiliary assets: name -> the output filename it is copied to.
AUX_WHOLE_COPIES = (
    "versemap.json",
    "strongs_lexicon.json",
    "strongs_lexicon_ru.json",
    "audio_index.json",
    "audio_index_gen.json",
)

# Splits keyed by an integer book index threaded through the same 0-based
# numbering the rest of the project uses. The value is written as-is under the
# key's own string form, so reassembly is a plain dict merge.
AUX_BOOK_SPLITS = (
    ("interlinear_gr.json", "interlinear/gr"),
    ("interlinear_he.json", "interlinear/he"),
)


def drop_one_enabled():
    """The known-bad control for the reassembly checks — selftest only.

    It drops one entry from each split before the reassembly control runs, so
    the EQUALITY check must fire. It is honoured ONLY when _IN_SELFTEST is
    true, so it can never touch a real build.
    """
    return _IN_SELFTEST and __import__("os").environ.get("HEXAPLA_WEB_AUX_DROP") == "1"

# Locale.X -> BCP-47 language tag, as the Android registry uses them.
LOCALE_SIMPLE = {
    "ENGLISH": "en",
    "FRENCH": "fr",
    "GERMAN": "de",
    "ITALIAN": "it",
    "JAPANESE": "ja",
    "SIMPLIFIED_CHINESE": "zh-Hans",
    "TRADITIONAL_CHINESE": "zh-Hant",
}


class BuildError(Exception):
    """A loud, reportable failure — never swallowed into a partial build."""


# ---------------------------------------------------------------- parsing

def strip_notes(raw):
    """Port of BibleRepo.parseAsset's text pass. Never raises, never 0-ish."""
    if _IN_SELFTEST and __import__("os").environ.get("HEXAPLA_WEB_NO_NOTESTRIP") == "1":
        return raw
    return MULTI_SPACE.sub(
        " ", MARGIN_NOTE.sub("", raw).replace("{", "").replace("}", "")
    ).strip()


def read_text(path):
    """Read a text file, or raise BuildError naming the path."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise BuildError("cannot read {}: {}".format(path, e))


def parse_translations(kt_text=None):
    """Parse the Translation(...) rows out of BibleRepo.translations.

    Returns a list of dicts {id, asset, label, lang}. Raises BuildError on a
    row whose Locale form is not in the approved set — never a guess, never a
    silent default of "en".
    """
    text = read_text(BIBLE_KT) if kt_text is None else kt_text
    if "val translations" not in text or "fun translation(" not in text:
        raise BuildError("Bible.kt: could not locate BibleRepo.translations block")
    blk = text[text.index("val translations"):text.index("fun translation(")]

    # The Locale argument may itself contain parens — Locale.forLanguageTag("sv")
    # — so the trailing group is matched lazily up to the last `)` before the
    # `name` field's localizer: here the row always ends the line, so `\)\s*,?\s*$`
    # in MULTILINE is the anchor. Rows are one-per-line in Bible.kt by convention.
    row_re = re.compile(
        r'Translation\(\s*"([a-z0-9]+)"\s*,\s*"bibles/([a-z0-9_]+)\.json"\s*,'
        r'\s*"((?:[^"\\]|\\.)*)"\s*,\s*(.*?)\)\s*,?\s*$',
        re.S | re.M,
    )
    rows = row_re.findall(blk)
    if not rows:
        raise BuildError("Bible.kt: no Translation(...) rows matched")

    out = []
    seen = set()
    for tid, asset, label, loc in rows:
        if tid in seen:
            raise BuildError("Bible.kt: duplicate translation id {!r}".format(tid))
        seen.add(tid)
        out.append({
            "id": tid,
            "asset": asset,
            "label": label.replace('\\"', '"').replace("\\'", "'"),
            "lang": locale_to_tag(loc.strip(), tid),
        })
    return out


def locale_to_tag(loc, tid):
    """Map a Kotlin Locale expression to a language tag, or raise."""
    m = re.fullmatch(r'Locale\.forLanguageTag\("([A-Za-z0-9-]+)"\)', loc)
    if m:
        return m.group(1)
    m = re.fullmatch(r"Locale\.([A-Z_]+)", loc)
    if m and m.group(1) in LOCALE_SIMPLE:
        return LOCALE_SIMPLE[m.group(1)]
    raise BuildError(
        "Bible.kt: translation {!r} has an unrecognised Locale form: {}".format(tid, loc)
    )


def read_credits():
    """The <string name="sources_text"> body, XML-unescaped.

    This is a LICENCE OBLIGATION (CC-BY / CC-BY-SA data). It is copied
    verbatim — not reflowed, not shortened, not appended to.
    """
    xml = read_text(STRINGS_XML)
    m = re.search(r'<string name="sources_text">(.*?)</string>', xml, re.S)
    if not m:
        raise BuildError("strings.xml: <string name=\"sources_text\"> not found")
    body = m.group(1)
    # `\'` in this file is a Kotlin/Android escape for an apostrophe —
    # the shipped text reads `Strong's`, not `Strong\'s`.
    body = body.replace("\\'", "'").replace('\\"', '"')
    body = body.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    body = body.replace("&#39;", "'").replace("&apos;", "'").replace("&amp;", "&")
    if "openbible.info" not in body or "CC BY-SA 4.0" not in body:
        raise BuildError("strings.xml: sources_text is missing openbible.info / CC BY-SA 4.0")
    return body


def load_books(path):
    """Parse a bible asset. Any failure is a BuildError naming the path —
    never an empty list, never a missing translation."""
    raw = read_text(path)
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise BuildError("cannot parse {}: {}".format(path, e))
    if not isinstance(data, list) or not data:
        raise BuildError("{}: expected a non-empty JSON array of books".format(path))
    books = []
    for i, obj in enumerate(data):
        if not isinstance(obj, dict) or "name" not in obj or "chapters" not in obj:
            raise BuildError("{}: book {} is not {{name, chapters}}".format(path, i))
        chapters = obj["chapters"]
        if not isinstance(chapters, list):
            raise BuildError("{}: book {} chapters is not a list".format(path, i))
        clean = []
        notes = {}
        for c, verses in enumerate(chapters):
            if not isinstance(verses, list):
                raise BuildError("{}: book {} chapter {} is not a list".format(path, i, c))
            clean.append([strip_notes(v) for v in verses])
            # The notes the strip removes, kept as BibleRepo.notes keeps them
            # (Bible.kt ~line 197): "c:v" 0-based -> each group, trimmed.
            for v, raw in enumerate(verses):
                found = [m.group(1).strip() for m in MARGIN_NOTE.finditer(raw)]
                if found:
                    notes["{}:{}".format(c, v)] = found
        book = {"name": obj["name"], "chapters": clean}
        # Absent, not empty, where a book has none: those files stay byte-identical.
        if notes:
            book["notes"] = notes
        books.append(book)
    return books


# --------------------------------------------------------------- writing

def json_bytes(obj):
    """UTF-8, ensure_ascii=False, compact, LF — no timestamps, no paths."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


def write_bytes(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)


def assert_out_outside_repo(out_dir):
    """The built data is ~200 MB and must never land inside the repo."""
    try:
        resolved = Path(out_dir).resolve()
    except OSError as e:
        raise BuildError("--out cannot be resolved: {}".format(e))
    if resolved == REPO or REPO in resolved.parents:
        raise BuildError(
            "--out resolves inside the repo ({}); the built data is ~200 MB and "
            "must never be committed".format(resolved)
        )
    return resolved


def build_one(tr, out_root):
    """Write one translation. Returns the manifest entry. Raises BuildError."""
    src = ASSETS / "bibles" / (tr["asset"] + ".json")
    if not src.is_file():
        raise BuildError("{}: source asset is missing: {}".format(tr["id"], src))
    books = load_books(src)

    src_verse_total = sum(len(c) for b in books for c in b["chapters"])
    src_book_count = len(books)

    # --- control 1: verse sum across the split files == the source asset.
    # Stripping edits verse text, it never removes a verse.
    tr_dir = out_root / "data" / tr["id"]
    written_verses = 0
    books_index = []
    for bi, book in enumerate(books):
        write_bytes(tr_dir / (str(bi) + ".json"), json_bytes(book))
        counts = [len(c) for c in book["chapters"]]
        books_index.append({"name": book["name"], "chapters": counts})
        written_verses += sum(counts)

    if written_verses != src_verse_total:
        raise BuildError(
            "{}: verse-sum control FAILED — split files hold {} verses, "
            "source asset holds {}".format(tr["id"], written_verses, src_verse_total)
        )

    # --- control 2: book count.
    if len(books_index) != src_book_count:
        raise BuildError(
            "{}: book-count control FAILED — books.json holds {} books, "
            "source asset holds {}".format(tr["id"], len(books_index), src_book_count)
        )

    # --- control 3: per-chapter counts in books.json == the split files' own.
    for bi, book in enumerate(books):
        live = [len(c) for c in book["chapters"]]
        if books_index[bi]["chapters"] != live:
            raise BuildError(
                "{}: chapter-count control FAILED for book {} — books.json holds {}, "
                "book file holds {}".format(
                    tr["id"], bi, len(books_index[bi]["chapters"]), len(live)
                )
            )

    write_bytes(tr_dir / "books.json", json_bytes(books_index))
    return {
        "id": tr["id"],
        "lang": tr["lang"],
        "label": tr["label"],
        "file": tr["asset"] + ".json",
        "bookCount": src_book_count,
        "verseCount": src_verse_total,
    }


def bible_kt_entry_count():
    """Run count_translations.py and parse `entries in Bible.kt`. Never
    hard-coded, and never a guess: an unparseable run is a BuildError."""
    try:
        proc = subprocess.run(
            [sys.executable, str(COUNT_TOOL)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO),
        )
    except OSError as e:
        raise BuildError("cannot run {}: {}".format(COUNT_TOOL, e))
    if proc.returncode != 0:
        raise BuildError(
            "{} exited {}\n{}".format(COUNT_TOOL, proc.returncode, proc.stderr.strip())
        )
    m = re.search(r"entries in Bible\.kt\s*:\s*(\d+)", proc.stdout)
    if not m:
        raise BuildError("count_translations.py printed no 'entries in Bible.kt' line")
    return int(m.group(1))


def run_build(out_dir):
    out_root = assert_out_outside_repo(out_dir)
    translations = parse_translations()

    expected = bible_kt_entry_count()
    if len(translations) != expected:
        raise BuildError(
            "manifest control FAILED — parsed {} Translation rows from Bible.kt, "
            "count_translations.py reports {}".format(len(translations), expected)
        )

    entries = []
    for tr in translations:
        entries.append(build_one(tr, out_root))

    manifest = {"translations": entries, "credits": read_credits()}
    write_bytes(out_root / "data" / "manifest.json", json_bytes(manifest))

    print("wrote {} translations to {}".format(len(entries), out_root))
    print("manifest control: {} rows == count_translations.py '{}'".format(
        len(entries), expected))
    for e in entries:
        print("  {:<8} {:<8} books={:<4} verses={}".format(
            e["id"], e["lang"], e["bookCount"], e["verseCount"]))
    return entries


# ------------------------------------------------------------------- aux

def load_json_dict(path):
    """Parse a JSON object out of an asset. Any failure is a BuildError
    naming the path — never an empty dict, never a plausible number."""
    if not path.is_file():
        raise BuildError("aux source asset is missing: {}".format(path))
    try:
        data = json.loads(read_text(path))
    except ValueError as e:
        raise BuildError("cannot parse {}: {}".format(path, e))
    if not isinstance(data, dict):
        raise BuildError("{}: expected a JSON object at the top level".format(path))
    return data


def md5_file(path):
    """Streaming MD5 of a file's bytes. Raises BuildError naming the path."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                buf = f.read(1 << 20)
                if not buf:
                    break
                h.update(buf)
    except OSError as e:
        raise BuildError("cannot read {} for MD5: {}".format(path, e))
    return h.hexdigest()


def copy_whole(src, dst):
    """Copy an asset's BYTES to dst. Returns (bytes, md5).

    Deliberately not a json.load/json.dump round-trip: a re-dump changes
    separators and escaping, which would break the MD5 control and gain
    nothing.
    """
    if not src.is_file():
        raise BuildError("aux source asset is missing: {}".format(src))
    try:
        blob = src.read_bytes()
    except OSError as e:
        raise BuildError("cannot read {}: {}".format(src, e))
    write_bytes(dst, blob)
    return len(blob), hashlib.md5(blob).hexdigest()


def bucket_letter(headword):
    """The Webster output bucket for a headword's first character.

    L = first char uppercased when it is ASCII A-Z; everything else (digits,
    punctuation, accented letters, an empty headword) goes to "_other".
    """
    if headword:
        c = headword[0]
        if "a" <= c <= "z" or "A" <= c <= "Z":
            return c.upper()
    return "_other"


def reassemble_split(out_dir, rel_dir, label):
    """Read every file in rel_dir back, merge them, and return (merged, n).

    Returns the merged dict and the number of files read. Raises BuildError
    if the directory is missing or holds no files — a control that cannot run
    must never look like a pass with 0 entries.
    """
    d = out_dir / "data" / rel_dir
    if not d.is_dir():
        raise BuildError(
            "reassembly control for {} could not run: {} does not exist".format(label, d)
        )
    files = sorted(p for p in d.iterdir() if p.suffix == ".json")
    if not files:
        raise BuildError(
            "reassembly control for {} could not run: no .json files in {}".format(label, d)
        )
    merged = {}
    for p in files:
        try:
            part = json.loads(read_text(p))
        except ValueError as e:
            raise BuildError("cannot parse the file just written: {}: {}".format(p, e))
        if not isinstance(part, dict):
            raise BuildError("{}: split file is not a JSON object".format(p))
        dup = set(part) & set(merged)
        if dup:
            raise BuildError(
                "{}: key(s) appear in more than one split file, e.g. {!r}".format(
                    label, sorted(dup)[0]
                )
            )
        merged.update(part)
    return merged, len(files)


def write_split(source, out_dir, rel_dir, key_of, label, mutate=None):
    """Split `source` into one file per group, then control it by reassembly.

    `key_of(key)` returns the group name (a str) a key belongs to. All keys
    keep their ORIGINAL key strings — no re-keying — so the control is a plain
    dict comparison. Returns a (files, keys, ok) triple; ok is True only when
    every written entry reassembles to exactly the source dict.
    """
    groups = {}
    for k in source:
        groups.setdefault(key_of(k), {})[k] = source[k]
    if drop_one_enabled():
        # Known-bad control: drop one entry from each group so the EQUALITY
        # check below must fire. Selftest only — never a real build.
        for g in groups:
            if groups[g]:
                groups[g].pop(sorted(groups[g])[0])
    if mutate is not None:
        mutate(groups)

    d = out_dir / "data" / rel_dir
    for g in sorted(groups):
        write_bytes(d / (g + ".json"), json_bytes(groups[g]))

    merged, n_files = reassemble_split(out_dir, rel_dir, label)
    ok = merged == source
    print("{}: {} keys reassembled from {} files (source holds {} keys)".format(
        label, len(merged), n_files, len(source)))
    if not ok:
        raise BuildError(
            "{}: reassembly control FAILED — reassembled {} keys, source holds {} keys; "
            "the merged dict is not equal to the source dict".format(
                label, len(merged), len(source)
            )
        )
    return n_files, len(merged), ok


def check_strongs_text(strongs, kjv):
    """Every tagged verse, with its [H/G] tags removed, must read as the plain
    KJV verse at the same place (the asset lost verse tails until
    tools/fix_kjv_text_loss.py). Returns the verse count; raises BuildError."""
    if [[len(c) for c in b["chapters"]] for b in strongs] != \
            [[len(c) for c in b["chapters"]] for b in kjv[:len(strongs)]]:
        raise BuildError("kjv_strongs: book/chapter/verse shape differs from the KJV")
    n = 0
    for bi, b in enumerate(strongs):
        for ci, ch in enumerate(b["chapters"]):
            for vi, v in enumerate(ch):
                plain = MULTI_SPACE.sub(" ", STRONGS_TAG.sub("", v)).strip()
                if plain != kjv[bi]["chapters"][ci][vi]:
                    raise BuildError("kjv_strongs: {} {}:{} untagged is not the KJV verse".format(
                        kjv[bi]["name"], ci + 1, vi + 1))
                n += 1
    return n


def build_aux(out_dir):
    """Write every auxiliary asset under --out. Raises BuildError. Returns the
    count of entries checked, so a control that could not run is loud."""
    out_root = assert_out_outside_repo(out_dir)
    checked = 0

    # --- xrefs.json: key "b:c:v" -> data/xrefs/<b>.json, SAME key strings.
    xrefs = load_json_dict(ASSETS / "xrefs.json")
    n_files, n_keys, _ = write_split(
        xrefs, out_root, "xrefs", lambda k: k.split(":")[0], "xrefs")
    checked += n_keys

    # --- interlinear_gr.json / interlinear_he.json: value as-is, keyed "<b>".
    for name, rel in AUX_BOOK_SPLITS:
        data = load_json_dict(ASSETS / name)
        n_files, n_keys, _ = write_split(
            data, out_root, rel, lambda k: k, name[:-5])
        checked += n_keys

    # --- en_kjv_strongs.json: the tagged KJV Android shows when Strong's is
    # on, parsed as BibleRepo.parseAsset parses it, one file per book
    # {"<b>": chapters}. Controlled by reassembly AND by the text: every
    # verse, untagged, must read exactly as the plain KJV verse.
    strongs = load_books(STRONGS_ASSET)
    n_verses = check_strongs_text(strongs, load_books(KJV_ASSET))
    print("kjv_strongs: {} verses untag to the plain KJV".format(n_verses))
    n_files, n_keys, _ = write_split(
        {str(i): b["chapters"] for i, b in enumerate(strongs)},
        out_root, "kjv_strongs", lambda k: k, "kjv_strongs")
    checked += n_keys

    # --- webster1828.json: first letter A-Z, everything else _other.
    webster = load_json_dict(ASSETS / "webster1828.json")
    n_files, n_keys, _ = write_split(
        webster, out_root, "webster", bucket_letter, "webster")
    checked += n_keys
    other_names = sorted(k for k in webster if bucket_letter(k) == "_other")
    print("webster: {} entries in _other.json".format(len(other_names)))
    for k in other_names[:10]:
        print("    _other headword: {!r}".format(k))

    # --- whole copies: bytes only, controlled by MD5.
    for name in AUX_WHOLE_COPIES:
        src = ASSETS / name
        dst = out_root / "data" / name
        n_bytes, src_md5 = copy_whole(src, dst)
        dst_md5 = md5_file(dst)
        print("copy {}: {} bytes  md5 {} == {}".format(
            name, n_bytes, src_md5, dst_md5))
        if src_md5 != dst_md5:
            raise BuildError(
                "MD5 control FAILED for {}: source {}, output {}".format(
                    name, src_md5, dst_md5
                )
            )
        checked += 1

    print("aux total: {} entries reassembled/copied".format(checked))
    return checked


# -------------------------------------------------------------- selftest

def _selftest():
    """In-process assertions. Prints one line each; rc 0 all pass, 1 else."""
    global _IN_SELFTEST
    results = []

    def check(name, fn):
        try:
            res = fn()
        except Exception as e:
            results.append(False)
            print("FAIL - {}: {}".format(name, e))
            return
        if res is False:
            results.append(False)
            print("FAIL - {}".format(name))
        else:
            results.append(True)
            print("PASS - {}".format(name))

    import tempfile
    tmp = tempfile.TemporaryDirectory(prefix="hexapla_web_selftest_")
    tmpdir = Path(tmp.name)

    kjv = load_books(KJV_ASSET)

    def a1():
        got = kjv[0]["chapters"][0][3]
        want = ("And God saw the light, that it was good: and God divided "
                "the light from the darkness.")
        assert got == want, "got {!r}".format(got)

    def a2():
        got = kjv[0]["chapters"][0][1]
        want = ("And the earth was without form, and void; and darkness was "
                "upon the face of the deep. And the Spirit of God moved upon "
                "the face of the waters.")
        assert got == want, "got {!r}".format(got)

    def a3():
        got = kjv[0]["chapters"][0][5]
        want = ("And God said, Let there be a firmament in the midst of the "
                "waters, and let it divide the waters from the waters.")
        assert got == want, "got {!r}".format(got)

    def a3n():
        # The notes the strip removed are kept per book, "c:v" 0-based, and a
        # book-level control: every stripped group is kept exactly once.
        got = kjv[0]["notes"].get("0:5")
        want = ["firmament: Heb. expansion"]
        if __import__("os").environ.get("HEXAPLA_WEB_NOTES_BAD") == "1":
            want = ["firmament"]
        assert got == want, "got {!r}".format(got)
        raw = json.loads(read_text(KJV_ASSET))
        n_raw = sum(len(MARGIN_NOTE.findall(v)) for b in raw for ch in b["chapters"] for v in ch)
        n_kept = sum(len(x) for b in kjv for x in b.get("notes", {}).values())
        assert n_raw == n_kept and n_raw > 7000, "{} groups in source, {} kept".format(n_raw, n_kept)

    def a4():
        rows = parse_translations()
        expected = bible_kt_entry_count()
        assert len(rows) == expected, "{} rows vs {} reported".format(len(rows), expected)

    def a5():
        try:
            locale_to_tag("Locale.FAKE_FORM", "fake")
        except BuildError:
            return
        raise AssertionError("unknown Locale form did not raise")

    def a6():
        try:
            assert_out_outside_repo(REPO / "data")
        except BuildError:
            return
        raise AssertionError("in-repo --out was not refused")

    def a7():
        """The verse-sum control can fire: feed it a truncated book."""
        books = [{"name": "Genesis", "chapters": [[
            "And God saw the light, that it was good.",
            "And God called the light Day.",
        ]]},
            {"name": "Exodus", "chapters": [["Verse one.", "Verse two."]]}]
        source_total = 4
        truncated = [dict(b) for b in books]
        truncated[1] = {"name": "Exodus", "chapters": [["Verse one."]]}
        split_total = sum(len(c) for b in truncated for c in b["chapters"])
        assert split_total != source_total, "fixture did not actually truncate"
        try:
            if split_total != source_total:
                raise BuildError("verse-sum control FAILED")
        except BuildError:
            return
        raise AssertionError("control did not fire")

    def a8():
        """A two-book fixture splits and reassembles to an EQUAL dict."""
        src = {
            "0:0:0": [["Gen", 1, 1]],
            "0:0:1": [["Gen", 1, 2]],
            "1:0:4": [["Exod", 1, 5]],
        }
        d = tmpdir / "s8"
        n_files, n_keys, ok = write_split(
            src, d, "xrefs", lambda k: k.split(":")[0], "s8 xrefs")
        merged, _ = reassemble_split(d, "xrefs", "s8 xrefs")
        assert n_files == 2, "expected 2 files, wrote {}".format(n_files)
        assert ok and merged == src, "reassembly is not equal to the source fixture"
        assert n_keys == 3, "expected 3 keys, got {}".format(n_keys)

    def a9():
        """The reassembly control FIRES when a split file is missing."""
        src = {
            "0:0:0": [["Gen", 1, 1]],
            "1:0:4": [["Exod", 1, 5]],
        }
        d = tmpdir / "s9"
        # Write only book 0's file — as if a write had silently failed, or as
        # the AUX_DROP control leaves it. The control must notice the gap.
        write_bytes(
            d / "data" / "xrefs" / "0.json",
            json_bytes({k: v for k, v in src.items() if k.startswith("0:")}))
        try:
            merged, _ = reassemble_split(d, "xrefs", "s9 dropped")
            if merged != src:
                raise BuildError("reassembly control FAILED")
        except BuildError:
            return
        raise AssertionError("reassembly control did not fire on a missing file")

    def a10():
        """Webster letter bucketing sends a non-A-Z headword to _other, and
        reassembly still matches."""
        src = {
            "Apple": "a fruit",
            "`WORD`": "a non A-Z headword",
            "ZEBRA": "a striped animal",
            "9LIVES": "a digit headword",
        }
        d = tmpdir / "s10"
        n_files, n_keys, ok = write_split(
            src, d, "webster", bucket_letter, "s10 webster")
        # Two entries share the "_other" bucket, so 3 files: A, Z, _other.
        assert n_files == 3, "expected 3 files (A, Z, _other), got {}".format(n_files)
        assert (d / "data" / "webster" / "_other.json").is_file(), "_other.json not written"
        other = json.loads((d / "data" / "webster" / "_other.json").read_text(encoding="utf-8"))
        assert set(other) == {"`WORD`", "9LIVES"}, "wrong _other contents: {}".format(sorted(other))
        merged, _ = reassemble_split(d, "webster", "s10 webster")
        assert ok and merged == src, "webster reassembly is not equal to the source"

    def a11():
        """An MD5 copy control FIRES when one byte of the output is mutated."""
        src = tmpdir / "s11_src.bin"
        dst = tmpdir / "s11_out.bin"
        src.write_bytes(b"hexapla-aux-copy-control")
        _, src_md5 = copy_whole(src, dst)
        assert md5_file(dst) == src_md5, "clean copy did not match its source MD5"
        blob = bytearray(dst.read_bytes())
        blob[0] ^= 0xFF
        dst.write_bytes(bytes(blob))
        assert md5_file(dst) != src_md5, "MD5 control did not fire on a mutated byte"

    def a12():
        """The tagged KJV untags to the plain KJV, and the control fires on a
        verse cut short (Gen 1:9 lost «and it was so.» before the fix)."""
        strongs = load_books(STRONGS_ASSET)
        n = check_strongs_text(strongs, kjv)
        assert n > 31000, "only {} verses checked".format(n)
        v = strongs[0]["chapters"][0][8]
        cut = v[:v.rindex(" and it was so.")]
        if __import__("os").environ.get("HEXAPLA_WEB_STRONGS_BAD") == "1":
            cut = v
        strongs[0]["chapters"][0][8] = cut
        try:
            check_strongs_text(strongs, kjv)
        except BuildError:
            return
        raise AssertionError("text control did not fire on a truncated verse")

    check("assert 1: Genesis 1:4 — supplied words kept, colon note dropped", a1)
    check("assert 2: Genesis 1:2 — supplied words survive", a2)
    check("assert 3: Genesis 1:6 — trailing colon note dropped", a3)
    check("assert 3n: margin notes kept per book, every stripped group once", a3n)
    check("assert 4: Bible.kt parser == count_translations.py rows", a4)
    check("assert 5: Locale mapper raises on an unknown form", a5)
    check("assert 6: --out inside the repo is refused", a6)
    check("assert 7: verse-sum control fires on a truncated book", a7)
    check("assert 8: split reassembles to an equal dict", a8)
    check("assert 9: reassembly control fires on a dropped split file", a9)
    check("assert 10: Webster sends non-A-Z to _other and reassembles", a10)
    check("assert 11: MD5 copy control fires on a mutated byte", a11)
    check("assert 12: Strong's text untags to the KJV; control fires on a cut verse", a12)

    passed = sum(1 for r in results if r)
    print("\n{} of {} assertions passed".format(passed, len(results)))
    return 0 if passed == len(results) else 1


def main():
    global _IN_SELFTEST
    ap = argparse.ArgumentParser(description="Build the web app's Bible data.")
    ap.add_argument("--out", help="output directory (required for a build)")
    ap.add_argument("--aux", action="store_true",
                    help="also (or only) write the auxiliary assets")
    ap.add_argument("--selftest", action="store_true", help="run fixture assertions")
    args = ap.parse_args()

    if args.selftest:
        _IN_SELFTEST = True
        return _selftest()

    if not args.out:
        print("ERROR - --out DIR is required", file=sys.stderr)
        return 2

    try:
        # --aux is additive: it writes the aux tree BESIDE the data/ tree
        # brief 1 builds, and running it with --out on its own writes both.
        if args.aux:
            build_aux(args.out)
        run_build(args.out)
    except BuildError as e:
        print("FAIL - {}".format(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
