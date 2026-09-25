// Reading aloud with the device's own voice (Web Speech) for a chapter that
// has no recording — the web half of the Android TTS path (ReadingService's
// speakVerse + Pronounce.kt). Pure: node-tested by speech.test.ts; the
// speechSynthesis calls live in player.ts.
//
// Same rules as Android, point for point:
//  - ONE verse per utterance, the next one queued only when it ends — never a
//    chapter pre-queued (a long queue is what a pause or a skip cannot undo,
//    and Chrome cuts an utterance off after ~15 s);
//  - SPEAK the normalized form, DISPLAY the original (Pronounce.forSpeech):
//    Tyndale/Geneva/Wycliffe spelling read literally is "yow", "lickness",
//    and "heauen" as "hoenn";
//  - a voice per LANGUAGE, remembered, «System default» otherwise.
//
// What the web adds: the voice reports word boundaries in the SPOKEN text,
// and the reader highlights words in the DISPLAYED text, so every rewrite
// below carries an offset map back to the original (`src`).

/** A `pron_*.json` table (tools/build_tyndale_pron.py). */
export interface PronTable {
  words: Record<string, string>;
  roman?: Record<string, number>;
  phrases?: Record<string, string>;
}

/** Web translation id -> the Android id its table is built for. */
export const PRON_ASSET: Record<string, string> = {
  tyn: "pron_tyndale.json",
  gen1599: "pron_gnv.json",
  wyc: "pron_wyc.json",
};

/** Owner-reported respellings (Pronounce.PHONETIC): every English set. */
const PHONETIC: Record<string, string> = { babel: "Babbel", babels: "Babbels" };

/** Names the Early Modern rules would wrongly change (Pronounce.RULE_EXCEPTIONS). */
const RULE_EXCEPTIONS = new Set(["deuel", "geuel", "euodias", "iim", "reuel"]);

const VOWELS = "aeiou";

/** Text as spoken, and for each of its characters the index in the original
 *  it came from. A replacement maps its characters onto the span it replaced
 *  (clamped), so any boundary inside it lands inside that original word. */
export interface Spoken {
  text: string;
  src: number[];
}

function replaceMapped(s: Spoken, re: RegExp, fn: (m: RegExpExecArray) => string): Spoken {
  let text = "";
  const src: number[] = [];
  let last = 0;
  re.lastIndex = 0;
  for (let m = re.exec(s.text); m !== null; m = re.exec(s.text)) {
    if (m[0].length === 0) {
      re.lastIndex += 1;
      continue;
    }
    const r = fn(m);
    text += s.text.slice(last, m.index);
    for (let i = last; i < m.index; i++) src.push(s.src[i]);
    const span = m[0].length;
    for (let k = 0; k < r.length; k++) src.push(s.src[m.index + Math.min(k, span - 1)]);
    text += r;
    last = m.index + m[0].length;
  }
  text += s.text.slice(last);
  for (let i = last; i < s.text.length; i++) src.push(s.src[i]);
  return { text, src };
}

