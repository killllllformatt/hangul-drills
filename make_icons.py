"""Render the app icons: a blue seal tile with 한 on it. Run once (or after changing the colours)."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SEAL, CREAM = "#2d4f9e", "#fff8ec"
FONT = r"C:\Windows\Fonts\malgunbd.ttf"

def tile(size, radius, glyph_scale, inset=0):
    S = size * 4  # supersample, then shrink
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * radius), fill=SEAL)
    if inset:
        m = int(S * inset)
        d.rounded_rectangle([m, m, S - 1 - m, S - 1 - m], radius=int(S * radius * .8), outline=CREAM, width=max(2, S // 110))
    f = ImageFont.truetype(FONT, int(S * glyph_scale))
    l, t, r, b = d.textbbox((0, 0), "한", font=f)
    d.text(((S - (r - l)) / 2 - l, (S - (b - t)) / 2 - t), "한", font=f, fill=CREAM)
    return im.resize((size, size), Image.LANCZOS)

os.makedirs(os.path.join(HERE, "icons"), exist_ok=True)
tile(192, .2, .6, .07).save(os.path.join(HERE, "icons", "icon-192.png"))
tile(512, .2, .6, .07).save(os.path.join(HERE, "icons", "icon-512.png"))
tile(180, 0, .58, .07).convert("RGB").save(os.path.join(HERE, "icons", "apple-touch-icon.png"))
tile(512, 0, .44).convert("RGB").save(os.path.join(HERE, "icons", "maskable-512.png"))
print("icons done")
