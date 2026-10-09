"""Subject strips: who the camera operator is following, once per second, for every clip.

The operator keeps the subject near the centre, so each sample crops the biggest target-team player
weighted by closeness to the frame centre (banner-shaped blobs, wider than tall, are skipped).
Reading these strips finds on-ball moments the 5-sample crop sheets miss: hair, sleeves and the
back number show up over a whole possession, not at 5 fixed instants.

Output: sheets/subject/subj_NN.jpg (one row per 12 samples, labelled with the clip and source second)
+ subj_meta.json {"<clip>@<t>": {"clip", "t", "box_src"}} (box in 4K source pixels, for profile refs).

--center skips detection and crops the middle of the frame (a 9:16 window, 70% of the frame height) —
for kits colour can't separate from the background (black/dark kits in Log footage, backlight). The operator
keeps the subject near the centre, so it still shows who they were following; box_src is the crop.
--crop F sets the crop height as a fraction of the frame (default 0.45; smaller zooms in for distant play).

Usage: subject.py [--team home|away|TEAM_ID] [--fps 1] [--jobs 4] [--center [--crop 0.45]] [CLIP...]   (default: every clip)"""
import os, sys, json, math, glob, subprocess, shutil, io
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, hrstate
from detect import team_blobs
from crops import players, crop_box
from PIL import Image, ImageDraw, ImageFont

TW, TH, COLS, ROWS, LW, DW = 150, 188, 12, 8, 120, 1280
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
except OSError:
    font = ImageFont.load_default()


def sample(args):
    """One clip → [(t, jpeg bytes | None, box_src | None)]."""
    c, m, rng, fps, center = args
    frac = center if isinstance(center, float) else 0.45
    d = hrstate.tmp('subject'); out = []
    subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-ss', str(m['in']), '-i', m['path'],
                    '-t', str(m['out'] - m['in']), '-vf', f'fps={fps},scale=1920:-2', '-strict', 'unofficial',
                    '-q:v', '3', f'{d}/f_%04d.jpg'], check=True)
    for i, f in enumerate(sorted(glob.glob(d + '/f_*.jpg'))):
        t = round(m['in'] + i / fps, 2); big = cv2.imread(f); os.remove(f)
        H, W = big.shape[:2]; small = cv2.resize(big, (DW, round(H * DW / W))); sc = W / DW
        if center:
            ch = int(H * frac); cw = int(ch * TW / TH); x0, y0 = (W - cw) // 2, (H - ch) // 2
            crop = cv2.convertScaleAbs(big[y0:y0 + ch, x0:x0 + cw], alpha=1.5, beta=-40)
            k = m.get('width', W) / W
            out.append((t, cv2.imencode('.jpg', crop)[1].tobytes(), [int(v * k) for v in (x0, y0, x0 + cw, y0 + ch)]))
            continue
        ps = [g for g in players(team_blobs(small, rng)) if g['y1'] - g['y0'] >= 0.9 * (g['x1'] - g['x0'])]
        best = max(ps, key=lambda g: g['area'] * math.exp(-(((g['x0'] + g['x1']) / 2 - DW / 2) / (DW * 0.22)) ** 2),
                   default=None)
        if not best:
            out.append((t, None, None)); continue
        x0, y0, x1, y1 = crop_box(best, sc)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        crop = cv2.convertScaleAbs(big[y0:y1, x0:x1], alpha=1.5, beta=-40)   # lift flat Log footage
        k = m.get('width', W) / W
        out.append((t, cv2.imencode('.jpg', crop)[1].tobytes(), [int(v * k) for v in (x0, y0, x1, y1)]))
    shutil.rmtree(d, ignore_errors=True)
    return c, out


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k, dflt: a[a.index(k) + 1] if k in a else dflt
    team, fps, jobs = opt('--team', None), float(opt('--fps', 1)), int(opt('--jobs', 4))
    clips = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--team', '--fps', '--jobs', '--crop'))]
    media = hrstate.get('media.clips') or {}
    clips = clips or sorted(c for c, m in media.items() if m.get('use', True))
    center = float(opt('--crop', 0.45)) if '--center' in a else False
    work = [(c, media[c], None if center else hrstate.team_hsv(c, team), fps, center) for c in clips]
    with ProcessPoolExecutor(jobs) as ex:
        res = dict(ex.map(sample, work))
    OUT = os.path.join(hrstate.sub('sheets'), 'subject'); os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(OUT + '/subj_*'):
        os.remove(f)
    rows, meta = [], {}
    for c in clips:
        tiles = []
        for t, jpg, box in res[c]:
            im = Image.open(io.BytesIO(jpg)).convert('RGB').resize((TW, TH)) if jpg else Image.new('RGB', (TW, TH), (20, 20, 20))
            if box:
                meta[f'{c}@{t}'] = {'clip': c, 't': t, 'box_src': box}
            ImageDraw.Draw(im).text((3, 2), f'{t:.0f}', fill=(0, 255, 255), font=font); tiles.append(im)
        rows += [(c if j == 0 else '', tiles[j:j + COLS]) for j in range(0, len(tiles), COLS)]
    n = 0
    for s in range(0, len(rows), ROWS):
        n += 1; sheet = Image.new('RGB', (LW + COLS * TW, ROWS * TH), (16, 16, 16)); dr = ImageDraw.Draw(sheet)
        for r, (lab, ts) in enumerate(rows[s:s + ROWS]):
            dr.text((4, r * TH + TH // 2 - 8), lab, fill=(255, 255, 0), font=font)
            for k, im in enumerate(ts):
                sheet.paste(im, (LW + k * TW, r * TH))
        sheet.save(f'{OUT}/subj_{n:02d}.jpg', quality=88)
    json.dump(meta, open(f'{OUT}/subj_meta.json', 'w'))
    print(f'{len(clips)} clips, {n} sheets → {OUT}')
