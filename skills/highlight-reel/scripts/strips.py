"""Usage: strips.py OUT.jpg CLIP...   5-frame strip per clip (autocontrast for Log footage)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate
FR = hrstate.sub('frames')
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
out = sys.argv[1]; clips = sys.argv[2:]; W, H = 384, 216
sheet = Image.new('RGB', (W * 5, len(clips) * (H + 26)), (15, 15, 15)); d = ImageDraw.Draw(sheet)
for r, c in enumerate(clips):
    y = r * (H + 26); d.text((4, y + 2), c, fill=(255, 255, 0), font=font)
    for k in range(5):
        im = ImageOps.autocontrast(Image.open(f'{FR}/{c}/frame_{k}.jpg').resize((W, H)), cutoff=1)
        sheet.paste(im, (k * W, y + 26)); d.text((k * W + W - 30, y + 2), f'f{k}', fill=(0, 255, 255), font=font)
sheet.save(out, quality=88); print(out)
