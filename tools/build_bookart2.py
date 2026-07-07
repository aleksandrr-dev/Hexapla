"""Add Schnorr von Carolsfeld (Die Bibel in Bildern, 1860, public domain)
plates as media-card covers, mapped from the volume's own transcribed index.
Downloads from Wikimedia Commons via Special:FilePath.
"""
import io
import os
import time
import urllib.request
from PIL import Image

OUT = r"C:\Projects\Hexapla\app\src\main\assets\bookart"
URL = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
       "Schnorr_von_Carolsfeld_Bibel_in_Bildern_1860_{:03d}.png?width=760")

# bookIdx -> (plate, index title). Verified against the 1852/1860 "Inhalt".
PLATES = {
    2: (60, "Aarons Priesterthum (budding rod)"),        # Leviticus
    3: (61, "The brazen serpent"),                       # Numbers
    4: (65, "Mosis Tod"),                                # Deuteronomy
    8: (92, "David ueberwindet Goliath"),                # 1 Samuel (upgrade)
    12: (106, "David und seine Helden"),                 # 1 Chronicles
    14: (126, "Founding the new temple"),                # Ezra
    15: (127, "Building the city walls"),                # Nehemiah
    17: (132, "Der leidende Hiob und seine Freunde"),    # Job
    18: (134, "David der Psalmist"),                     # Psalms
    23: (140, "Der Prophet Jeremia"),                    # Jeremiah (upgrade)
    24: (141, "Jeremiae Klage"),                         # Lamentations
    44: (235, "Pauli Ankunft zu Rom"),                   # Romans
    45: (233, "Paulus lehrt zu Athen"),                  # 1 Corinthians
    47: (232, "Paulus und Barnabas zu Lystra"),          # Galatians
    48: (234, "Abschied von den Ephesern"),              # Ephesians
    68: (146, "Das Gebet des Tobias und der Sara"),      # Tobit
    69: (144, "Judith enthauptet den Holofernes"),       # Judith
    70: (148, "Ruhm der Weisheit"),                      # Wisdom of Solomon
    71: (149, "Lob guter Kinderzucht"),                  # Sirach
    75: (152, "Judas Maccabaeus reinigt den Tempel"),    # 1 Maccabees
    80: (159, "Daniel errettet Susanna"),                # Susanna
}

def main():
    os.makedirs(OUT, exist_ok=True)
    for idx, (plate, title) in sorted(PLATES.items()):
        url = URL.format(plate)
        req = urllib.request.Request(url, headers={
            "User-Agent": "HexaplaArtBot/1.0 (aleksratchkov@gmail.com)"
        })
        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                break
            except Exception as e:
                print(f"  retry {attempt + 1} plate {plate}: {e}")
                time.sleep(8 * (attempt + 1))
        if data is None:
            print(f"  !! failed plate {plate}")
            continue
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = max(0, int((h - side) * 0.30))
        img = img.crop((left, top, left + side, top + side)).resize((512, 512), Image.LANCZOS)
        dst = os.path.join(OUT, f"{idx}.webp")
        img.save(dst, "WEBP", quality=78)
        print(f"{idx:>3} plate {plate:>3} {title:<42} {os.path.getsize(dst)//1024} KB")
        time.sleep(1.5)
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"\nassets/bookart total: {len(os.listdir(OUT))} covers, {total // 1024} KB")

if __name__ == "__main__":
    main()
