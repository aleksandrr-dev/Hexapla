"""Extra Dore plates so the most-read books ROTATE their cover art.

BookArt.kt picks among "<bookIdx>.webp", "<bookIdx>_1.webp", "<bookIdx>_2.webp"
with a date seed, so a book that ships more than one plate shows a different
one each day. This script adds the variants; build_bookart.py still owns the
base plate.

Same source, crop and quality as build_bookart.py — Gustave Dore, public
domain 1866, via Project Gutenberg #8710 — so a rotating book never changes
artist mid-rotation.

⚠ The plate numbers below were NOT recalled. They come from the plate index
derived off Gutenberg #8710's own text (each plate's scripture reference is
printed under it); the derivation was checked against build_bookart.py's
existing curated map, which it reproduces exactly — plate 4 = Genesis vii
(the Deluge), 73 = Luke x (the Good Samaritan), 100 = Revelation vi (the pale
horse). Re-derive rather than edit by hand if this ever needs extending.
"""
import io
import os
import time
import urllib.request
from PIL import Image

OUT = r"C:\Projects\Hexapla\app\src\main\assets\bookart"
BASE = "https://www.gutenberg.org/files/8710/8710-h/images/{:03d}.jpg"

# Plates already spoken for as a book's BASE cover in build_bookart.py. Reusing
# one would make two books share a picture, which reads as a bug.
BASE_PLATES = {4, 19, 20, 27, 29, 31, 34, 37, 41, 43, 44, 45, 46, 48, 52, 53,
               54, 55, 56, 63, 64, 73, 80, 95, 100}

# bookIdx -> [(plate, scripture ref, subject)] in rotation order after the base.
# Chosen to be iconic AND distinct from the book's other plates: a second
# lions'-den or a second Lazarus would read as a glitch, not variety.
VARIANTS = {
    0: [(6,  "Genesis xi, 1-9",       "The Tower of Babel"),
        (8,  "Genesis xix, 15-28",    "The Destruction of Sodom"),
        (11, "Genesis xxii, 1-18",    "The Sacrifice of Isaac"),
        (14, "Genesis xxvii, 1-29",   "Isaac Blessing Jacob"),
        (17, "Genesis xli, 1-36",     "Joseph Interprets Pharaoh's Dream"),
        (18, "Genesis xlv, 1-18",     "Joseph Made Known to His Brethren")],
    8: [(33, "1 Samuel xxxi",         "The Death of Saul")],
    10: [(38, "1 Kings v",            "Timber Felled for the Temple")],
    26: [(50, "Daniel iii, 12-27",    "The Fiery Furnace"),
         (51, "Daniel v",             "Belshazzar's Feast")],
    39: [(82, "Matthew xxvi, 17-30",  "The Last Supper"),
         (91, "Matthew xxviii, 1-8",  "The Resurrection Morning"),
         (59, "Matthew ii, 13-15",    "The Flight into Egypt"),
         (69, "Matthew xxi",          "The Entry into Jerusalem"),
         (89, "Matthew xxvii, 45-56", "The Darkness at the Crucifixion")],
    40: [(72, "Mark v, 22-43",        "Jairus' Daughter Raised"),
         (68, "Mark vi, 46-52",       "Christ Walking on the Sea"),
         (85, "Mark xiv, 41-50",      "The Betrayal"),
         (70, "Mark xii, 13-17",      "The Tribute Money")],
    41: [(75, "Luke xv, 10-32",       "The Prodigal Son"),
         (92, "Luke xxiv, 13-35",     "The Road to Emmaus"),
         (57, "Luke ii",              "The Nativity"),
         (61, "Luke ii, 41-52",       "The Boy Jesus in the Temple"),
         (76, "Luke xvi, 19-31",      "Dives and Lazarus")],
    42: [(86, "John xix, 16-18",      "Christ Bearing the Cross"),
         (78, "John iv, 5-30",        "Christ and the Samaritan Woman"),
         (79, "John viii, 1-11",      "The Woman Taken in Adultery")],
    43: [(93, "Acts i, 1-10",         "The Ascension"),
         (99, "Acts xxvii, 33-44",    "Paul's Shipwreck"),
         (94, "Acts vi, 8-15",        "The Stoning of Stephen"),
         (96, "Acts xii, 1-11",       "Peter Delivered from Prison")],
}


def fetch(plate: int) -> bytes | None:
    req = urllib.request.Request(BASE.format(plate), headers={"User-Agent": "hexapla-art"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            print(f"  retry {attempt + 1} for plate {plate}: {e}")
            time.sleep(10 * (attempt + 1))
    return None


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    seen_plates = {}
    written = 0
    for idx, plates in sorted(VARIANTS.items()):
        base = os.path.join(OUT, f"{idx}.webp")
        if not os.path.exists(base):
            print(f"!! book {idx} has no base plate — run build_bookart.py first")
            continue
        for n, (plate, ref, subject) in enumerate(plates, start=1):
            # A plate used twice would make two books share a cover.
            if plate in BASE_PLATES:
                print(f"!! plate {plate} is already a base cover — skipping")
                continue
            if plate in seen_plates:
                print(f"!! plate {plate} already assigned to book {seen_plates[plate]}")
                continue
            seen_plates[plate] = idx
            dst = os.path.join(OUT, f"{idx}_{n}.webp")
            if os.path.exists(dst):
                print(f"{idx:>3}_{n} plate {plate:>3} {subject:<32} (already done)")
                continue
            data = fetch(plate)
            if data is None:
                print(f"  !! giving up on plate {plate}")
                continue
            time.sleep(2)
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = max(0, int((h - side) * 0.25))
            img = img.crop((left, top, left + side, top + side)).resize((512, 512), Image.LANCZOS)
            img.save(dst, "WEBP", quality=78)
            written += 1
            print(f"{idx:>3}_{n} plate {plate:>3} {subject:<32} {ref:<22} "
                  f"{os.path.getsize(dst) // 1024} KB")

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    rotating = sum(1 for v in VARIANTS.values() if v)
    print(f"\nwrote {written} variants; {rotating} books now rotate")
    print(f"assets/bookart total: {len(os.listdir(OUT))} files, {total // 1024} KB")


if __name__ == "__main__":
    main()
