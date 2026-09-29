// The chapter's drop cap is a two-line initial: it spans line 1's cap height
// to line 2's baseline (styles.css `.dropcap`). A verse 1 that fits on ONE
// line leaves it hanging a full line below its only text ("the capital seems
// too low", owner 2026-09-29, Jonah 2 kie+syn), so such a verse gets a raised
// initial instead - same letter, standing on line 1's baseline (`.dropcap.one`).
//
// The count is of the TEXT's lines, never the verse box's height: the raised
// cap makes the box taller, and a height test would flip the class back.

/** Lines the verse text occupies beside its cap (the cap and screen-reader copy excluded). */
export function textLines(vt: HTMLElement): number {
  const walker = document.createTreeWalker(vt, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let lines = 0;
  let last = -Infinity;
  for (let n = walker.nextNode(); n !== null; n = walker.nextNode()) {
    const p = n.parentElement;
    if (p !== null && p.closest(".dropcap, .sr") !== null) continue;
    range.selectNodeContents(n);
    for (const r of range.getClientRects()) {
      if (r.width === 0 || r.height === 0) continue;
      // A new line starts below the previous line's middle; inline runs on
      // one line (a highlighted word, a note mark) share it.
      if (r.top > last) {
        lines++;
        last = r.top + r.height / 2;
      }
    }
  }
  return lines;
}

/** Raise the cap when the verse text is one line; keep it dropped otherwise. */
export function fitCap(vt: HTMLElement): void {
  const cap = vt.querySelector<HTMLElement>(":scope > .dropcap");
  if (cap === null) return;
  cap.classList.toggle("one", textLines(vt) <= 1);
}
