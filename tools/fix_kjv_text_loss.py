# -*- coding: utf-8 -*-
"""Repair two KJV text-loss defects, in the ASSETS (Android and the web build
both read them). Dry run by default; --apply writes.

    python tools/fix_kjv_text_loss.py            # dry run: counts + examples
    python tools/fix_kjv_text_loss.py --apply    # write both assets, re-read
    python tools/fix_kjv_text_loss.py --selftest # fixtures + known-bad controls

1. en_kjv.json — 7 verses where a SUPPLIED-words span contains a colon
   ("{tarry: for}"). BibleRepo.parseAsset (and narrate.py strip_kjv_notes)
   take any brace group with a colon for a translator's margin note and drop
   it, so the words vanished from the verse and turned up as a "note". Fix:
   move the colon out of the braces ("{tarry}: {for}"), which keeps the words
   marked as supplied and makes the group a plain supplied-words span. Genuine
   notes in this asset sit after the verse text (or, twice, mid-verse and
   starting "or,"); the list below is explicit, never a pattern.

2. en_kjv_strongs.json — the tagged text shown when Strong's is on. Its
   source (kaiserlik/kjv via convert_strongs.py) drops the text after a
   colon in ~3,400 verses ("...the dry land appear:" without "and it was
   so."), carries 444 stray "➔" paragraph marks and reshapes psalm titles.
   Fix: rebuild each verse from the PLAIN KJV's displayed text (after fix 1)
   and carry every tag across a word alignment. By construction the
   displayed Strong's verse then reads exactly as the plain KJV verse; words
   the tagged source lacks come back untagged (there is no source for their
   numbers). A verse whose untagged text already equals the plain verse is
   copied through BYTE-IDENTICAL.

Controls (all must hold or nothing is written, rc 2):
  - both files round-trip: json.dumps(json.loads(file)) == file bytes;
  - fix 1: each listed group occurs exactly once in its verse; afterwards the
    displayed text of every other verse is unchanged and the note count
    drops by exactly 7;
  - fix 2: for EVERY verse, untagged(new) == plain displayed verse; verses
    that already matched are byte-identical; the shape (books x chapters x
    verses) is unchanged; tags lost are counted and printed (never silent).

Exit codes: 0 ok, 1 selftest failure, 2 control failure / unreadable asset.
"""
import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
BIBLES = REPO / "app/src/main/assets/bibles"
KJV = BIBLES / "en_kjv.json"
STRONGS = BIBLES / "en_kjv_strongs.json"

# BibleRepo.parseAsset (Bible.kt): colon group = note (dropped), braces
# without a colon = supplied words (kept), whitespace collapsed.
MARGIN_NOTE = re.compile(r"\s*\{([^{}]*:[^{}]*)\}")
MULTI_SPACE = re.compile(r"\s+")
TAG = re.compile(r"\[[HG]\d+\]")

# (book index 0-based, chapter 1-based, verse 1-based, group as in the asset)
EATEN = (
    (0, 30, 27, "{tarry: for}"),
    (0, 42, 34, "{men: so}"),
    (2, 23, 21, "{therein: it shall be}"),
    (17, 36, 5, "{any: he is}"),
    (18, 18, 41, "{them: even}"),
    (22, 6, 13, "{their leaves: so}"),
    (23, 22, 16, "{with him: was}"),
)


class ControlError(Exception):
    pass


def display(raw):
    """The text the reader shows for a raw verse."""
    return MULTI_SPACE.sub(" ", MARGIN_NOTE.sub("", raw).replace("{", "").replace("}", "")).strip()


def untag(v):
    return MULTI_SPACE.sub(" ", TAG.sub("", display(v))).strip()


def unbrace_colon(group):
    """'{tarry: for}' -> '{tarry}: {for}' (the words stay supplied)."""
    head, _, tail = group[1:-1].partition(":")
    return "{" + head.strip() + "}: {" + tail.strip() + "}"


def load_exact(path):
    """(object, dumper) where dumper(obj) reproduces the file's bytes."""
    blob = path.read_bytes()
    obj = json.loads(blob.decode("utf-8-sig"))
    for kw in ({"ensure_ascii": False, "separators": (",", ":")},
               {"ensure_ascii": False, "separators": (", ", ": ")},
               {"ensure_ascii": False, "indent": 1},
               {"ensure_ascii": False, "indent": 2},
               {"ensure_ascii": True, "separators": (",", ":")}):
        for nl in (b"", b"\n"):
            dump = lambda o, kw=kw, nl=nl: json.dumps(o, **kw).encode("utf-8") + nl
            if dump(obj) == blob:
                return obj, dump
    raise ControlError("{}: no json.dumps setting reproduces its bytes; refusing to rewrite it".format(path.name))


# ------------------------------------------------------------------ fix 1

