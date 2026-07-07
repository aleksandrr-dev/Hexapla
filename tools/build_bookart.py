"""Download Gustave Doré plates (public domain, via Project Gutenberg #8710)
and build square media-card art assets: assets/bookart/<bookIdx>.webp
"""
import io
import os
import time
import urllib.request
from PIL import Image

OUT = r"C:\Projects\Hexapla\app\src\main\assets\bookart"
BASE = "https://www.gutenberg.org/files/8710/8710-h/images/{:03d}.jpg"

# bookIdx -> (plate number, title) — the most memorable Doré depiction per book.
PLATES = {
    0: (4, "The Deluge"),                       # Genesis
    1: (19, "Moses in the Bulrushes"),          # Exodus
    5: (20, "The War Against Gibeon"),          # Joshua
    6: (27, "The Death of Samson"),             # Judges
    7: (29, "Ruth and Boaz"),                   # Ruth
    8: (31, "Saul and David"),                  # 1 Samuel
    9: (34, "The Death of Absalom"),            # 2 Samuel
    10: (37, "The Judgment of Solomon"),        # 1 Kings
    11: (41, "Elijah's Ascent in a Chariot of Fire"),  # 2 Kings
    13: (45, "Destruction of Sennacherib's Host"),     # 2 Chronicles
    16: (43, "Esther Confounding Haman"),       # Esther
    19: (36, "Solomon"),                        # Proverbs
    22: (44, "Isaiah"),                         # Isaiah
    25: (48, "The Vision of Ezekiel"),          # Ezekiel
    26: (52, "Daniel in the Lions' Den"),       # Daniel
    29: (53, "The Prophet Amos"),               # Amos
    31: (54, "Jonah Calling Nineveh to Repentance"),   # Jonah
    39: (63, "Sermon on the Mount"),            # Matthew
    40: (64, "Christ Stilling the Tempest"),    # Mark
    41: (73, "The Good Samaritan"),             # Luke
    42: (80, "The Resurrection of Lazarus"),    # John
    43: (95, "Saul's Conversion"),              # Acts
    65: (100, "Death on the Pale Horse"),       # Revelation
    72: (46, "Baruch"),                         # Baruch (Apocrypha)
    76: (56, "Heliodorus Punished in the Temple"),     # 2 Maccabees
    81: (55, "Daniel Confounding the Priests of Bel"), # Bel and the Dragon
}

def main():
    os.makedirs(OUT, exist_ok=True)
    for idx, (plate, title) in sorted(PLATES.items()):
        dst_check = os.path.join(OUT, f"{idx}.webp")
        if os.path.exists(dst_check):
            print(f"{idx:>3} plate {plate:>3} {title:<45} (already done)")
            continue
        url = BASE.format(plate)
        req = urllib.request.Request(url, headers={"User-Agent": "hexapla-art"})
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                break
            except Exception as e:
                print(f"  retry {attempt + 1} for plate {plate}: {e}")
                time.sleep(10 * (attempt + 1))
        if data is None:
            print(f"  !! giving up on plate {plate}")
            continue
        time.sleep(2)
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        side = min(w, h)
        # Center-crop horizontally; bias upward vertically — engravings tend to
        # carry the subject in the upper two thirds.
        left = (w - side) // 2
        top = max(0, int((h - side) * 0.25))
        img = img.crop((left, top, left + side, top + side)).resize((512, 512), Image.LANCZOS)
        dst = os.path.join(OUT, f"{idx}.webp")
        img.save(dst, "WEBP", quality=78)
        print(f"{idx:>3} plate {plate:>3} {title:<45} {os.path.getsize(dst)//1024} KB")
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"\ntotal: {len(PLATES)} covers, {total // 1024} KB")

if __name__ == "__main__":
    main()
