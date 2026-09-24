// P1 — the reader: translation picker, book/chapter, parallel view, deep links,
// share (WEB_APP_PLAN.md § 3). The look is the P0.5 design canvas (gate
// passed 2026-09-24; its link is in the session handoff, not here — this tree
// may name no remote origin, not even in a comment).
//
// The parallel view is the hexapla: the primary translation and up to five
// more (owner, 2026-09-24). One translation beside it keeps the two-column
// look the design gate passed; two or more label and tint each column.
//
// Audio (P3) lives in player.ts; this file only drives it and follows it:
// the sounding verse and word are lit in the PRIMARY column.
//
// Search (P2) is one translation at a time: search.ts, run in search.worker.ts.
// Offline and UI locales are P4 and deliberately absent.

import type { JSX } from "preact";
import { createPortal } from "preact/compat";
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { loadBook, loadBooksIndex, loadManifest, loadVersemap } from "./data";
import { chapterRows, type Row, type Side } from "./parallel";
import { Player, type AudioPrefs, type PlayState } from "./player";
import { FONT_MAX, FONT_MIN, MAX_PARALLEL, RATE_MAX, RATE_MIN, VOL_MIN, loadPrefs, parseWith, savePrefs, type BedKind, type Layout, type Prefs, type Theme } from "./prefs";
import { buildHash, parseRoute, type Route } from "./route";
import { directionOf, dropCapEnd, isCjk } from "./text";
import { SEARCH_CAP, SEARCH_MIN, type SearchHit } from "./search";
import type { SearchMsg, SearchReq } from "./search.worker";
// Unicode License v3 + Apache-2.0: the fold table's notice travels with it.
import cjkFoldNotice from "../../app/src/main/assets/CJK_FOLD_NOTICE.txt?url";
import type { Book, BooksIndex, Manifest, Translation } from "./types";
import { fromKjv, type Ref, type VerseMapData } from "./versemap";
import { EMPTY, HL_COUNT, bookmarkKey, bookmarksAt, canonKey, fromBackup, parseCanon, placeIn, sortedBookmarks, sortedCanon, toBackup, withBookmark, withHighlight, withNote, type Marks } from "./marks";
import { loadMarks, onOtherTab, saveMarks } from "./marksdb";
import { xrefsFor, type XrefData } from "./xrefs";
// The Android asset as is (2.2 MB, ~630 KB gzipped): fetched on the first
// Refs tap only, then kept for the page's life.
import xrefsUrl from "../../app/src/main/assets/xrefs.json?url";

// John 1: where a first-time reader with no link is most likely to start.
const START: Route = { translation: "kjv", book: 42, chapter: 0, verse: null };

/** A column narrower than this is not readable side by side; below it,
 *  «Auto» stacks (owner, 2026-09-24: ~260px). */
const COL_MIN = 250;

function initialRoute(prefs: Prefs): Route {
  return parseRoute(window.location.hash) ?? (prefs.last !== null ? parseRoute(prefs.last) : null) ?? START;
}

/** The label without its trailing «(EN)» language tag. */
function shortLabel(t: Translation | undefined, fallback: string): string {
  return t === undefined ? fallback : t.label.replace(/\s*\([^()]*\)\s*$/, "");
}

/** The name alone, for tight spots: «King James Version», «明治元訳». */
function tinyLabel(t: Translation | undefined, fallback: string): string {
  return shortLabel(t, fallback).split(" — ")[0].split(", ")[0].trim();
}

function refLabel(refs: Ref[], chapter: number | null): string {
  if (refs.length === 0) return "";
  const first = refs[0];
  const last = refs[refs.length - 1];
  const pre = (r: Ref) => (chapter !== null && r.c !== chapter ? String(r.c) + ":" : "");
  if (refs.length === 1) return pre(first) + String(first.v);
  return pre(first) + String(first.v) + "–" + (last.c !== first.c ? String(last.c) + ":" : "") + String(last.v);
}

function sameRefs(x: Ref[], y: Ref[]): boolean {
  return x.length === y.length && x.every((r, i) => r.c === y[i].c && r.v === y[i].v);
}

function moved<T>(xs: T[], i: number, d: number): T[] {
  const j = i + d;
  if (j < 0 || j >= xs.length) return xs;
  const out = xs.slice();
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

// ---------------------------------------------------------------------------
// Icons (the canvas's own strokes)

const I = {
  prev: <path d="M15 5l-7 7 7 7" />,
  next: <path d="M9 5l7 7-7 7" />,
  swap: <path d="M7 7h12l-3-3M17 17H5l3 3" />,
  aa: (
    <>
      <path d="M3 18l5-12 5 12M4.8 14h6.4" />
      <path d="M15 18l3-7.5 3 7.5M15.9 16h4.2" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6L6 18" />,
  link: <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />,
  copy: (
    <>
      <rect x="8" y="8" width="11" height="12" rx="2" />
      <path d="M5 16V6a2 2 0 0 1 2-2h8" />
    </>
  ),
  share: <path d="M12 15V4M8 8l4-4 4 4M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" />,
  back: <path d="M11 6l-6 6 6 6M5 12h14" />,
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </>
  ),
  chev: <path d="M9 6l6 6-6 6" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4.5 4.5" />
    </>
  ),
  up: <path d="M6 15l6-6 6 6" />,
  down: <path d="M6 9l6 6 6-6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  play: <path d="M8 5.5v13l10.5-6.5z" fill="currentColor" />,
  pause: (
    <>
      <rect x="6.5" y="5" width="3.5" height="14" rx="1" fill="currentColor" />
      <rect x="14" y="5" width="3.5" height="14" rx="1" fill="currentColor" />
    </>
  ),
  skipPrev: <path d="M7 5v14M18 5.5v13L9 12z" />,
  skipNext: <path d="M17 5v14M6 5.5v13L15 12z" />,
  pip: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <rect x="12" y="11" width="7" height="6" rx="1" fill="currentColor" />
    </>
  ),
  listen: <path d="M4 15v-3a8 8 0 0 1 16 0v3M4 15a2 2 0 0 1 2-2h1v7H6a2 2 0 0 1-2-2zM20 15a2 2 0 0 0-2-2h-1v7h1a2 2 0 0 0 2-2z" />,
  bookmark: <path d="M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1z" />,
  bookmarked: <path d="M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1z" fill="currentColor" />,
  note: <path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4" />,
  xref: <path d="M4 8h13l-3-3M20 16H7l3 3" />,
};

/** Android's HighlightColors (ReaderScreen.kt), same order: the index is stored. */
const HL_NAMES = ["Amber", "Green", "Blue", "Pink"];

function audioPrefs(p: Prefs): AudioPrefs {
  return { rate: p.rate, autoNext: p.autoNext, bed: p.bed, bedKind: p.bedKind, bedVolume: p.bedVolume, uniformBed: p.uniformBed };
}