def fix_kjv(kjv):
    """Apply the EATEN list in place. Returns the changed (b, c, v) list."""
    before_notes = sum(len(MARGIN_NOTE.findall(v)) for b in kjv for ch in b["chapters"] for v in ch)
    before = [[[display(v) for v in ch] for ch in b["chapters"]] for b in kjv]
    changed = []
    for bi, c, v, group in EATEN:
        raw = kjv[bi]["chapters"][c - 1][v - 1]
        if group not in raw and raw.count(unbrace_colon(group)) == 1:
            continue  # already applied: a re-run must be a no-op
        if raw.count(group) != 1:
            raise ControlError("{} {}:{}: {!r} occurs {} times, expected 1".format(
                kjv[bi]["name"], c, v, group, raw.count(group)))
        kjv[bi]["chapters"][c - 1][v - 1] = raw.replace(group, unbrace_colon(group))
        changed.append((bi, c - 1, v - 1))
    after_notes = sum(len(MARGIN_NOTE.findall(v)) for b in kjv for ch in b["chapters"] for v in ch)
    if before_notes - after_notes != len(changed):
        raise ControlError("note count fell by {}, expected {}".format(before_notes - after_notes, len(changed)))
    moved = set(changed)
    for bi, b in enumerate(kjv):
        for ci, ch in enumerate(b["chapters"]):
            for vi, v in enumerate(ch):
                now = display(v)
                if (bi, ci, vi) in moved:
                    if len(now.split()) <= len(before[bi][ci][vi].split()):
                        raise ControlError("{} {}:{} gained no words".format(b["name"], ci + 1, vi + 1))
                elif now != before[bi][ci][vi]:
                    raise ControlError("{} {}:{} changed but is not listed".format(b["name"], ci + 1, vi + 1))
    return changed


# ------------------------------------------------------------------ fix 2

def tokens(tagged):
    """Tagged verse -> [(base word, original token string)]. A token that is
    only tags ('[H853]') rides with its neighbour so nothing is lost and an
    untouched verse re-joins byte-identical."""
    out = []
    lead = ""
    for tok in tagged.split(" "):
        base = TAG.sub("", tok)
        if base == "":
            if out:
                out[-1] = (out[-1][0], out[-1][1] + " " + tok)
            else:
                lead += tok + " "
            continue
        out.append((base, lead + tok))
        lead = ""
    if lead:
        out.append(("", lead.strip()))
    return out


def loose(w):
    return re.sub(r"[^\w]", "", w.lower())


