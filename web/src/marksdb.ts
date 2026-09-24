// IndexedDB for marks.ts — this browser only, nothing leaves the device
// (web/README.md house rule 4). One record per mark, not one blob per kind:
// two open tabs each writing a whole blob would lose each other's marks.
//
// Storage can be missing or refuse (private windows, blocked site data, a
// full disk). Loading then yields null — «not available», which the reader
// must not show as «you have no marks» — and a failed write rejects, so the
// caller can say the mark was not kept.

import { openDB, type IDBPDatabase } from "idb";
import type { Marks } from "./marks";

const DB = "hexapla";
const KINDS = ["notes", "highlights", "bookmarks"] as const;
type Kind = (typeof KINDS)[number];

let db: Promise<IDBPDatabase> | null = null;

function open(): Promise<IDBPDatabase> {
  if (db === null) {
    db = openDB(DB, 1, {
      upgrade(d) {
        for (const k of KINDS) if (!d.objectStoreNames.contains(k)) d.createObjectStore(k);
      },
    });
    // A failed open is retried next time rather than cached forever.
    db.catch(() => (db = null));
  }
  return db;
}

// Other tabs of the app hear about a change and reload.
const channel = typeof BroadcastChannel === "function" ? new BroadcastChannel("hexapla-marks") : null;

export function onOtherTab(f: () => void): () => void {
  if (channel === null) return () => undefined;
  const h = () => f();
  channel.addEventListener("message", h);
  return () => channel.removeEventListener("message", h);
}

/** Every mark, or null when this browser will not give us storage. */
export async function loadMarks(): Promise<Marks | null> {
  try {
    const d = await open();
    const tx = d.transaction([...KINDS], "readonly");
    const read = async (k: Kind) => {
      const s = tx.objectStore(k);
      const [keys, vals] = await Promise.all([s.getAllKeys(), s.getAll()]);
      return keys.map((key, i) => [String(key), vals[i]] as const);
    };
    const [n, h, b] = await Promise.all([read("notes"), read("highlights"), read("bookmarks")]);
    await tx.done;
    const out: Marks = { notes: {}, highlights: {}, bookmarks: [] };
    for (const [k, v] of n) if (typeof v === "string") out.notes[k] = v;
    for (const [k, v] of h) if (typeof v === "number") out.highlights[k] = v;
    // Oldest first: the value is when it was made.
    out.bookmarks = b
      .slice()
      .sort((x, y) => (x[1] as number) - (y[1] as number))
      .map(([k]) => k);
    return out;
  } catch {
    return null;
  }
}

/** Write the difference between `before` and `after`, in one transaction. */
export async function saveMarks(before: Marks, after: Marks): Promise<void> {
  const d = await open();
  const tx = d.transaction([...KINDS], "readwrite");
  const ops: Promise<unknown>[] = [];
  const diff = <T>(kind: Kind, a: Record<string, T>, b: Record<string, T>) => {
    const s = tx.objectStore(kind);
    for (const k of Object.keys(a)) if (!(k in b)) ops.push(s.delete(k));
    for (const [k, v] of Object.entries(b)) if (a[k] !== v) ops.push(s.put(v, k));
  };
  diff("notes", before.notes, after.notes);
  diff("highlights", before.highlights, after.highlights);
  const bs = tx.objectStore("bookmarks");
  const now = Date.now();
  after.bookmarks.forEach((k, i) => {
    if (!before.bookmarks.includes(k)) ops.push(bs.put(now + i, k));
  });
  for (const k of before.bookmarks) if (!after.bookmarks.includes(k)) ops.push(bs.delete(k));
  await Promise.all([...ops, tx.done]);
  channel?.postMessage("changed");
  // Ask once that the browser not evict the reader's own words under storage
  // pressure. A refusal changes nothing; iOS may still evict after 7 days.
  void navigator.storage?.persist?.().catch(() => undefined);
}
