// Behaviour check for read-aloud (speech.ts) against the Android source it ports.
// Run: node --experimental-strip-types src/speech.test.ts
// Needs HEXAPLA_WEB_DATA=<.../data> for the whole-corpus word-map check.
// Exit 0 all pass, 1 any fail. Known-bad control: HEXAPLA_SPEECH_BAD=1 must FAIL
// (it reads the spoken index as if it were the displayed one).
import { readFileSync } from "node:fs";
import { forSpeech, pickVoice, voicesFor, voiceKey, wordOf, PRON_ASSET, type PronTable, type VoiceLike } from "./speech.ts";

let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

const asset = (f: string) => readFileSync(new URL("../../app/src/main/assets/" + f, import.meta.url), "utf8");
const kt = readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/Pronounce.kt", import.meta.url), "utf8");

// ---- The tables are Android's ----
const ktAssets = Object.fromEntries([...kt.matchAll(/"(\w+)" to "(pron_\w+\.json)"/g)].map((m) => [m[1], m[2]]));
const WEB_TO_ANDROID: Record<string, string> = { tyn: "tyn", gen1599: "gnv", wyc: "wyc" };
eq("PRON_ASSET == Pronounce.ASSETS (web ids)", Object.fromEntries(Object.entries(PRON_ASSET).map(([w, f]) => [WEB_TO_ANDROID[w], f]).sort()), Object.fromEntries(Object.entries(ktAssets).sort()));
const exc = /RULE_EXCEPTIONS = setOf\(([^)]*)\)/.exec(kt)?.[1];
eq("RULE_EXCEPTIONS == Kotlin", exc?.replace(/\s/g, ""), '"deuel","geuel","euodias","iim","reuel"');
eq("PHONETIC == Kotlin", [...kt.matchAll(/"(babels?)" to "(\w+)"/g)].map((m) => m[1] + ">" + m[2]), ["babel>Babbel", "babels>Babbels"]);

const tables: Record<string, PronTable> = Object.fromEntries(Object.entries(PRON_ASSET).map(([id, f]) => [id, JSON.parse(asset(f)) as PronTable]));
const gnv = tables.gen1599;

// ---- forSpeech: Pronounce.forSpeech ----
eq("phonetic on English, no table", forSpeech("the tower of Babel", true, null).text, "the tower of Babbel");
eq("phonetic never on other languages", forSpeech("Babel", false, null).text, "Babel");
eq("early modern rules", forSpeech("Iesus saide vnto them, heauen and euel", true, { words: {} }).text, "Jesus saide unto them, heaven and evel");
eq("-uel names untouched", forSpeech("Samuel and Deuel", true, { words: {} }).text, "Samuel and Deuel");
eq("hyphenated proper name joined", forSpeech("Nebuchad-nezzar and well-favoured", true, { words: {} }).text, "Nebuchadnezzar and well-favoured");
eq("roman numeral between stops", forSpeech("after .vij. dayes", true, { words: {} }).text, "after  7  dayes");
eq("map keeps case", forSpeech("ABHORRE Abhorre abhorre", true, gnv).text, "ABHOR Abhor abhor");

// ---- wordOf: a spoken boundary lands on the displayed word ----
{
  const o = "Beth-el and heauen, .vij. Babel";
  const sp = forSpeech(o, true, { words: {} });
  const at = (w: string) => wordOf(o, sp, sp.text.indexOf(w));
  eq("word after a join", at("and"), [8, 11]);
  eq("rewritten word", at("heaven"), [12, 18]);
  eq("word after a numeral", at("Babbel"), [26, 31]);
  eq("past the end", wordOf(o, sp, sp.text.length), null);
}

// ---- The whole corpus of the three mapped sets (0 tokens: never a sample) ----
// Every original word must be hit by a spoken word boundary, in order: a map
// that drifts skips or repeats words, and that is what a reader would see.
const DATA = process.env.HEXAPLA_WEB_DATA;
if (DATA === undefined) {
  eq("HEXAPLA_WEB_DATA set (corpus check cannot run)", false, true);
} else {
  for (const id of Object.keys(PRON_ASSET)) {
    const books = JSON.parse(readFileSync(DATA + "/" + id + "/books.json", "utf8")) as unknown[];
    let verses = 0;
    let missed = 0;
    let backwards = 0;
    let example = "";
    for (let b = 0; b < books.length; b++) {
      const book = JSON.parse(readFileSync(DATA + "/" + id + "/" + String(b) + ".json", "utf8")) as { chapters: string[][] };
      for (const ch of book.chapters) {
        for (const v of ch) {
          verses += 1;
          const sp = forSpeech(v, true, tables[id]);
          const hit = new Set<number>();
          let prev = -1;
          for (const m of sp.text.matchAll(/[\p{L}\p{N}]+/gu)) {
            const r = wordOf(v, sp, m.index);
            if (r === null) continue;
            if (r[0] < prev) backwards += 1;
            prev = r[0];
            hit.add(r[0]);
            // A joined word ("to gedder" -> "together", "Tubal-kain") is
            // reached through the span its spoken token covers.
            for (let k = m.index; k < m.index + m[0].length; k++) hit.add(sp.src[k]);
          }
          for (const m of v.matchAll(/[\p{L}\p{M}\p{N}'’]+/gu)) {
            // A roman numeral between stops is spoken as digits: still hit.
            if (!hit.has(m.index) && !/^[\p{P}]*$/u.test(m[0])) {
              missed += 1;
              if (example === "") example = m[0] + " in «" + v.slice(0, 80) + "»";
            }
          }
        }
      }
    }
    eq(id + ": every displayed word is reached (" + String(verses) + " verses)" + (example ? "; first miss " + example : ""), missed, 0);
    eq(id + ": boundaries never run backwards", backwards, 0);
  }
}

// ---- Voices ----
const V = (name: string, lang: string, local = true, def = false): VoiceLike => ({ name, lang, localService: local, default: def });
const list = [V("net-en", "en-US", false, true), V("loc-en", "en-GB"), V("cn", "zh-CN"), V("tw", "zh-TW"), V("hk", "zh_HK"), V("sr", "sr-RS"), V("de", "de-DE")];
eq("on-device before network", voicesFor(list, "en").map((v) => v.name), ["loc-en", "net-en"]);
eq("zh-Hant prefers Taiwan, then Hong Kong", voicesFor(list, "zh-Hant").map((v) => v.name), ["tw", "hk", "cn"]);
eq("zh-Hans prefers mainland", voicesFor(list, "zh-Hans")[0].name, "cn");
eq("sr-Latn takes a Serbian voice", voicesFor(list, "sr-Latn").map((v) => v.name), ["sr"]);
eq("no voice for the language", voicesFor(list, "hy"), []);
eq("remembered voice kept", pickVoice(list, "en", "net-en")?.name, "net-en");
eq("remembered voice gone -> best", pickVoice(list, "en", "gone")?.name, "loc-en");
eq("voice key is the primary subtag", voiceKey("zh-Hant"), "zh");

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