function Icon({ d, size = 22 }: { d: JSX.Element; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      {d}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Verse text

/** `text` from `from` on, with the sounding word `[start, end)` in a <mark>.
 *  The range indexes the displayed text (build_web_data.strip_notes =
 *  parseAsset); a word inside a drop cap is clamped to after it. */
function marked(text: string, from: number, m: [number, number] | null): preact.ComponentChildren {
  if (m === null || m[1] <= from || m[0] >= text.length) return text.slice(from);
  const s = Math.max(m[0], from);
  return (
    <>
      {text.slice(from, s)}
      <mark class="word">{text.slice(s, m[1])}</mark>
      {text.slice(m[1])}
    </>
  );
}

function VerseText({ text, lang, cap, cls, word = null, after = null }: { text: string; lang: string; cap: boolean; cls: string; word?: [number, number] | null; after?: JSX.Element | null }) {
  const dir = directionOf(text) ?? undefined;
  const end = cap ? dropCapEnd(text) : -1;
  const c = cls + (isCjk(lang) ? " cjk" : "");
  if (end < 0) {
    return (
      <div class={c} lang={lang} dir={dir}>
        {marked(text, 0, word)}
        {after}
      </div>
    );
  }
  return (
    <div class={c} lang={lang} dir={dir}>
      <span class="dropcap" aria-hidden="true">
        {text.slice(0, end)}
      </span>
      <span class="sr">{text.slice(0, end)}</span>
      {marked(text, end, word)}
      {after}
    </div>
  );
}

/** The verse the narration is on: 1-based chapter and verse, and its word. */
interface Sounding {
  c: number;
  v: number;
  word: [number, number] | null;
}

function SideText({ side, lang, cls, chapter, showNum, noCap = false, hl = null, margin }: { side: Side; lang: string; cls: string; chapter: number; showNum: boolean; noCap?: boolean; hl?: Sounding | null; margin?: MarginFn }) {
  if (side.kind === "gap") return null;
  return (
    <>
      {side.texts.map((t, i) => {
        const r = side.refs[i];
        const cap = !noCap && r.v === 1 && i === 0;
        const word = hl !== null && hl.c === r.c && hl.v === r.v ? hl.word : null;
        return (
          <div class="vpart" key={String(r.c) + ":" + String(r.v)}>
            {showNum && !cap && <span class="inum">{refLabel([r], chapter)}</span>}
            <VerseText text={t} lang={lang} cap={cap} cls={cls} word={word} after={margin === undefined ? null : margin(r)} />
          </div>
        );
      })}
    </>
  );
}

/** The translator's margin-note marker for one verse, or null. */
type MarginFn = (r: Ref) => JSX.Element | null;

function Gap({ name, other }: { name: string; other: string | null }) {
  return (
    <div class="gap">
      <div class="gap-h">Not in this translation</div>
      <div class="gap-b">
        {name} has no verse here{other !== null ? ". " + other + " reads it alongside." : "."}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

interface Chapter {
  aId: string;
  /** The translations beside A that contain this book, in column order. */
  others: { id: string; book: Book }[];
  /** Ids read alongside that do NOT contain this book. */
  missing: string[];
  book: number;
  chapter: number; // 0-based
  a: Book;
  vm: VerseMapData | null;
}

/** One column on screen: the primary is index 0. */
interface Col {
  id: string;
  t: Translation | undefined;
  name: string;
  tiny: string;
  lang: string;
  book: Book;
  side: (r: Row) => Side;
}

// "text" is the quick Aa sheet; "prefs" is the full Settings menu, laid out
// in the Android app's own sections (owner, 2026-09-24). "par" is the list of
// translations read alongside; "add" picks one more for it.
// "note" edits the selected verse's note; "marks" lists bookmarks, highlights
// and notes.
type Sheet = null | "a" | "add" | "par" | "book" | "text" | "prefs" | "search" | "note" | "marks" | "xref" | "margin";

/** `?with=a,b,c` in a shared link opens the reader with those translations
 *  beside the first — what the sender was looking at. */
function initialPrefs(): Prefs {
  const p = loadPrefs();
  const w = parseWith(window.location.search);
  return w !== null ? { ...p, parallel: w, show: "all" } : p;
}

export function App() {
  const [prefs, setPrefs] = useState<Prefs>(initialPrefs);
  const [route, setRoute] = useState<Route>(() => initialRoute(prefs));
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [index, setIndex] = useState<BooksIndex | null>(null);
  const [chap, setChap] = useState<Chapter | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<Sheet>(null);
  // A picker opened from another sheet returns to it, not to the page.
  const [stack, setStack] = useState<Sheet[]>([]);
  const openFrom = (s: Sheet, from: Sheet) => (setStack([...stack, from]), setSheet(s));
  const done = () => (setSheet(stack.length > 0 ? stack[stack.length - 1] : null), setStack(stack.slice(0, -1)));
  const [selected, setSelected] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [wide, setWide] = useState<boolean>(() => window.matchMedia("(min-width: 960px)").matches);
  const [vw, setVw] = useState<number>(() => window.innerWidth);
  const scrollTo = useRef<number | null>(route.verse);
  // ONE player for the page's life; the reader follows its state.
  const [player] = useState(() => new Player(audioPrefs(prefs)));
  const [ps, setPs] = useState<PlayState>(player.state);
  const [canListen, setCanListen] = useState(false);
  const [credits, setCredits] = useState<string[]>([]);
  // Kept across openings: back from a hit, the list is where it was left.
  const [query, setQuery] = useState("");
  // Bookmarks, highlights, notes (marks.ts). `stored` false = this browser
  // gives no storage: marks still work until the page closes, and it says so.
  const [marks, setMarks] = useState<Marks>(EMPTY);
  const marksRef = useRef<Marks>(EMPTY);
  const [stored, setStored] = useState(true);
  // The versemap for every mark (63 KB, the same cached fetch the parallel
  // view uses): a note's key is the KJV position, whatever is being read.
  const [vmAll, setVmAll] = useState<VerseMapData | null>(null);
  const [noteEdit, setNoteEdit] = useState<{ key: string; label: string; text: string } | null>(null);
  // The row whose cross-references are open: its KJV keys, as marks use.
  const [xref, setXref] = useState<{ keys: string[]; label: string } | null>(null);
  const [margin, setMargin] = useState<{ label: string; notes: string[]; lang: string } | null>(null);

  const update = (p: Partial<Prefs>) =>
    setPrefs((old) => {
      const next = { ...old, ...p };
      savePrefs(next);
      return next;
    });

  // The hash is the source of truth for position; a link always wins.
  useEffect(() => {
    if (window.location.hash !== buildHash(route)) history.replaceState(null, "", buildHash(route));
    const onHash = () => {
      const r = parseRoute(window.location.hash);
      if (r === null) return;
      scrollTo.current = r.verse;
      setRoute(r);
    };
    window.addEventListener("hashchange", onHash);
    const mq = window.matchMedia("(min-width: 960px)");
    const onMq = () => setWide(mq.matches);
    mq.addEventListener("change", onMq);
    const onResize = () => setVw(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("hashchange", onHash);
      mq.removeEventListener("change", onMq);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  const go = (r: Route) => {
    scrollTo.current = r.verse;
    setSelected(null);
    setRoute(r);
    history.pushState(null, "", buildHash(r));
    if (r.verse === null) window.scrollTo(0, 0);
  };

  useEffect(() => {
    loadManifest().then(setManifest, (e) => setError(String(e)));
    loadVersemap().then(setVmAll, () => undefined);
    const reload = () =>
      void loadMarks().then((m) => {
        if (m === null) return setStored(false);
        marksRef.current = m;
        setMarks(m);
      });
    reload();
    return onOtherTab(reload);
  }, []);

  /** Change the marks: on screen at once, then written through. */
  const mutate = (f: (m: Marks) => Marks) => {
    const before = marksRef.current;
    const after = f(before);
    marksRef.current = after;
    setMarks(after);
    saveMarks(before, after).then(
      () => setStored(true),
      () => {
        if (stored) flash("Not kept: this browser is not saving site data");
        setStored(false);
      },
    );
  };

  const find = (id: string) => manifest?.translations.find((t) => t.id === id);
  const aT = find(route.translation);
  // Read alongside: known translations only, never the primary itself.
  const parIds = prefs.parallel.filter((id) => id !== route.translation && (manifest === null || find(id) !== undefined));
  const parKey = parIds.join(",");

  useEffect(() => {
    let live = true;
    setIndex(null);
    loadBooksIndex(route.translation).then(
      (x) => live && setIndex(x),
      (e) => live && setError(String(e)),
    );
    return () => {
      live = false;
    };
  }, [route.translation]);

  useEffect(() => {
    if (manifest === null) return;
    let live = true;
    setError(null);
    void (async () => {
      try {
        if (aT === undefined) throw new Error("There is no translation called «" + route.translation + "».");
        if (route.book >= aT.bookCount) throw new Error(shortLabel(aT, aT.id) + " does not contain book " + String(route.book + 1) + ".");
        const has = parIds.filter((id) => route.book < (find(id)?.bookCount ?? 0));
        const [a, vm, ...books] = await Promise.all([
          loadBook(route.translation, route.book),
          has.length > 0 ? loadVersemap() : Promise.resolve(null),
          ...has.map((id) => loadBook(id, route.book)),
        ]);
        if (route.chapter >= a.chapters.length) throw new Error(a.name + " has " + String(a.chapters.length) + " chapters.");
        if (live) {
          setChap({
            aId: route.translation,
            others: has.map((id, i) => ({ id, book: books[i] })),
            missing: parIds.filter((id) => !has.includes(id)),
            book: route.book,
            chapter: route.chapter,
            a,
            vm,
          });
        }
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, [manifest, route.translation, route.book, route.chapter, parKey]);

  const ready =
    chap !== null &&
    chap.aId === route.translation &&
    chap.book === route.book &&
    chap.chapter === route.chapter &&
    [...chap.others.map((o) => o.id), ...chap.missing].sort().join(",") === parIds.slice().sort().join(",");

  const rows: Row[] = useMemo(() => {
    if (chap === null) return [];
    const others = chap.others.map((o) => ({ id: o.id, book: o.book.chapters }));
    return chapterRows(chap.vm ?? {}, chap.book, chap.aId, chap.chapter + 1, chap.a.chapters, others);
  }, [chap]);

  // The columns on screen, primary first.
  const cols: Col[] =
    chap === null
      ? []
      : [
          { id: chap.aId, t: aT, book: chap.a, side: (r: Row) => r.a },
          ...chap.others.map((o, i) => ({ id: o.id, t: find(o.id), book: o.book, side: (r: Row) => r.others[i] })),
        ].map((c) => ({ ...c, name: shortLabel(c.t, c.id), tiny: tinyLabel(c.t, c.id), lang: c.t?.lang ?? "und" }));
  const multi = cols.length > 1;
  // «Show»: all columns, or one alone. A remembered id that is not on screen
  // (another book, removed) reads as «All».
  const alone = multi && prefs.show !== "all" ? cols.findIndex((c) => c.id === prefs.show) : -1;
  const shown = alone >= 0 ? [cols[alone]] : cols;

  // ---- marks on a row: the first shown column with text owns them ------------
  const leadOf = (r: Row): { c: Col; refs: Ref[] } | null => {
    for (const c of shown) {
      const s = c.side(r);
      if (s.kind === "text") return { c, refs: s.refs };
    }
    return null;
  };
  /** Canonical keys (KJV grid) of the row's verses; empty until the map loads. */
  const keysOf = (r: Row): string[] => {
    const l = leadOf(r);
    return l === null || vmAll === null ? [] : l.refs.map((x) => canonKey(vmAll, l.c.id, route.book, x.c, x.v));
  };
  /** Stored bookmarks, from any translation, that land on the row's verses. */
  const bookmarksOf = (r: Row): string[] => {
    const l = leadOf(r);
    return l === null || vmAll === null ? [] : l.refs.flatMap((x) => bookmarksAt(vmAll, marks, l.c.id, route.book, x.c - 1, x.v - 1));
  };
  const hlOf = (keys: string[]): number | null => {
    for (const k of keys) if (k in marks.highlights) return marks.highlights[k];
    return null;
  };

  // Deep link to a verse: bring it to the middle of the screen, select it.
  useEffect(() => {
    if (!ready || scrollTo.current === null) return;
    const v = scrollTo.current + 1;
    scrollTo.current = null;
    const row = rows.find((r) => r.a.kind === "text" && r.a.refs.some((x) => x.v === v));
    if (row === undefined) return;
    setSelected(row.key);
    requestAnimationFrame(() => document.getElementById("r-" + row.key)?.scrollIntoView({ block: "center" }));
  }, [ready, rows]);

  useEffect(() => {
    update({ last: buildHash({ ...route, verse: null }) });
  }, [route.translation, route.book, route.chapter]);

  // Theme on <html>, so the page background follows it too.
  useEffect(() => {
    const el = document.documentElement;
    if (prefs.theme === "auto") el.removeAttribute("data-theme");
    else el.setAttribute("data-theme", prefs.theme);
  }, [prefs.theme]);

  const bookName = chap?.a.name ?? index?.[route.book]?.name ?? "";
  useEffect(() => {
    if (bookName !== "") document.title = bookName + " " + String(route.chapter + 1) + " · " + shortLabel(aT, route.translation) + " · Hexapla";
  }, [bookName, route.chapter, aT]);

  // ---- audio -------------------------------------------------------------------
  useEffect(() => {
    const off = player.subscribe(setPs);
    return () => void off();
  }, []);

  useEffect(() => player.setPrefs(audioPrefs(prefs)), [prefs.rate, prefs.autoNext, prefs.bed, prefs.bedKind, prefs.bedVolume, prefs.uniformBed]);

  // Is there a recording of this chapter? The indexes (~1.7 MB, fetched
  // once) wait until the chapter itself is on screen.
  useEffect(() => {
    let live = true;
    const t = window.setTimeout(() => {
      player.hasAudio(route.translation, route.book, route.chapter).then(
        (x) => live && setCanListen(x),
        () => live && setCanListen(false),
      );
    }, 400);
    return () => {
      live = false;
      window.clearTimeout(t);
    };
  }, [route.translation, route.book, route.chapter]);

  // The chapter the player is on; a LibriVox section may hold several.
  const onAir = ps.status !== "idle" && ps.translation === route.translation && ps.book === route.book && ps.chapter === route.chapter;
  const sounding: Sounding | null = onAir && ps.verse >= 0 ? { c: route.chapter + 1, v: ps.verse + 1, word: ps.word } : null;

  // At the end of a chapter the player moves on; a reader who was on that
  // chapter turns the page with it.
  const aired = useRef<string | null>(null);
  useEffect(() => {
    if (ps.status === "idle" || ps.book < 0) {
      aired.current = null;
      return;
    }
    const key = ps.translation + "/" + String(ps.book) + "/" + String(ps.chapter);
    const was = aired.current;
    aired.current = key;
    if (was !== null && was !== key && was === route.translation + "/" + String(route.book) + "/" + String(route.chapter)) {
      go({ translation: ps.translation, book: ps.book, chapter: ps.chapter, verse: null });
    }
  }, [ps.translation, ps.book, ps.chapter, ps.status === "idle"]);

  // Keep the sounding verse on screen, without yanking a reader who is
  // merely a little ahead: only when it has left the viewport.
  useEffect(() => {
    if (sounding === null || !ready) return;
    const el = document.querySelector(".row.play");
    if (el === null) return;
    const r = el.getBoundingClientRect();
    if (r.top < 80 || r.bottom > window.innerHeight - 90) el.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [sounding?.v, ready]);

  useEffect(() => {
    if (sheet === "prefs" && credits.length === 0) player.musicCredits().then(setCredits, () => undefined);
  }, [sheet]);

  // Pop-out player (Document PiP): a small always-on-top window that keeps the
  // controls in reach when the reader switches to another tab or app.
  const [pip, setPip] = useState<Window | null>(null);
  const popOut = async () => {
    if (docPip === undefined || docPip.window !== null) return;
    try {
      const w = await docPip.requestWindow({ width: 420, height: 84 });
      dressPip(w);
      w.addEventListener("pagehide", () => setPip(null));
      setPip(w);
    } catch {
      // Refused (no user gesture, or the browser said no): stay in the page.
    }
  };
  useEffect(() => {
    if (ps.status === "idle" && pip !== null) pip.close();
  }, [ps.status === "idle", pip]);
  // Chrome may open it by itself when the tab is left while audio plays
  // («automatic picture-in-picture», Chrome 134+); elsewhere this is a no-op.
  useEffect(() => {
    if (docPip === undefined || !("mediaSession" in navigator)) return;
    try {
      navigator.mediaSession.setActionHandler("enterpictureinpicture" as MediaSessionAction, () => void popOut());
    } catch {
      // Not a known action here.
    }
  }, []);

  const listen = (verse: number) => player.play(route.translation, aName, route.book, route.chapter, verse);

  const step = (delta: number): Route | null => {
    if (index === null) return null;
    let b = route.book;
    let c = route.chapter + delta;
    if (c < 0) {
      b -= 1;
      if (b < 0) return null;
      c = index[b].chapters.length - 1;
    } else if (c >= (index[b]?.chapters.length ?? 0)) {
      b += 1;
      c = 0;
      if (b >= index.length) return null;
    }
    return { translation: route.translation, book: b, chapter: c, verse: null };
  };
  const prev = step(-1);
  const next = step(1);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (sheet !== null || e.altKey || e.ctrlKey || e.metaKey) return;
      if ((e.target as HTMLElement | null)?.closest("input, textarea, select") != null) return;
      if (e.key === "ArrowLeft" && prev !== null) go(prev);
      else if (e.key === "ArrowRight" && next !== null) go(next);
      else if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // Swipe between chapters, as on Android (ReaderScreen.kt pointerInput):
  // a mostly-horizontal drag past a threshold; toward the reading direction
  // is next, flipped for a right-to-left UI. Not from inside something that
  // scrolls sideways itself (the parallel columns, the chips).
  const swipe = useRef<{ x: number; y: number; t: number } | null>(null);
  const scrollsX = (el: Element | null): boolean => {
    for (let e = el; e !== null && e !== document.body; e = e.parentElement) {
      if (e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== "visible" && getComputedStyle(e).overflowX !== "hidden") return true;
    }
    return false;
  };
  const onTouchStart = (e: TouchEvent) => {
    const t = e.touches[0];
    swipe.current = e.touches.length === 1 && !scrollsX(e.target as Element) ? { x: t.clientX, y: t.clientY, t: Date.now() } : null;
  };
  const onTouchEnd = (e: TouchEvent) => {
    const s0 = swipe.current;
    swipe.current = null;
    if (s0 === null || sheet !== null) return;
    const t = e.changedTouches[0];
    const dx = (t.clientX - s0.x) * (document.documentElement.dir === "rtl" ? -1 : 1);
    const dy = t.clientY - s0.y;
    if (Date.now() - s0.t > 800 || Math.abs(dx) < 70 || Math.abs(dx) < 2 * Math.abs(dy)) return;
    if (dx < 0 && next !== null) go(next);
    else if (dx > 0 && prev !== null) go(prev);
  };

  const flash = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast((t) => (t === msg ? null : t)), 1800);
  };

  // ---- share: every column on screen ------------------------------------------
  const selRow = rows.find((r) => r.key === selected) ?? null;
  const selVerse = selRow !== null && selRow.a.kind === "text" ? selRow.a.refs[0].v - 1 : null;
  const selRoute: Route = { ...route, verse: selVerse };
  // The recipient opens what the sender sees: every column, unless the
  // primary was being read alone.
  const withIds = alone === 0 ? [] : cols.slice(1).map((c) => c.id);
  const selLink = window.location.origin + window.location.pathname + (withIds.length > 0 ? "?with=" + withIds.join(",") : "") + buildHash(selRoute);
  const selRef = (() => {
    if (selRow === null) return "";
    if (selRow.a.kind === "text" && alone <= 0) return bookName + " " + String(route.chapter + 1) + ":" + refLabel(selRow.a.refs, null);
    for (const c of shown) {
      const s = c.side(selRow);
      if (s.kind === "text") return c.book.name + " " + refLabel(s.refs, -1);
    }
    return "";
  })();

  useEffect(() => {
    if (selVerse !== null) history.replaceState(null, "", buildHash(selRoute));
  }, [selected]);

  const selText = (): string => {
    if (selRow === null) return "";
    const parts: string[] = [];
    for (const c of shown) {
      const s = c.side(selRow);
      if (s.kind === "text") parts.push(s.texts.join(" ") + "\n— " + c.book.name + " " + refLabel(s.refs, -1) + " (" + c.name + ")");
    }
    return parts.join("\n\n") + "\n" + selLink;
  };

  const copy = async (s: string, done: string) => {
    try {
      await navigator.clipboard.writeText(s);
      flash(done);
    } catch {
      flash("Copying is blocked in this browser");
    }
  };

  const canShare = typeof navigator.share === "function";

  // ---- marks on the selected verse ----------------------------------------------
  const openNote = (key: string, label: string) => {
    setNoteEdit({ key, label, text: marksRef.current.notes[key] ?? "" });
    openFrom("note", null);
  };
  const selKeys = selRow === null ? [] : keysOf(selRow);
  const selHl = hlOf(selKeys);
  const selBms = selRow === null ? [] : bookmarksOf(selRow);
  // A row that is a block (several verses together) is marked as a whole.
  const setSelHl = (c: number | null) => mutate((m) => selKeys.reduce((acc, k) => withHighlight(acc, k, c), m));
  const toggleSelBm = () => {
    const l = selRow === null ? null : leadOf(selRow);
    if (l === null) return;
    if (selBms.length > 0) {
      mutate((m) => selBms.reduce((acc, k) => withBookmark(acc, k, false), m));
      flash("Bookmark removed");
    } else {
      const x = l.refs[0];
      mutate((m) => withBookmark(m, bookmarkKey({ id: l.c.id, book: route.book, chapter: x.c - 1, verse: x.v - 1 }), true));
      flash("Bookmarked");
    }
  };

  // ---- backup: the Android app's own file («Settings › Backup») -------------------
  const fileIn = useRef<HTMLInputElement>(null);
  const saveBackup = () => {
    const blob = new Blob([toBackup(marksRef.current, vmAll ?? {})], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "hexapla-backup.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  };
  const restoreBackup = async (f: File) => {
    const r = fromBackup(await f.text(), marksRef.current);
    if (r === null) return flash("That file is not a Hexapla backup");
    mutate(() => r.marks);
    const n = r.read;
    flash("Restored " + String(n.bookmarks) + " bookmarks, " + String(n.highlights) + " highlights, " + String(n.notes) + " notes");
  };

  // ---- layout -------------------------------------------------------------------
  const style = { "--fs": String(prefs.fontSize) + "px" } as JSX.CSSProperties;
  const n = shown.length;
  // Room for the text column: the page minus its padding (and the chapter
  // rail on a wide screen). Two columns keep the design's centre gutter.
  const gutter = n === 2 ? 56 : 40;
  const room = wide ? vw - 264 - 112 : vw - 40;
  const fits = n * COL_MIN + gutter <= room;
  const side = n > 1 && (prefs.layout === "side" || (prefs.layout === "auto" && wide && fits));
  // An explicit «Side by side» that does not fit scrolls sideways.
  const scroll = side && !fits;
  const aName = cols[0]?.name ?? shortLabel(aT, route.translation);
  const aLang = aT?.lang ?? "und";
  const chapNo = route.chapter + 1;
  const tint = (i: number) => ({ "--tc": "var(--c" + String(i) + ")" }) as JSX.CSSProperties;
  const parLabel = (() => {
    if (parIds.length === 0) return "+ Parallel";
    const first = wide ? shortLabel(find(parIds[0]), parIds[0]) : tinyLabel(find(parIds[0]), parIds[0]);
    return parIds.length === 1 ? first : first + " +" + String(parIds.length - 1);
  })();

  const header = (
    <header class="bar">
      {wide && (
        <a class="mark" href="../">
          Hexapla
        </a>
      )}
      <div class="tr">
        <button type="button" class="btn tbtn" onClick={() => openFrom("a", null)} aria-label={"Translation: " + aName}>
          <span class="ell">{wide ? aName : tinyLabel(aT, route.translation)}</span>
        </button>
        {parIds.length === 1 && (
          <button
            type="button"
            class="ib"
            aria-label="Swap translations"
            onClick={() => {
              update({ parallel: [route.translation] });
              go({ ...route, translation: parIds[0], verse: null });
            }}
          >
            <Icon d={I.swap} size={20} />
          </button>
        )}
        <button
          type="button"
          class={"btn tbtn" + (parIds.length === 0 ? " add" : "")}
          onClick={() => openFrom(parIds.length === 0 ? "add" : "par", null)}
          aria-label={parIds.length === 0 ? "Add a parallel translation" : "Parallel translations: " + parIds.map((id) => shortLabel(find(id), id)).join(", ")}
        >
          <span class="ell">{parLabel}</span>
        </button>
      </div>
      <button type="button" class="ib" aria-label="Search" onClick={() => openFrom("search", null)}>
        <Icon d={I.search} size={22} />
      </button>
      {/* A narrow phone keeps three icons; the list is in Settings there too. */}
      {(wide || vw >= 400) && (
        <button type="button" class="ib" aria-label="Bookmarks, highlights and notes" onClick={() => openFrom("marks", null)}>
          <Icon d={I.bookmark} size={21} />
        </button>
      )}
      <button type="button" class="ib" aria-label="Text size and theme" onClick={() => openFrom("text", null)}>
        <Icon d={I.aa} size={24} />
      </button>
      <button type="button" class="ib" aria-label="Settings" onClick={() => openFrom("prefs", null)}>
        <Icon d={I.gear} size={22} />
      </button>
    </header>
  );

  const nav = (
    <div class="nav">
      <button type="button" class="ib" aria-label="Previous chapter" disabled={prev === null} onClick={() => prev !== null && go(prev)}>
        <Icon d={I.prev} />
      </button>
      <button type="button" class="btn title" onClick={() => setSheet("book")} lang={aLang} dir={directionOf(bookName) ?? undefined}>
        {bookName} {chapNo}
      </button>
      <button type="button" class="ib" aria-label="Next chapter" disabled={next === null} onClick={() => next !== null && go(next)}>
        <Icon d={I.next} />
      </button>
    </div>
  );

  const chapterGrid = (bi: number, onPick: (c: number) => void) => (
    <div class="chgrid">
      {(index?.[bi]?.chapters ?? []).map((_, c) => (
        <button type="button" key={c} class={"ch" + (bi === route.book && c === route.chapter ? " cur" : "")} aria-current={bi === route.book && c === route.chapter ? "page" : undefined} onClick={() => onPick(c)}>
          {c + 1}
        </button>
      ))}
    </div>
  );

  // The Show bar: «All» and one chip per translation, to read one alone.
  const showBar = (label: string) => (
    <div class="modes chips" role="group" aria-label={label}>
      {[["all", "All"] as [string, string], ...cols.map((c) => [c.id, c.tiny] as [string, string])].map(([id, l]) => {
        const on = id === "all" ? alone < 0 : cols[alone]?.id === id;
        return (
          <button type="button" key={id} class={"seg" + (on ? " sel" : "")} aria-pressed={on} onClick={() => update({ show: id })}>
            <span class="ell">{l}</span>
          </button>
        );
      })}
    </div>
  );

  let body: JSX.Element;
  if (error !== null) {
    body = (
      <div class="msg">
        <p>{error}</p>
        <p>
          <a href={buildHash(START)} onClick={(e) => (e.preventDefault(), go(START))}>
            Open John 1
          </a>
        </p>
      </div>
    );
  } else if (!ready || chap === null) {
    body = (
      <div class="loading" aria-busy="true" aria-label="Loading the chapter">
        {[92, 100, 84, 97, 70, 88, 95, 60].map((w, i) => (
          <div key={i} class="sk" style={{ width: String(w) + "%" }} />
        ))}
      </div>
    );
  } else {
    const heading = (
      <div class="chead">
        <div class="cnum">{chapNo}</div>
        <div class="cname" lang={aLang} dir={directionOf(chap.a.name) ?? undefined}>
          {chap.a.name}
        </div>
        {canListen && (
          <button
            type="button"
            class="btn listen"
            aria-label={onAir && ps.status === "playing" ? "Pause" : "Listen to this chapter"}
            onClick={() => (onAir && ps.status !== "error" && ps.status !== "loading" ? player.toggle() : listen(0))}
          >
            <Icon d={onAir && ps.status === "playing" ? I.pause : I.listen} size={20} />
            <span>{onAir && ps.status === "playing" ? "Pause" : "Listen"}</span>
          </button>
        )}
      </div>
    );
    // Column index (into `cols`) of each shown column, for its tint.
    const ci = (c: Col) => cols.indexOf(c);
    const grid = { gridTemplateColumns: n === 2 ? "minmax(0, 1fr) 56px minmax(0, 1fr)" : "40px repeat(" + String(n) + ", minmax(0, 1fr))" } as JSX.CSSProperties;
    const scrollW = scroll ? ({ minWidth: String(n * 240 + gutter + 16) + "px" } as JSX.CSSProperties) : undefined;
    // One other column beside A keeps the passed design; more are labelled.
    const labelled = n > 2;
    const colHeads = side && (
      <div class={"colheads w" + (n > 2 ? " n" : "")} style={{ ...grid, ...scrollW }}>
        {n > 2 && <div />}
        {shown.flatMap((c, i) => [
          ...(n === 2 && i === 1 ? [<div key="gutter" />] : []),
          <div key={c.id} class={labelled ? "tc" : undefined} style={labelled ? tint(ci(c)) : undefined} lang={c.lang}>
            {c.name}
          </div>,
        ])}
      </div>
    );
    const missing = chap.missing.map((id) => shortLabel(find(id), id));
    const verses = (
      <div class={"verses" + (side ? " cols" : "")} style={scrollW}>
        {rows.map((r) => {
          const sel = r.key === selected;
          const lead = shown.find((c) => c.side(r).kind === "text");
          if (lead === undefined) return null; // nothing to show in the shown columns
          const leadSide = lead.side(r) as Extract<Side, { kind: "text" }>;
          const pick = () => setSelected(sel ? null : r.key);
          const onKey = (e: KeyboardEvent) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              pick();
            }
          };
          // The row's number is the first shown column's; the number gutter
          // sits on that verse's own reading side.
          const numOf = shown[0].side(r);
          const num = numOf.kind === "text" ? (numOf.refs[0].v === 1 ? "" : refLabel(numOf.refs, chapNo)) : "";
          const rowDir = directionOf(leadSide.texts[0]) ?? undefined;
          // The narration reads the primary translation, so its refs decide.
          const play = sounding !== null && r.a.kind === "text" && r.a.refs.some((x) => x.c === sounding.c && x.v === sounding.v);
          const keys = keysOf(r);
          const hl = hlOf(keys);
          const bm = bookmarksOf(r).length > 0;
          const notes = keys.filter((k) => k in marks.notes);
          const common = {
            dir: rowDir,
            id: "r-" + r.key,
            class: "row" + (sel ? " sel" : "") + (play ? " play" : "") + (hl !== null ? " hl" + String(hl) : ""),
            onClick: pick,
            onKeyDown: onKey,
            tabIndex: 0,
            "aria-pressed": sel,
          };
          const numCell = (cls: string) => (
            <div class={cls}>
              {bm && (
                <span class="bmk" role="img" aria-label="Bookmarked">
                  <Icon d={I.bookmarked} size={13} />
                </span>
              )}
              {num}
            </div>
          );
          const noteEl =
            notes.length > 0 ? (
              <div class="rnote">
                {notes.map((k) => (
                  <button
                    type="button"
                    key={k}
                    class="rn"
                    dir="auto"
                    aria-label="Edit note"
                    onClick={(e) => {
                      e.stopPropagation();
                      openNote(k, lead.book.name + " " + refLabel(leadSide.refs, -1));
                    }}
                  >
                    <Icon d={I.note} size={14} />
                    <span>{marks.notes[k]}</span>
                  </button>
                ))}
              </div>
            ) : null;
          // The translator's margin notes (KJV, Luther, a few others), kept by
          // the build per book at the column's own "c:v", 0-based; Android
          // shows them from the verse's actions (BibleRepo.notes).
          const marginOf = (c: Col): MarginFn | undefined => {
            const mn = c.book.notes;
            if (mn === undefined) return undefined;
            return (x: Ref) => {
              const list = mn[String(x.c - 1) + ":" + String(x.v - 1)];
              if (list === undefined) return null;
              const label = c.book.name + " " + String(x.c) + ":" + String(x.v);
              return (
                <button
                  type="button"
                  class="mn"
                  aria-label={"Translator's note, " + label}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMargin({ label, notes: list, lang: c.lang });
                    openFrom("margin", null);
                  }}
                >
                  †
                </button>
              );
            };
          };
          // A verse number inside a cell only where that column's verses
          // differ from the row's own numbering.
          const base = numOf.kind === "text" ? numOf.refs : [];
          const cell = (c: Col, secondary: boolean) => {
            const s = c.side(r);
            const nameOfText = shown.find((x) => x !== c && x.side(r).kind === "text")?.name ?? null;
            if (s.kind === "gap") return labelled ? <div class="gap1">Not in {c.tiny}</div> : <Gap name={c.name} other={nameOfText} />;
            return <SideText side={s} lang={c.lang} cls={secondary && !side ? "vt b" : "vt"} chapter={chapNo} showNum={s.refs.length > 1 || (secondary && !sameRefs(s.refs, base))} noCap={labelled && secondary && !side} hl={c === cols[0] ? sounding : null} margin={marginOf(c)} />;
          };
          if (n === 1) {
            const c = shown[0];
            const s = c.side(r);
            if (s.kind === "gap") return null;
            return (
              <div {...common} class={common.class + " single"}>
                {numCell("num")}
                <div class="txt">
                  <SideText side={s} lang={c.lang} cls="vt" chapter={chapNo} showNum={s.refs.length > 1} hl={c === cols[0] ? sounding : null} margin={marginOf(c)} />
                </div>
                {noteEl}
              </div>
            );
          }
          if (side && n === 2) {
            return (
              <div {...common} class={common.class + " triple"} style={grid}>
                <div class="cell">{cell(shown[0], false)}</div>
                {numCell("num mid")}
                <div class="cell">{cell(shown[1], true)}</div>
                {noteEl}
              </div>
            );
          }
          if (side) {
            return (
              <div {...common} class={common.class + " grid"} style={grid}>
                {numCell("num")}
                {shown.map((c, i) => (
                  <div class="cell" key={c.id}>
                    {cell(c, i > 0)}
                  </div>
                ))}
                {noteEl}
              </div>
            );
          }
          return (
            <div {...common} class={common.class + " single"}>
              {numCell("num")}
              <div class="txt stack">
                {cell(shown[0], false)}
                {shown.slice(1).map((c) =>
                  labelled ? (
                    <div class="oc" key={c.id} style={tint(ci(c))}>
                      <div class="ol" lang={c.lang}>
                        {c.tiny}
                      </div>
                      {cell(c, true)}
                    </div>
                  ) : (
                    <div key={c.id}>{cell(c, true)}</div>
                  ),
                )}
              </div>
              {noteEl}
            </div>
          );
        })}
      </div>
    );
    body = (
      <>
        {heading}
        {multi && showBar("Text shown")}
        {missing.length > 0 && (
          <p class="note">
            {missing.join(", ")} {missing.length === 1 ? "does" : "do"} not contain {chap.a.name}.
          </p>
        )}
        {scroll ? (
          <div class="hscroll">
            {colHeads}
            {verses}
          </div>
        ) : (
          <>
            {colHeads}
            {verses}
          </>
        )}
        <div class="endnav">
          {prev !== null && (
            <button type="button" class="btn" onClick={() => go(prev)}>
              <Icon d={I.prev} size={18} /> Previous
            </button>
          )}
          {next !== null && (
            <button type="button" class="btn" onClick={() => go(next)}>
              Next <Icon d={I.next} size={18} />
            </button>
          )}
        </div>
      </>
    );
  }

  // Text size and theme: the Aa sheet and Settings › Appearance share them.
  const textControls = (
    <>
      <label class="field">
        <span>Text size</span>
        <input type="range" min={FONT_MIN} max={FONT_MAX} step={1} value={prefs.fontSize} onInput={(e) => update({ fontSize: Number((e.target as HTMLInputElement).value) })} />
        <span class="val">{prefs.fontSize}</span>
      </label>
      <p class="preview" style={{ fontSize: String(prefs.fontSize) + "px" }}>
        In the beginning was the Word.
      </p>
      <div class="modes" role="group" aria-label="Theme">
        {(
          [
            ["auto", "Device"],
            ["light", "Light"],
            ["dark", "Dark"],
          ] as [Theme, string][]
        ).map(([t, l]) => (
          <button type="button" key={t} class={"seg" + (prefs.theme === t ? " sel" : "")} aria-pressed={prefs.theme === t} onClick={() => update({ theme: t })}>
            {l}
          </button>
        ))}
      </div>
    </>
  );

  // ---- sheets ------------------------------------------------------------------
  const full = parIds.length >= MAX_PARALLEL;
  let sheetEl: JSX.Element | null = null;
  if (sheet === "a" || sheet === "add") {
    const adding = sheet === "add";
    const list = manifest?.translations ?? [];
    sheetEl = (
      <Sheet title={adding ? "Read alongside" : "Translation"} onClose={done} back={stack.length > 0 && stack[stack.length - 1] !== null ? done : undefined}>
        <div class="list">
          {list
            .filter((t) => !adding || (t.id !== route.translation && !parIds.includes(t.id)))
            .map((t) => {
              const cur = !adding && t.id === route.translation;
              return (
                <button
                  type="button"
                  key={t.id}
                  class={"li" + (cur ? " cur" : "")}
                  lang={t.lang}
                  dir={directionOf(t.label) ?? undefined}
                  aria-current={cur ? "true" : undefined}
                  onClick={() => {
                    done();
                    if (adding) update({ parallel: [...parIds, t.id].slice(0, MAX_PARALLEL) });
                    else {
                      // The new primary leaves the parallel list; the old one
                      // takes its place there, so no column is lost.
                      if (parIds.includes(t.id)) update({ parallel: parIds.map((id) => (id === t.id ? route.translation : id)) });
                      const book = route.book < t.bookCount ? route.book : START.book;
                      go({ translation: t.id, book, chapter: book === route.book ? route.chapter : 0, verse: null });
                    }
                  }}
                >
                  {t.label}
                </button>
              );
            })}
        </div>
      </Sheet>
    );
  } else if (sheet === "par") {
    sheetEl = (
      <Sheet title="Parallel translations" onClose={done} back={stack.length > 0 && stack[stack.length - 1] !== null ? done : undefined}>
        <p class="hint">
          Up to six translations at once, verse by verse. {aName} leads; the others follow in this order.
        </p>
        <div class="list">
          <div class="li plain" lang={aLang}>
            <span class="ell">{aName}</span>
          </div>
          {parIds.map((id, i) => (
            <div class="li prow" key={id} style={tint(i + 1)}>
              <span class="dot" aria-hidden="true" />
              <span class="ell" lang={find(id)?.lang}>
                {shortLabel(find(id), id)}
              </span>
              <button type="button" class="ib" aria-label="Move up" disabled={i === 0} onClick={() => update({ parallel: moved(parIds, i, -1) })}>
                <Icon d={I.up} size={20} />
              </button>
              <button type="button" class="ib" aria-label="Move down" disabled={i === parIds.length - 1} onClick={() => update({ parallel: moved(parIds, i, 1) })}>
                <Icon d={I.down} size={20} />
              </button>
              <button type="button" class="ib" aria-label={"Remove " + shortLabel(find(id), id)} onClick={() => update({ parallel: parIds.filter((x) => x !== id) })}>
                <Icon d={I.close} size={20} />
              </button>
            </div>
          ))}
        </div>
        <div class="pact">
          <button type="button" class="btn" disabled={full} onClick={() => openFrom("add", "par")}>
            <Icon d={I.plus} size={18} /> {full ? "Six is the most" : "Add a translation"}
          </button>
          {parIds.length > 0 && (
            <button type="button" class="btn" onClick={() => (update({ parallel: [] }), done())}>
              One translation only
            </button>
          )}
        </div>
      </Sheet>
    );
  } else if (sheet === "book") {
    sheetEl = <BookSheet index={index} lang={aLang} current={route} grid={chapterGrid} onClose={() => setSheet(null)} onPick={(b, c) => (setSheet(null), go({ ...route, book: b, chapter: c, verse: null }))} />;
  } else if (sheet === "search") {
    sheetEl = (
      <SearchSheet
        t={route.translation}
        name={aName}
        lang={aLang}
        index={index}
        query={query}
        setQuery={setQuery}
        onClose={done}
        onPick={(h) => (done(), go({ translation: route.translation, book: h.b, chapter: h.c, verse: h.v }))}
      />
    );
  } else if (sheet === "note" && noteEdit !== null) {
    const had = noteEdit.key in marks.notes;
    const save = (text: string) => {
      mutate((m) => withNote(m, noteEdit.key, text));
      setNoteEdit(null);
      done();
    };
    sheetEl = (
      <Sheet title={"Note · " + noteEdit.label} onClose={() => (setNoteEdit(null), done())}>
        <textarea
          class="ntext"
          dir="auto"
          rows={6}
          aria-label="Note"
          value={noteEdit.text}
          onInput={(e) => setNoteEdit({ ...noteEdit, text: (e.target as HTMLTextAreaElement).value })}
        />
        <p class="hint">Kept in this browser only. The note stays with the verse in every translation.</p>
        <div class="pact">
          <button type="button" class="btn pri" onClick={() => save(noteEdit.text)}>
            Save
          </button>
          {had && (
            <button type="button" class="btn" onClick={() => save("")}>
              Delete note
            </button>
          )}
        </div>
      </Sheet>
    );
  } else if (sheet === "margin" && margin !== null) {
    sheetEl = (
      <Sheet title={"Translator's notes · " + margin.label} onClose={() => (setMargin(null), done())}>
        <div class="mnotes">
          {margin.notes.map((t, i) => (
            <p key={i} lang={margin.lang} dir="auto">
              {t}
            </p>
          ))}
        </div>
      </Sheet>
    );
  } else if (sheet === "xref" && xref !== null) {
    sheetEl = (
      <XrefSheet
        keys={xref.keys}
        label={xref.label}
        vm={vmAll}
        lang={aLang}
        t={route.translation}
        index={index}
        onClose={() => (setXref(null), done())}
        onPick={(b, c, v) => (setXref(null), done(), go({ translation: route.translation, book: b, chapter: c, verse: v }))}
      />
    );
  } else if (sheet === "marks") {
    sheetEl = (
      <MarksSheet
        marks={marks}
        vm={vmAll}
        t={route.translation}
        lang={aLang}
        index={index}
        stored={stored}
        onClose={done}
        onPick={(b, c, v) => (done(), go({ translation: route.translation, book: b, chapter: c, verse: v }))}
        onChange={mutate}
        onSave={saveBackup}
        onRestore={() => fileIn.current?.click()}
      />
    );
  } else if (sheet === "text") {
    sheetEl = (
      <Sheet title="Text" onClose={done}>
        {textControls}
      </Sheet>
    );
  } else if (sheet === "prefs") {
    const split = parIds.length > 0;
    const seg = <T extends string>(label: string, cur: T, opts: [T, string][], set: (v: T) => void) => (
      <div class="modes" role="group" aria-label={label}>
        {opts.map(([v, l]) => (
          <button type="button" key={v} class={"seg" + (cur === v ? " sel" : "")} aria-pressed={cur === v} onClick={() => set(v)}>
            <span class="ell">{l}</span>
          </button>
        ))}
      </div>
    );
    // Rows for what Android has and the web app does not have yet: listed, so
    // the menu already has its final shape, but never pretending to work.
    const soon = (title: string, note: string) => (
      <div class="srow off" aria-disabled="true">
        <div class="st">
          <span>{title}</span>
          <span class="sn">{note}</span>
        </div>
        <span class="badge">Coming</span>
      </div>
    );
    const toggle = (title: string, note: string, on: boolean, flip: () => void) => (
      <button type="button" class="srow" role="switch" aria-checked={on} onClick={flip}>
        <div class="st">
          <span>{title}</span>
          <span class="sn">{note}</span>
        </div>
        <span class={"sw" + (on ? " on" : "")} aria-hidden="true" />
      </button>
    );
    sheetEl = (
      <Sheet title="Settings" onClose={done}>
        <h3 class="sec">Reading</h3>
        <button type="button" class="srow" onClick={() => openFrom("a", "prefs")}>
          <div class="st">
            <span>Translation</span>
            <span class="sn" lang={aLang}>{aName}</span>
          </div>
          <Icon d={I.chev} size={18} />
        </button>
        <button type="button" class="srow" role="switch" aria-checked={split} onClick={() => (split ? update({ parallel: [] }) : openFrom("add", "prefs"))}>
          <div class="st">
            <span>Split view</span>
            <span class="sn">Translations side by side, verse by verse</span>
          </div>
          <span class={"sw" + (split ? " on" : "")} aria-hidden="true" />
        </button>
        {split && (
          <>
            <button type="button" class="srow" onClick={() => openFrom("par", "prefs")}>
              <div class="st">
                <span>Parallel translations</span>
                <span class="sn">{parIds.map((id) => tinyLabel(find(id), id)).join(" · ")}</span>
              </div>
              <Icon d={I.chev} size={18} />
            </button>
            {multi && (
              <div class="sfield">
                <span>Show</span>
                {showBar("Text shown")}
              </div>
            )}
            <div class="sfield">
              <span>Split layout</span>
              {seg<Layout>("Split layout", prefs.layout, [["auto", "Auto"], ["side", "Side by side"], ["stacked", "Stacked"]], (l) => update({ layout: l }))}
            </div>
          </>
        )}
        <button type="button" class="srow" onClick={() => openFrom("marks", "prefs")}>
          <div class="st">
            <span>Bookmarks, highlights and notes</span>
            <span class="sn">{markCount(marks)}</span>
          </div>
          <Icon d={I.chev} size={18} />
        </button>
        <h3 class="sec">Appearance</h3>
        {textControls}
        <h3 class="sec">Study</h3>
        {soon("Strong's numbers (KJV)", "Tap a number for the Hebrew or Greek word and its definition.")}
        {soon("Webster's 1828 Dictionary", "Tap an English word for what it meant in the era of the classic Bibles.")}
        <h3 class="sec">Listening</h3>
        {!player.opus && <p class="hint">This browser cannot play the generated narration (Ogg Opus). The King James Version's LibriVox readings still play.</p>}
        <label class="field">
          <span>Reading speed</span>
          <input type="range" min={RATE_MIN} max={RATE_MAX} step={0.05} value={prefs.rate} onInput={(e) => update({ rate: Number((e.target as HTMLInputElement).value) })} />
          <span class="val wide">{prefs.rate.toFixed(2)}×</span>
        </label>
        {toggle("Continue to the next chapter", "When a chapter ends, go on to the next one.", prefs.autoNext, () => update({ autoNext: !prefs.autoNext }))}
        {toggle("Background while listening", "Music or a fireside underneath the narration.", prefs.bed, () => {
          // iOS lets the bed start later only if this tap has played it.
          if (!prefs.bed) player.unlockBed();
          update({ bed: !prefs.bed });
        })}
        {prefs.bed && (
          <>
            <div class="sfield">
              <span>Background</span>
              {seg<BedKind>("Background", prefs.bedKind, [["music", "Music"], ["fireside", "Fireside"]], (k) => (player.unlockBed(), update({ bedKind: k })))}
            </div>
            <label class="field">
              <span>Volume</span>
              <input type="range" min={VOL_MIN} max={1} step={0.05} value={prefs.bedVolume} onInput={(e) => update({ bedVolume: Number((e.target as HTMLInputElement).value) })} />
              <span class="val">{Math.round(prefs.bedVolume * 100)}</span>
            </label>
            {prefs.bedKind === "music" && toggle("Same music throughout", "One calm track after another, instead of music matched to the passage.", prefs.uniformBed, () => update({ uniformBed: !prefs.uniformBed }))}
          </>
        )}
        <h3 class="sec">Backup</h3>
        {backupRows(stored, saveBackup, () => fileIn.current?.click())}
        {/* The sources_text credit is a licence obligation: verbatim, at the
            foot of Settings as on Android, never on every chapter (owner,
            2026-09-24: a footnote here, not in the Aa sheet). */}
        {manifest !== null && (
          <footer class="foot">
            {/* Collapsed to its title; the credit opens on tap (owner,
                2026-09-24: the full text on show was too messy). */}
            <details class="src">
              <summary>Text sources</summary>
              <p>{manifest.credits}</p>
              <p>
                Chinese and Japanese search matches character variants using Unihan (Unicode License v3) and OpenCC (Apache-2.0):{" "}
                <a href={cjkFoldNotice} target="_blank" rel="noopener">licences</a>.
              </p>
            </details>
            {/* CC BY: the music pack's credits must be shown (Scott Buckley
                is not in sources_text). */}
            {credits.length > 0 && (
              <details class="src">
                <summary>Music</summary>
                <p>{credits.join("\n")}</p>
              </details>
            )}
            <p>
              <a href="../">Hexapla</a> is free and collects no data. <a href="../PRIVACY.html">Privacy</a>
            </p>
          </footer>
        )}
      </Sheet>
    );
  }

  const mini = (
    <div class="mini" role="region" aria-label="Audio player">
      <button type="button" class="ib" aria-label="Previous chapter" onClick={() => player.skip(-1)}>
        <Icon d={I.skipPrev} size={20} />
      </button>
      <button
        type="button"
        class="ib pp"
        aria-label={ps.status === "playing" ? "Pause" : "Play"}
        disabled={ps.status === "loading"}
        onClick={() => (ps.status === "error" ? player.play(ps.translation, ps.label, ps.book, ps.chapter, 0) : player.toggle())}
      >
        {ps.status === "loading" ? <span class="spin" aria-hidden="true" /> : <Icon d={ps.status === "playing" ? I.pause : I.play} size={22} />}
      </button>
      <button
        type="button"
        class="mlabel"
        onClick={() => ps.book >= 0 && !onAir && go({ translation: ps.translation, book: ps.book, chapter: ps.chapter, verse: null })}
      >
        <span class="ell mt">{ps.bookName !== "" ? ps.bookName + " " + String(ps.chapter + 1) : " "}</span>
        <span class={"ell ms" + (ps.status === "error" ? " err" : "")} role={ps.status === "error" ? "alert" : undefined}>
          {ps.status === "error" ? ps.message : ps.status === "loading" ? "Loading…" : ps.label}
        </span>
      </button>
      <button type="button" class="ib" aria-label="Next chapter" onClick={() => player.skip(1)}>
        <Icon d={I.skipNext} size={20} />
      </button>
      {docPip !== undefined && pip === null && (
        <button type="button" class="ib" aria-label="Pop out the player" title="Keep the player on top of other windows" onClick={() => void popOut()}>
          <Icon d={I.pip} size={20} />
        </button>
      )}
      <button type="button" class="ib" aria-label="Stop" onClick={() => player.stop()}>
        <Icon d={I.close} size={20} />
      </button>
    </div>
  );

  return (
    <div class={"hx" + (wide ? " wide" : "") + (side && n > 2 ? " many" : "") + (ps.status !== "idle" ? " playing" : "") + (selRow !== null ? " selecting" : "")} style={style}>
      {header}
      <div class="main">
        {wide && index !== null && (
          <nav class="side" aria-label={"Chapters of " + bookName}>
            <button type="button" class="btn bookbtn" lang={aLang} onClick={() => setSheet("book")}>
              {bookName}
            </button>
            {chapterGrid(route.book, (c) => go({ ...route, chapter: c, verse: null }))}
          </nav>
        )}
        <main class="page" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} onTouchCancel={() => (swipe.current = null)}>
          {nav}
          {body}
        </main>
      </div>
      {selRow !== null && (
        <div class="actions" role="toolbar" aria-label={"Verse " + selRef}>
          {/* Highlight colours as on Android: tap one to mark, the lit one to clear. */}
          <div class="arow amarks">
            {Array.from({ length: HL_COUNT }, (_, c) => (
              <button
                type="button"
                key={c}
                class={"hdot hd" + String(c) + (selHl === c ? " on" : "")}
                aria-label={"Highlight " + HL_NAMES[c]}
                aria-pressed={selHl === c}
                disabled={selKeys.length === 0}
                onClick={() => setSelHl(selHl === c ? null : c)}
              />
            ))}
            <span class="asp" />
            <button type="button" class="ab" aria-pressed={selBms.length > 0} disabled={selKeys.length === 0} onClick={toggleSelBm}>
              <Icon d={selBms.length > 0 ? I.bookmarked : I.bookmark} size={20} />
              <span>{selBms.length > 0 ? "Saved" : "Bookmark"}</span>
            </button>
            <button type="button" class="ab" disabled={selKeys.length === 0} onClick={() => openNote(selKeys[0], selRef)}>
              <Icon d={I.note} size={20} />
              <span>Note</span>
            </button>
          </div>
          <div class="arow">
          <span class="aref">{selRef}</span>
          {canListen && selVerse !== null && (
            <button type="button" class="ab" onClick={() => (listen(selVerse), setSelected(null))}>
              <Icon d={I.listen} size={20} />
              <span>Listen</span>
            </button>
          )}
          <button type="button" class="ab" disabled={selKeys.length === 0} onClick={() => (setXref({ keys: selKeys, label: selRef }), openFrom("xref", null))}>
            <Icon d={I.xref} size={20} />
            <span>Refs</span>
          </button>
          <button type="button" class="ab" onClick={() => void copy(selLink, "Link copied")}>
            <Icon d={I.link} size={20} />
            <span>Link</span>
          </button>
          <button type="button" class="ab" onClick={() => void copy(selText(), "Text copied")}>
            <Icon d={I.copy} size={20} />
            <span>Text</span>
          </button>
          {canShare && (
            <button type="button" class="ab" onClick={() => void navigator.share({ title: selRef, text: selText() }).catch(() => undefined)}>
              <Icon d={I.share} size={20} />
              <span>Share</span>
            </button>
          )}
          <button type="button" class="ib" aria-label="Close" onClick={() => setSelected(null)}>
            <Icon d={I.close} size={20} />
          </button>
          </div>
        </div>
      )}
      <input
        ref={fileIn}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={(e) => {
          const el = e.target as HTMLInputElement;
          const f = el.files?.[0];
          el.value = "";
          if (f !== undefined) void restoreBackup(f);
        }}
      />
      {ps.status !== "idle" && (pip === null ? mini : createPortal(mini, pip.document.body))}
      {toast !== null && (
        <div class="toast" role="status">
          {toast}
        </div>
      )}
      {sheetEl}
    </div>
  );
}

function markCount(m: Marks): string {
  const b = m.bookmarks.length;
  const h = Object.keys(m.highlights).length;
  const n = Object.keys(m.notes).length;
  if (b + h + n === 0) return "None yet. Tap a verse to mark it.";
  return String(b) + " bookmarks · " + String(h) + " highlights · " + String(n) + " notes";
}

/** Settings › Backup, as on Android: the same file, so it moves both ways. */
function backupRows(stored: boolean, onSave: () => void, onRestore: () => void): JSX.Element {
  return (
    <>
      {!stored && <p class="hint">This browser is not keeping site data, so marks last only until the page closes. Save a backup to keep them.</p>}
      <button type="button" class="srow" onClick={onSave}>
        <div class="st">
          <span>Save backup…</span>
          <span class="sn">Bookmarks, highlights and notes as hexapla-backup.json — the Android app restores it too.</span>
        </div>
      </button>
      <button type="button" class="srow" onClick={onRestore}>
        <div class="st">
          <span>Restore backup…</span>
          <span class="sn">From this app or the Android app. Adds to what is here; nothing is lost.</span>
        </div>
      </button>
    </>
  );
}

type MarkTab = "bookmarks" | "highlights" | "notes";

/** Bookmarks, highlights and notes, in Bible order, read in the current
 *  translation (BookmarksScreen.kt): a mark on a verse this translation lacks
 *  is dimmed and keeps its own reference. */
function MarksSheet(p: {
  marks: Marks;
  vm: VerseMapData | null;
  t: string;
  lang: string;
  index: BooksIndex | null;
  stored: boolean;
  onClose: () => void;
  onPick: (b: number, c: number, v: number) => void;
  onChange: (f: (m: Marks) => Marks) => void;
  onSave: () => void;
  onRestore: () => void;
}) {
  const [tab, setTab] = useState<MarkTab>(() => (p.marks.bookmarks.length > 0 ? "bookmarks" : Object.keys(p.marks.notes).length > 0 ? "notes" : "highlights"));
  const [books, setBooks] = useState<Map<number, Book>>(new Map());
  const vm = p.vm ?? {};

  interface Item {
    id: string;
    book: number;
    /** 0-based position in the current translation, or null when it has none. */
    at: { chapter: number; verse: number } | null;
    /** The stored reference, 1-based, shown when `at` is null. */
    fallback: string;
    hl?: number;
    note?: string;
    remove: (m: Marks) => Marks;
  }
  const canonItem = (k: string, extra: Partial<Item>, remove: (m: Marks) => Marks): Item | null => {
    const c = parseCanon(k);
    if (c === null) return null;
    const pos = fromKjv(vm, p.t, c[0], c[1] + 1, c[2] + 1)[0];
    return { id: k, book: c[0], at: pos === undefined ? null : { chapter: pos.c - 1, verse: pos.v - 1 }, fallback: String(c[1] + 1) + ":" + String(c[2] + 1) + " (KJV)", remove, ...extra };
  };
  const items: Item[] =
    tab === "bookmarks"
      ? sortedBookmarks(vm, p.marks).map((b) => {
          const k = bookmarkKey(b);
          return { id: k, book: b.book, at: placeIn(vm, b, p.t), fallback: String(b.chapter + 1) + ":" + String(b.verse + 1) + " (" + b.id + ")", remove: (m: Marks) => withBookmark(m, k, false) };
        })
      : tab === "highlights"
        ? sortedCanon(Object.keys(p.marks.highlights)).flatMap((k) => canonItem(k, { hl: p.marks.highlights[k] }, (m) => withHighlight(m, k, null)) ?? [])
        : sortedCanon(Object.keys(p.marks.notes)).flatMap((k) => canonItem(k, { note: p.marks.notes[k] }, (m) => withNote(m, k, "")) ?? []);

  // The verse texts: the books the marks are in, in the current translation.
  const need = [...new Set(items.map((x) => x.book))].filter((b) => !books.has(b) && b < (p.index?.length ?? 0)).join(",");
  useEffect(() => {
    if (need === "") return;
    let live = true;
    void Promise.all(need.split(",").map((b) => loadBook(p.t, Number(b)).then((x) => [Number(b), x] as const, () => null))).then((got) => {
      if (!live) return;
      setBooks((old) => {
        const m = new Map(old);
        for (const g of got) if (g !== null) m.set(g[0], g[1]);
        return m;
      });
    });
    return () => {
      live = false;
    };
  }, [need, p.t]);

  const counts: Record<MarkTab, number> = { bookmarks: p.marks.bookmarks.length, highlights: Object.keys(p.marks.highlights).length, notes: Object.keys(p.marks.notes).length };
  return (
    <Sheet title="Your marks" onClose={p.onClose}>
      <div class="modes" role="group" aria-label="Show">
        {(["bookmarks", "highlights", "notes"] as MarkTab[]).map((k) => (
          <button type="button" key={k} class={"seg" + (tab === k ? " sel" : "")} aria-pressed={tab === k} onClick={() => setTab(k)}>
            <span class="ell">{k[0].toUpperCase() + k.slice(1) + " " + String(counts[k])}</span>
          </button>
        ))}
      </div>
      {items.length === 0 && <p class="hint">{tab === "bookmarks" ? "No bookmarks yet. Tap a verse, then Bookmark." : tab === "highlights" ? "No highlights yet. Tap a verse, then a colour." : "No notes yet. Tap a verse, then Note."}</p>}
      <div class="list">
        {items.map((x) => {
          const name = p.index?.[x.book]?.name ?? "Book " + String(x.book + 1);
          const text = x.at === null ? "" : (books.get(x.book)?.chapters[x.at.chapter]?.[x.at.verse] ?? "");
          const ref = name + " " + (x.at === null ? x.fallback : String(x.at.chapter + 1) + ":" + String(x.at.verse + 1));
          const at = x.at;
          return (
            <div class={"li mrow" + (at === null ? " dim" : "")} key={x.id}>
              <button type="button" class="mgo" disabled={at === null} onClick={() => at !== null && p.onPick(x.book, at.chapter, at.verse)}>
                <span class="href" lang={p.lang}>
                  {x.hl !== undefined && <span class={"hdot mini hd" + String(x.hl)} aria-hidden="true" />}
                  {ref}
                </span>
                {x.note !== undefined && (
                  <span class="mnote" dir="auto">
                    {x.note}
                  </span>
                )}
                {text !== "" && (
                  <span class="htx" lang={p.lang} dir="auto">
                    {text}
                  </span>
                )}
                {at === null && <span class="sn">Not in this translation</span>}
              </button>
              <button type="button" class="ib" aria-label={"Remove " + ref} onClick={() => p.onChange(x.remove)}>
                <Icon d={I.close} size={18} />
              </button>
            </div>
          );
        })}
      </div>
      <h3 class="sec">Backup</h3>
      {backupRows(p.stored, p.onSave, p.onRestore)}
    </Sheet>
  );
}

let xrefData: Promise<XrefData> | null = null;
function loadXrefs(): Promise<XrefData> {
  if (xrefData === null) {
    xrefData = fetch(xrefsUrl).then((r) => {
      if (!r.ok) throw new Error("HTTP " + String(r.status));
      return r.json() as Promise<XrefData>;
    });
    // A failed fetch is not remembered: the next tap tries again.
    xrefData.catch(() => (xrefData = null));
  }
  return xrefData;
}

/** A verse's cross-references (ReaderScreen.kt XrefsDialog), read in the
 *  current translation; one it lacks is dimmed and keeps its KJV reference. */
function XrefSheet(p: {
  keys: string[];
  label: string;
  vm: VerseMapData | null;
  t: string;
  lang: string;
  index: BooksIndex | null;
  onClose: () => void;
  onPick: (b: number, c: number, v: number) => void;
}) {
  const [data, setData] = useState<XrefData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [books, setBooks] = useState<Map<number, Book>>(new Map());
  useEffect(() => {
    let live = true;
    loadXrefs().then(
      (d) => live && setData(d),
      (e) => live && setErr(String(e)),
    );
    return () => {
      live = false;
    };
  }, []);
  const n = p.index?.length ?? 0;
  // A book this translation does not have at all (an NT-only one) is absent too.
  const items = data === null ? null : xrefsFor(data, p.vm ?? {}, p.keys, p.t).map((x) => ({ ...x, at: x.book < n && (p.index?.[x.book]?.chapters.length ?? 0) > 0 ? x.at : null }));

  const need = items === null ? "" : [...new Set(items.filter((x) => x.at !== null).map((x) => x.book))].filter((b) => !books.has(b)).join(",");
  useEffect(() => {
    if (need === "") return;
    let live = true;
    void Promise.all(need.split(",").map((b) => loadBook(p.t, Number(b)).then((x) => [Number(b), x] as const, () => null))).then((got) => {
      if (!live) return;
      setBooks((old) => {
        const m = new Map(old);
        for (const g of got) if (g !== null) m.set(g[0], g[1]);
        return m;
      });
    });
    return () => {
      live = false;
    };
  }, [need, p.t]);

  return (
    <Sheet title={"Cross-references · " + p.label} onClose={p.onClose}>
      {err !== null && <p class="hint">Could not load the cross-references: {err}</p>}
      {items === null && err === null && <p class="hint">Loading…</p>}
      {items !== null && items.length === 0 && <p class="hint">No cross-references for this verse.</p>}
      {items !== null && items.length > 0 && (
        <div class="list">
          {items.map((x) => {
            const name = p.index?.[x.book]?.name ?? "Book " + String(x.book + 1);
            const at = x.at;
            const ref = name + " " + (at === null ? String(x.kjv.chapter + 1) + ":" + String(x.kjv.verse + 1) + " (KJV)" : String(at.chapter + 1) + ":" + String(at.verse + 1));
            const text = at === null ? "" : (books.get(x.book)?.chapters[at.chapter]?.[at.verse] ?? "");
            return (
              <button type="button" key={String(x.book) + ":" + String(x.kjv.chapter) + ":" + String(x.kjv.verse)} class={"li hit" + (at === null ? " dim" : "")} disabled={at === null} onClick={() => at !== null && p.onPick(x.book, at.chapter, at.verse)}>
                <span class="href" lang={p.lang} dir={directionOf(name) ?? undefined}>
                  {ref}
                </span>
                {text !== "" && (
                  <span class="htx" lang={p.lang} dir={directionOf(text) ?? undefined}>
                    {text}
                  </span>
                )}
                {at === null && <span class="sn">Not in this translation</span>}
              </button>
            );
          })}
        </div>
      )}
      <p class="hint">The most-voted references at openbible.info (CC BY).</p>
    </Sheet>
  );
}

/** Chrome/Edge desktop's Document Picture-in-Picture (116+). Not in the
 *  TypeScript DOM lib yet, and absent from Safari, Firefox and every mobile
 *  browser — there the Media Session (lock screen, notification) is the
 *  control surface once the page is left. */
interface DocPip {
  requestWindow(o: { width: number; height: number }): Promise<Window>;
  window: Window | null;
}
const docPip = (window as unknown as { documentPictureInPicture?: DocPip }).documentPictureInPicture;

/** Carry the page's styles and theme into the PiP window: it starts blank. */
function dressPip(w: Window): void {
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      const css = Array.from(sheet.cssRules).map((r) => r.cssText).join("\n");
      const el = w.document.createElement("style");
      el.textContent = css;
      w.document.head.appendChild(el);
    } catch {
      // A cross-origin sheet (the web font): link it instead.
      if (sheet.href !== null) {
        const l = w.document.createElement("link");
        l.rel = "stylesheet";
        l.href = sheet.href;
        w.document.head.appendChild(l);
      }
    }
  }
  const t = document.documentElement.getAttribute("data-theme");
  if (t !== null) w.document.documentElement.setAttribute("data-theme", t);
  w.document.body.className = "pipbody";
  w.document.title = "Hexapla";
}

function Sheet({ title, onClose, children, back }: { title: string; onClose: () => void; children: preact.ComponentChildren; back?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div class="scrim" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div class="sheet" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div class="sh">
          {back !== undefined ? (
            <button type="button" class="ib" aria-label="Back" onClick={back}>
              <Icon d={I.back} />
            </button>
          ) : (
            <span />
          )}
          <h2>{title}</h2>
          <button type="button" class="ib" aria-label="Close" onClick={onClose}>
            <Icon d={I.close} />
          </button>
        </div>
        <div class="sb">{children}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Search

let searchWorker: Worker | null = null;
let searchSeq = 0;
function worker(): Worker {
  searchWorker ??= new Worker(new URL("./search.worker.ts", import.meta.url), { type: "module" });
  return searchWorker;
}

/** Android's debounce: a scan per keystroke would redo the work per letter. */
const DEBOUNCE_MS = 300;

function SearchSheet(p: { t: string; name: string; lang: string; index: BooksIndex | null; query: string; setQuery: (q: string) => void; onClose: () => void; onPick: (h: SearchHit) => void }) {
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [load, setLoad] = useState<[number, number] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const live = useRef(0);

  // After Sheet's own effect, which focuses the dialog.
  useEffect(() => input.current?.focus(), []);

  useEffect(() => {
    const w = worker();
    const onMsg = (e: MessageEvent<SearchMsg>) => {
      const m = e.data;
      if (m.id !== live.current) return;
      if (m.kind === "progress") setLoad(m.done < m.total ? [m.done, m.total] : null);
      else if (m.kind === "hits") (setLoad(null), setHits(m.hits));
      else (setLoad(null), setErr(m.message));
    };
    w.addEventListener("message", onMsg);
    return () => w.removeEventListener("message", onMsg);
  }, []);

  useEffect(() => {
    const raw = p.query.trim();
    const id = ++searchSeq;
    live.current = id;
    setErr(null);
    // Short query: nothing to find, but start loading the translation now so
    // the first real query does not wait for the download.
    if (raw.length < SEARCH_MIN) {
      setHits(null);
      worker().postMessage({ id, t: p.t, q: "" } satisfies SearchReq);
      return;
    }
    const timer = setTimeout(() => worker().postMessage({ id, t: p.t, q: raw } satisfies SearchReq), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [p.query, p.t]);

  const name = (b: number) => p.index?.[b]?.name ?? "?";
  return (
    <Sheet title="Search" onClose={p.onClose}>
      <input
        ref={input}
        class="sq"
        type="search"
        enterkeyhint="search"
        autoComplete="off"
        spellcheck={false}
        placeholder={"Search " + p.name}
        aria-label={"Search " + p.name}
        value={p.query}
        onInput={(e) => p.setQuery(e.currentTarget.value)}
        lang={p.lang}
      />
      {load !== null && (
        <div class="sload" role="status">
          <progress max={load[1]} value={load[0]} />
          <span>
            {load[0]} / {load[1]}
          </span>
        </div>
      )}
      {err !== null && <p class="hint">Search failed: {err}</p>}
      {hits !== null && hits.length === 0 && load === null && <p class="hint">No results</p>}
      {hits !== null && hits.length >= SEARCH_CAP && <p class="hint">The first {SEARCH_CAP} verses. Add a word to narrow it.</p>}
      {hits === null && load === null && err === null && (
        <p class="hint">
          Finds a phrase in {p.name}, then verses with every word in any order. Searching all translations at once is not on the web yet (it would download about 200 MB).
        </p>
      )}
      {hits !== null && hits.length > 0 && (
        <div class="list">
          {hits.map((h) => (
            <button type="button" key={String(h.b) + ":" + String(h.c) + ":" + String(h.v)} class="li hit" onClick={() => p.onPick(h)}>
              <span class="href" lang={p.lang} dir={directionOf(name(h.b)) ?? undefined}>
                {name(h.b)} {h.c + 1}:{h.v + 1}
              </span>
              <span class="htx" lang={p.lang} dir={directionOf(h.text) ?? undefined}>
                {h.text}
              </span>
            </button>
          ))}
        </div>
      )}
    </Sheet>
  );
}

function BookSheet(p: { index: BooksIndex | null; lang: string; current: Route; grid: (b: number, onPick: (c: number) => void) => JSX.Element; onClose: () => void; onPick: (b: number, c: number) => void }) {
  const [book, setBook] = useState<number | null>(null);
  if (book !== null && p.index !== null) {
    return (
      <Sheet title={p.index[book].name} onClose={p.onClose} back={() => setBook(null)}>
        {p.grid(book, (c) => p.onPick(book, c))}
      </Sheet>
    );
  }
  return (
    <Sheet title="Books" onClose={p.onClose}>
      <div class="list books">
        {(p.index ?? []).map((b, i) => (
          <button
            type="button"
            key={i}
            class={"li" + (i === p.current.book ? " cur" : "")}
            lang={p.lang}
            dir={directionOf(b.name) ?? undefined}
            onClick={() => (b.chapters.length === 1 ? p.onPick(i, 0) : setBook(i))}
          >
            {b.name}
          </button>
        ))}
      </div>
    </Sheet>
  );
}
