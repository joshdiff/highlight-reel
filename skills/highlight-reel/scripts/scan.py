"""Team-colour blobs on every survey frame → sheets/blobs.json, using each clip's own jersey range
(per encoding). Also merges into media.clips: frame info and `looks` (flat|contrasty) — a Log clip
that looks contrasty (or Rec.709 that looks flat) is flagged: the camera was probably set differently."""
import os, sys, json
from concurrent.futures import ProcessPoolExecutor
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate
from detect import team_blobs

FR = hrstate.sub('frames')


def looks(imgs):
    hsv = np.concatenate([cv2.cvtColor(i, cv2.COLOR_BGR2HSV).reshape(-1, 3) for i in imgs])
    sat = hsv[:, 1].mean() / 255; v = hsv[:, 2] / 255
    spread = np.percentile(v, 97) - np.percentile(v, 3)
    return ('flat' if sat < 0.22 and spread < 0.6 else 'contrasty'), round(float(sat), 3), round(float(spread), 3)


def job(a):
    c, rng = a
    imgs = [cv2.imread(f'{FR}/{c}/frame_{k}.jpg') for k in range(5)]
    return c, [team_blobs(i, rng) for i in imgs], looks(imgs)


def info(c):
    p = open(f'{FR}/{c}/info.txt').read().strip().split(',', 6)  # path (last) may contain commas
    n, d = p[3].split('/')
    return dict(path=p[-1], width=int(p[1]), height=int(p[2]), fps=round(float(n) / float(d), 3),
                frames=int(p[4]) if p[4].isdigit() else None, duration=float(p[5]))


if __name__ == '__main__':
    clips = sorted(d for d in os.listdir(FR) if not d.startswith('.') and os.path.exists(f'{FR}/{d}/frame_4.jpg'))
    with ProcessPoolExecutor(10) as ex:
        out = list(ex.map(job, [(c, hrstate.team_hsv(c)) for c in clips]))
    res = {c: b for c, b, _ in out}
    json.dump(res, open(os.path.join(hrstate.sub('sheets'), 'blobs.json'), 'w'))
    mc = hrstate.get('media.clips', {}) or {}
    flagged = []
    for c, _, (lk, sat, spread) in out:
        e = mc.setdefault(c, {})
        for k, v in info(c).items():
            e.setdefault(k, v)
        e.update(looks=lk, look_sat=sat, look_spread=spread)
        kind = __import__('cameras').ENCODINGS.get(e.get('encoding') or '', {}).get('kind')
        if (kind == 'log' and lk == 'contrasty') or (kind == 'sdr' and lk == 'flat'):
            flagged.append(f"{c} ({e.get('encoding')} but looks {lk}: sat {sat}, spread {spread})")
    hrstate.set_('media.clips', mc)
    for th in (100, 150, 250, 400):
        print(f'blobs >= {th}px:', sum(1 for c in res for fr in res[c] for b in fr if b['area'] >= th))
    print(len(clips), 'clips scanned')
    if flagged:
        print('ENCODING MISMATCH — check these clips:\n  ' + '\n  '.join(flagged))
