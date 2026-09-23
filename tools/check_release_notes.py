#!/usr/bin/env python3
"""Validate the CURRENT release-notes block in store-assets/STORE_LISTING.md.

WHY THIS EXISTS
---------------
The 1.6.1 notes failed at paste time in Play Console: "30 of 31 posted", and
ta-IN was rejected for length. Both were invisible until the owner was sitting
in the console with the release in front of him.

  · en-IN was missing — the block predated that locale being added to the
    account, so it had 30 of Play's 31.
  · ta-IN was 507 chars against a 500 cap, and self-inflicted: an earlier
    wording fix swapped a 19-char Tamil phrase for a 31-char one. English was
    re-checked at the time; the locales the substitution LENGTHENED were not.

Both are mechanical and cheap to catch. Neither is catchable by reading.

WHAT IT CHECKS
--------------
  1. Locale set EXACTLY matches Play's What's-new list (no missing, no extra).
  2. Locale ORDER matches Play's, so the block pastes in one go.
  3. Every entry <= 500 characters (Play's cap).
  4. No entry empty or still holding placeholder text.
  5. Exactly ONE release block sits above "## Store descriptions" — older
     releases belong under the ARCHIVE banner at the end of the file, so the
     file opens on what you actually need to paste.

Archived blocks are NOT length/locale-checked: they are historical records of
what was submitted, and older releases legitimately had fewer locales.

USAGE
  python tools/check_release_notes.py          # exit 1 on any failure
  python tools/check_release_notes.py -v       # also print每 locale's length

Run before pasting into Play Console, and after ANY edit that changes wording
in more than one locale.
"""
import argparse, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "store-assets", "STORE_LISTING.md")

LIMIT = 500

# Play Console's What's-new locale list, in its own order.
PLAY_ORDER = ['en-US', 'ar', 'be', 'cs-CZ', 'da-DK', 'de-DE', 'el-GR', 'en-IN',
              'es-419', 'es-ES', 'es-US', 'fi-FI', 'fr-CA', 'fr-FR', 'hu-HU',
              'hy-AM', 'it-IT', 'iw-IL', 'ja-JP', 'lv', 'nl-NL', 'pl-PL',
              'pt-BR', 'pt-PT', 'ru-RU', 'sr', 'sv-SE', 'ta-IN', 'zh-CN',
              'zh-HK', 'zh-TW']

# ⚠ Case-SENSITIVE on the bare markers, and word-bounded. A case-insensitive
# /TODO/ matches the ordinary Portuguese word "todo" ("todo o Novo Testamento")
# and falsely blocked pt-BR and pt-PT on a perfectly valid release. Real
# placeholders are uppercase; Play's own prefill is matched case-insensitively
# because it is a whole distinctive phrase, not a word that occurs in prose.
PLACEHOLDER = re.compile(r'(?i:enter or paste your release notes)|\b(?:TODO|TBD|FIXME|XXX)\b')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    raw = io.open(PATH, encoding='utf-8', newline='').read()
    fails = []

    desc_i = raw.find('## Store descriptions')
    if desc_i < 0:
        sys.exit('could not find "## Store descriptions"')
    head = raw[:desc_i]

    blocks = re.findall(r'^## ([0-9]+\.[0-9]+\.[0-9]+) release notes',
                        head, re.M)
    if not blocks:
        sys.exit('no release-notes block found above the descriptions section')
    if len(blocks) > 1:
        fails.append(
            f'{len(blocks)} release blocks sit above the descriptions section '
            f'({", ".join(blocks)}). Only the CURRENT release belongs at the '
            f'top; move older ones under the ARCHIVE banner at the end.')

    version = blocks[0]
    # Search `raw`, not `head`: head is cut immediately before the next "## "
    # heading, so a lookahead for it can never match inside head.
    m = re.search(
        r'## ' + re.escape(version) + r' release notes.*?\r?\n(.*?)(?=\r?\n## |\Z)',
        raw, re.S)
    if not m:
        sys.exit(f'could not extract the {version} block')
    block = m.group(1)

    entries = re.findall(r'<([a-zA-Z0-9\-]+)>\r?\n(.*?)\r?\n</\1>', block, re.S)
    seen, dupes = set(), []
    for loc, _ in entries:
        (dupes.append(loc) if loc in seen else seen.add(loc))
    if dupes:
        fails.append(f'duplicate locale tags: {sorted(set(dupes))}')

    found = [l for l, _ in entries]
    missing = [l for l in PLAY_ORDER if l not in found]
    extra = [l for l in found if l not in PLAY_ORDER]
    if missing:
        fails.append(f'MISSING {len(missing)} locale(s) Play expects: {missing}')
    if extra:
        fails.append(f'EXTRA locale(s) Play does not list: {extra}')

    if not missing and not extra and found != PLAY_ORDER:
        first = next(i for i, (a, b) in enumerate(zip(found, PLAY_ORDER)) if a != b)
        fails.append(f'locale ORDER differs from Play at position {first}: '
                     f'{found[first]!r} where Play has {PLAY_ORDER[first]!r} '
                     f'(reorder so the block pastes in one go)')

    for loc, body in entries:
        text = body.strip()
        n = len(text)
        if n > LIMIT:
            fails.append(f'{loc} is {n} chars, over Play\'s {LIMIT} cap '
                         f'(trim {n - LIMIT}+)')
        if not text:
            fails.append(f'{loc} is empty')
        elif PLACEHOLDER.search(text):
            fails.append(f'{loc} still contains placeholder text')
        if args.verbose:
            print(f'  {loc:<8} {n:>4}')

    print(f'release {version}: {len(entries)} locales, '
          f'longest {max((len(b.strip()) for _, b in entries), default=0)} chars '
          f'(cap {LIMIT})')

    if fails:
        print('\n!!! RELEASE NOTES NOT READY TO PASTE !!!')
        for f in fails:
            print(f'  · {f}')
        return 1
    print('OK — locale set and order match Play, every entry within the cap.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
