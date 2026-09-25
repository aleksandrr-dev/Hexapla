// The original-language interlinear (Interlinear.kt): word-aligned Strong's +
// morphology for the Greek NT (Byzantine, Robinson parsing, public domain) and
// the Hebrew Tanakh (Open Scriptures morphology, CC-BY). Live whenever the text
// on screen is grc or wlc: tap a word -> its Strong's entry and decoded parse.
// Data: `data/interlinear/{gr,he}/<b>.json` (build_web_data.py), each verse a
// space-separated tag list, one `strongs|morph` (or `-`) per word token.
//
// Pure: t() is passed in, so interlinear.test.ts runs it under node against
// the Kotlin itself (scripts/interlinear_oracle.ts). The grammar terms are the
// Android `morph_*` strings, each written as a literal t("...") call so
// scripts/strings.ts ships it.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type T = (key: any) => string;

/** Word tokens as the interlinear pipeline counts them: maximal runs of
 *  letters + combining marks (Interlinear.token). */
const TOKEN = /[\p{L}\p{M}]+/gu;
const LETTER = /\p{L}/u;

export const isOriginal = (id: string): boolean => id === "grc" || id === "wlc";

/** Which data set a book reads: Hebrew for the OT (0-38), Greek after. */
export const dataLang = (book: number): "he" | "gr" => (book < 39 ? "he" : "gr");

/** One tappable word: `[start, end)` in the verse text and its index among
 *  the verse's words. A run of marks with no letter is no word and takes no
 *  index (ReaderScreen.kt appendWordsIndexed). */
export interface Tok {
  s: number;
  e: number;
  i: number;
}

export function tokens(text: string): Tok[] {
  const out: Tok[] = [];
  let i = 0;
  for (const m of text.matchAll(TOKEN)) {
    if (!LETTER.test(m[0])) continue;
    const s = m.index ?? 0;
    out.push({ s, e: s + m[0].length, i: i++ });
  }
  return out;
}

/** [strongsId, morphCode] of word `index` in a verse's tag list, or null when
 *  the word is untagged (Interlinear.word). */
export function word(tags: string | undefined, index: number): [string, string] | null {
  if (tags === undefined || tags === "") return null;
  const tag = tags.split(" ")[index] as string | undefined;
  if (tag === undefined || tag === "-" || !tag.includes("|")) return null;
  const bar = tag.indexOf("|");
  return [tag.slice(0, bar), tag.slice(bar + 1)];
}

/** The human-readable parse: OSHM for the OT, Robinson for the NT. */
export function decode(t: T, book: number, morph: string): string {
  return book < 39 ? decodeOshm(t, morph) : decodeRobinson(t, morph);
}

// ---- Robinson (Greek) ----

