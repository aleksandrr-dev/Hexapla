#!/usr/bin/env python
"""
kxii_diff.py - diff our image-transcribed Karl XII apocrypha against kxii.se.

    python tools/kxii_diff.py --book vish --chunk karlxii_wisdom.md \
        --name "Wisdom of Solomon" [--chapters 1-10] [--out report.md]

## WHAT THIS IS AND IS NOT

kxii.se is an INDEPENDENT WITNESS to the same 1703 print. It is the campaign's
designated QA diff target and **NEVER A COPY SOURCE** - its transcription right
is exactly what this project could not obtain permission for. The legal
position depends on the ORDER of operations: transcribe from the cc-0 page
image first, diff afterwards. This tool therefore refuses to emit kxii.se text
as a correction; it emits DISAGREEMENT SITES, and every site must be settled by
re-reading the page image.

Two independent readers of the same page agreeing on the same wrong character
is rare, so agreement is real evidence. Disagreement is NOT evidence that we
are wrong - it means one of us is, and only the image can say which.

## ⚠⚠ 2026-08-29: THE PLAIN FETCH IS BLOCKED - THIS TOOL CANNOT RUN

kxii.se now answers EVERY path, including known-good ones, with a ~12 KB
anti-bot interstitial titled "One moment, please..." that reloads itself after
5 seconds. `parse_kxii` finds no `<section id="kap_">` and silently yields an
empty book.

POSITIVE CONTROL, and it is what makes this a finding rather than a guess:
`https://kxii.se/vish` returns 12 KB with 0 `<p>` today, while the cached copy
at `_kxii_cache/kxii_vish.html` is 84 KB with 469. **The slug is not wrong and
the parser is not wrong - the fetch no longer reaches the text.** The in-app
browser did not get through the challenge either.

## ✓ SETTLED 2026-08-30: IT IS NOT THE PROXY. kxii.se IS BLOCKING THIS HOST.

The 2026-08-29 note left this undetermined and named the local
`mitmdump --listen-port 8080` proxy as the prime suspect, following the session
handoff. **That suspicion is now falsified.** Measured, all three in one run,
same shell, same opener:

    litteraturbanken.se   200, 17 KB      <- our cc-0 source
    archive.org           200, 1.1 MB     <- metadata API
    kxii.se               TLS handshake TIMEOUT

The proxy carries every other host fine, so it is healthy. Only kxii.se fails.
⚠ Note also that `HTTPS_PROXY=http://127.0.0.1:8080` IS set in this shell and
urllib honours it (`urllib.request.getproxies()` shows it), and that DIRECT,
proxy-bypassing egress does not exist here at all — a no-proxy opener also times
out at the handshake. So "just bypass the proxy" is not an available fix, and it
would not have helped anyway.

⚠⚠ AND IT GOT WORSE BETWEEN 08-29 AND 08-30. On 08-29 kxii.se answered with a
~12 KB "One moment, please..." anti-bot interstitial. On 08-30 it does not
complete a TLS handshake at all. **The most likely cause is our own automated
fetch volume tripping an escalating block.**

⛔ DO NOT TRY TO EVADE IT. Rotating the User-Agent, forging browser headers,
cycling IPs or scripting the challenge are all circumvention of an access
control on someone else's server, and this campaign's whole legal position with
kxii.se rests on being the well-behaved party. **Stop fetching.** The block may
lapse on its own; retry at most once, days apart, not in a loop.

▶ THE LEGITIMATE ROUTE, and it already exists: the campaign has correspondence
with kxii.se's operator (`karlxii_apoc_navigation.md` §1 records the retraction
sent to Cai Alfredson). If the witness matters enough, ASK — for access, or for
a text dump for QA use. That is a human step, not a code change.

Meanwhile the four books diffed before the block (vish, judit, syr, 2-mack)
still have their cached HTML in `_kxii_cache/`; every other book, including the
whole `karlxii_daniel_additions.md` unit, is UNWITNESSED. That is a stated gap
in the campaign's QA, not a passed check.

## NORMALISATION

Comparison is on a folded form, because the two transcriptions differ in
editorial convention, not substance:
  - the print's `/` is a comma; kxii.se modernises it. All punctuation folded.
  - we mark a decorated initial by doubling case (JAgh); kxii.se does not.
  - our `*` and `(a)` apparatus markers have no counterpart there.
  - long s, ligature and whitespace variation.
The folded form is for MATCHING ONLY. Reports quote our original text.

⚠ Folding is deliberately aggressive on punctuation and case, and deliberately
NOT aggressive on letters: a/aa, a-ring and a-umlaut stay distinct, because the
diacritic class is exactly what we most need this witness for.
"""
import argparse
import difflib
import io
import os
import re
import sys
import unicodedata
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
BASE = "https://kxii.se/"


