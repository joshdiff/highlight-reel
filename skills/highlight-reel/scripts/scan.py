"""Team-colour blobs on every survey frame → sheets/blobs.json; also records clip info in reel.json media.clips."""
import os, sys, json
from concurrent.futures import ProcessPoolExecutor
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate
from detect import team_blobs

FR = hrstate.sub('frames')
RNG = hrstate.team_hsv()


def job(c):
    return c, [team_blobs(cv2.imread(f'{FR}/{c}/frame_{k}.jpg'), RNG) for k in range(5)]


def info(c):
    p = open(f'{FR}/{c}/info.txt').read().strip().split(',', 6)  # path (last) may contain commas
    n, d = p[3].split('/')
    return dict(path=p[-1], width=int(p[1]), height=int(p[2]), fps=round(float(n) / float(d), 3),
                frames=int(p[4]) if p[4].isdigit() else None, duration=float(p[5]))


if __name__ == '__main__':
    clips = sorted(d for d in os.listdir(FR) if not d.startswith('.') and os.path.exists(f'{FR}/{d}/frame_4.jpg'))
    with ProcessPoolExecutor(10) as ex:
        res = dict(ex.map(job, clips))
    json.dump(res, open(os.path.join(hrstate.sub('sheets'), 'blobs.json'), 'w'))
    hrstate.set_('media.clips', {c: info(c) for c in clips})
    for th in (100, 150, 250, 400):
        print(f'blobs >= {th}px:', sum(1 for c in res for fr in res[c] for b in fr if b['area'] >= th))
    print(len(clips), 'clips scanned')
