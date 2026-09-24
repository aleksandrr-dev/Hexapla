// Webster's 1828 American Dictionary (Bible.kt `Webster1828`): tap a word in
// an English translation for what it meant in the era of the classic Bibles.
// The dictionary is built as `data/webster/<L>.json`, one file per first
// letter (build_web_data.bucket_letter), fetched only when a word is tapped.
//
// Pure: no imports, so webster.test.ts runs it under node. The lookup chain is
// a PORT of Webster1828.candidates — webster.test.ts reads the irregular map
// out of Bible.kt and fails on any drift.

/** KJV-frequent forms the 1828 lacks as headwords (or spells otherwise).
 *  Bible.kt `irregular`, in the same order. */
export const IRREGULAR: Readonly<Record<string, string>> = {
  HATH: "HAVE", DOTH: "DO", DOST: "DO", DIDST: "DO",
  SAITH: "SAY", SAIDST: "SAY", SHALT: "SHALL", WILT: "WILL",
  CANST: "CAN", COULDEST: "COULD", WOULDEST: "WOULD",
  SHOULDEST: "SHOULD", MIGHTEST: "MIGHT", MAYEST: "MAY",
  SHEW: "SHOW", SHEWED: "SHOW", SHEWETH: "SHOW",
  SHEWN: "SHOW", SHEWING: "SHOW", SHEWBREAD: "SHOW-BREAD",
  BEGAT: "BEGET", BEGOTTEN: "BEGET", SLEW: "SLAY", SLAIN: "SLAY",
  SMOTE: "SMITE", SMITTEN: "SMITE", TRODDEN: "TREAD", TROD: "TREAD",
  BADE: "BID", FORBADE: "FORBID", GAVEST: "GIVE", GAVE: "GIVE",
  TOOK: "TAKE", TOOKEST: "TAKE", TAKEN: "TAKE", WENT: "GO",
  WENTEST: "GO", CAME: "COME", CAMEST: "COME", SAW: "SEE",
  SAWEST: "SEE", SEEN: "SEE", STOOD: "STAND", STOODEST: "STAND",
  BROUGHT: "BRING", BROUGHTEST: "BRING", SOUGHT: "SEEK",
  FOUGHT: "FIGHT", BOUGHT: "BUY", TAUGHT: "TEACH", CAUGHT: "CATCH",
  KEPT: "KEEP", SLEPT: "SLEEP", WEPT: "WEEP", SWEPT: "SWEEP",
  FLED: "FLEE", FED: "FEED", LED: "LEAD", LEDDEST: "LEAD",
  MET: "MEET", HELD: "HOLD", HELDEST: "HOLD", TOLD: "TELL",
  TOLDEST: "TELL", SOLD: "SELL", SENT: "SEND", SENTEST: "SEND",
  SPENT: "SPEND", BENT: "BEND", LENT: "LEND", RENT: "REND",
  BUILT: "BUILD", SAT: "SIT", SATEST: "SIT", LAY: "LIE",
  LAIN: "LIE", MADE: "MAKE", MADEST: "MAKE", SPOKEN: "SPEAK",
  CHOSE: "CHOOSE", CHOSEN: "CHOOSE", DROVE: "DRIVE",
  DRIVEN: "DRIVE", RODE: "RIDE", RIDDEN: "RIDE", ROSE: "RISE",
  RISEN: "RISE", AROSE: "ARISE", ARISEN: "ARISE", WROTE: "WRITE",
  WRITTEN: "WRITE", SWORE: "SWEAR", SWORN: "SWEAR", TORE: "TEAR",
  TORN: "TEAR", WORE: "WEAR", WORN: "WEAR", BORE: "BEAR",
  BORNE: "BEAR", BORN: "BEAR", GRAVEN: "GRAVE", HEWN: "HEW",
  SOWN: "SOW", MOWN: "MOW", KNOWN: "KNOW", KNEW: "KNOW",
  KNEWEST: "KNOW", GREW: "GROW", GROWN: "GROW", THREW: "THROW",
  THROWN: "THROW", BLEW: "BLOW", BLOWN: "BLOW", FLEW: "FLY",
  FLOWN: "FLY", DREW: "DRAW", DRAWN: "DRAW", DRAWEST: "DRAW",
  ATE: "EAT", EATEN: "EAT", DRANK: "DRINK", DRUNK: "DRINK",
  DRUNKEN: "DRINK", SANG: "SING", SUNG: "SING", RANG: "RING",
  RUNG: "RING", SANK: "SINK", SUNK: "SINK", SUNKEN: "SINK",
  SWAM: "SWIM", SWUM: "SWIM", RAN: "RUN", WON: "WIN",
  SHONE: "SHINE", STRUCK: "STRIKE", STRICKEN: "STRIKE",
  STOLE: "STEAL", STOLEN: "STEAL", FELL: "FALL", FELLEST: "FALL",
  FALLEN: "FALL", FORGAVE: "FORGIVE", FORGIVEN: "FORGIVE",
  FORSOOK: "FORSAKE", FORSAKEN: "FORSAKE", FOUND: "FIND",
  FOUNDEST: "FIND", GROUND: "GRIND", BOUND: "BIND", WOUND: "WIND",
  HID: "HIDE", HIDDEN: "HIDE", BITTEN: "BITE", BIT: "BITE",
  SHOT: "SHOOT", GOT: "GET", GOTTEN: "GET", GAT: "GET",
  BESOUGHT: "BESEECH", WROUGHT: "WORK", LEFT: "LEAVE",
  LOST: "LOSE", PAID: "PAY", LAID: "LAY", LAIDST: "LAY",
  SAID: "SAY", HEARD: "HEAR", HEARDEST: "HEAR", MEANT: "MEAN",
  FELT: "FEEL", DEALT: "DEAL", KNELT: "KNEEL", DWELT: "DWELL",
  SPAT: "SPIT", CLAD: "CLOTHE", SHOD: "SHOE",
  WAS: "BE", WAST: "BE", WERT: "BE", WERE: "BE", BEEN: "BE",
  AM: "BE", IS: "BE", ARE: "BE", HAD: "HAVE", HADST: "HAVE",
  HAS: "HAVE", HAST: "HAVE", HAVING: "HAVE", DID: "DO",
  DONE: "DO", DOES: "DO",
  MEN: "MAN", WOMEN: "WOMAN", CHILDREN: "CHILD",
  BRETHREN: "BROTHER", KINE: "COW", OXEN: "OX", FEET: "FOOT",
  TEETH: "TOOTH", GEESE: "GOOSE", MICE: "MOUSE", LICE: "LOUSE",
  DIED: "DIE", DIETH: "DIE", DYING: "DIE", LIETH: "LIE",
  LYING: "LIE", SPUE: "SPEW", SPUED: "SPEW",
  MARISHES: "MARSH", MARISH: "MARSH", AGONE: "AGO",
  STRAWED: "STREW", WOE: "WO", BEGAN: "BEGIN", BEGUN: "BEGIN",
  YOURSELVES: "YOURSELF", OURSELVES: "OURSELF",
  SELVES: "SELF", WOLVES: "WOLF", CALVES: "CALF",
  HALVES: "HALF", LOAVES: "LOAF", LIVES: "LIFE",
  WIVES: "WIFE", KNIVES: "KNIFE", THIEVES: "THIEF",
  SHEAVES: "SHEAF", LEAVES: "LEAF", STAVES: "STAFF",
  HOOVES: "HOOF",
};

