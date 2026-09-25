// node --experimental-strip-types src/offline.test.ts
// Known-bad control: HEXAPLA_OFFLINE_BAD=1 must FAIL.
import { readFileSync } from "node:fs";
import { DATA_CACHE, SHELL_CACHE, dataRoot, keepUrls } from "./offline.ts";

const BAD = process.env.HEXAPLA_OFFLINE_BAD === "1";
let bad = 0;
const eq = (label: string, got: unknown, want: unknown): void => {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g !== w) bad++;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
};

// data/ is a SIBLING of the app base, as data.ts resolves it.
eq("data root beside the app", dataRoot("/Hexapla/app/", "https://x.io"), "https://x.io/Hexapla/data/");
eq("data root at a domain root", dataRoot("/app/", "https://hexaplabible.com"), "https://hexaplabible.com/data/");
eq("data root, the app AT the root", dataRoot("/", "https://hexaplabible.com"), "https://hexaplabible.com/data/");
eq("data root, base without slash", dataRoot("/Hexapla/app", "https://x.io"), "https://x.io/Hexapla/data/");

const urls = keepUrls("R/", "kjv", BAD ? 82 : 83);
eq("kjv: shared + books.json + 83 books", urls.length, 86);
eq("first book file", urls[3], "R/kjv/0.json");
eq("last book file", urls[urls.length - 1], "R/kjv/82.json");
eq("no duplicates", new Set(urls).size, urls.length);

// The worker and the page must write the SAME caches.
const sw = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
eq("sw SHELL name matches", sw.includes(`const SHELL = "${SHELL_CACHE}"`), true);
eq("sw DATA name matches", sw.includes(`const DATA = "${DATA_CACHE}"`), true);

console.log(bad ? bad + " FAILED" : "all passed");
process.exit(bad ? 1 : 0);
