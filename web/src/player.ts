// P3 — narration and the bed beneath it, in the browser. The DOM half of
// audio.ts: one <audio> for the narration, two for the bed (so it can
// crossfade), and the Media Session so a phone's lock screen and Control
// Centre show the chapter and its controls (WEB_APP_PLAN.md § 2, iPhone).
//
// Same rules as ReadingService.kt, which this follows point for point:
//  - generated narration wins over LibriVox; verse following from `o`, words
//    from `.w.json` (absent sidecar = verse-level only, never an error);
//  - the bed swaps only when the MOOD changes; fireside is ONE continuous bed
//    that only the silence boundary stops;
//  - ⚠ ONLY the `silence` mood may produce no bed. A track that fails to load
//    falls back — pack -> bundled; fireside -> bundled loop -> music — because
//    a listener cannot tell an unintended silence from a bug.
//
// What the web cannot do that Android does: there is no text-to-speech
// fallback (Web Speech is a v2 candidate), so a chapter with no recording
// says so instead of reading it aloud.

import { bundledFor, moodFor, packUrl, parseWords, pick, sectionFor, sectionsFor, SILENCE, startMs, verseAt, wordAt, wordsUrl, type Bed, type MoodMapData, type MusicIndex, type Section, type Words } from "./audio";
import { loadBooksIndex, loadGenIndex, loadLibriVoxIndex, loadVersemap } from "./data";
import type { Prefs } from "./prefs";
import type { BooksIndex } from "./types";
import type { VerseMapData } from "./versemap";

// The app's own bundled beds, straight from its assets (as the font is), so
// the two can never differ and the bed works when archive.org does not.
import airPrelude from "../../app/src/main/assets/music/air_prelude.mp3?url";
import canonInD from "../../app/src/main/assets/music/canon_in_d.mp3?url";
import healing from "../../app/src/main/assets/music/healing.mp3?url";
import meditation from "../../app/src/main/assets/music/meditation01.mp3?url";
import fireLoop from "../../app/src/main/assets/ambience/fire_loop.ogg?url";
import moodMapUrl from "../../app/src/main/assets/mood_map.json?url";
import musicIndexUrl from "../../app/src/main/assets/music_index.json?url";

const BUNDLED = [airPrelude, canonInD, healing, meditation];

/** The Listening prefs (stored and migrated in prefs.ts). */
export type AudioPrefs = Pick<Prefs, "rate" | "autoNext" | "bed" | "bedKind" | "bedVolume" | "uniformBed">;

export interface PlayState {
  status: "idle" | "loading" | "playing" | "paused" | "error";
  translation: string;
  book: number;
  chapter: number;
  bookName: string;
  label: string;
  /** Sounding verse, 0-based; -1 when not known (LibriVox has no offsets). */
  verse: number;
  /** Character range of the sounding word in that verse's displayed text. */
  word: [number, number] | null;
  /** The recording carries verse offsets, so the reader can follow it. */
  following: boolean;
  message: string | null;
}

const IDLE: PlayState = { status: "idle", translation: "", book: -1, chapter: -1, bookName: "", label: "", verse: -1, word: null, following: false, message: null };

// 0.1 s of silence, 8 kHz 8-bit mono WAV. Played inside the tap that starts
// playback: iOS lets a script start an <audio> later (after the index fetch,
// or at the next chapter) only if a user gesture has played it once.
const SILENT = (() => {
  const n = 800;
  const b = new Uint8Array(44 + n);
  const dv = new DataView(b.buffer);
  const s = (o: number, t: string) => [...t].forEach((c, i) => b[o + i] = c.charCodeAt(0));
  s(0, "RIFF"); dv.setUint32(4, 36 + n, true); s(8, "WAVEfmt "); dv.setUint32(16, 16, true);
  dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, 8000, true); dv.setUint32(28, 8000, true);
  dv.setUint16(32, 1, true); dv.setUint16(34, 8, true); s(36, "data"); dv.setUint32(40, n, true);
  b.fill(128, 44);
  let bin = "";
  b.forEach((x) => (bin += String.fromCharCode(x)));
  return "data:audio/wav;base64," + btoa(bin);
})();

