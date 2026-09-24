// Strong's numbers over the KJV (Bible.kt `StrongsRepo`): the tagged text
// `data/kjv_strongs/<b>.json` is shown INSTEAD of the plain KJV verse when the
// setting is on and the KJV is the primary translation. Display only — search,
// copy, marks and the narration keep reading the plain text, which the build
// guarantees is the tagged text with its tags removed (build_web_data.py
// check_strongs_text).
//
// Pure: no imports, so strongs.test.ts runs it under node.

/** `[H7225]`, `[G2316]` — the same pattern as `StrongsRepo.tag`. */
const TAG = /\[([HG]\d+)\]/g;

/** A run of verse text, or one Strong's number sitting after its word. */
export type Seg = { text: string } | { id: string };

/** Tagged verse -> text runs and ids, in order. Empty runs are dropped, so
 *  `created[H1254][H853]` is one run and two ids. */
export function segments(tagged: string): Seg[] {
  const out: Seg[] = [];
  let pos = 0;
  for (const m of tagged.matchAll(TAG)) {
    const at = m.index ?? 0;
    if (at > pos) out.push({ text: tagged.slice(pos, at) });
    out.push({ id: m[1] });
    pos = at + m[0].length;
  }
  if (pos < tagged.length) out.push({ text: tagged.slice(pos) });
  return out;
}

/** The tag-free text, whitespace as the source has it. */
export function untag(tagged: string): string {
  return tagged.replace(TAG, "");
}

/** Segments as they are SHOWN: whitespace collapsed and trimmed the way
 *  parseAsset does the plain verse, so their text runs join to exactly the
 *  plain KJV verse (build_web_data.check_strongs_text). A number ahead of the
 *  first word (`[G1161] In those days`, an untranslated particle) moves to just
 *  after that word, so a drop cap is always a letter. */
export function shown(tagged: string): Seg[] {
  const segs: Seg[] = [];
  for (const s of segments(tagged)) {
    if ("id" in s) {
      segs.push(s);
      continue;
    }
    const prev = segs.length > 0 ? segs[segs.length - 1] : null;
    const endsSpace = /\s$/.test(joined(segs));
    let t = s.text.replace(/\s+/g, " ");
    if (joined(segs) === "" || endsSpace) t = t.replace(/^ /, "");
    if (t === "") continue;
    if (prev !== null && "text" in prev) prev.text += t;
    else segs.push({ text: t });
  }
  // trailing whitespace
  for (let i = segs.length - 1; i >= 0; i -= 1) {
    const s = segs[i];
    if (!("text" in s)) continue;
    s.text = s.text.replace(/ $/, "");
    if (s.text === "") segs.splice(i, 1);
    else break;
  }
  // leading ids -> after the first word
  let lead = 0;
  while (lead < segs.length && "id" in segs[lead]) lead += 1;
  if (lead > 0 && lead < segs.length) {
    const first = segs[lead] as { text: string };
    const m = /^\S+/.exec(first.text);
    const word = m === null ? "" : m[0];
    const rest = first.text.slice(word.length);
    const out: Seg[] = [{ text: word }, ...segs.slice(0, lead)];
    if (rest !== "") out.push({ text: rest });
    return [...out, ...segs.slice(lead + 1)];
  }
  return segs;
}

function joined(segs: Seg[]): string {
  return segs.map((s) => ("text" in s ? s.text : "")).join("");
}

/** The text runs of `shown(...)` joined: the plain KJV verse. */
export function shownText(segs: Seg[]): string {
  return joined(segs);
}

/** `segs` with the first `n` characters of TEXT removed (a drop cap already
 *  drew them); ids are never dropped. */
export function afterCap(segs: Seg[], n: number): Seg[] {
  const out: Seg[] = [];
  let left = n;
  for (const s of segs) {
    if ("text" in s && left > 0) {
      const cut = Math.min(left, s.text.length);
      left -= cut;
      if (cut < s.text.length) out.push({ text: s.text.slice(cut) });
    } else out.push(s);
  }
  return out;
}

/** The superscript shown for an id: its number without the H/G, as Android
 *  (`append(id.drop(1))`). */
export function shownNumber(id: string): string {
  return id.slice(1);
}

/** One lexicon row as `strongs_lexicon*.json` stores it: word, transliteration,
 *  part of speech, definition. Any field may be missing or blank. */
export interface RawEntry {
  w?: string;
  t?: string;
  p?: string;
  d?: string;
}
export type RawLexicon = Record<string, RawEntry>;

export interface Entry {
  word: string;
  translit: string;
  pos: string;
  def: string;
}
export type Lexicon = Record<string, Entry>;

/** Languages with a translated gloss file `strongs_lexicon_<lang>.json`
 *  (StrongsRepo.translatedLexicons). Everything else reads English. */
export const TRANSLATED: readonly string[] = ["ru"];

/** The translated lexicon to use for a UI language tag ("ru-RU" -> "ru"), or
 *  null for English. */
export function lexiconLang(tag: string): string | null {
  const l = tag.toLowerCase().split("-")[0];
  return TRANSLATED.includes(l) ? l : null;
}

function entry(e: RawEntry): Entry {
  return { word: e.w ?? "", translit: e.t ?? "", pos: e.p ?? "", def: e.d ?? "" };
}

const blankOr = (s: string, dflt: string | undefined): string => (s.trim() === "" ? dflt ?? "" : s);

/** English, with the translated gloss swapped in PER ID and PER FIELD — the
 *  translated source lacks some ids and carries no transliteration or part
 *  of speech at all (StrongsRepo.entry). `translated` null = English only. */
export function mergeLexicon(english: RawLexicon, translated: RawLexicon | null): Lexicon {
  const m: Lexicon = {};
  for (const k of Object.keys(english)) m[k] = entry(english[k]);
  if (translated === null) return m;
  for (const k of Object.keys(translated)) {
    const t = entry(translated[k]);
    const en = m[k] as Entry | undefined;
    m[k] = {
      word: blankOr(t.word, en?.word),
      translit: blankOr(t.translit, en?.translit),
      pos: blankOr(t.pos, en?.pos),
      def: blankOr(t.def, en?.def),
    };
  }
  return m;
}

/** The line under the title: transliteration · part of speech, blanks left out. */
export function subline(e: Entry): string {
  return [e.translit, e.pos].filter((x) => x.trim() !== "").join(" · ");
}
