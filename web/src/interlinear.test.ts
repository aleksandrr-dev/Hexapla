// The interlinear port against the Android source it ports, the Kotlin
// decoder's own output, and the data.
// Run: HEXAPLA_WEB_DATA=<data dir> HEXAPLA_INTERLINEAR_ORACLE=<oracle.json> node --experimental-strip-types src/interlinear.test.ts
// The oracle comes from scripts/interlinear_oracle.ts (compiles Interlinear.kt).
// Exit 0 all pass, 1 any fail. Known-bad control: HEXAPLA_INTERLINEAR_BAD=1
// must FAIL (it moves one Kotlin table entry, and makes one oracle line a
// per-character OSHM tail - the bug Interlinear.kt's comment warns about).
import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { decode, decodeOshm, decodeRobinson, tables, tokens, word } from "./interlinear.ts";

const BAD = process.env.HEXAPLA_INTERLINEAR_BAD === "1";
const DATA = process.env.HEXAPLA_WEB_DATA;
const ORACLE = process.env.HEXAPLA_INTERLINEAR_ORACLE;
if (DATA === undefined || ORACLE === undefined) throw new Error("set HEXAPLA_WEB_DATA and HEXAPLA_INTERLINEAR_ORACLE");
let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}
const key = (k: string): string => k;

// ---- Tables == Interlinear.kt, entry for entry (an independent parse) ----
const kt = readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/Interlinear.kt", import.meta.url), "utf8");
const ktTables: Record<string, Record<string, string>> = {};
for (const m of kt.matchAll(/private val (\w+) = mapOf\(([\s\S]*?)\n    \)/g)) {
  ktTables[m[1]] = Object.fromEntries([...m[2].matchAll(/['"](\w+)['"] to R\.string\.(\w+)/g)].map((e) => [e[1], e[2]]));
}
if (BAD) ktTables.grkTense.P = "morph_tense_imperfect";
eq("tables == Interlinear.kt mapOf tables", tables(key), ktTables);
const xml = readFileSync(new URL("../../app/src/main/res/values/strings.xml", import.meta.url), "utf8");
const src = readFileSync(new URL("./interlinear.ts", import.meta.url), "utf8");
const used = [...new Set([...src.matchAll(/\bt\("(\w+)"\)/g)].map((m) => m[1]))];
eq("every t() key is an Android string (" + String(used.length) + ")", used.filter((k) => !xml.includes('name="' + k + '"')), []);
const ktKeys = [...new Set([...kt.matchAll(/R\.string\.(\w+)/g)].map((m) => m[1]))].sort();
eq("the same string set as Interlinear.kt", [...used].sort(), ktKeys);

// ---- Decoder == the compiled Kotlin, on every code in the data ----
const oracle = JSON.parse(readFileSync(ORACLE, "utf8")) as { kt_sha256: string; gr: Record<string, string>; he: Record<string, string> };
eq("oracle is of this Interlinear.kt (else re-run scripts/interlinear_oracle.ts)", oracle.kt_sha256, createHash("sha256").update(kt).digest("hex"));
if (BAD) oracle.he.HNcmpc = "morph_noun, morph_masculine morph_plural morph_common";
for (const [lang, dec] of [["gr", decodeRobinson], ["he", decodeOshm]] as const) {
  const codes = Object.keys(oracle[lang]);
  const wrong = codes.filter((c) => dec(key, c) !== oracle[lang][c]);
  eq(lang + ": decode == Kotlin on all " + String(codes.length) + " codes" + (wrong.length > 0 ? " (first: " + wrong[0] + ")" : ""), wrong.slice(0, 5), []);
}
eq("> 1000 Greek and > 3000 Hebrew codes compared", [Object.keys(oracle.gr).length > 1000, Object.keys(oracle.he).length > 3000], [true, true]);
// Beyond the data: the fallbacks.
eq("unknown Robinson code comes back as itself", decodeRobinson(key, "ZZ-Q"), "ZZ-Q");
eq("decode picks OSHM for the OT, Robinson for the NT", [decode(key, 0, "HTo"), decode(key, 42, "PREP")], ["morph_obj_marker", "morph_preposition"]);

// ---- word(): the tag of one word ----
eq("word 1 of John 1:1", word("G1722|PREP G746|N-DSF", 1), ["G746", "N-DSF"]);
eq("untagged '-' and out of range", [word("G1722|PREP - x", 1), word("G1722|PREP - x", 2), word("G1722|PREP", 5), word("", 0), word(undefined, 0)], [null, null, null, null, null]);

// ---- tokens(): marks-only runs take no index ----
eq("tokens split on punctuation", tokens("Ἐν ἀρχῇ ἦν, ὁ λόγος.").map((x) => x.i), [0, 1, 2, 3, 4]);
eq("a mark-only run is no word", tokens("a ́ b").map((x) => [x.s, x.i]), [[0, 0], [4, 1]]);

// ---- The data: every verse has as many tags as tokens ----
for (const [id, lang] of [["grc", "gr"], ["wlc", "he"]] as const) {
  let verses = 0;
  let tagged = 0;
  const off: string[] = [];
  for (const f of readdirSync(join(DATA, "interlinear", lang))) {
    const b = f.replace(".json", "");
    const inter = (JSON.parse(readFileSync(join(DATA, "interlinear", lang, f), "utf8")) as Record<string, string[][]>)[b];
    let text: string[][];
    try {
      text = (JSON.parse(readFileSync(join(DATA, id, f), "utf8")) as { chapters: string[][] }).chapters;
    } catch {
      off.push(id + " has no book " + b);
      continue;
    }
    inter.forEach((ch, c) =>
      ch.forEach((tags, v) => {
        verses += 1;
        if (tags === "") return;
        tagged += 1;
        const t = text[c]?.[v];
        if (t === undefined) off.push(b + " " + String(c + 1) + ":" + String(v + 1) + " no text");
        else if (tokens(t).length !== tags.split(" ").length) off.push(b + " " + String(c + 1) + ":" + String(v + 1) + " " + String(tokens(t).length) + " words, " + String(tags.split(" ").length) + " tags");
      }),
    );
  }
  eq(id + ": words == tags in all " + String(tagged) + " tagged of " + String(verses) + " verses" + (off.length > 0 ? " (" + String(off.length) + " off)" : ""), off.slice(0, 5), []);
}

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
