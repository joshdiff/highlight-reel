"""Torso-crop ID sheets from the full-res survey frames: the top 3 players of one team per frame,
10 clips per sheet → sheets/<side>/crops_NN.jpg + crops_meta.json.

Each tile is labelled  f<k>.<i>  and its meta entry "<clip>:<n>" holds the source time `t` and the
player's box in SOURCE pixels `box_src` — exactly what a player profile reference needs
(hrprofile.py ref add … --t T --box x0,y0,x1,y1, or the `ref` field of a find.json clip).

Usage: crops.py [--team home|away|TEAM_ID] [CLIP...]   (default team: the current target's, else home)"""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate
from PIL import Image, ImageDraw, ImageFont, ImageOps

FRACS = (0.10, 0.25, 0.50, 0.75, 0.90)
TW, TH, PER, ROWS, LW = 120, 150, 3, 10, 110
F4 = hrstate.sub('frames_4k')
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
except OSError:
    font = ImageFont.load_default()


def players(bl):
    """Merge shirt blobs that belong to one player (shirt split by a number/arm), biggest first."""
    bl = [b for b in bl if b['area'] >= 60]; groups = []
    for b in sorted(bl, key=lambda b: -b['area']):
        for g in groups:
            if b['x1'] > g['x0'] - 4 and b['x0'] < g['x1'] + 4 and abs(b['cy'] - g['cy']) < (g['y1'] - g['y0']) * 2.5:
                g['x0'] = min(g['x0'], b['x0']); g['x1'] = max(g['x1'], b['x1'])
                g['y0'] = min(g['y0'], b['y0']); g['y1'] = max(g['y1'], b['y1']); g['area'] += b['area']; break
        else:
            groups.append(dict(b))
    return sorted([g for g in groups if g['area'] >= 250], key=lambda g: -g['area'])


def crop_box(g, S):
    w = g['x1'] - g['x0']; h = g['y1'] - g['y0']; cx = (g['x0'] + g['x1']) / 2
    side = max(w, h * 0.8) * 1.3; top = g['y0'] - h * 0.35
    return [int((cx - side / 2) * S), int(top * S), int((cx + side / 2) * S), int((top + side * 1.25) * S)]


if __name__ == '__main__':
    a = sys.argv[1:]
    team = a[a.index('--team') + 1] if '--team' in a else None
    if team:
        a = [x for x in a if x not in ('--team', team)]
    else:
        tj = hrstate._read(os.path.join(hrstate.game_dir(), 'targets', hrstate.current().get('target') or '-', 'find.json'), {})
        team = tj.get('side') or 'home'
    side = hrstate.team_key(team)[0]
    SH = hrstate.sub('sheets'); OUT = os.path.join(SH, side); os.makedirs(OUT, exist_ok=True)
    res = json.load(open(f'{SH}/blobs_{side}.json'))
    media = hrstate.get('media.clips') or {}
    clips = a or sorted(res)
    rows = []
    for c in clips:
        tiles = [(k, g) for k in range(5) for g in players(res[c][k])[:PER]]
        rows.append((c, tiles))
    meta = {}
    for s in range(0, len(rows), ROWS):
        chunk = rows[s:s + ROWS]
        sheet = Image.new('RGB', (LW + 15 * TW, ROWS * (TH + 20)), (15, 15, 15)); d = ImageDraw.Draw(sheet)
        for r, (c, tiles) in enumerate(chunk):
            y = r * (TH + 20); d.text((4, y + 60), c[-12:], fill=(255, 255, 0), font=font)
            m = media.get(c, {}); t0, t1 = float(m.get('in', 0)), float(m.get('out') or m.get('duration') or 0)
            for i, (k, g) in enumerate(tiles):
                im = Image.open(f'{F4}/{c}/frame_{k}.jpg'); S = im.width / 1280
                tile = ImageOps.autocontrast(im.crop(crop_box(g, S)).resize((TW, TH)), cutoff=1)
                sheet.paste(tile, (LW + i * TW, y + 18)); d.text((LW + i * TW + 3, y), f'f{k}.{i}', fill=(0, 255, 255), font=font)
                meta[f'{c}:{i}'] = dict(frame=k, t=round(t0 + (t1 - t0) * FRACS[k], 3),
                                        box_src=[int(g['x0'] * S), int(g['y0'] * S), int(g['x1'] * S), int(g['y1'] * S)])
        sheet.save(os.path.join(OUT, f'crops_{s // ROWS + 1:02d}.jpg'), quality=88)
    json.dump(meta, open(os.path.join(OUT, 'crops_meta.json'), 'w'))
    print(f'{(len(rows) + ROWS - 1) // ROWS} sheets → {OUT}')
