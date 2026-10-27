"""Fetch Oddur Gottskalksson's NT 1540 (is.wikisource, normalised spelling) as a
SECOND WITNESS for the Thorlaksbiblia 1644 NT transcription. 0 model tokens.

WITNESS ONLY, never a source and never shipped (owner 2026-09-26: comparison
use is fine). Stored under Hexapla-releases/research/_witness/oddur1540/
(untracked), transcribe first, diff after. Wikisource's text derives from the
Arnastofnun lexis.hi.is file ntodds.txt; spelling is NORMALISED, so it settles
which WORD is printed, never which sort.

Writes the raw wikitext of each of the 27 books (book_NN.txt, NT order, so a
parser bug never needs a re-fetch), then a manifest. Resumable: an existing
book file is not re-fetched. Exit 1 unless all 27 are on disk and non-empty.
Usage: fetch_oddur_witness.py [--out DIR]
"""
import json, os, sys, time, urllib.parse, urllib.request

BASE = "Nýja testamenti Odds Gottskálkssonar/"
BOOKS = [  # NT order, Matthew .. Revelation
    "S. Matteus guðsspjöll", "S. Markús guðsspjöll", "S. Lúkas guðsspjöll",
    "S. Jóhannis guðsspjöll", "Postulagjörningar skrifaðir af s. Lúkas",
    "S. Páls pistill til Rómverja", "Hinn fyrri s. Páls pistill til Korintios",
    "Annar s. Páls pistill til Korintios", "S. Páls pistill til Galatas",
    "S. Páls pistill til Efesios", "S. Páls pistill til Filippensis",
    "S. Páls pistill til Kolossenses",
    "Hinn fyrri s. Páls pistill til Þessalonikenses",
    "Annar pistill s. Páls til Þessalonia",
    "Hinn fyrri s. Páls pistill til Tímóteo", "Annar s. Páls pistill til Tímóteo",
    "S. Páls pistill til Títum", "S. Páls pistill til Fílemonem",
    "Pistillinn til Ebreos", "S. Jakobs pistill", "Hinn fyrri pistill s. Petrus",
    "Annar pistill s. Petrus", "Hinn fyrsti s. Jóhannis pistill",
    "Annar s. Jóhannis pistill", "Þriðji s. Jóhannis pistill",
    "Pistill hins heilaga Júde", "Opinberingar sankti Jóhannis"]
URL = "https://is.wikisource.org/w/index.php?title=%s&action=raw"
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else \
    "C:/Projects/Hexapla-releases/research/_witness/oddur1540"
os.makedirs(out, exist_ok=True)


def get(title):
    url = URL % urllib.parse.quote((BASE + title).replace(" ", "_"))
    req = urllib.request.Request(url, headers={"User-Agent": "HexaplaWitness/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # Wikimedia sometimes errors once; retry
            print("  retry", title, e)
            time.sleep(5)
    raise SystemExit("FAILED " + title)


ok = 0
for i, t in enumerate(BOOKS):
    f = os.path.join(out, "book_%02d.txt" % (i + 1))
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        open(f, "wb").write(get(t))
        time.sleep(1)
    n = os.path.getsize(f)
    print("%02d %7d  %s" % (i + 1, n, t))
    ok += n > 0
json.dump({"books": BOOKS, "fetched": ok}, open(os.path.join(out, "manifest.json"),
          "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("books %d of %d" % (ok, len(BOOKS)))
sys.exit(0 if ok == len(BOOKS) else 1)
