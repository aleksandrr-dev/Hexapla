"""Localized Play feature graphics (1024x500) from the English master.

Keeps the scroll art, the Hexapla wordmark and the gold underline from
feature_1024x500_en.png; replaces only the two tagline lines below the
underline. The background patch is rebuilt per pixel column by lerping
between clean rows sampled above and below the text, so the vignette
survives. Tagline color is sampled from the underline itself.

Usage: python make_feature_graphic.py  (writes feature_1024x500_<lang>.png)
"""
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "store-assets")

# Patch region: everything below the underline, right of the scroll.
X0, X1 = 440, 1010
Y_CLEAN_TOP = 306     # clean row between underline and tagline
Y_CLEAN_BOT = 404     # clean row below the tagline
UNDERLINE_Y = range(292, 302)  # scan for the brightest (gold) pixel here

FONTS = {
    "ja": ["yumindb.ttf", "yumin.ttf", "msmincho.ttc", "meiryo.ttc"],
    "zh_cn": ["simsun.ttc", "msyh.ttc"],
    "zh_tw": ["mingliu.ttc", "msjh.ttc"],
    "ta": ["Nirmala.ttf", "latha.ttf"],
    "latin": ["georgia.ttf", "constan.ttf", "times.ttf"],
}
LATIN = {"es", "fr", "de", "pt", "it", "sv", "da"}
# Indic scripts PIL cannot shape -> WPF family names (render_text.ps1).
COMPLEX = {"ta": "Nirmala UI"}
HERE = os.path.dirname(os.path.abspath(__file__))

TAGLINES = {
    "ja": ("ヘブライ語・ギリシア語・明治元訳・欽定訳", "いにしえの聖書を、並べて読む"),
    "zh_cn": ("希伯来文·希腊文·和合本·钦定本", "古老经文，并排对照"),
    "zh_tw": ("希伯來文·希臘文·和合本·欽定本", "古老經文，並排對照"),
    "es": ("Hebreo · Griego · Reina-Valera · KJV", "textos antiguos, lado a lado"),
    "fr": ("Hébreu · Grec · Martin · KJV", "textes anciens, côte à côte"),
    "de": ("Hebräisch · Griechisch · Luther · KJV", "alte Texte, Seite an Seite"),
    "pt": ("Hebraico · Grego · Almeida · KJV", "textos antigos, lado a lado"),
    "it": ("Ebraico · Greco · Diodati · KJV", "testi antichi, fianco a fianco"),
    "sv": ("Hebreiska · Grekiska · Karl XII · KJV", "gamla texter, sida vid sida"),
    "da": ("Hebraisk · Græsk · Dansk 1819 · KJV", "gamle tekster, side om side"),
    "ta": ("எபிரெயம் · கிரேக்கம் · தமிழ் IRV · KJV", "பழைமையான வேத உரைகள், அருகருகே"),
}


def load_font(lang, size):
    windir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for name in FONTS["latin" if lang in LATIN else lang]:
        path = os.path.join(windir, name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise SystemExit(f"no usable font for {lang}")


def main():
    base = Image.open(os.path.join(ASSETS, "feature_1024x500_en.png")).convert("RGB")
    gold = max(
        (base.getpixel((x, y)) for y in UNDERLINE_Y for x in range(460, 910, 10)),
        key=sum,
    )
    top_row = [base.getpixel((x, Y_CLEAN_TOP)) for x in range(X0, X1)]
    bot_row = [base.getpixel((x, Y_CLEAN_BOT)) for x in range(X0, X1)]

    for lang, (line1, line2) in TAGLINES.items():
        img = base.copy()
        px = img.load()
        for x in range(X0, X1):
            t, b = top_row[x - X0], bot_row[x - X0]
            for y in range(Y_CLEAN_TOP, Y_CLEAN_BOT + 1):
                f = (y - Y_CLEAN_TOP) / (Y_CLEAN_BOT - Y_CLEAN_TOP)
                px[x, y] = tuple(round(t[i] + (b[i] - t[i]) * f) for i in range(3))

        draw = ImageDraw.Draw(img)
        cx = (X0 + X1) // 2
        max_w = (X1 - X0) - 30
        if lang in COMPLEX:
            # PIL cannot shape Indic scripts; render the two lines via
            # tools/render_text.ps1 (WPF/DirectWrite) and paste them.
            tmp = tempfile.gettempdir()
            outs = [os.path.join(tmp, f"hex_feat_{lang}_{i}.png") for i in (1, 2)]
            items = [{"text": t, "font": COMPLEX[lang], "size": 34,
                      "color": "#%02X%02X%02X" % gold, "wrap": False,
                      "maxwidth": max_w, "out": o}
                     for t, o in zip((line1, line2), outs)]
            mf = os.path.join(tmp, "hex_feat_manifest.json")
            with open(mf, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False)
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", os.path.join(HERE, "render_text.ps1"), "-Manifest", mf],
                check=True, stdout=subprocess.DEVNULL)
            for o, y in zip(outs, (306, 354)):
                png = Image.open(o)
                img.paste(png, (cx - png.width // 2, y), png)
        else:
            for text, y in ((line1, 312), (line2, 356)):
                size = 34
                font = load_font(lang, size)
                while draw.textlength(text, font=font) > max_w and size > 20:
                    size -= 2
                    font = load_font(lang, size)
                w = draw.textlength(text, font=font)
                draw.text((cx - w / 2, y), text, font=font, fill=gold)

        out = os.path.join(ASSETS, f"feature_1024x500_{lang}.png")
        img.save(out)
        print("wrote", out)


if __name__ == "__main__":
    main()