# ---------------------------------------------------------------- fetch ----
def fetch(book, cache_dir):
    """Fetch a kxii.se book page, caching so a re-run costs nothing."""
    if cache_dir:
        path = os.path.join(cache_dir, "kxii_%s.html" % book)
        if os.path.isfile(path):
            return io.open(path, encoding="utf-8").read()
    req = urllib.request.Request(BASE + book, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=90).read()
    for enc in ("utf-8", "cp1252", "iso-8859-1"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit("could not decode %s" % book)
    if cache_dir:
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        io.open(path, "w", encoding="utf-8").write(html)
    return html


def unescape(s):
    import html as _h

    return _h.unescape(s)


def parse_kxii(html):
    """-> {chapter: {verse: text}}. Verse 1 is printed unnumbered."""
    out = {}
    for sec in re.findall(
        r'<section id="kap_(\d+)".*?</section>', html, flags=re.S
    ):
        pass
    for m in re.finditer(
        r'<section id="kap_(\d+)"(.*?)(?=<section id="kap_|\Z)', html, flags=re.S
    ):
        ch = int(m.group(1))
        body = m.group(2)
        verses = {}
        n = 0
        for pm in re.finditer(r"<p>(.*?)</p>", body, flags=re.S):
            frag = pm.group(1)
            if "<small>" in frag:  # chapter argument, not scripture
                continue
            txt = unescape(re.sub(r"<[^>]+>", "", frag)).strip()
            if not txt:
                continue
            vm = re.match(r"^(\d+)\.\s*(.*)$", txt, flags=re.S)
            if vm:
                n = int(vm.group(1))
                txt = vm.group(2)
            else:
                n = n + 1 if n else 1
            verses[n] = re.sub(r"\s+", " ", txt).strip()
        if verses:
            out[ch] = verses
    return out


    # A verse may WRAP onto continuation lines. Missing that manufactured a
    # false "dropped clause" finding at Wisdom 2:1 on the first run: the parser
    # read only the head line and the witness appeared to have text we lacked.
    # A differ that under-reads one side invents defects on that side.
NOTE_PREFIX = ("·", "-", "|", ">")
NOTE_START = ("⚠", "✅", "★", "▶", "⛔", "ℹ")


# A note paragraph that follows the last verse of a chapter with NO blank
# line between them was being swallowed as a continuation of that verse,
# which made the differ report the whole note as text kxii.se "lacks" - two
# invented delete-sites at Sirach 50:31 and 51:38 on 2026-08-30. Neither a
# NOTE_PREFIX nor a NOTE_START character opens those lines; they open
# "Notes on ch50, CLOSED (Argument from p694_L5; ...)".
# These two patterns are safe stops because NO scripture line can contain
# either: a strip id is our own coordinate system, and "Notes on ch<N>" is
# the chunk format's own section opener.
NOTE_LINE = re.compile(r"^Notes on ch\d+|p\d{3}_[LR]\d")


def parse_chunk(path, name):
    """Our chunk file -> {chapter: {verse: text}}, joining wrapped lines."""
    out = {}
    cur = None
    vnum = None
    head = re.compile(r"^##\s+%s\s+(\d+)\s*$" % re.escape(name))
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = head.match(line)
        if m:
            cur = int(m.group(1))
            vnum = None
            out.setdefault(cur, {})
            continue
        if line.startswith("#"):
            cur, vnum = None, None
            continue
        if cur is None:
            continue
        vm = re.match(r"^(\d+)\s+(.*)$", line)
        if vm:
            vnum = int(vm.group(1))
            out[cur][vnum] = vm.group(2).strip()
            continue
        stripped = line.strip()
        if (not stripped or stripped.startswith(NOTE_PREFIX) or
                stripped[:1] in NOTE_START or
                stripped.startswith("Argument:") or
                NOTE_LINE.search(stripped)):
            vnum = None
            continue
        if vnum is not None:  # continuation of a wrapped verse
            out[cur][vnum] = (out[cur][vnum] + " " + stripped).strip()
    return out


# ------------------------------------------------------------ normalise ----
def fold(s):
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ſ", "s")            # long s
    s = s.replace("ß", "ss")           # sharp s -> ss (o-sharp-s / oss)
    s = re.sub(r"\(\w\)", " ", s)           # (a) apparatus markers
    s = s.replace("*", " ")                 # marginal reference markers
    s = re.sub(r"[\/,.;:!?()\[\]«»\"'‘’“”–—-]", " ", s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokens(s):
    return fold(s).split()


# ----------------------------------------------------------------- diff ----
def diff_verse(ours, theirs):
    a, b = tokens(ours), tokens(theirs)
    sites = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        sites.append((tag, " ".join(a[i1:i2]), " ".join(b[j1:j2])))
    ratio = sm.ratio()
    return sites, ratio


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--book", required=True, help="kxii.se slug, e.g. vish")
    ap.add_argument("--chunk", required=True)
    ap.add_argument("--name", required=True, help="exact book name in the chunk")
    ap.add_argument("--chapters", help="e.g. 1-10 or 3")
    ap.add_argument("--cache", default="_kxii_cache")
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    ours = parse_chunk(args.chunk, args.name)
    theirs = parse_kxii(fetch(args.book, args.cache))
    if not ours:
        raise SystemExit(
            "parsed ZERO chapters from %s - check --name matches the '## <name> N' "
            "headings exactly" % args.chunk
        )
    if not theirs:
        raise SystemExit("parsed ZERO chapters from kxii.se/%s" % args.book)

    if args.chapters:
        if "-" in args.chapters:
            lo, hi = (int(v) for v in args.chapters.split("-"))
            want = set(range(lo, hi + 1))
        else:
            want = {int(args.chapters)}
    else:
        want = set(ours)

    lines = []
    tot_v = tot_sites = exact = 0
    count_mismatch = []
    for ch in sorted(want):
        ov, tv = ours.get(ch, {}), theirs.get(ch, {})
        if not ov:
            continue
        if len(ov) != len(tv):
            count_mismatch.append((ch, len(ov), len(tv)))
        for v in sorted(ov):
            if v not in tv:
                lines.append("- **%d:%d** VERSE ABSENT on kxii.se (count %d vs %d)"
                             % (ch, v, len(ov), len(tv)))
                continue
            tot_v += 1
            sites, ratio = diff_verse(ov[v], tv[v])
            if not sites:
                exact += 1
                continue
            tot_sites += len(sites)
            lines.append("- **%d:%d** (similarity %.3f)" % (ch, v, ratio))
            for tag, a, b in sites:
                lines.append("    - `%s` ours=%r theirs=%r" % (tag, a, b))

    report = []
    report.append("# kxii.se witness diff - %s" % args.name)
    report.append("")
    report.append("Witness comparison ONLY. kxii.se is not a correction source;")
    report.append("every site below must be settled by re-reading the page image.")
    report.append("")
    report.append("- verses compared: **%d**" % tot_v)
    report.append("- verses identical after folding: **%d** (%.1f%%)"
                  % (exact, 100.0 * exact / tot_v if tot_v else 0))
    report.append("- verses with at least one site: **%d**" % (tot_v - exact))
    report.append("- total disagreement sites: **%d**" % tot_sites)
    if count_mismatch:
        report.append("")
        report.append("## Verse-count differences (editorial split, investigate)")
        for ch, a, b in count_mismatch:
            report.append("- ch %d: ours %d, kxii.se %d" % (ch, a, b))
    report.append("")
    report.append("## Sites")
    report.extend(lines or ["(none)"])
    text = "\n".join(report)

    if args.out:
        io.open(args.out, "w", encoding="utf-8").write(text)
        print("wrote %s" % args.out)
    print("\n".join(report[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
