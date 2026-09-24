// Per-verse typography rules ported from ReaderScreen.kt, so the web reader
// lays text out the way the Android app does. Pure: no imports.

const RTL_STRONG = /[֐-ࣿיִ-﷿ﹰ-﻿]/u;
const LTR_STRONG = /\p{L}/u;

/** Direction of the first strong letter, as `textIsRtl` in ReaderScreen.kt:
 *  "rtl", "ltr", or null when the text has no strong letter (then the caller
 *  inherits). Each verse gets its own, so a Persian verse quoting a Latin
 *  name, or a Hebrew word inside an English note, lays out as the app does. */
export function directionOf(s: string): "rtl" | "ltr" | null {
  for (const ch of s) {
    if (RTL_STRONG.test(ch)) return "rtl";
    if (LTR_STRONG.test(ch)) return "ltr";
  }
  return null;
}

// Scripts whose printed Bibles set a chapter's first letter as a drop cap
// (DROP_CAP_SCRIPTS). RTL and CJK never get one.
const DROP_CAP_SCRIPT = /[\p{Script=Latin}\p{Script=Cyrillic}\p{Script=Greek}\p{Script=Armenian}\p{Script=Georgian}]/u;
const LETTER = /\p{L}/u;
const MARK = /\p{M}/u;
const SPACE = /\s/u;

/** End offset (in UTF-16 units) of the drop-cap initial — up to two leading
 *  quote/bracket marks, the first letter and its combining marks — or -1 when
 *  the verse gets none. Same rule as `dropCapEnd` in ReaderScreen.kt. */
export function dropCapEnd(text: string): number {
  let i = 0;
  let lead = 0;
  for (;;) {
    const cp = text.codePointAt(i);
    if (cp === undefined) return -1;
    const ch = String.fromCodePoint(cp);
    if (LETTER.test(ch)) break;
    lead += 1;
    if (SPACE.test(ch) || lead > 2) return -1;
    i += ch.length;
  }
  const first = String.fromCodePoint(text.codePointAt(i) as number);
  if (!DROP_CAP_SCRIPT.test(first)) return -1;
  i += first.length;
  for (;;) {
    const cp = text.codePointAt(i);
    if (cp === undefined) break;
    const ch = String.fromCodePoint(cp);
    if (!MARK.test(ch)) break;
    i += ch.length;
  }
  // A one-letter verse would leave the body empty.
  return i < text.length ? i : -1;
}

/** Chinese and Japanese: set justified on a character grid with strict
 *  line-breaking, as they are printed, never ragged-right. */
export function isCjk(lang: string): boolean {
  return /^(ja|zh)(-|$)/.test(lang);
}
