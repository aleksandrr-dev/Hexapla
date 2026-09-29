// Behaviour check: OsmKelam's © heads the Turkish column on the canon only;
// kie's apocrypha (book >= 66) are Ali Bey 1665 in Kadir Akın's transliteration.
// Run: node --experimental-strip-types src/credits.test.ts   (node 24 on this box)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { columnCredit } from "./credits.ts";

let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const ok = got === want;
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${label}: got ${String(got)}, want ${String(want)}`);
}

eq("kie Genesis", columnCredit("kie", 0)?.short, "©");
eq("kie Revelation (last canon book)", columnCredit("kie", 65)?.short, "©");
eq("kie 1 Esdras (first apocrypha slot)", columnCredit("kie", 66), undefined);
eq("kie Bel and the Dragon", columnCredit("kie", 81), undefined);
eq("kjv has no column credit", columnCredit("kjv", 0), undefined);

process.exit(bad ? 1 : 0);
