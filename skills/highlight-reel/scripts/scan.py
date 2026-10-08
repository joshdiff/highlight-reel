"""Team-colour blobs on every survey frame, for each team in the game → sheets/blobs_<side>.json,
using each clip's own shirt range (per team, per encoding). Also merges `looks` (flat|contrasty) into
media.clips — a Log clip that looks contrasty (or Rec.709 that looks flat) is flagged: the camera was
probably set to a different picture profile.

Usage: python3 scan.py [--team home|away|TEAM_ID ...]   (default: every team calibrated for all encodings)"""
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
    c, rngs = a
    imgs = [cv2.imread(f'{FR}/{c}/frame_{k}.jpg') for k in range(5)]
    return c, {side: [team_blobs(i, r) for i in imgs] for side, r in rngs.items()}, looks(imgs)


if __name__ == '__main__':
    a = sys.argv[1:]
    sides = [hrstate.team_key(t)[0] for t in a[a.index('--team') + 1:]] if '--team' in a else list(hrstate.get('teams'))
    encs = list(hrstate.get('media.encodings') or {})
    skipped = [s for s in sides if not all(hrstate.calibrated(s, e) for e in encs)]
    sides = [s for s in sides if s not in skipped]
    for s in skipped:
        print(f"skip {s} ({hrstate.get(f'teams.{s}.name')}): shirt not calibrated for "
              f"{[e for e in encs if not hrstate.calibrated(s, e)]} — calibrate (hr-survey), then scan.py --team {s}")
    clips = sorted(d for d in os.listdir(FR) if not d.startswith('.') and os.path.exists(f'{FR}/{d}/frame_4.jpg'))
    work = [(c, {s: hrstate.team_hsv(c, s) for s in sides}) for c in clips]
    with ProcessPoolExecutor(10) as ex:
        out = list(ex.map(job, work))
    SH = hrstate.sub('sheets')
    for s in sides:
        json.dump({c: b[s] for c, b, _ in out}, open(os.path.join(SH, f'blobs_{s}.json'), 'w'))
        n = sum(1 for _, b, _ in out for fr in b[s] for x in fr if x['area'] >= 250)
        print(f"{s} ({hrstate.get(f'teams.{s}.name')}): {n} player-size blobs")
    import cameras
    mc = hrstate.get('media.clips', {}) or {}
    flagged = []
    for c, _, (lk, sat, spread) in out:
        e = mc.setdefault(c, {})
        e.update(looks=lk, look_sat=sat, look_spread=spread)
        kind = cameras.ENCODINGS.get(e.get('encoding') or '', {}).get('kind')
        if (kind == 'log' and lk == 'contrasty') or (kind == 'sdr' and lk == 'flat'):
            flagged.append(f"{c} ({e.get('encoding')} but looks {lk}: sat {sat}, spread {spread})")
    hrstate.set_('media.clips', mc)
    print(len(clips), 'clips scanned')
    if flagged:
        print('ENCODING MISMATCH — check these clips:\n  ' + '\n  '.join(flagged))
