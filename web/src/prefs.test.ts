// Behaviour check for stored-prefs migration and the `?with=` list.
// Run: node --experimental-strip-types src/prefs.test.ts
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { DEFAULTS, MAX_PARALLEL, migrate, parseWith } from "./prefs.ts";

let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

// The two-column shape the reader shipped with (f78d7f3) must carry over.
eq("old second+both", migrate({ second: "mei", mode: "both" }).parallel, ["mei"]);
eq("old both -> all", migrate({ second: "mei", mode: "both" }).show, "all");
eq("old b -> that id alone", migrate({ second: "mei", mode: "b" }).show, "mei");
eq("old a -> all", migrate({ second: "mei", mode: "a" }).show, "all");
eq("old no second", migrate({ second: null, mode: "both" }).parallel, []);
eq("old b with no second -> all", migrate({ second: null, mode: "b" }).show, "all");
eq("old keeps the rest", migrate({ last: "#/kjv/43/3", second: "syn", mode: "both", fontSize: 22, theme: "dark", layout: "side" }), {
  last: "#/kjv/43/3",
  parallel: ["syn"],
  show: "all",
  fontSize: 22,
  theme: "dark",
  layout: "side",
});

// The current shape.
eq("new round trip", migrate({ ...DEFAULTS, parallel: ["a", "b"], show: "b" }), { ...DEFAULTS, parallel: ["a", "b"], show: "b" });
eq("new: junk ids dropped, repeats dropped", migrate({ parallel: ["a", "a", "x y", 3, "b"] }).parallel, ["a", "b"]);
eq("new: capped at MAX_PARALLEL", migrate({ parallel: ["a", "b", "c", "d", "e", "f", "g"] }).parallel.length, MAX_PARALLEL);
eq("new: bad show -> all", migrate({ parallel: [], show: "<x>" }).show, "all");
eq("empty object -> defaults", migrate({}), DEFAULTS);

// Shared links.
eq("?with=mei (old single form)", parseWith("?with=mei"), ["mei"]);
eq("?with=mei,syn,vul", parseWith("?with=mei,syn,vul"), ["mei", "syn", "vul"]);
eq("?with= junk dropped", parseWith("?with=mei,%3Cb%3E,,syn"), ["mei", "syn"]);
eq("?with= capped", parseWith("?with=a,b,c,d,e,f,g")?.length, MAX_PARALLEL);
eq("no ?with", parseWith(""), null);
eq("?with= empty", parseWith("?with="), null);

// Control: HEXAPLA_PREFS_BAD=1 asserts something false; the run must FAIL.
if (process.env.HEXAPLA_PREFS_BAD === "1") eq("control (must fail)", migrate({ second: "mei", mode: "b" }).show, "all");

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
