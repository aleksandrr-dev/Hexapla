"""Store screenshot: the reader showing John 1 in a localized
translation, redrawn clean in the app's dark-theme look (same approach
as make_widget_shot.py). Verse text is pulled from the real assets.
CJK entries wrap per character (with simple kinsoku); Latin-script
entries wrap on words.

Usage: python make_reader_shot.py
Writes store-assets/screenshot_reader_{ja,zh_cn,zh_tw,pt,it,sv,da}.png
"""
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")
OUT = os.path.join(HERE, "..", "store-assets")

W, H = 1080, 1920
BG = (0x18, 0x14, 0x11)
INK = (0xE9, 0xE2, 0xD4)
GOLD = (0xD6, 0xA2, 0x5E)
NUM = (0xC9, 0x93, 0x50)
ICON = (0xE0, 0xD8, 0xC8)
DIVIDER = (0x3A, 0x35, 0x2F)

WIN_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# (lang, asset, title, font candidates, cjk wrap?)
SHOTS = [
    ("ja", "ja_meiji.json", "約翰傳福音書 1", ["YuGothM.ttc", "MEIRYO.TTC", "msgothic.ttc"], True),
    ("zh_cn", "zh_cuv_s.json", "约翰福音 1", ["simsun.ttc", "msyh.ttc"], True),
    ("zh_tw", "zh_cuv_t.json", "約翰福音 1", ["simsun.ttc", "msjh.ttc"], True),
    ("pt", "pt_almeida.json", "João 1", ["segoeui.ttf"], False),
    ("it", "it_diodati.json", "Giovanni 1", ["segoeui.ttf"], False),
    ("sv", "sv_karlxii.json", "Johannes 1", ["segoeui.ttf"], False),
    ("da", "da_1819.json", "Johannes 1", ["segoeui.ttf"], False),
    ("ta", "ta_irv.json", "யோவான் 1", ["Nirmala.ttf"], False),
]

# Scripts PIL cannot shape (Indic reordering needs Raqm, absent from the
# Windows wheels): text is rendered by tools/render_text.ps1 (WPF /
# DirectWrite) into transparent PNGs and pasted. Font = WPF family name.
COMPLEX = {"ta": "Nirmala UI"}


def render_via_wpf(items):
    mf = os.path.join(tempfile.gettempdir(), "hexapla_render_text.json")
    with open(mf, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", os.path.join(HERE, "render_text.ps1"), "-Manifest", mf],
        check=True, stdout=subprocess.DEVNULL)

NO_LINE_START = "、。，．」』）？！：；・"


def font_of(names, size):
    for n in names:
        p = os.path.join(WIN_FONTS, n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    raise SystemExit(f"no font among {names}")


def wrap_words(draw, text, font, maxw):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def wrap_cjk(draw, text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= maxw:
            cur += ch
        else:
            if ch in NO_LINE_START:  # simple kinsoku: keep punctuation attached
                cur += ch
                lines.append(cur)
                cur = ""
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_topbar(d, title, tfont):
    y = 165
    # back arrow
    d.line((70, y, 130, y), fill=ICON, width=7)
    d.line((70, y, 100, y - 28), fill=ICON, width=7)
    d.line((70, y, 100, y + 28), fill=ICON, width=7)
    # title (None when a COMPLEX language pastes a prerendered title)
    if title is not None:
        w = d.textlength(title, font=tfont)
        d.text(((W - w) / 2 - 60, y - 30), title, font=tfont, fill=GOLD)
    # search
    d.ellipse((715, y - 26, 755, y + 14), outline=ICON, width=6)
    d.line((752, y + 10, 775, y + 32), fill=ICON, width=7)
    # speaker
    d.polygon([(845, y - 8), (868, y - 8), (896, y - 32), (896, y + 32),
               (868, y + 8), (845, y + 8)], fill=ICON)
    d.arc((900, y - 20, 934, y + 20), -50, 50, fill=ICON, width=5)
    # forward arrow
    d.line((950, y, 1010, y), fill=ICON, width=7)
    d.line((1010, y, 980, y - 28), fill=ICON, width=7)
    d.line((1010, y, 980, y + 28), fill=ICON, width=7)
    d.line((0, 232, W, 232), fill=DIVIDER, width=2)


def hexc(rgb):
    return "#%02X%02X%02X" % rgb


def main():
    for lang, asset, title, fonts, cjk in SHOTS:
        books = json.load(open(os.path.join(ASSETS, asset), encoding="utf-8"))
        verses = books[42]["chapters"][0]

        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        nfont = font_of(["segoeui.ttf"], 28) if lang in COMPLEX else font_of(fonts, 28)

        x_num, x_text, maxw = 48, 100, W - 100 - 52
        y = 300
        if lang in COMPLEX:
            # Shape title + verse blocks in WPF, paste; icons/numbers by PIL.
            family = COMPLEX[lang]
            tmp = tempfile.gettempdir()
            outs = [os.path.join(tmp, f"hex_{lang}_title.png")] + [
                os.path.join(tmp, f"hex_{lang}_v{i}.png") for i in range(len(verses))
            ]
            items = [{"text": title, "font": family, "size": 48,
                      "color": hexc(GOLD), "wrap": False, "maxwidth": 0,
                      "out": outs[0]}]
            items += [{"text": v, "font": family, "size": 46,
                       "color": hexc(INK), "wrap": True, "maxwidth": maxw,
                       "out": outs[1 + i]} for i, v in enumerate(verses)]
            render_via_wpf(items)
            draw_topbar(d, None, None)
            tpng = Image.open(outs[0])
            img.paste(tpng, ((W - tpng.width) // 2 - 60, 165 - tpng.height // 2), tpng)
            for i in range(len(verses)):
                vpng = Image.open(outs[1 + i])
                d.text((x_num, y + 14), str(i + 1), font=nfont, fill=NUM)
                img.paste(vpng, (x_text, y), vpng)
                y += vpng.height + 36
                if y > H:
                    break
        else:
            tfont = font_of(fonts, 48)
            vfont = font_of(fonts, 46)
            draw_topbar(d, title, tfont)
            line_h, verse_gap = (70, 42) if cjk else (62, 36)
            wrap = wrap_cjk if cjk else wrap_words
            for i, verse in enumerate(verses):
                d.text((x_num, y + 14), str(i + 1), font=nfont, fill=NUM)
                for line in wrap(d, verse, vfont, maxw):
                    d.text((x_text, y), line, font=vfont, fill=INK)
                    y += line_h
                    if y > H:
                        break
                y += verse_gap
                if y > H:
                    break

        out = os.path.join(OUT, f"screenshot_reader_{lang}.png")
        img.save(out)
        print("saved", out)


if __name__ == "__main__":
    main()
