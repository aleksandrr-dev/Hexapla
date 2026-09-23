// Deliberately minimal. This renders the route's name and nothing more: the
// reader UI, the parallel view and every styling decision are P1/P0.5 and wait
// on the design gate (WEB_APP_PLAN.md § 3, P0.5). A scaffold that quietly ships
// a design pre-empts that gate, so this file stays this small on purpose.

import { useEffect, useState } from "preact/hooks";
import { loadBooksIndex, loadManifest } from "./data";
import { parseRoute, type Route } from "./route";
import type { Translation } from "./types";

interface Loaded {
  route: Route;
  translation: Translation | null;
  bookName: string | null;
  error: string | null;
}

function currentRoute(): Route | null {
  return parseRoute(window.location.hash);
}

export function App() {
  const [route, setRoute] = useState<Route | null>(currentRoute);
  const [state, setState] = useState<Loaded | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (route === null) {
      setState(null);
      return;
    }
    let live = true;
    void (async () => {
      try {
        const manifest = await loadManifest();
        const translation = manifest.translations.find((t) => t.id === route.translation) ?? null;
        let bookName: string | null = null;
        if (translation !== null) {
          const index = await loadBooksIndex(route.translation);
          bookName = index[route.book]?.name ?? null;
        }
        if (live) setState({ route, translation, bookName, error: null });
      } catch (e) {
        if (live) {
          setState({ route, translation: null, bookName: null, error: String(e) });
        }
      }
    })();
    return () => {
      live = false;
    };
  }, [route]);

  if (route === null) {
    return <p>Add a route to the address bar: #/kjv/1/1/1</p>;
  }
  if (state === null) {
    return <p>Loading…</p>;
  }
  if (state.error !== null) {
    return <p>{state.error}</p>;
  }
  const label = state.translation === null ? route.translation : state.translation.label;
  return (
    <main>
      <h1>{label}</h1>
      <h2>{state.bookName ?? "Book " + String(route.book + 1)}</h2>
      <p>Chapter {String(route.chapter + 1)}</p>
    </main>
  );
}
