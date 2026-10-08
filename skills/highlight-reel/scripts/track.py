"""Dense subject tracking for a shot list's on-ball phase.

Keys hand-read from a 2–5 fps grid lag a camera operator who swings fast on a close subject; the
subject drops out of a 9:16 window between keys. This follows the subject at --fps (default 8):
each sample takes the target-team player nearest the last x (within 30 units), weighted by size, so it
locks on a close player and ignores far teammates.

It replaces the shot list's player keys from `in` up to the first ball key or "fast" move (the shot or
pass) and keeps everything after (whips, holds, freeze). Zoom at each new key is taken from the rough
keys it replaces, so punch-ins survive. Start x = the first rough key's x, or --x0 when the first frame
has a decoy nearer the centre.

Usage: track.py SHOTLIST.json [--x0 X] [--fps 8] [--team home|away|TEAM_ID]"""
import os, sys, json, glob, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, hrstate
from detect import team_blobs
from crops import players

a = sys.argv[1:]
opt = lambda k, dflt: a[a.index(k) + 1] if k in a else dflt
path = a[0]; s = json.load(open(path)); keys = sorted(s['keys'], key=lambda k: k['t'])
fps = float(opt('--fps', 8))
end = next((k['t'] for k in keys if k.get('move') == 'fast' or k.get('subject') == 'ball'), s['out_t'])
x = float(opt('--x0', keys[0]['x']))
m = hrstate.get(f"media.clips.{s['src']}") or {'path': s['src']}
rng = hrstate.team_hsv(s['src'], opt('--team', None))


def zoom_at(t):
    before = [k for k in keys if k['t'] <= t]
    return (before[-1] if before else keys[0]).get('zoom', 1.0)


d = tempfile.mkdtemp()
subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-ss', str(s['in']), '-i', m['path'],
                '-t', str(end - s['in']), '-vf', f'fps={fps},scale=1280:-2', '-strict', 'unofficial',
                f'{d}/f_%04d.jpg'], check=True)
dense, held = [], 0
for i, f in enumerate(sorted(glob.glob(d + '/f_*.jpg'))):
    im = cv2.imread(f); H, W = im.shape[:2]; t = round(s['in'] + i / fps, 3)
    ps = [((g['x0'] + g['x1']) / 2 / W * 100, (g['y0'] + g['y1']) / 2 / H * 100, g['area'])
          for g in players(team_blobs(im, rng))]
    ps = [p for p in ps if abs(p[0] - x) <= 30]
    if not ps:
        held += 1; continue                       # no detection: keep the last good x (vcam holds it)
    px, py, _ = max(ps, key=lambda p: p[2] / (1 + abs(p[0] - x) / 10)); x = px
    dense.append({'t': t, 'x': round(px, 1), 'y': round(min(65, max(35, py)), 1), 'zoom': zoom_at(t),
                  'subject': 'player'})
s['keys'] = dense + [k for k in keys if k['t'] >= end]
json.dump(s, open(path, 'w'), indent=1)
print(f"{s['src']}: {len(dense)} tracked keys to {end}s ({held} samples held), "
      f"{len(s['keys']) - len(dense)} kept; x path {[k['x'] for k in dense][::4]}")
