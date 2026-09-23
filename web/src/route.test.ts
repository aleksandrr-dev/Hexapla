// Behaviour check for the 1-based-URL / 0-based-internal boundary.
// Run: node --experimental-strip-types src/route.test.ts   (node 24 on this box)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { parseRoute, buildHash } from "./route.ts";

let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

// The boundary: the URL is 1-based, the Route is 0-based.
eq("#/kjv/1/1/1 -> all zeros", parseRoute("#/kjv/1/1/1"), { translation: "kjv", book: 0, chapter: 0, verse: 0 });
eq("#/kjv/43/3/16 -> 42/2/15", parseRoute("#/kjv/43/3/16"), { translation: "kjv", book: 42, chapter: 2, verse: 15 });

// A chapter link with no verse must SURVIVE (the sentinel-collision bug).
eq("#/kjv/1/1 -> verse null", parseRoute("#/kjv/1/1"), { translation: "kjv", book: 0, chapter: 0, verse: null });
eq("#/kjv/1 -> chapter default", parseRoute("#/kjv/1"), { translation: "kjv", book: 0, chapter: 0, verse: null });
eq("#/kjv -> book default", parseRoute("#/kjv"), { translation: "kjv", book: 0, chapter: 0, verse: null });
eq("no leading # or /", parseRoute("kjv/2/3"), { translation: "kjv", book: 1, chapter: 2, verse: null });

// Malformed returns null, never a clamped route.
eq("zero chapter is malformed", parseRoute("#/kjv/1/0"), null);
eq("negative is malformed", parseRoute("#/kjv/-1/1"), null);
eq("non-numeric is malformed", parseRoute("#/kjv/one/1"), null);
eq("empty is malformed", parseRoute("#"), null);
eq("too many segments is malformed", parseRoute("#/kjv/1/1/1/1"), null);

// buildHash is the inverse, back to 1-based.
eq("buildHash with verse", buildHash({ translation: "kjv", book: 42, chapter: 2, verse: 15 }), "#/kjv/43/3/16");
eq("buildHash without verse", buildHash({ translation: "kjv", book: 0, chapter: 0, verse: null }), "#/kjv/1/1");
const rt = parseRoute("#/ylt/19/23/1");
eq("round trip", rt === null ? "PARSE FAILED" : buildHash(rt), "#/ylt/19/23/1");

console.log(bad === 0 ? "route: all assertions passed" : "route: " + String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