def realign(tagged, plain):
    """Return (new tagged verse, tags kept, tags dropped)."""
    if untag(tagged) == plain:
        return tagged, len(TAG.findall(tagged)), 0
    toks = tokens(tagged)
    words = plain.split(" ") if plain else []
    sm = difflib.SequenceMatcher(None, [t[0] for t in toks], words, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.extend(t[1] for t in toks[i1:i2])
        elif op == "insert":
            out.extend(words[j1:j2])
        elif op == "replace":
            # A second, looser alignment inside the block: case and
            # punctuation differences ("[A" / "A", "n" / "N") keep their tags.
            sub = difflib.SequenceMatcher(
                None, [loose(t[0]) for t in toks[i1:i2]], [loose(w) for w in words[j1:j2]],
                autojunk=False)
            block = []
            for op2, a1, a2, b1, b2 in sub.get_opcodes():
                if op2 == "equal":
                    for k in range(a2 - a1):
                        block.append(words[j1 + b1 + k] + "".join(TAG.findall(toks[i1 + a1 + k][1])))
                elif op2 in ("insert", "replace"):
                    block.extend(words[j1 + b1:j1 + b2])
            # A punctuation-only tagged token the source split off a psalm
            # title ("][H1732]" = David): its tags go on the block's last
            # word ending in that punctuation ("David.]").
            for base, tok in toks[i1:i2]:
                if base and loose(base) == "" and TAG.search(tok):
                    for k in range(len(block) - 1, -1, -1):
                        if TAG.sub("", block[k]).endswith(base):
                            block[k] += "".join(TAG.findall(tok))
                            break
            out.extend(block)
        elif op == "delete":
            # Tagged-only tokens ("➔") go. A "➔[G4671]" marks a Greek word the
            # KJV leaves untranslated: keep its number standalone, the form
            # the asset already uses for the untranslated [H853].
            for base, tok in toks[i1:i2]:
                tags = "".join(TAG.findall(tok))
                if tags:
                    out.append(tags)
    new = " ".join(out)
    kept = len(TAG.findall(new))
    return new, kept, len(TAG.findall(tagged)) - kept


def fix_strongs(strongs, kjv):
    if [[len(c) for c in b["chapters"]] for b in strongs] != \
            [[len(c) for c in b["chapters"]] for b in kjv[:len(strongs)]]:
        raise ControlError("Strong's and KJV shapes differ; refusing to align")
    stats = {"verses": 0, "same": 0, "rebuilt": 0, "kept": 0, "dropped": 0, "restored_words": 0}
    examples = []
    for bi, b in enumerate(strongs):
        for ci, ch in enumerate(b["chapters"]):
            for vi, v in enumerate(ch):
                plain = display(kjv[bi]["chapters"][ci][vi])
                new, kept, dropped = realign(v, plain)
                stats["verses"] += 1
                stats["kept"] += kept
                stats["dropped"] += dropped
                if new == v:
                    stats["same"] += 1
                else:
                    stats["rebuilt"] += 1
                    stats["restored_words"] += max(0, len(plain.split()) - len(untag(v).split()))
                    if len(examples) < 3 or dropped:
                        examples.append((kjv[bi]["name"], ci + 1, vi + 1, v, new, dropped))
                if untag(new) != plain:
                    raise ControlError("{} {}:{}: untagged text still differs from the KJV".format(
                        kjv[bi]["name"], ci + 1, vi + 1))
                ch[vi] = new
    return stats, examples


# --------------------------------------------------------------- selftest

def _selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS" if cond else "FAIL") + " - " + name)
        ok = ok and cond

    bad = os.environ.get("HEXAPLA_KJVFIX_BAD", "")
    check("1: unbrace keeps the words supplied",
          unbrace_colon("{tarry: for}") == ("{tarry}: {for}" if bad != "1" else "{tarry: for}"))
    check("2: fixed group displays its words",
          display("thine eyes, {tarry}: {for} I have") == "thine eyes, tarry: for I have")
    t = "the dry[H3004] land appear:"
    new, kept, dropped = realign(t, "the dry land appear: and it was so.")
    check("3: truncated tail restored, tag kept",
          new == "the dry[H3004] land appear: and it was so." and kept == 1 and dropped == 0)
    t = "created[H1254] [H853] the heaven[H8064] ➔ and the earth."
    new, kept, dropped = realign(t, "created the heaven and the earth.")
    want = "created[H1254] [H853] the heaven[H8064] and the earth."
    if bad == "2":
        want = t
    check("4: arrow dropped, standalone tag rides along", new == want and dropped == 0)
    t = "A Psalm[H4210] of David.[H1732] Unto thee"
    new, kept, dropped = realign(t, "[A Psalm of David.] Unto thee")
    check("5: psalm-title brackets keep their tags",
          new == "[A Psalm[H4210] of David.][H1732] Unto thee" and kept == 2)
    t = "care[G3199] ➔[G4671] not[G3361] for it:"
    new, kept, dropped = realign(t, "care not for it:")
    check("5b: an untranslated word's number stays, standalone",
          new == "care[G3199] [G4671] not[G3361] for it:" and dropped == 0)
    t = "said,[H559] Let there be light:[H216]"
    check("6: a verse that already matches is byte-identical",
          realign(t, "said, Let there be light:")[0] == t)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write both assets (default: dry run)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    try:
        kjv, dump_kjv = load_exact(KJV)
        strongs, dump_strongs = load_exact(STRONGS)
        changed = fix_kjv(kjv)
        print("fix 1 (en_kjv): {} verses get their supplied words back".format(len(changed)))
        for bi, ci, vi in changed:
            print("   {} {}:{}  {}".format(kjv[bi]["name"], ci + 1, vi + 1, display(kjv[bi]["chapters"][ci][vi])))
        stats, examples = fix_strongs(strongs, kjv)
        print("fix 2 (en_kjv_strongs): {verses} verses, {same} unchanged, {rebuilt} rebuilt; "
              "tags kept {kept}, dropped {dropped}; ~{restored_words} words restored untagged".format(**stats))
        shown = examples[:3] + [e for e in examples[3:] if e[5]][:9]
        for name, c, v, old, new, dropped in shown:
            print("   {} {}:{}  (tags dropped: {})\n      OLD {}\n      NEW {}".format(name, c, v, dropped, old, new))
        if len(examples) > len(shown):
            print("   ... {} more examples".format(len(examples) - len(shown)))
    except ControlError as e:
        print("FAIL - " + str(e), file=sys.stderr)
        return 2
    if not args.apply:
        print("DRY RUN - nothing written (--apply to write)")
        return 0
    KJV.write_bytes(dump_kjv(kjv))
    STRONGS.write_bytes(dump_strongs(strongs))
    # Re-read what landed, and re-run the controls against it.
    k2 = json.loads(KJV.read_text(encoding="utf-8-sig"))
    s2 = json.loads(STRONGS.read_text(encoding="utf-8-sig"))
    bad = sum(1 for bi, b in enumerate(s2) for ci, ch in enumerate(b["chapters"])
              for vi, v in enumerate(ch) if untag(v) != display(k2[bi]["chapters"][ci][vi]))
    notes = sum(len(MARGIN_NOTE.findall(v)) for b in k2 for ch in b["chapters"] for v in ch)
    print("re-read: {} Strong's verses differ from the KJV (must be 0); KJV notes now {}".format(bad, notes))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
