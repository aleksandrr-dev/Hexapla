"""Block-EDGE screen: is there scripture ink just OUTSIDE the text block? (0 tokens)

thorlaks_prep_coverage.py measures ROWS inside the block; thorlaks_crop_widths.py
measures the crop's right margin. Neither looks at ink immediately left or right
of the block edge, which is where Luke idx 79 was cut (2026-09-26: the default
block started ~25 pt inside the text, so every line lost its first words and
both reads declared the hanging numerals «not printed»).

Per page: re-derive the block with prep_chunk.text_block() (default, then
--robust-block), pick the one whose width matches the crops on disk (or FULL
when the crops are full-page width), then take a STRIP pt wide just outside
each block edge and count the text rows (rows with ink inside the block) that
also have ink in the strip. A healthy edge has a gutter or page margin there;
a clipped edge has the line's own words.

A page whose crop width matches no derivation is UNMATCHED - not a pass.

usage: block_edge_screen.py <kit> [<kit> ...]     (rc 1 if any flag/unmatched)
"""
import importlib.util
import io
import re
import sys
from pathlib import Path

import fitz
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOOLS = Path("C:/Projects/Hexapla/tools")
PREP = Path("C:/Projects/Hexapla-releases/research/_prep")
RESEARCH = PREP.parent
_spec = importlib.util.spec_from_file_location("prep_chunk", TOOLS / "prep_chunk.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

STRIP_PT = 4.0     # just outside the edge (PAD_X=2 already sits inside it)
FLAG = 0.10        # min single-column ink fraction over text rows near the edge


def vol_of(kit):
    m = PREP / kit / "MANIFEST.md"
    g = re.search(r"Þorláksbiblía v(\d)", io.open(m, encoding="utf-8").read())
    return int(g.group(1))


def binarised(page):
    im = pc._gray(page, pc.PROFILE_ZOOM)
    hist, tot, acc, cut = im.histogram(), 0, 0, 128
    tot = sum(hist)
    for i, c in enumerate(hist):
        acc += c
        if acc > tot * 0.12:
            cut = i
            break
    return im.point(lambda v, t=cut: 1 if v <= t else 0)


def edge_fracs(page, block):
    b = binarised(page)
    px = b.load()
    W, H = b.size
    z = pc.PROFILE_ZOOM
    bx0 = int((block.x0 - page.rect.x0) * z)
    bx1 = int((block.x1 - page.rect.x0) * z)
    s = int(STRIP_PT * z)
    rows = [y for y in range(H)
            if sum(px[x, y] for x in range(max(bx0, 0), min(bx1, W))) >= max(2, int(0.01 * (bx1 - bx0)))]
    if not rows:
        return None, None

    # GUTTER test, not strip-ink: the minimum over single columns near the edge
    # of the fraction of text rows inked in that column. A real edge (page
    # margin, or the gutter before the apparatus) has a near-white column
    # there; a cut through the text has none, every column crosses words.
    # (Strip-ink flagged the apparatus sitting 3 pt off a healthy right edge.)
    def gutter(xa, xb):
        xa, xb = max(xa, 0), min(xb, W)
        if xb - xa < 1:
            return 0.0  # the block edge IS the page edge
        return min(sum(px[x, y] for y in rows) / len(rows) for x in range(xa, xb))
    g = int(2 * z)
    return gutter(bx0 - s, bx0 + g), gutter(bx1 - g, bx1 + s)


def main():
    bad = 0
    for kit in sys.argv[1:]:
        pdf = fitz.open(str(RESEARCH / f"thorlaks_v{vol_of(kit)}.pdf"))
        for d in sorted((PREP / kit).iterdir(), key=lambda p: p.name):
            if not (d.is_dir() and re.fullmatch(r"p\d+", d.name)):
                continue
            idx = int(d.name[1:])
            page = pdf[idx]
            crops = sorted(d.glob("line[0-9][0-9].png"))
            if not crops:
                continue
            widths = sorted(Image.open(c).width for c in crops)
            cw = widths[len(widths) // 2] / pc.READ_ZOOM  # pt
            cands = [("default", pc.text_block(page)[0]),
                     ("robust", pc.text_block(page, robust=True)[0]),
                     ("full", page.rect)]
            which = [(n, r) for n, r in cands if abs(r.width - cw) <= 1.5]
            if not which:
                print(f"{kit:16s} {d.name:5s} UNMATCHED crop width {cw:.1f}pt vs "
                      + ", ".join(f"{n} {r.width:.1f}" for n, r in cands))
                bad += 1
                continue
            name, blk = which[0]
            if name == "full":
                print(f"{kit:16s} {d.name:5s} full-width  (no edge to clip)")
                continue
            L, R = edge_fracs(page, blk)
            if L is None:
                print(f"{kit:16s} {d.name:5s} {name:8s} NO TEXT ROWS - not measured")
                bad += 1
                continue
            flag = []
            if L >= FLAG:
                flag.append("LEFT-CLIP?")
            if R >= FLAG:
                flag.append("RIGHT-CLIP?")
            bad += bool(flag)
            print(f"{kit:16s} {d.name:5s} {name:8s} L={L:5.1%} R={R:5.1%} {' '.join(flag)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
