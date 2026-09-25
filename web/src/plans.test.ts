// Behaviour check for the reading plans against the Android source they port.
// Run: node --experimental-strip-types src/plans.test.ts
// Exit 0 all pass, 1 any fail. Known-bad control: HEXAPLA_PLANS_BAD=1 must FAIL
// (it drops one chapter from the Kotlin order, and asserts the old one-day-late streak).
import { readFileSync } from "node:fs";
import { CHRONO_ORDER, KJV_CHAPTERS, buildPlans, bumped, chronoChapters, cleanPlanState, distribute, nextDay, reset, toggled, EMPTY_PLANS } from "./plans.ts";

const BAD = process.env.HEXAPLA_PLANS_BAD === "1";
let bad = 0;

function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

// ---- The data is Android's, byte for byte ----
const kt = (f: string) => readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/" + f, import.meta.url), "utf8");
const order = [...kt("ChronoOrder.kt").matchAll(/^\s*"([^"]*)"/gm)].map((m) => m[1]).join("");
eq("CHRONO_ORDER == ChronoOrder.kt ORDER", CHRONO_ORDER, BAD ? order.replace(" 65:1-22", " 65:1-21") : order);
const grid = /KJV_CHAPTERS = intArrayOf\(([^)]*)\)/.exec(kt("Bible.kt"))?.[1].split(",").map((s) => Number(s.trim()));
eq("KJV_CHAPTERS == Bible.kt", KJV_CHAPTERS, grid);
eq("grid sums to 1189", KJV_CHAPTERS.reduce((a, b) => a + b, 0), 1189);
for (const [id, era] of [...kt("ChronoOrder.kt").matchAll(/Triple\((\d+), (\d+), R\.string\.(era_\w+)\)/g)].map((m) => [m[3], m] as const)) {
  const chrono = buildPlans()[1];
  const day = chrono.days.find((d) => d.chapters.some((c) => c[0] === Number(era[1]) && c[1] === Number(era[2])));
  eq("era " + id + " is on its chapter's day", day !== undefined && chrono.eraByDay.get(day.day) === id, true);
}

// ---- Order and distribution ----
const chron = chronoChapters();
eq("chrono is every chapter once", chron.length, 1189);
let threw = false;
try {
  chronoChapters(CHRONO_ORDER + " 0:1");
} catch {
  threw = true;
}
eq("a repeated chapter throws", threw, true);

const plans = buildPlans();
eq("ids in Android order", plans.map((p) => p.id), ["year", "chrono", "nt90", "gospels30", "prov31", "ps75"]);
eq("day counts", plans.map((p) => p.days.length), [365, 365, 90, 30, 31, 75]);
eq("chapter totals", plans.map((p) => p.days.reduce((a, d) => a + d.chapters.length, 0)), [1189, 1189, 260, 89, 31, 150]);
// distribute is ceil-first: 1189/365 -> the first 94 days take 4, the rest 3.
eq("year day 1", plans[0].days[0].chapters, [[0, 0], [0, 1], [0, 2], [0, 3]]);
eq("year last day", plans[0].days[364].chapters, [[65, 19], [65, 20], [65, 21]]);
eq("distribute never makes an empty day", distribute([[0, 0], [0, 1]], 5).map((d) => d.chapters.length), [1, 1]);
eq("psalms 150/75 = 2 a day", plans[5].days.every((d) => d.chapters.length === 2), true);
eq("chrono day 1 opens Genesis 1", plans[1].days[0].chapters[0], [0, 0]);
eq("chrono has 18 era headings", plans[1].eraByDay.size, 18);

// ---- Progress ----
let s = toggled(toggled(toggled({ ...EMPTY_PLANS, done: {} }, "year", 3), "year", 1), "year", 2);
eq("toggle keeps days sorted", s.done.year, [1, 2, 3]);
eq("next day skips the done ones", nextDay(plans[0], new Set(s.done.year)), 4);
s = toggled(s, "year", 2);
eq("toggle again unticks", s.done.year, [1, 3]);
eq("next day is the first gap", nextDay(plans[0], new Set(s.done.year)), 2);
eq("all done -> the last day", nextDay(plans[4], new Set(plans[4].days.map((d) => d.day))), 31);
eq("reset clears one plan only", reset(toggled(s, "ps75", 1), "year").done, { ps75: [1] });
eq("stored junk is dropped", cleanPlanState({ last: 7, done: { year: [0, 2, 2, "x", 400, 1.5], nt90: "no" }, streak: -1, streakDay: "yesterday" }), { last: "", done: { year: [2] }, streak: 0, streakDay: "" });
eq("null storage -> empty", cleanPlanState(null), EMPTY_PLANS);

// ---- Streak: Store.touchStreak ----
const at = (y: number, m: number, d: number, h = 12) => new Date(y, m - 1, d, h);
let k = bumped({ ...EMPTY_PLANS, done: {} }, at(2026, 9, 25));
eq("first open = 1", k.streak, 1);
eq("same day keeps", bumped(k, at(2026, 9, 25, 23)).streak, 1);
k = bumped(k, at(2026, 9, 26, 0));
eq("next day just after midnight = 2", k.streak, 2);
eq("across a month end", bumped({ ...k, streakDay: "2026-09-30" }, at(2026, 10, 1)).streak, 3);
eq("a gap restarts at 1", bumped(k, at(2026, 9, 28)).streak, BAD ? 3 : 1);

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