const grkPos = (t: T): Record<string, string> => ({
  N: t("morph_noun"), A: t("morph_adjective"), T: t("morph_article"), V: t("morph_verb"),
  P: t("morph_pron_personal"), R: t("morph_pron_relative"), C: t("morph_pron_reciprocal"),
  D: t("morph_pron_demonstrative"), F: t("morph_pron_reflexive"), I: t("morph_pron_interrogative"),
  X: t("morph_pron_indefinite"), Q: t("morph_pron_correlative"), K: t("morph_pron_correlative"),
  S: t("morph_pron_possessive"), PRT: t("morph_particle"), PREP: t("morph_preposition"),
  CONJ: t("morph_conjunction"), COND: t("morph_cond_particle"), ADV: t("morph_adverb"),
  INJ: t("morph_interjection"), ARAM: t("morph_aramaic_word"), HEB: t("morph_hebrew_word"),
});
const grkTense = (t: T): Record<string, string> => ({
  P: t("morph_tense_present"), I: t("morph_tense_imperfect"), F: t("morph_tense_future"),
  A: t("morph_tense_aorist"), R: t("morph_tense_perfect"), L: t("morph_tense_pluperfect"),
});
const grkVoice = (t: T): Record<string, string> => ({
  A: t("morph_voice_active"), M: t("morph_voice_middle"), P: t("morph_voice_passive"),
  E: t("morph_voice_midpass"), D: t("morph_voice_mid_deponent"), O: t("morph_voice_pass_deponent"),
  N: t("morph_voice_midpass_deponent"), Q: t("morph_voice_impersonal"),
});
const grkMood = (t: T): Record<string, string> => ({
  I: t("morph_mood_indicative"), S: t("morph_mood_subjunctive"), O: t("morph_mood_optative"),
  M: t("morph_mood_imperative"), N: t("morph_mood_infinitive"), P: t("morph_mood_participle"),
});
const grkCase = (t: T): Record<string, string> => ({
  N: t("morph_case_nominative"), G: t("morph_case_genitive"), D: t("morph_case_dative"),
  A: t("morph_case_accusative"), V: t("morph_case_vocative"),
});
const grkGender = (t: T): Record<string, string> => ({ M: t("morph_masculine"), F: t("morph_feminine"), N: t("morph_neuter") });
const grkNumber = (t: T): Record<string, string> => ({ S: t("morph_singular"), P: t("morph_plural") });
// Trailing qualifiers and indeclinable markers (PRT-N, N-PRI, A-NUI, ADV-I...)
const grkQualifier = (t: T): Record<string, string> => ({
  PRI: t("morph_q_pri"), NUI: t("morph_q_nui"), LI: t("morph_q_li"), OI: t("morph_q_oi"),
  N: t("morph_q_negative"), I: t("morph_q_interrogative"), K: t("morph_q_crasis"),
  S: t("morph_q_superlative"), C: t("morph_q_comparative"), ATT: t("morph_q_att"),
  ABB: t("morph_q_abb"), P: t("morph_q_attached"),
});
const person = (t: T): Record<string, string> => ({ "1": t("morph_person_1"), "2": t("morph_person_2"), "3": t("morph_person_3") });

/** A table lookup that misses on an absent character, as Kotlin's `map[c]`
 *  on `getOrNull` (and never on an inherited key such as "constructor"). */
const at = (m: Record<string, string>, k: string | undefined): string | undefined => (k !== undefined && Object.prototype.hasOwnProperty.call(m, k) ? m[k] : undefined);

function grkCNG(t: T, p: string): string | null {
  if (p.length < 2) return null;
  const c = at(grkCase(t), p[0]);
  if (c === undefined) return null;
  const num = at(grkNumber(t), p[1]);
  if (num === undefined) return null;
  const gen = at(grkGender(t), p[2]);
  return [c, num, gen].filter((x) => x !== undefined).join(" ");
}

export function decodeRobinson(t: T, code: string): string {
  const parts = code.split("-");
  const pos = at(grkPos(t), parts[0]) ?? at(grkPos(t), code);
  if (pos === undefined) return code;
  if (parts.length === 1) return pos;
  const numbers = grkNumber(t);
  const persons = person(t);
  // Verb: tense/voice/mood, then person+number or case+number+gender
  if (parts[0] === "V") {
    let v = parts[1];
    const second = v.startsWith("2");
    if (second) v = v.slice(1);
    if (v.length >= 3) {
      const tense = (second ? t("morph_second") : "") + (v[0] === "X" ? "—" : at(grkTense(t), v[0]) ?? v[0]);
      const voice = v[1] === "X" ? "—" : at(grkVoice(t), v[1]) ?? v[1];
      const mood = at(grkMood(t), v[2]) ?? v[2];
      const p = parts[2] as string | undefined;
      let tail = "";
      if (p !== undefined) {
        if (p.length >= 2 && /\d/.test(p[0]) && at(persons, p[0]) !== undefined) tail = ", " + persons[p[0]] + " " + (at(numbers, p[1]) ?? p[1]);
        else {
          const cng = grkCNG(t, p);
          tail = cng === null ? "" : ", " + cng;
        }
      }
      // 4th part is a qualifier: V-RAI-3S-ATT (Attic form) etc.
      const q = at(grkQualifier(t), parts[3]);
      const extra = q === undefined ? "" : ", " + q;
      return pos + " — " + tense + " " + voice + " " + mood + tail + extra;
    }
  }
  const tail: string[] = [];
  for (const p of parts.slice(1)) {
    const pers = at(persons, p[0]);
    let x: string | null | undefined;
    // person + number (3S) or person + case+number(+gender) (1GS, 3ASM)
    if (pers !== undefined && p.length >= 2 && at(numbers, p[1]) !== undefined) x = pers + " " + numbers[p[1]];
    else if (pers !== undefined) {
      const cng = grkCNG(t, p.slice(1));
      x = cng === null ? null : pers + " " + cng;
    } else x = grkCNG(t, p) ?? at(grkQualifier(t), p);
    if (x !== null && x !== undefined) tail.push(x);
  }
  return tail.length === 0 ? pos + " " + parts.slice(1).join("-") : pos + " — " + tail.join(", ");
}

