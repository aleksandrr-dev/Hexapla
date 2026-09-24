// Behaviour check for the search port (search.ts = ReaderScreen.kt scanBooks).
// Run: node --experimental-strip-types src/search.test.ts
// Exit 0 all pass, 1 any fail. With HEXAPLA_WEB_DATA=<tree>/data it also
// searches the real KJV and CUV; without it those checks are SKIPPED, loudly.
//
// Control: HEXAPLA_SEARCH_BAD=1 swaps in the character-BIGRAM tokenizer that
// Android measured at 1/16; the reordered-CJK assertions must then FAIL.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { scanBooks, search, searchNorm, searchTerms, toCorpus, SEARCH_CAP, type Corpus } from "./search.ts";

let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

/** The rejected tokenizer: overlapping character pairs inside a CJK run. */
function bigramTerms(q: string): string[] {
  const out = new Set<string>();
  for (const tok of q.split(" ")) {
    if (tok.trim() === "") continue;
    const cs = [...tok];
    if (!/\p{Script=Han}/u.test(tok) || cs.length < 2) (out.add(tok));
    else for (let i = 0; i + 1 < cs.length; i++) out.add(cs[i] + cs[i + 1]);
  }
  return [...out];
}

const CONTROL = process.env.HEXAPLA_SEARCH_BAD === "1";
const terms = CONTROL ? bigramTerms : searchTerms;
/** search() with the tokenizer under test. */
function run(corpus: Corpus, query: string): { b: number; c: number; v: number }[] {
  const raw = query.trim();
  if (raw.length < 2) return [];
  const q = searchNorm(raw);
  return scanBooks(corpus, q, terms(q)).map(({ b, c, v }) => ({ b, c, v }));
}
const has = (hits: { b: number; c: number; v: number }[], b: number, c: number, v: number) => hits.some((h) => h.b === b && h.c === c && h.v === v);

// ---- norm ----------------------------------------------------------------
eq("greek breathings and accents", searchNorm("Ἐν ἀρχῇ ἦν ὁ λόγος"), "εν αρχη ην ο λογος");
eq("latin accents + case", searchNorm("Élohim CRÉA"), "elohim crea");
eq("hebrew niqqud", searchNorm("בְּרֵאשִׁית"), "בראשית");

// ---- terms ---------------------------------------------------------------
eq("latin splits on spaces, drops empties", searchTerms("for  god so"), ["for", "god", "so"]);
eq("duplicates collapse, order kept", searchTerms("the lord the"), ["the", "lord"]);
eq("han decomposes to characters", searchTerms("神愛世人"), ["神", "愛", "世", "人"]);
eq("latin run inside cjk kept whole", searchTerms("神ab愛"), ["神", "ab", "愛"]);
eq("punctuation breaks a latin run", searchTerms("神a,b"), ["神", "a", "b"]);
eq("kana decomposes too", searchTerms("かみ"), ["か", "み"]);
eq("hangul is NOT spaceless", searchTerms("하나님 사랑"), ["하나님", "사랑"]);

// ---- scan (fixtures) -----------------------------------------------------
const fx = toCorpus([
  [["In the beginning God created", "and God saw the light"], ["the light was good"]],
  null,
  [["God so loved the world", "the world God so loved"]],
  [["「神愛世人，甚至將他的獨生子賜給他們", "世人都犯了罪"]],
]);
eq("exact phrase", run(fx, "so loved"), [{ b: 2, c: 0, v: 0 }, { b: 2, c: 0, v: 1 }]);
eq("exact before loose", run(fx, "god so loved"), [{ b: 2, c: 0, v: 0 }, { b: 2, c: 0, v: 1 }]);
eq("loose any order", run(fx, "loved world"), [{ b: 2, c: 0, v: 0 }, { b: 2, c: 0, v: 1 }]);
eq("loose needs every term", run(fx, "light created"), []);
eq("one term: no loose fallback", run(fx, "GOD"), [{ b: 0, c: 0, v: 0 }, { b: 0, c: 0, v: 1 }, { b: 2, c: 0, v: 0 }, { b: 2, c: 0, v: 1 }]);
eq("a missing book is skipped", run(fx, "the light"), [{ b: 0, c: 0, v: 1 }, { b: 0, c: 1, v: 0 }]);
eq("query under 2 chars = nothing", run(fx, " g "), []);
eq("case/diacritics in the query", run(fx, "Gód"), run(fx, "god"));
// The bigram failure: 世人神愛 invents 人神, in no verse.
eq("reordered han phrase finds the verse", run(fx, "世人神愛"), [{ b: 3, c: 0, v: 0 }]);
eq("search() = the same path", search(fx, "loved world").map(({ b, c, v }) => ({ b, c, v })), run(fx, "loved world"));

const many = toCorpus([[Array.from({ length: 500 }, (_, i) => "word " + String(i))]]);
eq("cap on exact", search(many, "word").length, SEARCH_CAP);
const mixed = toCorpus([[[...Array.from({ length: 250 }, () => "b a"), ...Array.from({ length: 100 }, () => "a b")]]]);
const mh = search(mixed, "a b");
eq("cap mixes exact first, then loose", [mh.length, mh[0].v, mh[99].v, mh[100].v], [SEARCH_CAP, 250, 349, 0]);

// ---- real data -----------------------------------------------------------
const root = process.env.HEXAPLA_WEB_DATA;
function corpusOf(id: string): Corpus | null {
  if (root === undefined || !existsSync(join(root, id, "books.json"))) return null;
  const idx = JSON.parse(readFileSync(join(root, id, "books.json"), "utf-8")) as unknown[];
  return toCorpus(idx.map((_, b) => (JSON.parse(readFileSync(join(root, id, String(b) + ".json"), "utf-8")) as { chapters: string[][] }).chapters));
}
const kjv = corpusOf("kjv");
const cuv = corpusOf("cuv");
if (kjv === null || cuv === null) {
  console.log("SKIP real-data checks: set HEXAPLA_WEB_DATA to a built data/ tree");
} else {
  const t0 = performance.now();
  const j316 = run(kjv, "for god so loved");
  const ms = performance.now() - t0;
  eq("kjv: John 3:16 is the first exact hit", j316[0], { b: 42, c: 2, v: 15 });
  eq("kjv: half-remembered order still finds it", has(run(kjv, "god loved the world so"), 42, 2, 15), true);
  // One exact hit, then the loose ones (Peter wept, in a verse naming Jesus).
  eq("kjv: 'jesus wept' = John 11:35 first, then loose", run(kjv, "jesus wept"), [{ b: 42, c: 10, v: 34 }, { b: 39, c: 25, v: 74 }, { b: 40, c: 13, v: 71 }]);
  eq("cuv: reordered 世人神愛 finds John 3:16", has(run(cuv, "世人神愛"), 42, 2, 15), true);
  eq("cuv: reordered 永生信 finds John 3:16", has(run(cuv, "永生 信他"), 42, 2, 15), true);
  console.log("info: kjv 'for god so loved' scan " + ms.toFixed(1) + " ms (node, unthrottled)");
}

if (CONTROL) console.log("control: bigram tokenizer in use — this run MUST fail");
console.log(bad === 0 ? "search: all assertions passed" : "search: " + String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
