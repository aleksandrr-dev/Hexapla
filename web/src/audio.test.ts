// Behaviour check for audio.ts against the REAL app assets: both audio
// indexes, the mood map, the music index and the versemap.
// Run: node --experimental-strip-types src/audio.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { bundledFor, moodFor, packUrl, parseWords, sectionFor, sectionsFor, SILENCE, startMs, verseAt, wordAt, wordsUrl, type GenIndex, type LibriVoxIndex, type MoodMapData, type MusicIndex, type Section } from "./audio.ts";
import type { VerseMapData } from "./versemap.ts";

const ASSETS = new URL("../../app/src/main/assets/", import.meta.url);
const read = <T>(f: string): T => JSON.parse(readFileSync(new URL(f, ASSETS), "utf8")) as T;
const librivox = read<LibriVoxIndex>("audio_index.json");
const gen = read<GenIndex>("audio_index_gen.json");
const moods = read<MoodMapData>("mood_map.json");
const music = read<MusicIndex>("music_index.json");
const vm = read<VerseMapData>("versemap.json");

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}

// ---- which file plays ------------------------------------------------------
const kjv = sectionsFor("kjv", librivox, gen);
const john1 = sectionFor(kjv.get(42), 0);
// Generated wins over LibriVox on a book in both, because only it has offsets.
eq("kjv John 1 is generated", john1?.generated, true);
eq("kjv John 1 carries offsets", (john1?.offsets?.length ?? 0) > 0, true);
eq("kjv John 1 url", john1?.url, gen.kjv["42"].base + "/" + gen.kjv["42"].chapters["0"].f);
// A book only LibriVox has keeps LibriVox (synthetic: drop kjv gen).
const lvOnly = sectionsFor("kjv", librivox, { ...gen, kjv: {} });
const gen1 = sectionFor(lvOnly.get(0), 0);
eq("LibriVox Genesis 1 section", gen1 === null ? null : [gen1.first, gen1.last, gen1.generated], [1, 6, false]);
eq("LibriVox Genesis 4 is in section 1-6", sectionFor(lvOnly.get(0), 3)?.first, 1);
eq("LibriVox Genesis 7 is in section 7-12", sectionFor(lvOnly.get(0), 6)?.first, 7);
// Other translations never read the LibriVox index.
eq("wbt has no LibriVox", sectionsFor("wbt", librivox, { ...gen, wbt: {} }).size, 0);
eq("unknown translation: nothing", sectionsFor("zz", librivox, gen).size, 0);
eq("no book: null", sectionFor(undefined, 0), null);
eq("wbt Genesis 50 exists", sectionFor(sectionsFor("wbt", librivox, gen).get(0), 49)?.first, 50);
eq("sections sorted", (sectionsFor("wbt", librivox, gen).get(0) ?? []).every((s, i, a) => i === 0 || a[i - 1].first < s.first), true);
eq("wordsUrl", wordsUrl("https://x/y/42/0.ogg"), "https://x/y/42/0.w.json");

// ---- seeking ---------------------------------------------------------------
const offs = [2800, 6825, 16375, 20325];
const g: Section = { first: 1, last: 1, url: "u", generated: true, offsets: offs };
eq("verse 0 plays from the top (announcement)", startMs(g, 0, 0, 60000, [4]), 0);
eq("verse 2 seeks with a 250 ms lead-in", startMs(g, 0, 2, 60000, [4]), 16125);
// verse 1 lands at 6575 > 1000, so it seeks.
eq("verse 1 seeks", startMs(g, 0, 1, 60000, [4]), 6575);
const lv: Section = { first: 1, last: 2, url: "u", generated: false, offsets: null };
// 10 + 10 verses over 200 s; chapter 2 verse 0 is halfway, minus 4 s.
eq("LibriVox chapter 2 of a 1-2 section", startMs(lv, 1, 0, 200000, [10, 10]), 96000);
eq("LibriVox first chapter start", startMs(lv, 0, 0, 200000, [10, 10]), 0);
eq("unknown duration plays from the top", startMs(lv, 1, 0, NaN, [10, 10]), 0);

// ---- following -------------------------------------------------------------
eq("before the first verse = verse 0", verseAt(offs, 100), 0);
eq("exactly on an offset", verseAt(offs, 16375), 2);
eq("between", verseAt(offs, 20000), 2);
eq("past the end", verseAt(offs, 999999), 3);
const words: [number, number, number, number][] = [
  [100, 300, 0, 2],
  [400, 700, 3, 7],
];
eq("word 1", wordAt(words, 150), [0, 2]);
eq("pause between words lights nothing", wordAt(words, 350), null);
eq("word 2", wordAt(words, 700), [3, 7]);
eq("past the last word lights nothing", wordAt(words, 900), null);
eq("before the first word", wordAt(words, 50), null);
eq("unaligned verse", wordAt(null, 150), null);
eq("sidecar parse", parseWords({ v: [[[1, 2, 3, 4]], null, "junk"] }), [[[1, 2, 3, 4]], null, null]);
eq("malformed sidecar is null", parseWords({ nope: 1 }), null);

