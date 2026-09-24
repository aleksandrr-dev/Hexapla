// Behaviour check for strongs.ts against the BUILT data tree.
// Run: HEXAPLA_WEB_DATA=<build>/data node --experimental-strip-types src/strongs.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { afterCap, lexiconLang, mergeLexicon, segments, shown, shownNumber, shownText, subline, untag, type RawLexicon, type Seg } from "./strongs.ts";

const root = process.env.HEXAPLA_WEB_DATA;
if (root === undefined) {
  console.log("FAIL set HEXAPLA_WEB_DATA to the built data/ directory");
  process.exit(1);
}
const data = (f: string) => JSON.parse(readFileSync(root + "/" + f, "utf8"));

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}
const ids = (s: Seg[]) => s.flatMap((x) => ("id" in x ? [x.id] : []));

// ---- parsing -------------------------------------------------------------------
const gen = data("kjv_strongs/0.json")["0"] as string[][];
const g11 = segments(gen[0][0]);
// The source carries no number on «earth» here; the ids are what it has.
eq("Gen 1:1 ids in order", ids(g11), ["H7225", "H430", "H1254", "H853", "H8064", "H853"]);
eq("Gen 1:1 first run", g11[0], { text: "In the beginning" });
eq("two tags in a row = two ids, no empty run", g11.slice(4, 7), [{ text: " created" }, { id: "H1254" }, { id: "H853" }]);
eq("a verse ending in a tag has no trailing run", segments("word[G1]"), [{ text: "word" }, { id: "G1" }]);
eq("an untagged verse is one run", segments("Jesus wept."), [{ text: "Jesus wept." }]);
eq("lookalikes are text, not tags", ids(segments("[X12] [H] [h12] [G1a]")), []);
eq("shown number drops the H/G", [shownNumber("H7225"), shownNumber("G2316")], ["7225", "2316"]);

// ---- shown: whitespace as parseAsset, a leading number after the first word ----
const mt = data("kjv_strongs/39.json")["39"] as string[][];
const m31 = shown(mt[2][0]);
eq("Matt 3:1 [G1161] moves after «In»", m31.slice(0, 4), [{ text: "In" }, { id: "G1161" }, { id: "G1722" }, { text: " those" }]);
eq("space around a tag collapses once", shownText(shown("word [H1] next")), "word next");
eq("tags only at the end: no trailing space", shown("end. [H1]"), [{ text: "end." }, { id: "H1" }]);
eq("drop cap cuts text, keeps ids", afterCap(m31, 1).slice(0, 2), [{ text: "n" }, { id: "G1161" }]);
eq("drop cap across a run boundary", afterCap([{ text: "A" }, { id: "H1" }, { text: "bc" }], 2), [{ id: "H1" }, { text: "c" }]);

// ---- the whole tagged corpus reads as the plain KJV (the repaired colon tails) ----
eq("Gen 1:9 keeps «and it was so.»", untag(gen[0][8]).endsWith("appear: and it was so."), true);
let verses = 0;
let differ = 0;
let first = "";
for (let b = 0; b < 66; b += 1) {
  const tagged = data("kjv_strongs/" + String(b) + ".json")[String(b)] as string[][];
  const plain = data("kjv/" + String(b) + ".json").chapters as string[][];
  if (tagged.length !== plain.length) {
    differ += 1;
    first ||= "book " + String(b) + " chapter count";
    continue;
  }
  tagged.forEach((ch, c) =>
    ch.forEach((v, i) => {
      verses += 1;
      if (shownText(shown(v)) !== plain[c][i]) {
        differ += 1;
        first ||= String(b) + ":" + String(c + 1) + ":" + String(i + 1);
      }
    }),
  );
}
eq("every tagged verse untags to the plain KJV (" + String(verses) + " verses)", first === "" ? differ : first, 0);
eq("... and the corpus is the whole protestant canon", verses, 31102);

// ---- lexicon: English, with ru swapped in per id and per field -------------------
const en = data("strongs_lexicon.json") as RawLexicon;
const ruRaw = data("strongs_lexicon_ru.json") as RawLexicon;
const english = mergeLexicon(en, null);
eq("English H7225 has its word", english.H7225.word, en.H7225.w);
const ru = mergeLexicon(en, ruRaw);
eq("ru G1 gloss is the Russian one", ru.G1.def, ruRaw.G1.d);
eq("ru G1 has no translit of its own, keeps the English", ru.G1.translit, en.G1.t ?? "");
const onlyEn = Object.keys(en).filter((k) => !(k in ruRaw));
eq("premise: ru lacks some ids", onlyEn.length > 0, true);
eq("an id ru lacks reads English", ru[onlyEn[0]], english[onlyEn[0]]);
eq("every English id survives the merge", Object.keys(en).every((k) => k in ru), true);
eq("a blank translated field falls back", mergeLexicon({ X: { w: "a", d: "eng" } }, { X: { w: "b", d: "  " } }).X, { word: "b", translit: "", pos: "", def: "eng" });
eq("subline leaves blanks out", [subline({ word: "", translit: "ʼâb", pos: "", def: "" }), subline({ word: "", translit: "x", pos: "n", def: "" })], ["ʼâb", "x · n"]);
eq("language tags", [lexiconLang("ru-RU"), lexiconLang("RU"), lexiconLang("en-US"), lexiconLang("uk")], ["ru", "ru", null, null]);

// Controls: HEXAPLA_STRONGS_BAD=1 asserts the unrepaired colon tail (Gen 1:9
// ending at «appear:»); =2 asserts a per-FILE fallback (ru G1 with no
// transliteration). Both must FAIL.
if (process.env.HEXAPLA_STRONGS_BAD === "1") eq("control 1 (must fail)", untag(gen[0][8]).endsWith("appear:"), true);
if (process.env.HEXAPLA_STRONGS_BAD === "2") eq("control 2 (must fail)", ru.G1.translit, "");

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