function canPlay(type: string): boolean {
  try {
    return new Audio().canPlayType(type) !== "";
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// The bed

/** Two elements that swap roles, so a mood change crossfades. Volume goes
 *  through a GainNode where the element's own volume is read-only (iOS
 *  Safari ignores `audio.volume`, which would put the bed at full loudness
 *  over the reading). */
class BedPlayer {
  private els: HTMLAudioElement[] = [new Audio(), new Audio()];
  private gains: (GainNode | null)[] = [null, null];
  private ctx: AudioContext | null = null;
  private cur = 0;
  private fade: number | null = null;
  private vol = 0.2;
  /** What is sounding: a URL, or null. */
  url: string | null = null;
  /** `fire` while the fireside bed is on (it ignores mood changes). */
  fire = false;
  mood: string | null = null;
  private readonly volumeWorks: boolean;

  constructor() {
    const probe = new Audio();
    probe.volume = 0.5;
    this.volumeWorks = probe.volume === 0.5;
    for (const el of this.els) el.preload = "auto";
  }

  /** Inside a user gesture: unlock both elements (and the gain graph). */
  unlock(): void {
    if (!this.volumeWorks && this.ctx === null) {
      try {
        const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (Ctx !== undefined) {
          this.ctx = new Ctx();
          this.gains = this.els.map((el) => {
            // A cross-origin source routed into Web Audio must be fetched
            // with CORS or it plays silence; archive.org sends ACAO *.
            el.crossOrigin = "anonymous";
            const g = (this.ctx as AudioContext).createGain();
            g.gain.value = 0;
            (this.ctx as AudioContext).createMediaElementSource(el).connect(g).connect((this.ctx as AudioContext).destination);
            return g;
          });
        }
      } catch {
        this.ctx = null;
      }
    }
    void this.ctx?.resume();
    for (const el of this.els) {
      if (el.src === "" || el.src === SILENT) {
        el.src = SILENT;
        el.play().catch(() => undefined);
      }
    }
  }

  private setVol(i: number, v: number): void {
    const g = this.gains[i];
    if (g !== null) g.gain.value = v;
    else this.els[i].volume = Math.min(1, Math.max(0, v));
  }

  setVolume(slider: number): void {
    const s = Math.min(1, Math.max(0, slider));
    this.vol = s * s;
    if (this.fade === null) this.setVol(this.cur, this.vol);
  }

  /** Fade the current bed out and `url` in (null = fade to nothing). */
  to(url: string | null, opts: { loop: boolean; onError?: () => void; onEnded?: () => void }, playing: boolean, ms = 2500): void {
    if (this.fade !== null) window.clearInterval(this.fade);
    const out = this.cur;
    const inn = 1 - out;
    const eo = this.els[out];
    const ei = this.els[inn];
    this.url = url;
    ei.onerror = null;
    ei.onended = null;
    if (url !== null) {
      ei.loop = opts.loop;
      ei.src = url;
      this.setVol(inn, 0);
      ei.onerror = () => {
        if (this.url === url) opts.onError?.();
      };
      ei.onended = () => opts.onEnded?.();
      if (playing) ei.play().catch(() => undefined);
    }
    this.cur = inn;
    const from = eo.src !== "" && eo.src !== SILENT && !eo.paused ? this.vol : 0;
    let step = 0;
    const steps = 25;
    this.fade = window.setInterval(() => {
      step += 1;
      const t = step / steps;
      this.setVol(out, from * (1 - t));
      if (url !== null) this.setVol(inn, this.vol * t);
      if (step >= steps) {
        if (this.fade !== null) window.clearInterval(this.fade);
        this.fade = null;
        eo.pause();
        eo.onerror = null;
        eo.onended = null;
      }
    }, ms / steps);
  }

  pause(): void {
    for (const el of this.els) el.pause();
  }

  resume(): void {
    void this.ctx?.resume();
    if (this.url !== null) this.els[this.cur].play().catch(() => undefined);
  }

  stop(): void {
    if (this.fade !== null) window.clearInterval(this.fade);
    this.fade = null;
    for (const el of this.els) {
      el.onerror = null;
      el.onended = null;
      el.pause();
    }
    this.url = null;
    this.fire = false;
    this.mood = null;
  }
}

// ---------------------------------------------------------------------------
// The player

export class Player {
  private el = new Audio();
  private bed = new BedPlayer();
  private st: PlayState = IDLE;
  private subs = new Set<(s: PlayState) => void>();
  private prefs: AudioPrefs;
  private sec: Section | null = null;
  private words: Words | null = null;
  private wordsCache = new Map<string, Promise<Words | null>>();
  private timer: number | null = null;
  private token = 0;
  private books: BooksIndex | null = null;
  private sections = new Map<string, Promise<Map<number, Section[]>>>();
  private moods: MoodMapData | null = null;
  private music: MusicIndex | null = null;
  private vm: VerseMapData | null = null;
  private rotation = 0;
  readonly opus = canPlay('audio/ogg; codecs="opus"');
  readonly vorbis = canPlay('audio/ogg; codecs="vorbis"');

  constructor(prefs: AudioPrefs) {
    this.prefs = prefs;
    this.el.preload = "auto";
    this.el.addEventListener("ended", () => void this.onEnded());
    this.el.addEventListener("error", () => {
      if (this.el.src === "" || this.el.src === SILENT || this.sec === null) return;
      this.stopTimer();
      this.bed.pause();
      this.set({ status: "error", message: "The recording could not be loaded. Check the connection and try again." });
    });
    this.el.addEventListener("pause", () => {
      if (this.st.status === "playing" && !this.el.ended) {
        // Paused from outside the app (headphones, lock screen, a call).
        this.bed.pause();
        this.stopTimer();
        this.set({ status: "paused" });
      }
    });
    this.el.addEventListener("play", () => {
      if (this.st.status === "paused") {
        this.bed.resume();
        this.startTimer();
        this.set({ status: "playing" });
      }
    });
    this.el.addEventListener("timeupdate", () => this.position());
    this.session();
  }

  get state(): PlayState {
    return this.st;
  }

  subscribe(fn: (s: PlayState) => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private set(p: Partial<PlayState>): void {
    this.st = { ...this.st, ...p };
    for (const fn of this.subs) fn(this.st);
    if ("mediaSession" in navigator) {
      navigator.mediaSession.playbackState = this.st.status === "playing" ? "playing" : this.st.status === "paused" ? "paused" : "none";
    }
  }

  setPrefs(p: AudioPrefs): void {
    const old = this.prefs;
    this.prefs = p;
    this.el.playbackRate = p.rate;
    this.bed.setVolume(p.bedVolume);
    const live = this.st.status === "playing" || this.st.status === "paused";
    if (!live) return;
    if (!p.bed) this.bed.stop();
    else if (!old.bed || p.bedKind !== old.bedKind || p.uniformBed !== old.uniformBed) {
      this.bed.stop();
      void this.updateBed(true);
    }
  }

  /** Does `translation` have any recording at all? Loads the indexes. */
  async hasAudio(translation: string, book: number, chapter: number): Promise<boolean> {
    const s = await this.sectionsOf(translation);
    return sectionFor(s.get(book), chapter) !== null;
  }

  private sectionsOf(translation: string): Promise<Map<number, Section[]>> {
    let p = this.sections.get(translation);
    if (p === undefined) {
      p = Promise.all([translation === "kjv" ? loadLibriVoxIndex() : Promise.resolve({}), loadGenIndex()]).then(([lv, gen]) => sectionsFor(translation, lv, gen));
      p.catch(() => this.sections.delete(translation));
      this.sections.set(translation, p);
    }
    return p;
  }

  /** Start a chapter. Call it from the tap itself: the first thing it does
   *  is unlock the elements, which iOS allows only inside a gesture. */
  play(translation: string, label: string, book: number, chapter: number, verse: number): void {
    this.unlock();
    void this.start(translation, label, book, chapter, verse);
  }

  /** From the tap that turns the bed on: iOS needs the gesture. */
  unlockBed(): void {
    this.bed.unlock();
  }

  private unlock(): void {
    if (this.el.src === "") {
      this.el.src = SILENT;
      this.el.play().catch(() => undefined);
    }
    if (this.prefs.bed) this.bed.unlock();
  }

  private async start(translation: string, label: string, book: number, chapter: number, verse: number): Promise<void> {
    const token = ++this.token;
    this.stopTimer();
    this.sec = null;
    this.words = null;
    this.set({ status: "loading", translation, label, book, chapter, verse: -1, word: null, following: false, message: null, bookName: this.st.translation === translation ? this.st.bookName : "" });
    try {
      const [sections, books] = await Promise.all([this.sectionsOf(translation), loadBooksIndex(translation)]);
      if (token !== this.token) return;
      this.books = books;
      const bookName = books[book]?.name ?? "";
      this.set({ bookName });
      const sec = sectionFor(sections.get(book), chapter);
      if (sec === null) {
        this.el.pause();
        this.bed.stop();
        this.set({ status: "error", message: "There is no recording of " + bookName + " " + String(chapter + 1) + " in this translation yet." });
        return;
      }
      if (sec.generated && !this.opus) {
        this.el.pause();
        this.bed.stop();
        this.set({ status: "error", message: "This browser cannot play these recordings (Ogg Opus audio). Try a current Chrome, Firefox or Safari." });
        return;
      }
      this.sec = sec;
      this.set({ following: sec.offsets !== null });
      this.metadata();
      if (sec.generated) {
        const u = wordsUrl(sec.url);
        let w = this.wordsCache.get(u);
        if (w === undefined) {
          w = fetch(u).then((r) => (r.ok ? r.json() : null)).then(parseWords, () => null);
          this.wordsCache.set(u, w);
        }
        void w.then((x) => {
          if (token === this.token) this.words = x;
        });
      }
      const counts = books[book]?.chapters ?? [];
      this.el.src = sec.url;
      this.el.playbackRate = this.prefs.rate;
      await new Promise<void>((res, rej) => {
        const ok = () => (this.el.removeEventListener("error", bad), res());
        const bad = () => (this.el.removeEventListener("loadedmetadata", ok), rej(new Error("load")));
        this.el.addEventListener("loadedmetadata", ok, { once: true });
        this.el.addEventListener("error", bad, { once: true });
      });
      if (token !== this.token) return;
      const at = startMs(sec, chapter, verse, this.el.duration * 1000, counts);
      if (at > 0) this.el.currentTime = at / 1000;
      this.el.playbackRate = this.prefs.rate;
      await this.el.play();
      if (token !== this.token) return;
      this.set({ status: "playing" });
      this.startTimer();
      void this.updateBed(true);
    } catch (e) {
      if (token !== this.token) return;
      const blocked = e instanceof DOMException && e.name === "NotAllowedError";
      this.bed.stop();
      this.set({ status: blocked ? "paused" : "error", message: blocked ? null : "The recording could not be loaded. Check the connection and try again." });
    }
  }

  toggle(): void {
    if (this.st.status === "playing") this.pause();
    else if (this.st.status === "paused") this.resume();
  }

  pause(): void {
    if (this.st.status !== "playing") return;
    this.set({ status: "paused" });
    this.el.pause();
    this.bed.pause();
    this.stopTimer();
  }

  resume(): void {
    if (this.st.status !== "paused") return;
    this.unlock();
    this.el.playbackRate = this.prefs.rate;
    this.el.play().then(
      () => {
        this.set({ status: "playing" });
        this.bed.resume();
        if (this.prefs.bed && this.bed.url === null) void this.updateBed(true);
        this.startTimer();
      },
      () => undefined,
    );
  }

  stop(): void {
    this.token += 1;
    this.el.pause();
    this.bed.stop();
    this.stopTimer();
    this.sec = null;
    this.set({ ...IDLE });
    if ("mediaSession" in navigator) navigator.mediaSession.metadata = null;
  }

  /** The chapter `delta` away from the playing one, across books. */
  private neighbour(delta: number, fromLast = false): { book: number; chapter: number } | null {
    const books = this.books;
    if (books === null) return null;
    let b = this.st.book;
    // A LibriVox section spans chapters: «next» is the chapter after it.
    let c = (fromLast && this.sec !== null ? this.sec.last - 1 : this.st.chapter) + delta;
    while (b >= 0 && b < books.length && (c < 0 || c >= books[b].chapters.length)) {
      if (c < 0) {
        b -= 1;
        if (b >= 0) c = books[b].chapters.length - 1;
      } else {
        b += 1;
        c = 0;
      }
    }
    return b >= 0 && b < books.length ? { book: b, chapter: c } : null;
  }

  skip(delta: number): void {
    const n = this.neighbour(delta, delta > 0);
    if (n === null) return;
    this.unlock();
    void this.start(this.st.translation, this.st.label, n.book, n.chapter, 0);
  }

  private async onEnded(): Promise<void> {
    if (this.sec === null || this.st.status !== "playing") return;
    const n = this.prefs.autoNext ? this.neighbour(1, true) : null;
    if (n === null) {
      this.stop();
      return;
    }
    await this.start(this.st.translation, this.st.label, n.book, n.chapter, 0);
  }

  private stopTimer(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
  }

  // A word lasts ~300 ms: poll at 60 ms while there are words to follow, as
  // the Android service does, and at 250 ms for verses alone.
  private startTimer(): void {
    this.stopTimer();
    if (this.sec?.offsets == null) return;
    this.timer = window.setInterval(() => this.follow(), 60);
  }

  private follow(): void {
    const offs = this.sec?.offsets;
    if (offs == null || this.st.status !== "playing") return;
    const pos = this.el.currentTime * 1000;
    const v = verseAt(offs, pos);
    const w = wordAt(this.words?.[v], pos);
    const old = this.st.word;
    const same = old === w || (old !== null && w !== null && old[0] === w[0] && old[1] === w[1]);
    if (v !== this.st.verse) {
      this.set({ verse: v, word: w });
      void this.updateBed(false);
    } else if (!same) this.set({ word: w });
  }

  private position(): void {
    if (!("mediaSession" in navigator) || !Number.isFinite(this.el.duration)) return;
    try {
      navigator.mediaSession.setPositionState({ duration: this.el.duration, playbackRate: this.el.playbackRate, position: Math.min(this.el.currentTime, this.el.duration) });
    } catch {
      // Older Safari: no position state. The controls still work.
    }
  }

  // ---- the bed ------------------------------------------------------------

  private async loadBedData(): Promise<void> {
    if (this.moods === null) {
      try {
        this.moods = (await (await fetch(moodMapUrl)).json()) as MoodMapData;
      } catch {
        // No map: the uniform bed, the pre-1.6.3 behaviour (MoodMap.load).
      }
    }
    if (this.music === null) {
      try {
        this.music = (await (await fetch(musicIndexUrl)).json()) as MusicIndex;
      } catch {
        // Bundled tracks carry on regardless.
      }
    }
    if (this.vm === null && this.st.translation !== "kjv") {
      try {
        this.vm = await loadVersemap();
      } catch {
        // Identity pivot: right for most translations, and never silence.
      }
    }
  }

  /** Credits for the music pack: CC BY, so they must be shown. */
  async musicCredits(): Promise<string[]> {
    await this.loadBedData();
    return this.music?.credits ?? [];
  }

  private bedNow(): Bed | null {
    if (this.prefs.uniformBed || this.moods === null) return null;
    return moodFor(this.moods, this.vm, this.st.translation, this.st.book, this.st.chapter, this.st.verse);
  }

  /** Re-resolve the bed for what is sounding now. `fresh` = a new chapter or
   *  a settings change; otherwise only a mood change moves it. */
  private async updateBed(fresh: boolean): Promise<void> {
    if (!this.prefs.bed) {
      if (this.bed.url !== null) this.bed.stop();
      return;
    }
    await this.loadBedData();
    const playing = this.st.status === "playing";
    const bed = this.bedNow();

    if (this.prefs.bedKind === "fireside") {
      // ONE continuous bed: only the silence boundary matters.
      if (bed?.mood === SILENCE) {
        if (this.bed.url !== null) this.bed.to(null, { loop: true }, playing);
        this.bed.fire = false;
      } else if (!this.bed.fire || this.bed.url === null) {
        this.fireside(bed, playing);
      }
      this.bed.mood = bed?.mood ?? null;
      return;
    }

    if (bed === null) {
      // «Same music throughout»: the bundled rotation, track to track.
      if (fresh && this.bed.url === null) this.rotate(playing);
      return;
    }
    // Only a MOOD change moves the bed, a new chapter included: a bed that
    // changes constantly is worse than one that is slightly generic.
    if (bed.mood === this.bed.mood && this.bed.url !== null) return;
    this.bed.mood = bed.mood;
    this.bed.fire = false;
    if (bed.mood === SILENCE) {
      this.bed.to(null, { loop: true }, playing);
      return;
    }
    const stand = bundledFor(BUNDLED, bed.mood);
    const url = packUrl(this.music, bed, this.st.book, this.st.chapter) ?? stand;
    this.bed.to(url, { loop: true, onError: () => stand !== null && url !== stand && this.bed.to(stand, { loop: true }, this.st.status === "playing", 0) }, playing);
  }

  /** Fireside, best source first; the chain never ends in silence. */
  private fireside(bed: Bed | null, playing: boolean): void {
    const music = () => {
      this.bed.fire = false;
      this.bed.to(bundledFor(BUNDLED, bed?.mood ?? "narrative"), { loop: true }, this.st.status === "playing", 0);
    };
    const loop = () => {
      if (this.vorbis) this.bed.to(fireLoop, { loop: true, onError: music }, this.st.status === "playing", 0);
      else music();
    };
    this.bed.fire = true;
    const long = this.music?.ambience;
    if (long !== undefined) this.bed.to(this.music?.base + "/" + long.f, { loop: true, onError: loop }, playing);
    else if (this.vorbis) this.bed.to(fireLoop, { loop: true, onError: music }, playing);
    else music();
  }

  private rotate(playing: boolean): void {
    const url = pick(BUNDLED, this.rotation);
    this.bed.to(url, { loop: false, onEnded: () => (this.rotation += 1, this.rotate(this.st.status === "playing")) }, playing);
  }

  // ---- Media Session: the lock screen and Control Centre ---------------------

  private metadata(): void {
    if (!("mediaSession" in navigator) || typeof MediaMetadata === "undefined") return;
    const icon = new URL("../icon.png", window.location.href).href;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: this.st.bookName + " " + String(this.st.chapter + 1),
      artist: this.st.label,
      album: "Hexapla",
      artwork: [{ src: icon, sizes: "512x512", type: "image/png" }],
    });
  }

  private session(): void {
    if (!("mediaSession" in navigator)) return;
    const ms = navigator.mediaSession;
    const on = (a: MediaSessionAction, h: MediaSessionActionHandler) => {
      try {
        ms.setActionHandler(a, h);
      } catch {
        // An action this browser does not know.
      }
    };
    on("play", () => this.resume());
    on("pause", () => this.pause());
    on("stop", () => this.stop());
    on("previoustrack", () => this.skip(-1));
    on("nexttrack", () => this.skip(1));
    on("seekbackward", (d) => (this.el.currentTime = Math.max(0, this.el.currentTime - (d.seekOffset ?? 10))));
    on("seekforward", (d) => (this.el.currentTime = Math.min(this.el.duration || 0, this.el.currentTime + (d.seekOffset ?? 10))));
    on("seekto", (d) => {
      if (d.seekTime !== undefined) this.el.currentTime = d.seekTime;
    });
  }
}