// ---- OSHM (Hebrew/Aramaic) ----

const hebStem = (t: T): Record<string, string> => ({
  q: t("morph_stem_qal"), N: t("morph_stem_niphal"), p: t("morph_stem_piel"), P: t("morph_stem_pual"),
  h: t("morph_stem_hiphil"), H: t("morph_stem_hophal"), t: t("morph_stem_hithpael"), o: t("morph_stem_polel"),
  O: t("morph_stem_polal"), r: t("morph_stem_hithpolel"), m: t("morph_stem_poel"), M: t("morph_stem_poal"),
  k: t("morph_stem_palel"), K: t("morph_stem_pulal"), Q: t("morph_stem_qal_passive"), l: t("morph_stem_pilpel"),
  L: t("morph_stem_polpal"), f: t("morph_stem_hithpalpel"), D: t("morph_stem_nithpael"), j: t("morph_stem_pealal"),
  i: t("morph_stem_pilel"), u: t("morph_stem_hothpaal"), c: t("morph_stem_tiphil"), v: t("morph_stem_hishtaphel"),
  w: t("morph_stem_nithpalel"), y: t("morph_stem_nithpoel"), z: t("morph_stem_hithpoel"),
  // Aramaic stems (book of Daniel/Ezra portions)
  a: t("morph_stem_peal"), b: t("morph_stem_peil"), e: t("morph_stem_hithpeel"), s: t("morph_stem_saphel"),
  d: t("morph_stem_pael"), g: t("morph_stem_ithpaal"), x: t("morph_stem_ithpeel"),
});
const hebConj = (t: T): Record<string, string> => ({
  p: t("morph_hconj_perfect"), q: t("morph_hconj_seq_perfect"), i: t("morph_hconj_imperfect"),
  w: t("morph_hconj_seq_imperfect"), h: t("morph_hconj_cohortative"), j: t("morph_hconj_jussive"),
  v: t("morph_hconj_imperative"), r: t("morph_hconj_participle"), s: t("morph_hconj_passive_participle"),
  a: t("morph_hconj_inf_absolute"), c: t("morph_hconj_inf_construct"),
});
const hebGender = (t: T): Record<string, string> => ({ m: t("morph_masculine"), f: t("morph_feminine"), b: t("morph_common"), c: t("morph_common") });
const hebNumber = (t: T): Record<string, string> => ({ s: t("morph_singular"), p: t("morph_plural"), d: t("morph_dual") });
const hebState = (t: T): Record<string, string> => ({ a: t("morph_state_absolute"), c: t("morph_state_construct"), d: t("morph_state_determined") });

/* OSHM tails are positional; a per-character lookup mislabels the state slot
   ('c' construct reads as gender "common", Aramaic 'd' determined as number
   "dual"). */

const joinSome = (xs: (string | undefined)[], sep: string): string => xs.filter((x) => x !== undefined).join(sep);

/** gender + number + state — nouns, adjectives, participles. */
const hebGNS = (t: T, p: string): string => joinSome([at(hebGender(t), p[0]), at(hebNumber(t), p[1]), at(hebState(t), p[2])], " ");

/** person + gender + number — pronouns, suffixes, finite verbs (the person
 *  slot may be 'x' = unmarked, which simply drops out). */
