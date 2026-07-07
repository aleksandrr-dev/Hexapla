"""Store screenshot: verse-of-the-day widget with cover art, redrawn clean."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG_TOP = (0x2A, 0x26, 0x1F)
BG_BOT = (0x14, 0x12, 0x0E)
CARD = (0x2E, 0x2A, 0x23)
INK = (0xE8, 0xE2, 0xD9)
ACCENT = (0xD8, 0xB9, 0xC3)

img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    t = y / H
    row = tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT))
    for x in range(W):
        px[x, y] = row
d = ImageDraw.Draw(img)

seg = "C:/Windows/Fonts/segoeui.ttf"
segb = "C:/Windows/Fonts/segoeuib.ttf"
verse_f = ImageFont.truetype(seg, 40)
ref_f = ImageFont.truetype(segb, 36)
cont_f = ImageFont.truetype(seg, 36)
title_f = ImageFont.truetype(segb, 52)

cx0, cy0, cx1, cy1 = 60, 700, W - 60, 1230
d.rounded_rectangle((cx0, cy0, cx1, cy1), radius=42, fill=CARD,
                    outline=(0x4A, 0x44, 0x3A), width=2)

# Cover art (John = the Resurrection of Lazarus), rounded, left side.
art = Image.open(r"C:\Projects\Hexapla\app\src\main\assets\bookart\42.webp").resize((330, 330))
mask = Image.new("L", art.size, 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 330, 330), radius=28, fill=255)
img.paste(art, (cx0 + 34, cy0 + 34 + 60), mask)

verse = ("«" "For God so loved the world, that he gave his only begotten Son, "
         "that whosoever believeth in him should not perish, but have "
         "everlasting life." "»")

text_x = cx0 + 34 + 330 + 30
maxw = cx1 - 34 - text_x

def wrap(text, font):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

y = cy0 + 46
for line in wrap(verse, verse_f):
    d.text((text_x, y), line, font=verse_f, fill=INK)
    y += 52
d.text((text_x, cy1 - 148), "John 3:16", font=ref_f, fill=ACCENT)
d.text((text_x, cy1 - 92), "Continue reading: John 3 →", font=cont_f, fill=ACCENT)

d.text((W // 2, 480), "Verse of the day on your home screen",
       font=title_f, fill=INK, anchor="mm")

img.save(r"C:\Projects\Hexapla\store-assets\screenshot_widget.png")
print("saved", img.size)