// ---- the bed ---------------------------------------------------------------
const PS = 18;
// The 2026-08-23 Android defect: Synodal Psalm 87 (LXX) = KJV Psalm 88, the
// darkest psalm, must get KJV 88's bed, not KJV 87's.
const kjv88 = moodFor(moods, vm, "kjv", PS, 87, -1).mood;
eq("syn Ps 87 at chapter start = kjv Ps 88", moodFor(moods, vm, "syn", PS, 86, -1).mood, kjv88);
eq("syn Ps 87 mid-chapter = kjv Ps 88", moodFor(moods, vm, "syn", PS, 86, 5).mood, moodFor(moods, vm, "kjv", PS, 87, 5).mood);
eq("kjv is identity (no versemap needed)", moodFor(moods, null, "kjv", PS, 87, -1).mood, kjv88);
// Anchor turns: find one in the real map and step across it.
const turned = moods.anchors.find((a) => (a.turns ?? []).length > 0 && a.book < 66);
if (turned === undefined) eq("the map has an anchor with a turn", false, true);
else {
  const t = (turned.turns ?? [])[0];
  eq("anchor opens on its mood", moodFor(moods, vm, "kjv", turned.book, turned.chapter, -1).mood, t.verse === 0 ? t.mood : turned.mood);
  eq("anchor turns at its verse", moodFor(moods, vm, "kjv", turned.book, turned.chapter, t.verse).mood, t.mood);
}
// A pin whose track is in the pack plays it; a pin whose track is NOT falls
// back to the mood's track, never to silence (Ps 143's `dalitz_ricercar_ps143`
// is pinned in mood_map.json but absent from music_index.json — on Android too).
const pinned = moods.trackPin?.find((p) => music.pinned?.[p.track] !== undefined);
const unpinned = moods.trackPin?.find((p) => music.pinned?.[p.track] === undefined);
if (pinned === undefined) eq("the map has a pin the pack serves", false, true);
else {
  eq("a pinned chapter carries its track", moodFor(moods, vm, "kjv", pinned.book, pinned.chapter, -1).track, pinned.track);
  eq("the pinned track resolves in the pack", packUrl(music, moodFor(moods, vm, "kjv", pinned.book, pinned.chapter, -1), pinned.book, pinned.chapter), music.base + "/" + music.pinned?.[pinned.track]?.f);
}
if (unpinned !== undefined) {
  const bed = moodFor(moods, vm, "kjv", unpinned.book, unpinned.chapter, -1);
  eq("a pin the pack lacks falls back to its mood", packUrl(music, bed, unpinned.book, unpinned.chapter), packUrl(music, { mood: bed.mood, track: null }, unpinned.book, unpinned.chapter));
}
// Every canonical chapter resolves to a mood the pack or silence can serve.
let unserved = 0;
for (let b = 0; b < 66; b++) {
  for (let c = 0; c < 150; c++) {
    const m = moodFor(moods, vm, "kjv", b, c, -1);
    if (m.mood !== SILENCE && packUrl(music, m, b, c) === null) unserved += 1;
  }
}
eq("every mood has a pack track", unserved, 0);
eq("pack pick is stable", packUrl(music, { mood: "awe", track: null }, 3, 4), packUrl(music, { mood: "awe", track: null }, 3, 4));
eq("no music index -> bundled", packUrl(null, { mood: "awe", track: null }, 0, 0), null);
// Kotlin: "awe".fold(7) { a, c -> a * 31 + c.code } = 7*31^3 + ... wraps at 32 bits.
const k = (s: string) => {
  let h = 7n;
  for (const ch of s) h = BigInt.asIntN(32, h * 31n + BigInt(ch.codePointAt(0) as number));
  return Number(h);
};
const four = ["a", "b", "c", "d"];
for (const m of ["awe", "narrative", "lament", "judgment", "praise", "wisdom", "hope", "passion", "tender"]) {
  eq("bundledFor(" + m + ") matches Kotlin's wrap", bundledFor(four, m), four[((k(m) % 4) + 4) % 4]);
}
eq("bundledFor with no tracks", bundledFor([], "awe"), null);

// Control: HEXAPLA_AUDIO_BAD=1 asserts the pre-fix Android pivot (no +1),
// which gives KJV Ps 87's bed to the Synodal Ps 87; the run must FAIL.
if (process.env.HEXAPLA_AUDIO_BAD === "1") eq("control (must fail)", moodFor(moods, vm, "syn", PS, 86, -1).mood, moodFor(moods, null, "kjv", PS, 86, -1).mood);

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