// HEXAPLA_SPEECH_BAD=1 only under node (the test); a browser has no process.
function process_bad(): boolean {
  const p = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
  return p?.env?.HEXAPLA_SPEECH_BAD === "1";
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function romanValue(s: string): number | null {
  const v: Record<string, number> = { i: 1, v: 5, x: 10, l: 50, c: 100, d: 500, m: 1000 };
  const t = s.toLowerCase().replace(/j/g, "i");
  if (t === "" || [...t].some((c) => !(c in v))) return null;
  let total = 0;
  for (let i = 0; i < t.length; i++) {
    const cur = v[t[i]];
    const next = i + 1 < t.length ? v[t[i + 1]] : undefined;
    total += next !== undefined && next > cur ? -cur : cur;
  }
  return total > 0 ? total : null;
}

const isUpper = (c: string): boolean => c !== c.toLowerCase() && c === c.toUpperCase();

/** Pronounce.earlyModern: initial I+vowel -> J, intervocalic u -> v, initial v+consonant -> u. */
function earlyModern(w: string): string {
  if (w.length < 2 || RULE_EXCEPTIONS.has(w.toLowerCase())) return w;
  let s = w;
  if (s[0].toLowerCase() === "i" && VOWELS.includes(s[1].toLowerCase())) s = (isUpper(s[0]) ? "J" : "j") + s.slice(1);
  if (s.length > 2) {
    const b = [...s];
    for (let i = 1; i < s.length - 1; i++) {
      if (s[i].toLowerCase() === "u" && VOWELS.includes(s[i - 1].toLowerCase()) && VOWELS.includes(s[i + 1].toLowerCase())) b[i] = isUpper(s[i]) ? "V" : "v";
    }
    s = b.join("");
  }
  if (s[0].toLowerCase() === "v" && !VOWELS.includes(s[1].toLowerCase())) s = (isUpper(s[0]) ? "U" : "u") + s.slice(1);
  return s;
}

function applyPhonetic(s: Spoken): Spoken {
  return replaceMapped(s, /[A-Za-z]+/g, (m) => {
    const hint = PHONETIC[m[0].toLowerCase()];
    if (hint === undefined) return m[0];
    return isUpper(m[0][0]) ? hint : hint[0].toLowerCase() + hint.slice(1);
  });
}

/** Pronounce.forSpeech, with the offset map. `english` = the translation's
 *  language is English (Kotlin's ENGLISH set is exactly the English sets). */
export function forSpeech(text: string, english: boolean, table: PronTable | null): Spoken {
  // Indexed in UTF-16 units, as the voice's charIndex and the reader's ranges are.
  let s: Spoken = { text, src: Array.from({ length: text.length }, (_, i) => i) };
  if (table === null) return english ? applyPhonetic(s) : s;
  for (const [from, to] of Object.entries(table.phrases ?? {})) {
    s = replaceMapped(s, new RegExp("\\b" + escapeRe(from) + "\\b", "gi"), () => to);
  }
  s = replaceMapped(s, /\b([A-Z][A-Za-z]*)-([A-Za-z]+)/g, (m) => m[1] + m[2]);
  s = replaceMapped(s, /\.\s*([ivxlcdmIVXLCDMj]+)\s*\./g, (m) => {
    const n = romanValue(m[1]);
    return n === null ? m[0] : " " + String(n) + " ";
  });
  s = replaceMapped(s, /[A-Za-z]+/g, (m) => {
    const w = m[0];
    const repl = table.words[w.toLowerCase()];
    if (repl === undefined) return earlyModern(w);
    if (w.length > 1 && [...w].every(isUpper)) return repl.toUpperCase();
    if (isUpper(w[0])) return repl[0].toUpperCase() + repl.slice(1);
    return repl;
  });
  return english ? applyPhonetic(s) : s;
}

const WORDCH = /[\p{L}\p{M}\p{N}'’]/u;

/** The displayed word a boundary at spoken `charIndex` falls on, as a
 *  [start, end) range in the original text; null past the end or on a space. */
export function wordOf(original: string, sp: Spoken, charIndex: number): [number, number] | null {
  if (charIndex < 0 || charIndex >= sp.src.length || (process_bad() && charIndex >= original.length)) return null;
  // Known-bad control (node only): the spoken index used as if it were the
  // displayed one - right until the first rewrite changes a length.
  let i = process_bad() ? charIndex : sp.src[charIndex];
  // A boundary may sit on the space or punctuation before the word.
  while (i < original.length && !WORDCH.test(original[i])) i++;
  if (i >= original.length) return null;
  let a = i;
  let b = i;
  while (a > 0 && WORDCH.test(original[a - 1])) a--;
  while (b < original.length && WORDCH.test(original[b])) b++;
  return [a, b];
}

/** The part of SpeechSynthesisVoice this needs (so node can test it). */
export interface VoiceLike {
  name: string;
  lang: string;
  localService: boolean;
  default: boolean;
}

/** BCP 47 translation tag -> the region a voice should prefer, where the
 *  script decides it (a zh-Hant text read by a mainland voice is wrong). */
const PREFER: Record<string, string[]> = { "zh-hant": ["zh-tw", "zh-hk"], "zh-hans": ["zh-cn"], zh: ["zh-cn"] };

/** The voices that can read `lang`, best first: exact region preference,
 *  on-device before network (a network voice goes silent offline), then the
 *  browser's default. Primary subtags must match; «sr-Latn» takes any sr. */
export function voicesFor(voices: VoiceLike[], lang: string): VoiceLike[] {
  const tag = lang.toLowerCase();
  const primary = tag.split("-")[0];
  const pref = PREFER[tag] ?? [];
  const norm = (v: VoiceLike) => v.lang.toLowerCase().replace(/_/g, "-");
  const fits = voices.filter((v) => norm(v).split("-")[0] === primary);
  const rank = (v: VoiceLike) => {
    const i = pref.findIndex((p) => norm(v).startsWith(p));
    return (i < 0 ? pref.length : i) * 4 + (v.localService ? 0 : 2) + (v.default ? 0 : 1);
  };
  return fits.map((v, i) => ({ v, i, r: rank(v) })).sort((x, y) => x.r - y.r || x.i - y.i).map((x) => x.v);
}

/** The voice to use: the remembered one if it still exists, else the best. */
export function pickVoice(voices: VoiceLike[], lang: string, remembered: string | undefined): VoiceLike | null {
  const fits = voicesFor(voices, lang);
  return fits.find((v) => v.name === remembered) ?? fits[0] ?? null;
}

/** The language key a remembered voice is stored under (Android keys its
 *  voicePrefs by Locale.language, the primary subtag). */
export const voiceKey = (lang: string): string => lang.toLowerCase().split("-")[0];
