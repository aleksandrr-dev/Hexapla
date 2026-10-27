"""Fetch the Guðbrandsbiblía 1584 (biblian.is, modernised spelling) as a
WITNESS for the Þorláksbiblía 1644 transcription. 0 model tokens.

⛔ WITNESS ONLY, never a source and never shipped: the text is «Allur réttur
áskilinn» and the Icelandic Bible Society declined publication (2026-07-12,
docs/TRANSLATIONS.md). Owner 2026-09-26: comparison use is fine. Stored under
Hexapla-releases/research/_witness/ (untracked), transcribe first, diff after.

Writes one JSON per REST page of 100 chapter pages (raw WordPress JSON, so a
parser bug never needs a re-fetch), then a manifest. Resumable: an existing
page file is not re-fetched.
Usage: fetch_gudbrandsbiblia_witness.py [--out DIR]
"""
import json, os, sys, time, urllib.request

API = ("https://biblian.is/gudbrandsbiblia/wp-json/wp/v2/pages"
       "?per_page=100&page=%d&_fields=id,slug,title,content,parent")
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else \
    "C:/Projects/Hexapla-releases/research/_witness/gudbrandsbiblia"
os.makedirs(out, exist_ok=True)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers


body, hdr = get(API % 1)
total, pages = int(hdr["X-WP-Total"]), int(hdr["X-WP-TotalPages"])
got = 0
for p in range(1, pages + 1):
    f = os.path.join(out, "pages_%02d.json" % p)
    if not os.path.exists(f):
        if p > 1:
            time.sleep(2)
            body, _ = get(API % p)
        open(f, "wb").write(body)
    got += len(json.load(open(f, encoding="utf-8")))
json.dump({"total": total, "pages": pages, "records": got},
          open(os.path.join(out, "manifest.json"), "w"), indent=1)
print("records %d of X-WP-Total %d" % (got, total))
sys.exit(0 if got == total else 1)
