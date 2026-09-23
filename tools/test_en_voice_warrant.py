# -*- coding: utf-8 -*-
"""Control for the 2026-09-13 widening of the pronunciation lexicon to `en`.

    python tools/test_en_voice_warrant.py              # must exit 0
    HEXAPLA_NO_WARRANT=1 python tools/test_en_voice_warrant.py   # must exit 1

## What it guards

On 2026-09-13 every `pronounce_lexicon` row was widened from `ylt` to
`("ylt", "en")`. The rows were NOT re-heard on the KJV set; the warrant is that
`en` and `ylt` are the SAME VOICE — narrate.py points both at the same
reference recording, with the same engine and the same knobs. Every ylt ear
test was therefore an ear test on this voice.

⛔ **That warrant is a fact about narrate.py's config, and config drifts.** If
`en`'s `voice` is ever repointed at another reference (it was
`_en_ref_kjv.wav` with kokoro `am_adam` until 2026-09-10), the widening becomes
18 rows nobody ever heard on the voice that is actually speaking — silently,
across 1,371 chapters. This test is what makes that loud.

⚠ It does NOT check that any respelling is correct. Only an ear does that. It
checks that the CONDITION under which the clearances were transferred still
holds.

## The known-bad control

`HEXAPLA_NO_WARRANT=1` simulates the drift (it rewrites the compared value in
memory only, nothing on disk). If BOTH runs exit 0 this test is inert and
proves nothing — that is the failure mode the project cares about most.
"""
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

NARRATE = HERE / "narrate.py"
BROKEN = os.environ.get("HEXAPLA_NO_WARRANT") == "1"


def voice_of(src, lang):
    """-> the `voice` expression for one set in narrate.py's config, as source text."""
    m = re.search(r'"%s":\s*\{(.*?)\n    \}' % re.escape(lang), src, re.S)
    if not m:
        return None
    v = re.search(r'"voice":\s*(.+?),\s*\n', m.group(1))
    return v.group(1).strip() if v else None


def main():
    src = NARRATE.read_text(encoding="utf-8")
    en = voice_of(src, "en")
    ylt = voice_of(src, "ylt")

    if BROKEN:
        # the drift this test exists to catch: en repointed at its own recording
        en = 'str(OUTPUT / "_en_ref_kjv.wav")'

    print("narrate.py  en  voice: %s" % en)
    print("narrate.py  ylt voice: %s" % ylt)

    fail = 0
    if en is None or ylt is None:
        print("FAIL: could not read one of the voice settings (config shape changed?)")
        fail += 1
    elif en != ylt:
        print("FAIL: `en` no longer shares ylt's reference recording.")
        print("      The lexicon widening to `en` is VOID -- 18 rows are now")
        print("      applied to a voice nobody heard them on. Either repoint")
        print("      `en` back, or drop `en` from every row and re-run the ear.")
        fail += 1
    else:
        print("ok: en and ylt share one reference recording")

    import pronounce_lexicon as L
    rows = L.rows_for("en")
    total = len(L.LEXICON)
    print("lexicon rows cleared for en: %d of %d" % (len(rows), total))
    if len(rows) != total:
        missing = sorted(set(L.LEXICON) - set(rows))
        print("FAIL: rows not cleared for en: %s" % missing)
        fail += 1
    else:
        print("ok: every row is cleared for en")

    # the engine and the knobs matter as much as the file
    for field, want in (("engine", '"chatterbox"'), ("cfg_weight", "0.5"),
                        ("exaggeration", "1.0")):
        blk_en = re.search(r'"en":\s*\{(.*?)\n    \}', src, re.S).group(1)
        blk_ylt = re.search(r'"ylt":\s*\{(.*?)\n    \}', src, re.S).group(1)
        a = re.search(r'"%s":\s*(.+?),' % field, blk_en)
        b = re.search(r'"%s":\s*(.+?),' % field, blk_ylt)
        a = a.group(1).strip() if a else None
        b = b.group(1).strip() if b else None
        if a != b:
            print("FAIL: %s differs -- en=%s ylt=%s" % (field, a, b))
            fail += 1
        else:
            print("ok: %s matches (%s)" % (field, a))

    print()
    print("WARRANT INTACT" if not fail else "WARRANT BROKEN (%d check(s) failed)" % fail)
    return 1 if fail else 0


sys.exit(main())
