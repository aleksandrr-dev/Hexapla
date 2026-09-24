// P1 — the reader: translation picker, book/chapter, parallel view, deep links,
// share (WEB_APP_PLAN.md § 3). The look is the P0.5 design canvas (gate
// passed 2026-09-24; its link is in the session handoff, not here — this tree
// may name no remote origin, not even in a comment).
//
// Search, audio, offline and UI locales are P2-P4 and deliberately absent.

import type { JSX } from "preact";
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { loadBook, loadBooksIndex, loadManifest, loadVersemap } from "./data";
import { chapterRows, type Row, type Side } from "./parallel";
import { FONT_MAX, FONT_MIN, loadPrefs, savePrefs, type Layout, type Mode, type Prefs, type Theme } from "./prefs";
import { buildHash, parseRoute, type Route } from "./route";
import { directionOf, dropCapEnd, isCjk } from "./text";
import type { Book, BooksIndex, Manifest, Translation } from "./types";
import type { Ref, VerseMapData } from "./versemap";

// John 1: where a first-time reader with no link is most likely to start.
const START: Route = { translation: "kjv", book: 42, chapter: 0, verse: null };

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
};

function Icon({ d, size = 22 }: { d: JSX.Element; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      {d}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Verse text

function VerseText({ text, lang, cap, cls }: { text: string; lang: string; cap: boolean; cls: string }) {
  const dir = directionOf(text) ?? undefined;
  const end = cap ? dropCapEnd(text) : -1;
  const c = cls + (isCjk(lang) ? " cjk" : "");
  if (end < 0) {
    return (
      <div class={c} lang={lang} dir={dir}>
        {text}
      </div>
    );
  }
  return (
    <div class={c} lang={lang} dir={dir}>
      <span class="dropcap" aria-hidden="true">
        {text.slice(0, end)}
      </span>
      <span class="sr">{text.slice(0, end)}</span>
      {text.slice(end)}
    </div>
  );
}

function SideText({ side, lang, cls, chapter, showNum }: { side: Side; lang: string; cls: string; chapter: number; showNum: boolean }) {
  if (side.kind === "gap") return null;
  return (
    <>
      {side.texts.map((t, i) => {
        const r = side.refs[i];
        const cap = r.v === 1 && i === 0;
        return (
          <div class="vpart" key={String(r.c) + ":" + String(r.v)}>
            {showNum && !cap && <span class="inum">{refLabel([r], chapter)}</span>}
            <VerseText text={t} lang={lang} cap={cap} cls={cls} />
          </div>
        );
      })}
    </>
  );
}

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
  bId: string | null;
  book: number;
  chapter: number; // 0-based
  a: Book;
  b: Book | null;
  bMissing: boolean;
  vm: VerseMapData | null;
}

// "text" is the quick Aa sheet; "prefs" is the full Settings menu, laid out
// in the Android app's own sections (owner, 2026-09-24).
type Sheet = null | "a" | "b" | "book" | "text" | "prefs";

/** `?with=<id>` in a shared link opens the reader with that second
 *  translation beside the first — what the sender was looking at. */
function initialPrefs(): Prefs {
  const p = loadPrefs();
  const w = new URLSearchParams(window.location.search).get("with");
  if (w !== null && /^[A-Za-z0-9_-]+$/.test(w)) return { ...p, second: w, mode: "both" };
  return p;
}

export function App() {
  const [prefs, setPrefs] = useState<Prefs>(initialPrefs);
  const [route, setRoute] = useState<Route>(() => initialRoute(prefs));
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [index, setIndex] = useState<BooksIndex | null>(null);
  const [chap, setChap] = useState<Chapter | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<Sheet>(null);
  // A picker opened from Settings returns to Settings, not to the page.
  const [ret, setRet] = useState<Sheet>(null);
  const openFrom = (s: Sheet, from: Sheet) => (setRet(from), setSheet(s));
  const done = () => (setSheet(ret), setRet(null));
  const [selected, setSelected] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [wide, setWide] = useState<boolean>(() => window.matchMedia("(min-width: 960px)").matches);
  const scrollTo = useRef<number | null>(route.verse);

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
    return () => {
      window.removeEventListener("hashchange", onHash);
      mq.removeEventListener("change", onMq);
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
  }, []);

  const aT = manifest?.translations.find((t) => t.id === route.translation);
  const bId = prefs.second !== null && prefs.second !== route.translation ? prefs.second : null;
  const bT = bId === null ? undefined : manifest?.translations.find((t) => t.id === bId);

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
        const bHas = bT !== undefined && route.book < bT.bookCount;
        const [a, b, vm] = await Promise.all([
          loadBook(route.translation, route.book),
          bHas ? loadBook(bT.id, route.book) : Promise.resolve(null),
          bHas ? loadVersemap() : Promise.resolve(null),
        ]);
        if (route.chapter >= a.chapters.length) throw new Error(a.name + " has " + String(a.chapters.length) + " chapters.");
        if (live) {
          setChap({ aId: route.translation, bId: bHas ? bT.id : null, book: route.book, chapter: route.chapter, a, b, bMissing: bT !== undefined && !bHas, vm });
        }
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, [manifest, route.translation, route.book, route.chapter, bT?.id]);

  const ready = chap !== null && chap.aId === route.translation && chap.book === route.book && chap.chapter === route.chapter && chap.bId === (bT !== undefined && route.book < bT.bookCount ? bT.id : null);

  const rows: Row[] = useMemo(() => {
    if (chap === null) return [];
    const vm = chap.vm ?? {};
    return chapterRows(vm, chap.book, chap.aId, chap.chapter + 1, chap.a.chapters, chap.bId, chap.b?.chapters ?? null);
  }, [chap]);

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

  const flash = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast((t) => (t === msg ? null : t)), 1800);
  };

  // ---- share ---------------------------------------------------------------
  const selRow = rows.find((r) => r.key === selected) ?? null;
  const selVerse = selRow !== null && selRow.a.kind === "text" ? selRow.a.refs[0].v - 1 : null;
  const selRoute: Route = { ...route, verse: selVerse };
  const withB = chap?.bId != null && prefs.mode !== "a" ? "?with=" + chap.bId : "";
  const selLink = window.location.origin + window.location.pathname + withB + buildHash(selRoute);
  const selRef = (() => {
    if (selRow === null) return "";
    if (selRow.a.kind === "text") return bookName + " " + String(route.chapter + 1) + ":" + refLabel(selRow.a.refs, null);
    return (chap?.b?.name ?? bookName) + " " + (selRow.b?.kind === "text" ? refLabel(selRow.b.refs, -1) : "");
  })();

  useEffect(() => {
    if (selVerse !== null) history.replaceState(null, "", buildHash(selRoute));
  }, [selected]);

  const selText = (): string => {
    if (selRow === null) return "";
    const parts: string[] = [];
    const showA = prefs.mode !== "b" || chap?.bId === null;
    const showB = chap?.bId !== null && prefs.mode !== "a";
    if (showA && selRow.a.kind === "text") parts.push(selRow.a.texts.join(" ") + "\n— " + selRef + " (" + shortLabel(aT, route.translation) + ")");
    if (showB && selRow.b?.kind === "text") {
      const bref = (chap?.b?.name ?? "") + " " + refLabel(selRow.b.refs, -1);
      parts.push(selRow.b.texts.join(" ") + "\n— " + bref + " (" + shortLabel(bT, bId ?? "") + ")");
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

  // ---- render ----------------------------------------------------------------
  const style = { "--fs": String(prefs.fontSize) + "px" } as JSX.CSSProperties;
  const both = chap?.bId != null && prefs.mode === "both";
  const side = prefs.layout === "side" || (prefs.layout === "auto" && wide);
  const onlyB = chap?.bId != null && prefs.mode === "b";
  const aName = shortLabel(aT, route.translation);
  const bName = shortLabel(bT, bId ?? "");
  const aLang = aT?.lang ?? "und";
  const bLang = bT?.lang ?? "und";
  const chapNo = route.chapter + 1;

  const header = (
    <header class="bar">
      {wide && (
        <a class="mark" href="../">
          Hexapla
        </a>
      )}
      <div class="tr">
        <button type="button" class="btn tbtn" onClick={() => setSheet("a")} aria-label={"Translation: " + aName}>
          <span class="ell">{wide ? aName : tinyLabel(aT, route.translation)}</span>
        </button>
        {bT !== undefined && (
          <button
            type="button"
            class="ib"
            aria-label="Swap translations"
            onClick={() => {
              update({ second: route.translation });
              go({ ...route, translation: bT.id, verse: null });
            }}
          >
            <Icon d={I.swap} size={20} />
          </button>
        )}
        <button type="button" class={"btn tbtn" + (bT === undefined ? " add" : "")} onClick={() => setSheet("b")} aria-label={bT === undefined ? "Add a second translation" : "Second translation: " + bName}>
          <span class="ell">{bT === undefined ? "+ Parallel" : wide ? bName : tinyLabel(bT, bId ?? "")}</span>
        </button>
      </div>
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
      </div>
    );
    const colHeads = chap.bId !== null && prefs.mode === "both" && (
      <div class={"colheads" + (side ? " w" : "")}>
        <div>{aName}</div>
        {side && <div />}
        <div>{bName}</div>
      </div>
    );
    body = (
      <>
        {heading}
        {chap.bId !== null && (
          <div class="modes" role="group" aria-label="Text shown">
            {(
              [
                ["a", tinyLabel(aT, route.translation)],
                ["both", "Both"],
                ["b", tinyLabel(bT, bId ?? "")],
              ] as [Mode, string][]
            ).map(([m, l]) => (
              <button type="button" key={m} class={"seg" + (prefs.mode === m ? " sel" : "")} aria-pressed={prefs.mode === m} onClick={() => update({ mode: m })}>
                <span class="ell">{l}</span>
              </button>
            ))}
          </div>
        )}
        {chap.bMissing && <p class="note">{bName} does not contain {chap.a.name}; showing {aName} alone.</p>}
        {colHeads}
        <div class={"verses" + (both && side ? " cols" : "")}>
          {rows.map((r) => {
            const sel = r.key === selected;
            const aNum = r.a.kind === "text" ? refLabel(r.a.refs, chapNo) : "";
            const aCap = r.a.kind === "text" && r.a.refs[0].v === 1;
            const bDiffers = r.b !== null && r.b.kind === "text" && (r.a.kind !== "text" || !sameRefs(r.a.refs, r.b.refs));
            if (onlyB && (r.b === null || r.b.kind === "gap")) return null;
            const pick = () => setSelected(sel ? null : r.key);
            const onKey = (e: KeyboardEvent) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                pick();
              }
            };
            // The number gutter sits on the verse's own reading side.
            const lead = onlyB ? r.b : r.a.kind === "text" ? r.a : r.b;
            const rowDir = lead !== null && lead.kind === "text" ? (directionOf(lead.texts[0]) ?? undefined) : undefined;
            const common = { dir: rowDir, id: "r-" + r.key, class: "row" + (sel ? " sel" : ""), onClick: pick, onKeyDown: onKey, tabIndex: 0, "aria-pressed": sel };
            if (onlyB && r.b !== null && r.b.kind === "text") {
              const bCap = r.b.refs[0].v === 1;
              return (
                <div {...common} class={common.class + " single"}>
                  <div class="num">{bCap ? "" : refLabel(r.b.refs, chapNo)}</div>
                  <div class="txt">
                    <SideText side={r.b} lang={bLang} cls="vt" chapter={chapNo} showNum={r.b.refs.length > 1} />
                  </div>
                </div>
              );
            }
            if (!both) {
              return (
                <div {...common} class={common.class + " single"}>
                  <div class="num">{aCap ? "" : aNum}</div>
                  <div class="txt">
                    <SideText side={r.a} lang={aLang} cls="vt" chapter={chapNo} showNum={r.a.kind === "text" && r.a.refs.length > 1} />
                  </div>
                </div>
              );
            }
            const aCell = r.a.kind === "gap" ? <Gap name={aName} other={bName} /> : <SideText side={r.a} lang={aLang} cls="vt" chapter={chapNo} showNum={r.a.refs.length > 1} />;
            const bCell = r.b === null ? null : r.b.kind === "gap" ? <Gap name={bName} other={null} /> : <SideText side={r.b} lang={bLang} cls={side ? "vt" : "vt b"} chapter={chapNo} showNum={bDiffers} />;
            if (side) {
              return (
                <div {...common} class={common.class + " triple"}>
                  <div class="cell">{aCell}</div>
                  <div class="num mid">{aCap ? "" : aNum}</div>
                  <div class="cell">{bCell}</div>
                </div>
              );
            }
            return (
              <div {...common} class={common.class + " single"}>
                <div class="num">{aCap ? "" : aNum}</div>
                <div class="txt stack">
                  {aCell}
                  {bCell}
                </div>
              </div>
            );
          })}
        </div>
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
  let sheetEl: JSX.Element | null = null;
  if (sheet === "a" || sheet === "b") {
    const forB = sheet === "b";
    const list = manifest?.translations ?? [];
    sheetEl = (
      <Sheet title={forB ? "Read alongside" : "Translation"} onClose={done} back={ret !== null ? done : undefined}>
        <div class="list">
          {forB && (
            <button type="button" class={"li" + (bT === undefined ? " cur" : "")} onClick={() => (update({ second: null }), done())}>
              One translation only
            </button>
          )}
          {list
            .filter((t) => !forB || t.id !== route.translation)
            .map((t) => {
              const cur = forB ? t.id === bT?.id : t.id === route.translation;
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
                    if (forB) update({ second: t.id, mode: prefs.mode === "a" ? "both" : prefs.mode });
                    else {
                      if (t.id === bId) update({ second: route.translation });
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
  } else if (sheet === "book") {
    sheetEl = <BookSheet index={index} lang={aLang} current={route} grid={chapterGrid} onClose={() => setSheet(null)} onPick={(b, c) => (setSheet(null), go({ ...route, book: b, chapter: c, verse: null }))} />;
  } else if (sheet === "text") {
    sheetEl = (
      <Sheet title="Text" onClose={done}>
        {textControls}
      </Sheet>
    );
  } else if (sheet === "prefs") {
    const split = bT !== undefined;
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
        <button
          type="button"
          class="srow"
          role="switch"
          aria-checked={split}
          onClick={() => (split ? update({ second: null }) : openFrom("b", "prefs"))}
        >
          <div class="st">
            <span>Split view</span>
            <span class="sn">Two translations, verse by verse</span>
          </div>
          <span class={"sw" + (split ? " on" : "")} aria-hidden="true" />
        </button>
        {split && (
          <>
            <button type="button" class="srow" onClick={() => openFrom("b", "prefs")}>
              <div class="st">
                <span>Second translation</span>
                <span class="sn" lang={bLang}>{bName}</span>
              </div>
              <Icon d={I.chev} size={18} />
            </button>
            <div class="sfield">
              <span>Show</span>
              {seg<Mode>("Text shown", prefs.mode, [["a", tinyLabel(aT, route.translation)], ["both", "Both"], ["b", tinyLabel(bT, bId ?? "")]], (m) => update({ mode: m }))}
            </div>
            <div class="sfield">
              <span>Split layout</span>
              {seg<Layout>("Split layout", prefs.layout, [["auto", "Auto"], ["side", "Side by side"], ["stacked", "Stacked"]], (l) => update({ layout: l }))}
            </div>
          </>
        )}
        <h3 class="sec">Appearance</h3>
        {textControls}
        <h3 class="sec">Study</h3>
        {soon("Strong's numbers (KJV)", "Tap a number for the Hebrew or Greek word and its definition.")}
        {soon("Webster's 1828 Dictionary", "Tap an English word for what it meant in the era of the classic Bibles.")}
        <h3 class="sec">Listening</h3>
        {soon("Narrated audio", "Chapters read aloud, following the verse and the word.")}
        {soon("Background while listening", "Music or a fireside underneath the narration.")}
        {/* The sources_text credit is a licence obligation: verbatim, at the
            foot of Settings as on Android, never on every chapter (owner,
            2026-09-24: a footnote here, not in the Aa sheet). */}
        {manifest !== null && (
          <footer class="foot">
            <h3>Text sources</h3>
            <p>{manifest.credits}</p>
            <p>
              <a href="../">Hexapla</a> is free and collects no data. <a href="../PRIVACY.html">Privacy</a>
            </p>
          </footer>
        )}
      </Sheet>
    );
  }

  return (
    <div class={"hx" + (wide ? " wide" : "")} style={style}>
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
        <main class="page">
          {nav}
          {body}
        </main>
      </div>
      {selRow !== null && (
        <div class="actions" role="toolbar" aria-label={"Verse " + selRef}>
          <span class="aref">{selRef}</span>
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
      )}
      {toast !== null && (
        <div class="toast" role="status">
          {toast}
        </div>
      )}
      {sheetEl}
    </div>
  );
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