const VOWELS = "AEIOU";
const SUFFIXES = ["ETH", "EST", "ES", "ED", "ING", "S"];

/** Kotlin's `Char.isLetter()` for the trim, as a test on one character. */
const isLetter = (c: string) => /\p{L}/u.test(c);

/** Lookup candidates for a tapped word, most specific first
 *  (Webster1828.candidates, step for step). */
export function candidates(word: string): string[] {
  let w = word.toUpperCase().replace(/’/g, "'");
  let a = 0;
  let b = w.length;
  while (a < b && !isLetter(w[a])) a += 1;
  while (b > a && !isLetter(w[b - 1])) b -= 1;
  w = w.slice(a, b);
  const out = [w];
  const irr = IRREGULAR[w];
  if (irr !== undefined) {
    out.push(irr);
    return out;
  }
  if (w.endsWith("'S")) {
    w = w.slice(0, -2);
    out.push(w);
  } else if (w.endsWith("S'")) {
    w = w.slice(0, -1);
    out.push(w);
  }
  for (const suffix of SUFFIXES) {
    if (!w.endsWith(suffix) || w.length <= suffix.length + 1) continue;
    const stem = w.slice(0, -suffix.length);
    if (suffix !== "ING" && suffix !== "S" && stem.endsWith("I")) out.push(stem.slice(0, -1) + "Y"); // carrieth -> carry
    out.push(stem); // walketh -> walk
    out.push(stem + "E"); // loveth -> love
    const last = stem[stem.length - 1];
    if (stem.length > 2 && last === stem[stem.length - 2] && !VOWELS.includes(last)) out.push(stem.slice(0, -1)); // sitteth -> sit
  }
  if (w.endsWith("LY") && w.length > 4) out.push(w.slice(0, -2));
  return out;
}

/** The file a headword lives in: `A`..`Z`, else `_other`
 *  (build_web_data.bucket_letter). */
export function bucket(headword: string): string {
  const c = headword.charAt(0);
  return /^[A-Za-z]$/.test(c) ? c.toUpperCase() : "_other";
}

export type Bucket = Record<string, string>;

/** The first candidate the dictionary has: [headword, definition], or null.
 *  `load` fetches one bucket; each bucket is asked for once per call. */
export async function lookup(word: string, load: (b: string) => Promise<Bucket>): Promise<[string, string] | null> {
  const seen = new Map<string, Promise<Bucket>>();
  for (const c of candidates(word)) {
    if (c === "") continue;
    const k = bucket(c);
    let p = seen.get(k);
    if (p === undefined) {
      p = load(k);
      seen.set(k, p);
    }
    const d = (await p)[c];
    if (d !== undefined) return [c, d];
  }
  return null;
}

/** The word around character `offset` of `text`: letters, with an inner
 *  apostrophe kept (`Abraham's`), or null when the offset is not on a word. */
export function wordAt(text: string, offset: number): string | null {
  const s = wordSpanAt(text, offset);
  return s === null ? null : text.slice(s[0], s[1]);
}

/** wordAt's word as [start, end) in `text`, or null. */
export function wordSpanAt(text: string, offset: number): [number, number] | null {
  const inWord = (i: number) => i >= 0 && i < text.length && (isLetter(text[i]) || (/['’]/.test(text[i]) && isLetter(text[i - 1] ?? "") && isLetter(text[i + 1] ?? "")));
  // A tap on a word's right half can report the offset just past it.
  let i = inWord(offset) ? offset : inWord(offset - 1) ? offset - 1 : -1;
  if (i < 0) return null;
  let a = i;
  while (inWord(a - 1)) a -= 1;
  while (inWord(i + 1)) i += 1;
  return [a, i + 1];
}

/** A definition's paragraphs: the source separates them with newlines. */
export function paragraphs(def: string): string[] {
  return def.split("\n").map((p) => p.trim()).filter((p) => p !== "");
}
