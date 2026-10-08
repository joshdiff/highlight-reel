"""Overview contact sheets: 3 clips per row, 5 survey frames each, 42 clips per sheet → sheets/sheet_N.jpg"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate
FR = hrstate.sub('frames'); SH = hrstate.sub('sheets')
clips = sorted(d for d in os.listdir(FR) if not d.startswith('.') and os.path.exists(f'{FR}/{d}/frame_4.jpg'))
FW, FH = 256, 144; LAB = 28; STRIP = FW * 5; GAP = 12
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
for s in range(0, len(clips), 42):
    chunk = clips[s:s + 42]; rows = (len(chunk) + 2) // 3
    sheet = Image.new('RGB', (3 * STRIP + 2 * GAP, rows * (FH + LAB + GAP)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for i, c in enumerate(chunk):
        x = (i % 3) * (STRIP + GAP); y = (i // 3) * (FH + LAB + GAP)
        d.text((x + 4, y + 2), c, fill=(255, 255, 0), font=font)
        for k in range(5):
            sheet.paste(Image.open(f'{FR}/{c}/frame_{k}.jpg').resize((FW, FH)), (x + k * FW, y + LAB))
    sheet.save(f'{SH}/sheet_{s // 42 + 1}.jpg', quality=85)
print(len(clips), 'clips', (len(clips) + 41) // 42, 'sheets in', SH)