const hebPGN = (t: T, p: string): string => joinSome([at(person(t), p[0]), at(hebGender(t), p[1]), at(hebNumber(t), p[2])], " ");

const kindTail = (kind: string, tail: string): string => (tail === "" ? kind : kind + ", " + tail);
const notBlank = (s: string): boolean => s.trim() !== "";

function decodeSegment(t: T, seg: string): string {
  if (seg === "") return "";
  const k = seg[1] as string | undefined;
  switch (seg[0]) {
    case "C":
      return t("morph_conjunction");
    case "D":
      return t("morph_adverb");
    case "R":
      return k === "d" ? t("morph_prep_article") : t("morph_preposition");
    case "T":
      switch (k) {
        case "d": return t("morph_article");
        case "a": return t("morph_affirmation");
        case "e": return t("morph_exhortation");
        case "i": return t("morph_int_particle");
        case "j": return t("morph_interjection");
        case "n": return t("morph_neg_particle");
        case "o": return t("morph_obj_marker");
        case "r": return t("morph_rel_particle");
        default: return t("morph_particle");
      }
    case "N": {
      const kind = k === "p" ? t("morph_proper_noun") : k === "g" ? t("morph_gentilic_noun") : t("morph_noun");
      return kindTail(kind, hebGNS(t, seg.slice(2)));
    }
    case "A": {
      const kind = k === "c" ? t("morph_cardinal") : k === "o" ? t("morph_ordinal") : k === "g" ? t("morph_gentilic_adj") : t("morph_adjective");
      return kindTail(kind, hebGNS(t, seg.slice(2)));
    }
    case "P": {
      const kind =
        k === "d" ? t("morph_pron_demonstrative")
        : k === "i" ? t("morph_pron_interrogative")
        : k === "p" ? t("morph_pron_personal")
        : k === "r" ? t("morph_pron_relative")
        : k === "f" ? t("morph_pron_indefinite")
        : t("morph_pronoun");
      return kindTail(kind, hebPGN(t, seg.slice(2)));
    }
    case "S":
      switch (k) {
        case "d": return t("morph_suffix_dir");
        case "h": return t("morph_paragogic_he");
        case "n": return t("morph_paragogic_nun");
        case "p": return kindTail(t("morph_suffix_pron"), hebPGN(t, seg.slice(2)));
        default: return t("morph_suffix");
      }
    case "V": {
      // Kotlin's "${seg.getOrNull(1)}" prints "null" for a bare "V".
      const stem = at(hebStem(t), k) ?? (k === undefined ? "null" : k);
      const conjCh = seg[2] as string | undefined;
      const conj = at(hebConj(t), conjCh) ?? "";
      // Participles decline like nouns (gender-number-state); finite forms
      // conjugate (person-gender-number).
      const tail = conjCh === "r" || conjCh === "s" ? hebGNS(t, seg.slice(3)) : hebPGN(t, seg.slice(3));
      return [t("morph_verb"), stem, conj, tail].filter(notBlank).join(", ");
    }
    default:
      return seg;
  }
}

export function decodeOshm(t: T, code: string): string {
  if (code === "") return code;
  const aramaic = code[0] === "A";
  const parts = code
    .slice(1)
    .split("/")
    .map((s) => decodeSegment(t, s))
    .filter(notBlank);
  return (aramaic ? t("morph_aramaic_prefix") : "") + parts.join(" + ");
}

/** Every lookup table by its Interlinear.kt name, for interlinear.test.ts. */
export function tables(t: T): Record<string, Record<string, string>> {
  return {
    grkPos: grkPos(t), grkTense: grkTense(t), grkVoice: grkVoice(t), grkMood: grkMood(t), grkCase: grkCase(t),
    grkGender: grkGender(t), grkNumber: grkNumber(t), grkQualifier: grkQualifier(t), person: person(t),
    hebStem: hebStem(t), hebConj: hebConj(t), hebGender: hebGender(t), hebNumber: hebNumber(t), hebState: hebState(t),
  };
}
