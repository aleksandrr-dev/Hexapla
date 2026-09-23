"""Fill the last coverable empty cover slots — Merian's minor prophets and the
Song of Songs, plus one Schnorr apostle plate for 1 Peter.

This finishes what Doré and Schnorr left, as far as it CAN be finished. The
source audit behind it is research/bookart_gap_sources_2026-08-10.md; the
short version is that 17th-century picture Bibles illustrate NARRATIVE, so
the 17 epistle slots and the 8 remaining apocrypha slots have no historical
plates at all and keep BookArt.kt's generated title pages. These five are the
honest remainder.

Sources
-------
· **Merian, _Icones Biblicae_ (1625-30)** — the Getty Research Institute scan,
  516 pages, one plate per page with a running head giving book and chapter.
  Public domain (Matthäus Merian d. 1650). Commons hosts it as
  `File:Icones Biblicae Veteris et Novi Testamenti … (IA gri 33125009314267).pdf`;
  staged locally beside the other campaign scans. NOTE the plates are NOT on
  Commons individually, so build_bookart2.py's Special:FilePath pattern does
  not apply here — this extracts from the PDF.
· **Schnorr von Carolsfeld, _Die Bibel in Bildern_ (1860)** — same source and
  same download path as build_bookart2.py.

Every page below was READ before being mapped, not inferred from position:
each Merian plate prints its own title, and p266's Latin epigram — "Est
Christus Sponsus, Sponsa est Ecclesia Christi" — is what identifies
"COELESTIS SALOMON" as the Song of Songs rather than a Solomon-the-king
scene.

⚠ Style note: Merian is 17th-century baroque line engraving against Doré and
Schnorr's 19th-century romantic work. Monochrome line art in both cases, but
denser hatching and busier compositions. Judged acceptable for four slots
that would otherwise be blank; it is not seamless.
"""
import io
import os
import time
import urllib.request

import fitz
from PIL import Image

OUT = r"C:\Projects\Hexapla\app\src\main\assets\bookart"
MERIAN = r"C:/Projects/Hexapla-releases/research/merian_icones_biblicae.pdf"
MERIAN_URL = ("https://upload.wikimedia.org/wikipedia/commons/9/96/"
              "Icones_Biblicae_Veteris_et_Novi_Testamenti._Figuren_Biblischer_"
              "Historien_Alten_und_Neuen_Testaments_%28IA_gri_33125009314267%29.pdf")
SCHNORR_URL = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
               "Schnorr_von_Carolsfeld_Bibel_in_Bildern_1860_{:03d}.png?width=760")
UA = {"User-Agent": "HexaplaArtBot/1.0 (+https://github.com/aleksandrr-dev/Hexapla)"}

# bookIdx -> (pdf page, printed running head, Merian's own plate number)
MERIAN_PLATES = {
    21: (266, "COELESTIS SALOMON, Cap. I", 23),   # Song of Solomon
    27: (296, "HOSEA", 38),                       # Hosea
    36: (294, "PROPHETA HAGGAEUS, Cap. I", 37),   # Haggai
    38: (298, "PROPHETA MALACHIAS, Cap. I", 39),  # Malachi
}

# bookIdx -> (plate, subject). Schnorr's 12 unused NT plates are Acts and
# Revelation scenes; 231 is the only one that maps to an empty slot without
# an arbitrary pairing — a Peter plate for a Peter epistle.
SCHNORR_PLATES = {
    59: (231, "Peter Freed from Prison by the Angel"),
}


def longest_run(mask, max_gap: int = 12):
    """Longest contiguous True run, tolerating small gaps."""
    runs, start, gap = [], None, 0
    for i, v in enumerate(mask):
        if v:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap > max_gap:
                runs.append((start, i - gap))
                start, gap = None, 0
    if start is not None:
        runs.append((start, len(mask) - 1 - gap))
    return max(runs, key=lambda r: r[1] - r[0]) if runs else None


def detect_plate(page):
    """Find the engraving on a Merian page.

    ⚠ Fixed fractions do NOT work here, and trying them is what produced a
    first pass of covers with the running head and the Latin epigram baked
    into the picture. The plate sits between those two text bands and both
    drift page to page. So find it by ink: the scan carries black margins, so
    locate the paper first (mostly-bright rows and columns), then take the
    longest sustained high-ink band inside it. That band is the engraving —
    the epigram is dense too but broken by white line gaps, so it loses the
    run.
    """
    import numpy as np

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    a = np.asarray(Image.frombytes("RGB", (pix.width, pix.height),
                                   pix.samples).convert("L"))
    H, W = a.shape
    bright = a > 170
    rs = np.where(bright.sum(1) / W > 0.5)[0]
    cs = np.where(bright.sum(0) / H > 0.5)[0]
    if len(rs) < 2 or len(cs) < 2:
        raise SystemExit(f"page {page.number}: could not find the paper")
    py0, py1, px0, px1 = rs[0], rs[-1], cs[0], cs[-1]

    sub = a[py0:py1 + 1, px0:px1 + 1]
    h, w = sub.shape
    ink = sub < 140
    ry = longest_run((ink.sum(1) / w) > 0.25)
    if ry is None:
        raise SystemExit(f"page {page.number}: no engraving band found")
    band = ink[ry[0]:ry[1] + 1]
    rx = longest_run((band.sum(0) / band.shape[0]) > 0.25)
    if rx is None:
        raise SystemExit(f"page {page.number}: engraving has no width")

    r = page.rect
    sx, sy = r.width / W, r.height / H
    box = fitz.Rect(r.x0 + (px0 + rx[0]) * sx, r.y0 + (py0 + ry[0]) * sy,
                    r.x0 + (px0 + rx[1]) * sx, r.y0 + (py0 + ry[1]) * sy)
    aspect = box.width / box.height
    if not 1.1 < aspect < 1.9:
        raise SystemExit(f"page {page.number}: detected box has aspect "
                         f"{aspect:.2f}, expected a landscape plate near 1.4 — "
                         "the detector has latched onto the wrong band")
    return box


def square(img: Image.Image, bias: float = 0.30) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = max(0, int((h - side) * bias))
    return img.crop((left, top, left + side, top + side)).resize(
        (512, 512), Image.LANCZOS)


def ensure_merian() -> str:
    if os.path.exists(MERIAN):
        return MERIAN
    print(f"downloading Merian scan -> {MERIAN}")
    os.makedirs(os.path.dirname(MERIAN), exist_ok=True)
    req = urllib.request.Request(MERIAN_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=900) as r, open(MERIAN, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    return MERIAN


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    written = 0

    doc = fitz.open(ensure_merian())
    for idx, (page, head, plate) in sorted(MERIAN_PLATES.items()):
        dst = os.path.join(OUT, f"{idx}.webp")
        if os.path.exists(dst):
            print(f"{idx:>3} merian p{page} {head:<32} (already done)")
            continue
        p = doc[page]
        clip = detect_plate(p)
        pix = p.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        # The engraving is much wider than tall; take the middle, no top bias.
        square(img, bias=0.5).save(dst, "WEBP", quality=78)
        written += 1
        print(f"{idx:>3} merian p{page} plate {plate:<3} {head:<32} "
              f"{os.path.getsize(dst) // 1024} KB")

    for idx, (plate, subject) in sorted(SCHNORR_PLATES.items()):
        dst = os.path.join(OUT, f"{idx}.webp")
        if os.path.exists(dst):
            print(f"{idx:>3} schnorr {plate} {subject:<32} (already done)")
            continue
        req = urllib.request.Request(SCHNORR_URL.format(plate), headers=UA)
        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception as e:
                print(f"  retry {attempt + 1} plate {plate}: {e}")
                time.sleep(8 * (attempt + 1))
        if data is None:
            print(f"  !! failed schnorr plate {plate}")
            continue
        img = Image.open(io.BytesIO(data)).convert("RGB")
        square(img, bias=0.30).save(dst, "WEBP", quality=78)
        written += 1
        print(f"{idx:>3} schnorr {plate} {subject:<32} "
              f"{os.path.getsize(dst) // 1024} KB")
        time.sleep(1.5)

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"\nwrote {written} covers; assets/bookart: "
          f"{len(os.listdir(OUT))} files, {total // 1024} KB")


if __name__ == "__main__":
    main()
